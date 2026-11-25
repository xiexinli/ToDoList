# 2026-11-15（周日）· 可恢复工作流：检查点（Checkpoint）与断点续跑

> 轨道 1 · 地基工程化补充｜W4 已于 11-14 收官；不提前进入 Android 阶段。今天日材料与 W46 周总结同时产出。
> 选题依据：实读 11-12 的上下文记忆、11-13 的规划器/执行器、11-14 的可观测与护栏正文，均未实现流程状态持久化与新进程恢复。本讲只解决「进程退出后，从哪里继续」，不重讲 Memory、一般重试或 HITL。

## 0 速览（30 秒读完）
- 今日主题：把**已完成步骤及结果**存成检查点，让新进程只做剩余工作。
- 学完你能做到：给一个三步离线工作流加持久状态，验证中断后续跑、重复启动跳过，以及不安全时拒绝恢复。
- 预计时长：**120 分钟**（速览 0.5 / 概念 30 / 代码 40 / 动手 20 / 动态 20 / 收尾 9.5）。

## 1 概念精讲（30 min）

### 一句话定义
**Checkpoint 是流程的可恢复快照**：记录任务身份、流程版本、输入指纹、各步骤状态与输出，使另一个进程能验证现场并定位续跑起点。

### 它解决什么问题 / 为什么现在必须懂
Agent 或 RAG 批处理已经做完「解析 → 统计」，进程被关闭后，内存里的 `messages`、`plan` 或日志都不足以告诉执行器「哪些输出可以直接复用」。从头运行既浪费计算，又可能重复提交订单或消息。

把这个问题类比为 Android 的后台任务：ViewModel 活着时保存了进度，不代表系统杀进程后还能继续。**任务状态必须离开进程内存，而且保存成功才算提交。**

今天学习的是「恢复协议」，不是新一轮模型推理策略：不调模型、不计算 usage，全部输入均为演示 fixture。

### 关键机制
```text
启动新进程
   ↓
互斥锁 → 读取 checkpoint
   ↓
检查格式版本 + 流程版本 + 输入 SHA-256
   ├─ 不一致 → 拒绝恢复，保留现场
   └─ 一致
        ↓
逐步检查
  done + 已保存结果 → 直接复用，不执行
  pending           → 写 running → 执行 → 写 done + result
  running 的纯计算  → 允许重新计算
  running 的副作用  → 结果未知 → 停止，交还控制权
        ↓
全部步骤 done → 流程 complete
```

今天的状态包含：
| 字段 | 为什么需要 |
|---|---|
| `schema` | 检查点文件结构版本，不能按旧格式误读 |
| `workflow_version` | 步骤逻辑变更后不能复用旧结果 |
| `input_hash` | 同一目录不能悄悄切换输入；本例绑定原始 UTF-8 输入 |
| `steps[].name/status/result` | 知道成功到哪一步，并恢复后继所需的真实结果 |
| `status/reason` | 区分运行中、完成、需交还控制权；不能把所有失败当暂态异常 |

**保存检查点**用「同目录临时文件 → flush/fsync → replace → 目录 fsync」。这避免读取半份 JSON，降低进程中断造成的状态丢失风险；不是所有文件系统/突然断电情形下的绝对保证。示例用进程锁限制单写入者，不实现分布式抢占。

**最重要的边界：副作用与检查点不是一个事务。**
```text
A. 写 running
B. 模拟发送成功：effects.jsonl 追加一条事件
   ← 在这里进程退出！
C. 写 done + result
```
下个进程只看到 `running`，不知道 B 是否成功。**「没有 done」不等于「没执行」**。本例选择停止并保留现场，不自动重复 B，也不声称 exactly-once。

真实远程写必须依靠服务端的幂等契约、稳定操作标识、结果查询或人工对账等具体能力；没有这些能力时只能承认结果不确定。同库事务也只能覆盖该事务内的操作。**幂等键、先查后写、checkpoint 都不是解决所有远程写的万能药**。

### 常见误区（3 条）
1. 很多人以为「有 trace 就能恢复」；其实日志解释发生过什么，检查点还要保存可复用结果与可信状态，二者不能互相替代。
2. 很多人以为「只存下一个步骤编号就够了」；其实输入或逻辑已变、上步结果丢失时，编号相同也不能继续。
3. 很多人以为「有检查点就永远不重复」；其实只有**已提交 done 的步骤**可直接跳过，副作用提交空隙仍需单独核对。

**📝 我的复述（这段留空给用户自己写，不要代写）：**


## 2 代码片段（40 min）
- 场景：演示「规范化输入 → 词数统计 → 发布一条结果事件」的三步 fixture，模拟 RAG 摄取/评估批任务中断恢复。所谓发布仅写本地 `effects.jsonl`，**不是对用户真实系统发消息、下单或写业务数据**。
- 依赖与版本：本机实跑 **CPython 3.9.6 / macOS arm64**；只使用随 Python 3.9.6 提供的 `argparse`、`fcntl`、`hashlib`、`json`、`os`、`pathlib`。无第三方包、无模型、无令牌、无需 pip。`fcntl` 适用于 macOS/Linux，此代码未验证 Windows。
- 阅读安排：10 分钟看 `load/save`，15 分钟看步骤状态转移，15 分钟按下面命令运行并看断言。
- 最小可运行代码：另存为 `checkpoint_demo.py` 即可，完整实现如下；本次已在本地证据目录保留同一份源码。

