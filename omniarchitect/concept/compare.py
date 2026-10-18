"""多方案比较与总设计师推荐。

比较的目的不是算出一个分数排名，而是让业主看清**取舍**。所以每一项评分都必须
带理由，且资料不足时记 `未评估`——不把"资料缺失"折算成中间分，那等于用 50 分
掩盖一个没有依据的判断。

推荐只表达总设计师的专业倾向，不代替业主决策。推荐必须写三件事：
为什么是它、为什么不是另外两套、进 S3 之前还要核实什么。

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

#: 评价维度与权重。权重体现"概念阶段最该关心什么"。
CRITERIA: Sequence[Dict[str, Any]] = (
    {"id": "needs", "name": "S1 需求响应", "weight": 0.24},
    {"id": "opportunity", "name": "设计机会解决", "weight": 0.20},
    {"id": "spatial", "name": "空间组织合理性", "weight": 0.16},
    {"id": "aesthetic", "name": "美学与业主偏好", "weight": 0.12},
    {"id": "budget", "name": "预算适配", "weight": 0.10},
    {"id": "buildability", "name": "施工与维护", "weight": 0.10},
    {"id": "downstream", "name": "后续深化可行性", "weight": 0.08},
)


def _clamp(v: float) -> int:
    return int(max(0, min(100, round(v))))


#: 第一层：不可逾越的硬门槛。清单与四态语义统一在 `hardgate` 里定义，
#: 这里不再维护第二份——两套分类正是 S1/S2 结论对不上的根源。
GATE_BLOCKING = {"area": "面积不成立", "capacity": "容量明显不足",
                 "safety": "已识别的安全条件不成立",
                 "regulation": "已识别的强制性规范不允许",
                 "physics": "经核实的物理条件不可满足"}


def _lead_weights(ctx: Any) -> Dict[str, float]:
    """主导专业决定的维度权重。没有主导信息时退回中性权重。"""
    try:
        return dict(getattr(ctx, "lead_weights", {}) or {})
    except Exception:                                  # noqa: BLE001
        return {}


def _w(ctx: Any, cid: str, base: float) -> float:
    return round(base * _lead_weights(ctx).get(cid, 1.0), 4)


def _hard_gate(ctx: Any, concept: Dict[str, Any]) -> Dict[str, Any]:
    """第一层可行性门槛：不管设计多好，`failed` 就不能当推荐。

    直接复用 `hardgate.evaluate()` 的口径，只保留 failed 与 unknown 的区分：
    * `failed`  → 不参与推荐排序（美学分不能抵消）；
    * `unknown` → 参与排序但标为待补资料，不冒充通过。
    """
    reasons: List[Dict[str, str]] = []
    unknowns: List[Dict[str, str]] = []
    verdict = getattr(ctx, "hard_gate", None)
    if isinstance(verdict, dict):
        for row in verdict.get("rows") or []:
            item = {"id": row.get("dimension", ""),
                    "category": row.get("dimension", ""),
                    "text": row.get("statement", "")}
            if row.get("status") == "failed":
                reasons.append(item)
            elif row.get("status") == "unknown":
                item["needs"] = row.get("needs", "")
                unknowns.append(item)
    else:
        # 没有统一判定时退回 ctx.conflicts，但仍按同一套维度词过滤
        for c in getattr(ctx, "conflicts", []) or []:
            cat = str(c.get("category") or "")
            if cat in GATE_BLOCKING and str(c.get("severity") or "") == "blocker":
                reasons.append({"id": str(c.get("id") or ""), "category": cat,
                                "text": str(c.get("problem") or "")})
    # 概念层面的容量硬冲突（如办公人均面积不足）
    for r in (concept.get("discipline_conflicts") or []):
        if str(r.get("severity") or "") == "blocker":
            reasons.append({"id": str(r.get("id") or ""), "category": "capacity",
                            "text": str(r.get("detail") or "")})
    return {
        "failed": bool(reasons),
        "reasons": reasons,
        "unknowns": unknowns,
        "rule": ("安全 / 消防与强制性规范 / 已核实的容量与物理限制不成立时，"
                 "不能用美学高分抵消。unknown 不等于 passed。"),
    }


def evaluate(concept: Dict[str, Any], ctx: Any, total_opportunities: int) -> Dict[str, Any]:
    """Score one concept. Every number carries the reason it was given."""
    rows: List[Dict[str, Any]] = []

    # 1. 需求响应 —— 用原型与信号的匹配度，而不是自评
    func = float((concept.get("scores") or {}).get("functional") or 0)
    rows.append({
        "id": "needs", "name": "S1 需求响应", "weight": _w(ctx, "needs", 0.24),
        "score": _clamp(min(100, func * 2.2)) if func else None,
        "reason": (f"原型回应的信号强度合计 {func:.1f}（来自需求矩阵与机会条目）"
                   if func else "无信号可对照"),
        "evaluated": bool(func),
    })

    # 2. 机会解决 —— 覆盖了几个机会，不是"感觉回应得好"
    refs = concept.get("s1_opportunity_refs") or []
    if total_opportunities:
        rows.append({
            "id": "opportunity", "name": "设计机会解决", "weight": _w(ctx, "opportunity", 0.20),
            "score": _clamp(100 * len(refs) / total_opportunities),
            "reason": f"覆盖 {len(refs)}/{total_opportunities} 项机会（{'、'.join(refs) or '无'}）",
            "evaluated": True,
        })
    else:
        rows.append({"id": "opportunity", "name": "设计机会解决", "weight": _w(ctx, "opportunity", 0.20),
                     "score": None, "reason": "S1 未识别到机会条目，本项不评",
                     "evaluated": False})

    # 3. 空间组织 —— 家族清晰度 + 是否有可核验的组织描述
    p = concept.get("spatial_prototype") or {}
    zoning_txt = str(p.get("zoning") or "")
    circ_txt = str(p.get("circulation") or "")
    base = 55
    why = []
    if len(zoning_txt) > 25:
        base += 15
        why.append("分区原则可被一句话复述")
    if len(circ_txt) > 25:
        base += 15
        why.append("动线关系明确")
    if p.get("family"):
        why.append(f"空间家族：{p.get('family_zh')}")
    rows.append({"id": "spatial", "name": "空间组织合理性", "weight": _w(ctx, "spatial", 0.16),
                 "score": _clamp(base), "reason": "；".join(why) or "组织描述不足",
                 "evaluated": True})

    # 4. 美学与偏好 —— 业主指定风格时，符合指定即高分，而不是比较谁更好看
    policy = concept.get("aesthetic_policy") or {}
    checks = (concept.get("palette") or {}).get("checks") or []
    evaluated_checks = [c for c in checks if c.get("evaluated")]
    failed = [c for c in evaluated_checks if not c["ok"]]
    if ctx.style_preference:
        # Compare resolved ids, not display names: 「现代意式极简」→ italian-minimal,
        # while the label reads 「意式极简（Italian Minimal）」 and never matches.
        from .directions import resolve_style_id

        resolved = resolve_style_id(ctx.style_preference)
        matched = bool(resolved) and resolved in (concept.get("style_ids") or [])
        score = 90 if matched else 70
        why = (f"业主指定「{ctx.style_preference}」，本方案保留该方向"
               if matched else
               f"业主指定「{ctx.style_preference}」，本方案采用 {'/'.join(concept.get('style_labels') or [])}，需业主确认")
    else:
        score = 75
        why = "业主未指定风格，按项目类型与预算推荐"
    if failed:
        score -= 15 * len(failed)
        why += f"；配色校核未过 {len(failed)} 项"
    elif not evaluated_checks:
        score -= 5
        why += "；配色缺少数值声明，未能校核"
    rows.append({"id": "aesthetic", "name": "美学与业主偏好", "weight": _w(ctx, "aesthetic", 0.12),
                 "score": _clamp(score), "reason": why, "evaluated": True})

    # 5. 预算适配
    tier = ctx.budget_tier
    if tier:
        penalty = {"economy": 20, "mid": 8, "premium": 0, "luxury": 0}.get(tier, 0)
        cost = str(concept.get("cost_impact") or "")
        if "增量" in cost:
            penalty += 6
        rows.append({"id": "budget", "name": "预算适配", "weight": _w(ctx, "budget", 0.10),
                     "score": _clamp(100 - penalty * 2),
                     "reason": f"预算档位 {tier}；{cost[:40]}", "evaluated": True})
    else:
        rows.append({"id": "budget", "name": "预算适配", "weight": _w(ctx, "budget", 0.10), "score": None,
                     "reason": "预算未定，本项不评（不猜测档位）", "evaluated": False})

    # 6. 施工与维护
    risks = concept.get("technical_risks") or []
    score = 92 - 9 * len(risks)
    rows.append({"id": "buildability", "name": "施工与维护",
                 "weight": _w(ctx, "buildability", 0.10),
                 "score": _clamp(score),
                 "reason": f"{len(risks)} 项技术风险；{str(concept.get('maintenance_impact') or '')[:40]}",
                 "evaluated": True})

    # 7. 后续深化
    if p.get("plan_strategy"):
        rows.append({"id": "downstream", "name": "后续深化可行性", "weight": _w(ctx, "downstream", 0.08),
                     "score": 90,
                     "reason": f"S3 现有平面算法支持策略 `{p['plan_strategy']}`",
                     "evaluated": True})
    else:
        rows.append({"id": "downstream", "name": "后续深化可行性", "weight": _w(ctx, "downstream", 0.08),
                     "score": 55,
                     "reason": "S3 现有算法不支持该原型，需要专用深化或调整；本轮不假装可自动落地",
                     "evaluated": True})

    # 8. 专业维度 —— 只评"在范围内且有依据"的；没有依据就记不评，
    #    绝不把"缺结构资料"折成一个中等分数混进总分。
    DIRS = [("structure", "结构可行性", 0.0),
            ("mep", "机电协调难度", 0.0),
            ("landscape", "景观与生态", 0.0),
            ("planning", "规划适应性", 0.0)]
    dirs = concept.get("disciplines") or {}
    for did, name, weight in DIRS:
        d = dirs.get(did)
        if not d:
            continue                    # 不在范围：不加这一维，也不给 0 分
        if d.get("status") != "proposed":
            rows.append({
                "id": f"disc-{did}", "name": name, "weight": weight,
                "score": None, "evaluated": False,
                "reason": (f"{d['label']}资料不足（{d.get('evidence') or '未提供'}）："
                           "本项不评——缺依据时给分等于编"),
            })
            continue
        # 有依据才评：要求越多，说明这套概念对专业的依赖越重
        demand = len(d.get("demanded_by") or [])
        if did == "structure":
            score = 88 - 7 * demand
            why = (f"概念向结构提出 {demand} 项要求，均可由常规做法满足" if demand
                   else "概念不改变结构体系，落地风险低")
        elif did == "mep":
            score = 88 - 6 * demand
            why = (f"需配套 {demand} 类机电条件" if demand
                   else "不新增机电系统")
        elif did == "landscape":
            score = 84 if demand else 90
            why = ("室外参与空间组织，需处理防水排水与灌溉" if demand
                   else "室外不参与空间组织")
        else:
            score = 80
            why = "需按当地规划条件核对，系统不出法定结论"
        rows.append({"id": f"disc-{did}", "name": name, "weight": weight,
                     "score": _clamp(score), "reason": why, "evaluated": True})

    # 硬性前提：概念自己要求某专业回答，而该专业还是"待补资料"。
    # 这不是扣几分的问题——它意味着这套概念此刻**不能被当作已成立的方案**推荐。
    hard = [{"discipline": did, "label": (dirs.get(did) or {}).get("label", did),
             "needs": (dirs.get(did) or {}).get("open_questions") or []}
            for did, _n, _w in DIRS
            if (dirs.get(did) or {}).get("status") == "requires_input"
            and (dirs.get(did) or {}).get("demanded_by")]

    # ---- 第一层：硬门槛。美学分不能抵消 --------------------------------
    gate = _hard_gate(ctx, concept)

    evaluated = [r for r in rows if r.get("evaluated")]
    wsum = sum(r["weight"] for r in evaluated)
    total = (sum(float(r["score"]) * r["weight"] for r in evaluated) / wsum) if wsum else 0.0
    return {
        "concept_id": concept["concept_id"],
        "rows": rows,
        "weighted": round(total, 1),
        "coverage": round(wsum, 2),
        "unevaluated": [r["id"] for r in rows if not r.get("evaluated")],
        "hard_flags": hard,
        "hard_gate": gate,
        "rankable": not gate["failed"],
        "note": ("加权分只在已评估项上归一；覆盖不足 0.8 时该分数不足以拉开差距，"
                 "须结合文字判断。hard_flags 非空时，该方案不能作为无条件推荐。"
                 "hard_gate.failed 为真时，无论加权分多高都不得排在可行方案之前。"),
    }


def compare(concept_set: Dict[str, Any], ctx: Any) -> Dict[str, Any]:
    total_ops = len(ctx.opportunities)
    evals = [evaluate(c, ctx, total_ops) for c in concept_set["concepts"]]
    # 排序先按"是否过硬门槛"，再按加权分：
    # 一个装不下的方案，不应因为造型好就排在能装下的方案之前。
    order = sorted(evals, key=lambda e: (0 if e.get("rankable", True) else 1,
                                         -e["weighted"]))
    return {
        "project_id": ctx.project_id,
        "revision": ctx.revision,
        "evaluations": evals,
        "ranking": [e["concept_id"] for e in order],
        "criteria": [dict(c) for c in CRITERIA],
        "lead": {
            "mode": str(getattr(ctx, "lead", {}).get("mode", "")),
            "discipline": str(getattr(ctx, "lead", {}).get("project_lead_discipline", "")),
            "label": str(getattr(ctx, "lead", {}).get("lead_label", "")),
            "weights": _lead_weights(ctx),
        },
        "recommendation": recommend(concept_set, evals, ctx),
        "note": "评分用于呈现取舍，不用于替代业主决策；未评估项不按中间分计入。"
                "排序先过硬门槛，再比加权分。",
    }


def recommend(concept_set: Dict[str, Any], evals: Sequence[Dict[str, Any]],
              ctx: Any) -> Dict[str, Any]:
    """The lead designer's opinion — with the reasoning a client can argue with."""
    if not evals:
        return {"concept_id": "", "rationale": "无可比较方案", "why_not": [], "verify": []}
    by_id = {c["concept_id"]: c for c in concept_set["concepts"]}
    # 先排除过不了硬门槛的方案；全都过不了才退回按分数选，并明确说明原因
    pool = [e for e in evals if e.get("rankable", True)] or list(evals)
    top = max(pool, key=lambda e: (e["weighted"], e["coverage"]))
    chosen = by_id[top["concept_id"]]
    others = [e for e in evals if e["concept_id"] != top["concept_id"]]
    blocked_by_gate = [e["concept_id"] for e in evals if not e.get("rankable", True)]

    why: List[str] = []
    strong = [r for r in top["rows"] if r.get("evaluated") and r["score"] >= 80]
    for r in strong[:3]:
        why.append(f"{r['name']} {r['score']}：{r['reason']}")
    if not why:
        why.append("各项均无明显优势，推荐基于空间组织与深化可行性")
    if ctx.style_preference:
        why.append(f"在业主指定的「{ctx.style_preference}」范围内表达，未替换方向")

    why_not: List[Dict[str, str]] = []
    for e in others:
        c = by_id[e["concept_id"]]
        weak = sorted([r for r in e["rows"] if r.get("evaluated")],
                      key=lambda r: r["score"])[:1]
        reason = (f"{weak[0]['name']} 较弱（{weak[0]['score']}）：{weak[0]['reason']}"
                  if weak else "差异主要在取向，不在高低")
        why_not.append({
            "concept_id": e["concept_id"],
            "concept_name": c["concept_name"],
            "reason": reason,
            "still_valid_when": _still_valid(c, ctx),
        })

    verify: List[str] = []
    if blocked_by_gate:
        verify.append(
            "以下方案未通过硬门槛，不参与推荐排序：" + "、".join(blocked_by_gate) +
            "（安全 / 规范 / 已核实的容量或物理限制不成立，美学分不能抵消）")
    if not top.get("rankable", True):
        verify.append(
            "**本轮所有方案都没有通过硬门槛**：请先解决上面列出的硬问题，"
            "否则这不是选哪个方案的问题，是这个项目现在不成立")
    # 这套概念自己向某专业提了要求，而该专业还没有资料：必须先补，
    # 不能靠其他维度的高分把它平均成"可以推进"。
    for f in (top.get("hard_flags") or []):
        needs = "、".join(str(x) for x in (f.get("needs") or [])[:2])
        verify.append(
            f"**{f['label']}是这套概念成立的前提**，目前资料不足"
            + (f"（需先明确：{needs}）" if needs else "")
            + "：补齐前该方案只能作为方向，不能当作已成立方案推进")
    if ctx.precision != "authoritative_capable":
        verify.append("尺寸与净宽：进 S3 前需图纸或实测核实，当前概念未按精确尺寸校核")
    for u in ctx.uncertainty[:3]:
        verify.append(f"{u['id']}：{u['statement']}（影响 {','.join(u.get('blocks_stages') or [])}）")
    if not (chosen.get("spatial_prototype") or {}).get("plan_strategy"):
        verify.append("该原型的平面落地方式需在 S3 与主创确认，现有算法不直接支持")
    if not verify:
        verify.append("暂无需前置核实项；S3 仍需在统一模型中复核")

    return {
        "concept_id": top["concept_id"],
        "concept_name": chosen["concept_name"],
        "weighted": top["weighted"],
        "coverage": top["coverage"],
        "rationale": why,
        "why_not": why_not,
        "verify_before_s3": verify,
        "disclaimer": "推荐为总设计师专业意见，最终选择由业主决定；本系统不代为决策。",
    }


