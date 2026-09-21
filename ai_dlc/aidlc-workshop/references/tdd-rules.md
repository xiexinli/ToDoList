# TDD 契约

## 顺序不可变
1. **Runner first**：没有能运行的测试命令之前不写功能代码（T0 的唯一目的）。T0 同时做 **SDK 探针**：打印关键 SDK 版本并做一次最小调用（如起一个 MCP server 列工具、Bedrock converse 一句），版本漂移在这里暴露而不是在 T3。
2. **Red**：写测试 → 运行 → 必须失败 → 记录失败摘要。
3. **Green**：最小实现 → 全量运行 → 全绿。
4. **Refactor**：全绿下重构 → 再跑。

## 命名与追溯
- 测试名必含 AC ID：
  - pytest：`def test_ac_07_missing_translation_reported():` + `@pytest.mark.ac("AC-07")`
  - 参数化 / 数据驱动（一个函数覆盖多条 AC）：
    ```python
    @pytest.mark.parametrize("msg, expect", [
        pytest.param("I need reset password", "clarify", marks=pytest.mark.ac("AC-08"), id="ac_08-vague"),
        pytest.param("never got the email", "in_mail_sent", marks=pytest.mark.ac("AC-07"), id="ac_07-normal"),
    ])
    ```
    统计脚本按 `id` 里的 `ac_07` 归类，所以 **id 必须以 `ac_xx-` 开头**。
  - JS `test('AC-07 …')`；Java `@DisplayName("AC-07 …")` 或方法名 `ac07_…`。
- 一条 AC 可有多个测试；一个测试（或一个参数化 case）只对应一条 AC。
- 实现代码关键处注释 `Implements: AC-07`。
- `traceability.md` 每完成一个任务就更新，不要留到最后。

## Red 证据
- 每条 AC 一行独立的失败摘要（`assert 0 == 3` / `NotImplementedError` / `KeyError: 'diff'`）。
- 整个文件 `ImportError` 无法收集时，先补空模块/空签名（不含逻辑）再跑，拿到独立证据。工具注册（如 MCP `@server.tool` 空函数）也算"签名"。
- 子进程/契约类 AC（起 MCP server、连 stdio）：首轮"连接失败 / 工具列表为空"就是合格的红证据。
- 集成检查点不要求新红，记 `e2e: <命令> → <关键输出>`。
- 新测试直接绿：先加更严的断言或更刁的输入让它红；仍绿且确认被前序任务实现的，记 `已被 Tn 覆盖`。

## Fake 与测试的边界（Agent / 外部依赖类课题）
- **FakeLLM 有两种形态，design.md 里先选**：① 脚本回放（按测试给定的工具调用/回复序列返回，用于单元测试，最确定）；② 规则模拟"理想模型"（关键词 → 意图 → 工具调用，用于离线演示与样例回放）。单元测试优先用①。
- 修 fake **不算**改测试——前提是断言没动、fake 的行为仍取自客户样例；但如果你在改 fake 让它"恰好吐出断言要的值"，那就是在作弊。
- 哪些结局由代码短路（守则拦截、转人工、查不到即收口）、哪些交给 LLM，要在 design.md 写明；短路的部分用规则测试，LLM 的部分用脚本 fake + live 抽样。

## Vitest 约定（选 TypeScript 栈时：Next.js 或 Vite）
```ts
// tests/lib/reader.test.ts
import { describe, it, expect } from "vitest";
describe("reader: 缺译文处理", () => {            // describe 名不带 AC 编号
  it("AC-07 空译文列入 missing 且不写入该语言", () => { /* ... */ });
  it("AC-04 空行跳过并计入 skippedRows", () => { /* ... */ });
});
// 参数化：cases 为 [name, data] 元组，name 以 "AC-05 …" 开头
it.each(cases)("%s", (name, c) => { /* ... */ });
```
- `package.json`：`"test": "vitest run"`，`"test:live": "LIVE=1 vitest run tests/live --reporter=verbose --silent=false"`（否则 console.log 不落盘），`"test:json": "vitest run --reporter=json --outputFile=.kiro/specs/<feature>/vitest.json"`，`"typecheck": "tsc --noEmit"`。
- live 测试放 `tests/live/`，`vitest.config.ts` 按 `LIVE` 环境变量切 include/exclude（模板 `templates/ts/vitest.config.ts`），默认不跑。
- **归类坑**：`ac_status.py` 用 fullName（describe 名 + 测试名）里出现的 `AC-xx` 归类，所以 **describe 名不要带 AC 编号**，除非其下所有 case 同一 AC；`it.each` 用 `[name, data]` 元组把 `AC-xx` 拼进 case 名：`it.each(cases)("%s", (name, c) => …)`，其中 `name = "AC-07 c02 normal"`。
- API route 契约测试：直接 `import { POST } from "@/app/api/x/route"`，构造 `new Request(url, {method, body})` 调用，动态路由传 `{ params: Promise.resolve({ id }) }`，断言 `res.status` 与 `await res.json()`。`DATA_DIR` 在 `beforeAll` 里设成 `mkdtemp` 临时目录，再动态 `import()` route 让 env 先生效。模板 `templates/ts/route.contract.test.ts`。
- stub 抛 `not implemented` 时，`expect(...).toThrow()` 类测试会误绿——Red 阶段看清失败原因是不是你要测的那个。
- 统计：`npm run test:json && python <skill>/scripts/ac_status.py .kiro/specs/<feature>/requirements.md < .kiro/specs/<feature>/vitest.json`。
- 文件系统：测试里把 `DATA_DIR` 环境变量指到临时目录（`fs.mkdtempSync`），断言读回的文件。

## pytest 约定（Python 栈时）
```toml
# pyproject.toml
[tool.pytest.ini_options]
markers = [
  "ac(id): EARS acceptance criterion id",
  "live: 需要真实外部服务（LLM/网络），默认不跑",
]
testpaths = ["tests"]
addopts = "-m 'not live'"
```
`tests/conftest.py` 见 `templates/py/conftest.py`。

运行：`uv run pytest -q`；只跑某条：`uv run pytest -k ac_07 -v`；live：`uv run pytest -m live -v`；统计：`uv run pytest -q --color=no -rA --tb=no | python <skill>/scripts/ac_status.py .kiro/specs/<feature>/requirements.md`。

## 禁止
- 为了转绿：删断言、放宽断言、`xfail`/`skip`、写死期望输出、把阈值调低、在测试里 mock 掉被测逻辑本身。
- 一个 Green 顺手实现三个任务的功能。
- 单元测试访问真实外部服务（LLM、HTTP、MCP 远端）；真实调用只放 `live` marker 的评估，且 live 只断言确定性结果（outcome、工具调用序列、语言），不断言措辞。
- 跑红了直接 commit / 汇报"完成"。

## 允许
- 测试逼出接口设计：发现 design.md 需要改就改并注明。
- 标 `TODO(blocked: 原因)`：如实暴露，比假绿好。
- 外部 SDK 漂移时 pin 版本或改实现适配，测试不动。

## 确定性
- 外部依赖（LLM、网络、时间、随机）一律注入接口 + fake。fake 的返回值来自客户提供的真实样例（如接口 JSON 样例、对话记录），不要自己编格式。
- 文件生成类：测试用临时目录，断言读回来的内容而不是日志。
- Agent 类：对话样例放 `samples/scenarios.json`（见模板），`source` 标 `customer` / `synthetic`，synthetic 必须列入会后跟进。

## 汇报格式（每个任务结束一行）
```
T3 完成 | 新增测试 4 | 全量 12/12 | ~35min | TODO 0
```
