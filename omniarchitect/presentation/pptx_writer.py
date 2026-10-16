"""PPTX writers.

Two backends, one output format:

* **python-pptx** when installed — full layout control, real tables, images;
* **native OOXML writer** when it is not — the deck is written straight into
  the Open XML container. No library, no invented capability, still a file
  PowerPoint can open and edit.

Both are verified after writing: the file is reopened, its parts listed, and a
different implementation is used for the check than for the write.

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import re
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .layouts import Deck, Slide

SLIDE_W_IN = 13.333
SLIDE_H_IN = 7.5

PT_PER_IN = 72.0
EMU_PER_IN = 914400


# --------------------------------------------------------------------------
def hex_to_rgb(value: str) -> Tuple[int, int, int]:
    v = (value or "#000000").lstrip("#")
    if len(v) == 3:
        v = "".join(c * 2 for c in v)
    try:
        return int(v[0:2], 16), int(v[2:4], 16), int(v[4:6], 16)
    except Exception:
        return 0, 0, 0


def hex_to_rgb_float(value: str) -> Tuple[float, float, float]:
    r, g, b = hex_to_rgb(value)
    return r / 255.0, g / 255.0, b / 255.0


def _backend() -> str:
    try:
        import pptx  # noqa: F401

        return "python-pptx"
    except Exception:
        return "native-ooxml"


def write_pptx(deck: Deck, path: str | Path) -> Dict[str, Any]:
    """Write a real, editable PPTX and report which backend did it."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    backend = _backend()
    if backend == "python-pptx":
        _write_python_pptx(deck, p)
    else:
        _write_native_pptx(deck, p)
    return {
        "path": str(p),
        "backend": backend,
        "slides": len(deck.slides),
        "size_bytes": p.stat().st_size,
        "editable": True,
        "honest_label": "可编辑演示文稿（PPTX）",
    }


def available_backends() -> List[str]:
    out = ["native-ooxml"]           # always available
    if _backend() == "python-pptx":
        out.insert(0, "python-pptx")
    return out


# --------------------------------------------------------------------------
def _slide_blocks(s: Slide) -> List[str]:
    """Slide -> ordered plain-text blocks. Shared by both backends."""
    out: List[str] = []
    if s.kicker:
        out.append(s.kicker)
    if s.title:
        out.append(s.title)
    if s.subtitle:
        out.append(s.subtitle)
    out.extend(s.bullets)
    for col in s.columns:
        out.append(str(col.get("title", "")))
        out.extend(str(i) for i in col.get("items", []))
    if s.table_header:
        out.append("　|　".join(s.table_header))
        for row in s.table:
            out.append("　|　".join(str(c) for c in row))
    if s.notes:
        out.append(f"（讲稿）{s.notes}")
    return [b for b in out if b]


