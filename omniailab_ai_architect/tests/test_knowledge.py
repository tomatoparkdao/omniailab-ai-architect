"""Original knowledge base: structure, progressive loading, provenance."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from omniailab_ai_architect import knowledge  # noqa: E402


def test_thirteen_domains_are_present_and_valid():
    domains = knowledge.index()
    assert len(domains) == 13, [d.slug for d in domains]
    assert knowledge.validate() == []


def test_domain_metadata_is_complete():
    for d in knowledge.index():
        assert d.stage_affinity, d.slug
        assert all(s in {f"S{i}" for i in range(1, 9)} for s in d.stage_affinity), d.slug
        assert d.load_cost in ("light", "medium", "heavy"), d.slug
        assert d.loads_when, d.slug
        assert d.lines > 60, (d.slug, d.lines)


def test_progressive_loading_is_cheaper_than_full_load():
    outline = knowledge.outline("lighting-design")
    assert len(outline) >= 5
    one = knowledge.section("lighting-design", outline[0])
    full = knowledge.load("lighting-design")
    assert one and len(one.splitlines()) < len(full.splitlines())
    assert outline[0] in one


def test_section_reads_exactly_one_section():
    body = knowledge.section("lighting-design", "数值与区间")
    assert body.startswith("## 数值与区间")
    assert body.count("\n## ") == 0, "section() 只能返回一节"


def test_resolve_prefers_the_matching_domain():
    sel = knowledge.resolve("客厅采光不足，想加灯带洗墙", stage="S4")
    assert "lighting-design" in [d.slug for d in sel.domains]
    sel2 = knowledge.resolve("把厨房和餐厅之间的墙移一下，通道净宽够不够", stage="S3")
    assert {"spatial-planning", "human-ergonomics"} & {d.slug for d in sel2.domains}
    assert sel2.estimate_lines > 0


def test_resolve_falls_back_instead_of_loading_everything():
    sel = knowledge.resolve("zzzz 完全无关的问题 zzzz", stage="S7")
    assert sel.domains, "必须回退到默认领域"
    assert len(sel.domains) <= 3, "回退也不能把 12 个领域全加载"
    assert any("回退" in r for r in sel.reason)


def test_budget_respects_the_line_ceiling():
    picked = knowledge.budget("S4", max_lines=300)
    assert sum(d.lines for d in picked) <= 300
    assert picked


def test_search_is_literal_and_bounded():
    hits = knowledge.search("照度", limit=3)
    assert hits and len(hits) <= 3
    assert all("domain" in h and "line" in h for h in hits)
    assert knowledge.search("") == []


def test_cases_are_generic_and_original():
    cs = knowledge.cases()
    assert len(cs) >= 3
    for c in cs:
        assert str(c.get("source")) == "original", c.get("slug")
        assert c.get("project_type"), c.get("slug")
        assert float(c.get("area_m2") or 0) > 0, c.get("slug")
        assert c.get("review_results"), c.get("slug")


def test_knowledge_is_self_contained_and_carries_the_signature():
    from omniailab_ai_architect.paths import KNOWLEDGE
    from omniailab_ai_architect.registry import SIGNATURE

    for p in KNOWLEDGE.glob("*.md"):
        text = p.read_text(encoding="utf-8")
        assert "http://" not in text and "https://" not in text, \
            f"{p.name} 不应含外部链接"
        assert SIGNATURE in text, f"{p.name} 缺少 OmniAiLab 署名"


def test_report_is_machine_readable():
    rep = knowledge.report()
    assert rep["count"] == 13
    assert rep["total_lines"] > 1200
    assert rep["issues"] == []
    assert set(rep["by_stage"]) == {f"S{i}" for i in range(1, 9)}
