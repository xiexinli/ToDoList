"""只读查询Host夹具：零网络，trusted不是认证，绝不创建生成。"""
import sqlite3
from ledger_host import valid

class Budget:
    def __init__(self, remaining):
        if type(remaining) is not int or remaining < 0:
            raise ValueError('查询预算必须是非负整数')
        self.remaining = remaining

    def take(self):
        if self.remaining == 0:
            return False
        self.remaining -= 1  # 查询失败也消耗预算；绝不是生成重试预算。
        return True

class QueryStub:
    def __init__(self, replies):
        self.replies, self.calls = list(replies), []

    def query(self, identity):
        self.calls.append(identity)  # 仅记内存日志，没有HTTP或生成接口。
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply

class FixtureAdapter:
    def __init__(self, *, contract=False, scope=None, receipt=None):
        self.contract, self.scope, self.receipt = contract, scope, receipt

    def approved(self, identity):
        return self.contract is True and valid(self.scope) and self.scope == identity

    def verify(self, reply, identity):
        # 对象白名单仅模拟独立验证器；JSON里trusted=True不能自行成为证据。
        # 生产必须由已批准adapter验证来源/账号/后端代际/关联/终结与释放。
        return (reply is self.receipt and isinstance(reply, dict)
                and type(reply.get('http')) is int and reply['http'] == 200
                and valid(reply.get('identity')) and reply['identity'] == identity
                and all(reply.get(k) is True for k in ('trusted', 'terminal', 'released')))

def reconcile(ledger, adapter, stub, budget):
    if ledger.c is None:
        return '待确认：账本不可读'
    try:
        row = ledger.c.execute(
            'SELECT op_id,account,digest,backend FROM ops WHERE slot=1').fetchone()
    except sqlite3.Error:
        return '待确认：账本不可读'
    if row is None:
        return '无待确认操作（不创建新生成）'
    identity = tuple(row)  # 只从旧占位恢复完整身份，不接收替换ID。
    if not valid(identity) or not adapter.approved(identity):
        return 'NOT_EXECUTED：契约或查询scope未批准'
    if not budget.take():
        return '待确认：查询预算耗尽'
    try:
        reply = stub.query(identity)
        if not adapter.verify(reply, identity):
            return '待确认：状态或证据不充分'
        # 只有经adapter验证的同身份终结+释放才能交给昨日finish。
        ok = ledger.finish(identity, trusted=True, terminal=True, released=True)
        return '已对账：终结并释放' if ok else '待确认：账本提交未成功'
    except Exception:
        return '待确认：查询或验证失败'  # 404/超时/未知绝不删UNKNOWN或重发。

if __name__ == '__main__':
    from pathlib import Path
    from tempfile import TemporaryDirectory
    from ledger_host import Ledger, bootstrap_fixture
    with TemporaryDirectory() as d:
        p = Path(d) / 'fixture.db'; bootstrap_fixture(p)
        identity = ('op-1', 'account-A', 'sha256:fixture', 'backend-A:generation-1')
        ledger = Ledger(p); assert ledger.reserve(identity)  # 人工造占位，无生成。
        reply = dict(http=200, identity=identity, trusted=True, terminal=True, released=True)
        adapter = FixtureAdapter(contract=True, scope=identity, receipt=reply)
        stub, budget = QueryStub([{'http': 404}, reply]), Budget(2)
        print(reconcile(ledger, adapter, stub, budget))
        print(reconcile(ledger, adapter, stub, budget))
        print('查询次数:', len(stub.calls), '剩余预算:', budget.remaining)
        print('账本:', ledger.c.execute('SELECT state,slot FROM ops').fetchone())
        print('usage=NOT_EXECUTED（无模型调用）'); ledger.close()
