# 2026-11-05（周四）· Function Calling / Tool Use：让模型"能做事"

> 轨道 1 · W2 Prompt 工程与工具调用 · 第 4 讲（承接 11-04「结构化输出」）｜ W2 收官

## 0 速览（30 秒读完）
- 今日主题：给模型一张"工具清单"，它就从一个"会说话的"变成一个"**会让你去执行的**"——注意，它**只输出意图，永远不真的执行**。
- 学完你能做到：写通一个完整的工具调用循环（声明 → 收 `tool_calls` → 你的代码执行 → 以 `role: "tool"` 回传 → 拿最终答案），并知道该在哪里设防。
- 预计时长：2 小时（概念 30 / 代码 40 / 动手 20 / 动态 20 / 收尾 8）

---

## 1 概念精讲（30 min）

**一句话定义**
工具调用（Function Calling / Tool Use）= 你在请求里声明"我有哪些函数可用（名字、用途、参数 schema）"，模型在需要时**返回一个结构化对象说"请调用 get_weather，参数是 city=北京"**；真正调用的是**你的代码**，结果再由你以 `role:"tool"` 回传，模型据此给出最终回答。

> 一句话记住它的本质：**模型是"提议者"，不是"执行者"**。这条边界不是设计缺陷，而是**安全模型**——它把"能不能真的删库"的决定权牢牢留在你的代码里。

**它解决什么问题 / 为什么现在必须懂**
1. 昨天解决的是"输出**数据**"，今天解决的是输出**动作**。这是 **Agent 的地基**（W4 会把今天这个循环套上"多轮 + 规划"）。
2. 它把模型从"知识截止日期"里解放出来：模型不知道今天的汇率、你的库存、用户的订单状态——但它可以**去查**。
3. 反向来说，**凡是"精确事实"和"副作用操作"都应该走工具**，而不是指望模型的思维链（11-03 已论证 CoT 只提升推理可靠性，不提升事实准确性）。

**关键机制：一个完整的往返**

```
第 1 轮  你 ──► 模型
   messages: [{"role":"user","content":"北京今天天气怎么样？"}]
   tools:    [{"type":"function","function":{
                 "name":"get_weather",
                 "description":"查询指定城市当前天气",          ← ★ 模型选工具的唯一依据
                 "parameters":{...JSON Schema...}}}]           ← ★ 与昨天学的 schema 同一套东西

第 1 轮  模型 ──► 你
   finish_reason: "tool_calls"                                     ← ★ 不是 "stop"
   message.tool_calls: [{"id":"call_xxx","type":"function",
                         "function":{"name":"get_weather",
                                     "arguments":"{\"city\": \"北京\"}"}}]
                                                          ↑★ 注意：是一段【JSON 字符串】，不是对象

   ┌────────────── 到这里模型就停下了，它不会自己执行 ──────────────┐

第 2 轮  你 ──► 执行 get_weather("北京") → "晴，26℃"

第 2 轮  你 ──► 模型（把模型上一轮的 message 原样放回，再追加一条 tool 消息）
   messages: [..., 
      {"role":"assistant","content":null,"tool_calls":[...]},      ← ★ 必须放回，否则模型不知道在回什么
      {"role":"tool","tool_call_id":"call_xxx","content":"晴，26℃"} ]  ← ★ tool_call_id 必须对应
   tools: 还是同一份（一般也要带上）

第 2 轮  模型 ──► 你
   finish_reason: "stop"
   content: "北京今天天气晴，气温约 26℃。"                             ← ★ 自然语言最终答案
```

**三条不能错的规矩**
1. **`arguments` 是字符串**，必须 `json.loads`。直接当字典用会炸。
2. **每个 `tool_call` 都必须回一条 `role:"tool"` 消息**，且 `tool_call_id` 一一对应。模型一次返回 3 个调用，你只回了 2 个 → 400（或行为诡异）。
3. **模型上一轮那条含 `tool_calls` 的 `assistant` 消息必须原样放回历史**。少了它，`role:"tool"` 消息就变成了"没有来由的一句话"。

