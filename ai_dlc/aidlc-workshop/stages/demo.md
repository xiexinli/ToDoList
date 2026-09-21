# 阶段 3：`aidlc demo`（收口与演示）

目标：20 分钟内准备好分享材料：Spec 展示、追溯演示、通过率、未完成与跟进。

## Step 1 全量验证与通过率

Vitest 栈：
```bash
npm run test:json   # vitest run --reporter=json --outputFile=.kiro/specs/<feature>/vitest.json
python <skill目录>/scripts/ac_status.py .kiro/specs/<feature>/requirements.md < .kiro/specs/<feature>/vitest.json
npm run typecheck && npm run lint
```
pytest 栈：
```bash
uv run pytest -q --color=no -rA --tb=no | tee .kiro/specs/<feature>/test-report.txt \
  | python <skill目录>/scripts/ac_status.py .kiro/specs/<feature>/requirements.md
```
- 脚本按测试名中的 `AC-xx` 归类，输出 `通过 X / 总 Y 条 EARS（P0：a / b）` 和每条 AC 的状态表。**通过率按 AC 条数计，不按测试数。**
- 以脚本结果为准刷新 `traceability.md` 的状态列（不信任旧记录），把汇总行写到顶部。
- 其他栈：按同样规则手工归类，测试名里必须有 AC ID。
- demo 前 checklist：dev 服务已关；`data/` 里有一份演示用的产物/会话；live 输出文件存在（Agent 类）；`vitest.json` 是最新的；`typecheck`/`lint` 通过。

## Step 2 追溯演示准备

- 挑 **2 条** AC：一条正常流、一条 Unwanted 异常流。**优先 P0；P1 若更能体现价值（如冲突处理、守则拦截）也可选。**
- 对每条写出三跳：`EARS 语句 → 测试文件::函数（贴 5 行断言）→ 实现文件:函数（贴 5–10 行）`。
- 给出现场可执行的命令：只跑这条 AC 的测试（Vitest `npx vitest run -t "AC-07"`；pytest `uv run pytest -k ac_07 -v`），以及 `grep -rn "Implements: AC-07" src/`；最后在页面上操作一遍对应场景。

## Step 3 原型演示

- 确认一条命令能跑通原型（CLI 例：`uv run <entry> --help` 与一个真实输入的例子）。
- 演示输入优先用客户材料里的真实样本；Agent 类课题若有 `live` 评估，只现场演示 1 条，其余展示 `live-eval.txt`。
- 记下预期输出文本（大屏演示失败时可读）。

## Step 4 写 DEMO.md（用 `templates/DEMO.md`）

包含：① Spec 展示要点（EARS 总数、P0 数、任务拆解概览）② 追溯演示两条 ③ 测试结果（通过率 + 命令）④ 未完成项（每项：AC、原因、预计工时）⑤ 会后跟进（synthetic 样本替换为真实数据、可选的纯静态 Web 入口、接真实接口/模型时测试不变）⑥ 15 分钟分享时间分配。

## Step 5 复盘三行

"这套方法今天哪里顺、哪里卡、下次怎么改"，追加到 DEMO.md 末尾；把 `timeline.md` 的各阶段耗时也贴进去，供导师点评和 skill 迭代。
