# Jev 学习文档（草稿）

> 整理日期：2026-09-21
> 整理范围：基于公开资料调研。**本文档中的版本号、价格、限额均以 2026-09-21 抓取时为准，官方明确说明"可随时变化"，请以官方文档为准。**
> 项目上下文：本文件位于 `/Users/alion/DemoProjects/ToDoList/Jev/`，该目录原为空目录，项目内（含 `.idea/`、git 对象）未检索到任何 `jev` 相关内容，因此本文档是**外部调研结论**，不是对项目内既有代码的解释。

---

## 0. 结论速览（TL;DR）

在开发语境下，"jev" **最可能指 TypeSafe AI 的 System One 决策模型 "Jev"**，置信度较高（约 85%），理由见第 1 节。

- **一句话定义**：Jev 不是聊天模型，而是一个"**类型化决策模型**"——输入一段 state（文本/JSON），输出**你预先定义好答案空间**的类型化答案（选项 / 分值 / 是-否概率）+ 校准过的置信度，供代码直接分支使用。
- **官方口号式数据流**：`text or JSON state + typed questions → constrained answers + probabilities → your code`
- **发布方 / 发布时间**：TypeSafe AI（创始人 Diogo Almeida，前 OpenAI），2026-09-15 发布，目前为 **early access**。
- **核心卖点**：比 LLM 快 2 个数量级（端到端 70–500ms）、输出零类型错误、不产生幻觉文本、"输出 token 免费"。
- **核心代价**：**它不会写文字**。不能生成回复、代码、解释。该它干的是"判断"，不是"表达"。

---

## 1. 候选清单与判断依据（不臆测，先列候选）

| # | 候选 | 类别 | 判断 | 依据 |
|---|---|---|---|---|
| 1 | **TypeSafe AI 的 Jev（System One 模型）** | AI 模型 / API | ✅ **最可能** | ① 开发者语境下 GitHub 搜索 `jev` 共 7,471 个仓库，Top 结果几乎全部与它相关；② 官方站点 `typesafe.ai`、文档 `docs.typesafe.ai`、SDK 仓库、npm 包 `@typesafe-ai/sdk`、PyPI 包 `jev` 均真实存在且可访问；③ 2026-09 是当前热点（发布仅 6 天）；④ 用户项目里已有 `ai_dlc/`（AI 开发概念学习笔记），与"学一个 AI 概念"的动因高度吻合 |
| 2 | **JEV = Japanese Encephalitis Virus（乙型脑炎病毒）** | 医学 | ⚠️ 仅当用户在写医学/生物相关文档时成立 | 这是 "JEV" 在生物医学文献中最常见的全大写缩写。但用户项目是 ToDoList，且未大写成 JEV |
| 3 | **npm 包 `jev`** | JS 包 | ❌ 排除 | 该包真实存在但只有 `0.0.0` 一个版本，描述为空，是占位/抢注包，无可学习内容 |
| 4 | **jev.dev（Jev Forsberg，个人站点）** | 人名 | ❌ 排除 | `jev.dev` 实际是个人主页，非技术工具 |
| 5 | **Jevko（一种极简语法）** | 语法规范 | ❌ 可能性低 | 拼写相近但一般写作 "Jevko"，且热度远不及候选 1 |
| 6 | **项目内自定义缩写 / 打错的 `dev`、`js`、`json`** | 笔误 | ❌ 已排除 | 全工作空间正则检索 `(?i)jev` **零命中**；目录为空 |

**判断结论**：按"常见开发语境 + 用户已有 AI 学习笔记目录"两条证据，候选 1 是压倒性最可能的含义。候选 2 是唯一需要用户一句话确认的备选。

> ✅ **需用户确认的第 1 个关键点**：这里的 "jev" 是否指 TypeSafe AI 的 Jev 模型？（若其实指日语脑炎病毒或别的内部代号，本文档后续章节不适用。）

---

## 2. Jev 是什么：定位与原理

### 2.1 System One 是什么

"System One" 一词借用 Daniel Kahneman《思考，快与慢》中的概念：System 1 = 快速直觉，System 2 = 缓慢审慎。TypeSafe 用它命名一类**专为软件的"快速判断"而生**的模型类别。Jev 是该类别的第一个模型，也是旗舰模型。

### 2.2 与普通 LLM 的对比（官方对照表，这是理解 Jev 的关键）

