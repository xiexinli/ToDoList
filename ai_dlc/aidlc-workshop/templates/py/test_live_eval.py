"""live 评估模板：对真实模型抽样，默认不跑。

运行：uv run pytest -m live -v   （pyproject addopts 已 `-m 'not live'`）
原则：只断言确定性结果（outcome / 工具调用序列 / 语言），措辞由人在 DEMO 时判断。
每条 case 的 id 以 `ac_xx-` 开头以便 ac_status.py 归类。
"""
import json

import pytest

pytestmark = pytest.mark.live

# 按课题替换：真实 LLM 客户端、Agent、记录工具调用的后端、会话
# from my_agent import Agent, RealLLM, RecordingBackend, Session

CASES = [
    pytest.param("Requested for reset password, but never receive any email.", "<known_user_id>",
                 "in_mail_sent", ["get_system_id", "send_buyer_message"], id="ac_07-normal"),
    pytest.param("I need reset password", "<known_user_id>", "clarify", [], id="ac_08-vague"),
]


@pytest.mark.parametrize("msg, user_id, outcome, tools", CASES)
def test_live_outcome_and_tool_sequence(msg, user_id, outcome, tools, record_property):
    backend = RecordingBackend()
    agent = Agent(llm=RealLLM(), backend=backend, session=Session(user_id=user_id))
    result = agent.handle(msg)
    record_property("reply", result.reply)
    print("\nREPLY:", result.reply, "\nRESULT:", json.dumps(result.to_dict(), ensure_ascii=False))
    assert result.outcome == outcome
    assert [c.name for c in backend.calls] == tools
    assert result.is_english  # 或其他确定性语言校验
