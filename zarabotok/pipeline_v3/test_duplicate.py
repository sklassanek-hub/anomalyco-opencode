import subprocess, time, os, sys
BASE = r"C:\Users\klass\OneDrive\Desktop\work\zarabotok\pipeline_v3"

# Удаляем старый pid-файл
pid_file = os.path.join(BASE, "state", "watchdog.pid")
if os.path.exists(pid_file):
    os.remove(pid_file)

# Запускаем первый watchdog в фоне
proc1 = subprocess.Popen(
    [sys.executable, "watchdog.py"],
    cwd=BASE,
    stdout=open(os.path.join(BASE, "state", "test1.out.log"), "w"),
    stderr=open(os.path.join(BASE, "state", "test1.err.log"), "w"),
)
print(f"Запущен первый watchdog, pid={proc1.pid}")

# Ждём, чтобы он написал свой pid-файл
time.sleep(3)

# Проверяем pid-файл
if os.path.exists(pid_file):
    with open(pid_file) as f:
        saved_pid = f.read().strip()
    print(f"watchdog.pid содержит: {saved_pid}")
    if saved_pid == str(proc1.pid):
        print("[OK] pid-файл корректен (watchdog.pid, без .py)")
    else:
        print("[FAIL] pid-файл не совпадает!")
else:
    print("[FAIL] watchdog.pid не создан!")

# Пробуем запустить второй экземпляр (должен выйти с кодом 1 из-за дублирования)
proc2 = subprocess.Popen(
    [sys.executable, "watchdog.py"],
    cwd=BASE,
    stdout=open(os.path.join(BASE, "state", "test2.out.log"), "w"),
    stderr=open(os.path.join(BASE, "state", "test2.err.log"), "w"),
)
print(f"Запущен второй watchdog, pid={proc2.pid}")

# Ждём завершения второго (он должен быстро выйти)
try:
    proc2.wait(timeout=5)
    exit_code = proc2.returncode
    print(f"Второй watchdog завершился с кодом: {exit_code}")
    if exit_code == 1:
        print("[OK] дублирование предотвращено (выход 1)")
    else:
        print(f"[FAIL] ожидался код 1, получен {exit_code}")
except subprocess.TimeoutExpired:
    print("[FAIL] второй watchdog не завершился за 5 сек (не остановился)")
    proc2.kill()

# Останавливаем первый
proc1.kill()
proc1.wait()
print("Первый watchdog остановлен.")
