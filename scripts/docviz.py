#!/usr/bin/env python3
"""Plan, confirm, and verify docviz-suite-skill runs using only the standard library."""

import argparse
import hashlib
import json
import re
import secrets
import sys
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit


__version__ = "1.0.0"


PROFILES = {
    "business-rules": [
        "业务规则", "口径", "公式", "分支", "校验", "现金流", "结算", "抵扣",
        "kpi", "租赁", "处置", "审批", "规则", "起息", "复核",
    ],
    "prd": [
        "prd", "产品需求", "用户故事", "用户场景", "功能清单", "交互", "权限",
        "验收标准", "非目标", "埋点", "原型", "需求背景", "用户价值", "页面",
    ],
    "system-overview": [
        "系统架构", "系统介绍", "模块", "服务", "接口", "数据流", "部署", "依赖",
        "调用链", "组件", "拓扑", "数据库", "架构", "微服务", "安全边界",
    ],
}


class DocvizError(Exception):
    pass


def now_iso():
    return datetime.now().astimezone().isoformat(timespec="seconds")


def read_text(path):
    data = path.read_bytes()
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise DocvizError(f"无法识别文本编码：{path}")


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_json(path):
    try:
        return json.loads(read_text(path))
    except (json.JSONDecodeError, OSError) as exc:
        raise DocvizError(f"无法读取 JSON：{path}：{exc}") from exc


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resolve_file(workspace, raw_path):
    path = Path(raw_path).expanduser()
    if not path.is_absolute():
        path = workspace / path
    path = path.resolve()
    if not path.is_file():
        raise DocvizError(f"源文件不存在：{path}")
    return path


def ensure_output_inside_workspace(workspace, output_root):
    output_root = output_root.resolve()
    try:
        output_root.relative_to(workspace.resolve())
    except ValueError as exc:
        raise DocvizError("输出目录必须位于当前工作空间内") from exc
    return output_root


def source_metadata(path):
    stat = path.stat()
    return {
        "path": str(path),
        "bytes": stat.st_size,
        "modified_at": datetime.fromtimestamp(stat.st_mtime).astimezone().isoformat(timespec="seconds"),
        "sha256": sha256(path),
    }


def detect_profile(text):
    lowered = text.lower()
    scores = {}
    hits = {}
    for profile, keywords in PROFILES.items():
        matched = {word: lowered.count(word.lower()) for word in keywords}
        hits[profile] = {word: count for word, count in matched.items() if count}
        scores[profile] = sum(matched.values())
    ranked = sorted(scores, key=scores.get, reverse=True)
    top, second = ranked[0], ranked[1]
    if scores[top] == 0:
        selected, confidence = None, "low"
    elif scores[top] >= 6 and scores[top] >= max(2, scores[second] * 2):
        selected, confidence = top, "high"
    elif scores[top] >= 3 and scores[top] > scores[second]:
        selected, confidence = top, "medium"
    else:
        selected, confidence = None, "low"
    return {
        "selected": selected,
        "confidence": confidence,
        "scores": scores,
        "keyword_hits": hits,
        "needs_user_choice": selected is None,
    }


def extract_headings(text):
    headings = []
    for line in text.splitlines():
        match = re.match(r"^(#{1,6})\s+(.+?)\s*#*\s*$", line)
        if match:
            headings.append({"level": len(match.group(1)), "title": match.group(2).strip()})
    return headings


def safe_stem(path):
    stem = re.sub(r"[^\w.\-\u4e00-\u9fff]+", "_", path.stem, flags=re.UNICODE).strip("._")
    return (stem or "document")[:60]


def artifact(plan_id, path, skill, purpose):
    return {"id": plan_id, "path": path, "skill": skill, "purpose": purpose, "required": True}


