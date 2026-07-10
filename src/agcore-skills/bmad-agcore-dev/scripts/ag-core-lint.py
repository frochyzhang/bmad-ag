#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = ["pyyaml"]
# ///
"""ag-core-lint — 违规护栏(Story 3.1 / AD-8)。

独立脚本 + 数据化规则集(lint-rules.yaml)。抓违反 ag-core 封装约定的写法。

契约(钉死,供 bmad-agcore-dev 的 build+lint 关卡消费):
  输入: 项目路径(位置参数,必需)
  退出码: 0=无违规, 1=有违规, >=2=脚本自身错误(路径不存在/规则文件损坏)
  输出: 人可读红字报警(stderr) + 机器可读 JSON(stdout,始终输出 {"violations":[...]})

新增规则只改 lint-rules.yaml,不改本脚本。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

def _ensure_yaml():
    """确保 pyyaml 可用。缺失则自动安装(护栏不能因缺依赖静默失效)。

    顺序:直接 import → uv pip install → pip install(--user 兜底) → 重试 import。
    全部失败才放弃(由调用方 exit 2)。返回 yaml 模块或 None。
    """
    try:
        import yaml  # noqa: F401
        return yaml
    except ImportError:
        pass

    import subprocess
    import importlib

    print("ag-core-lint: 检测到缺少 pyyaml,尝试自动安装...", file=sys.stderr)

    # 候选安装命令,按优先级尝试;第一个成功即止
    attempts = []
    if __import__("shutil").which("uv"):
        # uv 装进当前解释器环境(--python 指向本进程 sys.executable)
        attempts.append(["uv", "pip", "install", "--python", sys.executable, "pyyaml"])
    attempts.append([sys.executable, "-m", "pip", "install", "pyyaml"])
    attempts.append([sys.executable, "-m", "pip", "install", "--user", "pyyaml"])

    for cmd in attempts:
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
            if r.returncode == 0:
                importlib.invalidate_caches()
                try:
                    import yaml  # noqa: F401
                    print(f"ag-core-lint: pyyaml 已自动安装({' '.join(cmd[:3])})。", file=sys.stderr)
                    return yaml
                except ImportError:
                    continue
        except (OSError, subprocess.TimeoutExpired):
            continue

    return None


yaml = _ensure_yaml()
if yaml is None:
    print(json.dumps({"error": "pyyaml required and auto-install failed"}))
    print(
        "ag-core-lint: pyyaml 未安装且自动安装失败。请手动执行 "
        "`pip install pyyaml`(或 `uv pip install pyyaml`)后重试。",
        file=sys.stderr,
    )
    sys.exit(2)

RED = "\033[31m"
BOLD = "\033[1m"
RESET = "\033[0m"

DEFAULT_RULES = Path(__file__).parent / "lint-rules.yaml"


def parse_args():
    p = argparse.ArgumentParser(description="ag-core 违规 lint 护栏")
    p.add_argument("project_path", help="要检查的 ag-core 项目根路径")
    p.add_argument("--rules", default=str(DEFAULT_RULES), help="规则数据文件(默认 lint-rules.yaml)")
    p.add_argument("--json-only", action="store_true", help="只输出 JSON,不打印红字")
    return p.parse_args()


def _glob_match(rel_posix: str, pattern: str) -> bool:
    """支持 `**` 递归段的 glob 匹配(相对 posix 路径 vs 模式)。

    Python 的 PurePath.match() 不支持 `**` 递归通配(把 `**` 当单层 `*`),
    这会让 `**/vendor/**` 这类 exclude 失效。这里用 fnmatch.translate 手工处理:
    先把 `**/` 翻成"零或多段",`**` 翻成"任意字符",再逐段回退到普通 fnmatch。
    """
    import fnmatch

    # 直接 fnmatch(fnmatch 的 * 会跨 /,对 `**/vendor/**` 恰好够用)
    if fnmatch.fnmatch(rel_posix, pattern):
        return True
    # 兜底:形如 `**/X/**` → 命中任意包含 X 段的路径
    core = pattern.strip("*/")
    if core and f"/{core}/" in f"/{rel_posix}/":
        return True
    return False


def iter_files(root: Path, include, exclude):
    """按 include glob 收集文件,排除 exclude glob(支持 `**` 递归段)。"""
    includes = include if isinstance(include, list) else [include]
    excludes = exclude or []
    seen = set()
    for pat in includes:
        for f in root.glob(pat):
            if not f.is_file():
                continue
            rel = f.relative_to(root).as_posix()
            if any(_glob_match(rel, ex) for ex in excludes):
                continue
            if f not in seen:
                seen.add(f)
                yield f, rel


def check_regex_in_file(root, rule):
    out = []
    rx = re.compile(rule["pattern"])
    for f, rel in iter_files(root, rule.get("include", "**/*"), rule.get("exclude")):
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for i, line in enumerate(text.splitlines(), 1):
            if rx.search(line):
                out.append({"rule": rule["id"], "severity": rule["severity"],
                            "file": rel, "line": i, "desc": rule["description"],
                            "snippet": line.strip()[:120]})
    return out


def check_regex_in_path(root, rule):
    out = []
    rx = re.compile(rule["pattern"])
    for f, rel in iter_files(root, rule["path_glob"], rule.get("exclude")):
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if rx.search(text):
            m = rx.search(text)
            # 定位行号
            line_no = text[: m.start()].count("\n") + 1
            out.append({"rule": rule["id"], "severity": rule["severity"],
                        "file": rel, "line": line_no, "desc": rule["description"],
                        "snippet": m.group(0).strip()[:120]})
    return out


def check_edited_generated(root, rule):
    out = []
    hdr = re.compile(rule["generated_header"])
    for f, rel in iter_files(root, rule.get("include", []), rule.get("exclude")):
        try:
            head = "\n".join(f.read_text(encoding="utf-8", errors="ignore").splitlines()[:5])
        except Exception:
            continue
        if not hdr.search(head):
            out.append({"rule": rule["id"], "severity": rule["severity"],
                        "file": rel, "line": 1, "desc": rule["description"],
                        "snippet": "生成目录文件缺少生成头,疑被手改"})
    return out


DISPATCH = {
    "regex_in_file": check_regex_in_file,
    "regex_in_path": check_regex_in_path,
    "edited_generated": check_edited_generated,
}


def main():
    args = parse_args()
    root = Path(args.project_path)
    if not root.is_dir():
        print(json.dumps({"error": f"project path not found: {args.project_path}"}))
        print(f"{RED}ag-core-lint: 项目路径不存在: {args.project_path}{RESET}", file=sys.stderr)
        return 2

    try:
        rules_doc = yaml.safe_load(Path(args.rules).read_text(encoding="utf-8"))
        rules = rules_doc["rules"]
    except Exception as e:
        print(json.dumps({"error": f"rules file error: {e}"}))
        print(f"{RED}ag-core-lint: 规则文件损坏: {e}{RESET}", file=sys.stderr)
        return 2

    violations = []
    for rule in rules:
        fn = DISPATCH.get(rule.get("match"))
        if not fn:
            print(json.dumps({"error": f"unknown match type: {rule.get('match')}"}))
            print(f"{RED}ag-core-lint: 未知 match 类型 {rule.get('match')}{RESET}", file=sys.stderr)
            return 2
        violations.extend(fn(root, rule))

    # 机器可读通道:始终输出到 stdout
    print(json.dumps({"violations": violations}, ensure_ascii=False))

    # 人可读红字:stderr
    if violations and not args.json_only:
        print(f"\n{BOLD}{RED}✗ ag-core-lint 发现 {len(violations)} 处违规:{RESET}", file=sys.stderr)
        for v in violations:
            print(f"{RED}  [{v['rule']}] {v['file']}:{v['line']}{RESET}", file=sys.stderr)
            print(f"      {v['desc']}", file=sys.stderr)
            print(f"      → {v['snippet']}", file=sys.stderr)

    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
