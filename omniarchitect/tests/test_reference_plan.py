"""图纸参考图：能上传、可核对、不拿 DXF 冒充。

这一组守三件事：

1. 参考图必须是真实存在的 SVG/PNG（含尺寸文字），不是一条 `.dxf` 路径；
2. 参考图与 DXF 出自同一份图元，房间/墙体/门窗数量对得上；
3. 视角缺数据就标待补充，不冒充完成。

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

from omniarchitect import concept as C
from omniarchitect import reference_plan as R
from omniarchitect.demo import build_demo_project
from omniarchitect.intake.gate import decide_gate as decide_g1
from omniarchitect.intake.interview import answer_question, start_interview
from omniarchitect.workflow import StageRunner


def _confirmed(tmp: Path):
    """跑到 G3 之前一步：S3 已出方案，模型里还没有装方案。"""
    p = build_demo_project(tmp / "proj")
    p.constraints = {**(p.constraints or {}), "style": "现代意式极简"}
    p.save(tmp / "proj" / "project.json")
    start_interview(p, "150㎡ 大平层，一家三口，现代意式极简")
    answer_question(p, "base.needs", "客厅要能坐 8 个人；东西很多要收纳")
    decide_g1(p, "approved", by="业主")
    runner = StageRunner(p, tmp / "out", project_dir=tmp / "proj")
    runner.run_stage("S2", confirm=False)
    chosen = next(c for c in p.meta["concept"]["options"]["concepts"]
                  if (c.get("spatial_prototype") or {}).get("plan_strategy"))
    C.select(p, chosen["concept_id"])
    runner.approve("S2", by="业主")
    runner.run_stage("S3", confirm=False)
    return p, runner


def test_reference_is_a_real_svg_and_png_not_a_dxf_path():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        p, runner = _confirmed(tmp)
        model = runner._reference_model(runner.scheme_variant)
        ref = R.build_reference(model, tmp / "ref", scheme="A")

        assert ref["files"], "没有输出任何参考文件"
        for f in ref["files"]:
            q = Path(f)
            assert q.exists() and q.stat().st_size > 512, f
            assert q.suffix.lower() in (".svg", ".png"), q.suffix
        assert not any(Path(f).suffix.lower() in R.NON_INPUT_FORMATS
                       for f in ref["files"]), "DXF/DWG 不能当图像模型输入"

        # SVG 能被解析，且尺寸是矢量文字
        tree = ET.parse(ref["svg"])
        texts = [t.text for t in tree.iter("{http://www.w3.org/2000/svg}text") if t.text]
        assert any(ch.isdigit() for t in texts for ch in t), "SVG 里没有尺寸数字"
        assert ref["counts"]["dimension_texts"] > 0
        assert ref["counts"]["spaces"] > 5 and ref["counts"]["walls"] > 5
        assert R.verify_files(ref)["all_ok"] is True


def test_reference_matches_the_model_it_came_from():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        p, runner = _confirmed(tmp)
        model = runner._reference_model(runner.scheme_variant)
        ref = R.build_reference(model, tmp / "ref", scheme="A")

        spaces = [s for s in model.spaces if s.use != "envelope"]
        walls = [w for w in model.by_type("wall")]
        doors = [d for d in model.by_type("door")]
        assert ref["counts"]["spaces"] == len(spaces)
        assert ref["counts"]["walls"] == len(walls)
        assert ref["counts"]["doors"] == len(doors)


def test_reference_flags_missing_views_instead_of_faking_them():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        p, runner = _confirmed(tmp)
        model = runner._reference_model(runner.scheme_variant)
        ref = R.build_reference(model, tmp / "ref", scheme="A")
        assert ref["has_plan_geometry"] is True
        assert ref["has_elevation"] is False, "还没有立面适配器，不能声称有"
        assert ref["has_perspective"] is False
        assert ref["ai_input"]["not_accepted"] == ["dxf", "dwg"]
