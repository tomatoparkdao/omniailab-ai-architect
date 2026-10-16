"""Presentation content model and brand styling.

A deck is data before it is a file. `Deck` -> `Slide` is deliberately free of
any library type so the same deck can be rendered to PPTX, to a print-ready
HTML sheet, or to plain Markdown for review.

Brand defaults are OmniArchitect's own: neutral paper, one accent, generous
margins. Nothing here imitates another studio's template, and no third-party
case material is bundled as sample content.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

SLIDE_KINDS = (
    "cover",            # 封面
    "agenda",           # 汇报结构
    "section",          # 章节页
    "summary",          # 项目摘要 / 任务书
    "concept",          # 概念主张
    "keywords",         # 概念关键词
    "moodboard",        # 意向板（图 + 关键词）
    "plan",             # 平面方案
    "plan_compare",     # 平面方案比选
    "analysis",         # 分析图 / 数据
    "perspective",      # 空间表现
    "materials",        # 材料与色彩
    "lighting",         # 照明逻辑
    "decisions",        # 设计决策
    "budget",           # 预算与概算
    "coordination",     # 机电与专业协调
    "drawings",         # 施工图 / 技术交底
    "open_items",       # 待确认事项
    "next_steps",       # 下一步
    "disclaimer",       # 免责与边界
)

# Deck flavour per workflow stage.
DECK_KINDS: Dict[str, Dict[str, Any]] = {
    "concept": {
        "stage": "S2", "title": "概念设计提案",
        "slides": ["cover", "agenda", "summary", "concept", "keywords", "moodboard",
                   "plan", "lighting", "materials", "budget", "open_items", "disclaimer"],
    },
    "plan-comparison": {
        "stage": "S3", "title": "平面方案比选汇报",
        "slides": ["cover", "agenda", "summary", "plan", "plan_compare", "analysis",
                   "budget", "decisions", "open_items", "disclaimer"],
    },
    "preliminary": {
        "stage": "S4", "title": "初步设计汇报",
        "slides": ["cover", "agenda", "summary", "concept", "plan", "materials",
                   "lighting", "coordination", "budget", "open_items", "disclaimer"],
    },
    "visual": {
        "stage": "S5", "title": "视觉表现汇报",
        "slides": ["cover", "agenda", "summary", "perspective", "materials",
                   "lighting", "decisions", "open_items", "disclaimer"],
    },
    "final": {
        "stage": "S6", "title": "设计定稿确认",
        "slides": ["cover", "agenda", "summary", "concept", "plan", "materials",
                   "lighting", "coordination", "budget", "decisions", "open_items",
                   "next_steps", "disclaimer"],
    },
    "materials-lighting": {
        "stage": "S4", "title": "材料与照明专项汇报",
        "slides": ["cover", "summary", "materials", "lighting", "budget",
                   "decisions", "disclaimer"],
    },
    "technical-briefing": {
        "stage": "S7", "title": "施工图技术交底",
        "slides": ["cover", "agenda", "summary", "drawings", "coordination",
                   "decisions", "open_items", "disclaimer"],
    },
    "delivery": {
        "stage": "S8", "title": "设计交付与物料清单",
        "slides": ["cover", "agenda", "summary", "materials", "budget", "drawings",
                   "open_items", "next_steps", "disclaimer"],
    },
    "full": {
        "stage": "S2", "title": "全过程设计汇报",
        "slides": ["cover", "agenda", "summary", "concept", "keywords", "moodboard",
                   "plan", "plan_compare", "analysis", "materials", "lighting",
                   "coordination", "perspective", "drawings", "budget", "decisions",
                   "open_items", "next_steps", "disclaimer"],
    },
}


# --------------------------------------------------------------------------
@dataclass
class Brand:
    """Style knobs. Overridable per project so a firm can use its own look."""

    name: str = "OmniArchitect"
    tagline: str = "AI Chief Designer · 建筑与室内设计"
    platform: str = "OmniAiLab"
    ink: str = "#1C1C1E"
    paper: str = "#FAFAF8"
    muted: str = "#6E6E73"
    accent: str = "#2F6F4F"
    accent_soft: str = "#E4EEE8"
    rule: str = "#D8D8D4"
    font_cjk: str = "微软雅黑"
    font_latin: str = "Segoe UI"
    logo: str = ""
    footer_note: str = ""

    def to_dict(self) -> Dict[str, str]:
        return {k: str(v) for k, v in self.__dict__.items()}


DEFAULT_BRAND = Brand()


# --------------------------------------------------------------------------
@dataclass
class Slide:
    kind: str
    title: str = ""
    subtitle: str = ""
    kicker: str = ""
    bullets: List[str] = field(default_factory=list)
    columns: List[Dict[str, Any]] = field(default_factory=list)
    table_header: List[str] = field(default_factory=list)
    table: List[List[str]] = field(default_factory=list)
    image: str = ""
    notes: str = ""
    attribution: str = ""

    def __post_init__(self) -> None:
        if self.kind not in SLIDE_KINDS:
            raise ValueError(f"未知版式 {self.kind!r}；允许：{', '.join(SLIDE_KINDS)}")

    @property
    def is_empty(self) -> bool:
        return not (self.title or self.bullets or self.table or self.image or self.columns)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "kind": self.kind, "title": self.title, "subtitle": self.subtitle,
            "kicker": self.kicker, "bullets": list(self.bullets),
            "columns": [dict(c) for c in self.columns],
            "table_header": list(self.table_header),
            "table": [list(r) for r in self.table],
            "image": self.image, "notes": self.notes,
            "attribution": self.attribution,
        }


@dataclass
class Deck:
    title: str
    subtitle: str = ""
    kind: str = "concept"
    stage: str = ""
    project_id: str = ""
    revision: int = 0
    slides: List[Slide] = field(default_factory=list)
    brand: Brand = field(default_factory=Brand)
    generated_at: str = field(
        default_factory=lambda: time.strftime("%Y-%m-%d %H:%M:%S")
    )
    warnings: List[str] = field(default_factory=list)
    provenance: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title, "subtitle": self.subtitle, "kind": self.kind,
            "stage": self.stage, "project_id": self.project_id,
            "revision": self.revision, "generated_at": self.generated_at,
            "brand": self.brand.to_dict(),
            "slide_count": len(self.slides),
            "slides": [s.to_dict() for s in self.slides],
            "warnings": list(self.warnings),
            "provenance": list(self.provenance),
        }

    # ------------------------------------------------------------------
    def validate(self) -> List[str]:
        issues: List[str] = []
        if len(self.slides) < 4:
            issues.append(f"页数过少（{len(self.slides)}），不足以构成提案")
        if not self.slides or self.slides[0].kind != "cover":
            issues.append("缺少封面")
        if not any(s.kind == "disclaimer" for s in self.slides):
            issues.append("缺少免责与边界页（必须声明专业校核范围）")
        for i, s in enumerate(self.slides):
            if s.is_empty:
                issues.append(f"第 {i+1} 页内容为空（{s.kind}）")
            if s.table and not s.table_header:
                issues.append(f"第 {i+1} 页有表格但缺表头")
            if s.table_header and s.table:
                w = len(s.table_header)
                bad = [r for r in s.table if len(r) != w]
                if bad:
                    issues.append(f"第 {i+1} 页表格列数与表头不一致")
        if not any(s.kind in ("plan", "plan_compare") for s in self.slides) and \
                self.kind in ("concept", "plan-comparison", "preliminary", "final", "full"):
            issues.append("提案缺少平面内容页")
        return issues

    def summary(self) -> Dict[str, Any]:
        return {
            "title": self.title, "kind": self.kind, "stage": self.stage,
            "slides": len(self.slides),
            "kinds": [s.kind for s in self.slides],
            "issues": self.validate(),
        }


def new_deck(kind: str, project: Any, brand: Optional[Brand] = None,
             title: str = "", subtitle: str = "") -> Deck:
    meta = DECK_KINDS.get(kind)
    if meta is None:
        raise ValueError(f"未知汇报类型 {kind!r}；允许：{', '.join(DECK_KINDS)}")
    return Deck(
        title=title or f"{getattr(project, 'name', '') or getattr(project, 'project_id', '')}"
                       f" · {meta['title']}",
        subtitle=subtitle,
        kind=kind,
        stage=str(meta["stage"]),
        project_id=str(getattr(project, "project_id", "")),
        revision=int(getattr(project, "revision", 0) or 0),
        brand=brand or Brand(),
    )


def slide_order(kind: str) -> List[str]:
    return list(DECK_KINDS.get(kind, {}).get("slides", []))  # type: ignore[arg-type]


__all__ = [
    "SLIDE_KINDS", "DECK_KINDS", "Brand", "DEFAULT_BRAND", "Slide", "Deck",
    "new_deck", "slide_order",
]
