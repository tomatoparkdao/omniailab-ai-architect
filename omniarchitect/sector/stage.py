"""S3 的行业执行：把行业程序排成平面、出图、写记录。

这是 S3 内部的**分支**，不是新阶段：入口、G3、空间模型、DXF 适配器都没变，
只是"房间从哪来、按什么带排"换成了行业程序。

三种产出：
* 建筑/室内：`zone_bands` 两套平面 + 面积表 + DXF + 总平面关系图；
* 景观：分区面积与做法（不套房间算法）；
* 无程序可排（缺关键输入）：如实 blocked，并写清要补什么。

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Sequence

from . import layout as lay
from . import program as prog_mod
from . import site
from .brief import SectorBrief


def _fmt_m2(v: Any) -> str:
    try:
        return f"{float(v):,.1f}"
    except (TypeError, ValueError):
        return "—"


def _inputs_table(brief: SectorBrief) -> List[str]:
    rows = ["| 项 | 值 | 来源 |", "|---|---|---|"]
    labels = {"classes": "班数", "students": "学生人数", "per_class": "每班人数",
              "beds": "床位数", "outpatient": "日门诊量", "keys": "客房数",
              "area": "建筑面积", "site_area": "用地面积", "floors": "层数",
              "grid": "柱网", "seats": "座位数", "shifts": "供餐批次"}
    used = {k: v for k, v in brief.inputs.items() if k in labels}
    for k, v in used.items():
        src = brief.sources.get(k, "客户原话")
        rows.append(f"| {labels[k]} | {v:g} | {src} |")
    if not used:
        rows.append("| — | 尚无可用数值 | 待客户补充 |")
    return rows


def _facts_lines(brief: SectorBrief) -> List[str]:
    if not brief.facts:
        return ["- 尚无由数据推出的事实（缺关键输入）。"]
    return [f"- **{f['label']}**：{f['value']}"
            + (f"（{f['formula']}）" if f.get("formula") else "")
            for f in brief.facts]


def _scheme_rows(schemes: Dict[str, Any]) -> List[str]:
    ids = sorted({r["id"] for s in schemes.values() for r in s.area_table()})
    rows = ["| 房间 | 带 | 方案A m² | 方案B m² | 任务书 m² |",
            "|---|---|---|---|---|"]
    base_scheme = schemes.get("A") or next(iter(schemes.values()))
    band_of = {}
    for r in base_scheme.area_table():
        band_of[r["id"]] = r["use"]
    for rid in ids:
        ra = next((r for r in (schemes.get("A") or base_scheme).area_table()
                   if r["id"] == rid), None)
        rb = next((r for r in (schemes.get("B") or base_scheme).area_table()
                   if r["id"] == rid), None)
        base = ra or rb
        rows.append(
            f"| {base['name']} | {band_of.get(rid, base.get('use', ''))} "
            f"| {_fmt_m2((ra or {}).get('area_m2'))} | {_fmt_m2((rb or {}).get('area_m2'))} "
            f"| {_fmt_m2(base.get('target_m2'))} |"
        )
    return rows


def _metrics_rows(schemes: Dict[str, Any]) -> List[str]:
    rows = ["| 指标 | 方案A | 方案B |", "|---|---|---|"]
    for key, label in [("room_count", "房间数"), ("total_area_m2", "使用面积 m²"),
                       ("corridor_area_m2", "走廊面积 m²"),
                       ("corridor_ratio", "走廊占比"), ("window_count", "外窗数"),
                       ("glazing_ratio", "窗地比"), ("daylight_rooms_served", "采光房间")]:
        rows.append(f"| {label} | {schemes['A'].metrics.get(key, '—')} "
                    f"| {schemes['B'].metrics.get(key, '—')} |")
    return rows


def _cost_lines(schemes: Dict[str, Any]) -> List[str]:
    out: List[str] = []
    for v, s in sorted(schemes.items()):
        walls = [e for e in s.elements if e.type == "wall"]
        length = sum(w.wall_length_mm() for w in walls) / 1000.0
        area = sum(w.wall_length_mm() / 1000.0
                   * float(w.geometry.get("height_mm", 2800)) / 1000.0 for w in walls)
        out.append(f"- 方案{v}：隔墙 {length:.0f} m（{area:.0f} m²），"
                   f"按 260–680 元/m² 估 {area * 260:,.0f}–{area * 680:,.0f} CNY")
    return out


def _boundary_lines(brief: SectorBrief, capability: Dict[str, str]) -> List[str]:
    out = [f"- 能力边界：**{capability.get('label') or '未登记'}**"
           + (f"；{capability.get('note')}" if capability.get("note") else "")]
    if brief.missing:
        out.append("- 还缺的输入（缺了只能按假设推进，不能当结论）：")
        out += [f"  - {m}" for m in brief.missing]
    if brief.assumptions:
        out.append("- 本次用到的假设：")
        out += [f"  - {a}" for a in brief.assumptions]
    return out


def run(runner: Any, d: Path, brief: SectorBrief,
        active: Sequence[str]) -> Dict[str, Any]:
    """执行行业 S3。返回 dict，由 workflow 包成 StageOutcome。"""
    from ..concept.handoff import load_for, store_plan_record, verify_scheme
    from ..concept.gate import concept_digest
    from .. import taxonomy as _tx

    program = prog_mod.build(brief)
    sectors = {"education", "healthcare", "industrial", "hospitality", "landscape"}
    if brief.sector not in sectors:
        return {"skip": True}
    if not program.rows:
        return {
            "status": "blocked",
            "error": (f"这不是能直接排房间的项目（{brief.sector_label or brief.sector}）："
                      "当前没有对应的行业程序。"),
            "next_action": "补齐项目类型与规模后重跑；或用住宅/办公算法另行委托",
            "notes": ["未生成平面：不拿房间算法冒充专项方案"],
        }

    handoff = load_for(runner.project)
    title = f"{runner.project.name}"

    # ---------- 景观：分区与做法，不排房间 ----------
    if brief.sector == "landscape":
        data = lay.landscape_data(program, brief)
        # 分区要进模型：只在报告里写"有水景"，G3 的一致性核验看不见它，
        # 会判成"设计意图要求的水景被取消了"。
        lay.install_landscape_spaces(runner.project, program, brief)
        svg = site.landscape_svg(program, brief, title=title)
        (d / "landscape-plan.svg").write_text(svg, encoding="utf-8")
        rows = ["# 景观方案（S3）", "",
                f"## {title}", "",
                f"- 场地 {data['site_area_m2']:,.0f} m²；绿地率 {data['green_ratio']}；"
                f"水面 {data['water_ratio']}", ""]
        rows += ["## 分区与占比", "", "| 分区 | 面积 m² | 占比 | 做法 |",
                 "|---|---|---|---|"]
        rows += [f"| {z['name']} | {z['area_m2']:,.0f} | {z['share']} | {z['note']} |"
                 for z in data["zones"]]
        rows += ["", "## 设计矛盾（本方案要处理的）", ""]
        rows += [f"- {t}" for t in brief.tensions] or ["- 尚无由数据推出的矛盾"]
        rows += ["", "## 能力边界", ""]
        rows += _boundary_lines(brief, _tx.capability_of(brief.codes))
        rows += ["", "> 分区与占比来自场地面积与客户诉求；竖向、放线、植物规格须实测与苗源确认。"]
        (d / "landscape-plan.md").write_text("\n".join(rows), encoding="utf-8")
        store_plan_record(runner.project, {
            "revision": runner.project.revision,
            "concept_id": handoff.get("concept_id") or "",
            "concept_digest": concept_digest(runner.project),
            "discipline": "landscape",
            "sector": "landscape",
            "design_data": {"zones": data["zones"], "site_area_m2": data["site_area_m2"],
                            "codes": list(brief.codes)},
            "rooms": len(data["zones"]),
            "handoff_status": handoff.get("status", "none"),
            "conformance": "not_applicable",
            "plan_strategy": "landscape_zones",
            "implements_concept": bool(handoff.get("status") == "locked"),
            "gate": {},
            "at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        })
        return {
            "artifacts": [str(d / "landscape-plan.md"), str(d / "landscape-plan.svg")],
            "notes": [f"景观分区 {len(data['zones'])} 项，场地 {data['site_area_m2']:,.0f} m²",
                      "未生成房间平面：景观不套房间算法"],
        }

    # ---------- 建筑 / 室内：排平面 ----------
    lay.install_program(runner.project, program)
    proposed = not lay.has_envelope(runner.project)
    env = lay.envelope_size(program, brief.sector)
    if proposed:
        lay.install_envelope(runner.project, env)
    schemes = lay.build_schemes(runner.project, program, brief.sector, env)
    runner.schemes = schemes
    concept_check = verify_scheme(handoff, schemes["A"], runner.project) \
        if handoff.get("status") in ("locked", "selected_not_confirmed") else None

    capability = _tx.capability_of(brief.codes)
    rows = ["# 平面方案对比（S3）", ""]
    from ..workflow import _s3_taxonomy_block     # 延迟导入，避免循环
    rows += _s3_taxonomy_block(runner.project, sorted(active))

    rows += ["## 行业输入（从 S1 原话推出）", ""]
    rows += _inputs_table(brief)
    rows += ["", "## 由输入推出的事实", ""]
    rows += _facts_lines(brief)
    if brief.ancillary:
        rows += ["", "**本项目里的配套功能**（不单独形成委托）："
                 + "、".join(a["label"] for a in brief.ancillary)]
    if brief.tensions:
        rows += ["", "## 设计矛盾（这套方案要解决的）", ""]
        rows += [f"{i}. {t}" for i, t in enumerate(brief.tensions, 1)]
    rows += ["", f"## 任务书（{program.unit}）", "", "| 房间 | 面积 m² | 带 | 依据 |",
             "|---|---|---|---|"]
    rows += [f"| {r.name} | {r.area_m2:,.1f} | {r.band} | {r.basis} |" for r in program.rows]
    if program.note:
        rows += ["", f"> {program.note}"]
    rows += ["", "## 方案面积表", ""] + _scheme_rows(schemes)
    rows += ["", "## 指标对比", ""] + _metrics_rows(schemes)
    rows += ["", "## 造价影响（R3）", ""] + _cost_lines(schemes)
    if concept_check is not None:
        rows += ["", "## 概念一致性校核（S2 → S3）", "",
                 f"选定概念：**{handoff.get('concept_id')} {handoff.get('concept_name')}**　"
                 f"结论：**{concept_check['conformance']}**", "",
                 "| 检查 | 结果 | 说明 |", "|---|---|---|"]
        rows += [f"| {c['check']} | {'通过' if c['ok'] else '不通过'} | {c['detail']} |"
                 for c in concept_check["checks"]]
        for c in concept_check["conflicts"]:
            rows.append(f"\n- ⚠ {c['id']}（{c['severity']}）：{c['detail']}")
    else:
        rows += ["", "## 概念一致性校核", "",
                 "- 无已确认概念：本轮平面为探索性验证，**不得签发 G3**。"]
    rows += ["", "## 能力边界与待补条件", ""] + _boundary_lines(brief, capability)
    rows += ["", "---", "",
             "> 平面为方案深度（schematic）：房间面积与关系可讨论，构造、结构与机电须专项。",
             "> 平面未确认前不得进入精细建模与正式出图（门禁 G3）。"]
    (d / "scheme-comparison.md").write_text("\n".join(rows), encoding="utf-8")

    arts: List[str] = [str(d / "scheme-comparison.md")]
    for v, s in schemes.items():
        (d / f"scheme-{v}.json").write_text(
            json.dumps(s.report(), ensure_ascii=False, indent=2), encoding="utf-8")

    # 完整模型（方案A）写进项目：S4 要继承这套墙与房间，G3 的一致性核验
    # 也要能看见真实的走廊与水景——只装在 fork 里，门禁看到的还是空模型。
    from ..workflow import _install_scheme
    _install_scheme(runner.project, s=schemes["A"])
    baseline = runner.project

    note_dxf = "未生成 DXF"
    from ..adapters.dxf import DxfAdapter
    dxf = DxfAdapter()
    if dxf.preflight().available:
        r = dxf.draw_plan(baseline, d / "S3-schematic-A.dxf",
                          level_id=runner.project.levels[0].id,
                          scheme="A", title=f"{title} 平面方案（方案深度）",
                          include_furniture=True)
        arts.extend(r.artifacts)
        note_dxf = ("方案深度 DXF 已生成并审计通过"
                    f"（{r.validation.get('stats', {}).get('entities', '?')} 实体）"
                    if r.ok else f"DXF 审计未通过：{r.errors[:2]}")
    else:
        note_dxf = "ezdxf 不可用，未生成方案深度 DXF"

    site_svg = None
    if program.blocks:
        svg = site.plan_svg(program, brief, title=f"{title} · 总平面关系")
        (d / "site-plan.svg").write_text(svg, encoding="utf-8")
        arts.append(str(d / "site-plan.svg"))
        m = site.metrics(program, brief)
        site_line = (f"总平面：容积率 {m['far']:.2f}、建筑密度 {m['coverage']:.0%}"
                     f"（{m['site_m2']:,.0f} m² 用地）")

    strategy_supported = bool((handoff.get("spatial") or {}).get("plan_strategy_supported"))
    implements = bool(concept_check and concept_check["conformance"] != "fail")
    store_plan_record(runner.project, {
        "revision": runner.project.revision,
        "concept_id": handoff.get("concept_id") or "",
        "concept_digest": concept_digest(runner.project),
        "discipline": brief.discipline,
        "sector": brief.sector,
        "design_data": {
            "unit": program.unit, "rooms": len(program.rows),
            "program_m2": round(program.area_m2, 1),
            "bands": list(program.bands),
            "inputs": dict(brief.inputs),
            "codes": list(brief.codes),
            "missing_inputs": list(brief.missing),
            "envelope": env.to_dict(),
            "proposed_envelope": proposed,
        },
        "rooms": len(program.rows),
        "dxf": [a for a in arts if str(a).lower().endswith(".dxf")],
        "handoff_status": handoff.get("status", "none"),
        "conformance": (concept_check or {}).get("conformance", "not_applicable"),
        "auto_pass": bool((concept_check or {}).get("auto_pass")),
        "fully_verified": bool((concept_check or {}).get("fully_verified")),
        "conflicts": list((concept_check or {}).get("conflicts") or []),
        "manual_review": list((concept_check or {}).get("manual_review") or []),
        "plan_strategy": "zone_bands",
        "requested_strategy": str((handoff.get("spatial") or {}).get("plan_strategy") or ""),
        "strategy_supported": True,
        "implements_concept": implements,
        "gate": {},
        "at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
    })

    notes = [
        f"行业：{brief.sector_label}（{program.unit}，{len(program.rows)} 个房间）",
        f"两套方案：A 前场采光 / B 后场前置；{'轮廓按任务书反算（建议轮廓）' if proposed else '沿用已有几何'}",
        note_dxf,
    ]
    if program.blocks:
        notes.append(site_line)
    if brief.missing:
        notes.append("缺输入：" + brief.missing[0])
    if capability.get("level") in ("concept_only", "specialist"):
        notes.append(f"能力边界（{capability['level']}）：{capability.get('note', '')}")
    return {"artifacts": arts, "notes": notes, "schemes": schemes, "program": program,
            "envelope": env}


__all__ = ["run"]
