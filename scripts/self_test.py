#!/usr/bin/env python3
"""Isolated functional tests; never touches installed upstream skills or the network."""

import argparse
import contextlib
import hashlib
import io
import json
import tempfile
import zipfile
from argparse import Namespace
from pathlib import Path

import docviz
import upstream


def expect(condition, message):
    if not condition:
        raise AssertionError(message)


def make_notes(path):
    notes = {
        "summary": "测试文档将输入转换为输出。",
        "scope": ["仅测试"],
        "core_model": ["输入经过规则形成输出"],
        "key_points": ["每个分支必须有去向"],
        "gaps": [],
        "questions": ["确认测试计划"],
        "chapter_coverage": [{"section": "规则", "coverage": "主流程"}],
    }
    path.write_text(json.dumps(notes, ensure_ascii=False), encoding="utf-8")


def make_stub_outputs(plan):
    run_dir = Path(plan["run_dir"])
    html_items = [item for item in plan["artifacts"] if item["path"].endswith(".html")]
    for item in plan["artifacts"]:
        path = run_dir / item["path"]
        if path.suffix == ".json":
            path.write_text("{}\n", encoding="utf-8")
        elif path.suffix == ".md":
            path.write_text("# 测试\n", encoding="utf-8")
        elif item["id"] == "navigation":
            links = "".join(f'<a href="{other["path"]}">{other["path"]}</a>' for other in html_items
                            if other["id"] != "navigation")
            path.write_text(f'<!doctype html><meta charset="utf-8"><title>导航</title>{links}', encoding="utf-8")
        else:
            path.write_text('<!doctype html><meta charset="utf-8"><title>测试</title><p>离线</p>', encoding="utf-8")


def expect_docviz_error(call, message):
    try:
        call()
        raise AssertionError(message)
    except docviz.DocvizError:
        pass


def expect_update_error(call, message):
    try:
        call()
        raise AssertionError(message)
    except upstream.UpdateError:
        pass


def test_docviz(root):
    workspace = root / "docviz-workspace"
    workspace.mkdir()
    source = workspace / "rules.md"
    source.write_text("# 业务规则\n## 公式与口径\n规则、流程、公式、现金流、复核、校验、抵扣。\n", encoding="utf-8")
    expect(docviz.detect_profile("PRD 产品需求 用户故事 用户场景 功能清单 交互 权限 验收标准")["selected"] == "prd",
           "PRD 自动分类失败")
    expect(docviz.detect_profile("系统架构 系统介绍 模块 服务 接口 数据流 部署 依赖 调用链")["selected"] == "system-overview",
           "系统文档自动分类失败")
    args = Namespace(workspace=str(workspace), source=str(source), profile="auto", mode="standard", output_root=None)
    with contextlib.redirect_stdout(io.StringIO()):
        docviz.command_plan(args)
    plan_path = next((workspace / "输出" / "docviz-runs").glob("*/plan.json"))
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    expect(plan["profile"] == "business-rules", "业务规则自动分类失败")
    expect(plan["status"] == "awaiting_confirmation", "计划初始状态错误")
    expect_docviz_error(
        lambda: docviz.command_confirm(Namespace(plan=str(plan_path), approve=plan["approval_code"], profile=None)),
        "未标注计划不应确认成功",
    )
    expect_docviz_error(
        lambda: docviz.command_ready(Namespace(plan=str(plan_path), artifact="understanding")),
        "未确认计划不应通过生成前检查",
    )
    notes = root / "notes.json"
    make_notes(notes)
    with contextlib.redirect_stdout(io.StringIO()):
        docviz.command_annotate(Namespace(plan=str(plan_path), notes=str(notes), profile=None))
    expect_docviz_error(
        lambda: docviz.command_confirm(Namespace(plan=str(plan_path), approve="wrong", profile=None)),
        "错误确认码不应通过",
    )
    with contextlib.redirect_stdout(io.StringIO()):
        docviz.command_confirm(Namespace(plan=str(plan_path), approve=plan["approval_code"], profile=None))
        docviz.command_ready(Namespace(plan=str(plan_path), artifact="understanding"))
    expect_docviz_error(
        lambda: docviz.command_ready(Namespace(plan=str(plan_path), artifact="not-in-plan")),
        "计划外产物不应通过生成前检查",
    )
    make_stub_outputs(plan)
    with contextlib.redirect_stdout(io.StringIO()):
        docviz.command_verify(Namespace(plan=str(plan_path)))
    report = json.loads((Path(plan["run_dir"]) / "verification.json").read_text(encoding="utf-8"))
    expect(report["passed"], "完整产物验证应通过")
    understanding = Path(plan["run_dir"]) / "01_文档理解.html"
    understanding.write_text('<!doctype html><style>@import url("https://example.com/a.css");</style>', encoding="utf-8")
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            docviz.command_verify(Namespace(plan=str(plan_path)))
        raise AssertionError("CSS 外部依赖不应验证通过")
    except SystemExit as exc:
        expect(exc.code == 1, "CSS 外部依赖应返回验证失败")
    make_stub_outputs(plan)
    source.write_text(source.read_text(encoding="utf-8") + "\n源文件漂移。\n", encoding="utf-8")
    expect_docviz_error(
        lambda: docviz.command_ready(Namespace(plan=str(plan_path), artifact="overview")),
        "确认后的源文件漂移不应通过生成前检查",
    )
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            docviz.command_verify(Namespace(plan=str(plan_path)))
        raise AssertionError("源文件漂移不应验证通过")
    except SystemExit as exc:
        expect(exc.code == 1, "源文件漂移应返回验证失败")
    media = root / "media.html"
    media.write_text('<video src="https://example.com/v.mp4"></video><object data="https://example.com/o.bin"></object>', encoding="utf-8")
    _, external, _ = docviz.inspect_html(media)
    expect(any(tag == "video" for tag, _ in external) and any(tag == "object" for tag, _ in external),
           "视频与对象外部资源应被识别")
    return [
        "三类文档自动分类", "确认前语义门槛", "确认码", "未确认生成拦截", "计划外产物拦截",
        "逐产物生成前检查", "完整产物验证", "CSS 外部依赖拦截", "视频/对象外部资源拦截", "确认后源文件漂移拦截",
    ]


