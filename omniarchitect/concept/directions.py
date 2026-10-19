"""概念方向生成：从证据出发，而不是从风格出发。

流程是固定的四步，但结果不是固定的：

1. 把 S1 证据折成信号（采光不足 / 穿越冲突 / 面积紧张 / 收纳缺口 / 后场效率 …）；
2. 用信号给项目类型的空间原型打分（`prototypes.py`）；
3. 选出 2–3 套**空间家族不同**的原型，分别承担稳妥 / 体验 / 平衡三种角色；
4. 给每套方向配视觉语言（风格 + 材料 + 光），配的时候遵守业主已指定的风格。

第 3 步的"家族不同"是硬约束：两套概念如果都是线性组织、只是走廊宽度不同，
那不是两个方向，是一个方向的两个版本。宁可只出两套，也不凑三套。

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

from ..design import vocabulary as vocab
from ..style import load_catalog
from ..style.recommender import PREFERENCE_SYNONYMS, RecommendRequest, recommend
from . import palette as pal
from .context import ConceptContext
from .prototypes import Prototype, THEME_LABEL, for_profile

#: 三种角色。只是策略框架，不是固定风格。
ROLE_LABEL: Dict[str, str] = {
    "A": "稳妥 · 功能效率优先",
    "B": "特色 · 空间体验优先",
    "C": "平衡 · 复合与创新",
}

#: 推敲路径的角色名。原型路径的 A/B/C 是"功能/体验/平衡"三种取向；
#: 推敲出的策略不是按取向分的，是按**证据强弱**排的，硬套旧标签会说谎
#: （"院中取院"被标成"功能效率优先"，业主一看就知道不对）。
ROLE_LABEL_DELIBERATED: Dict[str, str] = {
    "A": "首推 · 证据最强",
    "B": "对照 · 另一端的组织逻辑",
    "C": "补充 · 第三种组织",
}

#: 体验类主题：角色 B 用它们打分
EXPERIENCE_THEMES = ("experience", "daylight", "brand", "exhibit", "arrival", "outdoor")
#: 功能类主题：角色 A 用它们打分
FUNCTION_THEMES = ("area", "storage", "kitchen", "circulation", "privacy",
                   "acoustic", "operation", "service", "focus", "collaboration", "growth")


def resolve_style_id(text: str, catalog=None) -> str:
    """Turn a client's wording into a catalog id. Returns '' when unsure.

    Deliberately conservative: 「意式极简」must land on `italian-minimal`, but an
    unknown phrase must return '' rather than the highest-scoring style — quietly
    substituting a different style is the one thing we must not do here.
    """
    cat = catalog or load_catalog()
    raw = (text or "").strip()
    if not raw:
        return ""
    low = raw.lower().replace(" ", "-")
    if low in cat:
        return low
    # 名称精确匹配（中文/英文）
    for e in cat:
        if raw in (e.display_name_zh, e.display_name_en):
            return e.style_id
    # 去掉修饰词再试：「现代意式极简」→「意式极简」
    for e in cat:
        if e.display_name_zh and e.display_name_zh in raw:
            return e.style_id
    # 关键词 → 标签，命中最多者胜，但要求至少两个标签命中才算数
    tags: set = set()
    for key in sorted(PREFERENCE_SYNONYMS, key=len, reverse=True):
        if key in raw:
            tags.update(PREFERENCE_SYNONYMS[key])
    if not tags:
        return ""
    scored = sorted(
        ((len(tags & set(e.tags)), e.style_id) for e in cat),
        key=lambda t: (-t[0], t[1]),
    )
    return scored[0][1] if scored and scored[0][0] >= 2 else ""


def _taste_words(ctx: ConceptContext) -> List[str]:
    """Taste words the client actually used, mapped through the existing bridge.

    Without this the style engine only knows the project type, and ties get
    broken alphabetically — a lakeside guesthouse came back as "African
    Contemporary" purely because of list order. Reading the client's own words
    ("安静"、"湖景"、"有仪式感") is both more accurate and better evidenced.
    """
    answers = " ".join(ctx.answers.values())
    words: List[str] = []
    for key in PREFERENCE_SYNONYMS:
        if key in answers and key not in words:
            words.append(key)
    return words[:4]


def _style_brief(ctx: ConceptContext, preference: str) -> RecommendRequest:
    """Pass S1 facts to the style engine — including what it must not override."""
    prefs: List[str] = []
    if preference:
        prefs.append(preference)
    if ctx.style_preference:
        prefs.append(ctx.style_preference)
    for w in _taste_words(ctx):
        if w not in prefs:
            prefs.append(w)
    return RecommendRequest(
        space_type=_space_type(ctx),
        area_m2=ctx.area_available_m2 or (ctx.target_area_m2 or None),
        budget_tier=ctx.budget_tier,
        location=ctx.location,
        preferences=prefs,
        maintenance=_maintenance_level(ctx.maintenance),
        stage="S2",
        must_include=[o["problem"] for o in ctx.opportunities[:3]],
        avoid=[] if not ctx.style_preference else [],
    )


def _space_type(ctx: ConceptContext) -> str:
    return {"residential": "住宅", "office": "办公", "hospitality": "酒店",
            "retail": "商业", "exhibition": "展厅", "architecture": "建筑"}.get(
        ctx.profile_id, "住宅")


def _maintenance_level(text: str) -> str:
    t = text or ""
    if any(w in t for w in ("低", "不想", "省心", "少打理", "简单")):
        return "low"
    if any(w in t for w in ("高", "可以", "愿意", "定期", "保养")):
        return "high"
    return "medium" if t else ""


@dataclass
class Concept:
    """One design direction: spatial prototype + visual language + evidence."""

    concept_id: str
    role: str
    concept_name: str
    concept_statement: str
    design_problem: str
    evidence: List[str]
    design_strategy: str
    prototype: Dict[str, Any]
    user_experience: str
    aesthetic_direction: str
    material_direction: List[Dict[str, str]]
    lighting_direction: List[str]
    cost_impact: str
    maintenance_impact: str
    technical_risks: List[str]
    advantages: List[str]
    tradeoffs: List[str]
    s1_opportunity_refs: List[str]
    style_ids: List[str] = field(default_factory=list)
    style_labels: List[str] = field(default_factory=list)
    style_basis: str = ""
    palette: Dict[str, Any] = field(default_factory=dict)
    aesthetic_policy: Dict[str, Any] = field(default_factory=dict)
    scores: Dict[str, float] = field(default_factory=dict)
    #: 走进去经历什么（`design/vocabulary.sequence_for`）。
    #: 有了这一段，方案才从「房间这么排」变成「人会这样走过」。
    experience_sequence: Dict[str, Any] = field(default_factory=dict)
    #: 业主诉求 vs 这套方向能不能给（`design/vocabulary.fit`）。
    feeling_fit: Dict[str, Any] = field(default_factory=dict)
    #: 设计推敲记录（六问 + parti + 技术协同）。走原型路径时为空，
    #: 此时方案的空间推理来自原型库而不是本项目——`source` 会如实写明。
    deliberation: Dict[str, Any] = field(default_factory=dict)
    #: "deliberated"（按本项目推敲）或 "prototype"（原型库兜底）。
    source: str = "deliberated"
    revision: int = 1
    pre_gate: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "concept_id": self.concept_id,
            "role": self.role,
            "role_label": (ROLE_LABEL_DELIBERATED.get(self.role, self.role)
                           if self.source == "deliberated"
                           else ROLE_LABEL.get(self.role, self.role)),
            "concept_name": self.concept_name,
            "concept_statement": self.concept_statement,
            "design_problem": self.design_problem,
            "evidence": list(self.evidence),
            "design_strategy": self.design_strategy,
            "spatial_prototype": self.prototype,
            "user_experience": self.user_experience,
            "aesthetic_direction": self.aesthetic_direction,
            "material_direction": [dict(m) for m in self.material_direction],
            "lighting_direction": list(self.lighting_direction),
            "cost_impact": self.cost_impact,
            "maintenance_impact": self.maintenance_impact,
            "technical_risks": list(self.technical_risks),
            "advantages": list(self.advantages),
            "tradeoffs": list(self.tradeoffs),
            "s1_opportunity_refs": list(self.s1_opportunity_refs),
            "style_ids": list(self.style_ids),
            "style_labels": list(self.style_labels),
            "style_basis": self.style_basis,
            "palette": self.palette,
            "aesthetic_policy": self.aesthetic_policy,
            "experience_sequence": self.experience_sequence,
            "feeling_fit": self.feeling_fit,
            "deliberation": self.deliberation,
            "source": self.source,
            "scores": {k: round(v, 1) for k, v in self.scores.items()},
            "revision": self.revision,
            "pre_gate": self.pre_gate,
        }

    @property
    def style_label(self) -> str:
        return " + ".join(self.style_labels) if self.style_labels else "待定风格"


# --------------------------------------------------------------------------
# 打分
# --------------------------------------------------------------------------
def _functional(p: Prototype, ctx: ConceptContext) -> Tuple[float, List[str]]:
    score, why = 0.0, []
    for theme in p.answers:
        s = ctx.signal(theme)
        if s > 0:
            w = 1.4 if theme in FUNCTION_THEMES else 1.0
            score += s * 18 * w
            why.append(f"回应{THEME_LABEL.get(theme, theme)}：{ctx.label(theme)}")
    if p.plan_strategy:
        score += 6
        why.append("S3 平面算法可直接落地该策略")
    else:
        why.append("S3 需要专用深化，现有平面算法不直接支持")
    return score, why


def _experiential(p: Prototype, ctx: ConceptContext) -> Tuple[float, List[str]]:
    score, why = 0.0, []
    for theme in p.answers:
        if theme in EXPERIENCE_THEMES:
            s = ctx.signal(theme)
            if s > 0:
                score += s * 16
                why.append(f"体验价值来自{THEME_LABEL.get(theme, theme)}")
    # 体验型原型在"只有功能问题"的项目里不该被硬推
    if not any(ctx.signal(t) for t in EXPERIENCE_THEMES):
        score -= 10
        why.append("本项目未出现体验类诉求，体验优势缺少依据")
    return score, why


def _feasibility(p: Prototype, ctx: ConceptContext) -> Tuple[float, List[str]]:
    """Penalise prototypes whose preconditions the project cannot meet."""
    score, why = 0.0, []
    if ctx.precision == "diagnostic":
        score -= 4
        why.append("无几何：原型只能作为方向，尺寸待 S3 验证")
    if ctx.budget_tier in ("economy",) and "增量" in p.cost_note:
        score -= 5
        why.append("预算偏紧，原型包含增量构造")
    if ctx.budget_tier == "luxury":
        score += 3
    if p.id == "RES-LIGHT" and ctx.area_available_m2 and ctx.area_available_m2 < 60:
        score -= 8
        why.append("小面积开天窗的收益不足以抵消构造风险")
    if p.family == "courtyard" and (ctx.area_available_m2 or 0) < 120 \
            and ctx.profile_id == "residential":
        score -= 6
        why.append("面积不足时院落会退化为天井")
    return score, why


def _rank(ctx: ConceptContext) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for p in for_profile(ctx.profile_id):
        f, fw = _functional(p, ctx)
        e, ew = _experiential(p, ctx)
        z, zw = _feasibility(p, ctx)
        total = f + e + z
        out.append({
            "prototype": p, "functional": f, "experiential": e, "feasibility": z,
            "total": total, "why": fw + ew + zw,
        })
    out.sort(key=lambda d: (-d["total"], d["prototype"].id))
    return out


def _pick(ranked: List[Dict[str, Any]], ctx: ConceptContext) -> List[Tuple[str, Dict[str, Any]]]:
    """A = functional fit, B = experience, C = balance. Distinct spatial families."""
    if not ranked:
        return []
    # 只考虑对已确认问题有回应的原型：一个什么都不回应的方向不是"另一种选择"，
    # 而是"另一个话题"。全部为 0 时才退回全集（此时没有任何依据，属于资料不足）。
    relevant = [d for d in ranked if d["functional"] > 0] or ranked
    ranked = relevant
    used_family: set = set()
    used_ids: set = set()
    picks: List[Tuple[str, Dict[str, Any]]] = []

    def take(role: str, key: str, *, require_new_family: bool = True) -> bool:
        for item in sorted(ranked, key=lambda d: (-d[key], d["prototype"].id)):
            p = item["prototype"]
            if p.id in used_ids:
                continue
            if require_new_family and p.family in used_family:
                continue
            picks.append((role, item))
            used_ids.add(p.id)
            used_family.add(p.family)
            return True
        return False

    take("A", "functional")
    take("B", "experiential")
    if not take("C", "total"):
        # 家族用尽时允许回到已用家族，但必须是不同原型，并如实标注
        for item in sorted(ranked, key=lambda d: -d["total"]):
            p = item["prototype"]
            if p.id in used_ids:
                continue
            picks.append(("C", item))
            used_ids.add(p.id)
            break
    return picks[:3]


# --------------------------------------------------------------------------
def _evidence_for(themes: Sequence[str], ctx: ConceptContext) -> Tuple[str, List[str], List[str]]:
    """Problem statement + its evidence + which opportunity ids it answers."""
    refs: List[str] = []
    lines: List[str] = []
    problems: List[str] = []

    theme_of: Dict[str, str] = {}
    for o in ctx.opportunities:
        blob = o["problem"] + o["design_goal"]
        for theme, words in (
            ("daylight", ("采光", "通透", "自然光")),
            ("privacy", ("隐私", "安静", "穿越")),
            ("area", ("面积", "复用", "密度", "装不下")),
            ("storage", ("收纳", "储物", "储藏")),
            ("kitchen", ("烹饪", "厨房", "用餐", "油烟")),
            ("structure", ("结构", "拆改", "承重")),
        ):
            if any(w in blob for w in words):
                theme_of.setdefault(theme, o)

    for theme in themes:
        o = theme_of.get(theme)
        if o:
            refs.append(o["opportunity_id"])
            problems.append(o["problem"])
            lines.append(f"{o['opportunity_id']}：{o['evidence']}")

    if not problems:
        # 没有机会条目时，用业主原话 + 需求矩阵行作为依据，不编造问题
        rows = [r for r in ctx.needs
                if r.get("priority") in ("must", "high") and r.get("activity")][:2]
        for r in rows:
            need = str(r.get("space_need") or "").strip()
            act = str(r["activity"]).strip()
            if need and need != act and act not in need:
                problems.append(f"{act}（{need}）")
            else:
                problems.append(act)
            lines.append(f"需求矩阵 {r['id']}：{act}，"
                         f"{r.get('priority_label', '')}，来源 {r.get('source')}")
        if not lines:
            problems.append("S1 资料有限，概念针对项目类型的基本空间关系，待 S3 用平面验证")
            lines.append(f"项目类型 {ctx.profile_label}，G1 基准已确认")
    return "；".join(dict.fromkeys(problems)), lines, list(dict.fromkeys(refs))


def _aesthetic_line(labels: Sequence[str], policy: Dict[str, Any]) -> str:
    """One line that names the colours, not just the rule."""
    entries = (policy.get("palette") or {}).get("entries") or []
    top = [f"{e['name']} {e['pct']}%" for e in entries if e.get("pct")][:3]
    colours = "、".join(top) if top else "风格未声明色量分配"
    return (f"{' + '.join(labels)}；配色关系「{policy.get('ratio_rule')}」：{colours}；"
            f"适用判据 {len(policy.get('applied') or [])} 条、"
            f"不适用 {len(policy.get('skipped') or [])} 条（逐条注明理由）")


def _materials(style_doc: Dict[str, Any], limit: int = 4) -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []
    for m in (style_doc.get("materials") or [])[:limit]:
        if not isinstance(m, dict):
            continue
        out.append({
            "name": str(m.get("name_zh") or m.get("name_en") or ""),
            "application": str(m.get("application") or ""),
            "finish": str(m.get("finish") or ""),
        })
    return [m for m in out if m["name"]]


def _lighting(style_doc: Dict[str, Any], p: Prototype, limit: int = 3) -> List[str]:
    strat = style_doc.get("lighting_strategy") or {}
    principles = [str(x) for x in (strat.get("principles") or [])][:limit]
    if not principles:
        principles = ["以低位与中位光建立层次，避免均匀漫射压平材料"]
    return [f"空间侧：{p.daylight}"] + [f"风格侧：{x}" for x in principles]


def _declared_palette(plan: Dict[str, Any]) -> Dict[str, Any]:
    """Read the numbers straight from the palette plan — do not recompute them.

    An earlier version re-derived "warm" from hue here, which made italian-minimal
    look 100% warm (every one of its colours is a warm hue) while the cap check
    used material words and read 30%. Two definitions of the same word is exactly
    how a check becomes decorative.
    """
    entries = plan.get("entries") or []
    declared = [e["pct"] for e in entries if e.get("pct")]
    return {
        "warm_pct": plan.get("warm_share"),
        "dark_pct": plan.get("dark_share"),
        "ratio": declared or None,
        "dominant": [e for e in entries if e["band"] == "dominant"],
        "secondary": [e for e in entries if e["band"] == "secondary"],
        "accent": [e for e in entries if e["band"] == "accent"],
    }


#: 视觉语言：两条路径（推敲 / 原型）共用。风格是观感，不参与空间推理。
def _visual(role: str, ctx: ConceptContext, catalog, recset, preferred_id: str):
    if preferred_id:
        style_ids = [preferred_id]
        basis = (f"业主指定「{ctx.style_preference}」→ 锁定 {preferred_id}（不替换为评分更高者）")
        if role == "C":
            entry = catalog.get(preferred_id)
            pair = next((c for c in entry.compatible_styles if c in catalog), "")
            if pair:
                style_ids.append(pair)
                basis += f"；平衡方向叠加 {pair} 作为对照表达（主导仍为 {preferred_id}）"
    else:
        opt = recset.option({"A": "safe", "B": "distinctive", "C": "hybrid"}[role])
        style_ids = [opt.style_id] if opt else [recset.options[0].style_id]
        basis = (f"风格系统按项目类型/面积/预算/维护建议 {style_ids[0]}"
                 f"（角色：{ {'A':'稳妥','B':'个性','C':'混搭'}[role] }）")

    style_doc = catalog.load_style(style_ids[0])
    policy = pal.aesthetic_policy(style_doc, ctx.profile_id)
    declared = _declared_palette(policy["palette"])
    check = pal.check_palette(policy, declared)
    labels = [catalog.get(s).label for s in style_ids]
    return style_ids, basis, style_doc, policy, declared, check, labels


def _from_deliberation(ctx: ConceptContext, strategies: Sequence[Dict[str, Any]],
                       *, pre_gate: bool = False) -> Dict[str, Any]:
    """把推敲出的策略写成方案。空间推理来自本项目，风格只负责观感。"""
    catalog = load_catalog()
    request = _style_brief(ctx, ctx.style_preference)
    recset = recommend(request, catalog=catalog)
    preferred_id = resolve_style_id(ctx.style_preference, catalog) if ctx.style_preference else ""

    concepts: List[Concept] = []
    roles = ("A", "B", "C")
    for i, st in enumerate(strategies[:3]):
        # 角色按顺序给，避免两条策略都写着 B 时 concept_id 撞车。
        role = roles[i]
        style_ids, basis, style_doc, policy, declared, check, labels = _visual(
            role, ctx, catalog, recset, preferred_id)

        prot = st["prototype"]
        problem, evidence, refs = _evidence_for(prot.get("answers") or [], ctx)
        _fit = vocab.fit(ctx.feelings, prot)
        d = st["deliberation"]

        tradeoffs = list(st["tradeoffs"])
        if check and any(c.get("evaluated") and not c["ok"] for c in check["checks"]):
            bad = [c["detail"] for c in check["checks"] if c.get("evaluated") and not c["ok"]]
            tradeoffs.append("配色校核未过：" + "；".join(bad))
        if ctx.precision != "authoritative_capable":
            tradeoffs.append("尺寸未核实：策略成立，但面积、净宽与层高须在 S3 复核")
        if d.get("unmet_requires"):
            tradeoffs.append("前提未满足：" + "、".join(d["unmet_requires"])
                             + "；需先确认前提，否则该方向退回为备选")

        risks = list(st["risks"])
        for c in (style_doc.get("construction_considerations") or [])[:2]:
            risks.append(str(c))
        if ctx.precision == "diagnostic":
            risks.append("无几何数据：本方向的面积与净宽结论暂不成立")

        # 材料表只放真材料。界面分工写在 design_strategy 里，
        # 塞一条"（随策略）"进材料表会让下游把占位符当材料往下传。
        materials = _materials(style_doc)

        concepts.append(Concept(
            concept_id=f"C-{role}",
            role=role,
            concept_name=st["name"],
            concept_statement=st["statement"],
            design_problem=problem,
            evidence=evidence,
            design_strategy="\n\n".join(x for x in (
                "parti：" + d["parti"],
                "体量与分区：" + d["massing"],
                "剖面与竖向：" + d["section"],
                "界面与虚实：" + d["facade"],
                "动线：" + str(prot.get("circulation") or ""),
            ) if x.strip("：")),
            prototype=prot,
            user_experience="；".join(s["event"] for s in d.get("experience") or []),
            aesthetic_direction=_aesthetic_line(labels, policy),
            material_direction=materials,
            lighting_direction=[f"空间侧：{prot.get('daylight') or ''}"]
            + [f"风格侧：{x}" for x in
               (style_doc.get("lighting_strategy") or {}).get("principles") or []][:3],
            cost_impact=st["cost_note"] + (f"（预算档位：{ctx.budget_tier or '未定'}）"
                                           if ctx.budget_tier else ""),
            maintenance_impact=st["maintenance"],
            technical_risks=risks,
            advantages=list(st["advantages"]),
            tradeoffs=tradeoffs,
            s1_opportunity_refs=refs,
            style_ids=style_ids,
            style_labels=labels,
            style_basis=basis,
            palette={**declared, "checks": check["checks"],
                     "source": policy["palette"]["source"]},
            aesthetic_policy={k: policy[k] for k in
                              ("applied", "skipped", "ratio_rule", "warm_cap_pct", "note")},
            scores={"evidence": d.get("evidence_score", 0.0)},
            experience_sequence=st["sequence"],
            feeling_fit=_fit,
            deliberation=d,
            source=("method" if (st.get("source") == "method") else "deliberated"),
            revision=ctx.revision,
            pre_gate=pre_gate,
        ))

    return {
        "project_id": ctx.project_id,
        "revision": ctx.revision,
        "profile_id": ctx.profile_id,
        "lead_discipline": ctx.lead_id,
        "lead_label": ctx.lead_label,
        "source": ("method" if any(x.get("source") == "method" for x in strategies)
                   else "deliberated"),
        "generated_at": __import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M"),
        "concepts": [c.to_dict() for c in concepts],
        "count": len(concepts),
        "roles": {c.concept_id: ROLE_LABEL[c.role] for c in concepts},
        "style_request": request.to_dict(),
        "style_options": [o.to_dict() for o in recset.options],
        "preferred_style": ctx.style_preference,
        "preferred_style_resolved": preferred_id,
        "pre_gate": pre_gate,
        "note": ("每套策略的组织逻辑互不相同（parti 不同、空间家族不同）；"
                 "若两套只差材料或措辞，说明推敲失效，应重做而不是沿用。"),
        "_concepts": concepts,
    }


def _taxonomy_block(ctx: ConceptContext) -> Dict[str, Any]:
    """分类与能力边界：S2 的产物要能回答"这是什么项目、能做到哪一步"。"""
    from .. import taxonomy as _tx

    tax = dict(getattr(ctx, "taxonomy", {}) or {})
    codes = [str(c) for c in (getattr(ctx, "taxonomy_codes", ()) or tax.get("codes") or [])]
    cap = _tx.capability_of(codes)
    focus: List[str] = []
    for c in codes:
        spec = _tx.resolve(c)
        if spec:
            focus += [x for x in spec.focus if x not in focus]
    return {
        "codes": codes,
        "names": [(_tx.resolve(c).name if _tx.resolve(c) else c) for c in codes],
        "natures": list(tax.get("natures") or []),
        "nature_labels": list(tax.get("nature_labels") or []),
        "commissions": list(tax.get("commissions") or []),
        "capability": cap,
        "focus": focus[:8],
        "s3_tasks": {d: _tx.s3_tasks(codes, d)
                     for d in ("architecture", "interior", "landscape")},
        "unknown": bool(tax.get("unknown")),
        "note": ("未识别出已知类型：按最宽口径推进，不套任何专项方法。"
                 if tax.get("unknown") else ""),
    }


def generate_concepts(ctx: ConceptContext, *, limit: int = 3,
                      pre_gate: bool = False,
                      research: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Produce 2–3 materially different directions, each with evidence attached.

    主导专业有推敲策略时走 `deliberation`（空间推理针对本项目）；没有时回退到
    22 个空间原型，并在结果里标明 `source="prototype"` —— 回退不是降级隐瞒，
    是换了一套经验来源。
    """
    from . import deliberation as delib

    if delib.applies(ctx):
        strategies = delib.build_strategies(ctx, research, limit=limit)
        if strategies:
            result = _from_deliberation(ctx, strategies, pre_gate=pre_gate)
            result["taxonomy"] = _taxonomy_block(ctx)
            return result

    ranked = _rank(ctx)
    picks = _pick(ranked, ctx)[:max(2, min(3, limit))]
    if not picks:
        return {"concepts": [], "count": 0, "ranked": [],
                "note": "该项目类型没有可用的空间原型——不生成占位方案。"}

    catalog = load_catalog()
    request = _style_brief(ctx, ctx.style_preference)
    recset = recommend(request, catalog=catalog)
    preferred_id = resolve_style_id(ctx.style_preference, catalog) if ctx.style_preference else ""

    concepts: List[Concept] = []
    for role, item in picks:
        p: Prototype = item["prototype"]
        style_ids, basis, style_doc, policy, declared, check, labels = _visual(
            role, ctx, catalog, recset, preferred_id)

        problem, evidence, refs = _evidence_for(p.answers, ctx)
        _seq = vocab.sequence_for(p.to_dict())
        _fit = vocab.fit(ctx.feelings, p.to_dict())

        advantages: List[str] = []
        if item["functional"] >= 12:
            advantages.append("对 S1 已确认的主要问题有直接回应")
        if item["experiential"] >= 10:
            advantages.append("空间体验有明确记忆点，且不需要靠装饰堆出来")
        if p.plan_strategy:
            advantages.append("可在 S3 直接转成平面校核，落地风险低")
        if not advantages:
            advantages.append("方向本身成立，但优势取决于后续深化——本轮不夸大")

        tradeoffs: List[str] = []
        if not p.plan_strategy:
            tradeoffs.append("S3 现有平面算法不直接支持，需要专用深化或调整原型")
        if ctx.budget_tier in ("economy", "mid") and "增量" in p.cost_note:
            tradeoffs.append("包含增量构造，预算偏紧时需要替换材料或减少造型")
        if ctx.precision != "authoritative_capable":
            tradeoffs.append("尺寸未核实：方向成立，但面积与净宽须在 S3 复核")
        for c in check["checks"]:
            if c.get("evaluated") and not c["ok"]:
                tradeoffs.append(f"配色校核未过：{c['detail']}")
        if not tradeoffs:
            tradeoffs.append("主要代价在施工与维护，见技术风险")

        risks = list(p.risks)
        for c in (style_doc.get("construction_considerations") or [])[:2]:
            risks.append(str(c))
        if ctx.precision == "diagnostic":
            risks.append("无几何数据：本方向的面积与净宽结论暂不成立")

        concepts.append(Concept(
            concept_id=f"C-{role}",
            role=role,
            concept_name=p.name,
            concept_statement=p.statement,
            design_problem=problem,
            evidence=evidence,
            design_strategy=(f"{p.spatial_logic}\n\n动线：{p.circulation}\n\n分区：{p.zoning}"),
            prototype=p.to_dict(),
            user_experience=p.experience,
            aesthetic_direction=_aesthetic_line(labels, policy),
            material_direction=_materials(style_doc),
            lighting_direction=_lighting(style_doc, p),
            cost_impact=p.cost_note + (f"（预算档位：{ctx.budget_tier or '未定'}）" if ctx.budget_tier else ""),
            maintenance_impact=p.maintenance,
            technical_risks=risks,
            advantages=advantages,
            tradeoffs=tradeoffs,
            s1_opportunity_refs=refs,
            style_ids=style_ids,
            style_labels=labels,
            style_basis=basis,
            palette={**declared, "checks": check["checks"], "source": policy["palette"]["source"]},
            aesthetic_policy={k: policy[k] for k in
                              ("applied", "skipped", "ratio_rule", "warm_cap_pct", "note")},
            scores={"functional": item["functional"], "experiential": item["experiential"],
                    "feasibility": item["feasibility"], "total": item["total"]},
            experience_sequence=_seq,
            feeling_fit=_fit,
            source="prototype",
            revision=ctx.revision,
            pre_gate=pre_gate,
        ))

    return {
        "project_id": ctx.project_id,
        "revision": ctx.revision,
        "profile_id": ctx.profile_id,
        "lead_discipline": ctx.lead_id,
        "lead_label": ctx.lead_label,
        "source": "prototype",
        "generated_at": __import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M"),
        "concepts": [c.to_dict() for c in concepts],
        "count": len(concepts),
        "roles": {c.concept_id: ROLE_LABEL[c.role] for c in concepts},
        "style_request": request.to_dict(),
        "style_options": [o.to_dict() for o in recset.options],
        "preferred_style": ctx.style_preference,
        "preferred_style_resolved": preferred_id,
        "pre_gate": pre_gate,
        "note": ("每套方向的空间家族互不相同；若某方向与另一方向只有材料或颜色差异，"
                 "说明生成有误，应重跑而不是沿用。"),
        "taxonomy": _taxonomy_block(ctx),
        "_concepts": concepts,      # 内部用，不写盘
    }


