# DHgate 黑客松 Workshop —— Mock 数据管理

本文档面向 **Mock 数据管理** 任务组,规范本次黑客松的**方法论流程、MVP 范围、交付标准与技术约束**。

> 说明:《Mock 数据管理与 APP Debug 场景开关平台技术设计方案 V1》为**参考示例**,展示该任务的目标与设计思路,不作为强制实现规格。以本指导文档的流程与约束为准。

---

## 一、目标

- **目标**:做一个 mock serve + Agent,用对话式(自然语言)实现对接口 mock 数据的增删改查。最终形态 = 一个本地可被 App 消费的 mock 服务 + 一个基于 LLM(DHCoder/Codex)的 Agent——由模型自主调用工具(upload/list/get/delete/serve)完成管理与消费。
- **分工**:每人**单人全角色**,一人分饰 PM / 架构 / 开发 / 测试,各自独立走完整流程。

---

## 二、方法论流程(AI-DLC)

以 **Spec 最佳实践 + TDD + EARS 验收标准** 为主线,按以下顺序推进:

1. **写 Spec** — 产出完整 Spec:需求(含 EARS 清单)+ 设计 + 任务拆解。
2. **定 EARS 验收标准** — 把「验收思路与标准」逐条改写成 EARS 格式,形成验收标准清单;每条标准都应能对应一个测试。
3. **TDD 写测试** — 用 TDD Skills 把每条 EARS 验收标准逐条转成测试。
4. **Agent 实现** — 让 Agent 实现功能,使测试逐条通过;报错时进行必要的人工调整。
5. **跑通原型** — 全部标准通过后,跑通本地原型。

**要求**:EARS 标准 ↔ 测试 ↔ 实现三者可一一追溯。

---

## 三、MVP 范围约束

- **对话式管理** — 用户上传 JSON → 识别「保存假数据」意图 → 确认三字段(page_or_feature / interface_url / business_scene)→ 查重(规则 + AI 语义)→ 保存 / 覆盖 JSON → 写元数据记录 → 重建 `mock_index.json`。
- **本地 mock serve** — 起一个本地 **localhost** HTTP 端点,App / Charles 直接指向它,按接口取到对应的 mock 响应。

**客户已确认的边界与简化项**:

- **只做 Agent + 本地服务** — Agent 侧闭环 + 本地 mock serve 为必做;App 端内嵌 Debug 页面、开关、本地拦截等本期**不做**(按参考方案理解即可)。
- **serve 不部署云端** — mock serve 只跑在本地 localhost,**不上 AgentCore / 云主机**。
- **落盘用飞书多维表格** — 交付态存储为飞书多维表格(元数据 + Mock 响应 JSON),`mock_index.json` 供 serve。存储走可切换适配器(MetaStore),开发早期无凭证可临时用本地文件。不单独建后端 Mock 配置服务。
- **同接口仅一个场景激活** — 同一 `interface_key` 同一时间仅允许一份 Mock 生效(见第四节)。

---

## 四、技术约束 / 设计原则

以下为实现时必须遵守的关键约束:

- **同一 `interface_key` 同一时间仅允许一份 Mock 生效**(`interface_key` = METHOD + normalized_url)。避免同接口命中多份 JSON 时无法决策。
- **normalized_url**:去掉域名仅保留 path,V1 默认忽略 query 参数。
- **数据分层(目标飞书双表)**:目标存储为**飞书多维表格双表关联结构**——「接口定义」(接口名称/请求路径/请求方法/接口状态/说明) + 「Mock数据」(场景名称/Mock响应内容(存 JSON)/状态(启用|停用)/备注/所属接口→关联接口定义);Mock 响应 JSON 存「Mock响应内容」列,新建接口填「接口状态」(默认 开发中)。`mock_index.json` 作为对外消费唯一索引。
- **本地为开发期过渡**:存储经 MetaStore 适配器,开发早期无凭证时可临时用本地文件,但**交付演示以飞书为准**(切换不动核心逻辑)。
- **文件命名**:`{page_or_feature}-{business_scene}.json`,保存前做文件名安全化(去非法字符、截断、保留 .json)。
- **查重两段式**:先规则召回候选,再 AI 语义判断是否同一场景;命中相似记录时回显并询问覆盖/新增。

---

## 五、Agent 工具与验收用例

**5 个 Agent 工具**(进程内 / MCP 形态均可,自主 tool-calling 由 LLM 决定调用):
- `upload` — 上传一条 mock 记录(校验结构 + responseBody 合法 JSON,非法拒绝并给原因)
- `list` — 返回全部已保存记录
- `get` — 按 name(或 interface_key)查询记录
- `delete` — 删除记录,删除后再取返回 not found
- `serve` — 本地 HTTP 端点,按 method+path 命中当前 active 场景返回其 responseBody

**mock 记录 schema**(只校记录结构 + responseBody 合法 JSON,不校业务字段):
`name`、`http_method`、`interface_url`(→ normalized → interface_key)、`statusCode`、`responseBody`(合法 JSON)、`page_or_feature`、`business_scene`。

---

## 六、交付规范

分享演示需包含:

1. **Spec 展示** — EARS 验收标准清单 + 任务拆解。
2. **追溯演示** — 挑 1–2 条 EARS 标准,现场指出它对应哪个测试、哪段实现。
3. **场景演示** — 对话式上传并保存一份 mock,再用 App / Charles 指向本地 mock serve,取到预期响应。
4. **测试结果** — 已通过条数 / 总条数。
5. **未完成部分** — 列出未完成项 + 会后跟进计划。