**⚠️ 本机实测：这套端点完整支持工具调用（2026-11-05 实跑，非杜撰）**

```
第 1 轮  finish_reason = tool_calls
        tool_calls = [{"id":"call_G6yY0OqY17MxjulIYPFl0fuq","type":"function",
                       "function":{"name":"get_weather",
                                   "arguments":"{\"city\":\"北京\"}"}}]

第 2 轮（回传 "晴，26℃"） finish_reason = stop
        content = "北京今天天气晴，气温约 26℃。"
```

两点值得注意：
- 模型把参数**规范成了 `{"city":"北京"}`**（提示里我说的是"北京今天天气怎么样"，它正确地只抽出了城市）。
- 第 2 轮的最终答案里**包含了工具返回的"26℃"**——这说明回传链路是通的（这是判断"工具调用到底有没有生效"最快的方法）。

**常见误区**
1. **"模型帮我执行了函数。"** 没有。模型**永远不会**执行任何代码。它只是输出一段结构化文本说"我想调这个"。**所有副作用都发生在你的进程里，所以权限、幂等、审计都在你手上。**
2. **"工具名和参数名起得随意点没关系。"** `description` 是模型**选择工具的唯一依据**。两个工具描述含糊相似，模型必然选错。这是工具调用里 ROI 最高的调优点：**把 description 当成给新同事看的接口文档来写**。
3. **"循环可以一直转。"** 必须设 `max_iterations`。否则模型可能"调工具 → 不满意 → 再调 → 再不满意"无限循环，烧钱直到超时。
4. **"工具越多越强。"** 相反。工具清单本身占 prompt token，而且**工具越多，选错的概率越高**。经验做法：**按场景分组**（查数据的 / 改数据的分开给），而不是一次把 30 个工具全塞进去。

**📝 我的复述（这段留空给用户自己写，不要代写）：**


---

## 2 代码片段（40 min）

- **场景**：一个**可直接运行的完整工具调用循环**——不是玩具示例，而是带**最大迭代保护、参数解析容错、工具白名单、危险操作拦截**的骨架。后面 W4 的 Agent 就是把这份骨架加上"规划"和"记忆"。
- **依赖与版本**：**零第三方依赖**（仅 Python 标准库 `json` / `urllib.request`，Python 3.9+ 直接可跑）；端点用本机 DHwork 的 `https://www.dhcoder.net/llm-api/v1`。

**① 工具定义与实现 `tools.py`**

```python
# tools.py —— 工具注册表：声明（给模型看的 schema）与实现（真正执行的函数）放在一起
import json
import os
from typing import Any, Callable, Dict, List

# ★ 中文注释：这里是"实现"，模型永远看不到这些函数体，它只看得到下面的 SCHEMA
def get_weather(city: str) -> str:
    """真实项目里这里会调天气 API；示例里返回固定值。"""
    table = {"北京": "晴，26℃", "上海": "多云，24℃", "广州": "雷阵雨，30℃"}
    return table.get(city, f"{city}：暂无数据")


def get_learning_progress(date: str) -> str:
    """示例：查本机 AI 每日学习的进度（把真实文件读出来，证明这是真代码不是玩具）。"""
    path = "/Users/alion/DemoProjects/ToDoList/AI每日学习/00_进度/进度.md"
    try:
        with open(path, encoding="utf-8") as f:
            lines = [l for l in f if date in l]
        return "\n".join(lines) if lines else f"{date} 没有学习记录"
    except FileNotFoundError:
        return "进度文件不存在"


class Tool:
    def __init__(self, name: str, description: str, parameters: Dict[str, Any],
                 func: Callable[..., str], dangerous: bool = False):
        self.name = name
        self.description = description      # ★ 写得越清楚，模型选得越准
        self.parameters = parameters
        self.func = func
        self.dangerous = dangerous          # ★ 标记"有副作用"的工具，走人工确认

    def to_spec(self) -> Dict[str, Any]:
        """转成 API 要求的 tools 字段格式。"""
        return {"type": "function", "function": {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
        }}


REGISTRY: List[Tool] = [
    Tool(
        name="get_weather",
        # ★ description 是模型唯一的选型依据：写清"什么时候用"和"什么时候别用"
        description="查询中国城市当前的天气。参数必须是城市的中文名（如『北京』）。"
                    "不要用它查未来天气或历史天气。",
        parameters={
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "城市中文名，例如 北京"},
            },
            "required": ["city"],
            "additionalProperties": False,      # ★ 沿用 11-04 的 schema 三规则
        },
        func=get_weather,
    ),
    Tool(
        name="get_learning_progress",
        description="查询某个日期的 AI 学习记录，日期格式 YYYY-MM-DD。",
        parameters={
            "type": "object",
            "properties": {"date": {"type": "string", "description": "日期，格式 YYYY-MM-DD"}},
            "required": ["date"],
            "additionalProperties": False,
        },
        func=get_learning_progress,
    ),
]

BY_NAME = {t.name: t for t in REGISTRY}
```

