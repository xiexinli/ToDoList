import hashlib, threading
from dataclasses import dataclass, replace

def fp(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()

@dataclass(frozen=True)
class Request:
    rid: str
    text: str
    purpose: str = '摘要'
    route: str = 'MANUAL'  # 默认人工编辑；非自动路由
    target: str = 'device:local'
    sensitivity: str = 'UNKNOWN'

@dataclass(frozen=True)
class Grant:
    rid: str
    fingerprint: str
    purpose: str
    target: str
    expires: int  # fixture逻辑时钟；生产需统一可信时间域

class Router:
    def __init__(self):
        self.lock, self.seen = threading.Lock(), {}
    def run(self, r, grant, clock, backend):
        with self.lock:  # 校验与占位原子化；占位后不换后端
            if r.rid in self.seen: return 'DUPLICATE'
            if r.route == 'MANUAL': return 'EDIT'
            targets = {'LOCAL': 'device:local', 'CLOUD': 'cloud:approved-A'}
            if not r.rid or targets.get(r.route) != r.target: return 'DENY'
            if r.route == 'CLOUD':
                if r.sensitivity != 'PUBLIC' or grant is None: return 'DENY'
                if ((grant.rid, grant.fingerprint, grant.purpose, grant.target)
                        != (r.rid, fp(r.text), r.purpose, r.target)
                        or clock() >= grant.expires): return 'DENY'
            self.seen[r.rid] = 'RUNNING'
        try:
            result = backend(r)  # 固定fixture；无网络/SDK
        except Exception:
            result = 'UNKNOWN'  # 不确定结束，保留占位，不自动上云
        with self.lock: self.seen[r.rid] = result
        return result

router = Router(); calls = []
r = Request('r1', '公开商品描述', route='CLOUD',
            target='cloud:approved-A', sensitivity='PUBLIC')
g = Grant(r.rid, fp(r.text), r.purpose, r.target, 100)
def backend(q):
    calls.append(q.route)
    assert router.run(q, g, lambda: 1, backend) == 'DUPLICATE'
    return 'FAILED'  # 后端明确失败；不切换路由
assert router.run(replace(r, route='MANUAL'), None, lambda: 1, backend) == 'EDIT'
for q,h,now in [(replace(r, text='新文本'),g,1), (r,g,100), (r,None,1),
               (replace(r, sensitivity='SENSITIVE'),g,1),
               (replace(r, sensitivity='UNKNOWN'),g,1),
               (r,replace(g, rid='其他'),1), (r,replace(g,purpose='翻译'),1),
               (r,replace(g,target='cloud:other'),1)]:
    assert router.run(q,h,lambda: now,backend) == 'DENY'
assert router.run(r,g,lambda: 99,backend) == 'FAILED'
assert router.run(r,g,lambda: 1,backend) == 'DUPLICATE'
assert calls == ['CLOUD']
print('EXECUTED_HOST: 13 assertions passed; backend_calls=1; route=CLOUD')
print('同进程fixture；无云请求，无设备测试，无跨进程exactly-once证据')
