"""Workflow-integration tests: the six stage hooks and their outputs.

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from omniarchitect.style import catalog as C  # noqa: E402
from omniarchitect.style import compiler as K  # noqa: E402
from omniarchitect.style import hooks as W  # noqa: E402

CAT = C.load_catalog()


def test_six_stages_have_hooks_and_the_rest_do_not():
    hooked = {h["stage"] for h in W.all_hooks()}
    assert hooked == {"S2", "S3", "S4", "S5", "S7", "S8"}
    for stage in ("S1", "S6"):
        h = W.hook(stage)
        assert h["actions"] == []
        assert "无风格系统挂钩" in h["name"]


def test_every_hook_declares_actions_api_outputs_and_a_rule():
    for h in W.all_hooks():
        assert h["actions"], h["stage"]
        assert h["api"], h["stage"]
        assert h["produces"], h["stage"]
        assert h["rule"], h["stage"]


def test_gates_are_named_for_each_hook():
    for h in W.all_hooks():
        assert h["gate"].startswith("G"), h["stage"]


def test_s5_hook_states_the_geometry_disclaimer():
    h = W.hook("S5")
    assert "不承载几何" in h["rule"]
    assert "校核" in h["rule"]


def test_space_check_reports_conflicts_without_deciding():
    brief = K.SpaceBrief(space_name="客厅", width_mm=3000, depth_mm=4200,
                         ceiling_mm=2300)
    rep = W.style_space_check("european-classical", brief, catalogue=CAT)
    assert rep["stage"] == "S3"
    assert rep["conflicts"], "净高不足时应报冲突"
    assert len(rep["decision_paths"]) == 2
    assert "不由系统替你决定" in rep["rule"]


def test_space_check_passes_a_comfortable_room():
    brief = K.SpaceBrief(space_name="客厅", width_mm=5200, depth_mm=7000,
                         ceiling_mm=3200)
    rep = W.style_space_check("italian-minimal", brief, catalogue=CAT)
    assert isinstance(rep["conflicts"], list)
    assert rep["notes"], "无论有无冲突都应给出对照说明"


def test_material_spec_is_procurement_shaped():
    rep = W.material_spec("italian-minimal", catalogue=CAT)
    assert rep["materials"]
    for row in rep["materials"]:
        assert row["material_zh"] and row["application"]
    assert rep["palette"] and all(c["hex"].startswith("#") for c in rep["palette"])
    assert rep["lighting"]
    assert rep["construction_focus"]


def test_material_substitution_is_recorded_not_silent():
    style = CAT.load_style("italian-minimal")
    original = style["materials"][0]["name_zh"]
    rep = W.material_spec("italian-minimal", catalogue=CAT,
                          substitutions={original: "国产同类岩板"})
    hit = [m for m in rep["materials"] if m["material_zh"] == original]
    assert hit and hit[0]["substituted_to"] == "国产同类岩板"
    assert hit[0]["substitution_reason"]


def test_intent_check_escalates_deviations_rather_than_judging_them():
    rep = W.design_intent_check("italian-minimal", ["门套缝宽由 3mm 改为 10mm"],
                                catalogue=CAT)
    assert rep["stage"] == "S7"
    assert rep["deviations"][0]["needs_owner_decision"] is True
    assert "持证专业人员复核" in rep["deviations"][0]["note"]
    assert rep["checklist"]


def test_comparison_data_covers_the_deciding_fields():
    rep = W.comparison_data(["modern-minimalism", "chinese-neo-classical",
                             "industrial-loft"], catalogue=CAT)
    assert rep["count"] == 3
    for s in rep["styles"]:
        assert s["spatial_principles"]
        assert s["materials"]
        assert s["palette"]
        assert s["budget_tier"]
        assert s["budget_drivers"]
        assert s["lighting"]["color_temperature_k"]
        assert s["incompatible"]
    assert "不写「两套都行」" in rep["note"]


def test_every_capability_used_by_a_hook_exists():
    """The hooks name real functions, not aspirations."""
    for h in W.all_hooks():
        for name in h["api"]:
            assert callable(getattr(W, name, None)), f"{h['stage']} 引用了不存在的 {name}"
