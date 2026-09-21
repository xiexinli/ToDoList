# 设计补充（Agent 类课题）：<feature 中文名>

> 与 `design.md` 一起用。Agent 类课题最大的自主决策是"哪些结局由代码决定、哪些交给 LLM"，这里先写死，TDD 才有确定性。

## 1. 结局（outcome）枚举
| outcome | 含义 | 由谁决定 | 对应 AC |
|---|---|---|---|
| `clarify` | 信息不全，追问 | LLM（或规则） | |
| `in_mail_sent` | 主流程闭环完成 | 编排器（工具返回成功） | |
| `buyer_not_found` | 后端查不到（与 scenarios.json 模板一致） | 编排器短路 | |
| `need_buyer_id` | 缺少用户标识，需追问 | 编排器短路 | |
| `handoff` | 转人工 | Guardrail-in 短路 / 工具连续失败 / LLM 异常 | |
| `refused_policy` | 违规请求被拒 | Guardrail-in 短路 | |
| `safety_notice` | 用户泄露凭证 | Guardrail-in 短路 | |
| `answered` | 普通回答，无工具 | LLM | |

## 2. 数据结构
```python
@dataclass
class Session:        # 会话状态
    user_id: str | None
    history: list[Message]
    ...

@dataclass
class TurnResult:     # 每回合返回，测试只断言这里的确定性字段
    reply: str
    outcome: str          # 上表枚举
    tools: list[str]      # 本回合调用的工具名序列
    violations: list[str] # 出向守则命中项
    summary: str | None   # 给人工客服的摘要（可选 AC）
```

## 3. 回合流程与短路点
```
用户消息 → Guardrail-in（转人工词 / 凭证泄露 / 违规请求 → 短路返回）
        → 意图/上下文补全（缺 user_id → clarify 短路）
        → LLM（工具集按意图裁剪；只暴露本回合允许的工具）
        → 工具调用（失败重试 N 次 → 超过则 handoff 短路）
        → Guardrail-out（禁言、语言校验；不通过则替换为兜底句）
        → TurnResult
```

## 3b. 工具暴露策略（先决定）
- A. 按意图裁剪：只有识别为主流程意图时才把工具给 LLM（守则更稳，追问回合零工具调用可断言）。
- B. 全部暴露，交给模型决定（更"智能"，但守则要靠出向校验兜底）。
预跑采用 A。

## 4. LLM 抽象
- 接口：`LLMClient.chat(messages, tools) -> LLMResponse(text | tool_calls)`。
- 生产实现：<Bedrock converse / …>，参数注意：<如 不传 temperature>。
- Fake ①（脚本回放，单元测试用）：`ScriptedLLM([...])`。
- Fake ②（规则模拟，离线演示用）：`HeuristicLLM()`。

## 5. 工具（MCP 或浏览器内 ToolRegistry）
- 有后端：MCP server（官方 SDK），单测用进程内传输。
- 纯前端：浏览器没有 stdio，用 `ToolRegistry { list(): ToolSpec[]; call(name, args): Promise<Result> }` 对齐 MCP 的 tools/list、tools/call 形状，mock 接口是页内函数；会后有后端时把 registry 换成 MCP client，编排器不动。

| 工具名 | 参数 | 成功返回 | 失败返回 | 来源样例 |
|---|---|---|---|---|
| | | | | samples/api_samples.json |

## 6. 对话样例 → 测试
- `samples/scenarios.json`：每条 `id / source / ac / turns[].expect{outcome, tools}`。
- `tests/test_scenarios.py` 用参数化回放全部样例，`id="ac_xx-<id>"`。
- `tests/test_live_eval.py`：抽 3–5 条走真实模型，只断言 outcome / tools / 语言。
