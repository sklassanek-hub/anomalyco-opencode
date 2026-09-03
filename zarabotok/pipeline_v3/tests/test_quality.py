"""Тесты модуля quality и его интеграции в executor/proposals."""
import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest import mock

from modules import quality
from modules import proposals
from modules import executor


class TestQuality(unittest.TestCase):
    def test_inject_adds_standard(self):
        s = quality.inject("Ты — агент.")
        self.assertIn("СТАНДАРТ КАЧЕСТВА", s)
        self.assertTrue(s.startswith("Ты — агент."))

    def test_inject_no_duplicate(self):
        s = quality.inject("Ты — агент.")
        s2 = quality.inject(s)
        self.assertEqual(s, s2)

    def test_clean_removes_preamble(self):
        t = "Привет! Вот ваш готовый результат:\nКод готов, всё работает."
        out = quality.clean_output(t)
        self.assertNotIn("Привет", out)
        self.assertIn("Код готов", out)

    def test_clean_removes_epilogue(self):
        t = "Код готов.\n\nЕсли у вас остались вопросы, пишите. С уважением, (ваше имя)."
        out = quality.clean_output(t)
        self.assertNotIn("вопросы", out)
        self.assertNotIn("С уважением", out)
        self.assertIn("Код готов", out)

    def test_clean_keeps_real_content(self):
        t = "Реализуй функцию sort(x): возвращает отсортированный список. Сложность O(n log n)."
        self.assertEqual(quality.clean_output(t), t)

    def test_clean_empty(self):
        self.assertEqual(quality.clean_output(""), "")


class TestExecutorQuality(unittest.TestCase):
    def test_run_agent_injects_standard_and_cleans(self):
        with mock.patch.object(executor, "_read_agent_prompt", return_value="Роль: разработчик."), \
             mock.patch.object(executor, "_models", return_value={"coder": "m"}):
            captured = {}
            def fake_llm(model, system, user, **kw):
                captured["system"] = system
                return "Здравствуйте! Как ИИ, я проанализирую задачу. Готовый код:\nprint(1)"
            with mock.patch.object(executor, "_call_llm", side_effect=fake_llm):
                res = executor.run_agent("coder", "Сделай скрипт", role="coder")
        self.assertTrue(res["ok"])
        self.assertIn("СТАНДАРТ КАЧЕСТВА", captured["system"])
        self.assertNotIn("Здравствуйте", res["text"])
        self.assertNotIn("Как ИИ", res["text"])
        self.assertIn("Готовый код", res["text"])


class TestProposalsQuality(unittest.TestCase):
    def test_writer_prompt_has_standard(self):
        self.assertIn("СТАНДАРТ КАЧЕСТВА", proposals._WRITER_SYS)

    def test_template_draft_cleaned(self):
        job = {"title": "Сделать парсер Python", "description": "нужен parser",
               "budget": "5000", "url": "https://x/1"}
        # мокаем email чтобы не зависеть от конфига
        with mock.patch.object(proposals, "_our_email", return_value=""):
            out = proposals.template_draft(job)
        self.assertIn("По задаче", out)
        self.assertNotIn("Привет", out)

    def test_writer_draft_cleaned(self):
        def fake(mid, sys_p, user, **kw):
            captured["sys"] = sys_p
            return "Добрый день! Я помогу вам. Вот отклик: сделаю парсер за 3 дня."
        captured = {}
        with mock.patch.object(proposals, "_chat", side_effect=fake):
            out = proposals.writer_draft({"title": "парсер", "description": "x"}, chat_fn=fake)
        self.assertIn("СТАНДАРТ КАЧЕСТВА", captured["sys"])
        self.assertNotIn("Добрый день", out)
        self.assertNotIn("Я помогу", out)
        self.assertIn("отклик", out.lower())


if __name__ == "__main__":
    unittest.main(verbosity=2)