def _still_valid(c: Dict[str, Any], ctx: Any) -> str:
    p = c.get("spatial_prototype") or {}
    if p.get("family") in ("courtyard", "hall"):
        return "业主更看重空间体验、且场地或层高条件允许时，仍应重新评估该方向"
    if p.get("family") == "layered":
        return "业主更看重隐私与到达仪式感时，该方向的取舍更值得"
    return "业主更看重使用效率或预算控制时，该方向仍有竞争力"


def markdown(result: Dict[str, Any], concept_set: Dict[str, Any]) -> str:
    by_id = {c["concept_id"]: c for c in concept_set["concepts"]}
    names = [r["name"] for r in result["criteria"]]
    lines = [
        "# 方案比较与推荐（S2）",
        "",
        f"项目：{result.get('project_id', '')}　模型修订 r{result.get('revision', '')}"
        f"　阶段 S2",
        "",
        "| 概念 | " + " | ".join(names) + " | 加权 |",
        "|---|" + "---|" * len(names) + "---|",
    ]
    for e in result["evaluations"]:
        cells = []
        for r in e["rows"]:
            cells.append(str(r["score"]) if r.get("evaluated") else "未评估")
        lines.append(f"| {e['concept_id']} {by_id[e['concept_id']]['concept_name']} | "
                     + " | ".join(cells) + f" | **{e['weighted']}** |")

    lines += ["", "## 逐项依据", ""]
    for e in result["evaluations"]:
        lines += [f"### {e['concept_id']} · {by_id[e['concept_id']]['concept_name']}（{e['weighted']}）", "",
                  "| 维度 | 分数 | 依据 |", "|---|---|---|"]
        for r in e["rows"]:
            lines.append(f"| {r['name']} | {r['score'] if r.get('evaluated') else '未评估'} | {r['reason']} |")
        if e["unevaluated"]:
            lines.append(f"\n未评估项：{'、'.join(e['unevaluated'])}（资料不足，不折算为中间分）")
        lines.append("")

    rec = result["recommendation"]
    lines += ["## 总设计师推荐", "",
              f"**推荐：{rec['concept_id']} {rec.get('concept_name', '')}**（加权 {rec.get('weighted')}，"
              f"覆盖 {rec.get('coverage')}）", ""]
    lines += [f"- {w}" for w in rec["rationale"]]
    lines += ["", "**为什么不优先另外两套**", ""]
    for w in rec["why_not"]:
        lines += [f"- {w['concept_id']} {w['concept_name']}：{w['reason']}",
                  f"  - 但仍然成立的情形：{w['still_valid_when']}"]
    lines += ["", "**进 S3 之前要核实什么**", ""]
    lines += [f"- {v}" for v in rec["verify_before_s3"]]
    lines += ["", f"> {rec['disclaimer']}", ""]
    return "\n".join(lines)


__all__ = ["CRITERIA", "evaluate", "compare", "recommend", "markdown"]
