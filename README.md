# docviz-suite-skill

English | [简体中文](./README.zh-CN.md)

<p align="center">
  <a href="https://github.com/feiloong7/docviz-suite-skill/actions/workflows/validate.yml"><img src="https://github.com/feiloong7/docviz-suite-skill/actions/workflows/validate.yml/badge.svg" alt="CI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/github/license/feiloong7/docviz-suite-skill" alt="License"></a>
  <img src="https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/version-1.0.0-blue" alt="Version">
</p>

Orchestrate upstream visualization skills to turn business rules, product requirement documents (PRD), system overviews, and architecture documents into a layered, offline-readable suite of visualizations — an understanding page, overview infographic, main diagram, detailed flowchart, full mind map, knowledge graph, and navigation page.

This skill **orchestrates** existing upstream skills instead of duplicating their rendering logic. It chains document understanding, user confirmation, per-artifact pre-generation checks, structural verification, and upstream update management into one traceable workflow.

## Table of Contents

- [Core Capabilities](#core-capabilities)
- [Supported Document Types](#supported-document-types)
- [Upstream Skills](#upstream-skills)
- [Repository Structure](#repository-structure)
- [Requirements](#requirements)
- [Quick Start](#quick-start)
- [Generation Modes](#generation-modes)
- [Upstream Check and Sync](#upstream-check-and-sync)
- [Local Validation](#local-validation)
- [Contributing and License](#contributing-and-license)

## Core Capabilities

- **Understand → confirm → generate** — no formal diagram is produced until the semantic plan is confirmed.
- **Three document profiles** — business rules, PRD, and system overview/architecture.
- **Unified reading path** — understanding → overview → main diagram → detailed flow → full mind map → knowledge graph → navigation.
- **Isolated run directory** — keeps source path, SHA-256, understanding notes, confirmation state, and verification report; never overwrites past results.
- **Per-artifact readiness check** — re-checks confirmation state, source drift, and artifact scope before every renderer call.
- **Upstream update management** — offline and read-only by default; explicit online check; backup, sync, and verify only after the user selects and confirms.
- **Offline delivery check** — validates files, JSON, navigation links, external scripts/styles/images, and external CSS dependencies.

## Supported Document Types

| Profile | Focus | Main diagram |
| --- | --- | --- |
| `business-rules` | Objects, events, branches, formulas, criteria, red lines, KPIs | Main flow, complex decisions, rule relations |
| `prd` | Roles, scenarios, features, permissions, states, exceptions, acceptance | User journey, lifecycle, interaction sequence |
| `system-overview` | System boundary, modules, data flow, interfaces, deployment, dependencies | Architecture, data flow, call sequence, lifecycle |

## Upstream Skills

| Skill | Purpose |
| --- | --- |
| `show-me` | Understanding page and result presentation |
| `methodology-visualization` | One-page overview infographic |
| `archify` | Main flow, architecture, data flow, sequence, and lifecycle diagrams |
| `flowchart-designer` | Standard detailed flows with editable Mermaid |
| `mindmapgenerator` | Full layered outline and interactive mind map |
| `graphify` | Knowledge graph, query, and impact analysis |

The upstream manifest and version baselines live in [`references/sources.json`](references/sources.json). Before running the full suite, install these skills into the target project's `.workbuddypro/skills/`; quick mode only depends on the understanding, overview, and main-diagram skills.

## Repository Structure

```text
docviz-suite-skill/
├── SKILL.md                         # Skill entry and mandatory workflow
├── references/
│   ├── orchestration.md             # Orchestration, fallback, and quality rules
│   ├── sources.json                 # Upstream sources and version baselines
│   └── profiles/
│       ├── business-rules.md
│       ├── prd.md
│       └── system-overview.md
├── scripts/
│   ├── docviz.py                    # plan, understand, confirm, check, verify
│   ├── upstream.py                  # check, backup, sync, rollback
│   ├── self_test.py                 # offline, isolated functional tests
│   └── validate_repo.py             # repo structure and reference checks
├── .github/
│   ├── workflows/validate.yml       # GitHub Actions validation
│   ├── ISSUE_TEMPLATE/
│   └── PULL_REQUEST_TEMPLATE.md
├── CHANGELOG.md
├── CONTRIBUTING.md
├── SECURITY.md
├── LICENSE
└── README.md
```

## Requirements

- Python 3.11+; scripts use only the standard library.
- A writable workspace; outputs default to `<workspace>/输出/`.
- The upstream skills and their own runtime dependencies; follow each installed `SKILL.md`.
- Graphify auto-extraction needs an LLM API Key; without one you may use "manual extraction + graphify native rendering", which must be labeled accordingly.
- GitHub checks use the public API (60 requests/hour/IP unauthenticated); set the `GITHUB_TOKEN` environment variable to raise the limit.

## Quick Start

Place this directory at `.workbuddypro/skills/docviz-suite-skill/` in your project, or run the scripts directly from this repo.

```bash
export DOCVIZ_HOME="/absolute/path/to/docviz-suite-skill"

python3 "$DOCVIZ_HOME/scripts/docviz.py" plan \
  --workspace "/absolute/path/to/workspace" \
  --source "/absolute/path/to/document.md" \
  --profile auto \
  --mode standard
```

This step only creates a plan awaiting confirmation. Extract DOCX, PDF, etc. into Markdown that preserves heading levels first.

### 1. Write the full-text understanding

Prepare `notes.json`:

```json
{
  "summary": "A one-line description of how the document works",
  "scope": ["Scope and non-goals"],
  "core_model": ["Core objects and their relations"],
  "key_points": ["Key flows, rules, or architecture relations"],
  "gaps": ["Document gaps or conflicts"],
  "questions": ["Items needing the user's explicit confirmation"],
  "chapter_coverage": [
    {"section": "Section name", "coverage": "Which artifact covers it"}
  ]
}
```

Merge it into the plan:

```bash
python3 "$DOCVIZ_HOME/scripts/docviz.py" annotate \
  --plan "<run-dir>/plan.json" \
  --notes "/absolute/path/to/notes.json"
```

Show `00_生成计划.md` to the user first. Only execute **after the user explicitly confirms**:

```bash
python3 "$DOCVIZ_HOME/scripts/docviz.py" confirm \
  --plan "<run-dir>/plan.json" \
  --approve "<approval-code-from-plan>"
```

### 2. Per-artifact pre-generation check

```bash
python3 "$DOCVIZ_HOME/scripts/docviz.py" assert-ready \
  --plan "<run-dir>/plan.json" \
  --artifact understanding
```

`artifact` must be an ID from `plan.json`. On success, the command returns the authorized absolute output path. Any source drift blocks subsequent generation.

### 3. Verify and present

```bash
python3 "$DOCVIZ_HOME/scripts/docviz.py" verify \
  --plan "<run-dir>/plan.json"
```

Finally, open `00_可视化导航.html`. Structural verification does not replace business-semantic review or actual visual inspection.

## Generation Modes

- `quick`: understanding page, overview, main diagram, navigation.
- `standard`: full six visualization types plus source data.
- `deep`: standard plus relationship paths and change-impact analysis.

Each run defaults to:

```text
<workspace>/输出/docviz-runs/<document>-<run-id>/
```

## Upstream Check and Sync

The offline check never touches the network:

```bash
python3 "$DOCVIZ_HOME/scripts/upstream.py" check \
  --workspace "/absolute/path/to/workspace"
```

Go online only when the user explicitly asks to check for updates:

```bash
python3 "$DOCVIZ_HOME/scripts/upstream.py" check \
  --workspace "/absolute/path/to/workspace" --online
```

Checking never modifies skills. Sync only after the user explicitly selects a skill and confirms:

```bash
python3 "$DOCVIZ_HOME/scripts/upstream.py" sync \
  --workspace "/absolute/path/to/workspace" \
  --report "<workspace>/输出/docviz-updates/latest.json" \
  --skill archify \
  --approve "<approval-code-from-report>"
```

Sync is project-scoped only, with full backup, pinned-version download, in-package version verification, ZIP safety limits, failure rollback, and a structured receipt. User-level skills are never synced.

## Local Validation

```bash
python3 scripts/validate_repo.py --root .
python3 scripts/self_test.py --root .
```

Tests run in an isolated temp directory, without network access, and never modify real upstream skills. They cover document classification, the confirmation gate, per-artifact checks, source drift, external CSS dependencies, update confirmation, backup/rollback, malicious paths, and ZIP safety.

## Contributing and License

See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution and [SECURITY.md](SECURITY.md) for security.

The code and documentation in this repository use the [MIT License](LICENSE). Upstream skills keep their own licenses; this repository does not redistribute their implementations.
