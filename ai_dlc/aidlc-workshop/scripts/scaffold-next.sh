#!/usr/bin/env bash
# 在"非空"的 workshop 目录里从零生成 Next.js 项目（create-next-app 不接受非空目录，所以先在子目录生成再搬回来）。
# 用法：bash <skill>/scripts/scaffold-next.sh [额外 npm 依赖...]
#   例：bash .kiro/skills/aidlc-workshop/scripts/scaffold-next.sh xlsx jszip
#       bash .kiro/skills/aidlc-workshop/scripts/scaffold-next.sh @aws-sdk/client-bedrock-runtime @modelcontextprotocol/sdk zod
set -euo pipefail
SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP=".scaffold-tmp"
rm -rf "$TMP" && mkdir "$TMP"
( cd "$TMP" && npx -y create-next-app@latest app --ts --tailwind --eslint --app --src-dir --import-alias "@/*" --use-npm --yes )
rm -rf "$TMP/app/.git"
# 合并 .gitignore（保留 workshop 已有的条目）
if [ -f .gitignore ]; then cat "$TMP/app/.gitignore" >> .gitignore; rm "$TMP/app/.gitignore"; fi
# 搬回当前目录（包含隐藏文件）
shopt -s dotglob; mv "$TMP"/app/* . ; shopt -u dotglob; rm -rf "$TMP"
npm i -D --no-audit --no-fund "@types/node@^22" vitest tsx
if [ "$#" -gt 0 ]; then npm i --no-audit --no-fund "$@"; fi
cp "$SKILL_DIR/templates/ts/vitest.config.ts" ./vitest.config.ts
mkdir -p src/lib src/adapters data samples tests/live
touch data/.gitkeep
printf '\n# workshop\ndata/*\n!data/.gitkeep\n.kiro/specs/*/vitest.json\n' >> .gitignore
node -e '
const fs=require("fs");const p=JSON.parse(fs.readFileSync("package.json"));
const f=process.env.FEATURE||"feature";
p.scripts={...p.scripts,test:"vitest run",
 "test:json":"vitest run --reporter=json --outputFile=.kiro/specs/"+f+"/vitest.json",
 "test:live":"LIVE=1 vitest run tests/live --reporter=verbose --silent=false",
 typecheck:"tsc --noEmit"};
fs.writeFileSync("package.json",JSON.stringify(p,null,2)+"\n");'
npx next typegen
echo "scaffold done. next: write tests/smoke.test.ts + scripts/probe.ts, then: npm test && npm run typecheck && npm run lint && npm run dev"
