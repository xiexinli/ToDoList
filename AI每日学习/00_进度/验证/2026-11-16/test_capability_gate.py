"""确定性场景和组合不变量；标准库测试，不调用 Android。"""
import itertools
import unittest
from capability_gate import (Snapshot, Feature, DeviceGate, cases, reduce_capability)


class CapabilityTests(unittest.TestCase):
    def test_exact_fixtures(self):
        for name, snapshot, expected in cases():
            with self.subTest(name=name):
                d = reduce_capability(snapshot)
                self.assertEqual((d.local, d.download_advice,
                                  d.cloud_advice, d.can_attempt_local), expected)

    def test_all_2304_combinations(self):
        # 六种 feature × 三种设备状态 × 七个布尔字段 = 2304。
        count = 0
        for feature, device, bits in itertools.product(
                list(Feature), list(DeviceGate), itertools.product((False, True), repeat=7)):
            fg, fresh, online, da, dc, ca, cc = bits
            s = Snapshot(feature, device, fg, fresh, online, da, dc, ca, cc)
            d = reduce_capability(s)
            with self.subTest(snapshot=s):
                self.assertEqual(d, reduce_capability(s))
                self.assertEqual(d.can_attempt_local,
                    device == DeviceGate.OK and fg and fresh and feature == Feature.AVAILABLE)
                self.assertEqual(d.cloud_advice == "OFFER_CLOUD",
                    d.local != "READY" and online and ca and cc)
                self.assertEqual(d.download_advice == "OFFER_DOWNLOAD",
                    d.local == "NEED_DOWNLOAD" and online and da and dc)
                if not ca and d.local != "READY":
                    self.assertEqual(d.cloud_advice, "BLOCKED")
                if d.local == "DOWNLOADING":
                    self.assertEqual(d.download_advice, "NONE")
            count += 1
        self.assertEqual(count, 2304)
        print("PASS 2304 组合：确定性、端侧门禁、下载授权、云授权不变量")

    def test_future_or_bad_feature_is_unknown(self):
        d = reduce_capability(Snapshot("NEW_FUTURE_STATUS"))
        self.assertEqual(d.local, "UNKNOWN")
        self.assertFalse(d.can_attempt_local)


if __name__ == "__main__":
    unittest.main(verbosity=2)
