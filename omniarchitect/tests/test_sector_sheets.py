"""S4–S8 专业交付能力的守卫测试。

守四件事：

1. 景观四张专项图（铺装/种植/竖向/节点）都从模型出，且各自只表达本专业内容；
2. 同材质合并后仍保留孔洞——环路不能被填成一个实心圆盘；
3. 门窗表按模型洞口统计，门与窗各自编号、楼层按建造顺序排；
4. 交付清单跨 run 合并，且不把上一轮的清单列进自己。

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import tempfile
from pathlib import Path

from omniarchitect.adapters.drawing import Prim
from omniarchitect.model import Element, Level, Project, Space
from omniarchitect.sector import landscape_sheets


def _square(x0: float, y0: float, size: float):
    return [(x0, y0), (x0 + size, y0), (x0 + size, y0 + size), (x0, y0 + size)]


def _garden() -> Project:
    """A courtyard model: outer gravel, a loop path with a hole, beds, water."""
    p = Project(project_id="g")
    p.levels.append(Level(id="L-SITE", name="场地", elevation_mm=0, height_mm=0))
    outer = _square(0, 0, 20000)
    p.spaces.append(Space(id="S-OUTER", name="透水砂砾场地", use="paving",
                          level_id="L-SITE", boundary_mm2d=outer,
                          properties={"infill_kind": "gravel", "design_z_mm": 0.0}))
    # Four path pieces forming a ring — unioned they must keep the middle open.
    ring = (_square(4000, 4000, 2000) + _square(14000, 4000, 2000)
            + _square(4000, 14000, 2000) + _square(14000, 14000, 2000))
    for i in range(4):
        p.spaces.append(Space(id=f"S-PATH-{i}", name=f"园路 {i}", use="circulation",
                              level_id="L-SITE",
                              boundary_mm2d=ring[i * 4:(i + 1) * 4],
                              properties={"design_z_mm": 0.0}))
    p.spaces.append(Space(id="S-WATER", name="水面", use="water", level_id="L-SITE",
                          boundary_mm2d=_square(8500, 8500, 3000),
                          properties={"design_z_mm": -120.0}))
    p.spaces.append(Space(id="S-BED", name="绿地与种植（N 侧）", use="planting",
                          level_id="L-SITE", boundary_mm2d=_square(1000, 17000, 5000),
                          properties={"design_z_mm": 180.0}))
    p.elements.append(Element(
        id="TREE-001", type="other", level_id="L-SITE",
        geometry={"center": [3000, 19000]},
        properties={"landscape_kind": "tree", "species": "待选型",
                    "host_zone": "S-BED"}))
    p.elements.append(Element(
        id="L-NODE-01", type="other", level_id="L-SITE",
        geometry={"center": [10000, 8000]},
        properties={"landscape_kind": "view_node", "name": "临水观景点"}))
    return p


# --------------------------------------------------------------------------
# 1. 四张专项图各自只表达本专业内容
# --------------------------------------------------------------------------
def test_four_landscape_sheets_come_from_the_model() -> None:
    p = _garden()
    paving, rows = landscape_sheets.paving_sheet(p)
    planting, trees = landscape_sheets.planting_sheet(p)
    grading, levels = landscape_sheets.grading_sheet(p)
    nodes, index = landscape_sheets.node_sheet(p)
    assert paving and rows, "铺装图不能为空"
    assert planting and trees, "种植图不能为空"
    assert grading and levels, "竖向图不能为空"
    assert nodes and index, "节点图不能为空"
    # 铺装图只画硬质：水面与种植不能出现在铺装图里
    layers = {item.layer for item in paving}
    assert "L-ZONE-WATER" not in layers and "L-ZONE-PLANT" not in layers
    # 种植图必须带上每一棵树，且树号可追溯到模型
    assert any(item.layer == "L-TREE" for item in planting)
    assert {row[0] for row in trees} == {"TREE-001"}


def test_grading_labels_levels_in_metres_not_millimetres() -> None:
    """竖向表写 -120.00 会被读成 -120 米。

    模型存的是 mm；图纸标的是 m。混着写，客户会以为水池挖了一百多米。
    """
    _, levels = landscape_sheets.grading_sheet(_garden())
    values = dict(levels)          # 标高按材质/用途归类，不是按单个空间
    assert values["水面"] == "-0.12 m", values
    assert values["绿地与种植"] == "+0.18 m", values


# --------------------------------------------------------------------------
# 2. 合并保留孔洞
# --------------------------------------------------------------------------
def test_merged_ring_keeps_its_hole() -> None:
    """环路合并后必须还是环，不是实心块。

    把一圈铺装 union 成一块时若丢掉内环，图上就是一整块实心色，
    中间的绿地与水景全被盖住——这正是上一版铺装图的问题。
    """
    def rect(x0: float, y0: float, x1: float, y1: float):
        return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]

    bars = [rect(0, 0, 12000, 3000), rect(0, 3000, 3000, 6000),
            rect(9000, 3000, 12000, 6000), rect(0, 6000, 12000, 9000)]
    prims = [Prim("polyline", "L-ZONE-PATH", b, closed=True) for b in bars]
    merged = landscape_sheets._merge_rings(prims, "L-ZONE-PATH")  # noqa: SLF001
    assert len(merged) == 1
    outer, holes = merged[0]
    assert len(holes) == 1, "中间的洞必须作为 inner ring 保留"
    assert len(outer) >= 5 and len(holes[0]) >= 5


# --------------------------------------------------------------------------
# 3. 门窗表
# --------------------------------------------------------------------------
def _school() -> Project:
    p = Project(project_id="s")
    for i, (lid, name) in enumerate((("L1", "一层"), ("L2", "2层"))):
        p.levels.append(Level(id=lid, name=name, elevation_mm=i * 3900, height_mm=3900))
    p.spaces.append(Space(id="ENV", name="轮廓", use="envelope", level_id="L1",
                          boundary_mm2d=_square(0, 0, 20000)))
    p.elements.append(Element(
        id="W1", type="wall", level_id="L1",
        geometry={"start": [0, 0], "end": [20000, 0], "thickness_mm": 240},
        properties={}))
    for i in range(3):
        for lid in ("L1", "L2"):
            p.elements.append(Element(
                id=f"WIN-{lid}-{i}", type="window", level_id=lid,
                geometry={"host_wall": "W1", "offset_mm": 2000 + i * 3000,
                          "width_mm": 2100, "height_mm": 1500, "sill_mm": 900},
                properties={}))
    p.elements.append(Element(
        id="D1", type="door", level_id="L1",
        geometry={"host_wall": "W1", "offset_mm": 1000, "width_mm": 900,
                  "height_mm": 2100},
        properties={}))
    return p


def test_opening_schedule_numbers_doors_and_windows_separately() -> None:
    """同一张表里 M-01 后面接 C-02 会让人以为漏图。

    门与窗是两种产品、两条编号序列，各自从 01 起。
    """
    from omniarchitect.sector import deepening

    p = _school()
    with tempfile.TemporaryDirectory() as td:
        deepening._opening_schedule(p, Path(td))       # noqa: SLF001
        text = (Path(td) / "A-门窗表.md").read_text(encoding="utf-8")
    assert "| M-01 |" in text and "| C-01 |" in text
    assert "C-02" not in text                 # 只有一种窗，不该有第二个编号
    assert "| 6 |" in text                    # 6 樘窗，按模型统计
    assert "一层、2层" in text                 # 楼层按建造顺序，不按字符串


def test_elevations_cover_all_four_sides() -> None:
    """只有南北两面不算立面设计：端部的楼梯、山墙与端教室都在东西面。"""
    from omniarchitect.sector import deepening

    p = _school()
    with tempfile.TemporaryDirectory() as td:
        arts = deepening._school_elevations(p, Path(td))   # noqa: SLF001
    names = {Path(a).stem for a in arts}
    assert {"A-立面-南", "A-立面-北", "A-立面-东", "A-立面-西"} <= names
