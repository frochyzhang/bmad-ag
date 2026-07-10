#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# ///
"""check-staleness — ag-skills 知识过期主动比对(Story 2.3 · AD-12)。

读 SOURCE.md 的快照 commit,比对上游 github.com/aif-go/ag-skills 当前 HEAD。
落后(commit 不同)且快照距今超阈值天数则给 re-sync 提醒。上游不可达则优雅降级。
re-sync 动作由人决定,本脚本只比对 + 提醒,绝不自动改写 checkout(AD-13)。

契约:
  --source-md <路径>   SOURCE.md 路径(Story 1.5 写的)
  --threshold-days <n>  阈值(默认 30;dev/setup 从 config staleness_threshold_days 传)
退出码: 0=最新或未超阈值, 1=已过期(超阈值,提醒 re-sync), 2=脚本错误/无法比对
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path


def parse_args():
    p = argparse.ArgumentParser(description="ag-skills 知识过期比对")
    p.add_argument("--source-md", required=True, help="SOURCE.md 路径")
    p.add_argument("--threshold-days", type=int, default=30, help="落后天数阈值")
    return p.parse_args()


def parse_source(md_path: Path):
    text = md_path.read_text(encoding="utf-8")
    repo = re.search(r"repo:\s*(\S+)", text)
    commit = re.search(r"commit:\s*([0-9a-f]{7,40})", text)
    snap = re.search(r"snapshot_date:\s*(\d{4}-\d{2}-\d{2})", text)
    return (repo.group(1) if repo else None,
            commit.group(1) if commit else None,
            snap.group(1) if snap else None)


def upstream_head(repo: str):
    """git ls-remote 取上游 HEAD sha;不可达返回 None。"""
    try:
        out = subprocess.run(
            ["git", "ls-remote", repo, "HEAD"],
            capture_output=True, text=True, timeout=20, check=True,
        )
        return out.stdout.split()[0] if out.stdout.strip() else None
    except Exception:
        return None


def main():
    args = parse_args()
    md = Path(args.source_md)
    if not md.exists():
        print(f"❌ 未找到 SOURCE.md: {args.source_md}(先跑 /bmad-agcore-setup clone ag-skills)", file=sys.stderr)
        return 2

    repo, commit, snap = parse_source(md)
    if not (repo and commit):
        print(f"❌ SOURCE.md 缺 repo/commit 字段,无法比对", file=sys.stderr)
        return 2

    head = upstream_head(repo)
    if head is None:
        print(f"⚠️  无法连上游 {repo}(离线?),跳过过期比对,不误判。", file=sys.stderr)
        return 0  # 优雅降级:不可达不算过期、不中断

    if head.startswith(commit) or commit.startswith(head[:len(commit)]):
        print(f"✅ ag-skills 已是最新(快照 {commit[:7]} = 上游 {head[:7]})。")
        return 0

    # commit 不同 → 计算快照距今天数
    days = None
    if snap:
        try:
            days = (date.today() - datetime.strptime(snap, "%Y-%m-%d").date()).days
        except ValueError:
            days = None

    if days is not None and days < args.threshold_days:
        print(f"ℹ️  ag-skills 有上游更新(本地 {commit[:7]} → 上游 {head[:7]}),"
              f"但快照仅 {days} 天(阈值 {args.threshold_days}),暂不强提醒。")
        return 0

    # 超阈值(或无日期无法判定天数时,保守提醒)
    days_str = f"{days} 天" if days is not None else "未知天数"
    print(f"🔔 ag-skills 知识可能过期:本地快照 {commit[:7]}({snap or '?'},{days_str})"
          f" 落后上游 {head[:7]},已超 {args.threshold_days} 天阈值。", file=sys.stderr)
    print(f"   建议 re-sync:重跑 /bmad-agcore-setup(或手动 git pull {repo})。"
          f"是否同步由你决定 —— 本检查不自动改写 checkout。", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
