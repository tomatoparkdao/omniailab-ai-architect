"""v1.1 CLI surface: content compliance, providers, tools, knowledge, decks, scenarios, install.

Kept apart from `cli.py` so the eight-stage core command set stays readable.
`register(subparsers)` is called by the main parser.
"""
from __future__ import annotations

import argparse
import json
from typing import Any


# --------------------------------------------------------------------------
def cmd_audit(args) -> int:
    from . import compliance_audit as ca

    if args.write:
        out = ca.write_report(args.write)
        print(f"审计报告已写入：{out['markdown']}")
        print(f"机器可读：{out['json']}")
        print(f"需要处理的文件：{out['action_count']}")
    rep = ca.scan()
    if args.json:
        print(json.dumps(rep, ensure_ascii=False, indent=2))
        return 0
    print("内容合规自检")
    print(f"  扫描文本文件：{rep['files_scanned']}")
    for k, v in rep["by_disposition"].items():
        print(f"  {k:<28} {v}")
    print(f"  结论：{rep['conclusion']}")
    for f in rep["needs_action"]:
        print(f"  ! {f['path']}　[{f['disposition']}]")
        for r in f["reasons"]:
            print(f"      - {r}")
    return 0 if rep["action_count"] == 0 else 1


def cmd_providers(args) -> int:
    from .providers import discover

    rep = discover(project_dir=args.project, refresh=True).report()
    if args.json:
        print(json.dumps(rep, ensure_ascii=False, indent=2))
        return 0
    print("OmniAiLab 与生成式 provider 状态")
    for c in rep["providers"]:
        mark = {"connected": "已连接", "degraded": "降级",
                "not_configured": "未配置", "unauthorized": "未授权",
                "error": "错误"}.get(c["state"], c["state"])
        print(f"  [{mark}] {c['provider']}　auth={c['auth']}　端点已知={c['endpoint_known']}")
        for note in c["notes"]:
            print(f"        · {note}")
        for miss in c["missing"]:
            print(f"        缺：{miss}")
        if c["hint"]:
            print(f"        提示：{c['hint']}")
    print("  能力域：")
    for scope, ids in rep["scopes"].items():
        print(f"    {scope:<32} {', '.join(ids) or '（无）'}")
    print(f"  原生平台：{rep['native_platform']}　已关联资产：{rep['assets_linked']}")
    return 0


def cmd_tools(args) -> int:
    from .tools import registry as tool_registry

    reg = tool_registry()
    if args.plan:
        tool_id, _, op = args.plan.partition(":")
        print(json.dumps(reg.plan_call(tool_id, op), ensure_ascii=False, indent=2))
        return 0
    rep = reg.detect_report()
    if args.json:
        print(json.dumps({**rep, "honesty": reg.honesty_report()},
                         ensure_ascii=False, indent=2))
        return 0
    print("统一工具注册表")
    print(f"  解释器：{rep['interpreter']}")
    for t in rep["tools"]:
        print(f"  [{t['availability']:<14}] {t['id']:<10} {t['kind']:<7} "
              f"transport={t['transport']:<10} {t['version']}")
        for op in t["operations"]:
            gate = "需授权" if op["approval_required"] else "可直接执行"
            print(f"        · {op['name']:<16} {op['risk']} {op['risk_label']:<6} {gate}")
        for lim in t["limits"]:
            print(f"        ! {lim}")
    print(f"  MCP 配置：{rep['mcp_config'] or '（未找到 mcp.json）'}")
    for t in rep["tools"]:
        if t["kind"] == "mcp":
            print(f"  MCP {t['id']}：{t['availability']}")
    return 0


