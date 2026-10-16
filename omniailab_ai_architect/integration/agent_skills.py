"""Agent Skills compatibility.

OmniArchitect ships as a standard Agent Skill: a root `SKILL.md` with YAML
front-matter, progressive disclosure into `references/`, and no hard
dependency on any particular vendor runtime.

This module parses and validates that contract so the skill can be checked,
installed and run standalone — including on a machine where OmniAiLab was
never configured. Nothing here reads a platform key.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

from ..paths import ROOT

NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

# Where Agent runtimes look for skills. Detected, never assumed to exist.
KNOWN_TARGETS: Dict[str, Dict[str, str]] = {
    "workbuddy": {
        "label": "WorkBuddy（用户级）",
        "path": "~/.workbuddy/skills",
        "layout": "dir-per-skill",
    },
    "codex": {
        "label": "OpenAI Codex（用户级）",
        "path": "~/.codex/skills",
        "layout": "dir-per-skill",
    },
    "cursor": {
        "label": "Cursor（用户级）",
        "path": "~/.cursor/skills-cursor",
        "layout": "dir-per-skill",
    },
    "claude": {
        "label": "Claude Code（用户级）",
        "path": "~/.claude/skills",
        "layout": "dir-per-skill",
    },
    "project-workbuddy": {
        "label": "当前项目（WorkBuddy）",
        "path": "<project>/.workbuddy/skills",
        "layout": "dir-per-skill",
    },
    "project-agent": {
        "label": "当前项目（通用 Agent Skills）",
        "path": "<project>/.agent/skills",
        "layout": "dir-per-skill",
    },
}

SKILL_ROOT = ROOT
SKILL_FILE = SKILL_ROOT / "SKILL.md"


# --------------------------------------------------------------------------
@dataclass
class SkillManifest:
    name: str
    description: str = ""
    version: str = ""
    license: str = ""
    root: str = ""
    frontmatter: Dict[str, Any] = field(default_factory=dict)
    body: str = ""
    references: List[str] = field(default_factory=list)
    soft_references: List[str] = field(default_factory=list)
    lines: int = 0
    bytes_: int = 0
    issues: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name, "description": self.description,
            "version": self.version, "license": self.license, "root": self.root,
            "frontmatter": self.frontmatter, "references": list(self.references),
            "soft_references": list(self.soft_references),
            "lines": self.lines, "bytes": self.bytes_, "issues": list(self.issues),
        }


# --------------------------------------------------------------------------
def _parse_frontmatter(text: str) -> Dict[str, Any]:
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end < 0:
        return {}
    out: Dict[str, Any] = {}
    key: Optional[str] = None
    for raw in text[3:end].splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if raw.startswith((" ", "\t")) and key:
            cur = out.get(key)
            item = raw.strip().lstrip("-").strip()
            if isinstance(cur, list):
                cur.append(item)
            continue
        if ":" not in raw:
            continue
        key, val = raw.split(":", 1)
        key, val = key.strip(), val.strip()
        if not val:
            out[key] = []
        elif val.startswith("[") and val.endswith("]"):
            out[key] = [v.strip().strip("'\"") for v in val[1:-1].split(",") if v.strip()]
        else:
            out[key] = val.strip("'\"")
    return out


def parse(path: str | Path = SKILL_FILE) -> SkillManifest:
    p = Path(path)
    if not p.exists():
        return SkillManifest(name="", root=str(p.parent), issues=[f"缺少 {p}"])
    text = p.read_text(encoding="utf-8")
    fm = _parse_frontmatter(text)
    body = text.split("\n---", 3)[-1] if text.startswith("---") else text
    refs: List[str] = []
    soft: List[str] = []
    for m in re.finditer(r"\]\(([^)]+)\)", body):
        target = m.group(1).strip()
        if target.startswith(("http://", "https://", "#", "mailto:")):
            continue
        refs.append(target)
    # Skill bodies usually point at their payload with backticks rather than
    # links ("knowledge/", `docs/WORKFLOW.md`). Collect those separately and
    # check them leniently: only paths whose first segment is a real top-level
    # directory of this skill are required to resolve. That way a documented
    # *user-supplied* path (e.g. `providers/omniailab.api.json`) is not a
    # validator failure, while a renamed `knowledge/` still is.
    for m in re.finditer(r"`([^`\n]+)`", body):
        candidate = m.group(1).strip().rstrip("/")
        if not candidate or candidate.startswith(("http", "#", "-", "$", "python",
                                                  "pip", "git", "uvx", "npx")):
            continue
        if "/" not in candidate and "." not in candidate:
            continue
        if not re.match(r"^[A-Za-z0-9_./-]+$", candidate):
            continue
        soft.append(candidate)
    return SkillManifest(
        name=str(fm.get("name") or ""),
        description=str(fm.get("description") or ""),
        version=str(fm.get("version") or ""),
        license=str(fm.get("license") or ""),
        root=str(p.parent),
        frontmatter=fm,
        body=body,
        references=sorted(set(refs)),
        soft_references=sorted(set(soft)),
        lines=len(text.splitlines()),
        bytes_=len(text.encode("utf-8")),
    )


def validate(path: str | Path = SKILL_FILE) -> List[str]:
    m = parse(path)
    issues = list(m.issues)
    if not m.name:
        issues.append("front-matter 缺少 name")
    elif not NAME_RE.match(m.name):
        issues.append(f"name={m.name!r} 不符合 ^[a-z0-9]+(-[a-z0-9]+)*$")
    if not m.description:
        issues.append("front-matter 缺少 description")
    elif len(m.description) > 1024:
        issues.append(f"description 过长（{len(m.description)} > 1024）")
    if not m.version:
        issues.append("front-matter 缺少 version")
    # progressive disclosure: the always-loaded file must stay small
    if m.lines > 400:
        issues.append(f"SKILL.md 过长（{m.lines} 行）：应把细节下沉到 references/")
    if m.bytes_ > 24000:
        issues.append(f"SKILL.md 过大（{m.bytes_} 字节）：渐进式加载会被破坏")
    for ref in m.references:
        target = (Path(m.root) / ref).resolve()
        if not target.exists():
            issues.append(f"引用不存在：{ref}")
    top = {p.name for p in Path(m.root).iterdir() if p.is_dir()}
    top |= {p.name for p in Path(m.root).iterdir() if p.is_file()}
    for ref in m.soft_references:
        first = ref.split("/")[0]
        if first not in top:
            continue            # 用户自备路径，不是本技能的资产
        if not (Path(m.root) / ref).exists():
            issues.append(f"引用不存在：{ref}")
    return issues


def references() -> List[str]:
    return parse().references


# --------------------------------------------------------------------------
def payload_files(root: str | Path = SKILL_ROOT) -> List[Path]:
    """Files a full (copy-mode) install would carry."""
    r = Path(root)
    out: List[Path] = []
    skip_dirs = {".git", "out", "__pycache__", ".pytest_cache", "third_party",
                 ".workbuddy"}
    for p in sorted(r.rglob("*")):
        if p.is_dir():
            continue
        parts = set(p.relative_to(r).parts[:-1])
        if parts & skip_dirs:
            continue
        if p.suffix in (".pyc", ".pyo"):
            continue
        out.append(p)
    return out


def digest(path: str | Path) -> str:
    h = hashlib.sha256()
    h.update(Path(path).read_bytes())
    return h.hexdigest()[:16]


def build_manifest(root: str | Path = SKILL_ROOT, with_hashes: bool = False) -> Dict[str, Any]:
    r = Path(root)
    m = parse(r / "SKILL.md")
    files = payload_files(r)
    payload = []
    for p in files:
        rec = {"path": str(p.relative_to(r)).replace("\\", "/"),
               "size": p.stat().st_size}
        if with_hashes:
            rec["sha256_16"] = digest(p)
        payload.append(rec)
    return {
        "skill": m.to_dict(),
        "issues": validate(r / "SKILL.md"),
        "root": str(r),
        "file_count": len(payload),
        "total_bytes": sum(f["size"] for f in payload),
        "files": payload[:600],
        "truncated": len(payload) > 600,
        "entrypoint": "SKILL.md",
        "python_package": "omniailab_ai_architect",
        "standalone": {
            "requires_platform_account": False,
            "requires_network": False,
            "required_python": ">=3.10",
            "hard_dependencies": [],
        },
    }


def write_manifest(target: str | Path, root: str | Path = SKILL_ROOT,
                   with_hashes: bool = True) -> str:
    t = Path(target)
    t.parent.mkdir(parents=True, exist_ok=True)
    t.write_text(json.dumps(build_manifest(root, with_hashes),
                            ensure_ascii=False, indent=2), encoding="utf-8")
    return str(t)


# --------------------------------------------------------------------------
def detect_runtimes(project_dir: str | Path | None = None) -> Dict[str, Dict[str, Any]]:
    """Report which Agent runtimes are present. Detection only — nothing installed."""
    proj = Path(project_dir) if project_dir else Path.cwd()
    out: Dict[str, Dict[str, Any]] = {}
    for key, spec in KNOWN_TARGETS.items():
        raw = spec["path"].replace("<project>", str(proj))
        p = Path(os.path.expanduser(raw))
        present = p.exists()
        installed = None
        if present:
            candidate = p / "omniailab-ai-architect"
            installed = candidate.exists()
        out[key] = {
            "label": spec["label"],
            "path": str(p),
            "present": present,
            "installed": installed,
            "layout": spec["layout"],
        }
    return out


def default_target(project_dir: str | Path | None = None) -> Optional[str]:
    """First present runtime in preference order; None means 'no runtime found'."""
    found = detect_runtimes(project_dir)
    for key in ("workbuddy", "codex", "cursor", "claude",
                "project-workbuddy", "project-agent"):
        if found.get(key, {}).get("present"):
            return str(found[key]["path"])
    return None


def compatibility_report(project_dir: str | Path | None = None) -> Dict[str, Any]:
    m = parse()
    return {
        "skill": m.name,
        "version": m.version,
        "issues": validate(),
        "references": m.references,
        "always_loaded_bytes": m.bytes_,
        "always_loaded_lines": m.lines,
        "progressive_disclosure": m.bytes_ < 24000,
        "runtimes": detect_runtimes(project_dir),
        "modes": ["standalone", "platform-connected"],
        "standalone_ok": not [i for i in validate() if "缺少" in i],
        "notes": [
            "独立模式不需要注册 OmniAiLab，也不读取任何平台密钥",
            "平台连接模式仅在检测到 SDK/配置/契约时启用",
        ],
    }


__all__ = [
    "SkillManifest", "KNOWN_TARGETS", "SKILL_FILE", "SKILL_ROOT", "NAME_RE",
    "parse", "validate", "references", "payload_files", "digest",
    "build_manifest", "write_manifest", "detect_runtimes", "default_target",
    "compatibility_report",
]