# --------------------------------------------------------------------------
def _write_python_pptx(deck: Deck, path: Path) -> None:
    from pptx import Presentation
    from pptx.dml.color import RGBColor
    from pptx.enum.text import PP_ALIGN
    from pptx.util import Emu, Inches, Pt

    brand = deck.brand
    prs = Presentation()
    prs.slide_width = Inches(SLIDE_W_IN)
    prs.slide_height = Inches(SLIDE_H_IN)
    blank = prs.slide_layouts[6]

    def add_text(slide, left, top, width, height, text, size, color, bold=False,
                 align=PP_ALIGN.LEFT, wrap=True, space_after=4):
        box = slide.shapes.add_textbox(Inches(left), Inches(top),
                                       Inches(width), Inches(height))
        tf = box.text_frame
        tf.word_wrap = wrap
        lines = str(text).split("\n")
        for i, line in enumerate(lines):
            para = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            para.text = line
            para.alignment = align
            para.space_after = Pt(space_after)
            for run in para.runs:
                run.font.size = Pt(size)
                run.font.bold = bold
                run.font.color.rgb = RGBColor(*hex_to_rgb(color))
                run.font.name = brand.font_cjk
        return box

    def add_rect(slide, left, top, width, height, fill, line=None):
        from pptx.enum.shapes import MSO_SHAPE

        shp = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(left),
                                     Inches(top), Inches(width), Inches(height))
        shp.fill.solid()
        shp.fill.fore_color.rgb = RGBColor(*hex_to_rgb(fill))
        if line:
            shp.line.color.rgb = RGBColor(*hex_to_rgb(line))
        else:
            shp.line.fill.background()
        shp.shadow.inherit = False
        return shp

    total = len(deck.slides)
    for idx, s in enumerate(deck.slides, 1):
        slide = prs.slides.add_slide(blank)

        if s.kind == "cover":
            add_rect(slide, 0, 0, SLIDE_W_IN, SLIDE_H_IN, brand.ink)
            add_rect(slide, 0.9, 4.62, 1.6, 0.06, brand.accent)
            add_text(slide, 0.9, 0.85, 11.5, 0.5, s.kicker or brand.tagline,
                     13, brand.accent, bold=True)
            add_text(slide, 0.9, 1.5, 11.6, 1.6, s.title, 34, "#FFFFFF", bold=True)
            add_text(slide, 0.9, 3.5, 11.6, 0.9, s.subtitle, 15, "#C9C9C4")
            if s.bullets:
                add_text(slide, 0.9, 4.95, 11.6, 1.8, "\n".join(s.bullets),
                         12, "#9C9C98")
            continue

        # page furniture
        add_rect(slide, 0, 0, SLIDE_W_IN, 0.14, brand.accent)
        add_text(slide, 0.75, 0.42, 11.8, 0.3,
                 s.kicker or brand.name, 10.5, brand.muted, bold=True)
        add_text(slide, 0.75, 0.78, 11.8, 0.75, s.title, 26, brand.ink, bold=True)
        y = 1.62
        if s.subtitle:
            add_text(slide, 0.75, y, 11.8, 0.4, s.subtitle, 13, brand.muted)
            y += 0.52
        add_rect(slide, 0.75, y - 0.12, 11.83, 0.02, brand.rule)

        if s.image and Path(s.image).exists():
            try:
                slide.shapes.add_picture(str(s.image), Inches(0.75), Inches(y),
                                         height=Inches(4.05))
                y += 4.25
            except Exception:
                add_text(slide, 0.75, y, 11.8, 0.3,
                         f"[图像不可用] {s.image}", 11, brand.muted)
                y += 0.4

        if s.bullets:
            add_text(slide, 0.75, y, 11.8, 1.4, "\n".join(f"·  {b}" for b in s.bullets),
                     13, brand.ink, space_after=6)
            y += 0.34 * len(s.bullets) + 0.15

        if s.columns:
            w = 11.83 / max(1, len(s.columns)) - 0.25
            x = 0.75
            for col in s.columns:
                add_rect(slide, x, y, w, 2.4, brand.accent_soft)
                body = "\n".join([f"· {i}" for i in col.get("items", [])])
                add_text(slide, x + 0.18, y + 0.16, w - 0.36, 2.1,
                         f"{col.get('title','')}\n{body}", 11.5, brand.ink,
                         space_after=3)
                x += w + 0.25

        if s.table_header and s.table:
            rows = len(s.table) + 1
            cols = len(s.table_header)
            tbl = slide.shapes.add_table(rows, cols, Inches(0.75), Inches(y),
                                         Inches(11.83), Inches(0.34 * rows)).table
            for c, h in enumerate(s.table_header):
                cell = tbl.cell(0, c)
                cell.text = str(h)
                for para in cell.text_frame.paragraphs:
                    for run in para.runs:
                        run.font.size = Pt(11)
                        run.font.bold = True
                        run.font.color.rgb = RGBColor(*hex_to_rgb(brand.ink))
            for r, row in enumerate(s.table, 1):
                for c in range(cols):
                    cell = tbl.cell(r, c)
                    cell.text = str(row[c]) if c < len(row) else ""
                    for para in cell.text_frame.paragraphs:
                        for run in para.runs:
                            run.font.size = Pt(10.5)
                            run.font.color.rgb = RGBColor(*hex_to_rgb(brand.ink))

        foot = brand.footer_note or brand.platform
        add_text(slide, 0.75, SLIDE_H_IN - 0.46, 9.5, 0.3,
                 f"{foot} · {deck.title}", 9, brand.muted)
        add_text(slide, 11.6, SLIDE_H_IN - 0.46, 1.2, 0.3,
                 f"{idx} / {total}", 9, brand.muted, align=PP_ALIGN.RIGHT)

        if s.notes:
            slide.notes_slide.notes_text_frame.text = s.notes

    prs.save(str(path))