**② 循环骨架 `agent_loop.py`**

```python
# agent_loop.py —— 工具调用循环：零依赖（只用标准库），带迭代上限、参数容错、危险操作拦截
import json
import os
import urllib.request
from typing import Any, Dict, List

from tools import REGISTRY, BY_NAME

URL = "https://www.dhcoder.net/llm-api/v1/chat/completions"
TOKEN = os.environ["DHWORK_TOKEN"]
MODEL = "gpt-5.6-terra-dhwork"
MAX_ITERATIONS = 5      # ★ 硬上限：没有它，模型可能无限调工具烧钱


def chat(messages: List[Dict[str, Any]], tools: List[Dict[str, Any]]) -> Dict[str, Any]:
    """发一次请求，返回 choices[0]（含 message 与 finish_reason）。"""
    body = {"model": MODEL, "messages": messages, "tools": tools, "max_tokens": 900}
    req = urllib.request.Request(
        URL, data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + TOKEN},
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode("utf-8"))["choices"][0]


def execute_tool_call(call: Dict[str, Any]) -> Dict[str, str]:
    """执行【一个】tool_call，返回可直接放进 messages 的 tool 消息。"""
    name = call["function"]["name"]
    tool = BY_NAME.get(name)
    if tool is None:                       # 模型可能编出不存在的工具名（工具多时尤其常见）
        return {"role": "tool", "tool_call_id": call["id"],
                "content": f"错误：不存在名为 {name} 的工具"}

    # ★ arguments 是【JSON 字符串】；模型偶尔产出坏 JSON，要兜住
    try:
        args = json.loads(call["function"].get("arguments") or "{}")
    except json.JSONDecodeError as e:
        return {"role": "tool", "tool_call_id": call["id"],
                "content": f"错误：参数不是合法 JSON（{e}）。请重新调用并只输出合法 JSON。"}

    # ★ 危险操作不自动执行：真实产品里这里挂人机确认（Android 上就是一个弹窗）
    if tool.dangerous:
        return {"role": "tool", "tool_call_id": call["id"],
                "content": "该操作需要用户确认，已暂停。"}

    try:
        result = tool.func(**args)         # 真正执行
    except TypeError as e:                 # 参数名/数量不匹配
        return {"role": "tool", "tool_call_id": call["id"], "content": f"错误：参数不匹配（{e}）"}
    except Exception as e:                 # 工具内部异常也要回给模型，让它自己改
        return {"role": "tool", "tool_call_id": call["id"], "content": f"工具执行失败：{e}"}

    return {"role": "tool", "tool_call_id": call["id"], "content": str(result)}


def run(user_input: str) -> str:
    messages: List[Dict[str, Any]] = [{"role": "user", "content": user_input}]
    tools = [t.to_spec() for t in REGISTRY]

    for step in range(MAX_ITERATIONS):
        choice = chat(messages, tools)
        msg = choice["message"]

        if choice.get("finish_reason") != "tool_calls":     # ★ 唯一的正常出口
            return msg.get("content") or ""

        # ★ 把含 tool_calls 的 assistant 消息【原样】放回历史，否则 tool 消息没有来由
        messages.append(msg)
        # ★ 一个都不能漏：返回几个 tool_calls 就回几条 tool 消息
        for call in msg["tool_calls"]:
            messages.append(execute_tool_call(call))
        print(f"  [第 {step + 1} 轮] 执行了 {len(msg['tool_calls'])} 个工具调用")

    return "（达到最大迭代次数，已终止）"


if __name__ == "__main__":
    for q in ["北京今天天气怎么样？",
              "帮我看看 2026-10-31 那天学了什么",
              "上海和广州哪个更热？"]:                      # 最后这个会触发【并行】两个调用
        print(f"\n>>> {q}")
        print("<<<", run(q))
```

