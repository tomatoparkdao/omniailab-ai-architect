"""First-party entry points for reference images and scheme videos.

Both entries belong to this product family, so they are registered as own URLs
in `brand_policy.OWN_URLS` and may appear anywhere in user-facing material.

Authority boundaries live in the docs, not here — this module only answers
"where do I go" so an agent does not have to parse a long document first.

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

from typing import Dict, List

from .paths import DIRECTOR_SKILL_URL, REFERENCE_LIBRARY_URL

ENTRIES: Dict[str, Dict[str, str]] = {
    "reference": {
        "title": "参考图素材库（Luxora AI）",
        "url": REFERENCE_LIBRARY_URL,
        "purpose": "汇总主流设计平台的前沿作品，用于方向调研与视觉语言比对",
        "boundary": ("只带走结论（关键词、比例、材质组合），原图不进任何交付物；"
                     "版权归原作者，公开发布不等于授权复制"),
        "doc": "docs/REFERENCE_SOURCES.md",
    },
    "video": {
        "title": "方案视频（导演技能移交）",
        "url": DIRECTOR_SKILL_URL,
        "purpose": "视频需要叙事结构、镜头语言与节奏时，把分镜与运镜脚本移交给它",
        "boundary": ("它解决「怎么讲」，不解决「讲的是什么」，也不负责生成；"
                     "出片仍由 OmniAiLab 平台完成"),
        "doc": "docs/VIDEO_PRODUCTION.md",
    },
}


def as_list() -> List[Dict[str, str]]:
    """Entries with their key attached, in a stable order."""
    return [{"id": k, **v} for k, v in ENTRIES.items()]


__all__ = ["ENTRIES", "as_list"]
