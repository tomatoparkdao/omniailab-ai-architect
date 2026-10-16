#!/usr/bin/env python
"""Verify an installed OmniArchitect skill — or the checkout itself.

    python installer/verify_install.py                       # 校验本仓库
    python installer/verify_install.py --target ~/.codex/skills/omniailab-ai-architect
    python installer/verify_install.py --check-python        # 同时跑包导入自检

Exit codes: 0 ok · 1 problems found.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from omniailab_ai_architect.integration import agent_skills as sk  # noqa: E402
from omniailab_ai_architect.integration import installer as inst  # noqa: E402


def check_python(package_root: Path) -> dict:
    """Prove the package imports and the closed loop tool is present."""
    import subprocess

    code = (
        "import sys; sys.path.insert(0, r'%s');"
        "import omniailab_ai_architect as oa;"
        "from omniailab_ai_architect.tools import registry;"
        "r = registry().detect_report();"
        "print(oa.__version__);"
        "print(','.join(r['available']))" % str(package_root)
    )
    proc = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    ok = proc.returncode == 0
    return {"ok": ok, "stdout": proc.stdout.strip(), "stderr": proc.stderr.strip()[-400:]}


def main(argv: list | None = None) -> int:
    ap = argparse.ArgumentParser(prog="verify_install.py", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--target", default=None)
    ap.add_argument("--check-python", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    target = Path(args.target).expanduser() if args.target else ROOT
    rep: dict = {"checkout": str(ROOT), "target": str(target)}
    rep["skill_issues"] = sk.validate(target / "SKILL.md")
    rep["install"] = inst.verify(target) if args.target else {
        "ok": True, "mode": "checkout", "note": "校验的是仓库本身，不是安装副本"
    }
    if args.check_python:
        rep["python"] = check_python(ROOT)

    problems = list(rep["skill_issues"])
    if not rep["install"].get("ok", True):
        problems += rep["install"].get("errors", [])
    if args.check_python and not rep.get("python", {}).get("ok"):
        problems.append("python 自检失败：" + rep["python"]["stderr"])
    rep["ok"] = not problems
    rep["problems"] = problems

    if args.json:
        print(json.dumps(rep, ensure_ascii=False, indent=2))
    else:
        print(f"仓库：{rep['checkout']}")
        print(f"目标：{rep['target']}")
        print(f"SKILL.md 校验：{'通过' if not rep['skill_issues'] else '有问题'}")
        for i in rep["skill_issues"]:
            print(f"  ! {i}")
        inst_rep = rep["install"]
        if args.target:
            print(f"安装校验：{'通过' if inst_rep.get('ok') else '未通过'}"
                  f"　模式 {inst_rep.get('mode', 'pointer')}")
            for e in inst_rep.get("errors", []):
                print(f"  ! {e}")
        else:
            print(f"安装校验：{inst_rep.get('note')}")
        if args.check_python:
            py = rep.get("python", {})
            print(f"Python 自检：{'通过' if py.get('ok') else '失败'}")
            if py.get("stdout"):
                for line in py["stdout"].splitlines():
                    print(f"  {line}")
            if py.get("stderr"):
                print(f"  {py['stderr']}")
        print()
        print("结论：" + ("全部通过" if rep["ok"] else f"{len(problems)} 项问题"))
    return 0 if rep["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
