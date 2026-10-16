"""Local, deterministic media provider.

This provider exists so that the pipeline never *needs* an external model to
produce something real. It rasterises the same drawing primitives the DXF
writer uses, so the picture and the drawing cannot disagree.

What it produces is labelled honestly in every output: a **schematic
diagram**, not a photorealistic render, and never a dimensional authority.

Why it does *not* declare `image_generation`
-------------------------------------------
`schematic_diagram` is a separate, deterministic scope on purpose. AI image
and video generation are exclusively owned by the OmniAiLab platform; if this
project's own vector rasteriser were allowed to answer `image_generation`, that
would be an implicit, silent substitution for a generative model — exactly what
the brand-and-provider policy forbids. The two families are therefore kept
apart at the type level: a caller asking for a generative scope can only ever
be answered by the native platform, or by an explicit, clearly-labelled error.

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import json
import math
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from ..model import Project, polygon_centroid
from .base import (
    MediaProvider,
    NotConfigured,
    ProviderCapability,
    ProviderError,
    ProviderJob,
)

# Fonts tried in order for CJK labels; the first that exists wins.
CJK_FONTS: Sequence[str] = (
    r"C:\Windows\Fonts\msyh.ttc",
    r"C:\Windows\Fonts\msyh.ttf",
    r"C:\Windows\Fonts\simhei.ttf",
    r"C:\Windows\Fonts\simsun.ttc",
    "/System/Library/Fonts/PingFang.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
)

DISCLAIMER = "示意图 / 非写实渲染 · 不得作为施工尺寸依据"

# Layer -> (fill rgba, line rgba)
LAYER_PAINT: Dict[str, Tuple[Tuple[int, int, int, int], Tuple[int, int, int, int]]] = {
    "A-WALL": ((0, 0, 0, 0), (28, 28, 30, 255)),
    "A-WALL-PART": ((0, 0, 0, 0), (90, 90, 96, 255)),
    "A-UNCERTAIN": ((0, 0, 0, 0), (200, 40, 40, 255)),
    "A-DOOR": ((0, 0, 0, 0), (150, 100, 40, 255)),
    "A-GLAZ": ((0, 0, 0, 0), (40, 120, 190, 255)),
    "A-FURN": ((214, 214, 216, 160), (120, 120, 126, 200)),
    "A-AREA": ((235, 238, 240, 90), (200, 205, 210, 120)),
    "A-ANNO-DIMS": ((0, 0, 0, 0), (150, 150, 155, 255)),
    "A-ANNO-TEXT": ((0, 0, 0, 0), (60, 60, 64, 255)),
    "G-ANNO-TTLB": ((0, 0, 0, 0), (40, 40, 44, 255)),
}


def _load_font(size: int):
    from PIL import ImageFont

    for path in CJK_FONTS:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size), path
            except Exception:
                continue
    try:
        return ImageFont.load_default(), ""
    except Exception:
        return None, ""


class LocalDeterministicProvider(MediaProvider):
    """Raster output derived from the canonical model. No network, no model."""

    id = "local"
    name = "Local deterministic renderer"
    kind = "own-builtin"
    generative = False          # 自有确定性模块，不是生成式 AI 服务

    def probe(self) -> ProviderCapability:
        try:
            import PIL  # noqa: F401
        except Exception:
            return ProviderCapability(
                provider=self.id, state="not_configured", scopes=[],
                provider_kind="own-builtin",
                missing=["Pillow"], hint="安装 Pillow 后可用本地示意图输出。",
                notes=["本地 provider 不联网、不调用生成式模型",
                       "不承担任何生成式能力域：AI 生图 / AI 视频只经 OmniAiLab"],
            )
        font, path = _load_font(20)
        notes = ["输出为确定性示意图，由 Canonical Spatial Model 直接栅格化",
                 "非写实渲染，不得作为施工尺寸依据",
                 "只声明 schematic_diagram / media_asset_management；"
                 "生成式能力域（AI 生图 / AI 视频）不在本模块范围内"]
        if not path:
            notes.append("未找到中文字体：CJK 标注可能无法正常显示（已如实记录）")
        return ProviderCapability(
            provider=self.id, state="connected",
            provider_kind="own-builtin",
            scopes=["schematic_diagram", "media_asset_management"],
            models=["local-vector-raster"],
            evidence=[f"Pillow {getattr(PIL, '__version__', '?')}",
                      f"font: {path or 'default (no CJK)'}"],
            auth="none", endpoint_known=False, notes=notes,
        )

    # ------------------------------------------------------------------
    def estimate_cost(self, operation: str, params: Dict[str, Any]) -> Optional[float]:
        return 0.0

    def submit(self, operation: str, params: Dict[str, Any]) -> ProviderJob:
        cap = self.probe()
        if not cap.usable:
            raise NotConfigured(self.id, cap.missing, cap.hint)
        job = ProviderJob(job_id=f"local-{int(time.time()*1000)}", provider=self.id,
                          operation=operation, status="running")
        try:
            if operation == "schematic_diagram":
                variant = str(params.get("variant") or "plan")
                if variant == "rooms":
                    job.outputs = self._contact_sheet(**params)
                else:
                    job.outputs = [self._plan_png(**params)]
            elif operation == "media_asset_management":
                job.outputs = [self._asset_index(**params)]
            else:
                raise ProviderError(
                    f"本地 provider 不支持 {operation!r}；"
                    "生成式能力域只能由 OmniAiLab 平台承担，本模块不得改道执行"
                )
        except ProviderError:
            raise
        except Exception as exc:
            job.status = "failed"
            job.error = f"{type(exc).__name__}: {exc}"
            return job
        job.status = "succeeded"
        job.progress = 1.0
        return job

    def poll(self, job: ProviderJob) -> ProviderJob:
        return job            # work is synchronous

    def fetch(self, job: ProviderJob, target_dir: str | Path) -> List[str]:
        return list(job.outputs)

    # ------------------------------------------------------------------
    # renderers
    # ------------------------------------------------------------------
    def plan_png(self, project: Project, out_path: str | Path,
                 level_id: Optional[str] = None, px_per_m: float = 46.0,
                 title: str = "平面示意图", scheme: str = "") -> str:
        return self._plan_png(project=project, out_path=out_path,
                              level_id=level_id, px_per_m=px_per_m,
                              title=title, scheme=scheme)

    def _plan_png(self, project: Project, out_path: str | Path,
                  level_id: Optional[str] = None, px_per_m: float = 46.0,
                  title: str = "平面示意图", scheme: str = "", **_ignored: Any) -> str:
        from PIL import Image, ImageDraw

        from ..adapters.drawing import build_primitives

        lid = level_id or (project.levels[0].id if project.levels else "L1")
        prims = build_primitives(project, level_id=lid, include_furniture=True,
                                 include_dims=True, include_titleblock=False,
                                 title=title, scheme=scheme, depth="presentation")
        if not prims:
            raise ProviderError("没有可绘制的几何——平面示意图需要空间与墙体")

        pts: List[Tuple[float, float]] = []
        for pr in prims:
            pts.extend(pr.points)
            if pr.kind in ("circle", "arc"):
                pts.append(pr.center)
            if pr.kind == "text":
                pts.append(pr.center)
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        pad_mm = 900.0
        x0, x1 = min(xs) - pad_mm, max(xs) + pad_mm
        y0, y1 = min(ys) - pad_mm, max(ys) + pad_mm

        scale = px_per_m / 1000.0
        w = max(400, int((x1 - x0) * scale))
        h = max(300, int((y1 - y0) * scale)) + 64

        img = Image.new("RGBA", (w, h), (250, 250, 248, 255))
        dr = ImageDraw.Draw(img, "RGBA")

        def tx(p: Tuple[float, float]) -> Tuple[float, float]:
            return ((p[0] - x0) * scale, (y1 - p[1]) * scale)

        # fills first (spaces), then strokes, then text on top
        for pr in prims:
            if pr.kind == "polyline" and pr.closed and pr.layer in ("A-AREA", "A-FURN"):
                fill = LAYER_PAINT.get(pr.layer, ((0, 0, 0, 0),))[0]
                dr.polygon([tx(p) for p in pr.points], fill=fill)

        for pr in prims:
            _, stroke = LAYER_PAINT.get(pr.layer, ((0, 0, 0, 0), (0, 0, 0, 255)))
            width = 2 if pr.layer in ("A-WALL",) else 1
            if pr.kind == "polyline":
                seq = [tx(p) for p in pr.points]
                if pr.closed:
                    seq.append(seq[0])
                dr.line(seq, fill=stroke, width=width, joint="curve")
            elif pr.kind == "line":
                dr.line([tx(p) for p in pr.points], fill=stroke, width=width)
            elif pr.kind == "circle":
                cx, cy = tx(pr.center)
                r = pr.radius * scale
                dr.ellipse([cx - r, cy - r, cx + r, cy + r], outline=stroke, width=width)
            elif pr.kind == "arc":
                cx, cy = tx(pr.center)
                r = pr.radius * scale
                dr.arc([cx - r, cy - r, cx + r, cy + r],
                       start=-pr.end_angle, end=-pr.start_angle, fill=stroke, width=width)
            elif pr.kind == "text":
                size = max(9, int(pr.height * scale * 0.95))
                font, _ = _load_font(size)
                cx, cy = tx(pr.center)
                if font:
                    dr.text((cx, cy), pr.text, fill=stroke, font=font, anchor="mm")

        # honesty footer
        font, _ = _load_font(15)
        dr.rectangle([0, h - 46, w, h], fill=(24, 24, 26, 255))
        if font:
            dr.text((12, h - 30), DISCLAIMER, fill=(240, 200, 90, 255), font=font,
                    anchor="lm")
            dr.text((w - 12, h - 30),
                    f"{project.name or project.project_id} · r{project.revision} · "
                    f"{title} {scheme}".strip(),
                    fill=(220, 220, 220, 255), font=font, anchor="rm")

        p = Path(out_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        img.convert("RGB").save(p, "PNG")
        return str(p)

    def _contact_sheet(self, project: Project, out_path: str | Path,
                       level_id: Optional[str] = None,
                       **kwargs: Any) -> List[str]:
        """Plan + per-space call-outs on one sheet. Still schematic."""
        from PIL import Image, ImageDraw

        plan_path = Path(out_path).with_name(Path(out_path).stem + "-plan.png")
        self._plan_png(project=project, out_path=plan_path, level_id=level_id,
                       title="总平面示意")
        lid = level_id or (project.levels[0].id if project.levels else "L1")
        spaces = [s for s in project.spaces_on(lid) if s.use != "envelope"]

        plan = Image.open(plan_path).convert("RGB")
        thumb_h = 520
        scale = thumb_h / plan.height
        thumb = plan.resize((max(1, int(plan.width * scale)), thumb_h))
        cols = max(1, min(4, len(spaces)))
        rows = 1 + (len(spaces) + cols - 1) // cols
        cell_w = max(thumb.width, 300)
        cell_h = thumb_h + 34
        W = cols * cell_w + 24
        H = rows * cell_h + 92

        sheet = Image.new("RGB", (W, H), (246, 246, 244))
        dr = ImageDraw.Draw(sheet)
        fh, _ = _load_font(20)
        fs, _ = _load_font(14)
        if fh:
            dr.text((16, 18), f"{project.name or project.project_id} · 空间示意图集",
                    fill=(24, 24, 26), font=fh)
        sheet.paste(thumb, (16, 56))

        for i, s in enumerate(spaces):
            r = i // cols
            c = i % cols
            x = 16 + c * cell_w
            y = 56 + (r + 1) * cell_h
            dr.rectangle([x, y, x + cell_w - 14, y + cell_h - 14],
                         fill=(255, 255, 255), outline=(215, 218, 220))
            if fs:
                cx, cy = polygon_centroid(s.boundary_mm2d)
                dr.text((x + 10, y + 8),
                        f"{s.name or s.use}　{s.area_m2:.1f} m²",
                        fill=(30, 30, 34), font=fs)
                dr.text((x + 10, y + 30),
                        f"形心 ({cx:.0f}, {cy:.0f}) mm　用途 {s.use}",
                        fill=(110, 112, 118), font=fs)

        dr.rectangle([0, H - 40, W, H], fill=(24, 24, 26))
        if fs:
            dr.text((12, H - 26), DISCLAIMER + " · 各房间为几何示意，不含写实材质与光照",
                    fill=(240, 200, 90), font=fs, anchor="lm")

        p = Path(out_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        sheet.save(p, "PNG")
        return [str(p), str(plan_path)]

    def _asset_index(self, out_path: str | Path, assets: Sequence[Any] = (),
                     project_id: str = "", revision: int = 0, **kwargs: Any) -> str:
        payload = {
            "provider": self.id,
            "project_id": project_id,
            "revision": revision,
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "authoritative": False,
            "note": "本地确定性媒体索引；生成式与示意图媒体均非权威成果",
            "assets": [a.to_dict() if hasattr(a, "to_dict") else dict(a) for a in assets],
        }
        p = Path(out_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return str(p)


__all__ = ["LocalDeterministicProvider", "CJK_FONTS", "DISCLAIMER", "LAYER_PAINT"]
