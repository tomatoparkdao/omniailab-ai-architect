"""行业设计层（sector）的守卫测试。

守住四件事，它们是把分类"变成设计"的关键，一旦回退，本轮工作就白做：

1. 主体 vs 配套：学校里的食堂不该变成一份餐饮工装委托；
2. 数据驱动：方向里的数字必须来自客户原话，缺输入要如实说缺；
3. 排布复用：行业程序走同一套 `zone_bands`，面积回到任务书；
4. G3 专业核验：只有任务清单、没有设计数据，不能算专业方案。

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from omniarchitect import taxonomy as tx
from omniarchitect.model import Project
from omniarchitect.sector import brief as sb
from omniarchitect.sector import check as sck
from omniarchitect.sector import layout as lay
from omniarchitect.sector import moves as mv
from omniarchitect.sector import program as sp


def _ctx(text: str, codes=(), ancillary=(), lead: str = "architecture") -> SimpleNamespace:
    return SimpleNamespace(
        name=text, lead_id=lead, profile_id="architecture",
        taxonomy={"codes": list(codes), "ancillary": [{"label": a} for a in ancillary]},
        taxonomy_codes=tuple(codes), answers={}, program=[],
        area_available_m2=None, target_area_m2=0.0, location="",
    )


# --------------------------------------------------------------------------
# 1. 识别：主体、配套、同项目室内、独立委托
# --------------------------------------------------------------------------
def test_school_canteen_and_gym_are_facilities_not_commissions() -> None:
    c = tx.classify("新建中小学 24 班，含食堂和体育馆")
    assert c.codes == ["A3"], c.codes
    labels = [a["label"] for a in c.ancillary]
    assert "学生食堂" in labels and "校园体育馆" in labels
    assert c.commissions == ["architecture"], c.commissions


def test_hotel_restaurant_spa_are_parts_of_the_hotel() -> None:
    c = tx.classify("新建酒店，含餐厅、SPA 与会议中心")
    assert c.codes == ["A6"], c.codes
    # 会议室/餐厅属于酒店的配套，不该把 A2 办公抬成主体
    assert c.commissions == ["architecture"], c.commissions


def test_explicit_separate_building_keeps_the_second_use() -> None:
    c = tx.classify("新建学校，另建独立体育馆")
    assert "A8" in c.codes and "A3" in c.codes, c.codes
    assert c.primary == "A3", "加上一栋体育馆，主体仍是学校"


def test_new_hospital_interior_is_a_sibling_not_a_second_use() -> None:
    c = tx.classify("新建综合医院 300 床，含门诊与医技")
    assert c.codes == ["A4"], c.codes
    assert [x["code"] for x in c.sibling] == ["B8"], c.sibling
    # 没说做室内，就不该把室内算进委托
    assert c.commissions == ["architecture"], c.commissions


def test_fitout_commission_blocks_new_build_architecture() -> None:
    c = tx.classify("既有酒店室内精装修，120 间客房")
    assert "architecture" not in c.commissions, c.commissions


# --------------------------------------------------------------------------
# 2. 推敲：数字有出处，缺数据要说话
# --------------------------------------------------------------------------
def test_education_quantities_come_from_the_brief() -> None:
    b = sb.build(_ctx("新建 24 班小学，用地 20000 平方米", codes=["A3"]))
    assert b.get("classes") == 24
    assert b.get("students") == 1080, "45 人/班 是默认值，要写进 assumptions"
    assert any("每班人数" in a for a in b.assumptions)
    # 教学面积必须是算出来的，不是写的
    assert abs(b.get("teaching_m2") - 24 * 65) < 1


def test_moves_carry_numbers_and_name_what_they_answer() -> None:
    b = sb.build(_ctx("新建 24 班小学，用地 20000 平方米", codes=["A3"]))
    moves = mv.moves(b)
    assert len(moves) >= 2
    assert any("24 班" in m.parti for m in moves), [m.parti for m in moves]
    assert all(m.why for m in moves)
    assert any(m.answers for m in moves)


def test_missing_inputs_are_named_not_invented() -> None:
    b = sb.build(_ctx("新建工业厂房", codes=["A12"]))
    assert b.sector == "industrial"
    assert any("工艺" in m for m in b.missing), b.missing
    # 没有柱网就不要编一个"精确"的跨度结论
    assert any("柱网" in a for a in b.assumptions) or "grid" in b.inputs


def test_hospital_reasoning_uses_beds_and_outpatient() -> None:
    b = sb.build(_ctx("新建综合医院 300 床，日门诊 1200 人", codes=["A4"]))
    assert b.get("beds") == 300 and b.get("outpatient") == 1200
    moves = mv.moves(b)
    text = " ".join(m.parti + m.why for m in moves)
    assert "300" in text and "1200" in text, text[:120]


# --------------------------------------------------------------------------
# 3. 排布：同一套 zone_bands，面积回到任务书
# --------------------------------------------------------------------------
def _project_with(text: str, code: str, ancillary=(), lead="architecture") -> tuple:
    b = sb.build(_ctx(text, codes=[code], ancillary=ancillary, lead=lead))
    prog = sp.build(b)
    env = lay.envelope_size(prog, b.sector)
    p = Project(project_id="t", name=text)
    p.meta = {}
    lay.install_program(p, prog)
    lay.install_envelope(p, env)
    schemes = lay.build_schemes(p, prog, b.sector, env)
    return b, prog, env, p, schemes


def test_school_plan_keeps_target_areas() -> None:
    b, prog, env, p, schemes = _project_with(
        "新建 24 班小学，用地 20000 平方米", "A3", ["学生食堂", "校园体育馆"])
    a = schemes["A"]
    rows = {r["name"]: r for r in a.area_table()}
    classroom = rows["普通教室 1"]
    # 允许带宽补齐造成的 ±25% 偏差，但不能是 0 或翻倍
    assert 0.75 * 65 <= classroom["area_m2"] <= 1.25 * 65, classroom
    # 有窗、有采光：学校平面没有窗就不成立
    assert a.metrics["window_count"] >= 6, a.metrics["window_count"]
    assert not [w for w in a.warnings if "没有可利用的外墙" in w][:1]


def test_industry_uses_the_same_layout_algorithm() -> None:
    for text, code, sectors in (
        ("既有酒店室内精装修，120 间客房", "B4", "hospitality"),
        ("新建工业厂房 12000 平方米，柱网 9x9 米", "A12", "industrial"),
        ("新建综合医院 300 床，日门诊 1200 人", "A4", "healthcare"),
    ):
        b, prog, env, p, schemes = _project_with(text, code, lead=b"architecture".decode())
        assert b.sector == sectors, (text, b.sector)
        assert schemes["A"].strategy == "zone_bands"
        assert len(schemes["A"].area_table()) >= 6, text


def test_landscape_does_not_use_room_layout() -> None:
    b = sb.build(_ctx("独立私家庭院景观 800 平方米，包含水景与种植", codes=["C2"],
                      lead="landscape"))
    prog = sp.build(b)
    assert b.sector == "landscape"
    data = lay.landscape_data(prog, b)
    shares = sum(float(z["share"].rstrip("%")) for z in data["zones"])
    assert 95 <= shares <= 105, shares


# --------------------------------------------------------------------------
# 4. G3：没有设计数据不能算专业方案
# --------------------------------------------------------------------------
def test_gate_blocks_a_task_list_without_design_data() -> None:
    out = sck.assess(None, {"sector": "education", "rooms": 0,
                            "design_data": {"codes": ["A3"]}}, ["architecture"])
    assert [b["id"] for b in out["blockers"]] == ["G3-NO-DESIGN-DATA"]


def test_gate_records_the_proposed_envelope_and_type_limits() -> None:
    rec = {"sector": "healthcare", "rooms": 16,
           "design_data": {"codes": ["A4"], "proposed_envelope": True,
                           "envelope": {"area_m2": 1351, "width_mm": 81900,
                                        "depth_mm": 16500},
                           "missing_inputs": ["缺日门诊量：算不出门诊单元数量"]}}
    out = sck.assess(None, rec, ["architecture"])
    ids = [c["id"] for c in out["conditions"]]
    assert not out["blockers"]
    assert "G3-PROPOSED-ENVELOPE" in ids
    # 医疗属专项：必须留"须专项顾问复核"的条件
    assert "G3-SPECIALIST-REVIEW" in ids
    assert "G3-MISSING-INPUT" in ids


def test_landscape_gate_marks_zoning_as_schematic() -> None:
    rec = {"sector": "landscape", "rooms": 4,
           "design_data": {"codes": ["C2"], "zones": [{"name": "水面"}]}}
    ids = [c["id"] for c in sck.assess(None, rec, ["landscape"])["conditions"]]
    assert "G3-LANDSCAPE-SCHEMATIC" in ids


# --------------------------------------------------------------------------
# 5. 不退化：住宅/办公仍走原路
# --------------------------------------------------------------------------
def test_housing_projects_do_not_enter_the_sector_branch() -> None:
    b = sb.build(_ctx("150 平方米大平层家装", codes=["B1"], lead="interior"))
    assert b.sector == "housing"
    assert sp.BUILDERS.get(b.sector) is None, "住宅不该被行业程序接管"
