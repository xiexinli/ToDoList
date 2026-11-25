"""所有时间都是注入的合成值；测试运行耗时也不是Nano性能。"""
import unittest
from dataclasses import replace
from latency_meter import Event as E, analyse, fixture, percentile, summarize


def seq(frames=(), outcome="NORMAL", gen=True):
    start=[E("request",0)] + ([E("generation",100)] if gen else [])
    return start + list(frames) + [E("end",1000,outcome=outcome)]


class MeterTests(unittest.TestCase):
    def test_formula_boundaries(self):
        s=analyse(fixture())
        self.assertEqual((s.ttft_request_ms,s.ttft_generation_ms), (350,250))
        self.assertEqual((s.complete_request_ms,s.complete_generation_ms),(710,610))
        self.assertEqual(s.marker_ns,700_000_000)
    def test_empty_and_whitespace_do_not_count(self):
        for t in (None,""," \n\t"):
            s=analyse(seq([E("frame",200,t),E("frame",500,"字","STOP")]))
            self.assertEqual(s.first_ns,500)
    def test_metadata_only_no_first(self):
        s=analyse(seq([E("frame",500,None,"STOP")]))
        self.assertEqual(s.status,"EMPTY_RESULT"); self.assertIsNone(s.first_ns)
    def test_final_frame_body_counts(self):
        s=analyse(seq([E("frame",500,"字","STOP")]))
        self.assertEqual((s.status,s.first_ns), ("SUCCESS",500))
    def test_repeated_delta_legal(self):
        s=analyse(seq([E("frame",200,"哈"),E("frame",300,"哈","STOP")]))
        self.assertEqual((s.status,s.first_ns),("SUCCESS",200))
    def test_equal_timestamps_allowed(self):
        self.assertEqual(analyse(seq([E("frame",100,"字","STOP")])).status,"SUCCESS")
    def test_stop_not_complete_until_eof(self):
        s=analyse(seq([E("frame",500,"字","STOP")]))
        self.assertEqual(s.complete_generation_ms, .0009)
    def test_truncated_with_or_without_body(self):
        for t in ("字",None):
            s=analyse(seq([E("frame",500,t,"MAX_TOKENS")]))
            self.assertEqual(s.status,"TRUNCATED"); self.assertIsNone(s.complete_request_ms)
    def test_missing_unknown_and_other_reason(self):
        for r in (None,"OTHER","UNKNOWN"):
            self.assertEqual(analyse(seq([E("frame",500,"字",r)])).status,"INCOMPLETE")
    def test_empty_stream(self):
        self.assertEqual(analyse(seq()).status,"INCOMPLETE")
    def test_error_after_first(self):
        s=analyse(seq([E("frame",300,"字")],"ERROR"))
        self.assertEqual(s.status,"ERROR"); self.assertIsNotNone(s.ttft_generation_ms)
        self.assertIsNone(s.complete_generation_ms)
    def test_stop_then_abnormal(self):
        for o in ("ERROR","CANCELLED","TIMEOUT"):
            self.assertEqual(analyse(seq([E("frame",300,"字","STOP")],o)).status,o)
    def test_cancel_timeout_no_first(self):
        for o in ("CANCELLED","TIMEOUT"):
            s=analyse(seq(outcome=o)); self.assertIsNone(s.first_ns)
            self.assertEqual(s.status,o); self.assertEqual(s.observed_generation_ms,.0009)
    def test_time_backwards_quarantined(self):
        s=analyse(seq([E("frame",99,"字","STOP")]))
        self.assertFalse(s.valid); self.assertIsNone(s.ttft_request_ms)
    def test_bad_ns(self):
        for n in (-1,True,1.2):
            self.assertFalse(analyse([E("request",n),E("end",100,outcome="REJECTED")]).valid)
    def test_missing_or_duplicate_boundaries(self):
        cases=[[],[E("request",0)],seq([E("generation",200)]),
               seq([E("request",200)]),seq([E("end",200,outcome="NORMAL")])]
        for events in cases: self.assertFalse(analyse(events).valid)
    def test_frame_before_generation(self):
        self.assertFalse(analyse(seq([E("frame",500,"字")],gen=False)).valid)
    def test_frame_after_marker(self):
        self.assertFalse(analyse(seq([E("frame",300,"字","STOP"),E("frame",500,"")])).valid)
    def test_rejection_before_generation(self):
        s=analyse(seq(gen=False,outcome="REJECTED"))
        self.assertEqual(s.status,"REJECTED"); self.assertIsNone(s.observed_generation_ms)
        self.assertFalse(analyse(seq(outcome="REJECTED")).valid)
        for outcome in ("ERROR","CANCELLED","TIMEOUT"):
            early=analyse(seq(gen=False,outcome=outcome))
            self.assertEqual(early.status,outcome)
            self.assertTrue(early.valid)
            self.assertIsNone(early.observed_generation_ms)
            self.assertIsNone(early.complete_request_ms)
    def test_bad_outcome_and_types(self):
        self.assertFalse(analyse(seq(outcome="EOF")).valid)
        for e in (E("frame",300,123),E("frame",300,"字",123),E("mystery",300)):
            self.assertFalse(analyse(seq([e])).valid)
    def test_non_success_stats_isolated(self):
        ok=analyse(fixture())
        others=[analyse(seq(outcome=o)) for o in ("ERROR","TIMEOUT","CANCELLED")]
        others += [analyse(seq([E("frame",300,"字","MAX_TOKENS")])),
                   analyse(seq([E("frame",300,None,"STOP")])),
                   analyse(seq([E("frame",99,"字")]))]
        out=summarize([ok]+others)
        self.assertEqual(out["successful_n"],1); self.assertEqual(out["attempts"],7)
        self.assertEqual(out["metrics"]["complete_request_ms"]["p95"],710)
    def test_percentile_zero_one_and_small(self):
        self.assertIsNone(percentile([], .95)); self.assertEqual(percentile([3],.95),3)
        self.assertEqual(percentile([4,1,2,3], .5),2)
        self.assertEqual(percentile(list(range(1,21)), .95),19)
        self.assertIn("少于20",summarize([analyse(fixture())])["warning"])
    def test_zero_or_no_success_summary(self):
        for rows in ([],[analyse(seq(outcome="TIMEOUT"))]):
            out=summarize(rows); self.assertEqual(out["successful_n"],0)
            self.assertIsNone(out["metrics"]["complete_request_ms"]["p95"])
        self.assertIsNone(summarize([])["success_rate"])
    def test_invalid_percentile(self):
        for p in (0,-1,1.1):
            with self.assertRaises(ValueError): percentile([1],p)
        for values in ([float("nan")],[float("inf")],[-1]):
            with self.assertRaises(ValueError): percentile(values,.5)
    def test_sources_and_conditions_not_mixed(self):
        s=analyse(fixture())
        for changed in (replace(s,origin="ANDROID_ELAPSED_REALTIME_NS"),replace(s,conditions="另一冷态")):
            with self.assertRaises(ValueError): summarize([s,changed])
        self.assertFalse(analyse(fixture(),origin="WALL_CLOCK").valid)
    def test_subtract_before_float(self):
        large=10**18
        s=analyse([E("request",large),E("generation",large+1),
                   E("frame",large+2,"字","STOP"),E("end",large+3,outcome="NORMAL")])
        self.assertEqual(s.ttft_request_ms,.000002)


if __name__ == "__main__": unittest.main(verbosity=2)
