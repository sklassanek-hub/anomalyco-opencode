"""Тесты модуля vk_scanner (заказы из публичных сообществ ВКонтакте)."""
import json
import os
import sys
import unittest
from urllib.parse import urlencode

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest import mock

from modules import vk_scanner


class TestExtractBudget(unittest.TestCase):
    def test_rub_with_spaces(self):
        b = vk_scanner._extract_budget("Бюджет 25 000 руб")
        self.assertIn("25000", b)

    def test_no_budget(self):
        self.assertEqual(vk_scanner._extract_budget("дорого"), "")

    def test_thousands_kwork_style(self):
        b = vk_scanner._extract_budget("Возьму до 30 тыс за парсер")
        self.assertIn("30000", b)


class TestFindContact(unittest.TestCase):
    def test_tg_handle(self):
        self.assertEqual(vk_scanner._find_contact("пиши @ivan_dev"), "@ivan_dev")

    def test_email_fallback(self):
        self.assertEqual(vk_scanner._find_contact("мыло: boss@firm.ru"), "boss@firm.ru")

    def test_no_contact(self):
        self.assertIsNone(vk_scanner._find_contact("без связи"))


class TestParseWallJson(unittest.TestCase):
    ITEMS = [{"id": 5, "text": "Нужен Telegram-бот на aiogram, бюджет 30000 руб. @zakazchik",
              "date": 1756100000}]

    def test_single_item_normalized(self):
        got = vk_scanner._parse_wall_json(self.ITEMS)
        self.assertEqual(len(got), 1)
        rec = got[0]
        self.assertEqual(rec["id"], 5)
        self.assertIn("aiogram", rec["text"])
        self.assertEqual(rec["date"], 1756100000)
        self.assertEqual(rec["contact"], "@zakazchik")
        self.assertIn("30000", rec["budget"])

    def test_short_and_empty_skipped(self):
        items = [{"id": 1, "text": "коротко"}, {"id": 2},
                 {"text": "y" * 50}, {"id": 4, "text": "z" * 41}]
        got = vk_scanner._parse_wall_json(items)
        self.assertEqual([r["id"] for r in got], [4])


class TestParseMobileHtml(unittest.TestCase):
    def test_json_pattern_escapes(self):
        raw = ('{"wall_id":"-99_12","text":"'
               '\\u041d\\u0443\\u0436\\u0435\\u043d \\u043f\\u0430\u0440\u0441\u0435\u0440 @buyer"}')
        html = f"<html><script type=\"text/javascript\">{raw}</script></html>"
        got = vk_scanner._parse_mobile_html(html, "demo")
        self.assertEqual(len(got), 1)
        key, text = got[0]
        self.assertEqual(key, "99_12")
        self.assertIn("@buyer", text)
        self.assertNotIn("\\u041d", text)

    def test_reversed_json_pattern(self):
        raw = '{"text":"Всем привет, ищем разработчика на проект","wall_id":"-8_3"}'
        got = vk_scanner._parse_mobile_html(raw, "demo")
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0][0], "8_3")
        self.assertIn("разработчика", got[0][1])

    def test_href_fallback_with_visible_text(self):
        html = ('<html><body><div class="wi_body"><a href="/wall-15_9"></a>'
                '<div class="pi_text">Требуется веб-парсер каталога поставщиков, оплата сдельная</div>'
                "</div></body></html>")
        got = vk_scanner._parse_mobile_html(html, "demo")
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0][0], "15_9")
        self.assertIn("парсер", got[0][1])

    def test_dedupe_and_empty(self):
        html = '{"wall_id":"-7_1","text":"первый пост"},{"wall_id":"-7_1","text":"второй дубль"}'
        self.assertEqual(len(vk_scanner._parse_mobile_html(html, "demo")), 1)
        self.assertEqual(vk_scanner._parse_mobile_html("<html></html>", "demo"), [])


class FakeResponse:
    def __init__(self, status_code=200, text="", url=""):
        self.status_code = status_code
        self.text = text
        self.url = url

    def json(self):
        return json.loads(self.text)


class FakeSession:
    """Мок requests.Session: routes — список (префикс полного URL, status, text)."""

    def __init__(self, routes=()):
        self.routes = sorted(routes, key=lambda t: len(t[0]), reverse=True)
        self.calls = []

    def get(self, url, timeout=None, params=None, **kw):
        full = url + ("?" + urlencode(params) if params else "")
        self.calls.append(full)
        for prefix, status, text in self.routes:
            if full.startswith(prefix):
                return FakeResponse(status, text, url=full)
        return FakeResponse(404, "", url=full)


POST_TEXT = "Нужен Telegram-бот на aiogram, бюджет 30000 руб. @zakazchik"
MOBILE_POST_HTML = (
    '<html><body><div id="wk_content">'
    '{"wall_id":"-42_777","text":"'
    "\\u041d\\u0443\\u0436\\u0435\\u043d \\u043f\\u0430\u0440\u0441\u0435\u0440 "
    "\u0441\u0430\u0439\u0442\u043e\u0432, \u0431\u044e\u0434\u0436\u0435\u0442 20 000 "
    "\u0440\u0443\u0431. \u041f\u0438\u0448\u0438\u0442\u0435 @buyer\"}"
    "</div></body></html>"
)


