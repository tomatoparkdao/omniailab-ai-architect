"""S2 概念汇报：像事务所一样把方向讲清楚（8–12 页）。

这一版不再输出"二十多页文字 + 一排链接"。汇报的**主角是图**，文字只做三件事：
说明判断、说明取舍、说明下一步。所有页面共用一份页面模型 `Page`，HTML 与
PPTX 从同一份模型渲染——客户看到的、改稿时能动的，是同一版内容。

页面顺序（内部能力调用顺序，不是新阶段）：

1. 封面：项目与主张
2. 设计定位：项目性质 / 功能重点 / 审美方向 / 主要限制（一页讲完）
3. 参考意向：3–5 张真实参考，说明"为什么是这几张、借什么、不借什么"
4. 设计机会：要解决的三件事
5. 主推方向：概念视觉 + 功能如何被满足 + 空间创意 + 气质
6. 概念推敲：体块/空间是怎么长出来的（自有分析图）
7. 材料与光：色板 + 材质细部
8. 备选方向：另一套**组织逻辑不同**的方向，讲清代价
9. 建议：总设计师推荐哪一套、为什么、G2 要确认什么
10. 附录：面积、参数来源、未决事项（技术内容不占主线的注意力）

图分三类，版面与页脚必须区分：
* 参考照片（素材库，第三方摄影）：标"参考 · 出处"；
* 自有分析图（体块演变、分区、动线、轴测）：标"自有图解 · 非按比例"；
* 概念意象（平台生成）：未配置时**不放替代图**，只在附录里写状态。

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from . import evolution as evo_mod
from . import plate as plate_mod

PAGE_W, PAGE_H = 1280, 720
M = 64                      # 版心边距
SERIF = "'Songti SC','Noto Serif SC','Source Han Serif SC','SimSun',serif"
SANS = "'PingFang SC','Noto Sans SC','Microsoft YaHei',sans-serif"

FILE_HTML = "concept-proposal.html"
FILE_PPTX = "concept-proposal.pptx"
FILE_MD = "concept-proposal.md"

DISCIPLINE_CN = {"architecture": "建筑", "interior": "室内", "landscape": "景观",
                 "structure": "结构", "mep": "机电"}


# --------------------------------------------------------------------------
# 数据模型
# --------------------------------------------------------------------------
@dataclass
class Theme:
    paper: str = "#FAF8F3"
    ink: str = "#1A1D1A"
    muted: str = "#6E736A"
    line: str = "#DED9CB"
    accent: str = "#2F5D45"
    whitespace: float = 0.4
    image_dominant: bool = True
    source: str = "default"


@dataclass
class Figure:
    path: str
    caption: str = ""
    credit: str = ""
    role: str = "image"        # image | diagram
    kind: str = ""             # hero / intent / detail / analysis


@dataclass
class Block:
    label: str
    text: str
    num: str = ""


@dataclass
class Page:
    kind: str
    variant: str = ""
    kicker: str = ""
    title: str = ""
    lead: str = ""
    figures: List[Figure] = field(default_factory=list)
    blocks: List[Block] = field(default_factory=list)
    swatches: List[Dict[str, str]] = field(default_factory=list)
    foot: str = ""
    notes: str = ""
    steps: List[str] = field(default_factory=list)
    #: 对标案例卡片（只有文字与链接，第三方图片不进版面）
    refs: List[Dict[str, Any]] = field(default_factory=list)


def theme_from(rules: Optional[Dict[str, Any]]) -> Theme:
    t = Theme()
    if not rules:
        return t
    tokens = rules.get("tokens") or rules
    for k in ("paper", "ink", "muted", "line", "accent"):
        v = tokens.get(k) or (rules.get("tokens") or {}).get(k)
        if isinstance(v, str) and v.startswith("#") and len(v) == 7:
            setattr(t, k, v)
    # `line` 在视觉.md 里可能叫 line，也可能只在默认值里
    t.whitespace = float(tokens.get("whitespace") or t.whitespace)
    t.image_dominant = bool(tokens.get("image_dominant", True))
    t.source = "视觉.md" if rules.get("source") != "default" else "default"
    return t


# --------------------------------------------------------------------------
# 小工具
# --------------------------------------------------------------------------
def _clip(text: Any, n: int) -> str:
    """截短：先按句读断开，断不开才用省略号。

    客户页面上出现"组团之间用一个共享中庭串起来，食堂 356 m² 与体…"
    这种半句话，比短一句完整的话难读得多。
    """
    t = " ".join(str(text or "").split())
    if len(t) <= n:
        return t                      # 已经够短就原样返回（含它自带的省略号）
    for sep in ("。", "；"):
        head = t.split(sep)[0]
        if 10 <= len(head) <= n:
            return head
    # 退一步：在 n 之内最后一个逗号处断，宁可短一点也不留半句
    cut = t[: n + 1]
    for sep in ("，", "、", "；"):
        i = cut.rfind(sep)
        if i >= max(10, int(n * 0.6)):
            return cut[:i]
    return t[: n - 1].rstrip("，、；…") + "…"


def _as_list(v: Any) -> List[str]:
    if isinstance(v, str):
        return [v] if v.strip() else []
    if isinstance(v, (list, tuple)):
        # 上游有把字符串逐字 iterate 的情况（本轮在 tradeoffs 上抓到过）：
        # 相邻的单字先拼回句子，整句单独保留，否则简报里会出现"每；层"。
        raw = [str(x) for x in v if isinstance(x, str)]
        if sum(1 for x in raw if len(x.strip()) <= 1) > 3:
            out: List[str] = []
            buf: List[str] = []
            for x in raw:
                if len(x.strip()) <= 1:
                    buf.append(x)
                else:
                    if buf:
                        out.append("".join(buf).strip())
                        buf = []
                    out.append(x.strip())
            if buf:
                out.append("".join(buf).strip())
            return [x for x in out if x]
        out: List[str] = []
        for x in v:
            if isinstance(x, dict):
                out.append(str(x.get("name") or x.get("text") or ""))
            elif x:
                out.append(str(x))
        return [x for x in out if x.strip()]
    return []


#: 一个进程复用一个浏览器。每张图都冷启动 Chrome 太贵——一次 S2 要出 4–5 张图，
#: 测试里又要跑十几遍，累计就是几分钟。这里只开一次。
_BROWSER: Any = None
_PW: Any = None
_TRIED = False


def _browser() -> Any:
    global _BROWSER, _PW, _TRIED
    if _TRIED:
        return _BROWSER
    _TRIED = True
    try:
        from playwright.sync_api import sync_playwright
    except Exception:                     # noqa: BLE001
        return None
    try:
        _PW = sync_playwright().start()
        _BROWSER = _PW.chromium.launch(channel="chrome", headless=True)
    except Exception:                     # noqa: BLE001  没装浏览器就降级，不给假图
        _BROWSER = None
    return _BROWSER


def release() -> None:
    """用完就关。

    浏览器留着不关会占住 playwright 的进程级状态，同进程里别的调用
    （验收脚本自己截图）就起不来了——而且它是静默失败，很难查。
    """
    global _BROWSER, _PW, _TRIED
    for obj in (_BROWSER, _PW):
        try:
            if obj is not None:
                obj.stop() if obj is _PW else obj.close()
        except Exception:                 # noqa: BLE001
            pass
    _BROWSER = None
    _PW = None
    _TRIED = False


def _theme_tokens(th: "Theme") -> Dict[str, str]:
    """页面主题 → 图版配色。图与页面必须同一套色，否则像拼贴。"""
    return {"paper": th.paper, "ink": th.ink, "muted": th.muted,
            "line": th.line, "accent": th.accent}


def _png(svg: str | Path, cache_dir: str | Path) -> str:
    """SVG → PNG（PPTX 不认 SVG）。失败返回空串，调用方据此不给图。"""
    src = Path(svg)
    if not src.exists():
        return ""
    dest = Path(cache_dir) / (src.stem + ".png")
    if dest.exists() and dest.stat().st_size > 2048:
        return str(dest)
    b = _browser()
    if b is None:
        return ""
    pg = None
    try:
        pg = b.new_page(viewport={"width": 1280, "height": 900},
                        device_scale_factor=2)
        pg.goto(src.resolve().as_uri(), wait_until="load")
        pg.wait_for_timeout(120)
        el = pg.query_selector("svg") or pg.query_selector("body")
        if el is None:
            return ""
        dest.parent.mkdir(parents=True, exist_ok=True)
        el.screenshot(path=str(dest), timeout=30000)
        return str(dest) if dest.exists() else ""
    except Exception:                     # noqa: BLE001
        return ""
    finally:
        if pg is not None:
            try:
                pg.close()
            except Exception:             # noqa: BLE001
                pass


def _figure(path: str, *, caption: str = "", credit: str = "", role: str = "image",
            kind: str = "") -> Optional[Figure]:
    if not path or not Path(path).exists():
        return None
    return Figure(path=str(path), caption=caption, credit=credit, role=role, kind=kind)


def _focus_names(j: Dict[str, Any]) -> List[str]:
    return [str(x.get("name") or "") for x in (j.get("focus") or []) if x.get("name")][:3]


def _function_line(j: Dict[str, Any], project: Any) -> str:
    """功能基线：按功能成组，不逐间罗列。

    客户问"我的要求你怎么满足"，答案应该是"教学区 1,560 m² 分 3 栋、
    食堂 356 m²、体育馆 800 m²"，而不是"普通教室 65 m² ×6"。
    """
    facts = _sector_focus(project)
    if facts:
        return facts + "；间数与面积表见附录"
    prog = list(getattr(project, "program", []) or [])
    if prog:
        return f"按任务书落实 {len(prog)} 项空间；面积与间数见面积表"
    return "按任务书口径落实；未量化的部分在附录未决事项里"


def _clean_strategy(v: Any) -> List[str]:
    """去掉内部字段名前缀（parti: / zoning: …），客户不该看到这些。"""
    import re

    out: List[str] = []
    for x in _as_list(v):
        t = re.sub(r"^[A-Za-z_]+\s*[:：]\s*", "", str(x)).strip()
        if t:
            out.append(t)
    return out


def _diagram(diagrams: Dict[str, List[Dict[str, str]]], cid: str, *kinds: str) -> str:
    for k in kinds:
        for d in diagrams.get(cid) or []:
            if d.get("kind") == k:
                return str(d.get("path") or "")
    return ""


# --------------------------------------------------------------------------
# 组装
# --------------------------------------------------------------------------
def _pick_concepts(concept_set: Dict[str, Any], comparison: Dict[str, Any]
                   ) -> Tuple[Dict[str, Any], Optional[Dict[str, Any]]]:
    concepts = list(concept_set.get("concepts") or [])
    if not concepts:
        return {}, None
    rec_id = str((comparison.get("recommendation") or {}).get("concept_id") or "")
    rec = next((c for c in concepts if c["concept_id"] == rec_id), concepts[0])
    # 备选必须是**另一套组织逻辑**：先看空间家族，再看原型，不看配色
    fam = (rec.get("spatial_prototype") or {}).get("family")
    proto = (rec.get("spatial_prototype") or {}).get("prototype_id")
    alt = next((c for c in concepts if c is not rec
                and (c.get("spatial_prototype") or {}).get("family") != fam), None)
    if alt is None:
        alt = next((c for c in concepts if c is not rec
                    and (c.get("spatial_prototype") or {}).get("prototype_id") != proto), None)
    return rec, alt


LANDSCAPE_WORDS = ("景观", "花园", "庭院", "院子", "园林", "草坪", "树木", "户外")
BUILDING_WORDS = ("外立面", "立面", "别墅", "公寓", "住宅", "居所", "宅", "建筑摄影")


def _is_landscape_shot(shot: Dict[str, Any]) -> bool:
    """这张照片是在讲院子，还是在讲房子？"""
    blob = str(shot.get("title") or "") + " " + " ".join(
        str(t) for t in (shot.get("tags") or []))
    has_land = any(w in blob for w in LANDSCAPE_WORDS)
    has_bldg = any(w in blob for w in BUILDING_WORDS)
    return has_land and not has_bldg


def _ratio_line(colour: Sequence[Dict[str, Any]]) -> str:
    """配色比例：只用色板自己声明的占比，不推算、不编。"""
    entries = []
    for e in (colour or []):
        try:
            pct = float(e.get("pct") or 0)
        except (TypeError, ValueError):
            pct = 0.0
        if pct:
            entries.append({"name": str(e.get("name") or ""),
                            "pct": pct,
                            "band": str(e.get("band") or "accent")})
    if not entries:
        return "色板未声明占比：只给色彩关系，不编比例"
    bands: Dict[str, List[str]] = {}
    for e in entries:
        bands.setdefault(str(e.get("band") or "accent"), []).append(
            f"{e.get('name', '')} {float(e['pct']):.0f}%")
    order = [("dominant", "主色"), ("secondary", "辅色"), ("accent", "点缀"),
             ("dark", "深色")]
    parts = [f"{label} {'、'.join(bands[key])}" for key, label in order if bands.get(key)]
    total = sum(float(e["pct"]) for e in entries)
    tail = f"（合计 {total:.0f}%，取自风格声明的占比）"
    return "；".join(parts) + tail


def _sector_focus(project: Any) -> str:
    """功能重点用行业程序的口径：一个标准层 764 m²、全楼 4 层。

    只列单层房间（普通教室 65 m² ×6）会让客户以为只做 6 个班。
    """
    sp = ((getattr(project, "meta", {}) or {}).get("sector_program") or {})
    if not sp:
        return ""
    unit = str(sp.get("unit") or "")
    area = float(sp.get("area_m2") or 0)
    note = str(sp.get("note") or "")
    if not unit or not area:
        return ""
    head = f"{unit} {area:,.0f} m²"
    return head + ("；" + note if note else "")


def _position_blocks(ctx: Any, j: Dict[str, Any],
                     project: Any = None) -> List[Block]:
    focus = ""
    if project is not None:
        focus = _clip(_sector_focus(project), 76)
    if not focus:
        focus = "、".join(f"{x['name']}" + (f"（{x['note']}）" if x.get("note") else "")
                          for x in (j.get("focus") or [])[:3])
    aest = j.get("aesthetic") or {}
    mood = aest.get("label") or "、".join(o["label"] for o in (aest.get("options") or []))
    limits = "；".join((j.get("limits") or [])[:2]) or "无阻断项"
    return [
        Block("项目性质", f"{j.get('type_label', '')}"
                        + (f"　{j.get('nature')}" if j.get("nature") else "")),
        Block("功能重点", focus or "按任务书确认"),
        Block("审美方向", (mood or "待定")
             + ("（客户已指定）" if aest.get("source") == "client" else "")),
        Block("主要限制", limits),
    ]


def build(project: Any, ctx: Any, concept_set: Dict[str, Any],
          comparison: Dict[str, Any], moodboards: Dict[str, Dict[str, Any]],
          diagrams: Dict[str, List[Dict[str, str]]], visual: Optional[Dict[str, Any]] = None,
          *, curation: Optional[Dict[str, Any]] = None, judgment: Optional[Dict[str, Any]] = None,
          rules: Optional[Dict[str, Any]] = None, out_dir: str | Path = ".",
          page_cap: int = 12) -> Dict[str, Any]:
    """Build the page model. Text always traceable; images always credited."""
    out = Path(out_dir)
    cache = out / "assets" / "_png"
    rec, alt = _pick_concepts(concept_set, comparison)
    if not rec:
        return {"pages": [], "count": 0, "note": "没有概念可汇报"}
    j = judgment or {}
    th = theme_from(rules)
    pages: List[Page] = []
    lead = str(getattr(ctx, "lead_id", "") or "")
    try:
        from ..sector import brief as _sector_brief

        sector = _sector_brief.from_project(project).sector
    except Exception:                     # noqa: BLE001  非行业项目就是普通项目
        sector = ""
    shots = list((curation or {}).get("shots") or [])
    # 景观项目：参考页只留"讲院子"的图。素材库索引里混着别墅外观，
    # 拿它当庭院意向，客户一眼就知道没看懂委托范围。
    if lead == "landscape":
        shots = [s for s in shots if _is_landscape_shot(s)]
    hero_shot = next((s for s in shots if s.get("role") == "hero"), None)
    intent_shots = [s for s in shots if s.get("role") == "intent"][:3]
    detail_shots = [s for s in shots if s.get("role") == "detail"][:2]
    proto = rec.get("spatial_prototype") or {}
    lead_cn = DISCIPLINE_CN.get(lead, "建筑")
    project_name = str(getattr(project, "name", "") or project.project_id)

    # 1 封面
    # 景观项目的封面不能放一张建筑外立面照——客户委托的是院子，不是房子。
    # 有合格的景观实景才用照片，否则用自有的景观总平面图版。
    cover_fig = _figure((hero_shot or {}).get("path", ""), caption=(hero_shot or {}).get("title", ""),
                        credit=(hero_shot or {}).get("credit", ""), kind="hero")
    cid = rec["concept_id"].lower()
    # 封面图按封面的框（800×452）出，主推页按整幅（1200×496）出：
    # 同一张图缩放使用会让标注小到看不清。
    cover_svg = plate_mod.write(rec, out / "concept-plates", heading=False,
                                footer=False, annotate=False, discipline=lead,
                                sector=sector, width=800, height=452,
                                stem="plate-" + cid + "-cover")
    plate_svg = plate_mod.write(rec, out / "concept-plates", heading=False,
                                footer=False, discipline=lead, sector=sector,
                                width=1200, height=496,
                                stem="plate-" + cid)
    plate_png = _png(plate_svg, cache) if plate_svg else ""
    cover_plate_png = _png(cover_svg, cache) if cover_svg else plate_png
    if cover_fig is None:
        cover_fig = _figure(cover_plate_png,
                            caption="概念图解（自有图解·非按比例）",
                            credit="OmniAiLab 自有图解", role="diagram", kind="hero")
    pages.append(Page(
        kind="cover",
        kicker=f"CONCEPT PROPOSAL · {lead_cn}方案 · r{project.revision}",
        title=project_name,
        lead=rec["concept_statement"],
        figures=[cover_fig] if cover_fig else [],
        variant="bleed" if (hero_shot and cover_fig) else "panel",
        foot="概念阶段汇报：先看方向，再看图纸。图中空间关系为示意，不作尺寸依据。",
        notes=f"封面图：{cover_fig.caption if cover_fig else '无'}"
              f"　来源：{cover_fig.credit if cover_fig else '—'}",
    ))

    # 2 设计定位
    first_intent = intent_shots[0] if intent_shots else {}
    pos_fig = _figure(first_intent.get("path", ""),
                      caption=first_intent.get("caption", ""),
                      credit=first_intent.get("credit", ""), kind="intent")
    from . import quick as _quick

    try:
        pos_lead = str(judgment.get("headline") or _quick.headline(j) or "")
    except Exception:                     # noqa: BLE001
        pos_lead = str(j.get("type_label") or "")
    if not pos_lead:
        pos_lead = _clip(ctx.brief_lines()[0], 60)
    # 素材库没有同类空间时，把"该给什么参考"直接写在页脚，而不是留一页空白
    if not shots:
        pos_foot = ("参考：素材库暂无同类空间实景（" + (j.get("type_label") or "本类型")
                    + "），建议提供 3–5 张参考照片或建成项目，用于对齐气质。")
    else:
        pos_foot = "判断依据：客户原话 + 已确认任务书；未定项标为待确认，不影响概念探索。"
    pages.append(Page(
        kind="position", kicker="01 / 设计定位", title="先把项目看准",
        lead=pos_lead,
        blocks=_position_blocks(ctx, j, project),
        figures=[pos_fig] if pos_fig else [],
        foot=pos_foot,
        notes="这一页替代过去的问诊清单。客户只看一页就知道我们怎么理解他的项目。",
    ))

    # 3 参考意向。少于两张就不单独成页：一张图铺满整版会被裁成一条，
    # 与其硬撑一页，不如让定位页的那张承担意向（它已经在那儿了）。
    if len(intent_shots) >= 2:
        figs = []
        for s in intent_shots[:3]:
            f = _figure(s["path"], caption=s.get("caption", ""), credit=s.get("credit", ""),
                        kind="intent")
            if f:
                figs.append(f)
        asks = []
        for s in intent_shots[:3]:
            ex = s.get("explain") or {}
            for b in (ex.get("borrow") or []):
                b = _clip(b, 24)
                if b and b not in asks:
                    asks.append(b)
                    break
        pages.append(Page(
            kind="intents", kicker="02 / 参考意向", title="为什么是这几张",
            lead="参考照片只用于对齐气质与做法，不会照搬到本项目。",
            figures=figs,
            blocks=[Block("借什么", "；".join(x for x in asks if x)),
                    Block("不借什么", _clip(((intent_shots[0].get("explain") or {})
                                            .get("limits") or ["别人的场地与尺度"])[0], 52))],
            variant="refs",
            foot=(curation or {}).get("rights_note", ""),
            notes="图源：" + "、".join(s.get("credit", "") for s in intent_shots[:3]),
        ))

    # 3b 对标案例：素材库没有同类实景时，这一页就是主要的"别人怎么做"证据。
    # 只放文字与链接——第三方照片有版权，不嵌进可再分发的 PPTX。
    refs = [c for c in ((rec.get("references") or {}).get("cases") or [])
            if str(c.get("title") or "").strip()]
    if len(refs) >= 2:
        pages.append(Page(
            kind="cases", kicker="03 / 对标案例", title="同类项目是怎么解决的",
            lead="真实建成项目，按可核验程度标注；只给项目页链接，不把别人的照片搬进提案。",
            refs=refs[:3],
            foot="案例只用于讨论方法，不代表本项目效果；引用信息以原始项目页为准。",
            notes="来源：" + "；".join(
                f"{c.get('title')}（{c.get('architect')}，{c.get('url')}）" for c in refs[:3]),
        ))

    # 4 设计机会
    opps = list(getattr(ctx, "opportunities", []) or [])[:3]
    opp_blocks = [Block("", _clip(o.get("problem") or o.get("design_goal") or "", 54),
                        num=f"0{i + 1}")
                  for i, o in enumerate(opps)]
    # 这一页只放判断，不放图：1280×720 的分析图缩到 500 px 宽后字就看不清了。
    # 与其放一张看不清的图，不如把这几条判断排清楚。
    if len(opp_blocks) >= 2:
        cn = ("一", "两", "三")[min(3, len(opp_blocks)) - 1]
        pages.append(Page(
            kind="opportunity", kicker="02 / 设计机会",
            title="这一版要解决的" + cn + "件事",
            lead=(("功能关系：" + _clip(proto.get("zoning", ""), 52)) if proto.get("zoning")
                  else "以下条目来自 S1 的设计机会，不是本轮编的。"),
            blocks=opp_blocks,
            foot="机会条目来自 S1 的设计机会清单；每条都在本方案里有对应的空间做法。",
            notes="如果这里说不出「要解决什么」，后面的形式讨论都是空的。",
        ))
    # 任务书没有明确矛盾时不硬凑三条：这一页就不出，定位页已经把功能说清楚了。

    # 5 主推方向：一张大图（自有主图版），三条短句
    plate_caption = {"architecture": "主推方向 · 体块关系（自有图解·非按比例）",
                     "interior": "主推方向 · 功能与流线（自有图解·非按比例）",
                     "landscape": "主推方向 · 场地与游线（自有图解·非按比例）"}.get(
        lead, "主推方向 · 空间关系（自有图解·非按比例）")
    rec_plate = _figure(plate_png, caption=plate_caption,
                        credit="OmniAiLab 自有图解", role="diagram", kind="hero")
    if rec_plate is None:                  # 没有 Playwright 时退回分析图
        rec_plate = _figure(_png(_diagram(diagrams, rec["concept_id"], "axon",
                                          "massing", "landscape", "zoning"), cache),
                            caption="主推方向 · 空间关系（自有图解·非按比例）",
                            credit="OmniAiLab 自有图解", role="diagram", kind="hero")
    pages.append(Page(
        kind="concept", kicker=f"04 / 主推方向 · {rec['concept_id']}",
        title=rec["concept_name"], lead=_clip(rec["concept_statement"], 44),
        figures=[rec_plate] if rec_plate else [],
        foot={"architecture": "体块关系示意，平面尺寸与轮廓须在 S3 按实测复核。",
              "interior": "功能与流线示意，房间尺寸与净高须在 S3 按实测复核。",
              "landscape": "场地与游线示意，面积与高差须在 S3 按实测复核。"}.get(
            lead, "空间关系示意，尺寸须在 S3 按实测复核。"),
        notes="；".join(_as_list(rec.get("evidence")))[:300],
    ))

    # 5b 设计回应：功能 / 空间 / 体验，三条各一句，配功能关系图
    pages.append(Page(
        kind="response", kicker="04 / 设计回应", title="这套方向怎么回应你的需求",
        lead=_clip(rec.get("design_problem", ""), 56),
        blocks=[
            Block("功能", _clip(_function_line(j, project), 90)),
            Block("空间", _clip(proto.get("zoning", "") or proto.get("spatial_logic", ""), 90)),
            Block("体验", _clip(rec.get("user_experience", ""), 90)),
        ],
        foot="回应对象是 S1 已确认的需求；未回应到的部分写在附录的未决事项里。",
        notes="这一页回答客户最关心的：我说的那些事，你到底怎么做。",
    ))

    # 6 概念推敲：按专业推（建筑体块／室内序列／景观场地），不套同一套动画。
    # 概念数据不足以支撑推敲时，不出图也不出动画，只把四条判断写清楚。
    evo = evo_mod.plan(rec, lead, sector=sector)
    evo_png = ""
    if evo.ok:
        evo_svg = evo_mod.strip(rec, lead, width=700, height=470,
                                theme=dict(_theme_tokens(th)), sector=sector)
        if evo_svg:
            path = out / "concept-plates" / ("steps-" + rec["concept_id"].lower() + ".svg")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(evo_svg, encoding="utf-8")
            evo_png = _png(path, cache)
    evo_caption = {"architecture": "体块推演（自有图解·非按比例）",
                   "interior": "功能与序列（自有图解·非按比例）",
                   "landscape": "场地与游线（自有图解·非按比例）"}.get(lead, "概念推敲")
    evo_title = {"architecture": "这个形态是怎么长出来的",
                 "interior": "这套空间是怎么排出来的",
                 "landscape": "这个院子是怎么组织起来的"}.get(lead, "这套方案是怎么成立的")
    evo_lead = {"architecture": "四步推演：从场地限界推到最终形态，每一步都对应一条约束。",
                "interior": "四步推演：从功能重组推到核心空间体验，每一步都改变人的走法。",
                "landscape": "四步推演：从场地边界推到水景种植，每一步都改变人在院子里的感受。"}.get(
        lead, "四步推演：每一步都对应一条设计约束。")
    if evo.ok and evo_png:
        evo_fig = _figure(evo_png, caption=evo_caption,
                          credit="OmniAiLab 自有图解", role="diagram", kind="analysis")
        pages.append(Page(
            kind="evolution", kicker="05 / 概念推敲", title=evo_title,
            lead=evo_lead,
            figures=[evo_fig] if evo_fig else [],
            steps=[f"{s.name}：{_clip(s.note, 44)}" for s in evo.steps],
            blocks=[Block("专业判断", _clip("；".join(_as_list(rec.get("advantages"))[:2]), 60))],
            foot="图解为空间关系示意，不按比例；尺寸与构造依据见 S3。",
            notes="；".join(f"{s.n} {s.name} 依据 {s.basis}" for s in evo.steps),
        ))
    else:
        # 不出图：把概念里真实存在的四条判断排清楚，比放一张不相干的图诚实
        pages.append(Page(
            kind="tensions", kicker="05 / 概念要成立，靠这四件事", title="这套方案凭什么成立",
            lead=evo.reason or "概念数据不足以做推演，以下四条取自本方案自己的说法。",
            blocks=[Block("分区", _clip(proto.get("zoning", ""), 84)),
                    Block("动线", _clip(proto.get("circulation", ""), 84)),
                    Block("光", _clip(proto.get("daylight", ""), 84)),
                    Block("代价", _clip("；".join(_as_list(rec.get("tradeoffs"))[:2]), 84))],
            foot="不做推演图的场合，也不出动画：宁可少一张图，不放不相干的推演。",
            notes="这一页的所有句子都来自本方案自己的策略字段。",
        ))

    # 7 材料与光
    mb = moodboards.get(rec["concept_id"]) or {}
    colour = ((mb.get("slots") or {}).get("colour") or {}).get("entries") or []
    swatches = [{"name": str(e.get("name") or ""), "hex": str(e.get("hex") or ""),
                 "note": str(e.get("pct") or "")} for e in colour[:6] if e.get("hex")]
    mats = [f"{m['name']}｜{m.get('application', '')}" for m in
            (rec.get("material_direction") or [])][:4]
    ratio = _ratio_line(colour)
    lights = [str(x) for x in _as_list(rec.get("lighting_direction"))][:3]
    mat_figs = []
    for s in detail_shots[:2]:
        f = _figure(s["path"], caption=s.get("caption", ""), credit=s.get("credit", ""),
                    kind="detail")
        if f:
            mat_figs.append(f)
    pages.append(Page(
        kind="materials", kicker="06 / 材料与光", title="用什么材料把气质做出来",
        lead=f"风格：{' + '.join(_as_list(rec.get('style_labels'))) or '按视觉.md'}",
        swatches=swatches, figures=mat_figs,
        blocks=[Block("主材", "；".join(mats) or "按材料方向表"),
                Block("光", "；".join(lights) or "按采光原则"),
                Block("配色比例", ratio)],
        foot="色值为屏幕值，实物以打样为准；材料细部照片为参考，不是本项目实拍。",
        notes="色板来自 S2 意向板；材质照片来自素材库，注明出处。",
    ))

    # 7 备选方向
    if alt is not None:
        ap = alt.get("spatial_prototype") or {}
        alt_svg = plate_mod.write(alt, out / "concept-plates", heading=False,
                                  footer=False, annotate=False, discipline=lead,
                                  sector=sector, width=940, height=448,
                                  stem="plate-" + alt["concept_id"].lower())
        alt_fig = _figure(_png(alt_svg, cache) if alt_svg else "",
                          caption=f"备选 · {alt['concept_name']}（自有图解·非按比例）",
                          credit="OmniAiLab 自有图解", role="diagram", kind="analysis")
        cost = "；".join(_as_list(alt.get("tradeoffs"))[:2]) or \
            str(ap.get("cost_note") or "")
        pages.append(Page(
            kind="second", kicker=f"07 / 备选方向 · {alt['concept_id']}",
            title=alt["concept_name"], lead=_clip(alt["concept_statement"], 44),
            figures=[alt_fig] if alt_fig else [],
            blocks=[Block("组织逻辑", _clip(ap.get("zoning", "") or
                                            ap.get("spatial_logic", ""), 76)),
                    Block("代价", _clip(cost, 76))],
            foot="两套方向的空间家族不同，不是同一方案换个颜色。",
            notes="备选存在的意义是让客户有真实选择，而不是凑满三套。",
        ))

    # 9 建议
    reco = comparison.get("recommendation") or {}
    why = _as_list(reco.get("why_not"))
    pages.append(Page(
        kind="recommend", kicker="08 / 建议", title="我建议先按这一套推进",
        lead=f"{rec['concept_id']}　{rec['concept_name']}　—　{_clip(rec.get('role_label', ''), 24)}",
        blocks=[Block("为什么", _clip(x, 60), num=f"0{i + 1}")
                for i, x in enumerate((_as_list(reco.get("rationale")) or
                                       _as_list(rec.get("advantages")))[:3])]
               + ([Block("备选的顾虑", _clip(why[0], 60), num="")] if why else []),
        steps=["确认方向（选定 concept_id，不是选一个风格名）",
               "确认空间策略：分区、动线、采光原则",
               "确认风格与关键材料，形成概念基准",
               "进入 S3：按选定方向深化平面与几何"],
        foot="推荐是专业意见，决定权在业主；确认后 S3 以该方向为唯一设计输入。",
        notes="G2 的确认对象是 concept_id；确认后系统写 concept-baseline。",
    ))

    # 10 附录
    areas = (f"需求面积 {ctx.target_area_m2:,.0f} m²" if getattr(ctx, "target_area_m2", 0)
             else "需求面积未量化")
    if getattr(ctx, "area_available_m2", None):
        areas += f"　可用面积 {ctx.area_available_m2:,.0f} m²"
    vis = visual or {}
    pages.append(Page(
        kind="appendix", kicker="附录 / 数据与边界", title="这一版的数据从哪来",
        blocks=[
            Block("面积", areas),
            Block("资料精度", f"{getattr(ctx, 'precision', '')}　"
                             f"{getattr(ctx, 'dimensional_note', '') or ''}"),
            Block("概念意象", f"平台 {vis.get('platform_state', '未配置')}："
                             f"已生成 {vis.get('generated', 0)}、待平台 {vis.get('deferred', 0)}；"
                             "未生成的图不放假图"),
            Block("未决事项", "；".join((j.get("limits") or [])[:2]) or "无"),
            Block("免责", "结构安全、消防、无障碍、机电负荷与当地法规符合性不在本系统结论范围，"
                         "须由持证专业人员在项目所在地复核签署；概念图不作尺寸依据。"),
        ],
        foot=f"OmniAiLab AI Architect · r{project.revision} · 视觉规范来源：{th.source}",
        notes="技术校核放附录，不占主线的注意力；需要时单独出报告。",
    ))
    pages = pages[:page_cap]
    return {
        "pages": pages,
        "count": len(pages),
        "recommended": rec["concept_id"],
        "alternative": (alt or {}).get("concept_id", ""),
        "theme": th,
        "note": "页面为概念汇报主线；技术数据在附录，详细校核另出报告。",
    }


# --------------------------------------------------------------------------
# 版面（一份模型，两个后端）
# --------------------------------------------------------------------------
def _t(x: float, y: float, w: float, h: float, text: str, *, size: int = 15,
       color: str = "", font: str = "sans", weight: int = 400, lh: float = 1.7,
       spacing: float = 0) -> Dict[str, Any]:
    return {"t": "text", "x": x, "y": y, "w": w, "h": h, "text": text, "size": size,
            "color": color, "font": font, "weight": weight, "lh": lh, "spacing": spacing}


def _img(f: Figure, x: float, y: float, w: float, h: float,
         fit: str = "") -> Dict[str, Any]:
    """`fit=contain` 用于图纸：不裁边，整张放进框里。照片用 cover。"""
    return {"t": "img", "x": x, "y": y, "w": w, "h": h, "path": f.path,
            "fit": fit or ("contain" if f.role == "diagram" else "cover")}


def layout(page: Page, th: Theme) -> List[Dict[str, Any]]:
    """Absolute geometry in 1280×720. HTML and PPTX both consume this."""
    e: List[Dict[str, Any]] = []
    k = page.kind

    if k == "cover":
        if page.figures and page.variant == "bleed":
            e.append(_img(page.figures[0], 0, 0, PAGE_W, PAGE_H))
            e.append({"t": "rect", "x": 0, "y": 396, "w": PAGE_W, "h": 324,
                      "fill": "#141614", "opacity": 0.88})
            ink = "#F6F3EA"
            dim = "#B9B5A8"
            x0 = M
        else:
            # 面板式封面：左边一条纸色面板写字，右边放自有主图版，
            # 图不被色条盖住——体块是这一页的主角。
            e.append({"t": "rect", "x": 0, "y": 0, "w": PAGE_W, "h": PAGE_H,
                      "fill": th.paper, "opacity": 1})
            if page.figures:
                e.append(_img(page.figures[0], 452, 138, 800, 452))
                e.append(_t(458, 600, 780, 16,
                            f"{page.figures[0].caption}　{page.figures[0].credit}",
                            size=9, color=th.muted))
            ink = th.ink
            dim = th.muted
            x0 = 64
        if page.variant == "bleed":
            e.append(_t(x0, 420, 900, 18, page.kicker, size=11.5,
                        color="#A8C7B4", weight=600, spacing=2.0))
            e.append(_t(x0, 444, 900, 110, page.title, size=40, color=ink,
                        font="serif", lh=1.2))
            e.append(_t(x0, 560, 880, 88, page.lead, size=15, color=dim, lh=1.7))
            if page.foot:
                e.append(_t(x0, 682, 900, 16, _clip(page.foot, 56), size=9, color="#8E8B80"))
        else:
            e.append(_t(x0, 212, 380, 18, page.kicker, size=11.5, color=th.accent,
                        weight=600, spacing=2.0))
            e.append(_t(x0, 246, 372, 240, page.title, size=42, color=ink,
                        font="serif", lh=1.22))
            e.append(_t(x0, 462, 356, 130, page.lead, size=15, color=dim, lh=1.75))
            if page.foot:
                e.append(_t(x0, 628, 400, 34, _clip(page.foot, 60), size=9.5, color=dim,
                            lh=1.6))
        return e

    # 通用页头。定位页右侧若是一张整幅照片，页头与正文都收窄到照片左边，
    # 否则标题与说明会压在照片上（文字掉进暗部就看不清）。
    bleed = page.kind == "position" and bool(page.figures)
    hdr_w = 560.0 if bleed else 700.0
    rule_w = 576.0 if bleed else (PAGE_W - 2 * M)
    e.append(_t(M, 54, hdr_w, 16, page.kicker.upper(), size=11.5, color=th.accent,
                weight=600, spacing=1.8))
    e.append({"t": "rule", "x": M, "y": 78, "w": rule_w, "h": 1,
              "color": th.line})
    e.append(_t(M, 96, hdr_w, 40, page.title, size=30, color=th.ink, font="serif", lh=1.25))
    if page.lead:
        e.append(_t(M, 142, hdr_w, 46 if bleed else 26, page.lead, size=14.5,
                    color=th.muted, lh=1.55))

    if k in ("position", "opportunity"):
        col_w = (520.0 if page.figures else 700.0) if k == "position" else 460.0
        n = max(1, len(page.blocks))
        y = 212.0 if (k == "position" and page.figures) else 182.0
        step = (96.0 if k == "position" else 106.0) if n <= 4 else 78.0
        for i, b in enumerate(page.blocks):
            yy = y + i * step
            ox = M + (40 if b.num else 0)
            if i:
                e.append({"t": "rule", "x": M, "y": yy - 24, "w": col_w, "h": 1,
                          "color": th.line})
            if b.num:
                e.append(_t(M, yy - 2, 34, 18, b.num, size=11.5, color=th.accent, weight=700))
            e.append(_t(ox, yy - 2, col_w, 16, b.label.upper(), size=10, color=th.accent,
                        weight=600, spacing=1.3))
            e.append(_t(ox, yy + 20, col_w, step - 26, b.text,
                        size=14.5 if n <= 4 else 13.0, color=th.ink, lh=1.6))
        if page.figures:
            if k == "position":
                e.append(_img(page.figures[0], 660, 0, 620, PAGE_H))
                e.append(_t(660, PAGE_H - 34, 580, 16,
                            f"{page.figures[0].caption}　{page.figures[0].credit}",
                            size=9.5, color="#F2EFE6"))
            else:
                fx, fw = 700.0, 516.0
                fh = fw * 0.60
                e.append(_img(page.figures[0], fx, 190, fw, fh))
                e.append(_t(fx, 190 + fh + 10, fw, 16,
                            f"{page.figures[0].caption}　{page.figures[0].credit}",
                            size=9.5, color=th.muted))
        if page.foot:
            e.append(_t(M, 684, 860, 14, _clip(page.foot, 50), size=9, color=th.muted))
        return e

    if k == "intents":
        n = max(1, min(3, len(page.figures)))
        gap = 18.0
        total = PAGE_W - 2 * M
        fw = (total - gap * (n - 1)) / n
        fh = 300.0
        for i, f in enumerate(page.figures[:n]):
            x = M + i * (fw + gap)
            e.append(_img(f, x, 190, fw, fh))
            e.append(_t(x, 190 + fh + 10, fw, 30, f.caption or "", size=11.5,
                        color=th.ink, lh=1.4))
            e.append(_t(x, 190 + fh + 42, fw, 16, f.credit, size=9.5, color=th.muted))
        bx = M
        by = 190 + fh + 78
        cols = [b for b in page.blocks if b.text]
        for i, b in enumerate(cols[:2]):
            e.append(_t(bx + i * 560, by, 520, 18, b.label.upper(), size=10, color=th.accent,
                        weight=600, spacing=1.3))
            e.append(_t(bx + i * 560, by + 20, 520, 44, b.text, size=13, color=th.ink, lh=1.55))
        if page.foot:
            e.append(_t(M, 676, 1000, 16, _clip(page.foot, 56), size=9, color=th.muted))
        return e

    if k == "concept":
        if page.figures:
            e.append(_img(page.figures[0], 30, 172, 1200, 496))
            e.append(_t(36, 674, 700, 14,
                        f"{page.figures[0].caption}　{page.figures[0].credit}",
                        size=9, color=th.muted))
        return e

    if k == "second":
        if page.figures:
            e.append(_img(page.figures[0], 30, 172, 940, 448))
            e.append(_t(36, 626, 700, 14,
                        f"{page.figures[0].caption}　{page.figures[0].credit}",
                        size=9, color=th.muted))
        for i, b in enumerate([b for b in page.blocks if str(b.text or "").strip()][:2]):
            yy = 214 + i * 150
            e.append(_t(1000, yy, 232, 14, b.label.upper(), size=9.5, color=th.accent,
                        weight=600, spacing=1.2))
            e.append(_t(1000, yy + 18, 232, 120, b.text, size=11.5, color=th.ink, lh=1.6))
        return e

    if k == "response":
        if page.figures:
            fw, fh = 470.0, 330.0
            e.append(_img(page.figures[0], PAGE_W - M - fw, 176, fw, fh))
            e.append(_t(PAGE_W - M - fw, 176 + fh + 8, fw, 14,
                        f"{page.figures[0].caption}　{page.figures[0].credit}",
                        size=9, color=th.muted))
        blocks = [b for b in page.blocks if str(b.text or "").strip()][:3]
        step = 132.0
        for i, b in enumerate(blocks):
            yy = 232 + i * step
            e.append({"t": "rule", "x": M, "y": yy - 18, "w": 980, "h": 1,
                      "color": th.line})
            e.append(_t(M, yy, 120, 14, b.label.upper(), size=10, color=th.accent,
                        weight=600, spacing=1.2))
            e.append(_t(M + 130, yy - 4, 850, 60, b.text, size=15, color=th.ink, lh=1.7))
        if page.foot:
            e.append(_t(M, 682, 900, 14, _clip(page.foot, 52), size=9, color=th.muted))
        return e

    if k == "evolution":
        if page.figures:
            fw, fh = 700.0, 486.0
            e.append(_img(page.figures[0], M, 180, fw, fh))
            e.append(_t(M, 180 + fh + 8, fw, 16,
                        f"{page.figures[0].caption}　{page.figures[0].credit}",
                        size=9.5, color=th.muted))
        x = M + 736
        for i, s in enumerate(page.steps[:4]):
            yy = 196 + i * 92
            e.append(_t(x, yy, 28, 20, f"0{i + 1}", size=12, color=th.accent, weight=700))
            e.append(_t(x + 30, yy, 340, 72, s, size=12.5, color=th.ink, lh=1.65))
        if page.blocks:
            b = page.blocks[0]
            e.append(_t(x + 30, 570, 340, 16, b.label.upper(), size=9.5, color=th.accent,
                        weight=600, spacing=1.2))
            e.append(_t(x + 30, 588, 340, 52, b.text, size=11.5, color=th.muted, lh=1.55))
        return e

    if k == "materials":
        y = 186.0
        sw = min(6, len(page.swatches)) or 1
        total = 660.0
        gap = 10.0
        cw = (total - gap * (sw - 1)) / sw
        for i, s in enumerate(page.swatches[:sw]):
            x = M + i * (cw + gap)
            e.append({"t": "rect", "x": x, "y": y, "w": cw, "h": 96, "fill": s["hex"],
                      "opacity": 1})
            e.append(_t(x, y + 102, cw, 16, s["name"], size=10, color=th.ink))
            note = str(s.get("note") or "").strip()
            tail = (" · " + note if note else "")
            if note.replace(".", "").isdigit():
                tail = " · " + note + "%"
            e.append(_t(x, y + 118, cw, 14, s["hex"].upper() + tail,
                        size=9, color=th.muted))
        if page.figures:
            fy = 300.0
            fw = 316.0
            for i, f in enumerate(page.figures[:2]):
                e.append(_img(f, M + i * (fw + 16), fy, fw, 210))
                e.append(_t(M + i * (fw + 16), fy + 216, fw, 16,
                            f"{f.caption}　{f.credit}", size=9, color=th.muted))
        x2 = 748.0
        rows = [b for b in page.blocks if str(b.text or "").strip()][:3]
        gap = 128.0 if len(rows) <= 3 else 104.0
        for i, b in enumerate(rows):
            yy = 186 + i * gap
            e.append(_t(x2, yy, 460, 16, b.label.upper(), size=10, color=th.accent,
                        weight=600, spacing=1.3))
            e.append(_t(x2, yy + 18, 460, gap - 32, b.text, size=12, color=th.ink, lh=1.65))
        if page.foot:
            e.append(_t(M, 676, 1152, 16, page.foot, size=9.5, color=th.muted))
        return e

    if k == "cases":
        n = max(1, min(3, len(page.refs)))
        gap = 26.0
        fw = (PAGE_W - 2 * M - gap * (n - 1)) / n
        rows_of = [("为什么", lambda c: str(c.get("why") or "")),
                   ("借什么", lambda c: "；".join(str(x) for x in (c.get("borrow") or []))[:96]),
                   ("不照搬", lambda c: "；".join(str(x) for x in (c.get("limits") or []))[:96])]
        for i, c in enumerate(page.refs[:n]):
            x = M + i * (fw + gap)
            e.append({"t": "rule", "x": x, "y": 186, "w": fw, "h": 1, "color": th.line})
            e.append(_t(x, 200, fw, 16, f"0{i + 1}", size=11.5, color=th.accent,
                        weight=700))
            e.append(_t(x, 222, fw, 52, str(c.get("title") or ""), size=18,
                        color=th.ink, font="serif", lh=1.3))
            verify = {"verified": "已核验", "partial": "部分核验",
                      "unverified": "未核验"}.get(str(c.get("verify") or ""), "")
            src = {"archdaily": "ArchDaily"}.get(str(c.get("source") or ""),
                                                 str(c.get("source") or ""))
            meta = "　".join(str(v) for v in (c.get("architect"), c.get("year"), src,
                                             verify) if v)
            e.append(_t(x, 278, fw, 30, meta, size=9.5, color=th.muted, lh=1.5))
            yy = 316.0
            for label, getter in rows_of:
                text = getter(c)
                if not text:
                    continue
                e.append(_t(x, yy, fw, 14, label, size=9.5, color=th.accent,
                            weight=600, spacing=1.1))
                e.append(_t(x, yy + 16, fw, 62, text, size=10.5, color=th.ink, lh=1.55))
                yy += 86
            url = str(c.get("url") or "")
            e.append(_t(x, 664, fw, 14, _clip(url, 46), size=8.5, color=th.muted))
        if page.foot:
            e.append(_t(M, 690, 900, 14, _clip(page.foot, 52), size=9, color=th.muted))
        return e

    if k == "tensions":
        y = 200.0
        for i, b in enumerate(page.blocks[:4]):
            yy = y + i * 112
            e.append({"t": "rule", "x": M, "y": yy - 22, "w": 1152, "h": 1,
                      "color": th.line})
            e.append(_t(M, yy, 120, 14, b.label, size=10, color=th.accent,
                        weight=600, spacing=1.2))
            e.append(_t(M + 130, yy - 4, 1000, 76, b.text, size=14.5, color=th.ink,
                        lh=1.7))
        if page.foot:
            e.append(_t(M, 682, 900, 14, _clip(page.foot, 52), size=9, color=th.muted))
        return e

    if k == "recommend":
        y = 200.0
        for i, b in enumerate(page.blocks):
            if b.num:
                e.append(_t(M, y, 34, 18, b.num, size=11.5, color=th.accent, weight=700))
            e.append(_t(M + 40, y, 620, 16, b.label.upper(), size=10, color=th.accent,
                        weight=600, spacing=1.3))
            e.append(_t(M + 40, y + 18, 620, 64, b.text, size=13, color=th.ink, lh=1.6))
            y += 92 if b.num else 76
        x2 = 760.0
        e.append(_t(x2, 200, 420, 16, "下一步（G2 之后）".upper(), size=10, color=th.accent,
                    weight=600, spacing=1.3))
        for i, s in enumerate(page.steps[:4]):
            yy = 226 + i * 62
            e.append(_t(x2, yy, 26, 18, f"{i + 1}", size=11, color=th.accent, weight=700))
            e.append(_t(x2 + 28, yy, 392, 56, s, size=12, color=th.ink, lh=1.5))
        if page.foot:
            e.append(_t(M, 676, 1152, 16, page.foot, size=9.5, color=th.muted))
        return e

    if k == "appendix":
        y = 186.0
        for i, b in enumerate(page.blocks):
            yy = y + i * (96 if i < 4 else 120)
            e.append(_t(M, yy, 200, 16, b.label.upper(), size=10, color=th.accent,
                        weight=600, spacing=1.3))
            e.append(_t(M + 210, yy - 2, 940, 84, b.text, size=12, color=th.ink, lh=1.65))
        if page.foot:
            e.append(_t(M, 676, 1152, 16, page.foot, size=9.5, color=th.muted))
        return e

    return e


# --------------------------------------------------------------------------
# HTML
# --------------------------------------------------------------------------
_CSS = """
:root{
  --paper:%(paper)s; --ink:%(ink)s; --muted:%(muted)s; --line:%(line)s;
  --accent:%(accent)s; --serif:%(serif)s; --sans:%(sans)s;
}
*{box-sizing:border-box;margin:0;padding:0}
html,body{background:#1b1d1a;color:var(--ink);font-family:var(--sans);
  -webkit-font-smoothing:antialiased}
