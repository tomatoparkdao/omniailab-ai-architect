"""Style Recommendation Engine.

Given what the project actually is — space type, size, budget band, climate and
location, the client's taste, and how much upkeep they will tolerate — propose
**three materially different options**, each with its own rationale, advantages
and costs, then wait for the user to lock one.

Design choices worth knowing:

* Scoring is **explicit and inspectable**, not a black box. Every point a style
  earns is attributed to a named reason, so the agent can explain the ranking
  rather than assert it.
* The three options are forced apart: a safe fit, a distinctive alternative from
  a different family, and a hybrid built from the winner plus its declared
  compatible styles. Returning three near-identical styles would be useless.
* Maintenance tolerance is a first-class constraint. A style that scores well on
  looks but needs daily care is not a recommendation for a household that asked
  for low upkeep — it is a future complaint.
* Nothing here decides for the user. It reports a recommendation, the reasoning,
  and the alternatives; the lock step is explicit.

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from .catalog import Catalog, StyleEntry, load_catalog

BUDGET_ORDER = ("economy", "mid", "premium", "luxury")
MAINTENANCE_ORDER = ("low", "medium", "high")

# --------------------------------------------------------------------------
# Maintenance profile: how much upkeep a style demands in a normal home.
# This is engine knowledge, not schema data — the style records describe design
# intent; upkeep is a *use* property and belongs to the recommender.
# `reason` is what makes the rating arguable rather than arbitrary.
MAINTENANCE_PROFILE: Dict[str, Tuple[str, str]] = {
    "modern-minimalism": ("low", "无装饰线脚、少缝隙、素色饰面，日常擦拭即可"),
    "italian-minimal": ("medium", "大板石材与哑光木饰面怕酸怕刮，需要定期养护"),
    "contemporary-luxury": ("high", "高光与金属饰面易留指纹与划痕，需专业清洁"),
    "scandinavian": ("low", "浅色木与织物，耐磨、可局部更换"),
    "japandi": ("medium", "手工灰泥与深色木怕油污，需通风与定期养护"),
    "modernist-classic": ("low", "白墙与平直线条，维护简单"),
    "bauhaus": ("low", "钢管与平板门板，结构简单、易擦洗"),
    "corporate-contemporary": ("low", "耐磨地面与易清洁隔断，为高频使用设计"),
    "chinese-neo-classical": ("medium", "格栅与木饰面缝隙易积灰，需定期除尘"),
    "chinese-traditional": ("high", "雕花、榫卯与漆面陈设需要专业保养"),
    "wabi-sabi": ("medium", "手工肌理本就不追求匀净，但灰泥怕水、怕油"),
    "japanese-zen": ("medium", "榻榻米与木地板怕潮，需控制湿度与日照"),
    "korean-minimal": ("low", "圆角素色饰面与隐藏收纳，易打理"),
    "southeast-asian-tropical": ("medium", "实木与藤编在湿热环境需防霉处理"),
    "neoclassical": ("medium", "石膏线脚积灰，需定期除尘与补漆"),
    "european-classical": ("high", "镀金、雕刻与繁复线脚需要专业保养"),
    "french-romantic": ("high", "浅色织物与石膏线脚不耐脏，需频繁打理"),
    "american-classic": ("medium", "护墙板与实木家具需定期上蜡"),
    "english-country": ("high", "织物、壁纸与旧物混置，除尘负担大"),
    "american-country": ("medium", "原木与手作家具耐用，但需防潮防虫"),
    "victorian": ("high", "深色高光木、图案地毯与密集陈设，清洁难度高"),
    "art-deco": ("high", "高光漆面与金属镶嵌易留印，需专业维护"),
    "mid-century-modern": ("medium", "胡桃木需防晒防干裂，可翻新"),
    "retro-70s": ("high", "长绒织物与厚重地毯易积尘，需勤打理"),
    "memphis": ("medium", "层压板耐刮，但高饱和饰面怕褪色"),
    "postmodern": ("medium", "色彩块面怕磕碰，需局部修补"),
    "vintage-european": ("high", "旧物本就带痕迹，除尘与防虫成本高"),
    "industrial-loft": ("low", "混凝土、砖与钢构耐磨耐脏，几乎不娇气"),
    "brutalist": ("low", "清水混凝土耐候耐用，维护需求极低"),
    "warehouse-conversion": ("medium", "原结构耐久，但大面积高窗与明装管线需定期清理"),
    "steampunk": ("high", "黄铜与齿轮件需防氧化、定期上油"),
    "biophilic": ("high", "植物与绿化墙需要持续养护与灌溉系统"),
    "organic-modern": ("medium", "曲线无缝饰面怕磕碰，修补需整面处理"),
    "rustic-natural": ("low", "粗面材料耐刮耐污，痕迹可接受"),
    "tropical-resort": ("high", "木格栅、水面与户外织物需长期维护"),
    "mediterranean": ("low", "石灰抹面与陶土砖耐用，越旧越自然"),
    "earth-adobe": ("medium", "生土墙体怕水，需做好檐口与防水"),
    "moroccan": ("medium", "马赛克缝隙需防污，手工砖可局部更换"),
    "middle-eastern-luxury": ("high", "石材拼花与金箔饰面需要专业清洁"),
    "indian-contemporary": ("medium", "黄铜与织物需定期养护，石材耐用"),
    "african-contemporary": ("medium", "生土与手工艺品需防潮防虫"),
    "mexican-hacienda": ("medium", "陶砖与木梁耐用，彩墙需定期补漆"),
    "parametric-futurism": ("medium", "曲面无缝饰面修补困难，需整体处理"),
    "deconstructivism": ("medium", "斜交接缝与异形构件清洁不便"),
    "cyberpunk": ("high", "暗底与屏幕密集，落灰明显且线缆繁多"),
    "sci-fi-minimal": ("low", "无缝齐平收口，几乎无藏灰处"),
    "surrealist-interior": ("high", "异形构件与镜面需要频繁清洁"),
}

# Climate / location affinity: which style families travel well where.
# Keyed by a substring match on the user's location or climate note.
CLIMATE_AFFINITY: Tuple[Tuple[Tuple[str, ...], Tuple[str, ...], str], ...] = (
    (("潮湿", "湿热", "多雨", "梅雨", "沿海", "华南", "江南", "华东", "上海", "杭州",
      "广州", "深圳", "福建", "厦门", "海南", "长江", "tropical", "humid"),
     ("southeast-asian-tropical", "tropical-resort", "mediterranean", "industrial-loft",
      "modern-minimalism", "sci-fi-minimal"),
     "湿热或夏热冬冷地区宜选通风构造、快干材料与浅色反射面，避免大面积深色吸热面"),
    (("干燥", "寒冷", "北方", "严寒", "东北", "北京", "天津", "内蒙", "新疆", "dry", "cold"),
     ("scandinavian", "japandi", "mid-century-modern", "earth-adobe", "rustic-natural"),
     "干冷气候宜选高保温与蓄热做法、大面积木材与织物"),
    (("高原", "强日照", "少雨", "plateau", "云南", "西藏", "青海"),
     ("earth-adobe", "mediterranean", "brutalist", "moroccan"),
     "强日照少雨地区宜用厚墙蓄热、小窗遮阳、浅色反射面"),
    (("地震", "抗震"),
     ("modern-minimalism", "modernist-classic", "sci-fi-minimal"),
     "抗震区宜减少自重与复杂吊挂造型，优先轻质与整体性构造"),
)

# Chinese preference words → tags used in the style records.
#
# The records are tagged in English (that is the lingua franca of the prompt
# layer), but clients describe taste in Chinese. Without this bridge, someone
# asking for "简洁、温暖" scores exactly as if they had said nothing — which is
# how a recommender ends up suggesting Bauhaus to a family that wanted calm.
PREFERENCE_SYNONYMS: Dict[str, Tuple[str, ...]] = {
    "简洁": ("minimal", "restraint", "unadorned", "clean", "tidy"),
    "极简": ("minimal", "minimalism", "restraint", "unadorned", "seamless"),
    "温暖": ("warm", "warm-neutral", "warm-earth", "wood", "tactile", "cozy", "timber"),
    "温馨": ("cozy", "warm", "family", "homely", "layered"),
    "自然": ("natural", "organic", "rustic", "plants", "raw-materials", "honest"),
    "明亮": ("light", "pale", "daylight", "bright", "white"),
    "清爽": ("fresh", "light", "pale", "white", "airy", "minimal"),
    "安静": ("quiet", "calm", "serene", "restraint", "low-saturation"),
    "高级": ("luxury", "premium", "refined", "glamour", "stone"),
    "奢华": ("luxury", "opulent", "glamour", "gold", "statement"),
    "精致": ("refined", "delicate", "detail", "craft"),
    "复古": ("retro", "vintage", "patina", "aged", "heritage"),
    "工业": ("industrial", "exposed", "steel", "concrete", "raw"),
    "东方": ("oriental", "zen", "ink", "lattice", "symmetry", "courtyard"),
    "禅意": ("zen", "quiet", "natural", "restraint"),
    "侘寂": ("imperfection", "patina", "handmade", "quiet", "raw"),
    "厚重": ("mass", "monumental", "dense", "heavy"),
    "个性": ("bold", "statement", "playful", "anti-rule", "irony", "experimental"),
    "前卫": ("experimental", "futuristic", "algorithm"),
    "科技": ("tech-density", "engineered", "seamless", "monochrome"),
    "耐用": ("durable", "robust", "honest"),
    "粗犷": ("raw", "rough", "honest", "uneven"),
    "浪漫": ("delicate", "pastel", "curve", "soft"),
    "古典": ("classical", "moulding", "ornament", "formal", "symmetry"),
    "田园": ("country", "floral", "handmade", "casual", "rural"),
    "度假": ("resort", "water", "verandah", "outdoor", "relaxed"),
    "热带": ("tropical", "humid", "shade", "timber"),
    "地中海": ("mediterranean", "arch", "terracotta", "blue-white"),
    "日式": ("tatami", "shoji", "zen", "japanese"),
    "北欧": ("light", "wood", "hygge", "pale", "functional"),
    "意式": ("italian", "stone", "matte", "luxury"),
    "中式": ("lattice", "ink", "courtyard", "symmetry", "oriental"),
    "办公": ("workplace", "acoustic", "glass", "efficient", "calm"),
    "商业": ("statement", "glamour", "retail", "graphic"),
    "色彩丰富": ("bold-color", "colour", "vivid", "playful"),
    "低饱和": ("low-saturation", "muted", "neutral", "calm"),
}

# Space-type affinity by family — a coarse prior, refined by the record's own
# `applicable_spaces` during scoring.
#: 空间用途 → 常用的风格族。用途没被任何风格显式声明时，用这一层兜底，
#: 免得候选池空掉后按字母序选出一个跟项目无关的风格。
SPACE_FAMILY_PRIOR: Dict[str, Tuple[str, ...]] = {
    "住宅": ("modern", "oriental", "natural-organic", "classic"),
    "办公": ("modern", "industrial", "experimental"),
    "商业": ("modern", "deco-retro", "experimental", "industrial"),
    "餐饮": ("industrial", "deco-retro", "natural-organic", "regional"),
    "酒店": ("modern", "natural-organic", "regional", "classic"),
    "展厅": ("experimental", "modern", "industrial"),
    "展陈": ("experimental", "modern", "industrial"),
    "教育": ("modern", "natural-organic", "industrial"),
    "医疗": ("modern", "natural-organic"),
    "康养": ("natural-organic", "modern", "oriental"),
    "工业": ("industrial", "modern"),
    "农业": ("industrial", "natural-organic"),
    "景观": ("natural-organic", "oriental", "modern"),
    "庭院": ("natural-organic", "oriental", "modern"),
    "文化": ("modern", "experimental", "industrial", "regional"),
    "交通": ("modern", "industrial"),
    "体育": ("modern", "industrial", "natural-organic"),
}

SMALL_AREA_M2 = 90        # below this, heavy ornament and deep mouldings hurt
LARGE_AREA_M2 = 220       # above this, purely minimal schemes risk feeling empty

# Styles that are known to fight small footprints (need ceiling height / depth).
NEEDS_HEIGHT = {
    "european-classical": "需要较高净高承载柱式与穹顶语言（常见工程惯例区间 ≥4200mm）",
    "victorian": "装饰密度高，低净高下会显得压抑",
    "brutalist": "构件尺度粗大，小户型内难以成立",
    "middle-eastern-luxury": "大体量与高装饰密度需要足够面积展开",
    "warehouse-conversion": "依赖原有大跨度结构，常规住宅无法复现",
}


@dataclass
class RecommendRequest:
    """What the engine needs to know. Anything omitted simply scores neutral."""

    space_type: str = "住宅"          # 住宅 / 办公 / 商业 / 餐饮 / 酒店 / 展厅
    area_m2: Optional[float] = None
    budget_tier: str = ""             # economy / mid / premium / luxury
    location: str = ""                # 城市/地区或气候描述
    preferences: Sequence[str] = ()   # 用户喜好关键词或已指定的 style_id
    maintenance: str = ""             # low / medium / high —— 可接受的维护投入
    stage: str = "S2"
    must_include: Sequence[str] = ()  # 必须兼容的元素/需求
    avoid: Sequence[str] = ()         # 明确不要的东西

    def to_dict(self) -> Dict[str, Any]:
        return {
            "space_type": self.space_type,
            "area_m2": self.area_m2,
            "budget_tier": self.budget_tier,
            "location": self.location,
            "preferences": list(self.preferences),
            "maintenance": self.maintenance,
            "stage": self.stage,
            "must_include": list(self.must_include),
            "avoid": list(self.avoid),
        }


@dataclass
class Recommendation:
    """One option. `why` is the audit trail of the score."""

    role: str                       # safe | distinctive | hybrid
    style_id: str
    style_label: str
    score: float = 0.0
    why: List[str] = field(default_factory=list)
    pros: List[str] = field(default_factory=list)
    cons: List[str] = field(default_factory=list)
    fit: Dict[str, str] = field(default_factory=dict)
    hybrid_with: List[str] = field(default_factory=list)
    cautions: List[str] = field(default_factory=list)

    @property
    def role_zh(self) -> str:
        return {"safe": "稳妥首选", "distinctive": "个性对照", "hybrid": "混搭方案"}.get(self.role, self.role)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "role": self.role,
            "role_zh": self.role_zh,
            "style_id": self.style_id,
            "style": self.style_label,
            "score": round(self.score, 2),
            "why": list(self.why),
            "pros": list(self.pros),
            "cons": list(self.cons),
            "fit": dict(self.fit),
            "hybrid_with": list(self.hybrid_with),
            "cautions": list(self.cautions),
        }


@dataclass
class RecommendationSet:
    """Three options plus the lock step. Nothing is locked until asked."""

    request: RecommendRequest
    options: List[Recommendation] = field(default_factory=list)
    locked_style: str = ""
    lock_file: str = ""

    def option(self, role: str) -> Optional[Recommendation]:
        return next((o for o in self.options if o.role == role), None)

    def styles(self) -> List[str]:
        return [o.style_id for o in self.options]

    def lock(self, style_id: str, *, out_dir: str | Path,
             revision: int = 1, by: str = "") -> Dict[str, Any]:
        """Record the user's decision. Only after this may the engine proceed.

        The lock records *what* was chosen and *why*, plus the revision of the
        design it attaches to — so a later geometry change can invalidate it
        rather than silently keep a stale style.
        """
        known = {o.style_id for o in self.options}
        if style_id not in known and style_id not in {
            h for o in self.options for h in o.hybrid_with
        }:
            raise ValueError(
                f"{style_id!r} 不在本次推荐的三套方案内；"
                f"候选为 {sorted(known)}。若要选其它风格，请重新推荐或显式指定。"
            )
        chosen = self.option("safe")
        for o in self.options:
            if o.style_id == style_id:
                chosen = o
                break
        payload = {
            "locked_style": style_id,
            "role": chosen.role if chosen else "",
            "style_label": chosen.style_label if chosen else "",
            "revision": revision,
            "locked_by": by or "业主",
            "request": self.request.to_dict(),
            "options_considered": [o.to_dict() for o in self.options],
            "note": "风格已锁定。后续所有提示词编译与材料选择以本条为准；"
                    "几何或需求发生变更时应重新评估是否解锁。",
            "reversible": True,
        }
        p = Path(out_dir) / f"style-lock-r{revision}.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        self.locked_style = style_id
        self.lock_file = str(p)
        return payload

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request": self.request.to_dict(),
            "options": [o.to_dict() for o in self.options],
            "locked_style": self.locked_style,
            "lock_file": self.lock_file,
            "disclaimer": "推荐为方案层面建议，最终选择与门禁确认由业主与主创完成。",
        }

    def render(self) -> str:
        """Human-readable three-option comparison, for the S2 gate."""
        req = self.request
        head = [
            "# 风格推荐（三套方案对比）",
            "",
            f"- 空间类型：{req.space_type}",
        ]
        if req.area_m2:
            head.append(f"- 面积：{req.area_m2:g} m²")
        if req.budget_tier:
            head.append(f"- 预算档位：{req.budget_tier}")
        if req.location:
            head.append(f"- 所在地 / 气候：{req.location}")
        if req.maintenance:
            head.append(f"- 可接受维护投入：{req.maintenance}")
        if req.preferences:
            head.append(f"- 已表达的偏好：{'、'.join(req.preferences)}")
        head += ["", "| 方案 | 风格 | 得分 | 主要优点 | 主要代价 |", "|---|---|---|---|---|"]
        for o in self.options:
            pros = o.pros[0] if o.pros else "—"
            cons = o.cons[0] if o.cons else "—"
            head.append(f"| {o.role_zh} | {o.style_label} | {o.score:.1f} | {pros} | {cons} |")
        head.append("")
        for o in self.options:
            head += [f"## {o.role_zh}：{o.style_label}", ""]
            head.append("**为什么推荐它**")
            head += [f"- {w}" for w in o.why] or ["- （无）"]
            head.append("")
            head.append("**优点**")
            head += [f"- {p}" for p in o.pros] or ["- （无）"]
            head.append("")
            head.append("**代价与风险**")
            head += [f"- {c}" for c in o.cons] or ["- （无）"]
            if o.hybrid_with:
                head.append("")
                head.append("**混搭建议**")
                head += [f"- 可与 {h} 混搭（取其材质或色板，不改其空间逻辑）" for h in o.hybrid_with]
            if o.fit:
                head.append("")
                head.append("**适配核对**")
                head += [f"- {k}：{v}" for k, v in o.fit.items()]
            if o.cautions:
                head.append("")
                head.append("**提醒**")
                head += [f"- {c}" for c in o.cautions]
            head.append("")
        head += [
            "---",
            "",
            "**请指定其中一套**（回复风格名即可）。确认后风格将被锁定，"
            "后续提示词编译、材料与家具选择都以锁定结果为准。",
            "",
            "> 本推荐为方案层面建议，不构成工程结论；最终选择由业主与主创完成。",
        ]
        return "\n".join(head)


# --------------------------------------------------------------------------
_SYNONYM_CACHE: Dict[str, Tuple[str, ...]] = {}


def _preference_synonyms() -> Dict[str, Tuple[str, ...]]:
    """The preference bridge, longest key first so 「极简」 beats 「简」."""
    if not _SYNONYM_CACHE:
        for k in sorted(PREFERENCE_SYNONYMS, key=len, reverse=True):
            _SYNONYM_CACHE[k] = PREFERENCE_SYNONYMS[k]
    return _SYNONYM_CACHE


def _tier_gap(budget: str, style_tier: str) -> int:
    if budget not in BUDGET_ORDER or style_tier not in BUDGET_ORDER:
        return 0
    return BUDGET_ORDER.index(style_tier) - BUDGET_ORDER.index(budget)


def _climate_hint(location: str) -> Tuple[Tuple[str, ...], str]:
    low = (location or "").lower()
    for words, ids, note in CLIMATE_AFFINITY:
        if any(w.lower() in low for w in words):
            return ids, note
    return (), ""


def _score(entry: StyleEntry, req: RecommendRequest,
           climate_ids: Sequence[str]) -> Tuple[float, List[str], List[str]]:
    """Return (score, why, cautions). Every point is attributable."""
    score = 0.0
    why: List[str] = []
    cautions: List[str] = []

    # 1. space fit from the record's own declaration
    if req.space_type:
        if any(req.space_type in s for s in entry.applicable_spaces):
            score += 22
            why.append(f"该风格明确适用于「{req.space_type}」")
        else:
            prior = SPACE_FAMILY_PRIOR.get(req.space_type, ())
            if entry.family in prior:
                score += 12
                why.append(f"同族（{entry.family}）常用于「{req.space_type}」，但该风格未显式声明")
            else:
                score -= 18
                cautions.append(f"该风格的适用空间未包含「{req.space_type}」，需人工确认是否合适")

    # 2. budget
    gap = _tier_gap(req.budget_tier, entry.budget_tier)
    if req.budget_tier and entry.budget_tier:
        if gap == 0:
            score += 22
            why.append(f"造价档位与预算一致（{entry.budget_tier}）")
        elif gap < 0:
            score += 14
            why.append(f"造价档位（{entry.budget_tier}）低于预算（{req.budget_tier}），有做减法的余地")
        elif gap == 1:
            score -= 6
            cautions.append(f"该风格典型档位为 {entry.budget_tier}，高于当前预算一档，需要取舍")
        else:
            score -= 20
            cautions.append(f"该风格典型档位为 {entry.budget_tier}，明显高于预算，不建议直接采用")

    # 3. maintenance tolerance
    if req.maintenance and entry.style_id in MAINTENANCE_PROFILE:
        level, reason = MAINTENANCE_PROFILE[entry.style_id]
        if req.maintenance not in MAINTENANCE_ORDER:
            pass
        else:
            delta = MAINTENANCE_ORDER.index(level) - MAINTENANCE_ORDER.index(req.maintenance)
            if delta == 0:
                score += 18
                why.append(f"维护强度与你的容忍度一致（{reason}）")
            elif delta < 0:
                score += 10
                why.append(f"维护强度低于你的容忍度（{reason}）")
            elif delta == 1:
                score -= 8
                cautions.append(f"维护强度高于你的容忍度：{reason}")
            else:
                score -= 22
                cautions.append(f"维护强度明显超出你的容忍度：{reason}")

    # 4. climate / location
    if climate_ids:
        if entry.style_id in climate_ids:
            score += 16
            _, note = _climate_hint(req.location)
            why.append(f"与所在地条件契合（{note}）")

    # 5. stated preferences — the strongest signal, because it is the only one
    # that comes from the client rather than from our own priors.
    prefs = [p.strip().lower() for p in req.preferences if p and p.strip()]
    if prefs:
        blob = " ".join([entry.style_id, entry.display_name_zh, entry.display_name_en,
                         " ".join(entry.tags)]).lower()
        exact = [p for p in prefs if p == entry.style_id]
        if exact:
            score += 40
            why.append("你已点名该风格")
        else:
            direct = [p for p in prefs if p in blob]
            if direct:
                score += 12 * len(direct)
                why.append(f"直接命中的偏好词：{'、'.join(direct)}")
            # Chinese taste words have to be translated onto the English tags,
            # or "简洁、温暖" would score the same as saying nothing at all.
            have = {t.lower() for t in entry.tags}
            mapped: List[str] = []
            for p in prefs:
                for zh, tags in _preference_synonyms().items():
                    if zh in p and (have & {t.lower() for t in tags}):
                        mapped.append(zh)
                        break
            if mapped:
                score += 14 * len(mapped)
                why.append(f"与你的取向一致：{'、'.join(mapped)}")

    # 6. scale sanity
    if req.area_m2:
        if req.area_m2 < SMALL_AREA_M2 and entry.style_id in NEEDS_HEIGHT:
            score -= 16
            cautions.append(f"小面积（{req.area_m2:g} m²）下难以成立：{NEEDS_HEIGHT[entry.style_id]}")
        elif req.area_m2 >= LARGE_AREA_M2 and entry.style_id in (
                "modern-minimalism", "scandinavian", "sci-fi-minimal"):
            score -= 6
            cautions.append("大面积下纯极简容易显得空旷，需要用材质和光线补足层次")

    # 7. avoid list
    blob = " ".join([entry.style_id, entry.display_name_zh, entry.display_name_en,
                     " ".join(entry.tags)]).lower()
    for a in req.avoid:
        if a and a.strip().lower() in blob:
            score -= 30
            cautions.append(f"与你的排除项「{a}」冲突")

    return score, why, cautions


def _pros(entry: StyleEntry, style: Dict[str, Any]) -> List[str]:
    out: List[str] = []
    sp = style.get("spatial_principles") or []
    if sp:
        out.append(str(sp[0]))
    mats = style.get("materials") or []
    if mats:
        names = "、".join(str(m.get("name_zh", "")) for m in mats[:3] if m.get("name_zh"))
        out.append(f"材料体系清晰：{names}")
    lighting = (style.get("lighting_strategy") or {}).get("principles") or []
    if lighting:
        out.append(str(lighting[0]))
    return out[:3]


def _cons(entry: StyleEntry, style: Dict[str, Any], req: RecommendRequest) -> List[str]:
    out: List[str] = []
    budget = style.get("budget_considerations") or {}
    drivers = budget.get("drivers") or []
    if drivers:
        out.append(f"预算主要吃在：{'、'.join(str(d) for d in drivers[:3])}")
    for c in style.get("construction_considerations") or []:
        out.append(f"施工注意：{c}")
    if len(out) > 3:
        out = out[:3]
    return out


def recommend(
    request: RecommendRequest,
    *,
    catalog: Optional[Catalog] = None,
    top_k: int = 3,
) -> RecommendationSet:
    """Produce three materially different options, or fewer if the pool is small."""
    cat = catalog or load_catalog()
    climate_ids, climate_note = _climate_hint(request.location)

    # 先按"这个用途"收窄候选池：风格记录自己声明了适用空间，就以声明为准；
    # 声明不足三条时，用同族风格补足。不收窄的话，一个没人声明过的用途
    # （比如"医疗""工业"）会让所有风格同分，最后按 style_id 字母序选出
    #  africain-contemporary 这种跟项目完全无关的风格。
    pool: List[StyleEntry] = []
    if request.space_type:
        pool = [e for e in cat
                if any(request.space_type in str(sp) for sp in e.applicable_spaces)]
        if len(pool) < 3:
            fams = SPACE_FAMILY_PRIOR.get(request.space_type, ())
            pool += [e for e in cat if e.family in fams and e not in pool]
    if len(pool) < 3:
        pool = list(cat)

    scored: List[Tuple[float, StyleEntry, List[str], List[str]]] = []
    for entry in pool:
        score, why, cautions = _score(entry, request, climate_ids)
        scored.append((score, entry, why, cautions))
    # 同分时按该用途的常用族排序，而不是按 style_id 字母序——
    # 字母序会让 african-contemporary 永远排在第一个。
    prior_fams = SPACE_FAMILY_PRIOR.get(request.space_type, ())

    def _rank(entry: StyleEntry) -> int:
        try:
            return prior_fams.index(entry.family)
        except ValueError:
            return len(prior_fams) + 1

    scored.sort(key=lambda t: (-t[0], _rank(t[1]), t[1].style_id))

    options: List[Recommendation] = []
    used_families: set[str] = set()

    def add(role: str, item: Tuple[float, StyleEntry, List[str], List[str]]) -> None:
        score, entry, why, cautions = item
        style = cat.load_style(entry.style_id)
        fit: Dict[str, str] = {}
        if request.budget_tier:
            gap = _tier_gap(request.budget_tier, entry.budget_tier)
            fit["预算"] = ("档位一致" if gap == 0 else
                          f"低于预算 {abs(gap)} 档，可升级材料" if gap < 0 else
                          f"高于预算 {abs(gap)} 档，需要取舍")
        if request.area_m2:
            fit["尺度"] = ("适合小面积时需做减法" if request.area_m2 < SMALL_AREA_M2
                           else "需要材质层次补足空旷感" if request.area_m2 >= LARGE_AREA_M2
                           else "常规面积下可直接落地")
        if entry.style_id in MAINTENANCE_PROFILE:
            fit["维护"] = MAINTENANCE_PROFILE[entry.style_id][1]
        if climate_note:
            fit["气候"] = "契合" if entry.style_id in climate_ids else "中性，需在构造上补强"
        hybrid = [h for h in entry.compatible_styles if h in cat][:2]
        options.append(Recommendation(
            role=role,
            style_id=entry.style_id,
            style_label=entry.label,
            score=score,
            why=why or ["综合条件匹配"],
            pros=_pros(entry, style),
            cons=_cons(entry, style, request),
            fit=fit,
            hybrid_with=hybrid,
            cautions=cautions,
        ))
        used_families.add(entry.family)

    # A — best overall fit
    if scored:
        add("safe", scored[0])

    # B — best outside the leading family, so the alternative is truly different
    for item in scored[1:]:
        if item[1].family not in used_families:
            add("distinctive", item)
            break
    else:
        if len(scored) > 1:
            add("distinctive", scored[1])

    # C — hybrid: the leading style plus its declared compatible partners
    if options:
        lead = options[0]
        partners = [h for h in lead.hybrid_with if h in cat][:2]
        if partners:
            base = cat.get(partners[0])
            hybrid_score = lead.score - 4
            style = cat.load_style(base.style_id)
            options.append(Recommendation(
                role="hybrid",
                style_id=base.style_id,
                style_label=f"{lead.style_label} + {base.label}",
                score=hybrid_score,
                why=[
                    f"以 {lead.style_label} 为主，借 {base.label} 的材质或色板补层次",
                    f"两者在各自记录里互相声明兼容（{lead.style_id} ↔ {base.style_id}）",
                ],
                pros=_pros(base, style)[:2] or [f"补足 {lead.style_label} 的单调感"],
                cons=["混搭需要一份明确的配比纪律，否则容易两边都不像",
                      "需要在材料表里分别标注主次，施工时不能自由发挥"],
                fit={"主次": f"主 {lead.style_label} ≥70%，借入 {base.label} ≤30%"},
                hybrid_with=[lead.style_id],
                cautions=["混搭前先确认两套风格的光照策略不冲突"],
            ))

    return RecommendationSet(request=request, options=options[:top_k])
