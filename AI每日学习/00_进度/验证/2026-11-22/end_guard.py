# -*- coding: utf-8 -*-
"""Host固定事件：不发取消/不查询SDK；回执必须由可信适配层验证。"""
from dataclasses import dataclass
from threading import Lock

@dataclass(frozen=True)
class Receipt:
    rid: str
    backend: str
    source: str
    outcome: str
    ended: bool = False
    released: bool = False
    verified: bool = False

class EndGuard:
    def __init__(self):
        self.lock = Lock()
        self.active = None  # 资源域占位，不只是同一个ID去重
        self.used = set()
        self.state = 'IDLE'
        self.discard = False
        self.draft = ''

    def start(self, rid, backend, approved=False):
        with self.lock:
            if approved is not True or not isinstance(rid, str) or not rid:
                return 'DENY'
            if backend not in ('LOCAL', 'CLOUD'): return 'DENY'
            if rid in self.used: return 'DUPLICATE'
            if self.active is not None: return 'BLOCKED_IN_FLIGHT'
            self.active = (rid, backend)
            self.used.add(rid)
            self.state, self.discard, self.draft = 'RUNNING', False, ''
            return 'STARTED'

    def fragment(self, rid, text):
        with self.lock:
            if (self.active is None or self.active[0] != rid
                    or self.state != 'RUNNING' or not isinstance(text, str)):
                return 'DROP'
            self.draft += text
            return 'PREVIEW'

    def interrupt(self, rid, kind):
        with self.lock:
            if self.active is None or self.active[0] != rid: return 'IGNORE'
            if kind not in ('CANCEL', 'TIMEOUT', 'LOST'): return 'DENY'
            self.discard, self.draft = True, ''
            # 已未知不能因再次点击取消而倒退成“快结束了”。
            if self.state != 'UNKNOWN':
                self.state = 'CANCEL_REQUESTED' if kind == 'CANCEL' else 'UNKNOWN'
            return self.state  # 不释放占位，也不自动换后端

    def confirm(self, receipt):
        with self.lock:
            expected = {'LOCAL': 'LOCAL_ADAPTER', 'CLOUD': 'REMOTE_STATUS'}
            if (self.active != (receipt.rid, receipt.backend)
                    or receipt.source != expected.get(receipt.backend)
                    or any(v is not True for v in
                           (receipt.verified, receipt.ended, receipt.released))
                    or receipt.outcome not in ('SUCCESS', 'FAILED', 'CANCELLED')):
                return 'REJECT_RECEIPT'
            # 回执表明任务终结，不表示结果可展示；已取消的迟到成功不能复活。
            self.state = 'ENDED_SUPPRESSED' if self.discard else 'ENDED_' + receipt.outcome
            if self.discard or receipt.outcome != 'SUCCESS': self.draft = ''
            self.active = None
            return self.state

if __name__ == '__main__':
    g = EndGuard()
    print(g.start('a', 'LOCAL', approved=True))
    print(g.interrupt('a', 'TIMEOUT'))
    print(g.start('b', 'CLOUD', approved=True))
    print(g.confirm(Receipt('a', 'LOCAL', 'LOCAL_ADAPTER', 'SUCCESS', True, True, True)))
    print(g.start('b', 'LOCAL', approved=True))
    print('Host固定事件；真实后端调用=0，SDK取消/资源释放/usage均未测')