def _deliberation_md(c: Dict[str, Any]) -> List[str]:
    """六问 + 专业分工 + 技术协同。没有推敲记录（原型兜底）时不伪造这一段。"""
    d = c.get("deliberation") or {}
    if c.get("source") == "method" and d:
        out = ["### 设计推敲（按项目类型的方法）", "",
               "> 本类型的专属策略库尚未建立，因此方向来自该类型的设计方法："
               "组织逻辑（parti）与专业要点是这一类项目的通行做法，"
               "不是从通用住宅原型套出来的。深化时须按行业条件复核。", ""]
        out += ["**parti（一句话的组织逻辑）**：{}".format(d.get("parti") or "—"), ""]
        out += ["| 问题 | 本方案的答案 |", "|---|---|"]
        out.append("| 最有价值的设计机会 | {} |".format(_cell(d.get("key_opportunity"))))
        out.append("| 为什么采用这个策略 | {} |".format(_cell(d.get("why_this_strategy"))))
        out.append("| 光、视线、比例、材料如何配合 | {} |".format(
            _cell(d.get("light_view_proportion_material"))))
        out.append("| 三个专业如何成整体 | {} |".format(_cell(d.get("integration"))))
        out.append("")
        if d.get("gap"):
            out += ["> 缺口：{}".format(d["gap"]), ""]
        if d.get("technical_coordination"):
            out += ["**需要结构与机电配合的地方**：", ""]
            out += ["- {}".format(x) for x in d["technical_coordination"]]
            out.append("")
        return out
    if c.get("source") != "deliberated" or not d:
        return ["> 本方向来自 22 个空间原型的经验库，未做本项目专项推敲；"
                "空间逻辑是通用经验，须在 S3 按实测条件复核。", ""]
    out: List[str] = ["### 设计推敲", ""]
    out += ["**parti（一句话的组织逻辑）**：{}".format(d.get("parti") or "—"), ""]
    out += ["| 问题 | 本方案的答案 |", "|---|---|"]
    out.append("| 最有价值的设计机会 | {} |".format(_cell(d.get("key_opportunity"))))
    out.append("| 为什么采用这个策略 | {} |".format(_cell(d.get("why_this_strategy"))))
    out.append("| 光、视线、比例、材料如何配合 | {} |".format(
        _cell(d.get("light_view_proportion_material"))))
    out.append("| 三个专业如何成整体 | {} |".format(_cell(d.get("integration"))))
    out.append("")
    if d.get("levels_program"):
        out += ["**楼层分工（自下而上）**：", ""]
        for i, line in enumerate(d["levels_program"]):
            out.append("{}. {}".format(i + 1, line))
        out.append("")
    if d.get("zones"):
        out += ["**分区与占比**：", "",
                "| 分区 | 占比 |", "|---|---|"]
        for z in d["zones"]:
            out.append("| {} | {} |".format(z.get("name"), z.get("share")))
        out.append("")
    for key, label in (("water", "水景做法"), ("planting", "植物配置"),
                       ("paving", "铺装")):
        if d.get(key):
            out.append("**{}**：{}".format(label, d[key]))
            out.append("")
    if d.get("technical_coordination"):
        out += ["**需要结构与机电配合的地方**：", ""]
        out += ["- {}".format(x) for x in d["technical_coordination"]]
        out.append("")
    if d.get("unmet_requires") or d.get("unverified_requires"):
        bits = []
        if d.get("unmet_requires"):
            bits.append("不满足：" + "、".join(d["unmet_requires"]))
        if d.get("unverified_requires"):
            bits.append("未核验：" + "、".join(d["unverified_requires"]))
        out += ["> 前提条件：{}。未核验不等于不成立，但必须先确认再深化。".format(
            "；".join(bits)), ""]
    if d.get("precedent_note"):
        out += ["> {}".format(d["precedent_note"]), ""]
    if d.get("same_family_note"):
        out += ["> {}".format(d["same_family_note"]), ""]
    return out


