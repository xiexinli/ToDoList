/**
 * 浏览器冒烟（Playwright + 本机 chromium）：对 `vite preview --port 4174` 的页面
 *  ① 主流程：上传客户 xlsx → 生成 → 覆盖矩阵缺失 0 → 下载 zip → 条目数 70 → 截图
 *  ② 异常流：上传 prd_dirty.csv + 基线 zip → 生成 → 缺失 > 0、报告面板有 missing/placeholder/forbidden/conflict
 *  ③ 异常流：无 en 列的 csv → 错误横幅
 * 用法：node scripts/browser-smoke.mjs [baseURL]
 */
import { chromium } from "playwright";
import JSZip from "jszip";
import fs from "node:fs";
import path from "node:path";
import assert from "node:assert/strict";

const base = process.argv[2] ?? "http://localhost:4174/";
const root = path.resolve(import.meta.dirname, "..");
const spec = path.join(root, ".kiro/specs/multilang-gen");
const errors = [];

const browser = await chromium.launch();
const ctx = await browser.newContext({ viewport: { width: 1200, height: 1400 }, acceptDownloads: true });
const page = await ctx.newPage();
page.on("console", (m) => { if (m.type() === "error") errors.push(`console.error: ${m.text()}`); });
page.on("pageerror", (e) => errors.push(`pageerror: ${e.message}`));

// ① 主流程
await page.goto(base);
await page.getByTestId("prd-file").setInputFiles(path.join(root, "materials/prd_multilang_sample.xlsx"));
await page.getByTestId("generate").click();
await page.getByTestId("coverage").waitFor();
const summary = await page.getByTestId("summary").innerText();
console.log("summary:", summary);
assert.match(summary, /文件 70/);
assert.match(summary, /缺失 0/);
const missCells = await page.locator('[data-testid="coverage"] td.miss').count();
assert.equal(missCells, 0, "矩阵不应有红格");
const okCells = await page.locator('[data-testid="coverage"] td.ok').count();
assert.equal(okCells, 70, "矩阵应有 70 个绿格");
const [download] = await Promise.all([page.waitForEvent("download"), page.getByTestId("download").click()]);
const zipPath = path.join(spec, "demo", "browser-download.zip");
await download.saveAs(zipPath);
const zip = await JSZip.loadAsync(fs.readFileSync(zipPath));
const entries = Object.keys(zip.files).filter((f) => !zip.files[f].dir);
assert.equal(entries.length, 70, "下载 zip 应有 70 个文件");
assert.ok(entries.includes("ios/sv.lproj/Localizable.strings") && entries.includes("android/values-ko/strings.xml"));
console.log(`download: ${download.suggestedFilename()} entries=${entries.length}`);
const hist = JSON.parse(await page.evaluate(() => localStorage.getItem("multilang-gen:history") ?? "[]"));
assert.equal(hist.length, 1, "localStorage 应有 1 条历史");
assert.equal(hist[0].fileCount, 70);
await page.screenshot({ path: path.join(spec, "demo-browser.png"), fullPage: true });
console.log("screenshot: .kiro/specs/multilang-gen/demo-browser.png");

// ② 异常流：脏样本 + 基线 zip
await page.getByTestId("prd-file").setInputFiles(path.join(root, "materials/synthetic/prd_dirty.csv"));
await page.getByTestId("baseline-file").setInputFiles(path.join(spec, "demo/baseline-synthetic.zip"));
await page.getByTestId("generate").click();
await page.waitForFunction(() => /跳过空行 1/.test(document.querySelector('[data-testid="summary"]')?.textContent ?? ""));
const s2 = await page.getByTestId("summary").innerText();
console.log("dirty summary:", s2);
assert.doesNotMatch(s2, /缺失 0 /);
assert.match(s2, /基线 diff：新增 \d+ \/ 相同 \d+ \/ 冲突 1/);
const report = await page.getByTestId("report").innerText();
assert.match(report, /missing（1）/);
assert.match(report, /placeholderMismatch（1）/);
assert.match(report, /forbiddenTerm（1）/);
assert.match(report, /conflicts（1）/);
assert.ok((await page.locator('[data-testid="coverage"] td.miss').count()) > 0, "脏样本应出现红格");
await page.screenshot({ path: path.join(spec, "demo-browser-dirty.png"), fullPage: true });
const hist2 = JSON.parse(await page.evaluate(() => localStorage.getItem("multilang-gen:history") ?? "[]"));
assert.equal(hist2.length, 2);

// ③ 异常流：表头无 en
const badCsv = path.join(spec, "demo", "no-en.csv");
fs.writeFileSync(badCsv, "展示文案,fr,de\n标题,Bonjour,Hallo\n");
await page.getByTestId("prd-file").setInputFiles(badCsv);
await page.getByTestId("generate").click();
await page.getByTestId("error").waitFor();
const err = await page.getByTestId("error").innerText();
console.log("error banner:", err);
assert.match(err, /PrdParseError/);
assert.match(err, /en/);

await browser.close();
if (errors.length) {
  console.log("浏览器控制台报错：\n" + errors.join("\n"));
  process.exit(2);
}
console.log("browser-smoke OK · 控制台无报错");
