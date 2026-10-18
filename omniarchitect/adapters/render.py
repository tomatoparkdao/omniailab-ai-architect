"""Render / visualisation routing.

Two rules from the architecture document are enforced here:

1. A render job is assembled from **canonical** camera positions, material
   assignments and lighting, so five views of the same apartment stay
   mutually consistent (same wall, same finish, same light).
2. Anything produced by an image model is marked ``authoritative = False`` and
   can never be fed back into the geometry. It is presentation material.

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from ..model import Project, polygon_centroid
from .base import Adapter, AdapterResult, Capability
from .mesh import material_for

#: 面层默认值 —— 故意为空。
#:
#: 这里原来写死了"微水泥 + 暖白乳胶漆 + 橡木"，结果办公、酒店项目也被套上住宅材料。
#: 面层只能来自两处：G2 确认的概念材料，或项目 constraints 里客户给的材料。
#: 两处都没有时，提示词里就不出现材料句——宁可不写，也不替客户编。
DEFAULT_FINISHES: Dict[str, str] = {}


def camera_presets_for(project: Project, limit: int = 4) -> List[Dict[str, Any]]:
    """机位：全景 + 本项目最大的几个真实空间 + 轴测。

    不再固定"客厅/餐厅/主卧"。名取自 `project.spaces`（没有就用功能表），
    所以办公项目出来的是"开放办公区/会议室"，不是"主卧"。
    """
    presets: List[Dict[str, Any]] = [
        {"id": "01_overview", "label": "全景", "lens_mm": 24,
         "eye_height_mm": 1600, "framing": "bbox_diagonal"},
    ]
    spaces = [s for s in project.spaces if s.use != "envelope"]
    items = sorted(spaces, key=lambda s: -(s.area_m2 or 0))[:limit]
    if not items:
        items = [type("S", (), {"id": f"P{i}", "name": str(p.get("name") or f"空间{i}"),
                                "use": str(p.get("recipe") or ""),
                                "area_m2": float(p.get("area_m2") or 0)})()
                 for i, p in enumerate((project.program or [])[:limit], start=1)]
    for i, s in enumerate(items, start=2):
        presets.append({
            "id": f"{i:02d}_{getattr(s, 'use', 'space') or 'space'}",
            "label": str(getattr(s, "name", "") or "空间"),
            "lens_mm": 35,
            "eye_height_mm": 1400 if "bed" in str(getattr(s, "use", "")) else 1500,
            "framing": "room_corner",
        })
    presets.append({"id": "99_plan_axon", "label": "轴测", "lens_mm": 50,
                    "eye_height_mm": 0, "framing": "axon"})
    return presets


#: 兼容旧调用方：只有通用机位，不含任何房间名。
CAMERA_PRESETS: List[Dict[str, Any]] = [
    {"id": "01_overview", "label": "全景", "lens_mm": 24, "eye_height_mm": 1600, "framing": "bbox_diagonal"},
    {"id": "99_plan_axon", "label": "轴测", "lens_mm": 50, "eye_height_mm": 0, "framing": "axon"},
]

LIGHTING_PRESETS: Dict[str, Dict[str, Any]] = {
    "day_soft": {"key": "sun 12:00 秋分, 层高 2.8m, 南向落地窗", "cs": 5500, "fill": 0.35, "notes": "保留窗边过曝，不要补光打平"},
    "day_hard": {"key": "sun 14:30, 直射进深 1.5–2.0m", "cs": 5600, "fill": 0.2, "notes": "允许明确阴影边界，用来读空间关系"},
    "evening": {"key": "无自然光, 3000K 环境 + 灯带/洗墙为主", "cs": 3000, "fill": 0.5, "notes": "必须出现一个'发光的面'"},
}

NEGATIVE = (
    "变形几何, 错误的透视, 扭曲的墙面, 多余的窗户, 重复家具, 水印, 文字, "
    "杂物堆砌, 过度镀金, 塑料感, 过曝死白, 暗部死黑, 鱼眼畸变"
)


class RenderAdapter(Adapter):
    name = "render"
    tool = "omniailab-canvas"

    def preflight(self) -> Capability:
        configured = self._configured_backends()
        diagrams = self._diagram_backends()
        notes = [
            "job package (camera + material + lighting + prompt) is always produced offline",
        ]
        if configured:
            notes += [
                f"creative backend available: {', '.join(configured)} — OmniAiLab only",
                "generated results are non-authoritative presentation material",
            ]
        else:
            notes += [
                "OmniAiLab creative capability is NOT available right now",
                "generation is deferred, never re-routed: no third-party image or "
                "video platform is contacted, recommended or configured",
                "when the platform returns, run the saved job package as-is",
            ]
        if diagrams:
            notes.append(
                f"deterministic schematic backend: {', '.join(diagrams)} "
                "(ours, labelled non-photorealistic — never a stand-in for an AI model)"
            )
        return Capability(
            name=self.name,
            # The adapter is usable offline: it always produces the camera /
            # material / lighting / prompt package. Whether a *creative* backend
            # exists is reported through `executable` and the notes, because
            # "can compose shots" and "can generate images" are different claims.
            available=True,
            executable=",".join(configured),
            operations=["build_jobs", "describe_viewpoints"] + (
                ["render_local"] if diagrams else []
            ) + ["render_ai"],
            notes=notes,
        )

    @staticmethod
    def _configured_backends() -> List[str]:
        # Not guessed: ask the provider registry which providers may take a
        # generative scope. Under the brand-and-provider policy that list can
        # only ever contain the native OmniAiLab platform — when it is absent
        # the list is empty and the task is deferred rather than substituted.
        try:
            from ..providers import discover

            return discover().creative_backends()
        except Exception:
            return []

    @staticmethod
    def _diagram_backends() -> List[str]:
        """This project's own schematic rasterisers (never an AI model)."""
        try:
            from ..providers import discover

            return discover().diagram_backends()
        except Exception:
            return []

    # ------------------------------------------------------------------
    def build_job_package(
        self,
        project: Project,
        out_path: str | Path,
        level_id: Optional[str] = None,
        viewpoints: Optional[Sequence[str]] = None,
        lighting: str = "day_soft",
        style: str = "",
        finishes: Optional[Dict[str, str]] = None,
    ) -> AdapterResult:
        lid = level_id or (project.levels[0].id if project.levels else "L1")
        spaces = [s for s in project.spaces_on(lid) if s.use != "envelope"]
        provisional = False
        if not spaces:
            # Concept stage: rooms do not exist yet. Frame on the surveyed shell
            # and say so — the job package is a direction check, not a design.
            spaces = [s for s in project.spaces_on(lid) if s.use == "envelope"]
            provisional = True
        if not spaces:
            raise ValueError(
                "no spaces and no envelope on this level — nothing to frame a camera on"
            )
        pts = [p for s in spaces for p in s.boundary_mm2d]
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        bbox = {"x": [min(xs), max(xs)], "y": [min(ys), max(ys)]}
        span_m = max(max(xs) - min(xs), max(ys) - min(ys)) / 1000.0

        from ..finishes import finish_map

        fin = dict(DEFAULT_FINISHES)
        fin.update(finish_map(project))
        fin.update(finishes or {})

        material_takeoff: Dict[str, float] = {}
        for w in project.by_type("wall"):
            if w.level_id != lid:
                continue
            key = "wall"
            material_takeoff[key] = material_takeoff.get(key, 0.0) + (
                w.wall_length_mm() * float(w.geometry.get("height_mm", 2800)) / 1e6
            )
        for s in spaces:
            material_takeoff["floor"] = material_takeoff.get("floor", 0.0) + s.area_m2
            material_takeoff["ceiling"] = material_takeoff.get("ceiling", 0.0) + s.area_m2

        jobs = []
        for preset in camera_presets_for(project):
            if viewpoints and preset["id"] not in viewpoints:
                continue
            anchor = self._anchor_for(preset, spaces, bbox, span_m)
            jobs.append(
                {
                    "id": preset["id"],
                    "label": preset["label"],
                    "camera": {
                        "position_mm": anchor["position"],
                        "target_mm": anchor["target"],
                        "lens_mm": preset["lens_mm"],
                        "sensor_mm": 36,
                        "aspect": "16:10",
                        "eye_height_mm": preset["eye_height_mm"],
                    },
                    "lighting": {"preset": lighting, **LIGHTING_PRESETS.get(lighting, {})},
                    "finishes": fin,
                    "prompt": self._prompt(project, preset, anchor, fin, style, lighting),
                    "negative_prompt": NEGATIVE,
                    "authoritative": False,
                    "notes": "presentation only — not usable to derive dimensions",
                }
            )

        payload = {
            "project_id": project.project_id,
            "revision": project.revision,
            "level_id": lid,
            "generated_from": "canonical spatial model",
            "authoritative": False,
            "disclaimer": (
                "所有图片模型输出均为表现材料，不构成尺寸依据；"
                "施工图必须由经过校核的几何/BIM 模型生成。"
            ),
            "scene": {
                "bbox_mm": bbox,
                "extent_m": round(span_m, 2),
                "wall_height_mm": float(
                    next((l.height_mm for l in project.levels if l.id == lid), 2800.0)
                ),
                "space_count": len(spaces),
                "provisional": provisional,
                "provisional_note": (
                    "尚无房间分区，机位基于套内轮廓设定——仅用于概念方向判断，"
                    "平面确认后必须重新生成任务包"
                ) if provisional else "",
            },
            "material_takeoff_m2": {k: round(v, 2) for k, v in material_takeoff.items()},
            "jobs": jobs,
        }

        p = self.write_json(Path(out_path), payload)
        res = AdapterResult(adapter=self.name, ok=True, revision=project.revision)
        res.artifacts.append(str(p))
        res.authoritative = False
        res.validation = {
            "capability": self.preflight().to_dict(),
            "jobs": len(jobs),
            "note": "attach generated images back as artifacts with status 'needs_review'",
        }
        res.log.append(f"{len(jobs)} camera job(s) built for {len(spaces)} spaces")
        return res

    # ------------------------------------------------------------------
    @staticmethod
    def _anchor_for(preset, spaces, bbox, span_m) -> Dict[str, Any]:
        x0, x1 = bbox["x"]
        y0, y1 = bbox["y"]
        cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
        target = [round(cx, 1), round(cy, 1), 1200.0]
        dist = span_m * 1000.0

        room_hint = {
            "02_living": ["living", "dining"],
            "03_dining": ["dining", "kitchen"],
            "04_bedroom": ["bedroom"],
        }.get(preset["id"])
        if room_hint:
            cand = [s for s in spaces if s.use in room_hint]
            if cand:
                box_pts = [p for s in cand for p in s.boundary_mm2d]
                rx0 = min(p[0] for p in box_pts)
                rx1 = max(p[0] for p in box_pts)
                ry0 = min(p[1] for p in box_pts)
                ry1 = max(p[1] for p in box_pts)
                rcx, rcy = (rx0 + rx1) / 2.0, (ry0 + ry1) / 2.0
                target = [round(rcx, 1), round(rcy, 1), 1200.0]
                # stand in a corner of the room looking across it
                pos = [rx0 + 400.0, ry0 + 400.0, preset["eye_height_mm"]]
                return {"position": pos, "target": target, "room": cand[0].id}

        if preset["framing"] == "axon":
            return {
                "position": [round(cx, 1), round(cy - dist * 1.1, 1), round(dist * 0.9, 1)],
                "target": target,
            }
        return {
            "position": [round(cx, 1), round(cy - dist * 0.95, 1), max(preset["eye_height_mm"], 1550)],
            "target": target,
        }

    @staticmethod
    def _prompt(project, preset, anchor, finishes, style, lighting) -> str:
        light = LIGHTING_PRESETS.get(lighting, {})
        parts = [
            f"室内摄影，{preset['label']}视角，{preset['lens_mm']}mm 镜头",
            style or "风格未指定，按已确认概念方案的风格执行",
            f"地面 {finishes.get('floor','')}；墙面 {finishes.get('wall','')}；天花 {finishes.get('ceiling','')}",
            f"光线：{light.get('key','自然光')}，色温 {light.get('cs','5500')}K",
            "写实渲染，真实材质反射，柔和阴影，杂志级构图，无人物",
            f"项目：{project.name or project.project_id}",
        ]
        return "；".join(p for p in parts if p)
