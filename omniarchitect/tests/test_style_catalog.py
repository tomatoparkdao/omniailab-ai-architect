"""Catalog, schema and search tests.

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from omniarchitect.style import catalog as C  # noqa: E402
from omniarchitect.style import validation as S  # noqa: E402
from omniarchitect.style.resources import style_files  # noqa: E402

REQUIRED_FIELDS = (
    "style_id", "display_name_zh", "display_name_en", "history_and_context",
    "spatial_principles", "proportion_and_geometry", "color_palette", "materials",
    "furniture_language", "lighting_strategy", "architectural_elements",
    "applicable_spaces", "budget_considerations", "construction_considerations",
    "compatible_styles", "incompatible_elements", "positive_prompt_components",
    "geometry_preservation_rules", "negative_constraints", "quality_checklist",
)


def test_catalogue_has_at_least_forty_styles():
    cat = C.load_catalog()
    assert len(cat) >= 40, f"风格目录只有 {len(cat)} 条，第一版要求不少于 40 种"


def test_every_style_file_validates_against_the_schema():
    bad = S.check_style_dir()
    assert not bad, bad


def test_every_style_carries_all_twenty_required_fields():
    missing = {}
    for p in style_files():
        data = json.loads(p.read_text(encoding="utf-8"))
        gaps = [k for k in REQUIRED_FIELDS if k not in data]
        if gaps:
            missing[p.name] = gaps
    assert not missing, missing


def test_style_id_matches_filename_and_is_kebab_case():
    import re
    for p in style_files():
        data = json.loads(p.read_text(encoding="utf-8"))
        assert data["style_id"] == p.stem, f"{p.name} 的 style_id 与文件名不一致"
        assert re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", data["style_id"]), data["style_id"]


def test_compatible_styles_only_point_at_real_styles():
    cat = C.load_catalog()
    known = set(cat.ids)
    dangling = {}
    for sid in cat.ids:
        style = cat.load_style(sid)
        bad = [c for c in style.get("compatible_styles", []) if c not in known]
        if bad:
            dangling[sid] = bad
    assert not dangling, dangling


def test_all_eight_families_are_populated():
    cat = C.load_catalog()
    families = cat.families
    wanted = {"modern", "oriental", "classic", "deco-retro", "industrial",
              "natural-organic", "regional", "experimental"}
    assert wanted.issubset(set(families)), f"缺少族：{wanted - set(families)}"
    for fam in wanted:
        assert len(families[fam]) >= 4, f"{fam} 只有 {len(families[fam])} 条，覆盖不足"


def test_search_by_tag_returns_matches_only():
    cat = C.load_catalog()
    hits = cat.search(tags=["minimal"])
    assert hits, "至少应有一个 minimal 标签的风格"
    for e in hits:
        assert "minimal" in [t.lower() for t in e.tags], e.style_id


def test_search_with_match_all_tags_is_stricter_than_any():
    cat = C.load_catalog()
    any_hits = cat.search(tags=["minimal", "warm"])
    all_hits = cat.search(tags=["minimal", "warm"], match_all_tags=True)
    assert len(all_hits) <= len(any_hits)
    for e in all_hits:
        low = [t.lower() for t in e.tags]
        assert "minimal" in low and "warm" in low


def test_search_by_stage_and_budget_and_space():
    cat = C.load_catalog()
    s2 = cat.search(stage="S2")
    assert s2 and all("S2" in e.stages for e in s2)
    luxury = cat.search(budget_tier="luxury")
    assert luxury and all(e.budget_tier == "luxury" for e in luxury)
    homes = cat.search(space="住宅")
    assert homes, "应有适用于住宅的风格"
    for e in homes:
        assert any("住宅" in s for s in e.applicable_spaces), e.style_id


def test_catalog_loads_records_on_demand_not_up_front():
    """The index must not carry whole records — that is the memory discipline."""
    cat = C.load_catalog()
    entry = cat.get("italian-minimal")
    assert not isinstance(entry, dict)
    style = cat.load_style("italian-minimal")
    assert isinstance(style, dict) and "materials" in style
    # Second call comes from the per-process cache, not from disk again.
    assert cat.load_style("italian-minimal") is style


def test_catalog_index_has_no_full_records():
    data = json.loads((C.CATALOG_FILE).read_text(encoding="utf-8"))
    for row in data["styles"]:
        assert "materials" not in row and "color_palette" not in row, \
            "索引里不应有完整风格内容"


def test_unknown_style_raises_with_a_helpful_message():
    cat = C.load_catalog()
    try:
        cat.get("no-such-style")
    except KeyError as exc:
        assert "可用" in str(exc)
    else:                                                        # pragma: no cover
        raise AssertionError("未知风格必须抛 KeyError")


def test_schema_validator_catches_a_missing_field():
    cat = C.load_catalog()
    style = dict(cat.load_style("italian-minimal"))
    style.pop("lighting_strategy")
    problems = S.validate_style(style)
    assert any("lighting_strategy" in p for p in problems), problems


def test_schema_validator_catches_an_invented_field():
    cat = C.load_catalog()
    style = dict(cat.load_style("italian-minimal"))
    style["brand_new_field"] = "x"
    problems = S.validate_style(style)
    assert any("brand_new_field" in p for p in problems), problems


def test_schema_validator_catches_a_bad_hex_colour():
    cat = C.load_catalog()
    style = json.loads(json.dumps(cat.load_style("italian-minimal")))
    style["color_palette"][0]["hex"] = "not-a-colour"
    problems = S.validate_style(style)
    assert any("hex" in p for p in problems), problems


def test_no_style_record_contains_an_external_url():
    offenders = []
    for p in style_files():
        if "http" in p.read_text(encoding="utf-8"):
            offenders.append(p.name)
    assert not offenders, f"风格数据里不得出现外部链接：{offenders}"


def test_no_style_prompt_mentions_a_model_or_platform_name():
    banned = ("midjourney", "leonardo", "krea", "higgsfield", "runway", "pika",
              "sora", "stable diffusion", "dall-e", "firefly", "kling", "jimeng")
    offenders = []
    for p in style_files():
        blob = p.read_text(encoding="utf-8").lower()
        for b in banned:
            if b in blob:
                offenders.append(f"{p.name}: {b}")
    assert not offenders, offenders
