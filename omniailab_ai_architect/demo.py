"""Demo project builder — a real ~131 m² three-bedroom apartment.

Writes a canonical model whose shell comes from a "surveyed" base plan. Two
walls are marked `uncertain` on purpose: they were inferred from the drawing and
must be confirmed on site, which is exactly the kind of thing the system must
refuse to treat as fact.
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple

from .model import Element, Level, Project, Space

# interior-face envelope, CCW, mm — a rectilinear plan with the core notched out
ENVELOPE: List[List[float]] = [
    [0.0, 0.0],
    [13200.0, 0.0],
    [13200.0, 8200.0],
    [10600.0, 8200.0],
    [10600.0, 10400.0],
    [0.0, 10400.0],
]

EXT_THICKNESS = 240.0
INT_THICKNESS = 240.0
PART_THICKNESS = 120.0
WALL_HEIGHT = 2800.0
LEVEL_HEIGHT = 2900.0

PROGRAM: List[Dict[str, Any]] = [
    {"key": "LIVING", "name": "客厅", "recipe": "living", "area_m2": 26, "zone": "day",
     "min_width_mm": 3600, "priority": 10},
    {"key": "DINING", "name": "餐厅", "recipe": "dining", "area_m2": 12, "zone": "day",
     "min_width_mm": 3000, "priority": 20},
    {"key": "KITCHEN", "name": "厨房", "recipe": "kitchen", "area_m2": 8, "zone": "day",
     "min_width_mm": 2400, "priority": 30},
    {"key": "ENTRY", "name": "玄关", "recipe": "entry", "area_m2": 4, "zone": "entry",
     "min_width_mm": 1800, "priority": 5},
    {"key": "MBED", "name": "主卧", "recipe": "master_bedroom", "area_m2": 16, "zone": "night",
     "min_width_mm": 3300, "priority": 15},
    {"key": "BED2", "name": "次卧", "recipe": "bedroom", "area_m2": 11, "zone": "night",
     "min_width_mm": 2900, "priority": 25},
    {"key": "BED3", "name": "儿童房", "recipe": "bedroom", "area_m2": 9, "zone": "night",
     "min_width_mm": 2700, "priority": 35},
    {"key": "BATH1", "name": "主卫", "recipe": "bathroom", "area_m2": 6, "zone": "service",
     "min_width_mm": 2000, "priority": 40},
    {"key": "BATH2", "name": "次卫", "recipe": "bathroom", "area_m2": 4, "zone": "service",
     "min_width_mm": 1600, "priority": 45},
    {"key": "STORAGE", "name": "储藏", "recipe": "storage", "area_m2": 4, "zone": "service",
     "min_width_mm": 1400, "priority": 50},
    {"key": "LAUNDRY", "name": "家务间", "recipe": "laundry", "area_m2": 3, "zone": "service",
     "min_width_mm": 1400, "priority": 55},
]


def _polygon_area(points: Sequence[Sequence[float]]) -> float:
    total = 0.0
    n = len(points)
    for i in range(n):
        x1, y1 = points[i][0], points[i][1]
        x2, y2 = points[(i + 1) % n][0], points[(i + 1) % n][1]
        total += x1 * y2 - x2 * y1
    return abs(total) / 2.0


def build_demo_project(project_dir: str | Path) -> Project:
    d = Path(project_dir)
    d.mkdir(parents=True, exist_ok=True)

    level = Level(id="L1", name="一层", elevation_mm=0.0, height_mm=LEVEL_HEIGHT)

    spaces = [
        Space(
            id="S-ENV",
            level_id="L1",
            name="套内轮廓",
            use="envelope",
            boundary_mm2d=[list(p) for p in ENVELOPE],
            source="drawing_import",
            confidence=0.72,
            properties={
                "note": "由原始户型图识别，内表面尺寸，须现场复核",
                "requires_door": False,
            },
        )
    ]

    elements: List[Element] = []
    walls: List[Element] = []

    def add_wall(idx: int, a, b, thickness, kind, uncertain=False, note="", source="drawing_import"):
        e = Element(
            id=f"W-EXT-{idx:03d}",
            type="wall",
            level_id="L1",
            geometry={
                "start": [round(a[0], 1), round(a[1], 1)],
                "end": [round(b[0], 1), round(b[1], 1)],
                "thickness_mm": thickness,
                "height_mm": WALL_HEIGHT,
                "kind": kind,
            },
            source=source,
            confidence=0.62 if uncertain else 0.72,
            uncertain=uncertain,
            properties={"note": note} if note else {},
        )
        walls.append(e)
        return e

    # exterior walls: centreline offset outward so the interior face is the envelope
    n = len(ENVELOPE)
    for i in range(n):
        p = ENVELOPE[i]
        q = ENVELOPE[(i + 1) % n]
        dx, dy = q[0] - p[0], q[1] - p[1]
        L = math.hypot(dx, dy)
        nx, ny = dy / L, -dx / L  # outward normal for a CCW ring
        off = EXT_THICKNESS / 2.0
        a = (p[0] + nx * off, p[1] + ny * off)
        b = (q[0] + nx * off, q[1] + ny * off)
        uncertain = i in (2,)  # the wall against the core: inferred, not measured
        add_wall(
            i + 1, a, b, EXT_THICKNESS, "exterior", uncertain=uncertain,
            note="与核心筒相邻，图纸信息不足，须现场实测" if uncertain else "",
        )

    # inferred structural wall across the middle — the perfect `uncertain` specimen
    walls.append(
        Element(
            id="W-INT-100",
            type="wall",
            level_id="L1",
            geometry={
                "start": [0.0, 5200.0],
                "end": [7200.0, 5200.0],
                "thickness_mm": INT_THICKNESS,
                "height_mm": WALL_HEIGHT,
                "kind": "structural",
            },
            source="drawing_inferred",
            confidence=0.45,
            uncertain=True,
            properties={"note": "图纸中墙厚异常，疑为承重墙；须现场探测或原设计单位确认"},
        )
    )
    elements.extend(walls)

    # --- existing windows on the surveyed shell -------------------------
    def add_window(idx: int, host: str, offset: float, width: float,
                   height: float = 1500.0, sill: float = 900.0,
                   uncertain: bool = False, note: str = "") -> None:
        elements.append(
            Element(
                id=f"WN-EXIST-{idx:03d}",
                type="window",
                level_id="L1",
                geometry={
                    "host_wall": host, "offset_mm": offset, "width_mm": width,
                    "height_mm": height, "sill_mm": sill,
                },
                source="drawing_import",
                confidence=0.6 if uncertain else 0.72,
                uncertain=uncertain,
                properties={"note": note} if note else {},
            )
        )

    # south façade wall is edge 0 (from (0,0) to (13200,0)), length 13200
    add_window(1, "W-EXT-001", 1200.0, 2400.0)
    add_window(2, "W-EXT-001", 4600.0, 2400.0)
    add_window(3, "W-EXT-001", 8200.0, 2400.0)
    # east façade wall is edge 1 (from (13200,0) to (13200,8200)), length 8200
    add_window(4, "W-EXT-002", 2000.0, 1800.0)
    add_window(5, "W-EXT-002", 5200.0, 1800.0, uncertain=True,
               note="开洞尺寸由图纸估算，须现场复核")

    project = Project(
        project_id="demo-120",
        name="云栖路 120–150㎡ 住宅（示例项目）",
        revision=1,
        units="mm",
        coordinate_system={"origin": [0.0, 0.0, 0.0], "axes": "X 东, Y 北, Z 上（单位 mm）"},
        levels=[level],
        spaces=spaces,
        elements=elements,
        artifacts=[],
        change_log=[],
        program=PROGRAM,
        constraints={
            "style": "现代意式极简",
            "budget_cny": 800000,
            "occupancy": "3 人（夫妻 + 1 孩）",
            "entry_point": [11900.0, 8200.0],
            "target_stage": "方案 + 施工图深化（示例）",
            "site": "南方城市住宅，南向为主要采光面",
            "cost_bands": {
                "floor_finish": {"low": 200, "high": 560},
                "ceiling": {"low": 150, "high": 460},
            },
        },
        assumptions=[
            "层高按 2900 mm 假定（未实测）",
            "内表面轮廓由图纸识别，未做现场实测",
            "南向为主要采光面，东向次之",
            "未取得原结构图，承重构件按推断标记",
        ],
        sources=[
            {"type": "pdf", "file": "原始户型图.pdf", "confidence": 0.72,
             "note": "由图纸识别，尺寸与结构信息须现场复核"},
            {"type": "site_visit", "file": "", "confidence": 0.0,
             "note": "尚未进行现场实测"},
        ],
        meta={"demo": True, "envelope_area_m2": round(_polygon_area(ENVELOPE) / 1e6, 2)},
    )

    project.save(d / "project.json")
    (d / "README.md").write_text(
        "\n".join([
            "# 示例项目 demo-120",
            "",
            f"- 套内轮廓面积 {_polygon_area(ENVELOPE)/1e6:.2f} m²",
            f"- 功能任务书 {len(PROGRAM)} 项",
            "- 2 个构件标记为 `uncertain`（推断承重墙 / 核心筒侧墙），须现场核对",
            "",
            "这个项目刻意保留不确定性：系统必须能区分『图纸读到的事实』与『推断』，"
            "并把后者挡在施工图之外。",
        ]),
        encoding="utf-8",
    )
    return project
