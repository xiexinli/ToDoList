import unittest,sqlite3,subprocess,sys,os
from pathlib import Path
from tempfile import TemporaryDirectory
from ledger_host import Ledger,bootstrap_fixture
from query_host import FixtureAdapter,QueryStub
from budget_host import PersistentBudget,seed_budget_fixture,reconcile_persistent as reconcile
I=('op-1','account-A','sha256:fixture','backend-A:generation-1')
class Tests(unittest.TestCase):
 def setUp(self):
  self.tmp=TemporaryDirectory();self.p=Path(self.tmp.name)/'ops.db';bootstrap_fixture(self.p)
  self.l=Ledger(self.p);self.assertTrue(self.l.reserve(I));seed_budget_fixture(self.l,I,2)
  self.b=PersistentBudget(self.p,I);self.q=QueryStub([{'http':404},TimeoutError('fixture')])
  self.a=FixtureAdapter(contract=True,scope=I);self.generated=[]
 def tearDown(self):self.b.close();self.l.close();self.tmp.cleanup()
 def remaining(self):return self.l.c.execute('SELECT remaining FROM query_budget').fetchone()[0]
 def pending(self):
  self.assertEqual(self.l.c.execute('SELECT state,slot FROM ops').fetchone(),('UNKNOWN',1))
  self.assertEqual(self.l.submit(('new-id',*I[1:]),self.generated.append),'BLOCKED');self.assertEqual(self.generated,[])
 def restart(self):
  self.b.close();self.l.close();self.l=Ledger(self.p);self.b=PersistentBudget(self.p,I)
 def test_01_restore_is_not_query(self):
  self.restart();self.assertEqual(self.q.calls,[]);self.assertEqual(self.remaining(),2);self.pending()
 def test_02_reopen_does_not_refill(self):
  self.assertTrue(self.b.take());self.restart();self.assertEqual(self.remaining(),1)
  self.assertTrue(self.b.take());self.restart();self.assertFalse(self.b.take());self.assertEqual(self.remaining(),0)
 def test_03_failure_charges_no_refund(self):
  for _ in range(2):self.assertIn('待确认',reconcile(self.l,self.a,self.q,self.b))
  self.assertEqual(self.remaining(),0);self.assertEqual(len(self.q.calls),2);self.pending()
 def test_04_exhaustion_no_more_queries(self):
  for _ in range(2):self.b.take()
  self.restart()
  for _ in range(3):self.assertIn('预算耗尽',reconcile(self.l,self.a,self.q,self.b))
  self.assertEqual(self.q.calls,[]);self.pending()
 def child(self,tail):
  code='from budget_host import PersistentBudget; import os; b=PersistentBudget('+repr(str(self.p))+','+repr(I)+'); assert b.take(); '+tail
  x=subprocess.run([sys.executable,'-c',code],cwd=Path(__file__).parent)
  self.assertEqual(x.returncode,0);self.restart()
 def test_05_exit_after_commit_before_query(self):
  self.child('os._exit(0)');self.assertEqual(self.remaining(),1);self.pending()
 def test_06_exit_after_fixture_query(self):
  marker=Path(self.tmp.name)/'queried.txt'
  self.child('open('+repr(str(marker))+',"w").write("query-once"); os._exit(0)')
  self.assertEqual(marker.read_text(),'query-once');self.assertEqual(self.remaining(),1);self.pending()
 def test_07_identity_all_fields_bound(self):
  for n in range(4):
   wrong=list(I);wrong[n]+='-wrong';b=PersistentBudget(self.p,tuple(wrong))
   self.assertFalse(b.take());b.close()
  self.assertEqual(self.remaining(),2);self.pending()
 def test_08_no_budget_row_or_table_no_query(self):
  self.l.c.execute('DELETE FROM query_budget');self.assertIn('预算记录缺失',reconcile(self.l,self.a,self.q,self.b));self.assertEqual(self.q.calls,[])
  self.l.c.execute('DROP TABLE query_budget');self.restart();self.assertFalse(self.b.take());self.pending()
 def test_09_missing_corrupt_incompatible_db(self):
  missing=Path(self.tmp.name)/'missing.db';b=PersistentBudget(missing,I);self.assertFalse(b.take());b.close();self.assertFalse(missing.exists())
  broken=Path(self.tmp.name)/'broken.db';broken.write_bytes(b'bad');b=PersistentBudget(broken,I);self.assertFalse(b.take());b.close()
  self.l.c.execute('ALTER TABLE query_budget ADD COLUMN other TEXT');self.restart();self.assertFalse(self.b.take());self.pending()
 def test_10_sql_commit_failure_no_query(self):
  for kind in ('update','commit'):
   def auth(code,a,*rest):
    deny=(kind=='update' and code==sqlite3.SQLITE_UPDATE) or (kind=='commit' and code==sqlite3.SQLITE_TRANSACTION and a=='COMMIT')
    return sqlite3.SQLITE_DENY if deny else sqlite3.SQLITE_OK
   self.b.c.set_authorizer(auth)
   self.assertIn('预算SQL或提交失败',reconcile(self.l,self.a,self.q,self.b))
   self.b.c.set_authorizer(lambda *args:sqlite3.SQLITE_OK)
   self.assertEqual(self.remaining(),2);self.assertEqual(self.q.calls,[]);self.pending()
 def test_11_two_connections_share_budget_sequential(self):
  other=PersistentBudget(self.p,I)
  try:
   self.assertTrue(self.b.take());self.assertTrue(other.take());self.assertFalse(self.b.take());self.assertEqual(self.remaining(),0)
  finally:other.close()
 def test_12_no_reseed_and_no_terminal_query(self):
  self.assertTrue(self.b.take())
  with self.assertRaises(sqlite3.Error):seed_budget_fixture(self.l,I,999)
  self.assertEqual(self.remaining(),1)
  self.assertTrue(self.l.finish(I,trusted=True,terminal=True,released=True))
  self.assertFalse(self.b.take());self.assertEqual(self.remaining(),1)
  self.assertIn('无待确认',reconcile(self.l,self.a,self.q,self.b));self.assertEqual(self.q.calls,[])
if __name__=='__main__':
 print('EXECUTED_HOST Python='+sys.version.split()[0]+' SQLite='+sqlite3.sqlite_version,flush=True)
 unittest.main(verbosity=2)