| 维度 | 传统 LLM | System One + Jev |
|---|---|---|
| 训练目标 | RLHF / RLVR，优化"人类喜欢的文字" | **RLCD**（Reinforcement Learning for Calibrated Decisions），优化"**校准过的判断**" |
| 输入 | 非结构化文本，偏重**消息序列** | 非结构化文本，偏重**程序状态（state）** |
| 输出 | 字符串（需解析+校验，可能幻觉/跑偏） | **类型化结构化值**，答案空间**预先定义**，**不会产生类型错误** |
| 采样方式 | 自回归，逐 token 顺序生成 | **并行**，一次查询生成全部输出 |
| 延迟 | 前沿模型 3–329 秒 | **70–500 ms** |
| 价格 | 输入 $0.20–$10 / MTok，输出约为输入 5 倍 | **输入 $0.042 / MTok，输出免费** |
| 置信度 | 即使要求也常过度自信、不一致 | **每个输出都带校准概率**，置信度越高准确率越高 |
| 适用 | 人机协作（chatbot、copilot、coding agent） | **AI 驱动的工作流 / "智能 if 语句"**、大数据 map-reduce、实时应用、给 LLM 做校验/护栏 |

### 2.3 一句话理解

> **Jev = 一个"可以做模糊判断的函数调用"**：输入是状态，输出是你在代码里预先定义好的那几个答案之一，外加一个可信度。
> 控制流、阈值、副作用**全部留在你自己的代码里**。

---

## 3. 作用（它到底解决什么问题）

1. **替代脆弱的硬编码 if-else**：判断规则写不清楚、边界情况太多时，用 Jev 做"模糊判断"，但结果仍是有限枚举，可放心分支。
2. **替代昂贵的生成式 LLM 调用**：大多数场景真正需要的不是"一段话"，而是"一个判断"，用 Jev 可把延迟和成本降两个数量级。
3. **给 LLM 系统做护栏**：给 prompt、推理链、输出打分、判定越狱、做校验。
4. **可自动化的前提是能表达"我不确定"**：Jev 的 confidence 让代码能在"自动执行 / 谨慎处理 / 转人工"之间分流。
5. **大规模数据处理**：把 PB 级数据转成特征和洞察（价格低到可以批量跑）。

---

## 4. 使用场景

官方给出的场景地图可归纳为六类动作：**classify（分类）、route（路由）、score（打分）、extract（抽取）、verify（校验）、gate（闸门/兜底）**。

| 场景 | 适合的提问类型 | 例子 |
|---|---|---|
| 工单分类 / 意向路由 | Choice | "这张工单属于 billing / technical / account 哪一类？" |
| 优先级 / 紧急度判定 | Noul | "这条消息表达了紧急诉求吗？" |
| 评分、风控、质量打分 | Score | "这位客户的愤怒程度 0=平静 1=不满 2=非常愤怒" |
| 退款 / 合规 / 政策判定 | Noul（多条并行） | "是否请求退款？""证据是否显示重复扣款？""政策是否支持退款？" |
| 实体抽取、字段校验 | Choice + Noul | "从候选人中选出正确的那一个" |
| Agent 护栏、LLM 输出校验 | Noul / Score | "这段回复是否泄露了 PII？" |
| 实时交互 UX | 全部 | 100ms 级别，可以放进实时界面 |
| 复合评分 | Score 多条 + 代码加权 | 把复杂判断拆成原子分数，权重由代码控制 |

---

## 5. 三个核心原语（Primitives）

所有请求都是"**一个 state + 一张 question 映射表**"，三种问题可混在**同一次调用**里，全部并行求值。

### 5.1 Noul — 是/否问题
返回"答案为 yes 的概率"。**（注意：Noul 答案不附带 `confidence` 字段。）**

```json
{
  "is_urgent": {
    "type": "noul",
    "instructions": "Does this convey urgency?",
    "criteria": {
      "true": "Explicitly time-sensitive",
      "false": "No urgency expressed"
    }
  }
}
```

> ⚠️ 不确定点：`noul` 这个命名不是常规英文词，官方文档也**未给出词源解释**。功能上它就是 boolean-with-probability。遇到这个名字不要困惑。

### 5.2 Choice — 从你定义的集合中选一个
答案包含：被选项、**每个选项的概率分布**、confidence。

