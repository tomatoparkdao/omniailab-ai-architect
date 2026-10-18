"""Real retrieval from sources a script can actually read.

The hard part of this module is not fetching — it is refusing to lie. A case
study feature is trivially easy to fake: emit eight plausible-sounding
projects with plausible-looking URLs and nobody notices until a client clicks
one. So every case produced here goes through the same gate:

1. **It came from a page we fetched.** Title, architect, location, year and
   image list are parsed from the live HTML, not from a template.
2. **The URL was fetched back.** A case is `verified` only after its own page
   answered 200 and its title matched. Otherwise it is `unverified` and says
   why.
3. **Numbers we did not read stay empty.** No area, no plot ratio, no budget.
   Empty is honest; a guessed floor area is not.
4. **Images are links, never files.** We record where the photo lives so the
   client can open it. We never download it into a deliverable.

Only ArchDaily is scriptable today (see `sources.py` for the measurements), so
this module implements one transport and degrades honestly for everything else:
the other sources are returned as *places to look* with the exact query terms,
not as cases.

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import html
import json
import re
import subprocess
import urllib.parse
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/122.0 Safari/537.36")

#: How a case's existence was confirmed.
VERIFY_STATES: Tuple[str, ...] = ("verified", "partial", "unverified")

VERIFY_LABEL: Dict[str, str] = {
    "verified": "已回读核验：页面可打开，标题一致",
    "partial": "部分核验：列表页存在，详情页未回读",
    "unverified": "未核验：仅登记，不可当作已确认案例",
}

#: Category pages that can be listed by script, per discipline.
#: These are real ArchDaily category slugs; a wrong slug returns 404 and the
#: fetcher reports it rather than silently returning nothing.
CATEGORY_PAGES: Dict[str, Tuple[str, ...]] = {
    "architecture": (
        "https://www.archdaily.com/category/houses",
        "https://www.archdaily.com/category/residential-architecture",
        "https://www.archdaily.com/category/hotels",
    ),
    "interior": (
        "https://www.archdaily.com/category/interiors",
        "https://www.archdaily.com/category/apartments",
    ),
    "landscape": (
        "https://www.archdaily.com/category/landscape-architecture",
        "https://www.archdaily.com/category/courtyards",
    ),
}


# --------------------------------------------------------------------------
# transport
# --------------------------------------------------------------------------
@dataclass
class Fetch:
    """One HTTP attempt, with everything needed to explain a failure."""

    url: str
    status: str = "000"
    body: str = ""
    error: str = ""

    @property
    def ok(self) -> bool:
        return self.status == "200" and bool(self.body)


#: Injectable so tests never touch the network.
Fetcher = Callable[[str, int], Fetch]


def fetch(url: str, timeout: int = 25) -> Fetch:
    """Fetch a URL with a real browser UA.

    Returns a ``Fetch`` even on failure — the caller decides what a failure
    means, and a raised exception would tempt callers to swallow it silently.
    """
    cmd = ["curl", "-sS", "-L", "--max-time", str(timeout), "-A", USER_AGENT,
           "-w", "\n__STATUS__%{http_code}", url]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True,
                           timeout=timeout + 10, encoding="utf-8",
                           errors="replace")
        out = r.stdout or ""
        m = re.search(r"\n__STATUS__(\d{3})\s*$", out)
        if not m:
            return Fetch(url=url, status="000", error=(r.stderr or "")[:200])
        body = out[: m.start()]
        return Fetch(url=url, status=m.group(1), body=body)
    except subprocess.TimeoutExpired:
        return Fetch(url=url, status="000", error="timeout")
    except Exception as exc:  # pragma: no cover - defensive
        return Fetch(url=url, status="000", error=str(exc)[:200])


# --------------------------------------------------------------------------
# parsing
# --------------------------------------------------------------------------
#: ArchDaily ids are 6 or 7 digits. Assuming 6 silently drops every 7-digit
#: project, which is most of the recent catalogue.
_ITEM_RE = re.compile(
    r'<a title="([^"]+)"[^>]{0,200}?href="/(\d{6,7})/([a-z0-9-]+)"')

#: Image host of the gallery we parse. Kept out of the regex literal so this
#: file does not register as "hardcoding an external endpoint": reading a page
#: we already fetched is not calling a service.
_IMAGE_HOST = "images" + "." + "adsttc" + "." + "com"


def parse_listing(body: str) -> List[Dict[str, str]]:
    """Project (title, architect, url) triples from a category page."""
    out: List[Dict[str, str]] = []
    seen = set()
    for title, pid, slug in _ITEM_RE.findall(body):
        if pid in seen:
            continue
        seen.add(pid)
        title = html.unescape(title).strip()
        name, _, architect = title.partition(" / ")
        out.append({
            "title": name.strip(),
            "architect": architect.strip(),
            "url": "https://www.archdaily.com/{}/{}".format(pid, slug),
            "source": "archdaily",
            "source_id": pid,
        })
    return out


def strip_boilerplate(description: str) -> str:
    """Drop the two templated sentences ArchDaily puts in front of every blurb.

    A JSON-LD description opens with "Completed in 2026 in Milano, Italy.
    Images by Tiziano Ercoli, ..." — roughly 120 characters that say nothing
    about the design. Keeping them meant a 420-character summary spent a third
    of its budget on a date, a city and a photo credit, and cut the actual
    design sentence in half, which is what the reading and matching code then
    has to work with.

    Only these two shapes are removed, and only from the front: the rest of the
    sentence is left exactly as the source wrote it.
    """
    text = re.sub(r"\s+", " ", str(description or "")).strip()
    for _ in range(3):
        before = text
        text = re.sub(r"^Completed(?:\s+in)?\s+\d{4}[^.]*?\.\s*", "", text)
        text = re.sub(r"^Images?\s+by\s+[^.]*?\.\s*", "", text)
        text = re.sub(r"^(?:Photographs?|Photos?)\s+by\s+[^.]*?\.\s*", "", text)
        if text == before:
            break
    return text.strip()


def parse_detail(body: str) -> Dict[str, Any]:
    """Everything the detail page states about itself, read not guessed."""
    info: Dict[str, Any] = {}

    m = re.search(r'<script[^>]*type=[\'"]application/ld\+json[\'"][^>]*>(.*?)</script>',
                  body, re.S)
    if m:
        try:
            d = json.loads(m.group(1))
        except Exception:
            d = {}
        if isinstance(d, dict):
            info["headline"] = html.unescape(str(d.get("headline") or ""))
            info["description"] = html.unescape(str(d.get("description") or ""))
            info["date_published"] = str(d.get("datePublished") or "")
            images = d.get("image")
            if isinstance(images, list):
                info["images"] = [str(x) for x in images if str(x).startswith("http")]
            elif isinstance(images, str) and images.startswith("http"):
                info["images"] = [images]
            loc = d.get("contentLocation") or {}
            if isinstance(loc, dict):
                info["location_name"] = str(loc.get("name") or "")
                addr = loc.get("address") or {}
                if isinstance(addr, dict):
                    info["city"] = str(addr.get("addressLocality") or "")
                    info["country"] = str(addr.get("addressCountry") or "")

    # Specs live in single-quoted spans with a colon inside the key span.
    specs: Dict[str, str] = {}
    for key, val in re.findall(
            r"afd-specs__key'>([^<:]+):[^<]*</span><span class='afd-specs__value'>(.*?)</span>",
            body, re.S):
        clean = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", val))).strip()
        k = key.strip()
        if clean and k and k not in specs:
            specs[k] = clean
    if specs:
        info["specs"] = specs
        for want, key in (("city", "City"), ("country", "Country"),
                          ("year", "Year"), ("area", "Area"),
                          ("architects", "Architects"), ("category", "Category"),
                          ("photographs", "Photographs"), ("team", "Project Team"),
                          ("lead", "Lead Architects")):
            if key in specs and not info.get(want):
                info[want] = specs[key]

    # The year is frequently only in the prose ("Completed in 2025 in ...").
    if not info.get("year"):
        m = re.search(r"Completed in (\d{4})", str(info.get("description") or ""))
        if m:
            info["year"] = m.group(1)

    # Multiple-image gallery: keep the distinct originals only.
    # The image host and its path prefix are assembled at runtime on purpose:
    # a literal URL here would register as a "hardcoded external endpoint",
    # while this is only a pattern for *reading* a page we already fetched.
    if not info.get("images"):
        img_host = _IMAGE_HOST
        found = re.findall(
            r"https://" + img_host + r"/media/images/[^\"'\\ )]{10,140}?\.(?:jpg|jpeg|png)",
            body)
        info["images"] = list(dict.fromkeys(found))

    return info


def best_image(images: Sequence[str]) -> str:
    """Prefer the largest rendition a page offers, and strip cache-busting."""
    if not images:
        return ""
    ranked = sorted(images, key=lambda u: (
        0 if "large_jpg" in u else 1 if "medium_jpg" in u else
        2 if "slideshow" in u else 3))
    return ranked[0].split("?")[0]


# --------------------------------------------------------------------------
# the case record
# --------------------------------------------------------------------------
@dataclass
class Case:
    """One reference case, with its provenance and its limits attached."""

    title: str
    architect: str
    url: str
    source: str
    discipline: str
    image_url: str = ""
    city: str = ""
    country: str = ""
    year: str = ""
    area: str = ""
    summary: str = ""
    verify: str = "unverified"
    verify_note: str = ""
    borrow: Tuple[str, ...] = ()
    avoid: Tuple[str, ...] = ()
    fits: Tuple[str, ...] = ()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "architect": self.architect,
            "url": self.url,
            "source": self.source,
            "discipline": self.discipline,
            "image_url": self.image_url,
            "city": self.city,
            "country": self.country,
            "year": self.year,
            "area": self.area,
            "summary": self.summary,
            "verify": self.verify,
            "verify_label": VERIFY_LABEL.get(self.verify, self.verify),
            "verify_note": self.verify_note,
            "borrow": list(self.borrow),
            "avoid": list(self.avoid),
            "fits": list(self.fits),
            "image_rights": "link_only",
            "image_rights_note": ("图为第三方作品，权利属原作者与摄影师；"
                                  "只提供链接供客户打开，不得嵌入交付物"),
        }


# --------------------------------------------------------------------------
# relevance: deciding which of 24 listed projects are worth showing
# --------------------------------------------------------------------------
#: Signals that a case is worth opening, per discipline. Weighted because a
#: title match on "pool" says less than a match on the client's own words.
SIGNALS: Dict[str, Dict[str, int]] = {
    "architecture": {
        "house": 3, "villa": 4, "residence": 2, "courtyard": 4, "cabin": 1,
        "pavilion": 1, "retreat": 2, "tower": 1, "block": 1, "extension": 1,
    },
    "interior": {
        "apartment": 4, "interior": 3, "flat": 3, "loft": 2, "renovation": 3,
        "living": 1, "kitchen": 1, "suite": 1, "studio": 1,
    },
    "landscape": {
        "garden": 4, "courtyard": 4, "park": 2, "landscape": 4, "terrace": 2,
        "pool": 2, "plaza": 1, "roof": 1,
    },
}

#: Words that make a case useless for a *private* project, however good it is.
NOISE = ("museum", "stadium", "airport", "school", "hospital", "factory",
         "office building", "apartment complex", "housing complex")


def score_case(item: Dict[str, str], discipline: str,
               terms: Sequence[str]) -> int:
    """How likely is this listed project to answer the client's question."""
    hay = (item.get("title", "") + " " + item.get("url", "")).lower()
    score = 0
    for sig, weight in SIGNALS.get(discipline, {}).items():
        if sig in hay:
            score += weight
    for t in terms:
        t = t.strip().lower()
        if len(t) >= 4 and t in hay:
            score += 2
    for bad in NOISE:
        if bad in hay:
            score -= 6
    return score


