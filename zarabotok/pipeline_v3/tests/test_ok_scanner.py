"""Тесты модуля ok_scanner (парсер публичных тем ok.ru)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest import mock

from modules import ok_scanner


class TestExtractBudget(unittest.TestCase):
    def test_rub_with_spaces(self):
        b = ok_scanner._extract_budget("Оплата 12 000 руб")
        self.assertIn("12000", b)

    def test_no_budget(self):
        self.assertEqual(ok_scanner._extract_budget("без бюджета"), "")


class TestFindContact(unittest.TestCase):
    def test_tg_handle(self):
        self.assertEqual(ok_scanner._find_contact("Пишите @shop_owner"), "@shop_owner")

    def test_email_fallback(self):
        self.assertEqual(ok_scanner._find_contact("мыло: boss@firm.ru"), "boss@firm.ru")

    def test_no_contact(self):
        self.assertIsNone(ok_scanner._find_contact("без связи"))


class TestParseTopicsHtml(unittest.TestCase):
    def test_two_links(self):
        html = ('<html><body>'
                '<div><a href="/myslug/topic/123456" class="tile">Нужен дизайн логотипа срочно</a></div>'
                '<div><a href="/myslug/topic/789">Требуется парсер сайта на Python</a></div>'
                '</body></html>')
        got = ok_scanner._parse_topics_html(html, "myslug")
        self.assertEqual(len(got), 2)
        for href, snippet in got:
            self.assertTrue(href.startswith("/"))
            self.assertIsInstance(snippet, str)
        ids = {h.rstrip("/").rsplit("/", 1)[-1] for h, _ in got}
        self.assertIn("123456", ids)
        self.assertIn("789", ids)

    def test_bare_link_fallback(self):
        html = ('<html><body>'
                '<a href="/myslug/topic/555"></a><div class="t">Ищу копирайтера для блога</div>'
                '</body></html>')
        got = ok_scanner._parse_topics_html(html, "myslug")
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0][0], "/myslug/topic/555")

    def test_empty_html(self):
        self.assertEqual(ok_scanner._parse_topics_html("<html></html>", "myslug"), [])


class FakeResponse:
    def __init__(self, status_code=200, text=""):
        self.status_code = status_code
        self.text = text


class FakeSession:
    """Мок requests.Session: routes — список (точный url, status, text)."""

    def __init__(self, routes=()):
        self.routes = list(routes)
        self.calls = []

    def get(self, url, timeout=None, **kw):
        self.calls.append(url)
        for u, status, text in self.routes:
            if url == u:
                return FakeResponse(status, text)
        return FakeResponse(404, "")


LIST_HTML = (
    "<html><body>"
    '<div><a href="/demo/topic/123456">Требуется парсер сайта на Python</a></div>'
    '<div><a href="/demo/topic/789">Нужен дизайн логотипа для магазина</a></div>'
    "</body></html>"
)
TOPIC_HTML_1 = (
    "<html><body>"
    '<div class="media-text__text">Требуется парсер сайта. Бюджет 15 000 руб. Пишите @shop_owner</div>'
    "</body></html>"
)
TOPIC_HTML_2 = (
    "<html><body>"
    '<div class="media-text__text">Нужен логотип для магазина. Оплата договорная, мыло: boss@firm.ru</div>'
    "</body></html>"
)


class TestFetchJobs(unittest.TestCase):
    def test_fetch_jobs_with_fake_session(self):
        fake = FakeSession([
            ("https://ok.ru/demo/topics", 200, LIST_HTML),
            ("https://ok.ru/demo/topic/123456", 200, TOPIC_HTML_1),
            ("https://ok.ru/demo/topic/789", 200, TOPIC_HTML_2),
        ])
        with mock.patch.object(ok_scanner.http_client, "client", return_value=fake):
            jobs, errors = ok_scanner.fetch_jobs(
                {"enabled": True, "groups": ["demo"], "max_per_group": 5})
        self.assertTrue(jobs or errors)
        self.assertTrue(jobs)
        self.assertEqual(errors, [])
        self.assertEqual(len(jobs), 2)
        for j in jobs:
            self.assertEqual(j["platform"], "OK")
            self.assertEqual(j["kind"], "order")
            self.assertTrue(j["job_id"].startswith("ok:demo:"))
            self.assertTrue(j["url"].startswith("https://ok.ru/demo/topic/"))
            self.assertEqual(j["author"], "demo")
            self.assertTrue(j["scanned_at"])
            self.assertLessEqual(len(j["title"]), 140)
            self.assertLessEqual(len(j["description"]), 600)
        by_id = {j["job_id"]: j for j in jobs}
        self.assertIn("ok:demo:123456", by_id)
        self.assertIn("ok:demo:789", by_id)
        self.assertEqual(by_id["ok:demo:123456"]["contact"], "@shop_owner")
        self.assertIn("15000", by_id["ok:demo:123456"]["budget"])
        self.assertEqual(by_id["ok:demo:789"]["contact"], "boss@firm.ru")
        # GET'ов: 1 список + 2 детали топиков, лимит 5 не превышен
        self.assertEqual(len(fake.calls), 3)

    def test_fetch_jobs_disabled(self):
        jobs, errors = ok_scanner.fetch_jobs({"enabled": False, "groups": ["demo"]})
        self.assertEqual((jobs, errors), ([], []))

    def test_fetch_jobs_no_topics_is_error_not_exception(self):
        fake = FakeSession([("https://ok.ru/closed/topics", 200, "<html>пусто</html>")])
        with mock.patch.object(ok_scanner.http_client, "client", return_value=fake):
            jobs, errors = ok_scanner.fetch_jobs(
                {"enabled": True, "groups": ["closed"], "max_per_group": 5})
        self.assertEqual(jobs, [])
        self.assertTrue(any("тем не найдено" in e for e in errors))

    def test_fetch_jobs_never_raises_on_http_error(self):
        fake = FakeSession()  # все ответы 404
        with mock.patch.object(ok_scanner.http_client, "client", return_value=fake):
            jobs, errors = ok_scanner.fetch_jobs(
                {"enabled": True, "groups": ["demo"], "max_per_group": 5})
        self.assertEqual(jobs, [])
        self.assertTrue(any("HTTP 404" in e for e in errors))


if __name__ == "__main__":
    unittest.main(verbosity=2)
