---
name: aidlc-workshop
description: AI-DLC 一日 workshop 流程：从任务卡出发，用 EARS 写验收标准、产出 Spec（requirements/design/tasks），再用 TDD 逐条转绿并生成可追溯的演示材料。当用户提到 aidlc、spec、EARS、验收标准、TDD、任务拆解、追溯矩阵、demo 收口，或说 "aidlc spec" / "aidlc tdd" / "aidlc demo" 时使用。
license: MIT-0
metadata:
  author: AWS ProServe / DHGate Workshop
  version: "0.8.0"
---

# AI-DLC Workshop Skill

一天之内把一张任务卡变成"有 Spec、有测试、能追溯、能演示"的原型。三个阶段、三个命令：

| 命令 | 阶段（AI-DLC） | 产物 | 何时用 | 门禁 |
|---|---|---|---|---|
| `aidlc spec` | Inception | `requirements.md`（EARS 清单）、`design.md`、`tasks.md` | 上午 | 2 道：批准需求、批准设计+任务 |
| `aidlc tdd` | Construction | 测试 + 实现 + `traceability.md` | 下午 | 集成检查点与结尾 |
| `aidlc demo` | 收口 | `DEMO.md`、通过率、追溯演示脚本 | 演示前 | — |

本 skill 安装在项目的 `.kiro/skills/aidlc-workshop/`（Kiro）或 `.claude/skills/aidlc-workshop/`（Claude Code），下文相对路径都以该目录为根。**执行某阶段前必须先完整读对应文件**：
- `stages/spec.md`、`stages/tdd.md`、`stages/demo.md`
- 参考：`references/ears.md`（EARS 句型、判据、P0 降级规则）、`references/tdd-rules.md`（TDD 契约）、`references/questions.md`（澄清问题格式）、`references/web-mvp.md`（产物形态：硬约束 vs 可选、分层、拓扑选项、栈选项、从零脚手架、测试分层、已知坑）
- 模板（按需选读，不必全读）：
  - 通用：`templates/requirements.md`、`design.md`、`tasks.md`、`traceability.md`、`DEMO.md`
  - Agent 类课题：`templates/design-agent.md`、`templates/scenarios.json`
  - TypeScript/Vitest 栈：`templates/ts/`（vitest.config.ts、tsconfig.test.json、route.contract.test.ts、live-eval.test.ts、_creds.ts、page-localstorage.tsx、e2e-browser-upload.mjs、e2e-browser-chat.mjs）
  - Python/pytest 栈：`templates/py/`（conftest.py、test_live_eval.py）
- 工具：`scripts/ac_status.py`（pytest 文本或 Vitest JSON → AC 通过率表）、`scripts/scaffold-next.sh`（非空目录里从零生成 Next.js 项目，拓扑 S）、`scripts/scaffold-vite.sh`（非空目录里从零生成 Vite 纯前端项目，拓扑 P）

## 核心原则（每个阶段都遵守）

1. **Reversed Conversation**：你提议，人批准。到门禁就停下来、把产物摘要给人看、等人回复。不要替人做决定。
2. **稳定追溯 ID**：每条验收标准一个 `AC-xx`（两位数字，从 01 开始，不重排、不复用）。从 requirements → tasks → 测试名 → 代码注释一路带着。
3. **不单发多步问题**：先出计划再动手；一个任务一个 bolt，做完再做下一个。
4. **测试是契约不是装饰**：Red 必须真的红，Green 不许改断言；做不到就如实标 TODO。
5. **文件即上下文**：所有产物写进仓库（`.kiro/specs/<feature>/`），换会话、换工具都能续。
6. **产物是 Web MVP，不是脚本；从空仓库开始**：硬约束只有四条（见 `references/web-mvp.md` §0）：核心逻辑 `lib` 与外壳分离、外部依赖走 fake/real 适配器、不上云不建数据库、有可操作的页面。**拓扑（纯前端 / 同仓库 API / 前后端分离 / 加 CLI）、技术栈、测试框架、存储、LLM 调用位置、mock 策略都是澄清阶段的选项，由你提出、客户按现场条件确认**，不要替客户预设；T0 按确认结果从零脚手架。客户会后要在这上面改造成生产系统，所以分层要干净。
7. **语言**：与人的对话、Spec 文档、EARS 语句主体用中文；EARS 关键字（THE/WHEN/WHILE/IF…THEN/WHERE/SHALL）、ID、文件名、代码、测试名用英文；面向最终用户的文本（回复、文案）按业务语言（任务卡说明，如客服为英文）。

## 运行模式

- **默认（interactive）**：门禁处停下等人。普通任务之间不停，但每个任务结束输出一行汇报。
- **自动模式（yolo）**：用户说"自动模式 / yolo / 不要停"时启用。门禁不停，但必须：为每个本该问人的问题选"若不回答我将假设"的答案并记录；文件头状态写 `已批准（自动模式，未经人工）`；只在集成检查点和阶段结尾汇报；阶段末尾输出"若在交互模式下我会问你的问题"，并追加到 `questions.md` 末尾的 `## 若交互模式我会问的问题` 小节。预跑和赶时间时用。

## 目录约定

```
.kiro/specs/<feature>/
  questions.md        §0 理解摘要 + 澄清问答（含答案）
  requirements.md     需求 + EARS 清单
  design.md           设计
  tasks.md            任务拆解
  traceability.md     AC → 测试 → 实现 → 状态
  test-report.txt     demo 阶段的全量测试输出
  DEMO.md             演示脚本与跟进
materials/            客户材料（只读）
samples/              小组自造样本：脏数据、小基线、对话样例
src/lib/ src/adapters/ + 外壳（page / api / cli 按拓扑）   见 references/web-mvp.md §1
data/                 本地文件存储（有后端的拓扑；运行时产生）
tests/                测试（Vitest：tests/**/*.test.ts；pytest：conftest.py 注册 marker）
```
`<feature>` 用短横线小写英文，如 `multilang-gen`、`cs-bot`。若项目已有 `.kiro/specs/`，沿用。

## 启动检查（任何命令开始前）

1. 找到 `.kiro/specs/<feature>/`，读已有产物，判断当前处于哪个阶段，不要重做已批准的产物。
2. 若用户没说 feature 名或材料位置，先问（一句话）。
3. 确认运行模式（默认 interactive，用户明确说了才 yolo）。
4. 每个阶段开始与结束用 `date +%H:%M:%S` 打卡，写入 `.kiro/specs/<feature>/timeline.md`（一行一条：`阶段 | 开始 | 结束`），用于会后复盘。
5. 然后读对应 `stages/*.md` 并执行。

## 与 Kiro / Claude Code 的关系

本 skill 只依赖"读写文件 + 运行 shell 命令"，在 Kiro CLI/IDE 与 Claude Code 中行为一致。Kiro IDE 原生 spec 也放在 `.kiro/specs/`，格式兼容。