```python
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
```

### 运行方法
在任意你自己建立的演示目录里保存上述代码，执行以下命令；`--state` 必须指向**专用 fixture 子目录**，不要填真实项目/业务存储目录。
```bash
# 首次运行：创建一个未用过的 fixture 目录。若已跑过，换新目录名，勿删旧现场。
python3 checkpoint_demo.py --state ./fixture-resume-1 --crash-after normalize
# 退出码 75 是我们主动注入的演示中断；停止后由你显式发起下一进程。
python3 checkpoint_demo.py --state ./fixture-resume-1
# 再启动一次：三步都跳过，不再追加事件。
python3 checkpoint_demo.py --state ./fixture-resume-1
# 以下命令退出码 2：输入/流程版本变化，禁止复用旧检查点。
python3 checkpoint_demo.py --state ./fixture-resume-1 --text "Different input"
python3 checkpoint_demo.py --state ./fixture-resume-1 --workflow-version 2
# 副作用已发生但未提交 done：下一进程停止，不自动重复发布。
python3 checkpoint_demo.py --state ./fixture-gap-1 --crash-gap
python3 checkpoint_demo.py --state ./fixture-gap-1
```

这些都是**用户主动启动的离线 fixture 命令**，不是自动重试审批。审批 `denied/timeout` 会写入 `needs_control`，后续即使传 `approved` 仍停止；示例故意不提供自动解锁。真实新授权必须独立设计并确认，本讲不实现。

### 本轮真实执行与断言结果（2026-11-15）
自检脚本使用 `subprocess.run` 启动彼此独立的 Python 进程；每次执行建立新 fixture 目录，不删除旧现场。完整断言和输出已保留。
| 验证组 | 实际结果 |
|---|---|
| 正常运行 | 三步均 `done`；状态 `complete`；输入 `Android AI` 词数 2；副作用 1 条 |
| normalize 提交后中断 → 新进程恢复 | 第一个进程退出 75；后进程跳过 normalize，只运行 stats/publish |
| 完成后重复启动 | 三步全跳过；checkpoint 与副作用文件字节均不变 |
| 输入变化 / 流程版本变化 | 各退出 2；现场字节不变 |
| 副作用与 done 之间中断 | 退出 76；恢复退出 3 并持久化 `needs_control`；重复启动仍停止，副作用保持 1 条 |
| 审批拒绝 / 超时 fixture | 均退出 3；副作用 0 条；后续 approved 不自动继续 |
| 格式版本被改为 999 | 退出 2；不执行、不改现场 |

**本轮共 7 组断言、15 个子进程，全部 PASS。**这证明本 fixture 的恢复协议，不证明真实远程系统具有同样语义，也不代表你已经完成练习。

证据定位（相对于 `AI每日学习` 根目录）：
- 源码：`00_进度/验证/2026-11-15/checkpoint_demo.py`
- assert 自检：`00_进度/验证/2026-11-15/test_checkpoint.py`（同目录保留，无其他外部文件依赖）
- 全量实跑输出：`00_进度/验证/2026-11-15/tests.log`
- 本轮报告与全部 checkpoint/副作用现场：`00_进度/验证/2026-11-15/fixture-1794701022622624000/report.json`
- 可复测：`python3 "/Users/alion/DemoProjects/ToDoList/AI每日学习/00_进度/验证/2026-11-15/test_checkpoint.py"`；它会另建新现场，保留旧证据。

### 逐行要点
- `input_hash` 绑定原始输入；**工作流语义变更要同步修改版本标识**，本例用 CLI 修订号演示版本不匹配。
- `save` 在一个提交点保存步骤结果；后继从 `results` 获得输出，而不是重新做成功步骤。
- `done` 分支是续跑的核心：加载结果、直接跳过。
- `running + publish` 不能猜测成功与否；持久化阻塞后交还控制权。
- `crash_after` 和 `crash_gap` 分别演示提交后的安全续跑与提交空隙的不确定性；它们不是生产重试策略。

### 踩坑提示
1. `--crash-after` 退出时没有清理临时资源的 Python `finally`；因此通过真正的子进程验证，而不是在同进程里 catch 一个异常冒充重启。
2. 同一输入的空白变化也会改变 hash，这是本例的保守设计；如要规范化后绑定身份，应明确规范与版本。
3. hash 不是签名，不阻止被篡改的状态；不要给不可信方修改检查点。本例文件明文保存结果，真实任务要考虑敏感信息最小化。
4. 锁和原子替换只作用于这个本地目录；未实测网络文件系统、硬断电或远程服务。普通 I/O 错误也不会自动循环重试。

