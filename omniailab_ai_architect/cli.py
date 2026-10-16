"""Command line interface.

    python -m omniailab_ai_architect doctor
    python -m omniailab_ai_architect stages
    python -m omniailab_ai_architect status    --project projects/demo-120
    python -m omniailab_ai_architect route     --project projects/demo-120 "帮我出施工图"
    python -m omniailab_ai_architect run       --project projects/demo-120 --all --assume-approval
    python -m omniailab_ai_architect confirm   --project projects/demo-120 --stage S3 --by 业主
    python -m omniailab_ai_architect change    --project projects/demo-120 "我不喜欢客厅的电视背景墙"
    python -m omniailab_ai_architect demo      --out out

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import __version__
from .adapters import DxfAdapter, doctor
from .changes import analyse
from .errors import OmniArchitectError, ValidationError
from .model import load_project, summary, validate_all
from .paths import EXAMPLES, PROJECTS, ROOT, ensure_output_dir
from .registry import criteria_report, registry_report
from .routing import route
from .stage_state import markdown as stage_markdown
from .stage_state import progress
from .stages import STAGES, validate_catalog
from .workflow import DEFAULT_STAGES, STAGE_SLUG, StageRunner


# --------------------------------------------------------------------------
def _load(args) -> Any:
    if not getattr(args, "project", None):
        raise SystemExit("--project is required")
    p = Path(args.project)
    if not p.is_absolute():
        cand = ROOT / p
        p = cand if cand.exists() else p
    if p.is_dir():
        p = p / "project.json"
    if not p.exists():
        raise SystemExit(f"project file not found: {p}")
    return load_project(p)


def _print_json(payload: Any) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def _write(payload: Any, out: Optional[str]) -> None:
    if not out:
        return
    p = Path(out)
    p.parent.mkdir(parents=True, exist_ok=True)
    if p.suffix == ".md":
        p.write_text(payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False, indent=2),
                     encoding="utf-8")
    else:
        p.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[written] {p}")


# --------------------------------------------------------------------------
def cmd_doctor(args) -> int:
    rep = doctor()
    if args.json:
        _print_json(rep)
        return 0
    print(f"OmniArchitect v{__version__} — 工具环境检测")
    print(f"宿主：{rep['host']['platform']}　Python {rep['host']['python']}\n")
    for row in rep["adapters"]:
        mark = "可用" if row["available"] else "缺失"
        ver = f"　{row['version']}" if row["version"] else ""
        print(f"[{mark}] {row['adapter']:<10}{ver}")
        if row["executable"]:
            print(f"         执行器：{row['executable']}")
        for n in row["notes"]:
            print(f"         · {n}")
        if row["degraded_to"]:
            print(f"         降级方案：{row['degraded_to']}")
    print(f"\n可用：{', '.join(rep['available']) or '（无）'}")
    print(f"缺失：{', '.join(rep['unavailable']) or '（无）'}")
    return 0


def cmd_stages(args) -> int:
    if args.json:
        _print_json([s.to_dict() for s in STAGES])
        return 0
    print("OmniArchitect 八阶段专业工作流\n")
    for s in STAGES:
        flags = []
        if s.drawing_depth:
            flags.append(f"图纸深度 {s.drawing_depth}")
        if s.modeling_allowed:
            flags.append("允许建模")
        if s.cost_estimate:
            flags.append("含动态造价")
        print(f"{s.code} {s.name}")
        print(f"   目的：{s.purpose}")
        print(f"   能力：{', '.join(s.skills)}")
        print(f"   交付：{', '.join(s.deliverables)}")
        print(f"   门禁：{s.gate.id} {s.gate.label}（{s.gate.approver}）")
        if flags:
            print(f"   标记：{' / '.join(flags)}")
        print()
    issues = validate_catalog()
    print("目录自检：" + ("通过" if not issues else f"{len(issues)} 项问题"))
    for i in issues:
        print(f"  - {i}")
    return 0


def cmd_registry(args) -> int:
    rep = registry_report()
    if args.json:
        _print_json(rep)
        return 0
    print(f"专业能力 {rep['capability_count']} 项，映射到 {rep['stage_count']} 个阶段\n")
    for r in rep["capabilities"]:
        stages = ",".join(r["stages"])
        src = "" if r["source"] == "OmniAiLab" else f"  [{r['source']}]"
        print(f"  {r['slug']:<34} {stages:<22}{src}")
    print("\n原始 18 项能力 → 阶段映射")
    for legacy, sts in rep["legacy_coverage"].items():
        print(f"  {legacy:<24} → {','.join(sts)}")
    if rep["catalog_issues"]:
        print(f"\n自检问题 {len(rep['catalog_issues'])} 项")
        for i in rep["catalog_issues"]:
            print(f"  - {i}")
    return 0


def cmd_criteria(args) -> int:
    rep = criteria_report()
    if args.json:
        _print_json(rep)
        return 0
    a = rep["attribution"]
    print(f"设计判据体系　（{a['owner']} · 开发者 {a['developer']}）")
    print(f"署名：{rep['signature']}\n")
    for slug, info in rep["criteria"].items():
        stages = ",".join(info["applies_to_stages"]) or "—"
        print(f"  {slug:<28} → 阶段 {stages}")
        for item in info["criteria"][:3]:
            print(f"      · {item}")
    s = rep["summary"]
    print(f"\n判据集 {s['criteria_sets']} 组，覆盖阶段 {', '.join(s['stages_touched'])}")
    print(f"不参与设计生成：{', '.join(s['not_applied']) or '（无）'}")
    print(f"说明：{s['note']}")
    return 0


def cmd_status(args) -> int:
    project = _load(args)
    if args.json:
        _print_json(progress(project))
        return 0
    print(stage_markdown(project))
    return 0


def cmd_route(args) -> int:
    project = _load(args) if getattr(args, "project", None) else None
    plan = route(args.request, project)
    if args.json:
        _print_json(plan.to_dict())
        return 0
    print(plan.markdown())
    return 0


def cmd_verify(args) -> int:
    project = _load(args)
    issues: List[str] = []
    status = "ok"
    try:
        validate_all(project)
    except ValidationError as exc:
        issues = exc.issues
        status = "failed"
    payload = {
        "status": status,
        "issues": issues,
        "summary": summary(project),
        "stage_progress": progress(project),
        "catalog_issues": validate_catalog(),
        "dxf_adapter": DxfAdapter().preflight().to_dict(),
    }
    if args.json:
        _print_json(payload)
    else:
        print(f"校验：{status}　使用面积 {payload['summary']['usable_area_m2']} m²")
        for i in issues:
            print(f"  - {i}")
        print(f"阶段进度：{payload['stage_progress']['percent']}%，"
              f"当前 {payload['stage_progress']['current_name']}")
    return 0 if status == "ok" else 1


def cmd_run(args) -> int:
    project = _load(args)
    out = ensure_output_dir(args.out, "out")
    runner = StageRunner(
        project, out, level_id=args.level, scheme_variant=args.scheme,
        assume_approval=args.assume_approval, project_dir=Path(args.project),
    )
    if args.stage:
        targets = args.stage if isinstance(args.stage, list) else [args.stage]
        for s in targets:
            if s not in DEFAULT_STAGES:
                raise SystemExit(f"unknown stage '{s}' (expected {'/'.join(DEFAULT_STAGES)})")
            runner.run_stage(s, confirm=args.assume_approval)
        from datetime import datetime

        runner.manifest.finished = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        runner.manifest.revision = project.revision
        runner.manifest.progress = progress(project)
        runner._finish()
    elif args.all:
        runner.run_all(confirm_all=args.assume_approval)
    else:
        runner.run_until_gate(start=args.from_stage)

    m = runner.manifest
    if args.json:
        _print_json(m.to_dict())
    else:
        print(f"运行 {m.run_id}")
        for o in m.outcomes:
            print(f"  [{o.status:<10}] {o.stage_name}　{', '.join(o.skills[:3])}")
            for n in o.notes[:3]:
                print(f"        · {n}")
            if o.error:
                print(f"        错误：{o.error}")
            if o.next_action:
                print(f"        下一步：{o.next_action}")
        if m.blocks:
            print("\n阻断 / 失败：")
            for b in m.blocks:
                print(f"  - {b}")
        print(f"\n输出：{m.out_dir}")
        print(f"阶段进度：{m.progress.get('percent')}%")
    return 0 if not m.blocks else 1


def cmd_confirm(args) -> int:
    project = _load(args)
    out = ensure_output_dir(args.out, "out")
    runner = StageRunner(project, out, level_id=args.level, scheme_variant=args.scheme,
                         project_dir=Path(args.project))
    st = runner.confirm(args.stage, by=args.by or "业主", note=args.note or "")
    print(f"{args.stage} → {st['status']}（{st['confirmed_by']}）")
    return 0


def cmd_reject(args) -> int:
    project = _load(args)
    out = ensure_output_dir(args.out, "out")
    runner = StageRunner(project, out, level_id=args.level, scheme_variant=args.scheme,
                         project_dir=Path(args.project))
    st = runner.reject(args.stage, reason=args.reason or "")
    print(f"{args.stage} → {st['status']}：{st['note']}")
    return 0


def cmd_change(args) -> int:
    project = _load(args)
    rep = analyse(project, args.request, apply=not args.dry_run)
    if args.json:
        _print_json(rep.to_dict())
    else:
        print(rep.markdown())
    if not args.dry_run:
        p = Path(args.project)
        p = (p if p.is_dir() else p.parent) / "project.json"
        project.save(p)
        print(f"\n[已写回] {p}")
    _write(rep.to_dict(), args.out)
    return 0


def cmd_demo(args) -> int:
    from .demo import build_demo_project

    d = PROJECTS / "demo-120"
    project = build_demo_project(d)
    print(f"示例项目已生成：{d / 'project.json'}")
    out = ensure_output_dir(args.out, "out")
    runner = StageRunner(project, out, level_id="L1", scheme_variant=args.scheme,
                         assume_approval=True, project_dir=d)
    runner.run_all(confirm_all=True)
    m = runner.manifest
    for o in m.outcomes:
        print(f"  [{o.status:<10}] {o.stage_name}　{', '.join(o.skills[:3])}")
        for n in o.notes[:4]:
            print(f"        · {n}")
    print(f"\n输出：{m.out_dir}")
    print(f"阶段进度：{m.progress.get('percent')}%")
    return 0 if not m.blocks else 1


# --------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="omniailab-ai-architect",
        description="OmniArchitect — AI 建筑 / 室内设计总设计师（八阶段工作流）",
    )
    p.add_argument("--version", action="version", version=f"OmniArchitect {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    def add_project(sp, required: bool = True):
        sp.add_argument("--project", required=required, help="项目目录或 project.json")
        sp.add_argument("--level", default=None, help="楼层 id")
        sp.add_argument("--scheme", default="A", help="方案编号 A/B")
        sp.add_argument("--json", action="store_true")
        return sp

    sp = sub.add_parser("doctor", help="检测本机工具链")
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=cmd_doctor)

    sp = sub.add_parser("stages", help="打印八阶段模型")
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=cmd_stages)

    sp = sub.add_parser("registry", help="打印专业能力目录与阶段映射")
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=cmd_registry)

    sp = sub.add_parser("criteria", help="设计判据体系（自有口径）")
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=cmd_criteria)

    sp = add_project(sub.add_parser("status", help="阶段推进状态"))
    sp.set_defaults(func=cmd_status)

    sp = add_project(sub.add_parser("verify", help="模型校验"))
    sp.set_defaults(func=cmd_verify)

    sp = add_project(sub.add_parser("route", help="把请求路由成阶段计划"))
    sp.add_argument("request", help="自然语言请求")
    sp.set_defaults(func=cmd_route)

    sp = add_project(sub.add_parser("run", help="执行阶段"))
    sp.add_argument("--stage", action="append", help="只跑指定阶段，可多次")
    sp.add_argument("--from-stage", default=None, help="从该阶段开始，跑到第一个门禁")
    sp.add_argument("--all", action="store_true", help="跑到 S8")
    sp.add_argument("--assume-approval", action="store_true", help="假设门禁已通过")
    sp.add_argument("--out", default=None)
    sp.set_defaults(func=cmd_run)

    sp = add_project(sub.add_parser("confirm", help="确认阶段门禁"))
    sp.add_argument("--stage", required=True)
    sp.add_argument("--by", default="业主")
    sp.add_argument("--note", default="")
    sp.add_argument("--out", default=None)
    sp.set_defaults(func=cmd_confirm)

    sp = add_project(sub.add_parser("reject", help="阶段成果不通过，退回返工"))
    sp.add_argument("--stage", required=True)
    sp.add_argument("--reason", default="")
    sp.add_argument("--out", default=None)
    sp.set_defaults(func=cmd_reject)

    sp = add_project(sub.add_parser("change", help="设计变更影响分析"))
    sp.add_argument("request", help="变更描述，例如：我不喜欢客厅的电视背景墙")
    sp.add_argument("--dry-run", action="store_true", help="只分析，不改动模型")
    sp.add_argument("--out", default=None)
    sp.set_defaults(func=cmd_change)

    sp = sub.add_parser("demo", help="生成示例项目并跑通全流程")
    sp.add_argument("--out", default=None)
    sp.add_argument("--scheme", default="A")
    sp.set_defaults(func=cmd_demo)

    # v1.1 surface: compliance, providers, tools, knowledge, decks, scenarios
    from .cli_v11 import register as _register_v11

    _register_v11(sub)

    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return int(args.func(args) or 0)
    except OmniArchitectError as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 2
    except SystemExit:
        raise
    except Exception as exc:  # pragma: no cover
        print(f"未预期错误：{type(exc).__name__}: {exc}", file=sys.stderr)
        return 3
