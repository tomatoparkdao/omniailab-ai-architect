"""设计主导权：谁定美学、谁研究实现、什么不能突破。

八项对应本轮验收 A–H。这组测试守的是"设计事务所逻辑"，不是功能清单：

* 客户买的是什么设计，就由那个专业主导，不能一律从建筑设计开始；
* 主导专业有统筹权，但安全与规范不可突破；
* 技术与设计冲突时，先找保留原意图的技术路径，而不是先说"做不了"；
* 反过来，也不能拿"美学优先"去覆盖已经证实的安全问题。

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import tempfile
from pathlib import Path

from omniarchitect import changes, disciplines as D, intent as I, leadership as L
from omniarchitect.concept import compare
from omniarchitect.demo import build_demo_project
from omniarchitect.intake.gate import decide_gate as decide_g1
from omniarchitect.intake.interview import answer_question, start_interview
from omniarchitect.model import Project


def _project(tmp: Path, one_liner: str, name: str = "") -> Project:
    p = build_demo_project(tmp / "proj")
    p.project_id = "lead-test"
    p.name = name or one_liner[:12]
    p.save(tmp / "proj" / "project.json")
    start_interview(p, one_liner)
    return p


def _lead_of(one_liner: str) -> L.Leadership:
    with tempfile.TemporaryDirectory() as td:
        p = _project(Path(td), one_liner)
        return L.detect(p, D.ensure(p))


# --------------------------------------------------------------------------
# A. 新建三层别墅 → 建筑主导，结构与机电只做概念级配合
# --------------------------------------------------------------------------
def test_a_villa_is_led_by_architecture():
    lead = _lead_of("有块地，建三层别墅，带庭院水池，室内精装，结构机电一并考虑")
    assert lead.mode in ("A", "D"), lead.mode
    assert lead.lead == "architecture", lead.lead
    assert "structure" in lead.support_disciplines
    assert "mep" in lead.support_disciplines
    # 结构/机电不是设计主导
    assert not lead.is_design("structure") and not lead.is_design("mep")
    # 讨论顺序从体量与形态开始，不是从设备与荷载开始
    assert "体量" in lead.design_priority[0] or "形态" in lead.design_priority[0]


# --------------------------------------------------------------------------
# B. 已建成大平层精装修 → 室内主导，不重启完整建筑设计
# --------------------------------------------------------------------------
def test_b_finished_flat_is_led_by_interior_without_restarting_architecture():
    lead = _lead_of("我买了一套 150㎡ 大平层，想重新做室内装修，现代意式极简")
    assert lead.mode == "B", lead.mode
    assert lead.lead == "interior", lead.lead
    assert lead.existing_building is True, "已建成项目必须标记为既有建筑约束"
    assert "architecture" not in lead.design_disciplines or lead.lead == "interior"
    # 室内主导时，界面与光优先于设备
    assert any("空间" in x or "顶墙地" in x for x in lead.design_priority[:2])


# --------------------------------------------------------------------------
# C. 独立庭院 → 景观主导，不启动住宅平面生成器
# --------------------------------------------------------------------------
def test_c_garden_is_led_by_landscape_and_never_uses_the_room_planner():
    lead = _lead_of("只想重新做我家的院子景观，铺装加种植，室内不动")
    assert lead.mode == "C", lead.mode
    assert lead.lead == "landscape", lead.lead

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        p = _project(tmp, "只想重新做我家的院子景观，铺装加种植，室内不动")
        answer_question(p, "base.needs", "想能坐下喝茶，好打理")
        decide_g1(p, "approved", by="业主")
        from omniarchitect.workflow import StageRunner

        out = StageRunner(p, tmp / "out", project_dir=tmp / "proj",
                          assume_approval=False).run_stage("S3", confirm=False)
        assert out.status == "blocked", out.status
        assert "不能拿房间组合算法冒充" in (out.error or "")


# --------------------------------------------------------------------------
# D. 大跨度空间 → 结构先给技术路径，不是"加柱子"
# --------------------------------------------------------------------------
def _intent_with(kind: str, statement: str) -> dict:
    return {
        "design_intent_id": "DI-TEST",
        "lead_discipline": "architecture",
        "lead_label": "建筑",
        "signature_features": [{
            "id": "SF-01", "kind": kind, "name": "核心空间特征",
            "statement": statement, "source_field": "spatial_logic",
            "technical_dependencies": list(I.DEPENDENCIES.get(kind, ())),
        }],
        "acceptable_adjustments": [],
        "technical_dependencies": [],
    }


def test_d_long_span_gets_technical_paths_not_a_column():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        p = _project(tmp, "自建别墅，客厅要大跨度无柱，通高六米")
        p.meta["design_intent"] = _intent_with(
            "spatial", "客厅做大跨度无柱空间，通高六米，视线不被遮挡")
        res = I.resolve(p, "客厅跨度太大，需要加柱子")
        assert res["verdict"] == "needs_technical_path", res["verdict"]
        opts = res["levels"][1]["options"]
        paths = [o["path"] for o in opts]
        assert paths, "没有给出任何技术路径"
        # 必须是"研究怎么实现"，不能上来就加柱或取消
        assert any(("钢结构" in x or "柱网" in x or "预应力" in x or "转换" in x)
                   for x in paths), paths
        assert not any(x.startswith("直接加柱") or "取消" in x for x in paths)
        assert res["requires_formal"] is True


def test_d2_unverified_structure_still_blocks_the_construction_drawings():
    """技术路径可以给，但没核实结构就不能当"已解决"。"""
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        p = _project(tmp, "自建别墅，客厅要大跨度无柱")
        p.meta["design_intent"] = _intent_with(
            "spatial", "客厅做大跨度无柱空间，通高六米")
        res = I.resolve(p, "客厅跨度太大")
        # 路径里明确要求专业计算与复核
        joined = " ".join(str(x) for x in res["levels"][2].get("compare_on") or [])
        assert "专业计算" in joined or "复核" in joined, res["levels"][2]
        assert res["levels"][2]["rule"].find("如实披露") >= 0


# --------------------------------------------------------------------------
# E. 无主灯天花 vs 风管 → 先优化设备与管线路由
# --------------------------------------------------------------------------
def test_e_duct_conflict_prefers_hiding_the_equipment():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        p = _project(tmp, "大平层室内装修，天花要无主灯极简")
        p.meta["design_intent"] = _intent_with(
            "surface", "天花做无主灯极简造型，不做局部吊顶，保持完整平顶")
        res = I.resolve(p, "天花上要放风管和检修口")
        assert res["verdict"] == "needs_technical_path"
        paths = [o["path"] for o in res["levels"][1]["options"]]
        assert any("隐蔽风口" in x or "线性风口" in x for x in paths), paths
        assert any("检修口整合" in x or "移位" in x or "绕行" in x for x in paths), paths
        # 不允许第一条建议就是"降低吊顶"
        assert "降低吊顶" not in paths[0]


# --------------------------------------------------------------------------
# F. 屋顶花园 → 景观提意图，结构/排水/防水给约束；荷载未核实不能说可施工
# --------------------------------------------------------------------------
def test_f_roof_garden_cannot_be_called_constructible_without_load_check():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        p = _project(tmp, "屋顶要做花园，种树做水景")
        rep = changes.analyse(p, "屋顶改成花园，种乔木做水景", apply=False)
        x = next(x for x in rep.cross_discipline if x["id"] == "XD-ROOF-GARDEN")
        assert {"structure", "landscape", "architecture", "mep"} <= set(x["disciplines"])
        st = next(a for a in x["affects"] if a["discipline"] == "structure")
        assert "荷载" in st["needs"], st
        assert st["blocks_stage"] == "S3", st
        # 报告必须提示荷载未核实
        assert any("荷载" in r for r in rep.risks), rep.risks


# --------------------------------------------------------------------------
# G. 技术方案成本过高 → 给保留方案 + 代价 + 备选，不直接取消设计
# --------------------------------------------------------------------------
def test_g_expensive_but_feasible_keeps_the_option_and_shows_the_cost():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        p = _project(tmp, "自建别墅，要一个悬挑六米的通透立面")
        p.meta["design_intent"] = _intent_with(
            "envelope", "建筑立面做六米悬挑，全玻璃通透，轮廓完整不被切断")
        res = I.resolve(p, "悬挑太长，结构说做不了")
        paths = [o["path"] for o in res["levels"][1]["options"]]
        assert any("悬挑" in x for x in paths), paths
        assert not any("取消" in x for x in paths), "把取消设计当成技术方案了"
        compare_on = res["levels"][2]["compare_on"]
        assert "造价影响" in compare_on and "工期影响" in compare_on, compare_on
        assert "技术复杂但可行 ≠ 劣质设计" in res["levels"][2]["rule"]


# --------------------------------------------------------------------------
# H. 安全问题不可突破：美学分不能救
# --------------------------------------------------------------------------
def test_h_safety_failure_cannot_be_offset_by_aesthetic_score():
    class _Ctx:
        lead_weights = {"aesthetic": 1.3}
        conflicts = [{"id": "F-CAP-01", "category": "capacity", "severity": "blocker",
                      "problem": "60 人放进 132㎡ 明显装不下（人均 2.2㎡）"}]
        style_preference = ""
        budget_tier = "mid"
        precision = "schematic"
        uncertainty = []

    concept = {
        "concept_id": "C-X",
        "spatial_prototype": {"family": "layered", "family_zh": "分层",
                              "zoning": "一条线分成两半，界线是一条墙加一扇门",
                              "circulation": "一条横向走廊串起两侧，末端收在阳台"},
        "aesthetic_policy": {}, "palette": {"checks": []},
        "technical_risks": [], "cost_impact": "", "maintenance_impact": "",
        "s1_opportunity_refs": [],
    }
    ev = compare.evaluate(concept, _Ctx(), 0)
    assert ev["hard_gate"]["failed"] is True, ev["hard_gate"]
    assert ev["rankable"] is False
    # 即使美学分很高，也不能排到可行方案前面
    assert "美学高分抵消" in ev["hard_gate"]["rule"]
