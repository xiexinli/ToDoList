# -*- coding: utf-8 -*-
# 每次运行创建新的 fixture 子目录，所有子进程与文件证据保留，不覆盖旧记录。
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent
RUN = ROOT / ('fixture-' + str(time.time_ns()))
RUN.mkdir()
SCRIPT = ROOT / 'checkpoint_demo.py'
records = []

def launch(case, *flags, expected=0):
    state = RUN / case
    cmd = [sys.executable, str(SCRIPT), '--state', str(state)] + list(flags)
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
    record = {'case': case, 'args': list(flags), 'exit': p.returncode,
              'stdout': p.stdout, 'stderr': p.stderr}
    records.append(record)
    print(json.dumps(record, ensure_ascii=False), flush=True)
    assert p.returncode == expected, record
    assert not p.stderr, record
    return p.stdout

def ck(case):
    return json.loads((RUN / case / 'checkpoint.json').read_text())

def effect(case):
    p = RUN / case / 'effects.jsonl'
    return p.read_bytes() if p.exists() else b''

def snapshot(case):
    return ((RUN / case / 'checkpoint.json').read_bytes(), effect(case))

# 1 正常完成：三步结果全部已提交，副作用一条。
launch('normal')
assert ck('normal')['status'] == 'complete'
assert all(s['status'] == 'done' for s in ck('normal')['steps'])
assert ck('normal')['steps'][1]['result']['count'] == 2
assert len(effect('normal').splitlines()) == 1

# 2 提交 normalize 后退出；另一 Python 进程跳过 normalize 再完成。
launch('resume', '--crash-after', 'normalize', expected=75)
assert [s['status'] for s in ck('resume')['steps']] == ['done','pending','pending']
out = launch('resume')
assert '跳过已提交步骤 normalize' in out
assert '执行步骤 normalize' not in out
assert len(effect('resume').splitlines()) == 1

# 3 重复启动：全跳过，检查点和副作用字节都不变。
before = snapshot('resume')
out = launch('resume')
assert out.count('跳过已提交步骤') == 3
assert '执行步骤' not in out and snapshot('resume') == before

# 4 输入或流程版本不同：拒绝且不改现场。
launch('resume', '--text', 'Changed input', expected=2)
assert snapshot('resume') == before
launch('resume', '--workflow-version', '2', expected=2)
assert snapshot('resume') == before

# 5 副作用与完成 checkpoint 之间退出；恢复不擅自重复写。
launch('gap', '--crash-gap', expected=76)
assert ck('gap')['steps'][2]['status'] == 'running'
assert len(effect('gap').splitlines()) == 1
launch('gap', expected=3)
assert ck('gap')['status'] == 'needs_control'
gap_before = snapshot('gap')
launch('gap', expected=3)
assert snapshot('gap') == gap_before

# 6 模拟拒绝/超时：持久化阻塞，即使下一进程传 approved 也不自动继续。
for case in ('denied', 'timeout'):
    launch(case, '--approval', case, expected=3)
    assert not effect(case)
    old = snapshot(case)
    launch(case, '--approval', 'approved', expected=3)
    assert snapshot(case) == old

# 7 检查点格式版本损坏：拒绝且不执行。
launch('schema')
schema_path = RUN / 'schema' / 'checkpoint.json'
c = ck('schema'); c['schema'] = 999
schema_path.write_text(json.dumps(c, ensure_ascii=False))
old = snapshot('schema')
launch('schema', expected=2)
assert snapshot('schema') == old

# 新进程验证：成功加载状态的各子进程 PID 不同。
pids = [r['stdout'].split('pid=')[1].splitlines()[0] for r in records
        if 'pid=' in r['stdout']]
assert len(pids) == len(set(pids))
report = {'result': 'PASS', 'groups': 7, 'subprocesses': len(records),
          'python': sys.version, 'runner_pid': os.getpid(),
          'fixture_path': str(RUN), 'records': records}
(RUN / 'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
(ROOT / 'latest-run.txt').write_text(str(RUN)+'\n')
print('PASS：7 组断言；子进程=' + str(len(records)) + '；证据=' + str(RUN))
