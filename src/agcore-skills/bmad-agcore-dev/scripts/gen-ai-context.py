#!/usr/bin/env python3
# ruff: noqa
"""
gen-ai-context.py — 根据已 clone 的 ag-skills 知识底座,动态生成项目级 ag-core 约束文件
(.claude/ai-context/00-instructions.md)。

设计原则(用户裁决):
  约束来源以 ag-skills 为真相源 —— "ag-core 里有的就用 ag-core,没有的要着重提出来讲"。
  因此本脚本不写死静态禁用清单(会随 ag-skills 演进过时),而是:
    1. 扫描 <agskills>/references/ 实际存在的 *-patterns / 能力文档;
    2. 按"文件名关键词 → 能力域 + 通用替代物"映射表归类,渲染"必用 ag-core 封装"覆盖表;
    3. 映射表定义了 ag-core 关心的能力域全集;references 里缺失的域 → 落入
       "ag-skills 未涵盖,需显式提出讨论"清单,提醒不得静默用通用库替代。

用法:
  gen-ai-context.py <agskills_path> <output_instructions_md> [--project-name NAME] [--force]

行为:
  - agskills_path 不存在 / 无 references → 退出码 3(调用方按"跳过"处理,不阻断安装)。
  - 输出文件已存在且未加 --force → 退出码 4(不覆盖用户已定制的约束),调用方视为跳过。
  - 成功写入 → 退出码 0。
  - 参数缺失 / 其他错误 → 退出码 2。

原子写:temp → fsync → atomic rename(借 memlog.py 手法),避免半截文件。
"""

import os
import sys
import argparse
import tempfile
import datetime


# 能力域映射:reference 文件名关键词 → (能力域中文名, ag-core 封装说法, 被禁用的通用替代物)
# 这是 ag-core 关心的能力域"全集"。references 命中即"有,必用封装";未命中的域 → 显式讨论清单。
CAPABILITY_MAP = [
    # (关键词匹配, 能力域, ag-core 封装, 通用替代物(禁止静默使用))
    ("aglog", "日志", "aglog", "zap / logrus / 标准 log 直接 new"),
    ("hertz", "HTTP 服务", "hertz(aghertz)", "net/http + gorilla/mux / gin / echo"),
    ("kitex", "gRPC 服务", "kitex(agkitex)", "google.golang.org/grpc 裸用"),
    ("ag-conf", "配置", "ag_conf", "手写 viper / 直接读环境变量拼配置"),
    ("nacos", "配置中心 / 注册发现", "ag_conf 接 nacos", "手拼 nacos-sdk-go client"),
    ("db-yaml", "数据库表定义", "表 YAML → gen-go-db 生成", "手写 model 结构体"),
    ("dao", "数据库访问", "gen-go-db 生成的 DAO", "裸 database/sql / 手写 gorm"),
    ("gen-go-db", "数据库代码生成", "gen-go-db CLI", "手写 CRUD"),
    ("redis", "缓存", "ag-core redis 封装", "go-redis 裸用"),
    ("kafka", "消息队列", "ag-core kafka 封装(agsarama)", "sarama / kafka-go 裸用"),
    ("gateway", "跨服务调用(网关层)", "Gateway 三层(biz 接口 → gateway 实现 → clients 工厂)", "在 biz 里直接 new 下游 client"),
    ("service-clients", "服务客户端连接管理", "ag-core service-clients 工厂", "手工管理连接池"),
    ("agonet", "网络", "agonet", "手写 net 层"),
    ("proto-idl", "接口定义(IDL)", "proto-first + aggo 生成", "手写 handler/router"),
    ("code-generation", "代码生成流水线", "aggo proto 插件矩阵", "手写骨架"),
]

# 每个能力域只需一个代表性关键词命中即算"覆盖"。用于计算缺失域。
# 把上面拆细的同域项归并(如 db-yaml/dao/gen-go-db 同属数据库域)。
DOMAIN_GROUPS = {
    "日志": ["aglog"],
    "HTTP 服务": ["hertz"],
    "gRPC 服务": ["kitex"],
    "配置与配置中心": ["ag-conf", "nacos"],
    "数据库": ["db-yaml", "dao", "gen-go-db"],
    "缓存": ["redis"],
    "消息队列": ["kafka"],
    "跨服务调用": ["gateway", "service-clients"],
    "接口定义与代码生成": ["proto-idl", "code-generation"],
}


