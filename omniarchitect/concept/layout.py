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

没有声明平面组织方式时
----------------------
不套教学/医疗那套分段。`plan_layout` 只有行业方向（教育、医疗、工业、酒店、
景观）才填，普通家装与办公本来就没有：拿"教学／专用教室"去标一间住宅，
是最容易被业主一眼看穿的错误。这时按委托类型给**中性分区**
（公共区／通道／私密区、工位区／协作区…），并在图注里写明
"这是功能关系示意，不是排房图"——宁可不画房间，也不编客户没提过的房间。

标注
----
标签位置由图形几何算出来（内部放得下就放内部，放不下引到外侧），并做基本避让：
不出界、不与别的标签重叠、不压在别的区域上。引入引线时只连到最近的边，
不穿过无关区域。图上只留 2–6 个字的短标签，长句交给页面正文。

**重要标签不能因为"放不下"就消失。** 入口、公共核、大堂、后场、水景、茶座
这些是读图的锚点，丢了图就白画了。所以：

1. `Frame.keep` 里的标签**先排**，普通区域其次，乔木等装饰性标签最后；
2. 排不下时依次放宽：避开别的区域 → 允许压过区域改用引线 → 字号降到 0.86 倍
   （再小就不排，宁可留白也不用 7 px 的字）；三层都失败才算真的放不下；
3. 仍然放不下的，写进 `draw(..., report=...)` 的 `missing`，由图注如实标出
   "未放置标注：…"。**不许假装图纸完整。**

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
#: 铺装排在草坡/台地/旱溪**之后**：茶席落在草坪里、整石落在旱溪上，
#: 排在前面的会被后画的草地与砾石盖掉——图上就只剩一个标签，看不见东西。
ORDER = {"terrace": 1, "creek": 2, "water": 3, "building": 4,
         "mass": 5, "private": 5, "green": 5,
         "paving": 6, "stone": 6, "mass2": 6, "public": 6, "service": 7, "core": 8,
         "counter": 9, "circulation": 9}


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
    #: 这幅图能说明什么、不能说明什么。只在中性回退或数据自相矛盾时写，
    #: 正常图纸留空——图注不该每张都是一样的免责声明。
    note: str = ""


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
    # 非酒店的公共核：只承认"公共/辅助/竖向交通"这三件事。
    # 不写餐厅、宴会、前台——这些是酒店的功能，别的类型没有提就不该出现。
    "generic": {
        "boh": "后场", "boh_sub": "竖向通道",
        "dining": "公共区", "dining_sub": "",
        "meeting": "辅助区", "meeting_sub": "",
        "lobby": "公共核", "lobby_sub": "",
        "recep": "服务台", "lift": "竖向交通", "gate": "入口",
    },
}

#: 判断"这是不是酒店"。`sector` 认不出来时退回识别概念自己的用词——
#: 真实酒店项目有时没有行业分类码，只靠 sector 会把客房层吞掉。
HOTEL_WORDS = ("酒店", "客房", "旅宿", "度假村", "民宿", "旅馆", "宾馆", "hospitality")


def _is_hotel(concept: Dict[str, Any], sector: str = "") -> bool:
    if sector == "hospitality":
        return True
    proto = concept.get("spatial_prototype") or {}
    text = " ".join(str(x or "") for x in (
        concept.get("concept_name"), concept.get("concept_statement"),
        proto.get("name"), proto.get("zoning"), proto.get("circulation"),
        proto.get("statement")))
    return any(w in text for w in HOTEL_WORDS)


def _public_floor(*, hotel: bool = True) -> Frame:
    """裙房公共层：大堂+餐厅+会议形成一个核，后场是一条独立的竖向通道。

    这是 `plan_layout=public_core` 的图。客流在右半（落客→大堂→前台→客梯厅），
    服务流在左半（后场→服务梯），两条线不交叉——这正是这个概念要证明的事。
    """
    L = PUBLIC_LABELS["hospitality" if hotel else "generic"]
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