## 3 动手 / 联想（20 min）
- **一个动手任务：把统计项扩成「词数 + 唯一词数」，做一次版本拒绝实验。**
  1. 5 分钟：给 stats 结果增加 `unique_count`，用 `Android AI Android` 做演示输入。
  2. 5 分钟：先对旧逻辑跑一个新 fixture，保存旧检查点；再将流程版本改为 `2`，对旧 fixture 启动，确认拒绝恢复。
  3. 5 分钟：对另一新 fixture 使用版本 `2`，在 normalize 后受控中断并显式续跑；不要删改旧现场。
  4. 5 分钟：记录你实际得到的词数、唯一词数，以及跳过了哪个步骤。**你的实测数值待填，不用教练的输出代替。**
- 验收：新逻辑结果符合输入、旧版本拒绝、提交后续跑跳过 normalize、重复启动不新增发布事件。
- **与我的工作结合**：Android 批量 OCR/本地文档索引被系统杀进程后，可以把输入身份、模型/流程版本和已完成文件结果存到本地持久存储；Web/小程序后台多步上传任务可以让后端保存状态，刷新页面只查询并展示进度。**UI 不要把「恢复中」或「结果待核对」显示成「完成」**。这只是迁移设计，今天没有接入 OCR、Room 或真实上传 API。

## 4 动态与机会（20 min）
> 以下均为 **11-15 首次纳入笔记的已核验资料**，不声称今天新发布。已做 canonical 去重（统一 http/https、去末尾斜杠、排序查询参数）；3 条均未出现在原台账。来源实读与响应归档见 `00_进度/验证/2026-11-15/sources.json`。

- 🔥 **新动向（1 条）**：**Google AI Edge Gallery 新增端侧语音识别与语音合成**（原文发布日期 **2026-11-10**；官方正文及 RSS 均实读）— 官方介绍本地 ASR/TTS、流式输入与句子级播报，并区分 Android 的 ML Kit 路径和跨平台 MediaPipe Tasks/LiteRT 路径。**影响判断**：端侧 AI 产品已不止文本聊天，你的 Android/Flutter 背景能用于离线语音交互；但设备支持范围、具体 SDK 版本须接入前另查，不把文章演示当全设备保证。**今天只读架构图，不提前开新课或接 SDK。** — [Google Developers Blog](https://developers.googleblog.com/on-device-speech-recognition-and-text-to-speech-in-google-ai-edge-gallery/)
- 💼 **岗位观察（1 条）**：**腾讯 · 微信 WeLM 大模型研发基础设施工程师（研发效能方向）**（官方 API 更新时间 **2026-11-02**，不是今日新增岗位）— JD 要求分布式系统或 ML Systems 经验，熟悉任务调度、工作流、容器/沙箱、Kubernetes、存储/消息系统或可观测性；职责包含故障恢复，并强调区分「系统成功运行」与「可信模型结论」。**我该补什么**：先把今天的恢复状态机、测试现场和版本拒绝整理成作品集证据，再补后端存储与调度；这不是凭今天一讲就满足的岗位要求。**数据注意**：标题写深圳/上海/广州，`LocationName` 写北京，城市信息不一致，投递前待核实。 — [腾讯招聘](https://careers.tencent.com/jobdesc.html?postId=2084637516971032576)
- 🧰 **其他有价值信息（1 条）**：**langchain-ai/langgraph**（既有开源项目；GitHub API 显示创建于 **2023-08-09**，最近推送 **2026-11-14 01:43:55 UTC**，不是新版本发布日期；API 与 README 已实读）— README 定位为有状态 Agent 的低层编排基础设施，并列出 Durable execution。**为什么值得看**：先用今天的零依赖实现理解「哪些状态可恢复、哪些副作用不可猜」，再对照其持久执行能力，而不是先装框架跳过恢复边界。**未安装、未实跑 LangGraph，不作版本或性能结论。** — [GitHub](https://github.com/langchain-ai/langgraph)

阅读分配：官方语音架构 8 分钟 / JD 能力差距 5 分钟 / README 的 Durable execution 7 分钟。只读，不开展另一个实现主题。

## 5 明日预告与待复习（9.5 min）
- **明日主题**：按台账从 **2026-11-16** 进入 `02_AndroidAI`，建议首讲聚焦**端侧推理的设备能力检查与可用性边界**；具体 API/SDK 待明日按官方资料核验，不提前修改阶段计划。
- **待复习（3 条）**：
  1. 检查点要含输入身份、版本、步骤状态及可复用结果；编号或日志都不够。
  2. 已提交 `done` 的步骤可跳过；副作用还在 `running` 时，必须承认结果未知。
  3. 版本/输入不匹配拒绝恢复；人工拒绝/审批超时停止并交还控制权，不自动重申审批。
- **一句话复盘**：最容易忘的是——「没保存成功」和「没执行成功」不是一回事。
- 收尾安排：5 分钟自己填写复述，3 分钟检查自己的练习记录，1.5 分钟对照 W46 周总结勾选真实完成情况。
