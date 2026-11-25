"""合成单调时序fixture统计器：Host可运行；不是Nano性能实测。"""
import json
import math
from collections import Counter
from dataclasses import dataclass, asdict
from typing import Optional


@dataclass(frozen=True)
class Event:
    kind: str
    ns: int  # 调用者注入同一单调时钟域的纳秒；fixture值纯合成
    text: Optional[str] = None
    reason: Optional[str] = None
    outcome: Optional[str] = None


@dataclass(frozen=True)
class Sample:
    origin: str
    conditions: str
    status: str
    valid: bool
    first_ns: Optional[int] = None
    marker_ns: Optional[int] = None
    ttft_request_ms: Optional[float] = None
    ttft_generation_ms: Optional[float] = None
    observed_request_ms: Optional[float] = None
    observed_generation_ms: Optional[float] = None
    complete_request_ms: Optional[float] = None
    complete_generation_ms: Optional[float] = None
    issue: str = ""


def analyse(events, origin="SYNTHETIC_FIXTURE", conditions="固定条件示例"):
    """NORMAL指collect正常返回，不能只用最后一个finishReason代替它。"""
    def invalid(message):
        return Sample(origin, conditions, "INVALID", False, issue=message)
    if origin not in ("SYNTHETIC_FIXTURE", "ANDROID_ELAPSED_REALTIME_NS"):
        return invalid("未知时钟来源；拒绝墙钟或Host测量混入")
    if (len(events) < 2 or events[0].kind != "request"
            or events[-1].kind != "end"):
        return invalid("缺少请求起点或观察终点")
    if any(type(e.ns) is not int or e.ns < 0 for e in events):
        return invalid("时间必须为非负整数纳秒")
    if any(a.ns > b.ns for a, b in zip(events, events[1:])):
        return invalid("时间倒退；不截成0、不参与分位数")
    request = events[0].ns
    generation = first = marker = reason = None
    for e in events[1:-1]:
        if e.kind == "generation":
            if generation is not None:
                return invalid("重复生成起点")
            generation = e.ns
        elif e.kind == "frame":
            if generation is None or marker is not None:
                return invalid("正文在生成前或终帧后出现")
            if e.text is not None and not isinstance(e.text, str):
                return invalid("正文类型错误")
            if e.reason is not None and not isinstance(e.reason, str):
                return invalid("结束原因类型错误")
            # 空串、null、纯空白不是有效首字；不去重，不记录正文/思考过程。
            if first is None and (e.text or "").strip():
                first = e.ns  # 最终帧的正文也必须检查
            if e.reason is not None:
                marker, reason = e.ns, e.reason
        else:
            return invalid("未知或重复边界事件")
    outcome, end = events[-1].outcome, events[-1].ns
    if outcome not in ("NORMAL", "ERROR", "CANCELLED", "TIMEOUT", "REJECTED"):
        return invalid("未知观察终态")
    if generation is None:
        if outcome == "NORMAL":
            return invalid("未开始生成不能正常完成")
        # 门禁前拒绝/异常/取消/超时都可能出现；只记录请求观察跨度。
        return Sample(origin, conditions, outcome, True,
                      observed_request_ms=(end-request)/1_000_000)
    if outcome == "REJECTED":
        return invalid("生成后不能伪称前置拒绝")
    if outcome != "NORMAL":
        status = outcome  # 即使见过STOP，之后异常/取消/超时也不是成功
    elif reason == "MAX_TOKENS":
        status = "TRUNCATED"
    elif reason != "STOP":
        status = "INCOMPLETE"
    else:
        status = "SUCCESS" if first is not None else "EMPTY_RESULT"
    ms = lambda a, b: None if a is None or b is None else (a-b)/1_000_000
    success = status == "SUCCESS"
    return Sample(origin, conditions, status, True, first, marker,
                  ms(first, request), ms(first, generation),
                  ms(end, request), ms(end, generation),
                  ms(end, request) if success else None,
                  ms(end, generation) if success else None)


def percentile(values, p):
    """nearest-rank；p50也用同一算法，不假装为两中值平均数。"""
    if not 0 < p <= 1:
        raise ValueError("分位点必须在(0,1]")
    if not values:
        return None
    if any(not math.isfinite(v) or v < 0 for v in values):
        raise ValueError("无效时长")
    return sorted(values)[math.ceil(len(values)*p)-1]


def summarize(samples):
    # 必须先按来源和全部条件分组，禁止冷热或合成/真机混合。
    groups = {(s.origin, s.conditions) for s in samples}
    if len(groups) > 1:
        raise ValueError("先按同来源/同条件分组，再统计")
    successful = [s for s in samples if s.valid and s.status == "SUCCESS"]
    metrics = {}
    for key in ("ttft_request_ms", "ttft_generation_ms",
                "complete_request_ms", "complete_generation_ms"):
        values = [getattr(s, key) for s in successful]
        metrics[key] = {"n": len(values), "p50": percentile(values, .5),
                        "p95": percentile(values, .95)}
    n = len(successful)
    return {"group": next(iter(groups), None), "attempts": len(samples),
            "statuses": dict(Counter(s.status for s in samples)),
            "success_rate": n/len(samples) if samples else None,
            "successful_n": n, "metrics": metrics,
            "warning": "无成功样本，分位数为null" if not n else
                       "成功样本少于20，p95仅描述本组，尾延迟证据不足" if n < 20 else
                       "分位数为样本描述，不保证统计置信度；仍报告条件与失败数"}


def fixture():
    """全是合成纳秒；两个相同字合法，最终帧也含正文。"""
    return [Event("request", 0), Event("generation", 100_000_000),
            Event("frame", 120_000_000, ""),
            Event("frame", 140_000_000, " \n"),
            Event("frame", 350_000_000, "哈"),
            Event("frame", 400_000_000, "哈"),
            Event("frame", 700_000_000, "！", "STOP"),
            Event("end", 710_000_000, outcome="NORMAL")]


if __name__ == "__main__":
    sample = analyse(fixture())
    print("来源：SYNTHETIC_FIXTURE；合成时间仅校验公式，不是Nano性能")
    print(json.dumps(asdict(sample), ensure_ascii=False, sort_keys=True))
    print(json.dumps(summarize([sample]), ensure_ascii=False, sort_keys=True))
    print("模型调用=0；真实输出tokens/usage=NOT_MEASURED；tokens/s不计算")
