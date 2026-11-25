"""Host 模拟能力门禁 fixture：不连接手机，不查询 SDK，不联网。"""
from dataclasses import dataclass, replace
from enum import Enum


class Feature(str, Enum):
    # 前四项对应官方 FeatureStatus 的语义；后两项是应用自己的状态。
    AVAILABLE = "AVAILABLE"
    DOWNLOADABLE = "DOWNLOADABLE"
    DOWNLOADING = "DOWNLOADING"
    UNAVAILABLE = "UNAVAILABLE"
    UNKNOWN = "UNKNOWN"
    QUERY_FAILED = "QUERY_FAILED"


class DeviceGate(str, Enum):
    # 应用层环境证据，不是 Google SDK 枚举，也不是芯片白名单。
    OK = "OK"
    BLOCKED = "BLOCKED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class Snapshot:
    feature: Feature
    device_gate: DeviceGate = DeviceGate.OK
    foreground: bool = True
    fresh: bool = True
    online: bool = False
    download_allowed: bool = True
    download_consent: bool = False
    cloud_allowed: bool = False
    cloud_consent: bool = False


@dataclass(frozen=True)
class Decision:
    local: str
    download_advice: str
    cloud_advice: str
    can_attempt_local: bool


def reduce_capability(s: Snapshot) -> Decision:
    """纯函数：只返回 UI 建议，没有下载、云请求或推理副作用。"""
    if s.device_gate == DeviceGate.BLOCKED:
        local = "UNSUPPORTED"
    elif s.device_gate != DeviceGate.OK:
        local = "UNKNOWN"
    elif not s.foreground:
        local = "FOREGROUND_REQUIRED"
    elif not s.fresh:
        local = "STALE"
    else:
        local = {
            Feature.AVAILABLE: "READY",
            Feature.DOWNLOADABLE: "NEED_DOWNLOAD",
            Feature.DOWNLOADING: "DOWNLOADING",
            Feature.UNAVAILABLE: "UNSUPPORTED",
            Feature.QUERY_FAILED: "QUERY_FAILED",
        }.get(s.feature, "UNKNOWN")

    # 有网络不等于允许下载；允许下载也不等于已经得到用户确认。
    download = "NONE"
    if local == "NEED_DOWNLOAD":
        if not s.download_allowed:
            download = "BLOCKED"
        elif not s.online:
            download = "WAIT_NETWORK"
        elif not s.download_consent:
            download = "ASK_CONSENT"
        else:
            download = "OFFER_DOWNLOAD"

    # 即使条件满足也仅建议按钮，不调用云端、不自动计费。
    cloud = "NONE"
    if local != "READY":
        if not s.cloud_allowed:
            cloud = "BLOCKED"
        elif not s.online:
            cloud = "WAIT_NETWORK"
        elif not s.cloud_consent:
            cloud = "ASK_CONSENT"
        else:
            cloud = "OFFER_CLOUD"
    return Decision(local, download, cloud, local == "READY")


def cases():
    base = Snapshot(Feature.AVAILABLE)
    # 每行是独立输入；这里所有状态都是人造 fixture，不是设备实测。
    rows = [
        ("可用且离线", base, ("READY", "NONE", "NONE", True)),
        ("可用且在线", replace(base, online=True),
         ("READY", "NONE", "NONE", True)),
        ("需下载在线未确认", replace(base, feature=Feature.DOWNLOADABLE, online=True),
         ("NEED_DOWNLOAD", "ASK_CONSENT", "BLOCKED", False)),
        ("需下载在线已确认", replace(base, feature=Feature.DOWNLOADABLE,
         online=True, download_consent=True),
         ("NEED_DOWNLOAD", "OFFER_DOWNLOAD", "BLOCKED", False)),
        ("需下载离线", replace(base, feature=Feature.DOWNLOADABLE,
         download_consent=True, cloud_allowed=True, cloud_consent=True),
         ("NEED_DOWNLOAD", "WAIT_NETWORK", "WAIT_NETWORK", False)),
        ("策略禁止下载", replace(base, feature=Feature.DOWNLOADABLE, online=True,
         download_allowed=False, download_consent=True),
         ("NEED_DOWNLOAD", "BLOCKED", "BLOCKED", False)),
        ("正在下载", replace(base, feature=Feature.DOWNLOADING, online=True),
         ("DOWNLOADING", "NONE", "BLOCKED", False)),
        ("不可用允许云建议", replace(base, feature=Feature.UNAVAILABLE, online=True,
         cloud_allowed=True, cloud_consent=True),
         ("UNSUPPORTED", "NONE", "OFFER_CLOUD", False)),
        ("未知且禁止上云", replace(base, feature=Feature.UNKNOWN, online=True),
         ("UNKNOWN", "NONE", "BLOCKED", False)),
        ("查询失败且禁止上云", replace(base, feature=Feature.QUERY_FAILED, online=True),
         ("QUERY_FAILED", "NONE", "BLOCKED", False)),
        ("查询失败未同意上云", replace(base, feature=Feature.QUERY_FAILED,
         online=True, cloud_allowed=True),
         ("QUERY_FAILED", "NONE", "ASK_CONSENT", False)),
        ("不可用离线已同意云", replace(base, feature=Feature.UNAVAILABLE,
         cloud_allowed=True, cloud_consent=True),
         ("UNSUPPORTED", "NONE", "WAIT_NETWORK", False)),
        ("设备环境明确不支持", replace(base, device_gate=DeviceGate.BLOCKED),
         ("UNSUPPORTED", "NONE", "BLOCKED", False)),
        ("设备环境证据未知", replace(base, device_gate=DeviceGate.UNKNOWN),
         ("UNKNOWN", "NONE", "BLOCKED", False)),
        ("可用但快照过期", replace(base, fresh=False),
         ("STALE", "NONE", "BLOCKED", False)),
        ("可用但已离开前台", replace(base, foreground=False),
         ("FOREGROUND_REQUIRED", "NONE", "BLOCKED", False)),
    ]
    return rows


if __name__ == "__main__":
    for name, snapshot, expected in cases():
        actual = reduce_capability(snapshot)
        values = (actual.local, actual.download_advice,
                  actual.cloud_advice, actual.can_attempt_local)
        if values != expected:
            raise AssertionError((name, values, expected))
        print("PASS", name, *values)
    total = len(cases())
    print("PASS 场景表：%d/%d；仅 Host fixture，无 Android 或真机推理" % (total, total))
