"""Тесты песочницы: реальный запуск кода с лимитами/без сети."""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules import sandbox


def _tmp_py(code: str) -> str:
    # ТЗ §11.3: запуск только внутри workspace/
    ws = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "workspace")
    os.makedirs(ws, exist_ok=True)
    d = tempfile.mkdtemp(prefix="sbtest_", dir=ws)
    p = os.path.join(d, "t.py")
    with open(p, "w", encoding="utf-8") as f:
        f.write(code)
    return p


class TestSandbox(unittest.TestCase):
    def test_ok(self):
        r = sandbox.run_smoke(_tmp_py("print('hello')"), timeout=15)
        self.assertTrue(r["ok"], r)
        self.assertIn("hello", r["stdout"])

    def test_fail_code(self):
        r = sandbox.run_smoke(_tmp_py("raise ValueError('boom')"), timeout=15)
        self.assertFalse(r["ok"])
        self.assertIn("boom", r["stderr"])

    def test_timeout_killed(self):
        r = sandbox.run_smoke(_tmp_py("while True:\n    pass\n"), timeout=3)
        self.assertFalse(r["ok"])
        self.assertTrue(r["killed"])

    def test_network_blocked(self):
        code = (
            "import socket\n"
            "try:\n"
            "    s = socket.socket(); s.connect(('127.0.0.1', 80))\n"
            "except RuntimeError as e:\n"
            "    print('NET_BLOCKED_OK')\n"
        )
        r = sandbox.run_smoke(_tmp_py(code), timeout=15)
        self.assertTrue(r["ok"], r)
        self.assertIn("NET_BLOCKED_OK", r["stdout"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
