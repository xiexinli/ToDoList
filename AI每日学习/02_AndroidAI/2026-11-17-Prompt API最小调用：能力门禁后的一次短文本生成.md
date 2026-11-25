# 2026-11-17（周二）· Prompt API 最小调用：能力门禁后的一次短文本生成

## 0 速览（30 秒读完）
- **今日主题**：续用昨日能力门禁，在有效客户端生命周期内完成**一次非流式短文本生成**。
- **学完你能做到**：把请求、生成中、有效结果、空结果、失败、取消和超时映射为明确的 UI 状态；不把“可尝试”冒充“已成功”。
- **预计时长**：2 小时＝速览 0.5 + 概念 30 + 代码 40 + 动手 20 + 动态 20 + 收尾 9.5＝120 分钟。
- **进度依据〔ARTIFACT〕**：完整台账、`00_进度/智能体规则.md`、11-16 全文已读取；台账原有 19 讲，当前 `02_AndroidAI` 第 2 讲与昨日预告一致。今天不重复首讲设备/下载/授权组合，不出周总结。勾选只表示**材料已产出**，复述待填。
- **验证边界〔TOOL〕**：本机 Python 3.9.6 标准库实跑 Host 模拟；10 个测试方法、23 个场景断言通过。Kotlin 官方 API 片段仅 SPEC_CHECK，**Kotlin/Android 编译、真机推理均 NOT_EXECUTED**；无 `kotlinc`/`gradle`，已有 `adb` 未使用。未安装工具、修改真实仓库、连接手机、下载模型、调用云聊天或读取令牌。

## 1 概念精讲（30 min）
- **一句话定义**：Prompt API 最小调用，是应用通过门禁后把短提示封装成一次请求，等待完整候选返回，校验结果并结束该次客户端生命周期。
- **它解决什么问题 / 为什么现在必须懂**：昨天只回答“是否可以尝试”。今天真正把这条布尔建议接到一次受控生成；否则 UI 容易在初始化完成时就显示成功、页面离开后仍更新结果，或失败后偷偷上传原文。

### 1.1 今天只走这条链
```text
昨日门禁结果 + 用户点击 + 短输入非空 + 当前最上层前台
   ↓
创建新的 Generation.getClient()（昨日探测实例已经 close，不能复用）
   ↓
同一实例 checkStatus() 确认仍 AVAILABLE（续用，不重讲状态矩阵）
   ↓
TextPart → GenerateContentRequest.Builder → build()
   ↓
generateContent(request) 挂起等待一次完整响应
   ↓
仅读取 candidates 首个候选 → 文本/结束原因检查 → UI 状态
   ↓
finally 尝试 close()；取消继续向上传播；无自动下载/重试/上云
```
- **非流式适合今天**：官方说明 `generateContent(request)` 是可取消的非阻塞挂起函数，等整段返回；不是 UI 线程上 `get()` 阻塞，也不是“创建对象即生成”。今天只处理一条短便签，不加流式、聊天记忆或工具调用。
- **最小请求**：一个 `TextPart`，`candidateCount = 1`，`maxOutputTokens = 64`。64 是本课输出 Token 预算〔PROPOSAL〕，不是 64 个汉字、不是 10 秒性能承诺；默认值 0 表示模型配置的目标长度，不是零输出。未设置采样细节，不重开 W1 参数课。
- **有效结果不等于接口返回**：文档说 `candidates` 非空，但应用仍防御坏适配器/测试空集合。空白文本 → `EMPTY_RESULT`；自然停止 `STOP` + 非空文本 → `SUCCESS`；`MAX_TOKENS` → `TRUNCATED`，保留草稿但不自动替换原文；`OTHER` 或未知结束原因 → `INCOMPLETE`。这些状态都是应用自定义，不是 SDK 枚举。
- **取消与超时不同**：本次查询/生成预算耗尽 → 明确超时状态；页面退出或父协程取消 → `CancellationException` 继续传播。`withTimeoutOrNull` 只吸收它自己的超时，不应把外层取消当成本次超时。客户端引用在超时块外持有，避免异步超时丢失可关闭资源。
- **前台要求**：官方要求应用为最上层前台，前台服务不替代；查询后与发布结果前都复查。页面退出要由调用方取消绑定该页面的 Job，仅检查布尔值不会自动中止在途任务。边界竞态仍以真实 SDK 错误为准，不声称 Host 能证明 Android 调度。

**常见误区（3 条）**：
1. 很多人以为“昨日门禁已通过，拿探测客户端继续生成即可”，其实昨日 `finally` 已关闭实例；今日重新创建、同实例复查状态，再发一次请求。
2. 很多人以为“请求返回或字符串非空就是成功”，其实结束原因可能是 Token 上限或其他停止；空结果、截断与完整结果需要不同 UI。
3. 很多人以为“`catch (Exception)` 能统一处理所有结束”，其实取消是生命周期控制信号；必须先捕获并重抛，不能自动重试或切云端。

