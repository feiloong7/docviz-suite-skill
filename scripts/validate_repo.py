#!/usr/bin/env python3
"""Validate the GitHub repository and skill structure without external dependencies."""

import argparse
import json
import re
import sys
from pathlib import Path


REQUIRED_FILES = [
    "SKILL.md",
    "README.md",
    "LICENSE",
    "CHANGELOG.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    ".gitignore",
    ".gitattributes",
    ".github/workflows/validate.yml",
    ".github/PULL_REQUEST_TEMPLATE.md",
    ".github/ISSUE_TEMPLATE/bug_report.yml",
    ".github/ISSUE_TEMPLATE/feature_request.yml",
    "references/orchestration.md",
    "references/sources.json",
    "references/profiles/business-rules.md",
    "references/profiles/prd.md",
    "references/profiles/system-overview.md",
    "scripts/docviz.py",
    "scripts/upstream.py",
    "scripts/self_test.py",
    "scripts/validate_repo.py",
]


def validate(root):
    errors = []
    checked = []
    for relative in REQUIRED_FILES:
        path = root / relative
        if not path.is_file() or path.stat().st_size == 0:
            errors.append(f"缺失或空文件：{relative}")
        else:
            checked.append(relative)
    skill_path = root / "SKILL.md"
    if skill_path.is_file():
        text = skill_path.read_text(encoding="utf-8")
        match = re.match(r"^---\n(.*?)\n---\n", text, re.S)
        if not match:
            errors.append("SKILL.md 缺少有效 YAML frontmatter")
        else:
            frontmatter = match.group(1)
            keys = re.findall(r"^([A-Za-z0-9_-]+):", frontmatter, re.M)
            if set(keys) != {"name", "description"} or len(keys) != 2:
                errors.append("SKILL.md frontmatter 必须且只能包含 name 与 description")
            if not re.search(r"^name:\s*docviz-suite-skill\s*$", frontmatter, re.M):
                errors.append("SKILL.md 的 name 必须为 docviz-suite-skill")
            if not re.search(r"^description:\s*\S.+$", frontmatter, re.M):
                errors.append("SKILL.md 缺少有效 description")
        if "TODO" in text:
            errors.append("SKILL.md 仍含 TODO")
        for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", text):
            if re.match(r"^(?:https?://|#|mailto:)", target):
                continue
            if not (root / target).is_file():
                errors.append(f"SKILL.md 本地引用不存在：{target}")
    sources_path = root / "references" / "sources.json"
    if sources_path.is_file():
        try:
            sources = json.loads(sources_path.read_text(encoding="utf-8"))["sources"]
            ids = [item["id"] for item in sources]
            expected = {
                "show-me", "methodology-visualization", "archify",
                "flowchart-designer", "mindmapgenerator", "graphify",
            }
            if set(ids) != expected or len(ids) != len(set(ids)):
                errors.append("上游清单必须恰好包含六个唯一技能 ID")
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            errors.append(f"上游清单无效：{exc}")
    for name in ("docviz.py", "upstream.py", "self_test.py", "validate_repo.py"):
        path = root / "scripts" / name
        if path.is_file():
            try:
                compile(path.read_text(encoding="utf-8"), str(path), "exec")
            except SyntaxError as exc:
                errors.append(f"Python 语法错误 {name}：{exc}")
    workflow = root / ".github" / "workflows" / "validate.yml"
    if workflow.is_file():
        text = workflow.read_text(encoding="utf-8")
        for command in ("validate_repo.py", "self_test.py", "py_compile"):
            if command not in text:
                errors.append(f"GitHub Actions 缺少校验步骤：{command}")
    return checked, errors


def main():
    parser = argparse.ArgumentParser(description="docviz-suite-skill 仓库结构自检")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parent.parent))
    args = parser.parse_args()
    root = Path(args.root).expanduser().resolve()
    if not root.is_dir():
        print(json.dumps({"error": f"仓库目录不存在：{root}"}, ensure_ascii=False), file=sys.stderr)
        return 2
    checked, errors = validate(root)
    report = {"repository": str(root), "passed": not errors,
              "checked_files": len(checked), "errors": errors}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