def build_artifacts(profile, mode):
    system = profile == "system-overview"
    main_stem = "03_系统主图" if system else "03_主流程"
    groups = {
        "understanding": artifact("understanding", "01_文档理解.html", "show-me", "解释文档本质、主线和关键约束"),
        "overview": artifact("overview", "02_总览信息图.html", "methodology-visualization", "一页回顾核心结构"),
        "main_html": artifact("main_html", f"{main_stem}.html", "archify", "呈现主流程或系统主关系"),
        "main_json": artifact("main_json", f"{main_stem}.json", "archify", "保留可校验、可重生成的主图源数据"),
        "details": artifact("details", "04_细节流程.html", "flowchart-designer", "展开复杂判定、异常与子流程"),
        "outline": artifact("outline", "05_全量大纲.md", "mindmapgenerator", "保留完整章节覆盖"),
        "mindmap": artifact("mindmap", "05_全量导图.html", "mindmapgenerator", "分层浏览全文"),
        "graph_json": artifact("graph_json", "06_关系图谱.graph.json", "graphify", "保留节点、边和来源"),
        "graph_html": artifact("graph_html", "06_关系图谱.html", "graphify", "搜索和筛选关系"),
        "graph_report": artifact("graph_report", "06_图谱报告.md", "graphify", "说明社区、路径与抽取方式"),
        "impact": artifact("impact", "07_影响分析.md", "graphify", "记录关键路径和变更影响面"),
        "navigation": artifact("navigation", "00_可视化导航.html", "show-me", "汇总真实成果、阅读顺序与缺口"),
    }
    quick = ["understanding", "overview", "main_html", "main_json", "navigation"]
    standard = quick[:-1] + [
        "details", "outline", "mindmap", "graph_json", "graph_html", "graph_report", "navigation",
    ]
    deep = standard[:-1] + ["impact", "navigation"]
    return [groups[key] for key in {"quick": quick, "standard": standard, "deep": deep}[mode]]


def render_plan(plan):
    understanding = plan["understanding"]

    def lines(key, empty="待补充"):
        values = understanding.get(key) or []
        if not values:
            return f"- {empty}"
        rendered = []
        for item in values:
            if isinstance(item, dict):
                rendered.append("- " + "；".join(f"{k}：{v}" for k, v in item.items()))
            else:
                rendered.append(f"- {item}")
        return "\n".join(rendered)

    detection = plan["profile_detection"]
    candidates = "、".join(
        f"{name}({score})" for name, score in sorted(detection["scores"].items(), key=lambda x: x[1], reverse=True)
    )
    artifacts = "\n".join(
        f"{index}. `{item['path']}` — {item['skill']}：{item['purpose']}"
        for index, item in enumerate(plan["artifacts"], 1)
    )
    headings = "\n".join(
        f"- {'  ' * max(0, item['level'] - 1)}{item['title']}" for item in plan["heading_outline"][:120]
    ) or "- 未检测到 Markdown 标题，需在全量理解中建立逻辑章节"
    coverage = understanding.get("chapter_coverage") or []
    coverage_text = "\n".join(
        f"- {item.get('section', '未命名')}：{item.get('coverage', item.get('status', '待复核'))}"
        if isinstance(item, dict) else f"- {item}"
        for item in coverage
    ) or "- 待助手逐章确认覆盖方式"
    summary = understanding.get("summary") or "待助手通读全文后补充；此时尚不可确认。"
    return f"""# Docviz 生成计划

- 运行 ID：`{plan['run_id']}`
- 状态：`{plan['status']}`
- 文档类型：`{plan['profile'] or '待用户选择'}`
- 类型识别置信度：`{detection['confidence']}`；候选得分：{candidates}
- 生成模式：`{plan['mode']}`
- 源文件：`{plan['source']['path']}`
- SHA-256：`{plan['source']['sha256']}`

## 一句话理解

{summary}

## 范围与非目标

{lines('scope')}

## 核心对象与运转方式

{lines('core_model')}

## 关键规则、流程或架构关系

{lines('key_points')}

## 章节覆盖

{coverage_text}

## 缺口、冲突与歧义

{lines('gaps', '未发现；仍须以用户复核为准')}

## 待用户重点确认

{lines('questions', '请确认上述理解、文档类型与产物范围')}

## 检测到的源文档结构

{headings}

## 确认后拟生成产物

{artifacts}

## 确认方式

确认码：`{plan['approval_code']}`。只有用户明确确认当前计划后，才可执行 confirm 命令并生成图表。
"""


def save_plan(plan, plan_path):
    write_json(plan_path, plan)
    (plan_path.parent / "00_生成计划.md").write_text(render_plan(plan), encoding="utf-8")
    write_json(plan_path.parent / "state.json", {
        "run_id": plan["run_id"],
        "status": plan["status"],
        "updated_at": plan["updated_at"],
        "source_sha256": plan["source"]["sha256"],
    })


