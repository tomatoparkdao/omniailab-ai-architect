"""Command line surface for the S1 intake engine.

Kept thin on purpose: every command loads the project, calls one function from
the intake package, saves the project back, and prints either text or JSON.
No logic lives here, so the engine can be driven from tests, scripts or an
agent without going through the CLI.

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..model import Project
from .diligence import (
    SourceEntry,
    UncertaintyItem,
    assess_sources,
    blocking_stages,
    precision_level,
    register_source,
    register_uncertainty,
    store_precision,
)
from .feasibility import run_feasibility
from .gate import check_baseline, decide_gate
from .interview import (
    answer_question,
    completeness,
    detect_start_mode,
    load_interview,
    mark_asked,
    next_questions,
    start_interview,
    summary as interview_summary,
)
from .needs import build_need_matrix
from .opportunities import find_opportunities
from .report import generate_bundle
from .profiles import PROFILES, profile_for

PRECISION_LABEL = {
    "diagnostic": "诊断级（只能做需求诊断与概念方向）",
    "schematic": "示意级（可出示意，尺寸须核验）",
    "authoritative_capable": "可出图级（有实测依据）",
}


def _project_path(value: str) -> Path:
    p = Path(value)
    if p.is_dir():
        p = p / "project.json"
    if not p.exists():
        raise SystemExit(f"项目文件不存在：{p}")
    return p


def _out_dir(args, project_path: Path) -> Path:
    if getattr(args, "out", ""):
        return Path(args.out)
    return project_path.parent / "out" / "S1"


def _print(payload: Any, as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))


# --------------------------------------------------------------------------
def _action_start(project: Project, args) -> Dict[str, Any]:
    state = start_interview(project, args.text or "", args.profile or "")
    qs = next_questions(project)
    mark_asked(project, [q.id for q in qs])
    return {
        "profile": state.profile_id,
        "profile_label": PROFILES.get(state.profile_id).label if state.profile_id in PROFILES else "",
        "start_mode": state.start_mode,
        "completeness": completeness(project),
        "questions": [q.to_dict() for q in qs],
        "note": "先问最关键的 1–3 个；已回答过的槽位不会再问。",
    }


def _action_ask(project: Project, args) -> Dict[str, Any]:
    limit = int(getattr(args, "limit", 3) or 3)
    qs = next_questions(project, limit=limit)
    mark_asked(project, [q.id for q in qs])
    if not qs:
        s = interview_summary(project)
        return {"questions": [], "completeness": s["completeness"],
                "note": ("关键问题已问完或全部标为暂不确定，可以进入分析"
                         if s["can_proceed"] else "仍有依赖未满足的问题")}
    return {"questions": [q.to_dict() for q in qs],
            "completeness": completeness(project)}


def _action_answer(project: Project, args) -> Dict[str, Any]:
    if not args.id:
        raise SystemExit("--id 必填（问题编号，见 ask 输出）")
    result = answer_question(project, args.id, args.value or "",
                             state_name=args.state or "answered")
    result["completeness"] = completeness(project)
    return result


def _action_register(project: Project, args) -> Dict[str, Any]:
    """Register a source document or an uncertainty item."""
    if args.uncertainty:
        item = UncertaintyItem(
            id=args.uid or f"U{len((project.meta.get('intake') or {}).get('uncertainty') or []) + 1:02d}",
            topic=args.topic or "scope",
            statement=args.statement or "",
            state=args.state or "unknown",
            affects=args.affects or "S3",
            action_needed=args.note or "",
        )
        register_uncertainty(project, item)
        return {"registered": item.to_dict()}
    entry = SourceEntry(
        id=args.uid or f"S{len((project.meta.get('intake') or {}).get('sources') or []) + 1:02d}",
        kind=args.kind or "pdf",
        file=args.file or "",
        revision=args.revision or "",
        confidence=args.confidence or "documented",
        note=args.note or "",
    )
    register_source(project, entry)
    return {"registered": entry.to_dict(), "assessment": assess_sources(project)}


def _action_status(project: Project, args) -> Dict[str, Any]:
    store_precision(project)
    s = interview_summary(project)
    s["precision"] = precision_level(project)
    s["precision_label"] = PRECISION_LABEL.get(s["precision"], "")
    s["sources"] = assess_sources(project)
    s["blocking"] = blocking_stages(project)
    s["baseline"] = check_baseline(project)
    s["interview"] = load_interview(project).to_dict()
    return s


def _action_analyze(project: Project, args) -> Dict[str, Any]:
    store_precision(project)
    out = _out_dir(args, _project_path(args.project))
    feas = run_feasibility(project)
    bundle = generate_bundle(project, out, summary_text=args.note or "")
    return {
        "bundle": bundle,
        "feasibility": {
            "verdict": feas["verdict"],
            "headline": feas["headline"],
            "counts": feas["counts"],
            "blocked_stages": feas["blocked_stages"],
        },
        "needs": {"rows": len(build_need_matrix(project)["rows"])},
        "opportunities": {"count": find_opportunities(project)["count"]},
        "precision": precision_level(project),
    }


def _action_gate(project: Project, args) -> Dict[str, Any]:
    decision = args.decision or "approved"
    out = _out_dir(args, _project_path(args.project))
    bundle = generate_bundle(project, out, summary_text=args.note or "")
    outcome = decide_gate(project, decision, by=args.by or "",
                          note=args.note or "", force=bool(args.force),
                          summary_path=str(out / "s1-approval-summary.md"))
    return {
        "outcome": outcome.to_dict(),
        "baseline_check": check_baseline(project),
        "summary_path": str(out / "s1-approval-summary.md"),
        "bundle_files": bundle["files"],
    }


ACTIONS = {
    "start": _action_start,
    "ask": _action_ask,
    "answer": _action_answer,
    "register": _action_register,
    "status": _action_status,
    "analyze": _action_analyze,
    "gate": _action_gate,
}


def cmd_intake(args) -> int:
    path = _project_path(args.project)
    project = Project.load(path)
    action = args.action or "status"
    fn = ACTIONS.get(action)
    if fn is None:
        raise SystemExit(f"未知 action '{action}'（可用：{'/'.join(ACTIONS)}）")

    payload = fn(project, args)
    project.save(path)
    payload.setdefault("project", str(path))
    payload.setdefault("action", action)

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    # --- human readable ---------------------------------------------------
    if action == "start":
        print(f"项目类型判定：{payload['profile_label']}（{payload['profile']}）")
        print(f"启动方式：{payload['start_mode']}　完整度："
              f"{payload['completeness']['ratio'] * 100:.0f}%")
        print()
        for q in payload["questions"]:
            print(f"[{q['priority']}] {q['id']}")
            print(f"  {q['text']}")
            if q["why"]:
                print(f"  为什么问：{q['why']}")
            print()
        if not payload["questions"]:
            print("暂无必须追问的问题，可以直接 --action analyze。")
    elif action == "ask":
        if not payload["questions"]:
            print(payload["note"])
        for q in payload["questions"]:
            print(f"[{q['priority']}] {q['id']}：{q['text']}")
    elif action == "answer":
        print(f"已记录 {payload['question_id']}：{payload['value'] or '（暂不确定）'}")
        print(f"完整度：{payload['completeness']['ratio'] * 100:.0f}%")
        if payload.get("requires_change_analysis"):
            print("⚠ " + str(payload.get("note", "")))
    elif action == "register":
        print(json.dumps(payload["registered"], ensure_ascii=False, indent=2))
    elif action == "status":
        print(f"项目类型：{payload['profile_label']}　启动方式：{payload['start_mode_label']}")
        print(f"完整度：{payload['completeness']['ratio'] * 100:.0f}%"
              f"（{payload['completeness']['verdict']}）")
        print(f"已答 {payload['answered']} 项，暂不确定 {len(payload['unknown'])} 项")
        print(f"精度：{payload['precision_label']}")
        if payload["pending_critical"]:
            print("仍需关键信息：" + "、".join(payload["pending_critical"]))
        if payload["blocking"]:
            print("阻断：")
            for sid, reasons in payload["blocking"].items():
                print(f"  {sid}: {reasons[0]}")
        print(f"基准：{payload['baseline']['reason']}")
    elif action == "analyze":
        b = payload["bundle"]
        f = payload["feasibility"]
        print(f"S1 成果包已生成：{b['dir']}")
        for name in b["files"]:
            print(f"  - {name}")
        print()
        print(f"可行性：{f['headline']}")
        print(f"冲突：阻断 {f['counts']['blocker']} / 重要 {f['counts']['major']} / "
              f"次要 {f['counts']['minor']} / 待核实 {f['counts']['info']}")
        print(f"设计机会：{payload['opportunities']['count']} 项　"
              f"需求行：{payload['needs']['rows']} 条")
        print(f"精度：{PRECISION_LABEL.get(payload['precision'], payload['precision'])}")
    elif action == "gate":
        o = payload["outcome"]
        print(f"G1 决策：{o['decision_label']}")
        print(f"阶段状态：{o['stage_status']}")
        for n in o["notes"]:
            print(f"  · {n}")
        print(f"摘要：{payload['summary_path']}")
    return 0


def add_parser(sub) -> None:
    sp = sub.add_parser("intake", help="S1 智能项目启动：访谈 / 资料 / 可行性 / 设计机会 / G1")
    sp.add_argument("--project", required=True, help="项目目录或 project.json")
    sp.add_argument("--action", default="status",
                    help="start / ask / answer / register / status / analyze / gate")
    sp.add_argument("--text", default="", help="start：业主的首句需求")
    sp.add_argument("--profile", default="", help="start：强制指定项目类型")
    sp.add_argument("--limit", type=int, default=3, help="ask：本轮问题数（最多 3）")
    sp.add_argument("--id", default="", help="answer：问题编号")
    sp.add_argument("--value", default="", help="answer：回答内容")
    sp.add_argument("--state", default="answered",
                    help="answer：answered / unknown / deferred")
    sp.add_argument("--uncertainty", action="store_true", help="register：登记不确定项")
    sp.add_argument("--kind", default="pdf", help="register：资料类型")
    sp.add_argument("--file", default="", help="register：文件路径或名称")
    sp.add_argument("--revision", default="", help="register：文件版本")
    sp.add_argument("--confidence", default="documented", help="register：可信度")
    sp.add_argument("--uid", default="", help="register：自定义编号")
    sp.add_argument("--topic", default="", help="register：不确定项主题")
    sp.add_argument("--statement", default="", help="register：不确定事项描述")
    sp.add_argument("--affects", default="", help="register：影响的阶段")
    sp.add_argument("--note", default="", help="备注")
    sp.add_argument("--out", default="", help="analyze/gate：成果目录")
    sp.add_argument("--decision", default="approved",
                    help="gate：approved / revision_requested / blocked")
    sp.add_argument("--by", default="", help="gate：确认人")
    sp.add_argument("--force", action="store_true", help="gate：存在阻断项时强制通过")
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=cmd_intake)
