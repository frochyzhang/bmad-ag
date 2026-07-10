#!/bin/bash
# Story 1.4: 从 GitHub 唯一来源装齐 7 件 ag-core 工具链(AD-5 / NFR3)
#
# 唯一来源 = GitHub,无 fallback,严禁本地旧 checkout 或 GitLab 源。
# 因 ag-core go.mod 模块路径为 gitlab 内网地址(≠ 仓库路径),
# 不能 `go install <path>@latest`,必须 clone 后进各 tool/cmd/<bin>/ go install。
# 探测用 command -v(aggo/gen-go-db 无 --version)。
set -euo pipefail

readonly AGCORE_REPO="https://github.com/aif-go/ag-core.git"
readonly BINS=(aggo gen-go-db protoc-gen-go-agkitex protoc-gen-go-aghertz protoc-gen-go-agserver protoc-gen-go-agservice protoc-gen-go-agapi)

# 1) 探测:全部在 PATH 则跳过
missing=()
for b in "${BINS[@]}"; do
  if ! command -v "$b" >/dev/null 2>&1; then missing+=("$b"); fi
done

if [ "${#missing[@]}" -eq 0 ]; then
  echo "✅ 7 件工具链已全部在 PATH,跳过安装。"
  exit 0
fi

echo "缺失工具链:${missing[*]}"
echo "从 GitHub 唯一来源安装:${AGCORE_REPO}(严禁本地/GitLab 源)"

# 2) clone GitHub 仓库到临时目录,checkout 内逐目录 go install
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
git clone --depth 1 "$AGCORE_REPO" "$tmp/ag-core"

cmd_dir="$tmp/ag-core/tool/cmd"
if [ ! -d "$cmd_dir" ]; then
  echo "❌ GitHub 仓库结构异常:未找到 tool/cmd(期望 install.sh 所在目录)。" >&2
  exit 2
fi

# 装全部 7 件(不只缺失的,保证版本一致跟随 GitHub 最新)
for b in "${BINS[@]}"; do
  if [ -d "$cmd_dir/$b" ]; then
    echo "go install $b ..."
    ( cd "$cmd_dir/$b" && go install )
  else
    echo "⚠️  仓库内未找到 tool/cmd/$b,跳过(GitHub 结构可能已变,请检查)。" >&2
  fi
done

# 3) 安装后验证
still_missing=()
for b in "${BINS[@]}"; do
  if ! command -v "$b" >/dev/null 2>&1; then still_missing+=("$b"); fi
done

if [ "${#still_missing[@]}" -ne 0 ]; then
  echo "❌ 安装后仍缺失:${still_missing[*]}。请确认 \$(go env GOBIN)/\$(go env GOPATH)/bin 在 PATH。" >&2
  exit 1
fi

echo "✅ 7 件工具链已全部就位(GitHub 源)。"
