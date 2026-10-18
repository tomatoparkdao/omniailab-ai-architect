"""Moodboard：从 Markdown 骨架升级为可交付的视觉板。

六格结构来自 `registry.DESIGN_CRITERIA` 的意向板协议，但内容全部取自**风格库的
真实记录**：色值来自 `color_palette.hex`，材料来自 `materials[]`，气质来自
`positive_prompt_components`，光来自 `lighting_strategy.principles`。

产出的 SVG 是确定性绘制的：色块用声明的 hex 与占比，材料用可辨认的肌理图案，
文字写清"这块材料用在哪"。没有摄影感的氛围图 —— 那需要 AI 生成，属于另一类
成果（`visual.py`），两者在文件与状态上严格分开，不互相冒充。

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from . import palette as pal
from .diagrams import C_ACCENT, C_INK, C_LIGHT, C_MUTED, C_RULE, Svg, _dw, _fit, _header

#: 六格协议：与判据文档一一对应
SLOTS: Tuple[Tuple[str, str, str], ...] = (
    ("core_image", "① 主空间意象", "这一套要让人记住的那一眼"),
    ("colour", "② 色彩与比例", "主/次/点缀的占比，按风格库声明"),
    ("material", "③ 材料与质感", "4–6 块，写清用在哪里"),
    ("atmosphere", "④ 空间氛围", "气质关键词与排除项"),
    ("furniture", "⑤ 家具与造型语言", "体量、线条、落地或悬空"),
    ("light", "⑥ 照明与光线方向", "光从哪来、落在哪、什么色温"),
)

#: 参考案例是**第七格**，但它不是「图」：第三方作品只以卡片形式出现。
#: 单列出来是为了不说谎——意向板上的六格全是本系统确定性绘制的，
#: 案例卡上面没有图，只有标题、来源链接和一句"借什么"。
CASE_SLOT = ("reference", "⑦ 参考案例", "只给链接与说明，不嵌入第三方图片")



def _prompts(style_doc: Dict[str, Any], lang: str = "zh") -> Dict[str, str]:
    comp = (style_doc.get("positive_prompt_components") or {}).get(lang) or {}
    return {k: str(v) for k, v in comp.items()}


def _negatives(style_doc: Dict[str, Any]) -> List[str]:
    neg = (style_doc.get("negative_constraints") or {}).get("zh") or []
    if not neg:
        neg = style_doc.get("incompatible_elements") or []
    return [str(x) for x in neg][:4]


def build_slots(concept: Dict[str, Any], style_doc: Dict[str, Any],
                policy: Dict[str, Any]) -> Dict[str, Any]:
    """Fill the six slots from real style data; empty slots stay empty, not invented."""
    comp = _prompts(style_doc)
    plan = policy.get("palette") or pal.palette_plan(style_doc)
    entries = plan.get("entries") or []
    mats = concept.get("material_direction") or []
    lights = concept.get("lighting_direction") or []
    furn = [str(x) for x in (style_doc.get("furniture_language") or [])][:3]
    spatial = [str(x) for x in (style_doc.get("spatial_principles") or [])][:2]

    return {
        "core_image": {
            "title": SLOTS[0][1],
            "lead": comp.get("space") or (spatial[0] if spatial else ""),
            "detail": concept["concept_statement"],
            "source": "风格库 positive_prompt_components.space + 概念主张",
        },
        "colour": {
            "title": SLOTS[1][1],
            "lead": f"配色关系：{policy.get('ratio_rule')}",
            "entries": entries,
            "detail": ("　".join(f"{e['name']} {e['pct']}%" for e in entries if e["pct"])
                       or "风格库未声明占比，仅给出色彩关系"),
            "source": plan.get("source", ""),
        },
        "material": {
            "title": SLOTS[2][1],
            "lead": "、".join(m["name"] for m in mats) or "材料待定",
            "entries": mats,
            "detail": comp.get("material", ""),
            "source": "风格库 materials[]",
        },
        "atmosphere": {
            "title": SLOTS[3][1],
            "lead": " · ".join(str(t) for t in (style_doc.get("tags") or [])[:4]),
            "detail": "排除：" + "；".join(_negatives(style_doc)) if _negatives(style_doc) else "",
            "source": "风格库 tags + negative_constraints",
        },
        "furniture": {
            "title": SLOTS[4][1],
            "lead": furn[0] if furn else comp.get("furniture", ""),
            "detail": "；".join(furn[1:]),
            "source": "风格库 furniture_language[]",
        },
        "light": {
            "title": SLOTS[5][1],
            "lead": lights[0] if lights else "",
            "detail": "；".join(lights[1:]) if len(lights) > 1 else "",
            "source": "概念原型 daylight + 风格库 lighting_strategy",
        },
    }


def case_slot(references: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """The seventh cell: what we looked at, as a citation rather than a picture.

    Empty when there is no case — a board with nothing to cite says so by
    omitting the cell, instead of filling it with a vague sentence.
    """
    refs = (references or {}).get("cases") or []
    if not refs:
        return {}
    names = [str(r.get("title") or "") for r in refs if r.get("title")]
    borrow: List[str] = []
    for r in refs:
        for b in (r.get("borrow") or [])[:1]:
            if b:
                borrow.append(str(b))
    return {
        "title": CASE_SLOT[1],
        "lead": "　／　".join(names[:3]) or "—",
        "detail": "；".join(borrow[:2]),
        "links": [str(r.get("url")) for r in refs if r.get("url")],
        "source": "S1 案例研究（reference-shortlist）；图为第三方作品，只给链接",
        "embeddable": False,
    }


def _swatch_label(entry: Dict[str, Any]) -> str:
    pct = f"{entry['pct']}%" if entry.get("pct") else "—"
    return f"{entry['name']}　{entry['hex']}　{pct}"


def render_svg(concept: Dict[str, Any], style_doc: Dict[str, Any],
               slots: Dict[str, Any], ctx: Any) -> str:
    """One page: colour bands, material chips, and the four text slots."""
    style_label = " + ".join(concept.get("style_labels") or []) or style_doc.get("display_name_zh", "")
    s = Svg(width=1200, height=900,
            title=f"{concept['concept_id']} 意向板",
            subtitle=f"{concept['concept_name']} · {style_label}")
    _header(s, f"{concept['concept_name']} · 意向板",
            f"风格：{style_label}　配色关系：{concept.get('aesthetic_policy', {}).get('ratio_rule', '')}",
            "本系统确定性绘制 · 色值取自风格库")

    entries = (slots.get("colour") or {}).get("entries") or []
    # ① 色带
    y = 130
    s.text(56, y, "① 色彩与比例", size=14, weight="600")
    s.text(1200 - 56, y, "占比取自风格库声明", size=10, color=C_MUTED, anchor="end")
    bw = (1200 - 112) / max(1, len(entries)) if entries else 0
    for i, e in enumerate(entries[:6]):
        x = 56 + i * bw
        s.rect(x + 4, y + 14, bw - 8, 96, fill=e["hex"], stroke=C_RULE, sw=1, rx=4)
        s.text(x + 8, y + 130, _fit(_swatch_label(e), int(bw / 7)), size=11, color=C_INK)
        s.text(x + 8, y + 146, _fit(e.get("usage", ""), int(bw / 6.4)), size=10, color=C_MUTED)

    # ② 材料块
    y2 = y + 190
    s.text(56, y2, "③ 材料与质感", size=14, weight="600")
    mats = (slots.get("material") or {}).get("entries") or []
    mw = (1200 - 112) / max(1, len(mats)) if mats else 0
    for i, m in enumerate(mats[:5]):
        x = 56 + i * mw
        s.rect(x + 4, y2 + 14, mw - 8, 84, fill="#F1F1EE", stroke=C_INK, sw=1.1, rx=4)
        # 肌理：细斜线，仅作"这是材料样板"的提示，不假装真实材质照片
        for k in range(6):
            s.line(x + 10 + k * (mw - 20) / 6, y2 + 88,
                   x + 10 + k * (mw - 20) / 6 + 24, y2 + 22,
                   stroke=C_RULE, sw=0.7)
        s.text(x + 10, y2 + 118, _fit(m["name"], int(mw / 7)), size=12, weight="600")
        s.text(x + 10, y2 + 136, _fit(m.get("application", ""), int(mw / 6.4)),
               size=10, color=C_MUTED)
        s.text(x + 10, y2 + 152, _fit(m.get("finish", ""), int(mw / 6.4)),
               size=10, color=C_MUTED)

    # ③ 四个文字格
    y3 = y2 + 200
    cells = [("core_image", slots.get("core_image") or {}),
             ("atmosphere", slots.get("atmosphere") or {}),
             ("furniture", slots.get("furniture") or {}),
             ("light", slots.get("light") or {})]
    cw = (1200 - 112) / 2 - 14
    for i, (key, slot) in enumerate(cells):
        x = 56 + (i % 2) * (cw + 28)
        yy = y3 + (i // 2) * 132
        s.rect(x, yy, cw, 118, fill="#FFFFFF", stroke=C_RULE, sw=1, rx=6)
        s.text(x + 14, yy + 24, slot.get("title", key), size=12, color=C_ACCENT, weight="600")
        lead = slot.get("lead") or "—"
        s.text(x + 14, yy + 50, _fit(lead, int((cw - 28) / 7)), size=12, weight="500")
        detail = slot.get("detail") or ""
        if detail:
            s.text(x + 14, yy + 72, _fit(detail, int((cw - 28) / 6.6)), size=10, color=C_MUTED)
            s.text(x + 14, yy + 90, _fit(detail[int(len(detail) / 2):] if len(detail) > 40 else "",
                                        int((cw - 28) / 6.6)), size=10, color=C_MUTED)

    s.text(56, 892 - 46, "图像位：主空间意象 / 材料场景 / 光的性格 由 OmniAiLab 平台生成，"
                         "未生成时标 awaiting_platform，不以占位图冒充。",
           size=10, color=C_MUTED)
    s.text(56, 892 - 28, ctx.dimensional_note, size=10, color=C_MUTED)
    return s.render()


def markdown(concept: Dict[str, Any], style_doc: Dict[str, Any],
             slots: Dict[str, Any], policy: Dict[str, Any],
             references: Optional[Dict[str, Any]] = None) -> str:
    lines = [
        f"# 意向板 · {concept['concept_id']} {concept['concept_name']}",
        "",
        f"> {concept['concept_statement']}",
        "",
        f"**风格**：{' + '.join(concept.get('style_labels') or [])}　"
        f"**配色关系**：{policy.get('ratio_rule')}",
        "",
        "| 格位 | 内容 | 依据 |",
        "|---|---|---|",
    ]
    for _key, title, _hint in SLOTS:
        slot = slots.get(_key) or {}
        body = slot.get("lead") or "—"
        if slot.get("detail"):
            body += f"（{slot['detail']}）"
        lines.append(f"| {title} | {_fit(body, 58)} | {slot.get('source', '')} |")

    colour = (slots.get("colour") or {}).get("entries") or []
    if colour:
        lines += ["", "## 色板（取自风格库声明）", "",
                  "| 颜色 | 色值 | 占比 | 用法 |", "|---|---|---|---|"]
        lines += [f"| {e['name']} | `{e['hex']}` | {e['pct'] or '—'} | {e.get('usage', '')} |"
                  for e in colour]

    mats = (slots.get("material") or {}).get("entries") or []
    if mats:
        lines += ["", "## 材料", "", "| 材料 | 用在 | 做法 |", "|---|---|---|"]
        lines += [f"| {m['name']} | {m['application']} | {m['finish']} |" for m in mats]

    checks = (concept.get("palette") or {}).get("checks") or []
    if checks:
        lines += ["", "## 判据校核（只对适用项）", "", "| 判据 | 结果 | 说明 |", "|---|---|---|"]
        for c in checks:
            verdict = "通过" if c.get("ok") else ("不通过" if c.get("evaluated") else "无法校核")
            lines.append(f"| {c['rule_id']} | {verdict} | {c['detail']} |")

    lines += ["", "> 图像位（主空间意象 / 材料场景 / 光的性格）由 OmniAiLab 平台生成；"
                  "未生成时状态为 awaiting_platform，不以占位图替代。"]

    refs = (references or {}).get("cases") or []
    if refs:
        lines += ["", "## ⑦ 参考案例（只给链接，不嵌图）", "",
                  "| 案例 | 事务所 | 为什么看它 | 链接 |", "|---|---|---|---|"]
        for r in refs:
            lines.append("| {} | {} | {} | {} |".format(
                _fit(str(r.get("title") or ""), 28),
                _fit(str(r.get("architect") or "—"), 18),
                _fit(str(r.get("why") or ""), 34),
                r.get("url") or ""))
        lines += ["", "> 以上图为第三方作品，权利属原作者与摄影师；"
                      "本意向板不放它们的图片，只提供链接供你打开核对。"]
    return "\n".join(lines)


def image_slots(concept: Dict[str, Any]) -> List[Dict[str, str]]:
    """Which photographic slots this concept still needs. No images are faked."""
    return [
        {"slot": "core_image", "label": "主空间意象",
         "intent": f"{concept['concept_name']}：{concept['concept_statement']}",
         "target": "moodboard"},
        {"slot": "material_scene", "label": "材料场景",
         "intent": "材料组合在真实光线下的关系，用于判断质感是否成立",
         "target": "moodboard"},
        {"slot": "light_character", "label": "光的性格",
         "intent": "一个发光的面与它的落点，用于确认光的方向与色温",
         "target": "moodboard"},
    ]


def build(concept: Dict[str, Any], style_doc: Dict[str, Any],
          policy: Dict[str, Any], ctx: Any, out_dir: str | Path,
          references: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Render the board. ``references`` is the concept's case attachment.

    The attachment is *printed*, never drawn: a board that puts a third-party
    photograph next to our own colour bands would imply the photo is ours.
    """
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    slots = build_slots(concept, style_doc, policy)
    slot_ref = case_slot(references)
    if slot_ref:
        slots[CASE_SLOT[0]] = slot_ref
    svg = render_svg(concept, style_doc, slots, ctx)
    svg_path = out / f"mb-{concept['concept_id'].lower()}.svg"
    svg_path.write_text(svg, encoding="utf-8")
    md_path = out / f"mb-{concept['concept_id'].lower()}.md"
    md_path.write_text(markdown(concept, style_doc, slots, policy, references),
                       encoding="utf-8")
    return {
        "concept_id": concept["concept_id"],
        "style_ids": concept.get("style_ids") or [],
        "slots": slots,
        "board_svg": str(svg_path),
        "board_md": str(md_path),
        "image_slots": image_slots(concept),
        "reference_cards": len((references or {}).get("cases") or []),
        "status": "colour_and_material_ready",
        "note": "色板与材料板为本系统确定性绘制；氛围摄影图需平台生成，状态另行登记。"
                "参考案例只以链接卡片出现，第三方图片不进版面。",
    }


__all__ = ["SLOTS", "CASE_SLOT", "build", "build_slots", "case_slot",
           "render_svg", "markdown", "image_slots"]
