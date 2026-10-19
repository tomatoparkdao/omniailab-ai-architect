"""Design presentation: content model, deck assembly, PPTX/HTML/PDF output.

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from ..model import Project
from . import html, online_doc  # noqa: F401
from .deck import DeckBuilder, build, kinds  # noqa: F401
from .layouts import (  # noqa: F401
    DECK_KINDS,
    SLIDE_KINDS,
    Brand,
    Deck,
    Slide,
    new_deck,
    slide_order,
)
from .pptx_writer import (  # noqa: F401
    available_backends,
    export_pdf,
    write_html,
    write_markdown,
    write_pptx,
)


def _stamp(path: Path) -> None:
    """Every deck ends with the OmniAiLab signature."""
    from ..registry import SIGNATURE

    text = path.read_text(encoding="utf-8").rstrip()
    if SIGNATURE in text:
        return
    path.write_text(f"{text}\n\n---\n\n{SIGNATURE}\n", encoding="utf-8")


def render(project: Project, kind: str = "concept", out_dir: str | Path = "out",
           stem: str = "", brand: Optional[Brand] = None, want_pdf: bool = True,
           **builder_kwargs: Any) -> Dict[str, Any]:
    """Build a deck and write every format this host can honestly produce."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    deck = DeckBuilder(project, kind=kind, brand=brand, out_dir=out,
                       **builder_kwargs).build()
    name = stem or f"presentation-{kind}-r{project.revision}"

    written: Dict[str, str] = {}
    pptx_path = out / f"{name}.pptx"
    written["pptx"] = write_pptx(deck, pptx_path)["path"]      # type: ignore[assignment]
    written["markdown"] = write_markdown(deck, out / f"{name}.md")
    _stamp(Path(written["markdown"]))
    written["html"] = write_html(deck, out / f"{name}.html")

    pdf_report: Dict[str, Any] = {"ok": False, "reason": "未请求 PDF"}
    if want_pdf:
        pdf_report = export_pdf(deck, out / f"{name}.pdf", written["html"])
        if pdf_report.get("ok"):
            written["pdf"] = str(pdf_report["path"])

    spec_path = out / f"{name}.deck.json"
    import json

    spec_path.write_text(
        json.dumps({"deck": deck.to_dict(), "files": written, "pdf": pdf_report},
                   ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return {
        "kind": kind,
        "stage": deck.stage,
        "title": deck.title,
        "slides": len(deck.slides),
        "issues": deck.validate(),
        "files": written,
        "pdf": pdf_report,
        "pptx_backends": available_backends(),
        "provenance": list(deck.provenance),
        "spec": str(spec_path),
    }


__all__ = [
    "render", "build", "kinds", "DeckBuilder", "Deck", "Slide", "Brand",
    "new_deck", "slide_order", "DECK_KINDS", "SLIDE_KINDS",
    "write_pptx", "write_markdown", "write_html", "export_pdf",
    "available_backends", "html", "online_doc",
]
