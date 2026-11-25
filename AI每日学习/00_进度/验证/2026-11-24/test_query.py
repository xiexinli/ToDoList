"""12项Host测试；仅隔离SQLite fixture，不访问真实后端或昨日数据库。"""
import unittest, sqlite3
from tempfile import TemporaryDirectory
from pathlib import Path
from ledger_host import Ledger, bootstrap_fixture
from query_host import Budget, QueryStub, FixtureAdapter, reconcile
I = ('op-1','account-A','sha256:fixture','backend-A:generation-1')

def receipt(**changes):
    r = dict(http=200, identity=I, trusted=True, terminal=True, released=True)
    r.update(changes); return r

class TestQuery(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory(); self.p = Path(self.tmp.name)/'ops.db'
        bootstrap_fixture(self.p); self.l = Ledger(self.p); self.assertTrue(self.l.reserve(I))
        self.finishes = 0; self.generations = []; self.old_finish = self.l.finish
        def finish(*args, **kwargs):
            self.finishes += 1; return self.old_finish(*args, **kwargs)
        self.l.finish = finish
    def tearDown(self):
        self.l.close(); self.tmp.cleanup()
    def state(self):
        return self.l.c.execute('SELECT state,slot FROM ops WHERE op_id=?',(I[0],)).fetchone()
    def blocked(self):
        self.assertEqual(self.state(), ('UNKNOWN',1))
        self.assertEqual(self.l.submit(('new-op',*I[1:]),self.generations.append),'BLOCKED')
        self.assertEqual(self.generations,[])
    def run_reply(self, r, approved_receipt=True):
        s=QueryStub([r]); b=Budget(1)
        a=FixtureAdapter(contract=True,scope=I,receipt=r if approved_receipt else None)
        out=reconcile(self.l,a,s,b)
        self.assertEqual(s.calls,[I]); self.assertEqual(b.remaining,0)
        return out
    def test_01_contract_and_scope_unapproved(self):
        for contract,scope in [(False,I),('true',I),(True,None),(True,('other',*I[1:]))]:
            with self.subTest(contract=contract,scope=scope):
                s=QueryStub([receipt()]); b=Budget(1)
                self.assertTrue(reconcile(self.l,FixtureAdapter(contract=contract,scope=scope),s,b).startswith('NOT_EXECUTED'))
                self.assertEqual(s.calls,[]); self.assertEqual(b.remaining,1); self.blocked()
        self.assertEqual(self.finishes,0)
    def test_02_query_failure(self):
        for r in [TimeoutError('fixture'),RuntimeError('fixture')]:
            self.assertIn('待确认',self.run_reply(r)); self.blocked()
        self.assertEqual(self.finishes,0)
    def test_03_404(self):
        self.assertIn('待确认',self.run_reply(receipt(http=404))); self.blocked()
        self.assertEqual(self.finishes,0)
    def test_04_unknown_running_or_malformed(self):
        for r in [None,{}, {'http':200,'state':'UNKNOWN'},receipt(terminal=False),receipt(http='200')]:
            self.assertIn('待确认',self.run_reply(r)); self.blocked()
        self.assertEqual(self.finishes,0)
    def test_05_all_four_identity_mismatches(self):
        for n in range(4):
            wrong=list(I); wrong[n]+='-wrong'
            self.assertIn('待确认',self.run_reply(receipt(identity=tuple(wrong)))); self.blocked()
        self.assertEqual(self.finishes,0)
    def test_06_missing_identity_or_evidence(self):
        for k in ['identity','trusted','terminal','released']:
            r=receipt(); del r[k]
            self.assertIn('待确认',self.run_reply(r)); self.blocked()
        self.assertEqual(self.finishes,0)
    def test_07_flags_must_be_strict_true(self):
        for k in ['trusted','terminal','released']:
            for value in [False,1,'true',None]:
                self.assertIn('待确认',self.run_reply(receipt(**{k:value}))); self.blocked()
        self.assertEqual(self.finishes,0)
    def test_08_payload_trusted_is_not_verifier(self):
        self.assertIn('待确认',self.run_reply(receipt(),False)); self.blocked()
        self.assertEqual(self.finishes,0)
    def test_09_budget_exhaustion_keeps_pending(self):
        s=QueryStub([{'http':404},TimeoutError('fixture'),receipt()]);b=Budget(2)
        a=FixtureAdapter(contract=True,scope=I)
        for _ in range(2): self.assertIn('待确认',reconcile(self.l,a,s,b))
        for _ in range(3): self.assertIn('预算耗尽',reconcile(self.l,a,s,b))
        self.assertEqual(s.calls,[I,I]); self.assertEqual(b.remaining,0)
        self.assertEqual(self.finishes,0); self.blocked()
    def test_10_verified_terminal_release_only_finishes(self):
        self.assertEqual(self.run_reply(receipt()),'已对账：终结并释放')
        self.assertEqual(self.finishes,1);self.assertEqual(self.state(),('TERMINAL',None))
        self.assertEqual(self.l.c.execute('SELECT count(*) FROM ops').fetchone(),(1,))
        self.assertEqual(self.generations,[])  # 解锁后也没有自动新生成。
        self.assertEqual(self.l.submit(I,self.generations.append),'BLOCKED')
    def test_11_missing_ledger_does_not_query(self):
        l=Ledger(Path(self.tmp.name)/'missing.db');s=QueryStub([receipt()]);b=Budget(1)
        a=FixtureAdapter(contract=True,scope=I)
        self.assertIn('账本不可读',reconcile(l,a,s,b));self.assertEqual(s.calls,[])
        self.assertFalse((Path(self.tmp.name)/'missing.db').exists());self.blocked()
    def test_12_finish_write_or_commit_failure(self):
        for kind in ['update','commit']:
            def auth(code,a,b,c,d):
                deny=(kind=='update' and code==sqlite3.SQLITE_UPDATE) or (kind=='commit' and code==sqlite3.SQLITE_TRANSACTION and a=='COMMIT')
                return sqlite3.SQLITE_DENY if deny else sqlite3.SQLITE_OK
            self.l.c.set_authorizer(auth)
            self.assertIn('待确认',self.run_reply(receipt()))
            self.l.c.set_authorizer(lambda *args:sqlite3.SQLITE_OK)
            self.blocked()
        self.assertEqual(self.finishes,2)

if __name__ == '__main__':
    unittest.main(verbosity=2)