def read_h1(path):
    """读文件首个 H1 标题,失败返回空串。"""
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("# "):
                    return line[2:].strip()
    except OSError:
        pass
    return ""


def scan_references(agskills_path):
    """扫描 references 目录,返回 [(filename, h1_title), ...](按名排序)。"""
    ref_dir = os.path.join(agskills_path, "references")
    if not os.path.isdir(ref_dir):
        return None
    out = []
    for name in sorted(os.listdir(ref_dir)):
        if name.endswith(".md"):
            out.append((name, read_h1(os.path.join(ref_dir, name))))
    return out


def build_coverage(refs):
    """根据实际存在的 reference 文件,构建命中的能力覆盖行 + 缺失域清单。"""
    ref_names = [n for n, _ in refs]

    covered_rows = []
    hit_keywords = set()
    for keyword, domain, wrapper, generic in CAPABILITY_MAP:
        matched = [n for n in ref_names if keyword in n]
        if matched:
            hit_keywords.add(keyword)
            covered_rows.append((domain, wrapper, generic, matched[0]))

    # 计算缺失域:DOMAIN_GROUPS 里没有任何代表关键词命中的域
    missing_domains = []
    for domain, keywords in DOMAIN_GROUPS.items():
        if not any(k in hit_keywords for k in keywords):
            missing_domains.append(domain)

    return covered_rows, missing_domains


def render(project_name, agskills_path, refs, covered_rows, missing_domains, snapshot):
    date = os.environ.get("BMAD_GEN_DATE", "")  # 允许注入,避免 Date.now 不确定性场景
    if not date:
        date = datetime.date.today().isoformat()

    lines = []
    lines.append("---")
    lines.append("title: ag-core 项目开发约束(自动生成,可手动增补)")
    lines.append(f"project: {project_name}")
    lines.append("tags: [ag-core, ai-context, dev-constraints]")
    lines.append(f"generated: {date}")
    lines.append(f"source: ag-skills @ {snapshot}")
    lines.append("generator: gen-ai-context.py")
    lines.append("---")
    lines.append("")
    lines.append("# ag-core 项目开发约束")
    lines.append("")
    lines.append(
        "> 本文件由 fork 版 BMad 的 agcore 模块在安装时**自动生成**,"
        "扫描已 clone 的 ag-skills 知识底座得出。它是本项目开发阶段的**项目级覆盖约束**"
        "(优先级高于 BMad 通用开发指导)。`bmad-dev-story` 与 `bmad-agcore-dev` 均会读取本文件。"
    )
    lines.append("")
    lines.append("## 核心原则(不可协商)")
    lines.append("")
    lines.append("**ag-core 里有的能力,必须用 ag-core 封装;ag-core 没有的,必须显式提出来讨论 —— 禁止静默改用通用 Go 库替代。**")
    lines.append("")
    lines.append(
        "机器负责按 ag-skills 黄金范例生成/填充代码,人负责守关口。任何偏离 ag-core 封装的写法,"
        "要么被 `ag-core-lint` 拦截,要么在这里被明确禁止。"
    )
    lines.append("")

    # ── 必用 ag-core 封装(references 命中)──
    lines.append("## 必须使用 ag-core 封装(ag-skills 已涵盖)")
    lines.append("")
    lines.append("下列能力 ag-skills 已有黄金范例,**必须**走 ag-core 封装,**禁止**使用括注的通用替代物:")
    lines.append("")
    lines.append("| 能力域 | 必用 ag-core | 禁止(通用替代) | ag-skills 参考 |")
    lines.append("| --- | --- | --- | --- |")
    for domain, wrapper, generic, ref in covered_rows:
        lines.append(f"| {domain} | {wrapper} | {generic} | `references/{ref}` |")
    lines.append("")

    # ── 缺失域:显式讨论 ──
    lines.append("## ag-skills 未涵盖的能力(必须显式提出讨论)")
    lines.append("")
    if missing_domains:
        lines.append(
            "下列能力域在当前 ag-skills 快照中**没有**对应封装文档。若本项目需要用到,"
            "**不得**擅自选用通用库静默实现 —— 必须**明确提出来**,与团队确认 ag-core 是否有未文档化的封装、"
            "或是否批准使用特定通用方案:"
        )
        lines.append("")
        for d in missing_domains:
            lines.append(f"- **{d}** —— ag-skills 无对应 pattern,用到需先讨论")
        lines.append("")
    else:
        lines.append("当前 ag-skills 快照已覆盖上述全部核心能力域。")
        lines.append("")
    lines.append(
        "> 除上表列出的域之外,任何**新引入的第三方依赖**(日志/HTTP/DB/MQ/缓存/配置/RPC 之外的能力)"
        "也适用同一规则:先确认 ag-core 是否已封装,没有再讨论选型,不静默引入。"
    )
    lines.append("")

    # ── 结构与护栏 ──
    lines.append("## 结构与护栏(固定约束)")
    lines.append("")
    lines.append("- **proto-first**:无 `.proto` 不生成代码。`.proto` 落 `idl/api/<service>/`。")
    lines.append("- **生成物不可手改**:`api/`、`internal/adpgen/`、`internal/svcgen/` 由 aggo 生成,禁止手工编辑。")
    lines.append("- **业务逻辑落 biz 层**:`internal/biz/<service>_biz.go`;`internal/service/` 只做薄层委托,禁塞业务逻辑。")
    lines.append("- **每次生成/填充后必跑护栏**:`go mod tidy && go build ./...`,再跑 `ag-core-lint`;任一失败即停,不得进下一步、不得声称完成。")
    lines.append("- **知识加载前置**:产出任何 ag-core 代码前,先经 `bmad-agcore-skills` 按任务类型懒加载对应 references(见上表)。黄金范例优先于 API 文档。")
    lines.append("")

    # ── 现存 references 清单(便于人工查阅)──
    lines.append("## 当前 ag-skills 知识底座清单")
    lines.append("")
    lines.append(f"快照:`{snapshot}` · 位置:`{agskills_path}`")
    lines.append("")
    for name, title in refs:
        lines.append(f"- `references/{name}` — {title}")
    lines.append("")

    return "\n".join(lines) + "\n"


