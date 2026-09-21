/**
 * API route 契约测试模板（Next.js App Router + Vitest）。
 * - DATA_DIR 指到临时目录，再动态 import route，保证 env 先生效。
 * - 动态路由的 params 是 Promise。
 * - 测试名带 AC 编号；describe 名不带（避免把所有 case 归到同一 AC）。
 */
import { beforeAll, afterAll, describe, it, expect } from "vitest";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

let tmp: string;
let POST: (req: Request) => Promise<Response>;
let GET_DOWNLOAD: (req: Request, ctx: { params: Promise<{ id: string }> }) => Promise<Response>;

beforeAll(async () => {
  tmp = fs.mkdtempSync(path.join(os.tmpdir(), "mvp-"));
  process.env.DATA_DIR = tmp;
  ({ POST } = await import("@/app/api/generate/route"));
  ({ GET: GET_DOWNLOAD } = await import("@/app/api/jobs/[id]/download/route"));
});

afterAll(() => fs.rmSync(tmp, { recursive: true, force: true }));

describe("POST /api/generate", () => {
  it("AC-11 上传客户样本 → 200 且返回 jobId 与 report", async () => {
    const form = new FormData();
    const bytes = fs.readFileSync(path.resolve(__dirname, "../materials/prd_multilang_sample.xlsx"));
    form.append("prd", new File([bytes], "prd.xlsx"));
    form.append("targets", "ios,android,wap,pc");
    const res = await POST(new Request("http://test/api/generate", { method: "POST", body: form }));
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.jobId).toMatch(/^\d{8}-/);
    expect(body.report.missing).toEqual([]);
    expect(fs.existsSync(path.join(tmp, "jobs", body.jobId, "report.json"))).toBe(true);
  });

  it("AC-12 未上传文件 → 400", async () => {
    const res = await POST(new Request("http://test/api/generate", { method: "POST", body: new FormData() }));
    expect(res.status).toBe(400);
  });
});

describe("GET /api/jobs/[id]/download", () => {
  it("AC-13 未知 jobId → 404", async () => {
    const res = await GET_DOWNLOAD(new Request("http://test/api/jobs/nope/download"), { params: Promise.resolve({ id: "nope" }) });
    expect(res.status).toBe(404);
  });
});
