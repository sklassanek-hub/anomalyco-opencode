@echo off
REM Zarabotok autostart: proxy + LM Studio + watchdog (workers)
cd /d C:\Users\klass\OneDrive\Desktop\work\zarabotok\pipeline_v3
start "" /min "C:\Users\klass\OneDrive\Desktop\work\zarabotok\pipeline\tools\singbox\sing-box.exe" run -c "C:\Users\klass\OneDrive\Desktop\work\zarabotok\pipeline\tools\singbox\config.json"
start "" /min "%USERPROFILE%\.lmstudio\bin\lms.exe" server start
timeout /t 5 /nobreak >nul
start "" /min python watchdog.py
