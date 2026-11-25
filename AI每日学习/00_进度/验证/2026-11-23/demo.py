from pathlib import Path
from tempfile import TemporaryDirectory
from ledger_host import Ledger, bootstrap_fixture
with TemporaryDirectory() as d:
    p = Path(d) / 'ops.db'; bootstrap_fixture(p)
    i = ('op-1', 'account-A', 'sha256:fixture-content', 'backend-A:generation-1')
    new = ('op-2', *i[1:]); l = Ledger(p)
    print('首次:', l.submit(i, lambda _: print('fixture dispatch（没有网络）')))
    l.close(); l = Ledger(p)
    print('重启换ID:', l.submit(new, lambda _: print('不应出现')))
    print('确认:', l.finish(i, trusted=True, terminal=True, released=True))
    print('旧ID:', l.submit(i, lambda _: print('不应出现')))
    print('显式新任务:', l.submit(new, lambda _: print('fixture new dispatch')))
    l.close()
