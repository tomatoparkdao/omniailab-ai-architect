"""案例可视化：让客户看见"手法"，而不是看见一张我们无权使用的照片。

案例卡片此前只有一个链接和一段说明。客户点开才看得到东西，等于没给。但把
ArchDaily 的照片拖进提案是另一条错路：照片的权利属摄影师与原作者，方案里
嵌一张来源不明的图，交付出去就是把风险转给业主。

所以这里只做三件能负责的事：

1. **读案例自己的文字，提炼手法。** 命中词必须是案例页面真的写了的（`title`
   / `summary`），命不中就画"空间关系示意"，不编一个手法出来。
2. **把手法画成我们自己的图。** 确定性 SVG，几何来自手法本身（院是围合、
   退台是逐层后退、架空是柱与板的分离）。图上明写"本系统绘制，非原案例照片"。
3. **照片只在拿到许可时才出现。** 项目目录里放 `references/credits.json` 并
   登记 `license` 与 `source_url`，才允许嵌入本地文件并署名；没有登记就只给
   来源入口。这个判断集中在 `resolve()`，调用方绕不过去。

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ..concept.deliberation import PRECEDENT_TERMS, _has_term
from ..concept.diagrams import (C_ACCENT, C_CIRC, C_INK, C_LIGHT, C_MUTED,
                                C_RULE, Svg, _fit)

PLATE_W, PLATE_H = 540, 372

#: 文案里的手法词 -> 可画的图元。图元名同时决定"同义手法只画一次"：
#: 案例写了 `pond` 又写了 `pool`，客户不需要看两个水池。
LABEL_KIND: Dict[str, str] = {
    "内院围合": "courtyard",
    "静水倒影": "water", "静水": "water", "水面": "water",
    "溪流": "stream", "旱溪": "dry", "砾石": "gravel",
    "退台": "terrace", "错层": "split",
    "架空": "pilotis", "架空悬浮": "pilotis",
    "林下": "canopy", "树冠": "canopy", "本土植物": "planting",
    "压缩释放": "compression", "门槛过渡": "compression",
    "连续开间": "openplan", "回游": "loop", "天光": "skylight",
    "独立体量": "cluster", "组团": "cluster",
}

#: 只在**图注**里用的补充词表。
#:
#: 为什么与 `deliberation.PRECEDENT_TERMS` 分开：那张表同时参与概念打分，往
#: 里加词会悄悄改变方案排序；而景观与体量的手法需要更细的词才能读出来
#: （`slope`、`retaining`、`vegetation` 这些词在案例描述里很常见）。两张表
#: 都只认案例原文，区别是一张用于排序、一张用于解释。
EXTRA_TERMS: Dict[str, str] = {
    "topography": "顺应地形", "slope": "顺应地形", "contour": "顺应地形",
    "hillside": "顺应地形", "hill": "顺应地形",
    "retaining": "挡土墙", "embankment": "挡土墙",
    "vegetation": "低植被", "shrub": "低植被", "meadow": "低植被",
    "garden": "花园", "green space": "大绿地", "green area": "大绿地",
    "park": "公园绿地",
    "path": "园路游线", "walkway": "园路游线", "footpath": "园路游线",
    "disappear": "体量消隐", "blend": "体量消隐", "buried": "体量消隐",
}
LABEL_KIND.update({
    "顺应地形": "contour", "挡土墙": "retain", "低植被": "planting",
    "花园": "garden", "大绿地": "green", "公园绿地": "green",
    "园路游线": "path", "体量消隐": "blend",
})

#: 画图顺序：先空间组织，再地形与界面，最后材料性的。客户先看懂"怎么组织"。
KIND_ORDER: Tuple[str, ...] = (
    "courtyard", "terrace", "split", "pilotis", "compression", "loop",
    "openplan", "skylight", "cluster", "blend", "contour", "retain",
    "water", "stream", "dry", "gravel", "path", "garden", "green",
    "canopy", "planting",
)

#: 图元的中文名（图注用）。与 `LABEL_KIND` 的值一一对应。
KIND_LABEL: Dict[str, str] = {
    "courtyard": "围合取院", "terrace": "逐层退台", "split": "错层",
    "pilotis": "底层架空", "compression": "压缩后释放", "loop": "回游动线",
    "openplan": "连续开间", "skylight": "顶部采光", "cluster": "分散体量",
    "blend": "体量消隐", "contour": "顺应地形", "retain": "挡土与分级",
    "water": "静水面", "stream": "线性水声", "dry": "旱溪", "gravel": "砾石铺地",
    "path": "园路游线", "garden": "种植花园", "green": "连续绿地",
    "canopy": "林下树冠", "planting": "本土植物", "axis": "空间关系",
}

#: 案例图片的权利状态。前两项可以出现在交付物里，后两项不行。
RIGHTS_LEGEND: Tuple[Tuple[str, str], ...] = (
    ("第三方案例", "照片权利属原作者与摄影师；本提案只给来源入口，不嵌入"),
    ("手法示意", "本系统按案例文字绘制的关系图，不是原案例照片"),
    ("原创意向", "OmniAiLab 原生画布生成，仅表达氛围，不是本项目效果图"),
    ("正式效果图", "G3 平面确认后生成，带机位与版本号，可作讨论依据"),
)


# --------------------------------------------------------------------------
# 1. 读案例文字，提炼手法
# --------------------------------------------------------------------------
def _text(case: Dict[str, Any]) -> str:
    return " ".join([str(case.get("title") or ""),
                     str(case.get("summary") or "")]).lower()


def _snippet(text: str, term: str, budget: int = 58) -> str:
    """案例原文里出现该词的那一小段，用来证明"这不是我们编的"。"""
    low = text.lower()
    i = low.find(term)
    if i < 0:
        return ""
    start = max(0, low.rfind(". ", 0, i) + 2)
    end = low.find(". ", i)
    end = len(text) if end < 0 else end + 1
    out = " ".join(text[start:end].split())
    if len(out) > budget:
        out = out[:budget].rstrip(" ,;:") + "…"
    return out


def techniques(case: Dict[str, Any], *, limit: int = 3) -> List[Dict[str, str]]:
    """案例自己写到的手法，按可画性排序，同一图元只留一次。

    一个手法都没命中时返回空表——调用方据此画"空间关系示意"，而不是硬塞
    一个看起来专业的词。空表是结论，不是故障。
    """
    hay = _text(case)
    if not hay.strip():
        return []
    found: Dict[str, Dict[str, str]] = {}
    terms: Dict[str, str] = dict(PRECEDENT_TERMS)
    terms.update(EXTRA_TERMS)
    for term, label in terms.items():
        kind = LABEL_KIND.get(label)
        if not kind or not _has_term(term, hay):
            continue
        rank = KIND_ORDER.index(kind) if kind in KIND_ORDER else 99
        prev = found.get(kind)
        if prev and int(prev["rank"]) <= rank:
            continue
        found[kind] = {
            "kind": kind,
            "label": label,
            "term": term,
            "evidence": _snippet(str(case.get("summary") or ""), term),
            "rank": str(rank),
        }
    items = sorted(found.values(), key=lambda d: int(d["rank"]))[:limit]
    for it in items:
        it.pop("rank", None)
    return items


# --------------------------------------------------------------------------
# 2. 把手法画出来（确定性，纯几何）
# --------------------------------------------------------------------------
def _draw(s: Svg, kind: str, x: float, y: float, w: float, h: float) -> None:
    """在 (x, y, w, h) 内画一个图元。所有坐标都是相对框算的。"""
    cx, cy = x + w / 2, y + h / 2
    if kind == "courtyard":
        s.rect(x + 8, y + 8, w - 16, h - 16, fill="none", stroke=C_INK, sw=1.6, rx=2)
        s.rect(cx - w * 0.20, y + 22, w * 0.40, h - 44, fill="#EFF3EC",
               stroke=C_ACCENT, sw=1.2, rx=2)
        s.text(cx, cy + 4, "院", size=13, anchor="middle", color=C_ACCENT)
        for i in range(3):  # 院墙厚度示意
            s.line(x + 8 + i * 3, y + 8, x + 8 + i * 3, y + h - 8, stroke=C_RULE, sw=1)
    elif kind in ("water", "stream", "dry", "gravel"):
        solid = kind in ("water", "stream")
        s.rect(x + 10, cy - h * 0.20, w - 20, h * 0.40,
               fill="#DCEAF5" if solid else "#F1EEE6",
               stroke="#9CC3DE" if solid else "#CFC6B4", sw=1.2, rx=4)
        for i in range(4 if solid else 9):
            yy = cy - h * 0.10 + i * (h * 0.075)
            if solid:
                s.line(x + 24, yy, x + w - 24, yy, stroke="#7FA8C9", sw=1, dash="6 6")
            else:
                for k in range(6):
                    px = x + 24 + k * (w - 48) / 5 + (i % 2) * 8
                    s.circle(px, yy, 2.2, fill="#BFB49C", stroke="none")
        if kind == "stream":
            s.polyline([(x + 14, cy + 6), (cx - 30, cy - 8), (cx + 20, cy + 10),
                        (x + w - 14, cy - 4)], stroke="#5F93BD", sw=1.6, arrow=False)
    elif kind in ("terrace", "split"):
        base_y = y + h - 18
        for i in range(3):
            bw = w * (0.72 - i * 0.14)
            bx = x + (w - bw) / 2 + (i * 14 if kind == "terrace" else 0)
            bh = 16
            s.rect(bx, base_y - i * (bh + 4), bw, bh, fill="#FFFFFF" if i % 2 == 0 else "#F0EFEA",
                   stroke=C_INK, sw=1.2, rx=1)
        if kind == "split":
            s.line(x + 18, base_y + 6, x + w - 18, base_y + 6, stroke=C_INK, sw=1.8)
            s.line(cx, base_y + 6, cx, base_y - 18, stroke=C_CIRC, sw=1.4, arrow=True)
    elif kind == "pilotis":
        s.rect(x + 14, cy - 16, w - 28, 14, fill="#FFFFFF", stroke=C_INK, sw=1.4, rx=1)
        s.rect(x + 24, cy - 54, w - 48, 34, fill="none", stroke=C_INK, sw=1.2, rx=1)
        for i in range(4):
            px = x + 32 + i * (w - 64) / 3
            s.line(px, cy - 2, px, y + h - 16, stroke=C_INK, sw=2.2)
        s.line(x + 10, y + h - 16, x + w - 10, y + h - 16, stroke=C_INK, sw=1.8)
        s.text(x + w - 12, y + h - 22, "地面", size=9, anchor="end", color=C_MUTED)
    elif kind == "compression":
        s.rect(x + 12, y + 14, w * 0.30, h - 28, fill="#E8E2D2", stroke=C_INK, sw=1.2, rx=1)
        s.rect(x + w * 0.42, y + 30, w * 0.18, h - 60, fill="#FFFFFF", stroke=C_INK, sw=1.2, rx=1)
        s.rect(x + w * 0.60, y + 8, w * 0.30, h - 16, fill="#EFF3EC", stroke=C_ACCENT, sw=1.2, rx=1)
        s.line(x + 18, cy, x + w - 18, cy, stroke=C_CIRC, sw=1.6, arrow=True)
        s.text(x + w * 0.78, cy + 4, "释放", size=10, anchor="middle", color=C_ACCENT)
    elif kind == "loop":
        s.rect(x + w * 0.22, y + 12, w * 0.56, h - 24, fill="none", stroke=C_RULE, sw=12, rx=6)
        s.polyline([(cx, y + 18), (x + w * 0.80, y + 18), (x + w * 0.80, y + h - 18),
                    (x + w * 0.22, y + h - 18), (x + w * 0.22, y + 22)],
                   stroke=C_CIRC, sw=2.2)
        s.text(cx, cy + 4, "回游", size=11, anchor="middle", color=C_CIRC)
    elif kind == "openplan":
        s.rect(x + 12, y + 16, w - 24, 12, fill="#FFFFFF", stroke=C_INK, sw=1.4, rx=1)
        s.rect(x + 12, y + h - 28, w - 24, 12, fill="#FFFFFF", stroke=C_INK, sw=1.4, rx=1)
        for i in range(5):
            px = x + 26 + i * (w - 52) / 4
            s.line(px, y + 28, px, y + h - 28, stroke=C_RULE, sw=1.4, dash="4 5")
        s.text(cx, cy + 4, "无隔断连续界面", size=10, anchor="middle", color=C_MUTED)
    elif kind == "skylight":
        s.polyline([(x + 14, y + h - 22), (cx, y + 18), (x + w - 14, y + h - 22)],
                   stroke=C_INK, sw=1.8, arrow=False)
        s.polyline([(cx - 40, y + 34), (cx - 10, y + 18), (cx + 40, y + 34)],
                   stroke=C_LIGHT, sw=2.4, arrow=False)
        s.rect(cx - 8, y + 30, 16, h - 56, fill=C_LIGHT, stroke="none", opacity=0.16, rx=2)
        s.line(x + 20, y + h - 22, x + w - 20, y + h - 22, stroke=C_INK, sw=1.8)
        s.text(cx, y + h - 8, "顶部补光", size=9, anchor="middle", color=C_MUTED)
    elif kind == "cluster":
        boxes = ((0.06, 0.28, 0.30, 0.44), (0.40, 0.10, 0.26, 0.38), (0.70, 0.34, 0.24, 0.40))
        for i, (fx, fy, fw, fh) in enumerate(boxes):
            s.rect(x + w * fx, y + h * fy, w * fw, h * fh,
                   fill="#FFFFFF" if i % 2 == 0 else "#F0EFEA", stroke=C_INK, sw=1.2, rx=1)
        s.line(x + w * 0.36, cy, x + w * 0.46, cy, stroke=C_CIRC, sw=1.4, arrow=True)
    elif kind in ("canopy", "planting"):
        for i in range(3):
            px = x + w * (0.22 + i * 0.28)
            s.line(px, y + h - 15, px, cy + 6, stroke="#7A8B72", sw=2)
            s.circle(px, cy - 2, 17 if kind == "canopy" else 11,
                     fill="#D8E6D2", stroke="#B9CDB2", sw=1)
        s.line(x + 12, y + h - 15, x + w - 12, y + h - 15, stroke=C_INK, sw=1.6)
        if kind == "planting":
            for k in range(7):
                px = x + 18 + k * (w - 36) / 6
                s.line(px, y + h - 15, px - 3, y + h - 30, stroke="#8FAF86", sw=1.2)
    elif kind == "contour":
        # 等高线压过场地：房子跟着等高线走，不是把地推平
        for i in range(4):
            yy = y + 20 + i * (h - 40) / 3
            s.path("M {:.1f} {:.1f} Q {:.1f} {:.1f} {:.1f} {:.1f} T {:.1f} {:.1f}".format(
                x + 12, yy, cx - w * 0.1, yy - 12, cx, yy,
                x + w - 12, yy + (6 if i % 2 else -6)),
                fill="none", stroke="#C7CFC4", sw=1.2)
        s.rect(cx - w * 0.12, y + h * 0.42, w * 0.24, h * 0.24, fill="#FFFFFF",
               stroke=C_INK, sw=1.4, rx=1)
    elif kind == "retain":
        s.line(x + 14, y + 16, x + 14, y + h - 16, stroke=C_INK, sw=2.4)
        s.rect(x + 14, cy - 6, w - 28, h * 0.42, fill="#EDEAE0", stroke=C_RULE, sw=1, rx=0)
        for i in range(5):
            s.line(x + 20 + i * 8, cy + 4, x + 30 + i * 8, cy + 18, stroke="#B9AC92", sw=1)
        s.line(x + 14, cy - 6, x + w - 14, cy - 6, stroke=C_INK, sw=1.6)
        s.line(x + 30, y + 20, x + 30, cy - 6, stroke=C_CIRC, sw=1.4, arrow=True)
        s.text(x + w - 16, y + 26, "上：台地", size=9, anchor="end", color=C_MUTED)
    elif kind == "path":
        s.path("M {:.1f} {:.1f} C {:.1f} {:.1f}, {:.1f} {:.1f}, {:.1f} {:.1f}".format(
            x + 16, y + h - 16, x + w * 0.35, y + h * 0.20,
            x + w * 0.62, y + h * 0.86, x + w - 16, y + 18),
            fill="none", stroke=C_CIRC, sw=2.6)
        for k in range(5):
            t = (k + 0.5) / 5
            px = x + 16 + (w - 32) * t
            py = y + h - 16 - (h - 34) * t + 8 * (1 if k % 2 else -1)
            s.circle(px, py, 3.4, fill="#FFFFFF", stroke=C_CIRC, sw=1.2)
    elif kind in ("garden", "green"):
        s.rect(x + 12, y + 12, w - 24, h - 24, fill="#F2F6EF", stroke="none", rx=6)
        for i in range(4 if kind == "garden" else 6):
            px = x + 30 + i * (w - 60) / (3 if kind == "garden" else 5)
            py = cy + (12 if i % 2 else -10)
            s.circle(px, py, 13 if kind == "garden" else 9,
                     fill="#D8E6D2", stroke="#B9CDB2", sw=1)
        if kind == "garden":
            for i in range(3):
                s.rect(x + 26 + i * (w - 52) / 3, y + h - 34, (w - 60) / 3, 12,
                       fill="#EDEAE0", stroke=C_RULE, sw=0.8, rx=1)
    elif kind == "blend":
        s.line(x + 10, cy, x + w - 10, cy, stroke=C_INK, sw=1.8, dash="10 5")
        s.rect(cx - w * 0.22, cy - 6, w * 0.44, h * 0.30, fill="#FFFFFF", stroke=C_INK, sw=1.4, rx=1)
        s.rect(cx - w * 0.22, cy + h * 0.24, w * 0.44, h * 0.10, fill="#E4E8DF",
               stroke="none", rx=0)
        for i in range(4):
            s.line(cx - w * 0.26 + i * 12, cy + 4, cx - w * 0.26 + i * 12, cy + h * 0.22,
                   stroke="#C7CFC4", sw=1, dash="3 4")
        s.text(x + 14, cy - 8, "室外地坪", size=9, color=C_MUTED)
    else:  # axis / 什么都没有
        s.line(x + 16, cy, x + w - 16, cy, stroke=C_INK, sw=1.2, dash="8 6")
        s.line(cx, y + 12, cx, y + h - 12, stroke=C_RULE, sw=1, dash="4 6")
        s.rect(cx - 34, cy - 26, 68, 52, fill="#FFFFFF", stroke=C_INK, sw=1.4, rx=2)
        s.text(cx, cy + 5, "空间", size=11, anchor="middle", color=C_MUTED)


def plate(case: Dict[str, Any], *, index: int = 1) -> str:
    """一张 540×372 的手法示意。

    尺寸按**卡片宽度**定：客户是在提案里看到它，不是在独立画布上。早先做成
    720 宽，嵌进两列卡片后被缩到 0.5，14px 的标注变成 7px，图上写了什么看不
    清——图有内容，但没传达出去。
    """
    techs = techniques(case) or [{"kind": "axis", "label": "空间关系",
                                  "term": "", "evidence": ""}]
    s = Svg(PLATE_W, PLATE_H, title="手法示意", bg="#FFFFFF")
    s.text(22, 30, "手法提炼", size=17, weight="600", color=C_INK)
    s.text(96, 30, _fit(str(case.get("title") or ""), 46), size=11, color=C_MUTED)
    s.text(PLATE_W - 22, 30, f"REF {index:02d}", size=11, anchor="end", color=C_RULE)
    s.line(22, 43, PLATE_W - 22, 43, stroke=C_RULE, sw=1)

    # 只有一条手法时，第二格放案例信息：留一块空白会让人以为图没画完。
    rows = list(techs[:3])
    if len(rows) < 2:
        rows.append({"kind": "info", "label": "案例信息", "term": "", "evidence": ""})

    band_h = (PLATE_H - 96) / len(rows)
    for i, t in enumerate(rows):
        top = 56 + i * band_h
        if i:
            s.line(22, top - 6, PLATE_W - 22, top - 6, stroke=C_RULE, sw=0.8, dash="3 5")
        if t["kind"] == "info":
            _info(s, case, 22, top + 8, PLATE_W - 44, band_h - 14)
            continue
        s.text(22, top + 20, f"{i + 1:02d}", size=11, color=C_RULE)
        s.text(22, top + 44, t["label"], size=20, weight="600", color=C_INK)
        s.text(22, top + 64, KIND_LABEL.get(t["kind"], ""), size=11, color=C_MUTED)
        _draw(s, t["kind"], 146, top, PLATE_W - 172, band_h - 8)

    s.line(22, PLATE_H - 34, PLATE_W - 22, PLATE_H - 34, stroke=C_RULE, sw=1)
    s.text(22, PLATE_H - 15,
           "本图按案例公开文字绘制，非原案例照片", size=10, color=C_MUTED)
    s.text(PLATE_W - 22, PLATE_H - 15, "非按比例", size=10, anchor="end", color=C_MUTED)
    return s.render()


def _info(s: Svg, case: Dict[str, Any], x: float, y: float,
          w: float, h: float) -> None:
    """案例的地点、年份与规模。读到什么印什么，读不到就跳过。"""
    s.text(x, y + 16, "案例信息", size=17, weight="600", color=C_INK)
    s.text(x, y + 36, "来源页面登记的公开字段", size=11, color=C_MUTED)
    rows = [("地点", "、".join([v for v in (case.get("city"), case.get("country")) if v])),
            ("年份", str(case.get("year") or "")),
            ("规模", str(case.get("area") or "")),
            ("专业", {"architecture": "建筑", "interior": "室内",
                      "landscape": "景观"}.get(str(case.get("discipline")), ""))]
    yy = y + 62
    for label, value in rows:
        if not value:
            continue
        s.text(x, yy, label, size=11, color=C_MUTED)
        s.text(x + 44, yy, _fit(value, 40), size=12, color=C_INK)
        yy += 22


# --------------------------------------------------------------------------
# 3. 决定这个案例能给你看什么
# --------------------------------------------------------------------------
_IMG_EXT = (".jpg", ".jpeg", ".png", ".webp", ".avif")


def _slug(case: Dict[str, Any]) -> str:
    url = str(case.get("url") or "")
    tail = url.rstrip("/").rsplit("/", 1)[-1]
    return re.sub(r"[^a-z0-9\-]+", "-", tail.lower()).strip("-")[:60] or "case"


def credits(project_dir: Optional[Path]) -> List[Dict[str, Any]]:
    """项目里登记过的授权图片。

    格式：``<project>/references/credits.json``
    ``{"images": [{"url": 案例链接, "file": "x.jpg", "license": "<许可证名称>",
                   "author": "摄影者", "source_url": "来源页面地址"}]}``

    声明 `license` 与 `source_url` 两样缺一不可：只写"可用"不算授权，
    将来没人能复核它到底谁给的。
    """
    if not project_dir:
        return []
    path = Path(project_dir) / "references" / "credits.json"
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    items = data.get("images") if isinstance(data, dict) else data
    out: List[Dict[str, Any]] = []
    for it in items or []:
        if not isinstance(it, dict):
            continue
        if not (it.get("license") and it.get("source_url") and it.get("file")):
            continue
        out.append(it)
    return out


def licensed_image(case: Dict[str, Any],
                   project_dir: Optional[Path]) -> Optional[Dict[str, Any]]:
    """已登记、且文件真的存在的授权图片；否则 None。"""
    url = str(case.get("url") or "")
    for it in credits(project_dir):
        if it.get("url") and it["url"] != url:
            continue
        f = Path(project_dir) / "references" / str(it["file"])
        if f.exists() and f.suffix.lower() in _IMG_EXT:
            return {**it, "path": f}
    return None


def resolve(case: Dict[str, Any], *, project_dir: Optional[Path] = None,
            index: int = 1) -> Dict[str, Any]:
    """一个案例在交付物里能呈现的样子。

    返回的 `kind` 只有两种取值：`licensed_photo`（有登记的授权图）与
    `original_plate`（本系统绘制的手法图）。**没有第三种"先放上来再说"**。
    """
    licensed = licensed_image(case, project_dir)
    if licensed:
        credit = "图：{}／{}（{}）".format(
            licensed.get("author") or "未署名", licensed.get("license"),
            licensed.get("source_url"))
        return {
            "kind": "licensed_photo",
            "image": str(licensed["path"]),
            "credit": credit,
            "rights": "licenced",
            "rights_label": "已登记授权",
            "note": "使用范围以登记文件为准",
            "techniques": techniques(case),
        }
    return {
        "kind": "original_plate",
        "svg": plate(case, index=index),
        "credit": "手法示意：本系统按案例公开文字绘制，非原案例照片。",
        "rights": "own",
        "rights_label": "本系统绘制",
        "note": "原案例照片请点开来源页",
        "techniques": techniques(case),
    }


__all__ = ["KIND_LABEL", "LABEL_KIND", "PLATE_H", "PLATE_W", "RIGHTS_LEGEND",
           "credits", "licensed_image", "plate", "resolve", "techniques"]
