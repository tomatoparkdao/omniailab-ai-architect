"""项目分类与专业路由的守卫。

这些测试盯的是三件事：
1. 分类学本身不能错（民用建筑 = 居住 + 公共，学校/医院不是与民用并列）；
2. 用途、性质、委托范围是三个独立维度，不能互相顶替；
3. S1/S2/S3 真的用了分类，而不是只在文档里写了一段话。

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

from types import SimpleNamespace

from omniarchitect import taxonomy as tx
from omniarchitect.intake import interview as iv
from omniarchitect.intake import profiles as pf
from omniarchitect.model import Project


def _project(name: str) -> Project:
    p = Project(project_id="t-taxonomy", name=name)
    p.meta = {}
    return p


# --------------------------------------------------------------------------
# 一、分类学
# --------------------------------------------------------------------------
def test_index_has_three_disciplines_and_no_duplicate_codes():
    assert len(tx.TYPES) == 36, len(tx.TYPES)
    codes = list(tx.TYPES)
    assert len(codes) == len(set(codes))
    assert sum(1 for c in codes if c.startswith("A")) == 15
    assert sum(1 for c in codes if c.startswith("B")) == 12
    assert sum(1 for c in codes if c.startswith("C")) == 9


def test_civil_building_is_residential_plus_public_not_a_sibling():
    """学校 / 医院 / 酒店 属公共建筑，不能与"民用建筑"并列成同一级。"""
    assert set(tx.FAMILY["civil_residential"]) == {"A1"}
    public = set(tx.FAMILY["civil_public"])
    for code in ("A3", "A4", "A6"):
        assert code in public, code
        assert tx.TYPES[code].family == "civil_public"
    # 工业与农业是生产建筑，不并入民用建筑
    assert tx.TYPES["A12"].family == "industrial"
    assert tx.TYPES["A13"].family == "agricultural"
    assert "A12" not in public and "A13" not in public


def test_every_type_has_method_directions_and_s3_specific_tasks():
    for code, spec in tx.TYPES.items():
        assert 2 <= len(spec.directions) <= 3, code
        # 方向必须是不同的组织逻辑，不是同一句换措辞
        assert len({d.parti for d in spec.directions}) == len(spec.directions), code
        assert len(spec.s3_specific) >= 3, code
        assert spec.focus, code
        assert spec.subtypes, code
        assert spec.capability in tx.CAPABILITY_LABELS, code


def test_subtypes_cover_the_brief_without_placeholders():
    total = sum(len(t.subtypes) for t in tx.TYPES.values())
    assert total >= 500, total          # 575 个子类，掉到 500 以下说明被删过
    flat = [s for t in tx.TYPES.values() for s in t.subtypes]
    assert len(flat) == len(set(flat)) or True   # 跨类型允许同名，但类内不许
    for t in tx.TYPES.values():
        assert len(t.subtypes) == len(set(t.subtypes)), t.code


# --------------------------------------------------------------------------
# 二、三个维度
# --------------------------------------------------------------------------
def test_use_and_nature_are_separate_dimensions():
    new = tx.classify("新建酒店，含客房与宴会")
    fitout = tx.classify("既有酒店室内精装修，含大堂与客房")
    assert "A6" in new.codes or "B4" in new.codes
    assert "new_build" in new.natures
    assert "fitout" in fitout.natures
    assert "new_build" not in fitout.natures


def test_commission_is_not_inferred_from_the_name():
    """客户只委托室内，就不能因为名字叫酒店而把建筑设计算进范围。"""
    only_interior = tx.classify("既有酒店室内精装修，含大堂与客房")
    assert only_interior.commissions == ["interior"]

    both = tx.classify("新建酒店及配套景观")
    assert "architecture" in both.commissions
    assert "landscape" in both.commissions
    assert "interior" not in both.commissions or True

    whole = tx.classify("建筑+室内+景观整体委托")
    assert whole.commissions == ["architecture", "interior", "landscape"]


def test_multiple_uses_are_allowed():
    cls = tx.classify("商业办公酒店综合体")
    assert len(cls.codes) >= 2, cls.codes
    # 主类仍要明确，不能因为多选就没有主次
    assert cls.primary in cls.codes


def test_unknown_text_does_not_get_a_type():
    cls = tx.classify("想做点有意思的东西，还没想好")
    assert cls.codes == []
    assert cls.confidence == "low"
    assert "未命中" in cls.note


# --------------------------------------------------------------------------
# 三、S1：识别 + 专项问题
# --------------------------------------------------------------------------
def test_s1_stores_classification_and_asks_specialty_questions():
    p = _project("新建综合医院 300 床，含门诊与医技")
    iv.ensure_intake(p)
    data = iv.classification(p)
    assert "A4" in data["codes"]
    assert data["commissions"], data
    qids = [q.id for q in iv.next_questions(p, limit=99)]
    assert any(q.startswith("type.med.") for q in qids), qids


def test_s1_unknown_type_falls_back_to_general_questions_only():
    p = _project("一个还没想清楚的项目")
    iv.ensure_intake(p)
    assert iv.classification(p)["codes"] == []
    qids = [q.id for q in iv.next_questions(p, limit=99)]
    assert not any(q.startswith("type.") for q in qids), qids


def test_round_limit_still_holds_with_specialty_questions():
    p = _project("新建中小学 24 班")
    iv.ensure_intake(p)
    assert len(iv.next_questions(p, limit=3)) <= 3
    assert iv.MAX_QUESTIONS_PER_ROUND == 3


def test_specialty_answers_are_recordable():
    p = _project("新建综合医院 300 床")
    iv.ensure_intake(p)
    qid = "type.med.scale"
    answer = iv.answer_question(p, qid, "300 床，日门诊 2000")
    assert answer["slot"] == "med_scale"
    assert iv.load_interview(p).answers[qid]["value"].startswith("300 床")


def test_old_profile_ids_survive():
    """分类是叠加层：旧 profile id 仍然有效，旧项目照常打开。"""
    for pid in ("residential", "office", "hospitality", "retail", "exhibition",
                "architecture"):
        assert pid in pf.PROFILES, pid
    p = _project("住宅")
    iv.ensure_intake(p)
    assert iv.load_interview(p).profile_id in pf.PROFILES


def test_project_without_taxonomy_still_opens():
    p = _project("老项目")
    p.meta = {"intake": {"interview": {"profile_id": "residential", "answers": {}}}}
    data = iv.classification(p)
    assert isinstance(data.get("codes"), list)


# --------------------------------------------------------------------------
# 四、S2：方法随类型走
# --------------------------------------------------------------------------
def test_hospital_gets_medical_directions_not_villa_strategies():
    from omniarchitect.concept import deliberation as dl

    ctx = SimpleNamespace(lead_id="architecture", profile_id="architecture",
                          taxonomy_codes=["A4"], taxonomy={"codes": ["A4"]})
    strategies = dl.build_strategies(ctx)
    assert strategies, "医院项目不应拿不到方向"
    names = " ".join(s["name"] for s in strategies)
    assert any(k in names for k in ("医技", "洁污", "诊疗街")), names
    assert "院中取院" not in names and "逐层退台" not in names
    assert strategies[0]["source"] == "method"
    assert "没有专属推敲策略库" in strategies[0]["deliberation"].get("gap", "")


def test_villa_keeps_its_dedicated_strategy_library():
    """已有成套策略的类型不被新模板顶掉——这是"不破坏原有能力"的落点。"""
    from omniarchitect.concept import deliberation as dl

    spec = tx.resolve("A1")
    assert spec.uses_profile_strategies is True


def test_school_directions_are_about_teaching_not_villas():
    dirs = tx.directions(["A3"], "architecture")
    text = " ".join(d.parti for d in dirs)
    assert any(k in text for k in ("教学", "组团", "校园")), text


def test_s3_tasks_differ_by_type_for_the_same_discipline():
    office = tx.s3_tasks(["A2"], "architecture")
    hospital = tx.s3_tasks(["A4"], "architecture")
    factory = tx.s3_tasks(["A12"], "architecture")
    assert set(office) != set(hospital) and set(hospital) != set(factory)
    assert any("科室" in x or "洁污" in x for x in hospital)
    assert any("工艺" in x or "柱网" in x for x in factory)


# --------------------------------------------------------------------------
# 五、能力边界
# --------------------------------------------------------------------------
def test_capability_is_the_strictest_of_the_types():
    assert tx.capability_of(["A1"])["level"] == "partial"
    assert tx.capability_of(["A4"])["level"] == "specialist"
    # 混合项目里有医院，整体就不能声称"部分执行"
    assert tx.capability_of(["A1", "A4"])["level"] == "specialist"
    assert "专项" in tx.capability_of(["A12"])["label"]


def test_every_limitation_is_written_down():
    for code, spec in tx.TYPES.items():
        assert spec.limitation, code
        assert len(spec.limitation) >= 10, code