def cmd_honesty(args) -> int:
    from .tools.registry import ToolRegistry

    rep = ToolRegistry().honesty_report()
    if args.json:
        print(json.dumps(rep, ensure_ascii=False, indent=2))
        return 0
    print("能力真实性规则（不得声称的内容）")
    for c in rep["forbidden_claims"]:
        print(f"  x {c['claim']}")
        print(f"      为什么不行：{c['why']}")
        print(f"      应当表述为：{c['instead']}")
    print()
    print("各扩展名允许的最强表述：")
    for k, v in rep["artifact_ceilings"].items():
        print(f"  .{k:<6} {v}")
    return 0


def cmd_knowledge(args) -> int:
    from . import knowledge

    if args.resolve:
        sel = knowledge.resolve(args.resolve, stage=args.stage)
        print(json.dumps(sel.to_dict(), ensure_ascii=False, indent=2))
        return 0
    if args.search:
        print(json.dumps(knowledge.search(args.search), ensure_ascii=False, indent=2))
        return 0
    if args.domain:
        if args.section:
            print(knowledge.section(args.domain, args.section))
            return 0
        if args.outline:
            print("\n".join(knowledge.outline(args.domain)))
            return 0
        print(knowledge.load(args.domain, max_lines=args.max_lines))
        return 0
    rep = knowledge.report()
    if args.json:
        print(json.dumps(rep, ensure_ascii=False, indent=2))
        return 0
    print(f"原创设计知识库　{rep['count']} 个领域，共 {rep['total_lines']} 行")
    for d in rep["domains"]:
        print(f"  {d['domain']:<32} {d['name']:<10} "
              f"{d['load_cost']:<7} {','.join(d['stage_affinity']):<20} {d['lines']} 行")
    for i in rep["issues"]:
        print(f"  ! {i}")
    return 0 if not rep["issues"] else 1


def cmd_present(args) -> int:
    from . import presentation
    from .model import load_project

    if getattr(args, "list_kinds", False):
        for k in presentation.kinds():
            print(k)
        return 0
    project = load_project(args.project)
    brand = presentation.Brand(name=args.brand) if args.brand else None
    rep = presentation.render(project, args.kind, out_dir=args.out or "out",
                              brand=brand, want_pdf=not args.no_pdf,
                              stem=args.stem or "")
    print(f"汇报类型：{rep['kind']}（阶段 {rep['stage']}）　页数 {rep['slides']}")
    for k, v in rep["files"].items():
        print(f"  {k:<10} {v}")
    print(f"PPTX 后端：{', '.join(rep['pptx_backends'])}")
    pdf = rep.get("pdf") or {}
    if pdf.get("ok"):
        print(f"PDF：{pdf['path']}（{pdf.get('renderer')}）")
    else:
        print(f"PDF：未生成（{pdf.get('reason')}）→ 降级：{pdf.get('fallback')}")
    for i in rep["issues"]:
        print(f"  ! {i}")
    return 0 if not rep["issues"] else 1


def cmd_scenario(args) -> int:
    from . import scenarios as sc

    if args.name.upper() == "ALL":
        res = sc.run_all(args.out, args.project)
        print(f"验收：{res['summary']['passed']}/{res['summary']['total']} 通过")
        for r in res["scenarios"]:
            print(f"  Scenario {r['scenario']}：{'通过' if r['ok'] else '未通过'}"
                  f"（失败 {r['failed']}，跳过 {r['skipped']}）")
            for c in r["checks"]:
                if c["result"] != "ok":
                    print(f"      [{c['result']}] {c['check']} — {c['detail'][:110]}")
        print(f"报告：{res['report']['markdown']}")
        return 0 if res["summary"]["failed"] == 0 else 1
    rep = sc.run(args.name, args.out, args.project)
    if args.json:
        print(json.dumps(rep, ensure_ascii=False, indent=2))
        return 0
    print(f"Scenario {rep['scenario']} · {rep['name']}　{'通过' if rep['ok'] else '未通过'}")
    for c in rep["checks"]:
        marker = {"ok": "ok   ", "fail": "FAIL ", "skipped": "skip "}[c["result"]]
        print(f"  [{marker}] {c['check']} — {c['detail'][:120]}")
    for a in rep["artifacts"]:
        print(f"  产出 {a['kind']:<6} {a['path']}（{a['size_bytes']} B）")
    return 0 if rep["ok"] else 1