#deck{display:flex;flex-direction:column;align-items:center;gap:24px;padding:24px 0 64px}
.page{width:%(w)dpx;height:%(h)dpx;background:var(--paper);position:relative;
  overflow:hidden;flex:0 0 auto;box-shadow:0 18px 60px rgba(0,0,0,.35)}
.page .el{position:absolute}
.page .text{white-space:pre-wrap;word-break:break-word}
.page .rule{background:var(--line);height:1px}
.page .img{background-size:cover;background-position:center;background-repeat:no-repeat}
.num{position:absolute;right:%(m)dpx;bottom:26px;font-size:10px;color:var(--muted);
  letter-spacing:.14em}
.wm{position:absolute;left:%(m)dpx;bottom:26px;font-size:10px;color:var(--muted);
  letter-spacing:.06em}
#bar{position:fixed;left:0;right:0;bottom:0;height:34px;background:rgba(16,18,16,.92);
  color:#cfcabf;font:11px/34px var(--sans);text-align:center;letter-spacing:.08em;z-index:9}
#bar b{color:#fff;font-weight:600}
#nav{position:fixed;right:18px;bottom:44px;display:flex;gap:8px;z-index:9}
#nav button{width:32px;height:32px;border:1px solid #4a4d48;background:#22251f;color:#ddd;
  border-radius:50%%;cursor:pointer;font-size:13px}
