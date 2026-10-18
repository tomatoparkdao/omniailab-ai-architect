"""Render the research into the two files a client can actually use.

Two artifacts, deliberately separate:

``reference-shortlist.md``   客户看的：5–8 个案例，每个都有能点开的链接、
                             在哪看、为什么推荐、能借鉴什么、别照搬什么
``reference-shortlist.json`` 下游用的：S2 概念挂接案例时读它，不读 markdown

They are not a second database. The library lives in ``reference-log.md``
(documented in ``docs/REFERENCE_SOURCES.md``) and this is its structured
counterpart for one project revision — same cases, one machine-readable, one
readable by a person who is paying for the building.

The honesty rules are enforced in the rendering, not left to the caller:

- A case with ``verify != verified`` is visibly marked, and the reason is
  printed. A client should never click a link that we have not opened.
- An empty result prints *why* it is empty. "Nothing found" and "we could not
  read that site" are different sentences and must not be merged.
- Third-party images appear as a link plus a one-line caption, never as an
  embedded image, because we have no right to embed them.

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from . import cases as case_mod
from .brief import ResearchBrief
from .sources import FIRST_PARTY, case_sources, registry_markdown

SHORTLIST_MD = "reference-shortlist.md"
SHORTLIST_JSON = "reference-shortlist.json"

#: How many cases to show. Eight is a judgement call: enough to compare
#: approaches, few enough that a client actually opens them.
TARGET_MIN = 5
TARGET_MAX = 8


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class ResearchResult:
    """Everything one research round produced."""

    brief: ResearchBrief
    cases: List[case_mod.Case]
    manual: List[Dict[str, str]]
    log: List[Dict[str, str]]
    project_id: str = ""
    revision: int = 0
    generated_at: str = ""

    @property
    def verified(self) -> List[case_mod.Case]:
        return [c for c in self.cases if c.verify == "verified"]

    def by_discipline(self) -> Dict[str, List[case_mod.Case]]:
        out: Dict[str, List[case_mod.Case]] = {}
        for c in self.cases:
            out.setdefault(c.discipline, []).append(c)
        return out

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_id": self.project_id,
            "revision": self.revision,
            "generated_at": self.generated_at or _now(),
            "first_entry": {
                "name": FIRST_PARTY.name,
                "url": FIRST_PARTY.url,
                "why": "第一优先：自有素材库，方向调研首选",
                "access": FIRST_PARTY.access,
                "access_label": FIRST_PARTY.to_dict()["access_label"],
                "note": FIRST_PARTY.note,
            },
            "brief": self.brief.to_dict(),
            "cases": [c.to_dict() for c in self.cases],
            "counts": {
                "total": len(self.cases),
                "verified": len(self.verified),
                "by_discipline": {k: len(v) for k, v in self.by_discipline().items()},
            },
            "manual_sources": list(self.manual),
            "attempts": list(self.log),
            "note": ("verify=verified 表示详情页已回读且标题一致；"
                     "partial/unverified 必须按未确认处理。"
                     "图片一律只给链接，权利属原作者。"),
        }


# --------------------------------------------------------------------------
# the human-facing file
# --------------------------------------------------------------------------
def _case_block(n: int, c: case_mod.Case) -> List[str]:
    lines: List[str] = []
    where = "，".join(x for x in (c.city, c.country) if x)
    meta = " ｜ ".join(x for x in (where, c.year, c.area and ("面积 " + c.area)) if x)
    lines.append("### {}. {}　／　{}".format(n, c.title, c.architect or "（事务所未标注）"))
    lines.append("")
    if meta:
        lines.append("- **项目信息**：{}".format(meta))
    lines.append("- **案例页面**：<{}>".format(c.url))
    if c.image_url:
        lines.append("- **该案例的实景图（第三方作品，点开看）**：<{}>".format(c.image_url))
        lines.append("  （权利属原作者与摄影师；只给链接，不嵌入本方案）")
    else:
        lines.append("- **实景图**：该页未取到可直接打开的图片链接，请在案例页内查看")
    label = case_mod.VERIFY_LABEL.get(c.verify, c.verify)
    note = (c.verify_note or "").strip()
    # VERIFY_LABEL 已经说清了「页面可打开、标题一致」，再把它括在后面就成了
    # 「已回读核验：页面可打开，标题一致（页面可打开，标题一致）」。只有核验
    # 说明真的多说了什么（比如降级原因）才补括号。
    if note and note != label and note not in label:
        lines.append("- **核验状态**：{}（{}）".format(label, note))
    else:
        lines.append("- **核验状态**：{}".format(label))
    if c.summary:
        lines.append("- **这是什么**：{}".format(c.summary))
    if c.fits:
        lines.append("- **与你的需求相符之处**：{}".format("；".join(c.fits)))
    if c.borrow:
        lines.append("- **值得借鉴的手法**：")
        for b in c.borrow:
            lines.append("  - {}".format(b))
    if c.avoid:
        lines.append("- **不适合直接照搬**：")
        for a in c.avoid:
            lines.append("  - {}".format(a))
    lines.append("")
    return lines


def _empty_reason(disc: str, log: Sequence[Dict[str, str]]) -> str:
    """Why a discipline has nothing to show, in one honest sentence."""
    calls = [a for a in log if a.get("action") in ("list", "detail")]
    bad = [a for a in calls if a.get("status") not in ("200", None)]
    if not calls:
        return "该专业没有可脚本检索的来源，见下方「需要你自己打开的站点」"
    if bad and len(bad) == len(calls):
        return "来源站点本次全部未返回 200（状态码 {}），因此没有可核验的案例；这不是「没有合适案例」".format(
            "、".join(sorted({str(a.get("status")) for a in bad})))
    return "本次检索没有命中符合条件且可核验的项目；宁可少给，不给凑数的"


def render_markdown(r: ResearchResult) -> str:
    b = r.brief
    lines: List[str] = []
    lines.append("# 专业案例研究与意向参考清单")
    lines.append("")
    lines.append("项目：{}　｜　修订：r{}　｜　生成：{}".format(
        r.project_id or "—", r.revision, _now()))
    lines.append("")

    # --- why this list exists -------------------------------------------
    lines.append("## 一、这份清单怎么来的")
    lines.append("")
    lines.append("在了解你的初步需求之后（{}），我们就开始找参考了——"
                 "不等所有问题问完，也不等方案确认。".format(b.trigger))
    lines.append("")
    if b.readiness == "early":
        lines.append("> 目前信息还偏少（{}）。所以下面的清单先解决「方向对不对」，"
                     "不作为设计结论；你补充更多诉求后我们会收紧一次。".format(
                         "缺：" + "、".join(b.missing[:5]) if b.missing else "仅有初步描述"))
        lines.append("")
    lines.append("检索方向按项目类型确定，每个专业看不同的问题：")
    lines.append("")
    lines.append("| 专业 | 看什么 | 检索用词 |")
    lines.append("|---|---|---|")
    for d in b.directions:
        lines.append("| {} | {} | {} |".format(
            d.to_dict()["discipline_label"], "、".join(d.aspects),
            "、".join(d.idea) or "—"))
    lines.append("")

    # --- first entry ----------------------------------------------------
    lines.append("## 二、第一优先：先去这里看")
    lines.append("")
    lines.append("**{}** ｜ <{}>".format(FIRST_PARTY.name, FIRST_PARTY.url))
    lines.append("")
    lines.append("- 用途：{}".format(FIRST_PARTY.use))
    seen_terms: List[str] = []
    for d in b.directions:
        for x in d.idea[:3]:
            if x not in seen_terms:
                seen_terms.append(x)
    lines.append("- 建议检索词：{}".format("、".join(seen_terms) or "按项目类型直接浏览"))
    lines.append("- 关于可达性，必须如实说明：{}".format(FIRST_PARTY.note))
    lines.append("- 边界：只带走结论（关键词、比例、材质组合），原图不进任何交付物；"
                 "作品权利属各自创作者，公开发布不等于授权复制")
    lines.append("")

    # --- cases ----------------------------------------------------------
    lines.append("## 三、精选参考案例")
    lines.append("")
    n = 0
    by_disc = r.by_discipline()
    if not r.cases:
        lines.append("本次没有可核验的案例。原因：")
        lines.append("")
        lines.append("- {}".format(_empty_reason("all", r.log)))
        lines.append("")
    for d in b.directions:
        group = by_disc.get(d.discipline) or []
        label = d.to_dict()["discipline_label"]
        lines.append("### 【{}】".format(label))
        lines.append("")
        if not group:
            lines.append("这一专业本次没有可核验案例。原因：{}".format(
                _empty_reason(d.discipline, r.log)))
            lines.append("")
            continue
        for c in group:
            n += 1
            lines.extend(_case_block(n, c))

    # --- manual sources -------------------------------------------------
    if r.manual:
        lines.append("## 四、需要你自己打开的站点")
        lines.append("")
        lines.append("下面这些站点我们**没有**脚本读取能力或本次无法读取，"
                     "所以只给出入口和检索词，不代替你判断内容。"
                     "请不要把这里当成「已找到的案例」。")
        lines.append("")
        lines.append("| 站点 | 入口 | 建议检索词 | 本次可达性 |")
        lines.append("|---|---|---|---|")
        for m in r.manual:
            lines.append("| {} | <{}> | {} | {} |".format(
                m["name"], m["url"], m.get("query") or "—", m.get("access_label", "")))
        lines.append("")
        notes = [m for m in r.manual if m.get("note")]
        if notes:
            for m in notes:
                lines.append("- {}：{}".format(m["name"], m["note"]))
            lines.append("")

    # --- how it feeds S2 -------------------------------------------------
    lines.append("## 五、这些案例怎么进入概念方案")
    lines.append("")
    lines.append("在 S2 出两到三套概念时，每套方案会挂上最相关的参考案例，并回答四个问题：")
    lines.append("")
    lines.append("1. 为什么参考它——它对应你哪一句诉求；")
    lines.append("2. 借鉴什么手法——是空间关系、材料交接，还是光的处理；")
    lines.append("3. 怎么转化成你自己的方案——换了什么、为什么换；")
    lines.append("4. 哪些特征不能照搬——尺寸、预算、规范、场地条件上的差异。")
    lines.append("")
    lines.append("参考图只用于讨论方向，**不能冒充本项目的效果图**。"
                 "需要看本项目的效果图时，走原创生成，不与案例照片混在一起。")
    lines.append("")

    # --- honesty --------------------------------------------------------
    lines.append("## 六、这份清单的边界")
    lines.append("")
    lines.append("| 事项 | 说明 |")
    lines.append("|---|---|")
    lines.append("| 链接可打开 | 标「已回读核验」的，是我们在生成时真的打开过页面并核对标题；"
                 "其余标「部分核验」「未核验」，请按未确认处理 |")
    lines.append("| 图片权利 | 全部为第三方作品，只给链接，不嵌入交付物；"
                 "作品权利属原作者与摄影师，公开发布不等于授权复制 |")
    lines.append("| 尺寸与面积 | 案例的面积、层数、开间属于它自己的地块与规范，"
                 "本项目几何只认已确认的实测与图纸 |")
    lines.append("| 没有虚构 | 无法访问或读不到的站点，写「读不到」，不编造项目和链接 |")
    lines.append("")
    return "\n".join(lines)


# --------------------------------------------------------------------------
# write
# --------------------------------------------------------------------------
def write(r: ResearchResult, out_dir: str | Path) -> Dict[str, Any]:
    """Write both artifacts and return what was written."""
    d = Path(out_dir)
    d.mkdir(parents=True, exist_ok=True)
    md = d / SHORTLIST_MD
    js = d / SHORTLIST_JSON
    md.write_text(render_markdown(r), encoding="utf-8")
    js.write_text(json.dumps(r.to_dict(), ensure_ascii=False, indent=2),
                  encoding="utf-8")
    return {
        "dir": str(d),
        "files": [SHORTLIST_MD, SHORTLIST_JSON],
        "cases": len(r.cases),
        "verified": len(r.verified),
    }


__all__ = [
    "SHORTLIST_JSON", "SHORTLIST_MD", "TARGET_MAX", "TARGET_MIN",
    "ResearchResult", "render_markdown", "write",
]
