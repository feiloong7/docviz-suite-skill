# docviz-suite-skill

[English](./README.md) | 简体中文

<p align="center">
  <a href="https://github.com/feiloong7/docviz-suite-skill/actions/workflows/validate.yml"><img src="https://github.com/feiloong7/docviz-suite-skill/actions/workflows/validate.yml/badge.svg" alt="CI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/github/license/feiloong7/docviz-suite-skill" alt="License"></a>
  <img src="https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/version-1.0.0-blue" alt="Version">
</p>

编排上游可视化技能，把业务规则、产品需求文档（PRD）、系统介绍与架构文档，转化为可分层阅读、可离线打开的一整套可视化成果——包括文档理解页、总览信息图、主图、细节流程图、全量思维导图、关系知识图谱和导航页。

本技能采用**编排引用**方式调用现有上游技能，不复制其渲染实现。它将文档理解、用户确认、逐产物生成前检查、结构验证和上游更新管理串成一条可追溯流程。

## 目录

- [核心能力](#核心能力)
- [支持的文档类型](#支持的文档类型)
- [上游技能](#上游技能)
- [仓库结构](#仓库结构)
- [环境要求](#环境要求)
- [快速开始](#快速开始)
- [生成模式](#生成模式)
- [上游查新与同步](#上游查新与同步)
- [本地验证](#本地验证)
- [贡献与许可](#贡献与许可)

## 核心能力

- **先理解、再确认、后生成**：未确认语义计划时，不生成正式图表。
- **三类文档 Profile**：业务规则、PRD、系统介绍/架构。
- **统一阅读路径**：理解页 → 总览 → 主图 → 细节流程 → 全量导图 → 关系图谱 → 导航。
- **独立运行目录**：保留源文件路径、SHA-256、理解笔记、确认状态和验证报告，不覆盖历史成果。
- **逐产物就绪检查**：每次调用渲染器前重新检查确认状态、源文件漂移和产物范围。
- **上游更新管理**：默认离线只读；显式联网查新；用户选择并确认后才备份、同步和验证。
- **离线交付检查**：检查文件、JSON、导航链接、外部脚本/样式/图片及 CSS 外部依赖。

## 支持的文档类型

| Profile | 重点提取 | 主图选择 |
| --- | --- | --- |
| `business-rules` | 业务对象、事件、分支、公式、口径、红线、KPI | 主流程、复杂判定、规则关系 |
| `prd` | 角色、场景、功能、权限、状态、异常、验收 | 用户旅程、生命周期、交互时序 |
| `system-overview` | 系统边界、模块、数据流、接口、部署、依赖 | 架构、数据流、调用时序、生命周期 |

## 上游技能

| 技能 | 用途 |
| --- | --- |
| `show-me` | 文档理解页与成果呈现 |
| `methodology-visualization` | 一页式总览信息图 |
| `archify` | 主流程、架构、数据流、时序和生命周期主图 |
| `flowchart-designer` | 标准细节流程与可编辑 Mermaid |
| `mindmapgenerator` | 全量分层大纲与交互思维导图 |
| `graphify` | 关系知识图谱、查询与影响分析 |

上游清单及版本基线见 [`references/sources.json`](references/sources.json)。使用完整套件前，请将这些技能安装到目标项目的 `.workbuddypro/skills/`；quick 模式只依赖理解页、总览和主图相关技能。

## 仓库结构

```text
docviz-suite-skill/
├── SKILL.md                         # 技能入口与强制工作流
├── references/
│   ├── orchestration.md             # 编排、降级与质量规则
│   ├── sources.json                 # 上游来源与版本基线
│   └── profiles/
│       ├── business-rules.md
│       ├── prd.md
│       └── system-overview.md
├── scripts/
│   ├── docviz.py                    # 计划、理解、确认、逐产物检查、验证
│   ├── upstream.py                  # 上游查新、备份、同步与回滚
│   ├── self_test.py                 # 无网络、隔离功能测试
│   └── validate_repo.py             # 仓库结构与引用检查
├── .github/
│   ├── workflows/validate.yml       # GitHub Actions 自动校验
│   ├── ISSUE_TEMPLATE/
│   └── PULL_REQUEST_TEMPLATE.md
├── CHANGELOG.md
├── CONTRIBUTING.md
├── SECURITY.md
├── LICENSE
└── README.md
```

## 环境要求

- Python 3.11+；仓库脚本只使用 Python 标准库。
- 工作空间可写，产物默认写入 `<工作空间>/输出/`。
- 各上游技能及其自身运行依赖；具体以安装版本的 `SKILL.md` 为准。
- Graphify 自动语义抽取需要用户已有 LLM API Key；无 Key 时可采用「人工语义抽取 + graphify 原生渲染」，必须如实标注。
- 上游查新对 GitHub 使用公开 API，未认证时限流为 60 次/小时/IP；可设置 `GITHUB_TOKEN` 环境变量提升额度。

## 快速开始

将本仓库目录放到项目的 `.workbuddypro/skills/docviz-suite-skill/`，或在当前仓库直接运行脚本。

```bash
export DOCVIZ_HOME="/absolute/path/to/docviz-suite-skill"

python3 "$DOCVIZ_HOME/scripts/docviz.py" plan \
  --workspace "/absolute/path/to/workspace" \
  --source "/absolute/path/to/document.md" \
  --profile auto \
  --mode standard
```

此步骤只生成待确认计划。DOCX、PDF 等先提取为保留标题层级的 Markdown。

### 1. 写入全文理解

准备 `notes.json`：

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

合并到计划：

```bash
python3 "$DOCVIZ_HOME/scripts/docviz.py" annotate \
  --plan "<运行目录>/plan.json" \
  --notes "/absolute/path/to/notes.json"
```

先把 `00_生成计划.md` 展示给用户。**只有用户明确确认后**才执行：

```bash
python3 "$DOCVIZ_HOME/scripts/docviz.py" confirm \
  --plan "<运行目录>/plan.json" \
  --approve "<计划中的确认码>"
```

### 2. 每个产物生成前检查

```bash
python3 "$DOCVIZ_HOME/scripts/docviz.py" assert-ready \
  --plan "<运行目录>/plan.json" \
  --artifact understanding
```

`artifact` 必须来自 `plan.json` 中的产物 ID。检查通过后，命令返回允许写入的绝对路径。任何源文件漂移都会阻止后续生成。

### 3. 验证并呈现

```bash
python3 "$DOCVIZ_HOME/scripts/docviz.py" verify \
  --plan "<运行目录>/plan.json"
```

最后打开 `00_可视化导航.html`。结构验证不替代业务语义复核和实际视觉检查。

## 生成模式

- `quick`：理解页、总览、主图、导航。
- `standard`：完整六类可视化及源数据。
- `deep`：standard 加关系路径与变更影响分析。

每次运行默认位于：

```text
<工作空间>/输出/docviz-runs/<文档名>-<运行ID>/
```

## 上游查新与同步

离线检查不会访问网络：

```bash
python3 "$DOCVIZ_HOME/scripts/upstream.py" check \
  --workspace "/absolute/path/to/workspace"
```

用户明确要求查新时才联网：

```bash
python3 "$DOCVIZ_HOME/scripts/upstream.py" check \
  --workspace "/absolute/path/to/workspace" --online
```

查新不会修改技能。只有用户明确选择技能并确认后才同步：

```bash
python3 "$DOCVIZ_HOME/scripts/upstream.py" sync \
  --workspace "/absolute/path/to/workspace" \
  --report "<工作空间>/输出/docviz-updates/latest.json" \
  --skill archify \
  --approve "<报告中的确认码>"
```

同步仅限项目级技能，支持完整备份、固定版本下载、包内版本核验、ZIP 安全限制、失败回滚和结构化回执。用户级技能不会被同步。

## 本地验证

```bash
python3 scripts/validate_repo.py --root .
python3 scripts/self_test.py --root .
```

测试使用临时隔离目录，不访问网络，不修改真实上游技能。覆盖文档分类、确认门、逐产物检查、源文件漂移、CSS 外部依赖、更新确认、备份回滚、恶意路径与 ZIP 安全等场景。

## 贡献与许可

贡献流程见 [CONTRIBUTING.md](CONTRIBUTING.md)，安全问题见 [SECURITY.md](SECURITY.md)。

本仓库代码与文档采用 [MIT License](LICENSE)。上游技能仍遵循各自许可证；本仓库不重新分发其实现。