**本机实测输出（2026-11-05 实跑，非杜撰；`tools.py` + `agent_loop.py` 均从本讲正文原样抽出执行）**

```
>>> 北京今天天气怎么样？
  [第 1 轮] 执行了 1 个工具调用
<<< 北京今天天气晴，气温 26℃。

>>> 帮我看看 2026-10-31 那天学了什么
  [第 1 轮] 执行了 1 个工具调用
<<< 2026-10-31 学习主题是 **采样参数与可控生成**，属于「01_地基 · W1」第 3 讲。

>>> 上海和广州哪个更热？
  [第 1 轮] 执行了 2 个工具调用
<<< 广州更热：广州当前 **30℃**，上海 **24℃**，广州高 **6℃**。
```

> 第三个问题是最有价值的：模型在一次响应里返回了**两个** `tool_calls`（查上海 + 查广州），循环里用 `for` 把它们都执行并回传，模型才拼出对比结论。**如果你写的是 `msg["tool_calls"][0]`，这一步就直接崩了。**

- **逐行要点**
  - `finish_reason != "tool_calls"` 是**唯一的正常出口**。写成 `if msg.content:` 是错的——有些模型在工具调用轮也会带一点 content。
  - `messages.append(msg)` 必须在追加 tool 消息**之前**，且**原样放回**（本实现里 `msg` 就是响应里的那个字典）。手写一个 `{"role":"assistant","content":""}` 会丢掉 `tool_calls` 字段，第二轮直接 400。
  - `execute_tool_call` 里**每一类失败都返回一条 tool 消息**而不是抛异常：**因为"错误"也是模型需要的信息**——它看到"参数不是合法 JSON"就会自己改。这跟 11-04 把校验错误喂回去是同一个套路。
  - `MAX_ITERATIONS = 5`：不是形式主义。真实项目里工具报错 + 模型反复重试是最常见的烧钱方式。
- **踩坑提示**
  1. **`arguments` 是字符串，不是对象**：`call.function.arguments` 用 `json.loads` 之后才能 `**args` 展开。当成 dict 用必然 AttributeError。
  2. **并行工具调用要全部回传**：一句"上海和广州哪个更热"会返回**两个** `tool_calls`。只回一个 → 报错。**用 `for` 循环遍历，别写 `[0]`。**
  3. **流式模式下 `tool_calls` 是分片到达的**：`delta.tool_calls[i].function.arguments` 每次只来几个字符，必须**按 `index` 拼接**完再 `json.loads`。这是"非流式能跑、流式就崩"的经典原因。
  4. **别把危险工具直接暴露**。`delete_order`、`transfer_money` 这类要么不给模型，要么走"人确认"。**模型的输出是不可信输入**——这一条和 11-04 的输出校验是同一件事的两面。

---

## 3 动手 / 联想（20 min）

