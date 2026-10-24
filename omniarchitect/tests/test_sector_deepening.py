"""Specialist S4–S8 files must include all actual school/hotel levels.

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path

from omniarchitect.adapters.dxf import DxfAdapter
from omniarchitect.paths import test_output_root
from omniarchitect.adapters.mesh import MeshAdapter
from omniarchitect.tests.test_sector_levels import _project
from omniarchitect.workflow import StageRunner


def _check(sector: str, text: str, code: str, expected: int, floors: int) -> None:
    project, _state = _project(sector, text, code)
    root = test_output_root() / "sector-deepening-test"
    runner = StageRunner(project, root / sector)
    for stage in ("S4", "S5", "S6", "S7", "S8"):
        result = getattr(runner, f"stage_{stage}")()
        assert result.status == "degraded", (stage, result.error)
        assert result.artifacts and all(Path(a).is_file() for a in result.artifacts)
    drawing = runner.out / "07-documents" / ("教学楼" if sector == "education" else "酒店客房楼")
    drawing = drawing.with_name(drawing.name + f"-L{floors}-平面.dxf")
    assert DxfAdapter().audit(drawing)["ok"]
    obj = runner.out / "05-visual" / "whole-building.obj"
    mesh = MeshAdapter().read_back(obj)
    assert mesh["ok"] and mesh["size_m"][2] > 3.9 * (floors - 1)
    for view in ("isometric-ne.svg", "isometric-sw.svg"):
        svg = runner.out / "05-visual" / view
        root_svg = ET.parse(svg).getroot()
        assert len(root_svg.findall("{http://www.w3.org/2000/svg}polygon")) > 100
    takeoff = json.loads((runner.out / "08-delivery" / "sector-takeoff.json")
                         .read_text(encoding="utf-8"))
    assert takeoff["modeled_primary_rooms"] == expected
    assert len(takeoff["by_floor"]) == floors
    assert takeoff["status"] == "review_only"
    if sector == "hospitality":
        lighting = takeoff["lighting_proposal"]
        assert lighting["status"] == "proposed_points_only"
        assert lighting["total_points"] > expected
        for lid in ("L1", f"L{floors}"):
            sheet = runner.out / "07-documents" / lid / "I-06-lighting-proposal.dxf"
            assert DxfAdapter().audit(sheet, "I-LIGHT")["ok"]
            schedule = json.loads((sheet.parent / "interior-surface-areas.json")
                                  .read_text(encoding="utf-8"))
            assert len(schedule["lighting_points"]) == lighting["by_floor"][lid]
            assert sum("走廊" in p["name"] for p in schedule["lighting_points"]) >= 11
            wall_sheet = sheet.parent / "I-07-typical-wall-elevations.dxf"
            assert DxfAdapter().audit(wall_sheet, "I-ELEV")["ok"]
            assert schedule["typical_wall_elevation"]["openings"]


def test_school_four_levels_and_24_classes() -> None:
    _check("education", "新建 24 班小学，每班 45 人", "A3", 24, 4)


def test_hotel_eight_levels_and_120_keys() -> None:
    _check("hospitality", "既有酒店室内精装修 120 间客房", "B4", 120, 8)
