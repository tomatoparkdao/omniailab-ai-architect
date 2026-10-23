"""Materialise school and hotel standard floors in the canonical model.

The S3 program is one *typical* floor. Repeated floors are real model levels,
not a floor-count caption. A short final hotel floor is generated separately,
so 120 keys never silently become 128.

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import math
from typing import Any

from ..model import Element, Level, Project, Space
from . import layout, program as program_mod


def install(project: Project, program: Any, brief: Any, parti: Any,
            env: layout.Envelope, first_scheme: Any) -> dict[str, Any]:
    sector = brief.sector
    if sector not in ("education", "hospitality"):
        return {}
    total_key = "classes" if sector == "education" else "keys"
    total = int(round(float(program.totals.get(total_key) or 0)))
    per = int(round(float(program.totals.get("per_floor") or 0)))
    if total <= 0 or per <= 0:
        return {}
    floors = math.ceil(total / per)
    base_level = project.levels[0]
    base_envelope = next((s for s in project.spaces_on(base_level.id)
                          if s.use == "envelope"), None)
    base_walls = [e for e in project.by_type("wall")
                  if e.level_id == base_level.id and
                  not str(e.source).startswith("scheme_")]
    if base_envelope is None:
        return {"status": "blocked", "reason": "缺少标准层轮廓，不能复制楼层"}

    # `_install_scheme` clears previous generated levels' scheme geometry. Its
    # companion generated Level objects are replaced here; surveyed levels stay.
    old = set((project.meta.get("sector_levels") or {}).get("generated_ids") or [])
    project.levels = [lv for lv in project.levels if lv.id not in old]
    project.spaces = [s for s in project.spaces if s.level_id not in old]
    project.elements = [e for e in project.elements if e.level_id not in old]

    generated = []
    counts = [min(per, total - per * (i - 1)) for i in range(1, floors + 1)]
    for number in range(2, floors + 1):
        lid = f"L{number}"
        if any(lv.id == lid for lv in project.levels):
            return {"status": "blocked", "reason": f"{lid} 已存在非生成楼层，不能覆盖"}
        level = Level(id=lid, name=f"{number}层", height_mm=base_level.height_mm,
                      elevation_mm=base_level.elevation_mm +
                      (number - 1) * base_level.height_mm)
        project.levels.append(level)
        generated.append(lid)

        if counts[number - 1] == per:
            spaces = list(first_scheme.spaces)
            elements = list(first_scheme.elements)
        else:
            floor_program = (program_mod.education(brief, per_floor_classes=counts[number - 1])
                             if sector == "education" else
                             program_mod.hospitality(brief, keys_per_floor=counts[number - 1]))
            temp = Project(project_id=project.project_id + f"-L{number}",
                           levels=[level], program=floor_program.to_rows(),
                           constraints=dict(project.constraints))
            env_space = Space.from_dict(base_envelope.to_dict())
            env_space.level_id = lid
            temp.spaces = [env_space]
            temp.elements = [Element.from_dict(w.to_dict()) for w in base_walls]
            for wall in temp.elements:
                wall.level_id = lid
            result = layout.build_schemes(temp, floor_program, sector, env,
                                          parti=parti, level_id=lid)["A"]
            spaces, elements = list(result.spaces), list(result.elements)

        # Map every geometry reference with the same prefix. IDs remain unique
        # across levels while host-wall and room references still resolve.
        all_elements = base_walls + elements
        id_map = {obj.id: f"F{number}-{obj.id}" for obj in [*spaces, *all_elements]}
        cloned_env = Space.from_dict(base_envelope.to_dict())
        cloned_env.id = f"F{number}-{base_envelope.id}"
        cloned_env.level_id = lid
        cloned_env.properties["scheme"] = "A"
        project.spaces.append(cloned_env)
        for src in spaces:
            room = Space.from_dict(src.to_dict())
            room.id = id_map[src.id]
            room.level_id = lid
            room.name = f"{number}层 {src.name}"
            project.spaces.append(room)
        for src in all_elements:
            obj = Element.from_dict(src.to_dict())
            obj.id = id_map[src.id]
            obj.level_id = lid
            obj.source = f"scheme_A_L{number}"
            host = obj.geometry.get("host_wall")
            if host in id_map:
                obj.geometry["host_wall"] = id_map[host]
            for key in ("from_space", "to_space", "space_id"):
                ref = obj.properties.get(key)
                if ref in id_map:
                    obj.properties[key] = id_map[ref]
            if isinstance(obj.properties.get("space_ids"), list):
                obj.properties["space_ids"] = [id_map.get(ref, ref)
                                               for ref in obj.properties["space_ids"]]
            project.elements.append(obj)

    state = {"sector": sector, "total": total, "per_floor": per,
             "floors": floors, "counts": counts, "generated_ids": generated,
             "floor_height_mm": base_level.height_mm,
             "note": "楼层按标准层程序生成；竖向交通与结构/消防须专项复核"}
    project.meta["sector_levels"] = state
    return state
