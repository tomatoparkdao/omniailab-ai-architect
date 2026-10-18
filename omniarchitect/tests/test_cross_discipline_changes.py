"""跨专业变更：一次改动落在多个专业上，不能只当一个专业的事。

这组测试守的是最容易出错、后果最贵的判断：

* 「屋顶改成花园」不是改材料；
* 「加泳池」不是加个装饰；
* 「建筑后退两米」不是微调；
* 而「客厅墙面换个颜色」也不该让结构景观全部返工。

同时守一条纪律：没有结构依据不能说已验算，没有排水条件不能说已核定。

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import tempfile
from pathlib import Path

from omniarchitect import changes
from omniarchitect.demo import build_demo_project


def _project(tmp: Path):
    return build_demo_project(tmp / "proj")


# --------------------------------------------------------------------------
# 1. 识别：跨专业规则必须命中，且说清"不是只改这个"
# --------------------------------------------------------------------------
def test_roof_garden_is_not_a_material_change():
    with tempfile.TemporaryDirectory() as td:
        p = _project(Path(td))
        rep = changes.analyse(p, "屋顶改成花园，种点植物", apply=False)
        ids = {x["id"] for x in rep.cross_discipline}
        assert "XD-ROOF-GARDEN" in ids, ids
        x = next(x for x in rep.cross_discipline if x["id"] == "XD-ROOF-GARDEN")
        assert set(x["disciplines"]) == {"architecture", "structure",
                                         "landscape", "mep"}, x["disciplines"]
        assert x["not_just"] == "改材料", x["not_just"]
        # 结构那一项必须写清"需要什么才能定"，不能只说"要注意"
        st = next(a for a in x["affects"] if a["discipline"] == "structure")
        assert "荷载" in st["needs"], st
        # 落点必须早于"改材料"的 S4 —— 结构条件在 S3 就要定
        assert rep.diagnosis.landing_stage <= "S3", rep.diagnosis.landing_stage


def test_pool_brings_structure_waterproofing_and_electrics():
    with tempfile.TemporaryDirectory() as td:
        p = _project(Path(td))
        rep = changes.analyse(p, "院子里加一个泳池", apply=False)
        x = next(x for x in rep.cross_discipline if x["id"] == "XD-POOL")
        assert {"structure", "architecture", "mep"} <= set(x["disciplines"]), x
        joined = " ".join(a["needs"] for a in x["affects"])
        assert "水深" in joined or "荷载" in joined
        assert any("等电位" in r for r in rep.risks), rep.risks


def test_moving_the_building_touches_planning_and_site_drainage():
    with tempfile.TemporaryDirectory() as td:
        p = _project(Path(td))
        rep = changes.analyse(p, "建筑往后退两米", apply=False)
        x = next(x for x in rep.cross_discipline if x["id"] == "XD-BUILDING-MOVE")
        assert {"planning", "architecture", "structure", "landscape"} <= set(
            x["disciplines"]), x
        assert rep.diagnosis.landing_stage == "S2", rep.diagnosis.landing_stage


def test_adding_a_floor_is_not_just_adding_a_room():
    with tempfile.TemporaryDirectory() as td:
        p = _project(Path(td))
        rep = changes.analyse(p, "三楼加建一间客房", apply=False)
        x = next(x for x in rep.cross_discipline if x["id"] == "XD-ADD-FLOOR")
        assert "structure" in x["disciplines"] and "planning" in x["disciplines"]
        assert any("消防" in a["aspect"] for a in x["affects"]), x["affects"]


# --------------------------------------------------------------------------
# 2. 不该被夸大的：换颜色不该让结构和景观全返工
# --------------------------------------------------------------------------
def test_repainting_a_wall_does_not_trigger_cross_discipline_rework():
    with tempfile.TemporaryDirectory() as td:
        p = _project(Path(td))
        rep = changes.analyse(p, "客厅墙面换个颜色，暖灰改成奶白", apply=False)
        assert not rep.cross_discipline, [x["id"] for x in rep.cross_discipline]
        assert rep.scope == "local", rep.scope
        assert rep.diagnosis.geometry_affecting is False


# --------------------------------------------------------------------------
# 3. 专业边界的硬话：没有依据不许说已验算/已核定
# --------------------------------------------------------------------------
def test_structural_reinforcement_without_a_survey_says_so():
    with tempfile.TemporaryDirectory() as td:
        p = _project(Path(td))
        rep = changes.analyse(p, "楼板承重不够，要加固", apply=False)
        x = next(x for x in rep.cross_discipline if x["id"] == "XD-STRUCT-REINFORCE")
        st = next(a for a in x["affects"] if a["discipline"] == "structure")
        assert "鉴定" in st["needs"], st
        assert any("无依据施工" in r for r in rep.risks), rep.risks


def test_cross_discipline_report_lists_every_affected_discipline_in_markdown():
    with tempfile.TemporaryDirectory() as td:
        p = _project(Path(td))
        rep = changes.analyse(p, "屋顶改成花园，种点植物", apply=False)
        md = rep.markdown()
        assert "跨专业影响" in md
        for label in ("建筑", "结构", "景观", "机电"):
            assert label in md, label
        assert "这不只是一处改动" in md
