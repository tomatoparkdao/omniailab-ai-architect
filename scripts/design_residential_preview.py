#!/usr/bin/env python
"""Generate an explicitly unsigned 150 m²-class residential preview package.

The shell is a synthetic case fixture (131.56 m² interior polygon), not a
surveyed client apartment. No gate is confirmed by this script.

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from omniarchitect.adapters import DxfAdapter  # noqa: E402
from omniarchitect.paths import test_output_root
from omniarchitect.demo import build_demo_project  # noqa: E402
from omniarchitect.sector.plandraw import plan_svg  # noqa: E402
from omniarchitect.registry import SIGNATURE  # noqa: E402
from omniarchitect.workflow import StageRunner  # noqa: E402
from scripts.design_sector_cases import _shot  # noqa: E402


def main() -> int:
    root = test_output_root() / "residential-150-preview"
    project = build_demo_project(root / "project")
    project.project_id = "preview-residence-150"
    project.name = "150㎡级住宅精装修 · 合成案例"
    project.constraints["gross_area_target_m2"] = 150
    project.meta["synthetic_case"] = True
    project.sources = [{"type": "case_fixture", "file": "",
                        "note": "合成几何，未获现场图纸或实测尺寸"}]
    project.assumptions = [item for item in project.assumptions
                           if "由图纸识别" not in item and "由原始户型图" not in item]
    project.assumptions.append("150㎡为项目级目标；模型套内轮廓约131.56㎡，不等于经核算建筑面积")
    for item in [*project.spaces, *project.elements]:
        if item.source in ("drawing_import", "drawing_inferred"):
            item.source = "case_assumption"
            item.confidence = min(item.confidence, 0.35)
    project.save(root / "project" / "project.json")
    (root / "project" / "README.md").write_text("\n".join([
        "# 150㎡级住宅 · 合成案例（待审查）", "",
        "- 150㎡是项目建筑面积目标，不是已核算面积。",
        "- 131.56㎡为本案例套内多边形面积，几何来自合成样例，非客户图纸或实测。",
        "- 结构、机电、材料、造价与当地规范均待专业复核。",
        "- 此包不含真实业主 G3–G8 审批，不得用于施工或采购。", "", SIGNATURE,
    ]), encoding="utf-8")

    runner = StageRunner(project, root / "delivery")
    chosen = runner._ensure_scheme_installed()
    s3 = root / "S3"
    s3.mkdir(parents=True, exist_ok=True)
    plan = DxfAdapter().draw_plan(project, s3 / "residence-plan.dxf",
                                  level_id="L1", scheme=chosen,
                                  title="住宅方案平面（合成案例，待审查）")
    if not plan.ok:
        raise RuntimeError(f"S3 plan read-back failed: {plan.errors}")
    (s3 / "residence-plan.svg").write_text(
        plan_svg(runner.schemes[chosen], title="150㎡级住宅 · 方案平面预览"),
        encoding="utf-8")
    results = []
    for stage in ("S4", "S5", "S6", "S7", "S8"):
        outcome = getattr(runner, f"stage_{stage}")()
        results.append({"stage": stage, "status": outcome.status,
                        "artifacts": outcome.artifacts, "notes": outcome.notes,
                        "error": outcome.error})
        if outcome.status in ("failed", "blocked"):
            raise RuntimeError(f"{stage}: {outcome.error}")
    screenshots = []
    for svg in (s3 / "residence-plan.svg",
                runner.out / "04-preliminary" / "I-04-ceiling.svg",
                runner.out / "07-documents" / "I-05-floor-finish.svg"):
        png = svg.with_suffix(".png")
        if svg.is_file() and _shot(svg, png, width=1200):
            screenshots.append(str(png))
    project.save(root / "project" / "project-preview.json")
    (root / "review-status.json").write_text(json.dumps({
        "project": project.project_id, "geometry": "synthetic_case_fixture",
        "gross_area_target_m2": 150,
        "model_interior_envelope_m2": project.meta.get("envelope_area_m2"),
        "gates": "G3–G8 not approved", "formal_delivery": False,
        "surveyed": False, "licensed_review": False,
        "limitations": ["现场尺寸/结构待核", "材料样板与灯具回路待确认",
                        "CAD 为方案/待审查深度", "OBJ 为可编辑网格，不是参数化 BIM"],
        "screenshots": screenshots,
        "results": results,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"residential preview: {root}")
    print(" ".join(f"{r['stage']}={r['status']}" for r in results))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
