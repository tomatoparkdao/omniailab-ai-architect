"""`concept` 子命令：S2 的全部动作。

与 `run --stage S2` 共用同一个 `generate_bundle()`，所以两条入口不会给出
不同的方案。这里多做的是交互动作：选定、提交 G2、查看交接、补出提案。

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..model import Project
from . import (
    approval_summary,
    assess_gate,
    check_baseline,
    decide_gate,
    generate_bundle,
    lock_style_for,
    select,
    status,
)
from . import handoff as handoff_mod

ACTIONS = ("generate", "status", "select", "gate", "handoff", "deck")


def _load(path: str) -> Project:
    p = Path(path)
    f = p / "project.json" if p.is_dir() else p
    return Project.load(f)


def _out_dir(args: Any, project: Project) -> Path:
    base = getattr(args, "out", None)
    if base:
        return Path(base)
    return Path(args.project) / "out" / "S2"


def _print(payload: Dict[str, Any], action: str) -> None:
    if action == "generate":
        print(f"概念方向 {payload.get('count', 0)} 套　"
              f"项目类型 {payload.get('profile', '')}　精度 {payload.get('precision', '')}")
        for cid, role in (payload.get("roles") or {}).items():
            print(f"  · {cid}　{role}")
        if payload.get("suggested"):
            print(f"  建议：{payload['suggested']}（需业主在 G2 明确选定 concept_id）")
        files = payload.get("files") or {}
        print("  成果：")
        for key in ("concept_options", "comparison", "presentation", "g2_summary"):
            if files.get(key):
                print(f"    {key}: {files[key]}")
        deck = payload.get("deck") or {}
        if deck:
            print(f"  提案：{deck.get('slides')} 页 / {deck.get('backend')} / "
                  f"{deck.get('size_bytes', 0) / 1024:.0f} KB")
        visual = payload.get("visual") or {}
        if visual:
            print(f"  概念视觉：平台 {visual.get('platform_state')}　"
                  f"已生成 {visual.get('generated')}　待平台 {visual.get('deferred')}")
        for w in (payload.get("warnings") or [])[:4]:
            print(f"  ⚠ {w}")

    elif action == "status":
        print(f"项目 {payload['project_id']}　r{payload['revision']}")
        print(f"  已生成方向：{'、'.join(payload['concept_ids']) or '无'}")
        print(f"  已选定：{payload.get('selected') or '未选定'}"
              f"　建议：{payload.get('suggested') or '—'}")
        gate = payload.get("gate") or {}
        print(f"  G2 可批准：{'是' if gate.get('can_approve') else '否'}")
        for r in gate.get("blocked_reasons") or []:
            print(f"    ✗ {r}")
        for c in gate.get("conditions") or []:
            print(f"    · 条件：{c}")
        base = payload.get("baseline") or {}
        print(f"  概念基准：{'已形成' if base.get('has_baseline') else '无'}"
              f"　变化：{base.get('reason', '—')}")
        lock = payload.get("style_lock") or {}
        if lock:
            print(f"  风格锁定：{' + '.join(lock.get('labels') or [])}（r{lock.get('revision')}）")
        print(f"  交接：{payload.get('handoff_status')}")

    elif action == "select":
        print(f"已选定：{payload.get('selected')}（原：{payload.get('previous') or '无'}）")
        if payload.get("note"):
            print(f"  ⚠ {payload['note']}")

    elif action == "gate":
        o = payload.get("outcome") or {}
        print(f"G2 决策：{o.get('decision_label')}　来源：{o.get('source_label')}")
        print(f"阶段状态：{o.get('stage_status')}")
        for n in o.get("notes") or []:
            print(f"  · {n}")
        if payload.get("summary_path"):
            print(f"摘要：{payload['summary_path']}")

    elif action == "handoff":
        h = payload.get("handoff") or {}
        print(f"状态：{h.get('status')}　概念：{h.get('concept_id') or '—'} "
              f"{h.get('concept_name') or ''}")
        sp = h.get("spatial") or {}
        print(f"  平面策略：{sp.get('plan_strategy') or '无'}"
              f"（{'支持' if sp.get('plan_strategy_supported') else '需专用深化'}）")
        for k in ("adjacency", "separation"):
            for item in h.get(k) or []:
                print(f"  {k}: {item}")
        if payload.get("path"):
            print(f"文件：{payload['path']}")

    elif action == "deck":
        print(f"提案已写出：{payload.get('pptx')}")
        print(f"  页数 {payload.get('slides')}　问题 {len(payload.get('issues') or [])}")


def run(args: Any) -> int:
    project = _load(args.project)
    action = getattr(args, "action", "generate")
    out = _out_dir(args, project)

    if action == "generate":
        payload = generate_bundle(
            project, out, limit=int(getattr(args, "limit", 3) or 3),
            pre_gate=bool(getattr(args, "explore", False)),
            with_deck=not bool(getattr(args, "no_deck", False)),
            submit=bool(getattr(args, "submit", False)),
            authorize=bool(getattr(args, "authorize", False)),
            max_cost=getattr(args, "max_cost", None),
            project_dir=args.project,
        )
        project.save(Path(args.project) / "project.json")
        if getattr(args, "json", False):
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            _print(payload, action)
        return 0

    if action == "status":
        payload = status(project)
        print(json.dumps(payload, ensure_ascii=False, indent=2) if getattr(args, "json", False)
              else "", end="")
        if not getattr(args, "json", False):
            _print(payload, action)
        return 0

    if action == "select":
        cid = getattr(args, "concept", "") or ""
        if not cid:
            raise SystemExit("--concept 必填（例如 C-B）")
        payload = select(project, cid)
        project.save(Path(args.project) / "project.json")
        _print(payload, action)
        return 0

    if action == "gate":
        decision = getattr(args, "decision", "approved") or "approved"
        ack = [a.strip() for a in (getattr(args, "acknowledge", "") or "").split(",") if a.strip()]
        # 重新出一次摘要，让摘要与本次决策一致
        summary_path = out / "g2-approval-summary.md"
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary_path.write_text(approval_summary(project, getattr(args, "note", "") or "") + "\n",
                                encoding="utf-8")
        outcome = decide_gate(project, decision, by=getattr(args, "by", "") or "",
                             note=getattr(args, "note", "") or "",
                             source=getattr(args, "source", "owner") or "owner",
                             acknowledge=ack, force=bool(getattr(args, "force", False)),
                             summary_path=str(summary_path))
        if outcome.decision == "approved" and outcome.source == "owner":
            try:
                lock_style_for(project, out)
            except Exception as exc:  # never hide a lock failure
                outcome.notes.append(f"风格锁定写入失败：{type(exc).__name__}: {exc}")
        project.save(Path(args.project) / "project.json")
        _print({"outcome": outcome.to_dict(), "summary_path": str(summary_path)}, action)
        return 0 if outcome.decision == "approved" else 1

    if action == "handoff":
        h = handoff_mod.load_for(project)
        path = ""
        if h.get("concept_id"):
            path = handoff_mod.write(h, out)
        payload = {"handoff": h, "path": path}
        if getattr(args, "json", False):
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            _print(payload, action)
        return 0

    if action == "deck":
        from . import deck as deck_mod

        state = project.meta.get("concept") or {}
        options = state.get("options") or {}
        if not options.get("concepts"):
            raise SystemExit("尚未生成概念方案：先运行 --action generate")
        from .context import build_context

        ctx = build_context(project, require_gate=False)
        deck = deck_mod.build(project, ctx, options, state.get("comparison") or {},
                              {}, {})
        info = deck_mod.write(deck, out)
        payload = {"pptx": info["pptx"]["path"], "slides": info["slide_count"],
                   "issues": info["issues"]}
        _print(payload, action)
        return 0

    raise SystemExit(f"未知动作 {action}；可用：{'、'.join(ACTIONS)}")


def register(sub) -> None:
    sp = sub.add_parser("concept", help="S2 概念方案：生成 / 选定 / G2 / 交接")
    sp.add_argument("--project", required=True)
    sp.add_argument("--action", default="generate", choices=ACTIONS)
    sp.add_argument("--out", default=None, help="成果目录（默认 <project>/out/S2）")
    sp.add_argument("--limit", type=int, default=3, help="方向数量（2–3）")
    sp.add_argument("--explore", action="store_true",
                    help="G1 未确认时生成本轮探索稿（不可锁定、不可作为正式依据）")
    sp.add_argument("--no-deck", action="store_true", help="跳过 PPTX")
    sp.add_argument("--submit", action="store_true", help="向 OmniAiLab 提交概念视觉任务")
    sp.add_argument("--authorize", action="store_true",
                    help="确认授权联网与计费（必须与 --submit 同时使用）")
    sp.add_argument("--max-cost", type=float, default=None, help="本次提交的费用上限")
    sp.add_argument("--concept", default="", help="select：概念编号，如 C-B")
    sp.add_argument("--decision", default="approved",
                    choices=("approved", "revision_requested", "blocked"))
    sp.add_argument("--source", default="owner", choices=("owner", "demo"))
    sp.add_argument("--by", default="", help="确认人")
    sp.add_argument("--note", default="")
    sp.add_argument("--acknowledge", default="")
    sp.add_argument("--force", action="store_true")
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=run)


__all__ = ["ACTIONS", "register", "run"]
