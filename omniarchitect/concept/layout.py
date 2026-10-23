"""概念布局：一张概念图与四步推敲共用**同一份几何**。

为什么需要这一层
----------------
v1.15 有两套画法：`plate.plan_plate` 画主图，`evolution._interior_body` 画四步。
两边各写一套百分比坐标，于是同一个"公共核"在两张图上位置不同，主推图里的
大堂到了四步图里变成一条横带，最后一步还会"挪"一下——客户把两页并排看就露了。

这里把几何抽出来一次：区域是归一化矩形，节点是归一化点，联系是折线。
`plate.py` 用它画主图，`evolution.py` 用它画四步——**四步不移动任何已定区域**，
只是按 `appear` 逐步显形、按 `emphasis` 点亮。位置永远一致。

几何从哪来
----------
不新设一套分类，读概念自己已声明的字段：

* 室内：`spatial_prototype.plan_layout`（public_core / guest_wing / tech_core …）；
* 景观：`spatial_prototype.massing_kind`（pond / terraces / grove）。

`plan_layout=public_core` 的酒店必须画**两幅**：裙房公共层与客房标准层。
把它们压成一张图，就会把大堂画成客房层里的一个房间——那是最典型的专业错误。

标注
----
标签位置由图形几何算出来（内部放得下就放内部，放不下引到外侧），并做基本避让：
不出界、不与别的标签重叠、不压在别的区域上。引入引线时只连到最近的边，
不穿过无关区域。图上只留 2–6 个字的短标签，长句交给页面正文。

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

from . import diagrams as dia

Box = Tuple[float, float, float, float]
Pt = Tuple[float, float]

#: 图版配色。与 `evolution._pal` 同名同义，页面主题覆盖时按 key 合并。
PAL: Dict[str, str] = {
    "paper": "#FAF8F3", "ink": "#1E2328", "muted": "#6E736A", "line": "#D6D2C6",
    "accent": "#2F5D45",
    "ground": "#F1EFE7",
    "mass": "#E7EDE6",       # 客房/教学/生产等重复单元
    "mass2": "#EAE6DC",      # 公共（餐厅、会议）
    "core": "#E3DED1",       # 核心（大堂）
    "service": "#DFD9C9",    # 后场、布草
    "paving": "#EDE7D8",
    "terrace": "#EDE8DC",
    "creek": "#E4DFD1",
    "water": "#DDE7EE",
    "waterline": "#9FB3BF",
    "path": "#D3C9B2",
    "pathline": "#B3A88D",
    "green": "#DCE6D3",
    "greenline": "#8FA684",
    "building": "#E9E4D6",
}

#: 先画背景（铺地、台地、水面、房子），再画有边界的功能块。
ORDER = {"paving": 0, "terrace": 1, "creek": 2, "water": 3, "building": 4,
         "mass": 5, "mass2": 6, "public": 6, "service": 7, "core": 8,
         "counter": 9, "circulation": 9, "private": 5}


@dataclass
class Region:
    """一个功能块。box 为归一化 (x, y, w, h)，y 向下。"""
    key: str
    label: str
    box: Box
    kind: str = "mass"
    sub: str = ""
    appear: int = 0
    emphasis: int = -1
    shape: str = "rect"
    #: 内部模数分隔线数量（客房带分成 6 间），只表达"重复单元"，不是真实开间
    ticks: int = 0

    def rect(self, area: Box) -> Box:
        x0, y0, w, h = area
        return (x0 + self.box[0] * w, y0 + self.box[1] * h,
                self.box[2] * w, self.box[3] * h)


@dataclass
class Node:
    """一个点状要素：入口、茶座、电梯。"""
    key: str
    label: str
    x: float
    y: float
    kind: str = "pad"
    appear: int = 0
    emphasis: int = -1
    #: 入口的进入方向（up / right），决定箭头指向，别让门口对着墙
    axis: str = "up"


@dataclass
class Link:
    """一条联系：客流、服务流、视线、园路。"""
    key: str
    pts: Tuple[Pt, ...]
    kind: str = "path"
    arrow: bool = False
    appear: int = 0
    emphasis: int = -1
    dash: str = ""


@dataclass
class Ring:
    """环形游路（椭圆带状）。"""
    cx: float
    cy: float
    rx: float
    ry: float
    appear: int = 0
    emphasis: int = -1


@dataclass
class Tree:
    x: float
    y: float
    r: float = 0.045
    appear: int = 0
    label: str = ""


@dataclass
class Outline:
    """把一组功能区圈成一个"核"。点按顺序连成闭合折线，用于表达"核在哪"。"""
    key: str
    pts: Tuple[Pt, ...]
    appear: int = 0
    emphasis: int = -1


@dataclass
class Frame:
    """一幅图。两幅图（公共层 / 标准层）各自独立，但同一套画法。"""
    key: str
    title: str = ""
    regions: List[Region] = field(default_factory=list)
    nodes: List[Node] = field(default_factory=list)
    links: List[Link] = field(default_factory=list)
    rings: List[Ring] = field(default_factory=list)
    trees: List[Tree] = field(default_factory=list)
    outlines: List[Outline] = field(default_factory=list)
    #: 需要"永远标注"的 key（四步图里也保留），例如入口、水景
    keep: Tuple[str, ...] = ()


# --------------------------------------------------------------------------
# 室内：按 plan_layout 出图，不按"室内"一个大类出图
# --------------------------------------------------------------------------
PUBLIC_LABELS: Dict[str, Dict[str, str]] = {
    "hospitality": {
        "boh": "后场", "boh_sub": "服务梯 · 后勤",
        "dining": "餐厅", "dining_sub": "全日",
        "meeting": "会议", "meeting_sub": "宴会 · 无窗",
        "lobby": "大堂", "lobby_sub": "公共核",
        "recep": "前台", "lift": "客梯厅", "gate": "落客",
    },
    "generic": {
        "boh": "后勤", "boh_sub": "服务梯",
        "dining": "会议", "dining_sub": "多功能",
        "meeting": "接待", "meeting_sub": "洽谈",
        "lobby": "门厅", "lobby_sub": "公共核",
        "recep": "前台", "lift": "电梯厅", "gate": "入口",
    },
}


def _public_floor(sector: str) -> Frame:
    """裙房公共层：大堂+餐厅+会议形成一个核，后场是一条独立的竖向通道。

    这是 `plan_layout=public_core` 的图。客流在右半（落客→大堂→前台→客梯厅），
    服务流在左半（后场→服务梯），两条线不交叉——这正是这个概念要证明的事。
    """
    L = PUBLIC_LABELS.get(sector, PUBLIC_LABELS["generic"])
    regs = [
        Region("boh", L["boh"], (0.03, 0.04, 0.17, 0.92), "service", sub=L["boh_sub"]),
        Region("dining", L["dining"], (0.23, 0.04, 0.39, 0.30), "mass2",
               sub=L["dining_sub"]),
        Region("meeting", L["meeting"], (0.65, 0.04, 0.32, 0.48), "mass2",
               sub=L["meeting_sub"]),
        Region("lobby", L["lobby"], (0.23, 0.34, 0.39, 0.62), "core",
               sub=L["lobby_sub"]),
        Region("recep", L["recep"], (0.455, 0.675, 0.135, 0.07), "counter"),
        Region("lifts", L["lift"], (0.65, 0.52, 0.32, 0.44), "circulation"),
    ]
    nodes = [
        Node("gate", L["gate"], 0.42, 0.985, "gate"),
        Node("slift", "", 0.115, 0.60, "lift"),
        Node("lift_a", "", 0.715, 0.74, "lift"),
        Node("lift_b", "", 0.785, 0.74, "lift"),
    ]
    links = [
        # 客流：落客 → 大堂 → 前台 → 客梯厅（右半侧一条线）
        Link("guest_flow", ((0.42, 0.99), (0.42, 0.88), (0.44, 0.80),
                            (0.50, 0.782), (0.62, 0.782), (0.70, 0.782)),
             "flow", True, appear=1),
        # 服务流：后勤入口 → 服务梯（左半侧，不碰大堂）
        Link("service_flow", ((0.045, 0.92), (0.115, 0.87), (0.115, 0.68)),
             "service", True, appear=1),
        # 界面对外：餐厅与门厅的外墙开窗
        Link("win_dining", ((0.29, 0.04), (0.29, -0.012)), "window", appear=2),
        Link("win_dining2", ((0.40, 0.04), (0.40, -0.012)), "window", appear=2),
        Link("win_dining3", ((0.51, 0.04), (0.51, -0.012)), "window", appear=2),
        Link("win_lobby", ((0.27, 0.958), (0.27, 0.925)), "window", appear=2),
        Link("win_lobby2", ((0.33, 0.958), (0.33, 0.925)), "window", appear=2),
    ]
    outlines = [
        # 公共核 = 大堂 + 餐厅 + 会议，绕开客梯厅的 L 形
        Outline("core", ((0.23, 0.04), (0.97, 0.04), (0.97, 0.52), (0.65, 0.52),
                         (0.65, 0.96), (0.23, 0.96)), appear=3),
    ]
    return Frame("public", "裙房公共层", regs, nodes, links,
                 outlines=outlines, keep=("gate", "lobby"))


def _guest_floor() -> Frame:
    """客房标准层：两排客房 + 一条走廊 + 两端各一个核（客梯 / 服务）。

    这里**没有**公共核：大堂在裙房，不在这层。上一版把它画进标准层，
    于是"大堂"看起来像走廊边上的一个房间。
    """
    regs = [
        Region("guest_top", "客房", (0.03, 0.05, 0.94, 0.33), "private", ticks=6),
        Region("guest_bot", "", (0.03, 0.515, 0.94, 0.33), "private", ticks=6),
        Region("corridor", "走廊", (0.17, 0.395, 0.66, 0.105), "circulation"),
        Region("lifts", "客梯厅", (0.02, 0.335, 0.145, 0.235), "circulation",
               emphasis=3),
        Region("linen", "服务核", (0.845, 0.335, 0.135, 0.235), "service",
               sub="布草·服务梯", emphasis=3),
    ]
    nodes = [Node("glift", "", 0.092, 0.505, "lift"),
             Node("slift_mark", "", 0.912, 0.505, "lift")]
    links = [
        # 客人：客梯厅 → 走廊 → 房门（走走廊下半，不压标签）
        Link("guest_flow", ((0.17, 0.472), (0.84, 0.472)), "flow", True, appear=1),
        Link("win_top", ((0.20, 0.05), (0.20, 0.008)), "window", appear=2),
        Link("win_top2", ((0.50, 0.05), (0.50, 0.008)), "window", appear=2),
        Link("win_top3", ((0.80, 0.05), (0.80, 0.008)), "window", appear=2),
        Link("win_bot", ((0.20, 0.845), (0.20, 0.887)), "window", appear=2),
        Link("win_bot2", ((0.50, 0.845), (0.50, 0.887)), "window", appear=2),
        Link("win_bot3", ((0.80, 0.845), (0.80, 0.887)), "window", appear=2),
    ]
    return Frame("floor", "客房标准层", regs, nodes, links, keep=("lifts",))


#: 非酒店工装的三段式楼层。酒店以外的类型不能套客房图版。
BANDS: Dict[str, Tuple[str, str, str, str]] = {
    # key: (北侧, 中间通道, 南侧, 端部核)
    "tech_core": ("门诊", "医疗街", "医技", "候诊"),
    "medical_street": ("门诊", "医疗街", "医技", "候诊"),
    "dual_corridor": ("洁净区", "走廊", "污染区", "更衣"),
    "cluster_atrium": ("教学", "连廊", "专用教室", "办公"),
    "linear_corridor": ("教学", "连廊", "专用教室", "办公"),
    "public_front": ("办公", "连廊", "教学", "门厅"),
    "process_line": ("生产", "通道", "仓储", "设备"),
    "stacked_module": ("生产", "通道", "仓储", "设备"),
}


def _bands_floor(kind: str, sector: str) -> List[Frame]:
    """其他工装：三段式楼层（北侧／通道／南侧＋端部核）。标签来自类型，不套客房。"""
    top, mid, bot, core = BANDS.get(kind, ("使用空间", "走廊", "辅助空间", "门厅"))
    regs = [
        Region("north", top, (0.03, 0.06, 0.80, 0.30), "mass"),
        Region("south", bot, (0.03, 0.48, 0.80, 0.30), "mass"),
        Region("mid", mid, (0.03, 0.375, 0.80, 0.09), "circulation"),
        Region("core", core, (0.85, 0.06, 0.12, 0.72), "core"),
    ]
    links = [
        Link("flow", ((0.90, 0.90), (0.90, 0.72), (0.43, 0.72), (0.43, 0.42)),
             "flow", True, appear=1),
        Link("win", ((0.25, 0.06), (0.25, 0.012)), "window", appear=2),
        Link("win2", ((0.55, 0.06), (0.55, 0.012)), "window", appear=2),
    ]
    return [Frame("floor", "", regs, nodes=[], links=links, keep=("core",))]


def interior_frames(concept: Dict[str, Any], *, sector: str = "") -> List[Frame]:
    proto = concept.get("spatial_prototype") or {}
    kind = str(proto.get("plan_layout") or proto.get("plan_strategy") or "")
    if "public_core" in kind:
        return [_public_floor(sector), _guest_floor()]
    if "guest_wing" in kind:
        return [_guest_floor()]
    if kind in BANDS:
        return _bands_floor(kind, sector)
    # 没有声明平面组织方式的室内：按业态给三段式，绝不套客房
    guess = {"retail": "public_front", "office": "linear_corridor"}.get(sector,
                                                                       "cluster_atrium")
    return _bands_floor(guess, sector)


# --------------------------------------------------------------------------
# 景观：按 massing_kind 出图。没有水就绝不画水池
# --------------------------------------------------------------------------
def _has_water(concept: Dict[str, Any]) -> bool:
    """这套概念里到底有没有"常年水面"。

    `DLB-LAN-DRY` 的整条主张就是"不做池子"，画一个中心水池等于把备选方案
    画成了主推方案。判据只看声明，不猜：massing_kind 优先，其次否定的说法。
    """
    proto = concept.get("spatial_prototype") or {}
    kind = str(proto.get("massing_kind") or "")
    if kind == "pond":
        return True
    if kind in ("terraces", "grove"):
        return False
    text = " ".join(str(proto.get(k) or "") for k in ("zoning", "daylight", "water"))
    text += " " + str(concept.get("concept_statement") or "")
    if any(w in text for w in ("不做池", "没有水面", "旱溪", "无水")):
        return False
    return any(w in text for w in ("水面", "静水", "水池", "水景"))


def _pond_frame(concept: Dict[str, Any]) -> Frame:
    """一池静水：入口在南，水面居中，茶座在远岸（正对入口的北岸），环路绕水成环。

    四条关系必须同时成立，这是概念自己写的：
    穿门见水（入口正对水面）／绕水一圈（环与入口接通、不穿水）／
    茶座在远岸（与入口隔水相对）／背靠种植、面向房子与水（视线穿过水面看到房子）。
    """
    regs = [
        Region("house", "建筑", (0.78, 0.20, 0.19, 0.60), "building"),
        Region("paving", "", (0.40, 0.90, 0.12, 0.08), "paving"),
        Region("water", "水景", (0.25, 0.325, 0.40, 0.35), "water", shape="ellipse"),
        Region("lawn", "草坪", (0.06, 0.62, 0.16, 0.22), "green"),
    ]
    nodes = [
        Node("gate", "入口", 0.46, 0.985, "gate"),
        Node("seat", "茶座", 0.27, 0.33, "seat", appear=3),
    ]
    rings = [Ring(0.45, 0.50, 0.255, 0.24, appear=2)]
    links = [
        # 入口到环：垂直接到环的下缘，不断在半空
        Link("entry", ((0.46, 0.985), (0.46, 0.742)), "path", False, appear=2),
        # 茶座回望房子：这条线穿过水面才有倒影
        Link("sight_back", ((0.30, 0.345), (0.80, 0.50)), "sight", True, appear=3),
    ]
    trees = [
        Tree(0.09, 0.14, 0.052, 1, "乔木"), Tree(0.20, 0.09, 0.042, 1),
        Tree(0.15, 0.25, 0.050, 1, ""), Tree(0.33, 0.17, 0.044, 1, ""),
        Tree(0.10, 0.47, 0.042, 1), Tree(0.19, 0.80, 0.052, 1),
        Tree(0.31, 0.90, 0.040, 1), Tree(0.66, 0.90, 0.042, 1),
        Tree(0.72, 0.14, 0.040, 1),
    ]
    return Frame("site", "", regs, nodes, links, rings=rings, trees=trees,
                 keep=("gate", "water", "seat"))


def _terrace_frame(concept: Dict[str, Any]) -> Frame:
    """旱溪台地：两级台地 + 一条旱溪（砾石，不是水）+ 整石跨溪 + 低台地茶座。

    两件事必须守住：
    1. 这里**不能出现任何水面**——这套方案的主张就是"用一条旱溪代替水"，
       画个池子等于把备选方案画成了主推方案；
    2. 房子是场地条件，位置与主推方案一致（右缘同一块），不许换方案就挪房子。
    """
    regs = [
        Region("high", "高台地", (0.04, 0.06, 0.74, 0.33), "terrace"),
        Region("low", "低台地", (0.04, 0.50, 0.74, 0.45), "terrace"),
        Region("creek", "旱溪", (0.04, 0.39, 0.74, 0.105), "creek"),
        Region("stone", "", (0.545, 0.355, 0.085, 0.175), "paving"),
        Region("house", "建筑", (0.78, 0.20, 0.19, 0.60), "building"),
        Region("seat", "茶座", (0.175, 0.69, 0.115, 0.115), "paving", appear=3),
    ]
    nodes = [Node("gate", "入口", 0.045, 0.20, "gate", axis="right")]
    links = [
        # 从高处进门先看到两级台地与中间那条石溪
        Link("sight", ((0.075, 0.205), (0.47, 0.435)), "sight", True, appear=0),
        # 沿等高线走到整石，跨溪一次，再下到低台地的茶座
        Link("path_up", ((0.05, 0.205), (0.36, 0.245), (0.567, 0.36)), "path",
             False, appear=2),
        Link("path_low", ((0.585, 0.52), (0.42, 0.615), (0.245, 0.695)), "path",
             False, appear=2),
    ]
    trees = [Tree(0.11, 0.12, 0.050, 1, "乔木"), Tree(0.30, 0.10, 0.044, 1),
             Tree(0.63, 0.13, 0.046, 1), Tree(0.72, 0.30, 0.040, 1),
             Tree(0.16, 0.85, 0.044, 1), Tree(0.30, 0.90, 0.048, 1),
             Tree(0.60, 0.84, 0.042, 1)]
    return Frame("site", "", regs, nodes, links, trees=trees,
                 keep=("gate", "creek", "seat"))


def _grove_frame(concept: Dict[str, Any]) -> Frame:
    """林下茶席：边界一圈乔木，中间留空地做茶席；浅渠走边、不切中心。"""
    regs = [
        Region("house", "建筑", (0.78, 0.20, 0.19, 0.60), "building"),
        Region("lawn", "草坪", (0.26, 0.28, 0.42, 0.44), "green"),
        Region("seat", "茶席", (0.33, 0.44, 0.13, 0.12), "paving", appear=2),
        Region("channel", "浅渠", (0.10, 0.885, 0.60, 0.05), "water",
               shape="rect", appear=3),
    ]
    nodes = [Node("gate", "入口", 0.08, 0.72, "gate")]
    links = [
        Link("path", ((0.085, 0.72), (0.20, 0.72), (0.26, 0.52), (0.33, 0.50)),
             "path", True, appear=2),
        Link("steps", ((0.46, 0.56), (0.62, 0.72), (0.82, 0.72)), "path", False,
             appear=2),
    ]
    trees = [Tree(0.10, 0.10, 0.055, 1, "乔木"), Tree(0.22, 0.09, 0.050, 1),
             Tree(0.36, 0.10, 0.046, 1), Tree(0.52, 0.09, 0.050, 1),
             Tree(0.66, 0.11, 0.044, 1), Tree(0.76, 0.14, 0.040, 1),
             Tree(0.09, 0.26, 0.048, 1), Tree(0.09, 0.44, 0.046, 1),
             Tree(0.10, 0.60, 0.048, 1), Tree(0.40, 0.80, 0.046, 1),
             Tree(0.62, 0.82, 0.042, 1)]
    return Frame("site", "", regs, nodes, links, trees=trees,
                 keep=("gate", "seat"))


def landscape_frames(concept: Dict[str, Any]) -> List[Frame]:
    proto = concept.get("spatial_prototype") or {}
    kind = str(proto.get("massing_kind") or "")
    if kind == "terraces":
        return [_terrace_frame(concept)]
    if kind == "grove":
        return [_grove_frame(concept)]
    if kind == "pond":
        return [_pond_frame(concept)]
    if not _has_water(concept):
        # 没声明水面也没有原型：按台地处理，绝不凭空加水
        return [_terrace_frame(concept)]
    return [_pond_frame(concept)]


def frames(concept: Dict[str, Any], discipline: str = "architecture", *,
           sector: str = "") -> List[Frame]:
    """这套概念该画几幅、画什么。建筑不走这一层（仍用等距体块）。"""
    if discipline == "interior":
        return interior_frames(concept, sector=sector)
    if discipline == "landscape":
        return landscape_frames(concept)
    return []


# --------------------------------------------------------------------------
# 画
# --------------------------------------------------------------------------
def _tw(text: str, size: float) -> float:
    """粗略字宽：汉字 1 em，西文/数字 0.55 em。只用于摆放，不追求排版精度。"""
    return sum(size * (1.0 if ord(ch) > 0x2E80 else 0.55) for ch in str(text))


def _trect(x: float, y: float, tw: float, th: float, anchor: str) -> Box:
    if anchor == "middle":
        return (x - tw / 2, y - th * 0.8, tw, th)
    if anchor == "end":
        return (x - tw, y - th * 0.8, tw, th)
    return (x, y - th * 0.8, tw, th)


def _hit(a: Box, b: Box, pad: float = 3.0) -> bool:
    return not (a[0] + a[2] + pad <= b[0] or b[0] + b[2] + pad <= a[0]
                or a[1] + a[3] + pad <= b[1] or b[1] + b[3] + pad <= a[1])


def _inside(inner: Box, outer: Box, pad: float = 4.0) -> bool:
    return (inner[0] >= outer[0] + pad and inner[1] >= outer[1] + pad
            and inner[0] + inner[2] <= outer[0] + outer[2] - pad
            and inner[1] + inner[3] <= outer[1] + outer[3] - pad)


def _place(own: Box, text: str, *, size: float, taken: List[Box],
           avoid: Sequence[Box], area: Box, prefer_in: bool = True,
           out_order: Sequence[str] = ("r", "l", "t", "b"),
           center_first: bool = False) -> Optional[Dict[str, Any]]:
    """给一段标签找位置：内部优先，放不下引到外侧；返回位置与引线。"""
    tw = _tw(text, size)
    th = size * 1.15
    bx, by, bw, bh = own
    cands: List[Tuple[str, float, float, str]] = []
    if prefer_in:
        # 基线 = 顶部 + 一行高 + 4；rect 向上取 0.8 行高，正好落进区域内部
        mid = ("in", bx + bw / 2, by + bh * 0.5 + size * 0.35, "middle")
        top = ("in", bx + 8, by + size * 1.05 + 4, "start")
        left = ("in", bx + 8, by + bh * 0.5 + size * 0.35, "start")
        cands.extend([mid, top, left] if center_first else [top, left, mid])
    side = {"r": (bx + bw + 9, by + bh * 0.5 + size * 0.35, "start"),
            "l": (bx - 9, by + bh * 0.5 + size * 0.35, "end"),
            "t": (bx + bw / 2, by - 6, "middle"),
            "b": (bx + bw / 2, by + bh + size + 4, "middle")}
    cands += [("out", *side[k]) for k in out_order if k in side]
    for strict in (True, False):
        for mode, x, y, anchor in cands:
            rect = _trect(x, y, tw, th, anchor)
            if mode == "in" and not _inside(rect, own, pad=3):
                continue
            if not _inside(rect, area, pad=-2.0):      # 允许贴边外一点点，不许飞出去
                continue
            if any(_hit(rect, t, 3.0) for t in taken):
                continue
            if strict and any(_hit(rect, a, 1.5) for a in avoid):
                continue
            leader = () if mode == "in" else _leader(rect, own)
            return {"x": x, "y": y, "anchor": anchor, "rect": rect,
                    "leader": leader, "mode": mode}
    return None


def _leader(lab: Box, own: Box) -> Tuple[Pt, Pt]:
    """引线：从标签最近的一条边，连到图形最近的一条边。"""
    lx, ly = lab[0] + lab[2] / 2, lab[1] + lab[3] / 2
    ox = min(max(lx, own[0] + 2), own[0] + own[2] - 2)
    oy = min(max(ly, own[1] + 2), own[1] + own[3] - 2)
    if lx > own[0] + own[2]:
        return ((lab[0], ly), (own[0] + own[2], oy))
    if lx < own[0]:
        return ((lab[0] + lab[2], ly), (own[0], oy))
    if ly < own[1]:
        return ((lx, lab[1] + lab[3]), (ox, own[1]))
    return ((lx, lab[1]), (ox, own[1] + own[3]))


def draw(s: Any, frame: Frame, area: Box, pal: Dict[str, str], *,
         step: Optional[int] = None, label_size: float = 10.5,
         detail: bool = True) -> List[Dict[str, Any]]:
    """把一幅图画进 area。step=None 画全部；给了 step 只画到这一步。

    两种用法共用同一段代码，所以位置不可能不一致——这正是这一层存在的理由。
    """
    x0, y0, w, h = area

    def P(nx: float, ny: float) -> Pt:
        return (x0 + nx * w, y0 + ny * h)

    def R(b: Box) -> Box:
        return (x0 + b[0] * w, y0 + b[1] * h, b[2] * w, b[3] * h)

    marks: Dict[str, str] = {}

    def arrow_of(color: str) -> str:
        """给某种颜色注册一个固定尺寸的箭头。默认 marker 会随线宽放大。"""
        name = "arw%d" % len(marks)
        marks[name] = color
        s.defs.append(
            f'<marker id="{name}" viewBox="0 0 10 10" refX="8.5" refY="5" '
            f'markerWidth="9" markerHeight="9" markerUnits="userSpaceOnUse" '
            f'orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" '
            f'fill="{color}"/></marker>')
        return f"url(#{name})"

    def run(pts: Sequence[Pt], *, color: str, sw: float, dash: str = "",
            arrow: bool = False) -> None:
        path = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
        d = f' stroke-dasharray="{dash}"' if dash else ""
        m = f' marker-end="{arrow_of(color)}"' if arrow else ""
        s.body.append(
            f'<polyline points="{path}" fill="none" stroke="{color}" '
            f'stroke-width="{sw:.2f}" stroke-linejoin="round" '
            f'stroke-linecap="round"{d}{m}/>')

    def on(i: int) -> bool:
        return step is None or i <= step

    def now(i: int) -> bool:
        return step is not None and i == step

    # 1) 底板
    s.rect(x0, y0, w, h, fill=pal["ground"], stroke=pal["line"], sw=1.0, rx=0)

    # 2) 区域：背景在前
    for r in sorted(frame.regions, key=lambda r: ORDER.get(r.kind, 5)):
        if not on(r.appear):
            continue
        bx, by, bw, bh = R(r.box)
        if r.shape == "ellipse":
            s.ellipse(bx + bw / 2, by + bh / 2, bw / 2, bh / 2, fill=pal["water"],
                      stroke=pal["waterline"], sw=1.0)
            continue
        if r.kind == "creek":
            # 干河床：砾石带 + 两道浅岸线。颜色比台地深一档，否则会被读成"空地"。
            mid = [(bx + bw * (i / 16), by + bh * (0.5 + 0.26 * math.sin(i / 16 * 7.1)))
                   for i in range(17)]
            run(mid, color="#CFC5AB", sw=bh * 1.02)
            run(mid, color="#B5A98B", sw=1.0, dash="3 5")
            for i in range(22):
                t = (i + 0.5) / 22
                gx = bx + bw * t
                gy = by + bh * (0.5 + 0.26 * math.sin(t * 7.1)) + bh * (
                    0.20 if i % 3 else -0.18)
                s.circle(gx, gy, max(1.3, bh * 0.085), fill="#AFA180",
                         stroke="#9E9071", sw=0.6)
            continue
        fill = pal.get({"mass2": "mass2", "public": "mass2", "core": "core",
                        "service": "service", "circulation": "paper",
                        "private": "mass", "building": "building",
                        "terrace": "terrace", "paving": "paving",
                        "counter": "paper", "green": "green",
                        "water": "water"}.get(r.kind, "mass"), pal["mass"])
        stroke = pal["line"] if r.kind == "circulation" else pal["ink"]
        if r.kind == "counter":
            # 服务台：白底 + 强调边，一眼看出是"一件家具"不是"一个房间"
            s.rect(bx, by, bw, bh, fill=pal["paper"], stroke=pal["accent"], sw=1.4,
                   rx=1.0)
            continue
        sw = 1.0
        if now(r.appear) or now(r.emphasis):
            stroke, sw = pal["accent"], 1.9
            s.rect(bx, by, bw, bh, fill=pal["accent"], stroke="none", sw=0,
                   rx=2.0, opacity=0.10)
        s.rect(bx, by, bw, bh, fill=fill, stroke=stroke, sw=sw, rx=2.0)
        for i in range(1, max(0, r.ticks) + 1):
            tx = bx + bw * i / (r.ticks + 1)
            s.line(tx, by + 1.5, tx, by + bh - 1.5, stroke=pal["line"], sw=0.8)

    # 3) 环路
    for g in frame.rings:
        if not on(g.appear):
            continue
        cx, cy = P(g.cx, g.cy)
        rx, ry = g.rx * w, g.ry * h
        s.ellipse(cx, cy, rx, ry, fill="none", stroke=pal["path"], sw=9.0)
        s.ellipse(cx, cy, rx, ry, fill="none", stroke=pal["pathline"], sw=0.9,
                  opacity=1.0)

    # 4) 联系
    for lk in frame.links:
        if not on(lk.appear):
            continue
        pts = [P(*p) for p in lk.pts]
        hot = now(lk.appear) or now(lk.emphasis)
        if lk.kind == "window":
            s.line(pts[0][0], pts[0][1], pts[1][0], pts[1][1],
                   stroke=pal["accent"], sw=2.5)
        elif lk.kind == "service":
            run(pts, color="#8C7B5F", sw=1.6 if not hot else 2.2,
                dash="5 4", arrow=lk.arrow)
        elif lk.kind == "sight":
            run(pts, color=pal["accent"], sw=1.0, dash="6 5", arrow=lk.arrow)
        elif lk.kind in ("path", "stone", "step"):
            # 园路不给箭头：一条路本身没有方向，箭头会被误读成动线
            run(pts, color=pal["path"], sw=9.0 if lk.kind == "path" else 4.0)
        else:
            run(pts, color=pal["accent"], sw=2.0 if hot else 1.7,
                arrow=lk.arrow)

    # 5) 种植
    for t in frame.trees:
        if not on(t.appear):
            continue
        cx, cy = P(t.x, t.y)
        s.circle(cx, cy, min(w, h) * t.r * 1.9, fill=pal["green"],
                 stroke=pal["greenline"], sw=0.9)

    # 6) 核的轮廓：圈出"哪几块合在一起才是核"
    for o in frame.outlines:
        if not on(o.appear):
            continue
        pts = [P(*p) for p in o.pts]
        if now(o.appear):
            s.polygon(pts, fill=pal["accent"], stroke="none", sw=0, opacity=0.07)
        s.polygon(pts, fill="none", stroke=pal["accent"], sw=1.4, dash="7 5")

    # 7) 点状要素
    for nd in frame.nodes:
        if not on(nd.appear):
            continue
        cx, cy = P(nd.x, nd.y)
        if nd.kind == "gate":
            if nd.axis == "right":
                run(((cx - w * 0.028, cy), (cx + w * 0.032, cy)),
                    color=pal["accent"], sw=2.0, arrow=True)
            else:
                run(((cx, cy + h * 0.04), (cx, cy - h * 0.055)),
                    color=pal["accent"], sw=2.0, arrow=True)
        elif nd.kind == "seat":
            s.rect(cx - 0.045 * w, cy - 0.038 * h, 0.09 * w, 0.076 * h,
                   fill=pal["paving"], stroke=pal["accent"], sw=1.2, rx=2.0)
            s.circle(cx, cy - 0.004 * h, 0.016 * min(w, h) * 2, fill="none",
                     stroke=pal["accent"], sw=1.0)
        elif nd.kind == "lift":
            bw, bh = 0.030 * w, 0.030 * h
            s.rect(cx - bw / 2, cy - bh / 2, bw, bh, fill="none",
                   stroke=pal["muted"], sw=0.9, rx=1.0)
            s.line(cx, cy + bh * 0.28, cx, cy - bh * 0.28, stroke=pal["muted"],
                   sw=1.1, arrow=True)

    # 8) 标注
    if label_size <= 0:
        return []
    placed: List[Box] = []
    out: List[Dict[str, Any]] = []
    rects = [R(r.box) for r in frame.regions]
    # 水平流线的窄带也参与避让：否则"走廊"标签一定被客流箭头穿过去
    bands: List[Box] = []
    for lk in frame.links:
        if lk.kind not in ("flow", "service") or len(lk.pts) < 2:
            continue
        ys = [p[1] for p in lk.pts]
        if max(ys) - min(ys) > 0.02:
            continue
        xs = [p[0] for p in lk.pts]
        cy = sum(ys) / len(ys)
        bands.append((x0 + min(xs) * w, y0 + cy * h - 7, (max(xs) - min(xs)) * w, 14))

    def put(text: str, own: Box, *, size: float, color: str, avoid: List[Box],
            prefer_in: bool = True, weight: str = "400",
            center_first: bool = False,
            out_order: Sequence[str] = ("r", "l", "t", "b")
            ) -> Optional[Dict[str, Any]]:
        spot = _place(own, text, size=size, taken=placed, avoid=avoid,
                      area=area, prefer_in=prefer_in, center_first=center_first,
                      out_order=out_order)
        if spot is None:
            return None
        placed.append(spot["rect"])
        if spot["leader"]:
            (lx, ly), (ox, oy) = spot["leader"]
            s.line(lx, ly, ox, oy, stroke=pal["line"], sw=0.9)
            s.circle(ox, oy, 1.8, fill=pal["line"], stroke="none")
        s.text(spot["x"], spot["y"], text, size=size, color=color,
               anchor=spot["anchor"], weight=weight)
        out.append({"text": text, "rect": spot["rect"], "mode": spot["mode"]})
        return spot

    for r in frame.regions:
        if not str(r.label or "").strip():
            continue
        # 四步图里只标"这一步新增/点亮的"，其余留给页面正文，避免糊成一团。
        # keep 只保它本来就有的东西（入口、水面），不能把第三步才出现的茶座
        # 提前标到空地上——那正是"标签指错地方"。
        if step is not None and not (now(r.appear) or now(r.emphasis)
                                     or (r.key in frame.keep and r.appear == 0)):
            continue
        if step is not None and r.key not in frame.keep and len(out) >= 3:
            continue
        own = R(r.box)
        avoid = [b for b, rr in zip(rects, frame.regions) if rr.key != r.key] + bands
        spot = put(r.label, own, size=label_size, color=pal["ink"], avoid=avoid,
                   weight="500", center_first=(r.shape == "ellipse"))
        if spot is None or not r.sub or not detail:
            continue
        # 副行紧贴主行：主行在外面（引线）时没有位置，就不写副行
        if spot["mode"] != "in":
            continue
        sub_size = label_size * 0.78
        sub_rect = _trect(spot["x"], spot["y"] + label_size * 1.15, _tw(r.sub, sub_size),
                          sub_size * 1.15, spot["anchor"])
        if not _inside(sub_rect, own, pad=2):
            continue
        if any(_hit(sub_rect, t, 2) for t in placed) or any(_hit(sub_rect, a, 1)
                                                            for a in avoid):
            continue
        placed.append(sub_rect)
        s.text(spot["x"], spot["y"] + label_size * 1.15, r.sub, size=sub_size,
               color=pal["muted"], anchor=spot["anchor"])

    for tr in frame.trees:
        if not tr.label or not on(tr.appear):
            continue
        if step is not None and not now(tr.appear):
            continue
        cx, cy = P(tr.x, tr.y)
        rad = min(w, h) * tr.r * 1.9
        put(tr.label, (cx - rad, cy - rad, rad * 2, rad * 2), size=label_size,
            color=pal["muted"], avoid=rects + bands, prefer_in=False,
            out_order=("r", "l", "t", "b"))

    for nd in frame.nodes:
        if not str(nd.label or "").strip():
            continue
        if step is not None and not (now(nd.appear)
                                     or (nd.key in frame.keep and nd.appear == 0)):
            continue
        cx, cy = P(nd.x, nd.y)
        own = (cx - 0.02 * w, cy - 0.02 * h, 0.04 * w, 0.04 * h)
        # 入口标签允许落在框外下方：门口本来就在图外
        spot = _place(own, nd.label, size=label_size, taken=placed,
                      avoid=rects + bands,
                      area=(area[0], area[1], area[2], area[3] + 30.0),
                      prefer_in=False,
                      out_order=("b", "r", "l", "t") if nd.kind == "gate"
                      else ("r", "l", "b", "t"))
        if spot is not None:
            placed.append(spot["rect"])
            if spot["leader"]:
                (lx, ly), (ox, oy) = spot["leader"]
                s.line(lx, ly, ox, oy, stroke=pal["line"], sw=0.9)
                s.circle(ox, oy, 1.8, fill=pal["line"], stroke="none")
            s.text(spot["x"], spot["y"], nd.label, size=label_size,
                   color=pal["accent"], anchor=spot["anchor"], weight="500")
            out.append({"text": nd.label, "rect": spot["rect"],
                        "mode": spot["mode"]})
    return out


__all__ = ["Box", "Frame", "Link", "Node", "Outline", "PAL", "Region", "Ring",
           "Tree", "draw", "frames", "interior_frames", "landscape_frames"]
