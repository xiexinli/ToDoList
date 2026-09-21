# 产物形态：Web MVP

今天做的不是脚本，是一个**能打开页面、能操作、能看到结果的最小 Web 应用**，从空仓库由 agent 生成，客户会后在它上面继续改造成生产系统。

## 0. 什么是硬约束、什么是可选

**硬约束（方法论需要，不随现场条件变）**
1. **核心逻辑与外壳分离**：业务规则放在不依赖 UI、HTTP、LLM、文件系统的 `lib`（纯函数 / 类），这是 TDD 的主战场，80% 的 EARS 在这里用单元测试断言。
2. **外部依赖走适配器**：LLM、接口、MCP、存储都通过接口注入，有 real 与 fake 两套实现；单测只用 fake，真实调用只在 live 抽样。
3. **不上云、不建数据库**：状态与产物存本地文件或浏览器存储。
4. **有页面**：至少一个能操作主流程的页面；没有页面就不是 MVP。

**可选（澄清阶段 T3/T4/T5 让客户按现场条件选，任何组合都可以）**
- 拓扑：纯前端 / 同仓库前端 + API / 前后端分离 / 再加 CLI。
- 存储：浏览器 localStorage、IndexedDB、文件下载 / 服务端 `data/` 文件 / SQLite 单文件。
- LLM 调用位置：浏览器直连 Bedrock（本机 AKSK）/ 服务端调用 / 只用 fake 离线演示。
- 技术栈：Next.js / Vite SPA / FastAPI + 静态页 / 其他。

## 1. 分层（外壳按拓扑选，lib 与 adapters 不变）

```
lib/        核心逻辑：纯函数 / 类，不碰 UI、HTTP、LLM、fs（唯一例外：storage 适配器）   ← TDD 主战场
adapters/   外部依赖适配：llm.{real,fake}、tools.{mock,real}、storage.{file,browser,memory}  ← 用参数/环境变量切换
外壳（任选组合）：
  page/     页面：表单 / 上传 / 聊天框 → 调 lib（纯前端）或调 API（有后端）→ 展示结果            ← smoke + 人工演示
  api/      接口层（可选）：解析请求 → 调 lib → 通过 storage 读写 → 返回 JSON                     ← 契约测试
  cli/      命令行（可选）：给研发流水线用                                                          ← 契约测试
samples/    自造样本：脏数据、小基线、对话样例（只读 fixture）；materials/ 是客户材料
```

原则：**lib 的函数拿到的是解析好的数据结构，返回的是数据结构**。同一份 lib 既能被页面直接 import（纯前端），也能被 API route 调用（有后端）——这正是"会后可以改造"的保证。

## 2. 拓扑选项（澄清阶段 T3）

| 拓扑 | 组成 | 存储 | LLM / 接口 | 适合 | 注意 |
|---|---|---|---|---|---|
| **P 纯前端** | Vite + React SPA（或 Next 静态导出），lib 在浏览器里跑 | localStorage / IndexedDB；生成文件用浏览器下载（jszip 浏览器打包） | 浏览器用 AWS SDK v3 直连 Bedrock，凭证从页面输入（AK / SK / 可选 Session Token，只存 sessionStorage，**只用于本地演示，绝不进生产**）；mock 接口就是页内函数（用 `ToolRegistry{list, call}` 对齐 MCP 的 tools/list、tools/call，会后有后端再换 MCP server）；浏览器没有 stdio | 现场没有后端环境、想最快看到页面 | **已预跑验证**：Bedrock 预检返回 `access-control-allow-origin: *`，浏览器 3 次 converse 全 200、无 CORS；xlsx/jszip 浏览器可用。凭证三项必须显式传 `credentials`，临时凭证要带 Session Token |
| **S 同仓库前端 + API** | Next.js App Router：页面 + `app/api/*` route | 服务端 `data/` 文件 + 前端 localStorage | 服务端调 Bedrock（本机 AKSK 走默认凭证链）；MCP 进程内或 stdio | 客户 PC 端同栈；一个仓库 | Next 16 坑位见 §6 |
| **D 前后端分离** | 前端目录（Vite/React/Vue）+ 后端目录（Express / FastAPI） | 后端文件 / SQLite | 后端调 | 团队前后端分工明确 | 两套配置，一天内偏重 |
| **+C 加 CLI** | 任一拓扑 + `cli/` 入口 | 同上 | 同上 | 研发效能类课题要进构建 | 只是多一层壳 |