**教学参考：当天实读，和第 4 段动态分开**。下面 S01～S15 是接口/版本证据；S16～S21 是第 4 段来源证据。日期是页面更新/原发布日，不冒充今天发布；必要旧接口链接标“继续使用”。

- [S01 Direct model access接入指南](https://developers.google.com/ml-kit/genai/prompt/android/get-started)（2026-10-27；继续使用（首次11-16））：Android API >=26；依赖beta4；非流式generateContent；短输入输出；不自动下载。
- [S02 ML Kit GenAI概览](https://developers.google.com/ml-kit/genai)（2026-11-10；继续使用（首次11-16））：输入、推理、输出本地处理；仅最上层前台；前台服务不替代；仍可能配额失败。
- [S03 Generation.getClient](https://developers.google.com/android/reference/kotlin/com/google/mlkit/genai/prompt/Generation)（2026-01-28；继续使用（首次11-16））：getClient()创建默认配置的新GenerativeModel实例。
- [S04 GenerativeModel生成与释放](https://developers.google.com/android/reference/kotlin/com/google/mlkit/genai/prompt/GenerativeModel)（2026-10-27；继续使用（首次11-16））：suspend generateContent(request)返回完整GenerateContentResponse，可取消，可能GenAiException；close()可多次调用。
- [S05 Google Maven genai-prompt beta4 POM](https://dl.google.com/dl/android/maven2/com/google/mlkit/genai-prompt/1.0.0-beta4/genai-prompt-1.0.0-beta4.pom)（无发布日期；版本文件；继续使用（首次11-16））：genai-prompt=1.0.0-beta4；kotlin-stdlib=2.3.21；kotlinx-coroutines-core=1.7.3；未解析依赖。
- [S06 GenerateContentRequest](https://developers.google.com/android/reference/kotlin/com/google/mlkit/genai/prompt/GenerateContentRequest)（2026-10-27）：candidateCount默认1；maxOutputTokens默认0不是零输出；本课显式64；未开启思考或工具。
- [S07 GenerateContentRequest.Builder](https://developers.google.com/android/reference/kotlin/com/google/mlkit/genai/prompt/GenerateContentRequest.Builder)（2026-10-27）：构造器Builder(text:TextPart)；candidateCount和maxOutputTokens为可变Int?；build()返回请求。
- [S08 TextPart](https://developers.google.com/android/reference/kotlin/com/google/mlkit/genai/prompt/TextPart)（2026-01-28）：data class；构造器TextPart(textString:String)。
- [S09 GenerateContentResponse](https://developers.google.com/android/reference/kotlin/com/google/mlkit/genai/prompt/GenerateContentResponse)（2026-07-15）：candidates:List<Candidate>文档保证非空；只读候选，不读thoughtProcess。
- [S10 Candidate文本与结束原因](https://developers.google.com/android/reference/kotlin/com/google/mlkit/genai/prompt/Candidate)（2026-10-27）：text声明String但文字提示仅工具结果时可能null；防御空文本；finishReason:Int?最终应非空。
- [S11 Candidate.FinishReason](https://developers.google.com/android/reference/kotlin/com/google/mlkit/genai/prompt/Candidate.FinishReason)（2026-01-28）：整数常量STOP自然停止、MAX_TOKENS达到上限、OTHER其他停止；非Kotlin enum。
- [S12 GenAiException](https://developers.google.com/android/reference/kotlin/com/google/mlkit/genai/common/GenAiException)（2026-07-15）：继承Exception；errorCode为Int；不按message字符串分流；协程CancellationException另行传播。
- [S13 kotlinx.coroutines 1.7.3 Timeout.kt](https://raw.githubusercontent.com/Kotlin/kotlinx.coroutines/1.7.3/kotlinx-coroutines-core/common/src/Timeout.kt)（源码版本1.7.3，不推定发布日期）：withTimeoutOrNull只将自己创建的超时转成null，外层/其他取消继续向上传播；资源引用应在超时块外持有。
- [S14 kotlinx.coroutines 1.7.3 CoroutineScope.kt](https://raw.githubusercontent.com/Kotlin/kotlinx.coroutines/1.7.3/kotlinx-coroutines-core/common/src/CoroutineScope.kt)（源码版本1.7.3，不推定发布日期）：currentCoroutineContext()返回当前协程上下文；源码版本锁定1.7.3。
- [S15 kotlinx.coroutines 1.7.3 Job.kt](https://raw.githubusercontent.com/Kotlin/kotlinx.coroutines/1.7.3/kotlinx-coroutines-core/common/src/Job.kt)（源码版本1.7.3，不推定发布日期）：CoroutineContext.ensureActive()调用Job.ensureActive()，已取消时抛CancellationException。
- [S16 动态｜A2UI 1.0：原生交互界面的开放协议](https://developers.googleblog.com/a2ui-10-build-delightful-fast-reliable-agentic-experiences/)（2026-11-11）：协议1.0稳定；React/Flutter等渲染器；Jetpack Compose当时为0.9.1，1.0即将支持，不能称Android渲染器已1.0。
- [S17 岗位证据｜腾讯混元架构专家正式详情API](https://careers.tencent.com/tencentcareer/api/post/ByPostId?postId=2110191895966826496)（2026-10-31）：正文明确7年以上研发、系统架构、Agent/RAG、跨端和端云协同；是长期能力参考，不是当前即可胜任。
- [S18 岗位｜腾讯混元大模型工程架构专家/Tech Lead](https://careers.tencent.com/jobdesc.html?postId=2110191895966826496)（2026-10-31）：页面HTTP200仅JS壳；岗位职责/要求实读自正式ByPostId API；原发布日期未知，更新时间2026-10-31。
- [S19 工具证据｜ML Kit GenAI Quickstart README](https://raw.githubusercontent.com/googlesamples/mlkit/master/android/genai/README.md)（README未给原发布日）：官方README含Prompt等GenAI示例；不推定首次发布日期。
- [S20 工具证据｜ML Kit GenAI目录API](https://api.github.com/repos/googlesamples/mlkit/contents/android/genai)（README未给原发布日）：官方内容API列出README和app等文件；已核对目录不是空壳；未克隆或编译。
- [S21 工具｜ML Kit GenAI Quickstart](https://github.com/googlesamples/mlkit/tree/master/android/genai)（README未给原发布日）：页面HTTP200；正文主要依据README与正式目录API；与昨日Gallery不同，是ML Kit样例。

- 📝 **我的复述（留空给你自己写）**：


## 2 代码片段（40 min）
- **场景**：“本地便签改写”入口。只用虚构文本；用户先预览生成结果，点击采纳才替换输入。模型失败时保留手动编辑，不外发原文。
- **依赖与版本**：Host＝CPython **3.9.6** 标准库 `asyncio/dataclasses/typing/unittest`，零 pip 依赖；本机无 OpenAI SDK，本课也不需要。Android＝`com.google.mlkit:genai-prompt:1.0.0-beta4`（官方指南与 Google Maven POM 均实读），Android API ≥26；该 POM 声明 Kotlin 标准库 2.3.21、协程核心 1.7.3，**只是依赖声明，不是本机已安装/已解析事实**。不新建/改动真实 Android 工程，不猜 AGP/Compose 完整版本组合。

### 2.1 最小可运行 Host 契约（已执行）
下面与 `../00_进度/验证/2026-11-17/prompt_contract.py` **逐字一致**。`FakeClient` 生成固定 fixture；其中 `SUCCESS` 只表示**模拟调用契约成功**，不是 Nano 输出。

```python
"""仅 Host 模拟：单次生成生命周期；不连接 SDK、手机或云端。"""
import asyncio
from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass(frozen=True)
class Candidate:
    text: Optional[str]
    finish_reason: Optional[str] = "STOP"


@dataclass(frozen=True)
class Response:
    candidates: Tuple[Candidate, ...]


@dataclass(frozen=True)
class Request:
    prompt: str
    max_output_tokens: int = 64
    candidate_count: int = 1


@dataclass(frozen=True)
class Result:
    state: str
    text: str = ""
    note: str = ""


class FakeClient:
    """所有输出都是固定 fixture，不能用来证明 SDK、模型质量或性能。"""
    def __init__(self, mode="normal", feature="AVAILABLE", close_error=False):
        self.mode, self.feature = mode, feature
        self.close_error = close_error
        self.events = ["create"]
        self.requests = []
        self.started = asyncio.Event()
        self.closed = False

    async def check_status(self):
        self.events.append("check_status")
        if self.mode == "status_error":
            raise RuntimeError("虚构状态查询错误")
        if self.mode == "status_timeout":
            await asyncio.Event().wait()
        return self.feature

    async def generate(self, request):
        if self.closed:
            raise RuntimeError("不能复用已关闭客户端")
        self.events.append("generate")
        self.requests.append(request)
        self.started.set()
        if self.mode == "error":
            raise RuntimeError("虚构生成错误")
        if self.mode == "cancel":
            raise asyncio.CancelledError()
        if self.mode == "wait":
            try:
                await asyncio.Event().wait()  # 等待真实任务取消或本地预算耗尽
            except asyncio.CancelledError:
                self.events.append("generate_cancelled")
                raise
        candidates = {
            "normal": (Candidate("今天先完成一件小事。"),),
            "blank": (Candidate("  "),),
            "no_candidates": (),  # 防御性坏适配器 fixture；SDK文档说列表非空
            "null_text": (Candidate(None),),
            "truncated": (Candidate("今天先完成", "MAX_TOKENS"),),
            "other": (Candidate("未完成草稿", "OTHER"),),
            "unknown_finish": (Candidate("未完成草稿", None),),
        }[self.mode]
        return Response(candidates)

    def close(self):
        self.events.append("close")
        self.closed = True
        if self.close_error:
            raise RuntimeError("虚构清理错误")


async def generate_short(raw, gate_passed, is_foreground, factory, states,
                         status_budget=0.02, generation_budget=0.02):
    """门禁结果来自昨日逻辑；这里只消费结果，不重算设备组合。"""
    def finish(state, text="", note=""):
        states.append(state)
        return Result(state, text, note)

    text = raw.strip()
    if not text:
        return finish("EMPTY_INPUT")
    if len(text) > 120:
        return finish("INPUT_TOO_LONG")  # 产品示例上限，不是SDK Token限制
    if not gate_passed:
        return finish("BLOCKED")
    if not is_foreground():
        return finish("FOREGROUND_REQUIRED")
    client = None
    stage = "CREATE"
    try:
        client = factory()  # 昨日客户端已close；今天创建独立有效实例
        stage = "CHECK"
        states.append("CHECKING")
        try:
            feature = await asyncio.wait_for(client.check_status(), status_budget)
        except asyncio.TimeoutError:
            return finish("CHECK_TIMEOUT")
        if feature != "AVAILABLE":
            return finish("BLOCKED")  # 不下载、不隐式上传
        if not is_foreground():
            return finish("FOREGROUND_REQUIRED")
        request = Request("请将下面的虚构便签改写成一句简洁中文，只返回改写文本：\n" + text)
        stage = "GENERATE"
        states.append("GENERATING")
        try:
            response = await asyncio.wait_for(client.generate(request), generation_budget)
        except asyncio.TimeoutError:
            return finish("GENERATION_TIMEOUT")
        if not is_foreground():
            return finish("FOREGROUND_REQUIRED")  # 离开前台不发布成功
        candidate = response.candidates[0] if response.candidates else None
        output = (candidate.text or "").strip() if candidate else ""
        if not output:
            return finish("EMPTY_RESULT")
        if candidate.finish_reason == "MAX_TOKENS":
            return finish("TRUNCATED", output)
        if candidate.finish_reason != "STOP":
            return finish("INCOMPLETE")
        return finish("SUCCESS", output)
    except asyncio.CancelledError:
        states.append("CANCELLED")
        raise  # 生命周期取消必须传播，不能转为成功或云端重试
    except Exception as error:
        return finish("FAILED", note=stage + ":" + type(error).__name__)
    finally:
        if client is not None:
            try:
                client.close()
            except Exception:
                # 清理错误不能覆盖原始生成失败或取消；独立记录事件，不打印提示词
                client.events.append("cleanup_failed")


async def main():
    client = FakeClient()
    states = []
    result = await generate_short("先把今天最重要的小事完成", True, lambda: True,
                                  lambda: client, states)
    print("Host 模拟结果：", result)
    print("状态：", " -> ".join(states))
    print("生命周期：", " -> ".join(client.events))
    print("调用次数：", len(client.requests), "；没有端侧推理")


if __name__ == "__main__":
    asyncio.run(main())
```

### 2.2 对生命周期的可执行测试（已执行）
下面与 `test_prompt_contract.py` 逐字一致。今天不是重跑昨日 2304 个能力组合，而是验证**调用次数、状态顺序、取消传播和 close**。

```python
"""对应用生命周期契约的Host测试，不验证SDK真实性或设备性能。"""
import asyncio
import unittest
from prompt_contract import FakeClient, generate_short


class LifecycleTest(unittest.IsolatedAsyncioTestCase):
    async def test_preflight_rejects_without_client(self):
        rows = [
            ("空输入", "  ", True, True, "EMPTY_INPUT"),
            ("输入过长", "字" * 121, True, True, "INPUT_TOO_LONG"),
            ("门禁未通过", "虚构便签", False, True, "BLOCKED"),
            ("初始非前台", "虚构便签", True, False, "FOREGROUND_REQUIRED"),
        ]
        for name, raw, gate, foreground, expected in rows:
            with self.subTest(name=name):
                def forbidden():
                    self.fail("拒绝输入时不应创建客户端")
                states = []
                result = await generate_short(raw, gate, lambda: foreground, forbidden, states)
                self.assertEqual(result.state, expected)
                self.assertEqual(states, [expected])
                print("PASS", name, expected)

    async def test_unavailable_closes_without_generation(self):
        c, states = FakeClient(feature="UNAVAILABLE"), []
        r = await generate_short("虚构便签", True, lambda: True, lambda: c, states)
        self.assertEqual(r.state, "BLOCKED")
        self.assertEqual(c.events, ["create", "check_status", "close"])
        self.assertEqual(c.requests, [])
        print("PASS 不可用：零次生成，客户端关闭")

    async def test_result_table(self):
        rows = [("normal", "SUCCESS"), ("blank", "EMPTY_RESULT"),
                ("no_candidates", "EMPTY_RESULT"), ("null_text", "EMPTY_RESULT"),
                ("truncated", "TRUNCATED"), ("other", "INCOMPLETE"),
                ("unknown_finish", "INCOMPLETE"), ("error", "FAILED")]
        for mode, expected in rows:
            with self.subTest(mode=mode):
                c, states = FakeClient(mode), []
                r = await generate_short("虚构便签", True, lambda: True, lambda: c, states)
                self.assertEqual(r.state, expected)
                self.assertEqual(c.events, ["create", "check_status", "generate", "close"])
                self.assertEqual(states, ["CHECKING", "GENERATING", expected])
                self.assertEqual(len(c.requests), 1)
                self.assertEqual(c.requests[0].max_output_tokens, 64)
                self.assertEqual(c.requests[0].candidate_count, 1)
                self.assertTrue(c.requests[0].prompt.endswith("\n虚构便签"))
                if expected not in ["SUCCESS", "TRUNCATED"]:
                    self.assertEqual(r.text, "")
                print("PASS", mode, expected, "一次生成+关闭")

    async def test_lifecycle_cancel_propagates(self):
        c, states = FakeClient("wait"), []
        task = asyncio.create_task(generate_short("虚构便签", True, lambda: True,
                                   lambda: c, states, generation_budget=5))
        await asyncio.wait_for(c.started.wait(), 1)
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertEqual(states, ["CHECKING", "GENERATING", "CANCELLED"])
        self.assertEqual(c.events[-2:], ["generate_cancelled", "close"])
        self.assertEqual(len(c.requests), 1)
        print("PASS 生命周期取消：向上传播，关闭，无自动重试")

    async def test_generator_cancel_propagates(self):
        c, states = FakeClient("cancel"), []
        with self.assertRaises(asyncio.CancelledError):
            await generate_short("虚构便签", True, lambda: True, lambda: c, states)
        self.assertTrue(c.closed)
        self.assertEqual(states[-1], "CANCELLED")
        print("PASS 生成协程取消：不吞控制信号")

    async def test_generation_timeout_cancels_and_closes(self):
        c, states = FakeClient("wait"), []
        r = await generate_short("虚构便签", True, lambda: True, lambda: c, states)
        self.assertEqual(r.state, "GENERATION_TIMEOUT")
        self.assertEqual(c.events[-2:], ["generate_cancelled", "close"])
        self.assertEqual(len(c.requests), 1)
        print("PASS 生成超时：取消在途调用，关闭，无成功文本")

    async def test_status_timeout_and_error(self):
        for mode, expected in [("status_timeout", "CHECK_TIMEOUT"), ("status_error", "FAILED")]:
            with self.subTest(mode=mode):
                c, states = FakeClient(mode), []
                r = await generate_short("虚构便签", True, lambda: True, lambda: c, states)
                self.assertEqual(r.state, expected)
                self.assertEqual(c.requests, [])
                self.assertTrue(c.closed)
                print("PASS", mode, expected, "零次生成+关闭")

    async def test_creation_error(self):
        def fail():
            raise RuntimeError("虚构创建失败")
        r = await generate_short("虚构便签", True, lambda: True, fail, [])
        self.assertEqual((r.state, r.note), ("FAILED", "CREATE:RuntimeError"))
        print("PASS 创建失败：明确阶段")

    async def test_foreground_changes(self):
        for checks, expected_calls in [([True, False], 0), ([True, True, False], 1)]:
            with self.subTest(checks=checks):
                values, c, states = iter(checks), FakeClient(), []
                r = await generate_short("虚构便签", True, lambda: next(values), lambda: c, states)
                self.assertEqual(r.state, "FOREGROUND_REQUIRED")
                self.assertEqual(len(c.requests), expected_calls)
                self.assertTrue(c.closed)
                print("PASS 前台变化：生成次数", expected_calls, "不发布成功")

    async def test_cleanup_does_not_mask_failure_or_cancel(self):
        for mode in ["error", "cancel"]:
            with self.subTest(mode=mode):
                c, states = FakeClient(mode, close_error=True), []
                if mode == "cancel":
                    with self.assertRaises(asyncio.CancelledError):
                        await generate_short("虚构便签", True, lambda: True, lambda: c, states)
                else:
                    r = await generate_short("虚构便签", True, lambda: True, lambda: c, states)
                    self.assertEqual((r.state, r.note), ("FAILED", "GENERATE:RuntimeError"))
                self.assertEqual(c.events[-1], "cleanup_failed")
                print("PASS 清理错误不掩盖", mode)


if __name__ == "__main__":
    unittest.main(verbosity=2)
```

**运行命令**（只操作专用 fixture）：
```bash
cd '/Users/alion/DemoProjects/ToDoList/AI每日学习/00_进度/验证/2026-11-17'
python3 -B prompt_contract.py
python3 -B -m unittest -v test_prompt_contract.py
```
**真实结果〔EXECUTED〕**：两条命令退出码均为 `0`；`unittest` 10 个测试方法通过，输出 23 条 `PASS` 场景行。完整命令/环境/退出码在 `runs.json`，输出在 `fixture-run.log`、`tests.log`。
```text
Host 模拟结果： Result(state='SUCCESS', text='今天先完成一件小事。', note='')
状态： CHECKING -> GENERATING -> SUCCESS
生命周期： create -> check_status -> generate -> close
调用次数： 1 ；没有端侧推理
PASS 不可用：零次生成，客户端关闭
PASS 生命周期取消：向上传播，关闭，无自动重试
PASS 生成超时：取消在途调用，关闭，无成功文本
Ran 10 tests
OK
```
测试不证明 SDK 二进制/API 版本兼容、AICore 取消响应、真实模型质量、设备性能或端侧隐私实现。20 ms 仅让 Host 等待 fixture 快速结束；Android 示例 2500/10000 ms 是教学 UI 预算，**不能相互换算为推理延迟**。

### 2.3 完整 Kotlin 实际 API 调用片段（官方契约核对，NOT_EXECUTED）
此函数已经包含请求构造、真实 `generateContent` 调用、公开候选处理、异常/取消与释放；与 `NanoShortGeneration.kt` 逐字一致。**它是接入函数，不是独立可运行 Android App**：还需要已有 Android 应用、Gradle/SDK/协程依赖、页面前台证据与 Job 绑定，以及支持并已准备好 Nano 的设备。以上条件本次未验证，所以不给“编译/推理通过”结论。

```kotlin
// NOT_EXECUTED：实际ML Kit API接入片段，不是完整Android App。
// com.google.mlkit:genai-prompt:1.0.0-beta4；Android API >= 26。
// 需要已有Android应用与协程环境；禁止本次安装依赖/连接手机/下载模型。
import com.google.mlkit.genai.common.FeatureStatus
import com.google.mlkit.genai.common.GenAiException
import com.google.mlkit.genai.prompt.Candidate
import com.google.mlkit.genai.prompt.GenerateContentRequest
import com.google.mlkit.genai.prompt.Generation
import com.google.mlkit.genai.prompt.GenerativeModel
import com.google.mlkit.genai.prompt.TextPart
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.ensureActive
import kotlinx.coroutines.currentCoroutineContext
import kotlinx.coroutines.withTimeoutOrNull

// 应用自定义结果；不是Google SDK枚举。
data class ShortResult(val state: String, val text: String = "", val note: String = "")

suspend fun generateShortNote(
    raw: String,
    gatePassed: Boolean,              // 续用昨日can_attempt_local；不可写死true
    isTopForeground: () -> Boolean,  // 调用方提供当前证据，不是前台服务状态
    onState: (String) -> Unit,        // 映射给UI；必须不抛异常、不外发数据
    onCleanupFailure: () -> Unit     // 独立本地告警；不记录原文，必须不抛异常
): ShortResult {
    fun finish(state: String, text: String = "", note: String = ""): ShortResult {
        onState(state)
        return ShortResult(state, text, note)
    }
    currentCoroutineContext().ensureActive()
    val text = raw.trim()
    if (text.isEmpty()) return finish("EMPTY_INPUT")
    if (text.length > 120) return finish("INPUT_TOO_LONG") // 产品上限，不是Token计数
    if (!gatePassed) return finish("BLOCKED")
    if (!isTopForeground()) return finish("FOREGROUND_REQUIRED")
    var client: GenerativeModel? = null
    var stage = "CREATE"
    try {
        val model = Generation.getClient() // 不复用昨日finally中已close的实例
        client = model                    // 先记录引用，再进入可取消区间
        stage = "CHECK"
        onState("CHECKING")
        val status = withTimeoutOrNull(2500L) { model.checkStatus() }
            ?: return finish("CHECK_TIMEOUT")
        if (status != FeatureStatus.AVAILABLE) return finish("BLOCKED")
        if (!isTopForeground()) return finish("FOREGROUND_REQUIRED")
        val request = GenerateContentRequest.Builder(
            TextPart("请将下面的虚构便签改写成一句简洁中文，只返回改写文本：\n$text")
        ).apply {
            candidateCount = 1
            maxOutputTokens = 64  // Token预算，不保证64汉字，更不是时延保证
        }.build()
        stage = "GENERATE"
        onState("GENERATING")
        val response = withTimeoutOrNull(10000L) { model.generateContent(request) }
            ?: return finish("GENERATION_TIMEOUT")
        currentCoroutineContext().ensureActive()
        if (!isTopForeground()) return finish("FOREGROUND_REQUIRED")
        // 文档说candidates非空；仍防御空适配结果。只读取公开候选，不读取thoughtProcess。
        val candidate = response.candidates.firstOrNull()
        val output = candidate?.text.orEmpty().trim()
        if (output.isEmpty()) return finish("EMPTY_RESULT")
        return when (candidate?.finishReason) {
            Candidate.FinishReason.STOP -> finish("SUCCESS", output)
            Candidate.FinishReason.MAX_TOKENS -> finish("TRUNCATED", output)
            else -> finish("INCOMPLETE") // 不把OTHER/未知结束原因当完整成功
        }
    } catch (cancelled: CancellationException) {
        onState("CANCELLED")
        throw cancelled // Lifecycle/ViewModel取消继续向上；不触发云端或重试
    } catch (error: GenAiException) {
        // 保存数值错误码与阶段，不按message猜原因，不记录提示词/输出。
        return finish("FAILED", note = "$stage:SDK:${error.errorCode}")
    } catch (error: Exception) {
        return finish("FAILED", note = "$stage:${error.javaClass.simpleName}")
    } finally {
        try {
            client?.close()  // 每次调用独立生命周期；取消/超时/失败同样尝试释放
        } catch (_: Exception) {
            onCleanupFailure() // 不让清理错误掩盖原始失败或取消
        }
    }
}
```

**接入契约（不是另一个主题）**：
- 原有工程具备条件后才添加官方 `implementation("com.google.mlkit:genai-prompt:1.0.0-beta4")`；本次**未执行此修改**。
- 调用方把昨日门禁结果传入 `gatePassed`，把当前页面/最上层前台证据传入 `isTopForeground`，把 `onState` 映射到不可变 UI 状态。三个回调不得抛异常，不得写入原文日志或发送数据。
- 页面进入后台/退出、输入被新请求替代时取消该请求 Job；不能仅依赖 `viewModelScope` 自动处理所有页面不可见情况。本课只展示单次函数，Compose 流式/多请求调度留到后续。
- `onState("CANCELLED")` 可记录局部状态，不要求离开页面后强行刷新旧 UI；`onCleanupFailure` 仅独立本地告警。没有任何 `download()`、网络客户端、云端 fallback 或自动重试。

**逐行要点（5 条）**：
1. 输入/门禁/前台拒绝发生在创建客户端之前，因此拒绝路径应是**零次生成**；创建失败记录 `CREATE` 阶段。
2. `client = model` 在超时块外，`finally` 可取得有效引用；同实例状态复查后才构造请求。昨日已关闭实例不被复用。
3. `Builder(TextPart(...)).apply { ... }.build()` 是实读的实际 SDK 构造器与属性；Host 的 `Request` 只是相应的应用模拟，不是伪造 SDK 类。
4. `firstOrNull()`、`orEmpty().trim()` 与 `finishReason` 分别防御候选缺失、空文本和不完整结束；只读 `candidates`，不读推理过程字段。
5. 取消先重抛，SDK 失败保留数值错误码，清理失败另行告警；不输出原始异常文案/业务数据，也不把失败变为授权。

**踩坑提示**：
- SDK 的 `Candidate.text` 类型签名和文字说明存在细微不一致（声明 `String`，文字说仅工具结果时可能 null）；本课不启用工具，但仍防御空文本，真实运行需继续核验。
- SDK 说明响应候选非空。Host 空集合用例是**应用防御性坏适配器测试**，不是声称官方 SDK 正常返回空集合。
- `maxOutputTokens` 能截断，不能保证格式或指定汉字数。`TRUNCATED` 只能显示“未完成草稿”，不得自动替换用户原文。
- `close()` 尝试失败的告警不代表已释放成功；Host 的 `closed=True` 仅是模拟标记。取消/预算耗尽能否及时停止设备计算需要后续真机验证。

## 3 动手 / 联想（20 min）
- **动手任务〔PROPOSAL〕**：在专用 Host fixture 增加一个“模型自然结束但只返回换行”的模式 `newline`，让 `test_result_table` 新增预期 `EMPTY_RESULT`；验证一次生成、无成功文本、最后 close。只做这一个小改动，不安装 SDK，不改真实工程。
- **时间分配**：5 分钟在纸面列 `GENERATING / SUCCESS / EMPTY_RESULT / TRUNCATED / FAILED` 对应 UI；10 分钟改 fixture；5 分钟重跑上述两条命令。
- **与我的工作结合**：Android 便签/聊天输入框可在按钮触发后显示“正在本地生成”；成功进入预览，用户点击采纳才写回；空结果/失败保持原文可编辑。前端和小程序可沿用“请求状态≠业务采纳”语义，但它们不能直接使用本 Android ML Kit SDK，更不能借网页成功证明手机端侧推理。
- **自检标准**：换行结果不是成功；重跑前后的请求次数仍为 1；不自动下载/重试/上云；截断只显示草稿，失败保留原文。练习记录留给你，不预填完成或复述。

## 4 动态与机会（20 min）
> 观察日期 **2026-11-17**；本段 **1 条新动向 + 1 条岗位 + 1 条工具**。均按 canonical 与完整台账去重后首次收录；“新”指本学习系统新收录，不表示今天刚发布。教学参考继续使用不充当新动态。外链使用 `curl -sL` 核验；HTTP 200 页面壳不当正文，正式 API/README 单独列证据。

- 🔥 **新动向（1 条）｜Google 发布 A2UI 1.0：让 Agent 返回原生交互界面** — 官方正文与 `datePublished` 均确认**原发布日 2026-11-11**，HTTP 200 已实读。协议稳定到 1.0，但正文明确 **Jetpack Compose 渲染器当前 0.9.1，1.0 支持即将到来**；不能把协议版本当全部平台 SDK 版本。**影响判断〔PROPOSAL〕**：你的 React/Flutter/Compose 背景可成为 AI 应用交付优势；先把今天单次生成的状态/预览做好，之后再研究可控原生组件，不在今日接 A2UI。— [来源](https://developers.googleblog.com/a2ui-10-build-delightful-fast-reliable-agentic-experiences/)
- 💼 **岗位观察（1 条）｜腾讯混元：大模型工程架构专家 / Tech Lead（深圳/北京）** — **更新时间 2026-10-31，原发布日期未提供**。职位网页 HTTP 200 仅 JS 壳，职责/要求来自正式详情 API（S17，HTTP 200、业务 `Code=200`）实读。正文要求 **7 年以上研发**、系统设计/异步调度、Agent/RAG 与跨端/端云协同；并非只会客户端调用 API。**对应该补〔PROPOSAL〕**：现有多端经验有衔接点，但还需后端与 AI 工程作品；今天用可取消、可测试、明确失败的调用链补一小块。该高级岗位是长期能力标尺，**不宣称当前即可胜任**，不编薪资或岗位量。— [来源](https://careers.tencent.com/jobdesc.html?postId=2110191895966826496)
- 🧰 **其他有价值信息（1 条）｜Google 官方 ML Kit GenAI Quickstart** — 官方 GenAI 概览指向该目录，目录页/内容 API/README 已核验（HTTP 200）；README 明列 Prompt 示例，**未提供该功能原发布日**，不拿版权年份或仓库更新时间代替。**值得看〔PROPOSAL〕**：读真实样例的文件组织，区分 SDK 调用层与 UI；它是 ML Kit 路线，与昨日自部署模型 Gallery 不同。本次只阅读，不克隆、不编译、不运行或下载模型。— [来源](https://github.com/googlesamples/mlkit/tree/master/android/genai)

**20 分钟阅读安排**：新动向 8 分钟（只看平台版本边界）；岗位 6 分钟（圈出客户端强项与后端缺口）；工具 6 分钟（只看 Prompt 样例入口）。不把产品演示或招聘要求抄成自己的验证成果。

## 5 明日预告与待复习（9.5 min）
- **明日主题〔PROPOSAL〕**：Android × AI 第 3 讲：**端侧流式生成的 Compose 增量呈现（续地基 Streaming，聚焦 Android 接入）**。先复核流式 API 与页面生命周期；工具/设备不足仍分清 Host/NOT_EXECUTED，不重开通用流式概念课。
- **待复习（3 条）**：
  1. 昨日门禁只给“可尝试”，昨日已 close 的实例不能复用；今日实例同生命周期复查后才生成。
  2. 非空且 `STOP` 才按本课策略显示完整成功；空结果/截断/其他停止不同状态，用户采纳是另一动作。
  3. 取消继续传播；超时显式结束；finally 尝试 close；失败不自动重试、下载或上传。
- **一句话复盘**：最容易忘的是——“拿到响应”与“得到可采纳的完整结果”之间，还有结果校验和用户确认。
- **收尾安排**：5 分钟自己填复述，3 分钟核对新增换行 fixture，1.5 分钟记录尚缺的 Kotlin/SDK/真机验证。本文产出不等于你已经学会。
- **证据定位**：`../00_进度/验证/2026-11-17/`：`inputs.json`（完整输入版本及19篇历史哈希）、`sources.json`（来源/日期/canonical/摘要）、三份源码与两份日志、`runs.json`（命令/退出码）、`进度.写前备份.md`、`ledger.diff`、`验收.json`。USER＝授权与禁令，ARTIFACT＝台账/规则/昨日全文，TOOL＝来源与实跑，PROPOSAL＝教学预算/任务/明日主题；无未标注的假设，无真实业务数据。