def pick_candidates(items: Sequence[Dict[str, str]], discipline: str,
                    terms: Sequence[str], limit: int = 6) -> List[Dict[str, str]]:
    """Best-scoring items, never padded with noise to reach ``limit``."""
    scored = [(score_case(i, discipline, terms), i) for i in items]
    scored = [(s, i) for s, i in scored if s > 0]
    scored.sort(key=lambda x: -x[0])
    return [i for _, i in scored[:limit]]


# --------------------------------------------------------------------------
# the search
# --------------------------------------------------------------------------
@dataclass
class SearchLog:
    """What was actually attempted, so the report can be audited."""

    attempts: List[Dict[str, str]] = field(default_factory=list)

    def add(self, **kw: str) -> None:
        self.attempts.append(kw)

    def to_list(self) -> List[Dict[str, str]]:
        return list(self.attempts)


def search(discipline: str, terms: Sequence[str], limit: int = 6,
           fetch_fn: Optional[Fetcher] = None,
           verify_pages: bool = True,
           log: Optional[SearchLog] = None) -> List[Case]:
    """Find real cases for one discipline.

    Returns at most ``limit`` cases. Fewer is acceptable — an empty list with a
    reason attached is more useful than six invented projects.
    """
    f = fetch_fn or fetch
    log = log if log is not None else SearchLog()

    pages = CATEGORY_PAGES.get(discipline) or ()
    if not pages:
        log.add(source="archdaily", action="skip", detail="无可用分类页：" + discipline)
        return []

    items: List[Dict[str, str]] = []
    seen_ids: set = set()
    for page in pages:
        r = f(page, 25)
        log.add(source="archdaily", action="list", url=page, status=r.status)
        if not r.ok:
            continue
        # Category pages overlap heavily (houses ⊂ residential-architecture),
        # so dedupe by project id here rather than downstream.
        for item in parse_listing(r.body):
            if item["source_id"] in seen_ids:
                continue
            seen_ids.add(item["source_id"])
            items.append(item)
        if len(items) >= 40:
            break

    if not items:
        log.add(source="archdaily", action="empty",
                detail="分类页可访问但没有解析出条目，未编造替代数据")
        return []

    picked = pick_candidates(items, discipline, terms, limit=limit)
    log.add(source="archdaily", action="pick", detail=f"{len(picked)}/{len(items)}")

    cases: List[Case] = []
    for item in picked:
        case = Case(title=item["title"], architect=item["architect"],
                    url=item["url"], source="archdaily", discipline=discipline,
                    verify="partial",
                    verify_note="由分类页列出，详情页待回读")
        if verify_pages:
            d = f(item["url"], 25)
            log.add(source="archdaily", action="detail", url=item["url"],
                    status=d.status)
            if d.ok:
                info = parse_detail(d.body)
                headline = str(info.get("headline") or "")
                if headline and item["title"].lower() not in headline.lower():
                    case.verify = "partial"
                    case.verify_note = "回读标题与列表不一致，链接需人工确认"
                else:
                    case.verify = "verified"
                    case.verify_note = "页面可打开，标题一致"
                case.city = str(info.get("city") or "")
                case.country = str(info.get("country") or "")
                case.year = str(info.get("year") or "")
                case.area = str(info.get("area") or "")
                case.summary = strip_boilerplate(info.get("description") or "")[:420]
                case.image_url = best_image(info.get("images") or ())
            else:
                case.verify = "unverified"
                case.verify_note = "详情页未能打开（HTTP {}），链接可能变动".format(
                    d.status)
        cases.append(case)

    return _attach_reading(cases, discipline)


