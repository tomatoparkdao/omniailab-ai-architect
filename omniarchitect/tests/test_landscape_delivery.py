"""Landscape deliverables must use L-SITE geometry, not room defaults.

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path

from omniarchitect.adapters.dxf import DxfAdapter
from omniarchitect.paths import test_output_root
from omniarchitect.adapters.mesh import MeshAdapter
from omniarchitect.concept.handoff import store_plan_record
from omniarchitect.model import Element, Level, Project, Space
from omniarchitect.workflow import StageRunner
from omniarchitect.geometry import HAS_SHAPELY
from omniarchitect.sector.brief import SectorBrief
from omniarchitect.sector.program import ProgramRow, SectorProgram
from omniarchitect.sector.layout import install_landscape_spaces


def test_landscape_s4_to_s8_real_files() -> None:
    project = Project(project_id="landscape-delivery-test", name="庭院")
    project.levels = [Level(id="L-SITE", name="场地", height_mm=0)]
    project.spaces = [
        Space(id="P", level_id="L-SITE", name="种植", use="planting",
              boundary_mm2d=[[0, 0], [10000, 0], [10000, 10000], [0, 10000]]),
        Space(id="W", level_id="L-SITE", name="水景", use="water",
              boundary_mm2d=[[12000, 0], [17000, 0], [17000, 5000], [12000, 5000]]),
    ]
    project.elements = [Element(id="TREE-001", type="other", level_id="L-SITE",
                                geometry={"center": [5000, 5000],
                                          "crown_radius_mm": 1100,
                                          "trunk_radius_mm": 130,
                                          "height_mm": 3200},
                                properties={"landscape_kind": "tree"})]
    store_plan_record(project, {"sector": "landscape", "discipline": "landscape"})
    root = test_output_root() / "landscape-delivery-test"
    runner = StageRunner(project, root)
    for stage in ("S4", "S5", "S6", "S7", "S8"):
        outcome = getattr(runner, f"stage_{stage}")()
        assert outcome.status == "degraded", (stage, outcome.error)
        assert all(Path(a).is_file() for a in outcome.artifacts)
    s4 = runner.out / "04-preliminary" / "L-01-景观总平面.dxf"
    drawing = DxfAdapter().audit(s4, required_layer_prefix="L-ZONE")
    assert drawing["ok"] and drawing["stats"]["entities"].get("CIRCLE") == 2
    s5 = runner.out / "05-visual" / "landscape-model.obj"
    mesh = MeshAdapter().read_back(s5)
    assert mesh["ok"] and "landscape_water" in mesh["materials"]
    assert "landscape_planting" in mesh["materials"]
    assert "landscape_canopy" in mesh["materials"]
    assert ET.parse(runner.out / "05-visual" / "isometric-ne.svg").getroot().find(
        "{http://www.w3.org/2000/svg}polygon") is not None
    data = json.loads((runner.out / "08-delivery" / "landscape-takeoff.json")
                      .read_text(encoding="utf-8"))
    assert data["quantities_m2"]["planting"] == 100
    assert data["quantities_m2"]["water"] == 25
    assert data["proposed_tree_count"] == 1
    assert data["status"] == "review_only"


def test_proposed_garden_cad_and_mesh_read_canonical_site_geometry() -> None:
    project = Project(project_id="garden-geometry-test", name="庭院空间模型")
    program = SectorProgram(rows=[
        ProgramRow("P", "边界绿地", 360, "planting", "planting"),
        ProgramRow("W", "水景", 64, "water", "water"),
        ProgramRow("F", "活动铺装", 240, "paving", "paving"),
        ProgramRow("R", "园路", 48, "path", "paving"),
    ])
    brief = SectorBrief(sector="landscape", quant={"site_area": 800})
    install_landscape_spaces(project, program, brief)
    zones = [s for s in project.spaces_on("L-SITE") if s.use in
             ("planting", "water", "paving", "circulation")]
    nodes = [e for e in project.by_type("other")
             if e.properties.get("landscape_kind") == "view_node"]
    assert len([s for s in zones if s.use == "circulation"]) == 16
    assert len(nodes) == 2
    assert any(s.properties.get("design_z_mm") == 180 for s in zones)
    if HAS_SHAPELY:
        from shapely.geometry import Polygon
        from shapely.ops import unary_union

        polygons = [Polygon(s.boundary_mm2d) for s in zones]
        assert all(p.is_valid for p in polygons)
        assert abs(unary_union(polygons).area / 1e6 - 800) < 0.01
        assert abs(sum(p.area for p in polygons) / 1e6 - 800) < 0.01
    root = test_output_root() / "garden-geometry-test"
    result = DxfAdapter().draw_landscape(project, root / "site.dxf")
    assert result.ok, result.errors
    assert result.validation["stats"]["entities"].get("CIRCLE", 0) >= 2
    mesh = MeshAdapter().export_obj(project, root, level_id="L-SITE", stem="site")
    assert mesh.ok, mesh.errors
    assert mesh.validation["bbox_mm"][1][2] > 3000
