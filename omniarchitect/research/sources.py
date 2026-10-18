"""Where professional references come from, and what each source may be used for.

The previous version of this registry only knew one entry (the Luxora AI
library). That is enough to say "go look" and not enough to run a real case
study, because a designer needs to know *which* site answers *which* question:
a housing case is not a material library, and a material library cannot tell
you how a courtyard drains.

So each source is registered with:

``kind``     architecture / interior / landscape / material / visual / code
``use``      what question it can answer, in one sentence
``access``   how this machine actually reached it (measured, not guessed)
``search``   whether a script can list items from it, or only a human can
``image``    whether its images may be embedded in a deliverable

The last field is the one that keeps us honest. Almost nothing here may be
embedded: the default is ``link_only``, meaning we hand the client a link and a
finding, never a copied image.

``access`` values were measured on 2026-10-18 from this machine with a real
browser User-Agent. ``403`` is recorded as ``blocked`` and not as ``dead``,
because a site that refuses robots is still a site a human can read.

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from ..paths import REFERENCE_LIBRARY_URL

# --------------------------------------------------------------------------
# enums
# --------------------------------------------------------------------------
KIND_ORDER: Tuple[str, ...] = (
    "architecture",
    "interior",
    "landscape",
    "material",
    "visual",
)

KIND_LABEL: Dict[str, str] = {
    "architecture": "建筑",
    "interior": "室内",
    "landscape": "景观",
    "material": "材料与模型",
    "visual": "视觉灵感",
}

#: Measured reachability. ``blocked`` means the host answered but refused the
#: request; it is not the same as unreachable.
ACCESS_STATES: Tuple[str, ...] = (
    "direct",
    "browser",
    "proxy",
    "blocked",
    "http_only",
    "registered",
    "client_rendered",
    "unreachable",
)

ACCESS_LABEL: Dict[str, str] = {
    "direct": "直连可达",
    "browser": "直连可达（需浏览器 UA）",
    "proxy": "需代理",
    "blocked": "反爬拦截，人工可读",
    "http_only": "仅 http 可达",
    "registered": "注册制，脚本不可核验",
    "client_rendered": "客户端渲染，正文不可脚本读取",
    "unreachable": "当前不可达",
}

#: Whether a script can list items, or only a person can browse.
SEARCH_MODES: Tuple[str, ...] = ("scriptable", "human_only", "none")

SEARCH_LABEL: Dict[str, str] = {
    "scriptable": "可脚本列项",
    "human_only": "仅人工浏览",
    "none": "无检索",
}

#: Whether a source's imagery may enter a deliverable. ``link_only`` is the
#: default and the only safe assumption for third-party case photography.
IMAGE_RIGHTS: Tuple[str, ...] = ("link_only", "embeddable", "own")

IMAGE_RIGHTS_LABEL: Dict[str, str] = {
    "link_only": "只给链接，图不可嵌入交付物",
    "embeddable": "取得授权后可嵌入",
    "own": "自有素材，可直接使用",
}


@dataclass(frozen=True)
class Source:
    """One reference site, with everything needed to use it correctly."""

    id: str
    name: str
    url: str
    kind: str
    use: str
    access: str
    search: str = "human_only"
    image: str = "link_only"
    region: str = "intl"
    note: str = ""

    def to_dict(self) -> Dict[str, str]:
        return {
            "id": self.id,
            "name": self.name,
            "url": self.url,
            "kind": self.kind,
            "kind_label": KIND_LABEL.get(self.kind, self.kind),
            "use": self.use,
            "access": self.access,
            "access_label": ACCESS_LABEL.get(self.access, self.access),
            "search": self.search,
            "search_label": SEARCH_LABEL.get(self.search, self.search),
            "image": self.image,
            "image_label": IMAGE_RIGHTS_LABEL.get(self.image, self.image),
            "region": self.region,
            "note": self.note,
        }


# --------------------------------------------------------------------------
# the registry
# --------------------------------------------------------------------------
#: The first-party library. It is not one more entry in the list — it is the
#: default destination, and `recommend()` puts it first for every query.
FIRST_PARTY: Source = Source(
    id="luxora",
    name="Luxora AI 参考图素材库",
    url=REFERENCE_LIBRARY_URL,
    kind="visual",
    use="第一优先：按风格与空间感找前沿作品，用于方向调研与视觉语言比对",
    access="client_rendered",
    search="human_only",
    image="link_only",
    region="cn",
    note=("Notion 页面，正文由客户端渲染，脚本读不到条目；"
          "必须由人打开浏览，系统只负责把它排在最前面并给出检索词。"
          "不得因为读不到就假装读到了。"),
)

SOURCES: Tuple[Source, ...] = (
    # --- 建筑 -------------------------------------------------------------
    Source(
        id="archdaily",
        name="ArchDaily",
        url="https://www.archdaily.com",
        kind="architecture",
        use="按类型与关键词找建成案例，字段完整（地点/年份/面积/摄影师），可核实",
        access="direct", search="scriptable",
        note="分类页可脚本列项；详情页有 JSON-LD，标题与描述可取真实值。"
             "站内搜索页是脚本渲染，不可抓，因此检索走分类页而非搜索框。",
    ),
    Source(
        id="archdaily-cn",
        name="ArchDaily 中文",
        url="https://www.archdaily.cn",
        kind="architecture",
        use="同上，中文，便于业主直接阅读",
        access="direct", search="scriptable", region="cn",
    ),
    Source(
        id="gooood",
        name="谷德设计网 gooood",
        url="https://www.gooood.cn",
        kind="architecture",
        use="国内项目密度高，文字说明详细，适合提取设计意图",
        access="direct", search="human_only", region="cn",
        note="分类页依赖前端渲染，脚本取不到列表。",
    ),
    Source(
        id="archiposition",
        name="有方 Position",
        url="https://www.archiposition.com",
        kind="architecture",
        use="高质量项目报道与评论，适合引用观点而非图片",
        access="browser", search="human_only", region="cn",
        note="无浏览器 UA 时返回 403。",
    ),
    Source(
        id="divisare",
        name="Divisare",
        url="https://divisare.com",
        kind="architecture",
        use="图少而精，看体量与立面比例关系",
        access="direct", search="human_only",
    ),
    Source(
        id="dezeen",
        name="Dezeen",
        url="https://www.dezeen.com",
        kind="architecture",
        use="看趋势与新材料用法，不适合当项目细节依据",
        access="browser", search="human_only",
        note="无浏览器 UA 时返回 403。",
    ),
    Source(
        id="architizer",
        name="Architizer",
        url="https://architizer.com",
        kind="architecture",
        use="看获奖项目与事务所作品集",
        access="blocked", search="human_only",
        note="直连与代理均 403，人工浏览器可读。",
    ),
    Source(
        id="detail",
        name="DETAIL",
        url="https://www.detail.de",
        kind="architecture",
        use="构造与节点深度参考，方案阶段用来判断做法可行性",
        access="browser", search="human_only",
        note="无浏览器 UA 时返回 403。",
    ),
    # --- 室内 -------------------------------------------------------------
    Source(
        id="ciid",
        name="室内设计联盟",
        url="https://www.ciid.com.cn",
        kind="interior",
        use="国内住宅与商业室内项目，施工图语境接近国内做法",
        access="direct", search="human_only", region="cn",
    ),
    Source(
        id="designwire",
        name="设计腕儿",
        url="https://www.designwire.com.cn",
        kind="interior",
        use="高端住宅与酒店室内，看材料与氛围",
        access="unreachable", search="human_only", region="cn",
        note="本次实测 www 与裸域均连接失败（000），域名可能已变更；"
             "登记为当前不可达，不编造其内容。",
    ),
    Source(
        id="yellowtrace",
        name="Yellowtrace",
        url="https://www.yellowtrace.com.au",
        kind="interior",
        use="看色彩与家具搭配的当代做法",
        access="direct", search="human_only",
    ),
    Source(
        id="interiordesign",
        name="Interior Design",
        url="https://www.interiordesign.net",
        kind="interior",
        use="商业与办公室内，看公共空间组织",
        access="direct", search="human_only",
    ),
    Source(
        id="frame",
        name="FRAME",
        url="https://frameweb.com",
        kind="interior",
        use="概念性强的零售与 hospitality 室内",
        access="direct", search="human_only",
    ),
    Source(
        id="officesnapshots",
        name="Office Snapshots",
        url="https://officesnapshots.com",
        kind="interior",
        use="办公空间实景，看工位与公共区比例",
        access="proxy", search="human_only",
        note="直连 403，经本地代理 200。",
    ),
    Source(
        id="hospitalitydesign",
        name="Hospitality Design",
        url="https://hospitalitydesign.com",
        kind="interior",
        use="酒店与餐饮，看客房与公区体验节奏",
        access="blocked", search="human_only",
        note="直连与代理均 403，人工浏览器可读。",
    ),
    # --- 景观 -------------------------------------------------------------
    Source(
        id="landezine",
        name="Landezine",
        url="https://landezine.com",
        kind="landscape",
        use="建成景观项目，看平面组织与植物配置",
        access="direct", search="human_only",
    ),
    Source(
        id="landscape-cn",
        name="景观中国",
        url="http://www.landscape.cn",
        kind="landscape",
        use="国内景观项目与行业信息",
        access="http_only", search="human_only", region="cn",
        note="https 不可达，仅 http 可访问；交付链接请用 http 形式。",
    ),
    Source(
        id="wla",
        name="World Landscape Architecture",
        url="https://worldlandscapearchitect.com",
        kind="landscape",
        use="国际竞赛与建成项目，看概念表达",
        access="direct", search="human_only",
    ),
    Source(
        id="asla",
        name="ASLA",
        url="https://www.asla.org",
        kind="landscape",
        use="获奖项目与行业标准口径，可作专业依据线索",
        access="direct", search="human_only",
    ),
    Source(
        id="turenscape",
        name="土人设计",
        url="https://www.turenscape.com",
        kind="landscape",
        use="国内本土景观语汇，看生态与低维护做法",
        access="direct", search="human_only", region="cn",
    ),
    # --- 材料与模型 -------------------------------------------------------
    Source(
        id="architonic",
        name="Architonic",
        url="https://www.architonic.com",
        kind="material",
        use="找具体产品与规格，选材阶段用",
        access="direct", search="human_only",
        note="案例站不等于材料站：这里能查到型号与参数，不能查到空间体验。",
    ),
    Source(
        id="archiproducts",
        name="Archiproducts",
        url="https://www.archiproducts.com",
        kind="material",
        use="同 Architonic，欧洲品牌密度高",
        access="direct", search="human_only",
    ),
    Source(
        id="materialbank",
        name="Material Bank",
        url="https://www.materialbank.com",
        kind="material",
        use="实体样板寄送（北美），需要企业账号",
        access="registered", search="none",
        note="根域 404，重定向到 sample.materialbank.com 仍 404；注册制区域跳转，"
             "脚本无法核验，登记为不可核验而非已可用。",
    ),
    Source(
        id="bimobject",
        name="BIMobject",
        url="https://www.bimobject.com",
        kind="material",
        use="构件级模型与参数，深化阶段用",
        access="blocked", search="human_only",
        note="直连与代理均 403。",
    ),
    Source(
        id="polyhaven",
        name="Poly Haven",
        url="https://polyhaven.com",
        kind="material",
        use="CC0 材质与 HDRI，可直接用于效果图照明环境",
        access="direct", search="scriptable",
        note="CC0 授权，是少数可以直接使用素材文件而不只是给链接的来源。",
    ),
    Source(
        id="ambientcg",
        name="ambientCG",
        url="https://ambientcg.com",
        kind="material",
        use="CC0 材质贴图，可平铺，适合渲染",
        access="direct", search="scriptable",
        note="CC0 授权。",
    ),
    Source(
        id="justeasy",
        name="建E网",
        url="https://www.justeasy.cn",
        kind="material",
        use="国内素材与模型库，注意授权条款",
        access="direct", search="human_only", region="cn",
        note="多数资源需会员授权，未经授权不得进交付物。",
    ),
    # --- 视觉灵感 ---------------------------------------------------------
    Source(
        id="behance",
        name="Behance",
        url="https://www.behance.net",
        kind="visual",
        use="看整体呈现与版面风格",
        access="proxy", search="human_only",
        note="直连不可达，经代理 403，需登录且人工浏览；不可脚本抓取。",
    ),
    Source(
        id="pinterest",
        name="Pinterest",
        url="https://www.pinterest.com",
        kind="visual",
        use="快速看风格聚类，来源常不可追溯，只作启发",
        access="proxy", search="human_only",
        note="直连不可达，经代理 200。图片几乎都无法追溯原作者，"
             "因此只能作私人启发，不得作为案例引用。",
    ),
    Source(
        id="huaban",
        name="花瓣",
        url="https://huaban.com",
        kind="visual",
        use="国内风格聚类，同样存在来源不可追溯问题",
        access="direct", search="human_only", region="cn",
    ),
    Source(
        id="zcool",
        name="站酷",
        url="https://www.zcool.com.cn",
        kind="visual",
        use="看表现技法与版面，非建成项目",
        access="direct", search="human_only", region="cn",
    ),
)

SOURCE_INDEX: Dict[str, Source] = {s.id: s for s in SOURCES}


# --------------------------------------------------------------------------
# queries
# --------------------------------------------------------------------------
def for_kind(kind: str) -> List[Source]:
    """Every source registered for one kind, in registry order."""
    return [s for s in SOURCES if s.kind == kind]


def usable(kind: str) -> List[Source]:
    """Sources a script can actually reach, best first.

    ``blocked`` and ``registered`` sources are excluded on purpose: a case list
    built on a site we could not read would be invented data wearing a URL.
    """
    ok = {"direct", "browser", "proxy", "http_only", "client_rendered"}
    return [s for s in for_kind(kind) if s.access in ok]


def case_sources(kind: str) -> List[Source]:
    """Sources that can supply *cases* (not materials, not mood).

    Material libraries answer "which tile", visual boards answer "what feels
    right", and neither can answer "what did someone build and how".
    """
    if kind == "material":
        return [s for s in for_kind("material") if s.access in
                ("direct", "browser", "proxy", "http_only")]
    if kind == "visual":
        return [s for s in for_kind("visual") if s.access in
                ("direct", "browser", "proxy")]
    return [s for s in for_kind(kind) if s.access in
            ("direct", "browser", "proxy", "http_only")]


def recommend(kinds: Optional[List[str]] = None) -> List[Dict[str, str]]:
    """Ordered recommendation for a project.

    The first-party library is always first — not because it is the most
    complete, but because it is ours and it is the one we are accountable for.
    """
    kinds = kinds or list(KIND_ORDER)
    out: List[Dict[str, str]] = [{**FIRST_PARTY.to_dict(), "rank": "1", "why": "第一优先"}]
    seen = {FIRST_PARTY.id}
    for kind in KIND_ORDER:
        if kind not in kinds:
            continue
        for s in case_sources(kind):
            if s.id in seen:
                continue
            seen.add(s.id)
            out.append(s.to_dict())
    return out


def registry_markdown() -> str:
    """The source table used by docs and by the CLI."""
    lines: List[str] = []
    lines.append("## 一、第一优先入口")
    lines.append("")
    lines.append("| 入口 | 用途 | 可达性 | 检索 | 图片权利 |")
    lines.append("|---|---|---|---|---|")
    d = FIRST_PARTY.to_dict()
    lines.append("| [{name}]({url}) | {use} | {access_label} | {search_label} | "
                 "{image_label} |".format(**d))
    lines.append("")
    lines.append("地址唯一来源是 `omniarchitect/paths.py` 的 `REFERENCE_LIBRARY_URL`。")
    lines.append("")
    for kind in KIND_ORDER:
        rows = [s.to_dict() for s in for_kind(kind)]
        if not rows:
            continue
        lines.append("## {}".format(KIND_LABEL[kind]))
        lines.append("")
        lines.append("| 来源 | 能回答什么 | 可达性 | 检索 | 图片权利 |")
        lines.append("|---|---|---|---|---|")
        for r in rows:
            lines.append("| [{name}]({url}) | {use} | {access_label} | {search_label} | "
                         "{image_label} |".format(**r))
        lines.append("")
        notes = [(r["name"], r["note"]) for r in rows if r.get("note")]
        if notes:
            lines.append("**实测备注**")
            lines.append("")
            for name, note in notes:
                lines.append("- {}：{}".format(name, note))
            lines.append("")
    return "\n".join(lines)


def as_list() -> List[Dict[str, str]]:
    """All sources with labels attached, stable order."""
    return [s.to_dict() for s in SOURCES]


__all__ = [
    "ACCESS_LABEL", "ACCESS_STATES", "FIRST_PARTY", "IMAGE_RIGHTS",
    "IMAGE_RIGHTS_LABEL", "KIND_LABEL", "KIND_ORDER", "SEARCH_LABEL",
    "SEARCH_MODES", "SOURCES", "SOURCE_INDEX", "Source", "as_list",
    "case_sources", "for_kind", "recommend", "registry_markdown", "usable",
]