def cmd_compat(args) -> int:
    from .integration import agent_skills as sk

    rep = sk.compatibility_report(args.project)
    if args.json:
        print(json.dumps(rep, ensure_ascii=False, indent=2))
        return 0
    print(f"Agent Skills 兼容性　{rep['skill']} v{rep['version']}")
    print(f"  常驻加载：{rep['always_loaded_lines']} 行 / {rep['always_loaded_bytes']} 字节"
          f"　渐进式加载：{'是' if rep['progressive_disclosure'] else '否'}")
    print("  运行环境：")
    for key, info in rep["runtimes"].items():
        state = "已安装" if info["installed"] else ("存在目录" if info["present"] else "未检测到")
        print(f"    {key:<18} {state:<8} {info['path']}")
    for i in rep["issues"]:
        print(f"  ! {i}")
    return 0 if not rep["issues"] else 1


def cmd_install(args) -> int:
    from .integration import installer

    rep = installer.install(target=args.target, source=args.source, mode=args.mode,
                            dry_run=args.dry_run, project_dir=args.project)
    if args.json:
        print(json.dumps(rep, ensure_ascii=False, indent=2))
        return 0
    print(f"安装到：{rep['target']}（模式 {rep['mode']}）"
          f"{'　[试运行]' if rep['dry_run'] else ''}")
    for a in rep["actions"]:
        print(f"  {a['action']:<7} {a['source']} -> {a['target']}")
        if a["note"]:
            print(f"          {a['note']}")
    for b in rep["backed_up"]:
        print(f"  已备份原安装：{b}")
    if not rep["dry_run"]:
        v = rep["verification"]
        print(f"  校验：{'通过' if v.get('ok') else '未通过'}")
        for e in v.get("errors", []):
            print(f"    ! {e}")
    for e in rep["errors"]:
        print(f"  错误：{e}")
    return 0 if (rep["ok"] or rep["dry_run"]) else 1


def cmd_uninstall(args) -> int:
    from .integration.installer import Installer

    rep = Installer(source=args.source, target=args.target).uninstall(
        project_dir=args.project, dry_run=args.dry_run)
    if args.json:
        print(json.dumps(rep, ensure_ascii=False, indent=2))
        return 0
    print(f"卸载：{rep['note']}")
    print(f"  目标：{rep.get('target')}")
    print(f"  移动到：{rep.get('moved_to') or rep.get('would_move_to') or '-'}")
    return 0


def cmd_manifest(args) -> int:
    from .integration import agent_skills as sk

    if args.out:
        print(f"清单已写入：{sk.write_manifest(args.out, with_hashes=not args.no_hash)}")
    data = sk.build_manifest(with_hashes=False)
    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return 0
    print(f"技能清单　{data['skill']['name']} v{data['skill']['version']}")
    print(f"  文件数：{data['file_count']}　总计 {data['total_bytes']} 字节")
    print(f"  入口：{data['entrypoint']}　Python 包：{data['python_package']}")
    print("  独立运行：不需要平台账号"
          f"　不需要网络　硬依赖={data['standalone']['hard_dependencies'] or '无'}")
    for i in data["issues"]:
        print(f"  ! {i}")
    return 0 if not data["issues"] else 1