```json
{
  "department": {
    "type": "choice",
    "instructions": "Which team should handle this ticket?",
    "criteria": {
      "billing": "Payment, invoice, refund, or charge issues",
      "technical": "Bugs, outages, integrations, and API problems",
      "account": "Login, profile, permissions, or plan changes"
    }
  }
}
```

### 5.3 Score — 在有序刻度上打分
答案包含：分值（可能是小数，如 `1.43`）、**每个等级的概率**、confidence、以及 level 的 legend。

```json
{
  "severity": {
    "type": "score",
    "instructions": "How severe is the reported issue?",
    "criteria": {
      "0": "Cosmetic; no impact to functionality",
      "1": "Broken or degraded feature, but workaround exists",
      "2": "Blocking issue; no workaround exists"
    }
  }
}
```

### 5.4 Confidence 与 Probability 的区别（易错点）

- `probabilities`：**概率分布**，告诉你模型在各选项间的倾向形状。
- `confidence`：把分布形状**压缩成 0–1 的一个数**（集中=高，分散=低），方便直接设阈值。
- confidence **由概率分布推导而来**，并且官方明确：**校准是在"一组预测"上度量的，不保证单个答案正确**。
- 官方建议的三段式用法：**高 → 自动执行；中 → 谨慎执行；低 → 转人工或升级给推理模型**。

### 5.5 结构化提问（进阶）

`instructions`、Choice 的选项描述、Score 的等级描述、Noul 的 criteria **都接受 JSON 对象或数组**，而不只是字符串。用于：问题有多个部分时更清晰；或直接把 schema / taxonomy / 数据库行喂进去。

---

## 6. 安装与配置

### 6.1 前置：拿 API Key
在控制台获取：`https://console.typesafe.ai/keys`（Playground：`https://console.typesafe.ai/playground`）

环境变量统一为：

```bash
TYPESAFE_API_KEY=...
```

### 6.2 HTTP 接口（最底层，任何语言可用）

```http
POST https://api.typesafe.ai/v1/systemone
Authorization: Bearer <API_KEY>
Content-Type: application/json
```

### 6.3 Python SDK

```bash
uv add typesafe-sdk
```

### 6.4 JavaScript / TypeScript SDK

```bash
npm install @typesafe-ai/sdk
```
要求 **Node.js 20 或更高**。包内含 ESM、CommonJS 和 TypeScript 声明。

### 6.5 社区包 `jev`（装饰器风格，非官方 SDK）

PyPI 上的 `jev`（v0.3.0，`requires_python >= 3.14`）是一个把**函数签名直接编译成 Jev 请求**的封装：

```bash
uv sync        # 需要 Python 3.14
```

它把「函数名 = 决定什么、参数 = 依据什么、返回注解 = 答案形状、docstring = 判断标准」当成完整规格，不需要维护 prompt 字符串或 JSON schema。

> ⚠️ **不确定性**：`jev` 这个 PyPI 包**不是官方 SDK**（官方 SDK 是 `typesafe-sdk` / `@typesafe-ai/sdk`）。Python 3.14 这个版本要求相当激进，使用前请确认可用性。

---

## 7. 基本用法示例

### 7.1 cURL

```bash
curl -X POST https://api.typesafe.ai/v1/systemone \
  -H "Authorization: Bearer $TYPESAFE_API_KEY" \
  -H "Content-Type: application/json" \
  -d @- <<'EOF'
  {
    "state": "Hi, I've been trying to connect my Stripe account for 3 days and the integration keeps failing. I'm losing sales. Please help ASAP.",
    "model": "jev-latest",
    "questions": {
      "urgency": {
        "type": "noul",
        "instructions": "Does this message express urgency?"
      }
    }
  }
EOF
```

### 7.2 Python SDK

```python
from typesafe_sdk import Choice, TypeSafeClient

with TypeSafeClient() as client:
    response = client.system_one(
        state={"document": "I was charged twice. Please fix this ASAP."},
        questions={
            "category": Choice(
                instructions="What is this ticket about?",
                criteria={"billing": None, "technical": None, "other": None},
            ),
        },
    )

print(response.choices["category"].choice)
```

### 7.3 JavaScript / TypeScript SDK

```ts
import { choice, TypeSafeClient } from "@typesafe-ai/sdk";

const client = new TypeSafeClient();
const response = await client.systemOne({
  state: { document: "I was charged twice. Please fix this ASAP." },
  questions: {
    category: choice("What is this ticket about?", {
      billing: null,
      technical: null,
      other: null,
    }),
  },
});

console.log(response.answers.category.choice);
```

