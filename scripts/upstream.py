#!/usr/bin/env python3
"""Read-only upstream checks and explicitly approved project-scope synchronization."""

import argparse
import hashlib
import json
import os
import re
import secrets
import shutil
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from datetime import datetime
from pathlib import Path, PurePosixPath


__version__ = "1.0.0"

SKILL_HOME = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST = SKILL_HOME / "references" / "sources.json"
MAX_DOWNLOAD_BYTES = 100 * 1024 * 1024
MAX_RESPONSE_BYTES = 2 * 1024 * 1024
MAX_ARCHIVE_ENTRIES = 5000
MAX_TOTAL_UNCOMPRESSED_BYTES = 300 * 1024 * 1024
MAX_COMPRESSION_RATIO = 200


class UpdateError(Exception):
    def __init__(self, message, **details):
        super().__init__(message)
        self.details = details


def validate_identifier(value, label):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}", value):
        raise UpdateError(f"{label} 必须是安全的单段标识符：{value!r}")
    return value


def validate_source(source):
    validate_identifier(source.get("id"), "技能 ID")
    validate_identifier(source.get("install_dir"), "技能安装目录")
    if source.get("kind") == "skillhub":
        validate_identifier(source.get("slug"), "SkillHub slug")
    elif source.get("kind") == "github":
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", str(source.get("repo", ""))):
            raise UpdateError("GitHub repo 格式不安全")
        subpath = PurePosixPath(str(source.get("subpath", "")))
        if subpath.is_absolute() or not subpath.parts or ".." in subpath.parts:
            raise UpdateError("GitHub subpath 不安全")
    else:
        raise UpdateError(f"不支持的来源类型：{source.get('kind')}")


def ensure_within(path, root, label):
    resolved = path.resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError as exc:
        raise UpdateError(f"{label} 逃逸出允许目录：{resolved}") from exc
    return resolved


def project_skill_path(workspace, install_dir):
    validate_identifier(install_dir, "技能安装目录")
    skills_root = ensure_within(workspace / ".workbuddypro" / "skills", workspace, "技能根目录")
    raw = skills_root / install_dir
    if raw.is_symlink():
        raise UpdateError(f"技能目录不允许是符号链接：{raw}")
    return ensure_within(raw, skills_root, "技能目录")


def now_iso():
    return datetime.now().astimezone().isoformat(timespec="seconds")


def read_text(path):
    data = path.read_bytes()
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise UpdateError(f"无法识别文本编码：{path}")


def load_json(path):
    try:
        return json.loads(read_text(path))
    except (OSError, json.JSONDecodeError) as exc:
        raise UpdateError(f"无法读取 JSON：{path}：{exc}") from exc


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_limited(response, limit, label):
    data = response.read(limit + 1)
    if len(data) > limit:
        raise UpdateError(f"{label} 超过 {limit} 字节安全上限")
    return data


def github_headers():
    headers = {"User-Agent": "docviz-suite-skill/1.0"}
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        headers["Authorization"] = f"token {token}"
    return headers


