# BMAD AG

[![Latest Release](https://img.shields.io/github/v/release/frochyzhang/bmad-ag?label=release)](https://github.com/frochyzhang/bmad-ag/releases/latest)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Node.js](https://img.shields.io/badge/Node.js-%3E%3D20.12.0-brightgreen)](https://nodejs.org)
[![Go for ag-core](https://img.shields.io/badge/Go-%3E%3D1.24.8-00ADD8)](https://go.dev/dl/)

BMAD AG is an independent fork of
[BMad Method](https://github.com/bmad-code-org/BMAD-METHOD), tailored for
teams that use the `ag-core` Go microservice framework while retaining the
structured, agent-assisted software delivery workflows from upstream.

> [!IMPORTANT]
> This is an independent, unofficial fork. It is not affiliated with,
> sponsored by, or endorsed by BMad Code, LLC. BMad, BMad Method, and BMad
> Core are trademarks of BMad Code, LLC. See [Upstream and licensing](#upstream-and-licensing).

## What This Fork Adds

- **Optional built-in ag-core module** — available during installation but not
  selected by default, so non-Go projects stay lightweight.
- **Proto-first development pipeline** — load framework knowledge, define
  Protobuf APIs, generate an `aggo` scaffold, implement business logic, then
  pass build and lint gates.
- **ag-core knowledge integration** — lazily loads patterns from the external
  `ag-skills` knowledge base instead of relying on generic Go conventions.
- **Framework guardrails** — `ag-core-lint` detects direct use of competing or
  low-level libraries when an ag-core wrapper should be used.
- **Project-specific AI constraints** — generates an ag-core instruction file
  from the installed knowledge base without overwriting an existing custom file.
- **Obsidian development memory** — records key decisions, implementation
  milestones, and reusable lessons in a configured Obsidian vault.
- **Fork-specific installer defaults** — ag-core is opt-in, Game Dev Studio is
  currently hidden for new installations, and existing installations remain
  upgrade-compatible.

## Included Modules

The installer combines built-in modules from this repository with optional
modules maintained in the upstream ecosystem.

| Module                           | ID          | Availability        | Purpose                                                                 |
| -------------------------------- | ----------- | ------------------- | ----------------------------------------------------------------------- |
| BMad Core Module                 | `core`      | Always installed    | Shared configuration and utilities                                      |
| BMad Method                      | `bmm`       | Selected by default | Analysis, planning, architecture, and implementation workflows          |
| BMAD ag-core Skills              | `agcore`    | Optional, built in  | ag-core knowledge, generation pipeline, guardrails, and vault recording |
| BMad Loop                        | `bmad-loop` | Optional            | Deterministic unattended development loop with adversarial review       |
| BMad Test Architect              | `tea`       | Optional            | Test strategy, automation, traceability, and release gates              |
| BMad Builder                     | `bmb`       | Optional            | Build custom agents, workflows, and modules                             |
| BMad Creative Intelligence Suite | `cis`       | Optional            | Ideation, storytelling, design thinking, and problem-solving            |
| Whiteport Design Studio          | `wds`       | Optional            | UX and design-first planning workflows                                  |

Game Dev Studio is temporarily hidden for new installations. Existing projects
that already contain its `gds` module remain recognized during updates.

## Installation

### Prerequisites

- [Node.js](https://nodejs.org) 20.12 or later
- Git
- [uv](https://docs.astral.sh/uv/) recommended for Python-based workflows
- Go 1.24.8 or later only when installing the optional `agcore` module
- An Obsidian vault path when installing `agcore`

### Install the Fork from GitHub

Run the installer from the current `main` branch:

```bash
npx github:frochyzhang/bmad-ag#main install
```

For a reproducible installation, choose a tag from
[GitHub Releases](https://github.com/frochyzhang/bmad-ag/releases) and pin it:

```bash
BMAD_AG_REF=v1.1.4
npx github:frochyzhang/bmad-ag#${BMAD_AG_REF}" bmad install
```

The fork uses `v1.x` GitHub Release tags, while the inherited package metadata
still reports the underlying BMad Method version, currently `6.10.0`. These are
separate version lines.

Do not use `npx bmad-method@latest install` when you intend to install BMAD AG.
That command downloads the upstream npm package and does not include this
fork's ag-core integration or installer changes.

### Install from a Local Checkout

```bash
git clone https://github.com/frochyzhang/bmad-ag.git
cd bmad-ag
npm ci
```

From the project that should receive the installation, point `npx` at the local
checkout:

```bash
cd /path/to/your/project
npx --package /absolute/path/to/bmad-ag bmad install
```

### Non-Interactive Installation

Install the standard BMad Method workflow into a Claude Code project:

```bash
npx --package github:frochyzhang/bmad-ag#main bmad install \
  --directory /path/to/project \
  --modules bmm \
  --tools claude-code \
  --yes
```

List supported tool IDs and module configuration keys before scripting an
installation:

```bash
npx --package github:frochyzhang/bmad-ag#main bmad install --list-tools
npx --package github:frochyzhang/bmad-ag#main bmad install --list-options
```

## Installing ag-core Support

In an interactive installation, select **BMAD ag-core Skills** in the official
module picker. The installer asks for the Obsidian vault root and uses defaults
for the ag-skills checkout and knowledge staleness threshold.

For a non-interactive installation, include `agcore` and provide the vault path
explicitly:

```bash
npx --package github:frochyzhang/bmad-ag#main bmad install \
  --directory /path/to/ag-core-project \
  --modules bmm,agcore \
  --tools claude-code \
  --set agcore.vault_path=/absolute/path/to/obsidian-vault \
  --yes
```

After ag-core files are installed, the post-install step attempts to:

1. Validate Go 1.24.8 or later.
2. Install `aggo`, `gen-go-db`, and the ag-core Protobuf generators.
3. Clone the external `ag-skills` knowledge base.
4. Generate project-level ag-core AI constraints.

This setup is best-effort. A missing Go toolchain or temporary clone failure
does not abort the base BMad installation; ag-core development skills retry
missing setup when they are first used.

## Using the Installed Skills

Launch the selected AI tool from the installed project directory. Useful entry
points include:

- `bmad-help` — explain what to do next based on the current project state.
- `bmad-agcore-skills` — load the relevant ag-core patterns and check knowledge
  freshness.
- `bmad-agcore-dev` — run the proto-to-scaffold-to-business-code pipeline with
  build, lint, and vault gates.
- `bmad-loop-setup` — finish configuring BMad Loop after selecting that module.

Installed skills and their exact locations are recorded in the generated
manifest and summarized when installation completes.

## Updating

Run the same GitHub or local-checkout installer command against a project that
already contains `_bmad`. The installer detects the existing installation and
offers update or quick-update flows while preserving user configuration and
custom files.

Deprecated modules such as Game Dev Studio are hidden for new projects but
remain visible to projects where they were previously installed.

## Development and Validation

Install dependencies and run the repository quality gate:

```bash
npm ci
npm run quality
```

Useful targeted checks:

```bash
npm run validate:skills
node test/test-installation-components.js
```

Before pushing, run `npm ci && npm run quality` on `HEAD` in the exact checkout
being pushed. Commit messages follow [Conventional Commits](https://www.conventionalcommits.org/).

## Releases and Issues

- [BMAD AG releases](https://github.com/frochyzhang/bmad-ag/releases)
- [BMAD AG issues](https://github.com/frochyzhang/bmad-ag/issues)
- [Upstream BMad Method](https://github.com/bmad-code-org/BMAD-METHOD)

## Upstream and Licensing

This repository is derived from
[bmad-code-org/BMAD-METHOD](https://github.com/bmad-code-org/BMAD-METHOD) and
retains its open-source notices and contributor attribution.

The software is available under the [MIT License](LICENSE). The license applies
to the software, not to upstream trademarks. BMad, BMad Method, BMad Core, the
upstream logos, and related branding are trademarks of BMad Code, LLC. Review
[TRADEMARK.md](TRADEMARK.md) before redistributing or renaming this fork.

This independent fork does not claim official status, certification,
partnership, sponsorship, or endorsement from BMad Code, LLC.