def test_upstream(root):
    workspace = root / "update-workspace"
    target = workspace / ".workbuddypro" / "skills" / "demo"
    target.mkdir(parents=True)
    original_skill = "---\nname: demo\nversion: 1.0.0\n---\n# Old\n"
    (target / "SKILL.md").write_text(original_skill, encoding="utf-8")
    (target / "_meta.json").write_text('{"slug":"demo","version":"1.0.0"}\n', encoding="utf-8")
    manifest_path = workspace / "sources.json"
    manifest = {"schema_version": 1, "sources": [{
        "id": "demo", "install_dir": "demo", "kind": "skillhub", "slug": "demo", "recorded_version": "1.0.0"
    }]}
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    original_manifest = manifest_path.read_bytes()
    original_fetch, original_download = upstream.fetch_json, upstream.download
    original_find, original_installed = upstream.find_install, upstream.installed_version
    original_total_limit = upstream.MAX_TOTAL_UNCOMPRESSED_BYTES
    try:
        def forbidden_network(url):
            raise AssertionError("离线检查触发了网络")

        upstream.fetch_json = forbidden_network
        offline = upstream.check_skill(workspace, manifest["sources"][0], False)
        expect(not offline["remote_checked"] and offline["status"] == "installed", "默认离线零网络检查失败")
        upstream.fetch_json = lambda url: {"latestVersion": {"version": "1.1.0"}}

        def fake_download(url, destination, headers=None):
            with zipfile.ZipFile(destination, "w") as archive:
                archive.writestr("SKILL.md", "---\nname: demo\nversion: 1.1.0\n---\n# New\n")
                archive.writestr("_meta.json", '{"slug":"demo","version":"1.1.0"}')

        upstream.download = fake_download
        item = upstream.check_skill(workspace, manifest["sources"][0], True)
        expect(item["status"] == "update_available" and item["sync_eligible"], "更新检测失败")
        upstream.find_install = lambda workspace, name: (target, "user", False)
        user_item = upstream.check_skill(workspace, manifest["sources"][0], True)
        expect(not user_item["sync_eligible"] and not user_item["sync_supported"], "用户级技能不应允许同步")
        upstream.find_install = original_find
        for unsafe_dir in ("../demo", "/tmp/demo"):
            unsafe_source = dict(manifest["sources"][0], install_dir=unsafe_dir)
            expect_update_error(lambda: upstream.check_skill(workspace, unsafe_source, False),
                                "不安全 install_dir 不应通过")
        outside = root / "outside"
        outside.mkdir()
        link = workspace / ".workbuddypro" / "skills" / "linkdemo"
        symlink_tested = False
        try:
            link.symlink_to(outside, target_is_directory=True)
            symlink_tested = True
            link_source = {"id": "linkdemo", "install_dir": "linkdemo", "kind": "skillhub", "slug": "linkdemo"}
            expect_update_error(lambda: upstream.check_skill(workspace, link_source, False),
                                "符号链接技能目录不应通过")
        except OSError:
            pass
        report = {
            "schema_version": 1, "report_id": "test-report", "created_at": upstream.now_iso(),
            "workspace": str(workspace), "online": True, "dry_run": True,
            "manifest": str(manifest_path),
            "manifest_sha256": hashlib.sha256(original_manifest).hexdigest(),
            "approval_code": "approved-test", "complete": True, "items": [item],
        }
        report_path = workspace / "输出" / "docviz-updates" / "latest.json"
        upstream.write_json(report_path, report)
        bad_report = dict(report, report_id="../escape")
        bad_report_path = report_path.parent / "bad-report.json"
        upstream.write_json(bad_report_path, bad_report)
        expect_update_error(
            lambda: upstream.command_sync(Namespace(workspace=str(workspace), report=str(bad_report_path), manifest=None,
                                                    skill=["demo"], approve="approved-test")),
            "恶意报告 ID 不应通过",
        )
        sync_args = Namespace(workspace=str(workspace), report=str(report_path), manifest=None,
                              skill=["demo"], approve="approved-test")
        try:
            upstream.command_sync(Namespace(**{**vars(sync_args), "approve": "wrong"}))
            raise AssertionError("错误更新确认码不应同步")
        except upstream.UpdateError:
            pass
        expect(upstream.installed_version(target) == "1.0.0", "错误确认码修改了技能")
        (target / "SKILL.md").write_text(original_skill + "local drift\n", encoding="utf-8")
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                upstream.command_sync(sync_args)
            raise AssertionError("本地漂移不应同步")
        except SystemExit as exc:
            expect(exc.code == 1, "本地漂移应返回同步失败")
        expect(upstream.installed_version(target) == "1.0.0", "本地漂移测试修改了版本")
        (target / "SKILL.md").write_text(original_skill, encoding="utf-8")
        manifest_path.write_bytes(original_manifest + b"\n")
        try:
            upstream.command_sync(sync_args)
            raise AssertionError("清单漂移不应同步")
        except upstream.UpdateError:
            pass
        manifest_path.write_bytes(original_manifest)

        def fail_new_version(path):
            path = Path(path)
            if path == target and "version: 1.1.0" in (path / "SKILL.md").read_text(encoding="utf-8"):
                return "0.0.0"
            return original_installed(path)

        upstream.installed_version = fail_new_version
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                upstream.command_sync(sync_args)
            raise AssertionError("故障注入不应同步成功")
        except SystemExit as exc:
            expect(exc.code == 1, "故障注入应返回同步失败")
        upstream.installed_version = original_installed
        expect(upstream.installed_version(target) == "1.0.0", "同步失败后未回滚")
        rollback_receipt = json.loads((report_path.parent / "sync-test-report.json").read_text(encoding="utf-8"))
        rollback_result = rollback_receipt["results"][0]
        expect(rollback_result["rollback"] == "completed" and rollback_result.get("backup"), "回滚回执缺少状态或备份位置")
        with contextlib.redirect_stdout(io.StringIO()):
            upstream.command_sync(sync_args)
        expect(upstream.installed_version(target) == "1.1.0", "确认后同步失败")
        backups = list((workspace / "输出" / "docviz-backups").glob("*/demo/SKILL.md"))
        expect(len(backups) >= 2 and all("1.0.0" in p.read_text(encoding="utf-8") for p in backups), "同步前备份失败")
        unsafe = root / "unsafe.zip"
        with zipfile.ZipFile(unsafe, "w") as archive:
            archive.writestr("../escape.txt", "bad")
        try:
            upstream.validate_archive(unsafe)
            raise AssertionError("不安全 ZIP 路径不应通过")
        except upstream.UpdateError:
            pass
        total = root / "total.zip"
        with zipfile.ZipFile(total, "w") as archive:
            archive.writestr("a.txt", "1234567890")
            archive.writestr("b.txt", "1234567890")
        upstream.MAX_TOTAL_UNCOMPRESSED_BYTES = 10
        try:
            upstream.validate_archive(total)
            raise AssertionError("ZIP 总解压量超限不应通过")
        except upstream.UpdateError:
            pass
        mismatch = root / "mismatch"
        mismatch.mkdir()
        (mismatch / "SKILL.md").write_text("---\nname: demo\nversion: 9.9.9\n---\n", encoding="utf-8")
        try:
            upstream.validate_package_version(mismatch, "1.1.0")
            raise AssertionError("下载包原始版本不匹配不应通过")
        except upstream.UpdateError:
            pass
    finally:
        upstream.fetch_json, upstream.download = original_fetch, original_download
        upstream.find_install, upstream.installed_version = original_find, original_installed
        upstream.MAX_TOTAL_UNCOMPRESSED_BYTES = original_total_limit
    passed = [
        "默认离线零网络", "更新检测", "用户级拒同步", "目录名绝对路径与 .. 拦截", "恶意报告 ID 拦截",
        "更新确认码", "本地漂移拦截", "清单漂移拦截", "失败回滚与回执", "确认后同步", "完整备份",
        "ZIP 路径安全", "ZIP 总量限制", "包内原始版本核验",
    ]
    if symlink_tested:
        passed.append("符号链接目录拦截")
    return passed


def main():
    parser = argparse.ArgumentParser(description="docviz-suite-skill 隔离功能测试")
    parser.add_argument("--root", required=True, help="工作空间内用于临时测试的已存在目录")
    args = parser.parse_args()
    root = Path(args.root).expanduser().resolve()
    if not root.is_dir():
        raise SystemExit("测试根目录不存在")
    with tempfile.TemporaryDirectory(prefix="docviz-self-test-", dir=str(root)) as temp:
        root_path = Path(temp)
        passed = test_docviz(root_path) + test_upstream(root_path)
    print(json.dumps({"passed": True, "count": len(passed), "tests": passed,
                      "network_used": False, "real_upstream_modified": False}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
