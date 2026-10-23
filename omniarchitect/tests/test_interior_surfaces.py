"""Interior surface drawings and schedules share the installed room geometry.

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import json
from pathlib import Path

from omniarchitect.adapters.dxf import DxfAdapter
from omniarchitect.demo import build_demo_project
from omniarchitect.interior_surfaces import export
from omniarchitect.workflow import StageRunner


def test_residential_surface_cad_and_schedule_use_model_rooms() -> None:
    root = Path(__file__).resolve().parents[2] / "out" / "interior-surface-test"
    project = build_demo_project(root / "project")
    runner = StageRunner(project, root / "delivery")
    runner._ensure_scheme_installed()
    assert {s.properties.get("zone") for s in project.spaces if s.use != "envelope"} >= {
        "day", "night", "service"}
    artifacts = export(project, root / "sheets", "L1")
    assert len(artifacts) == 6
    for stem, layer in (("I-04-ceiling", "I-CEILING"),
                        ("I-05-floor-finish", "I-FLOOR")):
        audit = DxfAdapter().audit(root / "sheets" / f"{stem}.dxf",
                                   required_layer_prefix=layer)
        assert audit["ok"], audit["errors"]
    data = json.loads((root / "sheets" / "interior-surface-areas.json")
                      .read_text(encoding="utf-8"))
    assert data["status"] == "review_only"
    rooms = {s.id: s for s in project.spaces if s.use != "envelope"}
    assert len(data["rooms"]) == len(rooms)
    assert all(row["gross_area_m2"] == round(rooms[row["space_id"]].area_m2, 2)
               for row in data["rooms"])
