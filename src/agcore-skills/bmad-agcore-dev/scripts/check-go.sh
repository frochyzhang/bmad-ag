#!/bin/bash
# Story 1.3: Go 环境硬前提校验(AD-5 末句 / NFR2)
# ag-core go.mod 要求 go >=1.24.8。无 Go 或版本不足 → 提示并以非零退出(setup 据此引导)。
# 退出码:0=满足;1=无 Go 或版本不足(需人安装/升级)
set -euo pipefail

MIN_MAJOR=1
MIN_MINOR=24
MIN_PATCH=8
MIN_STR="1.24.8"

if ! command -v go >/dev/null 2>&1; then
  echo "❌ 未检测到 Go。ag-core 工具链需 Go >=${MIN_STR}。" >&2
  echo "   请先安装 Go(https://go.dev/dl/),再重跑 /bmad-agcore-setup。安装 Go 是安装步骤的一部分。" >&2
  exit 1
fi

# 解析 `go version go1.25.5 darwin/arm64` → 1.25.5
raw="$(go version 2>/dev/null)"
ver="$(printf '%s\n' "$raw" | sed -n 's/.*go\([0-9][0-9]*\.[0-9][0-9]*\(\.[0-9][0-9]*\)*\).*/\1/p')"
if [ -z "$ver" ]; then
  echo "❌ 无法解析 Go 版本(输出:$raw)。" >&2
  exit 1
fi

# 补齐三段并按整数比较(1.25 → 1.25.0)
major="$(printf '%s' "$ver" | cut -d. -f1)"
minor="$(printf '%s' "$ver" | cut -d. -f2)"
patch="$(printf '%s' "$ver" | cut -d. -f3)"
patch="${patch:-0}"

ok=0
if [ "$major" -gt "$MIN_MAJOR" ]; then ok=1
elif [ "$major" -eq "$MIN_MAJOR" ]; then
  if [ "$minor" -gt "$MIN_MINOR" ]; then ok=1
  elif [ "$minor" -eq "$MIN_MINOR" ]; then
    if [ "$patch" -ge "$MIN_PATCH" ]; then ok=1; fi
  fi
fi

if [ "$ok" -eq 1 ]; then
  echo "✅ Go ${ver} 满足要求(>=${MIN_STR})。"
  exit 0
else
  echo "❌ Go ${ver} 版本过低,ag-core 需 >=${MIN_STR}。请升级 Go 后重跑 /bmad-agcore-setup。" >&2
  exit 1
fi
