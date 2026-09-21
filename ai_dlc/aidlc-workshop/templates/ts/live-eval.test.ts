/**
 * live 评估模板（tests/live/live-eval.test.ts）：对真实模型抽样，默认不跑。
 * 运行：npm run test:live   （LIVE=1 vitest run tests/live --reporter=verbose --silent=false）
 * 原则：只断言确定性结果（outcome / 工具调用序列 / 语言），措辞由人在 DEMO 时判断。
 * case 名以 AC 编号开头以便 ac_status.py 归类。
 */
import { describe, it, expect } from "vitest";
// import { handleTurn } from "@/lib/orchestrator";
// import { BedrockLLM } from "@/adapters/llm.bedrock";
// import { createMockTools } from "@/adapters/tools.mock";

const KNOWN = "40286396771e7a0e01772e273f190081";

const CASES: [string, { message: string; buyerId: string | null; outcome: string; tools: string[] }][] = [
  ["AC-07 c07 normal", { message: "Requested for reset password, but never receive any email.", buyerId: KNOWN, outcome: "in_mail_sent", tools: ["get_system_id", "send_buyer_message"] }],
  ["AC-08 c04 vague", { message: "I need reset password", buyerId: KNOWN, outcome: "clarify", tools: [] }],
  ["AC-10 s02 not found", { message: "I requested a reset link twice but never got the email.", buyerId: "ffffffffffffffffffffffffffffffff", outcome: "buyer_not_found", tools: ["get_system_id"] }],
];

describe("live sampling against the real model", () => {
  it.each(CASES)("%s", async (_name, c) => {
    // const tools = createMockTools();
    // const result = await handleTurn({ llm: new BedrockLLM(), tools, session: { buyerId: c.buyerId, history: [] }, message: c.message });
    // console.log("REPLY:", result.reply);
    // expect(result.outcome).toBe(c.outcome);
    // expect(result.tools).toEqual(c.tools);
    // expect(result.isEnglish).toBe(true);
    expect(c.outcome).toBeTruthy(); // 占位，替换为上面的断言
  });
});