#: 没有 `plan_layout` 时按委托类型给的**中性分区**：(北侧, 通道, 南侧, 端部核)。
#:
#: 只写"公共/私密/辅助"这类分区关系，不写具体房间。住宅里没有"教学"，
#: 办公里没有"客房"——客户没提过的功能，图上就不许出现。
#: 不追求覆盖全部子类：分不出类型的落 `DEFAULT_BANDS`，并如实说明。
NEUTRAL_BANDS: Dict[str, Tuple[str, str, str, str]] = {
    "housing": ("公共区", "通道", "私密区", "门厅"),
    "office": ("工位区", "通道", "协作区", "门厅"),
    "retail": ("陈列区", "通道", "后场", "入口"),
    "food": ("餐区", "通道", "后厨", "门厅"),
    "culture": ("展陈区", "通道", "辅助区", "门厅"),
    "leisure": ("活动区", "通道", "辅助区", "门厅"),
    # 只认了"这是酒店"、没声明公共核/客房翼的平面组织方式时：
    # 只能说清客房区、走廊、公共区三件事，**不能**把它排成客房标准层。
    "hospitality": ("客房区", "走廊", "公共区", "电梯厅"),
}

DEFAULT_BANDS: Tuple[str, str, str, str] = ("使用区", "通道", "辅助区", "门厅")

#: 中性回退时写进图注的话。不说清楚，客户会把它当成排房图。
NEUTRAL_NOTE = "概念未声明平面组织方式：本图为功能关系示意，不是排房图"


def _bands_floor(kind: str, sector: str, *, note: str = "",
                 bands: Optional[Tuple[str, str, str, str]] = None) -> List[Frame]:
    """其他工装：三段式楼层（北侧／通道／南侧＋端部核）。标签来自类型，不套客房。"""
    top, mid, bot, core = bands or BANDS.get(kind, DEFAULT_BANDS)
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
    return [Frame("floor", "", regs, nodes=[], links=links, keep=("core",),
                  note=note)]


def _neutral_floor(concept: Dict[str, Any], sector: str, *,
                   note: str = NEUTRAL_NOTE) -> List[Frame]:
    """没有平面组织方式时的中性分段：按委托类型给分区关系，不排房间。

    这里**不拿概念里的 `experience_sequence` 当标签**：那串字是给人读的
    （"右手是接待台""不是房间布置"），抽出来当图注只会出洋相。图上出现的每个词
    都得是能站住的房间/分区名，所以只从类型表里取。

    三个方向如果都画同一张图，客户会问"这不都一样吗"。所以按概念已经声明的
    空间家族（`family`）换**组织形状**：线性走三段带、组团走四点块、环形走中心核。
    换的是排布方式，不是配色——这本来就是"组织方式不同"的意思。
    """
    bands = NEUTRAL_BANDS.get(sector, DEFAULT_BANDS)
    fam = str((concept.get("spatial_prototype") or {}).get("family") or "linear")
    if fam in ("cluster", "grid"):
        return _cluster_floor(bands, note)
    if fam in ("radial", "hall"):
        return _radial_floor(bands, note)
    return _bands_floor("", sector, note=note, bands=bands)


def _cluster_floor(bands: Tuple[str, str, str, str],
                   note: str) -> List[Frame]:
    """组团式：两个使用空间成组 + 一条通道 + 端部核。"""
    top, mid, bot, core = bands
    regs = [
        Region("left", top, (0.03, 0.06, 0.38, 0.34), "mass"),
        Region("right", "", (0.47, 0.06, 0.36, 0.34), "mass"),
        Region("left2", "", (0.03, 0.50, 0.38, 0.34), "mass"),
        Region("right2", bot, (0.47, 0.50, 0.36, 0.34), "mass2"),
        Region("mid", mid, (0.03, 0.405, 0.80, 0.09), "circulation"),
        Region("core", core, (0.85, 0.06, 0.12, 0.78), "core"),
    ]
    links = [
        Link("flow", ((0.91, 0.92), (0.91, 0.45), (0.42, 0.45)), "flow", True,
             appear=1),
        Link("win", ((0.15, 0.06), (0.15, 0.012)), "window", appear=2),
        Link("win2", ((0.62, 0.06), (0.62, 0.012)), "window", appear=2),
    ]
    return [Frame("floor", "", regs, nodes=[], links=links, keep=("core",),
                  note=note)]