def read_snapshot(agskills_path):
    """尽量读出 ag-skills 快照标识(HEAD 短 SHA);读不到返回 'unknown'。"""
    head = os.path.join(agskills_path, ".git", "HEAD")
    try:
        with open(head, "r", encoding="utf-8") as f:
            ref = f.read().strip()
        if ref.startswith("ref:"):
            ref_path = os.path.join(agskills_path, ".git", ref[4:].strip())
            with open(ref_path, "r", encoding="utf-8") as f:
                return f.read().strip()[:12]
        return ref[:12]
    except OSError:
        return "unknown"


def atomic_write(path, content):
    """temp → fsync → atomic rename。"""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    dir_name = os.path.dirname(path)
    fd, tmp = tempfile.mkstemp(dir=dir_name, prefix=".ai-context.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def main():
    ap = argparse.ArgumentParser(description="生成 ag-core 项目级约束文件")
    ap.add_argument("agskills_path", help="已 clone 的 ag-skills 根路径")
    ap.add_argument("output_md", help="输出的 00-instructions.md 路径")
    ap.add_argument("--project-name", default="", help="项目名(写入 frontmatter)")
    ap.add_argument("--force", action="store_true", help="已存在也覆盖")
    args = ap.parse_args()

    refs = scan_references(args.agskills_path)
    if refs is None or len(refs) == 0:
        print(f"⚠️  ag-skills references 不存在或为空({args.agskills_path}),跳过约束文件生成。", file=sys.stderr)
        return 3

    if os.path.exists(args.output_md) and not args.force:
        print(f"ℹ️  约束文件已存在,保留用户定制不覆盖:{args.output_md}", file=sys.stderr)
        return 4

    project_name = args.project_name or "ag-core-project"
    snapshot = read_snapshot(args.agskills_path)
    covered_rows, missing_domains = build_coverage(refs)
    content = render(project_name, args.agskills_path, refs, covered_rows, missing_domains, snapshot)

    try:
        atomic_write(args.output_md, content)
    except OSError as e:
        print(f"⚠️  写入约束文件失败:{e}", file=sys.stderr)
        return 2

    print(f"✅ ag-core 约束文件已生成:{args.output_md}")
    print(f"   覆盖能力域 {len(covered_rows)} 项,ag-skills 未涵盖 {len(missing_domains)} 项(已列入显式讨论清单)。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
