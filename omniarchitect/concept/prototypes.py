"""Spatial prototypes —— 概念方向的「空间组织策略」库。

一份概念方向由两部分组成，缺一不可：

1. **空间原型**（本模块）：房间怎么组织、人怎么走、光怎么进来、服务怎么藏。
2. **视觉语言**（`palette.py` 与风格库）：材料、色彩、光的质感。

两者必须分开。同一个「中部服务脊」可以是意式极简，也可以是非洲当代；
同一个「意式极简」既可以做动静横分，也可以做回游环。把选风格当成做完概念，
是这一层最常犯的错。

每个原型都带 `answers`：它主要回应 S1 的哪一类设计问题。方向生成时按证据匹配，
不按「凑三个」匹配 —— 一个项目如果只有采光问题，三个方向就该都在采光上做文章，
而不是硬塞一个储物方向。

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

#: 机会主题 → 原型 `answers` 用的判据词
THEME_LABEL: Dict[str, str] = {
    "daylight": "自然采光",
    "circulation": "动线与穿过",
    "privacy": "隐私与安静",
    "area": "面积效率",
    "storage": "收纳系统",
    "kitchen": "烹饪与用餐",
    "acoustic": "噪声与分贝",
    "flexibility": "未来变化",
    "service": "服务与后勤",
    "experience": "空间体验",
    "brand": "品牌与识别",
    "focus": "专注工作",
    "collaboration": "协作",
    "growth": "增长弹性",
    "operation": "运营效率",
    "arrival": "到达序列",
    "exhibit": "展陈叙事",
    "structure": "结构与跨度",
    "outdoor": "室内外关系",
}


@dataclass
class Prototype:
    """One way of organising space. Not a style, not a mood."""

    id: str
    profile: str
    name: str
    family: str                       # linear / radial / cluster / layered / hall / courtyard
    statement: str                    # 一句话空间主张（动词 + 空间事件）
    spatial_logic: str                # 房间怎么排
    circulation: str                  # 人怎么走
    daylight: str                     # 光怎么进
    zoning: str                       # 公共/私密、前置/后场怎么分
    experience: str                   # 走进去是什么感受
    cost_note: str                    # 造价影响（方向性，不是报价）
    maintenance: str                  # 维护影响
    risks: Tuple[str, ...] = ()       # 技术风险
    answers: Tuple[str, ...] = ()     # 主要回应的问题主题
    plan_strategy: str = ""           # 映射到 PlanGenerator 策略；"" = 当前平面算法不支持
    suitable_when: Tuple[str, ...] = ()
    tags: Tuple[str, ...] = field(default_factory=tuple)

    @property
    def family_zh(self) -> str:
        return {"linear": "线性", "radial": "环形 / 放射", "cluster": "组团",
                "layered": "分层 / 递进", "hall": "大厅式",
                "courtyard": "院落式"}.get(self.family, self.family)

    def to_dict(self) -> Dict[str, object]:
        return {
            "prototype_id": self.id,
            "profile": self.profile,
            "name": self.name,
            "family": self.family,
            "family_zh": self.family_zh,
            "statement": self.statement,
            "spatial_logic": self.spatial_logic,
            "circulation": self.circulation,
            "daylight": self.daylight,
            "zoning": self.zoning,
            "experience": self.experience,
            "cost_note": self.cost_note,
            "maintenance": self.maintenance,
            "risks": list(self.risks),
            "answers": list(self.answers),
            "answers_zh": [THEME_LABEL.get(a, a) for a in self.answers],
            "plan_strategy": self.plan_strategy,
            "suitable_when": list(self.suitable_when),
            "tags": list(self.tags),
        }


# --------------------------------------------------------------------------
# 住宅 / 公寓 / 别墅
# --------------------------------------------------------------------------
RESIDENTIAL: List[Prototype] = [
    Prototype(
        id="RES-SPINE", profile="residential", name="中部服务脊", family="linear",
        statement="把不该被看见的东西压进一条中脊，剩下的面积才整体、安静。",
        spatial_logic="卫生间、厨房、储藏沿户型中段排成一条脊，两侧都是完整房间，"
                      "每个房间都能直接对外开窗。",
        circulation="脊两侧各走一条短走廊，主卧与次卧互不穿越；访客动线在脊的公共端终止。",
        daylight="所有房间贴外墙，采光面最大化；中脊本身无自然光，必须靠机械排风与人工照明。",
        zoning="公共区在中脊一端，私密区在另一端，脊是两者之间的实体分界。",
        experience="进门先看到一条完整的石质界面，转向后才看见客厅——空间是「转」出来的，不是「一览无余」。",
        cost_note="隔墙总长偏少、管线集中，机电造价通常低于分散布置；但中脊需做吊顶与排风，单项成本上升。",
        maintenance="管线集中在脊内，检修口集中、后期改动便宜；脊体表面材料需耐污。",
        risks=("中脊无窗，排风与防水要求高", "脊体厚度占用使用面积，小户型需复核净宽"),
        answers=("storage", "kitchen", "service", "circulation"),
        plan_strategy="spine_centre",
        suitable_when=("面积 90–200㎡", "厨卫位置可调整", "需要把收纳与设备集中"),
        tags=("minimal", "efficient", "quiet"),
    ),
    Prototype(
        id="RES-BAND", profile="residential", name="动静横分", family="linear",
        statement="会客与休息不共享同一条路径，一条走廊把它们缝在一起。",
        spatial_logic="南侧（或采光最好的一侧）整条做公共区：客厅、餐厨、家政；"
                      "北侧整条做私密区：卧室、书房、卫浴。",
        circulation="一条横向走廊串起北侧房间，公共区完全开放；走廊只在私密端出现。",
        daylight="公共区获得最好的采光面，私密区靠走廊尽端的窗与高窗补光。",
        zoning="一条线分成两半，界线是一条墙 + 一扇门，而不是若干隔墙。",
        experience="从玄关往北走，天花上的灯带一直把人带到主卧门口——路径本身是一条「叙事线」。",
        cost_note="开放区面积占比高，隔墙少；走廊面积占比上升，得房率略降。",
        maintenance="走廊面积大、地面材料用量多；开放区家具布置需长期自律，否则容易显乱。",
        risks=("北侧房间进深偏大时采光不足", "走廊过长会产生「隧道感」"),
        answers=("privacy", "acoustic", "circulation"),
        plan_strategy="band_day_night",
        suitable_when=("进深方向有明确采光差", "公共活动占比高", "需要强隐私分区"),
        tags=("classic", "clear", "family"),
    ),
    Prototype(
        id="RES-LOOP", profile="residential", name="回游环", family="radial",
        statement="让人绕着核心走一圈，而不是走到尽头再折返。",
        spatial_logic="以一个体块（衣帽间、储藏、设备）为中心，四周形成可环绕的通道，"
                      "房间沿环外侧布置。",
        circulation="两条以上路径通向同一房间，任何一处都不再是死胡同；家务动线可独立成环。",
        daylight="环外侧全部可开窗；核心体块无光，正好用来做不需要光的收纳与设备。",
        zoning="公共与私密不是两半，而是环上的两段——可以靠门的位置切换开放程度。",
        experience="同一个空间有两种走法，孩子可以跑圈；空间显得比实际面积大。",
        cost_note="通道面积占比高，实际使用面积减少；但隔墙少、造型少，单方造价可控。",
        maintenance="环形通道意味着更多地面与更多收口；核心体块表面容易被反复触碰，需耐磨。",
        risks=("通道占比过高会挤压房间尺寸", "环形动线对家具布置限制大，需要提前锁定家具尺度"),
        answers=("circulation", "flexibility", "area", "storage", "structure"),
        plan_strategy="",       # 当前平面算法只支持 band / spine
        suitable_when=("有孩子或老人，需要避免长走廊", "面积 100–180㎡", "希望空间显得更大"),
        tags=("playful", "open", "family"),
    ),
    Prototype(
        id="RES-THRESHOLD", profile="residential", name="层次入户", family="layered",
        statement="把「到家」这件事拆成三步：卸下、过渡、进入。",
        spatial_logic="入户后先经过一个可坐、可放、可挂的过渡区（玄关 + 家政），"
                      "再进入公共区；视线在过渡区被挡住，不直接看到客厅。",
        circulation="入户 → 过渡 → 公共 → 私密，四级递进；快递、外卖、访客都停在过渡区。",
        daylight="过渡区可用高窗或玻璃砖引光，不要求直射；公共区仍取最好采光面。",
        zoning="以外来者能到达的最远点划线：访客止于过渡区，家人进入公共区，私密区再一道门。",
        experience="开门不是「暴露」，而是「放下东西、换鞋、喝口水」——回家有缓冲。",
        cost_note="过渡区占用 4–8㎡，需要定制柜体与地面材质转换，木作与铺装成本上升。",
        maintenance="过渡区是脏污最集中的地方，地面需耐污易清洁，柜体需防潮。",
        risks=("小面积项目里过渡区容易被压缩成一条窄走廊", "过渡区无窗时需机械通风"),
        answers=("privacy", "storage", "arrival", "structure"),
        plan_strategy="",
        suitable_when=("有访客频繁上门", "需要家政与快递收纳", "入户直对客厅的户型"),
        tags=("ritual", "calm", "storage"),
    ),
    Prototype(
        id="RES-LIGHT", profile="residential", name="采光脊", family="hall",
        statement="把光做成一条可以走进去的空间，而不是墙上的一扇窗。",
        spatial_logic="沿进深方向切出一条贯穿的采光带（天窗、光井或整面落地），"
                      "房间挂在采光带两侧，进深被光切成两段。",
        circulation="采光带本身就是主通道，走道与光的路径重合，走廊不再是纯交通面积。",
        daylight="天窗或高侧窗把光送到户型中段，解决「进深大、中段黑」的典型问题。",
        zoning="公共区围绕采光带展开，私密区退到采光带尽端。",
        experience="白天不开灯，走到户型中间仍是亮的；天花上有一条真的光。",
        cost_note="天窗、光井与防水构造是主要增量；顶层或可开洞时可行性最高，中间层通常不可行。",
        maintenance="天窗需可清洁、可遮阳；玻璃与密封胶是长期维护点，漏水风险需在构造上解决。",
        risks=("中间层或非顶层无法开天窗——不可行时必须换方向，不能画了再说",
               "天窗带来夏季得热与眩光，需遮阳与低辐射玻璃"),
        answers=("daylight", "experience", "circulation"),
        plan_strategy="",
        suitable_when=("顶层 / 自建房 / 可开洞", "进深大于 12m", "业主明确抱怨「暗」"),
        tags=("bright", "dramatic", "daylight"),
    ),
    Prototype(
        id="RES-FLEX", profile="residential", name="复合可变核心", family="cluster",
        statement="不增加房间，让一间房在不同时段成为不同的房间。",
        spatial_logic="把一个房间做成「可切换」：推拉隔断、翻折床、可变家具，"
                      "白天是书房、晚上是客房、周末是孩子的活动室。",
        circulation="公共区保持一条主路径，可变房间的门位允许两种开法。",
        daylight="可变房间必须贴外墙——没有自然光的房间无法承担长时间的居住功能。",
        zoning="分区不再是固定的，而是靠隔断状态切换；因此隔断的隔声与密封是设计重点。",
        experience="空间会「变」，小面积也能过得宽裕；但每次转换都需要动作，需要业主愿意操作。",
        cost_note="定制可变家具与高气密隔断单价高，占造价比重大；省下的是面积而不是钱。",
        maintenance="机械件是长期维护点（滑轨、五金、密封条），需预留检修与更换条件。",
        risks=("可变隔断隔声通常弱于实体墙，不能用于需要绝对安静的卧室",
               "定制件一旦损坏难以替换，需选通用五金"),
        answers=("area", "flexibility", "storage", "structure"),
        plan_strategy="",
        suitable_when=("面积紧张", "需求会随家庭阶段变化", "业主接受操作成本"),
        tags=("compact", "flexible", "clever"),
    ),
]

# --------------------------------------------------------------------------
# 办公空间
# --------------------------------------------------------------------------
OFFICE: List[Prototype] = [
    Prototype(
        id="OFF-NEIGHBOURHOOD", profile="office", name="邻里组团", family="cluster",
        statement="以团队为一个邻里，而不是以一排工位为一条线。",
        spatial_logic="每个团队占据一个 8–20 人的组团，组团内含工位、小型讨论位与储物，"
                      "组团之间用共享协作区与茶水点分隔。",
        circulation="主通道连接组团入口，组团内部通道不承担穿越；访客动线只在前场。",
        daylight="组团沿外墙布置，进深控制在 6–8m 以内，保证每个工位都能看到窗。",
        zoning="前场（接待、会议、访客）—组团—后场（打印、储物、机房）三段。",
        experience="每个人知道自己属于哪一块，也知道去哪里找人；空间有「街区感」。",
        cost_note="家具与弱电点位密度高于开敞排布；隔断用量中等，改造灵活。",
        maintenance="家具与设备分散，日常维护点多；组团隔断可复用，搬迁成本低。",
        risks=("组团划分过细会降低整体使用弹性", "组团内讨论声会互相干扰，需吸声处理"),
        answers=("collaboration", "focus", "growth", "acoustic"),
        plan_strategy="",
        suitable_when=("20–150 人", "团队边界清晰", "有扩张计划"),
        tags=("team", "structured", "scalable"),
    ),
    Prototype(
        id="OFF-FOCUS-SPINE", profile="office", name="专注脊 + 协作岛", family="linear",
        statement="把安静做成一条脊，把热闹做成几个岛。",
        spatial_logic="一条安静的专注带（不通行、不临茶水）沿一侧布置；协作、会议、电话间"
                      "做成若干岛，集中在另一侧。",
        circulation="主动线走在专注带与协作岛之间，任何人去协作都不穿过专注区。",
        daylight="专注带贴外墙，协作岛靠内侧用玻璃隔断引光。",
        zoning="按声环境分区，而不是按部门分区——这是与邻里组团的根本差别。",
        experience="要安静就往里走，要讨论就在外面；不用戴耳机也能工作。",
        cost_note="玻璃隔断与吸声材料用量大；但工位密度可以更高，单位面积工位成本下降。",
        maintenance="玻璃面积大，清洁频次高；吸声软装需定期更换。",
        risks=("按声环境分区会打散部门，需要组织上接受", "玻璃隔断隔声不足时专注带仍受干扰"),
        answers=("focus", "acoustic", "collaboration"),
        plan_strategy="",
        suitable_when=("研发 / 设计 / 写作等深度工作占比高", "电话与会议频繁"),
        tags=("quiet", "focused", "professional"),
    ),
    Prototype(
        id="OFF-ACTIVITY-BAND", profile="office", name="活动带（图书馆式）", family="linear",
        statement="整个办公区像一间图书馆：一条长桌贯穿，安静由规则与布置共同维持。",
        spatial_logic="一条连续的共享长桌/工作台沿采光面展开，会议与电话间退到内侧小房间，"
                      "储物沿墙成带。",
        circulation="一条主通道与长桌平行，端部设茶水与休息，形成「走到底」的仪式。",
        daylight="长桌贴窗，全天自然光；内侧小房间用玻璃门补光。",
        zoning="开放为主、封闭为辅；封闭空间只给需要保密或高声量的活动。",
        experience="开阔、克制、有秩序；适合以个体产出为主、会议不多的团队。",
        cost_note="隔断极少，单位造价最低；但对声环境与自律要求最高。",
        maintenance="开放空间清洁与整理成本高；长桌与线槽是主要维护对象。",
        risks=("电话多时安静无法维持", "缺少私密空间会让 1v1 谈话无处可去"),
        answers=("focus", "area", "collaboration"),
        # 已实现：前场接待/会议带 + 主通道 + 开放办公 + 专注/服务后场
        plan_strategy="office_cluster",
        suitable_when=("10–40 人", "以个体深度工作为主", "预算敏感"),
        tags=("minimal", "open", "library"),
    ),
    Prototype(
        id="OFF-CORE-FRONT", profile="office", name="服务前置", family="layered",
        statement="把所有「外来」的事情挡在一条线之前，里面只剩工作。",
        spatial_logic="接待、会议、面试、快递、打印全部前置到入口一侧，形成一条服务带；"
                      "办公区在服务带之后，需刷卡进入。",
        circulation="访客动线在服务带内闭环，永不需要进入办公区；员工从服务带侧门进入。",
        daylight="服务带可靠内侧人工照明；办公区保留完整采光面。",
        zoning="按「谁能进」分区，而不是按功能分区——安全与保密优先。",
        experience="访客看到一个完整的前场，员工进入后是一个不受打扰的世界。",
        cost_note="需增加门禁与两道门，前场装修标准高于办公区，单方造价上升。",
        maintenance="门禁与前台需长期人力；前场材料需耐高频使用。",
        risks=("前场面积过大时得房率下降", "单出入口在消防疏散上需专项复核"),
        answers=("privacy", "brand", "arrival", "service"),
        plan_strategy="",
        suitable_when=("访客频繁", "有保密要求", "需要品牌形象前场"),
        tags=("secure", "branded", "professional"),
    ),
]

# --------------------------------------------------------------------------
# 酒店 / 民宿
# --------------------------------------------------------------------------
HOSPITALITY: List[Prototype] = [
    Prototype(
        id="HOS-PROCESSION", profile="hospitality", name="序列式到达", family="linear",
        statement="把入住拆成一段有节奏的路：停、看、等、进。",
        spatial_logic="入口 → 落客 → 大堂（可坐、可看景） → 电梯厅 → 客房层，"
                      "每一段都有明确的视觉终点。",
        circulation="客人动线与行李、后勤完全分离；前台位置决定客人第一眼看到什么。",
        daylight="大堂取最好的景观面，用低照度人工光压住背景，让景观成为唯一亮点。",
        zoning="客区在前、后勤在后、员工通道独立；三者不交叉。",
        experience="到达不是「办手续」，而是一段被设计过的过渡；记忆点在第三眼的景。",
        cost_note="大堂面积与层高是主要成本；景观面开窗与遮阳构造单价高。",
        maintenance="大堂高频使用，材料需耐磨耐污；大面积玻璃清洁成本高。",
        risks=("大堂过大而入住率不足时运营成本难摊平", "前台位置一旦定错，后续改动代价极大"),
        answers=("arrival", "experience", "brand", "operation"),
        plan_strategy="",
        suitable_when=("精品酒店 / 度假民宿", "有景观资源", "客单价中高"),
        tags=("ritual", "hospitality", "scenic"),
    ),
    Prototype(
        id="HOS-COURTYARD", profile="hospitality", name="院落组团", family="courtyard",
        statement="以院落为单位组织客房，让每间房都有一个「外面」。",
        spatial_logic="若干客房围绕一个内院或天井成组，公共设施（泳池、餐厅）作为组团之间的连接。",
        circulation="组团内短路径，组团之间由主路径串联；客人日常路径不穿越其他组团。",
        daylight="院落为内侧房间提供采光与通风，减少对单侧外窗的依赖。",
        zoning="公共（接待、餐饮）—半公共（院落）—私密（客房）三级。",
        experience="从公共区走进院落，声音与视线同时安静下来；每间房都有独立的户外感。",
        cost_note="院落占用容积率但不产生客房面积，单房造价上升；外墙面积增加，围护成本高。",
        maintenance="院落排水、绿化与防蚊是长期维护点；外墙与屋面节点多。",
        risks=("院落尺度不当会变成「天井」，采光与通风都不到位",
               "多雨地区需重点解决排水与连廊"),
        answers=("experience", "daylight", "privacy", "outdoor"),
        plan_strategy="",
        suitable_when=("低层 / 独栋 / 有地", "度假型产品", "客房数 10–60"),
        tags=("resort", "courtyard", "quiet"),
    ),
    Prototype(
        id="HOS-BOH-SPINE", profile="hospitality", name="后勤脊分离", family="layered",
        statement="客人永远看不到布草车，员工永远不用穿过大堂。",
        spatial_logic="一条独立的后勤脊（布草、备餐、垃圾、员工）贯穿楼层，"
                      "服务口开在客房走廊的侧端而不是正面。",
        circulation="员工动线与客人动线在平面上完全分离，只在服务口短暂交汇。",
        daylight="后勤区不需要自然光，可靠内侧布置，把外墙让给客房。",
        zoning="按「谁使用」分区：客区 / 服务区 / 后勤区，三条动线互不穿越。",
        experience="客人感知不到运营的存在——这正是高端住宿体验的一部分。",
        cost_note="独立后勤通道增加面积但不产生收入；服务口与隔声门是增量成本。",
        maintenance="后勤区磨损快，需耐磨地面与防撞墙面；垃圾与布草流线需每日管理。",
        risks=("后勤面积被压缩时服务效率立刻下降", "服务口位置不当会造成走廊噪声"),
        answers=("operation", "service", "privacy"),
        plan_strategy="",
        suitable_when=("客房数 ≥30", "有餐饮配套", "服务标准较高"),
        tags=("operational", "efficient", "backofhouse"),
    ),
]

# --------------------------------------------------------------------------
# 餐饮 / 商业零售
# --------------------------------------------------------------------------
RETAIL: List[Prototype] = [
    Prototype(
        id="RET-THEATRE", profile="retail", name="明档剧场", family="hall",
        statement="把后厨的一部分推到台前，让制作过程成为可观看的内容。",
        spatial_logic="明档/操作台沿客流主视线布置，后厨在其后，前场座位围绕明档展开。",
        circulation="点单 → 取餐 → 就座形成单向流，避免取餐与就座对冲。",
        daylight="前场取自然光，明档用重点照明突出食材与动作；后厨人工光为主。",
        zoning="前场（客座、明档）/ 后场（粗加工、洗碗、仓储）以一条线分开。",
        experience="看到食物被做出来，等待变成观看；空间有了「现场感」。",
        cost_note="明档需要排烟、隔油与不锈钢台面，单位造价高于封闭后厨；设备外露也提高标准。",
        maintenance="明档玻璃与台面需高频清洁；油烟处理是长期维护重点。",
        risks=("明档的油烟与噪声会直接影响客座区", "排烟路径一旦不合理，后续整改代价极高"),
        answers=("experience", "brand", "operation", "kitchen"),
        plan_strategy="",
        suitable_when=("客单价中高", "以现场制作为卖点", "有排烟条件"),
        tags=("theatre", "food", "branded"),
    ),
    Prototype(
        id="RET-LOOP", profile="retail", name="环形店铺动线", family="radial",
        statement="让客人绕一圈看完全部商品，而不是走到尽头就掉头。",
        spatial_logic="中央陈列或收银作为核心，货架沿环外侧布置，形成一条闭合的回游路径。",
        circulation="单向环形，入口与出口分离或错位，避免人流对冲。",
        daylight="沿街面全开放，环内侧靠重点照明补足；核心体块可作为试衣/仓储。",
        zoning="陈列（外环）—体验（核心周边）—收银（出口前）—仓储（核心内）。",
        experience="每一寸面积都被走过；客人不会漏掉某个角落。",
        cost_note="陈列道具与照明密度高；环形动线需要更多地面材料。",
        maintenance="道具与灯具数量多，维护点分散；地面高频磨损。",
        risks=("环形动线在面积过小时会显得局促", "消防疏散需复核两个出口"),
        answers=("operation", "area", "brand"),
        plan_strategy="",
        suitable_when=("零售 / 便利店 / 集合店", "面积 80–400㎡", "SKU 较多"),
        tags=("retail", "circulation", "commercial"),
    ),
    Prototype(
        id="RET-DAYPART", profile="retail", name="时段分区", family="layered",
        statement="同一个店，上午是咖啡，中午是快餐，晚上是酒吧——靠分区与灯光切换。",
        spatial_logic="把店铺沿进深分成 2–3 个可独立开放的区段，各段有独立入口或可关闭的隔断，"
                      "灯光与家具按区段分别控制。",
        circulation="主入口固定，区段之间可开可合；不同时段封闭不用的区段以降低运营成本。",
        daylight="沿街段白天全开，深段用可调光人工照明承担夜间氛围。",
        zoning="按时段与运营单元分区，而不是按功能分区。",
        experience="同一个地址在不同时间来是不同的店——复购的理由变多。",
        cost_note="分区意味着更多隔断、更多独立机电控制；但可以按段开业，降低人力与能耗。",
        maintenance="多套控制逻辑增加运维复杂度；隔断五金是主要维护点。",
        risks=("分区过多会让空间显得零碎", "消防与营业执照对分区有约束，需提前确认"),
        answers=("operation", "flexibility", "brand"),
        plan_strategy="",
        suitable_when=("临街铺面", "全天候经营", "希望提高坪效"),
        tags=("flexible", "commercial", "daypart"),
    ),
]

# --------------------------------------------------------------------------
# 展厅 / 文化与公共空间
# --------------------------------------------------------------------------
EXHIBITION: List[Prototype] = [
    Prototype(
        id="EXH-PROMENADE", profile="exhibition", name="叙事漫步", family="linear",
        statement="把展览编成一条有起伏的路，观众按顺序走完就理解了全部内容。",
        spatial_logic="按叙事章节分段，每段有独立的空间尺度与光环境，段与段之间用收窄或转折过渡。",
        circulation="单向主路径，允许局部回看但不能跳过；出口设在最后一段。",
        daylight="可控段用天光或高侧窗，重点展品用人工光；避免直射日光损伤展品。",
        zoning="序厅—主展区（分章）—尾厅—文创/出口，四段递进。",
        experience="空间本身在讲故事；观众的情绪随尺度与亮度变化。",
        cost_note="分段意味着更多隔墙与更多独立灯光回路，造价高于通厅布置。",
        maintenance="灯光与多媒体设备多，维护频次高；展陈更新需可拆装。",
        risks=("叙事顺序被打乱时体验失效", "分段的隔墙影响消防疏散与视线通透"),
        answers=("exhibit", "experience", "circulation"),
        plan_strategy="",
        suitable_when=("有明确叙事主题", "面积 300㎡ 以上", "参观时长 20 分钟以上"),
        tags=("narrative", "museum", "sequential"),
    ),
    Prototype(
        id="EXH-BOX", profile="exhibition", name="黑盒 / 白盒并置", family="cluster",
        statement="需要沉浸的进黑盒，需要看清的进白盒，二者并置互为对照。",
        spatial_logic="黑色沉浸厅（可控光、可投影）与白色展厅（均匀漫射光）并列，"
                      "中间用过渡廊连接，让眼睛有时间适应。",
        circulation="两厅可独立开放，也可串联；过渡廊承担讲解与停留。",
        daylight="白盒用天光或均匀漫射，黑盒完全遮光；过渡区低照度。",
        zoning="按光环境分区，而不是按内容分区。",
        experience="从黑到白的明暗切换本身就是一次展览。",
        cost_note="黑盒需要遮光与吸声构造，白盒需要均匀天光，两者单价都高于普通展厅。",
        maintenance="遮光帘与投影设备是维护重点；白盒天窗需清洁。",
        risks=("过渡廊过短会造成眩目与不适", "黑盒的消防疏散与通风需专项设计"),
        answers=("exhibit", "experience", "daylight"),
        plan_strategy="",
        suitable_when=("含多媒体 / 沉浸式内容", "展品对光敏感度差异大"),
        tags=("immersive", "contrast", "museum"),
    ),
    Prototype(
        id="EXH-ISLAND", profile="exhibition", name="岛式自由参观", family="cluster",
        statement="没有唯一正确的路线，观众按兴趣跳着看。",
        spatial_logic="若干独立展岛散布在开放大厅内，岛之间留出 2.4m 以上的通行宽度。",
        circulation="多路径、无强制顺序；主入口与出口各一处，视线可及大部分展岛。",
        daylight="大厅整体采光，展岛用重点照明；避免在展品表面形成直射高光。",
        zoning="开放大厅 + 若干半围合展岛；不设固定隔墙。",
        experience="自由、轻松、适合短时参观与社交；也便于举办活动。",
        cost_note="无隔墙、可复用展具，单位造价最低；但对展具设计质量要求高。",
        maintenance="展具可移动，更新成本低；大厅地面磨损集中。",
        risks=("缺少叙事时容易变成「摆摊」", "声环境难以控制，人多时嘈杂"),
        answers=("exhibit", "flexibility", "experience"),
        plan_strategy="",
        suitable_when=("企业展厅 / 规划馆 / 临展", "参观时长 15 分钟内", "需兼办活动"),
        tags=("flexible", "open", "event"),
    ),
]

# --------------------------------------------------------------------------
# 新建建筑项目
# --------------------------------------------------------------------------
ARCHITECTURE: List[Prototype] = [
    Prototype(
        id="ARC-COURTYARD", profile="architecture", name="合院式", family="courtyard",
        statement="用一个院子把房子围起来，让每一间房都朝向内部。",
        spatial_logic="建筑沿基地周边布置，中心留院；主要房间朝向院内，服务空间靠外侧。",
        circulation="环绕院落的回廊串联各功能，雨天不需打伞。",
        daylight="院落为内侧房间提供采光与通风；外立面可开窗面积减少，利于节能。",
        zoning="外（服务、辅助）—院（公共、半公共）—内（私密）。",
        experience="进门穿院，四季变化成为日常背景；空间有「内向的安定感」。",
        cost_note="外墙周长增加，围护成本上升；院落占用容积率。",
        maintenance="院落排水、绿化与外墙防水是长期维护点。",
        risks=("地块过小或退界受限时院落无法成立", "北方寒冷地区院落冬季使用率低"),
        answers=("outdoor", "daylight", "privacy", "experience"),
        plan_strategy="",
        suitable_when=("地块方正", "低层", "注重内向生活"),
        tags=("courtyard", "introverted", "traditional"),
    ),
    Prototype(
        id="ARC-BAR-PODIUM", profile="architecture", name="板楼 + 裙房", family="layered",
        statement="把公共功能铺在底层，把重复的单元叠在上面。",
        spatial_logic="裙房 1–3 层承担公共、商业、配套；塔楼/板楼承担主要使用单元，"
                      "两者用独立的垂直交通分开。",
        circulation="公共人流与住户/办公人流在不同标高分流，互不干扰。",
        daylight="板楼进深控制在 14m 以内保证双面采光；裙房用天窗与光井补光。",
        zoning="按标高分层：公共在下、半公共居中、私密在上。",
        experience="从街道进入是热闹的，进入单元后立刻安静。",
        cost_note="结构体系在裙房与塔楼交界处转换，结构造价上升；但容积率高，单方成本可控。",
        maintenance="裙房屋面与设备平台是维护重点；多业态带来管理界面复杂。",
        risks=("结构转换层需专项论证", "多业态的消防与疏散需分别核算"),
        answers=("operation", "structure", "area", "service"),
        plan_strategy="",
        suitable_when=("城市地块", "容积率要求高", "含商业或公共配套"),
        tags=("urban", "mixeduse", "dense"),
    ),
    Prototype(
        id="ARC-SPLIT", profile="architecture", name="体量拆分", family="cluster",
        statement="把一个大体量拆成几个小体量，让建筑与场地一起呼吸。",
        spatial_logic="按功能或朝向把建筑拆成 2–4 个体量，体量之间用连廊、平台或缝隙连接。",
        circulation="户外路径连接各体量，形成室内外交替的体验。",
        daylight="每个体量都能获得多面采光；体量之间的缝隙成为采光与通风通道。",
        zoning="按体量分区，而不是按楼层分区。",
        experience="建筑不再是一个盒子，而是一组有关系的房子。",
        cost_note="外墙面积与屋面面积增加，围护与防水成本上升；但施工可分区分期。",
        maintenance="多处屋面与天沟，防水维护点增多；室外连廊需考虑防滑与排水。",
        risks=("体量过散会削弱整体识别度", "缝隙过窄会成为难维护的消极空间"),
        answers=("outdoor", "daylight", "experience", "structure"),
        plan_strategy="",
        suitable_when=("场地较大或地形有高差", "功能差异明显", "注重场所感"),
        tags=("massing", "landscape", "articulated"),
    ),
]

#: 项目类型 → 原型集。键与 `intake.profiles` 的 profile id 一致。
PROTOTYPES: Dict[str, List[Prototype]] = {
    "residential": RESIDENTIAL,
    "office": OFFICE,
    "hospitality": HOSPITALITY,
    "retail": RETAIL,
    "exhibition": EXHIBITION,
    "architecture": ARCHITECTURE,
}


def for_profile(profile_id: str) -> List[Prototype]:
    """All prototypes of a project type. Unknown types get no prototypes, not guesses."""
    return list(PROTOTYPES.get(profile_id or "", ()))


def get(prototype_id: str) -> Optional[Prototype]:
    for items in PROTOTYPES.values():
        for p in items:
            if p.id == prototype_id:
                return p
    return None


def families(profile_id: str) -> List[str]:
    return sorted({p.family for p in for_profile(profile_id)})


def count() -> int:
    return sum(len(v) for v in PROTOTYPES.values())


__all__ = ["Prototype", "PROTOTYPES", "THEME_LABEL",
           "for_profile", "get", "families", "count"]