def fetch_json(url, headers=None):
    request = urllib.request.Request(url, headers=headers or {"User-Agent": "docviz-suite-skill/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(read_limited(response, MAX_RESPONSE_BYTES, "JSON 响应").decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise UpdateError(f"请求失败：{url}：{exc}") from exc


def download(url, destination, headers=None):
    request = urllib.request.Request(url, headers=headers or {"User-Agent": "docviz-suite-skill/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=60) as response, destination.open("wb") as target:
            total = 0
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > MAX_DOWNLOAD_BYTES:
                    raise UpdateError("下载包超过 100 MiB 安全上限")
                target.write(chunk)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as exc:
        raise UpdateError(f"下载失败：{url}：{exc}") from exc


def find_install(workspace, install_dir):
    project = workspace / ".workbuddypro" / "skills" / install_dir
    if project.is_dir():
        return project, "project", True
    for base in (Path.home() / ".workbuddypro" / "skills", Path.home() / ".workbuddy" / "skills"):
        candidate = base / install_dir
        if candidate.is_dir():
            return candidate, "user", False
    return project, "missing", False


def installed_version(path):
    meta_path = path / "_meta.json"
    if meta_path.is_file():
        try:
            meta = load_json(meta_path)
            if meta.get("version"):
                return str(meta["version"])
        except UpdateError:
            pass
    skill_path = path / "SKILL.md"
    if not skill_path.is_file():
        return None
    text = read_text(skill_path)
    match = re.search(r"^version:\s*[\"']?([^\s\"']+)", text, re.M)
    if match:
        return match.group(1)
    match = re.search(r"^\s+version:\s*[\"']?([^\s\"']+)", text, re.M)
    return match.group(1) if match else None


def local_signature(path):
    digest = hashlib.sha256()
    for name in ("SKILL.md", "_meta.json"):
        item = path / name
        digest.update(name.encode("utf-8"))
        if item.is_file():
            digest.update(item.read_bytes())
        else:
            digest.update(b"<missing>")
    return digest.hexdigest()


def numeric_version(value):
    if not value or not re.match(r"^v?\d+(?:\.\d+)*$", str(value)):
        return None
    return tuple(int(part) for part in str(value).lstrip("v").split("."))


def compare_versions(local, remote):
    left, right = numeric_version(local), numeric_version(remote)
    if left is None or right is None:
        return "up_to_date" if local == remote else "version_differs"
    width = max(len(left), len(right))
    left += (0,) * (width - len(left))
    right += (0,) * (width - len(right))
    if right > left:
        return "update_available"
    if right < left:
        return "local_ahead"
    return "up_to_date"


def source_by_id(manifest):
    return {item["id"]: item for item in manifest["sources"]}


def check_skill(workspace, source, online):
    validate_source(source)
    target, scope, sync_supported = find_install(workspace, source["install_dir"])
    if scope == "project":
        target = project_skill_path(workspace, source["install_dir"])
    exists = (target / "SKILL.md").is_file()
    local = installed_version(target) if exists else None
    result = {
        "id": source["id"],
        "kind": source["kind"],
        "role": source.get("role", ""),
        "path": str(target),
        "scope": scope,
        "installed": exists,
        "installed_version": local,
        "recorded_version": source.get("recorded_version"),
        "local_signature": local_signature(target) if exists else None,
        "sync_supported": sync_supported and exists,
        "remote_checked": False,
        "remote_version": None,
        "remote_reference": None,
        "status": "installed" if exists else "missing",
        "sync_eligible": False,
        "error": None,
    }
    if not online or not exists:
        return result
    try:
        if source["kind"] == "skillhub":
            url = "https://lightmake.site/api/v1/skills/" + urllib.parse.quote(source["slug"])
            data = fetch_json(url)
            remote = str(data.get("latestVersion", {}).get("version") or data.get("skill", {}).get("tags", {}).get("latest") or "")
            if not remote:
                raise UpdateError("SkillHub 响应没有 latestVersion.version")
            result["remote_version"] = remote
            result["remote_reference"] = remote
            result["status"] = compare_versions(local, remote)
        elif source["kind"] == "github":
            repo = source["repo"]
            branch = source.get("branch", "main")
            commit = fetch_json(f"https://api.github.com/repos/{repo}/commits/{urllib.parse.quote(branch)}", github_headers())
            sha = commit.get("sha")
            if not sha:
                raise UpdateError("GitHub 响应没有提交 SHA")
            raw_url = f"https://raw.githubusercontent.com/{repo}/{sha}/{source['subpath']}/SKILL.md"
            request = urllib.request.Request(raw_url, headers=github_headers())
            try:
                with urllib.request.urlopen(request, timeout=30) as response:
                    remote_text = read_limited(response, MAX_RESPONSE_BYTES, "上游 SKILL.md").decode("utf-8")
            except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, UnicodeDecodeError) as exc:
                raise UpdateError(f"读取上游 SKILL.md 失败：{exc}") from exc
            match = re.search(r"^version:\s*[\"']?([^\s\"']+)", remote_text, re.M)
            remote = match.group(1) if match else local
            result["remote_version"] = remote
            result["remote_reference"] = sha
            if sha != source.get("baseline_commit"):
                result["status"] = "update_available"
                result["reason"] = "上游提交已变化"
            else:
                result["status"] = compare_versions(local, remote)
        else:
            raise UpdateError(f"不支持的来源类型：{source['kind']}")
        result["remote_checked"] = True
        result["sync_eligible"] = result["status"] == "update_available" and result["sync_supported"]
    except UpdateError as exc:
        result["status"] = "check_failed"
        result["error"] = str(exc)
    return result


def default_report_path(workspace):
    return workspace / "输出" / "docviz-updates" / "latest.json"


def command_check(args):
    workspace = Path(args.workspace).expanduser().resolve()
    if not workspace.is_dir():
        raise UpdateError(f"工作空间不存在：{workspace}")
    manifest = load_json(Path(args.manifest).expanduser().resolve())
    items = [check_skill(workspace, source, args.online) for source in manifest["sources"]]
    report = {
        "schema_version": 1,
        "report_id": "up-" + datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + secrets.token_hex(4),
        "created_at": now_iso(),
        "workspace": str(workspace),
        "online": args.online,
        "dry_run": True,
        "manifest": str(Path(args.manifest).expanduser().resolve()),
        "manifest_sha256": hashlib.sha256(Path(args.manifest).expanduser().resolve().read_bytes()).hexdigest(),
        "approval_code": secrets.token_hex(8) if args.online else None,
        "complete": all(item["status"] != "check_failed" for item in items),
        "items": items,
    }
    report_path = Path(args.report).expanduser() if args.report else default_report_path(workspace)
    if not report_path.is_absolute():
        report_path = workspace / report_path
    report_path = report_path.resolve()
    try:
        report_path.relative_to(workspace)
    except ValueError as exc:
        raise UpdateError("更新报告必须写在工作空间内") from exc
    write_json(report_path, report)
    print(json.dumps({"report": str(report_path), "online": args.online, "dry_run": True,
                      "complete": report["complete"], "approval_code": report["approval_code"],
                      "items": items}, ensure_ascii=False, indent=2))


def validate_archive(archive_path):
    with zipfile.ZipFile(archive_path) as archive:
        entries = archive.infolist()
        if len(entries) > MAX_ARCHIVE_ENTRIES:
            raise UpdateError(f"压缩包条目超过 {MAX_ARCHIVE_ENTRIES} 个安全上限")
        total_size = sum(info.file_size for info in entries)
        if total_size > MAX_TOTAL_UNCOMPRESSED_BYTES:
            raise UpdateError("压缩包总解压量超过 300 MiB 安全上限")
        for info in entries:
            name = info.filename.replace("\\", "/")
            pure = PurePosixPath(name)
            if pure.is_absolute() or ".." in pure.parts or (pure.parts and re.match(r"^[A-Za-z]:$", pure.parts[0])):
                raise UpdateError(f"压缩包含不安全路径：{name}")
            if ((info.external_attr >> 16) & 0o170000) == 0o120000:
                raise UpdateError(f"压缩包不允许符号链接：{name}")
            if info.file_size > MAX_DOWNLOAD_BYTES:
                raise UpdateError(f"压缩包内文件过大：{name}")
            if info.file_size > 1024 * 1024 and info.file_size / max(info.compress_size, 1) > MAX_COMPRESSION_RATIO:
                raise UpdateError(f"压缩包内文件压缩比异常：{name}")
        archive.extractall(archive_path.parent / "archive")


def validate_package_version(candidate, expected):
    declared = []
    meta_path = candidate / "_meta.json"
    if meta_path.is_file():
        meta_version = load_json(meta_path).get("version")
        if meta_version:
            declared.append(str(meta_version))
    text = read_text(candidate / "SKILL.md").lstrip()
    parts = text.split("---", 2)
    frontmatter = parts[1] if text.startswith("---") and len(parts) >= 3 else ""
    match = re.search(r"^version:\s*[\"']?([^\s\"']+)", frontmatter, re.M)
    if match:
        declared.append(match.group(1))
    if not declared:
        raise UpdateError("下载包没有可独立核验的原始版本声明")
    if any(version != str(expected) for version in declared):
        raise UpdateError(f"下载包原始版本 {declared} 与查新版本 {expected} 不一致")


def prepare_download(item, source, temp_dir):
    archive_path = temp_dir / "download.zip"
    if source["kind"] == "skillhub":
        query = urllib.parse.urlencode({"slug": source["slug"], "version": item["remote_version"]})
        url = "https://lightmake.site/api/v1/download?" + query
    else:
        if not re.fullmatch(r"[0-9a-fA-F]{40}", str(item["remote_reference"])):
            raise UpdateError("GitHub 同步必须使用 40 位固定提交 SHA")
        url = f"https://codeload.github.com/{source['repo']}/zip/{item['remote_reference']}"
    if not item.get("remote_version"):
        raise UpdateError("查新报告缺少上游版本")
    download(url, archive_path, github_headers() if source["kind"] == "github" else None)
    if not zipfile.is_zipfile(archive_path):
        raise UpdateError("下载内容不是有效 ZIP")
    validate_archive(archive_path)
    archive_root = temp_dir / "archive"
    if source["kind"] == "skillhub":
        candidate = archive_root
    else:
        matches = [p for p in archive_root.iterdir() if p.is_dir()]
        if len(matches) != 1:
            raise UpdateError("GitHub 压缩包根目录结构不符合预期")
        candidate = matches[0] / source["subpath"]
    if not (candidate / "SKILL.md").is_file():
        raise UpdateError(f"下载包缺少 {source.get('subpath', '')}/SKILL.md")
    validate_package_version(candidate, item["remote_version"])
    staged = temp_dir / "new_install"
    shutil.copytree(candidate, staged)
    meta_path = staged / "_meta.json"
    meta = load_json(meta_path) if meta_path.is_file() else {}
    meta["version"] = item["remote_version"]
    if source["kind"] == "skillhub":
        meta["slug"] = source["slug"]
    else:
        meta["source"] = f"https://github.com/{source['repo']}"
        meta["upstream_commit"] = item["remote_reference"]
    write_json(meta_path, meta)
    return staged


def synchronize_one(workspace, item, source, temp_dir):
    validate_source(source)
    target = project_skill_path(workspace, source["install_dir"])
    if not item.get("sync_eligible"):
        raise UpdateError("该技能当前不符合同步条件（需为项目级、已安装且检测到 update_available）", rollback="not_needed")
    if local_signature(target) != item.get("local_signature"):
        raise UpdateError("检查后本地 SKILL.md 或 _meta.json 已变化，请重新查新", rollback="not_needed")
    staged = prepare_download(item, source, temp_dir)
    backup_root = workspace / "输出" / "docviz-backups" / (
        datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + secrets.token_hex(4)
    )
    backup_root = ensure_within(backup_root, workspace, "备份目录")
    backup = ensure_within(backup_root / source["install_dir"], backup_root, "技能备份目录")
    backup.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(target, backup)
    if local_signature(backup) != item.get("local_signature") or not (backup / "SKILL.md").is_file():
        raise UpdateError("备份校验失败，未修改现有技能", backup=str(backup), rollback="not_needed")
    old = temp_dir / "old_install"
    try:
        target.rename(old)
    except OSError as exc:
        raise UpdateError(f"无法进入替换阶段：{exc}", backup=str(backup), rollback="not_needed") from exc
    try:
        staged.rename(target)
        if not (target / "SKILL.md").is_file() or installed_version(target) != item["remote_version"]:
            raise UpdateError("同步后的 SKILL.md 或版本验证失败")
    except Exception as exc:
        rollback_error = None
        try:
            if target.exists():
                shutil.move(str(target), str(temp_dir / "failed_install"))
            old.rename(target)
        except OSError as rollback_exc:
            rollback_error = str(rollback_exc)
        details = {"backup": str(backup), "rollback": "failed" if rollback_error else "completed"}
        if rollback_error:
            details["rollback_error"] = rollback_error
        raise UpdateError(f"同步失败：{exc}", **details) from exc
    return {
        "id": source["id"], "status": "synchronized", "path": str(target),
        "version": item["remote_version"], "reference": item["remote_reference"],
        "backup": str(backup), "rollback": "not_needed",
    }


def command_sync(args):
    workspace = Path(args.workspace).expanduser().resolve()
    report_path = Path(args.report).expanduser().resolve()
    report = load_json(report_path)
    validate_identifier(report.get("report_id"), "报告 ID")
    if not report.get("online"):
        raise UpdateError("离线报告不能用于同步")
    if not report.get("approval_code") or not secrets.compare_digest(str(report.get("approval_code", "")), args.approve):
        raise UpdateError("更新确认码不匹配")
    if not report.get("workspace") or Path(report["workspace"]).resolve() != workspace:
        raise UpdateError("报告与当前工作空间不匹配")
    try:
        report_path.relative_to(workspace)
    except ValueError as exc:
        raise UpdateError("同步报告必须位于当前工作空间内") from exc
    manifest_path = Path(args.manifest).expanduser().resolve() if args.manifest else Path(report["manifest"])
    try:
        manifest_path.relative_to(workspace)
    except ValueError as exc:
        raise UpdateError("同步使用的上游清单必须位于当前工作空间内") from exc
    manifest = load_json(manifest_path)
    if hashlib.sha256(manifest_path.read_bytes()).hexdigest() != report.get("manifest_sha256"):
        raise UpdateError("上游清单在查新后已变化，请重新查新")
    sources = source_by_id(manifest)
    items = {item["id"]: item for item in report["items"]}
    results = []
    with tempfile.TemporaryDirectory(prefix="docviz-sync-", dir=str(report_path.parent)) as temp:
        temp_dir = Path(temp)
        for index, skill_id in enumerate(args.skill):
            try:
                validate_identifier(skill_id, "技能 ID")
            except UpdateError as exc:
                results.append({"id": str(skill_id), "status": "failed", "error": str(exc),
                                "backup": None, "rollback": "not_needed"})
                continue
            if skill_id not in sources or skill_id not in items:
                results.append({"id": skill_id, "status": "failed", "error": "技能不在清单或报告中",
                                "backup": None, "rollback": "not_needed"})
                continue
            item_temp = temp_dir / f"{index}-{skill_id}"
            item_temp.mkdir()
            try:
                validate_source(sources[skill_id])
                results.append(synchronize_one(workspace, items[skill_id], sources[skill_id], item_temp))
                sources[skill_id]["recorded_version"] = items[skill_id]["remote_version"]
                if sources[skill_id]["kind"] == "github":
                    sources[skill_id]["baseline_commit"] = items[skill_id]["remote_reference"]
            except (UpdateError, OSError, zipfile.BadZipFile) as exc:
                failure = {"id": skill_id, "status": "failed", "error": str(exc),
                           "backup": None, "rollback": "not_needed"}
                if isinstance(exc, UpdateError):
                    failure.update(exc.details)
                results.append(failure)
    manifest_error = None
    if any(item["status"] == "synchronized" for item in results):
        try:
            write_json(manifest_path, manifest)
        except OSError as exc:
            manifest_error = str(exc)
    receipt = {
        "schema_version": 1,
        "created_at": now_iso(),
        "report_id": report["report_id"],
        "workspace": str(workspace),
        "results": results,
        "manifest_error": manifest_error,
        "succeeded": all(item["status"] == "synchronized" for item in results) and manifest_error is None,
    }
    receipt_path = ensure_within(report_path.parent / f"sync-{report['report_id']}.json",
                                 report_path.parent, "同步回执")
    write_json(receipt_path, receipt)
    print(json.dumps({"receipt": str(receipt_path), **receipt}, ensure_ascii=False, indent=2))
    if not receipt["succeeded"]:
        raise SystemExit(1)


def build_parser():
    parser = argparse.ArgumentParser(description="docviz-suite-skill 上游技能查新与确认后同步")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("check", help="只读检查；联网需显式 --online")
    check.add_argument("--workspace", default=str(Path.cwd()))
    check.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    check.add_argument("--online", action="store_true")
    check.add_argument("--report")
    check.set_defaults(func=command_check)
    sync = sub.add_parser("sync", help="按查新报告同步用户明确选择的技能")
    sync.add_argument("--workspace", default=str(Path.cwd()))
    sync.add_argument("--report", required=True)
    sync.add_argument("--manifest")
    sync.add_argument("--skill", required=True, action="append", help="技能 ID；可重复传入")
    sync.add_argument("--approve", required=True)
    sync.set_defaults(func=command_sync)
    return parser


def main():
    args = build_parser().parse_args()
    try:
        args.func(args)
    except UpdateError as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
