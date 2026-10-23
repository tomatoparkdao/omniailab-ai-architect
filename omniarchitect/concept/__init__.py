"""S2 概念方案设计引擎 —— 一个引擎，两个适配层。

`run --stage S2` 与 `concept --action generate` 都调 `generate_bundle()`，
所以两者对同一项目产出的成果一致。这一点是硬要求：S1 曾经因为两套实现，
同一个项目能出两份不同的任务书。

引擎的分工：

| 模块 | 负责 |
|---|---|
| `context` | 把 S1 与 G1 基准读成可推理的输入（带出处） |
| `prototypes` | 空间原型库：按项目类型给出真正不同的组织方式 |
| `directions` | 用证据选原型、配视觉语言、生成 2–3 套方向 |
| `palette` | 审美判据的适用性裁量（不再全项目套 60-30-10） |
| `diagrams` | 确定性 SVG 概念图解 |
| `moodboard` | 六格意向板 + 真实色板/材料板 |
| `visual` | OmniAiLab 概念视觉任务（未连接就延后） |
| `compare` | 带证据的评分与总设计师推荐 |
| `gate` | G2 审批、概念基准、风格锁定 |
| `handoff` | `concept-handoff.json` 与 S3 一致性校核 |
| `deck` | 可编辑概念提案 PPTX |

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAIlab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from ..model import Project
from ..style import load_catalog
from . import anim as anim_mod
from . import compare as cmp
from . import curation as cur_mod
from . import deck as deck_mod
from . import diagrams as dia
from . import handoff as handoff_mod
from . import moodboard as mb_mod
from . import palette as pal
from . import proposal as prop_mod
from . import quick as quick_mod
from . import visual as vis
from .context import ConceptContext, assert_ready, build_context
from .directions import ROLE_LABEL, generate_concepts, markdown as options_md, resolve_style_id
from .gate import (
    ACKNOWLEDGEABLE,
    DECISIONS,
    SOURCES,
    GateAssessment,
    Outcome,
    StyleLockConflict,
    approval_summary,
    assess_gate,
    check_baseline,
    concept_digest,
    decide_gate,
    select,
    style_lock_path,
    write_style_lock,
)
from .prototypes import PROTOTYPES, Prototype, THEME_LABEL, for_profile
from .prototypes import count as prototype_count

BUNDLE_FILES = (
    "concept-options.json",
    "concept-options.md",
    "style-recommendation.json",
    "concept-comparison.md",
    "concept-visual-jobs.json",
    "concept-visual-brief.md",
    "concept-presentation.pptx",
    "concept-proposal.html",
    "concept-proposal.pptx",
    "concept-proposal.md",
    "concept-motion.html",
    "design-position.md",
    "g2-approval-summary.md",
    "concept-handoff.json",
)


def _concept_meta(project: Project) -> Dict[str, Any]:
    """The one live dict — never a copy (see the S1 lesson)."""
    meta = project.meta if isinstance(project.meta, dict) else {}
    state = meta.get("concept")
    if not isinstance(state, dict):
        state = {}
        meta["concept"] = state
    project.meta = meta
    return state


def _dump(path: Path, payload: Any) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")
    return str(path)


def generate_bundle(project: Project, out_dir: str | Path, *,
                    limit: int = 3, pre_gate: bool = False,
                    with_deck: bool = True, submit: bool = False,
                    authorize: bool = False, max_cost: Optional[float] = None,
                    project_dir: Optional[str | Path] = None,
                    summary_text: str = "") -> Dict[str, Any]:
    """Produce the whole S2 package. Idempotent: rerunning replaces, never appends."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    ctx = build_context(project, require_gate=not pre_gate)
    if not pre_gate:
        ctx = assert_ready(project)      # raises with a precise reason
    state = _concept_meta(project)

    # 案例在读概念之前取：推敲层要用案例里真实出现的手法做佐证（案例反哺概念），
    # 而不是等方案定完再挂一排链接。
    from .. import research as research_mod

    research_data = research_mod.load(project)

    concept_set = generate_concepts(ctx, limit=limit, pre_gate=pre_gate,
                                    research=research_data)
    if not concept_set["concepts"]:
        state["options"] = concept_set
        return {"count": 0, "files": [], "warnings": concept_set.get("note", ""),
                "precision": ctx.precision, "profile": ctx.profile_label}

    # 视觉规范：有就应用，没有就按参考目录与客户原话补一份。
    # 应用必须在画第一张图之前——图元的纸色、墨色、线宽都是从这里读的。
    from .. import visualref as _vref

    rules = _vref.load(project, project_dir)
    if rules is None:
        refs_path = Path(project_dir) / "references" if project_dir else None
        paths = [refs_path] if refs_path and refs_path.exists() else []
        client_text = "；".join(x for x in (
            getattr(ctx, "feeling", "") or "",
            getattr(ctx, "style_preference", "") or "",
            getattr(ctx, "summary_text", "") or "",
        ) if x)
        rules = _vref.from_refs(
            project, paths, client_text=client_text, lead=getattr(ctx, "lead_id", ""),
            style_labels=[s for c in concept_set["concepts"] for s in c.get("style_labels") or []][:3],
            project_dir=project_dir)
    _vtheme = dict(rules.get("tokens") or {})
    dia.apply_theme(_vtheme)

    catalog = load_catalog()
    style_docs: Dict[str, Dict[str, Any]] = {}
    policies: Dict[str, Dict[str, Any]] = {}
    moodboards: Dict[str, Dict[str, Any]] = {}
    all_diagrams: Dict[str, List[Dict[str, str]]] = {}

    # 专业归属必须在挑案例之前挂上：`references._discipline_keys` 读的是
    # 这套方案覆盖哪些专业，读不到就只剩风格分，专业对口的案例会被判成
    # "不匹配"。之前这段在挑案例之后，于是建筑案例挂不到建筑方案上。
    from .. import disciplines as _disc
    from . import disciplines as _cdisc

    _scope = _disc.ensure(project, profile_id=ctx.profile_id)
    for c in concept_set["concepts"]:
        c["disciplines"] = _cdisc.for_concept(project, _scope, c, ctx)

    # 意向板与提案都要用同一份案例，不在两处各挑一次。
    # 第三方图片永远是"带链接的参考卡"，不进版面（见 concept/references.py）。
    from . import references as ref_mod

    refs = ref_mod.build(concept_set["concepts"], research_data, ctx)
    for c in concept_set["concepts"]:
        c["references"] = refs.get(c["concept_id"], {})

    for c in concept_set["concepts"]:
        primary = c["style_ids"][0]
        if primary not in style_docs:
            style_docs[primary] = catalog.load_style(primary)
        policies[c["concept_id"]] = pal.aesthetic_policy(style_docs[primary], ctx.profile_id)
        all_diagrams[c["concept_id"]] = dia.build(
            c, ctx, ctx.program, ctx.needs, out / "concept-diagrams")
        moodboards[c["concept_id"]] = mb_mod.build(
            c, style_docs[primary], policies[c["concept_id"]], ctx,
            out / "moodboards", references=c["references"])
        c["moodboard"] = {
            "board_svg": moodboards[c["concept_id"]]["board_svg"],
            "board_md": moodboards[c["concept_id"]]["board_md"],
            "image_slots": moodboards[c["concept_id"]]["image_slots"],
            "reference_cards": moodboards[c["concept_id"]]["reference_cards"],
        }
        c["diagrams"] = [{"kind": d["kind"], "path": d["path"]} for d in all_diagrams[c["concept_id"]]]

    comparison = cmp.compare(concept_set, ctx)

    # 视觉任务：编译 + （可选）真实提交
    jobs: List[Dict[str, Any]] = []
    for c in concept_set["concepts"]:
        jobs.extend(vis.build_jobs(c, ctx, project, catalog=catalog))
    visual_res = vis.submit(jobs, project, out, submit=submit, authorize=authorize,
                            max_cost=max_cost, project_dir=project_dir)
    visual_files = vis.write_package(visual_res, concept_set, ctx, out)

    # 落盘：结构化数据 + 人读材料
    options_json = _dump(out / "concept-options.json", {
        k: v for k, v in concept_set.items() if not k.startswith("_")
    })
    style_rec = _dump(out / "style-recommendation.json", {
        "project_id": ctx.project_id,
        "revision": ctx.revision,
        "request": concept_set.get("style_request"),
        "options": concept_set.get("style_options"),
        "preferred_style": ctx.style_preference,
        "preferred_style_resolved": concept_set.get("preferred_style_resolved"),
        "per_concept": [
            {"concept_id": c["concept_id"],
             "style_ids": c["style_ids"],
             "style_labels": c["style_labels"],
             "basis": c["style_basis"],
             "policy_applied": (c.get("aesthetic_policy") or {}).get("applied"),
             "policy_skipped": (c.get("aesthetic_policy") or {}).get("skipped"),
             "ratio_rule": (c.get("aesthetic_policy") or {}).get("ratio_rule")}
            for c in concept_set["concepts"]
        ],
        "note": ("业主已指定风格时保留该方向，只在表达上做差异化；"
                 "未指定时才按评分推荐。概念方向与风格是两件事。"),
    })

    md_path = out / "concept-options.md"
    # 案例已在上面算好（意向板要用同一份），这里只负责排版。
    refs_md = ref_mod.markdown(refs, concept_set["concepts"])

    md_path.write_text("".join([
        f"# 概念方案 · {ctx.name}\n\n",
        f"项目：{ctx.project_id}（{ctx.name}）　模型修订 r{ctx.revision}"
        f"　阶段 S2　生成时间 {concept_set.get('generated_at') or ''}\n\n",
        "\n".join(f"- {line}" for line in ctx.brief_lines()),
        "\n\n", options_md(concept_set, ctx), "\n",
        refs_md, "\n",
    ]), encoding="utf-8")

    cmp_path = out / "concept-comparison.md"
    cmp_path.write_text(cmp.markdown(comparison, concept_set) + "\n", encoding="utf-8")

    # 提案 PPTX（逐条文字版，留档与快速改稿用）
    deck_info: Dict[str, Any] = {}
    if with_deck:
        deck = deck_mod.build(project, ctx, concept_set, comparison,
                              moodboards, all_diagrams, visual_res.to_dict())
        deck_info = deck_mod.write(deck, out)

    # ---- 概念汇报：先给设计，再给数据（8–12 页，图为主）----
    # 与上面的逐条 PPTX 不是两套内容：这份是**给客户看的那一版**，
    # HTML 与 PPTX 从同一份页面模型渲染，改稿只改一处。
    proposal_info: Dict[str, Any] = {}
    motion_info: Dict[str, Any] = {}
    if with_deck:
        rec_id = str((comparison.get("recommendation") or {}).get("concept_id") or "")
        rec_c = next((c for c in concept_set["concepts"]
                      if c["concept_id"] == rec_id), concept_set["concepts"][0])
        try:
            from ..sector import brief as _sector_brief

            _sector = _sector_brief.from_project(project).sector
        except Exception:                   # noqa: BLE001  非行业项目就是普通项目
            _sector = ""
        cur = cur_mod.curate(
            out, ctx=ctx, sector=_sector,
            style_labels=[str(x) for x in (rec_c.get("style_labels") or [])],
            max_items=5)
        judgment = quick_mod.judge(project)
        model = prop_mod.build(
            project, ctx, concept_set, comparison, moodboards, all_diagrams,
            visual_res.to_dict(), curation=cur, judgment=judgment, rules=rules,
            out_dir=out)
        html_path = prop_mod.write_html(model, out,
                                        title=f"{project.name or project.project_id} · 概念汇报")
        pptx_info = prop_mod.write_pptx(model, out,
                                        title=f"{project.name or project.project_id} · 概念汇报")
        md_path2 = prop_mod.write_markdown(model, out)
        # 动画按专业推：没有演变逻辑就返回 skipped，提案里只留静态分析图。
        motion_info = anim_mod.build(
            project, rec_c, out_dir=out,
            discipline=str(getattr(ctx, "lead_id", "") or ""),
            sector=_sector,
            theme={k: str(v) for k, v in
                   ((rules or {}).get("tokens") or {}).items() if v})
        proposal_info = {
            "html": html_path,
            "pptx": pptx_info.get("path", ""),
            "pptx_ok": bool(pptx_info.get("ok")),
            "markdown": md_path2,
            "pages": model.get("count", 0),
            "recommended": model.get("recommended", ""),
            "alternative": model.get("alternative", ""),
            "curation": {"available": cur.get("available"),
                         "count": cur.get("count", 0),
                         "reason": cur.get("reason", "")},
            "motion": motion_info.get("path", ""),
            "motion_skipped": motion_info.get("skipped", ""),
            "discipline": motion_info.get("discipline", ""),
            "judgment": judgment,
        }
        prop_mod.release()          # 交出浏览器：同进程可能还要截图/出别的文档
        (out / "concept-proposal.json").write_text(
            json.dumps({"pages": [{"kind": p.kind, "title": p.title,
                                   "kicker": p.kicker} for p in model.get("pages") or []],
                        "recommended": model.get("recommended"),
                        "alternative": model.get("alternative"),
                        "theme": model.get("theme").__dict__,
                        "curation": {"available": cur.get("available"),
                                     "count": cur.get("count", 0),
                                     "terms": cur.get("terms")},
                        "files": proposal_info},
                       ensure_ascii=False, indent=1), encoding="utf-8")

    # G2 摘要（先出草稿，确认后重写为正式版）
    summary_path = out / "g2-approval-summary.md"
    summary_path.write_text(approval_summary(project, summary_text) + "\n", encoding="utf-8")

    state["options"] = {k: v for k, v in concept_set.items() if not k.startswith("_")}
    if not state.get("selected") and concept_set["concepts"]:
        # 提一个默认建议，但**不选定**：选定是业主/主创的动作
        state["suggested"] = comparison["recommendation"]["concept_id"]
    state["comparison"] = comparison
    state["files"] = {
        "concept_options": options_json,
        "concept_options_md": str(md_path),
        "style_recommendation": style_rec,
        "comparison": str(cmp_path),
        "visual_jobs": visual_files["jobs"],
        "visual_brief": visual_files["brief"],
        "presentation": deck_info.get("pptx", {}).get("path", ""),
        "presentation_md": deck_info.get("markdown", ""),
        "proposal_html": proposal_info.get("html", ""),
        "proposal_pptx": proposal_info.get("pptx", ""),
        "proposal_md": proposal_info.get("markdown", ""),
        "motion": proposal_info.get("motion", ""),
        "design_position": str(Path(out) / "design-position.md")
        if (Path(out) / "design-position.md").exists() else "",
        "g2_summary": str(summary_path),
        "visual_rules": str(_vref.path_for(project, project_dir)),
        "diagram_dir": str(out / "concept-diagrams"),
        "moodboard_dir": str(out / "moodboards"),
    }
    state["generated_at"] = concept_set.get("generated_at") or ""

    # 概念基准已存在时，重新生成会让它失效——如实标记，不静默沿用
    base = check_baseline(project)
    warnings: List[str] = list(ctx.warnings)
    if base.get("has_baseline") and base.get("changed"):
        warnings.append("重新生成的概念与已确认基准不一致：须重新提交 G2")
    if visual_res.held:
        warnings.append(
            f"{visual_res.held} 个概念视觉任务被拦下（费用未知或上次结果未回）："
            "未发出任何请求，也不声称费用受控")
    if (submit or authorize) and not visual_res.submitted:
        if not (submit and authorize):
            warnings.append("提交未发生：--submit 与 --authorize 必须同时具备")
        elif visual_res.platform_state != "connected":
            warnings.append(
                f"提交未发生：平台状态 {visual_res.platform_state}——未配置就不提交，"
                "任务包已就绪，不生成替代图片")

    handoff = handoff_mod.build(project, ctx, concept_set, comparison,
                                style_docs.get(concept_set["concepts"][0]["style_ids"][0], {}))
    handoff_path = handoff_mod.write(handoff, out)
    state["handoff"] = handoff

    return {
        "count": concept_set["count"],
        "concept_ids": [c["concept_id"] for c in concept_set["concepts"]],
        "roles": {c["concept_id"]: ROLE_LABEL[c["role"]] for c in concept_set["concepts"]},
        "suggested": state.get("suggested", ""),
        "precision": ctx.precision,
        "profile": ctx.profile_label,
        "gate_confirmed": ctx.gate_confirmed,
        "files": state["files"],
        "deck": deck_info.get("pptx", {}),
        "visual": {k: visual_res.to_dict()[k] for k in
                   ("platform_state", "submit_requested", "authorized", "submitted",
                    "generated", "reused", "held", "deferred", "failed", "job_count",
                    "cost_estimate", "cost_known", "cost_cap", "cost_controlled")},
        "comparison": {"ranking": comparison["ranking"],
                       "recommendation": comparison["recommendation"]},
        "handoff": handoff_path,
        "proposal": proposal_info,
        "warnings": warnings,
        "bundle_files": [name for name in BUNDLE_FILES if (out / name).exists()],
        "context": ctx.to_dict(),
    }


