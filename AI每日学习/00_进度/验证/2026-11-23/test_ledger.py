import sqlite3, subprocess, sys, tempfile, unittest
from pathlib import Path
from ledger_host import Ledger, bootstrap_fixture

I = ('op-1', 'account-A', 'sha256:fixture-content', 'backend-A:generation-1')
J = ('op-2', *I[1:])
FLAGS = dict(trusted=True, terminal=True, released=True)

class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.p = Path(self.tmp.name) / 'ops.db'
        bootstrap_fixture(self.p)
        self.l = Ledger(self.p)
        self.calls = []

    def tearDown(self):
        self.l.close()
        self.tmp.cleanup()

    def restart(self):
        self.l.close(); self.l = Ledger(self.p)

    def blocked(self, identity=J):
        self.assertEqual(self.l.submit(identity, self.calls.append), 'BLOCKED')
        self.assertEqual(self.calls, [])

    def child(self, tail):
        code = 'import os; from ledger_host import Ledger; l=Ledger(' + repr(str(self.p)) + '); i=' + repr(I) + '; ' + tail
        r = subprocess.run([sys.executable, '-c', code], cwd=Path(__file__).parent)
        self.assertEqual(r.returncode, 0)
        self.restart()

    def test_01_committed_before_dispatch(self):
        def dispatch(i):
            c = sqlite3.connect(str(self.p))
            self.assertEqual(c.execute('SELECT state,slot FROM ops').fetchall(), [('UNKNOWN', 1)])
            c.close(); self.calls.append(i)
        self.assertEqual(self.l.submit(I, dispatch), 'DISPATCHED')
        self.assertEqual(self.calls, [I])

    def test_02_restart_blocks_same_and_new_id(self):
        self.assertTrue(self.l.reserve(I)); self.restart()
        self.blocked(I); self.blocked(J)

    def test_03_process_exit_before_dispatch(self):
        self.child('assert l.reserve(i); os._exit(0)')
        self.blocked(I); self.blocked(J)

    def test_04_process_exit_after_dispatch(self):
        marker = Path(self.tmp.name) / 'sent.txt'
        self.child('l.submit(i, lambda _: open(' + repr(str(marker)) + ', "w").write("sent-once")); os._exit(0)')
        self.assertEqual(marker.read_text(), 'sent-once')
        self.blocked(I); self.blocked(J)

    def test_05_dispatch_exception_stays_unknown(self):
        def fail(_): raise RuntimeError('模拟回包丢失')
        self.assertEqual(self.l.submit(I, fail), 'UNKNOWN')
        self.restart(); self.blocked()

    def test_06_full_identity_match(self):
        self.assertTrue(self.l.reserve(I))
        for k in range(4):
            wrong = list(I); wrong[k] += '-wrong'
            self.assertFalse(self.l.finish(tuple(wrong), **FLAGS))
        self.blocked()

    def test_07_trust_terminal_release_required(self):
        self.assertTrue(self.l.reserve(I))
        for key in FLAGS:
            flags = dict(FLAGS); flags[key] = False
            self.assertFalse(self.l.finish(I, **flags))
        self.assertFalse(self.l.finish(I, trusted=1, terminal=True, released=True))
        self.blocked()

    def test_08_finish_unlock_no_old_replay(self):
        self.assertTrue(self.l.reserve(I)); self.restart()
        self.assertTrue(self.l.finish(I, **FLAGS))
        self.restart(); self.blocked(I)
        self.assertEqual(self.l.submit(J, self.calls.append), 'DISPATCHED')
        self.assertEqual(self.calls, [J])

    def test_09_missing_db_no_create(self):
        self.l.close(); self.p.unlink(); self.restart(); self.blocked()
        self.assertFalse(self.p.exists())

    def test_10_corruption_and_missing_schema(self):
        self.l.c.execute('DROP TABLE ops'); self.restart(); self.blocked()
        self.l.close(); self.p.write_bytes(b'not-a-database'); self.restart(); self.blocked()

    def test_11_sql_failure_never_dispatch(self):
        self.l.c.set_authorizer(lambda a, *rest: sqlite3.SQLITE_DENY if a == sqlite3.SQLITE_INSERT else sqlite3.SQLITE_OK)
        self.blocked(I)
        self.l.c.set_authorizer(lambda *args: sqlite3.SQLITE_OK)
        self.assertEqual(self.l.c.execute('SELECT count(*) FROM ops').fetchone(), (0,))

    def test_12_commit_failure_never_dispatch_or_unlock(self):
        deny = lambda a, x, *rest: sqlite3.SQLITE_DENY if a == sqlite3.SQLITE_TRANSACTION and x == 'COMMIT' else sqlite3.SQLITE_OK
        self.l.c.set_authorizer(deny); self.blocked(I)
        self.l.c.set_authorizer(lambda *args: sqlite3.SQLITE_OK)
        self.assertEqual(self.l.c.execute('SELECT count(*) FROM ops').fetchone(), (0,))
        self.assertTrue(self.l.reserve(I)); self.l.c.set_authorizer(deny)
        self.assertFalse(self.l.finish(I, **FLAGS)); self.l.c.set_authorizer(lambda *args: sqlite3.SQLITE_OK)
        self.restart(); self.blocked()

if __name__ == '__main__':
    print('EXECUTED_HOST Python=' + sys.version.split()[0] + ' sqlite3=' + sqlite3.sqlite_version, flush=True)
    print('usage=NOT_EXECUTED (没有模型调用)', flush=True)
    unittest.main(verbosity=2)