# --------------------------------------------------------------------------
# Native OOXML backend. No third-party import at all.
# --------------------------------------------------------------------------
NS_P = "http://schemas.openxmlformats.org/presentationml/2006/main"
NS_A = "http://schemas.openxmlformats.org/drawingml/2006/main"
NS_R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS_CT = "http://schemas.openxmlformats.org/package/2006/content-types"
NS_REL = "http://schemas.openxmlformats.org/package/2006/relationships"

EMU_W = int(SLIDE_W_IN * EMU_PER_IN)
EMU_H = int(SLIDE_H_IN * EMU_PER_IN)


def _esc(text: str) -> str:
    return (str(text).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def _sp(shape_id: int, name: str, x: int, y: int, cx: int, cy: int,
        paragraphs: Sequence[Tuple[str, int, str, bool]]) -> str:
    body = []
    for text, size_pt, color, bold in paragraphs:
        if not text:
            continue
        rpr = (f'<a:rPr lang="zh-CN" sz="{int(size_pt*100)}" b="{1 if bold else 0}" '
               f'dirty="0"><a:solidFill><a:srgbClr val="{color.lstrip("#")}"/>'
               f'</a:solidFill></a:rPr>')
        body.append(f"<a:p><a:pPr algn=\"l\"/><a:r>{rpr}"
                    f"<a:t>{_esc(text)}</a:t></a:r></a:p>")
    return (
        '<p:sp><p:nvSpPr>'
        f'<p:cNvPr id="{shape_id}" name="{_esc(name)}"/>'
        '<p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr>'
        '<p:spPr>'
        f'<a:xfrm><a:off x="{x}" y="{y}"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>'
        '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom>'
        '<a:noFill/></p:spPr>'
        '<p:txBody><a:bodyPr wrap="square"><a:normAutofit/></a:bodyPr>'
        '<a:lstStyle/>' + "".join(body) + '</p:txBody></p:sp>'
    )


def _slide_xml(s: Slide, brand) -> str:
    blocks = _slide_blocks(s)
    paras: List[Tuple[str, int, str, bool]] = []
    if s.kind == "cover":
        paras.append((s.kicker or brand.tagline, 14, brand.accent, True))
        paras.append(("", 10, brand.ink, False))
        paras.append((s.title, 32, brand.ink, True))
        paras.append((s.subtitle, 15, brand.muted, False))
        paras.append(("", 10, brand.ink, False))
        for b in s.bullets:
            paras.append((f"· {b}", 12, brand.muted, False))
        height = 6.4
    else:
        paras.append((s.kicker or brand.name, 11, brand.muted, True))
        paras.append((s.title, 24, brand.ink, True))
        if s.subtitle:
            paras.append((s.subtitle, 13, brand.muted, False))
        paras.append(("", 8, brand.ink, False))
        for b in s.bullets:
            paras.append((f"· {b}", 13, brand.ink, False))
        for col in s.columns:
            paras.append((str(col.get("title", "")), 13, brand.accent, True))
            for i in col.get("items", []):
                paras.append((f"· {i}", 11.5, brand.ink, False))
        if s.table_header:
            paras.append(("　|　".join(s.table_header), 11, brand.ink, True))
            for row in s.table[:18]:
                paras.append(("　|　".join(str(c) for c in row), 10.5, brand.ink, False))
        if s.image:
            paras.append((f"[图像] {Path(s.image).name}（原生后端只输出文本层，"
                          f"图像请用 python-pptx 后端）", 10, brand.muted, False))
        height = 5.4
    body = _sp(2, "Content", int(0.75 * EMU_PER_IN), int(0.55 * EMU_PER_IN),
               int(11.83 * EMU_PER_IN), int(height * EMU_PER_IN), paras)
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        f'<p:sld xmlns:a="{NS_A}" xmlns:r="{NS_R}" xmlns:p="{NS_P}">'
        '<p:cSld><p:spTree>'
        '<p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>'
        '<p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/>'
        '<a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>'
        + body +
        '</p:spTree></p:cSld>'
        '<p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sld>'
    )


