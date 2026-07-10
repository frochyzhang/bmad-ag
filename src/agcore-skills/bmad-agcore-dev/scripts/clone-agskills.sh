#!/bin/bash
# Story 1.5: clone ag-skills 到 config 约定位置并写 SOURCE.md(AD-6 / AD-11)
#
# ag-skills 唯一来源 = GitHub。clone 到 agskills_path(由 setup 解析 config key 后传入)。
# 写 SOURCE.md 记 repo + commit + 快照日期,作为 CAP-1 SKILL_ROOT 与 CAP-7 re-sync 基准。
# 已存在则跳过(不覆盖用户改动),提示可经 re-sync 更新。
#
# 用法: clone-agskills.sh <agskills_path(已解析真实路径)> <source_md_path>
set -euo pipefail

readonly AGSKILLS_REPO="https://github.com/aif-go/ag-skills.git"

if [ "$#" -lt 2 ]; then
  echo "❌ 用法: clone-agskills.sh <agskills_path> <source_md_path>" >&2
  exit 2
fi
readonly DEST="$1"
readonly SOURCE_MD="$2"

if [ -d "$DEST/.git" ]; then
  echo "ℹ️  ag-skills checkout 已存在于 $DEST,跳过 clone(如需更新走 re-sync)。"
else
  echo "clone ag-skills(GitHub 唯一来源):$AGSKILLS_REPO → $DEST"
  mkdir -p "$(dirname "$DEST")"
  git clone "$AGSKILLS_REPO" "$DEST"
fi

# 校验结构:SKILL.md 应在根(SKILL_ROOT)
if [ ! -f "$DEST/SKILL.md" ]; then
  echo "❌ $DEST 下未找到 SKILL.md,ag-skills 结构异常。" >&2
  exit 1
fi

commit="$(git -C "$DEST" rev-parse HEAD)"
snapshot_date="$(date +%Y-%m-%d)"

mkdir -p "$(dirname "$SOURCE_MD")"
cat > "$SOURCE_MD" <<EOF
---
repo: ${AGSKILLS_REPO}
commit: ${commit}
snapshot_date: ${snapshot_date}
---

# ag-skills 知识底座来源快照

- **repo**: ${AGSKILLS_REPO}
- **commit**: ${commit}
- **snapshot_date**: ${snapshot_date}
- **checkout**: ${DEST}

CAP-7 re-sync 比对以此 commit 为基准。上游 \`git ls-remote ${AGSKILLS_REPO} HEAD\`
落后超阈值(见 config staleness_threshold_days)则提醒重新同步。
EOF

echo "✅ ag-skills 就位 @ $commit($snapshot_date),SOURCE.md 已写:$SOURCE_MD"
