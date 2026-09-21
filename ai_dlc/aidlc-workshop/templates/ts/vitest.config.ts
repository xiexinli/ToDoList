import { defineConfig } from "vitest/config";
import path from "node:path";

// live 测试（真实外部服务）默认排除；`npm run test:live`（LIVE=1）时只跑 tests/live。
const live = !!process.env.LIVE;

export default defineConfig({
  test: {
    environment: "node",
    include: live ? ["tests/live/**/*.test.ts"] : ["tests/**/*.test.ts"],
    exclude: live ? [] : ["tests/live/**", "node_modules/**"],
    testTimeout: live ? 60_000 : 5_000,
  },
  resolve: {
    alias: { "@": path.resolve(__dirname, "src") },
  },
});
