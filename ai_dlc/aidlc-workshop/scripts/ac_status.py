#!/usr/bin/env python3
"""把测试结果按 EARS 的 AC-xx 归类，输出状态表（Markdown）。支持 pytest 文本输出与 Vitest JSON。

pytest：
  uv run pytest -q --color=no -rA --tb=no | python <skill>/scripts/ac_status.py [requirements.md]
Vitest：
  npx vitest run --reporter=json --outputFile=.kiro/specs/<feature>/vitest.json ; \
  python <skill>/scripts/ac_status.py [requirements.md] < .kiro/specs/<feature>/vitest.json

规则：
- 测试名（pytest nodeid 最后一段 / Vitest fullName）中出现 `ac_07` / `ac07` / `AC-07`（大小写不敏感）即归到 AC-07。
- 一条 AC 有任一测试失败 → FAIL；全部通过 → PASS；有 skip/todo 混入 → PARTIAL；无测试 → TODO。
- 若给了 requirements.md 路径，会读出所有 `| AC-xx | 类型 | 优先级 |` 行，补上没有测试的 AC，并按 P0 统计。
"""
import json
import re
import sys
from collections import defaultdict

PYTEST_LINE = re.compile(r"^(PASSED|FAILED|ERROR|SKIPPED|XFAIL|XPASS)\s+(\S+)", re.M)
ACID = re.compile(r"ac[_-]?(\d{2})", re.I)
REQ = re.compile(r"^\|\s*(AC-\d{2})\s*\|\s*([^|]+?)\s*\|\s*(P[0-2])!?\s*\|", re.M)  # P0! 红线也算 P0
VITEST_STATUS = {"passed": "PASSED", "failed": "FAILED", "skipped": "SKIPPED", "pending": "SKIPPED", "todo": "SKIPPED"}


def parse(text: str):
    """返回 [(status, name)]。"""
    stripped = text.lstrip()
    if stripped.startswith("{"):
        data = json.loads(stripped)
        out = []
        for f in data.get("testResults", []):
            for a in f.get("assertionResults", []):
                out.append((VITEST_STATUS.get(a.get("status"), "FAILED"), a.get("fullName") or a.get("title", "")))
        return out
    return [(s, n.split("::")[-1]) for s, n in PYTEST_LINE.findall(text)]


def main() -> int:
    results = defaultdict(list)  # AC-xx -> [(status, name)]
    for status, name in parse(sys.stdin.read()):
        m = ACID.search(name)
        if m:
            results[f"AC-{m.group(1)}"].append((status, name))

    prio = {}
    if len(sys.argv) > 1:
        try:
            for ac, _typ, p in REQ.findall(open(sys.argv[1], encoding="utf-8").read()):
                prio[ac] = p
        except OSError as e:
            print(f"warn: cannot read {sys.argv[1]}: {e}", file=sys.stderr)

    rows, passed, total, p0_pass, p0_total = [], 0, 0, 0, 0
    for ac in sorted(set(results) | set(prio)):
        tests = results.get(ac, [])
        if not tests:
            st = "TODO"
        elif any(s in ("FAILED", "ERROR") for s, _ in tests):
            st = "FAIL"
        elif all(s == "PASSED" for s, _ in tests):
            st = "PASS"
        else:
            st = "PARTIAL"
        total += 1
        passed += st == "PASS"
        p = prio.get(ac, "?")
        if p == "P0":
            p0_total += 1
            p0_pass += st == "PASS"
        names = "<br>".join(n for _, n in tests) or "—"
        rows.append(f"| {ac} | {p} | {len(tests)} | {names} | {st} |")

    print(f"**通过 {passed} / 总 {total} 条 EARS（P0：{p0_pass} / {p0_total}）**\n")
    print("| AC | 优先级 | 测试数 | 测试名 | 状态 |")
    print("|---|---|---|---|---|")
    print("\n".join(rows))
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
