import math
from dataclasses import dataclass, replace

@dataclass(frozen=True)
class Failure:
    code: int = 9
    foreground: bool = True
    finished: bool = True
    released: bool = True
    partial: bool = False
    allowed: bool = True
    retry_ms: float = 1234.1
    attempts: int = 1  # 已开始次数，包括首次
    elapsed_ms: int = 100  # 首次受理以来的等待与操作

# 应用建议值，不是SDK默认；预算单位统一为毫秒
MAX_ATTEMPTS, TOTAL_MS, OP_CAP_MS = 2, 2500, 900

def decide(f):
    if f.code != 9:
        return 'STOP', 0  # policy、取消、未知均拒绝
    if not all(x is True for x in
               (f.foreground, f.finished, f.released, f.allowed)):
        return 'STOP', 0
    if f.partial is not False:
        return 'STOP', 0
    d = f.retry_ms
    if (type(d) not in (int, float) or not math.isfinite(d) or d <= 0):
        return 'STOP', 0
    wait_ms = math.ceil(d)  # 不可向下取整压短服务建议
    if (type(f.attempts) is not int or not 1 <= f.attempts < MAX_ATTEMPTS
            or type(f.elapsed_ms) is not int or f.elapsed_ms < 0
            or f.elapsed_ms + wait_ms + OP_CAP_MS > TOTAL_MS):
        return 'STOP', 0
    return 'RETRY', wait_ms

base = Failure()
assert decide(base) == ('RETRY', 1235)
fixtures = [dict(code=c) for c in (4, 11, 15, 7, 999)]
fixtures += [dict(foreground=False), dict(finished=False),
             dict(released=False), dict(partial=True), dict(allowed=False),
             dict(retry_ms=0), dict(retry_ms=-1), dict(retry_ms=float('nan')),
             dict(attempts=2), dict(elapsed_ms=500)]
for change in fixtures:
    assert decide(replace(base, **change)) == ('STOP', 0), change
print('EXECUTED_HOST: 16 assertions passed; retry_wait_ms=1235')
print('固定fixture；SDK/设备/模型/性能/usage均未测量')