def command_plan(args):
    workspace = Path(args.workspace).expanduser().resolve()
    if not workspace.is_dir():
        raise DocvizError(f"工作空间不存在：{workspace}")
    source = resolve_file(workspace, args.source)
    if source.suffix.lower() not in (".md", ".markdown", ".txt"):
        raise DocvizError("plan 脚本接受 .md/.markdown/.txt；其他格式请先提取为保留标题的 Markdown")
    if source.stat().st_size > 20 * 1024 * 1024:
        raise DocvizError("单个文本超过 20 MiB，请先按章节拆分或提取")
    if args.profile != "auto" and args.profile not in PROFILES:
        raise DocvizError(f"未知 profile：{args.profile}")
    text = read_text(source)
    detection = detect_profile(text)
    profile = detection["selected"] if args.profile == "auto" else args.profile
    if args.profile != "auto":
        detection["needs_user_choice"] = False
    output_root = Path(args.output_root) if args.output_root else workspace / "输出"
    if not output_root.is_absolute():
        output_root = workspace / output_root
    output_root = ensure_output_inside_workspace(workspace, output_root)
    run_id = "dv-" + datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + secrets.token_hex(4)
    run_dir = output_root / "docviz-runs" / f"{safe_stem(source)}-{run_id}"
    run_dir.mkdir(parents=True, exist_ok=False)
    plan = {
        "schema_version": 1,
        "run_id": run_id,
        "status": "awaiting_confirmation",
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "workspace": str(workspace),
        "run_dir": str(run_dir),
        "source": source_metadata(source),
        "profile": profile,
        "profile_detection": detection,
        "mode": args.mode,
        "heading_outline": extract_headings(text),
        "understanding": {
            "summary": "",
            "scope": [],
            "core_model": [],
            "key_points": [],
            "gaps": [],
            "questions": [],
            "chapter_coverage": [],
        },
        "artifacts": build_artifacts(profile, args.mode),
        "approval_code": secrets.token_hex(8),
        "confirmed_at": None,
    }
    plan_path = run_dir / "plan.json"
    save_plan(plan, plan_path)
    print(json.dumps({"status": plan["status"], "plan": str(plan_path), "run_dir": str(run_dir),
                      "profile": profile, "needs_semantic_annotation": True,
                      "approval_code": plan["approval_code"]}, ensure_ascii=False, indent=2))


def command_annotate(args):
    plan_path = Path(args.plan).expanduser().resolve()
    plan = load_json(plan_path)
    if plan["status"] != "awaiting_confirmation":
        raise DocvizError("只有待确认计划可以补充理解；已确认计划如需修改请重新创建")
    notes = load_json(Path(args.notes).expanduser().resolve())
    allowed = {"summary", "scope", "core_model", "key_points", "gaps", "questions", "chapter_coverage"}
    unknown = set(notes) - allowed
    if unknown:
        raise DocvizError(f"理解笔记含未知字段：{', '.join(sorted(unknown))}")
    for key, value in notes.items():
        if key == "summary" and not isinstance(value, str):
            raise DocvizError("summary 必须是字符串")
        if key != "summary" and not isinstance(value, list):
            raise DocvizError(f"{key} 必须是数组")
        plan["understanding"][key] = value
    if args.profile:
        if args.profile not in PROFILES:
            raise DocvizError(f"未知 profile：{args.profile}")
        plan["profile"] = args.profile
        plan["profile_detection"]["needs_user_choice"] = False
        plan["artifacts"] = build_artifacts(args.profile, plan["mode"])
    plan["updated_at"] = now_iso()
    save_plan(plan, plan_path)
    print(json.dumps({"status": plan["status"], "plan": str(plan_path), "annotated": True}, ensure_ascii=False, indent=2))


def assert_source_unchanged(plan):
    source = Path(plan["source"]["path"])
    if not source.is_file():
        raise DocvizError("源文件已不存在，必须重新生成计划")
    current = sha256(source)
    if current != plan["source"]["sha256"]:
        raise DocvizError("源文件 SHA-256 已变化，本计划及后续成果视为过期，必须重新生成计划")


