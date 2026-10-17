"""Tests for the S1 intelligent intake engine.

Coverage maps to the acceptance scenarios in the upgrade brief:

A  one-sentence brief        -> interview opens, nothing invented
B  complete material         -> no repeated questions, bundle produced
C  conflicting requirements  -> conflict found instead of accepted
D  drawing uncertainty       -> marked inferred / unknown, never authoritative
E  design opportunities      -> every item has evidence and a next step
F  G1 approval and change    -> three decisions, baseline, change detection
G  project types             -> different profiles ask different questions
H  regression                -> the rest of the suite (run_tests.py) stays green

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from omniarchitect.demo import build_demo_project
from omniarchitect.intake import (
    PROFILES,
    QUESTION_INDEX,
    S1_BUNDLE_FILES,
    answer_question,
    assess_sources,
    build_need_matrix,
    check_baseline,
    completeness,
    decide_gate,
    find_opportunities,
    generate_bundle,
    load_interview,
    next_questions,
    precision_level,
    profile_for,
    register_uncertainty,
    run_feasibility,
    start_interview,
)
from omniarchitect.intake.diligence import UncertaintyItem
from omniarchitect.intake.interview import detect_start_mode
from omniarchitect.model import Project
from omniarchitect.stage_state import CONFIRMED, get_state

ONE_LINER = "我有一套 150㎡ 的大平层在杭州市，一家三口，希望做现代意式极简"


def _bare(tmp: Path) -> Project:
    """A project that knows nothing — the one-sentence case."""
    p = Project(project_id="T-ONE", name="150㎡ 大平层",
                constraints={"style": "现代意式极简"})
    p.save(tmp / "project.json")
    return p


# --------------------------------------------------------------------------
# A. one sentence
# --------------------------------------------------------------------------
def test_a_one_sentence_opens_an_interview_without_inventing_facts():
    """A 只给一句话：能开访谈，但不虚构功能、预算与现场资料。"""
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        p = _bare(tmp)
        start_interview(p, ONE_LINER)

        assert load_interview(p).profile_id == "residential"
        assert not p.program, "不得凭空生成功能任务书"
        assert not (p.constraints or {}).get("budget_cny"), "不得虚构预算"
        assert not [s for s in (p.constraints or {}) if s.startswith("floor_area")]

        qs = next_questions(p)
        assert 1 <= len(qs) <= 3, f"每轮 1–3 个，实际 {len(qs)}"
        assert all(q.priority for q in qs)
        # 缺失的关键信息要以问题的形式出现，而不是被猜出来填上
        assert any(q.slot in ("budget", "needs") for q in qs)


def test_a_stated_facts_are_not_asked_again():
    """首句已经给了面积、城市、人数、风格，就不要再问一遍。"""
    with tempfile.TemporaryDirectory() as d:
        p = _bare(Path(d))
        start_interview(p, ONE_LINER)
        qs = next_questions(p, limit=99)
        asked_slots = {q.slot for q in qs}
        assert "floor_area" not in asked_slots, "面积已在首句说明"
        assert "location" not in asked_slots, "城市已在首句说明"
        assert "occupants" not in asked_slots, "人数已在首句说明"

        answered = load_interview(p).answers
        assert "base.floor_area" in answered
        assert "150" in answered["base.floor_area"]["value"]
        assert answered["base.floor_area"]["source"] == "text"


def test_a_start_mode_is_classified():
    with tempfile.TemporaryDirectory() as d:
        p = _bare(Path(d))
        assert detect_start_mode(p, ONE_LINER) == "words_only"
        demo = build_demo_project(Path(d) / "demo")
        assert detect_start_mode(demo, "") in ("with_assets", "complete")


# --------------------------------------------------------------------------
# B. complete material
# --------------------------------------------------------------------------
def test_b_bundle_is_written_and_registered():
    """B 资料完整：一次性产出 S1 成果包，且每份都登记为产物。"""
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        p = build_demo_project(tmp / "proj")
        start_interview(p, "150㎡ 大平层，现代意式极简，一家三口")
        answer_question(p, "base.budget", "硬装 80 万，不含家具家电")

        out = tmp / "S1"
        result = generate_bundle(p, out)
        assert result["count"] == len(S1_BUNDLE_FILES)
        for name in S1_BUNDLE_FILES:
            assert (out / name).exists(), name

        # 每份都绑定项目与修订，并登记为 artifact
        brief = (out / "design-brief.md").read_text(encoding="utf-8")
        assert p.project_id in brief and f"r{p.revision}" in brief
        for name in S1_BUNDLE_FILES:
            aid = f"art-s1-{name.replace('.', '-')}"
            assert p.artifact(aid).revision == p.revision

        needs = json.loads((out / "user-needs.json").read_text(encoding="utf-8"))
        assert needs["project_id"] == p.project_id
        assert needs["rows"], "功能需求矩阵不能是空的"


def test_b_complete_material_does_not_re_ask_known_slots():
    with tempfile.TemporaryDirectory() as d:
        p = build_demo_project(Path(d) / "proj")
        start_interview(p, "150㎡ 大平层")
        qs = next_questions(p, limit=99)
        slots = {q.slot for q in qs}
        # demo 已有 program 与几何 → 需求与面积不该再问
        assert "needs" not in slots
        assert "floor_area" not in slots
        assert "drawings" not in slots


# --------------------------------------------------------------------------
# C. conflicting requirements
# --------------------------------------------------------------------------
def test_c_area_overflow_is_a_blocker_not_a_promise():
    """C 需求面积超过可用面积：必须报冲突，不能全部接受。"""
    with tempfile.TemporaryDirectory() as d:
        p = build_demo_project(Path(d) / "proj")
        # 把需求撑到明显超出
        p.program = [{"name": f"房间{i}", "recipe": "bedroom", "area_m2": 40}
                     for i in range(10)]
        feas = run_feasibility(p)
        area = [c for c in feas["conflicts"] if c["category"] == "area"]
        assert area, "面积冲突必须被发现"
        blocker = [c for c in area if c["severity"] == "blocker"]
        assert blocker, f"需求远超可用面积时应为阻断：{area}"
        assert blocker[0]["alternatives"], "冲突必须给出可替代方案"
        assert blocker[0]["needs_human"] is True
        assert feas["verdict"] == "not_feasible_yet"


def test_c_multi_person_dinner_is_flagged():
    with tempfile.TemporaryDirectory() as d:
        p = _bare(Path(d))
        start_interview(p, ONE_LINER)
        answer_question(p, "base.needs", "客厅要能坐下 8 个人吃饭")
        feas = run_feasibility(p)
        beh = [c for c in feas["conflicts"] if c["category"] == "behavior"]
        assert beh, "8 人聚餐与日常起居的冲突应被识别"
        assert any("聚餐" in c["problem"] for c in beh)


# --------------------------------------------------------------------------
# D. uncertainty
# --------------------------------------------------------------------------
def test_d_unknown_structure_blocks_structure_work_not_the_whole_project():
    """D 结构未知：阻断结构与出图，但 S1/S2 仍可推进。"""
    with tempfile.TemporaryDirectory() as d:
        p = _bare(Path(d))
        start_interview(p, ONE_LINER)
        answer_question(p, "base.structure", "不清楚，物业没说")

        items = (p.meta["intake"].get("uncertainty") or [])
        assert items, "回答「不清楚」必须进入不确定登记"
        structural = [i for i in items if i["topic"] == "structural"][0]
        assert structural["state"] == "unknown"
        assert "S4" in structural["blocks_stages"]
        assert structural["needs_human"] is True

        # 不阻断概念阶段
        assert "S2" not in structural["blocks_stages"]
        feas = run_feasibility(p)
        assert feas["verdict"] in ("not_feasible_yet", "feasible_with_conditions")


def test_d_photo_only_is_inferred_not_documented():
    with tempfile.TemporaryDirectory() as d:
        p = _bare(Path(d))
        start_interview(p, ONE_LINER)
        answer_question(p, "base.drawings", "只有拍照/扫描件")
        items = p.meta["intake"]["uncertainty"]
        dim = [i for i in items if i["topic"] == "dimension"][0]
        assert dim["state"] == "inferred", dim
        assert "S3" in dim["blocks_stages"], "尺寸未证实，平面阶段即受限"
        assert precision_level(p) == "diagnostic"


def test_d_verified_source_raises_precision():
    """精度升级要有真凭据：文件名本身不算实测。"""
    from omniarchitect.intake.diligence import SourceEntry, register_source

    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        p = build_demo_project(tmp / "proj")
        assert precision_level(p) == "schematic"      # 有几何，无实测

        # 只写一个文件名：降级为 documented，精度不动
        register_source(p, SourceEntry(id="S-NAME", kind="measure",
                                       file="现场实测记录.pdf",
                                       confidence="verified"))
        assert precision_level(p) == "schematic"
        entry = [s for s in p.meta["intake"]["sources"] if s["id"] == "S-NAME"][0]
        assert entry["confidence"] == "documented"
        assert "未达 verified" in entry["note"]

        # 有核验人 + 可查文件 + 版本：才升到 authoritative_capable
        f = tmp / "实测记录.pdf"
        f.write_text("measure", encoding="utf-8")
        register_source(p, SourceEntry(id="S-REAL", kind="measure",
                                       file=str(f), revision="2026-10-01",
                                       verified_by="现场负责人 李工",
                                       confidence="verified"))
        assert precision_level(p) == "authoritative_capable"


def test_d_contradiction_blocks_harder_than_a_blank():
    with tempfile.TemporaryDirectory() as d:
        p = _bare(Path(d))
        register_uncertainty(p, UncertaintyItem(
            id="U-X", topic="dimension", statement="图纸标注 150㎡，实测 132㎡",
            state="conflicting", affects="S3"))
        items = p.meta["intake"]["uncertainty"]
        assert "S2" in items[0]["blocks_stages"], "来源冲突应阻断概念阶段，先澄清"


# --------------------------------------------------------------------------
# E. opportunities
# --------------------------------------------------------------------------
def test_e_opportunities_carry_evidence_and_next_step():
    """E 设计机会：每条都要有证据与下一阶段建议，不为凑数补条目。"""
    with tempfile.TemporaryDirectory() as d:
        p = _bare(Path(d))
        start_interview(p, ONE_LINER)
        answer_question(p, "base.needs",
                        "客厅要能坐下 8 个人吃饭；孩子写作业要看得见；东西很多需要收纳")
        answer_question(p, "res.daily_rhythm", "晚上陪孩子写作业，周末在家做饭")

        result = find_opportunities(p)
        assert 1 <= result["count"] <= 5
        for o in result["items"]:
            for f in ("opportunity_id", "problem", "evidence", "design_goal",
                      "expected_value", "constraints", "priority", "confidence",
                      "next_stage_recommendation"):
                assert o.get(f), f"{o['opportunity_id']} 缺字段 {f}"
            assert o["next_stage_recommendation"].startswith("S")


def test_e_no_padding_when_evidence_is_thin():
    with tempfile.TemporaryDirectory() as d:
        p = Project(project_id="T-EMPTY")
        result = find_opportunities(p)
        assert result["count"] <= 2, "资料不足时不得凑到 3 项"
        assert result["note"]


# --------------------------------------------------------------------------
# F. G1
# --------------------------------------------------------------------------
def test_f_approval_creates_a_baseline():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        p = _bare(tmp)
        start_interview(p, ONE_LINER)
        answer_question(p, "base.budget", "硬装 80 万")
        answer_question(p, "base.needs", "客厅要能坐下 6 个人吃饭")

        outcome = decide_gate(p, "approved", by="业主", force=True)
        assert outcome.decision == "approved"
        assert get_state(p, "S1").status == CONFIRMED
        base = p.meta["intake"]["baseline"]
        assert base["revision"] == p.revision
        assert base["digest"]
        assert check_baseline(p)["changed"] is False


def test_f_blocker_downgrades_approval_unless_forced():
    with tempfile.TemporaryDirectory() as d:
        p = build_demo_project(Path(d) / "proj")
        p.program = [{"name": f"房间{i}", "recipe": "bedroom", "area_m2": 40}
                     for i in range(10)]
        outcome = decide_gate(p, "approved")
        assert outcome.decision == "blocked", "有阻断项时不能直接通过"
        assert outcome.notes

        forced = decide_gate(p, "approved", force=True)
        assert forced.decision == "approved" and forced.forced is True


def test_f_revision_requested_keeps_the_baseline():
    with tempfile.TemporaryDirectory() as d:
        p = _bare(Path(d))
        start_interview(p, ONE_LINER)
        answer_question(p, "base.budget", "硬装 80 万")
        decide_gate(p, "approved", force=True)
        before = dict(p.meta["intake"]["baseline"])

        decide_gate(p, "revision_requested", note="预算需要再压")
        assert get_state(p, "S1").status == "rework"
        assert p.meta["intake"]["baseline"] == before, "退回修改不应抹掉已确认基准"


def test_f_editing_after_approval_requires_change_analysis():
    with tempfile.TemporaryDirectory() as d:
        p = _bare(Path(d))
        start_interview(p, ONE_LINER)
        answer_question(p, "base.budget", "硬装 80 万")
        decide_gate(p, "approved", force=True)

        result = answer_question(p, "base.budget", "硬装 60 万")
        assert result["changed"] is True
        assert result["requires_change_analysis"] is True
        assert check_baseline(p)["changed"] is True
        assert check_baseline(p)["requires_change_analysis"] is True


# --------------------------------------------------------------------------
# G. project types
# --------------------------------------------------------------------------
def test_g_profiles_ask_different_questions():
    """G 不同类型的问诊必须不同，不能一套问卷打天下。"""
    cases = {
        "residential": "150㎡ 大平层，一家三口自住",
        "office": "800㎡ 办公空间，60 人",
        "hospitality": "30 间客房的民宿",
        "retail": "一家咖啡店，客单 45 元",
        "exhibition": "企业展厅 500㎡",
        "architecture": "农村自建三层",
    }
    seen = {}
    for pid, text in cases.items():
        prof = profile_for(text)
        assert prof.id == pid, f"{text} -> {prof.id}，应为 {pid}"
        seen[pid] = {q.id for q in prof.questions}

    assert "res.household" in seen["residential"]
    assert "off.headcount" in seen["office"]
    assert "hos.keys" in seen["hospitality"]
    assert "ret.turnover" in seen["retail"]
    assert "exh.story" in seen["exhibition"]
    assert "arc.plot" in seen["architecture"]
    # 不同类型之间必须真的有差异
    assert not seen["office"] <= seen["residential"]


def test_g_same_project_switches_question_language():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        p1 = Project(project_id="G1")
        start_interview(p1, "800㎡ 办公空间，60 人")
        office_q = {q.id for q in next_questions(p1, limit=99)}

        p2 = Project(project_id="G2")
        start_interview(p2, "150㎡ 住宅，一家三口")
        home_q = {q.id for q in next_questions(p2, limit=99)}
        assert office_q != home_q


# --------------------------------------------------------------------------
# entry criteria were relaxed
# --------------------------------------------------------------------------
def test_s1_can_start_from_an_idea_alone():
    """S1 进入条件不得再要求「资料已收集」。"""
    from omniarchitect.stages import STAGE_BY_ID

    entry = STAGE_BY_ID["S1"].entry_criteria
    joined = " ".join(entry)
    assert "已收集" not in joined
    assert any("即可启动" in e for e in entry)
    assert any("精度" in e for e in entry), "必须写明资料完整度决定精度"


def test_precision_gate_only_applies_after_intake_recorded_it():
    from omniarchitect.stage_state import can_start

    with tempfile.TemporaryDirectory() as d:
        p = _bare(Path(d))
        start_interview(p, ONE_LINER)
        from omniarchitect.intake.diligence import store_precision
        store_precision(p)
        assert p.meta["intake"]["precision"] == "diagnostic"
        ok, reason = can_start(p, "S4")
        assert not ok and "诊断级" in reason

        # 没有 intake 记录的项目（脚本直接建模）不受影响
        demo = build_demo_project(Path(d) / "demo")
        assert "intake" not in (demo.meta or {}) or "precision" not in demo.meta["intake"]
