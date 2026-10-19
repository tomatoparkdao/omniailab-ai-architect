"""Command line interface.

    python -m omniarchitect doctor
    python -m omniarchitect stages
    python -m omniarchitect status    --project projects/demo-120
    python -m omniarchitect route     --project projects/demo-120 "帮我出施工图"
    python -m omniarchitect run       --project projects/demo-120 --all --assume-approval
    python -m omniarchitect confirm   --project projects/demo-120 --stage S3 --by 业主
    python -m omniarchitect change    --project projects/demo-120 "我不喜欢客厅的电视背景墙"
    python -m omniarchitect demo      --out out

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
    if rep["unavailable"]:
        from .manual import hint
        print("\n" + hint("degraded"))
    return 0


def cmd_manual(args) -> int:
    """打印操作手册指针：三处地址 + 主题 → 章节对照。"""
    from . import manual as M

    if args.json:
        _print_json({
            "local": M.MANUAL_LOCAL,
            "feishu": M.MANUAL_CN,
            "notion": M.MANUAL_NOTION,
            "repo": M.REPO,
            "exists_locally": M.manual_path() is not None,
            "topics": M.topics(),
        })
        return 0
    if args.read:
        p = M.manual_path()
        if p is None:
            print(f"本仓未找到 {M.MANUAL_LOCAL}；请在线查阅：{M.MANUAL_CN}")
            return 1
        text = p.read_text(encoding="utf-8")
        if args.section:
            # 只打印该章节（从标题到下一个同级或更高级标题）
            lines = text.splitlines()
            start = next((i for i, l in enumerate(lines)
                          if l.startswith("#") and args.section in l), None)
            if start is None:
                print(f"手册里没有匹配「{args.section}」的章节；可用主题：")
                for topic, sec in M.topics().items():
                    print(f"  {topic:<16} {sec}")
                return 1
            level = len(lines[start]) - len(lines[start].lstrip("#"))
            end = len(lines)
            for i in range(start + 1, len(lines)):
                l = lines[i]
                if l.startswith("#") and (len(l) - len(l.lstrip("#"))) <= level:
                    end = i
                    break
            print("\n".join(lines[start:end]).rstrip())
            return 0
        print(text)
        return 0
    if args.topic:
        print(M.hint(args.topic))
        print()
        print(M.pointer(args.topic))
        return 0
    print("操作手册（三处内容一致，版本与 Skill 同步）")
    print(M.pointer())
    print("\n按主题查：python -m omniarchitect manual --topic <主题>")
    for topic, sec in M.topics().items():
        print(f"  {topic:<16} {sec}")
    print("\n读正文：python -m omniarchitect manual --read [--section \"避坑\"]")
    return 0


def cmd_reference(args) -> int:
    """打印参考图素材库与方案视频的入口，连同使用边界。

    加了 ``--sources`` 与 ``--research`` 之后，这里也是案例研究的入口：
    一个入口比两个入口更容易被记住，而"去哪找"和"找到什么"本来就是一件事。
    """
    from .reference import as_list

    if getattr(args, "sources", False):
        from .research import registry_markdown

        if args.json:
            from .research import as_list as sources_list

            _print_json({"sources": sources_list()})
            return 0
        print(registry_markdown())
        return 0

    if getattr(args, "research", None):
        return _run_research(args)

    entries = as_list()
    if args.json:
        _print_json({"entries": entries})
        return 0

    print("参考图与方案视频（两个自有入口，可用但不等于无边界）")
    print()
    for e in entries:
        print(f"  {e['title']}")
        print(f"    {e['url']}")
        print(f"    用途：{e['purpose']}")
        print(f"    边界：{e['boundary']}")
        print(f"    细则：{e['doc']}")
        print()
    print("两个入口都是本项目自有：素材库用于调研、导演技能用于脚本，")
    print("生成式图像与视频的唯一被授权主体仍是 OmniAiLab 平台。")
    print()
    print("按专业看有哪些来源：python -m omniarchitect reference --sources")
    print("对某个项目做案例研究：python -m omniarchitect reference --research <项目文件>")
    return 0


def cmd_taxonomy(args) -> int:
    """项目分类：查索引、看单个类型、按一句话识别。

    索引是文档里那张表的机器版——不在 Markdown 里手抄一遍，避免两处漂移。
    """
    from . import taxonomy as tx

    if getattr(args, "detect", None):
        cls = tx.classify(args.detect)
        data = cls.to_dict()
        data["details"] = [tx.resolve(c).to_dict() for c in cls.codes if tx.resolve(c)]
        data["questions"] = [q.qid for q in tx.questions_for(cls.codes)]
        if args.json:
            _print_json(data)
            return 0
        print(f"识别结果：{'、'.join(data['names']) or '未命中已知类型'}")
        print(f"编码：{'、'.join(cls.codes) or '—'}　置信度：{cls.confidence}")
        if data["nature_labels"]:
            print("项目性质：" + "、".join(data["nature_labels"]))
        if data["commission_labels"]:
            print("委托范围：" + "、".join(data["commission_labels"]))
        cap = tx.capability_of(cls.codes)
        print(f"能力边界：{cap['label']}")
        if cap.get("note"):
            print(f"　{cap['note']}")
        if data["questions"]:
            print("行业专项问题：" + "、".join(data["questions"]))
        if cls.note:
            print("说明：" + cls.note)
        return 0

    if getattr(args, "show", None):
        spec = tx.resolve(args.show)
        if spec is None:
            print(f"没有这个分类：{args.show}")
            return 2
        data = spec.to_dict()
        data["focus"] = list(spec.focus)
        data["directions"] = [{"name": d.name, "parti": d.parti, "why": d.why}
                              for d in spec.directions]
        data["questions"] = [{"id": q.qid, "text": q.text} for q in spec.questions]
        data["s3_tasks"] = {
            "base": list(tx.S3_BASE.get(spec.discipline, ())),
            "specific": list(spec.s3_specific),
        }
        data["subtypes"] = list(spec.subtypes)
        if args.json:
            _print_json(data)
            return 0
        print(f"{spec.code} {spec.name}（{data['family_label']}／{spec.discipline}）")
        print(f"子类 {len(spec.subtypes)} 项：{'、'.join(spec.subtypes[:8])}…")
        print("专业要点：" + "、".join(spec.focus))
        print("能力边界：" + data["capability_label"])
        if spec.limitation:
            print("　" + spec.limitation)
        print("概念方向：")
        for d in spec.directions:
            print(f"  · {d.name}｜{d.parti}")
        if spec.s3_specific:
            print("S3 专属任务：")
            for t in spec.s3_specific:
                print(f"  - {t}")
        return 0

    rows = tx.index_rows()
    if args.json:
        _print_json({"count": len(rows), "types": [
            {"code": c, "name": n, "discipline": d, "subtypes": int(k)}
            for c, n, d, k in rows]})
        return 0
    print(f"项目分类索引（{len(rows)} 类／"
          f"{sum(int(r[3]) for r in rows)} 个子类）")
    print("民用建筑 = 居住建筑 + 公共建筑；工业与农业是生产建筑，不并入民用。")
    print()
    cur = ""
    for code, name, disc, n in rows:
        if code[0] != cur:
            cur = code[0]
            print({"A": "A 建筑", "B": "B 室内", "C": "C 景观"}.get(cur, cur))
        print(f"  {code:<4} {name:<16} {disc:<12} 子类 {n}")
    print()
    print("看单个类型：python -m omniarchitect taxonomy --show A4")
    print("按一句话识别：python -m omniarchitect taxonomy --detect \"新建综合医院 300 床\"")
    return 0


def _run_research(args) -> int:
    """S1 阶段的案例研究，单独可跑，也可由 S1 自动触发。"""
    from . import research as research_mod
    from .model import load_project

    proj = load_project(args.research)

    out_dir = args.out or ""
    res = research_mod.run(proj, out_dir=out_dir or None,
                           verify_pages=not args.no_verify)

    if args.json:
        _print_json(res.to_dict())
        return 0

    brief = res.brief
    print(f"项目：{res.project_id}　修订 r{res.revision}")
    print(f"触发：{brief.trigger}")
    print(f"专业：{'、'.join(brief.disciplines)}")
    print()
    print(f"第一优先入口：{research_mod.FIRST_PARTY.name}")
    print(f"  {research_mod.FIRST_PARTY.url}")
    print("  （客户端渲染，脚本读不到条目；由人打开看，系统不代你编内容）")
    print()
    if not res.cases:
        print("本次没有可核验案例。可能原因从上到下一目了然：")
        if not res.log:
            print("  - 未触发：项目类型还没确定")
        for a in res.log[-6:]:
            print("  - {action} {url} {status} {detail}".format(
                action=a.get("action", ""), url=a.get("url", ""),
                status=a.get("status", ""), detail=a.get("detail", "")))
    else:
        print(f"精选案例 {len(res.cases)} 个（已核验 {len(res.verified)} 个）：")
        for i, c in enumerate(res.cases, 1):
            print(f"  {i}. [{c.verify}] {c.title} / {c.architect}")
            print(f"     {c.url}")
            if c.city or c.year:
                print(f"     {c.city} {c.country} {c.year}".strip())
    if out_dir:
        print()
        print(f"已写出：{out_dir}/{research_mod.SHORTLIST_MD}")
        print(f"        {out_dir}/{research_mod.SHORTLIST_JSON}")
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
    print(f"专业能力 {rep['capability_count']} 项，映射到 {rep['stage_count']} 个阶段")
    print("说明文件：skills/<能力名>.md —— 文件名就是能力名，可直接按名加载\n")
    printed = set()
    for r in rep["capabilities"]:
        if r["slug"] in printed:          # slug 是唯一键，同一能力只印一行
            continue
        printed.add(r["slug"])
        stages = ",".join(r["stages"])
        src = "" if r["source"] == "OmniAiLab" else f"  [{r['source']}]"
        mark = "✓" if r["brief_file"] else "✗"
        print(f"  {mark} {r['slug']:<34} {stages:<24}{src}")
    if any(not r["brief_file"] for r in rep["capabilities"]):
        print("\n⚠ 有 ✗ 的能力缺说明文件——文档承诺与仓库不一致，需补齐")
    if rep["legacy_coverage"]:
        print("\nv1.0 编号说明（历史映射，文件已并入 skills/<能力名>.md）")
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
            for n in o.notes[:4]:
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
    ack = [a.strip() for a in (getattr(args, "acknowledge", "") or "").split(",") if a.strip()]
    try:
        st = runner.approve(args.stage, by=args.by or "业主", note=args.note or "",
                            source="owner", acknowledge=ack,
                            force=bool(getattr(args, "force", False)))
    except ValueError as exc:
        # 编号写错不等于"已接受风险"
        raise SystemExit(f"{args.stage} 未确认：{exc}")
    print(f"{args.stage} → {st['status']}（{st.get('confirmed_by') or '—'}）")
    for n in st.get("notes") or []:
        print(f"  · {n}")
    if st["status"] != "confirmed":
        assess = st.get("assessment") or {}
        if assess.get("blocks_gate"):
            print("\n需业主决定：")
            for b in assess["blocks_gate"]:
                print(f"  [{b['id']}] {b['problem']}")
                print(f"       依据：{b['evidence']}")
                print(f"       需要：{b['needs']}")
        elif assess.get("blockers"):
            print("\n不能签发（硬性条件，--force 无效）：")
            for b in assess["blockers"]:
                print(f"  [{b['id']}] {b['text']}")
            if assess.get("acknowledgeable_ids"):
                print("  可逐项书面接受：" + "、".join(assess["acknowledgeable_ids"]))
        return 1
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
    from .manual import MANUAL_CN, MANUAL_LOCAL, REPO

    p = argparse.ArgumentParser(
        prog="omniailab-ai-architect",
        description="OmniArchitect — AI 建筑 / 室内设计总设计师（八阶段工作流）",
        epilog=(
            "不会用或卡住了？先看操作手册（离线可用）：" + MANUAL_LOCAL + "\n"
            "飞书：" + MANUAL_CN + "\n"
            "源码仓库：" + REPO + "\n"
            "也可直接运行：python -m omniarchitect manual"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
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

    sp = sub.add_parser("manual", help="操作手册指针（三处地址 + 主题→章节 + 读正文）")
    sp.add_argument("--topic", default=None, help="按主题查该看哪一节")
    sp.add_argument("--read", action="store_true", help="打印手册正文（离线）")
    sp.add_argument("--section", default=None, help="配合 --read，只打印匹配该关键词的章节")
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=cmd_manual)

    sp = sub.add_parser("reference", help="参考图素材库、方案视频入口、专业案例研究")
    sp.add_argument("--json", action="store_true")
    sp.add_argument("--sources", action="store_true",
                    help="按专业列出参考来源与实测可达性")
    sp.add_argument("--research", default=None, metavar="PROJECT",
                    help="对某个项目做案例研究（项目目录或 project.json）")
    sp.add_argument("--out", default="", help="配合 --research，输出目录")
    sp.add_argument("--no-verify", action="store_true",
                    help="配合 --research，只列不逐个回读（速度更快，但只能标部分核验）")

    tp = sub.add_parser("taxonomy", help="项目分类索引、单个类型与按文字识别")
    tp.add_argument("--json", action="store_true")
    tp.add_argument("--list", action="store_true", help="列出全部分类（默认）")
    tp.add_argument("--show", default="", metavar="CODE",
                    help="看单个分类，如 A4 / B5 / C7")
    tp.add_argument("--detect", default="", metavar="TEXT",
                    help="按一句话识别用途、性质与委托范围")
    tp.set_defaults(func=cmd_taxonomy)
    sp.set_defaults(func=cmd_reference)

    from .intake.cli import add_parser as _add_intake

    _add_intake(sub)

    from .visualref.cli import add_parser as _add_visual

    _add_visual(sub)

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
    sp.add_argument("--acknowledge", default="",
                    help="G1：逐项确认需业主取舍的问题编号，用逗号分隔")
    sp.add_argument("--force", action="store_true",
                    help="G1：在需求矛盾未处理时强制通过（会记录，且不解除安全类限制）")
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
    from .concept.cli import register as _register_concept

    _register_concept(sub)

    from .cli_v11 import register as _register_v11

    _register_v11(sub)

    # v1.4 surface: the design-style module (47 styles, recommendation,
    # bilingual prompt compilation, material & lighting extraction).
    from .style.cli import register as _register_style

    _register_style(sub)

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