> 类型会从 questions 自动推断。

### 7.4 结构化 state（推荐的复杂场景写法）

```json
{
  "ticket": {
    "subject": "Duplicate charge",
    "messages": [
      {"from": "customer", "text": "I was charged twice for order A-104. Please refund the duplicate."},
      {"from": "support", "text": "We are checking the charges."}
    ]
  },
  "order": {
    "id": "A-104",
    "charges": [
      {"amount_usd": 49, "status": "captured"},
      {"amount_usd": 49, "status": "captured"}
    ]
  },
  "refund_policy": "Duplicate charges are ..."
}
```

### 7.5 社区装饰器风格（`jev` 包）

```python
from typing import Literal
from pydantic import BaseModel, Field
import jev

class Triage(BaseModel):
    department: Literal["billing", "technical", "sales"]
    is_urgent: bool
    frustration: int = Field(ge=0, le=2)

@jev.fn
def triage(ticket: str) -> Triage:
    """A customer support ticket:

    {{ ticket }}
    """
    return triage.state()

triage("I was charged twice. Fix this NOW.")
# Triage(department='billing', is_urgent=True, frustration=2)
```

机制：装饰时就校验返回注解必须是 `BaseModel` 子类（否则 import 时报 `TypeError`）；docstring 用 Jinja2 渲染成 `state`；答案由 pydantic 校验回填。

---

## 8. 最佳实践

### 8.1 架构原则（官方立场）
**代码保持控制权，只把窄而具体的判断交给 Jev。** 即：Jev 负责"判断"，代码负责"控制流、阈值、副作用"。

### 8.2 四个官方推荐模式

| 模式 | 做法 | 收益 |
|---|---|---|
| **Speculative Fan-Out（投机扇出）** | 一次调用里发很多问题，**包括当下不一定用得上的**，由代码决定哪些相关 | 成本、速度 |
| **Confidence-Gated Routing（置信度门控路由）** | 把 confidence 当作**第二决策轴**：答案告诉你"是什么"，置信度告诉你"该不该动手" | 可靠性、安全 |
| **Composite Scoring（复合评分）** | 把复杂判断拆成**原子化**的多个 Score，再用**你自己在代码里掌握的权重**合并 | 成本、可靠性、速度 |
| **Intent Routing（意图路由）** | 先分类意图，再路由到最优处理器：确定性逻辑 / 专家 LLM / 人工 | 成本、速度 |

### 8.3 实战建议
1. **优先用 object 形式的 state**，让每块内容有名字、关系清晰；只有极简场景才用裸字符串。
2. **把领域规则和边界情况写进 `instructions` / `criteria`**——Jev 不做微调，所有领域适配都靠请求本身。
3. **拆细问题**：宽泛判断拆成原子问题，在代码里组合，比让模型一次做综合判断更可靠。
4. **有阈值就不要用别名**：如果你按某个版本调过 confidence 阈值，**请固定版本 ID（如 `jev-1.13.0`）而不是用 `jev-latest`**，否则别名漂移会静默改变行为。
5. **记录响应里的 `model` 字段**：它返回实际应答的版本化 ID，便于溯源（别名会移动）。
6. **非英文场景先自测**：英文是主要训练语言，表现最好；**中文等 CJK 可用但准确率较低**，且要特别关注 confidence。

### 8.4 明确不要做的事
- ❌ 不要用它生成文字、写代码、要解释——它做不到。
- ❌ 不要把它当通用 LLM 的替代品。
- ❌ 不要因为"有概率"就假设单个答案一定正确（校准是群体性质）。

---

## 9. 常见问题 / 限制（踩坑清单）

