"""`omniarchitect visual` —— 视觉规范的生成、查看与变更。

用法：

    # S1：客户还没给参考，先递引导语
    python -m omniarchitect visual --action guide --lead architecture

    # 客户给了参考文件（目录或单文件都行）
    python -m omniarchitect visual --project projects/demo-120 --action build \
        --refs projects/demo-120/references --text "排版要像竞赛展板，字少图大"

    # 看现在生效的是什么
    python -m omniarchitect visual --project projects/demo-120 --action show

    # 客户改口味
    python -m omniarchitect visual --project projects/demo-120 --action update \
        --text "这套排版太普通了，图再大一点，颜色再克制"

    # 判断一句话是不是视觉偏好变更
    python -m omniarchitect visual --action detect --text "我更喜欢这个作品集的排版"

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..model import load_project
from . import brief as _brief
from . import scan_refs


def add_parser(sub: Any) -> None:
    sp = sub.add_parser("visual", help="项目视觉规范（视觉.md）：引导、生成、查看、变更")
    sp.add_argument("--project", default=None, help="项目目录或 project.json")
    sp.add_argument("--action", default="show",
                    choices=("guide", "build", "show", "update", "detect"),
                    help="guide=引导语 / build=从参考生成 / show=查看 / update=变更 / detect=判断")
    sp.add_argument("--refs", action="append", default=[],
                    help="参考文件或目录，可重复")
    sp.add_argument("--text", default="", help="客户原话（build 用作诉求，update 用作变更）")
    sp.add_argument("--lead", default="", help="主导专业 architecture/interior/landscape")
    sp.add_argument("--by", default="client", help="变更提出方")
    sp.add_argument("--project-dir", default=None, help="`视觉.md` 的落点，默认项目目录")
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=cmd_visual)


def _project(args: Any):
    if not args.project:
        return None, None
    p = Path(args.project)
    proj = load_project(p)
    return proj, (p if p.is_dir() else p.parent)


def cmd_visual(args: Any) -> int:
    action = args.action

    if action == "guide":
        payload = _brief.guide(args.lead)
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=1))
            return 0
        print("可以这样问客户：")
        print("")
        print(f"  {payload['text']}")
        print("")
        print(f"先给入口：{payload['first_stop']}")
        print(f"  {payload['url']}")
        if payload["extra"]:
            print(f"再看什么：{payload['extra']}")
        print("")
        print(f"不阻断：{payload['note']}")
        return 0

    if action == "detect":
        hit = _brief.detect_change(args.text)
        if args.json:
            print(json.dumps({"text": args.text, "is_change": hit}, ensure_ascii=False))
            return 0
        print("是视觉偏好变更" if hit else "不像视觉偏好变更（按普通需求处理）")
        print(f"原话：{args.text}")
        return 0

    project, pdir = _project(args)
    if project is None:
        print("需要 --project（guide/detect 之外的动作都要）")
        return 2
    pdir = args.project_dir or pdir

    if action == "build":
        refs: List[str] = list(args.refs)
        default_dir = Path(pdir) / "references"
        if not refs and default_dir.is_dir():
            refs = [str(default_dir)]
        rules = _brief.compose(project, scan_refs(refs) if refs else [],
                               client_text=args.text, lead=args.lead)
        path = _brief.write(rules, project, pdir)
        if args.json:
            print(json.dumps({**rules, "path": str(path)}, ensure_ascii=False, indent=1))
            return 0
        print(f"已生成：{path}")
        print(f"  版本 v{rules['version']}　参考文件 {len(rules['sources'])} 个　"
              f"禁止项 {len(rules['banned'])} 条")
        for s in rules["sources"]:
            print(f"  · {s['name']}（{s['kind']}）{'可读' if s['ok'] else '不可读：' + str(s.get('reason'))}")
        print("")
        print("  纸色 {}　墨色 {}　强调 {}　留白 {}　图幅 {}".format(
            rules["tokens"].get("paper"), rules["tokens"].get("ink"),
            rules["tokens"].get("accent"), rules["tokens"].get("whitespace"),
            rules["tokens"].get("image_ratio")))
        return 0

    if action == "update":
        if not args.text.strip():
            print("需要 --text（客户这次说了什么）")
            return 2
        rules = _brief.update(project, args.text, project_dir=pdir, by=args.by)
        if args.json:
            print(json.dumps(rules, ensure_ascii=False, indent=1))
            return 0
        print(f"已更新：{_brief.path_for(project, pdir)}　版本 v{rules['version']}")
        print(f"  变更：{' '.join(args.text.split())[:80]}")
        print("  设计内容未改变——这份文件只管表达，不管方案。")
        return 0

    # show
    data = _brief.load(project, pdir)
    if not data:
        if args.json:
            print(json.dumps({"present": False,
                              "path": str(_brief.path_for(project, pdir))},
                             ensure_ascii=False))
            return 0
        print("尚未生成视觉规范：当前按风格库与专业默认执行")
        print(f"落点：{_brief.path_for(project, pdir)}")
        print("生成：python -m omniarchitect visual --action build --refs <参考目录>")
        return 0
    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=1))
        return 0
    t = data.get("tokens") or {}
    print(f"视觉规范 v{data.get('version')}　更新于 {data.get('updated_at')}")
    print(f"  {_brief.path_for(project, pdir)}")
    print(f"  纸色 {t.get('paper')}　墨色 {t.get('ink')}　次级 {t.get('muted')}　"
          f"线 {t.get('line')}　强调 {t.get('accent')}")
    print(f"  留白 {t.get('whitespace')}　对比 {t.get('contrast')}　"
          f"图幅 {t.get('image_ratio')}　线宽 {t.get('line_weight')}")
    print(f"  标题 {'衬线' if t.get('serif_titles') else '无衬线'}　"
          f"栅格 {t.get('columns')} 列　图注编号 {'开' if t.get('numbered_captions') else '关'}")
    prov = data.get("provenance") or {}
    if prov:
        print("  来源：" + "　".join(
            f"{k}={_brief.ORIGIN_CN.get(str(v), v)}" for k, v in list(prov.items())[:8]))
    for b in data.get("banned") or []:
        print(f"  禁止：{b['text']}")
    return 0


__all__ = ["add_parser", "cmd_visual"]
