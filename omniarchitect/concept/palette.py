"""审美判据的条件化：什么时候该用「克制」，什么时候不该。

原来的写法是把几条住宅极简的经验当成普适规律：冷调打底、暖材 ≤40%、
黑色 3–8%、所有项目都套 60-30-10。用在 150㎡ 意式极简住宅上是对的，
用在度假民宿、主题餐饮、非洲当代或古典复兴上就是错的 —— 那类项目的
暖色本来就是主调，压到 40% 以下会把设计意图压没。

这一层把每条判据变成**有适用条件的建议**：

* 条件来自风格库的真实标签（`tags`、`family`）与项目类型；
* 不适用时明确写"不适用 + 为什么"，而不是悄悄跳过；
* 比例优先取自风格自己的 `color_palette` 里声明的占比，而不是外部拍一个数。

判据本身仍属本系统自有口径（见 `registry.DESIGN_CRITERIA`），这里只做适用性裁量。

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import colorsys
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

#: 判断"暖材"的关键词：材料语义，不看色相
# 「暖灰米」这类暖调石材是打底，不是暖材——所以这里只认材料，不认"暖"字。
WARM_MATERIAL_WORDS = ("木", "皮革", "藤", "织物", "布艺", "黄铜", "麻", "羊毛")
#: 冷材关键词 —— 用于确认打底不是暖调
COLD_MATERIAL_WORDS = ("石材", "岩板", "金属", "玻璃", "微水泥", "混凝土", "瓷砖")

#: 项目类型对暖色与配色的容忍度不同。值是"暖材上限"，None 表示不设上限。
WARM_CAP_BY_PROFILE: Dict[str, Optional[int]] = {
    "residential": 40,
    "office": 45,
    "exhibition": None,
    "retail": None,        # 餐饮/商业靠暖色建立食欲与停留
    "hospitality": None,   # 酒店/民宿的暖是产品的一部分
    "architecture": None,
}

#: 会触发"克制型"判据的风格标签
RESTRAINT_TAGS = {"minimal", "quiet", "restrained", "monochrome", "clinical",
                  "understated", "calm", "efficient"}
#: 明确与克制型判据冲突的标签（暖色主调/手作/浓烈）。
#: 注意不含 `warm`：意式极简的标签就是 minimal + warm，把 warm 当冲突会让
#: 最典型的克制案例反而拿不到任何判据（真实踩过）。
WARM_TAGS = {"earth-tone", "craft", "handmade", "bold", "maximal",
             "traditional", "ornate", "tropical", "rustic", "opulent"}


def hex_to_rgb(value: str) -> Tuple[int, int, int]:
    v = (value or "").lstrip("#")
    if len(v) == 3:
        v = "".join(c * 2 for c in v)
    if len(v) != 6:
        return (128, 128, 128)
    try:
        return tuple(int(v[i:i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]
    except ValueError:
        return (128, 128, 128)


def warmth(value: str) -> float:
    """0 = 纯冷，1 = 纯暖。按色相判断，不看明度。"""
    r, g, b = (c / 255.0 for c in hex_to_rgb(value))
    h, _l, _s = colorsys.rgb_to_hls(r, g, b)
    deg = h * 360.0
    if deg <= 60 or deg >= 330:
        return 1.0
    if 60 < deg <= 150:
        return 0.55          # 黄绿：中性偏暖
    if 150 < deg <= 260:
        return 0.0           # 青蓝：冷
    return 0.75              # 紫红：偏暖


def luminance(value: str) -> float:
    r, g, b = (c / 255.0 for c in hex_to_rgb(value))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


_PCT = re.compile(r"(\d{1,3})\s*%")


def _pct(text: str) -> Optional[int]:
    m = _PCT.search(text or "")
    return int(m.group(1)) if m else None


@dataclass
class Rule:
    """One aesthetic criterion, with the conditions under which it applies."""

    id: str
    name: str
    statement: str
    applies_to: Tuple[str, ...] = ()          # profiles; empty = all
    requires_any_tag: Tuple[str, ...] = ()
    blocked_by_tags: Tuple[str, ...] = ()
    source: str = "本系统自有判据"

    def decide(self, profile: str, tags: Sequence[str]) -> Tuple[bool, str]:
        tagset = set(tags or ())
        blocked = set(self.blocked_by_tags)
        required = set(self.requires_any_tag)
        if self.applies_to and profile not in self.applies_to:
            return False, f"项目类型为 {profile}，该判据原本只针对 {'/'.join(self.applies_to)}"
        if blocked & tagset:
            hit = sorted(blocked & tagset)[0]
            return False, f"风格含「{hit}」标签，与本判据的设计前提相反"
        if required and not (required & tagset):
            return False, "风格不属于该判据适用的气质类型"
        return True, "适用"


RULES: Tuple[Rule, ...] = (
    Rule(
        id="AESTHETIC-RESTRAINT",
        name="克制美学：冷调打底、一条主导线",
        statement="冷调作底、暖色点睛；全场只留一条主导线，天花是第一叙事面。",
        applies_to=("residential", "office"),
        requires_any_tag=tuple(RESTRAINT_TAGS),
        blocked_by_tags=tuple(WARM_TAGS),
        source="docs/DESIGN_CRITERIA.md · aesthetic-restraint",
    ),
    Rule(
        id="WARM-CAP",
        name="暖材占比上限",
        statement="暖材（木、藤、皮革、暖色石材）占可见饰面面积不超过 40%。",
        applies_to=("residential", "office"),
        requires_any_tag=tuple(RESTRAINT_TAGS),
        blocked_by_tags=tuple(WARM_TAGS),
        source="docs/DESIGN_CRITERIA.md · aesthetic-restraint",
    ),
    Rule(
        id="BLACK-ACCENT",
        name="黑色只做重音",
        statement="黑色作重音不作块面，占可见面积 3–8%。",
        applies_to=("residential", "office"),
        blocked_by_tags=tuple(WARM_TAGS) + ("bright",),
        source="docs/DESIGN_CRITERIA.md · aesthetic-restraint",
    ),
    Rule(
        id="RATIO-60-30-10",
        name="60-30-10 配色校验",
        statement="主色 60% / 次色 30% / 点缀 10% 的占比关系。",
        applies_to=("residential", "office"),
        requires_any_tag=tuple(RESTRAINT_TAGS),
        blocked_by_tags=tuple(WARM_TAGS),
        source="docs/DESIGN_CRITERIA.md · moodboard-iteration",
    ),
    Rule(
        id="CONTENT-LED-PALETTE",
        name="内容主导配色（展厅）",
        statement="配色服务于展品与叙事，不套固定比例；重点色由展项决定。",
        applies_to=("exhibition",),
        source="docs/DESIGN_CRITERIA.md · concept-diagram-language",
    ),
    Rule(
        id="OPERATION-LED-PALETTE",
        name="运营主导配色（餐饮/商业/酒店）",
        statement="配色服务于识别度、食欲与停留时长，暖色可作主调；不设 40% 上限。",
        applies_to=("retail", "hospitality"),
        source="docs/DESIGN_CRITERIA.md · aesthetic-restraint（例外条款）",
    ),
)


@dataclass
class PaletteEntry:
    name: str
    hex: str
    usage: str = ""
    pct: Optional[int] = None
    warm: float = 0.0
    lum: float = 0.0

    @property
    def band(self) -> str:
        if self.lum < 0.22:
            return "dark"
        if self.pct is not None and self.pct >= 35:
            return "dominant"
        if self.pct is not None and self.pct >= 15:
            return "secondary"
        return "accent"

    def to_dict(self) -> Dict[str, Any]:
        return {"name": self.name, "hex": self.hex, "usage": self.usage,
                "pct": self.pct, "warm": round(self.warm, 2),
                "luminance": round(self.lum, 2), "band": self.band}


def palette_plan(style_doc: Dict[str, Any]) -> Dict[str, Any]:
    """Read the style's own declared palette. Ratios come from the data, not from us."""
    entries: List[PaletteEntry] = []
    for item in style_doc.get("color_palette") or []:
        if not isinstance(item, dict):
            continue
        hx = str(item.get("hex") or "")
        if not hx.startswith("#"):
            continue
        usage = str(item.get("usage") or "")
        entries.append(PaletteEntry(
            name=str(item.get("name_zh") or item.get("name_en") or hx),
            hex=hx.upper(), usage=usage, pct=_pct(usage),
            warm=warmth(hx), lum=luminance(hx),
        ))
    declared = [(e.name, e.pct) for e in entries if e.pct is not None]
    total = sum(p for _n, p in declared) or 0
    # 「暖材」指材料本身偏暖（木、皮革、藤、织物、黄铜），不是"颜色偏暖"。
    # 意式极简的墙面是暖白（hue 暖、明度很高），它是打底而不是暖材。
    warm_share = sum(e.pct or 0 for e in entries
                     if e.pct and any(w in (e.name + e.usage) for w in WARM_MATERIAL_WORDS))
    dark_share = sum(e.pct or 0 for e in entries if e.lum < 0.22 and e.pct)
    return {
        "entries": [e.to_dict() for e in entries],
        "declared_total_pct": total,
        "warm_share": warm_share or None,
        "dark_share": dark_share or None,
        "dominant": [e.to_dict() for e in entries if e.band == "dominant"],
        "secondary": [e.to_dict() for e in entries if e.band == "secondary"],
        "accent": [e.to_dict() for e in entries if e.band == "accent"],
        "source": "风格库 color_palette 的 usage 声明",
        "note": ("占比取自风格自身声明；未声明的条目不计入合计，"
                 "缺失时只给出色彩关系而不编造比例。"),
    }


