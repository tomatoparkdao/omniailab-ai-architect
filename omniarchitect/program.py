"""房间任务表 —— 把「套内面积 + 客户说的话」变成可排布的 program。

S3 的排布算法要的是"每间房多大、什么用途、最小面宽"，不是一句"三居室"。
业主要么给功能表，要么给需求描述；这里做的是后者到前者的翻译：

* 面积按套内实测面积反算，比例来自本系统自有的住宅配比口径（不是国标）；
* 房间数按客户说的家庭构成定（几个孩子 → 几间儿童房），不按面积硬套；
* 每条都带 `basis`，客户在 S3 面积表里能看到"这个目标面积怎么来的"；
* 数据不足就不猜：套内面积未知时返回空表，让 S3 如实说缺什么。

它只服务"住宅"这一类委托；行业项目（学校/医院/酒店/景观）走 `sector.program`。

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from .model import Project

#: 住宅配比（占套内面积），本系统自有口径：够用、不奢侈、走廊不浪费。
RATIO: List[Dict[str, Any]] = [
    {"key": "LIVING", "name": "客厅", "recipe": "living", "zone": "day", "ratio": 0.185,
     "min_width_mm": 3600, "priority": 10},
    {"key": "DINING", "name": "餐厅", "recipe": "dining", "zone": "day", "ratio": 0.095,
     "min_width_mm": 2800, "priority": 20},
    {"key": "KITCHEN", "name": "厨房", "recipe": "kitchen", "zone": "day", "ratio": 0.065,
     "min_width_mm": 2200, "priority": 30},
    {"key": "ENTRY", "name": "玄关", "recipe": "entry", "zone": "entry", "ratio": 0.035,
     "min_width_mm": 1500, "priority": 5},
    {"key": "MBED", "name": "主卧", "recipe": "master_bedroom", "zone": "night",
     "ratio": 0.135, "min_width_mm": 3300, "priority": 15},
    {"key": "BATH1", "name": "主卫", "recipe": "bathroom", "zone": "service", "ratio": 0.048,
     "min_width_mm": 1800, "priority": 40},
    {"key": "BATH2", "name": "次卫", "recipe": "bathroom", "zone": "service", "ratio": 0.038,
     "min_width_mm": 1500, "priority": 45},
    {"key": "STORAGE", "name": "储藏", "recipe": "storage", "zone": "service", "ratio": 0.030,
     "min_width_mm": 1200, "priority": 55},
    {"key": "LAUNDRY", "name": "家务间", "recipe": "laundry", "zone": "service", "ratio": 0.024,
     "min_width_mm": 1200, "priority": 60},
]

CHILD = {"key": "BED_CHILD", "name": "儿童房", "recipe": "bedroom", "zone": "night",
         "ratio": 0.082, "min_width_mm": 2700, "priority": 25}
BED2 = {"key": "BED2", "name": "次卧", "recipe": "bedroom", "zone": "night", "ratio": 0.095,
        "min_width_mm": 2800, "priority": 22}
STUDY = {"key": "STUDY", "name": "书房", "recipe": "study", "zone": "day", "ratio": 0.055,
         "min_width_mm": 2200, "priority": 35}

_AREA_HINTS = re.compile(r"(\d{2,4})\s*(?:平方米|平米|㎡|m2|m²)")


def _text(project: Project) -> str:
    got: List[str] = []
    for row in (project.meta or {}).get("intake", {}).get("answers", []) or []:
        got.append(str(row.get("value") or ""))
    for item in project.program or []:
        got.append(str(item.get("note") or ""))
    for v in (project.constraints or {}).values():
        got.append(str(v))
    return " ".join(got)


def children_count(text: str) -> int:
    """从需求原话数孩子。数不出来就是 0（不猜）。"""
    if re.search(r"两个孩子|2 个孩子|两个小孩|2 个小孩", text):
        return 2
    if re.search(r"一个孩子|1 个孩子|一个小孩|1 个小孩", text):
        return 1
    if re.search(r"三个孩子|3 个孩子", text):
        return 3
    return 0


def envelope_area(project: Project) -> Optional[float]:
    """套内面积：优先实测轮廓，其次业主声明的面积。"""
    from .planner import envelope_polygon

    lid = project.levels[0].id if project.levels else ""
    try:
        poly = envelope_polygon(project, lid)
    except Exception:  # noqa: BLE001  没有轮廓就是没有
        poly = []
    if poly and len(poly) >= 3:
        s = 0.0
        n = len(poly)
        for i in range(n):
            x1, y1 = poly[i][0], poly[i][1]
            x2, y2 = poly[(i + 1) % n][0], poly[(i + 1) % n][1]
            s += x1 * y2 - x2 * y1
        area = abs(s) / 2.0 / 1e6
        if area >= 10:
            return round(area, 1)
    declared = (project.meta or {}).get("existing_conditions", {}).get("declared_area_m2")
    if declared:
        return float(declared)
    m = _AREA_HINTS.search(_text(project))
    return float(m.group(1)) if m else None


def build(project: Project) -> List[Dict[str, Any]]:
    """生成住宅房间任务表。套内面积未知时返回空表（不编面积）。"""
    total = envelope_area(project)
    if not total:
        return []
    text = _text(project)
    rows: List[Dict[str, Any]] = []
    used = 0.0
    for base in RATIO:
        row = dict(base)
        row["area_m2"] = round(total * row.pop("ratio"), 1)
        rows.append(row)
        used += row["area_m2"]

    kids = children_count(text)
    for i in range(min(kids, 3)):
        row = dict(CHILD)
        row["key"] = f"{CHILD['key']}{i + 1}"
        row["name"] = f"儿童房 {i + 1}" if kids > 1 else "儿童房"
        row["area_m2"] = round(total * CHILD["ratio"], 1)
        rows.append(row)
        used += row["area_m2"]
    # 一个孩子时仍留一间次卧（长辈/客房）；没孩子时次卧就是第二间卧室
    if kids <= 1:
        row = dict(BED2)
        row["key"] = "BED2B" if kids == 1 else "BED2"
        row["area_m2"] = round(total * BED2["ratio"], 1)
        rows.append(row)
        used += row["area_m2"]

    if re.search(r"书房|办公|在家工作|读书|看书", text):
        row = dict(STUDY)
        row["area_m2"] = round(total * STUDY["ratio"], 1)
        rows.append(row)
        used += row["area_m2"]

    # 剩下的面积是走廊与墙体：排布器自己会留，这里只如实报出来
    corridor = max(0.0, round(total - used, 1))
    for row in rows:
        row["basis"] = (f"按套内 {total:.1f} m² × 本系统住宅配比 "
                        f"{row['area_m2'] / total:.1%}；走廊与墙厚另计 {corridor:.1f} m²")
        row["priority"] = int(row.get("priority") or 50)
    return rows


def ensure(project: Project, *, force: bool = False) -> List[Dict[str, Any]]:
    """没有 program 就按住宅口径建一份，并记下来源。返回最终 program。"""
    if project.program and not force:
        return list(project.program)
    rows = build(project)
    if not rows:
        return list(project.program)
    project.program = rows
    project.meta["program_source"] = {
        "kind": "derived_from_room_schedule",
        "basis": "套内实测面积 × 住宅配比；家庭构成来自 S1 需求原话",
        "area_m2": envelope_area(project),
        "rooms": len(rows),
        "note": "目标面积为排布目标，不等于最终实测面积；S3 面积表按方案实测回填",
    }
    return rows


__all__ = ["build", "children_count", "ensure", "envelope_area"]
