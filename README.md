# docviz-suite-skill

<p align="center">
  <a href="https://github.com/feiloong7/docviz-suite-skill/actions/workflows/validate.yml"><img src="https://github.com/feiloong7/docviz-suite-skill/actions/workflows/validate.yml/badge.svg" alt="CI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/github/license/feiloong7/docviz-suite-skill" alt="License"></a>
  <img src="https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/version-1.0.0-blue" alt="Version">
</p>

Orchestrate upstream visualization skills to turn business rules, product requirement documents (PRD), system overviews, and architecture documents into a layered, offline-readable suite of visualizations — an understanding page, overview infographic, main diagram, detailed flowchart, full mind map, knowledge graph, and navigation page.

> **📖 Full documentation** — with an interactive **中文 / English** toggle — lives here:
> **[feiloong7.github.io/docviz-suite-skill](https://feiloong7.github.io/docviz-suite-skill/)** · [中英文一键切换的完整文档](https://feiloong7.github.io/docviz-suite-skill/)

## Highlights

- **Understand → confirm → generate** — no formal diagram is produced until the semantic plan is explicitly confirmed.
- **Three document profiles** — business rules, PRD, and system overview/architecture.
- **Isolated run directory** — keeps source path, SHA-256, notes, confirmation state, and verification report.
- **Per-artifact readiness check** — re-validates confirmation state, source drift, and artifact scope before every render.
- **Upstream update management** — offline by default; backup + sync only after explicit user confirmation.
- **Offline delivery check** — no external scripts/styles/images or CSS dependencies.

It orchestrates the upstream skills `show-me`, `methodology-visualization`, `archify`, `flowchart-designer`, `mindmapgenerator`, and `graphify` — without copying their rendering logic.

## Quick start

Place this directory at `.workbuddypro/skills/docviz-suite-skill/`, or run the scripts directly from this repo.

```bash
export DOCVIZ_HOME="/absolute/path/to/docviz-suite-skill"

python3 "$DOCVIZ_HOME/scripts/docviz.py" plan \
  --workspace "/absolute/path/to/workspace" \
  --source "/absolute/path/to/document.md" \
  --profile auto \
  --mode standard
```

This only creates a plan awaiting confirmation. See the [full documentation](https://feiloong7.github.io/docviz-suite-skill/) for the complete workflow, generation modes (`quick` / `standard` / `deep`), and upstream check-and-sync usage.

## Requirements

- Python 3.11+; scripts use only the standard library.
- A writable workspace; outputs default to `<workspace>/输出/`.
- Upstream skills installed to the target project's `.workbuddypro/skills/`.

## Local validation

```bash
python3 scripts/validate_repo.py --root .
python3 scripts/self_test.py --root .
```

## Contributing & License

See [CONTRIBUTING.md](CONTRIBUTING.md) and [SECURITY.md](SECURITY.md). Code and documentation are [MIT licensed](LICENSE).
