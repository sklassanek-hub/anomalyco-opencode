"""Тесты QA-гейтов: скам-фильтр, анти-дубль, матчинг USDT-платежей."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules import billing, proposals, sender


def setUpModule():
    from modules import proposals as _P
    _P.AUTHOR_SPAM.clear()


class TestScamGate(unittest.TestCase):
    def test_scam_positive(self):
        for t in ("Ищем воркеров по кардингу", "Нужны люди, оплата ежедневно",
                  "Схема заработка без вложений", "Кладмен требуется"):
            self.assertTrue(proposals.is_scam({"title": t}), t)

    def test_scam_negative(self):
        for t in ("Нужен парсер маркетплейса на Python", "Телеграм-бот магазина aiogram",
                  "Доработать сайт на WordPress", "Написать SEO-текст"):
            self.assertFalse(proposals.is_scam({"title": t}), t)

    def test_outbox_skips_scam(self):
        jobs = [dict(url="s://x/1", title="Воркеры по кардингу", description="Нужен скрипт автоматизации отчётов под Windows, детали в личке @client111", score=5),
                dict(url="s://x/2", title="Бот для магазина", description="Нужен Telegram-магазин на aiogram с оплатой и админкой, пишите @shop прямо в личку", score=5)]
        cap = {}

        def fake_mutate(name, fn, default):
            b = default.copy()
            res = fn(b)
            cap["items"] = b.get("items", [])
            return res

        orig = proposals.store.mutate
        proposals.store.mutate = fake_mutate
        try:
            drafts = proposals.build_outbox(jobs, chat_fn=lambda *a, **k: None, llm_top_n=0)
        finally:
            proposals.store.mutate = orig
        self.assertEqual(drafts, 1)  # скам отсеян, чистый с контактом прошёл


class TestTextSimilar(unittest.TestCase):
    def test_identical(self):
        self.assertTrue(sender.text_similar("Готов сделать парсер за 2 дня. Какие поля?",
                                            "готов сделать парсер за 2 дня. какие поля?"))

    def test_different(self):
        self.assertFalse(sender.text_similar(
            "Парсер цен Ozon на Python + выгрузка Excel, 3 дня.",
            "Бот-магазин с оплатой и админкой на aiogram, неделя."))


class TestUsdtMatch(unittest.TestCase):
    def test_match_found(self):
        invs = [{"no": "ZB-1", "amount": 15000, "method": "usdt"},
                {"no": "ZB-2", "amount": 5000.5, "method": "usdt"}]
        self.assertEqual(billing._match_invoice(invs, 15000.0)["no"], "ZB-1")
        self.assertEqual(billing._match_invoice(invs, 5000.504)["no"], "ZB-2")

    def test_no_match(self):
        invs = [{"no": "ZB-1", "amount": 15000, "method": "usdt"}]
        self.assertIsNone(billing._match_invoice(invs, 9999))
        self.assertIsNone(billing._match_invoice([], 15000))


if __name__ == "__main__":
    unittest.main(verbosity=2)
