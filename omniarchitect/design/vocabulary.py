"""设计语汇层 —— 让方案像一个建筑师做的，而不是像一个系统生成的。

## 这个模块存在的理由

S1 问的是行为，S2 选的是空间原型，风格库管的是观感。三层都成立，却仍缺一层：

**没有一层在描述「人走进去会经历什么」。**

原型说的是「房间怎么排」，风格说的是「看起来像什么」，中间这段——从进门到坐下，
视线被什么挡住、在哪一步被放开、什么时候安静下来、哪一处让人想停住——恰好是
建筑与「能用的房子」之间的全部差别。Appleton 的前景—庇护理论（1975）、
Palladio 关于平面比例决定层高的主张、以及 enfilade（套间序列）到走廊的演变，
讲的都是这件事。

所以这里只做三件事，不做第四件：

1. `VOCABULARY` —— 空间体验词表：每个词有判据、有做法、有用错了会怎样；
2. `sequence_for()` —— 从一个空间原型推出可指认的体验序列（第一眼 → 转折 → 主空间）；
3. `fit()` —— 把业主说过的感受词对回方案，判断「他要的感觉，这套方案给不给得出」。

## 边界（这几条比功能重要）

* **没有状态、没有门禁、没有审批。** 这一层是判据，不是流程。它不新增 G 点，
  不拦人，也不要求任何人签字。
* **不编造名作案例。** 词条里写做法与判据，不写「某某建筑因此著名」——
  一旦写了就等于替建筑师背书，而我们无法核实。
* **词表只用有专业依据的概念**（前景/庇护、压缩/释放、门槛、套间序列、
  框景、借景、节奏、触感、层高关系）。自造词是这一层最容易犯的错。
* **业主没说的时候，不替他决定感受。** `fit()` 在业主未表达时返回
  `not_stated`，而不是「推荐温馨」。

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

# --------------------------------------------------------------------------
# 1. 空间体验词表
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Device:
    """一个设计师真的能画出来的体验手法。

    `test` 是这整个 dataclass 存在的理由：一个没有核验办法的术语只是装饰。
    每条都必须回答「在图上怎么看出做到了」。
    """

    id: str
    name: str
    plain: str                      # 说给业主听的
    why: str                        # 为什么有效（机制，不是形容词）
    how: Tuple[str, ...]            # 具体做法
    test: str                       # 在图上怎么核验
    misuse: str                     # 用错了会怎样
    pairs_with: Tuple[str, ...] = ()


VOCABULARY: Dict[str, Device] = {
    "compression_release": Device(
        id="compression_release",
        name="压缩与释放",
        plain="先让人缩一下，再放开",
        why="天花压低、通道收窄会让身体先记下这个尺度，随后进入高敞空间时，"
            "同一净高会被读成更大——对比产生尺度感，绝对值不产生。",
        how=("进入段净高压到 2.4–2.6 m，主空间保持结构允许的最大净高",
             "通道净宽收到 900–1200 mm，进入主空间前放开到 2 倍以上",
             "压低段长度不超过 3 m，否则从仪式变成憋屈",
             "压低段用吸光材料，释放段用浅色或反光材料强化反转"),
        test="在剖面图上量：进入段与主空间净高之比应 ≥1:1.3；"
             "压低段长度 <3 m；平面上通道宽度与主空间宽度比 ≥1:2。",
        misuse="压低段过长或过暗，人会以为走错路；释放段不足时反差消失，白做了。",
        pairs_with=("threshold", "framing"),
    ),
    "prospect_refuge": Device(
        id="prospect_refuge",
        name="前景与庇护",
        plain="能看出去，但背后有靠",
        why="Appleton 1975：人偏好同时能远望（prospect）与有遮挡（refuge）的位置。"
            "这不是审美偏好，是安全感的空间表达——所以靠墙、背对实墙、面向开敞的座位"
            "会自然被选中。",
        how=("主要座位背靠实墙或高柜，面向视距 >4 m 的开敞面",
             "窗边做可坐的深度（≥450 mm）与上方压低的顶，形成壁龛",
             "避免座位背后是通道、玻璃或空旷区",
             "开放空间用家具围合出有背的角落，不靠加隔墙"),
        test="在平面上标出主要座位：背后 600 mm 内是否有实体（墙/柜/高靠背）；"
             "前方视距是否 >4 m。两者都满足才算成立。",
        misuse="只做开敞不做庇护，空间显得冷、留不住人；只做庇护不做前景，会压抑。",
        pairs_with=("framing", "compression_release"),
    ),
    "threshold": Device(
        id="threshold",
        name="门槛与过渡",
        plain="进门有个缓冲",
        why="limen（门槛）是空间的心理分界。没有过渡的空间会让人直接暴露——"
            "这是玄关被反复讨论的真正原因，与收纳无关。",
        how=("入户后先经过 ≥1.2 m 深的过渡区再进入公共区",
             "过渡区提供三个动作的落点：放下、换鞋、看一眼",
             "视线在过渡区被挡一次，不直接看到主空间全貌",
             "地面材质在过渡区变化，用材料提示已经进来了"),
        test="从入户门画一条 1.5 m 半径的视线扇形，检查是否直接看到客厅主沙发；"
             "过渡区进深 ≥1.2 m 且能容纳三个动作。",
        misuse="过渡区被压成一条窄走廊，就只剩交通功能，缓冲消失。",
        pairs_with=("compression_release", "arrival_sequence"),
    ),
    "enfilade": Device(
        id="enfilade",
        name="套间序列",
        plain="一扇门套着一扇门，看到底",
        why="门洞对齐形成的连续视轴，会把注意力推向端点——"
            "这是等级与仪式最古老的空间工具，也是唯一能一眼看到底的空间。",
        how=("三到四个门洞在同一条轴上对齐，端点放一个值得走到底的东西",
             "每道门洞尺寸依次略收，强化透视",
             "只用于公共到半公共段，不用于私密区（会牺牲隐私）",
             "端点可以是窗、艺术品、一段墙，但必须是实体而非通道"),
        test="在平面上连门洞中点：是否 3 个以上共线；端点是否为实体（不是门洞）。",
        misuse="用在住宅私密区会让人一进门看穿卧室；端点若是通道，视轴失效。",
        pairs_with=("framing", "arrival_sequence"),
    ),
    "framing": Device(
        id="framing",
        name="框景",
        plain="把景装进一个框里",
        why="无边的景会被当成背景，有边界的景会被当成画面。框的作用是"
            "把注意力从很大一片收到这一个。",
        how=("用墙体、梁下、门洞或家具形成前景框，框中放远景或光",
             "框的开口宽度与视距之比控制在 1:2–1:4，过宽失去框感",
             "前景框用深色或粗糙材料，远景用亮面，拉开层次",
             "同一空间只设一个主框，多框会让视线散掉"),
        test="在主视点画视线：是否有前景构件界定开口；开口外是否有可看的对象"
             "（景/光/墙）而非空走廊。",
        misuse="框太多等于没框；框中无物则成了挡板。",
        pairs_with=("prospect_refuge", "borrowed_view"),
    ),
    "borrowed_view": Device(
        id="borrowed_view",
        name="借景",
        plain="把外面的东西借进来用",
        why="视线穿过边界到达不属于本空间的对象时，空间的心理面积会扩大。"
            "这是小空间最有效的手法，也是唯一不需要增加面积的手法。",
        how=("优先借：树冠、天空、远处屋顶线、一段水",
             "窗台高度降到 450–600 mm，让坐姿也能看到借来的对象",
             "窗前 1.5 m 内不放大件家具，保证视线通道",
             "无景可借时，用院内一棵植物或一面有光的墙作为人造借景"),
        test="在平面上从主要座位画视线到外墙：是否落在可看的对象上；"
             "窗前 1.5 m 是否为通行或留空。",
        misuse="窗前堆家具，借景只剩有窗；借到邻栋墙面则变成压迫。",
        pairs_with=("framing", "prospect_refuge"),
    ),
    "rhythm": Device(
        id="rhythm",
        name="节奏与重复",
        plain="有重复，也有变化",
        why="等距重复建立预期，一次打破建立记忆点。全是变化等于没有重点，"
            "全是重复等于没有设计。",
        how=("选一个可重复的构件（柱、窗、柜门、灯位）按等距排布",
             "在同一序列里留一处不同：加宽、抬高、断掉一格",
             "重复单元的间距与功能模数对齐，不对齐会被读成施工误差",
             "变化点只出现一次，重复出现就失效"),
        test="在立面上数重复单元：是否 ≥5 个等距单元；是否只有一处例外；"
             "例外处是否与入口或主视点对应。",
        misuse="重复间距不等会被读成错误；例外过多会被读成没做完。",
        pairs_with=("light_layering",),
    ),
    "light_layering": Device(
        id="light_layering",
        name="光的层次",
        plain="不是一盏大灯照亮全部",
        why="均匀照度让材料失去质感，因为质感来自掠射与阴影。三个高度"
            "（低位、中位、高位）各自负责不同任务，才有层次。",
        how=("高位：洗墙或暗藏灯带，负责照亮界面而非地面",
             "中位：重点光，落在需要看清的东西上（桌面、台面、画）",
             "低位：地脚或家具下沿，负责夜间引导与低处的暖",
             "同一空间至少两个高度有光源，且能分开控制"),
        test="在照明点位图上按标高分类：是否 ≥2 个高度；是否有分区控制；"
             "洗墙光是否距墙 150–300 mm。",
        misuse="只有中位光时夜里像办公室；全部高位会压平材料。",
        pairs_with=("rhythm", "material_honesty"),
    ),
    "material_honesty": Device(
        id="material_honesty",
        name="材料的真实与触感",
        plain="看得出是什么做的，摸得到",
        why="材料被处理成某种效果时，人读到的是廉价；材料保留自身构造逻辑时，"
            "人读到的是可信。手能碰到的地方，触感比视觉更早形成判断。",
        how=("手可及高度（0.6–1.5 m）用有真实触感的材料，不用贴皮仿制",
             "让构造可见：板缝、砌缝、木纹方向成为设计的一部分",
             "同一空间主材不超过三种，其余做背景",
             "收口处不做假装（不用金属条遮住材料交界）"),
        test="在材料表中核对：主材是否 ≤3 种；0.6–1.5 m 高度带的材料是否为真实材质；"
             "是否标注了纹理方向与拼缝方式。",
        misuse="仿石材瓷砖贴在触手可及处，远看成立、近看失效。",
        pairs_with=("light_layering", "proportion"),
    ),
    "proportion": Device(
        id="proportion",
        name="比例与层高关系",
        plain="房间的长宽高是有关系的",
        why="Palladio 在《建筑四书》里主张层高应由平面尺寸推出，而非独立选一个数。"
            "尺寸之间互相呼应时，空间看起来才不是碰巧的。",
        how=("先定平面长宽比（常用 1:1、1:1.4、2:3、3:5、1:2）",
             "层高按平面推算：算术（均值）、几何（比例中项）或调和平均",
             "同一序列内的房间共用一套比例关系，不逐个看着办",
             "窄长空间靠压低层高或分段处理，不硬做方正"),
        test="在平面与剖面之间核对：主要房间长宽比是否落在常用比例上；"
             "层高是否与平面尺寸存在可复述的关系。",
        misuse="层高随手定 2.8 m 会让所有房间一个感觉；窄空间做高会更显窄。",
        pairs_with=("compression_release", "material_honesty"),
    ),
    "arrival_sequence": Device(
        id="arrival_sequence",
        name="到达序列",
        plain="到家是分几步的",
        why="到达不是办手续，是一段被设计的过渡。序列决定第一印象落在第几眼，"
            "也决定人有没有时间从外面切换到里面。",
        how=("拆成四步：接近、卸下、停留、进入，每步有独立的空间事件",
             "第一眼不放最重要的东西，第三眼放",
             "卸下与停留处必须有可坐或可放的面",
             "进入点收窄，让进去这个动作有明确边界"),
        test="按入口路径画四个停点：每点是否有一个明确的空间事件（可坐/可看/可放）；"
             "第一眼与主视觉焦点是否错开。",
        misuse="一眼看到全部，序列消失；四步压缩成一步，等于没有到达感。",
        pairs_with=("threshold", "compression_release"),
    ),
}

#: 中文感受词 → 词表 id。只收真正有空间含义的词，纯风格词走风格系统。
FEELING_WORDS: Dict[str, Tuple[str, ...]] = {
    "开阔": ("compression_release", "borrowed_view"),
    "敞亮": ("borrowed_view", "light_layering"),
    "通透": ("framing", "borrowed_view"),
    "大气": ("compression_release", "enfilade"),
    "仪式感": ("arrival_sequence", "enfilade", "threshold"),
    "安静": ("prospect_refuge", "compression_release"),
    "放松": ("prospect_refuge", "light_layering"),
    "温馨": ("light_layering", "material_honesty"),
    "温暖": ("light_layering", "material_honesty"),
    "有质感": ("material_honesty", "light_layering"),
    "质感": ("material_honesty",),
    "高级": ("material_honesty", "proportion"),
    "舒服": ("prospect_refuge", "proportion"),
    "不压抑": ("compression_release", "borrowed_view"),
    "有层次": ("compression_release", "light_layering", "rhythm"),
    "有趣": ("rhythm", "framing"),
    "私密": ("prospect_refuge", "threshold"),
    "一步一景": ("enfilade", "framing"),
    "秩序": ("rhythm", "enfilade"),
    "干净": ("material_honesty", "rhythm"),
    "显大": ("borrowed_view", "compression_release"),
    "自然": ("borrowed_view", "material_honesty"),
}


def device(device_id: str) -> Optional[Device]:
    return VOCABULARY.get(device_id)


def all_devices() -> List[Device]:
    return [VOCABULARY[k] for k in VOCABULARY]


def read_feelings(text: str) -> Dict[str, List[str]]:
    """从业主原话里读出空间感受诉求。

    返回 ``{原词: [手法 id]}``。长词优先，所以「不压抑」不会被读成「压抑」；
    保留原词，是为了在任务书里引用业主的话，而不是把他改写成设计术语。
    """
    raw = (text or "").strip()
    if not raw:
        return {}
    out: Dict[str, List[str]] = {}
    for word in sorted(FEELING_WORDS, key=len, reverse=True):
        if word in raw:
            if any(word in longer and word != longer for longer in out):
                continue
            out[word] = list(FEELING_WORDS[word])
    return out


# --------------------------------------------------------------------------
# 2. 从空间原型推出体验序列
# --------------------------------------------------------------------------

#: 每个空间家族天然擅长的体验手法——「这套原型本来就给得出什么」，
#: 不是「我们想让它说什么」。
#:
#: 判据是「这个家族的**空间结构**是否本身就解决了该手法要解决的问题」。
#: 列表第一位是它的**主张**（`score_feelings` 据此判断 primary）：
#: 分层递进的本质是门槛与到达，不是压缩——写成压缩会让「仪式感」被判成非强项，
#: 而仪式感恰恰是这套原型最给得出来的东西。
FAMILY_DEVICES: Dict[str, Tuple[str, ...]] = {
    "linear": ("compression_release", "enfilade", "rhythm", "light_layering"),
    "radial": ("rhythm", "framing", "light_layering", "borrowed_view"),
    "cluster": ("borrowed_view", "prospect_refuge", "material_honesty", "light_layering"),
    "layered": ("arrival_sequence", "threshold", "compression_release", "light_layering"),
    "hall": ("compression_release", "light_layering", "framing", "borrowed_view"),
    "courtyard": ("borrowed_view", "framing", "prospect_refuge", "light_layering"),
}

#: 「转折」这一段在不同家族里实际发生什么。原型写的是布局，这里写的是经历。
#: 没有对应条目的原型不硬凑——宁可少一段，也不写一句对的废话。
TURN_EVENT: Dict[str, str] = {
    "linear": "路径被墙或柜收窄一次，宽度变化提示「要到了」；走到端部才放开。",
    "radial": "身体被核心体块挡住，必须选一条边走；选路本身让人记住空间。",
    "cluster": "从一处围合走向另一处围合，中间的开口是唯一的视线出口。",
    "layered": "方向或标高的第一次改变落在门槛上——跨过去才算进入。",
    "hall": "从窄处走向开阔处，天花先抬起来，人跟着抬头。",
    "courtyard": "穿过一段有顶的廊，明暗交替一次，头顶从实体换成天空。",
}

#: 每套原型一句「进门先看到什么」——必须具体到能画，不能是形容词。
ENTRY_EVENT: Dict[str, str] = {
    "RES-SPINE": "进门先是一段收纳墙的完整面，看不出客厅在哪；转过墙端才看见窗。",
    "RES-BAND": "进门是一条横向灯带把人往公共区带，走廊在另一侧才开始。",
    "RES-LOOP": "进门正对一个体块的转角，向左或向右都能到公共区——第一眼没有主画面。",
    "RES-THRESHOLD": "进门停在一条可以坐下换鞋的长凳前，视线被半高柜挡住。",
    "RES-LIGHT": "进门正对采光带尽头，天花上有一条光把人往前引。",
    "RES-FLEX": "进门先看见可变房间的半开隔断，公共区在它后面。",
    "OFF-NEIGHBOURHOOD": "进门先看见接待与一组讨论位，办公区在玻璃之后。",
    "OFF-FOCUS-SPINE": "进门正对协作岛的热闹面，安静的一侧在左手边向内退。",
    "OFF-ACTIVITY-BAND": "进门沿长桌纵向往里看，尽头是茶水与窗。",
    "OFF-CORE-FRONT": "进门停在前场，右手是接待台，办公区在刷卡门之后。",
    "HOS-PROCESSION": "落客后先看见低照度门厅，大堂的景观面在第三步才出现。",
    "HOS-COURTYARD": "进门穿过一段廊，先看见院里的树，再看见前台。",
    "HOS-BOH-SPINE": "进门看到完整的大堂面，后勤口完全在视线之外。",
    "RET-THEATRE": "进门先看见明档的火与蒸汽，客座在它前面散开。",
    "RET-LOOP": "进门正对一段陈列墙，身体被带着向一侧绕。",
    "RET-DAYPART": "进门先看见沿街段的完整店面，往里逐段变暗。",
    "EXH-PROMENADE": "序厅压低收窄，主展区的第一次开放就是第一个展项。",
    "EXH-BOX": "进门是一条低照度过渡廊，先给眼睛适应的时间。",
    "EXH-ISLAND": "进门即看见大部分展岛，视线不被阻断。",
    "ARC-COURTYARD": "进门穿院，先看见院墙与天空，再看见门厅。",
    "ARC-BAR-PODIUM": "从街道进入裙房公共层，居住或办公入口在另一侧标高。",
    "ARC-SPLIT": "进门看到两个体量之间的缝，路径沿缝向里。",
}

SEQUENCE_STEPS = ("接近", "卸下", "第一眼", "转折", "主空间")

#: 方案希望人记住的那一处。必须是一个**位置**，不是一种感受——
#: 「很温馨」不可复核，「转过墙端的那个窗」可以。
_MEMORY_POINT: Dict[str, str] = {
    "linear": "转过墙端或走到端部的那一下——整面光出现在侧面",
    "radial": "选路那一刻：同一条走廊的两个方向都能到同一个地方",
    "cluster": "两处围合之间那个开口，它只框住一小片外面",
    "layered": "跨过门槛之后亮度抬起来的那一步",
    "hall": "抬头看到天花的那一眼",
    "courtyard": "头顶从有顶变成天空的那一瞬",
}

#: 主空间那一段的光，按家族写「人感受到什么」，而不是抄采光策略。
_DAYLIGHT_EVENT: Dict[str, str] = {
    "linear": "走到端部时光从一侧整面进来，墙上出现一道明确的明暗界。",
    "radial": "绕行过程中光从外侧断续进来，空间在明暗之间被切成一节一节。",
    "cluster": "从一个围合走到另一个围合，每处开口都框住一小片外面的光。",
    "layered": "穿过门槛后亮度抬一次，最深的私密区反而最暗、最稳。",
    "hall": "抬头看天花的瞬间，光从上方落下来，把整个空间一次交代清楚。",
    "courtyard": "头顶从实体换成天空，光的方向从侧面变成从上往下。",
}


def sequence_for(prototype: Dict[str, Any]) -> Dict[str, Any]:
    """把一套原型的「布局描述」翻译成「人经历到什么」。

    这是本模块唯一真正新增的能力：原型说的是房间怎么排，这里说的是走进去
    每一段发生什么空间事件。
    """
    pid = str(prototype.get("prototype_id") or "")
    family = str(prototype.get("family") or "")
    devices = [d for d in FAMILY_DEVICES.get(family, ()) if d in VOCABULARY]
    entry = ENTRY_EVENT.get(pid, "")

    steps: List[Dict[str, str]] = []
    if entry:
        dev = "compression_release" if family in ("layered", "hall") else (
            "threshold" if family == "courtyard" else "framing")
        steps.append({"step": "第一眼", "event": entry, "device": dev})
    if prototype.get("circulation"):
        turn = TURN_EVENT.get(family) or ""
        steps.append({
            "step": "转折",
            # 优先写「经历」，布局细节只在没有家族条目时后退使用——
            # 直接把 circulation 原文贴进来，等于把布局当体验，正是要消除的毛病。
            "event": turn or f"路径上第一次转向：{prototype['circulation']}",
            "detail": str(prototype["circulation"]),
            "device": "threshold" if family in ("layered", "courtyard") else "compression_release",
        })
    if prototype.get("daylight"):
        steps.append({
            "step": "主空间",
            "event": _DAYLIGHT_EVENT.get(family) or
                     f"进入主空间时的光环境：{prototype['daylight']}",
            "detail": str(prototype["daylight"]),
            "device": "light_layering",
        })
    if prototype.get("experience"):
        # 「留下什么」不再抄 experience——上一节「使用体验」已经原样引用过它，
        # 同一段话在报告里出现两次，读起来就是系统在凑字数。这里只给一个
        # 可复核的**记忆点**：方案希望人记住哪一处。
        memory = _MEMORY_POINT.get(family) or ""
        steps.append({
            "step": "记住的是",
            "event": memory or "本原型没有单独设定的记忆点，靠空间关系本身成立",
            "device": "prospect_refuge" if family in ("cluster", "courtyard")
            else "material_honesty",
        })

    return {
        "prototype_id": pid,
        "family": family,
        "steps": steps,
        "devices": devices,
        "missing_steps": [s for s in ("第一眼", "转折", "主空间")
                          if not any(x["step"] == s for x in steps)],
        "note": ("序列描述的是人走进去经历什么，不是房间布置。"
                 "缺少的段落如实列出，不用形容词补。"),
    }


# --------------------------------------------------------------------------
# 3. 业主的感受 → 方案能不能给
# --------------------------------------------------------------------------

def score_feelings(feelings: Dict[str, List[str]],
                   prototype: Dict[str, Any]) -> Dict[str, Any]:
    """给一套方向打「对业主诉求的代表性」，用于在方案之间拉出差别。

    为什么需要它：三套方向都能回应同一句「要显得敞亮」时，报告里三条都写
    「天然给得出」，业主读到的是一样的话，等于没帮他选。差别在于**是不是强项**：

    * ``primary``  —— 该手法排在这个空间家族的**第一位**：这是这套方案的主张本身；
    * ``supported``—— 在家族能力内但排在后面：能做得不错，但不是它出彩的地方；
    * ``stretched``——不在家族能力内：要额外努力，甚至补不回来。

    `primary` 是可以被反驳的判断（「不对，这套不是靠借景，是靠光」），
    这正是报告该有的东西。
    """
    family = str(prototype.get("family") or "")
    order = list(FAMILY_DEVICES.get(family, ()))
    primary: List[Dict[str, str]] = []
    supported: List[Dict[str, str]] = []
    stretched: List[Dict[str, str]] = []
    for word, devs in (feelings or {}).items():
        hit = [d for d in devs if d in order]
        if hit and order.index(hit[0]) == 0:
            primary.append({"word": word, "device": hit[0],
                            "how": f"{VOCABULARY[hit[0]].name}是这套空间家族的第一主张"})
        elif hit:
            supported.append({"word": word, "device": hit[0],
                              "how": f"靠{VOCABULARY[hit[0]].name}给得出，但不是这套的强项"})
        else:
            need = devs[0] if devs else ""
            obj = VOCABULARY.get(need)
            stretched.append({"word": word, "device": need,
                              "how": (f"要靠{obj.name}，而它不在这个空间家族的能力里"
                                      if obj else "没有对应的空间手法"),
                              "fix": obj.how[0] if obj else ""})
    # 权重：primary 2 分、supported 1 分、stretched 0 分，按业主提到的词数归一
    total = max(1, len(feelings or {}))
    weight = round((2 * len(primary) + len(supported)) / (2 * total), 3)
    return {
        "primary": primary,
        "supported": supported,
        "stretched": stretched,
        "weight": weight,
        "headline": (f"这套方案最擅长给的是「{primary[0]['word']}」"
                     if primary else
                     ("能给到" + "、".join(f"「{x['word']}」" for x in supported)
                      if supported else "你要的感觉它不是强项")),
    }


def fit(feelings: Dict[str, List[str]], prototype: Dict[str, Any]) -> Dict[str, Any]:
    """这套方向给不给得出业主要的那个感觉。

    三种结果，无聊的那种才是诚实的：

    * ``not_stated`` — 业主没说，我们不替他编一个愿望；
    * ``met``        — 这套原型的空间家族天然带得动该手法；
    * ``at_risk``    — 带不动，要么在 S3 用具体做法补，要么现在告诉业主。
    """
    if not feelings:
        return {"status": "not_stated", "asked": [], "met": [], "at_risk": [],
                "note": "业主未表达空间感受诉求——不替他决定要什么感觉。"
                        "可在 S1 补问一句，也可由主创先给方向。"}

    family = str(prototype.get("family") or "")
    native = set(FAMILY_DEVICES.get(family, ()))
    met: List[Dict[str, str]] = []
    risk: List[Dict[str, str]] = []
    for word, devs in feelings.items():
        hit = [d for d in devs if d in native]
        if hit:
            met.append({"word": word, "device": hit[0],
                        "how": f"{VOCABULARY[hit[0]].name}：这套原型的空间家族天然给得出"})
        else:
            need = devs[0] if devs else ""
            dev_obj = VOCABULARY.get(need)
            risk.append({
                "word": word, "device": need,
                "how": (f"需要靠{dev_obj.name}补，但该手法不属于这个空间家族的强项"
                        if dev_obj else "没有对应的空间手法"),
                "fix": dev_obj.how[0] if dev_obj else "",
            })
    status = "at_risk" if risk else ("met" if met else "not_stated")
    detail = score_feelings(feelings, prototype)
    return {
        "status": status,
        "asked": list(feelings),
        "met": met,
        "at_risk": risk,
        # 三套方向都能 met 时，靠这组字段拉出差别——见 score_feelings 的说明
        "primary": detail["primary"],
        "supported": detail["supported"],
        "weight": detail["weight"],
        "headline": detail["headline"],
        "note": ("met 表示这套方向不需要额外努力就成立；at_risk 表示要在 S3 用具体"
                 "做法补回来，或如实告诉业主这套方向给不出这个感觉。"),
    }


def markdown(feelings: Dict[str, List[str]], sequences: Sequence[Dict[str, Any]],
             fits: Sequence[Dict[str, Any]]) -> str:
    """业主能直接反应的一段「走到哪看到什么」。"""
    lines: List[str] = ["## 空间体验与序列", ""]
    if feelings:
        lines += ["业主原话里的感受：" + "、".join(f"「{w}」" for w in feelings), ""]
    if not sequences:
        return "\n".join(lines + ["> 本版未生成体验序列。", ""])
    for seq, f in zip(sequences, fits):
        lines += [f"### {seq['prototype_id']}", ""]
        if seq.get("steps"):
            lines += ["| 段落 | 人经历到什么 | 手法 |", "|---|---|---|"]
            for s in seq["steps"]:
                dev = VOCABULARY.get(s.get("device") or "")
                lines.append(f"| {s['step']} | {s['event']} | {dev.name if dev else '—'} |")
            lines.append("")
        if seq.get("devices"):
            names = "、".join(VOCABULARY[d].name for d in seq["devices"])
            lines += [f"**这套空间家族擅长的手法**：{names}", ""]
        if seq.get("missing_steps"):
            lines += [f"> 未覆盖的序列段落：{'、'.join(seq['missing_steps'])}"
                      "——不是遗漏，是本原型在这一段没有可指认的空间事件。", ""]
        if f["status"] == "met":
            lines += ["**对业主诉求的回应**：" + "；".join(
                f"「{m['word']}」— {m['how']}" for m in f["met"]), ""]
        elif f["status"] == "at_risk":
            lines += ["**对业主诉求的回应**："]
            for m in f["met"]:
                lines.append(f"- 「{m['word']}」可以给：{m['how']}")
            for r in f["at_risk"]:
                suffix = f"；起步做法：{r['fix']}" if r.get("fix") else ""
                lines.append(f"- 「{r['word']}」需要额外补：{r['how']}{suffix}")
            lines.append("")
        else:
            lines += [f"> {f['note']}", ""]
    return "\n".join(lines)


__all__ = [
    "Device", "VOCABULARY", "FEELING_WORDS", "FAMILY_DEVICES", "ENTRY_EVENT",
    "SEQUENCE_STEPS", "device", "all_devices", "read_feelings", "sequence_for",
    "fit", "score_feelings", "markdown",
]
