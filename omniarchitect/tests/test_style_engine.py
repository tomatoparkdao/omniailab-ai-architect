"""Recommender, compiler and provider-bridge tests.

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from omniarchitect.style import catalog as C  # noqa: E402
from omniarchitect.style import compiler as K  # noqa: E402
from omniarchitect.style import provider_bridge as P  # noqa: E402
from omniarchitect.style import recommender as R  # noqa: E402
from omniarchitect.style.resources import PROMPT_TARGETS  # noqa: E402

CAT = C.load_catalog()


# --------------------------------------------------------------------------
# Recommender
# --------------------------------------------------------------------------
def test_family_priors_are_only_called_for_known_families():
    """`family` must not silently mismatch — families are the option-diversity key."""
    for ids in R.SPACE_FAMILY_PRIOR.values():
        for f in ids:
            assert f in {e.family for e in CAT}, f


def test_recommend_returns_three_options_with_distinct_roles():
    rs = R.recommend(R.RecommendRequest(space_type="住宅", area_m2=120,
                                        budget_tier="mid", maintenance="low"))
    assert len(rs.options) == 3
    assert {o.role for o in rs.options} == {"safe", "distinctive", "hybrid"}


def test_safe_and_distinctive_options_come_from_different_families():
    rs = R.recommend(R.RecommendRequest(space_type="住宅", area_m2=140,
                                        budget_tier="mid", maintenance="low"))
    safe, alt = rs.option("safe"), rs.option("distinctive")
    assert safe and alt
    if safe.style_id != alt.style_id:
        assert CAT.get(safe.style_id).family != CAT.get(alt.style_id).family, \
            "对照方案必须来自不同族，否则不算另一种方案"


def test_chinese_preferences_actually_move_the_ranking():
    """Without the tag bridge, '简洁、温暖' scores as if nothing was said."""
    plain = R.recommend(R.RecommendRequest(space_type="住宅", area_m2=120,
                                           budget_tier="mid", maintenance="low"))
    with_pref = R.recommend(R.RecommendRequest(space_type="住宅", area_m2=120,
                                               budget_tier="mid", maintenance="low",
                                               preferences=["简洁", "温暖"]))
    assert plain.option("safe") and with_pref.option("safe")
    assert with_pref.option("safe").score > plain.option("safe").score
    assert any("取向" in w or "偏好" in w for w in with_pref.option("safe").why)


def test_naming_a_style_directly_wins():
    cat = C.load_catalog()
    rs = R.recommend(R.RecommendRequest(space_type="住宅", preferences=["japandi"]),
                     catalog=cat)
    assert rs.options[0].style_id == "japandi"


def test_over_budget_styles_are_flagged_not_hidden():
    rs = R.recommend(R.RecommendRequest(space_type="住宅", area_m2=100,
                                        budget_tier="economy", maintenance="low"))
    top = rs.options[0]
    tier = CAT.get(top.style_id).budget_tier
    if R.BUDGET_ORDER.index(tier) > R.BUDGET_ORDER.index("economy"):
        assert any("预算" in c for c in top.cautions), \
            "超出预算的风格必须给出提醒，而不是悄悄推荐"


def test_high_maintenance_styles_warn_when_the_client_wants_low_upkeep():
    rs = R.recommend(R.RecommendRequest(space_type="住宅", budget_tier="luxury",
                                        maintenance="low"))
    for o in rs.options:
        level = R.MAINTENANCE_PROFILE.get(o.style_id, ("low", ""))[0]
        if level == "high":
            assert any("维护" in c for c in o.cautions), o.style_id


def test_every_option_explains_itself():
    rs = R.recommend(R.RecommendRequest(space_type="办公", area_m2=500,
                                        budget_tier="mid"))
    for o in rs.options:
        assert o.why, f"{o.style_id} 没有给出推荐理由"
        assert o.pros or o.hybrid_with, f"{o.style_id} 没有列出优点"
        assert o.cons, f"{o.style_id} 没有列出代价"


def test_small_area_penalises_styles_that_need_height():
    rs = R.recommend(R.RecommendRequest(space_type="住宅", area_m2=60,
                                        budget_tier="mid"))
    for o in rs.options:
        if o.style_id in R.NEEDS_HEIGHT:
            assert any("小面积" in c or "难" in c for c in o.cautions), o.style_id


def test_lock_records_the_decision_with_a_revision():
    rs = R.recommend(R.RecommendRequest(space_type="住宅", budget_tier="mid"))
    picked = rs.options[0].style_id
    with tempfile.TemporaryDirectory() as td:
        payload = rs.lock(picked, out_dir=td, revision=3, by="业主")
        assert payload["locked_style"] == picked
        assert payload["revision"] == 3
        assert payload["locked_by"] == "业主"
        assert Path(rs.lock_file).exists()
        assert "几何" in payload["note"]


def test_lock_refuses_a_style_that_was_not_offered():
    rs = R.recommend(R.RecommendRequest(space_type="住宅"))
    with tempfile.TemporaryDirectory() as td:
        try:
            rs.lock("no-such-style", out_dir=td)
        except KeyError:
            pass
        except ValueError:
            pass
        else:                                                    # pragma: no cover
            raise AssertionError("未在候选内的风格应被拒绝锁定")


def test_recommendation_renders_a_readable_comparison():
    rs = R.recommend(R.RecommendRequest(space_type="住宅", area_m2=120,
                                        budget_tier="mid", location="上海"))
    text = rs.render()
    assert "三套方案对比" in text
    for o in rs.options:
        assert o.style_id in text or o.style_label in text
    assert "请指定其中一套" in text


# --------------------------------------------------------------------------
# Compiler
# --------------------------------------------------------------------------
def _brief(space: str = "客厅", **kw) -> K.SpaceBrief:
    base = dict(space_name=space, width_mm=4200, depth_mm=6000, ceiling_mm=2800,
                orientation="南向，主采光面 3.6m 落地窗")
    base.update(kw)
    return K.SpaceBrief(**base)


def test_all_eight_targets_compile():
    for t in PROMPT_TARGETS:
        p = K.compile_prompt(["italian-minimal"], _brief(), target=t, catalogue=CAT)
        assert p.target == t
        assert p.positive_zh.strip() and p.positive_en.strip()


def test_prompt_is_bilingual_and_layered():
    p = K.compile_prompt(["italian-minimal"], _brief(), catalogue=CAT)
    for marker in ("【风格】", "【材质】", "【光线】", "【家具】", "【机位】", "【氛围】"):
        assert marker in p.positive_zh, marker
    for marker in ("[style]", "[materials]", "[light]", "[furniture]", "[camera]"):
        assert marker in p.positive_en, marker


def test_geometry_from_the_model_is_carried_into_the_prompt():
    p = K.compile_prompt(["italian-minimal"], _brief(), catalogue=CAT)
    assert "4200" in p.positive_zh and "6000" in p.positive_zh
    assert "2800" in p.positive_zh
    assert "不得改动" in p.positive_zh
    assert "do not alter" in p.positive_en


def test_consistency_key_is_stable_and_sensitive():
    a = K.compile_prompt(["italian-minimal"], _brief(), catalogue=CAT)
    b = K.compile_prompt(["italian-minimal"], _brief(), catalogue=CAT)
    assert a.consistency_key == b.consistency_key, "同参数必须得到同一指纹"
    c = K.compile_prompt(["italian-minimal"], _brief(), catalogue=CAT, revision=2)
    assert c.consistency_key != a.consistency_key, "换修订号必须换指纹"
    d = K.compile_prompt(["scandinavian"], _brief(), catalogue=CAT)
    assert d.consistency_key != a.consistency_key, "换风格必须换指纹"


def test_geometry_preservation_rules_are_always_present():
    p = K.compile_prompt(["italian-minimal"], _brief(), catalogue=CAT)
    assert len(p.geometry_rules) >= 3
    joined = " ".join(p.geometry_rules)
    assert "墙体" in joined and "门窗" in joined


def test_partial_renovation_forces_a_hard_constraint():
    p = K.compile_prompt(
        ["italian-minimal"],
        _brief(existing_elements=["原承重墙", "原窗洞 1800×1500"],
               to_change=["电视背景墙饰面", "地面铺装"]),
        target="partial-renovation", catalogue=CAT)
    assert "局部改造强约束" in p.geometry_rules[0]
    assert "必须原样保留" in p.positive_zh
    assert "只允许改动" in p.positive_zh
    assert "keep exactly as-is" in p.positive_en


def test_partial_renovation_without_a_keep_list_warns():
    p = K.compile_prompt(["italian-minimal"], _brief(), target="partial-renovation",
                         catalogue=CAT)
    assert any("必须原样保留" in w for w in p.warnings)


def test_unlocked_style_is_reported_not_hidden():
    p = K.compile_prompt(["italian-minimal"], _brief(), catalogue=CAT, locked=False)
    assert "未锁定" in p.lock_note
    assert any("尚未在门禁确认" in w for w in p.warnings)
    q = K.compile_prompt(["italian-minimal"], _brief(), catalogue=CAT, locked=True)
    assert "已锁定" in q.lock_note


def test_missing_geometry_produces_an_honest_warning():
    p = K.compile_prompt(["italian-minimal"], K.SpaceBrief(space_name="客厅"),
                         catalogue=CAT)
    assert any("开间" in w or "进深" in w for w in p.warnings)
    assert any("参考图" in w for w in p.warnings)


def test_never_claims_prompt_alone_gives_geometry_consistency():
    p = K.compile_prompt(["italian-minimal"], _brief(), catalogue=CAT)
    assert p.to_dict()["authoritative"] is False
    assert "不承载几何" in p.to_dict()["disclaimer"]
    assert len(p.mandate) >= 4
    joined = " ".join(p.mandate)
    assert "已确认的统一空间模型" in joined
    assert "参考图" in joined


def test_negative_constraints_are_merged_and_deduplicated():
    p = K.compile_prompt(["italian-minimal", "scandinavian"], _brief(), catalogue=CAT)
    assert len(p.negative_zh) == len(set(p.negative_zh))
    assert len(p.negative_en) == len(set(p.negative_en))
    assert len(p.negative_zh) >= 5


def test_blend_states_the_ratio_and_keeps_the_primary_logic():
    p = K.compile_prompt(["modern-minimalism", "italian-minimal"], _brief(),
                         catalogue=CAT)
    assert "混搭（次要）" in p.positive_zh
    assert "不改主风格的空间逻辑" in p.positive_zh
    assert p.structured["style"]["ratio"] == {"modern-minimalism": 1.0}


def test_unknown_target_is_rejected():
    try:
        K.compile_prompt(["italian-minimal"], _brief(), target="hologram",
                         catalogue=CAT)
    except ValueError as exc:
        assert "未知目标类型" in str(exc)
    else:                                                        # pragma: no cover
        raise AssertionError("未知目标必须被拒绝")


def test_multi_view_shares_one_consistency_key():
    views = [_brief("客厅"), _brief("主卧"), _brief("餐厨")]
    rep = K.compile_view_set(["italian-minimal"], views, catalogue=CAT)
    assert rep["view_count"] == 3
    assert rep["consistent"] is True
    assert rep["consistency_key"]
    for p in rep["prompts"]:
        assert p["consistency_key"] == rep["consistency_key"]


def test_multi_view_detects_an_inconsistent_set():
    """Different revisions are different identities — the set must not be merged."""
    views = [_brief("客厅"), _brief("主卧")]
    a = K.compile_prompt(["italian-minimal"], views[0], catalogue=CAT, revision=1)
    b = K.compile_prompt(["italian-minimal"], views[1], catalogue=CAT, revision=2)
    assert a.consistency_key != b.consistency_key
    rep = K.compile_view_set(["italian-minimal"], views, catalogue=CAT, revision=1)
    assert rep["consistent"] is True, "同修订同风格必须一致，房间不同不影响指纹"


def test_rooms_share_the_key_but_keep_their_own_geometry():
    views = [_brief("客厅"), _brief("主卧", width_mm=3600, depth_mm=4200)]
    rep = K.compile_view_set(["italian-minimal"], views, catalogue=CAT)
    assert rep["consistent"] is True
    assert len({p["structured"]["space"]["width_mm"] for p in rep["prompts"]}) == 2
    for p in rep["prompts"]:
        assert p["structured"]["consistency"]["view"]["space"]


def test_prompt_markdown_contains_the_verification_checklist():
    p = K.compile_prompt(["italian-minimal"], _brief(), catalogue=CAT)
    md = p.to_markdown()
    assert "产出后必须做的校核" in md
    assert "[ ]" in md
    assert "提示词**不承载几何**" in md


# --------------------------------------------------------------------------
# Provider bridge — the safe-exit path
# --------------------------------------------------------------------------
def test_probe_reports_not_configured_without_a_contract():
    st = P.probe()
    assert st.state in (P.STATUS_NOT_CONFIGURED, P.STATUS_CONNECTED)
    if not st.usable:
        assert st.missing, "未配置时必须说清缺什么"


def test_probe_never_invents_an_endpoint():
    st = P.probe()
    if not st.usable:
        assert st.base_url == ""


def test_submit_defers_instead_of_faking_success():
    p = K.compile_prompt(["italian-minimal"], _brief(), catalogue=CAT)
    with tempfile.TemporaryDirectory() as td:
        rep = P.submit([p], out_dir=td, authorize=True)
        assert rep["deferred_count"] == rep["job_count"]
        assert Path(rep["jobs_file"]).exists()
        for j in rep["package"]["jobs"]:
            assert j["status"] == "awaiting_platform"
            assert j["outputs"] == [], "不得写占位图"
            assert j["authoritative"] is False
            assert j["owner_required"] == "omniailab"


def test_submit_without_authorization_also_defers():
    p = K.compile_prompt(["italian-minimal"], _brief(), catalogue=CAT)
    with tempfile.TemporaryDirectory() as td:
        rep = P.submit([p], out_dir=td, authorize=False)
        assert rep["deferred_count"] == 1
        assert "授权" in rep["package"]["jobs"][0]["reason"]


def test_third_party_fallback_is_declared_forbidden():
    p = K.compile_prompt(["italian-minimal"], _brief(), catalogue=CAT)
    with tempfile.TemporaryDirectory() as td:
        rep = P.submit([p], out_dir=td)
        assert rep["package"]["third_party_fallback"] == "forbidden"
        assert rep["package"]["not_implemented_as_fallback"]
        st = P.probe().to_dict()
        assert st["third_party_fallback"] == "forbidden"


def test_no_image_file_is_ever_written_when_the_platform_is_down():
    p = K.compile_prompt(["italian-minimal"], _brief(), catalogue=CAT)
    with tempfile.TemporaryDirectory() as td:
        P.submit([p], out_dir=td)
        produced = {q.suffix.lower() for q in Path(td).rglob("*") if q.is_file()}
        assert produced <= {".json", ".md"}, f"未配置平台时不得产出图像：{produced}"


def test_target_to_scope_mapping_is_declared():
    for t in PROMPT_TARGETS:
        assert t in P.TARGET_SCOPE, t
        assert P.TARGET_SCOPE[t] in P.CREATIVE_SCOPES


def test_not_configured_error_says_what_is_missing():
    err = P.NotConfigured(["base_url"], "补上契约即可")
    assert "base_url" in str(err)
    assert "补上契约即可" in str(err)


def test_candidates_are_narrowed_to_the_actual_space_use():
    """用途要先收窄候选池：否则所有风格同分，按字母序挑出无关风格。

    "教育""医疗""工业"这些用途只有少数风格声明过；不收窄时
    african-contemporary 会因为 style_id 排第一而永远当"稳妥方案"。
    """
    for space in ("教育", "医疗", "工业", "酒店", "景观"):
        rs = R.recommend(R.RecommendRequest(space_type=space, area_m2=20000))
        top = rs.option("safe")
        assert top is not None, space
        entry = CAT.get(top.style_id)
        declared = any(space in str(sp) for sp in entry.applicable_spaces)
        prior = entry.family in R.SPACE_FAMILY_PRIOR.get(space, ())
        assert declared or prior, f"{space} 推了不相干的风格：{top.style_id}"


def test_school_is_not_offered_african_contemporary_as_the_safe_option():
    rs = R.recommend(R.RecommendRequest(space_type="教育", area_m2=20000))
    ids = [o.style_id for o in rs.options]
    assert "african-contemporary" not in ids, ids
    assert "bauhaus" in ids or "biophilic" in ids, ids
