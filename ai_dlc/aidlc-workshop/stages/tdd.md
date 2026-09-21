# 阶段 2：`aidlc tdd`（Construction）

目标：按 `tasks.md` 顺序，用 TDD 把每条 `AC-xx` 变成一个真的先红后绿的测试，同时维护 `traceability.md`。下午 180 分钟。

先读 `references/tdd-rules.md`。

## 前置检查

1. `requirements.md`、`design.md`、`tasks.md` 存在且文件头状态为已批准。
2. 读 `traceability.md`（没有就用 `templates/traceability.md` 创建，把所有 AC 填成 `TODO`）。
3. 按栈选模板目录：`templates/ts/`（Vitest/Next）或 `templates/py/`（pytest）。

## T0：从零脚手架（先于任何功能代码）

- 打卡开始时间。**逐条执行** design.md §5 记录的命令（脚手架、装测试框架、装依赖、typegen、建目录）。不要凭记忆改命令；命令失败就修 design.md 再执行，让文档与现实一致。
- 复制对应模板：`vitest.config.ts`（或 `conftest.py`），加 `test / test:json / test:live / typecheck / lint` 脚本。
- 写 1 条 smoke 测试 + SDK 探针脚本（读一次客户样本 / MCP 进程内列工具 / Bedrock 一句），跑通。
- 起一次 dev 服务确认首页 200，然后关掉。
- 完成定义：测试、typecheck、lint、dev 首页、探针五项全过。记录实际用时（这是导师最关心的数字）。**没有可运行的测试命令之前不写任何功能代码。**
- 网络导致 npm 安装超过 15 分钟：告知人，可改用导师提供的兜底脚手架，并在 DEMO.md 复盘里写明。

## 每个任务的 Bolt 循环

对 `tasks.md` 中下一个"依赖已完成"的任务：

### 1. 开工（interactive 输出 3 行；yolo 不输出）
任务 ID/标题、覆盖的 AC 列表、打算写哪些测试。

### 2. Red
- 为该任务每条 AC 写 ≥ 1 个测试。**命名必须含 AC ID**（规范见 tdd-rules）：pytest `test_ac_07_*` + `@pytest.mark.ac("AC-07")`；参数化用 `pytest.param(..., marks=pytest.mark.ac("AC-07"), id="ac_07-…")`。
- 测试断言直接对应 EARS 的 SHALL 子句；fixture 复用 design.md 测试策略里的 fake 与样本。
- 运行测试命令，**确认新测试失败**。若整个文件因 `ImportError` 无法收集，允许先补空模块/空函数签名（不含逻辑）让测试可收集，以取得**每条 AC 独立的**失败摘要（`assert …` / `NotImplementedError`）。
- 把失败摘要（一行）记到 traceability 的"Red 证据"列。
- 不要在 `describe` 顶层或 `beforeAll` 里调用被测函数：它一抛错整个文件就是 "no tests / all skipped"，拿不到每条 AC 的独立红证据。被测调用放在各 `it` 里。
- 若新测试直接通过：先怀疑测试没测到 SHALL，修正后再跑；确实已被前序任务实现的，Red 证据写 `已被 Tn 覆盖`，状态照常 PASS。

### 3. Green
- 写**让当前红测试通过的最小实现**，不顺手做后面任务的事。
- 运行**全量**测试，全绿才算完成；跑红了先修。

### 4. Refactor
- 只在全绿下重构；重构后再跑一遍。

### 5. 记录
- 更新 `traceability.md`：每条 AC 一行 `AC | 优先级 | 测试数 | 测试（文件::函数）| 实现（文件:函数/类）| Red 证据 | 状态`。
- 在实现代码关键函数 docstring/注释里写 `Implements: AC-07, AC-08`（追溯演示时能 grep 到）。
- 在 `tasks.md` 勾选 `[x]` 并写实际用时（只记用时，证据不重复写）。

### 6. 汇报与门禁
- 一行汇报：`T3 完成 | 新增测试 4 | 全量 12/12 | ~35min | TODO 0`（interactive 每任务；yolo 只在集成检查点与结尾）。
- interactive：**在集成检查点任务和最后一个任务之后停下**等人看；普通任务连续做，人插话就停。

## 集成检查点任务（Web MVP 版）

- 不要求"新红"。操作：
  1. 后台起服务：`(nohup npm run dev -- -p 3100 > /tmp/dev.log 2>&1 &)`，轮询 `curl -s -o /dev/null -w "%{http_code}" http://localhost:3100/` 到 200（端口被占就换一个）。
  2. 用 curl 走真实 API：主流程 1 次（客户真实样本）、异常流 1 次（脏样本 / 未知 id / 缺文件）。
  3. Agent 类课题且有凭证：再走 1 次真实模型（`llm=real`），把回复存 `.kiro/specs/<feature>/demo-live.txt`；无凭证则注明。
  4. 关服务：`fuser -k 3100/tcp`（**不要用 `pkill -f`，会误杀自己的 shell**）。
  5. 把每次的 `e2e: <命令> → <关键输出>` 写进 traceability 对应 AC 的 Red 证据列。
- **纯前端拓扑（P）版**：① `npm run build` 通过，`npx vite preview --port 4173` 起静态站，curl 首页 200；② Node 侧用同一份 lib 跑一次主流程（证明浏览器代码路径在 Node 同样成立；Agent 类用 `aws configure export-credentials --format env` 导出的临时凭证显式传给适配器）；③ 若 `~/.cache/ms-playwright` 有 chromium，用 `npx -y playwright@latest` 跑最小脚本（模板 `templates/ts/e2e-browser-upload.mjs` 或 `e2e-browser-chat.mjs`）：打开页面 → 操作主流程 → 断言页面结果 → 截图存 `.kiro/specs/<feature>/demo-browser.png`，同时记录 console 报错、失败请求、CORS；没有 chromium 就注明并只做 ①②；④ `fuser -k 4173/tcp`。页面接线任务要排在集成检查点**之前**，否则浏览器检查点跑不起来。
- 若端到端暴露缺口，就地写一个能复现的红测试再修，这才是它的价值。
- 完成定义除测试外还要 `typecheck` 与 `lint` 通过（Next 16 的 lint 是 error 级，拖到演示前才发现会很疼）。

## 卡住怎么办

- **一次失败** = 一次"修改实现 + 全量运行"仍未绿。同一任务连续 **3 次** 失败：停下。写出失败输出、你的判断、两个候选方案。interactive 等人；yolo 把该 AC 标 `TODO(blocked: 原因)`，跳到下一个不依赖它的任务。
- 外部 SDK 报错（版本漂移、参数弃用）：修实现或 pin 版本，**不动测试**；在 design.md 技术选型处记一行。
- EARS 条目本身有问题（不可测、自相矛盾）：**不要偷改测试凑合**。在 requirements.md 开放问题里记录，traceability 标 `NEEDS-SPEC-CHANGE`；interactive 立刻问人。
- 需要新验收条目：新增 `AC-xx`（顺延编号，标注"TDD 阶段新增"），同样先红后绿。

## 阶段结束

- 跑一次全量测试并贴结果；`live` 评估（如有）只跑一次并把输出存到 `.kiro/specs/<feature>/live-eval.txt`。
- 输出：PASS / TODO / NEEDS-SPEC-CHANGE 各多少条，剩余任务，T0 实际用时，建议进入 `aidlc demo`；打卡 timeline.md；yolo 下把本阶段"若交互我会问的问题"追加到 `questions.md` 末尾小节。