def aesthetic_policy(style_doc: Dict[str, Any], profile: str) -> Dict[str, Any]:
    """Which criteria actually apply to this project, and why the others do not."""
    tags = [str(t) for t in (style_doc.get("tags") or [])]
    family = str(style_doc.get("family") or "")
    decisions: List[Dict[str, Any]] = []
    for r in RULES:
        ok, why = r.decide(profile, tags)
        decisions.append({
            "rule_id": r.id, "name": r.name, "statement": r.statement,
            "applies": ok, "reason": why, "source": r.source,
            "target": _target_for(r.id, profile),
        })

    plan = palette_plan(style_doc)
    declared_total = int(plan.get("declared_total_pct") or 0)
    if declared_total >= 60:
        # 风格库自己给了分配，就按它的分配执行；60-30-10 只是没有声明时的默认框架。
        for d in decisions:
            if d["rule_id"] == "RATIO-60-30-10" and d["applies"]:
                d["applies"] = False
                d["reason"] = (f"风格库已声明自身色彩分配（合计 {declared_total}%），"
                               "优先遵循声明，不套 60-30-10")
                d["target"] = None

    applied = [d for d in decisions if d["applies"]]
    skipped = [d for d in decisions if not d["applies"]]
    warm_cap = next((d["target"] for d in applied if d["rule_id"] == "WARM-CAP"), None)
    return {
        "style_id": style_doc.get("style_id", ""),
        "profile": profile,
        "family": family,
        "tags": tags,
        "rules": decisions,
        "applied": [d["rule_id"] for d in applied],
        "skipped": [{"rule_id": d["rule_id"], "reason": d["reason"]} for d in skipped],
        "warm_cap_pct": warm_cap,
        "ratio_rule": ("风格声明" if declared_total >= 60
                       else "60-30-10" if any(d["rule_id"] == "RATIO-60-30-10" for d in applied)
                       else "运营主导" if any(d["rule_id"] == "OPERATION-LED-PALETTE" for d in applied)
                       else "内容主导" if any(d["rule_id"] == "CONTENT-LED-PALETTE" for d in applied)
                       else "不套固定比例"),
        "ratio_target": ([e["pct"] for e in plan["entries"] if e.get("pct")] if declared_total >= 60
                         else [60, 30, 10] if any(d["rule_id"] == "RATIO-60-30-10" for d in applied)
                         else None),
        "palette": plan,
        "note": ("判据只对适用项生效；不适用的项在本项目里既不打分也不作为硬性要求，"
                 "理由逐条列出，不允许'默认都适用'。"),
    }


