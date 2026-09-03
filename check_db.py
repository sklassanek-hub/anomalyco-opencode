import sqlite3, os
conn = sqlite3.connect("zarabotok/pipeline_v3/state/pipeline_state.db")
c = conn.cursor()
c.execute("SELECT name FROM sqlite_master WHERE type='table'")
print("Tables:", [r[0] for r in c.fetchall()])
c.execute("SELECT name FROM sqlite_master WHERE type='index'")
print("Indexes:", [r[0] for r in c.fetchall()])
c.execute("SELECT * FROM sqlite_master WHERE type='table' AND name='exec_tasks'")
print("exec_tasks sql:", c.fetchone()[4])
