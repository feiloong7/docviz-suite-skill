---
name: docviz-suite-skill
description: 将业务规则、产品需求文档（PRD）、系统介绍或架构文档转化为可分层阅读、可离线打开的可视化成果，包括文档理解页、总览信息图、主流程/架构图、细节流程图、全量思维导图、关系知识图谱和导航页；用户要求理解文档并做可视化、梳理业务流程/产品功能/系统架构、生成一套分层图表、整合多个可视化技能，或检查并同步上游技能更新时使用；支持先给理解与生成计划、用户确认后再执行，以及保留源文件证据和覆盖检查。Converts business rules, PRDs, system overviews, or architecture documents into layered, offline-openable visualizations (understanding page, overview infographic, main flow/architecture diagram, detailed flowchart, full mind map, knowledge graph, and navigation page). Use when the user wants to understand and visualize a document, map business processes / product features / system architecture, generate a layered diagram suite, integrate multiple visualization skills, or check and sync upstream skill updates. Supports presenting an understanding and generation plan for user confirmation before executing, plus source-file evidence and coverage checks.
---

# Docviz Suite Skill

## 目标

把文档理解放在绘图之前，把用户确认放在生成之前。编排现有 `show-me`、`methodology-visualization`、`archify`、`flowchart-designer`、`mindmapgenerator`、`graphify`，不复制其渲染实现；每次生成使用独立目录，不覆盖既有成果。

## 硬性约束

1. 仅以源文档和用户提供资料为事实来源。缺失信息写“文档未说明”，不补造角色、公式、接口、优先级或架构组件。
2. 未经用户明确确认 `00_生成计划.md`，不得生成任何正式 HTML/SVG/图谱。读取文档、编写大纲草案和计划属于确认前工作。
3. 确认后先校验源文件 SHA-256；若源文件已变，停止并重新生成计划，不沿用旧理解。
4. 默认写入 `<工作空间>/输出/docviz-runs/<文档名>-<运行ID>/`。不覆盖其他运行目录，不修改源文档。
5. 所有交付 HTML 优先单文件、零外部依赖、离线可读；图谱等工具自带运行时可保留其原生能力，但不得新增 CDN 依赖。
6. 更新检查默认离线且只读。只有用户明确要求查新时才联网；只有用户明确选择待更新技能并确认后才执行同步。
7. 不用视觉美观替代事实准确性。不能验证的版式、关系、命令或更新结果必须如实标注。

## 工作流

### 1. 提取并通读文档

优先取得保留标题层级的 Markdown 或纯文本。DOCX/PDF 等先使用当前环境的文档解析能力提取，再进入本流程；不要仅凭文件名、目录或摘要画图。

记录源文件绝对路径、大小、修改时间和 SHA-256。通读全文，长文档也须覆盖所有章节；补充阅读只用于澄清，不替代源文档。

### 2. 识别文档类型并生成确认计划

运行：

```bash
export DOCVIZ_HOME="<docviz-suite-skill 的绝对路径>"
python3 "$DOCVIZ_HOME/scripts/docviz.py" plan \
  --workspace "<工作空间>" \
  --source "<文档或提取后的 Markdown>" \
  --profile auto \
  --mode standard
```

`profile` 可选 `business-rules`、`prd`、`system-overview`、`auto`。自动识别置信度不足时必须让用户选择，不得猜测。

通读全文后，把语义理解写入一个 JSON 笔记文件，再合并进计划；脚本只做结构识别，不能代替助手理解全文：

```bash
python3 "$DOCVIZ_HOME/scripts/docviz.py" annotate \
  --plan "<运行目录>/plan.json" \
  --notes "<理解笔记.json>"
```

笔记只允许 `summary`、`scope`、`core_model`、`key_points`、`gaps`、`questions`、`chapter_coverage` 七类字段。`summary` 为字符串，其余为数组；`chapter_coverage` 使用 `{ "section": "章节", "coverage": "覆盖方式" }` 项。自动识别不确定时，可在 annotate 中用 `--profile` 写入用户选择的类型。

随后读取 [orchestration.md](references/orchestration.md) 和对应 profile：

- [业务规则](references/profiles/business-rules.md)
- [产品需求文档](references/profiles/prd.md)
- [系统介绍/架构](references/profiles/system-overview.md)

将计划中的“文档理解摘要、范围/非目标、关键对象与关系、章节覆盖、缺口与歧义、拟生成产物”展示给用户。对分支、公式、角色、模块和外部依赖做重点复核。使用一次集中确认，避免多轮琐碎提问；只有会改变整体结构的分歧才需要单独选择。