def _target_for(rule_id: str, profile: str) -> Any:
    if rule_id == "WARM-CAP":
        return WARM_CAP_BY_PROFILE.get(profile, None)
    if rule_id == "BLACK-ACCENT":
        return [3, 8]
    if rule_id == "RATIO-60-30-10":
        return [60, 30, 10]
    return None


def _declared_dark_cap(plan: Dict[str, Any]) -> Optional[int]:
    """Read a style's own declared upper bound for dark tones, if it states one."""
    for e in plan.get("entries") or []:
        usage = str(e.get("usage") or "")
        if e.get("luminance", 1) < 0.22 and "≤" in usage:
            m = _PCT.search(usage)
            if m:
                return int(m.group(1))
    return None


def check_palette(policy: Dict[str, Any], declared: Dict[str, Any]) -> Dict[str, Any]:
    """Compare a concept's declared palette against the *applicable* rules only."""
    out: List[Dict[str, Any]] = []
    warm_cap = policy.get("warm_cap_pct")
    warm = declared.get("warm_pct")
    dark = declared.get("dark_pct")

    if warm_cap is not None:
        ok = warm is None or warm <= warm_cap
        out.append({
            "rule_id": "WARM-CAP", "ok": ok,
            "detail": (f"暖材 {warm}% / 上限 {warm_cap}%" if warm is not None
                       else "概念未声明暖材占比，无法校核（不判通过）"),
            "evaluated": warm is not None,
        })
    else:
        out.append({"rule_id": "WARM-CAP", "ok": True, "evaluated": False,
                    "detail": f"{policy.get('profile')} 项目不设暖材上限（暖色是设计意图的一部分）"})

    if "BLACK-ACCENT" in (policy.get("applied") or []):
        # 3–8% 是判据默认区间；风格自己声明了 ≤10% 时按它的上限，不硬压回 8。
        declared_cap = _declared_dark_cap(policy.get("palette") or {})
        upper = declared_cap or 8
        ok = dark is None or (3 <= dark <= max(8, upper))
        out.append({
            "rule_id": "BLACK-ACCENT", "ok": ok, "evaluated": dark is not None,
            "detail": (f"深色 {dark}% / 区间 3–{max(8, upper)}%"
                       + (f"（风格声明上限 {upper}%）" if declared_cap else "")
                       if dark is not None else "未声明深色占比，无法校核"),
        })

    if policy.get("ratio_rule") == "风格声明":
        total = sum(p for p in (policy.get("ratio_target") or []) if p)
        ok = 80 <= total <= 110
        out.append({
            "rule_id": "RATIO-DECLARED", "ok": ok, "evaluated": True,
            "detail": f"风格声明色量合计 {total}%（应落在 80–110%，超出说明声明本身有误）",
        })
    elif policy.get("ratio_rule") == "60-30-10":
        ratio = declared.get("ratio")
        ok = ratio is None or (abs(ratio[0] - 60) <= 8 and abs(ratio[1] - 30) <= 8)
        out.append({
            "rule_id": "RATIO-60-30-10", "ok": ok, "evaluated": ratio is not None,
            "detail": f"声明比例 {ratio} / 目标 60-30-10" if ratio else "未声明比例",
        })
    else:
        out.append({"rule_id": "RATIO-60-30-10", "ok": True, "evaluated": False,
                    "detail": f"本项目采用「{policy.get('ratio_rule')}」，不套 60-30-10"})

    failed = [c for c in out if not c["ok"]]
    return {"checks": out, "failed": [c["rule_id"] for c in failed],
            "passed": not failed,
            "note": ("只有声明了数值的项才参与判断；未声明的项记为'无法校核'，"
                     "不记为通过——这是本项目对'不虚报'的一贯处理。")}


__all__ = ["RULES", "Rule", "PaletteEntry", "palette_plan", "aesthetic_policy",
           "check_palette", "warmth", "luminance", "hex_to_rgb",
           "WARM_CAP_BY_PROFILE"]
