#!/usr/bin/env python
"""Zero-dependency test runner.

The suite is written so it runs with pytest *or* with nothing at all. On a
workstation with no network and no pip, verification must still be possible —
that is the whole point of the adapter-degradation design.

    python scripts/run_tests.py            # run everything
    python scripts/run_tests.py planner    # only modules matching 'planner'
    python scripts/run_tests.py -v

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import importlib
import inspect
import io
import os
import sys
import time
import traceback
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent          # project root
sys.path.insert(0, str(ROOT))                          # makes the package importable

# The suite must pass on a machine with no internet. Case research reaches out
# to real sites on the live path, so it is switched off here rather than in each
# test — one switch, and `scripts/research_three_cases.py` is the place where
# network behaviour is exercised deliberately.
os.environ.setdefault("OMNIAILAB_NO_NETWORK", "1")

PACKAGE = "omniarchitect"
TEST_DIR = ROOT / PACKAGE / "tests"


def discover(pattern: str = "") -> list:
    mods = []
    for p in sorted(TEST_DIR.glob("test_*.py")):
        if pattern and pattern not in p.stem:
            continue
        name = f"{PACKAGE}.tests.{p.stem}"
        try:
            mods.append(importlib.import_module(name))
        except Exception as exc:  # a module that will not import is a failure
            print(f"[IMPORT FAIL] {p.name}: {exc}")
            raise
    return mods


def main(argv: list) -> int:
    verbose = "-v" in argv
    pattern = next((a for a in argv[1:] if not a.startswith("-")), "")
    mods = discover(pattern)

    passed = failed = 0
    failures = []
    t0 = time.time()
    for mod in mods:
        fns = [
            (name, fn) for name, fn in vars(mod).items()
            if name.startswith("test_") and inspect.isfunction(fn)
            and fn.__module__ == mod.__name__
        ]
        for name, fn in sorted(fns):
            buf = io.StringIO()
            try:
                with redirect_stdout(buf):
                    fn()
            except Exception:
                failed += 1
                failures.append((mod.__name__, name, traceback.format_exc()))
                print(f"FAIL  {mod.__name__}.{name}")
            else:
                passed += 1
                if verbose:
                    print(f"ok    {mod.__name__}.{name}")

    dt = time.time() - t0
    print()
    for mod_name, name, tb in failures:
        print("=" * 78)
        print(f"FAILURE: {mod_name}.{name}")
        print(tb.rstrip())
    print("=" * 78)
    print(f"passed {passed}　failed {failed}　in {dt:.2f}s　({len(mods)} module(s))")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