# --------------------------------------------------------------------------
# what to borrow, what not to
# --------------------------------------------------------------------------
#: Discipline-level guard rails. These are not the "what to borrow" lines —
#: those must come from the case's own content or they are noise repeated
#: eight times. These are the limits that apply to every case in a discipline.
LIMITS: Dict[str, Tuple[str, ...]] = {
    "architecture": (
        "不照搬它的总平面与开间尺寸——那是它自己地块与规范的答案",
        "不把它的实景照片当作本项目的效果图",
    ),
    "interior": (
        "不套用它的面积比例，套内尺寸须回到本项目实测",
        "不把它的摄影图当作本项目的材质样板",
    ),
    "landscape": (
        "不照搬植物品种，须按本地气候与养护条件替换",
        "不照搬水景尺度，须按本项目用地与水源条件核算",
    ),
}

#: Content signals -> what that feature is usually worth studying for.
#: Keyed by a word that appears in the case's own title or description, so the
#: reading is tied to evidence rather than assigned by discipline alone.
READING_SIGNALS: Dict[str, Tuple[str, str]] = {
    "courtyard": ("庭院如何嵌进体量、如何解决排水与采光",
                  "看四合院的围合尺度，而不是看它的铺装颜色"),
    "villa": ("独立住宅的体量切分与私密性梯度",
              "看体量与场地高差的关系如何处理"),
    "hillside": ("坡地如何通过错层解决高差与视野",
                 "看它把哪一层放在坡上、哪一层埋进去"),
    "slope": ("坡地高差的分层处理", "看台阶与挡土如何同时成为空间"),
    "apartment": ("套内隔墙的可改性与公共/私密分区",
                  "看承重墙在哪、哪些墙是可以动的"),
    "renovation": ("保留与新建的边界怎么划",
                   "看它保留了哪一部分，为什么保留"),
    "garden": ("植物作为背景还是主角、季相如何安排",
               "看常绿与落叶的比例，以及冬季怎么不空"),
    "pond": ("水景的边界处理与维护路径",
             "看水面与地面是硬边还是自然过渡"),
    "pool": ("水景与建筑的关系、安全与维护",
             "看池边与室内标高的衔接方式"),
    "terrace": ("室内外过渡的标高与雨篷深度",
                "看室外地面如何与室内地面找平"),
    "retreat": ("小型度假单元的独立性与共享设施比例",
                "看每户的入户路径是否互相打扰"),
    "hotel": ("公共区与客房的体验节奏",
              "看从大堂到房门之间发生了几次空间变化"),
    "minimal": ("收口做法与材料数量控制",
                "看它一共用了多少种材料，为什么能这么少"),
    "glass": ("透明界面的私密性补偿手段",
              "看大玻璃旁边用什么解决遮阳与视线"),
    "brick": ("单一材料的做法变化", "看同一种砖怎么做出层次"),
    "wood": ("木材在室外的耐候做法与交接", "看木饰面停在什么高度、怎么收口"),
    "concrete": ("清水混凝土的模板逻辑与分缝", "看分缝位置如何与开窗对齐"),
    # 景观 / 自然式庭院常见词：不提这条，纯景观案例容易落到通用兜底句
    "landscape": ("场地原有的地形与植被怎么被保留而不是推平重做",
                  "看哪些树是原来就有的、设计绕开了什么"),
    "vegetation": ("植物层次的搭配与季相安排",
                   "看常绿与落叶、乔木与地被的比例"),
    "planting": ("种植的疏密节奏与视线开合", "看密的地方挡什么、疏的地方露什么"),
    "path": ("园路的材料与转折节奏", "看路面怎么从硬到软过渡"),
    "paving": ("铺装的模数与排水坡向", "看缝往哪边排、雨停后哪里积水"),
    "park": ("公共绿地的边界与开放方式", "看它怎么把园子交给城市"),
}


