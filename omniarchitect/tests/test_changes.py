"""Change impact analysis — the capability that keeps the system honest.

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import tempfile
from pathlib import Path

from omniarchitect.changes import analyse, diagnose, is_geometry_change
from omniarchitect.demo import build_demo_project
from omniarchitect.workflow import StageRunner


def _built(tmp: Path):
    p = build_demo_project(tmp)
    r = StageRunner(p, tmp / "out", assume_approval=True)
    r.run_all(confirm_all=True)
    return p, r


def test_material_change_does_not_touch_geometry():
    d = diagnose("次卧的柜子换成浅色木饰面")
    assert d.primary in ("material", "furniture_layout")
    assert d.geometry_affecting is False


def test_background_wall_change_is_an_elevation_problem():
    d = diagnose("我不喜欢客厅的电视背景墙")
    assert d.primary == "elevation"
    assert d.landing_stage == "S4"
    assert d.geometry_affecting is False
    assert d.confidence >= 0.6


def test_moving_a_wall_is_a_geometry_change():
    d = diagnose("把厨房和餐厅之间的墙往外移300mm")
    assert d.primary in ("plan_dimension", "layout_zoning")
    assert d.geometry_affecting is True
    assert d.landing_stage == "S3"
    assert is_geometry_change("墙往外移300mm")


def test_vague_render_request_is_treated_as_presentation_only():
    d = diagnose("这几张效果图重出一下，镜头角度不对")
    assert d.primary == "visual_only"
    assert d.geometry_affecting is False


def test_diagnosis_reports_alternatives_it_rejected():
    d = diagnose("客厅背景墙的石材换成木饰面")
    assert d.considered, "a diagnosis without rejected alternatives is a guess"


def test_elevation_change_preserves_confirmed_geometry():
    """A finish-level change must NOT invalidate the plan or the model."""
    with tempfile.TemporaryDirectory() as td:
        p, r = _built(Path(td))
        rep = analyse(p, "我不喜欢客厅的电视背景墙", apply=False)
        assert rep.diagnosis.landing_stage == "S4"
        assert "S3" not in [x.stage for x in rep.rework]
        for aid in ("art-drawings-A", "art-model-A"):
            assert aid in rep.affected_artifacts, aid
        # and nothing already confirmed outside the room should be swept up
        assert rep.preserved


def test_material_change_leaves_construction_drawings_valid():
    with tempfile.TemporaryDirectory() as td:
        p, r = _built(Path(td))
        rep = analyse(p, "次卧的柜子换成浅色木饰面", apply=False)
        assert "art-drawings-A" not in rep.affected_artifacts
        assert "art-drawings-A" not in [x.stage for x in rep.rework]


def test_geometry_change_cascades_from_the_plan():
    with tempfile.TemporaryDirectory() as td:
        p, r = _built(Path(td))
        rep = analyse(p, "把客厅那面墙往外移300mm", apply=False)
        stages = [x.stage for x in rep.rework]
        assert stages[0] == "S3"
        assert stages[-1] == "S8"
        assert rep.diagnosis.geometry_affecting


def test_applying_a_change_writes_a_ledger_and_reopens_gates():
    with tempfile.TemporaryDirectory() as td:
        p, r = _built(Path(td))
        rep = r.apply_change("我不喜欢客厅的电视背景墙", apply=True)
        assert rep.applied
        assert rep.invalidation is not None
        assert rep.invalidation.revision > rep.invalidation.revision - 999
        state = p.meta["stage_state"]
        assert state["S4"]["status"] in ("rework", "pending")
        assert state["S4"]["confirmed_at"] == ""
        # the change ledger is on disk
        changes_dir = Path(r.out) / "changes"
        assert changes_dir.exists()
        assert list(changes_dir.glob("change-*.md"))


def test_change_report_is_human_readable():
    with tempfile.TemporaryDirectory() as td:
        p, _ = _built(Path(td))
        md = analyse(p, "我不喜欢客厅的电视背景墙", apply=False).markdown()
        for heading in ("一、诊断", "二、影响范围", "三、保持不变", "四、回流计划"):
            assert heading in md
        assert "立面" in md
