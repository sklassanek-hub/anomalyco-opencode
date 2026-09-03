import sqlite3, os
path = 'zarabotok/pipeline_v3/state/pipeline_state.db'
if not os.path.exists(path):
    print('DB MISSING')
else:
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [r[0] for r in cur.fetchall()]
    print('DB tables:', tables)
    for t in tables:
        try:
            cur.execute(f"SELECT COUNT(*) FROM {t}")
            count = cur.fetchone()[0]
            print(' ', t, 'rows:', count)
        except Exception as e:
            print(' ', t, 'count error:', e)
    cur.execute("SELECT name FROM sqlite_master WHERE type='index';")
    indexes = [r[0] for r in cur.fetchall()]
    print('Indexes:', indexes)
    conn.close()
