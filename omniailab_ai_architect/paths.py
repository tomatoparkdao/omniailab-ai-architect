"""Paths and small filesystem helpers for the project.

Everything is resolved relative to this package so the project can be moved or
cloned without editing constants.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # project root (package sits inside it)
SCHEMAS = ROOT / "schemas"
SKILLS = ROOT / "skills"
WORKFLOWS = ROOT / "workflows"
ADAPTER_SPECS = ROOT / "adapters" / "specs"
DOCS = ROOT / "docs"
EXAMPLES = ROOT / "examples"
PROJECTS = ROOT / "projects"
KNOWLEDGE = ROOT / "knowledge"
CASES = ROOT / "cases"
TEMPLATES = ROOT / "templates"
INSTALLER = ROOT / "installer"
COMPATIBILITY = ROOT / "compatibility"


def ensure_output_dir(path: str | Path | None, default: str = "out") -> Path:
    p = Path(path) if path else (ROOT / default)
    p.mkdir(parents=True, exist_ok=True)
    return p


def relpath(p: str | Path) -> str:
    """Path as stored in artifacts: relative to the project root when possible."""
    try:
        return str(Path(p).resolve().relative_to(ROOT))
    except Exception:
        return str(p)
