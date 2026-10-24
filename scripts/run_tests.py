#!/usr/bin/env python
"""Zero-dependency test runner.

The suite is written so it runs with pytest *or* with nothing at all. On a
workstation with no network and no pip, verification must still be possible —
that is the whole point of the adapter-degradation design.

    python scripts/run_tests.py            # run everything, throw the artefacts away
    python scripts/run_tests.py planner    # only modules matching 'planner'
    python scripts/run_tests.py -v
    python scripts/run_tests.py --keep     # keep artefacts in the workspace
    python scripts/run_tests.py --artifacts E:\\somewhere

**默认不产生"垃圾"**：这一轮跑出来的测试项目、DXF、截图、模型都写在系统临时目录里，
跑完即删 —— 失败时例外，会保留并把路径打出来，方便复盘。
想留档就显式 `--keep`（写进工作区 `tests/`）或 `--artifacts <目录>`。

无论哪种模式，产物都在**技能目录之外**：技能目录只放能力。

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import importlib
import inspect
import io
import os
import shutil
import sys
import tempfile
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


def _setup_artefact_dir(argv: list) -> tuple[Path, bool]:
    """决定这一轮的产物落点。返回 (目录, 是否跑完就删)。"""
    from omniarchitect import workspace

    explicit = None
    if "--artifacts" in argv:
        i = argv.index("--artifacts")
        if i + 1 < len(argv):
            explicit = argv[i + 1]
    keep = "--keep" in argv

    if explicit:
        d = Path(explicit).expanduser().resolve()
        d.mkdir(parents=True, exist_ok=True)
        os.environ["OMNIAILAB_TESTS_DIR"] = str(d)
        return d, False
    if keep:
        d = workspace.tests_dir()
        os.environ["OMNIAILAB_TESTS_DIR"] = str(d)
        return d, False
    d = Path(tempfile.mkdtemp(prefix="omniailab-tests-"))
    os.environ["OMNIAILAB_TESTS_DIR"] = str(d)
    return d, True


def _drop(d: Path, keep: bool) -> None:
    """跑完收摊 —— 只在"这是本轮临时目录"时删，绝不碰别人给的目录。"""
    if keep:
        print(f"临时产物已保留：{d}")
        return
    try:
        shutil.rmtree(d)
        print(f"临时产物已清理：{d}")
    except OSError as exc:
        print(f"临时产物清理失败（{exc}），目录留在：{d}")


def main(argv: list) -> int:
    verbose = "-v" in argv
    skip_next = False
    pattern = ""
    for a in argv[1:]:
        if skip_next:
            skip_next = False
            continue
        if a == "--artifacts":
            skip_next = True
            continue
        if not a.startswith("-"):
            pattern = a
            break

    artefacts, disposable = _setup_artefact_dir(argv)
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
    print(f"产物目录：{artefacts}")
    if disposable:
        # 失败时留着 —— 刚红过的现场比"干净"重要
        _drop(artefacts, keep=bool(failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
