"""Campus CAD, model placement and quantities share one proposed geometry.

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from omniarchitect.adapters import DxfAdapter, MeshAdapter
from omniarchitect.sector import brief, program
from omniarchitect.sector.site_delivery import export, install_school
from omniarchitect.sector.model_preview import COLORS, export as export_model_preview
from omniarchitect.tests.test_sector_levels import _project
from omniarchitect.workflow import StageRunner


def test_school_campus_cad_obj_and_takeoff_share_footprints() -> None:
    description = ("新建 24 班小学，每班 45 人，用地 20000 平方米，"
                   "需学生食堂、体育馆及 200 米跑道，北侧临路")
    project, _ = _project("education", description, "A3")
    context = SimpleNamespace(name=description, lead_id="architecture",
        profile_id="architecture", taxonomy={"codes": ["A3"], "ancillary": []},
        taxonomy_codes=("A3",), answers={}, program=[], area_available_m2=None,
        target_area_m2=0.0, location="")
    design_brief = brief.build(context)
    install_school(project, program.build(design_brief), design_brief)

    ground = next(s for s in project.spaces_on("L-SITE")
                  if s.properties.get("site_block_key") == "teach")
    envelope = next(s for s in project.spaces_on(project.levels[0].id)
                    if s.use == "envelope")
    dx, dy = project.meta["site_level_offsets_mm"][project.levels[0].id]
    placed = (envelope.bbox()[0]+dx, envelope.bbox()[1]+dy,
              envelope.bbox()[2]+dx, envelope.bbox()[3]+dy)
    assert all(abs(a-b) < .02 for a, b in zip(ground.bbox(), placed)), (
        ground.bbox(), placed)

    root = Path(__file__).resolve().parents[2] / "out" / "sector-site-test"
    artifacts = export(project, root)
    assert DxfAdapter().audit(artifacts[0], "S-FOOTPRINT")["ok"]
    # 红线 1 + 地块 5 + 临路带 1：临路带是这一轮补的，图上要有路也才有入口
    site_svg = Path(artifacts[1]).read_text(encoding="utf-8")
    assert site_svg.count("<polygon") == 7, site_svg.count("<polygon")
    assert "城市道路" in site_svg and "主入口" in site_svg
    mesh = MeshAdapter().export_multilevel_obj(project, root, stem="campus")
    assert mesh.ok and MeshAdapter().read_back(mesh.artifacts[0])["ok"]
    obj_text = Path(mesh.artifacts[0]).read_text(encoding="utf-8")
    assert "usemtl site_building" in obj_text
    assert "usemtl site_sport" in obj_text
    view = root / "campus-isometric.svg"
    export_model_preview(mesh.artifacts[0], view, title="校园模型检视")
    svg = view.read_text(encoding="utf-8")
    assert f'fill="{COLORS["site_sport"]}"' in svg
    assert f'fill="{COLORS["site_forecourt"]}"' in svg

    runner = StageRunner(project, root / "delivery")
    outcome = runner.stage_S8()
    assert outcome.status == "degraded"
    data = json.loads((runner.out / "08-delivery" / "sector-takeoff.json")
                      .read_text(encoding="utf-8"))
    site = data["campus_site"]
    assert site["status"] == "proposed_massing_only"
    assert {b["key"] for b in site["blocks"]} == {
        "teach", "canteen", "gym", "sport", "forecourt"}
    assert next(b for b in site["blocks"] if b["key"] == "teach")[
        "footprint_m2"] == round(ground.area_m2, 2)
    assert next(b for b in site["blocks"] if b["key"] == "sport")[
        "massing_volume_m3"] is None
