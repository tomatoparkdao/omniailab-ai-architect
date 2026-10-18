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
from typing import Any, Dict, List, Optional, Sequence, Tuple

from ..model import Project
from .gate import _concept, check_baseline, concept_digest


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
    # 设计意图与主导专业：G2 落盘后，S3 起一律读这一份
    try:
        from .. import intent as _intent
        from .. import leadership as _lead

        intent = _intent.load(project) or {}
        lead_raw = (project.meta or {}).get("leadership") or {}
        if lead_raw:
            intent["_leadership"] = dict(lead_raw)
    except Exception:                                  # noqa: BLE001
        intent = {}

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
            # 多专业基准：S3 起每个专业按这份对齐，而不是只看风格锁
            "multidisciplinary": dict(base.get("multidisciplinary") or {}),
            # 主导专业与设计意图：S3–S8 必须优先保留这份基准，
            # 调整可以，但要出具影响说明并走变更审批。
            "leadership": dict(intent.get("_leadership") or {}),
            "design_intent": {
                "design_intent_id": intent.get("design_intent_id", ""),
                "lead_discipline": intent.get("lead_discipline", ""),
                "lead_label": intent.get("lead_label", ""),
                "features": list(intent.get("signature_features") or []),
                "acceptable_adjustments": list(intent.get("acceptable_adjustments") or []),
                "technical_dependencies": list(intent.get("technical_dependencies") or []),
            } if intent else {},
        },
        "disciplines": {
            "directions": {
                k: {"goal": v.get("goal", ""), "strategy": v.get("strategy", ""),
                    "status": v.get("status", ""),
                    "deliverables": list(v.get("deliverables") or []),
                    "open_questions": list(v.get("open_questions") or []),
                    "interfaces": list(v.get("interfaces") or [])}
                for k, v in (chosen.get("disciplines") or {}).items()
            },
            "note": ("各专业方向都属于同一个 concept_id；"
                     "status=requires_input 的专业只能作为方向，不是结论。"),
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
                "manual_review": [], "auto_pass": False, "fully_verified": False,
                "manual_review_required": 0,
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
    else:
        # 概念要的原型，现有生成器根本没有对应策略：这不是"跳过检查"，
        # 而是"这个平面不可能实现该概念"，必须判失败，不能默认通过。
        checks.append({"check": "概念所需平面策略已实现", "ok": False,
                       "detail": "该原型需专用深化，现有生成器只能出近似策略"})
        conflicts.append({
            "id": "H-STRATEGY-UNSUPPORTED", "severity": "major",
            "detail": f"「{handoff.get('concept_name')}」的空间原型没有对应的平面策略，"
                      "本次平面是用通用策略生成的近似结果，不能视为该概念的落地",
        })

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
        # 无窗的卫浴、储藏、家务、走廊不算"居住空间没采光"——这是常识，
        # 不是妥协。把它们算进冲突，会让每个合理解法都被判成重大冲突：
        # 一条服务脊本来就是靠"把湿区压进芯里"换取两侧完整开间的。
        # 真正该拦的是**卧室、客厅这类有人长时间停留的房间**没有采光面。
        wet = sum(1 for r in (scheme.area_table() or [])
                  if any(w in str(r.get("name") or "")
                         for w in ("卫", "浴", "厕", "厨", "储藏", "储物", "衣帽",
                                   "家务", "设备", "走廊", "交通", "玄关", "楼梯")))
        allow = min(wet, max(0, total - served))
        ok = served >= total or allow >= (total - served)
        checks.append({"check": "每个居住房间都有采光面", "ok": ok,
                       "detail": f"{served}/{total} 个房间获得采光"
                                 + (f"（其中 {total - served} 间为无窗湿区/储藏，已豁免）"
                                    if allow else "")})
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

    # 4b. 办公容量：这张平面自己能不能坐得下这些人
    #     G1 的书面接受不等于平面成立；这里按实际开放办公面积重算一次。
    try:
        from ..finishes import project_profile
        from ..intake.feasibility import _headcount

        if project_profile(project) == "office":
            head = _headcount(project)
            # 按整套可用面积算人均（含会议/接待/交通），不是只算工位区
            usable = sum(float(sp.area_m2 or 0) for sp in scheme.spaces
                         if sp.use != "envelope")
            if head and usable:
                per = usable / head
                ok = per >= 4.0
                checks.append({"check": "人均可用面积", "ok": ok,
                               "detail": f"{usable:.1f}㎡ / {head} 人 = {per:.1f}㎡/人"})
                if not ok:
                    conflicts.append({
                        "id": "H-CAPACITY", "severity": "major",
                        "detail": (f"人均仅 {per:.1f}㎡：这一版平面装不下 {head} 人，"
                                   "须减少常驻人数或改轮用工位"),
                    })
    except Exception:
        pass

    # 5. 隔离要求：访客动线不得穿越私密区（用走廊是否贴着私密房间的间接证据不足，
    #    这里只做"私密区是否有独立门禁位置"的可判定检查）

    major = [c for c in conflicts if c["severity"] == "major"]
    conformance = "fail" if major else ("partial" if conflicts else "pass")
    auto_pass = conformance == "pass"
    return {
        "conformance": conformance,
        "auto_pass": auto_pass,
        # 只有"自动检查全过、且没有待人工判断项"才算完全核实。
        # 隔离类要求永远无法靠指标断言，所以它们使 fully_verified 为 False，
        # 而不是被悄悄算成"通过"。
        "fully_verified": bool(auto_pass and not manual_review),
        "manual_review_required": len(manual_review),
        "checks": checks,
        "conflicts": conflicts,
        "manual_review": manual_review,
        "note": ("pass = 可自动判定的检查全部通过；partial = 只有次要冲突；"
                 "fail = 存在重大冲突，该平面不能作为概念的落地成果。"
                 "注意：pass 不等于概念优秀，也不等于全部核实——"
                 "隔离类要求属于待人工复核，不计入通过；"
                 "fully_verified 才是「没有任何待人工判断项」。"),
    }


# --------------------------------------------------------------------------
# G3：平面方案门禁
# --------------------------------------------------------------------------
def plan_record(project: Project) -> Dict[str, Any]:
    """The S3 run's own record of what it produced and how it compared."""
    state = _concept(project)
    rec = state.get("plan")
    return dict(rec) if isinstance(rec, dict) else {}


def store_plan_record(project: Project, record: Dict[str, Any]) -> Dict[str, Any]:
    state = _concept(project)
    state["plan"] = dict(record)
    return state["plan"]


def assess_plan_gate(project: Project) -> Dict[str, Any]:
    """Can G3 be *formally* issued? (Exploration is always allowed.)

    The distinction matters: S3 may run without a confirmed concept — that is a
    legitimate exploratory study. What it may not do is turn that study into a
    signed gate. Formal issuance needs four things at once:

    1. a G2 concept baseline that still matches the live concept;
    2. an S3 record produced against *that* baseline, on the current revision;
    3. no major conformance conflict;
    4. a plan strategy that actually implements the selected prototype.
    """
    state = _concept(project)
    base = check_baseline(project)
    handoff = load_for(project)
    rec = plan_record(project)

    blockers: List[Dict[str, str]] = []
    conditions: List[Dict[str, str]] = []
    manual_review: List[str] = []

    # 任务书基准变了，概念与平面都失去依据 —— G3 不能只盯概念那一个 digest
    from ..intake.gate import check_baseline as check_brief

    brief = check_brief(project)
    brief_stale = bool(brief.get("requires_change_analysis"))

    if handoff.get("status") != "locked":
        blockers.append({
            "id": "G3-NO-CONCEPT-BASELINE",
            "text": "没有已确认的 G2 概念基准：本轮平面只是探索性验证，不能签发正式 G3",
        })
    elif handoff.get("stale") or base.get("changed") or brief_stale:
        blockers.append({
            "id": "G3-STALE-BASELINE",
            "text": "概念基准在平面生成之后发生了变更：S3 成果已失效，须重做平面后重新提交 G3"
                    if not brief_stale else
                    f"任务书基准已变更（{brief.get('change_kind') or '需求修改'}）："
                    "概念与平面都须重做，本平面不能签发",
        })

    if not rec:
        blockers.append({
            "id": "G3-NO-PLAN-RECORD",
            "text": "未找到本轮的平面方案记录：先运行 S3 生成平面方案",
        })
    else:
        if int(rec.get("revision") or -1) != int(project.revision):
            blockers.append({
                "id": "G3-PLAN-STALE",
                "text": f"平面记录是 r{rec.get('revision')} 的，当前模型是 "
                        f"r{project.revision}：须在当前修订下重出平面",
            })
        if base.get("has_baseline") and rec.get("concept_digest") \
                and rec.get("concept_digest") != base.get("baseline_digest"):
            blockers.append({
                "id": "G3-STALE-BASELINE",
                "text": "平面所依据的概念基准与当前基准不一致：该平面对应的不是已签的概念",
            })
        if rec.get("conformance") == "fail":
            detail = "；".join(
                f"{c.get('id')} {c.get('detail', '')}"[:90]
                for c in (rec.get("conflicts") or [])) or "存在重大概念冲突"
            blockers.append({
                "id": "G3-CONCEPT-CONFLICT",
                "text": f"平面与所选概念存在重大冲突，不能直接批准 G3：{detail}",
            })
        # 只有"确实有一个已确认概念"时，"平面没实现它"才是独立问题；
        # 完全没有概念的情况已经由 G3-NO-CONCEPT-BASELINE 报过，不重复指责。
        if (rec.get("implements_concept") is False and rec.get("concept_id")
                and any(c["id"] == "H-STRATEGY-UNSUPPORTED"
                        for c in (rec.get("conflicts") or []))):
            blockers.append({
                "id": "G3-PROTOTYPE-UNSUPPORTED",
                "text": "所选概念的空间原型没有对应的平面策略：本轮平面是通用策略的近似结果，"
                        "不能声称为该概念的实现；需换支持的方向，或由主创另行深化",
            })
        manual_review = list(rec.get("manual_review") or [])
        for c in (rec.get("conditions") or []):
            conditions.append({"id": str(c.get("id") or "G3-COND"), "text": str(c.get("text"))})

    if manual_review:
        conditions.append({
            "id": "G3-HUMAN-REVIEW",
            "text": f"{len(manual_review)} 项空间约束无法自动校核，须人工看图确认"
                    "（未计入通过）",
        })

    return {
        "formal_ready": not blockers,
        "blockers": blockers,
        "blocked_reasons": [b["text"] for b in blockers],
        "conditions": conditions,
        "manual_review": manual_review,
        "conformance": rec.get("conformance", "not_applicable"),
        "fully_verified": bool(rec.get("fully_verified")),
        "concept_id": handoff.get("concept_id", "") or str(base.get("concept_id") or ""),
        "concept_name": handoff.get("concept_name", ""),
        "handoff_status": handoff.get("status", "none"),
        "stale": bool(handoff.get("stale") or base.get("changed") or brief_stale),
        "brief_stale": brief_stale,
        "revision": project.revision,
        "planned_revision": rec.get("revision"),
        "baseline_digest": base.get("baseline_digest"),
        "plan_digest": rec.get("concept_digest"),
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
                  f"结论：**{verification.get('conformance')}**"
                  f"（自动检查{'通过' if verification.get('auto_pass') else '未通过'}；"
                  f"完全核实：{'是' if verification.get('fully_verified') else '否'}）", "",
                  "| 检查 | 结果 | 说明 |", "|---|---|---|"]
        for c in verification.get("checks") or []:
            lines.append(f"| {c['check']} | {'通过' if c['ok'] else '不通过'} | {c['detail']} |")
        for m in verification.get("manual_review") or []:
            lines.append(f"\n- 待人工复核（**未计入通过**）：{m}")
        for c in verification.get("conflicts") or []:
            lines.append(f"\n- ⚠ {c['id']}（{c['severity']}）：{c['detail']}")
    return "\n".join(lines) + "\n"


__all__ = ["build", "write", "refresh", "load_for", "verify_scheme", "markdown",
           "assess_plan_gate", "plan_record", "store_plan_record"]