def _cell(text: Any) -> str:
    """Markdown 表格单元格：压掉换行与竖线，避免把表撑破。"""
    return " ".join(str(text or "—").split()).replace("|", "／")


def _clip(text: Any, n: int) -> str:
    t = " ".join(str(text or "").split())
    return t if len(t) <= n else t[: n - 1] + "…"


def _sequence_md(c: Dict[str, Any]) -> List[str]:
    """把「走进去经历什么」写成业主能直接反对的一段。

    这段是本轮新增的核心：不给形容词，只给可指认的空间事件，让业主能说
    「不对，我进门应该先看到院子」。能这样被反驳的方案，才是设计。
    """
    seq = c.get("experience_sequence") or {}
    fit = c.get("feeling_fit") or {}
    out: List[str] = []
    steps = seq.get("steps") or []
    if steps:
        out += ["**走进去会经历什么**：", "", "| 段落 | 空间事件 | 手法 |", "|---|---|---|"]
        for s in steps:
            d = vocab.VOCABULARY.get(s.get("device") or "")
            out.append(f"| {s['step']} | {s['event']} | {d.name if d else '—'} |")
        out.append("")
    if seq.get("devices"):
        # 同一手法在序列里可能用两次；列两遍会让业主以为是两种手法。
        seen = list(dict.fromkeys(d for d in seq["devices"] if d in vocab.VOCABULARY))
        names = "、".join(vocab.VOCABULARY[d].name for d in seen)
        out += [f"本方案实际用到的手法：{names}", ""]
    if seq.get("missing_steps"):
        out += [f"> 本原型没有可指认的「{'、'.join(seq['missing_steps'])}」段落——"
                "如实标出，不用形容词补。", ""]

    if fit.get("status") == "met":
        # 「都能给」时更要写出差别：哪一句是这套方案的主张，哪一句只是勉强够用。
        out += [f"**对业主诉求的回应**：{fit.get('headline') or ''}", ""]
        for m in fit.get("primary") or []:
            out.append(f"- 「{m['word']}」—— {m['how']}")
        for m in fit.get("supported") or []:
            out.append(f"- 「{m['word']}」—— {m['how']}")
        out.append("")
    elif fit.get("status") == "at_risk":
        out += ["**对业主诉求的回应**："]
        for m in fit.get("met") or []:
            out.append(f"- 「{m['word']}」可以给：{m['how']}")
        for r in fit.get("at_risk") or []:
            tail = f"；起步做法：{r['fix']}" if r.get("fix") else ""
            out.append(f"- 「{r['word']}」需要额外补：{r['how']}{tail}")
        out.append("")
    return out