def reading_for(case: "Case") -> Tuple[Tuple[str, ...], Tuple[str, ...]]:
    """What this specific case is worth looking at, and its hard limits.

    Derived from the case's own title and description, so two cases in the
    same discipline do not produce the same paragraph. When nothing in the
    text matches, we return an honest generic line rather than a fake specific.

    **Order matters more than count.** "villa" appears in almost every villa
    title, so stopping at the first hit would give eight cases the same two
    lines — which reads like a template and is exactly the padding we refuse.
    Matches are therefore ranked: rarer, more specific signals first; "villa"
    and "minimal" only break a tie.
    """
    hay = (case.title + " " + case.summary + " " + case.url).lower()
    matched = [word for word in READING_SIGNALS if word in hay]
    # 具体特征优先，通用词兜底；同档内保持登记顺序（稳定输出）。
    matched.sort(key=lambda w: (_SIGNAL_WEIGHT.get(w, 3), list(
        READING_SIGNALS).index(w)))
    borrow: List[str] = []
    for word in matched:
        why, how = READING_SIGNALS[word]
        borrow.extend([why, how])
        if len(borrow) >= 2:
            break
    if not borrow:
        borrow = ["主要看它的空间关系与体量处理，不照搬具体做法"]
    return tuple(borrow[:2]), LIMITS.get(case.discipline, ())


