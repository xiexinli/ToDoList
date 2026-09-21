#!/usr/bin/env bash
# 在"非空"的 workshop 目录里从零生成 Vite + React + TypeScript 纯前端项目（拓扑 P）。
# 用法：FEATURE=<feature> bash <skill>/scripts/scaffold-vite.sh [额外 npm 依赖...]
#   例：FEATURE=multilang-gen bash .kiro/skills/aidlc-workshop/scripts/scaffold-vite.sh xlsx jszip
#       FEATURE=cs-bot bash .kiro/skills/aidlc-workshop/scripts/scaffold-vite.sh @aws-sdk/client-bedrock-runtime @smithy/types zod
set -euo pipefail
SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
F="${FEATURE:-feature}"
TMP=".scaffold-tmp"
rm -rf "$TMP" && mkdir "$TMP"
( cd "$TMP" && npm create vite@latest app -- --template react-ts >/dev/null )
rm -rf "$TMP/app/.git"
if [ -f .gitignore ]; then cat "$TMP/app/.gitignore" >> .gitignore; rm "$TMP/app/.gitignore"; fi
shopt -s dotglob; mv "$TMP"/app/* . ; shopt -u dotglob; rm -rf "$TMP"
npm i --no-audit --no-fund >/dev/null
npm i -D --no-audit --no-fund vitest tsx "@types/node@^22" >/dev/null
if [ "$#" -gt 0 ]; then npm i --no-audit --no-fund "$@" >/dev/null; fi
# vitest 配置（alias @ -> src；live 目录默认排除）
cp "$SKILL_DIR/templates/ts/vitest.config.ts" ./vitest.config.ts
# tests/ 与 scripts/ 的类型检查单独一份 tsconfig（Vite 的 tsc -b 只覆盖 src）
cp "$SKILL_DIR/templates/ts/tsconfig.test.json" ./tsconfig.test.json
mkdir -p src/lib src/adapters samples tests/live scripts .kiro/specs/"$F"
printf '\n# workshop\n.kiro/specs/*/vitest.json\n' >> .gitignore
node -e '
const fs=require("fs");const p=JSON.parse(fs.readFileSync("package.json"));
const f=process.env.F;
p.scripts={...p.scripts,
 test:"vitest run",
 "test:json":"vitest run --reporter=json --outputFile=.kiro/specs/"+f+"/vitest.json",
 "test:live":"LIVE=1 vitest run tests/live --reporter=verbose --silent=false",
 typecheck:"tsc -b && tsc --noEmit -p tsconfig.test.json",
 probe:"tsx scripts/probe.ts"};
fs.writeFileSync("package.json",JSON.stringify(p,null,2)+"\n");'
echo "scaffold done. lint 用脚手架自带的 npm run lint（Vite 8 起为 oxlint）。next: 写 tests/smoke.test.ts + scripts/probe.ts，然后 npm test && npm run typecheck && npm run lint && npm run build && npx vite preview"