def _radial_floor(bands: Tuple[str, str, str, str],
                  note: str) -> List[Frame]:
    """环形／大厅式：中心一个核，四周一圈使用空间。"""
    top, mid, bot, core = bands
    regs = [
        Region("ring", top, (0.03, 0.06, 0.80, 0.82), "mass"),
        Region("center", mid, (0.30, 0.30, 0.30, 0.34), "core", sub=core),
        Region("annex", bot, (0.85, 0.06, 0.12, 0.82), "service"),
    ]
    links = [
        Link("flow", ((0.91, 0.92), (0.91, 0.47), (0.60, 0.47)), "flow", True,
             appear=1),
        Link("win", ((0.18, 0.06), (0.18, 0.012)), "window", appear=2),
        Link("win2", ((0.50, 0.06), (0.50, 0.012)), "window", appear=2),
    ]
    return [Frame("floor", "", regs, nodes=[], links=links, keep=("center",),
                  note=note)]


# --------------------------------------------------------------------------
# 住宅室内的四种组织方式：按概念自己的 parti 画，不套类型模板
# --------------------------------------------------------------------------
#: 住宅室内策略的 `massing_kind` → 图版。名字与 `deliberation` 里对应策略的
#: parti 一致（服务脊／中心体块／明暗两段／盒中之盒），图上出现的词都是
#: 概念自己写过的，不是新编的房间。
def _spine_frame(concept: Dict[str, Any]) -> Frame:
    """一条服务脊：脊居中，脊两侧留完整开间；脊两端各留一个开口形成回游。"""
    regs = [
        Region("west", "开间", (0.04, 0.06, 0.26, 0.88), "mass"),
        Region("spine", "服务脊", (0.32, 0.16, 0.17, 0.68), "service",
               sub="厨卫·储藏·洗衣"),
        Region("east", "", (0.51, 0.06, 0.45, 0.88), "mass"),
    ]
    nodes = [Node("gate", "入户", 0.74, 0.90, "gate")]
    links = [
        # 脊两端各一个开口：绕过去才到另一侧，"走廊被脊吸收"
        Link("loop_n", ((0.10, 0.115), (0.90, 0.115)), "flow", True, appear=1),
        Link("loop_s", ((0.10, 0.885), (0.90, 0.885)), "flow", True, appear=1),
    ]
    return Frame("floor", "", regs, nodes, links, keep=("gate", "spine"))


def _loop_frame(concept: Dict[str, Any]) -> Frame:
    """中心体块回游：中间一个体块，人绕着它走，公共段与私密段在环上。"""
    regs = [
        Region("plate", "开间", (0.04, 0.06, 0.92, 0.88), "mass"),
        Region("core", "中心体块", (0.36, 0.31, 0.28, 0.38), "core",
               sub="衣帽·家政"),
    ]
    nodes = [Node("gate", "入户", 0.50, 0.90, "gate"),
             Node("looplab", "回游", 0.50, 0.10, "pad")]
    rings = [Ring(0.50, 0.50, 0.36, 0.38, appear=1)]
    return Frame("floor", "", regs, nodes, keep=("gate", "core"), rings=rings)


def _dark_frame(concept: Dict[str, Any]) -> Frame:
    """明暗两段：靠窗一段亮、内侧一段压暗，交界是一个 600 厚的门洞。"""
    regs = [
        Region("light", "亮段", (0.04, 0.06, 0.92, 0.40), "mass",
               sub="客厅·卧室"),
        Region("dark", "暗段", (0.04, 0.50, 0.92, 0.44), "mass2",
               sub="入户·储物·餐厨"),
        Region("door", "厚门洞", (0.42, 0.452, 0.16, 0.048), "counter"),
    ]
    nodes = [Node("gate", "入户", 0.16, 0.90, "gate")]
    links = [
        Link("win", ((0.22, 0.06), (0.22, 0.012)), "window", appear=2),
        Link("win2", ((0.50, 0.06), (0.50, 0.012)), "window", appear=2),
        Link("win3", ((0.78, 0.06), (0.78, 0.012)), "window", appear=2),
        # 站在暗段透过门洞看亮段：这条视线是这套方案的全部戏剧性
        Link("sight", ((0.50, 0.62), (0.50, 0.30)), "sight", True, appear=3),
    ]
    return Frame("floor", "", regs, nodes, links, keep=("gate", "door"))


