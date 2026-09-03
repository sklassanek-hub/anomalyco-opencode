# DB connection pool module (P1 [ ] DB connection pool)
# Wraps sqlite3 with WAL + connection reuse for pipeline_state.db.
import sqlite3, threading, os

class PipelineDB:
    def __init__(self, path='zarabotok/pipeline_v3/state/pipeline_state.db'):
        self.path = path
        self._lock = threading.Lock()
        self._conn = None
        self._open()

    def _open(self):
        if not os.path.exists(self.path):
            print('DB does not exist:', self.path)
            return
        self._conn = sqlite3.connect(self.path, check_same_thread=False, timeout=30)
        self._conn.execute('PRAGMA journal_mode=WAL;')
        self._conn.execute('PRAGMA foreign_keys=ON;')

    def get(self):
        if self._conn is None:
            self._open()
        return self._conn

    def execute(self, sql, params=()):
        with self._lock:
            cur = self.get().execute(sql, params)
            self.get().commit()
            return cur

    def query(self, sql, params=()):
        with self._lock:
            cur = self.get().execute(sql, params)
            return cur.fetchall()

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None

_pool = None

def pool():
    global _pool
    if _pool is None:
        _pool = PipelineDB()
    return _pool
