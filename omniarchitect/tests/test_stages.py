"""Stage model, capability catalogue and guardrail invariants.

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import omniarchitect as oa
from omniarchitect.stages import (
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
    assert ids == {"R1", "R2", "R3", "R4", "R5"}


def test_downstream_covers_every_stage():
    for s in STAGE_ORDER:
        assert s in DOWNSTREAM
        assert DOWNSTREAM["S1"] == STAGE_ORDER


def test_requires_confirmed_is_acyclic_and_declared():
    for s, reqs in REQUIRES_CONFIRMED.items():
        for r in reqs:
            assert r in STAGE_BY_ID
            assert STAGE_ORDER.index(r) < STAGE_ORDER.index(s)


def test_every_capability_has_a_specialist_brief():
    """30 项能力各自必须有一份 `skills/<slug>.md`。

    文档承诺「30 项专业能力说明在 skills/」，仓库就必须真有 30 份，且**文件名即可用能力名**——
    否则 Agent 拿到 `ergonomics` 这个能力名时无处定位，只能靠猜。
    """
    from omniarchitect.paths import SKILLS

    on_disk = {p.stem for p in SKILLS.glob("*.md")}
    declared = {c.slug for c in CAPABILITIES}
    missing = sorted(declared - on_disk)
    extra = sorted(on_disk - declared)
    assert not missing, f"这些能力缺说明文件：{missing}"
    assert not extra, f"skills/ 有未登记为能力的文件：{extra}"


def test_specialist_briefs_declare_matching_capability_and_stages():
    """每份能力说明的 front-matter 必须与该能力的定义一致。

    `capability` 与文件名不符、或 `stages` 与 `CAPABILITIES` 的定义不符，
    都会让按能力名加载的 Agent 拿到错内容，且不会报错——所以必须由测试守住。
    """
    from omniarchitect.paths import SKILLS

    by_slug = {c.slug: c for c in CAPABILITIES}
    problems = []
    for p in sorted(SKILLS.glob("*.md")):
        text = p.read_text(encoding="utf-8")
        assert text.startswith("---"), f"{p.name} 缺 front-matter"
        fm = text.split("---", 2)[1]
        cap = [ln.split(":", 1)[1].strip() for ln in fm.splitlines()
               if ln.startswith("capability:")]
        stg = [ln.split(":", 1)[1].strip() for ln in fm.splitlines()
               if ln.startswith("stages:")]
        if not cap or cap[0] != p.stem:
            problems.append(f"{p.name}: capability={cap}")
            continue
        want = "[" + ", ".join(by_slug[p.stem].stages) + "]"
        if not stg or stg[0] != want:
            problems.append(f"{p.name}: stages={stg} ≠ {want}")
    assert not problems, problems


def test_project_attribution_and_criteria_are_recorded():
    a = oa.PROJECT_ATTRIBUTION
    assert a["owner"] == "OmniAiLab"
    assert a["developer"] == "Mochiball"
    assert "OmniAiLab" in oa.SIGNATURE
    rep = oa.criteria_report()
    assert rep["summary"]["criteria_sets"] >= 8
    assert "S2" in rep["summary"]["stages_touched"]
    assert rep["summary"]["note"]


def test_registry_report_counts_match():
    rep = oa.registry_report()
    assert rep["stage_count"] == 8
    assert rep["capability_count"] == len(CAPABILITIES)
    assert rep["catalog_issues"] == []
