"""Acceptance tests — the six scenarios the brief named explicitly.

Each of these is end-to-end: they drive the public API the way an agent would,
and they assert on the *properties that matter* rather than on strings.

1. three-style recommendation
2. one Italian-Minimal living-room prompt
3. one flat compared across three styles
4. five rooms held consistent under one style
5. a partial renovation that pins walls and openings
6. a safe exit when the OmniAiLab provider is unavailable

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from omniarchitect.style import catalog as C  # noqa: E402
from omniarchitect.style import compiler as K  # noqa: E402
from omniarchitect.style import provider_bridge as P  # noqa: E402
from omniarchitect.style import recommender as R  # noqa: E402
from omniarchitect.style import hooks as W  # noqa: E402

CAT = C.load_catalog()


def _living_room(**kw) -> K.SpaceBrief:
    base = dict(space_name="客厅", width_mm=4200, depth_mm=6000, ceiling_mm=2800,
                orientation="南向，主采光面 3.6m 落地窗",
                openings=["阳台推拉门 2400×2400，南墙偏东"])
    base.update(kw)
    return K.SpaceBrief(**base)


# --------------------------------------------------------------------------
# 1. Three-style recommendation
# --------------------------------------------------------------------------
def test_scenario_1_three_style_recommendation():
    req = R.RecommendRequest(
        space_type="住宅", area_m2=120, budget_tier="mid", location="上海",
        preferences=["简洁", "温暖"], maintenance="low", stage="S2")
    rs = R.recommend(req, catalog=CAT, top_k=3)

    assert len(rs.options) == 3, "必须给出三套方案"

    roles = [o.role for o in rs.options]
    assert roles == ["safe", "distinctive", "hybrid"], roles

    safe, alt = rs.options[0], rs.options[1]
    assert safe.style_id != alt.style_id, "三套里前两套不能是同一个风格"
    assert CAT.get(safe.style_id).family != CAT.get(alt.style_id).family, \
        "对照方案必须来自不同族"

    for o in rs.options:
        assert o.why and o.pros and o.cons, f"{o.style_id} 缺少理由/优点/代价"

    text = rs.render()
    assert "稳妥首选" in text and "个性对照" in text and "混搭方案" in text
    assert "请指定其中一套" in text

    with tempfile.TemporaryDirectory() as td:
        payload = rs.lock(safe.style_id, out_dir=td, revision=1, by="业主")
        assert payload["locked_style"] == safe.style_id
        assert Path(rs.lock_file).exists()


# --------------------------------------------------------------------------
# 2. One Italian-Minimal living-room prompt
# --------------------------------------------------------------------------
def test_scenario_2_italian_minimal_living_room_prompt():
    p = K.compile_prompt(
        ["italian-minimal"], _living_room(),
        target="interior-render", stage="S4", revision=3, catalogue=CAT, locked=True,
        user_needs=["三人布艺沙发，坐深 900", "电视背景墙不做造型，只做整幅石材"],
        reference_note="参考图 = 已确认平面 G3 的确定性栅格化")

    # Bilingual, layered, and specific
    assert p.positive_zh and p.positive_en
    assert "意式极简" in p.positive_zh and "Italian Minimal" in p.positive_en
    for marker in ("【风格】", "【空间", "【材质】", "【光线】", "【家具】", "【机位】"):
        assert marker in p.positive_zh, marker

    # Geometry comes from the model and is declared out of the renderer's hands
    assert "4200" in p.positive_zh and "6000" in p.positive_zh
    assert "2800" in p.positive_zh
    assert "不得改动" in p.positive_zh
    assert any("墙体" in g for g in p.geometry_rules)

    # The client's own words survive into the prompt
    assert "三人布艺沙发" in p.positive_zh

    # Consistency identity and revision travel with the prompt
    assert p.consistency_key.startswith("sp-")
    assert p.revision == 3
    assert p.structured["style"]["primary"]["id"] == "italian-minimal"

    # And it never claims more than a prompt can deliver
    assert p.to_dict()["authoritative"] is False
    assert "不承载几何" in p.to_dict()["disclaimer"]


# --------------------------------------------------------------------------
# 3. One flat compared across three styles
# --------------------------------------------------------------------------
def test_scenario_3_one_flat_three_styles_compared():
    flat = _living_room()
    candidates = ["modern-minimalism", "chinese-neo-classical", "industrial-loft"]

    prompts = {}
    for sid in candidates:
        prompts[sid] = K.compile_prompt([sid], flat, target="concept",
                                        catalogue=CAT, locked=False)
    # Same space, three styles → three different identities, same geometry
    keys = {p.consistency_key for p in prompts.values()}
    assert len(keys) == 3
    for p in prompts.values():
        assert "4200" in p.positive_zh, "同一户型，几何必须一致"

    cmp_data = W.comparison_data(candidates, catalogue=CAT)
    assert cmp_data["count"] == 3
    families = {CAT.get(s).family for s in candidates}
    assert len(families) >= 2, "对比应跨越不同族"

    for row in cmp_data["styles"]:
        assert row["spatial_principles"] and row["materials"] and row["palette"]
        assert row["budget_tier"] and row["budget_drivers"]
        assert row["incompatible"], "每套都要写清与什么冲突"

    # And each style names its own conflicts with the *same* plan
    checks = {s: W.style_space_check(s, flat, catalogue=CAT) for s in candidates}
    assert set(checks) == set(candidates)
    for rep in checks.values():
        assert rep["stage"] == "S3"
        assert isinstance(rep["conflicts"], list)


# --------------------------------------------------------------------------
# 4. Five rooms held consistent under one style
# --------------------------------------------------------------------------
def test_scenario_4_five_rooms_share_one_consistency_constraint():
    rooms = [
        K.SpaceBrief(space_name="客厅", width_mm=4200, depth_mm=6000, ceiling_mm=2800,
                     camera="两点透视，视高 1500"),
        K.SpaceBrief(space_name="餐厅", width_mm=3200, depth_mm=3600, ceiling_mm=2800,
                     camera="两点透视，视高 1500"),
        K.SpaceBrief(space_name="主卧", width_mm=3600, depth_mm=4200, ceiling_mm=2800,
                     camera="两点透视，视高 1400"),
        K.SpaceBrief(space_name="书房", width_mm=2800, depth_mm=3200, ceiling_mm=2800,
                     camera="两点透视，视高 1500"),
        K.SpaceBrief(space_name="厨房", width_mm=2600, depth_mm=3600, ceiling_mm=2800,
                     camera="一点透视，视高 1500"),
    ]
    rep = K.compile_view_set(["italian-minimal"], rooms, target="multi-view",
                             revision=4, catalogue=CAT, locked=True)

    assert rep["view_count"] == 5
    assert rep["consistent"] is True, rep["note"]
    assert rep["consistency_key"].startswith("sp-")

    for p in rep["prompts"]:
        assert p["consistency_key"] == rep["consistency_key"], "五个机位必须共用同一指纹"
        assert p["structured"]["consistency"]["share_across_views"] is True
        # every room carries the same material and lighting language
        assert "瓦" in p["positive"]["zh"] or "岩板" in p["positive"]["zh"] or \
               "木" in p["positive"]["zh"], p["structured"]["space"]["space_name"]

    # Different rooms still describe their own geometry
    widths = {p["structured"]["space"]["width_mm"] for p in rep["prompts"]}
    assert len(widths) == 5


# --------------------------------------------------------------------------
# 5. Partial renovation that pins walls and openings
# --------------------------------------------------------------------------
def test_scenario_5_partial_renovation_pins_walls_and_openings():
    brief = K.SpaceBrief(
        space_name="客厅（局部改造）",
        width_mm=4200, depth_mm=6000, ceiling_mm=2800,
        existing_elements=["南墙推拉门 2400×2400（位置与尺寸不变）",
                           "西侧承重墙（不得开洞）",
                           "原梁位与净高 2800（不得降低）"],
        to_change=["电视背景墙饰面", "地面铺装", "窗帘形式"],
        camera="与现状照片一致的机位",
        references=["out/plan-r3.png", "out/site-photo-camera-a.jpg"],
    )
    p = K.compile_prompt(["italian-minimal"], brief, target="partial-renovation",
                         revision=5, catalogue=CAT, locked=True)

    assert p.geometry_rules[0].startswith("**局部改造强约束**")
    joined_rules = " ".join(p.geometry_rules)
    assert "墙体" in joined_rules and "门窗" in joined_rules

    assert "必须原样保留" in p.positive_zh
    assert "南墙推拉门" in p.positive_zh
    assert "只允许改动" in p.positive_zh
    assert "电视背景墙饰面" in p.positive_zh

    assert "keep exactly as-is" in p.positive_en
    assert "change only" in p.positive_en

    # The prompt must not have invented an escape hatch
    joined_neg = " ".join(p.negative_zh)
    assert "改变墙体或门窗位置" in joined_neg
    assert not any("尚未声明" in w for w in p.warnings), p.warnings


# --------------------------------------------------------------------------
# 6. Safe exit when the provider is unavailable
# --------------------------------------------------------------------------
def test_scenario_6_safe_exit_when_provider_unavailable():
    prompts = [
        K.compile_prompt(["italian-minimal"], _living_room(), target="interior-render",
                         catalogue=CAT, locked=True),
        K.compile_prompt(["italian-minimal"], _living_room(space_name="主卧"),
                         target="interior-render", catalogue=CAT, locked=True),
        K.compile_prompt(["italian-minimal"], _living_room(),
                         target="walkthrough-video", catalogue=CAT, locked=True),
    ]
    with tempfile.TemporaryDirectory() as td:
        rep = P.submit(prompts, out_dir=td, authorize=True)

        # 1) never claims success it does not have
        assert rep["deferred_count"] == rep["job_count"] == 3
        for j in rep["package"]["jobs"]:
            assert j["status"] == "awaiting_platform"
            assert j["outputs"] == []
            assert j["reason"]
            assert j["owner_required"] == "omniailab"

        # 2) no third-party route exists, and that is stated
        assert rep["package"]["third_party_fallback"] == "forbidden"
        assert len(rep["package"]["not_implemented_as_fallback"]) >= 3

        # 3) the job package is complete enough to run later
        job = rep["package"]["jobs"][0]
        assert job["package"]["positive"]["zh"]
        assert job["package"]["positive"]["en"]
        assert job["package"]["geometry_preservation"]
        assert job["package"]["verification_mandate"]
        assert job["consistency_key"]

        # 4) nothing that looks like a generated image was written
        written = sorted(q.name for q in Path(td).rglob("*") if q.is_file())
        assert all(n.endswith((".json", ".md")) for n in written), written
        assert any(n.endswith(".json") for n in written)
        assert any(n.endswith(".md") for n in written)

        # 5) scopes are creative-only, all owned by OmniAiLab
        for j in rep["package"]["jobs"]:
            assert j["scope"] in P.CREATIVE_SCOPES
            assert j["owner_required"] == "omniailab"

        package = json.loads((Path(td) / "style-jobs.json").read_text(encoding="utf-8"))
        assert package["platform_state"] in ("not_configured", "connected")
