"""Исполнение задач: честный пайплайн plan -> implement -> validate -> repair ->
package -> review. Статус done ставится ТОЛЬКО после явной доставки клиенту
(POST /api/order/<url>/deliver -> executor.deliver_result)."""
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, ".")

from modules import crm, executor, llm, store  # noqa: E402
try:
    from modules import sandbox as _sandbox  # noqa: E402
except Exception:
    _sandbox = None

INTERVAL = 60
PARALLEL_TASKS = 1  # локальная LLM тяжёлая — генерации строго по одной
STEP_TIMEOUT_MULT = 6


def _runtime_qa_enabled() -> bool:
    try:
        with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                               "config.json"), encoding="utf-8") as f:
            return bool(json.load(f).get("executors", {}).get("runtime_qa", True))
    except Exception:
        return True


def _log(url: str, msg: str):
    crm.agents_log(url, "exec_worker", msg)


def _cancelled(url: str) -> bool:
    t = executor.task_for(url)
    return not t or t.get("status") != "running" or bool(t.get("cancel_requested"))


def run_task(task: dict) -> int:
    """Полный цикл исполнения одной задачи (в своём потоке)."""
    if not task or task.get("status") != "queued":
        return 0
    url = task.get("url", "")
    cfg = llm.model_cfg()
    step_timeout = int(cfg.get("timeout") or 600)
    deadline = time.monotonic() + step_timeout * STEP_TIMEOUT_MULT

    if not executor.set_status(url, "running"):
        return 0
    tz = task.get("tz") or task.get("title") or ""
    _log(url, f"пайплайн запущен: plan -> implement -> validate -> repair")

    # 1. План файлов
    plan = executor.plan_files(tz)[:executor.EXEC_MAX_FILES]
    _log(url, "план файлов: " + ", ".join(f["path"] for f in plan))

    ver = task.get("version") or "v1"
    version_d = executor.version_dir(url, ver)
    results = []

    for f in plan:
        path, desc = f["path"], f.get("desc", "")
        if _cancelled(url):
            _log(url, f"задача отменена, файл пропущен: {path}")
            return 1
        if time.monotonic() >= deadline:
            executor.set_status(url, "failed", note="timeout пайплайна")
            _log(url, "failed: timeout")
            return 1

        code = executor.implement_file(tz, path, desc, ctx=plan)
        abs_path = executor.write_project_file(version_d, path, code or "") if code else None
        if not code or not abs_path:
            results.append({"path": path, "ok": False,
                            "errors": ["генерация не удалась"]})
            _log(url, f"{path}: генерация не удалась")
            continue

        errs = executor.validate_file(abs_path)
        # статический контроль качества: заглушки/опасные вызовы (ТЗ#4 11.4)
        code_errs = executor.lint_code(code or "")
        if code_errs:
            errs = (errs or []) + code_errs
        # RUNTIME QA (ТЗ#4 11.5): пробный запуск .py в песочнице (Job Object, без сети)
        if not errs and _sandbox and path.lower().endswith(".py") and _runtime_qa_enabled():
            res = _sandbox.run_smoke(abs_path, timeout=90)
            if not res.get("ok"):
                why = "таймаут" if res.get("killed") else f"exit {res.get('code')}"
                tail = (res.get("stderr") or res.get("stdout") or "")[-220:].replace("\n", " ")
                errs = (errs or []) + [f"runtime smoke ({why}): {tail}"]
                _log(url, f"{path}: runtime smoke fail — в ремонт")
        for round_no in range(1, executor.EXEC_REPAIR_ROUNDS + 1):
            if not errs:
                break
            _log(url, f"{path}: валидация не прошла ({round_no}/{executor.EXEC_REPAIR_ROUNDS}), ремонт")
            fixed = executor.repair_file(tz, path, code, "\n".join(errs))
            if not fixed:
                break
            new_path = executor.write_project_file(version_d, path, fixed)
            if not new_path:
                break
            code = fixed
            abs_path = new_path
            errs = executor.validate_file(abs_path)

        results.append({"path": path, "ok": not errs, "errors": [e[:200] for e in errs]})
        _log(url, f"{path}: {'ok' if not errs else 'ошибки: ' + str(len(errs))}")

    status = executor.finish_task(url, results)
    return 1


def run_pending(tasks: list) -> int:
    queued = [t for t in tasks if t.get("status") == "queued"]
    if not queued:
        return 0
    done = 0
    with ThreadPoolExecutor(max_workers=PARALLEL_TASKS) as ex:
        futures = [ex.submit(run_task, t) for t in queued]
        for fut in futures:
            try:
                done += 1 if fut.result() else 0
            except Exception as e:
                print(f"exec_worker task error: {e}", flush=True)
    return done


def main() -> int:
    print(f"exec_worker v2 (honest pipeline) start, interval {INTERVAL}s", flush=True)
    while True:
        try:
            tasks = [t for t in executor.tasks() if t.get("status") == "queued"]
            if tasks:
                n = run_pending(tasks)
                print(f"exec_worker: обработано {n} задач", flush=True)
        except Exception as e:
            print(f"exec_worker error: {e}", flush=True)
        time.sleep(INTERVAL)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