def _box_frame(concept: Dict[str, Any]) -> Frame:
    """盒中之盒：盒子贴外墙，其余三面是盒墙；盒外仍是完整大空间。"""
    regs = [
        Region("outer", "盒外", (0.04, 0.06, 0.92, 0.88), "mass"),
        Region("box", "盒子", (0.30, 0.50, 0.40, 0.44), "core", sub="卧·卫·衣"),
    ]
    nodes = [Node("gate", "入户", 0.10, 0.90, "gate")]
    links = [
        Link("win", ((0.40, 0.94), (0.40, 0.988)), "window", appear=2),
        Link("win2", ((0.60, 0.94), (0.60, 0.988)), "window", appear=2),
        # 盒顶留缝：光从盒子上方擦进来
        Link("gap", ((0.30, 0.50), (0.70, 0.50)), "sight", False, appear=3),
    ]
    return Frame("floor", "", regs, nodes, links, keep=("gate", "box"))


#: 住宅室内策略自己声明的 `massing_kind`。**不是**新分类：这些值本来就在
#: `deliberation` 里，只是过去落到"按类型给的分段"，图与 parti 对不上。
INTERIOR_LAYOUTS = {"spine": _spine_frame, "loop": _loop_frame,
                    "darklight": _dark_frame, "inner_box": _box_frame}


def interior_frames(concept: Dict[str, Any], *, sector: str = "") -> List[Frame]:
    proto = concept.get("spatial_prototype") or {}
    kind = str(proto.get("plan_layout") or proto.get("plan_strategy") or "")
    house = str(proto.get("massing_kind") or "")
    hotel = _is_hotel(concept, sector)
    if not str(proto.get("plan_layout") or "") and house in INTERIOR_LAYOUTS:
        # 住宅室内策略只声明了组织方式（脊／环／明暗／盒子），没有行业平面码，
        # 按它自己的 parti 画；不套教育、医疗或酒店的分段。
        return [INTERIOR_LAYOUTS[house](concept)]
    if "public_core" in kind:
        if hotel:
            return [_public_floor(hotel=True), _guest_floor()]
        # 非酒店的公共核：只画公共层。**不许**顺手带出客房标准层——
        # 那是酒店的功能，出现在文化馆或办公楼里就是编的。
        fr = _public_floor(hotel=False)
        fr.note = "未识别为酒店项目：只画公共层，不生成客房标准层"
        return [fr]
    if "guest_wing" in kind:
        if hotel:
            return [_guest_floor()]
        return _neutral_floor(concept, sector)
    if kind in BANDS:
        return _bands_floor(kind, sector)
    # 没有声明平面组织方式的室内：按业态给中性分段，绝不套教学或客房
    return _neutral_floor(concept, sector if sector in NEUTRAL_BANDS
                          else ("hospitality" if hotel else sector))



# --------------------------------------------------------------------------
# 景观：按 massing_kind 出图。没有水就绝不画水池
# --------------------------------------------------------------------------
#: 有的方案只写了 `plan_layout`（行业方向）没写 `massing_kind`，两者说的是同一件事。
LAYOUT_TO_KIND = {"water_loop": "pond", "terrace": "terraces", "grove_edge": "grove"}

#: 明确否定有水。比原型名更硬：这是业主能读到的承诺。
#: 只收"否定句"，不收"旱溪"这类做法词——水池边上也可以有一条旱溪，
#: 光看见"旱溪"就翻案，会把静水方案误画成无水方案。
DENY_WATER = ("不做池", "不做水", "不设水", "没有水面", "无水面", "没有水景",
              "不做水景", "不要水景", "取消常水面", "取消水面", "取消水池", "无水景")

#: 暗示"以旱做法为主"的词。没有原型时用来判断，不能用来推翻已声明的原型。
DRY_HINT = ("旱溪", "少水", "无水")

#: 明确要有常年水面。
CLAIM_WATER = ("静水", "水面", "水池", "水景", "水岸", "镜面水")


