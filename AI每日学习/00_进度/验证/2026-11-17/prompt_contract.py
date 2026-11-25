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
