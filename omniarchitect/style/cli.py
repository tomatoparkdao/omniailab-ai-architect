"""Command line interface for the style intelligence engine.

Usage examples::

    python -m omniarchitect style validate --all
    python -m omniarchitect style catalog
    python -m omniarchitect style search --tags minimal,warm --space 住宅
    python -m omniarchitect style recommend --space 住宅 --area 120 --budget mid
    python -m omniarchitect style lock --style italian-minimal --out out
    python -m omniarchitect style compile --style italian-minimal --target interior-render \\
        --space 客厅 --width 4200 --depth 6000 --ceiling 2800 --locked --out out
    python -m omniarchitect style submit --compile-out out/prompt.json --out out
    python -m omniarchitect style hooks --stage S2
    python -m omniarchitect style providers

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from . import __version__
from .catalog import load_catalog
from .compiler import CompiledPrompt, SpaceBrief, compile_prompt, compile_view_set
from .resources import PROMPT_TARGETS, project_version
from .provider_bridge import NATIVE_PLATFORM, NOT_IMPLEMENTED_AS_FALLBACK, probe, submit
from .recommender import MAINTENANCE_PROFILE, RecommendRequest, recommend
from .validation import check_style_dir, check_style_file
from .hooks import all_hooks, comparison_data, design_intent_check, hook, material_spec, style_space_check


def _dump(obj: Any) -> None:
    print(json.dumps(obj, ensure_ascii=False, indent=2))


def _brief_from_args(a: argparse.Namespace) -> SpaceBrief:
    openings = [s for s in (getattr(a, "openings", "") or "").split("|") if s]
    return SpaceBrief(
        space_name=getattr(a, "space", "") or "",
        area_m2=getattr(a, "area", None),
        width_mm=getattr(a, "width", None),
        depth_mm=getattr(a, "depth", None),
        ceiling_mm=getattr(a, "ceiling", None),
        orientation=getattr(a, "orientation", "") or "",
        openings=openings,
        existing_elements=[s for s in (getattr(a, "keep", "") or "").split("|") if s],
        to_change=[s for s in (getattr(a, "change", "") or "").split("|") if s],
        materials_override=[s for s in (getattr(a, "materials", "") or "").split("|") if s],
        lighting_override=[s for s in (getattr(a, "lighting", "") or "").split("|") if s],
        furniture_needs=[s for s in (getattr(a, "needs", "") or "").split("|") if s],
        camera=getattr(a, "camera", "") or "",
        references=[s for s in (getattr(a, "refs", "") or "").split("|") if s],
    )


def _style_ids(raw: str) -> List[str]:
    return [s.strip() for s in (raw or "").split(",") if s.strip()]


# --------------------------------------------------------------------------
def cmd_validate(a: argparse.Namespace) -> int:
    if a.style:
        from .resources import STYLE_DIR
        p = STYLE_DIR / f"{a.style}.json"
        if not p.exists():
            print(f"找不到风格文件：{p}", file=sys.stderr)
            return 1
        problems = check_style_file(p)
        if problems:
            print(f"{a.style}.json 校验未通过：")
            for x in problems:
                print(f"  - {x}")
            return 1
        print(f"{a.style}.json 校验通过")
        return 0
    bad = check_style_dir()
    cat = load_catalog()
    print(f"风格数据校验：共 {len(cat)} 条，问题 {len(bad)} 条")
    for name, problems in bad.items():
        print(f"  ✗ {name}")
        for x in problems:
            print(f"      - {x}")
    return 1 if bad else 0


def cmd_catalog(a: argparse.Namespace) -> int:
    cat = load_catalog()
    rep = cat.report()
    if a.json:
        _dump(rep)
        return 0
    print(f"风格目录　{rep['count']} 条　版本 {rep['version']}")
    print(f"  族：{'、'.join(f'{k}({v})' for k, v in rep['families'].items())}")
    print(f"  标签数：{rep['tag_count']}　未通过校验：{len(rep['invalid'])}")
    print(f"  说明：{rep['note']}")
    if a.list:
        print()
        for row in cat.summary_table():
            print(f"  {row['style_id']:<26} {row['style']:<34} [{row['family']}/{row['tier']}]")
    return 0


def cmd_search(a: argparse.Namespace) -> int:
    cat = load_catalog()
    hits = cat.search(tags=_style_ids(a.tags), family=a.family or "", stage=a.stage or "",
                      budget_tier=a.budget or "", space=a.space or "", text=a.text or "",
                      match_all_tags=a.all_tags, limit=a.limit or 0)
    if a.json:
        _dump([e.to_dict() for e in hits])
        return 0
    print(f"命中 {len(hits)} 条")
    for e in hits:
        print(f"  {e.style_id:<26} {e.label:<34} [{e.family}/{e.budget_tier}]")
        print(f"      {e.summary}")
    return 0


def cmd_show(a: argparse.Namespace) -> int:
    cat = load_catalog()
    style = cat.load_style(a.style)
    entry = cat.get(a.style)
    if a.json:
        _dump(style)
        return 0
    h = style.get("history_and_context") or {}
    print(f"{entry.label}　`{entry.style_id}`　[{entry.family}]")
    print(f"  时期：{h.get('period','')}　来源：{h.get('origin','')}")
    print(f"  概述：{h.get('summary','')}")
    print(f"  适用空间：{'、'.join(style.get('applicable_spaces') or [])}")
    print(f"  造价档位：{(style.get('budget_considerations') or {}).get('tier','')}")
    print(f"  维护强度：{MAINTENANCE_PROFILE.get(entry.style_id, ('未知',''))[0]}"
          f"（{MAINTENANCE_PROFILE.get(entry.style_id, ('',''))[1]}）")
    print(f"  兼容风格：{'、'.join(style.get('compatible_styles') or [])}")
    print("\n  空间原则：")
    for p in style.get("spatial_principles") or []:
        print(f"    · {p}")
    print("\n  材料：")
    for m in style.get("materials") or []:
        print(f"    · {m.get('name_zh')}（{m.get('finish','')}）— {m.get('application','')}")
    print("\n  色板：")
    for c in style.get("color_palette") or []:
        print(f"    · {c.get('hex')}  {c.get('name_zh')} — {c.get('usage','')}")
    return 0


def cmd_recommend(a: argparse.Namespace) -> int:
    req = RecommendRequest(
        space_type=a.space_type,
        area_m2=a.area,
        budget_tier=a.budget or "",
        location=a.location or "",
        preferences=_style_ids(a.prefer),
        maintenance=a.maintenance or "",
        stage=a.stage or "S2",
        avoid=_style_ids(a.avoid),
    )
    rs = recommend(req)
    if a.json:
        _dump(rs.to_dict())
        return 0
    print(rs.render())
    if a.out:
        out = Path(a.out)
        out.mkdir(parents=True, exist_ok=True)
        (out / "style-recommendation.md").write_text(rs.render(), encoding="utf-8")
        print(f"\n已写入：{out / 'style-recommendation.md'}", file=sys.stderr)
    return 0


def cmd_lock(a: argparse.Namespace) -> int:
    req = RecommendRequest(space_type=a.space_type, area_m2=a.area,
                           budget_tier=a.budget or "", location=a.location or "",
                           preferences=_style_ids(a.prefer), maintenance=a.maintenance or "")
    rs = recommend(req)
    if a.style not in {o.style_id for o in rs.options}:
        # Allow locking anything in the catalogue, but say so plainly.
        cat = load_catalog()
        if a.style not in cat:
            print(f"未知风格：{a.style}", file=sys.stderr)
            return 1
        payload = {
            "locked_style": a.style,
            "style_label": cat.get(a.style).label,
            "revision": a.revision,
            "locked_by": a.by or "业主",
            "request": req.to_dict(),
            "options_considered": [o.to_dict() for o in rs.options],
            "note": "该风格不在本次三套推荐内，由用户直接指定。依然记录修订号，便于几何变更时重新评估。",
            "reversible": True,
        }
        out = Path(a.out)
        out.mkdir(parents=True, exist_ok=True)
        p = out / f"style-lock-r{a.revision}.json"
        p.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"已锁定（直接指定）：{a.style} → {p}")
        return 0
    payload = rs.lock(a.style, out_dir=a.out, revision=a.revision, by=a.by or "")
    print(f"已锁定：{payload['locked_style']} → {rs.lock_file}")
    return 0


def cmd_compile(a: argparse.Namespace) -> int:
    brief = _brief_from_args(a)
    prompt = compile_prompt(
        _style_ids(a.style), brief, target=a.target, stage=a.stage or "",
        revision=a.revision, locked=a.locked,
        user_needs=[s for s in (a.extra or "").split("|") if s],
        extra_negative=[s for s in (a.negative or "").split("|") if s],
        plan_confirmed=bool(getattr(a, "plan_confirmed", False)),
    )
    if a.json:
        _dump(prompt.to_dict())
        return 0
    print(prompt.to_markdown())
    if a.out:
        out = Path(a.out)
        out.mkdir(parents=True, exist_ok=True)
        md = out / f"prompt-{prompt.target}-{prompt.consistency_key}.md"
        md.write_text(prompt.to_markdown(frontmatter=True), encoding="utf-8")
        js = out / "prompt.json"
        js.write_text(prompt.to_json(), encoding="utf-8")
        print(f"\n已写入：{md}", file=sys.stderr)
        print(f"已写入：{js}", file=sys.stderr)
    return 0


def cmd_multiview(a: argparse.Namespace) -> int:
    """Compile several viewpoints that share one consistency key."""
    names = [s.strip() for s in (a.views or "整户型").split(",") if s.strip()]
    briefs = []
    for n in names:
        briefs.append(SpaceBrief(
            space_name=n, width_mm=a.width, depth_mm=a.depth, ceiling_mm=a.ceiling,
            orientation=a.orientation or "", camera=a.camera or "",
            furniture_needs=[s for s in (a.needs or "").split("|") if s],
        ))
    rep = compile_view_set(_style_ids(a.style), briefs, target=a.target or "multi-view",
                           revision=a.revision, locked=a.locked,
                           plan_confirmed=bool(getattr(a, "plan_confirmed", False)))
    if a.json:
        _dump(rep)
        return 0
    print(f"多机位编译　{rep['view_count']} 个机位　一致性指纹：{rep['consistency_key'] or '（不一致）'}")
    print(f"  {rep['note']}")
    for p in rep["prompts"]:
        print(f"  · {p['structured']['space'].get('space_name','')}  {p['consistency_key']}")
    if a.out:
        out = Path(a.out)
        out.mkdir(parents=True, exist_ok=True)
        (out / "prompt-multiview.json").write_text(
            json.dumps(rep, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"\n已写入：{out / 'prompt-multiview.json'}", file=sys.stderr)
    return 0


def cmd_submit(a: argparse.Namespace) -> int:
    src = Path(a.compile_out)
    if not src.exists():
        print(f"找不到编译产物：{src}", file=sys.stderr)
        return 1
    data = json.loads(src.read_text(encoding="utf-8"))
    items = data["prompts"] if isinstance(data, dict) and "prompts" in data else [data]
    prompts: List[CompiledPrompt] = []
    for item in items:
        prompts.append(_prompt_from_dict(item))
    try:
        rep = submit(prompts, out_dir=a.out, project_dir=a.project, authorize=a.authorize)
    except ValueError as exc:
        # 平面未确认的配方不得排队：这属于"还不能花钱"，不是技术故障
        raise SystemExit(f"未提交：{exc}")
    if a.json:
        _dump(rep)
        return 0
    print(f"平台：{NATIVE_PLATFORM}　状态：{rep['platform_state']}")
    print(f"任务 {rep['job_count']} 个，待执行 {rep['deferred_count']} 个")
    if rep["missing"]:
        print("  平台缺少：" + "；".join(rep["missing"]))
    print(f"  第三方回退：forbidden（本系统不提供任何第三方创作入口）")
    print(f"  任务包：{rep['jobs_file']}")
    print(f"  说明：{rep['brief_file']}")
    return 0 if rep["platform_state"] == "connected" or rep["deferred_count"] == rep["job_count"] else 1


def _prompt_from_dict(d: Dict[str, Any]) -> CompiledPrompt:
    return CompiledPrompt(
        target=d.get("target", ""),
        stage=d.get("stage", ""),
        style_ids=list(d.get("style_ids") or []),
        style_labels=list(d.get("style_labels") or []),
        consistency_key=d.get("consistency_key", ""),
        revision=int(d.get("revision") or 1),
        positive_zh=(d.get("positive") or {}).get("zh", ""),
        positive_en=(d.get("positive") or {}).get("en", ""),
        negative_zh=list((d.get("negative") or {}).get("zh") or []),
        negative_en=list((d.get("negative") or {}).get("en") or []),
        structured=dict(d.get("structured") or {}),
        geometry_rules=list(d.get("geometry_preservation") or []),
        lock_note=d.get("style_lock", ""),
        mandate=list(d.get("verification_mandate") or []),
        warnings=list(d.get("warnings") or []),
        recipe_id=d.get("recipe_id", ""),
        gate=dict(d.get("gate") or {}),
        text_overlay=list(d.get("text_overlay") or []),
    )


def cmd_hooks(a: argparse.Namespace) -> int:
    if a.stage:
        _dump(hook(a.stage)) if a.json else _print_hook(hook(a.stage))
        return 0
    if a.json:
        _dump(all_hooks())
        return 0
    for h in all_hooks():
        _print_hook(h)
        print()
    return 0


def _print_hook(h: Dict[str, Any]) -> None:
    print(f"【{h['stage']}】{h['name']}")
    for x in h["actions"]:
        print(f"  · {x}")
    if h["api"]:
        print(f"  API：{', '.join(h['api'])}")
    if h["produces"]:
        print(f"  产物：{', '.join(h['produces'])}")
    if h.get("gate"):
        print(f"  门禁：{h['gate']}"
              + (f"（{h['gate_approver']}）" if h.get("gate_approver") else ""))
    if h.get("frame_source", {}).get("source_project"):
        fs = h["frame_source"]
        print(f"  契约：{fs['frame']} v{fs['source_version']}　"
              f"来源 {fs['source_project']}")
    if h["rule"]:
        print(f"  规则：{h['rule']}")


def cmd_space_check(a: argparse.Namespace) -> int:
    rep = style_space_check(a.style, _brief_from_args(a))
    if a.json:
        _dump(rep)
        return 0
    print(f"风格与空间关系检查：{rep['style']}")
    if rep["conflicts"]:
        print(f"  发现 {len(rep['conflicts'])} 项冲突：")
        for c in rep["conflicts"]:
            print(f"    ! {c}")
        print("  可选路径：")
        for p in rep["decision_paths"]:
            print(f"    · {p}")
        print(f"  {rep['rule']}")
        # 冲突是业务发现，不是命令失败：默认返回 0，需要门禁时用 --strict。
        return 1 if a.strict else 0
    print("  未发现冲突")
    for n in rep["notes"]:
        print(f"  · {n}")
    return 0


def cmd_materials(a: argparse.Namespace) -> int:
    subs = {}
    for pair in (a.substitute or "").split("|"):
        if "=" in pair:
            k, v = pair.split("=", 1)
            subs[k.strip()] = v.strip()
    rep = material_spec(a.style, substitutions=subs)
    if a.json:
        _dump(rep)
        return 0
    print(f"材料与照明规范：{rep['style']}")
    print("\n  材料：")
    for m in rep["materials"]:
        sub = f"　→ 替换为 {m['substituted_to']}" if m["substituted_to"] else ""
        print(f"    · {m['material_zh']}（{m['finish']}）— {m['application']}{sub}")
    print("\n  色板：")
    for c in rep["palette"]:
        print(f"    · {c['hex']}  {c['name_zh']} — {c['usage']}")
    print("\n  照明：")
    ls = rep["lighting"]
    print(f"    · 色温：{ls.get('color_temperature_k')}　照度取向：{ls.get('illuminance_lux','')}")
    for p in ls.get("principles") or []:
        print(f"    · {p}")
    print("\n  施工重点：")
    for c in rep["construction_focus"]:
        print(f"    · {c}")
    if a.out:
        out = Path(a.out)
        out.mkdir(parents=True, exist_ok=True)
        (out / "style-material-spec.json").write_text(
            json.dumps(rep, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"\n已写入：{out / 'style-material-spec.json'}", file=sys.stderr)
    return 0


def cmd_compare(a: argparse.Namespace) -> int:
    rep = comparison_data(_style_ids(a.styles))
    if a.json:
        _dump(rep)
        return 0
    print(f"风格对比（{rep['count']} 套）\n")
    for s in rep["styles"]:
        print(f"【{s['style']}】{s['family']}　造价档位：{s['budget_tier']}")
        print(f"  空间原则：{'；'.join(s['spatial_principles'])}")
        print(f"  材料：{'、'.join(str(m) for m in s['materials'])}")
        print(f"  色板：{' '.join(c['hex'] for c in s['palette'])}")
        print(f"  造价驱动：{'、'.join(str(d) for d in s['budget_drivers'])}")
        print(f"  与它冲突：{'、'.join(str(i) for i in s['incompatible'])}")
        print()
    print(rep["note"])
    if a.out:
        out = Path(a.out)
        out.mkdir(parents=True, exist_ok=True)
        (out / "style-comparison.json").write_text(
            json.dumps(rep, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"已写入：{out / 'style-comparison.json'}", file=sys.stderr)
    return 0


def cmd_intent(a: argparse.Namespace) -> int:
    deviations = [s for s in (a.deviations or "").split("|") if s]
    rep = design_intent_check(a.style, deviations)
    if a.json:
        _dump(rep)
        return 0
    print(f"设计意图核对：{rep['style']}")
    if not rep["deviations"]:
        print("  未提出偏差项")
    for d in rep["deviations"]:
        print(f"  ! {d['deviation']}")
        print(f"      {d['note']}")
    print("\n  风格自检清单：")
    for c in rep["checklist"]:
        print(f"    · {c.get('check')}：{c.get('criteria')}")
    return 0


def cmd_providers(a: argparse.Namespace) -> int:
    st = probe(a.project)
    if a.json:
        _dump(st.to_dict())
        return 0
    mark = {"connected": "已连接", "not_configured": "未配置"}.get(st.state, st.state)
    print(f"创作平台：{st.platform}　状态：{mark}")
    if st.contract_path:
        print(f"  契约：{st.contract_path}")
    if st.models:
        print(f"  模型：{', '.join(st.models)}")
    if st.missing:
        print("  缺少：")
        for m in st.missing:
            print(f"    · {m}")
    if st.hint:
        print(f"  提示：{st.hint}")
    print("  第三方回退：forbidden")
    print("  本系统不提供以下入口：")
    for x in NOT_IMPLEMENTED_AS_FALLBACK:
        print(f"    · {x}")
    return 0


def cmd_doctor(a: argparse.Namespace) -> int:
    cat = load_catalog()
    bad = check_style_dir()
    st = probe(a.project)
    hooks = all_hooks()
    missing_files = []
    from .resources import CATALOG_FILE, STYLE_SCHEMA
    if not STYLE_SCHEMA.exists():
        missing_files.append(str(STYLE_SCHEMA))
    if not CATALOG_FILE.exists():
        missing_files.append(str(CATALOG_FILE))
    rep = {
        "version": project_version(),
        "catalog_count": len(cat),
        "invalid_styles": len(bad),
        "stage_hooks": [h["stage"] for h in hooks],
        "prompt_targets": list(PROMPT_TARGETS),
        "platform_state": st.state,
        "platform_missing": list(st.missing),
        "missing_files": missing_files,
        "third_party_fallback": "forbidden",
    }
    if a.json:
        _dump(rep)
        return 0
    print(f"设计风格系统（OmniAiLab AI Architect 内部模块）　v{rep['version']}")
    print(f"  风格目录：{rep['catalog_count']} 条（校验未通过 {rep['invalid_styles']} 条）")
    print(f"  阶段挂钩：{', '.join(rep['stage_hooks'])}")
    print(f"  提示词目标：{len(rep['prompt_targets'])} 种 —— {', '.join(rep['prompt_targets'])}")
    print(f"  创作平台：{rep['platform_state']}"
          + (f"（缺 {len(rep['platform_missing'])} 项）" if rep["platform_missing"] else ""))
    print(f"  第三方回退：forbidden")
    if missing_files:
        print(f"  缺失文件：{', '.join(missing_files)}")
    ok = not bad and not missing_files
    print(f"  结论：{'通过' if ok else '存在问题'}")
    return 0 if ok else 1


# --------------------------------------------------------------------------
def _style_command_required(_a: argparse.Namespace) -> int:
    """No sub-command given: say what the options are instead of doing nothing."""
    print("用法：python -m omniarchitect style <子命令>")
    print("子命令：validate / catalog / search / show / recommend / lock / compile /")
    print("        multiview / submit / hooks / space-check / materials / compare /")
    print("        intent / providers / doctor")
    return 2


def register(sub: "argparse._SubParsersAction") -> None:
    """Attach the design-style commands to the main CLI.

    They live under one `style` sub-command rather than at the top level: the
    main CLI already owns `providers`, `present`, `audit` and friends, and a
    second top-level `providers` would be ambiguous. One name, one meaning.
    """
    top = sub.add_parser(
        "style",
        help="设计风格系统（47 种风格知识库 / 推荐 / 中英双语提示词 / 材料与灯光）",
        description="OmniAiLab 建筑与室内设计风格系统 —— 风格知识库、推荐引擎、"
                    "提示词编译器与八阶段挂钩。数据规范见 docs/DESIGN_STYLES.md。")
    top.set_defaults(func=_style_command_required)
    sub = top.add_subparsers(dest="style_cmd", required=True)

    sp = sub.add_parser("validate", help="校验风格数据（Schema + 引用完整性）")
    sp.add_argument("--all", action="store_true", help="校验全部（默认行为）")
    sp.add_argument("--style", default="")
    sp.set_defaults(func=cmd_validate)

    sp = sub.add_parser("catalog", help="风格索引报告")
    sp.add_argument("--list", action="store_true", help="列出全部风格")
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=cmd_catalog)

    sp = sub.add_parser("search", help="按标签/族/阶段/空间/预算搜索风格")
    sp.add_argument("--tags", default="", help="逗号分隔")
    sp.add_argument("--all-tags", action="store_true", help="要求同时命中所有标签")
    sp.add_argument("--family", default="")
    sp.add_argument("--stage", default="")
    sp.add_argument("--budget", default="")
    sp.add_argument("--space", default="")
    sp.add_argument("--text", default="")
    sp.add_argument("--limit", type=int, default=0)
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=cmd_search)

    sp = sub.add_parser("show", help="显示单条风格（摘要）")
    sp.add_argument("style")
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=cmd_show)

    def add_brief(sp: argparse.ArgumentParser) -> None:
        sp.add_argument("--space", default="", help="空间名称，如 客厅")
        sp.add_argument("--area", type=float, default=None)
        sp.add_argument("--width", type=int, default=None, help="开间 mm")
        sp.add_argument("--depth", type=int, default=None, help="进深 mm")
        sp.add_argument("--ceiling", type=int, default=None, help="净高 mm")
        sp.add_argument("--orientation", default="")
        sp.add_argument("--openings", default="", help="用 | 分隔")
        sp.add_argument("--keep", default="", help="局部改造必须保留的构件，用 | 分隔")
        sp.add_argument("--change", default="", help="局部改造允许改动的部位，用 | 分隔")
        sp.add_argument("--materials", default="", help="本项目材料，用 | 分隔")
        sp.add_argument("--lighting", default="", help="本项目光线条件，用 | 分隔")
        sp.add_argument("--needs", default="", help="客户功能需求，用 | 分隔")
        sp.add_argument("--camera", default="")
        sp.add_argument("--refs", default="", help="参考图路径，用 | 分隔")

    sp = sub.add_parser("recommend", help="风格推荐（三套方案）")
    sp.add_argument("--space-type", default="住宅")
    sp.add_argument("--area", type=float, default=None)
    sp.add_argument("--budget", default="", choices=["", "economy", "mid", "premium", "luxury"])
    sp.add_argument("--location", default="")
    sp.add_argument("--prefer", default="", help="喜好关键词或风格 id，逗号分隔")
    sp.add_argument("--maintenance", default="", choices=["", "low", "medium", "high"])
    sp.add_argument("--avoid", default="", help="排除项，逗号分隔")
    sp.add_argument("--stage", default="S2")
    sp.add_argument("--out", default="")
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=cmd_recommend)

    sp = sub.add_parser("lock", help="锁定风格（写入带修订号的锁定文件）")
    sp.add_argument("--style", required=True)
    sp.add_argument("--out", required=True)
    sp.add_argument("--revision", type=int, default=1)
    sp.add_argument("--by", default="")
    sp.add_argument("--space-type", default="住宅")
    sp.add_argument("--area", type=float, default=None)
    sp.add_argument("--budget", default="")
    sp.add_argument("--location", default="")
    sp.add_argument("--prefer", default="")
    sp.add_argument("--maintenance", default="")
    sp.set_defaults(func=cmd_lock)

    sp = sub.add_parser("compile", help="编译提示词（中英双语结构化）")
    sp.add_argument("--style", required=True, help="风格 id，多个用逗号分隔（混搭）")
    sp.add_argument("--target", default="interior-render", choices=list(PROMPT_TARGETS))
    sp.add_argument("--stage", default="")
    sp.add_argument("--revision", type=int, default=1)
    sp.add_argument("--locked", action="store_true", help="风格已在门禁确认")
    sp.add_argument("--negative", default="", help="附加负向约束，用 | 分隔")
    sp.add_argument("--extra", default="", help="其它要求（非家具类），用 | 分隔")
    sp.add_argument("--plan-confirmed", action="store_true",
                    help="平面已通过 G3；平面图上色/立轴/剖面/展示板必须打开，否则只能出探索稿")
    add_brief(sp)
    sp.add_argument("--out", default="")
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=cmd_compile)

    sp = sub.add_parser("multiview", help="多机位编译（共用一致性指纹）")
    sp.add_argument("--style", required=True)
    sp.add_argument("--views", default="整户型", help="机位名称，逗号分隔")
    sp.add_argument("--target", default="multi-view", choices=list(PROMPT_TARGETS))
    sp.add_argument("--revision", type=int, default=1)
    sp.add_argument("--locked", action="store_true")
    sp.add_argument("--plan-confirmed", action="store_true",
                    help="平面已通过 G3（图纸派生配方需要）")
    add_brief(sp)
    sp.add_argument("--out", default="")
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=cmd_multiview)

    sp = sub.add_parser("submit", help="提交任务包（平台不可用时标记 awaiting_platform）")
    sp.add_argument("--compile-out", required=True, help="compile/multiview 的产物 JSON")
    sp.add_argument("--out", required=True)
    sp.add_argument("--project", default="", help="平台契约所在目录")
    sp.add_argument("--authorize", action="store_true", help="显式授权联网提交")
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=cmd_submit)

    sp = sub.add_parser("hooks", help="八阶段挂钩")
    sp.add_argument("--stage", default="")
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=cmd_hooks)

    sp = sub.add_parser("space-check", help="S3：风格与空间关系检查")
    sp.add_argument("--style", required=True)
    sp.add_argument("--strict", action="store_true",
                    help="发现冲突时返回非零（供门禁/CI 使用；默认只报告）")
    add_brief(sp)
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=cmd_space_check)

    sp = sub.add_parser("materials", help="S4/S7：材料与照明规范")
    sp.add_argument("--style", required=True)
    sp.add_argument("--substitute", default="", help="材料替换，格式 原名=替换名，用 | 分隔")
    sp.add_argument("--out", default="")
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=cmd_materials)

    sp = sub.add_parser("compare", help="风格对比（汇报用）")
    sp.add_argument("--styles", required=True, help="逗号分隔，2–3 套")
    sp.add_argument("--out", default="")
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=cmd_compare)

    sp = sub.add_parser("intent", help="S7：设计意图核对")
    sp.add_argument("--style", required=True)
    sp.add_argument("--deviations", default="", help="偏差项，用 | 分隔")
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=cmd_intent)

    sp = sub.add_parser("providers", help="创作平台状态")
    sp.add_argument("--project", default="")
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=cmd_providers)

    sp = sub.add_parser("doctor", help="自检")
    sp.add_argument("--project", default="")
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=cmd_doctor)
