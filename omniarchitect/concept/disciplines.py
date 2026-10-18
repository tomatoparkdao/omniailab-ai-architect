"""专业方向：一套概念，多个专业各自的"怎么做"。

为什么不是"再生成三套"
----------------------
室内、结构、机电、景观不是四个独立方案，它们必须服从同一套空间主张。
所以这里不新建引擎：每个专业方向都从**已选的空间原型 + 已锁风格 + 范围状态**
推导出来，写清目标、策略、交付物、还缺什么、谁要签。

缺资料的写法
------------
数据不够时给的是"条件"而不是"结论"：例如结构只写"先鉴定后设计、需结构工程师
出计算书"，不写"采用 200×500 钢梁"——后者是编的。
每个方向都带 `status`：`proposed` / `requires_input`，一眼能看出哪条还不能用。

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .. import disciplines as D

PROPOSED = "proposed"
NEEDS_INPUT = "requires_input"


def _answer(project: Any, *keys: str) -> str:
    from ..intake.interview import load_interview

    answers = load_interview(project).answers or {}
    for k in keys:
        v = (answers.get(k) or {}).get("value")
        if v:
            return str(v)
    return ""


def _direction(did: str, *, goal: str, strategy: str,
               deliverables: List[str], open_questions: List[str],
               status: str = PROPOSED, evidence: str = "") -> Dict[str, Any]:
    d = D.DISCIPLINES[did]
    return {
        "discipline": did,
        "label": d.label,
        "goal": goal,
        "strategy": strategy,
        "deliverables": deliverables,
        "open_questions": open_questions,
        "status": status,
        "needs_professional": bool(d.needs_professional),
        "evidence": evidence,
        "note": d.note,
    }


def for_concept(project: Any, scope: D.DisciplineScope,
                concept: Dict[str, Any], ctx: Any) -> Dict[str, Dict[str, Any]]:
    """按范围给这套概念补齐各专业方向。只做在范围内的专业。"""
    out: Dict[str, Dict[str, Any]] = {}
    spatial = str(concept.get("spatial_strategy") or "")
    statement = str(concept.get("concept_statement") or "")
    materials = [str(m.get("name")) for m in (concept.get("material_direction") or [])
                 if isinstance(m, dict) and m.get("name")]
    active = scope.active()

    if "architecture" in active:
        out["architecture"] = _direction(
            "architecture",
            goal="用体量与开口把概念的空间主张立起来",
            strategy=f"以「{statement}」为形体依据；总平、体量、立面按同一逻辑展开",
            deliverables=["总平面", "各层平面", "立面与剖面", "体量示意"],
            open_questions=["用地红线与退线", "限高与容积率", "报建路径"],
            status=NEEDS_INPUT if not _answer(project, "scope.planning_approval") else PROPOSED,
            evidence="概念空间策略：" + (spatial[:40] or "未形成"),
        )

    if "interior" in active:
        has_material = bool(materials)
        out["interior"] = _direction(
            "interior",
            goal="把概念落到人每天接触的界面、家具与光",
            strategy=(spatial or "按概念的分区与动线组织室内") +
                     ("；材料按已锁定风格执行：" + "、".join(materials[:4]) if has_material else ""),
            deliverables=["平面布置", "顶墙地做法", "家具与固定件", "材料表"],
            open_questions=[] if has_material else ["材料方向待 G2 锁定"],
            status=PROPOSED if has_material else NEEDS_INPUT,
            evidence=f"材料 {len(materials)} 项来自概念",
        )

    if "structure" in active:
        e = scope.entries.get("structure")
        unverified = bool(e and e.state in (D.INFERRED, D.UNKNOWN, D.REQUIRED))
        out["structure"] = _direction(
            "structure",
            goal="确认现有结构能不能承受这次改动",
            strategy=("先鉴定后设计：以现场查勘与结构图纸为依据，再决定拆改范围；"
                      "涉及承重构件时不做无依据的假定"),
            deliverables=["结构现状说明", "拆改可行性条件", "加固/新增构件方案（由结构工程师出）"],
            open_questions=["现有结构图纸", "承重构件位置", "荷载变化"],
            status=NEEDS_INPUT if unverified else PROPOSED,
            evidence=(e.evidence if e else "") or "未提供结构资料",
        )

    if "mep" in active:
        e = scope.entries.get("mep")
        unverified = bool(e and e.state in (D.INFERRED, D.UNKNOWN, D.REQUIRED))
        out["mep"] = _direction(
            "mep",
            goal="让机电容量与点位配得上这套空间，而不是后期打补丁",
            strategy=("按功能分区提资：湿区给排水、公共区暖通与消防、弱电随家具点位走；"
                      "负荷与管综由机电工程师计算"),
            deliverables=["点位与容量提资", "管综走向示意", "消防与排烟条件"],
            open_questions=["机电系统现状", "可用容量", "消防审批要求"],
            status=NEEDS_INPUT if unverified else PROPOSED,
            evidence=(e.evidence if e else "") or "未提供机电资料",
        )

    if "landscape" in active:
        program = _answer(project, "scope.landscape_program", "outdoor_program")
        out["landscape"] = _direction(
            "landscape",
            goal="把室外做成室内能借用的空间，而不是剩下的空地",
            strategy=("按功能定分区（停留 / 通行 / 种植 / 水景），竖向先定排水与标高，"
                      "再定铺装与种植"),
            deliverables=["景观分区图", "竖向与排水", "铺装与种植做法"],
            open_questions=[] if program else ["室外主要用途（铺装/种植/水景/屋顶花园）"],
            status=PROPOSED if program else NEEDS_INPUT,
            evidence=program or "尚未说明室外用途",
        )

    if "planning" in active:
        approval = _answer(project, "scope.planning_approval")
        out["planning"] = _direction(
            "planning",
            goal="先确认这个方案在规划上可不可行，再谈好不好看",
            strategy="按项目所在地的规划条件逐项核对指标；本系统只列条件与缺口，不出法定结论",
            deliverables=["规划指标核对表", "报批路径与前置条件"],
            open_questions=[] if approval else ["是否需要报建、已知的容积率/退线/限高"],
            status=PROPOSED if approval else NEEDS_INPUT,
            evidence=approval or "未说明报批要求",
        )
    return out


def summary_lines(directions: Dict[str, Dict[str, Any]]) -> List[str]:
    lines: List[str] = []
    for did, d in directions.items():
        flag = "" if d["status"] == PROPOSED else "（待补资料）"
        lines.append(f"- {d['label']}{flag}：{d['strategy'][:60]}")
    return lines


__all__ = ["for_concept", "summary_lines", "PROPOSED", "NEEDS_INPUT"]