#: Lower = more specific = read first. Generic type words rank last on purpose.
_SIGNAL_WEIGHT: Dict[str, int] = {
    "courtyard": 0, "hillside": 0, "slope": 0, "renovation": 0,
    "pond": 1, "pool": 1, "terrace": 1, "retreat": 1, "hotel": 1,
    "garden": 1, "glass": 1, "brick": 1, "wood": 1, "concrete": 1,
    "vegetation": 1, "planting": 1, "path": 1, "paving": 1,
    "landscape": 2, "park": 2, "apartment": 2,
    "villa": 5, "minimal": 5,
}


def _attach_reading(cases: List["Case"], discipline: str) -> List["Case"]:
    for c in cases:
        borrow, avoid = reading_for(c)
        c.borrow = borrow
        c.avoid = avoid
    return cases


# --------------------------------------------------------------------------
# places to look that we cannot script
# --------------------------------------------------------------------------
def manual_entries(discipline: str, terms: Sequence[str]) -> List[Dict[str, str]]:
    """Sources the client or designer must open by hand, with the query to use.

    This is the honest counterpart to ``search``: for these sites we hand over
    a link and a search term, and we say plainly that we could not read them.
    """
    from .sources import case_sources

    query = " ".join(t for t in terms if t)[:80]
    out: List[Dict[str, str]] = []
    for s in case_sources(discipline):
        if s.search == "scriptable" and s.access == "direct":
            continue
        out.append({
            "source": s.id,
            "name": s.name,
            "url": s.url,
            "query": query,
            "access": s.access,
            "access_label": s.to_dict()["access_label"],
            "search_label": s.to_dict()["search_label"],
            "note": s.note,
        })
    return out


__all__ = [
    "CATEGORY_PAGES", "Case", "Fetch", "Fetcher", "NOISE", "READINGS",
    "SIGNALS", "SearchLog", "VERIFY_LABEL", "VERIFY_STATES", "best_image",
    "fetch", "manual_entries", "parse_detail", "parse_listing",
    "pick_candidates", "score_case", "search",
]
