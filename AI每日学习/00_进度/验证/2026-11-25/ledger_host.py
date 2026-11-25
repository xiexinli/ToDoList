"""仅Host fixture：单全局占位；不联网、不认证、不保证跨进程exactly-once。"""
import sqlite3
from pathlib import Path

SCHEMA = """CREATE TABLE ops (
 op_id TEXT PRIMARY KEY NOT NULL, account TEXT NOT NULL,
 digest TEXT NOT NULL, backend TEXT NOT NULL,
 state TEXT NOT NULL CHECK(state IN ('UNKNOWN','TERMINAL')),
 slot INTEGER UNIQUE,
 CHECK((state='UNKNOWN' AND slot IS NOT NULL AND slot=1) OR (state='TERMINAL' AND slot IS NULL)))"""

def connect(path):
    # rw不创建：丢库、换错路径不能当作“没有任务”。
    c = sqlite3.connect(Path(path).resolve().as_uri() + '?mode=rw',
                        uri=True, isolation_level=None, timeout=0.2)
    try:
        c.execute('PRAGMA synchronous=FULL')
        if c.execute('PRAGMA quick_check').fetchone() != ('ok',):
            raise ValueError('数据库损坏')
        if c.execute("SELECT sql FROM sqlite_master WHERE name='ops'").fetchone() != (SCHEMA,):
            raise ValueError('账本结构缺失或不兼容')
        return c
    except Exception:
        c.close()
        raise

def bootstrap_fixture(path):
    # 仅全新教学fixture显式初始化；恢复路径绝不调用它。
    with Path(path).open('xb'):
        pass
    c = sqlite3.connect(str(path))
    try:
        c.execute(SCHEMA)
        c.commit()
    finally:
        c.close()

def valid(identity):
    return isinstance(identity, tuple) and len(identity) == 4 and all(
        isinstance(x, str) and x for x in identity)

class Ledger:
    def __init__(self, path):
        self.c = None
        try:
            self.c = connect(path)
        except (OSError, ValueError, sqlite3.Error):
            pass  # 失败关闭；不能自动修复、删库或创建空库。

    def close(self):
        if self.c is not None:
            self.c.close()
            self.c = None

    def rollback(self):
        try:
            self.c.execute('ROLLBACK')
        except sqlite3.Error:
            self.close()  # 回滚也失败时关闭，之后全部拒绝。

    def reserve(self, identity):
        if self.c is None or not valid(identity):
            return False
        try:
            self.c.execute('BEGIN IMMEDIATE')
            if self.c.execute('SELECT 1 FROM ops WHERE slot=1').fetchone():
                self.c.execute('ROLLBACK')
                return False
            self.c.execute('INSERT INTO ops VALUES (?,?,?,?,?,?)',
                           (*identity, 'UNKNOWN', 1))
            self.c.execute('COMMIT')  # 必须成功返回后才可dispatch。
            return True
        except sqlite3.Error:
            self.rollback()
            return False

    def submit(self, identity, dispatch):
        if not self.reserve(identity):
            return 'BLOCKED'
        try:
            dispatch(identity)  # 此时库中已保守占位；成功返回也不代表释放。
            return 'DISPATCHED'
        except Exception:
            return 'UNKNOWN'  # 不重发、不清占位。

    def finish(self, identity, *, trusted=False, terminal=False, released=False):
        # trusted只是测试夹具输入，不是签名、TLS或真实后端认证。
        if self.c is None or not valid(identity) or not all(
                x is True for x in (trusted, terminal, released)):
            return False
        try:
            self.c.execute('BEGIN IMMEDIATE')
            changed = self.c.execute(
                "UPDATE ops SET state='TERMINAL',slot=NULL WHERE op_id=? "
                "AND account=? AND digest=? AND backend=? AND slot=1",
                identity).rowcount
            self.c.execute('COMMIT')  # 终结与释放同一事务，失败不能解锁。
            return changed == 1
        except sqlite3.Error:
            self.rollback()
            return False
