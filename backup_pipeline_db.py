#!/usr/bin/env python3
# DB backup cron script (P2)
# Copies pipeline_state.db to state/backup/ with timestamp.
import os, shutil, datetime
src = 'zarabotok/pipeline_v3/state/pipeline_state.db'
dst_dir = 'zarabotok/pipeline_v3/state/backup'
os.makedirs(dst_dir, exist_ok=True)
ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
dst = os.path.join(dst_dir, f'pipeline_state_{ts}.db')
if os.path.exists(src):
    shutil.copy2(src, dst)
    print(f'DB backup: {src} -> {dst} ({os.path.getsize(dst)} bytes)')
else:
    print('DB not found, skip')