| 项 | 说明 |
|---|---|
| **只能输入文本** | state 必须是 string、JSON object 或 text array。**图片、音频、视频暂不支持**，需先转成文本/结构化字段。 |
| **上下文长度** | 64k tokens/请求；其中 **`state` + 最长单个问题 合计 32k**。state 越长准确率会变化（官方有一篇 *Jev 1.13 jaggedness* 专门讲）。 |
| **限流会动态调整** | 当前 250,000 tokens/秒、1,200 请求/分钟；**官方明说会不预先通知地变化**。超限返回 `429`。官方 SDK 默认带退避重试并遵守 `retry-after`；自己调 HTTP 要处理限流。 |
| **定价** | 目前 $42 / Btok = $0.042 / Mtok（**按输入计费，输出免费**）。官方坦承"无法证明没有补贴"。 |
| **模型别名会漂移** | `jev-latest` / `jev-preview` 目前都指向 `jev-1.13.0`；`jev-preview` 在有预览版时会先于 latest 前移。 |
| **不做微调** | 所有账号共用同一份权重，**不会用客户数据做 LoRA / 微调**；领域适配只能靠 prompt 里的 state 和 criteria。 |
| **数据使用** | 官方称**不用客户请求/响应训练**；企业版有 ZDR（零数据保留）。 |
| **单个答案不保证正确** | 校准是跨预测组度量的，不是单条保证。 |
| **`noul` 没有 confidence** | Noul 答案不带 confidence 字段，只有 yes 概率。 |
| **状态会变** | 产品行为、价格、限额、别名都可能变——所以本文档所有数字都标了日期。 |

---

## 10. ⚠️ 不确定性与风险标注（重要）

1. **最高风险：是否真是这个 Jev**。虽然证据强，但用户只写了三个字母。**这是必须确认的第一件事。**
2. **产品极新**：2026-09-15 才发布，处于 **early access**，本文档所有规格**随时可能过时**。
3. **第三方生态资料不可信**：GitHub 上 7,471 个 `jev` 相关仓库绝大多数是发布后数天内涌现的。多个知名 awesome 列表**自己就在警告**"同日批量提交、共用脚手架、提交历史很薄"的项目属于**未被验证的线索，而非可用工具**。部分仓库的 star 增长速度（几天内上万 star）**明显异常**，有刷量嫌疑，请勿据此判断质量。
4. **抓取时点为 2026-09-21**：`awesome-jev` 系列列表自述"快照审阅：2026-09-19"，非官方仓库。
5. **上表中的数字均来自官方页面转述**，本文档未做独立复现验证。

---

## 11. 需要用户确认的关键点

请确认以下几项，我据此把草稿转成正式文档或继续深挖：

1. **"jev" 是否指 TypeSafe AI 的 Jev 模型？**（对比候选：乙型脑炎病毒 JEV / 内部代号 / 其他）
2. **你的使用角色是**：只是想理解概念（学习笔记）？还是要真的接入 API 写代码？
3. **主语言**：Python 还是 TypeScript？（决定我保留哪套示例、是否延伸 `jev` 装饰器包）
4. **是否与 ToDoList 项目相关**：是要给 ToDoList 加"智能判断"能力（如任务优先级自动判定），还是纯知识学习？若是前者，我可以直接给一份接入方案。
5. **中文场景**：官方明确中文准确率低于英文，若你的实际输入是中文，需要额外做置信度门控设计——要不要我补一节？
6. **文档归属**：确认放在 `Jev/` 目录，文件名与是否拆分（单文件 vs 多篇）。

---

## 12. 参考来源

- 官方博客（发布公告）：https://typesafe.ai/blog/introducing-system-one-models-and-jev
- 官方文档首页 / 索引：https://docs.typesafe.ai/ ，索引 https://docs.typesafe.ai/llms.txt
- 快速开始：https://docs.typesafe.ai/introduction/quickstart
- System One 概念：https://docs.typesafe.ai/concepts/system-one
- State：https://docs.typesafe.ai/concepts/state
- 原语：https://docs.typesafe.ai/primitives （/choice, /score, /noul, /advanced）
- 置信度：https://docs.typesafe.ai/confidence
- 如何构建：https://docs.typesafe.ai/concepts/how-to-build-with-system-one
- 模式：https://docs.typesafe.ai/patterns
- 模型/价格/限额：https://docs.typesafe.ai/models
- API 参考：https://docs.typesafe.ai/api
- 控制台：https://console.typesafe.ai （Playground / Keys）
- 官方 SDK（Python）：https://github.com/typesafe-ai/typesafe-sdk-python
- 官方 SDK（JS/TS）：https://github.com/typesafe-ai/typesafe-sdk-js
- 官方 Agent skills：https://github.com/typesafe-ai/skills
- 社区装饰器包：https://pypi.org/project/jev/
- 社区列表（**非官方，仅供参考**）：`Anil-matcha/awesome-jev-by-typesafe`、`yibie/awesome-jev`
