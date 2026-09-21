# 设计：<feature 中文名>

状态: 草稿 | 已批准（日期）| 已批准（自动模式，未经人工）
对应需求: requirements.md（AC-01 … AC-nn）

## 1. 架构（分层见 references/web-mvp.md §1；拓扑取 questions.md T3 的答案：<P 纯前端 / S 同仓库 API / D 前后端分离 / +C CLI>）
| 层 | 模块 | 职责 | 输入 → 输出 | 对应 AC |
|---|---|---|---|---|
| lib | `src/lib/<domain>/x.ts` | 纯函数：… | 数据结构 → 数据结构 | AC-… |
| adapters | `src/adapters/<dep>.{real,fake}.ts` | 外部依赖（LLM / 接口 / storage） | — | live |
| 外壳·page | `/<page>` | 上传/表单/聊天框 → 调 lib（纯前端）或 fetch API → 展示 | — | smoke |
| 外壳·api（如有） | `POST /api/<route>` | 解析请求 → lib → storage → JSON | multipart/JSON → JSON | AC-… |
| 外壳·cli（如有） | `<cmd> --in …` | 参数 → lib → 文件 | — | AC-… |

### 存储（按 T4 的答案）
- 服务端文件（如有）：`data/<…>/…`，环境变量 `DATA_DIR`，默认 `./data`
- 浏览器：localStorage / IndexedDB `<feature>:<key>`：…；下载文件名：…
- LLM 调用位置：<服务端 / 浏览器直连（本机 AKSK，仅演示）/ 仅 fake>

（可选 mermaid 图）

## 2. 数据模型与契约
### 输入
### 输出（每种输出给 1 个最小样例）
### 接口 / CLI
```
<entry> --in <file> --out <dir> [--targets a,b] ...
```

## 3. 关键流程
### 主流程
### 异常流程（对应 Unwanted 条目）

## 4. 测试策略
| AC 范围 | 层次（单元/契约/端到端/live） | fake / fixture / 样本 |
|---|---|---|
| | | |

外部依赖抽象：<接口名> → 生产实现 / fake 实现（fake 返回值取自客户真实样例）。

### 需要自造的样本（放 `samples/`）
- 文件生成类：脏数据样本（空行 / 缺译文 / 多余空格 / 占位符不一致 / 禁译词 / 需转义字符），小基线目录（与输出目录同结构，每端 1 个语言、10–20 行）。
- Agent 类：`samples/scenarios.json`（见 `templates/scenarios.json`），客户样例逐字保留、补充样例标 `synthetic`。

## 5. 技术选型（来自 questions.md T1–T5）、从零脚手架命令与 SDK 探针
- 语言/框架：<客户确认的选项>；运行时：<node 22 / python 3.12>
- **T0 脚手架命令（逐条执行）**：
  ```bash
  npx create-next-app@latest . --ts --tailwind --eslint --app --src-dir --import-alias "@/*" --use-npm --yes
  npm i -D "@types/node@^22" vitest tsx
  npm i <课题依赖>
  npx next typegen
  ```
- 脚本：`test` / `test:json` / `test:live` / `typecheck` / `lint` / `dev`
- 关键 SDK 与版本：
- SDK 探针要做的最小调用：<读一次客户样本 / MCP 进程内列工具 / Bedrock 一句>
- 原型入口：`npm run dev` → `http://localhost:3000/<page>`

## 6. 设计决策记录
| 决策 | 备选 | 选择理由 |
|---|---|---|
