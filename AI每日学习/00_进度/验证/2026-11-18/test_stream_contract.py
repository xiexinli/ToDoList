"""Host契约回归：只断言固定事件和应用状态，不测试Android。"""
import asyncio
import unittest
from stream_contract import Controller, FakeClient, Frame, Ui, append_frame


class StreamTest(unittest.IsolatedAsyncioTestCase):
    async def check(self, frames, expected, draft, **kwargs):
        c, vm = FakeClient(frames, **kwargs), Controller()
        await vm.start(lambda: c)
        self.assertEqual((vm.ui.state, vm.ui.draft), (expected, draft))
        self.assertEqual(vm.ui.can_accept, expected == "SUCCESS" and bool(draft.strip()))
        self.assertEqual(c.events.count("close"), 1)
        return vm, c

    async def test_partitions_and_repeated_words(self):
        for frames in [[Frame("哈"), Frame("哈"), Frame("！", "STOP")],
                       [Frame("哈哈！", "STOP")],
                       [Frame(""), Frame("哈哈"), Frame("！"), Frame("", "STOP")]]:
            await self.check(frames, "SUCCESS", "哈哈！")

    async def test_whitespace_preserved(self):
        await self.check([Frame("A "), Frame("B", "STOP")], "SUCCESS", "A B")

    async def test_explicit_cumulative_not_append(self):
        u = Ui()
        for f in [Frame("哈"), Frame("哈哈"), Frame("哈哈！", "STOP")]:
            u = append_frame(u, f, "CUMULATIVE")
        self.assertEqual(u.draft, "哈哈！")
        with self.assertRaises(ValueError):
            append_frame(Ui(), Frame("x"), "GUESS")

    async def test_finish_table(self):
        for reason, status in [("MAX_TOKENS", "TRUNCATED"), ("OTHER", "INCOMPLETE"),
                               ("FUTURE_REASON", "INCOMPLETE"), (None, "INCOMPLETE")]:
            await self.check([Frame("未完", reason)], status, "未完")

    async def test_empty_and_null(self):
        for frames, state, draft in [([], "INCOMPLETE", ""),
                                    ([Frame("  ", "STOP")], "EMPTY_RESULT", "  "),
                                    ([Frame(None, "STOP")], "EMPTY_RESULT", ""),
                                    ([Frame("", "MAX_TOKENS")], "TRUNCATED", "")]:
            await self.check(frames, state, draft)

    async def test_terminal_then_extra_is_invalid(self):
        await self.check([Frame("结束", "STOP"), Frame("多余")], "FAILED", "结束")

    async def test_failure_keeps_unacceptable_draft(self):
        await self.check([Frame("已有草稿")], "FAILED", "已有草稿", fail=True)

    async def test_stop_marker_then_failure_not_success(self):
        await self.check([Frame("已见结束", "STOP")], "FAILED", "已见结束", fail=True)

    async def test_timeout_after_draft(self):
        vm, c = await self.check([Frame("半句")], "GENERATION_TIMEOUT", "半句", wait=True)
        self.assertIn("cancel_received", c.events)

    async def test_user_cancel_propagates(self):
        c, vm = FakeClient([Frame("草稿")], wait=True), Controller()
        task = vm.start(lambda: c, budget=5)
        await asyncio.wait_for(c.ready.wait(), 1)
        vm.stop()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertEqual((vm.ui.state, vm.ui.draft), ("CANCELLED", "草稿"))
        self.assertFalse(vm.ui.can_accept)
        self.assertTrue(c.closed)

    async def test_parent_cancel_propagates(self):
        c, vm = FakeClient(wait=True), Controller()
        task = vm.start(lambda: c, budget=5)
        await asyncio.wait_for(c.ready.wait(), 1)
        task.cancel()  # 模拟ViewModel清理取消父任务
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertEqual(vm.ui.state, "CANCELLED")
        self.assertTrue(c.closed)

    async def test_page_pause_foreground_and_dispose(self):
        for event in ["ON_PAUSE", "onDispose", "ON_DESTROY"]:
            c, vm = FakeClient(wait=True), Controller()
            task = vm.start(lambda: c, budget=5)
            await asyncio.wait_for(c.ready.wait(), 1)
            vm.stop()  # 仅模拟事件对应动作，不证明Android真实事件顺序
            with self.assertRaises(asyncio.CancelledError):
                await task
            self.assertTrue(c.closed, event)

    async def test_foreground_lost_during_stream(self):
        checks = iter([True, False, False])
        c, vm = FakeClient([Frame("不得发布", "STOP")]), Controller()
        await vm.start(lambda: c, is_foreground=lambda: next(checks))
        self.assertEqual(vm.ui.state, "FOREGROUND_REQUIRED")
        self.assertEqual(vm.ui.draft, "")
        self.assertTrue(c.closed)

    async def test_replacement_blocks_stale_and_serializes_release(self):
        old = FakeClient([Frame("旧")], wait=True, stubborn=True)
        new, vm = FakeClient([Frame("新", "STOP")]), Controller()
        first = vm.start(lambda: old, budget=5)
        await asyncio.wait_for(old.ready.wait(), 1)
        def factory():
            self.assertTrue(old.closed, "新实例必须在旧close之后创建")
            return new
        second = vm.start(factory)
        with self.assertRaises(asyncio.CancelledError):
            await first
        await second
        self.assertEqual((vm.ui.state, vm.ui.draft), ("SUCCESS", "新"))
        self.assertFalse(vm.publish(1, Ui(1, "SUCCESS", "旧结果")))
        self.assertEqual(vm.ui.draft, "新")
        self.assertTrue(old.closed and new.closed)

    async def test_cleanup_failure_does_not_mask_original(self):
        vm, c = await self.check([Frame("草稿")], "FAILED", "草稿", fail=True, close_error=True)
        self.assertEqual(vm.cleanup_errors, 1)
        self.assertFalse(c.closed)  # 不能因尝试close就声称资源已释放
        c, vm = FakeClient(wait=True, close_error=True), Controller()
        task = vm.start(lambda: c, budget=5)
        await asyncio.wait_for(c.ready.wait(), 1)
        vm.stop()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertEqual(vm.cleanup_errors, 1)
        self.assertEqual(vm.ui.state, "CANCELLED")

    async def test_preflight_no_client(self):
        for options, expected in [({'raw':' '},'EMPTY_INPUT'), ({'gate':False},'BLOCKED'),
                                  ({'is_foreground':lambda:False},'FOREGROUND_REQUIRED')]:
            vm = Controller()
            def forbidden():
                self.fail("不应创建客户端")
            await vm.start(forbidden, **options)
            self.assertEqual(vm.ui.state, expected)

    async def test_unavailable_closes_without_stream(self):
        c, vm = FakeClient(feature="UNAVAILABLE"), Controller()
        await vm.start(lambda: c)
        self.assertEqual(vm.ui.state, "BLOCKED")
        self.assertEqual(c.events, ["create", "check", "close"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