def _water_text(concept: Dict[str, Any]) -> str:
    proto = concept.get("spatial_prototype") or {}
    d = concept.get("deliberation") or {}
    parts = [concept.get("concept_name"), concept.get("concept_statement")]
    for src in (proto, d):
        parts.extend(src.get(k) for k in ("zoning", "water", "spatial_logic",
                                          "parti", "massing", "statement"))
    return " ".join(str(x or "") for x in parts)


def _denies_water(concept: Dict[str, Any]) -> bool:
    return any(w in _water_text(concept) for w in DENY_WATER)


def _dry_hint(concept: Dict[str, Any]) -> bool:
    return any(w in _water_text(concept) for w in DRY_HINT)


def _claims_water(concept: Dict[str, Any]) -> bool:
    return any(w in _water_text(concept) for w in CLAIM_WATER)


def landscape_kind(concept: Dict[str, Any]) -> str:
    """这套概念到底是哪一种场地结构：pond / terraces / grove。

    以声明为准，**但文字能否定图形**：原型写着"静水"、主张却写"不做池子"时，
    以主张为准画无水方案——图上画一个池子，等于把客户明确否掉的东西又画回来。
    这种自相矛盾会进 `consistency()`，由图片注如实标出，等数据修正。
    """
    proto = concept.get("spatial_prototype") or {}
    kind = str(proto.get("massing_kind") or "")
    if not kind:
        kind = LAYOUT_TO_KIND.get(str(proto.get("plan_layout") or ""), "")
    if kind == "pond" and _denies_water(concept):
        return "terraces"
    if not kind:
        if _denies_water(concept) or _dry_hint(concept):
            return "terraces"
        return "pond" if _claims_water(concept) else "terraces"
    return kind


def consistency(concept: Dict[str, Any]) -> List[str]:
    """概念主张、`massing_kind` 与图版之间的矛盾。空列表 = 一致。

    只在真的矛盾时返回：这是给图和页面加一句说明用的，不是新的校核流程。
    """
    out: List[str] = []
    proto = concept.get("spatial_prototype") or {}
    declared = str(proto.get("massing_kind") or "")
    resolved = landscape_kind(concept)
    if declared == "pond" and resolved != "pond":
        out.append("主张写的是不做常水面，原型却标为静水：图按无水方案绘制，"
                   "`massing_kind` 需修正")
    elif declared in ("terraces", "grove") and _claims_water(concept) \
            and not _denies_water(concept):
        out.append("主张提到水面，原型却是无水做法：图按原型绘制，"
                   "水景需求需在 S2 重新确认")
    return out


