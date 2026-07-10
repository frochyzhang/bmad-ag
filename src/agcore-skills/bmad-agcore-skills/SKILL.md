---
name: 'bmad-agcore-skills'
description: ag-core 框架知识底座。Use when working with ag-core:定义 protobuf API、aggo 生成代码、实现 Kitex(gRPC)/Hertz(HTTP)服务、gen-go-db 生成 DAO/Model、设计数据库表、跨服务调用、配置 Nacos/Redis/Kafka/日志,或处理 idl/api、internal/biz、internal/service 目录。
allowed-tools:
  - Read
  - Grep
  - Glob
  - Bash
---

# BMAD ag-core Knowledge Base

ag-core 微服务框架的知识底座。本 skill 不 vendored 知识内容,而是**指向** ag-skills 的外部 checkout(AD-6),按其索引 + 懒加载结构调用相应封装模式(AD-6b)。

## SKILL_ROOT 解析(AD-11,不硬编码)

从 `_bmad/config.yaml` 的 `bmad-agcore` 段读 `agskills_path`,解析其中的 `{project-root}` 字面 token 为真实路径 → 得 **SKILL_ROOT**(ag-skills checkout 根,即其 SKILL.md 所在)。所有知识加载从此单一路径出发,任何单元不另行硬编码 ag-skills 路径。

## On Activation — 知识过期比对(Story 2.3 / AD-12)

激活时**主动**比对本地快照与上游(不等人问):

```bash
python3 {project-root}/.claude/skills/bmad-agcore-skills/scripts/check-staleness.py \
  --source-md {project-root}/.claude/skills/bmad-agcore-skills/SOURCE.md \
  --threshold-days <config 的 staleness_threshold_days,默认 30>
```

- 退出 `0`:最新或未超阈值,静默继续。
- 退出 `1`:落后超阈值 → 向用户转达 re-sync 提醒。**是否重新同步由人决定**,本 skill 不自动改写 checkout(AD-13 人守关口)。
- 退出 `2` 或上游不可达:优雅降级,提示无法比对,不中断、不误判为过期。

## 懒加载知识(Story 2.1 / AD-6)

面对 ag-core 任务时:

1. 先读 `<SKILL_ROOT>/SKILL.md` 的 **Knowledge Structure 索引**(它列了 workflows + 18 个编号 references + best-practices + troubleshooting,每条注明 When/Contains)。
2. 按任务类型**只加载相关 references**(不全载):

   | 任务 | 加载 references |
   | --- | --- |
   | 建/初始化项目 | workflows/create-project |
   | 定义 proto / gRPC 服务 | proto-idl-patterns、kitex-patterns、code-generation |
   | HTTP 服务 | proto-idl-patterns、hertz-patterns、code-generation |
   | 跨服务调用 | gateway-patterns、service-clients |
   | 数据库表/DAO | db-yaml-format、gen-go-db-cli、dao-usage |
   | 配置/日志 | ag-conf-patterns、aglog-patterns |
   | 缓存/消息 | redis-patterns、kafka-patterns、kafka-consumer-patterns |
   | 服务注册发现 | nacos-patterns |
   | TCP 长连接 | agonet-patterns |
   | 校验/排错 | verification、troubleshooting/common-issues |

3. 知识范围只锚 ag-core **稳定封装层**;**黄金范例(标准 ag-core 业务代码)优先于 API 文档**(NFR6)。

## 项目本地规则优先(继承 ag-skills 约定)

若目标 ag-core 项目有 `.claude/ai-context/00-instructions.md`,其**项目级规则覆盖**本 skill 的通用指导(目录约定、禁止项等)。这是 ag-skills 自身的约定,本 skill 遵守。

## 与 dev 流水线的关系

`bmad-agcore-dev` 的流水线 Step 0(知识加载前置,AD-6b)**强制**先经本 skill 加载相关封装模式,方可产出代码 —— 确保知识实际约束生成,而非装了指针仍写通用 Go。
