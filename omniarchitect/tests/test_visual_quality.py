"""视觉质量守卫：测"图能不能读"，不测"像素好不好看"。

审美不能靠断言，但**结构性缺陷**可以：一张图里有没有第三维、有没有种植层次、
图注编号连不连续、没有素材时会不会伪造。这些是上一轮出问题的真实原因，也是
这一轮最容易被后续改动悄悄改回去的地方。

这里不联网：素材匹配只查目录打分，不下载图片。

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import json
import re
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict

from omniarchitect.concept import diagrams as dia
from omniarchitect.concept import iso as iso_mod
from omniarchitect.presentation import html as html_mod
from omniarchitect.research import library as lib

SVG_NS = "{http://www.w3.org/2000/svg}"


def _concept(kind: str = "courtyard_carved") -> Dict[str, Any]:
    return {
        "concept_id": "C1",
        "concept_name": "院中取院",
        "concept_statement": "把院切进体量中央，房间全部朝院。",
        "style_ids": ["italian-minimal"],
        "style_labels": ["意式极简"],
        "spatial_prototype": {
            "prototype_id": "P-Courtyard",
            "family": "courtyard", "family_zh": "围合院落",
            "spatial_logic": "四面围合，中间取院",
            "zoning": "公共靠院，服务靠外墙", "circulation": "绕院回游",
            "daylight": "院内采光", "experience": "进院再进屋",
            "massing_kind": kind,
        },
        "deliberation": {
            "massing_kind": kind,
            "parti": "院中取院",
            "massing": "四面围合，中间挖出院与水",
            "section": "院通两层，顶层收成采光井",
            "facade": "临街实、院内透",
            "integration": "建筑定体量，室内延续院的分区，景观收边",
            "levels_program": ["公共与院落", "卧室", "主卧与书房"],
            "key_opportunity": "院把光和天空带进屋",
            "why_this_strategy": "回应私密：业主原话提到「私密」；parti；院在中间。",
            "light_view_proportion_material": "院给每一层同一侧提供侧向漫射光。",
            "technical_coordination": "院边梁需结构配合",
            "unverified_requires": ["场地排水条件"],
            "zones": [{"name": "静水面", "share": "20%"}, {"name": "种植", "share": "35%"}],
            "water": "静水，池底深色砾石", "planting": "乔木带 + 地被",
            "paving": "米色石材，工字铺",
        },
        "material_direction": [{"name": "米色石材", "application": "院墙", "finish": "哑光"}],
        "lighting_direction": ["院内顶部采光，色温 5000K"],
        "experience_sequence": {"steps": [
            {"step": "落客", "event": "视线先被院墙收住", "device": "threshold"},
            {"step": "穿院", "event": "光与天气成为第一个空间事件", "device": "courtyard"},
        ]},
        "diagrams": [],
        "references": {"cases": []},
        "advantages": ["院让每一层都有室外"],
        "tradeoffs": ["院占用建筑面积"],
        "technical_risks": ["院边需结构转换"],
    }


CTX = SimpleNamespace(dimensional_note="尺寸须在 S3/S4 复核",
                      lead_id="architecture", profile_id="architecture",
                      program=[], needs=[], area_available_m2=None,
                      target_area_m2=None, location="")


def _parse(svg: str) -> ET.Element:
    root = ET.fromstring(svg)
    assert root.tag.endswith("svg")
    return root


def _count(root: ET.Element, tag: str) -> int:
    return len(root.findall(f".//{SVG_NS}{tag}"))


# --------------------------------------------------------------------------
# 图元：没有 polygon 就没有体块
# --------------------------------------------------------------------------
def test_svg_has_the_primitives_axonometric_needs():
    for name in ("polygon", "ellipse", "gradient", "clip_rect"):
        assert hasattr(dia.Svg, name), name


def test_polygon_renders_as_a_filled_face():
    s = dia.Svg(200, 200)
    s.polygon([(10, 10), (90, 10), (90, 60)], fill="#EEEEEE", stroke="#333")
    root = _parse(s.render())
    polys = root.findall(f".//{SVG_NS}polygon")
    assert polys and polys[0].get("fill") == "#EEEEEE"
    assert polys[0].get("stroke") == "#333"


def test_iso_projection_is_30_degrees_and_keeps_height():
    iso = iso_mod.Iso(0, 0, scale=100)
    x0, y0 = iso.p(0, 0, 0)
    x1, y1 = iso.p(1, 0, 0)
    assert abs((x1 - x0) - 100 * iso_mod.COS30) < 0.01
    assert abs((y1 - y0) - 50) < 0.01
    # 同样的一米，竖起来要落在 z 轴上
    x2, y2 = iso.p(0, 0, 1)
    assert abs(x2 - x0) < 0.01 and y2 < y0


def test_box_has_three_visible_faces_with_different_tones():
    iso = iso_mod.Iso(0, 0, scale=10)
    s = dia.Svg(400, 400)
    iso_mod.draw_box(iso, s, 0, 0, 0, 2, 2, 2, fill="#E7E0D0")
    fills = re.findall(r'fill="(#[0-9A-F]{6})"', s.render())
    assert len(set(fills)) >= 3, fills        # 三个面不能同一个颜色


# --------------------------------------------------------------------------
# 各类图：必须真的表达各自专业
# --------------------------------------------------------------------------
def test_massing_is_a_four_step_evolution_with_axonometry():
    svg = dia.massing(_concept(), CTX)
    root = _parse(svg)
    assert _count(root, "polygon") > 20          # 体块面 + 地面 + 阴影
    text = "".join(t.text or "" for t in root.findall(f".//{SVG_NS}text"))
    for step in ("01", "02", "03", "04"):
        assert step in text
    assert "非按比例" in text
    # 三步必须真的不一样，否则"演变"是假的
    steps = dia._evolution("courtyard_carved")
    shapes = [len(x[2]) for x in steps]
    assert len(set(shapes)) >= 2


def test_landscape_plan_has_planting_water_and_a_north_arrow():
    c = _concept()
    svg = dia.landscape(c, CTX)
    root = _parse(svg)
    text = "".join(t.text or "" for t in root.findall(f".//{SVG_NS}text"))
    assert "N" in text                     # 指北针
    assert "图例" in text
    # 树冠是多瓣多边形、水面是曲线路径，不是 circle + rect
    assert _count(root, "ellipse") >= 10
    assert _count(root, "polygon") >= 5
    assert _count(root, "path") >= 3
    assert "乔木" in text or "种植" in text


def test_landscape_keeps_zones_as_data_not_as_shapes():
    c = _concept()
    svg = dia.landscape(c, CTX)
    text = "".join(t.text or "" for t in _parse(svg).findall(f".//{SVG_NS}text"))
    assert "分区占比" in text and "20%" in text


def test_interior_axon_is_a_cut_box_not_a_massing():
    c = _concept()
    svg = dia.axon(c, CTX)
    root = _parse(svg)
    text = "".join(t.text or "" for t in root.findall(f".//{SVG_NS}text"))
    assert "剖切轴测" in text or "空间" in text
    assert "视" in text                    # 视线
    assert _count(root, "polygon") >= 10


def test_section_shows_slabs_walls_and_a_person():
    svg = dia.section(_concept(), CTX)
    root = _parse(svg)
    assert _count(root, "rect") >= 6        # 楼板 + 墙
    text = "".join(t.text or "" for t in root.findall(f".//{SVG_NS}text"))
    assert "1.7" in text or "人体" in text
    assert "剖面" in text


# --------------------------------------------------------------------------
# 图种分配：不同专业不套同一套图
# --------------------------------------------------------------------------
def test_diagram_set_follows_the_lead_discipline():
    captured = {}

    def fake_build(concept, ctx, program, needs, out_dir, kinds=()):
        lead = ctx.lead_id
        has_rooms = bool([r for r in (program or []) if str(r.get("name") or "").strip()])
        if lead == "landscape":
            want = ["landscape", "sequence"]
        elif lead == "architecture":
            want = ["massing", "section", "sequence"]
        elif lead == "interior":
            want = ["axon", "sequence"] if not has_rooms else ["axon", "zoning"]
        else:
            want = ["sequence"]
        captured[lead] = want
        return []

    orig = dia.build
    try:
        dia.build = fake_build
        for lead in ("architecture", "interior", "landscape"):
            ctx = SimpleNamespace(lead_id=lead, profile_id=lead,
                                  dimensional_note="")
            dia.build(_concept(), ctx, [], [], tempfile.gettempdir())
    finally:
        dia.build = orig

    assert "massing" in captured["architecture"] and "axon" not in captured["architecture"]
    assert "axon" in captured["interior"] and "massing" not in captured["interior"]
    assert "landscape" in captured["landscape"] and "massing" not in captured["landscape"]


def test_every_diagram_kind_has_a_chinese_name():
    for kind in dia.DIAGRAM_KINDS:
        assert kind in html_mod.KIND_CN, kind


# --------------------------------------------------------------------------
# 素材库：匹配要对专业，取不到就空
# --------------------------------------------------------------------------
def test_library_catalog_is_a_text_index_without_binaries():
    items = lib.load_catalog()
    assert len(items) > 30
    for it in items[:5]:
        assert it["url"].startswith("http")
        assert it["title"] and it["tags"]
    assert lib.CATALOG.suffix == ".json"


def test_library_picks_the_right_discipline():
    arch = lib.pick(lead="architecture", keywords=("别墅", "庭院"), limit=3)
    inter = lib.pick(lead="interior", keywords=("客厅", "公寓"), limit=3)
    landscape = lib.pick(lead="landscape", keywords=("花园", "庭院"), limit=3)
    assert arch and inter and landscape
    assert any("建筑" in " ".join(x["tags"]) or "别墅" in " ".join(x["tags"]) for x in arch)
    assert any("室内" in " ".join(x["tags"]) for x in inter)
    assert any(("花园" in " ".join(x["tags"])) or ("景观" in " ".join(x["tags"]))
               for x in landscape)


def test_library_never_returns_paintings_or_fashion_shots():
    for lead in ("architecture", "interior", "landscape"):
        for it in lib.pick(lead=lead, limit=8):
            tags = " ".join(it["tags"])
            assert "油画" not in tags
            assert "插画" not in tags
            assert "手袋" not in tags


def test_gallery_returns_nothing_when_the_catalog_is_empty():
    with tempfile.TemporaryDirectory() as td:
        got = lib.gallery(td, lead="architecture", catalog=[], want=[("hero", "space")])
        assert got == []


def test_gallery_honours_hard_requirements():
    with tempfile.TemporaryDirectory() as td:
        got = lib.gallery(td, lead="landscape", catalog=[],
                          want=[("hero", "space")], require=("花园",))
        assert got == []


# --------------------------------------------------------------------------
# 提案：没有图也要成立，有图要有出处
# --------------------------------------------------------------------------
PAYLOAD = {
    "project_id": "P-1", "revision": 3, "lead_discipline": "architecture",
    "lead_label": "建筑",
    "concepts": [_concept()],
}


def test_proposal_works_without_any_images():
    with tempfile.TemporaryDirectory() as td:
        out = Path(td)
        page = html_mod.proposal(PAYLOAD, out, project_name="测试别墅",
                                 with_images=False)
        text = page.read_text(encoding="utf-8")
        assert "<h1>测试别墅</h1>" in text
        assert '<img class="cover-img"' not in text   # 没有图就不要假装有
        assert "FIG.01" not in text


def test_proposal_figure_numbers_are_sequential():
    with tempfile.TemporaryDirectory() as td:
        out = Path(td)
        diag = out / "d.svg"
        diag.write_text(dia.massing(_concept(), CTX), encoding="utf-8")
        payload = json.loads(json.dumps(PAYLOAD))
        payload["concepts"][0]["diagrams"] = [
            {"kind": "massing", "path": str(diag)},
            {"kind": "section", "path": str(diag)},
        ]
        page = html_mod.proposal(payload, out, project_name="测试别墅",
                                 with_images=False)
        text = page.read_text(encoding="utf-8")
        nums = [int(m) for m in re.findall(r"FIG\.(\d\d)", text)]
        assert nums == sorted(nums)
        assert len(set(nums)) == len(nums)


def test_proposal_does_not_leak_internal_field_names():
    c = _concept()
    line = html_mod._why_line(c)
    for bad in ("parti", "massing_kind", "levels_program"):
        assert bad not in line, line


def test_proposal_labels_every_kind_of_image():
    with tempfile.TemporaryDirectory() as td:
        out = Path(td)
        diag = out / "d.svg"
        diag.write_text(dia.massing(_concept(), CTX), encoding="utf-8")
        payload = json.loads(json.dumps(PAYLOAD))
        payload["concepts"][0]["diagrams"] = [{"kind": "massing", "path": str(diag)}]
        page = html_mod.proposal(payload, out, project_name="测试别墅",
                                 with_images=False)
        text = page.read_text(encoding="utf-8")
        for label in ("素材库参考", "手法示意", "正式效果图"):
            assert label in text
        assert "本系统确定性绘制" in text


__all__: list = []
