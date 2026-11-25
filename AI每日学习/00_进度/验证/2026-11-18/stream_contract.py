"""仅Host固定数据：不调用Android、模型、网络；不测推理或性能。"""
import asyncio
from dataclasses import dataclass, replace
from typing import Optional


@dataclass(frozen=True)
class Frame:
    text: Optional[str] = ""
    reason: Optional[str] = None


@dataclass(frozen=True)
class Ui:
    request_id: int = 0
    state: str = "IDLE"
    draft: str = ""
    reason: Optional[str] = None
    notice: str = ""

    @property
    def can_accept(self):
        return self.state == "SUCCESS" and bool(self.draft.strip())


def append_frame(ui, frame, mode="DELTA"):
    """Android已核对为DELTA；CUMULATIVE仅演示别的适配器必须明确声明。"""
    if ui.reason is not None:
        raise ValueError("终止标记后仍有帧")
    if mode not in ("DELTA", "CUMULATIVE"):
        raise ValueError("未知流值语义")
    piece = frame.text or ""
    # 不trim逐片文本，不按内容去重：两个相同词也可能是合法输出。
    draft = ui.draft + piece if mode == "DELTA" else piece
    return replace(ui, state="STREAMING", draft=draft, reason=frame.reason)


def completed(ui):
    if ui.reason == "STOP":
        state = "SUCCESS" if ui.draft.strip() else "EMPTY_RESULT"
    elif ui.reason == "MAX_TOKENS":
        state = "TRUNCATED"
    else:
        state = "INCOMPLETE"  # EOF或OTHER/未知原因，不能当成功
    return replace(ui, state=state)


class FakeClient:
    def __init__(self, frames=(), wait=False, fail=False, feature="AVAILABLE",
                 close_error=False, stubborn=False):
        self.frames, self.wait, self.fail = frames, wait, fail
        self.feature, self.close_error, self.stubborn = feature, close_error, stubborn
        self.events = ["create"]
        self.ready = asyncio.Event()
        self.closed = False

    async def check_status(self):
        self.events.append("check")
        return self.feature

    async def stream(self):
        self.events.append("stream")
        for frame in self.frames:
            yield frame
            await asyncio.sleep(0)  # 让不同任务有机会交错；不是性能数据
        self.ready.set()
        if self.wait:
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                self.events.append("cancel_received")
                if not self.stubborn:
                    raise
                yield Frame("旧请求迟到文本", "STOP")  # 坏适配器防御fixture
        if self.fail:
            raise RuntimeError("固定失败fixture")

    def close(self):
        self.events.append("close")
        if self.close_error:
            raise RuntimeError("固定释放失败fixture")
        self.closed = True


class Controller:
    """单事件循环模拟ViewModel：请求代号挡旧结果，锁隔离资源生命周期。"""
    def __init__(self):
        self.epoch, self.task = 0, None
        self.ui = Ui()
        self.lock = asyncio.Lock()
        self.history = []
        self.cleanup_errors = 0

    def publish(self, request_id, ui):
        if request_id != self.epoch:
            return False
        self.ui = ui
        self.history.append(ui)
        return True

    def start(self, factory, is_foreground=lambda: True, budget=0.03,
              gate=True, raw="虚构便签"):
        self.epoch += 1
        request_id = self.epoch
        if self.task is not None:
            self.task.cancel()
        self.publish(request_id, Ui(request_id, "CHECKING"))
        self.task = asyncio.create_task(self.run(request_id, factory, is_foreground,
                                                 budget, gate, raw))
        return self.task

    def stop(self):
        if self.task is not None and not self.task.done():
            self.epoch += 1  # 先让旧请求失效，再发送取消
            self.ui = replace(self.ui, state="CANCELLED", notice="仅未完成草稿")
            self.history.append(self.ui)
            self.task.cancel()

    async def run(self, request_id, factory, foreground, budget, gate, raw):
        async with self.lock:  # 新实例等待旧实例finally；不等于设备取消延迟承诺
            if request_id != self.epoch:
                raise asyncio.CancelledError()
            client = None
            local = Ui(request_id, "CHECKING")
            def status(state, notice=""):
                nonlocal local
                local = replace(local, state=state, notice=notice)
                self.publish(request_id, local)
            try:
                if not raw.strip():
                    status("EMPTY_INPUT"); return
                if not gate:
                    status("BLOCKED"); return
                if not foreground():
                    status("FOREGROUND_REQUIRED"); return
                client = factory()
                if await client.check_status() != "AVAILABLE":
                    status("BLOCKED"); return
                async def collect():
                    nonlocal local
                    async for frame in client.stream():
                        if request_id != self.epoch:
                            raise asyncio.CancelledError()
                        if not foreground():
                            status("FOREGROUND_REQUIRED"); return False
                        local = append_frame(local, frame)
                        self.publish(request_id, local)
                    return True
                try:
                    finished = await asyncio.wait_for(collect(), budget)
                except asyncio.TimeoutError:
                    status("GENERATION_TIMEOUT", "仅未完成草稿"); return
                if not foreground():
                    status("FOREGROUND_REQUIRED"); return
                if finished:
                    local = completed(local)
                    self.publish(request_id, local)
            except asyncio.CancelledError:
                status("CANCELLED", "仅未完成草稿")
                raise  # 传播生命周期取消，不转成失败重试
            except Exception:
                status("FAILED", "仅未完成草稿；禁止采纳")
            finally:
                if client is not None:
                    try:
                        client.close()
                    except Exception:
                        self.cleanup_errors += 1  # 不覆盖原始失败/取消


async def main():
    client = FakeClient([Frame("哈"), Frame("哈"), Frame("！", "STOP")])
    controller = Controller()
    await controller.start(lambda: client)
    print("Host固定输出：", controller.ui)
    print("状态：", " -> ".join(ui.state for ui in controller.history))
    print("生命周期：", " -> ".join(client.events))
    print("可采纳：", controller.ui.can_accept, "；端侧推理/usage/性能：未测")


if __name__ == "__main__":
    asyncio.run(main())
