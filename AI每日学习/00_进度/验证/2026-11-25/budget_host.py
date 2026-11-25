"""Host教学：不联网；预算提交成功才允许查询，没有恢复补额入口。"""
import sqlite3
from ledger_host import Ledger, valid
BSCHEMA = """CREATE TABLE query_budget (
 op_id TEXT PRIMARY KEY NOT NULL, account TEXT NOT NULL,
 digest TEXT NOT NULL, backend TEXT NOT NULL,
 remaining INTEGER NOT NULL CHECK(typeof(remaining)='integer' AND remaining>=0))"""

def seed_budget_fixture(ledger, identity, limit):
    # 仅全新隔离fixture人工批准的一次初始化，绝非恢复/补额/线上迁移。
    if not valid(identity) or type(limit) is not int or limit < 0:
        raise ValueError('无效fixture预算')
    c = ledger.c
    try:
        c.execute('BEGIN IMMEDIATE')
        row = c.execute('SELECT op_id,account,digest,backend FROM ops WHERE slot=1').fetchone()
        if row != identity:
            raise ValueError('不属于原占位')
        c.execute(BSCHEMA)  # 已有表就失败，不使用IF NOT EXISTS/REPLACE。
        c.execute('INSERT INTO query_budget VALUES (?,?,?,?,?)', (*identity, limit))
        c.execute('COMMIT')
    except Exception:
        if c.in_transaction:
            c.execute('ROLLBACK')
        raise

class PersistentBudget:
    def __init__(self, path, identity):
        self.identity = identity
        self.reason = "预算不可用"
        self.ledger = Ledger(path)  # mode=rw、quick_check；缺库不创建。
        self.c = self.ledger.c
        try:
            if not valid(identity) or self.c is None:
                raise ValueError('不可恢复')
            if self.c.execute("SELECT sql FROM sqlite_master WHERE name='query_budget'").fetchone() != (BSCHEMA,):
                raise ValueError('预算结构缺失/不兼容')
        except (ValueError, sqlite3.Error):
            self.close()

    def close(self):
        self.ledger.close()
        self.c = None

    def take(self):
        if self.c is None:
            return False
        try:
            self.c.execute('BEGIN IMMEDIATE')
            active = self.c.execute('SELECT op_id,account,digest,backend FROM ops WHERE slot=1').fetchone()
            if active != self.identity:
                self.c.execute('ROLLBACK')
                self.reason = '身份或操作状态不匹配'
                return False
            changed = self.c.execute(
                'UPDATE query_budget SET remaining=remaining-1 WHERE '
                'op_id=? AND account=? AND digest=? AND backend=? AND remaining>0',
                self.identity).rowcount
            row = self.c.execute('SELECT remaining FROM query_budget WHERE op_id=?', (self.identity[0],)).fetchone()
            self.reason = '预算记录缺失' if row is None else ('预算耗尽' if changed == 0 else '已扣减')
            self.c.execute('COMMIT')  # 成功返回后reconcile才查询；异常不查询。
            return changed == 1
        except sqlite3.Error:
            self.reason = '预算SQL或提交失败'
            try:
                self.c.execute('ROLLBACK')
            except sqlite3.Error:
                self.close()
            return False

def reconcile_persistent(ledger, adapter, stub, budget):
    from query_host import reconcile
    out = reconcile(ledger, adapter, stub, budget)
    if out == '待确认：查询预算耗尽' and budget.reason != '预算耗尽':
        return '待确认：' + budget.reason
    return out

if __name__ == '__main__':
    from pathlib import Path
    from tempfile import TemporaryDirectory
    from ledger_host import bootstrap_fixture
    from query_host import reconcile, QueryStub, FixtureAdapter
    with TemporaryDirectory() as d:
        p = Path(d)/'ops.db'; bootstrap_fixture(p)
        i = ('op-1','account-A','sha256:fixture','backend-A:generation-1')
        l = Ledger(p); assert l.reserve(i); seed_budget_fixture(l, i, 2)
        b = PersistentBudget(p, i); a = FixtureAdapter(contract=True,scope=i)
        q = QueryStub([{'http':404}, TimeoutError('fixture')])
        print('首次查询:', reconcile_persistent(l,a,q,b)); b.close(); l.close()
        l = Ledger(p); b = PersistentBudget(p,i)
        print('重启仅恢复，未查询；剩余:', l.c.execute('SELECT remaining FROM query_budget').fetchone()[0])
        print('用户显式查询:', reconcile_persistent(l,a,q,b))
        print('再次请求:', reconcile_persistent(l,a,q,b))
        print('fixture查询次数:',len(q.calls),'账本:',l.c.execute('SELECT state,slot FROM ops').fetchone())
        b.close(); l.close(); print('usage=NOT_EXECUTED（无模型调用）')
