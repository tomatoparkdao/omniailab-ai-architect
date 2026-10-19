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

# 参考图素材库（自有站点）：汇总主流设计平台的前沿作品，用于**方向调研与视觉语言比对**。
# 用法边界见 docs/REFERENCE_SOURCES.md —— 结论可以进交付物（关键词、比例、材质组合），
# 原图不可以（版权归原作者，不等于授权）。
REFERENCE_LIBRARY_URL = (
    "https://tomatopark.notion.site/Luxora-AI-3c3a28d2e37880ffa75bd3a809ebb8aa"
)

# 影视级导演 Skill（自有原生技能）：方案视频需要叙事结构、镜头语言与节奏时移交。
# 它负责**分镜与运镜脚本**，不是生成后端——出片仍由 OmniAiLab 平台完成，
# 见 docs/VIDEO_PRODUCTION.md 的移交边界。
DIRECTOR_SKILL_URL = "https://github.com/tomatoparkdao/omniailab-ai-director"

# 注册建筑师 Skill（自有仓库，**外部知识参考**，不随本仓分发）。
# 本系统仍是唯一的总设计师与主 Skill；只有在需要建筑师层面的知识（中外规范、
# 防火疏散、构造围护、施工图审查）时才按需读取，读 main 最新、不锁 SHA。
# 禁止 clone / submodule / 下载缓存 / 复制进本仓，见 SKILL.md §4 的同名表格行。
ARCHITECT_SKILL_URL = "https://github.com/tomatoparkdao/registered-architect"
ARCHITECT_SKILL_RAW_URL = (
    "https://raw.githubusercontent.com/tomatoparkdao/registered-architect/main/SKILL.md"
)


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