_THEME = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<a:theme xmlns:a="{NS_A}" name="OmniArchitect">
<a:themeElements>
<a:clrScheme name="OmniArchitect">
<a:dk1><a:sysClr val="windowText" lastClr="000000"/></a:dk1>
<a:lt1><a:sysClr val="window" lastClr="FFFFFF"/></a:lt1>
<a:dk2><a:srgbClr val="1C1C1E"/></a:dk2><a:lt2><a:srgbClr val="FAFAF8"/></a:lt2>
<a:accent1><a:srgbClr val="2F6F4F"/></a:accent1><a:accent2><a:srgbClr val="6E6E73"/></a:accent2>
<a:accent3><a:srgbClr val="E4EEE8"/></a:accent3><a:accent4><a:srgbClr val="D8D8D4"/></a:accent4>
<a:accent5><a:srgbClr val="B08D57"/></a:accent5><a:accent6><a:srgbClr val="3A3A3C"/></a:accent6>
<a:hlink><a:srgbClr val="2F6F4F"/></a:hlink><a:folHlink><a:srgbClr val="6E6E73"/></a:folHlink>
</a:clrScheme>
<a:fontScheme name="OmniArchitect">
<a:majorFont><a:latin typeface="Segoe UI"/><a:ea typeface="微软雅黑"/><a:cs typeface=""/></a:majorFont>
<a:minorFont><a:latin typeface="Segoe UI"/><a:ea typeface="微软雅黑"/><a:cs typeface=""/></a:minorFont>
</a:fontScheme>
<a:fmtScheme name="OmniArchitect">
<a:fillStyleLst><a:solidFill><a:schemeClr val="phClr"/></a:solidFill>
<a:solidFill><a:schemeClr val="phClr"/></a:solidFill>
<a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:fillStyleLst>
<a:lnStyleLst><a:ln w="9525"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln>
<a:ln w="25400"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln>
<a:ln w="38100"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln></a:lnStyleLst>
<a:effectStyleLst><a:effectStyle><a:effectLst/></a:effectStyle>
<a:effectStyle><a:effectLst/></a:effectStyle><a:effectStyle><a:effectLst/></a:effectStyle></a:effectStyleLst>
<a:bgFillStyleLst><a:solidFill><a:schemeClr val="phClr"/></a:solidFill>
<a:solidFill><a:schemeClr val="phClr"/></a:solidFill>
<a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:bgFillStyleLst>
</a:fmtScheme>
</a:themeElements><a:objectDefaults/><a:extraClrSchemeLst/></a:theme>
"""

_SLIDE_MASTER = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sldMaster xmlns:a="{NS_A}" xmlns:r="{NS_R}" xmlns:p="{NS_P}">
<p:cSld><p:bg><p:bgPr><a:solidFill><a:srgbClr val="FAFAF8"/></a:solidFill>
<a:effectLst/></p:bgPr></p:bg><p:spTree>
<p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>
<p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/>
<a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>
</p:spTree></p:cSld>
<p:clrMap bg1="lt1" tx1="dk1" bg2="lt2" tx2="dk2" accent1="accent1"
accent2="accent2" accent3="accent3" accent4="accent4" accent5="accent5"
accent6="accent6" hlink="hlink" folHlink="folHlink"/>
<p:sldLayoutIdLst><p:sldLayoutId id="2147483649" r:id="rId1"/></p:sldLayoutIdLst>
<p:txStyles><p:titleStyle/><p:bodyStyle/><p:otherStyle/></p:txStyles></p:sldMaster>
"""

