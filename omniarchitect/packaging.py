"""分发白名单 —— 什么才算"这个技能的正式安装包"。

为什么要有白名单
----------------
原来的 `copy` 安装器用的是**黑名单**（排除 `out/`、`.git/`、`__pycache__/`）。
黑名单的毛病是：新长出来的目录默认**在包里**。于是 `installer/manifest.json`
登记了 `projects/demo-120/concept-render/` 里的 PPTX、PNG 和运行记录 ——
它们不是能力，是某次演示留下的残渣，却进了正式分发清单。

现在反过来：**先声明什么该发，再复制**。不在白名单里的东西，无论长什么样，
都不进包。判定不看体积、不看扩展名，只看身份。

白名单（`DIST_DIRS` / `DIST_ROOT_FILES`）
----------------------------------------
技能定义、代码、知识库、风格库、Schema、Skill 说明、配置模板、许可证、安装器。
**不含**：`projects/`（项目数据）、`omniarchitect/tests/`（开发测试）、
`scripts/`（开发脚本）、`out/`、任何缓存与运行目录。

审计（`audit()` / `audit_tree()`）
----------------------------------
八项，全部对着"最终要发出去的那一堆文件"查，而不是对着 git 暂存区查：

1. 包总大小；2. 单文件大小（1 MB 硬上限）；3. 禁止分发的扩展名；
4. 是否混入项目/测试/缓存目录；5. manifest 与包内容是否一致；
6. 非文档文本里是否写死本机绝对路径；7. 是否像凭据；8. 顶层目录分布。

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import fnmatch
import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from . import workspace

# --------------------------------------------------------------------------
# 白名单
# --------------------------------------------------------------------------
#: 顶层文件（精确匹配，全部是运行或合规需要的）
DIST_ROOT_FILES = {
    ".gitignore",
    "AGENTS.md",
    "CHANGELOG.md",
    "LICENSE",
    "README.md",
    "README_EN.md",
    "SKILL.md",
    "THIRD_PARTY_NOTICES.md",
    "VERSION",
    "mcp.json.example",
    "openai.yaml",
    "pyproject.toml",
    "requirements.txt",
}

#: 顶层目录（整目录进包，再剔除下面的例外）
DIST_DIRS = {
    "LICENSES",
    "adapters",
    "cases",
    "compatibility",
    "docs",
    "examples",
    "installer",
    "knowledge",
    "omniarchitect",
    "providers",
    "schemas",
    "skills",
    "workflows",
}

#: 目录内例外：开发用，不进最终用户安装包
DIST_EXCLUDE_PREFIXES = (
    "omniarchitect/tests/",
)

#: 目录内例外（通配）：历史验收报告留在开发仓库做审计链，不进最终用户安装包
DIST_EXCLUDE_GLOBS = (
    "docs/ACCEPTANCE_*.md",
)

#: 任意层级都跳过的目录名
DIST_SKIP_DIR_NAMES = {
    ".git", ".pytest_cache", ".workbuddy", "__pycache__", "node_modules",
    "out", "build", "dist", ".venv", "venv", ".mypy_cache", ".ruff_cache",
    "concept-render", "renders", "_backup",
}

#: 禁止出现在包里的扩展名（生成物 / 工程文件 / 二进制）
FORBIDDEN_SUFFIXES = {
    # CAD 与三维
    ".dxf", ".dwg", ".dwf", ".skp", ".skb", ".obj", ".mtl", ".fbx", ".glb",
    ".gltf", ".blend", ".blend1", ".ifc", ".3dm", ".rvt", ".pln",
    # 效果图与影音
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".tif", ".tiff",
    ".psd", ".ai", ".eps", ".svgz", ".mp4", ".mov", ".avi", ".mkv", ".webm",
    ".mp3", ".wav", ".m4a", ".aac", ".flac",
    # 交付文档与压缩包
    ".pptx", ".ppt", ".docx", ".doc", ".xlsx", ".xls", ".pdf", ".odt",
    ".zip", ".rar", ".7z", ".tar", ".gz", ".tgz", ".bz2", ".xz",
    # 运行残渣
    ".pyc", ".pyo", ".log", ".tmp", ".bak", ".swp", ".sqlite", ".db",
    # 字体与安装包
    ".ttf", ".otf", ".woff", ".woff2", ".exe", ".dll", ".msi", ".dmg", ".iso",
}

#: 单个文件硬上限（与 `scripts/check_assets.py` 同一口径，只收紧不放松）
MAX_FILE_BYTES = 1 * 1024 * 1024

#: 正式安装包总量预算。超了说明又混进不该发的东西，不是"再宽一点"能解决的。
MAX_TOTAL_BYTES = 6 * 1024 * 1024

#: 会被当成"文档"的路径前缀 —— 文档里出现示例路径是正常的，只提示不阻断
DOC_PREFIXES = ("docs/", "examples/", "skills/", "cases/", "compatibility/")
DOC_FILES = {"README.md", "README_EN.md", "AGENTS.md", "SKILL.md",
             "CHANGELOG.md", "THIRD_PARTY_NOTICES.md", "LICENSE"}

TEXT_SUFFIXES = {".md", ".py", ".json", ".yaml", ".yml", ".txt", ".toml",
                 ".cmd", ".bat", ".ps1", ".sh", ".example"}

#: 配置/数据文件里出现盘符路径 = 换台机器就跑不通，直接算违规
CONFIG_SUFFIXES = {".json", ".yaml", ".yml", ".toml", ".example", ".cmd",
                   ".bat", ".ps1", ".sh", ".ini", ".cfg"}

#: **本机特有**路径才算违规：用户目录、本仓库的绝对位置。
#: 注意不能把 `C:\Windows\Fonts\msyh.ttc`、`C:\Program Files\Blender Foundation`
#: 这类**平台默认查找路径**也算进来 —— 那是功能代码，不是泄漏。
_MACHINE_PATH = [
    re.compile(r"[A-Za-z]:[\\/]+Users[\\/]+[^\\/\s\"']+", re.I),
    re.compile(r"/Users/[^/\s\"']+/"),
    re.compile(r"/home/[^/\s\"']+/"),
]
_ANY_DRIVE_PATH = re.compile(r"(?<![A-Za-z0-9])[A-Za-z]:[\\/]")

_SECRET_PATTERNS = [
    ("private-key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("openai-key", re.compile(r"\bsk-[A-Za-z0-9]{20,}")),
    ("aws-key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("bearer", re.compile(r"\bBearer\s+[A-Za-z0-9\-\._~\+\/]{20,}")),
    ("assigned-secret", re.compile(
        r"(?i)\b(?:api[_-]?key|secret|access[_-]?token|password|passwd)\b"
        r"\s*[:=]\s*[\"']([A-Za-z0-9_\-\.]{16,})[\"']")),
]
_SECRET_PLACEHOLDERS = ("FILL_ME", "YOUR_", "your-", "<", "${", "***",
                        "example", "EXAMPLE", "placeholder", "xxxx")


#: 审计器自己的源码里有正则字面量（`/Users/...`），不能自己举报自己。
AUDIT_SELF_EXEMPT = {"omniarchitect/packaging.py"}


# --------------------------------------------------------------------------
def _posix(rel: Path | str) -> str:
    p = str(rel).replace("\\", "/")
    while p.startswith("./"):
        p = p[2:]
    return p


def is_distributable(rel: str | Path) -> bool:
    """这条相对路径该不该进正式安装包。"""
    p = _posix(rel)
    if not p or p.endswith("/"):
        return False
    parts = p.split("/")
    if any(part in DIST_SKIP_DIR_NAMES for part in parts):
        return False
    if p.startswith(DIST_EXCLUDE_PREFIXES):
        return False
    if any(fnmatch.fnmatch(p, pat) for pat in DIST_EXCLUDE_GLOBS):
        return False
    if len(parts) == 1:
        return p in DIST_ROOT_FILES
    return parts[0] in DIST_DIRS


def distribution_files(root: str | Path | None = None) -> List[Path]:
    """按白名单列出要分发的文件（不含被例外排除的）。"""
    r = Path(root) if root else workspace.SKILL_ROOT
    out: List[Path] = []
    for p in sorted(r.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(r)
        if is_distributable(rel):
            out.append(p)
    return out


# --------------------------------------------------------------------------
def _is_doc(rel: str) -> bool:
    return rel in DOC_FILES or rel.startswith(DOC_PREFIXES)


def _scan_text(path: Path, rel: str) -> Dict[str, List[str]]:
    """扫一台文本文件里的本机路径与凭据特征。

    分两类返回：
    * `machine_path` —— 用户目录 / 本仓库绝对位置，任何文件里出现都算泄漏；
    * `config_path` —— 配置与数据文件里的盘符路径，换机器就跑不通。
    """
    hits = {"machine_path": [], "config_path": [], "secret": []}
    suffix = path.suffix.lower()
    if suffix not in TEXT_SUFFIXES or rel in AUDIT_SELF_EXEMPT:
        return hits
    try:
        if path.stat().st_size > 2 * 1024 * 1024:
            return hits
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return hits

    own_root = _posix(workspace.SKILL_ROOT)
    for i, line in enumerate(text.splitlines(), 1):
        if own_root and own_root in line.replace("\\\\", "/").replace("\\", "/"):
            hits["machine_path"].append(f"{rel}:{i}（写入本仓库绝对路径）")
            continue
        if any(pat.search(line) for pat in _MACHINE_PATH):
            hits["machine_path"].append(f"{rel}:{i}（用户目录绝对路径）")
            continue
        if suffix in CONFIG_SUFFIXES and _ANY_DRIVE_PATH.search(line):
            hits["config_path"].append(f"{rel}:{i}（配置里的盘符路径）")
        for label, pat in _SECRET_PATTERNS:
            m = pat.search(line)
            if not m:
                continue
            sample = m.group(0)
            if any(tok in sample for tok in _SECRET_PLACEHOLDERS):
                continue
            hits["secret"].append(f"{rel}:{i}（{label}）")
    return hits


def _by_top(files: Iterable[Path], root: Path) -> Dict[str, Dict[str, int]]:
    out: Dict[str, Dict[str, int]] = {}
    for f in files:
        rel = _posix(f.relative_to(root))
        top = rel.split("/")[0] if "/" in rel else "(根目录)"
        slot = out.setdefault(top, {"files": 0, "bytes": 0})
        slot["files"] += 1
        slot["bytes"] += f.stat().st_size
    return out


def _stray_artefacts(root: Path) -> List[str]:
    """技能目录里"不该在这儿"的生成物（不参与分发，但是膨胀的来源）。"""
    out: List[str] = []
    runtime_dirs = {"projects", "outputs", "cache", "archive", "out", "scenarios"}
    for p in sorted(root.rglob("*")):
        rel = _posix(p.relative_to(root))
        parts = rel.split("/")
        if any(x in DIST_SKIP_DIR_NAMES for x in parts) or parts[0] == ".git":
            continue
        if p.is_dir():
            if rel in runtime_dirs:
                out.append(f"{rel}/")
            continue
        if p.suffix.lower() in FORBIDDEN_SUFFIXES:
            out.append(rel)
    return out


# --------------------------------------------------------------------------
def audit(root: str | Path | None = None) -> Dict[str, Any]:
    """对着**将要发出去的文件**做八项检查。`ok` 为假时安装器应当停下。"""
    r = Path(root) if root else workspace.SKILL_ROOT
    files = distribution_files(r)
    violations: List[Dict[str, str]] = []
    warnings: List[str] = []

    def bad(rule: str, detail: str) -> None:
        violations.append({"rule": rule, "detail": detail})

    total = 0
    largest = ("", 0)
    payload: List[Dict[str, Any]] = []
    for f in files:
        rel = _posix(f.relative_to(r))
        try:
            size = f.stat().st_size
        except OSError as exc:
            bad("unreadable", f"{rel}：{exc}")
            continue
        total += size
        if size > largest[1]:
            largest = (rel, size)
        payload.append({"path": rel, "size": size})

        suffix = f.suffix.lower()
        if suffix in FORBIDDEN_SUFFIXES:
            bad("forbidden-type", f"{rel}（{suffix} 属于生成物/工程文件，不进包）")
        if size >= MAX_FILE_BYTES:
            bad("oversize-file", f"{rel}（{size / 1024:.0f} KB ≥ 1 MB 上限）")
        # 白名单自检：不白名单的东西理论上进不来，跑一遍证明它真的进不来
        if not is_distributable(rel):
            bad("not-whitelisted", rel)

        hits = _scan_text(f, rel)
        for h in hits["secret"]:
            bad("secret", h)
        for h in hits["config_path"]:
            bad("config-absolute-path", h)
        for h in hits["machine_path"]:
            # 文档里写示例路径是正常的（手册要举例子）；代码与配置里写死本机路径
            # 会让别人装完直接跑不通，属于违规。
            if _is_doc(rel):
                warnings.append(f"{h}（文档示例路径，已记录不阻断）")
            else:
                bad("absolute-path", h)

    if total > MAX_TOTAL_BYTES:
        bad("oversize-package",
            f"正式包 {total / 1024 / 1024:.2f} MB > 预算 "
            f"{MAX_TOTAL_BYTES / 1024 / 1024:.0f} MB，说明混进了不该发的东西")

    # 项目 / 测试 / 缓存目录污染
    for rec in payload:
        rel = rec["path"]
        for prefix in ("projects/", "out/", "tests/", "cache/", "archive/"):
            if rel.startswith(prefix):
                bad("contamination", f"{rel}（{prefix} 是运行数据，不进包）")

    # 技能目录里躺着生成物 —— 虽然进不了包（白名单挡着），但它就是膨胀的起点。
    # 这一条把"仓库又胖了"变成一次可见的失败，而不是等体积长到 1 GB 才发现。
    strays = _stray_artefacts(r)
    for stray in strays:
        bad("stray-artefact",
            f"{stray}（技能目录里不该有生成物，请移到工作区 outputs/ 或 archive/）")

    # manifest 与包内容必须完全一致：多一个少一个都算坏
    manifest_state = _check_manifest(r, {p["path"] for p in payload}, bad, warnings)

    return {
        "root": str(r),
        "ok": not violations,
        "file_count": len(payload),
        "total_bytes": total,
        "total_mb": round(total / 1024 / 1024, 2),
        "largest": largest,
        "budget_bytes": MAX_TOTAL_BYTES,
        "max_file_bytes": MAX_FILE_BYTES,
        "by_top": _by_top(files, r),
        "manifest": manifest_state,
        "strays": strays[:20],
        "violations": violations,
        "warnings": warnings,
        "files": payload,
    }


def _check_manifest(root: Path, payload: set, bad, warnings: List[str]) -> Dict[str, Any]:
    mf = root / "installer" / "manifest.json"
    if not mf.exists():
        warnings.append("没有 installer/manifest.json，无法核对清单与包内容是否一致")
        return {"present": False, "matches": False}
    try:
        data = json.loads(mf.read_text(encoding="utf-8"))
    except Exception as exc:                      # noqa: BLE001
        bad("manifest-corrupt", f"installer/manifest.json 解析失败：{exc}")
        return {"present": True, "matches": False}
    listed = {_posix(rec.get("path", "")) for rec in data.get("files", [])}
    listed.discard("")
    missing = sorted(listed - payload)          # 清单里有、包里没有 → 悬空条目
    extra = sorted(payload - listed)            # 包里有、清单没登记 → 漏登记
    if missing:
        bad("manifest-stale",
            f"manifest 登记了不存在的文件 {len(missing)} 个：{missing[:5]}")
    if extra:
        bad("manifest-incomplete",
            f"包里有 {len(extra)} 个文件未登记进 manifest：{extra[:5]}")
    if data.get("root"):
        raw = str(data["root"])
        if _ANY_DRIVE_PATH.search(raw) or any(p.search(raw) for p in _MACHINE_PATH):
            bad("absolute-path",
                f"installer/manifest.json 的 root 写了本机绝对路径：{raw}")
    return {
        "present": True,
        "matches": not missing and not extra,
        "listed": len(listed),
        "missing": missing[:10],
        "extra": extra[:10],
        "version": data.get("generated_from"),
    }


# --------------------------------------------------------------------------
def audit_tree(target: str | Path) -> Dict[str, Any]:
    """审计一个**已存在的目录**（装好的副本、别人给的压缩包解开后的样子）。

    和 `audit()` 的区别：这里不知道白名单，只查"这种东西根本不该出现"。
    """
    d = Path(target)
    violations: List[Dict[str, str]] = []
    total = 0
    count = 0
    if not d.exists():
        return {"target": str(d), "ok": False, "file_count": 0, "total_bytes": 0,
                "violations": [{"rule": "missing", "detail": f"目录不存在：{d}"}],
                "warnings": []}
    for p in sorted(d.rglob("*")):
        if not p.is_file():
            continue
        rel = _posix(p.relative_to(d))
        parts = rel.split("/")
        if any(x in DIST_SKIP_DIR_NAMES for x in parts):
            continue
        count += 1
        try:
            size = p.stat().st_size
        except OSError:
            continue
        total += size
        if p.suffix.lower() in FORBIDDEN_SUFFIXES:
            violations.append({"rule": "forbidden-type", "detail": f"{rel}（{p.suffix}）"})
        if size >= MAX_FILE_BYTES:
            violations.append({"rule": "oversize-file",
                               "detail": f"{rel}（{size / 1024:.0f} KB）"})
    if count == 0:
        violations.append({"rule": "empty", "detail": f"目录里没有任何文件：{d}"})
    return {
        "target": str(d),
        "ok": not violations,
        "file_count": count,
        "total_bytes": total,
        "total_mb": round(total / 1024 / 1024, 2),
        "violations": violations,
    }


__all__ = [
    "DIST_ROOT_FILES", "DIST_DIRS", "DIST_EXCLUDE_PREFIXES", "DIST_SKIP_DIR_NAMES",
    "FORBIDDEN_SUFFIXES", "MAX_FILE_BYTES", "MAX_TOTAL_BYTES",
    "is_distributable", "distribution_files", "audit", "audit_tree",
]