def markdown(result: Dict[str, Any], ctx: ConceptContext) -> str:
    lines: List[str] = []

    if result.get("source") == "deliberated":
        lead = result.get("lead_label") or ctx.lead_label
        lines += [
            "## 先看这一张：三套方案到底差在哪",
            "",
            "主导专业：{}。三套方案的组织逻辑互不相同，差别不在材料与颜色。".format(lead),
            "",
            "| 方案 | 组织逻辑 | 抓的机会 | 主要代价 |",
            "|---|---|---|---|",
        ]
        for c in result["concepts"]:
            d = c.get("deliberation") or {}
            lines.append("| {} {} | {} | {} | {} |".format(
                c["concept_id"], c["concept_name"],
                _cell(_clip(d.get("parti"), 46)),
                _cell(_clip(d.get("key_opportunity"), 46)),
                _cell(_clip((c.get("tradeoffs") or ["—"])[0], 46))))
        lines.append("")
    for c in result["concepts"]:
        p = c["spatial_prototype"]
        lines += [
            f"## {c['concept_id']} · {c['concept_name']}　（{c['role_label']}）",
            "",
            f"> {c['concept_statement']}",
            "",
            f"**空间家族**：{p['family_zh']}　**原型编号**：{p['prototype_id']}",
            "",
            "### 要解决的问题",
            "",
            c["design_problem"],
            "",
            "**依据**：",
            "",
            ] + [f"- {e}" for e in c["evidence"]] + [
            "",
            "### 空间策略",
            "",
            c["design_strategy"],
            "",
            "### 使用体验",
            "",
            c["user_experience"],
            "",
            ] + _sequence_md(c) + _deliberation_md(c) + [
            f"### 视觉语言：{' + '.join(c['style_labels'])}",
            "",
            f"- 风格依据：{c['style_basis']}",
            f"- 配色：{c['aesthetic_direction']}",
            "",
            "| 材料 | 用在 | 做法 |",
            "|---|---|---|",
            ] + [f"| {m['name']} | {m['application']} | {m['finish']} |"
                 for m in c["material_direction"]] + [
            "",
            "**光**：",
            "",
            ] + [f"- {x}" for x in c["lighting_direction"]] + [
            "",
            "### 代价与风险",
            "",
            f"- 造价：{c['cost_impact']}",
            f"- 维护：{c['maintenance_impact']}",
            ] + [f"- 技术风险：{r}" for r in c["technical_risks"]] + [
            "",
            "**优势**：" + "；".join(c["advantages"]),
            "",
            "**取舍**：" + "；".join(c["tradeoffs"]),
            "",
            "### 回应的 S1 机会",
            "",
            ("、".join(c["s1_opportunity_refs"]) if c["s1_opportunity_refs"]
             else "无独立机会条目，依据为需求矩阵与业主原话"),
            "",
            "---",
            "",
        ]
    lines += [
        "> 概念方向 ≠ 设计风格。空间原型决定房间怎么组织，风格决定它看起来像什么；"
        "两者可以自由组合，但不得用「换一种风格」冒充「换一个方案」。",
        f"> {ctx.dimensional_note}",
    ]
    return "\n".join(lines)


__all__ = ["Concept", "ROLE_LABEL", "generate_concepts", "resolve_style_id",
           "markdown", "EXPERIENCE_THEMES", "FUNCTION_THEMES"]
