"""Standalone-agent integration: Agent Skills contract + installer.

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

from . import agent_skills  # noqa: F401
from .agent_skills import (  # noqa: F401
    KNOWN_TARGETS,
    SKILL_FILE,
    SKILL_ROOT,
    SkillManifest,
    build_manifest,
    compatibility_report,
    default_target,
    detect_runtimes,
    parse,
    validate,
    write_manifest,
)
from .installer import (  # noqa: F401
    Installer,
    InstallReport,
    install,
    plan,
    verify,
)

__all__ = [
    "agent_skills", "parse", "validate", "build_manifest", "write_manifest",
    "detect_runtimes", "default_target", "compatibility_report",
    "SkillManifest", "KNOWN_TARGETS", "SKILL_FILE", "SKILL_ROOT",
    "Installer", "InstallReport", "install", "plan", "verify",
]
