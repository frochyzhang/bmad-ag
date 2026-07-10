#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# ///
"""vault-write — vault 第二记忆体的唯一写入入口(Story 4.1/4.2 · AD-9/AD-10)。

结构化写 20-项目/<项目名>.md(带 frontmatter + 分区),原子手法(temp→fsync→rename,借
memlog.py 手法但不复用其扇平格式)。双笔迹:脚本只追加带【行首锚定】作者标记的 agent 行,
【绝不改写】任何行首非 agent 标记的行(人手写行只读)。cleared 标记不移除。

契约:
  --project <名>   必需,取自 ag-core 项目 go module/目录名(显式传入,不靠 cwd 猜)
  --type <知识|经验|决策>   记录类型,决定落入哪个分区
  --content <文本>  记录正文(agent 一阶理由)
  --vault-root <路径>  vault 根;省略则从 BMAD_VAULT_ROOT 环境变量,再省略报错
  --cleared <文本子串>  可选:把匹配的 agent 行标记为 cleared(不移除)
退出码: 0=成功, 2=参数/IO 错误
"""
from __future__ import annotations

import argparse
import os
import re
import sys
import tempfile
from datetime import date
from pathlib import Path

# 行首锚定的 agent 作者标记(AD-10:分类仅按行首前缀,绝不子串)
AGENT_PREFIX = "- (by agent)"
AGENT_LINE_RE = re.compile(r"^- \(by agent\)")  # 仅匹配行首

# 记录类型 → 分区标题(分区映射的单一定义处,AD-9)
SECTION_MAP = {
    "知识": "## 知识",
    "经验": "## 经验",
    "决策": "## 决策",
}
SECTION_ORDER = ["## 知识", "## 经验", "## 决策"]

ALLOWED_TYPES = set(SECTION_MAP.keys())


def parse_args():
    p = argparse.ArgumentParser(description="vault 第二记忆体唯一写入入口")
    p.add_argument("--project", required=True, help="ag-core 项目名(显式传入)")
    p.add_argument("--type", dest="rtype", choices=sorted(ALLOWED_TYPES),
                   help="记录类型:知识/经验/决策")
    p.add_argument("--content", help="记录正文(agent 一阶理由)")
    p.add_argument("--vault-root", default=os.environ.get("BMAD_VAULT_ROOT"),
                   help="vault 根路径(或环境变量 BMAD_VAULT_ROOT)")
    p.add_argument("--cleared", help="把匹配此子串的 agent 行标记为 cleared(不移除)")
    return p.parse_args()


def atomic_write(path: Path, text: str) -> None:
    """temp→flush→fsync→atomic rename(借 memlog.py 手法)。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)  # 原子 rename
    except Exception:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def new_file_text(project: str) -> str:
    today = date.today().isoformat()
    lines = [
        "---",
        f"project: {project}",
        f"created: {today}",
        f"updated: {today}",
        "type: project-memory",
        "tags: [project, bmad-agcore]",
        "---",
        "",
        f"# {project} — 项目记忆",
        "",
        "> agent 记一阶理由(行首 `- (by agent)`);人记二阶评判(行首无此标记)。",
        "> 叠加不覆盖:废弃项标 `[cleared]` 不移除;人裁定优先。脚本绝不改写人手写行。",
        "",
    ]
    for sec in SECTION_ORDER:
        lines.append(sec)
        lines.append("")
    return "\n".join(lines) + "\n"


def split_sections(text: str):
    """返回 (header_text, {section_title: [lines]}, order)。保留原文行不动。"""
    lines = text.splitlines()
    sections = {}
    order = []
    header = []
    cur = None
    for ln in lines:
        if ln in SECTION_MAP.values():
            cur = ln
            sections[cur] = []
            order.append(cur)
        elif cur is None:
            header.append(ln)
        else:
            sections[cur].append(ln)
    return header, sections, order


def rebuild(header, sections, order) -> str:
    out = list(header)
    # 保证末尾无多余空行叠加
    while out and out[-1] == "":
        out.pop()
    out.append("")
    for sec in order:
        out.append(sec)
        body = sections[sec]
        # 去掉分区体首尾多余空行,统一留一行间隔
        while body and body[0] == "":
            body.pop(0)
        while body and body[-1] == "":
            body.pop()
        out.extend(body)
        out.append("")
    return "\n".join(out) + "\n"


def bump_updated(header):
    today = date.today().isoformat()
    return [re.sub(r"^updated: .*$", f"updated: {today}", h) for h in header]


def main():
    args = parse_args()
    if not args.vault_root:
        print("vault-write: 需 --vault-root 或 BMAD_VAULT_ROOT", file=sys.stderr)
        return 2

    target = Path(args.vault_root) / "20-项目" / f"{args.project}.md"

    # 读现有(若有),否则新建骨架
    if target.exists():
        text = target.read_text(encoding="utf-8")
    else:
        text = new_file_text(args.project)

    header, sections, order = split_sections(text)
    # 确保三分区都在(旧文件可能缺)
    for sec in SECTION_ORDER:
        if sec not in sections:
            sections[sec] = []
            order.append(sec)

    changed = False

    # --- cleared:只作用于 agent 行,标记不移除 ---
    if args.cleared:
        for sec in order:
            newbody = []
            for ln in sections[sec]:
                if AGENT_LINE_RE.match(ln) and args.cleared in ln and "[cleared]" not in ln:
                    ln = ln + " [cleared]"
                    changed = True
                newbody.append(ln)  # 非 agent 行原样保留(人行只读)
            sections[sec] = newbody

    # --- append:追加一条 agent 行到对应分区 ---
    if args.content:
        if not args.rtype:
            print("vault-write: --content 需配 --type", file=sys.stderr)
            return 2
        sec = SECTION_MAP[args.rtype]
        today = date.today().isoformat()
        # 一阶理由行,行首锚定 agent 标记
        entry = f"{AGENT_PREFIX} {today}: {args.content}"
        sections[sec].append(entry)
        changed = True

    if not changed:
        print("vault-write: 无操作(需 --content 或 --cleared)", file=sys.stderr)
        return 2

    header = bump_updated(header)
    try:
        atomic_write(target, rebuild(header, sections, order))
    except Exception as e:
        print(f"vault-write: 写入失败 {e}", file=sys.stderr)
        return 2

    print(f"✅ vault 记录已写:{target}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