不管选哪个，§1 的 lib/adapters 不变，EARS 与测试不变；变的只是外壳和 storage 适配器。

## 3. 技术栈选项（澄清阶段 T1/T2）

| 选项 | 组成 | 适合 | 取舍 |
|---|---|---|---|
| **A** | Next.js（App Router）+ TypeScript + Vitest；`xlsx`、`jszip`；`@aws-sdk/client-bedrock-runtime`；`@modelcontextprotocol/sdk`；Tailwind | 客户 PC 端同栈；拓扑 S 最顺，也能 `output: "export"` 做拓扑 P | Next 16 坑位（§6）；npm 靠网络 |
| **B** | Vite + React/Vue + TypeScript + Vitest（纯前端），可选 Vercel AI SDK（`ai` + `@ai-sdk/amazon-bedrock`）或 AWS SDK v3 做浏览器端 agent | 拓扑 P | AKSK 在浏览器，仅演示；MCP 需变通 |
| **C** | Python 3.12 + FastAPI + pytest；静态 HTML/JS 页；`openpyxl`、`boto3`、`mcp` | Python 团队；拓扑 D/S | 页面简陋；两种语言 |
| D | 与客户现有某项目同栈（请说明） | 会后接入最顺 | 现场无参考模板 |

有 `templates/ts/`（A/B）与 `templates/py/`（C）两套模板；没有对应模板就按同样分层自己写。

## 4. 从零脚手架（T0，命令写进 design.md §5，照抄执行）

**workshop 目录非空（有 TASK_CARD.md、materials/、.kiro/），`create-next-app .` / `npm create vite .` 会失败**，用 skill 自带脚本（子目录生成再搬回）：
```bash
FEATURE=<feature> bash <skill目录>/scripts/scaffold-next.sh xlsx jszip                                  # A，文件类课题
FEATURE=<feature> bash <skill目录>/scripts/scaffold-next.sh @aws-sdk/client-bedrock-runtime @modelcontextprotocol/sdk zod   # A，Agent 类课题
```
选 B（Vite 纯前端）用另一个脚本：
```bash
FEATURE=<feature> bash <skill目录>/scripts/scaffold-vite.sh xlsx jszip                                   # 文件类
FEATURE=<feature> bash <skill目录>/scripts/scaffold-vite.sh @aws-sdk/client-bedrock-runtime @smithy/types zod   # Agent 类
```
它会额外放一份 `tsconfig.test.json`（Vite 的 `tsc -b` 不覆盖 tests/ 与 scripts/）并把 `typecheck` 设为两段。预跑实测 80 秒–3 分钟。选 C：`uv init && uv add fastapi uvicorn openpyxl && uv add --dev pytest httpx`，静态页放 `static/index.html`。

预跑实测（A）：热 npm 缓存 1 分 43 秒，冷缓存估 3–8 分钟。T0 完成定义：测试（1 条 smoke）、typecheck、lint、页面首页 200、SDK 探针（读一次客户样本 / MCP 列工具 / Bedrock 一句）全部通过。

## 5. 测试分层与 AC 映射

| 层 | 测什么 | 怎么跑 | 典型 AC |
|---|---|---|---|
| lib 单元 | 每条业务规则 | 直接 import | 格式、映射、校验、守则、编排 |
| 外壳契约 | API handler 或 CLI 的入参/出参/状态码（拓扑 P 没有这层，用页面 smoke 代替） | 构造 `Request` 直接调用（模板 `templates/ts/route.contract.test.ts`） | 上传→报告、聊天→回复结构、400 |
| 端到端 smoke | 起 dev/preview，走一次主流程 + 一次异常流 | 集成检查点任务（有 API 用 curl；纯前端用 Playwright 最小脚本，模板 `templates/ts/e2e-browser-upload.mjs` / `e2e-browser-chat.mjs`，记录 console 与 CORS、截图） | 见 tdd.md |
| live | 真实 LLM/接口抽样 | `npm run test:live`，只断言确定性字段 | Agent 类 |

