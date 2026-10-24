"""产物边界守卫：技能目录里只有能力，没有跑出来的东西。

这条规则来自实际代价：技能目录（含同级缓存目录）曾堆到 1.34 GB /
30111 个文件，`installer/manifest.json` 甚至把某次演示的 PPTX、PNG 登记成了
分发包内容。结果是"这个技能到底发布了什么"根本看不出来。

现在分两层守：

1. **落点**：默认输出、项目、缓存都走 `omniarchitect.workspace`，在技能目录之外；
2. **形状**：技能目录里不出现 `out/`、`run-*`、CAD/模型/影音生成物。

再加一层"防以后手滑"：源码级扫描 —— 脚本和测试里不许再出现
`ROOT / "out"` 这种默认落点，也不许自己拼一个 `projects/`。

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import os
from pathlib import Path

from omniarchitect import paths, workspace


def _inside_skill(p: Path) -> bool:
    try:
        Path(p).resolve().relative_to(paths.ROOT.resolve())
        return True
    except ValueError:
        return False


def test_default_output_root_is_outside_the_skill_folder() -> None:
    """不传路径时，落点必须在技能目录外。"""
    root = paths.test_output_root()
    assert not _inside_skill(root), f"产物根仍在技能目录内：{root}"
    assert paths.ROOT.name not in root.parts
    assert root == workspace.path("tests")


def test_every_workspace_partition_is_outside_the_skill() -> None:
    """五个分区一个都不能落回技能目录。"""
    for kind in workspace.KINDS:
        p = workspace.path(kind)
        assert not _inside_skill(p), f"{kind} 分区在技能目录内：{p}"


def test_ensure_output_dir_never_lands_inside_the_skill() -> None:
    """`ensure_output_dir()` 不传参时落到工作区 `outputs/`，而且真的被创建出来。"""
    out = paths.ensure_output_dir(None)
    assert not _inside_skill(out)
    assert out.is_dir()
    assert out == workspace.path("outputs")


def test_ensure_output_dir_keeps_explicit_paths() -> None:
    """显式路径原样尊重（临时目录、客户盘符），不偷偷改道。"""
    with workspace.tempdir("path-check-") as td:
        assert paths.ensure_output_dir(td / "somewhere").parent == td


def test_skill_folder_has_no_runtime_output_dirs() -> None:
    """技能目录里不该出现 out/、run-2026xxxx、projects/ 这类运行时目录。"""
    for name in ("out", "projects", "outputs", "cache", "archive", ".pytest_cache"):
        p = paths.ROOT / name
        assert not p.exists(), f"技能目录内仍有 {name}/：{p}"
    runs = [p for p in paths.ROOT.glob("run-*") if p.is_dir()]
    assert not runs, f"技能目录内有运行目录：{[p.name for p in runs][:3]}"


def test_skill_folder_has_no_generated_artefacts() -> None:
    """技能目录里不该有 CAD / 模型 / 图纸 / 影音这类生成物。

    例外只有 `examples/` 里的结构化 JSON 与 `knowledge/` 里的风格数据 —— 那是内容。
    """
    banned = {".dxf", ".dwg", ".obj", ".fbx", ".glb", ".blend", ".ifc", ".skp",
              ".pptx", ".pdf", ".png", ".jpg", ".jpeg", ".mp4", ".zip", ".svg"}
    found = []
    for p in paths.ROOT.rglob("*"):
        if not p.is_file():
            continue
        rel = p.relative_to(paths.ROOT)
        if rel.parts and rel.parts[0] == ".git":
            continue
        if p.suffix.lower() in banned:
            found.append(str(rel))
    assert not found, f"技能目录里有生成物：{found[:5]}"


def test_scenario_runner_defaults_outside_the_skill_folder() -> None:
    from omniarchitect.scenarios import ScenarioRunner

    runner = ScenarioRunner()
    assert not _inside_skill(runner.out_root)
    assert runner.out_root == workspace.path("tests") / "scenarios"


def test_no_script_writes_to_the_skill_folder_by_default() -> None:
    """源码级扫描：不允许 `ROOT / "out"`、`ROOT / "projects"` 这类默认落点再出现。"""
    offenders = []
    patterns = ('ROOT / "out"', "ROOT / 'out'", 'ROOT/"out"',
                'ROOT / "projects"', "ROOT / 'projects'")
    for p in sorted((paths.ROOT / "scripts").glob("*.py")):
        text = p.read_text(encoding="utf-8", errors="replace")
        for pattern in patterns:
            if pattern in text:
                offenders.append(f"{p.name}: {pattern}")
    assert not offenders, "这些脚本仍默认写进技能目录：" + "；".join(offenders)


def test_no_test_writes_into_the_skill_folder_either() -> None:
    """测试自己也守同一条线：`parents[N] / "out"` 一律不许。"""
    offenders = []
    for p in sorted((paths.ROOT / "omniarchitect" / "tests").glob("*.py")):
        if p.name == "test_output_layout.py":
            continue
        text = p.read_text(encoding="utf-8", errors="replace")
        for pattern in ('parents[2] / "out"', "parents[2] / 'out'",
                        'Path("out")', 'out_dir="out/'):
            if pattern in text:
                offenders.append(f"{p.name}: {pattern}")
    assert not offenders, "这些测试仍写进技能目录：" + "；".join(offenders)


def test_no_module_builds_project_paths_from_the_skill_root() -> None:
    """`paths.PROJECTS` 已被删除：项目数据不在技能目录里。

    如果有人又把 `PROJECTS = ROOT / "projects"` 加回去，这里会红。
    """
    assert not hasattr(paths, "PROJECTS"), "paths.PROJECTS 不该存在，请用 paths.projects_root()"
    assert paths.projects_root() == workspace.path("projects")
    assert not _inside_skill(paths.projects_root())


def test_env_override_is_honoured() -> None:
    """`OMNIAILAB_TESTS_DIR` 优先——CI 或换盘时不必改代码。"""
    with workspace.tempdir("env-check-") as td:
        keys = ("OMNIAILAB_TESTS_DIR", "OMNI_TEST_OUTPUT")
        old = {k: os.environ.get(k) for k in keys}
        os.environ["OMNIAILAB_TESTS_DIR"] = str(td)
        try:
            assert str(paths.test_output_root()) == str(Path(td))
        finally:
            for k, v in old.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v


def test_legacy_env_still_works() -> None:
    """老变量 `OMNI_TEST_OUTPUT` 不失效（脚本/CI 里可能还写着）。"""
    with workspace.tempdir("legacy-") as td:
        keys = ("OMNIAILAB_TESTS_DIR", "OMNI_TEST_OUTPUT")
        old = {k: os.environ.get(k) for k in keys}
        os.environ.pop("OMNIAILAB_TESTS_DIR", None)
        os.environ["OMNI_TEST_OUTPUT"] = str(td)
        try:
            assert str(paths.test_output_root()) == str(Path(td))
        finally:
            for k, v in old.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v


def test_workspace_root_can_be_relocated_wholesale() -> None:
    """`OMNIAILAB_WORKSPACE` 一改，五个分区整体跟着走。"""
    with workspace.tempdir("ws-root-") as td:
        old = {k: os.environ.get(k) for k in
               ("OMNIAILAB_WORKSPACE", "OMNIAILAB_TESTS_DIR", "OMNI_TEST_OUTPUT")}
        for k in old:
            os.environ.pop(k, None)
        os.environ["OMNIAILAB_WORKSPACE"] = str(td)
        try:
            assert workspace.root() == Path(td)
            for kind in workspace.KINDS:
                assert workspace.path(kind) == Path(td) / kind
        finally:
            for k, v in old.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v


def test_resolve_project_finds_projects_in_the_workspace() -> None:
    """`--project demo-120` 与 `--project projects/demo-120` 都能解析到工作区。"""
    with workspace.tempdir("resolve-") as td:
        old = os.environ.get("OMNIAILAB_PROJECTS_DIR")
        os.environ["OMNIAILAB_PROJECTS_DIR"] = str(td)
        try:
            (Path(td) / "demo-x").mkdir()
            assert workspace.resolve_project("demo-x") == Path(td) / "demo-x"
            assert workspace.resolve_project("projects/demo-x") == Path(td) / "demo-x"
            try:
                workspace.resolve_project("no-such-project")
            except FileNotFoundError as exc:
                assert "找过" in str(exc), "报错要说清找过哪些位置"
            else:
                raise AssertionError("不存在的项目应当报 FileNotFoundError")
        finally:
            if old is None:
                os.environ.pop("OMNIAILAB_PROJECTS_DIR", None)
            else:
                os.environ["OMNIAILAB_PROJECTS_DIR"] = old


def test_scratch_is_removed_on_exit() -> None:
    """`workspace.scratch()` 退出即删 —— 临时中间件不该留下来。"""
    with workspace.scratch("guard-") as d:
        (d / "x.txt").write_text("x", encoding="utf-8")
        assert d.exists() and not _inside_skill(d)
    assert not d.exists(), "scratch 目录退出后应当被删除"