- **动手任务（20 分钟）**：给 `tools.py` 加第三个工具 `list_learning_files()`——读你本机 `AI每日学习/01_地基/` 目录、返回文件名列表。然后用两个问题测试它会不会**选对工具**：① "我这周学了哪些主题？"（该选它）② "北京天气怎么样？"（不该选它）。如果选错了，**别改代码，改 `description`**——你会亲身感受到"工具描述就是接口文档"这句话。
- **与我的工作结合**
  - **Android**：这是把"App 的既有能力"变成"AI 可调用能力"的最短路径。把 `发送通知`、`查询本地数据库`、`打开某个页面`、`设置闹钟` 各包一层函数 + 一份 schema，你就得到了一个"自然语言控制 App"的雏形——**而且全程不联网也能跑端侧那部分**。安全上必须做三级：读类工具直接放行、写类工具弹确认、删除类工具不暴露给模型。
  - **前端 / 小程序**：把"跳转页面"包成工具（`navigate_to(page, params)`），用户说"我要看我的优惠券"就直接跳过去——比关键词匹配准得多。注意**工具的 `description` 要写清楚 App 里真实存在的页面名**，否则模型会编出"我的钱包"这种不存在的路由。

---

## 4 动态与机会（20 min）

- 🔥 **新动向（2 条）**
  - **arXiv《CAREFUL-Bench: Effect-Aware, Judge-Free Evaluation of Multi-Turn LLM Function Calling》** — 针对**多轮**工具调用的评测基准，而且强调"看效果、不用裁判模型"，直接打在工具调用最难的地方：**多轮之后还能不能选对工具、配对是否正确**。这是我做 Agent 时一定会用到的检查视角。 — [arXiv:2611.02978](http://arxiv.org/abs/2611.02978)（论文实际提交日 2026-11-02）
  - **Google Developers Blog《Hill-Climbing Agent Quality with Agents CLI Evaluation》** — 把"Agent 质量提升"变成可循环的评测流程（跑评测 → 找短板 → 改 → 再跑），跟我这两讲在做的"跑对照实验再决定"是同一条路，只是被产品化成了工具链。 — [Google Developers Blog](https://developers.googleblog.com/hill-climbing-agent-quality-with-agents-cli-evaluation/)
- 💼 **岗位观察（1 条）**
  - **腾讯 · 元宝 大模型应用平台产品经理（北京）** — 注意这是**产品岗**而不是算法岗，说明"大模型应用"的岗位面已经从研发扩到产品：这类岗位要求的核心能力是**把业务动作拆成工具与流程**——正是今天这讲在做的事。对我（技术背景想转 AI 应用）来说，这是一个**技术优势能直接迁移、且竞争更小**的方向，值得纳入视野。 — [腾讯招聘](https://careers.tencent.com/jobdesc.html?postId=2052733034666573824)（更新于 2026-11-05）
- 🧰 **其他有价值信息（1 条）**
  - **openai-agents-python（GitHub，3 万 star）** — 官方轻量 Agent 框架，`@function_tool` 装饰器把"函数 → 工具 schema"自动化掉了，是今天手写那套的成品版；**建议先手写一遍再上框架**——手写过才知道它替你兜了哪些坑（并行调用、参数解析、错误回传）。 — [GitHub](https://github.com/openai/openai-agents-python)

---

## 5 明日预告与待复习（8 min）

- **明日主题**：RAG 全链路开篇（W3）——**文本切片（Chunking）**。进入"给模型一本资料书"的第一环：为什么切得好不好，直接决定检索找不找得到。
- **待复习（3 条，今天必须记住）**
  1. 模型**只提议、不执行**：`finish_reason="tool_calls"` 时它停下了，执行永远在你的代码里。
  2. 三条铁律：**`arguments` 是 JSON 字符串**、**每个 call 都要回一条 `tool` 消息**、**含 `tool_calls` 的 assistant 消息要原样放回历史**。
  3. **`description` 是模型选工具的唯一依据**——工具选错，先改描述，别先改代码。
- **一句话复盘**：最容易忘的是——**工具调用是一个"你来实现一半"的协议**：模型负责"决定调什么"，你负责"执行 + 回传 + 兜错 + 设上限"，这四件事少一件，Agent 就跑不起来（W4 见）。
