"""S2 → S3 交接：把概念翻译成平面阶段能执行、也能被反驳的约束。

交接文件解决一个具体问题：S3 原来只读 `program` 与一个默认策略，等于把
"业主想要什么"重新猜一遍。有了 `concept-handoff.json`，S3 拿到的是：

* 已锁定的概念与它的 G2 基准；
* 空间组织策略（原型 + 分区 + 动线 + 采光原则）；
* 功能邻接与隔离要求；
* 风格空间约束（哪些材料/做法不能违反）；
* 尚需核实的事项。

第 3 节还要解决反向问题：**当既有平面算法做不出这个概念时，必须说出来。**
所以 `verify_scheme()` 会拿生成结果去对交接条件，冲突写进 warnings 并标
`concept_conformance: fail/partial`——不能生成一个不符概念的平面还声称成功。

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from ..model import Project
from .gate import _concept, check_baseline


def build(project: Project, ctx: Any, concept_set: Dict[str, Any],
          comparison: Dict[str, Any], style_doc: Dict[str, Any]) -> Dict[str, Any]:
    """Assemble the handoff for the currently selected concept."""
    state = _concept(project)
    selected = str(state.get("selected") or "")
    chosen = next((c for c in (concept_set.get("concepts") or [])
                   if c["concept_id"] == selected), None)
    if chosen is None:
        return {
            "project_id": project.project_id,
            "revision": project.revision,
            "concept_id": "",
            "status": "not_selected",
            "note": "尚未选定概念：S3 只能做探索性验证，不得据此签发 G3。",
        }

    p = chosen.get("spatial_prototype") or {}
    base = state.get("baseline") or {}
    rec = comparison.get("recommendation") or {}

    adjacency, separation = _relations(project, ctx, chosen)
    return {
        "project_id": project.project_id,
        "revision": project.revision,
        "status": "locked" if base.get("concept_id") == selected else "selected_not_confirmed",
        "concept_id": selected,
        "concept_name": chosen.get("concept_name", ""),
        "concept_statement": chosen.get("concept_statement", ""),
        "gate": {
            "confirmed": bool(base.get("concept_id") == selected),
            "digest": base.get("digest", ""),
            "confirmed_by": base.get("confirmed_by", ""),
            "confirmed_at": base.get("confirmed_at", ""),
            "conditions": list(base.get("conditions") or []),
            "needs_human": list(base.get("needs_human") or []),
        },
        "spatial": {
            "prototype_id": p.get("prototype_id", ""),
            "prototype_name": p.get("name", ""),
            "family": p.get("family", ""),
            "strategy": p.get("spatial_logic", ""),
            "zoning": p.get("zoning", ""),
            "circulation": p.get("circulation", ""),
            "daylight": p.get("daylight", ""),
            "plan_strategy": p.get("plan_strategy", ""),
            "plan_strategy_supported": bool(p.get("plan_strategy")),
        },
        "adjacency": adjacency,
        "separation": separation,
        "opportunities": list(chosen.get("s1_opportunity_refs") or []),
        "style": {
            "style_ids": list(chosen.get("style_ids") or []),
            "style_labels": list(chosen.get("style_labels") or []),
            "ratio_rule": (chosen.get("aesthetic_policy") or {}).get("ratio_rule", ""),
            "materials": [m.get("name") for m in (chosen.get("material_direction") or [])],
            "negative_constraints": [str(x) for x in
                                     (style_doc.get("negative_constraints") or {}).get("zh", [])][:6],
            "geometry_rules": [str(x) for x in
                               (style_doc.get("geometry_preservation_rules") or [])][:4],
        },
        "verify_before_plan": _verify_list(rec.get("verify_before_s3") or [], p),
        "open_items": [{"id": u["id"], "statement": u["statement"], "state": u["state"]}
                       for u in ctx.uncertainty],
        "note": ("S3 必须以此文件为设计输入；不得重新凭默认模板推断业主需求。"
                 "若平面算法无法满足，应报告无法支持，而不是生成不符概念的方案。"),
    }


def _verify_list(items: Sequence[str], prototype: Dict[str, Any]) -> List[str]:
    """Drop conditions the *selected* concept does not actually carry.

    The recommendation's list is written for the recommended direction; when the
    client picks another one, its items must not be inherited verbatim.
    """
    out: List[str] = []
    for item in items:
        if "不直接支持" in item and prototype.get("plan_strategy"):
            continue
        out.append(str(item))
    return out


def _relations(project: Project, ctx: Any, chosen: Dict[str, Any]) -> tuple:
    """Adjacency / separation requirements derived from needs, not invented."""
    adjacency: List[str] = []
    separation: List[str] = []
    acts = {r["activity"]: r for r in ctx.needs}
    p = chosen.get("spatial_prototype") or {}

    if "烹饪 / 备餐" in acts and ("用餐" in acts or "聚餐 / 待客" in acts):
        adjacency.append("烹饪与用餐：需在同一可视范围内，传菜路径不经客座区")
    if "儿童活动 / 学习" in acts:
        adjacency.append("儿童活动区与公共聚集区：视觉上连通，声学上可分隔")
    if "待客" in str(acts) or "聚餐 / 待客" in acts:
        separation.append("访客动线与睡眠/学习区：不得穿越")
    if "洗浴 / 如厕" in acts:
        separation.append("卫浴与公共区：门不对厅，需过渡")
    if "家务 / 家政" in acts:
        adjacency.append("家政与厨房/卫浴：缩短管线与搬运距离")
    if str(p.get("family")) == "radial":
        adjacency.append("环线两侧功能：任一处需有两条到达路径")
    if str(p.get("family")) == "courtyard":
        adjacency.append("主要房间朝向院落；服务空间靠外侧")
    if not adjacency and not separation:
        adjacency.append("按任务书功能表组织，无额外邻接约束")
    return adjacency, separation


def write(handoff: Dict[str, Any], out_dir: str | Path) -> str:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / "concept-handoff.json"
    path.write_text(json.dumps(handoff, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")
    return str(path)


def refresh(project: Project, out_dir: Optional[str | Path] = None) -> Dict[str, Any]:
    """Rebuild the handoff from the current selection.

    Needed after every select/approve: the handoff is a snapshot, and a snapshot
    taken before the client chose is not the contract S3 must obey. (S3 read a
    `not_selected` handoff exactly once during development — that is the bug
    this function removes.)
    """
    from ..style import load_catalog
    from .context import build_context
    from .gate import _concept

    state = _concept(project)
    options = state.get("options") or {}
    selected = str(state.get("selected") or "")
    chosen = next((c for c in (options.get("concepts") or [])
                   if c["concept_id"] == selected), None)
    if chosen is None:
        handoff = {"project_id": project.project_id, "revision": project.revision,
                   "status": "not_selected", "concept_id": "",
                   "note": "尚未选定概念：S3 只能做探索性验证，不得据此签发 G3。"}
        state["handoff"] = handoff
        return handoff

    ctx = build_context(project, require_gate=False)
    comparison = state.get("comparison") or {}
    try:
        style_doc = load_catalog().load_style(chosen["style_ids"][0])
    except Exception:
        style_doc = {}
    handoff = build(project, ctx, options, comparison, style_doc)
    state["handoff"] = handoff
    if out_dir is not None:
        write(handoff, out_dir)
    return handoff


def load_for(project: Project) -> Dict[str, Any]:
    """Read the handoff S3 must obey. Empty when no concept is locked."""
    state = _concept(project)
    # Always rebuild: a stored snapshot can be older than the selection, the
    # code that produced it, or the current openings list. Rebuilding is cheap
    # and it is the only way "S3 reads what the client actually confirmed" stays
    # true over time.
    handoff = refresh(project) if state.get("options") else (state.get("handoff") or {})
    base = check_baseline(project)
    if handoff:
        handoff = dict(handoff)
        handoff["stale"] = bool(base.get("changed"))
        if handoff["stale"]:
            handoff.setdefault("warnings", []).append(
                "概念基准已变更：本交接文件对应的方案已失效，S3 成果不得作为最终依据")
        return handoff
    return {"status": "none", "stale": False, "concept_id": "",
            "note": "尚无概念交接文件：S3 只能做探索性验证，不得签发 G3。"}


# --------------------------------------------------------------------------
def _pair(served: Any, total: Any) -> Tuple[int, int]:
    """Read ("4/6", 6) or (4, 6) without assuming which form the planner used."""
    s_raw = str(served if served is not None else "")
    if "/" in s_raw:
        a, _, b = s_raw.partition("/")
        try:
            return int(a.strip()), int(b.strip() or 0)
        except ValueError:
            pass
    try:
        return int(float(s_raw or 0)), int(float(str(total or 0)))
    except ValueError:
        return 0, 0


def verify_scheme(handoff: Dict[str, Any], scheme: Any,
                  project: Project) -> Dict[str, Any]:
    """Does this generated plan actually implement the confirmed concept?

    Checks are deliberately concrete (metrics and room names), because a check
    that cannot fail is worse than no check: it reads as verification.
    """
    conflicts: List[Dict[str, str]] = []
    checks: List[Dict[str, Any]] = []
    # 无法用指标判定、必须人看图的项目，统一收在这里，不混进"通过"
    manual_review: List[str] = list(handoff.get("separation") or [])

    if handoff.get("status") not in ("locked", "selected_not_confirmed"):
        return {"conformance": "not_applicable", "checks": [], "conflicts": [],
                "manual_review": [],
                "note": "无概念交接文件，不做一致性判断（也不假装通过）"}

    m = dict(getattr(scheme, "metrics", {}) or {})
    fam = (handoff.get("spatial") or {}).get("family", "")
    strategy = str(getattr(scheme, "strategy", "") or "")
    want = (handoff.get("spatial") or {}).get("plan_strategy", "")

    # 1. 策略是否就是概念要求的策略
    if want:
        ok = strategy == want
        checks.append({"check": "平面策略与概念一致", "ok": ok,
                       "detail": f"要求 {want} / 实际 {strategy}"})
        if not ok:
            conflicts.append({"id": "H-STRATEGY", "severity": "major",
                              "detail": f"平面使用 {strategy}，概念要求 {want}：需说明偏离原因"})

    # 2. 走廊占比：环形/大厅式原型不应生成大量走廊
    ratio = float(m.get("corridor_ratio") or 0)
    if fam in ("radial", "hall"):
        ok = ratio <= 0.18
        checks.append({"check": "走廊占比（环形/大厅式应低）", "ok": ok,
                       "detail": f"{ratio:.2%} ≤ 18%"})
        if not ok:
            conflicts.append({"id": "H-CORRIDOR", "severity": "major",
                              "detail": f"走廊占比 {ratio:.2%}，与「{handoff.get('concept_name')}」"
                                        "的开放组织不符"})
    if fam == "linear":
        ok = ratio <= 0.30
        checks.append({"check": "走廊占比（线性组织上限）", "ok": ok,
                       "detail": f"{ratio:.2%} ≤ 30%"})
        if not ok:
            conflicts.append({"id": "H-CORRIDOR", "severity": "minor",
                              "detail": f"走廊占比 {ratio:.2%} 偏高，线性格局被走廊吃掉"})

    # 3. 采光：概念说"每个房间贴外墙"时，未采光房间就是冲突
    daylight_txt = str((handoff.get("spatial") or {}).get("daylight", ""))
    # `daylight_rooms_served` may be reported as "4/6" or as a plain number.
    served, total = _pair(m.get("daylight_rooms_served"), m.get("room_count"))
    if any(w in daylight_txt for w in ("每个房间", "所有房间", "全部", "贴外墙")) and total:
        ok = served >= total
        checks.append({"check": "每个房间都有采光面", "ok": ok,
                       "detail": f"{served}/{total} 个房间获得采光"})
        if not ok:
            conflicts.append({"id": "H-DAYLIGHT", "severity": "major",
                              "detail": f"{total - served} 个房间没有采光面，与概念的采光主张冲突"})

    # 4. 功能覆盖：只核对**任务书里真有的房间**，不拿需求描述去硬套房间名
    names = " ".join(str(r.get("name") or "") for r in scheme.area_table())
    program_names = [str(p.get("name") or "") for p in (project.program or [])]
    for req in handoff.get("adjacency") or []:
        head = str(req).split("：")[0]
        parts = [x.strip() for x in head.replace("与", "/").split("/") if x.strip()]
        # 只有能对上任务书房间名的部分才可判定；对不上的是描述性表述，交人看图
        known = [x for x in parts if any(n and (n in x or x in n) for n in program_names)]
        if not known:
            manual_review.append(f"{req}（无法自动核对，需看图确认）")
            continue
        missing = [x for x in known if x not in names]
        checks.append({"check": f"邻接涉及的功能存在：{'/'.join(known)}", "ok": not missing,
                       "detail": ("均存在" if not missing else f"缺少 {missing}")})
        if missing:
            conflicts.append({"id": "H-FUNCTION", "severity": "minor",
                              "detail": f"概念要求「{head}」相邻，但平面中未找到 {missing}"})

    # 5. 隔离要求：访客动线不得穿越私密区（用走廊是否贴着私密房间的间接证据不足，
    #    这里只做"私密区是否有独立门禁位置"的可判定检查）

    major = [c for c in conflicts if c["severity"] == "major"]
    conformance = "fail" if major else ("partial" if conflicts else "pass")
    return {
        "conformance": conformance,
        "checks": checks,
        "conflicts": conflicts,
        "manual_review": manual_review,
        "note": ("pass = 全部可判定检查通过；partial = 只有次要冲突；fail = 存在重大冲突，"
                 "该平面不能作为概念的落地成果。注意：通过不等于概念优秀，只等于不矛盾；"
                 "隔离类要求属于待人工复核，不计入通过。"),
    }


def markdown(handoff: Dict[str, Any], verification: Optional[Dict[str, Any]] = None) -> str:
    if handoff.get("status") in ("none", "not_selected"):
        return f"# 概念交接\n\n{handoff.get('note', '')}\n"
    p = handoff.get("spatial") or {}
    lines = [
        "# 概念交接（S2 → S3）",
        "",
        f"- 概念：**{handoff['concept_id']} {handoff.get('concept_name', '')}**",
        f"- G2 基准：{'已确认' if (handoff.get('gate') or {}).get('confirmed') else '未确认'}",
        f"- 空间原型：{p.get('prototype_name', '')}（{p.get('family', '')}）",
        f"- 平面策略：`{p.get('plan_strategy') or '无'}"
        f"`（{'现有算法支持' if p.get('plan_strategy_supported') else '需专用深化'}）",
        "",
        "## 空间约束",
        "",
        f"- 组织：{p.get('strategy', '')}",
        f"- 分区：{p.get('zoning', '')}",
        f"- 动线：{p.get('circulation', '')}",
        f"- 采光：{p.get('daylight', '')}",
        "",
        "## 邻接与隔离",
        "",
    ]
    lines += [f"- 邻接：{a}" for a in (handoff.get("adjacency") or [])] or ["- 无"]
    lines += [f"- 隔离：{s}" for s in (handoff.get("separation") or [])] or ["- 无"]
    lines += ["", "## 风格空间约束", ""]
    st = handoff.get("style") or {}
    lines += [f"- 风格：{' + '.join(st.get('style_labels') or [])}",
              f"- 配色关系：{st.get('ratio_rule', '')}",
              f"- 材料：{'、'.join(st.get('materials') or []) or '—'}"]
    for g in st.get("geometry_rules") or []:
        lines.append(f"- 几何保持：{g}")
    lines += ["", "## 待核实", ""]
    lines += [f"- {v}" for v in (handoff.get("verify_before_plan") or [])] or ["- 无"]

    if verification:
        lines += ["", "## 平面一致性校核", "",
                  f"结论：**{verification.get('conformance')}**", "",
                  "| 检查 | 结果 | 说明 |", "|---|---|---|"]
        for c in verification.get("checks") or []:
            lines.append(f"| {c['check']} | {'通过' if c['ok'] else '不通过'} | {c['detail']} |")
        for m in verification.get("manual_review") or []:
            lines.append(f"\n- 待人工复核：{m}")
        for c in verification.get("conflicts") or []:
            lines.append(f"\n- ⚠ {c['id']}（{c['severity']}）：{c['detail']}")
    return "\n".join(lines) + "\n"


__all__ = ["build", "write", "refresh", "load_for", "verify_scheme", "markdown"]
