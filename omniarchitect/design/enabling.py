"""技术如何实现设计 —— 结构与机电是手法，不是审批口。

## 为什么需要这一层

现行逻辑里，只要概念提到「挑空」「通高」「无窗」，结构和机电就被标成
`requires_input`，然后这套方案在比较表里被当成「不能推荐」。这在专业上是错的：

* 「这个通高能不能做」和「这个通高怎么做才成立」是两个问题。设计师问的是后者。
* 一个优秀建筑师不会因为「结构资料还没到」就放弃通高，他会先给出**做法路径**：
  用钢梁、用桁架、用边梁抬、用悬挑、把柱藏进墙里——然后才去要计算书。

所以本模块只做一件事：**把设计要求翻译成可选的实现路径**，每条路径写清
它拿什么换什么（代价），以及在哪一步才必须由持证专业签字。

## 两条铁律

1. **不越过安全底线。** 给出的是「做法方向」与「需要谁核」，不是构件尺寸；
   任何路径都带 `sign_off`，说明必须由哪一类持证专业人员出计算书。
   这一层不产生结构计算，也不声称产生。
2. **不给假选项。** 如果在这个条件下所有路径都不成立（比如中间层想开天窗），
   如实返回 `blocked_by_physics` 并说明原因——这比列三条看着都行的假路径诚实。

## 与既有模块的分工

* `concept/disciplines.py` 负责「这套概念向专业提出了什么要求」；
* 本模块负责「这个要求有几种实现方式，各自代价是什么」；
* `hardgate.py` 负责安全与强制性规范的红线，本模块**不替代**它。

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple


@dataclass(frozen=True)
class Path:
    """一条实现设计意图的技术路径。

    `trades` 是这条路径拿什么换什么——没有零代价的路径，说"都能做"等于没说。
    """

    id: str
    name: str
    how: str                       # 做法，具体到能被工程师接话
    gains: str                     # 换来了什么（对设计的价值）
    trades: str                    # 代价
    sign_off: str                  # 必须由谁核（不能省）
    feasible_when: str = ""        # 前提条件；"不变"时留空

    def to_dict(self) -> Dict[str, str]:
        return {
            "path_id": self.id, "name": self.name, "how": self.how,
            "gains": self.gains, "trades": self.trades,
            "sign_off": self.sign_off, "feasible_when": self.feasible_when,
        }


@dataclass(frozen=True)
class Goal:
    """一个设计诉求，以及实现它的一到三条路径。"""

    id: str
    trigger: Tuple[str, ...]       # 概念文本里命中这些词就该认真考虑
    question: str                  # 设计师真正在问的那句话
    paths: Tuple[Path, ...]
    blocked_when: Tuple[Tuple[str, str], ...] = ()   # (条件词, 为什么做不到)
    note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "goal_id": self.id, "question": self.question,
            "paths": [p.to_dict() for p in self.paths],
            "note": self.note,
        }


# --------------------------------------------------------------------------
# 结构：让空间成立，而不是让结构好看
# --------------------------------------------------------------------------
STRUCTURE_GOALS: Tuple[Goal, ...] = (
    Goal(
        id="STR-DOUBLE-HEIGHT",
        trigger=("挑空", "通高", "跃层", "错层", "夹层"),
        question="这里要做通高，楼板怎么开、上面的荷载怎么接？",
        paths=(
            Path(
                id="P-PERIMETER-BEAM",
                name="边梁抬 / 四周加梁",
                how="沿开洞四周设加强梁，把上层荷载绕到两侧墙体或柱上",
                gains="保留完整通高且不落柱，开洞边缘可以做薄（视线更干净）",
                trades="梁高会吃掉开洞边缘的净高 200–400 mm，洞口做不大",
                sign_off="结构工程师出开洞与加固计算书；须先做现状鉴定",
                feasible_when="洞口两侧有可承重的墙或柱",
            ),
            Path(
                id="P-STEEL-FRAME",
                name="钢梁框架",
                how="洞边设钢梁，把跨度问题交给钢材，原结构只承担支座反力",
                gains="跨度能力最强，梁高比混凝土小，最容易保住设计想要的净高",
                trades="需防火包覆（占用尺寸）、与混凝土交接处需专门构造、造价上升",
                sign_off="结构工程师出计算书；防火与节点由专业深化",
            ),
            Path(
                id="P-CANTILEVER",
                name="局部悬挑",
                how="只保留一侧楼板，用悬挑减少落柱，边沿做薄",
                gains="视觉最轻，通高的边界可以很薄",
                trades="悬挑长度受限，挠度与振动需核；边沿做薄后保温与防水更难",
                sign_off="结构工程师核算挠度与振动；边沿构造由建筑师与幕墙深化",
                feasible_when="悬挑长度在常规范围内（通常 ≤2 m 量级，须核算）",
            ),
        ),
        note="所有路径都要先做现状鉴定；不做鉴定就给尺寸的，都不是设计，是猜。",
    ),
    Goal(
        id="STR-OPEN-PLAN",
        trigger=("拆", "打掉", "合并", "开放", "打通", "承重"),
        question="要把这些墙拿掉，哪些能动、动到什么程度？",
        paths=(
            Path(
                id="P-KEEP-AND-FRAME",
                name="保留 + 门洞化",
                how="承重墙不开或只开小洞，用门洞与半高柜把空间连通",
                gains="最安全、最便宜，且半高柜能同时承担收纳与视线控制",
                trades="空间仍是分段，做不出完全开放；洞口尺寸受限",
                sign_off="结构工程师确认开洞位置与限值",
            ),
            Path(
                id="P-ADD-BEAM-REPLACE",
                name="加梁托换",
                how="在墙上方设梁把荷载转走，再拆墙下部分",
                gains="能真正做成开放空间，隔墙可完全拆除",
                trades="梁会落在天花下（除非能藏进吊顶），层高会损失；施工需临时支撑",
                sign_off="结构工程师出托换方案与施工顺序；施工期间需监测",
                feasible_when="墙上有可设梁的位置，且两端有可靠支座",
            ),
            Path(
                id="P-PARTIAL-COLUMN",
                name="留柱化处理",
                how="保留部分结构柱，把柱做成空间构件（书架、壁柱、灯柱）",
                gains="代价最低，且柱可以变成空间节奏的一部分——很多好方案是这么来的",
                trades="需要设计愿意接受柱，而不是把它藏起来",
                sign_off="结构工程师确认保留范围与加固需求",
            ),
        ),
        note="「承重墙不能动」不是结论，是前提；前提之后的答案有三种。",
    ),
    Goal(
        id="STR-ADD-LOAD",
        trigger=("夹层", "加建", "屋顶花园", "种植", "回填", "重物"),
        question="新增的荷载由谁承担？",
        paths=(
            Path(
                id="P-LIGHTWEIGHT",
                name="轻质体系",
                how="用轻钢、木结构或轻质混凝土减少新增自重",
                gains="对原结构最友好，多数情况不需要大范围加固",
                trades="跨度受限、隔声与振动表现弱于混凝土；构造节点要求高",
                sign_off="结构工程师核算新增荷载与连接节点",
            ),
            Path(
                id="P-LOCAL-REINFORCE",
                name="局部加固",
                how="在原结构上粘贴碳纤维、包钢或增大截面，只加固受力集中处",
                gains="保留原结构体系，改动范围小",
                trades="施工期间影响使用；加固后的外观需处理（包钢会露出来）",
                sign_off="结构工程师出加固设计；须做原结构检测",
            ),
            Path(
                id="P-SEPARATE-SYSTEM",
                name="独立支撑体系",
                how="新增部分自带柱与基础，与原结构脱开",
                gains="原结构完全不承担新荷载，最干净",
                trades="会多出柱与基础，占用使用面积；室内可能牺牲通透",
                sign_off="结构工程师与岩土工程师共同确认基础",
            ),
        ),
    ),
    Goal(
        id="STR-LONG-SPAN",
        trigger=("大跨", "跨度", "无柱", "开阔", "一整片"),
        question="要一个无柱的大空间，跨度从哪来？",
        paths=(
            Path(
                id="P-TRUSS",
                name="桁架",
                how="用桁架承担跨度，设备与照明可穿行于桁架之间",
                gains="跨度能力最强，且桁架本身可以成为空间的顶",
                trades="桁架高度大，会明显压低净高；节点多、造价高",
                sign_off="结构工程师出计算书；消防与防火包覆需专项",
            ),
            Path(
                id="P-POST-TENSION",
                name="预应力",
                how="用预应力梁或板减少梁高，把跨度藏进楼板厚度里",
                gains="净高损失最小，顶面可以做平",
                trades="施工要求高、后期开洞几乎不可能（这一点必须在方案阶段说清）",
                sign_off="结构工程师与专业施工单位共同确认",
            ),
            Path(
                id="P-REDUCE-SPAN",
                name="减少跨度",
                how="接受中间落一到两根柱，把柱做成空间构件",
                gains="结构最经济，柱反而能建立空间节奏与分区",
                trades="失去完全无柱；需要设计真正用得上这两根柱",
                sign_off="结构工程师确认柱位与基础",
            ),
        ),
        note="「要无柱」值得先问一句：是为了看穿，还是为了灵活？两者答案不同。",
    ),
)

# --------------------------------------------------------------------------
# 机电：让设备消失，而不是让设备好看
# --------------------------------------------------------------------------
MEP_GOALS: Tuple[Goal, ...] = (
    Goal(
        id="MEP-HIGH-CEILING",
        trigger=("通高", "净高", "不吊顶", "裸露", "原始天花"),
        question="不想吊顶，设备和管线往哪走？",
        paths=(
            Path(
                id="P-EXPOSED-ORDERED",
                name="裸装有序",
                how="不吊顶，把管线按走向排布成可见的秩序（平行、分层、同色）",
                gains="净高全额保留，管线本身成为空间质感的一部分",
                trades="对排布精度要求极高，做不好就是工地感；后期改管会破坏秩序",
                sign_off="机电工程师确认排布不违反规范间距；消防需专项确认",
            ),
            Path(
                id="P-PERIPHERAL",
                name="周边走管",
                how="主管沿墙脚或墙边集中，主空间上方尽量不放管线",
                gains="主空间上方干净，净高保得住",
                trades="末端要绕远，风量与水量平衡需要更细的调试；墙边会形成一圈包管",
                sign_off="机电工程师核算末端效果与水力平衡",
            ),
            Path(
                id="P-LOCAL-SOFFIT",
                name="局部吊顶",
                how="只在设备集中处与走廊做局部吊顶，主空间不吊",
                gains="性价比最高，设备藏在次要空间，主空间保持完整",
                trades="局部吊顶会成为空间里的实体，需要被设计成造型而不是补丁",
                sign_off="机电工程师确认设备容量与检修口位置",
            ),
        ),
    ),
    Goal(
        id="MEP-WET-RELOCATE",
        trigger=("厨房移位", "卫生间移位", "湿区", "岛台", "开放厨房"),
        question="湿区要挪，水怎么排？",
        paths=(
            Path(
                id="P-SAME-FLOOR-DRAIN",
                name="同层排水",
                how="排水管在本层地面内敷设，不穿楼下天花；用壁挂洁具或抬高局部地面",
                gains="位置自由，楼下不受影响；检修可在本层完成",
                trades="地面需抬高或降板 100–200 mm；对防水与坡度要求高",
                sign_off="给排水工程师确认管径、坡度与通气",
            ),
            Path(
                id="P-WALL-DRAIN",
                name="沿墙排水",
                how="湿区沿可排水的外墙或管井布置，走横管到原立管",
                gains="不必抬高地面，改造量小",
                trades="位置受限于立管附近；横管需坡度，长度受限",
                sign_off="给排水工程师确认横管长度与坡度",
                feasible_when="湿区离原立管在可排范围内（通常 ≤3–4 m 量级，须核算）",
            ),
            Path(
                id="P-PUMP-DRAIN",
                name="提升排放",
                how="用污水提升装置把排水送到远处立管",
                gains="位置几乎不受限制，中岛厨房、地下室卫浴都能实现",
                trades="需电、需维护、有噪声与故障风险；不建议承担全部排水",
                sign_off="给排水工程师确认提升设备选型与备用方案",
            ),
        ),
        note="能不动立管就不动；真要动，先问清「挪多远」，答案决定选哪条。",
    ),
    Goal(
        id="MEP-NO-WINDOW",
        trigger=("无窗", "内区", "暗", "地下室", "中脊"),
        question="这个空间没有外窗，怎么让人不觉得闷？",
        paths=(
            Path(
                id="P-MECH-VENT",
                name="机械新风",
                how="按使用人数配新风量，风管走吊顶或墙边",
                gains="空气质量可控，不依赖开窗",
                trades="需要设备位与风管路径；长期运行有能耗与噪声",
                sign_off="暖通工程师核算新风量与噪声；消防确认防排烟",
            ),
            Path(
                id="P-BORROWED-LIGHT",
                name="引光 + 借景",
                how="用玻璃隔断、玻璃砖或光井把邻室的自然光引进来",
                gains="解决「暗」的心理问题，且不需要开新窗",
                trades="引来的光不等同于直射光；玻璃隔断的隔声要单独处理",
                sign_off="建筑师主导；结构确认开洞与光井做法",
            ),
            Path(
                id="P-LIGHT-AS-MATERIAL",
                name="把人工光做成材料",
                how="承认无自然光，用分层人工光与材质反射把空间做出温度",
                gains="最诚实的做法，很多地下空间正是靠这个成立",
                trades="白天也要开灯；照度与色温设计不到位会显得像办公室",
                sign_off="照明设计师与电气工程师配合",
            ),
        ),
        note="无窗不是缺陷，是需要被设计处理的条件——前提是先承认它。",
    ),
    Goal(
        id="MEP-KITCHEN-OPEN",
        trigger=("开放厨房", "岛台", "明档", "中岛"),
        question="厨房要开放，油烟与噪声怎么处理？",
        paths=(
            Path(
                id="P-STRONG-HOOD",
                name="强排 + 补风",
                how="大吸力油烟机就近直排外墙，同时做补风避免负压",
                gains="真正开放的前提；不倒灌、不串味",
                trades="烟道走向决定灶位，不能随便挪；补风口位置会影响体感",
                sign_off="暖通工程师确认排风量与补风路径",
            ),
            Path(
                id="P-SEMI-OPEN",
                name="半开放（玻璃 / 移门）",
                how="用玻璃隔断或隐藏移门，重油烟时关上，平时打开",
                gains="兼顾开放感与实用性，是大多数家庭真正用得上的做法",
                trades="需要门扇收纳空间；隔断轨道是长期维护点",
                sign_off="建筑师与暖通共同确认",
            ),
            Path(
                id="P-COOKTOP-SPLIT",
                name="灶台分离",
                how="把重油烟的灶独立成小间，中岛只做备餐与轻食",
                gains="开放感最大化，且油烟问题从源头解决",
                trades="灶间面积小、需独立排风；动线变长",
                sign_off="暖通工程师确认灶间排风",
            ),
        ),
    ),
)

#: 关键词 → 目标。用于从概念文本里找到「需要回答的技术问题」。
STRUCTURE_INDEX: Dict[str, Tuple[str, ...]] = {g.id: g.trigger for g in STRUCTURE_GOALS}
MEP_INDEX: Dict[str, Tuple[str, ...]] = {g.id: g.trigger for g in MEP_GOALS}

_ALL_GOALS: Dict[str, Goal] = {g.id: g for g in (*STRUCTURE_GOALS, *MEP_GOALS)}

#: 物理上不成立的条件：命中就返回 blocked，不列假路径。
PHYSICAL_BLOCKS: Tuple[Tuple[str, Tuple[str, ...], str], ...] = (
    ("skylight_mid_floor",
     ("天窗", "开洞", "天光"),
     "非顶层且上方有住户时无法向上开天窗——这是物理条件，不是资料问题。"
     "可选替代：光井（若邻接屋面）、高侧窗、玻璃隔断引光、把人工光做成材料。"),
    ("below_grade_window",
     ("地下室", "地下层"),
     "地下层无法获得直接自然采光。可选替代：下沉庭院、采光井、导光管、"
     "把人工光做成材料——但不应当作「有自然光」来卖。"),
)


def _goals_for(text: str, goals: Sequence[Goal]) -> List[Goal]:
    """哪些目标被这段文字真正触发了。没有命中就不提，不列通用清单。"""
    hit: List[Goal] = []
    for g in goals:
        if any(w in text for w in g.trigger):
            hit.append(g)
    return hit


def structure_paths(text: str, *, floor_context: str = "") -> Dict[str, Any]:
    """结构侧：这个设计诉求有哪几条实现路径。"""
    goals = _goals_for(text, STRUCTURE_GOALS)
    return {
        "discipline": "structure",
        "role": "让空间成立",
        "goals": [g.to_dict() for g in goals],
        "blocked": _blocks(text, floor_context),
        "principle": ("结构从属于设计：先明确要做成什么，再选实现路径。"
                      "每条路径都标了代价与必须由谁签，不越过安全底线。"),
    }


def mep_paths(text: str, *, floor_context: str = "") -> Dict[str, Any]:
    """机电侧：这些条件怎么让设备消失。"""
    goals = _goals_for(text, MEP_GOALS)
    return {
        "discipline": "mep",
        "role": "让设备消失",
        "goals": [g.to_dict() for g in goals],
        "blocked": _blocks(text, floor_context),
        "principle": ("机电从属于设计：目标是让设备不成为空间的对手，"
                      "而不是把设备藏起来就算完成。"),
    }


def _blocks(text: str, floor_context: str) -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []
    ctx = (text + " " + floor_context).lower()
    for bid, words, why in PHYSICAL_BLOCKS:
        if not any(w in text for w in words):
            continue
        if bid == "skylight_mid_floor":
            # 只有明确「中间层/非顶层」或未说明层数时才提醒；顶层不拦
            top = any(w in ctx for w in ("顶层", "顶楼", "屋顶", "自建房", "独栋"))
            if top:
                continue
            out.append({"id": bid, "why": why,
                        "status": "conditional",
                        "needs": "该空间是否位于顶层或可对天开洞"})
        elif bid == "below_grade_window":
            out.append({"id": bid, "why": why, "status": "blocked",
                        "needs": "是否有可开挖的下沉庭院条件"})
    return out


def all_goals() -> List[Goal]:
    return [*STRUCTURE_GOALS, *MEP_GOALS]


def goal(goal_id: str) -> Optional[Goal]:
    return _ALL_GOALS.get(goal_id)


def markdown(sections: Sequence[Dict[str, Any]]) -> str:
    """写给业主看的「能做，代价是这个」——不是技术说明书。"""
    lines: List[str] = []
    for sec in sections:
        if not sec.get("goals") and not sec.get("blocked"):
            continue
        lines += [f"## {('结构' if sec['discipline'] == 'structure' else '机电')}：{sec['role']}", ""]
        for b in sec.get("blocked") or []:
            lines += [f"> **前提未满足**：{b['why']}", ""]
        for g in sec.get("goals") or []:
            lines += [f"**{g['question']}**", ""]
            lines += ["| 路径 | 怎么做 | 换来什么 | 代价 | 谁来核 |", "|---|---|---|---|---|"]
            for p in g["paths"]:
                lines.append(f"| {p['name']} | {p['how']} | {p['gains']} | "
                             f"{p['trades']} | {p['sign_off']} |")
            lines.append("")
            if g.get("note"):
                lines += [f"> {g['note']}", ""]
    return "\n".join(lines)


__all__ = [
    "Path", "Goal", "STRUCTURE_GOALS", "MEP_GOALS", "STRUCTURE_INDEX", "MEP_INDEX",
    "structure_paths", "mep_paths", "all_goals", "goal", "markdown",
]