def _has_water(concept: Dict[str, Any]) -> bool:
    """这套概念里到底有没有"常年水面"。

    `DLB-LAN-DRY` 的整条主张就是"不做池子"，画一个中心水池等于把备选方案
    画成了主推方案。判据只看声明，不猜。
    """
    return landscape_kind(concept) == "pond"


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
        # 茶座在远岸、环路**外侧**的岸上，不是坐在通道中间：
        # 摆在 (0.27,0.33) 时它正好压在环路上（环在 x=0.27 处过 y=0.330）。
        # 位置也决定视线：从这里望向房子，线正好斜穿整块水面。
        Node("seat", "茶座", 0.255, 0.255, "seat", appear=3),
    ]
    rings = [Ring(0.45, 0.50, 0.255, 0.24, appear=2)]
    links = [
        # 入口到环：垂直接到环的下缘，不断在半空
        Link("entry", ((0.46, 0.985), (0.46, 0.742)), "path", False, appear=2),
        # 茶座回望房子：这条线穿过水面才有倒影
        Link("sight_back", ((0.272, 0.272), (0.80, 0.50)), "sight", True, appear=3),
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
    """林下茶席：边界一圈乔木，中间留空地做茶席。

    这里**不画水**。这套主张是"私密靠边界种植"，从没说过要水；
    上一版在底边放了一条"浅渠"，等于替客户加了一个他没要求的水景。
    """
    regs = [
        Region("house", "建筑", (0.78, 0.20, 0.19, 0.60), "building"),
        Region("lawn", "草坪", (0.26, 0.28, 0.42, 0.44), "green"),
        Region("seat", "茶席", (0.33, 0.44, 0.13, 0.12), "paving", appear=2,
               emphasis=3),
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
    kind = landscape_kind(concept)
    conflicts = consistency(concept)
    note = "；".join(conflicts)
    build = {"pond": _pond_frame, "grove": _grove_frame}.get(
        kind, _terrace_frame)
    fr = build(concept)
    fr.note = note
    return [fr]


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


def _contains(outer: Box, inner: Box) -> bool:
    """inner 是否整个落在 outer 里。嵌套区域（盒子／盒外、茶席／草坪）要用。"""
    return (inner[0] >= outer[0] - 0.5 and inner[1] >= outer[1] - 0.5
            and inner[0] + inner[2] <= outer[0] + outer[2] + 0.5
            and inner[1] + inner[3] <= outer[1] + outer[3] + 0.5)


def _inside(inner: Box, outer: Box, pad: float = 4.0) -> bool:
    return (inner[0] >= outer[0] + pad and inner[1] >= outer[1] + pad
            and inner[0] + inner[2] <= outer[0] + outer[2] - pad
            and inner[1] + inner[3] <= outer[1] + outer[3] - pad)


def _place(own: Box, text: str, *, size: float, taken: List[Box],
           avoid: Sequence[Box], area: Box, prefer_in: bool = True,
           out_order: Sequence[str] = ("r", "l", "t", "b"),
           center_first: bool = False) -> Optional[Dict[str, Any]]:
    """给一段标签找位置：内部优先，放不下引到外侧；返回位置与引线。

    外侧不是只有"正右/正左"一个点：沿边给 3 个落点 × 3 个距离，
    否则一个标签被占位后它的邻居就全没地方去了。
    两轮：先守"不压别的区域"，都不行才允许压过去（有引线，读者不会认错）。
    """
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
    for k in out_order:
        for d in (9.0, 17.0, 26.0):
            for f in (0.5, 0.28, 0.72, 0.12, 0.88):
                if k in ("r", "l"):
                    x = bx + bw + d if k == "r" else bx - d
                    cands.append(("out", x, by + bh * f + size * 0.35,
                                  "start" if k == "r" else "end"))
                else:
                    y = by - 6 - (d - 9.0) if k == "t" else by + bh + size + 2 + (d - 9.0)
                    cands.append(("out", bx + bw * f, y, "middle"))
    # 按候选顺序打分，而不是"先把所有严格候选试一遍"：
    # 否则一个排在很后面的位置（比如正下方）会因为"压在树冠上但没压到别的标签"
    # 而在首选位置（右侧）只是压到树冠时就抢先落地——位置越排越差。
    fallback: Optional[Dict[str, Any]] = None
    for mode, x, y, anchor in cands:
        rect = _trect(x, y, tw, th, anchor)
        if mode == "in" and not _inside(rect, own, pad=3):
            continue
        if not _inside(rect, area, pad=-2.0):      # 允许贴边外一点点，不许飞出去
            continue
        if any(_hit(rect, t, 3.0) for t in taken):
            continue
        leader = () if mode == "in" else _leader(rect, own)
        spot = {"x": x, "y": y, "anchor": anchor, "rect": rect,
                "leader": leader, "mode": mode}
        if not any(_hit(rect, a, 1.5) for a in avoid):
            return spot
        if fallback is None:
            fallback = spot
    return fallback


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
         detail: bool = True,
         report: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """把一幅图画进 area。step=None 画全部；给了 step 只画到这一步。

    两种用法共用同一段代码，所以位置不可能不一致——这正是这一层存在的理由。

    `report` 填 `{"missing": [...], "labels": [...]}`：放不下的标签必须能被调用方
    读出来写进图注。返回的仍是**已放置**的标签（位置与 rect），老调用方不用改。
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
            # 这一步讲到的块：只换边线，不铺底色。
            # 铺一层深绿（哪怕 5%）在米色大块上，看起来像"这块被屏蔽了"，
            # 而不是"这一步讲这里"；四步图里连成一片就成了灰版。
            stroke, sw = pal["accent"], 1.9
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
    missing: List[str] = []
    rects = [R(r.box) for r in frame.regions]
    # 树冠也算障碍：标签压在树冠上不会读错位置，但看着像贴纸没贴好。
    crowns: List[Box] = []
    for tr in frame.trees:
        if not on(tr.appear):
            continue
        cx, cy = P(tr.x, tr.y)
        rad = min(w, h) * tr.r * 1.9
        crowns.append((cx - rad, cy - rad, rad * 2, rad * 2))
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
            out_order: Sequence[str] = ("r", "l", "t", "b"),
            box: Optional[Box] = None, role: str = "label",
            ) -> Optional[Dict[str, Any]]:
        """放一个标签。放不下先缩一档字，再放不下就记进 missing，交给图注说明。

        只缩一档（0.86）：再小就不是"标注"，是墨点，客户在 16:9 页面上读不到。
        """
        spot = None
        for scale in (1.0, 0.86):
            spot = _place(own, text, size=size * scale, taken=placed, avoid=avoid,
                          area=box or area, prefer_in=prefer_in,
                          center_first=center_first, out_order=out_order)
            if spot is not None:
                size = size * scale
                break
        if spot is None:
            if text not in missing:
                missing.append(text)
            return None
        placed.append(spot["rect"])
        if spot["leader"]:
            (lx, ly), (ox, oy) = spot["leader"]
            s.line(lx, ly, ox, oy, stroke=pal["line"], sw=0.9)
            s.circle(ox, oy, 1.8, fill=pal["line"], stroke="none")
        s.text(spot["x"], spot["y"], text, size=size, color=color,
               anchor=spot["anchor"], weight=weight)
        out.append({"text": text, "rect": spot["rect"], "mode": spot["mode"],
                    "size": size, "role": role})
        return spot

    # 先排锚点标签（入口、公共核、大堂、后场、水景、茶座…），普通区域其次，
    # 乔木这类装饰最后。反过来的话，最后一个排的入口最容易"没地方"被丢掉。
    jobs: List[Tuple[int, str, Any]] = []
    for r in frame.regions:
        if not str(r.label or "").strip():
            continue
        # 四步图里只标"这一步新增/点亮的"，其余留给页面正文，避免糊成一团。
        # keep 只保它本来就有的东西（入口、水面），不能把第三步才出现的茶座
        # 提前标到空地上——那正是"标签指错地方"。
        if step is not None and not (now(r.appear) or now(r.emphasis)
                                     or (r.key in frame.keep and r.appear == 0)):
            continue
        jobs.append((0 if r.key in frame.keep else 1, "region", r))
    for nd in frame.nodes:
        if not str(nd.label or "").strip():
            continue
        if step is not None and not (now(nd.appear)
                                     or (nd.key in frame.keep and nd.appear == 0)):
            continue
        jobs.append((0 if nd.key in frame.keep else 1, "node", nd))
    for tr in frame.trees:
        if not tr.label or not on(tr.appear):
            continue
        if step is not None and not now(tr.appear):
            continue
        # 小图（四步推敲的格子、缩印图版）不标乔木：那是最不重要的一条，
        # 却正好压在茶座、水景旁边，挤掉的都是要讲的东西。
        if not detail:
            continue
        jobs.append((2, "tree", tr))
    jobs.sort(key=lambda j: j[0])          # 稳定排序：同类保持声明顺序

    extra = 0                              # 四步图里已放的"非锚点"标签数
    for _, kind, obj in jobs:
        if kind == "tree":
            cx, cy = P(obj.x, obj.y)
            rad = min(w, h) * obj.r * 1.9
            put(obj.label, (cx - rad, cy - rad, rad * 2, rad * 2), size=label_size,
                color=pal["muted"], avoid=rects + bands, prefer_in=False,
                out_order=("r", "l", "t", "b"), role="tree")
            continue
        if kind == "node":
            cx, cy = P(obj.x, obj.y)
            if obj.kind == "seat":
                # 茶座这类"看图说话"的锚点，交给自动避让会反复挑到坏位置：
                # 右下方正是环路岸线与水面。这里按比例固定在方块正上方，
                # 并把占位登记进避让表，别的标签就不会挤过来。
                sx = cx
                sy = cy - 0.062 * h
                tw = _tw(obj.label, label_size)
                rect = _trect(sx, sy, tw, label_size * 1.15, "middle")
                if _inside(rect, area, pad=-2.0):
                    placed.append(rect)
                    s.text(sx, sy, obj.label, size=label_size, color=pal["accent"],
                           anchor="middle", weight="500")
                    out.append({"text": obj.label, "rect": rect, "mode": "in",
                                "size": label_size, "role": "node"})
                else:
                    missing.append(obj.label)
                continue
            # 入口的箭头从点上往下伸 0.04h：标签框也跟着长到那儿，
            # 否则"入户"会被箭杆穿过去，看着像加了下划线。
            hh = 0.06 * h if obj.kind == "gate" else 0.04 * h
            own = (cx - 0.02 * w, cy - 0.02 * h, 0.04 * w, hh)
            # 入口标签允许落到框外：左边界进门的项目，门本来就在图幅边上，
            # 挤在框内会和台地/边界线抢位置。只往左与往下放，且**左扩距离
            # 不超过框外真正存在的留白**——四步图的格子边距只有 3 px，
            # 硬扩 30 px 会把字裁掉一半，看起来像排版故障。
            left = max(0.0, min(30.0, area[0] - 3.0))
            # 点状要素的标签**允许落在房里**（入口写在自己那间屋里最自然），
            # 所以只避让流线窄带与树冠，不把区域当障碍。
            # 标签放到"门所在那条边界的外侧"：左边界进门就往左写，
            # 底边进门就往下写。放在图内会和台地/通道的分界线抢位置。
            if obj.kind == "gate":
                order = ("l", "b", "r", "t") if obj.x <= 0.12 else (
                    ("b", "l", "r", "t") if obj.y >= 0.90 else ("b", "r", "l", "t"))
            else:
                order = ("r", "l", "b", "t")
            put(obj.label, own, size=label_size, color=pal["accent"],
                avoid=bands + crowns, prefer_in=False,
                weight="500",
                out_order=order,
                box=(area[0] - left, area[1] - 6.0, area[2] + left, area[3] + 40.0),
                role="node")
            continue
        # 区域标签：四步图里**这一步新增的**最多四个，其余留给正文。
        # 计数只算非锚点标签——锚点（大堂、入口、水景）本来就该在，
        # 用它们去占配额，会让这一步真正要讲的功能一个都标不出来。
        if step is not None and obj.key not in frame.keep and extra >= 4:
            continue
        own = R(obj.box)
        # 包着自己的那块（盒外之于盒子、草坪之于茶席）不算障碍：
        # 否则"放进盒子里"的每个候选位置都判成压线，标签只能被挤到框外。
        avoid = [b for b, rr in zip(rects, frame.regions)
                 if rr.key != obj.key and not _contains(R(rr.box), own)]
        avoid += bands + crowns
        spot = put(obj.label, own, size=label_size, color=pal["ink"], avoid=avoid,
                   weight="500", center_first=(obj.shape == "ellipse"),
                   role="region")
        if obj.key not in frame.keep:
            extra += 1
        if spot is None or not obj.sub or not detail:
            continue
        # 副行紧贴主行：主行在外面（引线）时没有位置，就不写副行
        if spot["mode"] != "in":
            continue
        sub_size = label_size * 0.78
        sub_rect = _trect(spot["x"], spot["y"] + label_size * 1.15, _tw(obj.sub, sub_size),
                          sub_size * 1.15, spot["anchor"])
        if not _inside(sub_rect, own, pad=2):
            continue
        if any(_hit(sub_rect, t, 2) for t in placed) or any(_hit(sub_rect, a, 1)
                                                            for a in avoid):
            continue
        placed.append(sub_rect)
        s.text(spot["x"], spot["y"] + label_size * 1.15, obj.sub, size=sub_size,
               color=pal["muted"], anchor=spot["anchor"])

    if report is not None:
        report["missing"] = list(missing)
        report["labels"] = list(out)
    return out



__all__ = ["Box", "DEFAULT_BANDS", "Frame", "Link", "NEUTRAL_BANDS", "NEUTRAL_NOTE",
           "Node", "Outline", "PAL", "Region", "Ring", "Tree", "consistency",
           "draw", "frames", "interior_frames", "landscape_frames", "landscape_kind"]