def assert_ready(plan, artifact_id=None):
    if plan["status"] != "approved":
        raise DocvizError("计划尚未由用户明确确认，禁止生成")
    assert_source_unchanged(plan)
    if artifact_id is not None:
        matches = [item for item in plan["artifacts"] if item["id"] == artifact_id]
        if not matches:
            raise DocvizError(f"产物不在已确认计划中：{artifact_id}")
        return matches[0]
    return None


def command_ready(args):
    plan_path = Path(args.plan).expanduser().resolve()
    plan = load_json(plan_path)
    item = assert_ready(plan, args.artifact)
    print(json.dumps({
        "ready": True,
        "run_id": plan["run_id"],
        "artifact": item["id"] if item else None,
        "path": str(Path(plan["run_dir"]) / item["path"]) if item else None,
        "source_sha256": plan["source"]["sha256"],
        "checked_at": now_iso(),
    }, ensure_ascii=False, indent=2))


def command_confirm(args):
    plan_path = Path(args.plan).expanduser().resolve()
    plan = load_json(plan_path)
    if plan["status"] != "awaiting_confirmation":
        raise DocvizError(f"当前状态为 {plan['status']}，不能重复确认")
    if not secrets.compare_digest(str(plan["approval_code"]), args.approve):
        raise DocvizError("确认码不匹配")
    if plan["profile_detection"].get("needs_user_choice") and not args.profile:
        raise DocvizError("文档类型识别不确定，确认时必须用 --profile 明确选择")
    if args.profile:
        if args.profile not in PROFILES:
            raise DocvizError(f"未知 profile：{args.profile}")
        plan["profile"] = args.profile
        plan["profile_detection"]["needs_user_choice"] = False
        plan["artifacts"] = build_artifacts(args.profile, plan["mode"])
    if not plan["understanding"].get("summary", "").strip() or not plan["understanding"].get("key_points"):
        raise DocvizError("计划缺少语义理解摘要或关键点，请先 annotate 并向用户展示")
    assert_source_unchanged(plan)
    plan["status"] = "approved"
    plan["confirmed_at"] = now_iso()
    plan["updated_at"] = now_iso()
    save_plan(plan, plan_path)
    print(json.dumps({"status": "approved", "run_dir": plan["run_dir"], "confirmed_at": plan["confirmed_at"]},
                     ensure_ascii=False, indent=2))


class ReferenceParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.references = []
        self.links = []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag in ("script", "img", "iframe", "source", "video", "audio", "track", "embed") and values.get("src"):
            self.references.append((tag, values["src"]))
        if tag == "object" and values.get("data"):
            self.references.append((tag, values["data"]))
        if values.get("srcset"):
            for candidate in values["srcset"].split(","):
                self.references.append((tag + "-srcset", candidate.strip().split()[0]))
        if tag in ("link", "image", "use") and values.get("href"):
            self.references.append((tag, values["href"]))
        if values.get("poster"):
            self.references.append((tag + "-poster", values["poster"]))
        if tag == "a" and values.get("href"):
            self.links.append(values["href"])


def inspect_html(path):
    parser = ReferenceParser()
    text = read_text(path)
    parser.feed(text)
    external = [(tag, ref) for tag, ref in parser.references if re.match(r"^(?:https?:)?//", ref, re.I)]
    for pattern, label in (
        (r"@import\s+(?:url\()?\s*[\"']?((?:https?:)?//[^\s\"')]+)", "css-import"),
        (r"url\(\s*[\"']?((?:https?:)?//[^\s\"')]+)", "css-url"),
    ):
        external.extend((label, match) for match in re.findall(pattern, text, re.I))
    missing = []
    for ref in parser.links:
        if re.match(r"^(?:[a-z]+:|#|//)", ref, re.I):
            continue
        clean = unquote(urlsplit(ref).path)
        if clean and not (path.parent / clean).resolve().is_file():
            missing.append(ref)
    return parser, external, missing


