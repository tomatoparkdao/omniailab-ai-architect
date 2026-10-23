"""S3–S8 打通时新增/修改行为的守卫测试。

守四件事：

1. 原始条件导入：只认已量测的轮廓，宁可拒绝也不生成假几何；
2. 面积单位换算：公顷/亩读错，总平面就会"放不下"；
3. 住宅房间任务表：面积未知不编面积，孩子数与书房按原话；
4. `run --all` 跳过已确认阶段，不把"继续往下做"报成错误。

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import tempfile
from pathlib import Path

from omniarchitect import existing, program
from omniarchitect.model import Element, Level, Project, Space
from omniarchitect.sector import brief as sector_brief
from omniarchitect.sector.model_preview import export as preview_export

PLAN = [[0, 0], [12000, 0], [12000, 9000], [0, 9000]]


def _conditions(**over) -> dict:
    data = {
        "format": existing.FORMAT,
        "source": "client_survey",
        "unit": "mm",
        "level": {"id": "L1", "name": "一层", "height_mm": 2900},
        "envelope": PLAN,
        "walls": [{"start": [0, 0], "end": [12000, 0], "thickness_mm": 240,
                   "kind": "exterior"}],
    }
    data.update(over)
    return data


# --------------------------------------------------------------------------
# 1. 原始条件导入
# --------------------------------------------------------------------------
def test_conditions_import_builds_envelope_and_walls() -> None:
    p = Project(project_id="t")
    got = existing.apply(p, _conditions())
    assert got["envelope_area_m2"] == 108.0
    assert [s for s in p.spaces if s.use == "envelope"]
    assert len(p.by_type("wall")) == 1
    assert p.meta["existing_conditions"]["source"] == "client_survey"


def test_conditions_reject_what_cannot_be_used_as_geometry() -> None:
    """没有坐标、单位不对、点太少——一律拒绝，不替客户补数。"""
    for bad in ({"unit": "m"}, {"envelope": [[0, 0], [1, 1]]}, {"envelope": []}):
        try:
            existing.validate(_conditions(**bad))
        except existing.ConditionsError:
            continue
        raise AssertionError(f"应当拒绝：{bad}")


def test_conditions_refuse_to_overwrite_existing_geometry() -> None:
    """已有轮廓时导入 = 几何变更，必须走 change，不能悄悄替换。"""
    p = Project(project_id="t")
    existing.apply(p, _conditions())
    try:
        existing.apply(p, _conditions())
    except existing.ConditionsError as exc:
        assert "几何变更" in str(exc)
    else:
        raise AssertionError("第二次导入应被拒绝")


def test_uncertain_walls_stay_uncertain() -> None:
    p = Project(project_id="t")
    data = _conditions(walls=[{"start": [0, 0], "end": [6000, 0],
                               "thickness_mm": 200, "kind": "partition",
                               "uncertain": True, "note": "图纸未标注厚度"}])
    existing.apply(p, data)
    wall = p.by_type("wall")[0]
    assert wall.uncertain is True
    assert wall.confidence < 0.9


# --------------------------------------------------------------------------
# 2. 面积单位
# --------------------------------------------------------------------------
def test_site_area_reads_hectares_and_mu() -> None:
    """2.4 公顷必须读成 24000 m²；读成 2.4 会让总平面直接放不下。"""
    assert sector_brief._first("新征用地约 2.4 公顷", "site_area") == 24000.0  # noqa: SLF001
    assert round(sector_brief._first("用地 15 亩", "site_area")) == 10000  # noqa: SLF001
    assert sector_brief._first("用地 8000 平方米", "site_area") == 8000.0  # noqa: SLF001


# --------------------------------------------------------------------------
# 3. 住宅房间任务表
# --------------------------------------------------------------------------
def _house(area_pts=PLAN, needs="一家四口，两个孩子分别 7 岁和 3 岁，主卧想要一个能关起来的书房"):
    p = Project(project_id="h")
    p.meta = {"intake": {"answers": [{"id": "base.needs", "value": needs}]}}
    p.levels = [Level(id="L1", name="一层", height_mm=2900)]
    p.spaces = [Space(id="S-ENV", level_id="L1", name="套内轮廓", use="envelope",
                      boundary_mm2d=[list(x) for x in area_pts])]
    return p


def test_house_program_follows_area_and_family() -> None:
    p = _house()
    rows = program.build(p)
    names = [r["name"] for r in rows]
    assert sum(1 for n in names if n.startswith("儿童房")) == 2
    assert any("书房" in n for n in names)
    assert any("主卧" in n for n in names)
    total = sum(r["area_m2"] for r in rows)
    assert total < program.envelope_area(p)      # 走廊与墙体必须留出来
    assert all(r.get("basis") for r in rows)     # 每个目标面积都要能说清来源


def test_house_program_refuses_to_invent_area() -> None:
    """没有轮廓也没有声明面积：返回空表，让 S3 如实说缺资料。"""
    p = Project(project_id="h")
    p.meta = {"intake": {"answers": [{"id": "base.needs", "value": "三居室"}]}}
    assert program.build(p) == []


def test_children_count_reads_the_words() -> None:
    assert program.children_count("两个孩子分别 7 岁和 3 岁") == 2
    assert program.children_count("一个小孩") == 1
    assert program.children_count("夫妻两人自住") == 0


# --------------------------------------------------------------------------
# 4. run --all 跳过已确认阶段
# --------------------------------------------------------------------------
def test_run_all_skips_confirmed_stages() -> None:
    from omniarchitect import demo, workflow
    from omniarchitect.stage_state import CONFIRMED, get_state

    tmp = Path(tempfile.mkdtemp(prefix="omniailab-s38-"))
    p = demo.build_demo_project(tmp)
    runner = workflow.StageRunner(p, tmp / "out", project_dir=tmp)
    runner.stage_S1()
    runner.approve("S1", by="业主", source="demo", note="演示确认")
    assert get_state(p, "S1").status == CONFIRMED
    m = runner.run_all(confirm_all=True, stages=("S1",))
    assert m.outcomes[-1].status == "skipped", m.outcomes[-1].to_dict()


# --------------------------------------------------------------------------
# 5. 模型检视图带房间名
# --------------------------------------------------------------------------
def test_model_preview_draws_room_labels() -> None:
    tmp = Path(tempfile.mkdtemp(prefix="omniailab-axon-"))
    obj = tmp / "m.obj"
    obj.write_text(
        "v 0 0 0\nv 4000 0 0\nv 4000 3000 0\nv 0 3000 0\n"
        "v 0 0 2800\nv 4000 0 2800\nv 4000 3000 2800\nv 0 3000 2800\n"
        "usemtl floor\nf 1 2 3 4\nusemtl wall\nf 1 2 6 5\n",
        encoding="utf-8")
    out = tmp / "m.svg"
    got = preview_export(obj, out, title="t", labels=[(2000, 1500, 1400, "客厅")])
    assert got["vertices"] == 8 and got["faces"] == 2
    svg = out.read_text(encoding="utf-8")
    assert "客厅" in svg
