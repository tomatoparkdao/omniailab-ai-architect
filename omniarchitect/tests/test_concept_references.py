"""S2 ↔ case research: the concept must explain the case, not wear it.

The single most important assertion in this file is `test_third_party_image
_is_never_embeddable`. Everything else is about the four questions being
actually answered per concept instead of one paragraph repeated three times.

No network here: the research payload is constructed by hand in the shape
`research.run()` produces, which is also what a stored project looks like.

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

from omniarchitect.concept import references as ref


def _case(**over):
    base = {
        "title": "Colares Sintra House",
        "architect": "Sabrab",
        "url": "https://www.archdaily.com/1187054/colares-sintra-house-sabrab",
        "image_url": "https://images.adsttc.com/media/images/aa/large_jpg/x.jpg",
        "verify": "verified",
        "verify_label": "已回读核验：页面可打开，标题一致",
        "discipline": "architecture",
        "summary": "Set within a pine forest. Courtyard and villa.",
        "area": "320 m²",
        "fits": ["你提到「通透」"],
        "avoid": ["不照搬它的总平面与开间尺寸"],
        "image_rights": "link_only",
    }
    base.update(over)
    return base


def _research(cases=None):
    return {"cases": cases if cases is not None else [_case()], "counts": {"total": 1}}


def _concept(cid="c1", name="静院之家"):
    return {
        "concept_id": cid,
        "name": name,
        "style_labels": ["现代极简"],
        "feelings": ["通透"],
        "experience_sequence": ["入户", "转折", "见院"],
        "materials": ["木饰面", "清水混凝土"],
        "disciplines": {"architecture": {}},
    }


# --------------------------------------------------------------------------
# the rights gate
# --------------------------------------------------------------------------
def test_third_party_image_is_never_embeddable():
    assert ref.embed_allowed("link_only") is False
    att = ref.build([_concept()], _research())
    for entry in att.values():
        for c in entry["cases"]:
            assert c["embeddable"] is False
            assert c["usage"] == "card", c["usage"]


def test_own_imagery_may_be_embedded():
    assert ref.embed_allowed("own") is True
    att = ref.build([_concept()], _research([_case(image_rights="own")]))
    for entry in att.values():
        for c in entry["cases"]:
            assert c["embeddable"] is True
            assert c["usage"] == "board"


def test_usage_label_is_always_present_for_the_client():
    att = ref.build([_concept()], _research())
    for entry in att.values():
        for c in entry["cases"]:
            assert c["usage_label"]


# --------------------------------------------------------------------------
# the four questions
# --------------------------------------------------------------------------
def test_each_attached_case_answers_all_four_questions():
    att = ref.build([_concept()], _research())
    cases = att["c1"]["cases"]
    assert cases
    for c in cases:
        assert c["why"], "为什么参考它"
        assert isinstance(c["borrow"], list) and c["borrow"], "借鉴什么"
        assert c["transform"], "怎么转化"
        assert isinstance(c["limits"], list) and c["limits"], "什么不能照搬"


def test_transform_is_written_for_this_concept_not_copied():
    a = ref.build([_concept("c1", "静院之家")], _research())
    b = ref.build([_concept("c2", "光廊之家")], _research())
    ta = a["c1"]["cases"][0]["transform"]
    tb = b["c2"]["cases"][0]["transform"]
    assert "静院之家" in ta
    assert "光廊之家" in tb
    assert ta != tb


def test_area_becomes_a_limit_not_a_target():
    att = ref.build([_concept()], _research())
    limits = att["c1"]["cases"][0]["limits"]
    assert any("320" in x for x in limits), limits


# --------------------------------------------------------------------------
# refusals
# --------------------------------------------------------------------------
def test_unrelated_cases_are_not_forced_onto_a_concept():
    unrelated = _case(title="Museum of Concrete", summary="", url="",
                      image_rights="link_only")
    concept = _concept()
    concept["style_labels"] = ["巴洛克"]
    concept["feelings"] = ["繁复"]
    concept["disciplines"] = {}
    att = ref.build([concept], _research([unrelated]))
    entry = att["c1"]
    assert entry["cases"] == []
    assert "不强行挂靠" in entry["note"] or "不匹配" in entry["note"] or entry["note"]


def test_no_research_says_so_instead_of_inventing_a_case():
    att = ref.build([_concept()], None)
    assert att["c1"]["cases"] == []
    assert "不编造" in att["c1"]["note"] or "尚无" in att["c1"]["note"]


def test_research_that_found_nothing_is_stated_plainly():
    att = ref.build([_concept()], {"cases": []})
    assert att["c1"]["cases"] == []
    assert att["c1"]["note"]


# --------------------------------------------------------------------------
# the document
# --------------------------------------------------------------------------
def test_markdown_prints_links_and_the_no_image_rule():
    att = ref.build([_concept()], _research())
    md = ref.markdown(att, [_concept()])
    assert "https://www.archdaily.com/1187054/" in md
    assert "只给链接" in md or "不进入本提案的版面" in md
    assert "静院之家" in md


def test_markdown_for_empty_attachment_is_honest_not_blank():
    att = ref.build([_concept()], None)
    md = ref.markdown(att, [_concept()])
    assert "静院之家" in md
    assert "参考案例" in md