@media print{
  html,body{background:#fff}
  #bar,#nav{display:none}
  #deck{gap:0;padding:0}
  .page{box-shadow:none;page-break-after:always;break-after:page}
  @page{size:%(w)dpx %(h)dpx;margin:0}
}
"""

_JS = """
(function(){
  const pages=[...document.querySelectorAll('.page')];
  let i=0;
  function fit(){
    const s=Math.min(1,(window.innerWidth-48)/%(w)d);
    pages.forEach(p=>p.style.transform='scale('+s+')');
    document.getElementById('deck').style.gap=(24*s)+'px';
  }
  function go(n){i=Math.max(0,Math.min(pages.length-1,n));
    pages[i].scrollIntoView({behavior:'smooth',block:'center'});}
  document.addEventListener('keydown',e=>{
    if(e.key==='ArrowRight'||e.key==='ArrowDown'||e.key===' '){e.preventDefault();go(i+1);}
    if(e.key==='ArrowLeft'||e.key==='ArrowUp'){e.preventDefault();go(i-1);}
  });
  window.addEventListener('resize',fit);
  document.getElementById('prev').onclick=()=>go(i-1);
  document.getElementById('next').onclick=()=>go(i+1);
  window.addEventListener('scroll',()=>{
    let best=0,bd=1e9;
    pages.forEach((p,k)=>{const r=p.getBoundingClientRect();
      const d=Math.abs(r.top+r.height/2-window.innerHeight/2);
      if(d<bd){bd=d;best=k;}});
    i=best;
  },{passive:true});
  fit();
})();
"""


def _esc(s: str) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def _el_html(el: Dict[str, Any], th: Theme, idx: int, total: int, base: str,
             page: Page) -> str:
    x, y, w, h = el["x"], el["y"], el["w"], el["h"]
    pos = f"left:{x:.1f}px;top:{y:.1f}px;width:{w:.1f}px;height:{h:.1f}px;"
    if el["t"] == "rect":
        op = el.get("opacity", 1)
        return f'<div class="el" style="{pos}background:{el["fill"]};opacity:{op}"></div>'
    if el["t"] == "rule":
        return f'<div class="el rule" style="left:{x:.1f}px;top:{y:.1f}px;width:{w:.1f}px"></div>'
    if el["t"] == "img":
        rel = Path(el["path"]).resolve()
        try:
            src = rel.relative_to(Path(base).resolve()).as_posix()
        except ValueError:
            src = rel.as_uri()
        return f'<div class="el img" style="{pos}background-image:url(\'{src}\')"></div>'
    color = el.get("color") or th.ink
    font = "var(--serif)" if el.get("font") == "serif" else "var(--sans)"
    lh = el.get("lh", 1.7)
    sp = el.get("spacing", 0)
    return (f'<div class="el text" style="{pos}font-family:{font};'
            f'font-size:{el["size"]}px;line-height:{lh};color:{color};'
            f'font-weight:{el.get("weight", 400)};'
            f'letter-spacing:{sp}px">{_esc(el.get("text", ""))}</div>')


def write_html(model: Dict[str, Any], out_dir: str | Path, *, title: str = "") -> str:
    out = Path(out_dir)
    th: Theme = model["theme"]
    css = _CSS % {"paper": th.paper, "ink": th.ink, "muted": th.muted, "line": th.line,
                  "accent": th.accent, "serif": SERIF, "sans": SANS,
                  "w": PAGE_W, "h": PAGE_H, "m": M}
    pages = model.get("pages") or []
    body: List[str] = []
    for i, p in enumerate(pages, start=1):
        els = "".join(_el_html(el, th, i, len(pages), str(out), p) for el in layout(p, th))
        wm = ('<div class="wm">OmniAiLab AI Architect</div>'
              if p.kind == "appendix" else "")
        body.append(f'<section class="page" data-i="{i}">{els}{wm}'
                    f'<div class="num">{i:02d} / {len(pages):02d}</div></section>')
    html = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{_esc(title or '概念设计汇报')}</title>
<style>{css}</style></head>
<body><div id="deck">{''.join(body)}</div>
<div id="bar">← → 翻页　｜　{_esc(title)}　｜　<b>{len(pages)}</b> 页 ·
概念方向表达，不作尺寸依据</div>
<div id="nav"><button id="prev">◀</button><button id="next">▶</button></div>
<script>{_JS % {"w": PAGE_W}}</script></body></html>"""
    path = out / FILE_HTML
    path.write_text(html, encoding="utf-8")
    return str(path)


# --------------------------------------------------------------------------
# PPTX
# --------------------------------------------------------------------------
def _px(v: float) -> int:
    return int(round(v * 9525))


def _rgb(hexv: str) -> Tuple[int, int, int]:
    h = hexv.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def write_pptx(model: Dict[str, Any], out_dir: str | Path, *, title: str = "") -> Dict[str, Any]:
    """真·可编辑 PPTX：文字是文本框，图是图片对象（不是整页贴图）。"""
    out = Path(out_dir)
    try:
        from pptx import Presentation
        from pptx.dml.color import RGBColor
        from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
        from pptx.util import Emu, Pt
    except Exception as exc:              # noqa: BLE001
        return {"ok": False, "reason": f"python-pptx 不可用：{exc}"}
    from PIL import Image

    th: Theme = model["theme"]
    prs = Presentation()
    prs.slide_width = Emu(_px(PAGE_W))
    prs.slide_height = Emu(_px(PAGE_H))
    blank = prs.slide_layouts[6]
    font_serif = "宋体"
    font_sans = "微软雅黑"

    for p in model.get("pages") or []:
        slide = prs.slides.add_slide(blank)
        # 背景
        bg = slide.shapes.add_shape(1, 0, 0, Emu(_px(PAGE_W)), Emu(_px(PAGE_H)))
        bg.fill.solid()
        bg.fill.fore_color.rgb = RGBColor(*_rgb(th.paper))
        bg.line.fill.background()
        bg.shadow.inherit = False
        for el in layout(p, th):
            if el["t"] == "rect":
                sh = slide.shapes.add_shape(1, Emu(_px(el["x"])), Emu(_px(el["y"])),
                                            Emu(_px(el["w"])), Emu(_px(el["h"])))
                sh.fill.solid()
                sh.fill.fore_color.rgb = RGBColor(*_rgb(el["fill"]))
                sh.line.fill.background()
                sh.shadow.inherit = False
            elif el["t"] == "rule":
                sh = slide.shapes.add_shape(1, Emu(_px(el["x"])), Emu(_px(el["y"])),
                                            Emu(_px(el["w"])), Emu(9525))
                sh.fill.solid()
                sh.fill.fore_color.rgb = RGBColor(*_rgb(el.get("color") or th.line))
                sh.line.fill.background()
                sh.shadow.inherit = False
            elif el["t"] == "img":
                path = el["path"]
                try:
                    with Image.open(path) as im:
                        iw, ih = im.size
                except Exception:         # noqa: BLE001
                    continue
                box_w, box_h = el["w"], el["h"]
                target = box_w / box_h
                src = iw / ih if ih else target
                if el.get("fit") == "contain":
                    # 图纸不裁边：等比缩进框内并居中
                    scale = min(box_w / iw, box_h / ih)
                    w2, h2 = iw * scale, ih * scale
                    slide.shapes.add_picture(
                        path, Emu(_px(el["x"] + (box_w - w2) / 2)),
                        Emu(_px(el["y"] + (box_h - h2) / 2)),
                        Emu(_px(w2)), Emu(_px(h2)))
                    continue
                pic = slide.shapes.add_picture(path, Emu(_px(el["x"])), Emu(_px(el["y"])),
                                               Emu(_px(box_w)), Emu(_px(box_h)))
                if src > target:          # 图更宽 → 左右裁
                    cut = (1 - target / src) / 2
                    pic.crop_left = cut
                    pic.crop_right = cut
                elif src < target:        # 图更高 → 上下裁（略偏上）
                    cut = (1 - src / target) / 2
                    pic.crop_top = cut * 0.86
                    pic.crop_bottom = cut * 1.14
            else:
                tb = slide.shapes.add_textbox(Emu(_px(el["x"])), Emu(_px(el["y"])),
                                              Emu(_px(el["w"])), Emu(_px(el["h"])))
                tf = tb.text_frame
                tf.word_wrap = True
                tf.margin_left = 0
                tf.margin_right = 0
                tf.margin_top = 0
                tf.margin_bottom = 0
                tf.vertical_anchor = MSO_ANCHOR.TOP
                para = tf.paragraphs[0]
                para.alignment = PP_ALIGN.LEFT
                para.line_spacing = float(el.get("lh", 1.7))
                run = para.add_run()
                run.text = str(el.get("text", ""))
                f = run.font
                f.size = Pt(float(el["size"]) * 0.75)
                f.bold = int(el.get("weight", 400)) >= 600
                f.name = font_serif if el.get("font") == "serif" else font_sans
                f.color.rgb = RGBColor(*_rgb(el.get("color") or th.ink))
                # 字距（PPTX 没有直接 API，用 XML 属性）
                sp = float(el.get("spacing", 0) or 0)
                if sp:
                    try:
                        run.font._rPr.set("spc", str(int(sp * 100)))   # noqa: SLF001
                    except Exception:                                  # noqa: BLE001
                        pass
        if p.notes:
            slide.notes_slide.notes_text_frame.text = p.notes

    path = out / FILE_PPTX
    prs.save(str(path))
    try:
        n = len(prs.slides._sldIdLst)          # noqa: SLF001  官方未暴露计数
    except Exception:                          # noqa: BLE001
        n = len(model.get("pages") or [])
    return {"ok": True, "path": str(path), "slides": n}


# --------------------------------------------------------------------------
# Markdown（附录/检索用，不替代汇报）
# --------------------------------------------------------------------------
def write_markdown(model: Dict[str, Any], out_dir: str | Path) -> str:
    out = Path(out_dir)
    lines: List[str] = ["# 概念汇报（逐页文字稿）", "",
                        "> 汇报以 HTML/PPTX 为准；本文件只做检索与留档。", ""]
    for i, p in enumerate(model.get("pages") or [], start=1):
        lines.append(f"## {i:02d}　{p.kicker}　{p.title}")
        lines.append("")
        if p.lead:
            lines.append(p.lead)
            lines.append("")
        for f in p.figures:
            lines.append(f"- 图：{f.caption}　（{f.credit}）")
        for b in p.blocks:
            lines.append(f"- **{b.label}**：{b.text}")
        for s in p.steps:
            lines.append(f"- {s}")
        if p.swatches:
            lines.append("- 色板：" + "、".join(f"{s['name']} {s['hex']}" for s in p.swatches))
        if p.foot:
            lines.append("")
            lines.append(f"_{p.foot}_")
        lines.append("")
    path = out / FILE_MD
    path.write_text("\n".join(lines), encoding="utf-8")
    return str(path)


__all__ = ["FILE_HTML", "FILE_MD", "FILE_PPTX", "PAGE_H", "PAGE_W", "Block", "Figure",
           "Page", "Theme", "build", "layout", "release", "theme_from", "write_html",
           "write_markdown", "write_pptx"]
