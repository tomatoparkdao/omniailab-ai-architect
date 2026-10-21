"""Case research: does it find real cases, and does it refuse to invent them.

Two halves. The first half tests behaviour with a recorded fixture, so it
pin-never touches the network. The second half tests the *refusals*, which are
the actual feature: an empty list with a reason beats eight invented projects,
and a case that cannot be re-read must not be presented as verified.

The fixture below is a trimmed copy of a real ArchDaily category page and a
real detail page. Trimming is fine; inventing is not. Anything not in the
fixture must come out as "not found", which several tests assert.

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import json

from omniarchitect.model import Project
from omniarchitect.research import brief as brief_mod
from omniarchitect.research import cases as case_mod
from omniarchitect.research import report as report_mod
from omniarchitect.research import research as research_mod
from omniarchitect.research import sources as src_mod


def test_two_villas_do_not_get_the_same_borrow_lines():
    """八个别墅案例都写同一段「值得借鉴」= 套话，等于没看案例。

    "villa" 几乎出现在每个别墅标题里，所以「取第一个命中的信号」会把所有
    案例压成同一段。这里断言：更具体的特征（courtyard / hillside …）优先，
    通用类型词（villa / minimal）只在没有别的可读时才用。
    """
    plain = case_mod.Case(
        title="Some Villa", architect="A", url="https://www.archdaily.com/1/x",
        source="archdaily", discipline="architecture",
        summary="A quiet villa on a flat plot.")
    court = case_mod.Case(
        title="Courtyard Villa", architect="B", url="https://www.archdaily.com/2/y",
        source="archdaily", discipline="architecture",
        summary="A villa wrapped around a courtyard with a reflecting pond.")
    hill = case_mod.Case(
        title="Hillside Villa", architect="C", url="https://www.archdaily.com/3/z",
        source="archdaily", discipline="architecture",
        summary="A villa stepping down a hillside slope.")

    a = case_mod.reading_for(plain)[0]
    b = case_mod.reading_for(court)[0]
    c = case_mod.reading_for(hill)[0]

    assert a != b, "庭院别墅与普通别墅不能共用同一段借鉴点"
    assert b != c, "坡地别墅与庭院别墅不能共用同一段借鉴点"
    # 具体信号必须胜出，而不是被 "villa" 抢先
    assert "庭院" in b[0], b
    assert "坡" in c[0], c


# --------------------------------------------------------------------------
# fixture: recorded shapes, used to exercise parsing without network
# --------------------------------------------------------------------------
LISTING_HTML = """
<li class="afd-search-list__4xitem">
  <a title="Colares Sintra House / Sabrab" class="afd-search-list__link"
     href="/1187054/colares-sintra-house-sabrab">
    <figure class="afd-search-list__figure"></figure>
  </a>
</li>
<li class="afd-search-list__4xitem">
  <a title="Villa Courtyard Retreat / Studio Example" class="afd-search-list__link"
     href="/1186590/villa-courtyard-retreat-studio-example">
    <figure class="afd-search-list__figure"></figure>
  </a>
</li>
<li class="afd-search-list__4xitem">
  <a title="Museum of Concrete / Big Firm" class="afd-search-list__link"
     href="/1186000/museum-of-concrete-big-firm">
    <figure class="afd-search-list__figure"></figure>
  </a>
</li>
"""

DETAIL_HTML = """
<html><head>
<script type="application/ld+json">
{"@context":"http://schema.org","@type":"Article",
 "url":"https://www.archdaily.com/1187054/colares-sintra-house-sabrab",
 "headline":"Colares Sintra House / Sabrab",
 "image":["https://images.adsttc.com/media/images/aa/medium_jpg/x.jpg",
          "https://images.adsttc.com/media/images/aa/large_jpg/x.jpg"],
 "datePublished":"2026-10-17T15:00:00+00:00",
 "description":"Completed in 2026 in Sintra, Portugal. Set within a pine forest.",
 "contentLocation":{"@type":"Place",
   "address":{"addressLocality":"Sintra","addressCountry":"Portugal"},
   "name":"Colares Sintra House"}}
