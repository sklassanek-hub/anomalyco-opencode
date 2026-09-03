import subprocess
import sys
import os

os.chdir(r"C:\Users\klass\OneDrive\Desktop\work\zarabotok\pipeline")

DETACHED_PROCESS = 0x00000008
CREATE_NO_WINDOW = 0x08000000

services = [
    ("listener.py", "state/listener.out.log", "state/listener.err.log"),
    ("watchdog.py", "state/watchdog.out.log", "state/watchdog.err.log"),
]

for script, out_log, err_log in services:
    out_f = open(out_log, "w", encoding="utf-8", errors="ignore")
    err_f = open(err_log, "w", encoding="utf-8", errors="ignore")
    proc = subprocess.Popen(
        [sys.executable, script],
        stdout=out_f,
        stderr=err_f,
        creationflags=DETACHED_PROCESS | CREATE_NO_WINDOW,
        close_fds=True,
    )
    print(f"Started {script} with PID {proc.pid}")
    out_f.close()
    err_f.close()