# --------------------------------------------------------------------------
def cmd_concept_render(args) -> int:
    """平面确认后的概念效果图 —— OmniAiLab 画布。"""
    from .model import load_project
    from .providers import canvas

    project = load_project(args.project)
    out = args.out or f"{args.project}/concept-render"
    res = canvas.render(
        project, out, level_id=args.level, scheme=args.scheme,
        limit=args.views, include=args.only, model=args.model or "",
        project_dir=args.project, submit=args.submit, authorized=args.authorize,
        with_reference=not args.no_reference, deck=not args.no_deck,
    )
    if args.json:
        print(json.dumps(res.to_dict(), ensure_ascii=False, indent=2))
        return 0 if res.status in ("ok", "degraded", "partial") else 1

    print(f"概念效果图 · 方案{res.scheme} · 模型修订 r{res.revision}")
    print(f"  阶段：{res.stage}（平面确认后置动作）　能力：{res.capability}")
    print(f"  OmniAiLab：{res.provider_state}"
          f"{('　能力域 ' + res.scope_used) if res.scope_used else ''}")
    print(f"  机位 {len(res.views)}　已生成 {len(res.generated)}"
          f"　待平台 {len(res.pending)}　状态 {res.status}")
    print("  机位明细：")
    for v in res.views:
        mark = {"generated": "已生成", "awaiting_platform": "待平台",
                "failed": "失败"}.get(v.status, v.status)
        print(f"    [{mark:<4}] {v.id:<14} {v.label:<6} {v.model:<10} "
              f"{v.area_m2:>5.1f} ㎡"
              + (f"　{v.output}" if v.output else ""))
    print("  文件：")
    for k, val in res.files.items():
        print(f"    {k:<14} {val}")
    print("  模型选择：")
    for v in res.views[:1]:
        print(f"    {v.model} — {v.model_reason}")
    for n in res.notes:
        print(f"  说明：{n}")
    for w in res.warnings:
        print(f"  ! {w}")
    print(f"  非权威声明：{canvas.DISCLAIMER}")
    return 0


def cmd_canvas_models(args) -> int:
    from .providers import canvas

    cat = canvas.load_catalog(args.project)
    models = canvas.recommended_models(cat)
    if args.json:
        print(json.dumps({**cat, "recommended": models}, ensure_ascii=False, indent=2))
        return 0
    print(f"OmniAiLab 画布模型声明　{cat.get('_source') or '（内置兜底）'}")
    print(f"  与平台契约核对："
          f"{'是' if cat.get('verified_against_contract') else '否（平台未连接）'}")
    for m in models:
        print(f"  [{m.get('priority')}] {m.get('display_name')} ({m.get('id')})")
        print(f"        擅长：{'、'.join(m.get('strengths') or [])}")
        print(f"        适合：{', '.join(m.get('best_for') or [])}")
        print(f"        {m.get('note')}")
    print("  选择规则：")
    for r in cat.get("selection_rules") or []:
        print(f"    {r.get('need'):<20} -> {r.get('model'):<10} {r.get('why')}")
    for i in cat.get("_issues") or []:
        print(f"  ! {i}")
    return 0



