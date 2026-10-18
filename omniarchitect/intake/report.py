"""S1 deliverable bundle.

S1 used to produce two markdown files. That is enough to look organised and
not enough to design from, because the reasoning — what we asked, what we were
told, what we could not verify, what we therefore may not claim — lived only
in the conversation.

The bundle makes that reasoning an artifact:

===========================  ===============================================
file                         answer it gives
===========================  ===============================================
``design-brief.md``          what we are designing, for whom, to what depth
``user-needs.json``          how the space is actually used
``site-report.md``           the physical conditions we may rely on
``source-register.json``     where every input came from and how fresh it is
``uncertainty-register.json``what is unverified, and exactly what it blocks
``feasibility-report.md``    what does not add up, with evidence
``design-opportunities.md``  the 3–5 problems worth spending the project on
``s1-approval-summary.md``   what the client is being asked to sign
===========================  ===============================================

Every file is bound to ``project_id`` + ``revision`` and registered as an
artifact, so a later change can mark it stale instead of silently diverging.

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from ..model import Project
from ..paths import relpath
from ..revisions import register_artifact
from .diligence import (
    CONFIDENCE_LABEL,
    assess_sources,
    blocking_stages,
    markdown as uncertainty_markdown,
    precision_level,
    source_register,
    uncertainty_register,
)
from .feasibility import markdown as feasibility_markdown, run_feasibility
from .interview import completeness, load_interview, summary as interview_summary
from .needs import build_need_matrix, markdown as needs_markdown
from .opportunities import find_opportunities, markdown as opportunities_markdown

S1_BUNDLE_FILES = (
    "design-brief.md",
    "user-needs.json",
    "site-report.md",
    "source-register.json",
    "uncertainty-register.json",
    "feasibility-report.md",
    "design-opportunities.md",
    "s1-approval-summary.md",
)

#: 案例研究两份：**条件产出**，不是永远产出。
#:
#: 研究要联网，离网时（测试、安装自检、演示、`OMNIAILAB_NO_NETWORK`）根本
#: 没有结果可写。把它们放进 ``S1_BUNDLE_FILES`` 会让「清单」和「实际产出」
#: 对不上——清单说有、目录里没有，下游会把它当成丢件。
#: 因此单列一份，由实际写出与否决定。
RESEARCH_BUNDLE_FILES = (
    "reference-shortlist.md",
    "reference-shortlist.json",
)

#: 多专业项目额外产出的六份。
#:
#: 单专业（纯室内）项目不生成——空表比没有更危险：一份"全部 not_applicable"
#: 的接口矩阵会被误读成"已核对无冲突"。
DISCIPLINE_BUNDLE_FILES = (
    "discipline-scope.json",
    "discipline-scope.md",
    "discipline-interface-matrix.json",
    "discipline-interface-matrix.md",
    "discipline-responsibility-matrix.md",
    "information-request-list.md",
    "design-leadership.json",
)

PRECISION_LABEL = {
    "diagnostic": "诊断级：只能做需求诊断与概念方向，不出任何技术成果",
    "schematic": "示意级：可出方案图与示意，尺寸须现场核验，不出施工图",
    "authoritative_capable": "可出图级：有图纸或实测依据，可出方案深度图纸（施工图仍须专业签署）",
}


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _head(project: Project, title: str) -> List[str]:
    return [
        f"# {title} — {project.name or project.project_id}",
        "",
        f"- 项目编号：`{project.project_id}`　修订：r{project.revision}",
        f"- 生成时间：{_now()}",
        f"- 精度等级：{PRECISION_LABEL.get(precision_level(project), '')}",
        "",
    ]


def render_design_brief(project: Project, est: Any = None) -> str:
    """The formal brief. Facts, assumptions and gaps are kept apart on purpose."""
    cons = {k: v for k, v in (project.constraints or {}).items()
            if not k.startswith("_")}
    matrix = build_need_matrix(project)
    feas = run_feasibility(project)
    comp = completeness(project)
    intr = interview_summary(project)
    src = assess_sources(project)
    unc = uncertainty_register(project)
    open_unc = [u for u in unc if u.get("open")]

    lines = _head(project, "设计任务书")
    lines += [
        f"- 项目类型：{comp['profile_label']}",
        f"- 信息完整度：{comp['ratio'] * 100:.0f}%（{comp['verdict']}）；"
        f"登记资料 {src['count']} 份",
        f"- 启动方式：{intr['start_mode_label'] or '未记录'}",
        f"- 设计阶段：方案（非施工图深度）",
        "",
    ]
    for k, v in cons.items():
        lines.append(f"- {k}：{v}")
    budget = cons.get("budget_cny")
    if budget:
        try:
            lines.append(f"- 预算：{float(budget):,.0f} CNY")
        except (TypeError, ValueError):
            lines.append(f"- 预算：{budget}")

    # --- what we are actually solving ------------------------------------
    must = [r for r in matrix["rows"] if r["priority"] == "must"]
    lines += ["", "## 设计目标（按重要性，来自访谈）", ""]
    if must:
        for i, r in enumerate(must, 1):
            lines.append(f"{i}. {r['activity']}"
                         + (f"（{r['headcount']} 人）" if r["headcount"] else ""))
    else:
        lines.append("- 尚未获得可排序的设计目标：需求问题未回答，本任务书只覆盖已有 program。")

    # --- programme --------------------------------------------------------
    lines += ["", "## 功能任务书", ""]
    if not project.program:
        lines.append("- 尚未形成功能任务书：需求已收集，但还没有转成房间与面积。"
                     "这一步在 S2 概念阶段与平面同步完成，此处不虚构面积。")
        project_program: List[Dict[str, Any]] = []
    else:
        project_program = list(project.program)
        lines += ["| # | 房间 | 用途 | 目标面积 m² | 分区 | 需采光 | 来源 |",
                  "|---|---|---|---|---|---|---|"]
    for i, p in enumerate(project_program, 1):
        rec = str(p.get("recipe") or "")
        day = rec in ("living", "dining", "kitchen", "master_bedroom", "bedroom", "study")
        lines.append(
            f"| {i} | {p.get('name','')} | {rec} | {p.get('area_m2','')} "
            f"| {p.get('zone','')} | {'是' if day else '否'} | program |"
        )
    total = sum(float(p.get("area_m2") or 0) for p in project_program)
    if project_program:
        lines += ["", f"**任务书面积合计：{total:.1f} m²**"]

    # --- usage matrix -----------------------------------------------------
    lines += ["", "## 使用行为矩阵（摘要）", "", needs_markdown(matrix)]
    if matrix["gaps"]:
        lines += ["", "**矩阵缺口**：", ""]
        lines += [f"- {g}" for g in matrix["gaps"]]

    # --- sources and confidence -------------------------------------------
    lines += ["", "## 已知条件与信息来源", ""]
    if project.sources:
        lines += ["| 来源 | 类型 | 可信度 | 备注 |", "|---|---|---|---|"]
        for s in project.sources:
            conf = str(s.get("confidence") or "")
            lines.append(
                f"| {s.get('file','') or s.get('id','')} | {s.get('type','')} "
                f"| {CONFIDENCE_LABEL.get(conf, conf)} | {s.get('note','')} |"
            )
    else:
        lines.append("- 尚无资料登记：所有尺寸与现状均未证实。")
    if src["gaps"]:
        lines += ["", "**资料缺口**：", ""]
        lines += [f"- {g}" for g in src["gaps"]]

    # --- assumptions and open items ---------------------------------------
    lines += ["", "## 假设（未确认，不得当作事实）", ""]
    lines += [f"- {a}" for a in (project.assumptions or [])] or ["- 无"]
    if intr["unknown"]:
        lines += ["", "### 业主暂未确定（不阻断，已列为假设）", ""]
        for qid in intr["unknown"]:
            lines.append(f"- `{qid}`：业主表示暂不确定")

    lines += ["", "## 待核实与冲突（详见 uncertainty-register.json）", ""]
    if open_unc:
        lines += [f"- {u['statement']}（{u['state_label']}；阻断 "
                  f"{'、'.join(u.get('blocks_stages') or []) or '无'}）"
                  for u in open_unc]
    else:
        lines.append("- 无登记项")

    # --- budget -----------------------------------------------------------
    if est is not None:
        lines += ["", "## 预算口径（前期估算，非报价）", "",
                  f"- 估算区间：{est.cost['subtotal_low']:,.0f} – "
                  f"{est.cost['subtotal_high']:,.0f} CNY",
                  f"- 单位造价：{est.cost['per_m2_low']:,.0f} – "
                  f"{est.cost['per_m2_high']:,.0f} 元/m²"]
        lines += [f"- {n}" for n in est.notes]

    # --- feasibility headline --------------------------------------------
    lines += ["", "## 可行性结论", "", f"**{feas['headline']}**", ""]
    lines += ["| 严重度 | 问题 | 依据 |", "|---|---|---|"]
    for c in feas["conflicts"]:
        if c["severity"] in ("blocker", "major"):
            lines.append(f"| {c['severity_label']} | {c['problem']} | {c['evidence']} |")
    if not any(c["severity"] in ("blocker", "major") for c in feas["conflicts"]):
        lines.append("| — | 未发现阻断或重要冲突 | — |")

    # --- opportunities headline ------------------------------------------
    opps = find_opportunities(project)
    lines += ["", "## 设计机会（研究方向，不是方案）", ""]
    if opps["items"]:
        for o in opps["items"]:
            lines.append(f"- **{o['opportunity_id']}**　{o['problem']}")
    else:
        lines.append("- 资料不足，暂不提出设计机会；补齐后重跑，不凑数。")

    # --- acceptance -------------------------------------------------------
    lines += ["", "## 验收标准", "",
              "1. 功能任务书与使用行为矩阵经业主逐条确认；",
              "2. 面积指标与预算口径一致，且注明包含范围；",
              "3. 不确定性已登记，并写明各自阻断的阶段；",
              "4. 业主对「本轮可支撑的深度」无异议（见精度等级）。", ""]
    return "\n".join(lines)


def render_site_report(project: Project) -> str:
    """Physical conditions, with inferred items kept visibly separate."""
    from ..planner import envelope_polygon, entry_point

    lines = _head(project, "项目与建筑条件报告")
    try:
        env = envelope_polygon(project, project.levels[0].id if project.levels else "")
    except Exception:
        env = []
    if env:
        xs = [p[0] for p in env]
        ys = [p[1] for p in env]
        try:
            ex, ey = entry_point(project, env)
        except Exception:
            ex = ey = 0.0
        lvl_height = next((l.height_mm for l in project.levels
                           if l.id == (project.levels[0].id if project.levels else "")), 0.0)
        lines += ["## 外壳", "",
                  f"- 内表面外包尺寸：{(max(xs)-min(xs))/1000:.2f} m × "
                  f"{(max(ys)-min(ys))/1000:.2f} m",
                  f"- 外轮廓顶点数：{len(env)}（{'矩形' if len(env) == 4 else '非矩形，分区会被裁剪'}）",
                  f"- 入户位置（推断）：({ex:.0f}, {ey:.0f})",
                  f"- 层高：{lvl_height:.0f} mm", ""]
    else:
        lines += ["## 外壳", "",
                  "- 尚无几何数据：本报告只汇总已知资料，不含任何尺寸结论。", ""]

    walls = [w for w in project.by_type("wall")]
    uncertain = [e for e in project.elements if e.uncertain]
    lines += ["## 既有构件", "",
              f"- 墙体 {len(walls)} 段，其中推断所得 {len(uncertain)} 段", ""]

    lines += ["## 图纸解析", "",
              "- 图层识别：A-WALL（结构墙）/ A-WALL-PART（隔墙）/ A-DOOR / A-GLAZ / A-ANNO-DIMS",
              "- 推断内容与实测内容已分离标记（`uncertain` 字段）", ""]

    src = assess_sources(project)
    lines += ["## 资料完备性", "",
              f"- 登记资料 {src['count']} 份（{', '.join(f'{k}×{v}' for k, v in src['by_kind'].items()) or '无'}）",
              f"- 尺寸权威性：{CONFIDENCE_LABEL.get(src['dimensional_authority'], '未知')}", ""]
    if src["gaps"]:
        lines += ["- 缺口：", ""] + [f"  - {g}" for g in src["gaps"]]

    lines += ["", "## 不确定信息（必须现场核对）", "", uncertainty_markdown(project), "",
              "> 梁柱与承重墙不得依据图纸推定；须现场探测或由原设计单位确认。", ""]
    return "\n".join(lines)


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")


def generate_bundle(project: Project, out_dir: str | Path,
                    est: Any = None, summary_text: str = "",
                    research: bool = False,
                    fetch_fn: Any = None,
                    verify_pages: bool = True) -> Dict[str, Any]:
    """Write the whole S1 bundle and register every file as an artifact.

    ``out_dir`` is the stage output directory (``01-brief-and-brief`` or
    whatever the runner uses), so files land next to the runner's own output
    rather than in a second parallel tree.

    ``research`` is off by default **on purpose**: this function is called by
    tests, by scenarios and by the installer's smoke checks, and a default that
    reaches the network would make the whole suite depend on eight foreign
    websites being up. The live S1 stage passes ``research=True`` explicitly.
    ``fetch_fn`` and ``verify_pages`` are the seams tests use.
    """
    from .gate import approval_summary_text

    d = Path(out_dir)
    d.mkdir(parents=True, exist_ok=True)

    # Same starting point for every caller, so the bundle never depends on
    # whether the caller remembered to start an interview first.
    from .interview import ensure_intake

    ensure_intake(project)

    # Cost estimate is part of the brief (R3), so it is produced here rather
    # than by the caller — otherwise `run` and `intake analyze` disagree on the
    # same project. Absent budget or geometry simply yields no estimate.
    if est is None and (project.constraints or {}).get("budget_cny"):
        try:
            from .. import quantities

            level = project.levels[0].id if project.levels else "L1"
            est = quantities.takeoff(project, level)
        except Exception:
            est = None

    matrix = build_need_matrix(project)
    feas = run_feasibility(project)
    opps = find_opportunities(project)
    sources = {
        "project_id": project.project_id, "revision": project.revision,
        "generated_at": _now(), "assessment": assess_sources(project),
        "entries": source_register(project),
        "note": "每份资料的 revision 与取得时间是判断「图纸是否过期」的依据。",
    }
    uncertainty = {
        "project_id": project.project_id, "revision": project.revision,
        "generated_at": _now(),
        "precision": precision_level(project),
        "precision_label": PRECISION_LABEL.get(precision_level(project), ""),
        "items": uncertainty_register(project),
        "blocking_by_stage": blocking_stages(project),
        "note": ("state 五值：verified / documented / inferred / unknown / conflicting。"
                 "只有前两者可以作为出图依据。"),
    }

    written: List[str] = []
    (d / "design-brief.md").write_text(render_design_brief(project, est), encoding="utf-8")
    written.append("design-brief.md")
    _write_json(d / "user-needs.json", matrix)
    written.append("user-needs.json")
    (d / "site-report.md").write_text(render_site_report(project), encoding="utf-8")
    written.append("site-report.md")
    _write_json(d / "source-register.json", sources)
    written.append("source-register.json")
    _write_json(d / "uncertainty-register.json", uncertainty)
    written.append("uncertainty-register.json")
    (d / "feasibility-report.md").write_text(
        "\n".join(_head(project, "设计可行性分析") + [feasibility_markdown(feas), ""]),
        encoding="utf-8")
    written.append("feasibility-report.md")
    (d / "design-opportunities.md").write_text(
        "\n".join(_head(project, "核心设计问题与机会") + [opportunities_markdown(opps), ""]),
        encoding="utf-8")
    written.append("design-opportunities.md")
    (d / "s1-approval-summary.md").write_text(
        approval_summary_text(project, summary_text), encoding="utf-8")
    written.append("s1-approval-summary.md")

    # --- 案例研究：不等所有问题问完，也不等 G1 --------------------------
    # 这是 S1 的一部分，不是新阶段：客户刚说完"三层极简别墅"，就应该能看到
    # 真正的建成案例。检索失败是允许的，编造案例不允许——所以失败时文件照写，
    # 里面写清为什么没有。
    import os as _os

    network_ok = _os.environ.get("OMNIAILAB_NO_NETWORK", "").strip().lower() not in (
        "1", "true", "yes", "on")
    if research and network_ok:
        from .. import research as research_mod

        try:
            res = research_mod.run(project, out_dir=d, fetch_fn=fetch_fn,
                                   verify_pages=verify_pages)
            written.extend(name for name in
                           (research_mod.SHORTLIST_MD, research_mod.SHORTLIST_JSON)
                           if (d / name).exists())
            research_info = {
                "cases": len(res.cases),
                "verified": len(res.verified),
                "attempts": len(res.log),
            }
        except Exception as exc:      # pragma: no cover - defensive
            research_info = {"cases": 0, "verified": 0, "error": str(exc)[:160]}
    elif research:
        research_info = {"skipped": True, "reason": "OMNIAILAB_NO_NETWORK 已置位，未联网检索"}
    else:
        research_info = {"skipped": True}

    # --- 多专业范围：谁在范围、谁缺资料、谁和谁会打架 --------------------
    # 这四份不是"补充材料"：G1 确认的就是它们。没有它们，多专业项目在
    # S1 结束时根本无法说清"到底委托了什么"。
    from .. import disciplines as disc

    scope = disc.ensure(project)
    if scope.active():
        iface = disc.interfaces_for(scope)
        _write_json(d / "discipline-scope.json", {
            "project_id": project.project_id,
            "revision": project.revision,
            "generated_at": _now(),
            **scope.to_dict(),
            "interfaces": iface,
            "note": ("out_of_scope 必须有证据；needs_data 表示在范围内但资料不足，"
                     "不等于不做。"),
        })
        _write_json(d / "discipline-interface-matrix.json", {
            "project_id": project.project_id,
            "revision": project.revision,
            "generated_at": _now(),
            "interfaces": iface,
            "counts": {
                "active": sum(1 for r in iface if r["state"] == "active"),
                "one_side_out": sum(1 for r in iface if r["state"] == "one_side_out"),
            },
        })
        (d / "discipline-scope.md").write_text(
            disc.render_scope_markdown(project.name or project.project_id,
                                       project.revision, scope), encoding="utf-8")
        (d / "discipline-interface-matrix.md").write_text(
            disc.render_interface_markdown(project.name or project.project_id,
                                           project.revision, iface), encoding="utf-8")
        (d / "discipline-responsibility-matrix.md").write_text(
            disc.render_responsibility_markdown(project.name or project.project_id,
                                                project.revision, scope),
            encoding="utf-8")
        asks = disc.information_requests(scope)
        (d / "information-request-list.md").write_text(
            disc.render_information_requests_markdown(
                project.name or project.project_id, asks), encoding="utf-8")

        # --- 设计主导：谁定美学、谁研究怎么实现 --------------------------
        from .. import leadership as lead_mod

        lead = lead_mod.ensure(project, scope)
        _write_json(d / "design-leadership.json", {
            "project_id": project.project_id,
            "revision": project.revision,
            "generated_at": _now(),
            "design_scope": list(scope.active()),
            "design_scope_labels": scope.labels(),
            "technical_support_scope": list(lead.support_disciplines),
            "coordination_scope": list(lead.coordination),
            **lead.to_dict(),
            "note": ("项目主导专业在 G1 确认，S2 起据此决定概念组织与评价权重；"
                     "辅助专业研究如何实现，不主导形态。"),
        })
        for name in ("discipline-scope.json", "discipline-interface-matrix.json",
                     "discipline-scope.md", "discipline-interface-matrix.md",
                     "discipline-responsibility-matrix.md",
                     "information-request-list.md", "design-leadership.json"):
            written.append(name)

    for name in written:
        aid = f"art-s1-{name.replace('.', '-')}"
        kind = "document" if name.endswith(".md") else "data"
        deps = ["project:program", "project:constraints"]
        if name.startswith("reference-shortlist"):
            # Cases depend on the brief, not on geometry: a case list built
            # from a stale brief is exactly what must go stale with it.
            deps = ["project:constraints"]
        register_artifact(project, aid, kind, deps,
                          "design-brief", relpath(d / name), "draft")

    return {
        "dir": str(d),
        "files": written,
        "count": len(written),
        "precision": precision_level(project),
        "verdict": feas["verdict"],
        "opportunities": opps["count"],
        "completeness": completeness(project)["ratio"],
        "research": research_info,
    }
