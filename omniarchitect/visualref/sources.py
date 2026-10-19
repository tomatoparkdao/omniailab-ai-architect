"""参考文件的读取与客观指标：能读的读，读不到的如实说。

客户发来的"参考"有五种形态，能力边界完全不同：

| 形态 | 能拿到什么 | 拿不到什么 |
|---|---|---|
| Markdown / TXT | 全文、标题层级、明确写下的规则 | — |
| PDF / PPTX / DOCX | 每页文字、页数与画幅 | 图片里的构图细节（除非另有图像） |
| 图片 / 截图 | 尺寸、画幅、主色、明暗、留白比例 | 页边距、字号、栅格列数 |
| 网页链接 | 只登记，不抓（站点结构各不相同） | 除标题外的任何内容 |
| 加密 / 损坏文件 | 打不开的原因 | 任何内容 |

**这份清单是纪律，不是免责声明。** 一份纯文字的参考文件，就只能提取它的文字结构与
审美要求；不能因为"看起来像一份作品集"就编出它的图片排布。图片同理：能算出留白
占比与主色，算不出"标题用了 32pt 宋体"。

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import re
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

TEXT_EXT = {".md", ".markdown", ".txt", ".text"}
PDF_EXT = {".pdf"}
PPTX_EXT = {".pptx", ".ppt"}
DOCX_EXT = {".docx"}
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff", ".avif"}
LINK_EXT = {".url", ".webloc", ".html", ".htm"}

#: 单个文件读取上限：再大也不是"参考"，是素材库
MAX_TEXT_CHARS = 24000


def kind_of(path: str | Path) -> str:
    p = Path(path)
    ext = p.suffix.lower()
    if ext in TEXT_EXT:
        return "text"
    if ext in PDF_EXT:
        return "pdf"
    if ext in PPTX_EXT:
        return "pptx"
    if ext in DOCX_EXT:
        return "docx"
    if ext in IMAGE_EXT:
        return "image"
    if ext in LINK_EXT:
        return "link"
    if ext == "" and p.is_dir():
        return "dir"
    return "unknown"


def _decode(data: bytes) -> str:
    for enc in ("utf-8", "utf-8-sig", "gb18030", "big5", "latin-1"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def read_text(path: str | Path) -> str:
    p = Path(path)
    return _decode(p.read_bytes())[:MAX_TEXT_CHARS]


def read_pdf(path: str | Path) -> Dict[str, Any]:
    """PDF：逐页取文字。扫描件没有文字层时如实返回 `text_layer=False`。"""
    pages: List[str] = []
    try:
        import pdfplumber
    except ImportError:
        return {"ok": False, "reason": "缺少 pdfplumber，无法读取 PDF", "pages": []}
    try:
        with pdfplumber.open(str(path)) as pdf:
            for pg in pdf.pages[:40]:
                pages.append((pg.extract_text() or "").strip())
    except Exception as exc:                      # noqa: BLE001
        return {"ok": False, "reason": f"{type(exc).__name__}: {exc}", "pages": []}
    text = "\n\n".join(p for p in pages if p)
    return {
        "ok": bool(text),
        "reason": "" if text else "PDF 没有文字层（可能是扫描件或纯图片）",
        "pages": pages,
        "page_count": len(pages),
        "text": text[:MAX_TEXT_CHARS],
        "text_layer": bool(text),
    }


def read_pptx(path: str | Path) -> Dict[str, Any]:
    """PPTX：逐页取文字与页面尺寸（比例可量），不解析图片内容。"""
    try:
        from pptx import Presentation
    except ImportError:
        return {"ok": False, "reason": "缺少 python-pptx，无法读取 PPTX", "slides": []}
    try:
        prs = Presentation(str(path))
    except Exception as exc:                      # noqa: BLE001
        return {"ok": False, "reason": f"{type(exc).__name__}: {exc}", "slides": []}
    slides: List[str] = []
    for slide in prs.slides[:60]:
        buf: List[str] = []
        for shape in slide.shapes:
            if shape.has_text_frame:
                t = shape.text_frame.text.strip()
                if t:
                    buf.append(t)
        slides.append("\n".join(buf))
    w = int(prs.slide_width or 0)
    h = int(prs.slide_height or 0)
    return {
        "ok": any(slides),
        "reason": "" if any(slides) else "PPTX 里没有可读文字（纯图片页）",
        "slides": slides,
        "slide_count": len(slides),
        "ratio": round(w / h, 4) if w and h else None,
        "text": "\n\n".join(s for s in slides if s)[:MAX_TEXT_CHARS],
    }


def read_docx(path: str | Path) -> Dict[str, Any]:
    """DOCX：标准库解包读 document.xml，不依赖 python-docx。"""
    try:
        with zipfile.ZipFile(str(path)) as z:
            xml = z.read("word/document.xml").decode("utf-8", errors="replace")
    except Exception as exc:                      # noqa: BLE001
        return {"ok": False, "reason": f"{type(exc).__name__}: {exc}", "text": ""}
    # 段落分隔先替换，再去标签，避免整篇挤成一行
    xml = re.sub(r"</w:p>", "\n", xml)
    text = re.sub(r"<[^>]+>", "", xml)
    text = re.sub(r"[ \t]+", " ", text)
    text = "\n".join(line.strip() for line in text.splitlines() if line.strip())
    return {
        "ok": bool(text),
        "reason": "" if text else "DOCX 没有可读文字",
        "text": text[:MAX_TEXT_CHARS],
    }


# --------------------------------------------------------------------------
# 图片：只报能算出来的
# --------------------------------------------------------------------------
_HEX = "#{:02X}{:02X}{:02X}"


def _lum(rgb: Tuple[int, int, int]) -> float:
    r, g, b = rgb
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _sat(rgb: Tuple[int, int, int]) -> float:
    hi, lo = max(rgb), min(rgb)
    return 0.0 if hi == 0 else (hi - lo) / hi


def image_metrics(path: str | Path) -> Dict[str, Any]:
    """一张参考图的客观指标。

    只输出**可被复核**的量：画幅、主色、纸张色、墨色、留白占比、对比度、饱和度。
    不输出"高级""极简"这类判断——那不是从像素里能读出来的东西。
    """
    try:
        from PIL import Image
    except ImportError:
        return {"ok": False, "reason": "缺少 Pillow，无法读取图片"}
    try:
        im = Image.open(str(path)).convert("RGB")
    except Exception as exc:                      # noqa: BLE001
        return {"ok": False, "reason": f"{type(exc).__name__}: {exc}"}
    w, h = im.size
    small = im.copy()
    small.thumbnail((320, 320))
    px = list(small.getdata())
    n = max(1, len(px))

    lums = [_lum(p) for p in px]
    mean_lum = sum(lums) / n
    var = sum((x - mean_lum) ** 2 for x in lums) / n
    contrast = (var ** 0.5) / 128.0

    # 主色：量化到 12 色，取占比前四
    q = small.quantize(colors=12, method=Image.MEDIANCUT).convert("RGB")
    counts: Dict[Tuple[int, int, int], int] = {}
    for p in q.getdata():
        counts[p] = counts.get(p, 0) + 1
    top = sorted(counts.items(), key=lambda kv: -kv[1])[:4]
    palette = [{"hex": _HEX.format(*c), "share": round(v / n, 3),
                "lum": round(_lum(c), 1)} for c, v in top]

    # 纸色/墨色按**亮度分位**取：量化主色常常全是中间调，拿它当纸色会把
    # 浅底画成深蓝。取 P88 与 P12 的像素平均色，是版面真正在用的两端。
    order = sorted(range(n), key=lambda i: lums[i])
    def _band(lo: int, hi: int) -> Tuple[int, int, int]:
        idx = order[lo:hi] or order[:1]
        r = sum(px[i][0] for i in idx) / len(idx)
        g = sum(px[i][1] for i in idx) / len(idx)
        b = sum(px[i][2] for i in idx) / len(idx)
        return int(r), int(g), int(b)

    paper_rgb = _band(int(n * 0.86), n)
    ink_rgb = _band(0, max(1, int(n * 0.14)))
    paper = _HEX.format(*paper_rgb)
    ink = _HEX.format(*ink_rgb)

    # 留白：落在纸色 ±16 亮度带内的像素占比（近似版面空白）
    paper_lum = _lum(paper_rgb)
    whitespace = sum(1 for x in lums if abs(x - paper_lum) <= 16) / n

    # 点缀色：饱和度高、占比 2%–30% 的那一个
    accent = None
    for p in palette:
        rgb = tuple(int(p["hex"][i:i + 2], 16) for i in (1, 3, 5))
        if _sat(rgb) >= 0.22 and 0.02 <= p["share"] <= 0.30:
            accent = p["hex"]
            break

    return {
        "ok": True,
        "width": w, "height": h,
        "ratio": round(w / h, 4),
        "orientation": "landscape" if w >= h else "portrait",
        "paper": paper,
        "ink": ink,
        "accent": accent,
        "palette": palette,
        "whitespace": round(whitespace, 3),
        "contrast": round(contrast, 3),
        "mean_lum": round(mean_lum, 1),
        "mood": "light" if mean_lum >= 150 else ("dark" if mean_lum <= 90 else "mid"),
    }


def probe(path: str | Path) -> Dict[str, Any]:
    """读一个文件，返回统一结构。读不到就写明原因，不留空壳。"""
    p = Path(path)
    kind = kind_of(p)
    base: Dict[str, Any] = {"path": str(p), "name": p.name, "kind": kind}
    if not p.exists():
        return {**base, "ok": False, "reason": "文件不存在"}
    if kind == "text":
        text = read_text(p)
        return {**base, "ok": bool(text.strip()), "text": text,
                "reason": "" if text.strip() else "文件为空"}
    if kind == "pdf":
        return {**base, **read_pdf(p)}
    if kind == "pptx":
        return {**base, **read_pptx(p)}
    if kind == "docx":
        return {**base, **read_docx(p)}
    if kind == "image":
        return {**base, **image_metrics(p)}
    if kind == "link":
        text = read_text(p)
        return {**base, "ok": bool(text.strip()), "text": text,
                "reason": "" if text.strip() else "链接文件为空",
                "note": "链接只登记，不抓取站点内容"}
    return {**base, "ok": False, "reason": f"不支持的格式 {p.suffix or '(无扩展名)'}"}


def scan(root: str | Path) -> List[Dict[str, Any]]:
    """扫一个参考目录（或单个文件），逐个 probe。"""
    p = Path(root)
    if p.is_file():
        return [probe(p)]
    if not p.is_dir():
        return []
    out: List[Dict[str, Any]] = []
    seen: set = set()
    for f in sorted(x for x in p.rglob("*") if x.is_file()):
        if f.name.startswith((".", "_")):
            continue
        # 交付目录里的 assets/ 是副本，不是客户给的参考
        if "assets" in f.parts:
            continue
        if f.suffix.lower() in (".json", ".py", ".zip", ".mp4", ".mov", ".dwg"):
            continue
        try:
            digest = (f.stat().st_size, f.name.split("-")[0])
        except OSError:
            continue
        if digest in seen:
            continue
        seen.add(digest)
        out.append(probe(f))
    return out


__all__ = ["kind_of", "probe", "scan", "read_text", "read_pdf", "read_pptx",
           "read_docx", "image_metrics", "IMAGE_EXT", "LINK_EXT"]
