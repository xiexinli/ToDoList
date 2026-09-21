#!/usr/bin/env bash
# 把 aidlc-workshop skill 安装到目标项目，同时支持 Claude Code 与 Kiro。
# 用法: skills/aidlc-workshop/install.sh /path/to/project [--link]
#   --link  用符号链接（便于本仓库内迭代 skill）；默认复制。
set -euo pipefail
SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST="${1:?usage: install.sh <project-dir> [--link]}"
MODE="${2:-copy}"
for HARNESS in .claude .kiro; do
  mkdir -p "$DEST/$HARNESS/skills"
  TARGET="$DEST/$HARNESS/skills/aidlc-workshop"
  rm -rf "$TARGET"
  if [ "$MODE" = "--link" ]; then
    ln -s "$SRC" "$TARGET"
  else
    cp -r "$SRC" "$TARGET"
    rm -f "$TARGET/install.sh"
  fi
  echo "installed -> $TARGET"
done
mkdir -p "$DEST/.kiro/specs"
echo "done. 在 Claude Code 中: /aidlc-workshop spec ；在 Kiro 中直接说: aidlc spec"
