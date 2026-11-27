# docviz-suite-skill

> 把业务规则、产品需求文档（PRD）、系统介绍与架构文档，转化为可分层阅读、可离线打开的一整套可视化成果。
>
> Turn business rules, product requirement documents (PRD), system overviews, and architecture documents into a layered, offline-readable suite of visualizations.

本技能采用**编排引用**方式调用现有上游技能，不复制其渲染实现。它将文档理解、用户确认、逐产物生成前检查、结构验证和上游更新管理串成一条可追溯流程。

This skill **orchestrates** existing upstream skills instead of duplicating their rendering logic. It chains document understanding, user confirmation, per-artifact pre-generation checks, structural verification, and upstream update management into one traceable workflow.

## 目录 Table of Contents

- [核心能力 Core Capabilities](#核心能力-core-capabilities)
- [支持的文档类型 Supported Document Types](#支持的文档类型-supported-document-types)
- [上游技能 Upstream Skills](#上游技能-upstream-skills)
- [仓库结构 Repository Structure](#仓库结构-repository-structure)
- [环境要求 Requirements](#环境要求-requirements)
- [快速开始 Quick Start](#快速开始-quick-start)
- [生成模式 Generation Modes](#生成模式-generation-modes)
- [上游查新与同步 Upstream Check and Sync](#上游查新与同步-upstream-check-and-sync)
- [本地验证 Local Validation](#本地验证-local-validation)
- [贡献与许可 Contributing and License](#贡献与许可-contributing-and-license)

## 核心能力 Core Capabilities

- **先理解、再确认、后生成 / Understand → confirm → generate**：未确认语义计划时，不生成正式图表。No formal diagram is produced until the semantic plan is confirmed.
- **三类文档 Profile / Three document profiles**：业务规则、PRD、系统介绍/架构。Business rules, PRD, and system overview/architecture.
- **统一阅读路径 / Unified reading path**：理解页 → 总览 → 主图 → 细节流程 → 全量导图 → 关系图谱 → 导航。Understanding → overview → main diagram → detailed flow → full mind map → knowledge graph → navigation.
- **独立运行目录 / Isolated run directory**：保留源文件路径、SHA-256、理解笔记、确认状态和验证报告，不覆盖历史成果。Keeps source path, SHA-256, understanding notes, confirmation state, and verification report; never overwrites past results.
- **逐产物就绪检查 / Per-artifact readiness check**：每次调用渲染器前重新检查确认状态、源文件漂移和产物范围。Re-checks confirmation state, source drift, and artifact scope before every renderer call.
- **上游更新管理 / Upstream update management**：默认离线只读；显式联网查新；用户选择并确认后才备份、同步和验证。Offline and read-only by default; explicit online check; backup, sync, and verify only after the user selects and confirms.
- **离线交付检查 / Offline delivery check**：检查文件、JSON、导航链接、外部脚本/样式/图片及 CSS 外部依赖。Validates files, JSON, navigation links, external scripts/styles/images, and external CSS dependencies.

## 支持的文档类型 Supported Document Types

| Profile | 重点提取 Focus | 主图选择 Main diagram |
| --- | --- | --- |
| `business-rules` | 业务对象、事件、分支、公式、口径、红线、KPI<br>Objects, events, branches, formulas, criteria, red lines, KPIs | 主流程、复杂判定、规则关系<br>Main flow, complex decisions, rule relations |
| `prd` | 角色、场景、功能、权限、状态、异常、验收<br>Roles, scenarios, features, permissions, states, exceptions, acceptance | 用户旅程、生命周期、交互时序<br>User journey, lifecycle, interaction sequence |
| `system-overview` | 系统边界、模块、数据流、接口、部署、依赖<br>System boundary, modules, data flow, interfaces, deployment, dependencies | 架构、数据流、调用时序、生命周期<br>Architecture, data flow, call sequence, lifecycle |

## 上游技能 Upstream Skills

| 技能 Skill | 用途 Purpose |
| --- | --- |
| `show-me` | 文档理解页与成果呈现<br>Understanding page and result presentation |
| `methodology-visualization` | 一页式总览信息图<br>One-page overview infographic |
| `archify` | 主流程、架构、数据流、时序和生命周期主图<br>Main flow, architecture, data flow, sequence, and lifecycle diagrams |
| `flowchart-designer` | 标准细节流程与可编辑 Mermaid<br>Standard detailed flows with editable Mermaid |
| `mindmapgenerator` | 全量分层大纲与交互思维导图<br>Full layered outline and interactive mind map |
| `graphify` | 关系知识图谱、查询与影响分析<br>Knowledge graph, query, and impact analysis |

上游清单及版本基线见 [`references/sources.json`](references/sources.json)。使用完整套件前，请将这些技能安装到目标项目的 `.workbuddypro/skills/`；quick 模式只依赖理解页、总览和主图相关技能。

The upstream manifest and version baselines live in [`references/sources.json`](references/sources.json). Before running the full suite, install these skills into the target project's `.workbuddypro/skills/`; quick mode only depends on the understanding, overview, and main-diagram skills.

## 仓库结构 Repository Structure

```text
docviz-suite-skill/
├── SKILL.md                         # 技能入口与强制工作流 / Skill entry and mandatory workflow
├── references/
│   ├── orchestration.md             # 编排、降级与质量规则 / Orchestration, fallback, quality rules
│   ├── sources.json                 # 上游来源与版本基线 / Upstream sources and version baselines
│   └── profiles/
│       ├── business-rules.md
│       ├── prd.md
│       └── system-overview.md
├── scripts/
│   ├── docviz.py                    # 计划、理解、确认、逐产物检查、验证 / plan, understand, confirm, check, verify
│   ├── upstream.py                  # 上游查新、备份、同步与回滚 / check, backup, sync, rollback
│   ├── self_test.py                 # 无网络、隔离功能测试 / offline, isolated functional tests
│   └── validate_repo.py             # 仓库结构与引用检查 / repo structure and reference checks
├── .github/
│   ├── workflows/validate.yml       # GitHub Actions 自动校验 / GitHub Actions validation
│   ├── ISSUE_TEMPLATE/
│   └── PULL_REQUEST_TEMPLATE.md
├── CHANGELOG.md
├── CONTRIBUTING.md
├── SECURITY.md
├── LICENSE
└── README.md
```

## 环境要求 Requirements

- Python 3.9+；仓库脚本只使用 Python 标准库。Python 3.9+; scripts use only the standard library.
- 工作空间可写，产物默认写入 `<工作空间>/输出/`。A writable workspace; outputs default to `<workspace>/输出/`.
- 各上游技能及其自身运行依赖；具体以安装版本的 `SKILL.md` 为准。The upstream skills and their own runtime dependencies; follow each installed `SKILL.md`.
- Graphify 自动语义抽取需要用户已有 LLM API Key；无 Key 时可采用“人工语义抽取 + graphify 原生渲染”，必须如实标注。Graphify auto-extraction needs an LLM API Key; without one you may use "manual extraction + graphify native rendering", which must be labeled accordingly.
- 上游查新对 GitHub 使用公开 API，未认证时限流为 60 次/小时/IP；可设置 `GITHUB_TOKEN` 环境变量提升额度。GitHub checks use the public API (60 requests/hour/IP unauthenticated); set the `GITHUB_TOKEN` environment variable to raise the limit.

## 快速开始 Quick Start

将本仓库目录放到项目的 `.workbuddypro/skills/docviz-suite-skill/`，或在当前仓库直接运行脚本。Place this directory at `.workbuddypro/skills/docviz-suite-skill/` in your project, or run the scripts directly from this repo.

```bash
export DOCVIZ_HOME="/absolute/path/to/docviz-suite-skill"

python3 "$DOCVIZ_HOME/scripts/docviz.py" plan \
  --workspace "/absolute/path/to/workspace" \
  --source "/absolute/path/to/document.md" \
  --profile auto \
  --mode standard
```

此步骤只生成待确认计划。DOCX、PDF 等先提取为保留标题层级的 Markdown。This step only creates a plan awaiting confirmation. Extract DOCX, PDF, etc. into Markdown that preserves heading levels first.

### 1. 写入全文理解 Write the full-text understanding

准备 `notes.json`：Prepare `notes.json`:

```json
{
  "summary": "一句话说明文档如何运转",
  "scope": ["范围与非目标"],
  "core_model": ["核心对象及其关系"],
  "key_points": ["关键流程、规则或架构关系"],
  "gaps": ["文档缺口或冲突"],
  "questions": ["需要用户重点确认的事项"],
  "chapter_coverage": [
    {"section": "章节名", "coverage": "计划由哪个产物覆盖"}
  ]
}
```

合并到计划：Merge it into the plan:

```bash
python3 "$DOCVIZ_HOME/scripts/docviz.py" annotate \
  --plan "<运行目录>/plan.json" \
  --notes "/absolute/path/to/notes.json"
```

先把 `00_生成计划.md` 展示给用户。**只有用户明确确认后**才执行：Show `00_生成计划.md` to the user first. Only execute **after the user explicitly confirms**:

```bash
python3 "$DOCVIZ_HOME/scripts/docviz.py" confirm \
  --plan "<运行目录>/plan.json" \
  --approve "<计划中的确认码>"
```

### 2. 每个产物生成前检查 Per-artifact pre-generation check

```bash
python3 "$DOCVIZ_HOME/scripts/docviz.py" assert-ready \
  --plan "<运行目录>/plan.json" \
  --artifact understanding
```

`artifact` 必须来自 `plan.json` 中的产物 ID。检查通过后，命令返回允许写入的绝对路径。任何源文件漂移都会阻止后续生成。`artifact` must be an ID from `plan.json`. On success, the command returns the authorized absolute output path. Any source drift blocks subsequent generation.

### 3. 验证并呈现 Verify and present

```bash
python3 "$DOCVIZ_HOME/scripts/docviz.py" verify \
  --plan "<运行目录>/plan.json"
```

最后打开 `00_可视化导航.html`。结构验证不替代业务语义复核和实际视觉检查。Finally, open `00_可视化导航.html`. Structural verification does not replace business-semantic review or actual visual inspection.

## 生成模式 Generation Modes

- `quick`：理解页、总览、主图、导航。Understanding page, overview, main diagram, navigation.
- `standard`：完整六类可视化及源数据。Full six visualization types plus source data.
- `deep`：standard 加关系路径与变更影响分析。standard plus relationship paths and change-impact analysis.

每次运行默认位于：Each run defaults to:

```text
<工作空间>/输出/docviz-runs/<文档名>-<运行ID>/
```

## 上游查新与同步 Upstream Check and Sync

离线检查不会访问网络：The offline check never touches the network:

```bash
python3 "$DOCVIZ_HOME/scripts/upstream.py" check \
  --workspace "/absolute/path/to/workspace"
```

用户明确要求查新时才联网：Go online only when the user explicitly asks to check for updates:

```bash
python3 "$DOCVIZ_HOME/scripts/upstream.py" check \
  --workspace "/absolute/path/to/workspace" --online
```

查新不会修改技能。只有用户明确选择技能并确认后才同步：Checking never modifies skills. Sync only after the user explicitly selects a skill and confirms:

```bash
python3 "$DOCVIZ_HOME/scripts/upstream.py" sync \
  --workspace "/absolute/path/to/workspace" \
  --report "<工作空间>/输出/docviz-updates/latest.json" \
  --skill archify \
  --approve "<报告中的确认码>"
```

同步仅限项目级技能，支持完整备份、固定版本下载、包内版本核验、ZIP 安全限制、失败回滚和结构化回执。用户级技能不会被同步。Sync is project-scoped only, with full backup, pinned-version download, in-package version verification, ZIP safety limits, failure rollback, and a structured receipt. User-level skills are never synced.

## 本地验证 Local Validation

```bash
python3 scripts/validate_repo.py --root .
python3 scripts/self_test.py --root .
```

测试使用临时隔离目录，不访问网络，不修改真实上游技能。覆盖文档分类、确认门、逐产物检查、源文件漂移、CSS 外部依赖、更新确认、备份回滚、恶意路径与 ZIP 安全等场景。Tests run in an isolated temp directory, without network access, and never modify real upstream skills. They cover document classification, the confirmation gate, per-artifact checks, source drift, external CSS dependencies, update confirmation, backup/rollback, malicious paths, and ZIP safety.

## 贡献与许可 Contributing and License

贡献流程见 [CONTRIBUTING.md](CONTRIBUTING.md)，安全问题见 [SECURITY.md](SECURITY.md)。See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution and [SECURITY.md](SECURITY.md) for security.

本仓库代码与文档采用 [MIT License](LICENSE)。上游技能仍遵循各自许可证；本仓库不重新分发其实现。The code and documentation in this repository use the [MIT License](LICENSE). Upstream skills keep their own licenses; this repository does not redistribute their implementations.
