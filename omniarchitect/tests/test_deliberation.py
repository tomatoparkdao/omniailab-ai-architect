"""设计推敲层：必须真的在推敲，而不是换一套模板。

这一层最容易被写坏成"第二个原型库"——只要把固定句子换个说法，报告看起来
依然漂亮，但三套方案的组织逻辑其实一样。所以这里的断言集中在**互斥**与
**实事求是**两件事上：

* 同一专业的三套策略，parti 与空间家族必须不同；
* 景观项目不能拿到房间布局；室内项目不能重启建筑；
* 业主明确要水景时，不能给一个没有水面的院子；
* 判不了的前提不能算"已满足"，也不能算"不满足"。

只验证确定性逻辑，不联网。

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import tempfile
from pathlib import Path

from omniarchitect.concept import deliberation as dlb
from omniarchitect.concept import diagrams as dia
from omniarchitect.concept.context import build_context
from omniarchitect.concept.directions import generate_concepts, markdown
from omniarchitect.design import vocabulary as vocab
from omniarchitect.intake.interview import ensure_intake, record_answer
from omniarchitect.model import Project


# --------------------------------------------------------------------------
# 夹具
# --------------------------------------------------------------------------
def _project(tmp: Path, pid: str, name: str, cons: dict, answers: dict) -> Project:
    p = Project(project_id=pid, name=name)
    p.constraints = dict(cons)
    p.meta = {}
    ensure_intake(p)
    # 先算一次再补答案：复现"问诊初期就把范围定死"的真实顺序
    build_context(p, require_gate=False)
    for qid, value in answers.items():
        record_answer(p, qid, value)
    return p


def _villa(tmp: Path) -> Project:
    return _project(
        tmp, "t-villa", "三层现代极简别墅",
        {"project_type": "新建三层别墅", "style": "现代极简", "location": "苏州"},
        {"base.project_type": "新建三层别墅",
         "base.needs": "我有一块地，想建一栋三层现代极简别墅，室内也要精装修，"
                       "室外带庭院和水景。进入房子要有仪式感，室内通透、自然采光好，"
                       "同时要保证私密性。",
         "base.feeling": "外观高级简洁大气，进门有仪式感，室内通透自然，同时保证私密"})


def _flat(tmp: Path) -> Project:
    return _project(
        tmp, "t-flat", "既有大平层精装修",
        {"project_type": "大平层精装修", "style": "意式极简", "location": "上海"},
        {"base.project_type": "大平层精装修",
         "base.needs": "房子已经建好，是大平层，150 平米，想做意式极简的精装修。"
                       "要高级但不要冷，材料要看得出质感，客餐厅要通透，主卧要安静私密。"
                       "只做室内，建筑本体不动。",
         "base.feeling": "高级但不要冷，看得出质感，客餐厅通透，主卧安静私密"})


def _garden(tmp: Path) -> Project:
    return _project(
        tmp, "t-garden", "独立私家庭院",
        {"project_type": "私家庭院景观", "style": "现代自然", "location": "杭州"},
        {"base.project_type": "私家庭院景观",
         "base.needs": "有一个独立的私家院子，想做现代自然式的景观。要有水景、种植、"
                       "能坐下来喝茶的地方，家里有小孩，平时没太多时间打理，希望好维护。",
         "base.feeling": "现代自然、安静、好打理"})


# --------------------------------------------------------------------------
# 1. 主导专业决定拿哪一套策略
# --------------------------------------------------------------------------
def test_a_new_villa_is_architecture_led_even_if_asked_early():
    """主导专业不能在问诊第一轮被定死。

    早先 `leadership.ensure` 只要判过一次就不再重判，客户先说了"三层别墅"、
    后补"室外带庭院和水景"，主导专业仍是室内——于是拿住宅房间算法设计新房子。
    """
    with tempfile.TemporaryDirectory() as td:
        ctx = build_context(_villa(Path(td)), require_gate=False)
        assert ctx.lead_id == "architecture", ctx.lead_id
        assert "landscape" in (ctx.lead.get("design_disciplines") or [])


def test_a_fitout_is_interior_led_and_never_restarts_the_building():
    with tempfile.TemporaryDirectory() as td:
        p = _flat(Path(td))
        ctx = build_context(p, require_gate=False)
        assert ctx.lead_id == "interior", ctx.lead_id
        res = generate_concepts(ctx)
        for c in res["concepts"]:
            integration = (c["deliberation"] or {}).get("integration", "")
            assert "不重启建筑设计" in integration or "不动" in integration, integration
            assert "建筑" in integration


def test_a_private_garden_gets_landscape_strategies_not_rooms():
    with tempfile.TemporaryDirectory() as td:
        ctx = build_context(_garden(Path(td)), require_gate=False)
        assert ctx.lead_id == "landscape"
        res = generate_concepts(ctx)
        protos = [c["spatial_prototype"]["prototype_id"] for c in res["concepts"]]
        assert all(pid.startswith("DLB-LAN-") for pid in protos), protos
        for c in res["concepts"]:
            d = c["deliberation"]
            assert d["zones"], "景观方案必须有分区"
            assert d["water"] and d["planting"] and d["paving"], c["concept_id"]
        # 不能出现住宅房间词汇
        blob = " ".join(c["concept_statement"] + str(c["design_strategy"])
                        for c in res["concepts"])
        for word in ("主卧", "次卧", "玄关柜"):
            assert word not in blob, word


def test_architecture_concepts_carry_massing_section_and_levels():
    with tempfile.TemporaryDirectory() as td:
        ctx = build_context(_villa(Path(td)), require_gate=False)
        res = generate_concepts(ctx)
        assert res["source"] == "deliberated"
        for c in res["concepts"]:
            d = c["deliberation"]
            assert d["parti"] and d["massing"] and d["section"] and d["facade"]
            assert len(d["levels_program"]) >= 2, d["levels_program"]


# --------------------------------------------------------------------------
# 2. 三套必须真的不同
# --------------------------------------------------------------------------
def test_three_strategies_have_distinct_partis_and_families():
    for builder in (_villa, _flat, _garden):
        with tempfile.TemporaryDirectory() as td:
            ctx = build_context(builder(Path(td)), require_gate=False)
            res = generate_concepts(ctx)
            partis = [c["deliberation"]["parti"] for c in res["concepts"]]
            families = [c["spatial_prototype"]["family"] for c in res["concepts"]]
            ids = [c["spatial_prototype"]["prototype_id"] for c in res["concepts"]]
            assert len(set(partis)) == len(partis), partis
            assert len(set(families)) == len(families), families
            assert len(set(ids)) == len(ids), ids


def test_a_second_strategy_with_the_same_logic_is_skipped_not_renamed():
    """同族同逻辑的第二条策略必须被跳过，而不是改个名当第二套。"""
    with tempfile.TemporaryDirectory() as td:
        ctx = build_context(_villa(Path(td)), require_gate=False)
        pool = dlb.for_discipline("architecture")
        ranked_items = [dlb._score(s, ctx, {}) for s in pool]
        picked = dlb._pick(ranked_items, 3)
        logics = [(p["strategy"].logic_key or p["strategy"].id) for p in picked]
        assert len(set(logics)) == len(logics)


def test_swapping_materials_cannot_masquerade_as_a_new_scheme():
    """两套策略的 statement 与 parti 不能只差材料词。"""
    with tempfile.TemporaryDirectory() as td:
        ctx = build_context(_villa(Path(td)), require_gate=False)
        res = generate_concepts(ctx)
        statements = [c["concept_statement"] for c in res["concepts"]]
        assert len(set(statements)) == len(statements), statements


# --------------------------------------------------------------------------
# 3. 六问齐全，且不含空话
# --------------------------------------------------------------------------
def test_every_concept_answers_the_six_questions():
    with tempfile.TemporaryDirectory() as td:
        ctx = build_context(_villa(Path(td)), require_gate=False)
        res = generate_concepts(ctx)
        for c in res["concepts"]:
            d = c["deliberation"]
            for key, _label in dlb.SIX_QUESTIONS:
                assert d.get(key), (c["concept_id"], key)
            assert d["experience"], c["concept_id"]
            assert d["technical_coordination"], c["concept_id"]


def test_sequence_events_are_specific_not_adjectives():
    with tempfile.TemporaryDirectory() as td:
        ctx = build_context(_villa(Path(td)), require_gate=False)
        res = generate_concepts(ctx)
        for c in res["concepts"]:
            steps = c["experience_sequence"]["steps"]
            assert steps, c["concept_id"]
            for s in steps:
                assert s["device"] in vocab.VOCABULARY, (c["concept_id"], s)
                assert len(s["event"]) >= 8, s["event"]


def test_markdown_prints_the_six_questions_and_a_comparison_table():
    with tempfile.TemporaryDirectory() as td:
        ctx = build_context(_villa(Path(td)), require_gate=False)
        res = generate_concepts(ctx)
        md = markdown(res, ctx)
        assert "三套方案到底差在哪" in md
        assert "设计推敲" in md
        assert "最有价值的设计机会" in md
        assert "需要结构与机电配合" in md


# --------------------------------------------------------------------------
# 4. 实事求是：前提、水景、精度
# --------------------------------------------------------------------------
def test_unknown_prerequisites_are_neither_met_nor_failed():
    """判不了的前提既不能算满足，也不能算不满足。"""
    with tempfile.TemporaryDirectory() as td:
        ctx = build_context(_villa(Path(td)), require_gate=False)
        ranked = [dlb._score(s, ctx, {}) for s in dlb.ARCHITECTURE]
        for item in ranked:
            for req in item["unverified_requires"]:
                assert req not in item["met_requires"]
                assert req not in item["unmet_requires"]


def test_explicit_water_request_must_get_actual_water():
    with tempfile.TemporaryDirectory() as td:
        ctx = build_context(_garden(Path(td)), require_gate=False)
        res = generate_concepts(ctx)
        top = dlb.get(res["concepts"][0]["spatial_prototype"]["prototype_id"])
        assert top is not None and top.strong_water, top.id


def test_no_dimension_is_claimed_without_geometry():
    with tempfile.TemporaryDirectory() as td:
        ctx = build_context(_villa(Path(td)), require_gate=False)
        assert ctx.precision == "diagnostic"
        res = generate_concepts(ctx)
        for c in res["concepts"]:
            blob = " ".join(c["tradeoffs"])
            assert "未核实" in blob or "未核实" in " ".join(c["technical_risks"])


def test_precedent_only_counts_when_the_case_text_really_says_it():
    """案例佐证必须来自案例自己的文字，按词边界匹配。"""
    cases = [{"title": "A House", "summary": "a score of rooms"},
             {"title": "B House", "summary": "wrapped around a courtyard"}]
    got = dlb.precedent_signals({"cases": cases})
    assert "courtyard" in got
    assert "core" not in got, "`core` 不能命中 `score`"
    assert "light" not in got, "`light` 不能命中 `daylight`"


def test_case_evidence_never_outweighs_the_client():
    """案例加分必须低于业主原话加分：案例是佐证，不是需求。"""
    with tempfile.TemporaryDirectory() as td:
        ctx = build_context(_villa(Path(td)), require_gate=False)
        s = dlb.get("DLB-ARC-COURT")
        without = dlb._score(s, ctx, {})
        rich = {t: ["Some Case"] for t in s.precedent}
        with_cases = dlb._score(s, ctx, rich)
        assert with_cases["score"] > without["score"]
        assert with_cases["score"] - without["score"] <= 20


# --------------------------------------------------------------------------
# 5. 图解跟着主导专业走
# --------------------------------------------------------------------------
def test_diagram_kinds_follow_the_lead_discipline():
    with tempfile.TemporaryDirectory() as td:
        ctx = build_context(_villa(Path(td)), require_gate=False)
        res = generate_concepts(ctx)
        out = Path(td) / "dia"
        kinds = [m["kind"] for m in dia.build(res["concepts"][0], ctx, [], [], out)]
        assert "massing" in kinds and "section" in kinds, kinds

    with tempfile.TemporaryDirectory() as td:
        ctx = build_context(_garden(Path(td)), require_gate=False)
        res = generate_concepts(ctx)
        kinds = [m["kind"] for m in
                 dia.build(res["concepts"][0], ctx, [], [], Path(td) / "d2")]
        assert "landscape" in kinds, kinds
        assert "massing" not in kinds, kinds


def test_landscape_diagram_prints_the_real_shares():
    with tempfile.TemporaryDirectory() as td:
        ctx = build_context(_garden(Path(td)), require_gate=False)
        c = generate_concepts(ctx)["concepts"][0]
        svg = dia.landscape(c, ctx)
        for z in c["deliberation"]["zones"]:
            assert html_escape(z["share"]) in svg, z
        assert "非按比例" in svg


def html_escape(text: str) -> str:
    from xml.sax.saxutils import escape

    return escape(str(text))


__all__ = []