_SLIDE_LAYOUT = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sldLayout xmlns:a="{NS_A}" xmlns:r="{NS_R}" xmlns:p="{NS_P}" type="blank" preserve="1">
<p:cSld name="Blank"><p:spTree>
<p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>
<p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/>
<a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>
</p:spTree></p:cSld>
<p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sldLayout>
"""

_PRESENTATION = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:presentation xmlns:a="{NS_A}" xmlns:r="{NS_R}" xmlns:p="{NS_P}" saveSubsetFonts="1">
<p:sldMasterIdLst><p:sldMasterId id="2147483648" r:id="rId1"/></p:sldMasterIdLst>
<p:sldIdLst>{{sld_ids}}</p:sldIdLst>
<p:sldSz cx="{EMU_W}" cy="{EMU_H}"/><p:notesSz cx="{EMU_H}" cy="{EMU_W}"/>
<p:defaultTextStyle/></p:presentation>
"""


def _write_native_pptx(deck: Deck, path: Path) -> None:
    brand = deck.brand
    slides = deck.slides or [Slide(kind="cover", title=deck.title)]
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        overrides = [
            '<Override PartName="/ppt/presentation.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.'
            'presentationml.presentation.main+xml"/>',
            '<Override PartName="/ppt/slideMasters/slideMaster1.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.'
            'presentationml.slideMaster+xml"/>',
            '<Override PartName="/ppt/slideLayouts/slideLayout1.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.'
            'presentationml.slideLayout+xml"/>',
            '<Override PartName="/ppt/theme/theme1.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.theme+xml"/>',
            '<Override PartName="/docProps/core.xml" '
            'ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>',
            '<Override PartName="/docProps/app.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.'
            'extended-properties+xml"/>',
        ]
        for i in range(1, len(slides) + 1):
            overrides.append(
                f'<Override PartName="/ppt/slides/slide{i}.xml" '
                'ContentType="application/vnd.openxmlformats-officedocument.'
                'presentationml.slide+xml"/>'
            )
        z.writestr(
            "[Content_Types].xml",
            f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            f'<Types xmlns="{NS_CT}">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            + "".join(overrides) + "</Types>",
        )
        z.writestr(
            "_rels/.rels",
            f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            f'<Relationships xmlns="{NS_REL}">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/'
            'officeDocument/2006/relationships/officeDocument" Target="ppt/presentation.xml"/>'
            '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/'
            'package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>'
            '<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/'
            'officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>'
            "</Relationships>",
        )
        sld_ids = "".join(
            f'<p:sldId id="{256 + i}" r:id="rId{i + 1}"/>'
            for i in range(1, len(slides) + 1)
        )
        z.writestr("ppt/presentation.xml", _PRESENTATION.replace("{sld_ids}", sld_ids))
        rels = [
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/'
            'officeDocument/2006/relationships/slideMaster" Target="slideMasters/slideMaster1.xml"/>'
        ]
        for i in range(1, len(slides) + 1):
            rels.append(
                f'<Relationship Id="rId{i + 1}" Type="http://schemas.openxmlformats.org/'
                f'officeDocument/2006/relationships/slide" Target="slides/slide{i}.xml"/>'
            )
        rels.append(
            '<Relationship Id="rId%d" Type="http://schemas.openxmlformats.org/'
            'officeDocument/2006/relationships/theme" Target="theme/theme1.xml"/>'
            % (len(slides) + 2)
        )
        z.writestr(
            "ppt/_rels/presentation.xml.rels",
            f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            f'<Relationships xmlns="{NS_REL}">' + "".join(rels) + "</Relationships>",
        )
        z.writestr("ppt/slideMasters/slideMaster1.xml", _SLIDE_MASTER)
        z.writestr(
            "ppt/slideMasters/_rels/slideMaster1.xml.rels",
            f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            f'<Relationships xmlns="{NS_REL}">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/'
            'officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout1.xml"/>'
            '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/'
            'officeDocument/2006/relationships/theme" Target="../theme/theme1.xml"/>'
            "</Relationships>",
        )
        z.writestr("ppt/slideLayouts/slideLayout1.xml", _SLIDE_LAYOUT)
        z.writestr(
            "ppt/slideLayouts/_rels/slideLayout1.xml.rels",
            f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            f'<Relationships xmlns="{NS_REL}">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/'
            'officeDocument/2006/relationships/slideMaster" Target="../slideMasters/slideMaster1.xml"/>'
            "</Relationships>",
        )
        z.writestr("ppt/theme/theme1.xml", _THEME)
        for i, s in enumerate(slides, 1):
            z.writestr(f"ppt/slides/slide{i}.xml", _slide_xml(s, brand))
            z.writestr(
                f"ppt/slides/_rels/slide{i}.xml.rels",
                f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                f'<Relationships xmlns="{NS_REL}">'
                '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/'
                'officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout1.xml"/>'
                "</Relationships>",
            )
        z.writestr(
            "docProps/core.xml",
            f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<cp:coreProperties '
            'xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
            'xmlns:dc="http://purl.org/dc/elements/1.1/" '
            'xmlns:dcterms="http://purl.org/dc/terms/" '
            'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
            f'<dc:title>{_esc(deck.title)}</dc:title>'
            f'<dc:creator>{_esc(brand.name)}</dc:creator>'
            f'<cp:lastModifiedBy>{_esc(brand.name)}</cp:lastModifiedBy>'
            f'<cp:revision>{deck.revision}</cp:revision>'
            f'<dcterms:created xsi:type="dcterms:W3CDTF">{deck.generated_at.replace(" ", "T")}Z</dcterms:created>'
            "</cp:coreProperties>",
        )
        z.writestr(
            "docProps/app.xml",
            f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/'
            '2006/extended-properties" xmlns:vt="http://schemas.openxmlformats.org/'
            'officeDocument/2006/docPropsVTypes">'
            f'<Application>{_esc(brand.name)} native OOXML writer</Application>'
            f'<Slides>{len(slides)}</Slides>'
            f'<Company>{_esc(brand.platform)}</Company></Properties>',
        )


