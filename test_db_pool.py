#!/usr/bin/env python3
# Verify DB pool
import sys
sys.path.insert(0, '.')
from zarabotok.pipeline_v3 import db
p = db.pool()
tables = p.query("SELECT name FROM sqlite_master WHERE type='table'")
print('DB tables:', [r[0] for r in tables])
print('OK')
p.close()