### 3. 记录用户确认

只有用户明确回复确认后，才运行：

```bash
python3 "$DOCVIZ_HOME/scripts/docviz.py" confirm \
  --plan "<运行目录>/plan.json" \
  --approve "<计划中的确认码>"
```

若用户要求修改，先更新计划并重新展示。用户明确说“继续”“确认”或“按计划执行”可视为对当前计划的确认；沉默、超时或工具跳过一律不代表同意。

### 4. 检查上游并按顺序生成

先运行离线检查，确认所需上游技能可用：

```bash
python3 "$DOCVIZ_HOME/scripts/upstream.py" check --workspace "<工作空间>"
```

缺失上游时报告具体技能及影响，用户同意后再安装；不要静默替换渲染器。

**每生成一个产物前都必须运行就绪检查**，不能只在整批生成前检查一次：

```bash
python3 "$DOCVIZ_HOME/scripts/docviz.py" assert-ready \
  --plan "<运行目录>/plan.json" --artifact "<计划中的产物ID>"
```

该命令重新检查 approved 状态、源文件 SHA-256 和产物范围，并返回该产物允许写入的绝对路径。检查失败时立即停止，不调用上游渲染。源文件在生成过程中变化时，后续产物同样会被阻止。

按以下顺序生成，每一步复用同一份已确认理解，不重新解释文档：

1. `01_文档理解.html`：调用 `show-me`，回答“文档讲什么、如何运转、哪些点必须注意”。
2. `02_总览信息图.html`：调用 `methodology-visualization`，形成一页核心结构和关系总览。
3. 主图：调用 `archify`，业务/PRD 以主流程为主，系统文档选择架构、数据流、时序或生命周期。
4. `04_细节流程.html`：调用 `flowchart-designer`，展开复杂判定、异常和子流程；保留可编辑 Mermaid。
5. 全量基线：调用 `mindmapgenerator`，生成保留章节覆盖的分层大纲与可折叠导图。
6. 关系图谱：调用 `graphify`，生成可搜索、可筛选、可追溯关系图；无 LLM Key 时可人工抽取原生 `graph.json` 后离线渲染，但必须说明这不是 graphify 自动语义抽取。
7. `00_可视化导航.html`：最后生成，链接全部实际存在的成果，说明推荐阅读顺序、源文件哈希和覆盖情况。

具体选择、降级规则和质量门槛见 [orchestration.md](references/orchestration.md)。quick 模式只生成理解页、总览、主图和导航；standard 生成完整套件；deep 在 standard 上增加关系路径与影响分析。

### 5. 验证与交付

```bash
python3 "$DOCVIZ_HOME/scripts/docviz.py" verify --plan "<运行目录>/plan.json"
```

检查源文件未漂移、计划内文件存在、JSON 可解析、导航链接有效、HTML 未引用外部脚本/样式/图片。再按各上游技能的验收要求检查图内容和版式。

调用 `present_files`，将 `00_可视化导航.html` 放第一位；若用户更需要先理解文档，可将 `01_文档理解.html` 放第一位。最终回复说明文档类型、已交付内容、验证结果、未解决缺口及运行目录，不只给文件路径。

## 上游查新与同步

### 只读查新

用户询问“上游是否更新/检查技能更新”时运行：

```bash
python3 "$DOCVIZ_HOME/scripts/upstream.py" check \
  --workspace "<工作空间>" --online
```

默认报告写入 `<工作空间>/输出/docviz-updates/latest.json`。逐项展示已安装版本、上游版本/提交、状态和同步影响。`version_differs` 只表示版本字符串无法安全比较，不等于可安全升级；网络失败不得写成“已是最新”。

### 确认后同步

仅在用户明确选定技能并确认后运行：

```bash
python3 "$DOCVIZ_HOME/scripts/upstream.py" sync \
  --workspace "<工作空间>" \
  --report "<工作空间>/输出/docviz-updates/latest.json" \
  --skill "<用户选择的技能ID>" \
  --approve "<报告中的确认码>"
```

同步仅限项目级 `.workbuddypro/skills`。先将完整原目录备份到 `输出/docviz-backups/`，校验下载包中的 `SKILL.md` 和路径安全，再替换并验证。任何失败均报告备份位置和回滚结果；不得自动同步全部技能。清单与来源见 [sources.json](references/sources.json)。