def status(project: Project) -> Dict[str, Any]:
    state = _concept_meta(project)
    options = state.get("options") or {}
    assessment = assess_gate(project)
    base = check_baseline(project)
    return {
        "project_id": project.project_id,
        "revision": project.revision,
        "generated": bool(options.get("concepts")),
        "concept_ids": [c["concept_id"] for c in (options.get("concepts") or [])],
        "selected": state.get("selected", ""),
        "suggested": state.get("suggested", ""),
        "gate": assessment.to_dict(),
        "baseline": base,
        "style_lock": state.get("style_lock") or {},
        "handoff_status": (state.get("handoff") or {}).get("status", "none"),
        "last_decision": state.get("last_decision") or {},
        "files": state.get("files") or {},
    }


def lock_style_for(project: Project, out_dir: str | Path,
                   *, acknowledged: Sequence[str] = (),
                   by: str = "") -> Dict[str, Any]:
    """Write the canonical style lock for the selected concept.

    Delegates to `gate.write_style_lock`, which is the same function G2 uses —
    there is exactly one lock format and one place that writes it, so a caller
    cannot produce a lock that the gate would then call a conflict.
    """
    from .gate import write_style_lock

    return write_style_lock(project, out_dir, acknowledged=acknowledged, by=by)


__all__ = [
    "concept_bundle", "generate_bundle", "status", "lock_style_for",
    "select", "decide_gate", "assess_gate", "check_baseline", "approval_summary",
    "write_style_lock", "style_lock_path", "StyleLockConflict", "ACKNOWLEDGEABLE",
    "build_context", "assert_ready", "ConceptContext",
    "for_profile", "prototype_count", "PROTOTYPES", "Prototype", "THEME_LABEL",
    "ROLE_LABEL", "resolve_style_id", "BUNDLE_FILES", "deck_mod", "handoff_mod",
    "mb_mod", "dia", "cmp", "pal", "vis",
    "DECISIONS", "SOURCES", "GateAssessment", "Outcome", "concept_digest",
]

#: 语义化别名：调用方读起来更像业务动作
concept_bundle = generate_bundle