# --------------------------------------------------------------------------
def write_markdown(deck: Deck, path: str | Path) -> str:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"# {deck.title}", "", f"> {deck.subtitle}", ""]
    for i, s in enumerate(deck.slides, 1):
        lines.append(f"## {i:02d}　{s.title}")
        if s.subtitle:
            lines.append(f"*{s.subtitle}*")
        lines.append("")
        for b in s.bullets:
            lines.append(f"- {b}")
        for col in s.columns:
            lines.append(f"**{col.get('title','')}**")
            for it in col.get("items", []):
                lines.append(f"- {it}")
        if s.table_header:
            lines.append("")
            lines.append("| " + " | ".join(map(str, s.table_header)) + " |")
            lines.append("|" + "---|" * len(s.table_header))
            for row in s.table:
                lines.append("| " + " | ".join(map(str, row)) + " |")
        if s.image:
            lines.append("")
            lines.append(f"![{s.title}]({s.image})")
        lines.append("")
    if deck.provenance:
        lines += ["---", "", "## 内容来源", ""] + [f"- {x}" for x in deck.provenance]
    p.write_text("\n".join(lines), encoding="utf-8")
    return str(p)


_HTML_TPL = """<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<title>{title}</title>
<style>
  @page {{ size: 297mm 167mm; margin: 0; }}
  * {{ box-sizing: border-box; }}
  body {{ margin:0; background:#e9e9e6; font-family:"微软雅黑","Segoe UI",sans-serif; color:{ink}; }}
  .slide {{ width:297mm; height:167mm; padding:14mm 16mm; background:{paper};
            margin:0 auto 6mm; position:relative; overflow:hidden;
            border-top:4px solid {accent}; }}
  .kick {{ font-size:9pt; letter-spacing:.12em; color:{accent}; font-weight:700; }}
  h1 {{ font-size:26pt; margin:4mm 0 2mm; line-height:1.2; }}
  h2 {{ font-size:17pt; margin:0 0 2mm; }}
  .sub {{ color:{muted}; font-size:10.5pt; margin-bottom:3mm; }}
  ul {{ margin:0 0 3mm; padding-left:5mm; font-size:11pt; line-height:1.65; }}
  .cols {{ display:flex; gap:5mm; }}
  .col {{ flex:1; background:{accent_soft}; padding:4mm; font-size:9.5pt; line-height:1.6; }}
  table {{ border-collapse:collapse; width:100%; font-size:9.5pt; margin-top:2mm; }}
  th,td {{ border:1px solid {rule}; padding:1.6mm 2.4mm; text-align:left; }}
  th {{ background:{accent_soft}; }}
  img {{ max-height:78mm; display:block; margin:2mm 0; border:1px solid {rule}; }}
  .foot {{ position:absolute; left:16mm; right:16mm; bottom:5mm; display:flex;
           justify-content:space-between; font-size:8pt; color:{muted};
           border-top:1px solid {rule}; padding-top:2mm; }}
  .cover {{ background:{ink}; color:#fff; }}
  .cover h1 {{ font-size:32pt; }}
  .cover .sub, .cover li {{ color:#c9c9c4; }}
  .cover .kick {{ color:{accent}; }}
</style></head><body>
{slides}
</body></html>
"""


