"""设计能力层验收：空间体验与技术实现。

测试原则与 S2 一致——**测「能不能被反驳」**，不测「有没有返回一个字典」：

* 序列必须写「人经历什么」，不能把布局原文贴上来；
* 业主没说感受时，不能替他决定「要温馨」；
* 三套方向对同一句诉求不能给同一句话，否则业主看不出差别；
* 结构机电提到「挑空」时必须给实现路径，而不是把方案判成不可行；
* 物理做不到的（中间层开天窗）必须明说，且给替代做法，不列假路径。

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import tempfile
from pathlib import Path

from omniarchitect.concept.prototypes import PROTOTYPES, get
from omniarchitect.demo import build_demo_project
from omniarchitect.design import enabling as E
from omniarchitect.design import vocabulary as V
from omniarchitect.intake.gate import decide_gate as decide_g1
from omniarchitect.intake.interview import answer_question, start_interview
from omniarchitect.intake.profiles import QUESTION_INDEX, SLOTS


# --------------------------------------------------------------------------
# 1. 词表本身
# --------------------------------------------------------------------------
def test_every_device_has_a_way_to_be_checked():
    """一个没有核验办法的术语只是装饰——四项缺一不可。"""
    for d in V.all_devices():
        assert d.why and len(d.why) > 20, f"{d.id} 缺机制说明"
        assert d.how, f"{d.id} 缺做法"
        assert d.test, f"{d.id} 缺图上核验办法"
        assert d.misuse, f"{d.id} 缺误用后果"


def test_vocabulary_does_not_invent_famous_buildings():
    """写进「某某建筑因此著名」就等于替建筑师背书，而我们无法核实。"""
    for d in V.all_devices():
        blob = " ".join([d.why, d.plain, d.misuse, *d.how])
        for forbidden in ("著名", "代表作", "获得了", "普利兹克"):
            assert forbidden not in blob, f"{d.id} 出现不可核实的背书：{forbidden}"


def test_feeling_words_all_point_at_real_devices():
    for word, devs in V.FEELING_WORDS.items():
        assert devs, f"「{word}」没有对应手法"
        for d in devs:
            assert d in V.VOCABULARY, f"「{word}」指向不存在的手法 {d}"


def test_longer_negation_wins_over_shorter_word():
    """「不压抑」不能被读成「压抑」。"""
    got = V.read_feelings("我希望不压抑，别太闷")
    assert "不压抑" in got
    assert "压抑" not in got


def test_empty_text_states_nothing():
    assert V.read_feelings("") == {}
    assert V.read_feelings("   ") == {}


# --------------------------------------------------------------------------
# 2. 体验序列
# --------------------------------------------------------------------------
def test_every_prototype_has_an_entry_event():
    """每套原型都要能说清「进门先看到什么」，且必须具体到能画。"""
    for pid, items in PROTOTYPES.items():
        for p in items:
            assert p.id in V.ENTRY_EVENT, f"{p.id}（{pid}）没有进门第一眼的空间事件"


def test_sequence_does_not_echo_layout_text():
    """序列写的是「经历」，不是把 circulation 原文复制一遍。"""
    for p in PROTOTYPES["residential"]:
        seq = V.sequence_for(p.to_dict())
        circ = str(p.circulation)
        for step in seq["steps"]:
            assert step["event"] != circ, f"{p.id} 的序列直接贴了布局原文"
            # 转折那一步尤其危险：曾经就是「路径上第一次方向或宽度的改变：<原文>」
            if step["step"] == "转折":
                assert not step["event"].startswith("路径上第一次"), \
                    f"{p.id} 的转折仍是布局描述而不是经历"


def test_sequence_steps_carry_a_device():
    for p in PROTOTYPES["hospitality"]:
        for step in V.sequence_for(p.to_dict())["steps"]:
            assert step["device"] in V.VOCABULARY, f"{p.id} 的 {step['step']} 没有对应手法"


def test_missing_steps_are_reported_not_padded():
    """缺哪段就说缺哪段，不用形容词补。"""
    seq = V.sequence_for({"prototype_id": "X", "family": "linear"})
    assert seq["missing_steps"], "空原型居然报告序列完整"


# --------------------------------------------------------------------------
# 3. 业主感受 → 方案能力
# --------------------------------------------------------------------------
def test_no_stated_feeling_is_not_invented():
    got = V.fit({}, get("RES-BAND").to_dict())
    assert got["status"] == "not_stated"
    assert got["met"] == [] and got["at_risk"] == []
    assert "不替他决定" in got["note"]


def test_ritual_is_a_strength_of_the_layered_family():
    """分层递进的本质是门槛与到达；把它判成「不是强项」是判断错误。"""
    got = V.fit({"仪式感": ["arrival_sequence"]}, get("RES-THRESHOLD").to_dict())
    assert got["status"] == "met"
    assert got["primary"], "仪式感应是分层家族的主张"
    assert got["primary"][0]["word"] == "仪式感"


def test_loop_cannot_promise_ritual_and_says_so():
    """回游环的第一眼本来就没有主画面——给不出仪式感属于真实取舍，必须承认。"""
    got = V.fit({"仪式感": ["arrival_sequence"]}, get("RES-LOOP").to_dict())
    assert got["status"] == "at_risk"
    assert any(r["word"] == "仪式感" for r in got["at_risk"])


def test_three_directions_do_not_say_the_same_sentence():
    """都能回应同一句诉求时，必须拉出差别，否则业主看不出选哪套。"""
    feelings = {"仪式感": ["arrival_sequence"]}
    heads = {V.fit(feelings, p.to_dict())["headline"]
             for p in PROTOTYPES["residential"]
             if V.fit(feelings, p.to_dict())["status"] != "not_stated"}
    assert len(heads) >= 2, f"所有方向都说了同一句话：{heads}"


def test_score_feelings_weight_is_bounded():
    for p in PROTOTYPES["residential"]:
        got = V.score_feelings(V.read_feelings("要敞亮、显大、有仪式感"), p.to_dict())
        assert 0.0 <= got["weight"] <= 1.0


# --------------------------------------------------------------------------
# 4. 结构与机电：实现路径，不是审批口
# --------------------------------------------------------------------------
def test_required_paths_are_complete():
    """每条路径都要写代价与签字责任——没有零代价的路径。"""
    for g in E.all_goals():
        assert len(g.paths) >= 2, f"{g.id} 只有一个选项等于没有选择"
        for p in g.paths:
            assert p.how and p.gains and p.trades, f"{g.id}/{p.id} 缺做法或代价"
            assert p.sign_off, f"{g.id}/{p.id} 缺签字责任——这会越过安全底线"


def test_double_height_gets_real_paths_not_a_refusal():
    got = E.structure_paths("客厅做通高，楼上楼板要开洞")
    assert got["goals"], "提到通高却没有给出任何实现路径"
    ids = {p["path_id"] for g in got["goals"] for p in g["paths"]}
    assert "P-STEEL-FRAME" in ids


def test_opening_a_wall_offers_three_ways():
    got = E.structure_paths("要拆一面承重墙把客厅和餐厅打通")
    names = [p["name"] for g in got["goals"] for p in g["paths"]]
    assert any("托换" in n for n in names), "拆承重墙必须给出托换路径"
    assert any("保留" in n for n in names), "也必须给出不拆的路径"


def test_untriggered_goals_are_not_listed():
    """没提到的事就不列通用清单——凑数让报告变成模板。"""
    got = E.structure_paths("墙面刷浅色乳胶漆")
    assert got["goals"] == []


def test_skylight_mid_floor_is_called_out_with_alternatives():
    got = E.structure_paths("想在客厅开天窗，房子在 6 层，共 18 层")
    blocked = [b for b in got["blocked"] if b["id"] == "skylight_mid_floor"]
    assert blocked, "中间层开天窗被当成了可行"
    assert blocked[0]["status"] == "conditional"
    assert "替代" in blocked[0]["why"], "说了做不到，就必须给替代做法"


def test_top_floor_skylight_is_not_blocked():
    got = E.structure_paths("顶层自建房，客厅开天窗")
    assert not [b for b in got["blocked"] if b["id"] == "skylight_mid_floor"]


def test_mep_solves_the_disappearing_device_problem():
    got = E.mep_paths("不想吊顶，要保留原始天花，做开放厨房")
    ids = {g["goal_id"] for g in got["goals"]}
    assert "MEP-HIGH-CEILING" in ids
    assert "MEP-KITCHEN-OPEN" in ids


# --------------------------------------------------------------------------
# 5. S1：多问的一句是「感受」，不是又一道资料题
# --------------------------------------------------------------------------
def test_feeling_slot_exists_and_is_not_critical():
    """感受影响方案水平，但不该堵住任务书——它是 important，不是 critical。"""
    assert "feeling" in SLOTS
    assert SLOTS["feeling"]["critical"] is False
    q = QUESTION_INDEX["base.feeling"]
    assert q.slot == "feeling"
    assert q.priority == "important"
    assert q.affects == "S2"


def test_feeling_question_offers_no_options():
    """给选项会把业主的答案框成我们预设的那几种。"""
    assert QUESTION_INDEX["base.feeling"].options == ()


def test_feeling_seeded_from_first_sentence_is_not_asked_again():
    tmp = Path(tempfile.mkdtemp())
    p = build_demo_project(tmp / "proj")
    start_interview(p, "120㎡ 公寓改造，进门要有仪式感，客厅要显得敞亮")
    from omniarchitect.intake.interview import _covered_slots

    covered = _covered_slots(p)
    assert "feeling" in covered, "首句已经说了感受，却没有记下来"


# --------------------------------------------------------------------------
# 6. 端到端：报告里真的出现体验序列，且结构不再是阻断
# --------------------------------------------------------------------------
def _ready(tmp: Path):
    p = build_demo_project(tmp / "proj")
    p.constraints = {**(p.constraints or {}), "style": "日式", "budget_cny": 1_800_000}
    start_interview(p, "150㎡ 湖畔别墅改造，一家四口")
    answer_question(p, "res.household", "一家四口，有一个 5 岁孩子")
    answer_question(p, "base.feeling",
                    "进门不要一眼看穿，走两步再放开；要显得敞亮显大，回家有仪式感")
    answer_question(p, "base.needs", "客厅要能坐下来聊；主卧要有衣帽间；厨房要开放")
    decide_g1(p, "approved", by="业主", source="owner")
    return p


def test_report_contains_experience_section_and_feeling_answer():
    from omniarchitect.concept import generate_bundle

    tmp = Path(tempfile.mkdtemp())
    p = _ready(tmp)
    generate_bundle(p, tmp / "S2", with_deck=False)
    md = (tmp / "S2" / "concept-options.md").read_text(encoding="utf-8")
    assert "走进去会经历什么" in md
    assert "对业主诉求的回应" in md
    assert "第一眼" in md


def test_report_does_not_give_a_feeling_answer_when_client_said_nothing():
    from omniarchitect.concept import generate_bundle

    tmp = Path(tempfile.mkdtemp())
    p = build_demo_project(tmp / "proj")
    p.constraints = {**(p.constraints or {}), "budget_cny": 1_800_000}
    start_interview(p, "150㎡ 大平层，一家三口")
    answer_question(p, "res.household", "一家三口")
    answer_question(p, "base.needs", "客厅要大；要收纳")
    decide_g1(p, "approved", by="业主", source="owner")
    generate_bundle(p, tmp / "S2", with_deck=False)
    md = (tmp / "S2" / "concept-options.md").read_text(encoding="utf-8")
    assert "对业主诉求的回应" not in md
    assert "走进去会经历什么" in md      # 序列照给，但不对感受下结论


def test_structure_paths_reach_the_report():
    """概念提到通高时，结构方向必须带实现路径，而不是只有一句「待补资料」。"""
    from omniarchitect import disciplines as D
    from omniarchitect.concept import disciplines as CD

    tmp = Path(tempfile.mkdtemp())
    p = _ready(tmp)
    scope = D.ensure(p, profile_id="residential")
    concept = {
        "concept_id": "C-T", "concept_name": "通高中厅",
        "concept_statement": "客厅做通高，楼板开洞",
        "spatial_prototype": get("RES-LIGHT").to_dict(),
        "spatial_strategy": "客厅通高，挑空两层，结构需在楼板开洞",
        "material_direction": [], "lighting_direction": [],
    }
    got = CD.for_concept(p, scope, concept, None)["structure"]
    assert got["implementation_paths"]["goals"], "提到挑空却没给实现路径"
    assert got["status"] == "proposed", "给了具体做法却仍判为待补资料"
    for g in got["implementation_paths"]["goals"]:
        for path in g["paths"]:
            assert path["sign_off"], "实现路径缺签字责任"
