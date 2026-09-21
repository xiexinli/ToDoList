/**
 * 集成检查点（纯前端拓扑）：真实浏览器走一遍 real 模式主流程。
 *   打开 preview 页面 → 填入临时凭证 → 切 real → 发送客户样例 c07 → 断言侧栏 outcome=in_mail_sent 与两个工具名 → 截图。
 *   同时记录浏览器 console / 失败请求，判断 Bedrock 直连有没有 CORS 问题。
 * 运行（不把 playwright 装进项目）：
 *   eval "$(aws configure export-credentials --format env)"
 *   PW_PATH=$(ls -d ~/.npm/_npx/<hash>/node_modules/playwright | head -1) node scripts/e2e-browser.mjs
 * 可选：BASE_URL（默认 http://localhost:4173）、CHROMIUM_PATH（指定 chromium 可执行文件）、SHOT（截图路径）。
 */
// 说明：上面的 <hash> 是 npx 缓存目录名，用 shell 通配即可（写在注释里会误闭合块注释，故用占位符）。
import path from "node:path";

const PW_PATH = process.env.PW_PATH;
if (!PW_PATH) throw new Error("set PW_PATH to a playwright package dir (e.g. from ~/.npm/_npx/*/node_modules/playwright)");
const { chromium } = await import(path.join(PW_PATH, "index.mjs"));

const BASE_URL = process.env.BASE_URL ?? "http://localhost:4173";
const SHOT = process.env.SHOT ?? ".kiro/specs/cs-bot/demo-browser.png";
const { AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_SESSION_TOKEN } = process.env;
if (!AWS_ACCESS_KEY_ID || !AWS_SECRET_ACCESS_KEY) throw new Error("missing AWS creds in env");

const C07 = "Requested for reset password, but never receive any email.";
const t0 = Date.now();
const browser = await chromium.launch({
  headless: true,
  args: ["--no-sandbox"],
  ...(process.env.CHROMIUM_PATH ? { executablePath: process.env.CHROMIUM_PATH } : {}),
});
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });

const consoleMsgs = [];
const failedRequests = [];
page.on("console", (m) => consoleMsgs.push(`[${m.type()}] ${m.text()}`));
page.on("pageerror", (e) => consoleMsgs.push(`[pageerror] ${e.message}`));
page.on("requestfailed", (r) => failedRequests.push(`${r.method()} ${r.url()} → ${r.failure()?.errorText}`));
const bedrockRequests = [];
page.on("response", (r) => {
  if (r.url().includes("bedrock-runtime")) bedrockRequests.push(`${r.status()} ${r.request().method()} ${r.url()}`);
});

try {
  await page.goto(BASE_URL, { waitUntil: "networkidle" });
  console.log(`page loaded in ${Date.now() - t0}ms: ${await page.title()}`);

  await page.fill('input[name="accessKeyId"]', AWS_ACCESS_KEY_ID);
  await page.fill('input[name="secretAccessKey"]', AWS_SECRET_ACCESS_KEY);
  if (AWS_SESSION_TOKEN) await page.fill('input[name="sessionToken"]', AWS_SESSION_TOKEN);
  if ((await page.textContent('[data-testid="creds-status"]')) !== "credentials set") throw new Error("credentials not registered by page");

  await page.check('[data-testid="mode-real"]');
  if ((await page.textContent('[data-testid="mode-label"]')) !== "real") throw new Error("mode did not switch to real");

  await page.fill('[data-testid="chat-input"]', C07);
  const t1 = Date.now();
  await page.click('[data-testid="send"]');
  await page.waitForSelector('[data-testid="outcome"]', { timeout: 90_000 });
  const outcome = (await page.textContent('[data-testid="outcome"]')).trim();
  const tools = await page.$$eval('[data-testid="tools"] .tool-name', (els) => els.map((e) => e.textContent.trim()));
  const summary = (await page.textContent('[data-testid="summary"]')).trim();
  const reply = await page.$$eval(".bubble.assistant p", (els) => els.at(-1)?.textContent ?? "");
  const turnMs = Date.now() - t1;
  console.log(`turn done in ${turnMs}ms\noutcome=${outcome}\ntools=${JSON.stringify(tools)}\nsummary=${summary}\nreply=${reply}`);

  const stored = await page.evaluate(() => ({
    sessions: Object.keys(JSON.parse(localStorage.getItem("cs-bot:sessions") ?? "{}")).length,
    credsInSession: !!sessionStorage.getItem("cs-bot:creds"),
    credsInLocal: !!localStorage.getItem("cs-bot:creds"),
  }));
  console.log("storage:", JSON.stringify(stored));

  await page.screenshot({ path: SHOT, fullPage: true });
  console.log(`screenshot → ${SHOT}`);

  const cors = consoleMsgs.filter((m) => /CORS|Access-Control|blocked by/i.test(m));
  console.log(`bedrock responses: ${JSON.stringify(bedrockRequests)}`);
  console.log(`console messages: ${consoleMsgs.length}${consoleMsgs.length ? "\n  " + consoleMsgs.join("\n  ") : ""}`);
  console.log(`failed requests: ${failedRequests.length}${failedRequests.length ? "\n  " + failedRequests.join("\n  ") : ""}`);
  console.log(`CORS errors: ${cors.length === 0 ? "none" : cors.join(" | ")}`);

  const ok = outcome === "in_mail_sent" && tools.join(",") === "get_system_id,send_buyer_message" && stored.sessions >= 1 && stored.credsInSession && !stored.credsInLocal;
  console.log(ok ? "E2E PASS" : "E2E FAIL");
  process.exitCode = ok ? 0 : 1;
} finally {
  await browser.close();
}
