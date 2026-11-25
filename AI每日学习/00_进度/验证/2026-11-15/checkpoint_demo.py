# -*- coding: utf-8 -*-
# Python 3.9 标准库；仅处理演示输入和指定 fixture 目录，不调用真实服务。
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path

SCHEMA = 1
STEPS = ('normalize', 'stats', 'publish')

class NeedControl(Exception):
    pass

def emit(text):
    print(text, flush=True)

def save(path, data):
    # 同目录替换防止半份 JSON；fsync 降低进程中断时丢状态的风险。
    tmp = path.with_suffix('.new')
    with tmp.open('w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)
    fd = os.open(str(path.parent), os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)

def load(path, text, version):
    digest = hashlib.sha256(text.encode('utf-8')).hexdigest()
    if not path.exists():
        return {'schema': SCHEMA, 'workflow_version': version,
                'input_hash': digest, 'status': 'active',
                'steps': [{'name': n, 'status': 'pending'} for n in STEPS]}
    c = json.loads(path.read_text(encoding='utf-8'))
    if (c.get('schema') != SCHEMA or c.get('workflow_version') != version
            or c.get('input_hash') != digest):
        raise ValueError('检查点格式/流程版本/输入不匹配，拒绝恢复')
    rows = c.get('steps', [])
    if ([s.get('name') for s in rows] != list(STEPS)
            or c.get('status') not in ('active', 'complete', 'needs_control')):
        raise ValueError('检查点结构不合法')
    unfinished = False
    for s in rows:
        state = s.get('status')
        if state not in ('pending', 'running', 'done'):
            raise ValueError('步骤状态不合法')
        if state == 'done':
            if unfinished or 'result' not in s:
                raise ValueError('已完成步骤必须是连续前缀且带结果')
        else:
            if unfinished and state != 'pending':
                raise ValueError('串行流程不能同时有多个运行步骤')
            unfinished = True
    if c['status'] == 'complete' and unfinished:
        raise ValueError('完成声明与步骤状态矛盾')
    return c

def stop(c, path, reason):
    c['status'] = 'needs_control'
    c['reason'] = reason
    save(path, c)
    raise NeedControl(reason)

def run(a):
    base = Path(a.state)
    base.mkdir(parents=True, exist_ok=True)
    # macOS/Linux 的进程级互斥；进程退出自动释放，不用删除锁文件。
    with (base / 'writer.lock').open('a') as lock:
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise NeedControl('另一个进程正在执行，同目录禁止并发')
        path = base / 'checkpoint.json'
        c = load(path, a.text, a.workflow_version)
        emit('启动进程 pid=' + str(os.getpid()))
        if c['status'] == 'needs_control':
            raise NeedControl(c['reason'] + '；保留现场，禁止自动重申审批')
        results = {}
        for s in c['steps']:
            name = s['name']
            if s['status'] == 'done':
                results[name] = s['result']
                emit('跳过已提交步骤 ' + name)
                continue
            # publish 有副作用：上次运行中断时结果未知，不能直接重放。
            if s['status'] == 'running' and name == 'publish':
                stop(c, path, 'publish 结果不确定，先人工核对副作用')
            # 这里只是审批 fixture，不申请真实权限；拒绝/超时永久停在现场。
            if name == 'publish' and a.approval != 'approved':
                stop(c, path, '审批 fixture=' + a.approval + '，交还控制权')
            s['status'] = 'running'
            save(path, c)
            emit('执行步骤 ' + name)
            if name == 'normalize':
                result = ' '.join(a.text.lower().split())
            elif name == 'stats':
                result = {'words': results['normalize'].split()}
                result['count'] = len(result['words'])
            else:
                # 模拟远程写：故意让副作用与 checkpoint 位于两个文件。
                event = {'fixture': True, 'word_count': results['stats']['count'],
                         'input_hash': c['input_hash']}
                with (base / 'effects.jsonl').open('a', encoding='utf-8') as f:
                    f.write(json.dumps(event, ensure_ascii=False) + '\n')
                    f.flush()
                    os.fsync(f.fileno())
                if a.crash_gap:
                    emit('受控中断：副作用已写，完成检查点尚未提交')
                    os._exit(76)
                result = event
            s.update(status='done', result=result)
            save(path, c)  # 先持久化结果，下一进程才能安全跳过这个步骤。
            results[name] = result
            if a.crash_after == name:
                emit('受控中断：已提交 ' + name)
                os._exit(75)
        if c['status'] != 'complete':
            c['status'] = 'complete'
            save(path, c)
        emit('流程完成；词数=' + str(results['stats']['count']))

if __name__ == '__main__':
    p = argparse.ArgumentParser(description='离线检查点 fixture（非真实业务）')
    p.add_argument('--state', required=True, help='专用演示目录；勿填真实业务目录')
    p.add_argument('--text', default='Android AI')
    p.add_argument('--workflow-version', default='1', help='流程修订标识')
    p.add_argument('--crash-after', choices=STEPS)
    p.add_argument('--crash-gap', action='store_true')
    p.add_argument('--approval', choices=('approved', 'denied', 'timeout'),
                   default='approved', help='纯模拟审批状态，不申请真实权限')
    a = p.parse_args()
    try:
        run(a)
    except NeedControl as e:
        emit('停止：' + str(e))
        raise SystemExit(3)
    except (ValueError, KeyError, TypeError, AttributeError) as e:
        emit('拒绝恢复：' + str(e))
        raise SystemExit(2)