## 6. Next.js 16 / 相关 SDK 已知坑（预跑踩过；只适用于选项 A，其他栈忽略）

- `dynamic(() => import(...), { ssr: false })` 只能在 Client Component 里用：`page.tsx` 顶部要加 `"use client"`，否则 500。
- `route.ts` 的 `params` 是 `Promise<{id}>`，要 `await`；契约测试传 `{ params: Promise.resolve({ id }) }`。文档在 `node_modules/next/dist/docs/`。
- `LayoutProps<"/">`、`RouteContext<…>` 是 `next dev`/`next typegen` 生成的全局类型；T0 跑 `npx next typegen`。
- eslint-config-next 16 启用 React Compiler 规则（error 级）：不要在 `useEffect` 里 `setState` 读 localStorage，用 lazy initializer + `ssr:false`，或 `useSyncExternalStore`（模板 `templates/ts/page-localstorage.tsx`）。
- `next dev` 端口被占直接失败，用 `-p <port>`。
- `AGENTS.md` 由 `next dev` 自动重写，不用管 diff。
- Vitest 5：默认 reporter 不输出 `console.log`，live 要落盘用 `--reporter=verbose --silent=false`；`@types/node` 需 ≥ 20.19 或 22。
- MCP TS SDK 1.30：`registerTool(name, {description, inputSchema: zod 字段对象, outputSchema?}, handler)`；定义了 `outputSchema` 就必须返回 `structuredContent`；单测用 `InMemoryTransport.createLinkedPair()`。
- Bedrock SDK：`DocumentType` 从 `@smithy/types` 导入；`us.anthropic.claude-sonnet-5` 不接受 `temperature`。浏览器端使用时凭证要显式传入 `credentials`，并验证 CORS。

## 6b. Vite 纯前端（选项 B）已知坑（预跑踩过）

- Vite 8 脚手架：lint 已是 **oxlint**（不是 ESLint）；TypeScript 6 弃用 `baseUrl`（alias 用 `paths` + vitest `resolve.alias`）、`erasableSyntaxOnly` 禁止构造器参数属性；`__dirname` 用 `import.meta.dirname`；tsconfig 里不能有注释（脚本用 `JSON.parse` 读）。
- `tsc -b` 只查 `src/`，tests/ 与 scripts/ 要单独 `tsconfig.test.json`（脚手架脚本已放）。
- SheetJS 读 CSV：`XLSX.read(bytes)` 默认按 cp1252 解码，中文乱码；先 `new TextDecoder("utf-8").decode(bytes)` 再 `XLSX.read(text, { type: "string" })`。xlsx 表头可能带 `\r\n`，要 trim。
- 浏览器 zip：`Uint8Array` 传给 `Blob` 需类型断言；上传的 macOS zip 里的 `__MACOSX/` 与 `.DS_Store` 要过滤；jszip 生成时 `createFolders: false` 否则条目数多出目录项。
- Bedrock 浏览器端：`BedrockRuntimeClient({ region, credentials: { accessKeyId, secretAccessKey, sessionToken? } })`，`toolUse.input` 类型 `DocumentType` 从 `@smithy/types` 引；凭证只放 sessionStorage，页面给"Clear"按钮；`aws configure export-credentials --format env` 可导出临时凭证做演示。
- Playwright：用 `npx -y playwright@latest` 的缓存包，不必装进项目依赖；Chromium 需提前 `npx playwright install chromium`；脚本里记录 `console`、失败请求与 CORS 报错。
- npm 11 的 `allow-scripts` 警告无害。

## 7. MVP 边界（写进 requirements 的范围外）

不做：登录鉴权、多用户、权限、数据库、部署、UI 美化、国际化 UI。做：一条主流程 + 关键异常流 + 报告/追溯可见 + 页面能操作。

## 8. 会后改造路径（写进 DEMO.md 跟进）

- `adapters/*` 的 fake → real（接口地址、凭证走环境变量或服务端）。
- 拓扑 P → S/D：把页面里对 lib 的直接调用挪到 API 后面，lib 不动；AKSK 从浏览器撤到服务端。
- `storage` 适配器：浏览器/文件 → 数据库。
- 测试不变：EARS 是契约，改造后仍要全绿。
