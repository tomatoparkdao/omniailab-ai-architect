"""产物边界守卫：测试与演示文件不得落在技能目录内。

这条规则来自实际代价：技能目录里曾堆了 1.3 GB / 66 个 run 目录的渲染产物，
导致"这个技能到底发布了什么"完全看不出来，也让一次 git status 要用放大镜。
现在产物统一放到技能目录**隔壁**的 `缓存测试文件/`。

四道关口，任何一道被绕过都会红：

1. 默认输出根在技能目录之外；
2. 技能目录里没有 `out/` 或 `run-*` 这类运行时目录；
3. `ScenarioRunner` 的默认根也在外面；
4. 没有任何脚本把默认输出写回技能目录（源码级扫描，防以后有人手滑）。

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import os
from pathlib import Path

from omniarchitect import paths


def _inside_skill(p: Path) -> bool:
    try:
        p.resolve().relative_to(paths.ROOT.resolve())
        return True
    except ValueError:
        return False


def test_default_output_root_is_outside_the_skill_folder() -> None:
    """不传路径时，落点必须在技能目录外。"""
    root = paths.test_output_root()
    assert not _inside_skill(root), f"产物根仍在技能目录内：{root}"
    assert paths.ROOT.name not in root.parts


def test_ensure_output_dir_never_lands_inside_the_skill() -> None:
    """`ensure_output_dir()` 不传参时同样在外面，而且真的被创建出来。"""
    out = paths.ensure_output_dir(None)
    assert not _inside_skill(out)
    assert out.is_dir()
    assert out.parent == paths.test_output_root()


def test_skill_folder_has_no_runtime_output_dirs() -> None:
    """技能目录里不该出现 out/ 或 run-2026xxxx 这类目录。

    允许 projects/ 存在：那里有已入库的示例项目（demo-120 等），是技能内容，
    不是跑测试跑出来的垃圾。禁的是"跑一次就生成一堆"的目录。
    """
    stray_out = paths.ROOT / "out"
    assert not stray_out.exists(), f"技能目录内仍有 out/：{stray_out}"
    runs = [p for p in paths.ROOT.glob("run-*") if p.is_dir()]
    assert not runs, f"技能目录内有运行目录：{[p.name for p in runs][:3]}"


def test_scenario_runner_defaults_outside_the_skill_folder() -> None:
    from omniarchitect.scenarios import ScenarioRunner

    runner = ScenarioRunner()
    assert not _inside_skill(runner.out_root)
    assert runner.out_root.name == "scenarios"


def test_no_script_writes_to_the_skill_folder_by_default() -> None:
    """源码级扫描：不允许 `ROOT / "out"` 这类默认落点再出现。"""
    offenders = []
    for p in sorted((paths.ROOT / "scripts").glob("*.py")):
        text = p.read_text(encoding="utf-8", errors="replace")
        for pattern in ('ROOT / "out"', "ROOT / 'out'", 'ROOT/"out"'):
            if pattern in text:
                offenders.append(f"{p.name}: {pattern}")
    assert not offenders, "这些脚本仍默认写进技能目录：" + "；".join(offenders)


def test_no_test_writes_into_the_skill_folder_either() -> None:
    """测试自己也守同一条线：`parents[N] / "out"` 一律不许。

    第一版守卫只扫了 scripts/，结果测试用例把产物写回技能目录，
    跑完一轮 `out/` 又长出来了。测试和脚本一起吃。
    """
    offenders = []
    for p in sorted((paths.ROOT / "omniarchitect" / "tests").glob("*.py")):
        if p.name == "test_output_layout.py":
            continue
        text = p.read_text(encoding="utf-8", errors="replace")
        for pattern in ('parents[2] / "out"', "parents[2] / 'out'",
                        'Path("out")', "out_dir=\"out/"):
            if pattern in text:
                offenders.append(f"{p.name}: {pattern}")
    assert not offenders, "这些测试仍写进技能目录：" + "；".join(offenders)


def test_no_test_writes_into_the_skill_folder_either() -> None:
    """测试自己也守同一条线：`parents[N] / "out"` 一律不许。

    第一版守卫只扫了 scripts/，结果测试用例把产物写回技能目录，
    跑完一轮 `out/` 又长出来了。测试和脚本一起吃。
    """
    offenders = []
    for p in sorted((paths.ROOT / "omniarchitect" / "tests").glob("*.py")):
        if p.name == "test_output_layout.py":
            continue
        text = p.read_text(encoding="utf-8", errors="replace")
        for pattern in ('parents[2] / "out"', "parents[2] / 'out'",
                        'Path("out")', "out_dir=\"out/"):
            if pattern in text:
                offenders.append(f"{p.name}: {pattern}")
    assert not offenders, "这些测试仍写进技能目录：" + "；".join(offenders)


def test_env_override_is_honoured() -> None:
    """`OMNI_TEST_OUTPUT` 优先——CI 或换盘时不必改代码。"""
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        old = os.environ.get("OMNI_TEST_OUTPUT")
        os.environ["OMNI_TEST_OUTPUT"] = td
        try:
            assert str(paths.test_output_root()) == str(Path(td))
            assert paths.ensure_output_dir(None).parent == Path(td)
        finally:
            if old is None:
                os.environ.pop("OMNI_TEST_OUTPUT", None)
            else:
                os.environ["OMNI_TEST_OUTPUT"] = old
