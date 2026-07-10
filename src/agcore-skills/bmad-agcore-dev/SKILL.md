---
name: 'bmad-agcore-dev'
description: ag-core 开发流水线。Use when building an ag-core microservice, adding a gRPC/HTTP service, running the proto→scaffold→biz pipeline, or when the user says 'implement ag-core service', '加一个 ag-core 服务', 'aggo 生成代码'.
allowed-tools:
  - Read
  - Grep
  - Glob
  - Bash
  - Edit
  - Write
---

# BMAD ag-core Dev Pipeline

proto-first 流水线:`.proto` → aggo 生成骨架 → 填 biz 业务逻辑 → build+lint 护栏 → 关键节点记 vault。范式:pipes-and-filters,每级职责单一,生成物与手写物物理分离。贯穿灵魂:**机器干生成,人守关口**。

配置来源:从 `_bmad/config.yaml` 的 `bmad-agcore` 段读 `agskills_path`、`vault_path`(AD-11,不硬编码)。

---

## Step 0 — 知识加载前置(Story 2.2 / AD-6b,不可跳过)

**产出任何 ag-core 代码之前,必须先经 bmad-agcore-skills 加载相关封装模式知识。** 未加载不得进入生成/填充。

1. 激活 `bmad-agcore-skills`,它从 `agskills_path` 解析 SKILL_ROOT。
2. 按当前任务类型懒加载相关 references(不全载):
   - gRPC 服务 → proto-idl-patterns、kitex-patterns、code-generation
   - HTTP 服务 → proto-idl-patterns、hertz-patterns、code-generation
   - 跨服务调用 → gateway-patterns、service-clients
   - 数据库 → db-yaml-format、gen-go-db-cli、dao-usage
   - 配置/日志/缓存/MQ → ag-conf/aglog/redis/kafka-patterns
3. 知识范围只锚 ag-core **稳定封装层**;**黄金范例(标准 ag-core 业务代码)优先于 API 文档**(NFR6)。
4. 若目标项目有 `.claude/ai-context/00-instructions.md`,**项目级规则覆盖**本流水线通用指导。

---

## Step 1 — proto → 骨架生成(Story 3.2 / AD-7)

1. 确认 `.proto` 位于 `idl/api/<service>/`(proto-first;无 .proto 不生成)。
2. 按 ag-skills code-generation.md 的插件/模式矩阵跑 `aggo proto`(`-p` 逗号多值 go,api,server,kitex,hertz,service;`-m` 只对 kitex/hertz 取 server|client)。
3. 生成物落 `api/`、`internal/adpgen/`、`internal/svcgen/` —— **不可手改**(AD-7)。
4. `.proto` 语法错/缺失 → 报可读错误,**不硬造代码**。
5. 生成后立即 `go mod tidy`。

---

## Step 2 — 填 biz 业务逻辑(Story 3.3 / AD-7)

1. 业务逻辑写 `internal/biz/<service>_biz.go`(+ `zfx_biz.go` fx 注册);`internal/service/agservice_<service>.go` **只做薄层委托**,禁塞业务逻辑。
2. 守封装约定(照 Step 0 加载的黄金范例填):
   - **DB**:用 gen-go-db 生成的 DAO(InsertOne/Update/FindBy…)或 ag-core db 封装,**禁 `database/sql`**。
   - **context** 贯穿各层;**error** 用 ag-core 错误类型;**config** 走 `cmd/server/app.yml`。
   - **跨服务**:Gateway 三层(biz 接口 → gateway 实现 → clients 工厂)。
3. **不修改** `adpgen/`、`svcgen/`、`api/` 生成物。

---

## Step 3 — build + lint 护栏(Story 3.4 / AD-7、AD-8,不可跳过)

每次生成/填充后**必须**执行,任一失败即停,**不得进下一步、不得声称完成**:

```bash
go mod tidy && go build ./...
```

- build 非零 → **停**,报编译错误。

build 通过后跑 lint:

```bash
python3 {project-root}/.claude/skills/bmad-agcore-dev/scripts/ag-core-lint.py <ag-core 项目路径>
```

按退出码处置(AD-8 契约,严格区分):
- `0` → 无违规,通过。
- `1` → **有违规**,停;读 stdout 的 JSON `violations` 列表向用户报明违规文件/行/规则。
- `≥2` → **lint 脚本自身错误**(如路径错、规则文件损坏),停并报"lint 脚本错误",**不当违规甩锅用户代码,也不静默放行**。

端到端目标(CAP-2):给定 .proto,一条流水线产出的骨架+biz `go build ./...` 通过且 lint 退出 0。

---

## Step 4 — 关键节点记 vault(Story 4.3 / AD-9、AD-10、AD-13)

在关键节点(建项目 / 加服务 / 一次流水线 build+lint 全绿完成)主动记录:

```bash
python3 {project-root}/.claude/skills/bmad-agcore-dev/scripts/vault-write.py \
  --project "<ag-core 项目名(取自 go module/目录名,显式传入)>" \
  --type 决策 \
  --content "<agent 一阶理由:做了什么、为什么这么做>"
```

- 只记 **agent 一阶理由**(现场因果),**不做二阶价值判断**(那归人,AD-13)。
- 脚本写结构化 `20-项目/<项目名>.md`,agent 行带行首标记,**绝不改写人手写行**(AD-10)。
- 只有知识/经验/决策进 vault;项目 `.claude/ai-context` 属项目配置,不进 vault(NFR4)。

---

## Step 5 — 成果交付,人守关口(Story 3.5 / AD-13,不可抹除)

流水线产出 build 通过、lint 无违规的代码后:

1. **呈报产出摘要**:生成了哪些骨架、biz 填了什么、build/lint 结果、vault 记了什么。
2. **等人确认接受** —— build+lint 是**机器质量闸**(必过),但机器闸通过 **≠ 人已接受采纳**。二者分离。
3. 成果的最终接受由人确认,**不自动标记完成**。
4. 提炼出的可复用经验只作**草稿**(落 vault 00-Inbox/ 或标 draft),是否收录进长期经验区由人把关,agent 不自动收录(Story 4.4 / AD-13 经验限)。

> **红线**:任何后续自动化增强不得抹掉本步的人确认点(代码/记忆/经验三处人守关口同构)。