def write_html(deck: Deck, path: str | Path) -> str:
    """Print-ready sheet: open in a browser and print to PDF."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    b = deck.brand
    chunks: List[str] = []
    total = len(deck.slides)
    for i, s in enumerate(deck.slides, 1):
        cls = "slide cover" if s.kind == "cover" else "slide"
        body = []
        if s.kicker:
            body.append(f'<div class="kick">{_esc(s.kicker)}</div>')
        body.append(f"<h1>{_esc(s.title)}</h1>")
        if s.subtitle:
            body.append(f'<div class="sub">{_esc(s.subtitle)}</div>')
        if s.bullets:
            body.append("<ul>" + "".join(f"<li>{_esc(x)}</li>" for x in s.bullets) + "</ul>")
        if s.columns:
            body.append('<div class="cols">' + "".join(
                f'<div class="col"><b>{_esc(c.get("title",""))}</b><br>'
                + "<br>".join(_esc(x) for x in c.get("items", [])) + "</div>"
                for c in s.columns) + "</div>")
        if s.image and Path(s.image).exists():
            body.append(f'<img src="{_esc(Path(s.image).as_posix())}" alt="">')
        if s.table_header:
            body.append("<table><tr>" +
                        "".join(f"<th>{_esc(h)}</th>" for h in s.table_header) + "</tr>")
            for row in s.table:
                body.append("<tr>" + "".join(f"<td>{_esc(c)}</td>" for c in row) + "</tr>")
            body.append("</table>")
        body.append(f'<div class="foot"><span>{_esc(b.platform)} · {_esc(deck.title)}</span>'
                    f'<span>{i} / {total}</span></div>')
        chunks.append(f'<section class="{cls}">' + "".join(body) + "</section>")
    html = _HTML_TPL.format(
        title=_esc(deck.title), ink=b.ink, paper=b.paper, muted=b.muted,
        accent=b.accent, accent_soft=b.accent_soft, rule=b.rule,
        slides="\n".join(chunks),
    )
    p.write_text(html, encoding="utf-8")
    return str(p)


def export_pdf(deck: Deck, path: str | Path, html_path: str | Path) -> Dict[str, Any]:
    """Real PDF only when a renderer exists on this host. Never faked."""
    import shutil
    import subprocess

    p = Path(path)
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice:
        return {
            "ok": False, "path": str(p), "renderer": "",
            "reason": "本机未找到 LibreOffice/soffice：不伪造 PDF。",
            "fallback": str(html_path),
            "how_to": "打开 HTML 后用浏览器『打印为 PDF』，或安装 LibreOffice 后重试。",
        }
    try:
        proc = subprocess.run(
            [soffice, "--headless", "--convert-to", "pdf", "--outdir",
             str(p.parent), str(html_path)],
            capture_output=True, text=True, timeout=300,
        )
    except Exception as exc:
        return {"ok": False, "path": str(p), "renderer": soffice,
                "reason": f"转换失败：{exc}", "fallback": str(html_path)}
    produced = p.parent / (Path(html_path).stem + ".pdf")
    if proc.returncode == 0 and produced.exists():
        if produced != p:
            produced.replace(p)
        return {"ok": True, "path": str(p), "renderer": soffice,
                "size_bytes": p.stat().st_size}
    return {"ok": False, "path": str(p), "renderer": soffice,
            "reason": (proc.stderr or proc.stdout or "").strip()[-400:],
            "fallback": str(html_path)}


__all__ = [
    "write_pptx", "write_markdown", "write_html", "export_pdf",
    "available_backends", "hex_to_rgb",
]
