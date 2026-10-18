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
    """The shape `concept.generate_bundle()` really returns.

    Both `experience_sequence` and `disciplines` are mappings in the real
    payload. This fixture used to give `experience_sequence` as a bare list,
    which is why `_first_step` raised `KeyError: 0` in production while this
    file stayed green — do not put the list form back.
    """
    return {
        "concept_id": cid,
        "name": name,
        "style_labels": ["现代极简"],
        "feelings": ["通透"],
        "experience_sequence": {
            "prototype_id": "RES-THRESHOLD",
            "family": "layered",
            "steps": [
                {"step": "入户", "event": "压低净高，收住视线"},
                {"step": "转折", "event": "绕过隔墙"},
                {"step": "见院", "event": "庭院在转角后打开"},
            ],
        },
        "spatial_prototype": {"family": "layered"},
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


# --------------------------------------------------------------------------
# regressions: three shapes that silently disabled the whole attachment
# --------------------------------------------------------------------------
def test_mapping_experience_sequence_does_not_crash():
    """`experience_sequence` is a mapping. Indexing it as a list raised
    `KeyError: 0` as soon as a case was attached — an empty shortlist hid it."""
    c = _concept()
    assert isinstance(c["experience_sequence"], dict)
    assert ref._first_step(c) == "入户"


def test_first_step_still_reads_the_legacy_list_form():
    c = _concept()
    c["experience_sequence"] = ["入户", "转折"]
    assert ref._first_step(c) == "入户"


def test_first_step_of_an_empty_or_missing_sequence_is_blank():
    for seq in (None, {}, {"steps": []}, [], ()):
        c = _concept()
        c["experience_sequence"] = seq
        assert ref._first_step(c) == ""


def test_borrow_line_uses_the_real_first_step():
    att = ref.build([_concept()], _research())
    borrow = att["c1"]["cases"][0]["borrow"]
    assert any("入户" in b for b in borrow), borrow


def test_discipline_is_read_from_the_mapping_keys():
    """Testing membership on `str(dict)` searched the repr, so the discipline
    point never fired and every case scored on style alone."""
    assert ref._discipline_keys(_concept()) == frozenset({"architecture"})


def test_discipline_point_is_actually_awarded():
    concept = _concept()
    concept["style_labels"] = ["nothing-matches-here"]
    concept["feelings"] = []
    case = _case(title="Untitled", summary="", url="", discipline="architecture")
    assert ref._score(case, concept, "") == 1


def test_chinese_style_word_matches_english_case_text_via_the_bridge():
    """Concepts are Chinese, ArchDaily descriptions are English. Without the
    bridge every score was 0 and the shortlist came out falsely empty."""
    concept = _concept()
    concept["style_labels"] = ["极简"]
    concept["feelings"] = []
    concept["disciplines"] = {}
    case = _case(title="House", summary="A minimalist volume", discipline="")
    assert ref._score(case, concept, "") == 2


def test_an_unbridgeable_term_scores_zero_rather_than_matching_by_accident():
    concept = _concept()
    concept["style_labels"] = ["巴洛克"]
    concept["feelings"] = []
    concept["disciplines"] = {}
    case = _case(title="House", summary="A minimalist volume", discipline="")
    assert ref._score(case, concept, "") == 0


def test_family_signal_breaks_a_style_tie_without_inventing_a_match():
    """All three concepts of a client-specified style tie on style. The family
    signal decides *which* case explains *which* concept — and returns 0 when
    the case text says nothing about the family, rather than guessing."""
    layered = _concept("c1")
    hall = _concept("c2")
    hall["spatial_prototype"] = {"family": "hall"}
    case = _case(summary="A sequence of thresholds and level changes")
    assert ref._family_bonus(case, layered) == 1
    assert ref._family_bonus(case, hall) == 0

    silent = _case(title="Colares", summary="Set within a pine forest")
    assert ref._family_bonus(silent, layered) == 0


def test_family_tie_break_selects_the_closer_case():
    layered = _concept("c1")
    seq_case = _case(title="Threshold House",
                     summary="an entry sequence of compression and release")
    plain_case = _case(title="White House", summary="a minimal villa")
    att = ref.build([layered], _research([plain_case, seq_case]))
    titles = [c["title"] for c in att["c1"]["cases"]]
    assert titles[0] == "Threshold House", titles

