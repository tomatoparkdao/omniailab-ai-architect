"""设计交接层（视觉任务书 / SketchUp / 一致性）的守卫测试。

守四件事：

1. 提示词里的数字必须来自模型——景观不能被称为"99 个房间"，
   学校不能把 24 000 m² 的"场地基面"当成最大的房间；
2. SketchUp 脚本的长度必须带 `.mm`，否则整个模型小 25.4 倍；
3. 任务书与模型不同步时要报 stale，不能拿旧任务书继续画图；
4. 没有 MCP / 平台时状态如实写 not_configured，并且留下可执行的东西。

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from omniarchitect import consistency, sketchup, studio, visual_brief
from omniarchitect.model import Element, Level, Project, Space


def _room(pid: str, name: str, use: str, box, level: str = "L1") -> Space:
    x0, y0, x1, y1 = box
    return Space(id=pid, name=name, use=use, level_id=level,
                 boundary_mm2d=[(x0, y0), (x1, y0), (x1, y1), (x0, y1)])


def _house() -> Project:
    p = Project(project_id="h", name="测试住宅")
    p.levels.append(Level(id="L1", name="一层", elevation_mm=0, height_mm=2900))
    p.spaces.append(_room("ENV", "套内轮廓", "envelope", (0, 0, 12000, 9000)))
    p.spaces.append(_room("LIV", "客厅", "living", (0, 0, 5000, 4000)))
    p.spaces.append(_room("BED", "主卧", "bedroom", (5000, 0, 9000, 4000)))
    p.spaces.append(_room("BATH", "主卫", "bathroom", (9000, 0, 12000, 3000)))
    p.elements.append(Element(id="W1", type="wall", level_id="L1",
                              geometry={"start": [0, 0], "end": [12000, 0],
                                        "thickness_mm": 200}, properties={}))
    p.elements.append(Element(id="D1", type="door", level_id="L1",
                              geometry={"host_wall": "W1", "offset_mm": 1000,
                                        "width_mm": 900, "height_mm": 2100},
                              properties={}))
    p.elements.append(Element(id="WIN1", type="window", level_id="L1",
                              geometry={"host_wall": "W1", "offset_mm": 4000,
                                        "width_mm": 1800, "height_mm": 1500,
                                        "sill_mm": 900}, properties={}))
    return p


def _school() -> Project:
    """A school has a 20 000 m² site ground — which is *not* a room."""
    p = Project(project_id="s", name="测试小学")
    p.levels.append(Level(id="L1", name="一层", elevation_mm=0, height_mm=3900))
    p.spaces.append(Space(id="SITE", name="场地基面", use="site_ground",
                          level_id="L1", boundary_mm2d=[(0, 0), (200000, 0),
                                                        (200000, 120000), (0, 120000)]))
    p.spaces.append(_room("T1", "普通教室 1", "teaching", (0, 0, 9000, 7000)))
    p.spaces.append(_room("T2", "普通教室 2", "teaching", (9000, 0, 18000, 7000)))
    p.spaces.append(_room("COR", "走廊", "circulation", (0, 7000, 18000, 9500)))
    return p


def _garden() -> Project:
    p = Project(project_id="g", name="测试庭院")
    p.levels.append(Level(id="L-SITE", name="场地", elevation_mm=0, height_mm=0))
    for i, (name, use, box) in enumerate((
            ("水面", "water", (8000, 8000, 12000, 12000)),
            ("绿地与种植（N）", "planting", (0, 15000, 20000, 20000)),
            ("园路 1", "circulation", (0, 0, 20000, 1500)))):
        p.spaces.append(Space(id=f"S{i}", name=name, use=use, level_id="L-SITE",
                              boundary_mm2d=[(box[0], box[1]), (box[2], box[1]),
                                             (box[2], box[3]), (box[0], box[3])],
                              properties={"design_z_mm": 0}))
    return p


# --------------------------------------------------------------------------
# 1. 专业口径
# --------------------------------------------------------------------------
def test_landscape_speaks_in_zones_not_rooms() -> None:
    """景观叫"分区"。把种植带说成房间，提示词就会要一个室内空间。"""
    facts = visual_brief.geometry_facts(_garden(), None, "landscape")
    assert facts["unit"] == "分区"
    assert facts["rooms"] == 3
    inv = " ".join(visual_brief._invariants(facts, "landscape"))  # noqa: SLF001
    assert "分区数量固定" in inv
    assert "房间" not in inv


def test_site_ground_is_not_counted_as_the_biggest_room() -> None:
    """20 000 m² 的场地基面不是"最大的房间"。

    算进去，提示词就会要求一个两万平方米的室内空间。
    """
    facts = visual_brief.geometry_facts(_school(), None, "architecture")
    assert facts["rooms"] == 3          # 两间教室 + 走廊，不含场地
    # 教室 9×7=63 m² 大于走廊 18×2.5=45 m²，所以最大的是教室
    assert facts["largest_room"]["name"] == "普通教室 1"
    assert facts["largest_room"]["area_m2"] < 100


def test_prompt_carries_geometry_numbers() -> None:
    """提示词必须带模型里的数：房间数、门窗数、层高、外轮廓。"""
    pkg = visual_brief.brief(_house(), "interior", style="暖木风")
    shot = pkg["shots"][0]
    assert "3 个房间" in shot["prompt"] or "3 个" in shot["prompt"]
    assert "层高 2.90 m" in shot["prompt"]
    # 三个房间铺开是 0–12 m × 0–4 m，不是套内轮廓的 12 × 9
    assert "12.0 m × 4.0 m" in shot["prompt"]
    assert shot["invariants"] and "不得合并" in " ".join(shot["invariants"])


def test_three_disciplines_do_not_share_a_template() -> None:
    """建筑、室内、景观的镜头与光线不能是同一句模板。"""
    a = visual_brief.brief(_school(), "architecture")["shots"][0]["prompt"]
    i = visual_brief.brief(_house(), "interior")["shots"][0]["prompt"]
    l = visual_brief.brief(_garden(), "landscape")["shots"][0]["prompt"]
    assert a != i != l
    assert "建筑" in a and "室内" in i and "景观" in l


# --------------------------------------------------------------------------
# 2. SketchUp 单位
# --------------------------------------------------------------------------
def test_ruby_lengths_are_millimetres() -> None:
    """SketchUp Ruby 把裸数字当英寸；不带 .mm 会小 25.4 倍。"""
    payload = sketchup.scene_payload(_house())
    ruby = sketchup.build_ruby(payload)
    assert ".mm" in ruby
    # 墙长 12 000 mm 必须写成 12000.0.mm，而不是裸 12000.0
    assert "12000.0.mm" in ruby
    assert "pushpull(2900.0.mm)" in ruby
    assert "25.4 / 25.4" not in ruby


def test_sketchup_job_reports_state_and_keeps_script() -> None:
    with tempfile.TemporaryDirectory() as td:
        out = Path(td)
        job = sketchup.write_job(_house(), out, project_dir=out)
        assert job["state"] in ("not_configured", "available", "partial")
        assert (out / "build_model.rb").is_file()
        assert (out / "camera_jobs.json").is_file()
        assert job["counts"]["walls"] == 1
        assert job["counts"]["openings"] == 2
        # 脚本必须自己声明洞口是标记不是切割
        head = (out / "build_model.rb").read_text(encoding="utf-8")[:600]
        assert "标记" in head and "切割" in head


# --------------------------------------------------------------------------
# 3. 一致性
# --------------------------------------------------------------------------
def test_stale_brief_is_caught() -> None:
    """任务书记 3 个房间，模型后来变成 4 个——必须报 stale。"""
    p = _house()
    pkg = visual_brief.brief(p, "interior")
    assert consistency.check_brief(p, pkg)["ok"] is True
    p.spaces.append(_room("NEW", "书房", "study", (0, 4000, 3000, 7000)))
    rep = consistency.check_brief(p, pkg)
    assert rep["ok"] is False and rep["stale"] is True
    assert any("rooms" in d for d in rep["diffs"])


def test_mesh_comparison_flags_a_wrong_scale() -> None:
    """导出的网格比模型小 1000 倍（米当毫米）要被抓到。"""
    p = _house()
    with tempfile.TemporaryDirectory() as td:
        obj = Path(td) / "m.obj"
        # 与模型同尺寸（12 m × 4 m），但用米写：应被识别为换算而非错误
        obj.write_text("v 0 0 0\nv 12 0 0\nv 12 4 0\nv 0 4 0\n", encoding="utf-8")
        rep = consistency.check_mesh(p, obj, "interior")
    assert rep["skipped"] is False
    assert rep["ok"] is True                  # 自动按米换算后相符
    assert rep["scale_applied"] == 1000.0


# --------------------------------------------------------------------------
# 4. 交接包
# --------------------------------------------------------------------------
def test_studio_package_writes_everything_and_tells_the_truth() -> None:
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "handoff"
        res = studio.package(_house(), out, project_dir=Path(td))
        assert (out / "visual-brief.json").is_file()
        assert (out / "linework.svg").is_file()
        assert (out / "mcp-status.json").is_file()
        assert (out / "sketchup" / "build_model.rb").is_file()
        readme = (out / "README.md").read_text(encoding="utf-8")
    assert "not_configured" in readme          # 没连上就要写没连上
    assert "未生成任何替代图" in readme
    assert res["provider"]["image_generation"] in ("not_configured", "connected")
    assert res["discipline"] == "interior"


def test_linework_cuts_notches_through_walls() -> None:
    """线稿里洞口是墙上的白色缺口，不是墙中间一条看不见的细线。"""
    payload = sketchup.scene_payload(_house())
    with tempfile.TemporaryDirectory() as td:
        path = sketchup.linework(payload, Path(td) / "lw.svg")
        svg = path.read_text(encoding="utf-8")
    assert 'fill="#2f3437"' in svg            # 墙填实
    assert 'fill="#ffffff"' in svg            # 洞口挖白
    assert svg.count("<polygon") >= 2
