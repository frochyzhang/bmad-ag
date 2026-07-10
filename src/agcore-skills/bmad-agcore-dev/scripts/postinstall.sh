#!/bin/bash
# agcore 内置模块安装后编排(由 fork 安装器在 agcore 装完文件后调用)。
#
# 设计:尽力而为(best-effort),任何一步失败都不硬退出——BMad 整体安装不因
# 工具链/知识底座装不上而崩。缺 Go / go install 失败 / clone 失败只给醒目警告,
# dev 技能激活时本就有自检兜底(能力探测+优雅降级)。最终始终 exit 0。
#
# 用法: postinstall.sh <agskills_path(已解析真实路径)> <source_md_path> [staleness_days]
#
# 注意:不使用 set -e(要尽力而为跑完所有步骤);用 set -u 抓未定义变量。
set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

AGSKILLS_PATH="${1:-}"
SOURCE_MD="${2:-}"
STALENESS_DAYS="${3:-30}"

echo ""
echo "──────────────────────────────────────────────"
echo "  BMAD ag-core 模块:安装工具链与知识底座"
echo "──────────────────────────────────────────────"

# 汇总各步结果,最后统一报告
go_ok=0
tool_ok=0
skills_ok=0

# ── 1) Go 环境校验(软前提)────────────────────────────
echo ""
echo "▶ [1/3] 校验 Go 环境..."
if bash "$SCRIPT_DIR/check-go.sh"; then
  go_ok=1
else
  echo "⚠️  Go 环境不满足(需 >=1.24.8)。跳过工具链安装。"
  echo "   安装/升级 Go 后,首次运行 /bmad-agcore-dev 时会自动补装工具链。"
fi

# ── 2) 安装 7 件工具链(软,依赖 Go)──────────────────
echo ""
echo "▶ [2/3] 安装 ag-core 工具链(aggo + gen-go-db + 5 个 protoc-gen-go-ag*)..."
if [ "$go_ok" -eq 1 ]; then
  if bash "$SCRIPT_DIR/install-toolchain.sh"; then
    tool_ok=1
  else
    echo "⚠️  工具链安装未完成。首次运行 /bmad-agcore-dev 时会重试。"
  fi
else
  echo "⏭  跳过(Go 未就绪)。"
fi

# ── 3) clone ag-skills 知识底座(软,仅需 git)─────────
echo ""
echo "▶ [3/3] clone ag-skills 知识底座..."
if [ -z "$AGSKILLS_PATH" ] || [ -z "$SOURCE_MD" ]; then
  echo "⚠️  未收到 agskills_path / source_md 参数,跳过 clone。"
elif ! command -v git >/dev/null 2>&1; then
  echo "⚠️  未检测到 git,跳过 ag-skills clone。"
else
  if bash "$SCRIPT_DIR/clone-agskills.sh" "$AGSKILLS_PATH" "$SOURCE_MD"; then
    skills_ok=1
  else
    echo "⚠️  ag-skills clone 未完成。首次运行 /bmad-agcore-dev 时会重试。"
  fi
fi

# ── 汇总 ─────────────────────────────────────────────
echo ""
echo "──────────────────────────────────────────────"
echo "  ag-core 模块安装后处理结果"
echo "    Go 环境      : $([ "$go_ok" -eq 1 ] && echo '✅ 就绪' || echo '⚠️  缺失/过低')"
echo "    工具链(7件)  : $([ "$tool_ok" -eq 1 ] && echo '✅ 就位' || echo '⚠️  未完成(将在首次开发时重试)')"
echo "    ag-skills    : $([ "$skills_ok" -eq 1 ] && echo '✅ 就位' || echo '⚠️  未完成(将在首次开发时重试)')"
echo "──────────────────────────────────────────────"
echo ""

# 尽力而为:始终成功退出,不阻断 BMad 整体安装。
exit 0
