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
