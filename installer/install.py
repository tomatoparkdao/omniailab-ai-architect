#!/usr/bin/env python
"""Install OmniArchitect into an Agent runtime — without deleting anything.

    python installer/install.py --dry-run                 # 先看会发生什么
    python installer/install.py                           # 自动选择已检测到的运行环境
    python installer/install.py --target ~/.codex/skills
    python installer/install.py --mode copy               # 完整复制而非指针安装
    python installer/install.py --uninstall               # 只移入备份目录

Exit codes: 0 ok · 1 verification failed · 2 usage / no runtime found.

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from omniailab_ai_architect.integration import installer as inst  # noqa: E402
from omniailab_ai_architect.integration import agent_skills as sk  # noqa: E402


def main(argv: list | None = None) -> int:
    ap = argparse.ArgumentParser(prog="install.py", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--target", default=None, help="安装目录（技能根下的子目录）")
    ap.add_argument("--mode", default=inst.MODE_POINTER,
                    choices=[inst.MODE_POINTER, inst.MODE_COPY])
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--uninstall", action="store_true")
    ap.add_argument("--project", default=None, help="用哪个项目目录探测运行环境")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    ins = inst.Installer(source=ROOT, target=args.target, mode=args.mode)

    if args.uninstall:
        try:
            rep = ins.uninstall(project_dir=args.project, dry_run=args.dry_run)
        except RuntimeError as exc:
            print(f"错误：{exc}", file=sys.stderr)
            return 2
        print(json.dumps(rep, ensure_ascii=False, indent=2) if args.json
              else f"{rep['note']}\n  目标：{rep.get('target')}\n"
                   f"  移到：{rep.get('moved_to') or rep.get('would_move_to') or '-'}")
        return 0

    try:
        rep = ins.install(project_dir=args.project, dry_run=args.dry_run)
    except RuntimeError as exc:
        print(f"错误：{exc}", file=sys.stderr)
        print("\n已检测到的运行环境：", file=sys.stderr)
        for key, info in sk.detect_runtimes(args.project).items():
            print(f"  {key:<18} {'存在' if info['present'] else '未检测到'}　{info['path']}",
                  file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(rep.to_dict(), ensure_ascii=False, indent=2))
    else:
        d = rep.to_dict()
        print(f"安装到：{d['target']}（模式 {d['mode']}）"
              f"{'　[试运行，未写入]' if d['dry_run'] else ''}")
        for a in d["actions"]:
            line = f"  {a['action']:<7} {a['source']} -> {a['target']}"
            print(line)
            if a["note"]:
                print(f"          {a['note']}")
        for b in d["backed_up"]:
            print(f"  已备份原安装：{b}")
        if not d["dry_run"]:
            v = d["verification"]
            print(f"  校验：{'通过' if v.get('ok') else '未通过'}"
                  f"　入口行数 {v.get('skill', {}).get('lines')}"
                  f"　指针指向 {v.get('home', '(copy 模式)')}")
        for e in d["errors"]:
            print(f"  错误：{e}")
    return 0 if (rep.ok or rep.dry_run) else 1


if __name__ == "__main__":
    sys.exit(main())