def command_verify(args):
    plan_path = Path(args.plan).expanduser().resolve()
    plan = load_json(plan_path)
    errors = []
    checks = []
    if plan["status"] != "approved":
        errors.append("计划尚未确认")
    try:
        assert_source_unchanged(plan)
        checks.append("源文件 SHA-256 未变化")
    except DocvizError as exc:
        errors.append(str(exc))
    run_dir = Path(plan["run_dir"])
    html_paths = []
    nav_path = run_dir / "00_可视化导航.html"
    for item in plan["artifacts"]:
        path = run_dir / item["path"]
        if not path.is_file() or path.stat().st_size == 0:
            errors.append(f"缺失或空文件：{item['path']}")
            continue
        if path.suffix.lower() == ".json":
            try:
                load_json(path)
            except DocvizError as exc:
                errors.append(str(exc))
        if path.suffix.lower() == ".html":
            html_paths.append(path)
    linked_targets = set()
    for path in html_paths:
        try:
            parser, external, missing = inspect_html(path)
            if external:
                errors.append(f"{path.name} 含外部资源引用：{external}")
            if missing:
                errors.append(f"{path.name} 含失效本地链接：{missing}")
            if path == nav_path:
                linked_targets = {
                    (path.parent / unquote(urlsplit(ref).path)).resolve()
                    for ref in parser.links
                    if not re.match(r"^(?:[a-z]+:|#|//)", ref, re.I)
                }
        except (OSError, UnicodeError, DocvizError) as exc:
            errors.append(f"无法检查 HTML {path.name}：{exc}")
    if nav_path.is_file():
        for path in html_paths:
            if path != nav_path and path.resolve() not in linked_targets:
                errors.append(f"导航页未链接：{path.name}")
        if not errors:
            checks.append("计划产物存在，JSON 可解析，HTML 无外部资源且导航链接完整")
    report = {
        "run_id": plan["run_id"],
        "verified_at": now_iso(),
        "passed": not errors,
        "checks": checks,
        "errors": errors,
        "scope": "结构、文件、JSON、外部资源和本地链接检查；不替代语义与视觉复核",
    }
    write_json(run_dir / "verification.json", report)
    report_md = ["# Docviz 验证报告", "", f"- 结果：{'通过' if not errors else '未通过'}",
                 f"- 时间：{report['verified_at']}", f"- 范围：{report['scope']}", "", "## 已通过", ""]
    report_md += [f"- {item}" for item in checks] or ["- 无"]
    report_md += ["", "## 问题", ""] + [f"- {item}" for item in errors]
    (run_dir / "验证报告.md").write_text("\n".join(report_md) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if errors:
        raise SystemExit(1)


def command_status(args):
    plan = load_json(Path(args.plan).expanduser().resolve())
    print(json.dumps({
        "run_id": plan["run_id"], "status": plan["status"], "profile": plan["profile"],
        "mode": plan["mode"], "source": plan["source"], "artifacts": plan["artifacts"],
    }, ensure_ascii=False, indent=2))


def build_parser():
    parser = argparse.ArgumentParser(description="docviz-suite-skill 运行计划、确认与验证")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)
    plan = sub.add_parser("plan", help="创建待确认计划，不生成可视化")
    plan.add_argument("--workspace", default=str(Path.cwd()))
    plan.add_argument("--source", required=True)
    plan.add_argument("--profile", default="auto", choices=["auto"] + list(PROFILES))
    plan.add_argument("--mode", default="standard", choices=["quick", "standard", "deep"])
    plan.add_argument("--output-root")
    plan.set_defaults(func=command_plan)
    annotate = sub.add_parser("annotate", help="将助手的全文语义理解写入待确认计划")
    annotate.add_argument("--plan", required=True)
    annotate.add_argument("--notes", required=True, help="包含白名单理解字段的 JSON 文件")
    annotate.add_argument("--profile", choices=list(PROFILES))
    annotate.set_defaults(func=command_annotate)
    confirm = sub.add_parser("confirm", help="在用户明确确认后解锁生成")
    confirm.add_argument("--plan", required=True)
    confirm.add_argument("--approve", required=True)
    confirm.add_argument("--profile", choices=list(PROFILES))
    confirm.set_defaults(func=command_confirm)
    ready = sub.add_parser("assert-ready", help="每次生成前重新检查确认状态、源文件哈希和产物范围")
    ready.add_argument("--plan", required=True)
    ready.add_argument("--artifact", help="计划中的产物 ID；传入后同时返回其授权输出路径")
    ready.set_defaults(func=command_ready)
    verify = sub.add_parser("verify", help="验证已确认运行的产物")
    verify.add_argument("--plan", required=True)
    verify.set_defaults(func=command_verify)
    status = sub.add_parser("status", help="读取运行状态")
    status.add_argument("--plan", required=True)
    status.set_defaults(func=command_status)
    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    try:
        args.func(args)
    except DocvizError as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
