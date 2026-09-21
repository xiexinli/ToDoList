# questions.md 的格式：理解摘要 + 澄清问题

文件位置 `.kiro/specs/<feature>/questions.md`。

## §0 理解摘要（Step 1 写）

```markdown
## 0. 理解摘要
- 要做什么：…
- 输入：…（格式、样本在哪）
- 输出：…（几种、放哪、给谁用）
- 已知规则：…（逐条，带材料出处）
- 材料缺什么：…
- 业务语言：用户侧文本用 <英文/中文>
```
≤ 20 行。这是小组对齐认知的第一份产物，导师会先看它。

## §1+ 澄清问题（Step 2 写）

每题固定结构：

```markdown
## Q1. PRD 表格里没有 key 列，各端的 key 应如何产生？

影响：决定 AC 的 key 规则条目怎么写、Android/PC 任务是否需要 key 生成器。

A. 全部端都用英文原文作 key（与 iOS/wap 一致），Android/PC 也用英文原句
B. iOS/wap 用英文原文；Android/PC 由工具生成 snake_case，并以 CLI 参数指定模块前缀
C. 要求 PRD 表格新增 key 列，工具只做转换，缺 key 报错
D. 由 AI 根据英文语义生成 key，人工确认
E. 先按 B，将来支持 C
X. Other (please specify)

若不回答我将假设：B

[Answer]:
```

规则：
- 4–8 题；每题 3–5 个实质选项 + 固定的 `X. Other (please specify)`。
- "影响"一行写清楚这个问题改变什么，不写就别问。
- "若不回答我将假设"必填：interactive 下人可以一句"都按默认"拍板；yolo 下直接用它。
- 回答写回 `[Answer]:`，形式 `[Answer]: B` 或 `[Answer]: X: 我们用…`；yolo 写 `[Answer]: B（自动）`。
- 模糊回答（"看情况""都行""可能""不确定"）→ 追加 `## Q1a.` 追问，不得进入下一步。
- 答案汇总不单独成节，直接作为门禁 1 的一部分贴给人（与 EARS 清单一起批）。requirements.md 的假设小节只写 `Q1 → B：一句话`。

## B 组：技术确认（固定 5 题，照抄后按课题填选项）

```markdown
## T1. 技术栈与框架？

影响：决定 T0 脚手架命令、测试框架、页面写法；客户会后在这上面继续改造。

A. Next.js（App Router）+ TypeScript —— 一个仓库同时有页面与 API；贵司 PC 端同栈（推荐）
B. Python FastAPI + 一个静态 HTML/JS 页 —— 后端逻辑最简单，适合 Python 团队
C. Vue/Vite 前端 + Node Express 后端 —— 前后端分开两个目录
D. 与贵司现有某项目同栈（请说明）
X. Other (please specify)

若不回答我将假设：A

[Answer]:

## T2. 测试框架与命令？
A. Vitest（`npm test`）（随 A 栈推荐）  B. pytest（`uv run pytest -q`）  C. Jest  X. Other
若不回答我将假设：与 T1 匹配

## T3. 拓扑与页面形态？（见 web-mvp.md §2；按现场条件选，任何组合都行）
A. 同仓库前端 + API（Next.js 页面 + app/api），单页：<按课题写：上传→报告→下载 / 聊天框+侧栏>（推荐，客户 PC 端同栈）
B. 纯前端 SPA：lib 在浏览器跑，LLM 用本机 AKSK 从浏览器直连 Bedrock（仅演示），生成文件走浏览器下载
C. 前后端分离：前端目录 + 后端目录（Express / FastAPI）
D. A 或 B 再加 CLI 入口（研发效能类课题进构建用）
X. Other (please specify)
若不回答我将假设：A

## T4. 存储？
A. 服务端 `data/<…>/` JSON 与输出文件，前端 localStorage 存历史与偏好；不上云、无数据库（配拓扑 A/C）  B. 只用浏览器存储：localStorage / IndexedDB，产物用下载保存（配拓扑 B）  C. SQLite 单文件  X. Other
若不回答我将假设：与 T3 匹配

## T5. 外部依赖与运行时？（按课题类型选一种问法）
Agent 类：A. 接口用本地 mock（客户样例逐字）；LLM 单测用 fake，允许 live 抽样从服务端调 Bedrock us-west-2（本机凭证链）；Node 22/npm（推荐）  B. 同 A 但 LLM 从浏览器直连 Bedrock，AKSK 页面输入或 .env.local（配拓扑 B，仅演示）  C. 全离线，不调任何真实服务  D. 允许直连贵司测试环境接口  X. Other
文件类：A. 全离线；Excel 用 xlsx（SheetJS）、压缩用 jszip；基线由页面上传 zip（推荐）  B. 基线填服务器本地路径  C. 允许 AI 补翻（调 Bedrock）  X. Other
```

技术题的"推荐"只是推荐，**客户选什么就用什么**；无论选哪种拓扑/栈，`web-mvp.md` §0 的硬约束（lib 与外壳分离、适配器、不上云不建库、有页面）不变，模板选对应目录（`templates/ts/` 或 `templates/py/`），没有对应模板就按同样结构自己写。

典型业务必问项（看材料缺什么再选）：
- 输入输出格式的空白点（列、编码、目录名、占位符写法）
- 冲突处理策略（已存在、不一致、缺失）
- 边界：今天不做什么
- 技术栈与运行方式（CLI/Web、语言、是否联网、用哪个模型）
- 加料取舍：P1 里哪几条今天必须做
- 业务语言与口径冲突（如两条客户样例标签不一致）
