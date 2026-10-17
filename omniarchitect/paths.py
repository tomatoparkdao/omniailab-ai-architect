"""Paths and small filesystem helpers for the project.

Everything is resolved relative to this package so the project can be moved or
cloned without editing constants.

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
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

# --------------------------------------------------------------------------
# 官方地址（唯一来源）。front-matter 的「开源仓库 / 操作手册」、CLI 的 manual 命令、
# 生成器的报告头，全部读这里，避免同一串地址在多个文件里各写一份。
REPO_URL = "https://github.com/tomatoparkdao/omniailab-ai-architect"
MANUAL_CN_URL = "https://zcn03zgas1zl.feishu.cn/wiki/K1IWwPuBDiQXufkS76Yc3EMPnTd"
MANUAL_NOTION_URL = "https://tomatopark.notion.site/Skill-3fba28d2e37880ac9be5dd199c99677d"


def ensure_output_dir(path: str | Path | None, default: str = "out") -> Path:
    p = Path(path) if path else (ROOT / default)
    p.mkdir(parents=True, exist_ok=True)
    return p


def project_version() -> str:
    """The project version, read from `VERSION` (single source of truth).

    Used wherever a generated document has to stamp a version, so the header of
    every artifact can never disagree with the repository.
    """
    try:
        first = (ROOT / "VERSION").read_text(encoding="utf-8").splitlines()
        return first[0].strip() if first and first[0].strip() else "0.0.0"
    except Exception:
        return "0.0.0"


def relpath(p: str | Path) -> str:
    """Path as stored in artifacts: relative to the project root when possible."""
    try:
        return str(Path(p).resolve().relative_to(ROOT))
    except Exception:
        return str(p)