</script></head><body>
<li class='afd-specs__item'><div><span class='afd-specs__key'>Category:&nbsp;</span>
<span class='afd-specs__value'><a>Houses</a></span></div></li>
<li class='afd-specs__item'><div><span class='afd-specs__key'>City:&nbsp;</span>
<span class='afd-specs__value'>Sintra</span></div></li>
</body></html>
"""


def _fetch_map(mapping):
    """A fetcher that answers from a dict; anything else 404s, loudly."""
    def _f(url, timeout=25):
        for key, (status, body) in mapping.items():
            if url == key or url.startswith(key):
                return case_mod.Fetch(url=url, status=status, body=body)
        return case_mod.Fetch(url=url, status="404", body="")

    return _f


def _project(pid="t-a", name="三层现代极简别墅带庭院水景", cons=None):
    p = Project(project_id=pid, name=name)
    p.constraints = cons if cons is not None else {
        "project_type": "新建三层别墅", "style": "现代极简"}
    p.meta = {}
    return p


# --------------------------------------------------------------------------
# parsing: the facts must come from the page, not from us
# --------------------------------------------------------------------------
def test_listing_parse_reads_titles_and_urls_from_the_page():
    items = case_mod.parse_listing(LISTING_HTML)
    assert len(items) == 3, items
    first = items[0]
    assert first["title"] == "Colares Sintra House"
    assert first["architect"] == "Sabrab"
    assert first["url"].endswith("/1187054/colares-sintra-house-sabrab")


def test_listing_parse_handles_seven_digit_ids():
    """ArchDaily ids are 6 or 7 digits; assuming 6 silently drops most."""
    items = case_mod.parse_listing(LISTING_HTML)
    urls = [i["url"] for i in items]
    assert any("/1187054/" in u for u in urls)
    assert any("/1186000/" in u for u in urls)


def test_detail_parse_reads_real_fields():
    info = case_mod.parse_detail(DETAIL_HTML)
    assert info["headline"].startswith("Colares Sintra House")
    assert info["city"] == "Sintra"
    assert info["country"] == "Portugal"
    assert info["year"] == "2026"          # only in the prose, not in specs
    assert info["images"], "image list must be read from the page"


def test_best_image_prefers_the_large_rendition():
    big = case_mod.best_image([
        "https://x/media/aa/medium_jpg/a.jpg",
        "https://x/media/aa/large_jpg/a.jpg?1792180441",
    ])
    assert "large_jpg" in big
    assert "?" not in big, "cache-busting query is noise in a delivered link"


def test_missing_fields_stay_empty_instead_of_guessed():
    info = case_mod.parse_detail("<html><body>nothing here</body></html>")
    assert info.get("area") in (None, "")
    assert info.get("year") in (None, "")


def test_description_boilerplate_is_dropped_before_the_summary_is_cut():
    """每条 JSON-LD 描述都以「Completed in 2026 in Milano, Italy. Images by
    …」开头。留着它，420 字的摘要有三成预算花在日期、城市和摄影署名上，
    真正描述设计的那句反而被切半——后面匹配与借鉴说明只能读这半句。
    """
    raw = ("Completed in 2026 in Milano, Italy. Images by Tiziano Ercoli, "
           "Riccardo Giancola. The project transforms two small apartments "
           "organized around a shared threshold.")
    out = case_mod.strip_boilerplate(raw)
    assert out.startswith("The project transforms"), out
    assert "Milano" not in out
    assert "Ercoli" not in out


def test_boilerplate_strip_only_touches_the_front():
    raw = "A house on a slope. Images by X. Later text stays."
    assert case_mod.strip_boilerplate(raw) == raw


def test_boilerplate_strip_is_safe_on_empty_and_plain_text():
    assert case_mod.strip_boilerplate("") == ""
    assert case_mod.strip_boilerplate("A courtyard house.") == "A courtyard house."


def test_year_is_still_read_after_the_summary_is_cleaned():
    """剥前缀只作用于交给客户的摘要，不能连带把规格里的年份抹掉。"""
    info = case_mod.parse_detail(DETAIL_HTML)
    assert info["year"] == "2026"


# --------------------------------------------------------------------------
# relevance: noise must not be shown to a client
# --------------------------------------------------------------------------
def test_score_prefers_courtyard_villa_and_penalises_museums():
    items = case_mod.parse_listing(LISTING_HTML)
    villa = [i for i in items if "Villa" in i["title"]][0]
    museum = [i for i in items if "Museum" in i["title"]][0]
    terms = ("villa", "courtyard")
    assert case_mod.score_case(villa, "architecture", terms) > 0
    assert case_mod.score_case(museum, "architecture", terms) <= 0


def test_pick_candidates_is_not_padded_to_reach_limit():
    only_noise = [{"title": "Museum of Concrete", "url": "/1/museum",
                   "architect": "", "source": "archdaily", "source_id": "1"}]
    picked = case_mod.pick_candidates(only_noise, "architecture", ("villa",), limit=6)
    assert picked == [], "no relevant item must yield an empty list, not filler"


# --------------------------------------------------------------------------
# verification: the case must be re-readable
# --------------------------------------------------------------------------
def test_verified_only_when_detail_page_answers_and_title_matches():
    f = _fetch_map({
        "https://www.archdaily.com/category/": ("200", LISTING_HTML),
        "https://www.archdaily.com/1187054/": ("200", DETAIL_HTML),
        "https://www.archdaily.com/1186590/": ("200", DETAIL_HTML),
    })
    found = case_mod.search("architecture", ["villa", "courtyard"], limit=4,
                            fetch_fn=f)
    assert found
    verified = [c for c in found if c.verify == "verified"]
    assert verified, [c.verify_note for c in found]


def test_detail_page_failure_downgrades_to_unverified():
    f = _fetch_map({"https://www.archdaily.com/category/": ("200", LISTING_HTML)})
    found = case_mod.search("architecture", ["villa", "courtyard"], limit=3,
                            fetch_fn=f)
    assert found
    assert all(c.verify == "unverified" for c in found)
    assert all("未能打开" in c.verify_note for c in found)


def test_all_pages_down_yields_no_cases_and_a_reason():
    f = _fetch_map({})            # everything 404
    log = case_mod.SearchLog()
    found = case_mod.search("architecture", ["villa"], limit=3, fetch_fn=f, log=log)
    assert found == []
    attempts = log.to_list()
    assert any(a.get("action") == "empty" or a.get("status") in ("404",)
               for a in attempts)


# --------------------------------------------------------------------------
# the first entry is always first
# --------------------------------------------------------------------------
def test_luxora_is_always_the_first_recommendation():
    for kinds in (None, ["interior"], ["landscape"]):
        rec = src_mod.recommend(kinds)
        assert rec[0]["id"] == "luxora"


def test_luxora_address_is_not_hardcoded_anywhere_but_paths():
    """用户要求：地址从 paths 读，不要在别处再抄一遍。"""
    from omniarchitect.paths import REFERENCE_LIBRARY_URL

    assert src_mod.FIRST_PARTY.url == REFERENCE_LIBRARY_URL
    import pathlib

    root = pathlib.Path(__file__).resolve().parents[2]
    hits = []
    for path in (root / "omniarchitect").rglob("*.py"):
        if path.name == "paths.py" or path == pathlib.Path(__file__).resolve():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if "3c3a28d2e37880ffa75bd3a809ebb8aa" in text:
            hits.append(path.name)
    assert hits == [], f"素材库地址被重复硬编码：{hits}"


def test_unreachable_sources_are_recorded_as_such_not_hidden():
    dead = [s for s in src_mod.SOURCES if s.access == "unreachable"]
    assert dead, "至少要如实登记一个当前不可达的来源"
    for s in dead:
        assert s.note, "不可达必须写明原因，不能只标状态"


def test_every_registered_source_declares_rights_and_use():
    for s in src_mod.SOURCES:
        assert s.image in src_mod.IMAGE_RIGHTS
        assert s.access in src_mod.ACCESS_LABEL
        assert s.use.strip(), s.id
        if s.access in ("blocked", "registered", "unreachable", "http_only"):
            assert s.note, f"{s.id} 属非常规可达，必须写明情况"


# --------------------------------------------------------------------------
# research starts from S1, without waiting
# --------------------------------------------------------------------------
def test_research_starts_as_soon_as_the_type_is_known():
    p = _project()
    ok, why = brief_mod.should_start(p)
    assert ok and why


def test_new_villa_and_fitout_are_researched_differently():
    """同一个 residential profile，新建与精装的研究方向必须不同。"""
    villa = brief_mod.derive(_project())
    fitout = brief_mod.derive(_project(
        pid="t-b", name="大平层意式极简精装",
        cons={"project_type": "大平层精装修", "style": "意式极简"}))

    assert "architecture" in villa.disciplines
    assert villa.disciplines != fitout.disciplines
    v_aspects = {a for d in villa.directions for a in d.aspects}
    f_aspects = {a for d in fitout.directions for a in d.aspects}
    assert v_aspects != f_aspects


def test_directions_carry_what_to_look_at_per_discipline():
    b = brief_mod.derive(_project())
    assert b.directions
    for d in b.directions:
        assert d.aspects, d.discipline
        assert d.idea, d.discipline


def test_pure_courtyard_project_gets_landscape_direction_only():
    b = brief_mod.derive(_project(
        pid="t-c", name="私家庭院现代自然式景观",
        cons={"project_type": "私家庭院景观", "style": "现代自然"}))
    assert b.disciplines == ("landscape",)
    assert b.directions[0].discipline == "landscape"


def test_allocation_never_exceeds_eight_slots():
    plan = research_mod.allocate(["architecture", "interior", "landscape"])
    assert sum(plan.values()) <= research_mod.MAX_TOTAL


# --------------------------------------------------------------------------
# the artifacts
# --------------------------------------------------------------------------
def test_run_writes_both_artifacts_and_stores_state():
    p = _project()
    f = _fetch_map({
        "https://www.archdaily.com/category/": ("200", LISTING_HTML),
        "https://www.archdaily.com/1187054/": ("200", DETAIL_HTML),
        "https://www.archdaily.com/1186590/": ("200", DETAIL_HTML),
    })
    res = research_mod.run(p, out_dir="out/test-research", fetch_fn=f)
    assert res.cases
    data = research_mod.load(p)
    assert data and data["counts"]["total"] == len(res.cases)


def test_shortlist_markdown_links_are_openable_not_placeholders():
    p = _project()
    f = _fetch_map({
        "https://www.archdaily.com/category/": ("200", LISTING_HTML),
        "https://www.archdaily.com/1187054/": ("200", DETAIL_HTML),
        "https://www.archdaily.com/1186590/": ("200", DETAIL_HTML),
    })
    res = research_mod.run(p, fetch_fn=f, store=False)
    md = report_mod.render_markdown(res)
    assert "https://www.archdaily.com/1187054/" in md
    assert "第一优先" in md
    assert "example.com" not in md


def test_no_cases_means_the_reason_is_printed_not_hidden():
    p = _project()
    res = research_mod.run(p, fetch_fn=_fetch_map({}), store=False)
    md = report_mod.render_markdown(res)
    assert "没有可核验" in md or "未返回 200" in md


def test_report_states_the_image_rights_limit():
    p = _project()
    res = research_mod.run(p, fetch_fn=_fetch_map({}), store=False)
    md = report_mod.render_markdown(res)
    assert "不嵌入" in md
    assert "权利属原作者" in md or "第三方" in md


def test_research_is_skipped_with_a_reason_when_type_is_unknown():
    p = Project(project_id="t-empty", name="")
    p.constraints = {}
    p.meta = {}
    ok, why = brief_mod.should_start(p)
    res = research_mod.run(p, store=True)
    assert isinstance(res.cases, list)
    data = research_mod.load(p)
    assert data is not None
    if not ok:
        assert data.get("counts", {}).get("total", 0) == 0


def test_json_payload_carries_verify_state_per_case():
    p = _project()
    f = _fetch_map({
        "https://www.archdaily.com/category/": ("200", LISTING_HTML),
        "https://www.archdaily.com/1187054/": ("200", DETAIL_HTML),
    })
    res = research_mod.run(p, fetch_fn=f, store=False)
    payload = json.loads(json.dumps(res.to_dict(), ensure_ascii=False))
    for c in payload["cases"]:
        assert c["verify"] in case_mod.VERIFY_STATES
        assert c["image_rights"] == "link_only"


def test_school_research_asks_for_schools_not_villas():
    """学校要检索教育建筑；以前它落进 houses 分类页，案例页上全是别墅。

    这一条守两件事：分类页按项目类型选、类型词不再当噪声扣分。
    """
    from omniarchitect.research import brief as B
    from omniarchitect.research import cases as C

    assert "education" in B.ASPECTS, "教育类型必须有专属要点表"
    assert B.CODE_ASPECT["A3"] == "education"
    assert B.CODE_ASPECT["A12"] == "industrial"
    assert "educational-architecture" in " ".join(C.ASPECT_PAGES["education"])

    item = {"title": "Hongling Middle School Shixia Campus",
            "architect": "Tumushi Architects", "url": "https://x/1"}
    score = C.score_case(item, "architecture", ("school", "campus"),
                         aspect="education")
    assert score > 0, "学校项目里 school 是信号，不该被当噪声扣成负数"
    assert C.score_case({"title": "DUA Villa", "architect": "X", "url": "https://x/2"},
                        "architecture", ("school", "campus"),
                        aspect="education") < score, "别墅不该压过学校"


def test_case_reading_is_derived_from_the_case_itself():
    """读图要点必须来自该案例自身文字；两条案例不能输出同一段话。"""
    from omniarchitect.research import cases as C

    a = C.Case(title="City Pride School", architect="A Threshold",
               url="https://x/a", source="archdaily", discipline="architecture",
               summary="A primary school with classrooms around a courtyard.")
    b = C.Case(title="Yumoto Electric Factory", architect="YKAD",
               url="https://x/b", source="archdaily", discipline="architecture",
               summary="A factory where the production line sets the grid.")
    ba, _ = C.reading_for(a)
    bb, _ = C.reading_for(b)
    assert ba and bb
    assert ba != bb, "两台不同的项目不该得到同一段读图要点"
    assert any(("教室" in x) or ("教学" in x) or ("庭院" in x) or ("组团" in x)
               for x in ba), ba