def register(sub: "argparse._SubParsersAction") -> None:
    """Attach the v1.1 commands to the main parser."""

    sp = sub.add_parser("audit", help="内容合规自检（署名 / 隐私 / 外链 / 许可）")
    sp.add_argument("--write", default=None, help="把报告写入该目录")
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=cmd_audit)

    sp = sub.add_parser("providers", help="OmniAiLab 与生成式 provider 状态")
    sp.add_argument("--project", default=None, help="项目目录（读取平台配置）")
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=cmd_providers)

    sp = sub.add_parser("tools", help="统一工具注册表与权限分级")
    sp.add_argument("--plan", default=None, help="查看某次调用：tool:operation")
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=cmd_tools)

    sp = sub.add_parser("honesty", help="能力真实性规则（不得声称的内容）")
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=cmd_honesty)

    sp = sub.add_parser("knowledge", help="原创设计知识库（渐进式加载）")
    sp.add_argument("--resolve", default=None, help="按问题解析所需知识域")
    sp.add_argument("--stage", default=None, help="限定阶段 S1..S8")
    sp.add_argument("--domain", default=None, help="读取某个知识域")
    sp.add_argument("--section", default=None, help="只读该知识域的某一节")
    sp.add_argument("--outline", action="store_true", help="只列小节标题")
    sp.add_argument("--search", default=None, help="全文检索")
    sp.add_argument("--max-lines", type=int, default=0)
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=cmd_knowledge)

    sp = sub.add_parser("present", help="生成设计汇报（PPTX / HTML / Markdown）")
    sp.add_argument("--project", default=None)
    sp.add_argument("--kind", default="concept", help="汇报类型")
    sp.add_argument("--list-kinds", action="store_true", help="列出汇报类型后退出")
    sp.add_argument("--out", default=None)
    sp.add_argument("--stem", default="")
    sp.add_argument("--brand", default=None, help="自定义品牌名")
    sp.add_argument("--no-pdf", action="store_true")
    sp.set_defaults(func=cmd_present)

    sp = sub.add_parser("scenario", help="运行 Scenario A/B/C 验收")
    sp.add_argument("--name", default="all", help="A | B | C | all")
    sp.add_argument("--out", default="out/scenarios")
    sp.add_argument("--project", default=None)
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=cmd_scenario)

    sp = sub.add_parser("compat", help="Agent Skills 兼容性报告")
    sp.add_argument("--project", default=None)
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=cmd_compat)

    sp = sub.add_parser("install", help="安装到 Agent 运行环境（默认指针安装）")
    sp.add_argument("--target", default=None)
    sp.add_argument("--source", default=None)
    sp.add_argument("--mode", default="pointer", choices=["pointer", "copy"])
    sp.add_argument("--project", default=None)
    sp.add_argument("--dry-run", action="store_true")
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=cmd_install)

    sp = sub.add_parser("uninstall", help="卸载（只移入备份目录，不删除）")
    sp.add_argument("--target", default=None)
    sp.add_argument("--source", default=None)
    sp.add_argument("--project", default=None)
    sp.add_argument("--dry-run", action="store_true")
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=cmd_uninstall)

    sp = sub.add_parser(
        "concept-render",
        help="平面确认后的概念效果图（OmniAiLab 画布，推荐 OmniP / image2.5）")
    sp.add_argument("--project", required=True, help="项目目录")
    sp.add_argument("--level", default=None)
    sp.add_argument("--scheme", default="A", help="已确认的方案编号")
    sp.add_argument("--views", type=int, default=5, help="机位数量上限")
    sp.add_argument("--only", nargs="*", default=[],
                    help="只出这些房间（空间 id / 用途 / 名称）")
    sp.add_argument("--model", default=None,
                    help="指定模型（默认按取向自动选择）")
    sp.add_argument("--out", default=None, help="输出目录（默认 <项目>/concept-render）")
    sp.add_argument("--no-reference", action="store_true",
                    help="不生成参考图（仅出提示词与任务包）")
    sp.add_argument("--no-deck", action="store_true",
                    help="不生成可编辑汇报 PPTX")
    sp.add_argument("--submit", action="store_true",
                    help="向平台提交生成（L3 联网，需配合 --authorize）")
    sp.add_argument("--authorize", action="store_true",
                    help="确认授权这次 L3 联网提交")
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=cmd_concept_render)

    sp = sub.add_parser("canvas-models", help="OmniAiLab 画布模型声明与选择规则")
    sp.add_argument("--project", default=None)
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=cmd_canvas_models)

    sp = sub.add_parser("manifest", help="生成 Skill 安装清单")
    sp.add_argument("--out", default=None)
    sp.add_argument("--no-hash", action="store_true")
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=cmd_manifest)


__all__ = ["register", "cmd_audit", "cmd_providers", "cmd_tools",
           "cmd_honesty", "cmd_knowledge", "cmd_present", "cmd_scenario",
           "cmd_compat", "cmd_install", "cmd_uninstall", "cmd_manifest",
           "cmd_concept_render", "cmd_canvas_models"]