class TestFetchJobs(unittest.TestCase):
    def test_mode_b_mobile_parses_post(self):
        fake = FakeSession([("https://m.vk.com/demo", 200, MOBILE_POST_HTML)])
        with mock.patch.object(vk_scanner.http_client, "client", return_value=fake):
            jobs, errors = vk_scanner.fetch_jobs(
                {"enabled": True, "token": "", "groups": ["demo"], "max_per_group": 5})
        self.assertEqual(errors, [])
        self.assertEqual(len(jobs), 1)
        j = jobs[0]
        self.assertEqual(j["platform"], "VK")
        self.assertEqual(j["kind"], "order")
        self.assertEqual(j["job_id"], "vk:demo:777")
        self.assertEqual(j["url"], "https://vk.com/wall-42_777")
        self.assertEqual(j["author"], "demo")
        self.assertEqual(j["contact"], "@buyer")
        self.assertIn("20000", j["budget"])
        self.assertLessEqual(len(j["title"]), 140)
        self.assertLessEqual(len(j["description"]), 600)
        self.assertTrue(j["scanned_at"])
        self.assertEqual(fake.calls, ["https://m.vk.com/demo"])

    def test_mode_a_api_resolves_slug_and_parses_wall(self):
        wall_payload = json.dumps(
            {"response": {"count": 1, "items": [{"id": 5, "text": POST_TEXT, "date": 1756100000}]}},
            ensure_ascii=False)
        fake = FakeSession([
            ("https://api.vk.com/method/groups.getById?group_id=demo", 200,
             '{"response": {"groups": [{"id": 42, "screen_name": "demo"}]}}'),
            ("https://api.vk.com/method/wall.get?owner_id=-42", 200, wall_payload),
        ])
        with mock.patch.object(vk_scanner.http_client, "client", return_value=fake):
            jobs, errors = vk_scanner.fetch_jobs(
                {"enabled": True, "token": "TOK", "groups": ["demo"], "max_per_group": 10})
        self.assertEqual(errors, [])
        self.assertEqual(len(jobs), 1)
        j = jobs[0]
        self.assertEqual(j["job_id"], "vk:demo:5")
        self.assertEqual(j["url"], "https://vk.com/wall-42_5")
        self.assertEqual(j["contact"], "@zakazchik")
        self.assertIn("30000", j["budget"])
        self.assertTrue(any(c.startswith("https://api.vk.com/method/groups.getById?group_id=demo")
                            for c in fake.calls))
        self.assertTrue(any(c.startswith("https://api.vk.com/method/wall.get?owner_id=-42")
                            for c in fake.calls))

    def test_numeric_slug_skips_resolution(self):
        fake = FakeSession([
            ("https://api.vk.com/method/wall.get?owner_id=-77", 200,
             '{"response": {"items": []}}'),
        ])
        with mock.patch.object(vk_scanner.http_client, "client", return_value=fake):
            jobs, errors = vk_scanner.fetch_jobs(
                {"enabled": True, "token": "TOK", "groups": ["77"], "max_per_group": 5})
        self.assertTrue(all("groups.getById" not in c for c in fake.calls))
        self.assertEqual(len(fake.calls), 1)
        self.assertEqual(jobs, [])
        self.assertTrue(any("пуст" in e for e in errors))

    def test_disabled_or_empty_cfg(self):
        self.assertEqual(vk_scanner.fetch_jobs({"enabled": False, "groups": ["demo"]}), ([], []))
        self.assertEqual(vk_scanner.fetch_jobs({}), ([], []))
        self.assertEqual(vk_scanner.fetch_jobs(None), ([], []))

    def test_never_raises_on_any_response(self):
        fake = FakeSession([
            ("https://m.vk.com/boom500", 500, ""),
            ("https://m.vk.com/emptyhtml", 200, "<html><body>пусто</body></html>"),
            ("https://m.vk.com/loginpage", 200,
             "<html><body><h1>Авторизация</h1></body></html>"),
        ])
        with mock.patch.object(vk_scanner.http_client, "client", return_value=fake):
            jobs, errors = vk_scanner.fetch_jobs(
                {"enabled": True, "token": "",
                 "groups": ["boom500", "emptyhtml", "loginpage"], "max_per_group": 5})
        self.assertIsInstance(jobs, list)
        self.assertIsInstance(errors, list)
        self.assertEqual(jobs, [])
        self.assertEqual(len(errors), 3)
        self.assertTrue(all(isinstance(e, str) for e in errors))
        self.assertTrue(any("HTTP 500" in e for e in errors))
        self.assertTrue(any("вход" in e for e in errors))


if __name__ == "__main__":
    unittest.main(verbosity=2)
