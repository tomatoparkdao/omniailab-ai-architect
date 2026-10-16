"""Material takeoff, schedules and cost banding (specialist skill 16).

Quantities are derived from canonical geometry only. Rates live in
`project.constraints.cost_bands` so a local estimator can override them; the
defaults are indicative ranges, never a quotation.

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .model import Project, Space
from .geometry import point_along

# indicative unit rates, CNY, for banding only — must be replaced per project
DEFAULT_RATES: Dict[str, Dict[str, float]] = {
    "floor_finish": {"low": 180, "high": 520, "unit": "m2"},
    "wall_finish": {"low": 90, "high": 280, "unit": "m2"},
    "ceiling": {"low": 140, "high": 420, "unit": "m2"},
    "partition": {"low": 260, "high": 680, "unit": "m2"},
    "door": {"low": 1800, "high": 6500, "unit": "set"},
    "window": {"low": 900, "high": 2600, "unit": "m2"},
    "joinery": {"low": 1200, "high": 3800, "unit": "m2"},
    "mep_rough": {"low": 320, "high": 900, "unit": "m2"},
    "lighting": {"low": 120, "high": 420, "unit": "m2"},
}

CATEGORY_TO_RATE = {
    "wardrobe": "joinery", "tv_unit": "joinery", "bookshelf": "joinery",
    "shelf_unit": "joinery", "shoe_cabinet": "joinery", "sideboard": "joinery",
    "desk": "joinery", "kitchen_run": "joinery", "kitchen_island": "joinery",
}

_BASIS_LABEL = {
    "plan": "已确认平面（实测几何）",
    "envelope+program": "套内轮廓 + 任务书面积（前期估算）",
    "program": "任务书面积（前期估算）",
}


@dataclass
class Takeoff:
    project_id: str
    revision: int
    quantities: Dict[str, float] = field(default_factory=dict)
    by_space: List[Dict[str, Any]] = field(default_factory=list)
    cost: Dict[str, Any] = field(default_factory=dict)
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_id": self.project_id,
            "revision": self.revision,
            "quantities": {k: round(v, 2) for k, v in self.quantities.items()},
            "by_space": self.by_space,
            "cost": self.cost,
            "notes": self.notes,
            "disclaimer": "工程量用于方案阶段估算，不构成结算依据；须由造价人员复核。",
        }


def takeoff(project: Project, level_id: Optional[str] = None) -> Takeoff:
    lid = level_id or (project.levels[0].id if project.levels else "L1")
    spaces = [s for s in project.spaces_on(lid) if s.use != "envelope"]
    walls = [e for e in project.by_type("wall") if e.level_id == lid]
    doors = [e for e in project.by_type("door") if e.level_id == lid]
    windows = [e for e in project.by_type("window") if e.level_id == lid]
    furniture = [e for e in project.by_type("furniture") if e.level_id == lid]

    # Basis: with no plan yet, estimate from the surveyed envelope and the brief
    # rather than reporting zeros. R3 says estimation starts early; a zero is
    # not an estimate.
    basis = "plan"
    envelope_m2 = sum(s.area_m2 for s in project.spaces_on(lid) if s.use == "envelope")
    program_m2 = sum(float(p.get("area_m2") or 0) for p in (project.program or []))
    if not spaces:
        basis = "envelope+program" if envelope_m2 else "program"
        floor_m2 = envelope_m2 or program_m2
    else:
        floor_m2 = sum(s.area_m2 for s in spaces)

    q: Dict[str, float] = {}
    q["floor_area_m2"] = floor_m2
    q["ceiling_area_m2"] = floor_m2

    wall_area = 0.0
    partition_area = 0.0
    for w in walls:
        h = float(w.geometry.get("height_mm", 2800)) / 1000.0
        l = w.wall_length_mm() / 1000.0
        th = float(w.geometry.get("thickness_mm", 200)) / 1000.0
        is_part = w.geometry.get("kind") == "partition"
        a = l * h
        if is_part:
            q["partition_length_m"] = q.get("partition_length_m", 0.0) + l
            partition_area += l * h
        wall_area += a
        q["wall_volume_m3"] = q.get("wall_volume_m3", 0.0) + a * th

    # deduct openings from the paint/wall finish area
    opening_area = sum(
        float(o.geometry.get("width_mm", 0)) * float(o.geometry.get("height_mm", 0)) / 1e6
        for o in (*doors, *windows)
    )
    if basis == "plan":
        q["wall_finish_area_m2"] = max(0.0, wall_area - opening_area)
    else:
        # no partitions yet: use the 2.6 m² wall per m² floor ratio and declare it
        q["wall_finish_area_m2"] = floor_m2 * 2.6
        q["partition_area_m2"] = floor_m2 * 0.25
        q["partition_length_m"] = floor_m2 * 0.18
    q["partition_area_m2"] = partition_area if basis == "plan" else q["partition_area_m2"]

    q["door_count"] = float(len(doors)) if basis == "plan" else float(
        sum(1 for p in (project.program or []) if True)
    )
    q["window_count"] = float(len(windows))
    q["glazing_area_m2"] = (
        sum(float(w.geometry.get("width_mm", 0)) * float(w.geometry.get("height_mm", 0)) / 1e6
            for w in windows)
        if basis == "plan" else floor_m2 / 7.0
    )
    q["furniture_count"] = float(len(furniture))

    joinery_area = 0.0
    for f in furniture:
        cat = str(f.geometry.get("category") or "")
        if cat in CATEGORY_TO_RATE:
            sw, sd, sh = f.geometry.get("size_mm", [0, 0, 0])
            joinery_area += (sw / 1000.0) * (sh / 1000.0)
    q["joinery_area_m2"] = joinery_area

    per_space = []
    for s in spaces:
        per_space.append(
            {
                "id": s.id,
                "name": s.name,
                "use": s.use,
                "area_m2": round(s.area_m2, 2),
                "ceiling_area_m2": round(s.area_m2, 2),
            }
        )

    rates = dict(DEFAULT_RATES)
    override = (project.constraints or {}).get("cost_bands") or {}
    for k, v in override.items():
        if k in rates and isinstance(v, dict):
            rates[k].update({kk: float(vv) for kk, vv in v.items() if kk in ("low", "high")})

    lines = []
    total_low = total_high = 0.0
    mapping = [
        ("floor_finish", q["floor_area_m2"]),
        ("wall_finish", q["wall_finish_area_m2"]),
        ("ceiling", q["ceiling_area_m2"]),
        ("partition", q["partition_area_m2"]),
        ("door", q["door_count"]),
        ("window", q["glazing_area_m2"]),
        ("joinery", q["joinery_area_m2"]),
        ("mep_rough", q["floor_area_m2"]),
        ("lighting", q["floor_area_m2"]),
    ]
    for key, amount in mapping:
        r = rates[key]
        low, high = r["low"] * amount, r["high"] * amount
        total_low += low
        total_high += high
        lines.append(
            {
                "item": key,
                "quantity": round(amount, 2),
                "unit": r["unit"],
                "rate_low": r["low"],
                "rate_high": r["high"],
                "amount_low": round(low, 0),
                "amount_high": round(high, 0),
            }
        )

    cost = {
        "currency": "CNY",
        "basis": "方案阶段估算区间，未含设计费、软装、艺术品、税费与不可预见费",
        "lines": lines,
        "subtotal_low": round(total_low, 0),
        "subtotal_high": round(total_high, 0),
        "per_m2_low": round(total_low / max(q["floor_area_m2"], 1e-9), 0),
        "per_m2_high": round(total_high / max(q["floor_area_m2"], 1e-9), 0),
    }

    t = Takeoff(project_id=project.project_id, revision=project.revision,
                quantities=q, by_space=per_space, cost=cost)
    t.notes.append(f"计量基准：{_BASIS_LABEL.get(basis, basis)}")
    if basis != "plan":
        t.notes.append(
            "尚无平面方案，墙面、隔墙与门窗按经验系数估算，随深化逐步替换为实测值"
        )
    budget = (project.constraints or {}).get("budget_cny")
    if budget:
        t.notes.append(
            f"业主预算 {budget:,.0f} CNY；估算区间 {total_low:,.0f}–{total_high:,.0f} CNY"
        )
        if total_low > float(budget):
            t.notes.append("预算低于估算下沿——须在设计标准或面积上做取舍，而不是压缩不可见部分")
        elif total_high < float(budget) * 0.75:
            t.notes.append("预算明显高于估算区间上沿——可考虑升级主要材料的档位")
    return t


def schedule_doors(project: Project, level_id: Optional[str] = None) -> List[Dict[str, Any]]:
    lid = level_id or (project.levels[0].id if project.levels else "L1")
    rows = []
    for d in project.by_type("door"):
        if d.level_id != lid:
            continue
        g = d.geometry
        rows.append(
            {
                "mark": d.id,
                "type": g.get("kind") or "swing",
                "width_mm": g.get("width_mm"),
                "height_mm": g.get("height_mm"),
                "host_wall": g.get("host_wall"),
                "from": (d.properties.get("from_space") or ""),
                "to": (d.properties.get("to_space") or ""),
            }
        )
    return rows


def schedule_windows(project: Project, level_id: Optional[str] = None) -> List[Dict[str, Any]]:
    lid = level_id or (project.levels[0].id if project.levels else "L1")
    rows = []
    for w in project.by_type("window"):
        if w.level_id != lid:
            continue
        g = w.geometry
        rows.append(
            {
                "mark": w.id,
                "width_mm": g.get("width_mm"),
                "height_mm": g.get("height_mm"),
                "sill_mm": g.get("sill_mm"),
                "host_wall": g.get("host_wall"),
                "space": w.properties.get("space_id", ""),
            }
        )
    return rows


def room_schedule(project: Project, level_id: Optional[str] = None) -> List[Dict[str, Any]]:
    lid = level_id or (project.levels[0].id if project.levels else "L1")
    rows = []
    for s in project.spaces_on(lid):
        if s.use == "envelope":
            continue
        b = s.bbox()
        rows.append(
            {
                "id": s.id,
                "name": s.name,
                "use": s.use,
                "area_m2": round(s.area_m2, 2),
                "width_mm": round(b[2] - b[0], 0),
                "depth_mm": round(b[3] - b[1], 0),
                "daylight": bool(s.properties.get("daylight_required")),
            }
        )
    return rows
