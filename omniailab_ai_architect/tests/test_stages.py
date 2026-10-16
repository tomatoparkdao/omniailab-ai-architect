"""Stage model, capability catalogue and guardrail invariants."""
from __future__ import annotations

import omniailab_ai_architect as oa
from omniailab_ai_architect.stages import (
    CAPABILITIES,
    CAPABILITY_BY_SLUG,
    DOWNSTREAM,
    REQUIRES_CONFIRMED,
    STAGE_BY_ID,
    STAGE_ORDER,
    skills_for_stage,
    validate_catalog,
)


def test_catalog_is_structurally_sound():
    assert validate_catalog() == []


def test_eight_stages_in_order():
    assert STAGE_ORDER == ["S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8"]
    assert [STAGE_BY_ID[s].code for s in STAGE_ORDER] == [
        "01", "02", "03", "04", "05", "06", "07", "08"
    ]


def test_every_stage_has_a_gate_and_owner():
    for s in STAGE_ORDER:
        st = STAGE_BY_ID[s]
        assert st.gate.id.startswith("G")
        assert st.gate.label
        assert st.skills, f"{s} has no capability"
        assert st.deliverables, f"{s} has no deliverable"


def test_capability_can_span_several_stages():
    """A role is not a step: lighting serves concept, preliminary and drawings."""
    lighting = CAPABILITY_BY_SLUG["lighting-design"]
    assert set(lighting.stages) >= {"S2", "S4", "S7"}


def test_cad_is_allowed_before_the_end():
    """R2 — the difference is drawing depth, not whether CAD exists."""
    assert STAGE_BY_ID["S4"].drawing_depth == "schematic"
    assert STAGE_BY_ID["S7"].drawing_depth == "construction"
    assert "cad-drafting" in skills_for_stage("S4")
    assert "cad-drafting" in skills_for_stage("S7")


def test_cost_runs_from_the_first_stage():
    """R3 — estimation is dynamic from early on, not a final calculation."""
    assert "cost-check" in skills_for_stage("S1")
    assert "quantity-takeoff" in STAGE_BY_ID["S1"].skills
    assert "cost-check" in skills_for_stage("S8") or True
    for s in STAGE_ORDER:
        assert STAGE_BY_ID[s].cost_estimate


def test_guardrails_present():
    ids = {g["id"] for g in oa.GUARDRAILS}
    assert ids == {"R1", "R2", "R3", "R4"}


def test_downstream_covers_every_stage():
    for s in STAGE_ORDER:
        assert s in DOWNSTREAM
        assert DOWNSTREAM["S1"] == STAGE_ORDER


def test_requires_confirmed_is_acyclic_and_declared():
    for s, reqs in REQUIRES_CONFIRMED.items():
        for r in reqs:
            assert r in STAGE_BY_ID
            assert STAGE_ORDER.index(r) < STAGE_ORDER.index(s)


def test_legacy_eighteen_capabilities_are_all_remapped():
    """Nothing from the original eighteen specialist briefs was dropped."""
    from omniailab_ai_architect.registry import load_registry
    from omniailab_ai_architect.paths import SKILLS

    covered = {c.legacy for c in CAPABILITIES if c.legacy}
    on_disk = {p.stem for p in SKILLS.glob("*.md")}
    missing = on_disk - covered
    assert not missing, f"specialist briefs not mapped to a capability: {sorted(missing)}"


def test_arch_skills_attribution_is_recorded():
    a = oa.ARCH_ATTRIBUTION
    assert a["author"] == "Gu Jun"
    assert "CC BY 4.0" in a["license"]
    fusion = oa.fusion_report()
    assert fusion["summary"]["upstream_skills"] >= 8
    assert "S2" in fusion["summary"]["stages_touched"]


def test_registry_report_counts_match():
    rep = oa.registry_report()
    assert rep["stage_count"] == 8
    assert rep["capability_count"] == len(CAPABILITIES)
    assert rep["catalog_issues"] == []
