"""设计推敲层 —— 从「挑一个原型」到「推敲出一个策略」。

## 为什么需要这一层

`prototypes.py` 的 22 个原型回答的是「房间怎么排」。它有三个上限：

1. **按项目类型分组，不按主导专业**。三层别墅落在 `residential`，于是拿到的
   是公寓式的横向分区与中脊——对一栋要谈体量、退台、院墙、朝向的房子，这些
   策略根本不回答「房子怎么站在地上」。
2. **内容是固定句子**。选定原型之后，`statement`/`spatial_logic`/`experience`
   原样抄进方案。同一个原型用在两个项目上，方案就一模一样，只差风格。
3. **没有景观这一类**。纯庭院项目只能借住宅原型，输出的是房间布局，不是园子。

这一层补的是**推敲**：给定场地、层数、业主原话与专业主导，提出几种
**组织逻辑互不相同**的策略，每种策略都要回答六个问题（见 `SIX_QUESTIONS`），
并带上前提、代价与「在图上怎么核验」。

原型库保留，作为没有专业策略时的兜底——它的 22 条仍然是有效的经验集合。

## 一条策略由什么构成

不是形容词，是五样能被画出来的东西：

* `parti` —— 一句话能画成一根线的组织逻辑（谁围合谁、谁穿过谁）；
* `massing` / `section` / `facade`（建筑）或 `zones` / `path` / `water`（景观）；
* `sequence` —— 人走进去每一段经历到什么，每段必须挂一个可指认的手法；
* `technical` —— 哪些地方必须结构与机电配合，不配合就做不成；
* `tradeoffs` —— 这个策略拿什么换什么。

## 边界

* **不虚构尺寸与工程结论。** 没有实测就只谈关系与比例，并且在输出里标精度。
* **不宣称执业资格。** 这里的方法参考了公开的建筑设计方法与国内一级注册建筑师、
  RIBA 等体系中的通用设计判据，但系统本身不是注册主体，需要持证专业人员复核。
* **同一专业的三套策略组织逻辑必须不同。** 换材料、换风格、换措辞不算换方案。

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

# --------------------------------------------------------------------------
# 六个必须回答的问题
# --------------------------------------------------------------------------
#: 由 S2 输出，缺一个就不算概念成立。键名与 `build_strategies` 的返回值一致。
SIX_QUESTIONS: Tuple[Tuple[str, str], ...] = (
    ("key_opportunity", "这个项目最有价值的设计机会是什么"),
    ("why_this_strategy", "为什么采用这个空间或形态策略"),
    ("experience", "人进入空间会经历什么"),
    ("light_view_proportion_material", "光线、视线、比例和材料如何配合"),
    ("integration", "建筑、室内、景观之间如何形成整体"),
    ("technical_coordination", "哪些技术条件需要结构与机电协助"),
)


@dataclass(frozen=True)
class Strategy:
    """一条可推敲的设计策略。字段全部要求能被指出、被反驳。"""

    id: str
    discipline: str                  # architecture / interior / landscape
    name: str
    family: str                      # 图解用的空间家族，沿用既有六值
    role: str                        # A 稳妥 / B 特色 / C 平衡
    statement: str                   # 一句话主张
    parti: str                       # 组织逻辑（能画成一根线）
    opportunity: str                 # 它去抓的那个设计机会
    massing: str                     # 建筑：体量；室内：空间重组；景观：分区
    section: str                     # 建筑：楼层与剖面；室内：标高与净高；景观：竖向
    facade: str                      # 建筑：虚实与开窗；室内：界面；景观：边界
    circulation: str
    daylight: str
    materials_logic: str             # 材料怎么配合，不是材料清单
    sequence: Tuple[Tuple[str, str, str], ...]   # (段落, 经历, 手法 id)
    technical: Tuple[str, ...]
    tradeoffs: Tuple[str, ...]
    risks: Tuple[str, ...]
    cost_note: str
    maintenance: str
    serves: Tuple[str, ...]          # 回应的信号键（与 ctx.signals 对齐）
    keywords: Tuple[str, ...]        # 与业主原话匹配的词
    requires: Tuple[str, ...]        # 成立前提；不满足要扣分并如实说明
    precedent: Tuple[str, ...]       # 案例文本里能佐证这套手法的词
    zones: Tuple[Tuple[str, str], ...] = ()      # 景观：分区与占比
    water: str = ""                              # 景观：水景做法
    planting: str = ""                           # 景观：植物层级与季相
    paving: str = ""                             # 景观：铺装
    massing_kind: str = ""                       # 体量图解分型
    logic_key: str = ""                          # 组织逻辑标识，用于互斥
    #: 楼层怎么用（自下而上）。建筑的「楼层空间」不是把功能平均分到各层，
    #: 而是决定哪一层承担公共性、哪一层承担安静。空表示该策略不按层组织。
    levels_program: Tuple[str, ...] = ()
    #: 是否以**水面为主体**。业主明确要水景时，只有这一项能证明"水给足了"：
    #: 一条浅渠与一池静水都叫"有水"，但对业主的承诺完全不同。
    strong_water: bool = False
    #: 是否能映射到现有平面算法（`planner` 支持的策略）。空表示**不能**。
    #:
    #: 这个字段只有一种合法填法：算法真的实现了同一套组织逻辑。目前只有
    #: 「一条服务脊」= `spine_centre`（算法做的就是服务脊两侧留完整开间）。
    #: 其余策略硬填一个策略名，等于声称算法能落地一个它做不到的布局。
    plan_strategy: str = ""
    #: 这套策略适用的项目类型（`intake.profiles` 的 profile id）。空表示不限。
    #:
    #: 必要而非冗余：室内四套写的是**住宅大平层**的空间重组（服务脊、回游核心、
    #: 明暗两段、盒中之盒）。把它们套到办公或酒店项目上，会得到一间有主卧的
    #: 办公室。类型不匹配时回退到该类型的空间原型，那里才有办公/酒店的策略。
    profiles: Tuple[str, ...] = ()

    def to_prototype(self) -> Dict[str, Any]:
        """折成下游认得的 `spatial_prototype` 形状。

        下游（图解、G2、S3 交接、比较）读的是 `prototype_id` / `family` /
        `spatial_logic` / `plan_strategy` 这几个键。这里如实填，并加
        `deliberated: true` 与新策略自己的字段，**不冒充原型**。
        """
        return {
            "prototype_id": self.id,
            "profile": self.discipline,
            "name": self.name,
            "family": self.family,
            "family_zh": {"linear": "线性", "radial": "环形 / 放射", "cluster": "组团",
                          "layered": "分层 / 递进", "hall": "大厅式",
                          "courtyard": "院落式"}.get(self.family, self.family),
            "statement": self.statement,
            "spatial_logic": self.parti,
            "circulation": self.circulation,
            "daylight": self.daylight,
            "zoning": self.massing,
            "experience": self.sequence[-1][1] if self.sequence else self.statement,
            "cost_note": self.cost_note,
            "maintenance": self.maintenance,
            "risks": list(self.risks),
            "answers": list(self.serves),
            "answers_zh": [],
            "plan_strategy": self.plan_strategy,
            "plan_strategy_note": ("可直接交给 S3 平面算法" if self.plan_strategy
                                   else "现有平面算法不覆盖这套组织逻辑，须专用深化"),
            "suitable_when": list(self.requires),
            "tags": ["deliberated", self.discipline],
            "deliberated": True,
            "discipline": self.discipline,
            "massing_kind": self.massing_kind,
            "logic_key": self.logic_key or self.id,
        }


# --------------------------------------------------------------------------
# 建筑主导：体量、楼层、虚实、院与水
# --------------------------------------------------------------------------
ARCHITECTURE: List[Strategy] = [
    Strategy(
        id="DLB-ARC-COURT",
        discipline="architecture", name="院中取院", family="courtyard",
        role="A",
        statement="先把房子做成一圈墙，再从中间把院挖出来——院不是房子的外面，是房子的中心。",
        parti="完整体量沿退界围合，中间减掉一块做院；房子朝院开，朝街收。",
        opportunity="把「私密」和「通透」放进同一个动作：对外收住，对内全开。这一对诉求"
                    "如果分开做，必然一边妥协；围合加内院是少数能让两者同时成立的几何。",
        massing="减法体量：从不超过退界的完整体量里减掉院、减掉入口凹口。建筑沿院的两到三面"
                "围合，剩下一面做成院墙——院墙与主体之间留一道缝，用来走排水与设备。",
        section="院做两层通高（三层项目里院到二层顶），第三层在院上方收窄成一个采光井；"
                "楼梯沿院边折上，每上一跑都能看见院，竖向的每一层都还有「外面」。",
        facade="临街面开窗少而深，窗洞进深做到 300mm 以上；院内面几乎全玻璃。"
               "虚实按朝向反过来：外侧七成实、内侧七成透。这不是造型选择，是私密性与"
               "采光面分配的结果。",
        circulation="院是环形的枢纽：门厅、客厅、餐厨、楼梯都从院边进入，回到院就回到"
                    "所有房间的入口；家务与快递走院墙外侧的独立入口，不进院。",
        daylight="院给每一层的同一侧提供侧向漫射光，进深不再依赖单面开窗；三层靠采光井"
                 "顶部补光。院越大，内侧房间越亮，但外墙周长也越长。",
        materials_logic="外侧用耐候的实面材料（砌体、清水混凝土、深色金属），内侧用暖色"
                        "木与浅色矿物面——材料跟着「外/内」这对关系走，而不是跟着风格走。",
        sequence=(
            ("接近", "沿院墙走，只看见一段高度一致的实墙，看不出房子有多大", "threshold"),
            ("卸下", "墙后的门廊，一步之隔，风雨被挡住", "threshold"),
            ("第一眼", "进院：视线先落在静水面上，房子在水的另一侧", "framing"),
            ("转折", "沿院边走到客厅入口，天花压低，水在侧后方", "compression_release"),
            ("主空间", "客厅两层通高，院墙与水面停在视线高度", "prospect_refuge"),
        ),
        technical=("院四周要形成闭合的抗震体系，院的缺口不能把结构切成两半",
                   "院侧通高玻璃的热工与遮阳必须一次做对，后补代价高",
                   "院内排水、溢流与院墙防水是长期渗漏点",
                   "院墙与主体之间需设变形缝与独立基础"),
        tradeoffs=("外墙周长通常增加一成半到两成半，围护造价上升",
                   "院占容积率但不产生室内面积",
                   "临街面封闭会牺牲一部分街道景观与采光"),
        risks=("地块过小或退界受限时院退化成天井", "院侧大面积玻璃的夏季得热与眩光"),
        cost_note="外墙、通高玻璃与院墙是主要增量；院本身不产生面积，等于用容积率换空间质量。",
        maintenance="院的排水、防水与落叶清理是长期维护项；水景需循环与除藻。",
        serves=("privacy", "daylight", "experience", "outdoor", "arrival"),
        keywords=("私密", "采光", "通透", "仪式感", "庭院", "院子", "水景"),
        requires=("有独立地块", "退界允许围合", "层数不少于两层"),
        precedent=("courtyard", "inner garden", "patio", "enclosed"),
        levels_program=("公共：门厅、客厅、餐厨，三面朝院开",
                       "家庭：卧室与起居，沿院边排布",
                       "主卧与书房，靠采光井补顶部光"),
        profiles=("residential", "architecture"), massing_kind="courtyard_carved", strong_water=True, logic_key="perimeter_court",
    ),
    Strategy(
        id="DLB-ARC-TERRACE",
        discipline="architecture", name="逐层退台", family="layered",
        role="B",
        statement="三层不做齐平叠：每层向后退一个进深，退出来的就是上一层的院子。",
        parti="剖面是主要工具：每层收进，把「院」从地面搬到三个不同的标高上。",
        opportunity="地块进深不够做完整院落时，室外空间可以从平面搬到剖面——每层都有"
                    "自己的露台，而且不额外占地。这是用地受限时唯一还能给出「每层有院」的做法。",
        massing="堆叠加逐层收进：首层最满，二层退一跨，三层再退一跨。退出来的平台"
                "就是上一层的室外，栏杆与挑板一次成型。",
        section="退台进深决定下一层的采光与遮阳：退进 1.8m 以上才坐得住人，退进 2.5m"
                "以上才能种小乔木。每层的净高按用途定，不统一一个数。",
        facade="层间挑板成为水平线索，同时是遮阳与雨棚——南向挑深、北向挑浅，"
               "立面因此自然不对称，不需要额外造型。",
        circulation="竖向交通贴北侧，每一层的到达点都先经过一个露台再进门；"
                    "室内动线短，室外动线长——上下楼也是一次出门。",
        daylight="每层都能得到直射光，上一层挑板给下一层遮阳；进深方向靠露台补光，"
                 "避免出现只有一面临空的深房间。",
        materials_logic="挑板底做浅色（把光反射进下层），栏板用通透材料不挡视线；"
                        "外墙实体部分与挑板同材质，让退台看起来是一个动作而不是三个。",
        sequence=(
            ("接近", "从最低处进入，房子在头顶逐层后退，人在屋檐下", "threshold"),
            ("卸下", "首层门厅压低，净高只到 2.6m", "compression_release"),
            ("第一眼", "上到二层，第一次越过退台看到外面——景是横着进来的", "framing"),
            ("转折", "再上一层，露台的方向换了九十度，光从另一侧来", "rhythm"),
            ("主空间", "顶层起居三面都是室外，天花抬高一次", "prospect_refuge"),
        ),
        technical=("退台处的梁柱转换或悬挑必须专项计算，悬挑超出常规范围要加支撑",
                   "上层露台排水不得落到下层活动面，需做有组织排水",
                   "栏杆高度、防水收头与女儿墙泛水是常见失败点",
                   "逐层收进会改变各层刚度，抗震需整体建模"),
        tradeoffs=("结构成本高于齐平叠层",
                   "退台减少每层可用面积，得房率下降",
                   "下层进深采光受挑板遮挡，需要靠浅进深补偿"),
        risks=("悬挑过大时结构代价超过收益", "多层退台的外墙与屋面节点数量成倍增加"),
        cost_note="结构转换与悬挑是主要增量；屋面与外墙节点多，防水与收口人工占比高。",
        maintenance="多处屋面与天沟，落叶与排水口需定期清理；栏杆与玻璃需检查固定件。",
        serves=("daylight", "outdoor", "experience", "structure"),
        keywords=("露台", "退台", "层次", "采光", "视野", "景"),
        requires=("层数不少于两层", "有可看的景或朝向", "结构可做悬挑或转换"),
        precedent=("terrace", "stepped", "split-level", "level change", "hillside"),
        levels_program=("公共与车库，占地最满",
                       "家庭起居与儿童，第一次退台",
                       "主卧与露台，三面都是室外"),
        profiles=("residential", "architecture"), massing_kind="stepped", logic_key="sectional_step",
    ),
    Strategy(
        id="DLB-ARC-FLOAT",
        discipline="architecture", name="架空的水院", family="hall",
        role="B",
        statement="把地面层让给院和水，主体量抬起来——水从房子下面穿过去。",
        parti="首层退让成柱与楼梯，上部体量完整；院与水在地面连续，不被建筑打断。",
        opportunity="水景如果只是一块池子，它永远是房子旁边的装饰。让它从建筑底部穿过，"
                    "水就成了路径与结构的一部分——这是只有架空才能给的空间经验。",
        massing="减法加悬浮：地面层退到只剩结构柱、楼梯与一小块门厅；二层以上是完整体量，"
                "出挑在院与水之上。",
        section="剖面上做「压—放」：首层净高压到 2.6–3.0m，二层通高抬到 6m 以上。"
                "压低让水面与柱列成为主角，抬高把景一次放出来。",
        facade="下虚上实：首层玻璃或完全架空，上部用实体材料。重与轻的对比来自结构逻辑，"
               "不是贴上去的造型。",
        circulation="从水边的石板走近，穿过架空层才到门厅；上楼之后视线越过树冠。"
                    "回家这条路本身就是一次从水面到高处的移动。",
        daylight="首层靠水面反射光与侧光，比直接开窗更柔；二层四面采光，进深方向不缺光。",
        materials_logic="首层用能受潮的材料（石材、混凝土、防腐木），上部用轻质干挂；"
                        "材料的分界正好落在楼板位置。",
        sequence=(
            ("接近", "先听到水声，再看到水面从房子下面穿过去", "borrowed_view"),
            ("卸下", "架空层下的门厅，头上有楼板，前面是水", "compression_release"),
            ("第一眼", "站在水面上方的石板上，房子在头顶，天在两侧", "framing"),
            ("转折", "上楼，视线逐渐抬过树冠", "compression_release"),
            ("主空间", "二层起居，院与水面在脚下展开", "prospect_refuge"),
        ),
        technical=("上部体量的柱网转换与抗震是首要问题，转换层的代价要早算",
                   "首层防潮、防洪与地面返潮处理",
                   "水面与建筑基础的防水必须连续，不能断开",
                   "水面蒸发会影响室内湿度，需通风与除湿配合"),
        tradeoffs=("首层使用效率低，等于用面积换空间经验",
                   "结构造价在几种策略里最高",
                   "水面带来儿童安全与日常维护的长期责任"),
        risks=("架空层在寒冷地区会成为冷桥与风道", "水面维护不到位会变成负担而非景观"),
        cost_note="转换结构、防水与水面处理三项叠加，单方造价明显高于常规做法。",
        maintenance="水面循环、除藻、清落叶；架空层地面防潮需长期观察。",
        serves=("experience", "outdoor", "arrival", "daylight", "structure"),
        keywords=("水景", "架空", "悬浮", "仪式感", "高级"),
        requires=("有独立地块", "结构可做转换", "预算允许增量构造"),
        precedent=("pilotis", "floating", "reflecting", "pond", "stilt"),
        levels_program=("架空门厅、水院与家务，压低了净高",
                       "起居与餐厨，视线越过树冠",
                       "卧室，退到最安静的一侧"),
        profiles=("residential", "architecture"), massing_kind="floating", strong_water=True, logic_key="ground_released",
    ),
    Strategy(
        id="DLB-ARC-WINGS",
        discipline="architecture", name="双翼夹院", family="linear",
        role="C",
        statement="房子拆成两翼，中间留一条带水的院；院是两翼之间唯一的路。",
        parti="两个长条体量平行，中间是院；一翼公共，一翼私密，院是连接也是分界。",
        opportunity="用一条院同时办三件事——采光、私密、把水变成每天必经的一段路。"
                    "当地块是狭长形、做不出中心院时，这条「缝」是最有效的替代。",
        massing="加法：两个体量加中间的负空间。两翼高度可以不同，院端头用一堵片墙收住"
                "视线，院不至于一眼望穿。",
        section="院比两侧地面低 150–300mm，水在最低处；两翼首层都朝院开，二层靠外墙采光。"
                "剖面上一眼能看出「低—高—低」的关系。",
        facade="临街面两翼都实，院内面都透；院端头的片墙是唯一的实面，用来挡住巷子里的视线。",
        circulation="从两翼之间的缝进入，门厅在缝里；沿院走到哪一翼都行，水在一侧。"
                    "访客停在公共翼，家人穿过院去私密翼。",
        daylight="两翼都能双面采光；院给内侧补光。院的宽度决定补光效果，窄于 4m 就退化成通道。",
        materials_logic="两翼用同一套材料，院的地面单独用湿区材料（石材、砾石）；"
                        "材料在这里标记「室内/室外」，比标记风格更有效。",
        sequence=(
            ("接近", "沿长向立面走，看到两翼之间的一道缝", "threshold"),
            ("卸下", "进入缝里的门厅，两侧都是墙", "compression_release"),
            ("第一眼", "穿过门厅，院在两侧展开，水在一侧", "framing"),
            ("转折", "沿院走，水面低下去，脚边是石", "prospect_refuge"),
            ("主空间", "公共翼尽端的客厅，院与水在侧前方", "borrowed_view"),
        ),
        technical=("两翼之间的连廊结构与防水需单独处理",
                   "下沉院要做挡土与排水，不能靠自流排到市政",
                   "水面距外墙的防水收头是关键节点",
                   "两翼分开后，消防疏散需分别满足"),
        tradeoffs=("两翼意味着更多外墙与屋面，围护成本高于单体量",
                   "院过窄会变成通道，过宽则两翼联系变弱",
                   "狭长地块上的两翼容易形成「一线天」的压迫感"),
        risks=("院宽不足时采光与体验同时失效", "两翼分期施工时接口难处理"),
        cost_note="外墙与屋面面积增加是主要增量；下沉院另需挡土与排水构造。",
        maintenance="院的排水与水面维护；两翼之间的连廊是渗漏高发处。",
        serves=("privacy", "daylight", "outdoor", "circulation", "area"),
        keywords=("狭长", "进深", "水景", "私密", "采光", "院子"),
        requires=("地块长宽比明显", "有独立地块", "宽度允许两翼加院"),
        precedent=("linear", "axis", "courtyard", "water", "wing"),
        levels_program=("公共翼：客厅与餐厨；私密翼：客房",
                       "公共翼：书房；私密翼：主卧与次卧",
                       "最安静的一端，收在片墙之后"),
        profiles=("residential", "architecture"), massing_kind="twin_wings", strong_water=True, logic_key="twin_wing",
    ),
]


# --------------------------------------------------------------------------
# 室内主导：既建成，只做空间重组、界面、光与材料
# --------------------------------------------------------------------------
INTERIOR: List[Strategy] = [
    Strategy(
        id="DLB-INT-SPINE",
        discipline="interior", name="一条服务脊", family="linear",
        role="A",
        statement="把不该被看见的东西压进一条脊，剩下的开间才可能真的连成一片。",
        parti="厨房、卫浴、储藏、洗衣沿中段排成一条脊；脊两侧留完整开间，不再切小房间。",
        opportunity="大平层的通透不是「少隔墙」，而是「把杂物集中到一个地方」。集中之后，"
                    "剩下的空间才可能真的连续——否则开放只是把乱摊开。",
        massing="一条脊宽 1.8–2.4m（含管井），每段功能各有独立门；脊两端各留一个开口，"
                "形成两条可回游的路径，走廊面积被脊吸收。",
        section="脊体做到吊顶齐平（不高出梁底），其余区域保留结构净高；脊内管线走在"
                "吊顶里，出口集中，检修口连成一条线。",
        facade="既有外围护不动。室内界面只做两件事：脊体做成整面同材质，成为空间里唯一的"
               "「重」元素；其余墙面留白，让光和家具承担内容。",
        circulation="入户先被一道矮柜挡一下视线，转过柜端才看见客餐厅；主卧在脊的另一端，"
                    "要穿过一道门。公共与私密之间只隔这一道门，不是一条走廊。",
        daylight="两侧完整开间直接对外开窗，采光在连续界面上展开；脊内的卫浴、储藏、"
                 "家务无窗，靠机械排风——这是这套策略的代价，不是遗漏，S3 须逐间核对"
                 "实际采光面，不能默认「所有房间都亮」。",
        materials_logic="脊体用一种材料包到顶（石材、木饰面或微水泥），四面收口一致；"
                        "其余界面做背景。主材不超过三种，避免「高级」变成材料堆砌。",
        sequence=(
            ("入户", "被一道矮柜挡了一下，看不到客厅全貌", "threshold"),
            ("转折", "转过柜端，客餐厅一次展开", "compression_release"),
            ("主空间", "连续界面上的窗成为主画面，家具退到两侧", "light_layering"),
            ("抵达私密", "穿过一道门，走廊在这里结束", "prospect_refuge"),
    ),
        technical=("原有管井位置决定脊能不能成立；管井不在中段时脊要绕，效率下降",
                   "排水坡度与降板高度需现场核对，不能按经验定",
                   "燃气与排烟路径必须独立，不能借用脊内空腔",
                   "承重墙与剪力墙不能动，脊体只能贴不能穿"),
        tradeoffs=("脊占 8–12㎡，等于用面积换秩序",
                   "管井位置不理想时，脊的效率明显下降",
                   "开放界面要求长期自律，收纳必须一次做够"),
        risks=("把承重墙当隔墙拆是这类方案最容易出的事故", "降板不足时地面找平吃掉净高"),
        cost_note="脊体与定制柜是主要投入；隔墙减少、管线集中，机电造价通常下降。",
        maintenance="管线集中便于检修；脊体表面是高频接触面，需耐污耐磨。",
        serves=("daylight", "privacy", "storage", "kitchen", "circulation"),
        keywords=("通透", "采光", "收纳", "厨房", "开放", "大平层"),
        requires=("既有建筑，结构不动", "厨卫位置可调整", "管井在可借用范围内"),
        precedent=("open plan", "spine", "service", "storage wall", "continuous"),
        plan_strategy="spine_centre", profiles=("residential",),
        massing_kind="spine", logic_key="service_spine",
    ),
    Strategy(
        id="DLB-INT-LOOP",
        discipline="interior", name="中心体块回游", family="radial",
        role="C",
        statement="在户型中间放一个体块，人绕着它走——走廊的面积被还给房间。",
        parti="中心一个体块（衣帽、家政、储物），四周形成环；公共与私密是环上的两段。",
        opportunity="大平层最浪费的是走廊。把走廊取消的办法不是把门开在一起，而是让动线"
                    "绕着一个体块走：任何一处都不再是死胡同，走廊变成了房间的一部分。",
        massing="体块 3–5㎡，四周通道净宽不小于 1.1m；体块成为公共区与私密区共用的边界，"
                "省掉一道隔墙。",
        section="体块做到结构梁底，不再另做吊顶；体块内部净高只够储物与挂衣，"
                "不承担停留功能。",
        facade="既有外围护不动。体块四面用同一材料包住，像一件家具而不是一个房间；"
               "它的转角是空间里唯一的实体转角。",
        circulation="入户正对体块的一个面（挂画或柜门），向左或向右都能到公共区；"
                    "绕过去才看见客厅——第一眼没有主画面，这是刻意的。",
        daylight="体块无光，正好放衣帽与储物；四周房间都能直接开窗。光沿着环走，"
                 "而不是穿过一条暗走廊。",
        materials_logic="体块用一个材料包到顶，四面收口一致；其余界面退成背景。"
                        "体块是「物」，其他是「面」，两者不争。",
        sequence=(
            ("入户", "正对一个体块的转角，看不见客厅", "threshold"),
            ("选路", "向左或向右都能到公共区，走哪边由人决定", "rhythm"),
            ("绕过", "绕过体块，空间一次打开，光从外侧进来", "compression_release"),
            ("主空间", "客厅与餐厨在同一片连续空间里", "prospect_refuge"),
    ),
        technical=("体块不能压住梁下净高不足的位置，需按实测梁底定位",
                   "至少保留一条不小于 1.1m 的连续疏散路径",
                   "排水管不宜埋进体块，除非原管井就在此处",
                   "体块自重与楼板荷载需核对，尤其老楼"),
        tradeoffs=("通道面积增加，家具不能贴体块摆放",
                   "环形体块对家具尺度敏感，必须提前锁定",
                   "体块占掉的位置往往是最「好用」的中间地带"),
        risks=("体块位置压住梁或管井会让整个方案返工", "通道过窄时回游变成绕路"),
        cost_note="体块与定制柜是主要投入；隔墙减少、走廊取消，地面材料用量上升。",
        maintenance="环绕通道意味着更多地面与更多收口；体块转角容易被反复触碰。",
        serves=("circulation", "area", "storage", "flexibility"),
        keywords=("走廊", "动线", "通透", "显大", "储物", "回游"),
        requires=("既有建筑，结构不动", "中间区域无承重墙", "面积足以形成环"),
        precedent=("loop", "core", "circulation", "open plan", "island"),
        profiles=("residential",), massing_kind="loop", logic_key="loop_core",
    ),
    Strategy(
        id="DLB-INT-DARKLIGHT",
        discipline="interior", name="明暗两段", family="layered",
        role="B",
        statement="先把光管住：入户这一段压暗压低，穿过一个门洞，光才一次给你。",
        parti="房子分成暗的一段和亮的一段；两段之间不是一扇门，是一个 600mm 厚的门洞。",
        opportunity="「高级但不要冷」不是靠更多材料，是靠对比与控制。先把前段压暗，"
                    "后面那面墙和那束光才有机会被看见——这是最省钱也最有效的一招。",
        massing="前段（入户、储物、餐厨）净高压到 2.4–2.6m、界面用深色；后段（客厅、卧室）"
                "保留结构净高、界面浅色；交界处做厚门洞，形成取景框。",
        section="压低段长度控制在 3–4m，超过就变成憋屈；门洞高度与后段净高差保持在"
                "一比一点三以上，落差才读得出来。",
        facade="既有外围护不动。界面只做「深—浅」两段，交界处不做收口条，让两种材料直接对撞；"
               "这是室内唯一允许出现的强对比。",
        circulation="入户即进入暗段，储物与餐厨在两侧；穿过门洞进入亮段，客厅与卧室依次展开。"
                    "回家这条路自带节奏。",
        daylight="前段靠人工光与深色界面的反射光，后段靠原有窗。窗不做满墙窗帘，"
                 "让光成为后段唯一的装饰。",
        materials_logic="前段深色木或深色石材，后段浅色矿物涂料或微水泥；同一种材料在"
                        "两个段落里用不同明度，保持连续又有区分。",
        sequence=(
            ("入户", "净高压下来，界面是深的，只有脚边有光", "compression_release"),
            ("过渡", "储物与餐厨在两侧，声音被吸住", "threshold"),
            ("第一眼", "穿过门洞，客厅的亮面在框里出现", "framing"),
            ("主空间", "净高抬起来，浅色界面把光散开", "light_layering"),
    ),
        technical=("压低段需做吊顶，风管、新风与排水要在这段排布，净高要一次算清",
                   "门洞是否承重必须确认；承重墙只能开洞加固，不能拆",
                   "深色材料显灰，需要更高显色指数的光源与更细的收口",
                   "前段无自然光，需机械通风与可靠的人工照明回路"),
        tradeoffs=("压低段牺牲一部分净高与采光",
                   "深色界面难维护，指纹与灰尘更明显",
                   "对比手法只能用一次，重复就失效"),
        risks=("门洞开在承重墙上是结构事故的高发点", "压低段过长会让入户产生压迫感"),
        cost_note="吊顶、门洞加固与灯光是主要投入；材料总量不一定增加，贵在收口与精度。",
        maintenance="深色界面需专用清洁；灯具数量多，维护点分散。",
        serves=("daylight", "experience", "arrival", "acoustic"),
        keywords=("高级", "质感", "氛围", "光", "不冷", "仪式感"),
        requires=("既有建筑，结构不动", "层高足以做压低段", "有可用的自然光面"),
        precedent=("compression", "threshold", "dark", "light", "contrast"),
        profiles=("residential",), massing_kind="darklight", logic_key="light_sequence",
    ),
    Strategy(
        id="DLB-INT-BOX",
        discipline="interior", name="房间里的房间", family="cluster",
        role="C",
        statement="在平层里再嵌一个小建筑：主卧套间做成一个盒，盒外才是开放的家。",
        parti="盒子 25–35㎡，含卧、卫、衣；盒墙双层隔声；盒顶不到顶，留一道缝。",
        opportunity="主卧要安静私密，但整层只有一层楼板——私密不能靠距离，只能靠围合。"
                    "嵌一个盒，等于在同一个标高上造出第二个尺度。",
        massing="盒子贴外墙（否则卧室无窗），其余三面是盒墙；盒墙厚 200mm 以上，"
                "内填吸声材料，形成双墙。",
        section="盒顶不到顶，留 200–400mm 缝：声与光在此断开，空间却仍然连续。"
                "这是盒子能成立的关键构造，不是造型细节。",
        facade="既有外围护不动。盒外用浅色、盒内用深色或木；盒子的边界就是材料的分界，"
               "一条缝都不做装饰。",
        circulation="从公共区沿一面长墙走到盒子的门，门与墙齐平、不设门套；"
                    "进门之后是一个完整的套间，不再需要穿过客厅。",
        daylight="盒子必须贴外墙，盒内窗做横向长窗，把光压成一条，避免卧室被大面积玻璃"
                 "变成「展厅」。",
        materials_logic="盒外浅、盒内深，材料跟着「内/外」走；盒墙的厚度在视觉上要被读出来，"
                        "否则盒子会被当成普通隔墙。",
        sequence=(
            ("入户", "先看见开放的家，盒子在远端像一块实体", "framing"),
            ("走近", "沿长墙走，墙与盒子齐平，门几乎看不见", "threshold"),
            ("进入", "门后是另一个尺度：净高更低，材料更深", "compression_release"),
            ("主空间", "卧与卫在盒内自成一套，窗外是横向的一条光", "prospect_refuge"),
    ),
        technical=("盒墙自重与楼板荷载需核对，老楼尤其",
                   "隔声靠双墙加吸声棉，单墙贴隔声毡达不到效果",
                   "盒内卫生间排水必须靠近原管井，否则要抬高地面",
                   "盒顶留缝处的防火与隔声需同时满足，不能只做一边"),
        tradeoffs=("盒墙占面积，等于用面积换私密",
                   "盒顶留缝时隔声有限，缝太小又失去连续感",
                   "造价高于普通隔墙，且不可逆"),
        risks=("盒内卫生间离管井太远会导致排水失败", "留缝处理不当会成为串音通道"),
        cost_note="双层墙、隔声构造与盒内独立卫浴是主要投入，单方造价高于常规隔墙方案。",
        maintenance="隔声构造一旦封闭难以更改；盒内卫浴需独立排风。",
        serves=("privacy", "acoustic", "experience", "flexibility"),
        keywords=("私密", "安静", "主卧", "套间", "隔音"),
        requires=("既有建筑，结构不动", "主卧可贴外墙", "卫浴靠近原管井"),
        precedent=("box", "volume", "inner room", "pavilion", "cluster"),
        profiles=("residential",), massing_kind="inner_box", logic_key="inner_box",
    ),
]


# --------------------------------------------------------------------------
# 景观主导：分区、游线、水、竖向、植物
# --------------------------------------------------------------------------
LANDSCAPE: List[Strategy] = [
    Strategy(
        id="DLB-LAN-POND",
        discipline="landscape", name="一池静水 · 环形游线", family="courtyard",
        role="B",
        statement="院子中心放一块静水，园路绕水一圈；茶座在水远岸，回望房子。",
        parti="水是中心，路是环，房子是背景；三者互相看。",
        opportunity="静水的作用不是「有水」，是把天空和树变成院子的一部分。倒影让院子的"
                    "视觉面积翻倍，而且不需要多一寸土地——这是小院最划算的一招。",
        massing="以水面为心，园路成环；水与路之间留 600mm 收边石带，人不会踩到水边软土。",
        section="水面比园路低 100–150mm，草坪比园路高 50mm，种植区再高 100–150mm 做微地形；"
                "整个院子向排水点找坡，坡度不小于 0.5%。",
        facade="边界用围墙或密植挡住外部视线，墙高与视线高度对齐（1.8–2.0m）；"
               "临房一侧尽量通透，把院借进室内。",
        circulation="环形主路宽 900–1200mm，从入口绕水一周回到入口；跨水处不设桥，"
                    "让绕行成为设计的一部分。",
        daylight="水面把光反射进室内，白天不必开灯；树冠投影落在水面上，光变成会动的东西。",
        materials_logic="池底深色（让倒影更清楚），收边用整石，园路用透水混凝土或级配碎石；"
                        "三种材料足够，多则碎。",
        sequence=(
            ("进入", "穿过门，先看到水面的反光，再看到院子有多大", "framing"),
            ("绕行", "沿水走，房子在背后，树在前面", "rhythm"),
            ("停留", "茶座在远岸，背靠种植，面向房子与水", "prospect_refuge"),
            ("回望", "坐下时看到的是房子的倒影，不是房子的正面", "borrowed_view"),
        ),
        technical=("水池必须做结构池体与防水，砖砌薄壁会开裂",
                   "循环泵、溢流口与补水点需在施工前定位，后期加装要破面层",
                   "儿童安全：水深与防滑铺装需一并考虑，不能只靠「看着」",
                   "乔木与水池的距离要按成年冠幅预留，否则落叶全进池"),
        tradeoffs=("水面维护（落叶、藻类）是长期成本",
                   "水深带来儿童安全责任，需做浅水或加防护",
                   "静水无风时最好看，有风时倒影会碎"),
        risks=("池体防水失败返工代价极高", "落叶季不清池会迅速恶化水质"),
        cost_note="池体、防水、循环设备是主要投入；植物按冠幅计价，大乔木单价高。",
        maintenance="每周清落叶、每月查水质、每季修水生植物；循环泵需常年通电。",
        serves=("outdoor", "experience", "daylight", "privacy"),
        keywords=("水景", "倒影", "喝茶", "安静", "院子", "观赏"),
        requires=("有独立庭院", "有给排水与电源条件", "业主接受定期维护"),
        precedent=("pond", "reflecting", "water", "pool", "still"),
        zones=(("水景", "20–25%"), ("草坪与停留", "30%"), ("种植", "30–35%"),
               ("园路", "10%"), ("服务与收纳", "5%")),
        water="静水面深 300–450mm，池底深色；循环泵加溢流口，补水点藏在收边石内。",
        planting="三层配置：乔木 3–5 株做骨架，灌木围合与遮挡，地被满铺；"
                 "常绿与落叶约六比四，保证冬天不空。",
        paving="主路与停留区用两种材料，交界处用同宽石带；水边一圈整石收边，宽度 600mm。",
        massing_kind="pond", strong_water=True, logic_key="still_water_loop",
    ),
    Strategy(
        id="DLB-LAN-DRY",
        discipline="landscape", name="旱溪台地 · 无水的水景", family="layered",
        role="A",
        statement="不做池子：用一条旱溪代替水，两侧做两级台地，雨来时有水声，平时是干的。",
        parti="等高线决定台地，旱溪是排水线也是主景线；人沿等高线走，跨溪一次。",
        opportunity="要水景又要好维护，这在露天水池上是冲突的。旱溪给的是水的形与声，"
                    "却没有池水的日常维护——这是「低维护 + 有水的意象」唯一同时成立的做法。",
        massing="两级台地高差 300–450mm，用干砌石或矮挡墙；旱溪沿最低处走，宽 600–1200mm。",
        section="竖向是主要工具：台地决定视线高度，溪底再低 100–150mm；"
                "整个院子靠重力排水，不设集水井。",
        facade="边界用耐旱高篱或矮墙；台地挡墙同时是坐凳（高度 400–450mm 时可用）。",
        circulation="主路沿等高线走，坡度控制在 1:12 以内；跨旱溪处用一块整石或钢桥，宽 900mm。",
        daylight="没有水面反射，靠台地高差制造视线层次；乔木种在台地高处，投影落在低处。",
        materials_logic="台地用大板铺装，旱溪用砾石，两者之间一条混凝土收边；"
                        "材料的分界就是标高变化的位置。",
        sequence=(
            ("进入", "从高处进入，看到两级台地与中间那条石溪", "framing"),
            ("下行", "沿路下到低台地，视点降低，植物高过头顶", "compression_release"),
            ("跨溪", "踩一块整石过去，脚下是砾石", "threshold"),
            ("停留", "低台地的茶座被种植围住，只留一个开口", "prospect_refuge"),
        ),
        technical=("排水坡度与渗排能力需按暴雨重现期核算",
                   "挡土高度超过 600mm 需做结构基础，干砌只适用于低墙",
                   "砾石粒径不能太小，儿童活动区需避免小粒砾石",
                   "旱溪底部需设渗排管，否则暴雨时会积水"),
        tradeoffs=("没有常年水面，「水景」的直观性弱于池子",
                   "无雨时是枯景，靠置石与植物撑住画面",
                   "台地意味着土方与挡土，前期土建成本上升"),
        risks=("排水核算不足会在暴雨时倒灌", "干砌石挡墙在冻融地区易变形"),
        cost_note="土方、挡土与渗排是主要投入；没有池体与循环设备，长期成本低。",
        maintenance="雨季前清溪道，旱季修剪观赏草；无需换水与除藻。",
        serves=("outdoor", "maintenance", "structure", "experience"),
        keywords=("好维护", "低维护", "水景", "小孩", "自然", "省心"),
        requires=("有独立庭院", "场地有高差或允许做土方", "排水有出路"),
        precedent=("dry", "stream", "terrace", "gravel", "drainage"),
        zones=(("近房硬质停留", "30%"), ("旱溪带", "15%"), ("低台地草坪与种植", "45%"),
               ("服务", "10%")),
        water="旱溪底铺 100–150mm 砾石，下设渗排管；暴雨时形成 100–200mm 深的临时水流。",
        planting="以耐旱为主：观赏草、宿根花卉；溪边种喜湿品种；常绿与落叶约五比五。",
        paving="台地用 600×900 大板，旱溪用砾石，两者之间用一条混凝土收边过渡。",
        massing_kind="terraces", logic_key="dry_stream_terrace",
    ),
    Strategy(
        id="DLB-LAN-GROVE",
        discipline="landscape", name="林下茶席 · 借景", family="cluster",
        role="C",
        statement="院子的主体是树：沿边界围一圈乔木，中间留一块抬起 150mm 的茶席。",
        parti="树围成边界，中间是空的；水只做一条浅渠从旁边过，不占中心。",
        opportunity="「坐下来喝茶」这件事，位置比水的面积重要。把茶席放在树冠下、背靠边界、"
                    "面向房子，院子才会真的被每天使用，而不只是被观看。",
        massing="边界一圈乔木形成「林」，中间留 30–40㎡ 的空地做茶席与草坪；"
                "水渠沿边走过，不切中心。",
        section="茶席平台抬高 150mm（木平台），背靠种植、面向房子；标高变化只有一级，"
                "但足以把「坐的地方」与「走的地方」分开。",
        facade="用植物做边界而不是围墙：密植灌木加乔木形成视线屏障，成本低于围墙，"
               "而且随季节变化。",
        circulation="一条主路从入口到茶席，宽 900mm，两侧留 150mm 种植带；"
                    "茶席之外再有一条汀步通向院子深处。",
        daylight="树冠过滤直射光，形成斑驳光；落叶乔木夏天遮阴、冬天透光，"
                 "这是常绿树给不了的。",
        materials_logic="木平台、汀步石与砾石三种；木用耐久材（不是防腐木贴皮），"
                        "颜色随年份变灰是特性不是缺陷。",
        sequence=(
            ("进入", "穿过一段密植，看不到院子全貌", "threshold"),
            ("转折", "种植带断开，茶席出现，背后是树", "framing"),
            ("坐下", "背靠种植，面向房子，前方是草地与浅渠", "prospect_refuge"),
            ("停留", "树影落在桌面上，光随时间移动", "light_layering"),
        ),
        technical=("乔木与建筑基础的距离按成年冠幅预留，大树离墙不少于 3m",
                   "根系会顶起铺装，平台与铺装需做根障",
                   "落叶需要定期清理，落进浅渠会堵",
                   "平台基础需防潮，木构件需通风"),
        tradeoffs=("树荫下草坪长不好，需要换耐阴地被",
                   "落叶是长期清理工作",
                   "树长大后可能遮住室内采光，需选落叶大乔木并预留修剪"),
        risks=("选错树种（速生、浅根）会在五到十年后变成问题", "浅渠堵塞会导致积水"),
        cost_note="乔木按冠幅计价，是大头；平台与汀步次之；没有池体与循环设备。",
        maintenance="每年修剪一次，落叶季每周清扫；浅渠每季清淤。",
        serves=("outdoor", "experience", "maintenance", "privacy"),
        keywords=("种植", "喝茶", "树", "自然", "安静", "好维护"),
        requires=("有独立庭院", "土深足够种乔木", "业主接受落叶清理"),
        precedent=("grove", "garden", "native planting", "shade", "canopy"),
        zones=(("林带", "40–45%"), ("茶席与草坪", "30%"), ("浅水渠", "10%"),
               ("路径", "10%"), ("服务", "5%")),
        water="浅水渠宽 300–400mm、深 100–150mm，可做循环小水景；无水期作为枯山水渠。",
        planting="乔木 5–7 株形成树冠覆盖；下层用耐阴地被（蕨类、苔藓、玉簪）；"
                 "常绿与落叶约七比三。",
        paving="木平台加汀步石（间距 600mm）与砾石；汀步不切边，保留自然形状。",
        massing_kind="grove", logic_key="grove_tea",
    ),
]


STRATEGIES: Dict[str, List[Strategy]] = {
    "architecture": ARCHITECTURE,
    "interior": INTERIOR,
    "landscape": LANDSCAPE,
}

#: 没有专业策略时的退路说明（写给用户看的，不是内部日志）。
FALLBACK_NOTE = ("该主导专业暂无推敲策略，回退到 22 个空间原型作为经验参考；"
                 "原型的组织逻辑不针对本专业，须人工复核。")


def for_discipline(discipline: str) -> List[Strategy]:
    """该专业的全部策略。未知专业返回空表，不猜。"""
    return list(STRATEGIES.get(discipline or "", ()))


def for_project(discipline: str, profile_id: str) -> List[Strategy]:
    """该专业 + 该项目类型可用的策略。

    类型不匹配的策略不是"差一点"，是**说的是另一件事**（住宅的服务脊放到办公室
    里没有意义）。这里直接不返回，让调用方回退到该类型的空间原型。
    """
    pid = str(profile_id or "")
    return [s for s in for_discipline(discipline)
            if not s.profiles or pid in s.profiles]


def get(strategy_id: str) -> Optional[Strategy]:
    for items in STRATEGIES.values():
        for s in items:
            if s.id == strategy_id:
                return s
    return None


def applies(ctx: Any) -> bool:
    """这个项目该不该走推敲层。

    有专属策略就走专属；没有专属策略**但**类型给了方向模板的，走模板；
    名字在"已有成套策略"名单里的类型（住宅/办公/私家庭院…）保持原路，
    免得新加的分类把它们原有的原型/平面策略挤掉。
    """
    if for_project(getattr(ctx, "lead_id", ""), getattr(ctx, "profile_id", "")):
        return True
    from .. import taxonomy as _tx

    codes = _taxonomy_codes(ctx) or list(
        (getattr(ctx, "taxonomy", {}) or {}).get("codes") or [])
    specs = [_tx.resolve(c) for c in codes]
    if any(sp and (sp.uses_profile_strategies or sp.strategy_ids) for sp in specs):
        return False
    return bool(for_taxonomy(ctx, limit=2))


# --------------------------------------------------------------------------
# 打分：证据优先，其次业主原话，最后才是案例佐证
# --------------------------------------------------------------------------
#: 信号权重：与业主诉求直接相关的信号更重。数值是「一分信号值多少分」。
SIGNAL_WEIGHT: Dict[str, float] = {
    "privacy": 20.0, "daylight": 20.0, "arrival": 16.0, "outdoor": 18.0,
    "experience": 16.0, "circulation": 12.0, "area": 12.0, "storage": 10.0,
    "kitchen": 10.0, "acoustic": 12.0, "structure": 12.0, "maintenance": 10.0,
    "flexibility": 8.0, "service": 8.0, "operation": 8.0, "focus": 8.0,
}


def _text(ctx: Any) -> str:
    parts = [str(getattr(ctx, "feeling_text", "") or "")]
    parts += [str(v or "") for v in (getattr(ctx, "answers", {}) or {}).values()]
    parts += [str(o.get("problem") or "") + str(o.get("design_goal") or "")
              for o in (getattr(ctx, "opportunities", []) or [])]
    return " ".join(parts)


def _score(s: Strategy, ctx: Any, precedent: Dict[str, List[str]]) -> Dict[str, Any]:
    """一条策略对这个项目的适配度，连同它的理由。"""
    score = 0.0
    why: List[str] = []
    for key in s.serves:
        sig = ctx.signal(key)
        if sig > 0:
            w = SIGNAL_WEIGHT.get(key, 10.0)
            score += sig * w
            why.append(f"回应{KEY_LABEL.get(key, key)}：{ctx.label(key)}")

    blob = _text(ctx)
    hits = [k for k in s.keywords if k and k in blob]
    if hits:
        score += 4.0 * len(hits)
        why.append("业主原话提到「" + "」「".join(hits) + "」")

    # 水景的分量单独算。一条浅渠和一池静水都叫「有水」，但业主要水景时，
    # 只有以水面为主体的策略才算真的给了；否则「有水池」会靠别的关键词
    # （好维护、小孩、自然）堆分胜出，业主拿到的是一个没有水的院子。
    if any(w in blob for w in ("水景", "水池", "水面", "池水", "静水", "跌水", "水声")):
        if s.strong_water:
            score += 14.0
            why.append("业主提出水景，本策略以水面为主体")
        else:
            why.append("本策略的水只作点缀，不构成「水景」的主要画面")

    # 案例佐证：只在案例文本里真的出现这套手法时才加分，且分值低于业主原话。
    # 案例不是需求，不能压倒项目自身的证据。
    pres = [t for t in s.precedent if t in precedent]
    if pres:
        score += 2.5 * len(pres)
        titles = sorted({t for p in pres for t in precedent[p]})[:2]
        why.append("案例中出现同类手法：" + "、".join(pres[:3])
                   + ("（" + "；".join(titles) + "）" if titles else ""))

    met: List[str] = []
    unmet: List[str] = []
    unverified: List[str] = []
    for req in s.requires:
        ok = _requires_ok(req, ctx)
        if ok is True:
            met.append(req)
        elif ok is False:
            unmet.append(req)
        else:
            # 判不了就说判不了：既不算满足，也不污蔑它不满足。
            unverified.append(req)
    if unmet:
        score -= 6.0 * len(unmet)
        why.append("前提不满足：" + "、".join(unmet))

    if ctx.precision == "diagnostic":
        score -= 1.0     # 无几何时所有策略同等折扣，不因此改变相对排序

    return {"strategy": s, "score": round(score, 1), "why": why,
            "met_requires": met, "unmet_requires": unmet,
            "unverified_requires": unverified}


#: 信号键 -> 中文名（报告里用）
KEY_LABEL: Dict[str, str] = {
    "privacy": "私密", "daylight": "采光", "arrival": "到达与仪式感",
    "outdoor": "室内外关系", "experience": "空间体验", "circulation": "动线",
    "area": "面积效率", "storage": "收纳", "kitchen": "厨房与用餐",
    "acoustic": "声环境", "structure": "结构条件", "maintenance": "维护",
    "flexibility": "可变性", "service": "后勤", "operation": "运营", "focus": "专注",
}


def _requires_ok(req: str, ctx: Any) -> Optional[bool]:
    """前提核验。能判的判，判不了的不假装判过。

    这里刻意只做**最少**的判断：层数、地块、结构。其余前提（例如「有景可看」）
    无法从现有数据得出，返回 None，按"未核验"处理而不是判失败。
    """
    levels = _levels(ctx)
    if "层数不少于两层" in req and levels is not None:
        return levels >= 2
    if "层数不少于三层" in req and levels is not None:
        return levels >= 3
    if "有独立地块" in req or "有独立庭院" in req:
        # 新建/庭院类项目有地块；既有大平层没有
        return _has_site(ctx)
    if "既有建筑" in req:
        return _is_existing(ctx)
    return None


def _values(ctx: Any) -> Dict[str, str]:
    return {str(k): str(v or "") for k, v in (getattr(ctx, "answers", {}) or {}).items()}


def _levels(ctx: Any) -> Optional[int]:
    """层数：先从问答里读，读不到再从不带数字的「三层」这类说法里读。"""
    ans = _values(ctx)
    for key in ("base.floors", "arch.floors", "res.floors"):
        v = ans.get(key, "")
        if v.isdigit():
            return int(v)
    blob = " ".join(ans.values())
    for cn, n in (("三层", 3), ("四层", 4), ("二层", 2), ("两层", 2), ("单层", 1),
                  ("一层", 1), ("五层", 5)):
        if cn in blob:
            return n
    return None


def _has_site(ctx: Any) -> Optional[bool]:
    blob = " ".join(_values(ctx).values()) + str(getattr(ctx, "name", ""))
    for word in ("地块", "院子", "庭院", "庭院景观", "花园", "新建", "自建", "宅基地"):
        if word in blob:
            return True
    for word in ("大平层", "公寓", "二手房", "已建成", "现有住房"):
        if word in blob:
            return False
    return None


def _is_existing(ctx: Any) -> Optional[bool]:
    v = _has_site(ctx)
    return None if v is None else (not v)


# --------------------------------------------------------------------------
# 案例反哺：从已核验案例里提取手法词，供策略加分与引用
# --------------------------------------------------------------------------
#: 案例文本里的手法词 -> 中文说法。只收**能从描述里读到**的词，不做语义猜测。
#:
#: 一律按词边界匹配：早先用子串匹配时 `core` 会命中 `score`、`light` 会命中
#: `daylight`，于是每一条案例都"佐证"了每一条策略——加分变得毫无区分度。
#: 这里也只收**技法词**，不收「光」「水」这类几乎每篇描述都有的通名。
PRECEDENT_TERMS: Dict[str, str] = {
    "courtyard": "内院围合", "patio": "内院围合", "inner garden": "内院围合",
    "reflecting": "静水倒影", "pond": "静水", "pool": "水面",
    "terrace": "退台", "stepped": "退台", "split-level": "错层", "level change": "错层",
    "pilotis": "架空", "floating": "架空悬浮", "stilt": "架空",
    "grove": "林下", "canopy": "树冠", "native planting": "本土植物",
    "compression": "压缩释放", "threshold": "门槛过渡",
    "open plan": "连续开间", "loop": "回游", "skylight": "天光",
    "dry": "旱溪", "gravel": "砾石", "stream": "溪流",
    "pavilion": "独立体量", "cluster": "组团",
}


def _has_term(term: str, hay: str) -> bool:
    """词边界匹配。连字符与斜杠按词边界处理，避免 `split-level` 被截断。"""
    import re

    pattern = r"(?<![a-z])" + re.escape(term.lower()) + r"(?![a-z])"
    return re.search(pattern, hay) is not None


def precedent_signals(research: Optional[Dict[str, Any]]) -> Dict[str, List[str]]:
    """从案例摘要里读出真实出现的手法词，返回 ``{词: [案例标题]}``。

    只读案例**自己的文字**。案例没写到的词不会凭空出现——这是"案例帮上设计"
    与"拿案例当装饰"的分界。
    """
    out: Dict[str, List[str]] = {}
    for c in (research or {}).get("cases") or []:
        hay = " ".join([str(c.get("title") or ""), str(c.get("summary") or "")]).lower()
        title = str(c.get("title") or "")
        for term in PRECEDENT_TERMS:
            if _has_term(term, hay):
                out.setdefault(term, []).append(title)
    return out


# --------------------------------------------------------------------------
# 选策略：组织逻辑必须互不相同
# --------------------------------------------------------------------------
def _pick(ranked: List[Dict[str, Any]], limit: int) -> List[Dict[str, Any]]:
    """按分数取，但**同一组织逻辑只取一次**。

    这是三套方案「真的不同」的机械保证：同族、同 logic_key 的第二条直接跳过，
    哪怕它分更高。宁可只出两套，也不给两个换了措辞的同款。
    """
    picked: List[Dict[str, Any]] = []
    used_family: set = set()
    used_logic: set = set()
    for item in sorted(ranked, key=lambda d: (-d["score"], d["strategy"].id)):
        s: Strategy = item["strategy"]
        logic = s.logic_key or s.id
        if s.family in used_family or logic in used_logic:
            continue
        picked.append(item)
        used_family.add(s.family)
        used_logic.add(logic)
        if len(picked) >= limit:
            return picked
    # 家族用尽：允许同族但组织逻辑不同的一条补第三套，并如实标注
    for item in sorted(ranked, key=lambda d: (-d["score"], d["strategy"].id)):
        s: Strategy = item["strategy"]
        if any(s.id == p["strategy"].id for p in picked):
            continue
        if (s.logic_key or s.id) in used_logic:
            continue
        item = dict(item)
        item["same_family_note"] = (
            f"与已选方案同属「{s.family}」家族，但组织逻辑不同（{s.logic_key}）；"
            "如业主认为区分度不足，可只保留其中一套。")
        picked.append(item)
        used_logic.add(s.logic_key or s.id)
        break
    return picked


# --------------------------------------------------------------------------
# 输出：把策略写成方案的六个答案
# --------------------------------------------------------------------------
def _join(seq: Sequence[str]) -> str:
    return "；".join(x for x in seq if x)


def _facts(ctx: Any) -> Dict[str, str]:
    """能写进方案的已知事实。缺的写「未定」，不留空。"""
    levels = _levels(ctx)
    area = getattr(ctx, "area_available_m2", None) or getattr(ctx, "target_area_m2", 0) or 0
    return {
        "levels": f"{levels} 层" if levels else "层数未确认",
        "area": f"约 {area:.0f} ㎡" if area else "面积未确认",
        "location": getattr(ctx, "location", "") or "地点未确认",
        "style": getattr(ctx, "style_preference", "") or "风格未指定",
        "feelings": "、".join(f"「{w}」" for w in (getattr(ctx, "feelings", {}) or {}))
        or "业主未表达感受词",
    }


def _integration(s: Strategy, ctx: Any) -> str:
    """建筑 / 室内 / 景观怎么合成一个整体——按主导专业说清各自的位置。"""
    lead = getattr(ctx, "lead_id", "")
    parts: List[str] = []
    if lead == "architecture":
        parts.append("建筑定 parti 与体量，室内与景观都服从这套组织逻辑，而不是各自发挥")
        parts.append("室内延续立面的「实—透」分区：外侧实面对应服务与储藏，院内透面对应起居")
        parts.append("景观不是填补空地，它承接建筑让出来的那块负空间——院是这套方案的中心，"
                     "铺装线、水线、乔木位置都从院的几何推出")
    elif lead == "interior":
        parts.append("室内是唯一设计对象：外围护、结构、户门与管井位置均按现状保留，不重启建筑设计")
        parts.append("景观不涉及；如后续需要，只做窗台以外的界面协调，不改建筑本体")
        parts.append("室内策略的边界是「不动结构」——所有手法都靠隔墙、界面与家具实现")
    else:
        parts.append("景观是唯一设计对象：建筑本体、立面和出入口位置不动，只在必要处增加"
                     "铺装衔接与排水接驳")
        parts.append("室内不涉及；与建筑的关系只处理「从窗看出去是什么」这一件事")
        parts.append("分区、游线、水与植物合起来构成一个完整的游历，而不是几件小品的集合")
    if s.tradeoffs:
        parts.append("这套策略的代价已经写在取舍里，不是隐藏成本")
    return "；".join(parts) + "。"


def _taxonomy_codes(ctx: Any) -> List[str]:
    codes = getattr(ctx, "taxonomy_codes", None) or ()
    return [str(c) for c in codes]


def for_taxonomy(ctx: Any, *, limit: int = 3) -> List[Strategy]:
    """按项目类型的方向模板造策略：2–3 条组织逻辑不同的方向。

    这里**不是**第二套策略库：方向上写的是该类型的专业方法（医疗洁污双廊、
    教育分龄组团、工业工艺流线……），字段与 `Strategy` 同构，所以下游的
    六问、图解、提案不需要为新类型写分支。
    """
    from .. import taxonomy as _tx

    discipline = str(getattr(ctx, "lead_id", "") or "")
    codes = _taxonomy_codes(ctx) or list(
        (getattr(ctx, "taxonomy", {}) or {}).get("codes") or [])
    dirs = _tx.directions(codes, discipline)[:max(2, min(3, limit))]
    out: List[Strategy] = []
    names = [d.name for d in dirs]
    for i, d in enumerate(dirs):
        code = codes[0] if codes else ""
        spec = _tx.resolve(code)
        label = spec.name if spec else discipline
        focus = "、".join(spec.focus[:3]) if spec else ""
        fam = _family_for(d.name, i)
        out.append(Strategy(
            id=f"TX-{code or discipline.upper()}-{i + 1}",
            discipline=discipline,
            name=d.name,
            family=fam,
            role=("A", "B", "C")[i % 3],
            statement=f"{label}：{d.parti}",
            parti=d.parti,
            opportunity=d.why,
            massing=f"按组织逻辑排布功能块：{d.parti}",
            section="竖向关系按功能与流线确定；层高、净高须在 S3/S4 依据设备与结构条件定。",
            facade="界面按功能露出程度分级：公共面开放、后勤面收实；材料不指定品牌与型号。",
            circulation=f"主次流线由「{d.name}」决定，服务流线不与主动线交叉。",
            daylight=f"优先保证{focus or '主要使用空间'}的采光与视线，其余按功能分级。",
            materials_logic="材料按类型与当地做法确定；本方向只定原则（耐污、维护、质感），不定型号。",
            sequence=(
                ("第一眼", f"到达时先读到：{d.parti}", "入口与视线"),
                ("转折", f"经过{focus or '过渡空间'}，从公共转向内部", "分区收放"),
                ("主空间", f"停在「{d.name}」要解决的核心空间", "核心空间"),
            ),
            technical=("结构与设备条件须由相应专业确认",),
            tradeoffs=(f"代价：{d.name}成立的前提是{focus or '功能与场地条件'}能够落实",),
            risks=("缺少真实几何与设备条件时，本方向只作关系示意",),
            cost_note="造价随构造与设备等级变化，本阶段只给方向，不给单价。",
            maintenance="维护方式随运营主体确定；后场与设备可达性须在 S3 明确。",
            serves=(),
            keywords=(d.name,),
            requires=(),
            precedent=(),
        ))
    return out


def _family_for(name: str, index: int) -> str:
    """方向名 → 图解家族。只影响图形怎么画，不影响设计判断。"""
    for key, fam in (("围合", "courtyard"), ("院", "courtyard"), ("组团", "cluster"),
                     ("串联", "linear"), ("线性", "linear"), ("街", "linear"),
                     ("核心", "radial"), ("模块", "grid"), ("阵列", "grid"),
                     ("分区", "grid"), ("替代", "hall"), ("大厅", "hall")):
        if key in name:
            return fam
    return ("linear", "cluster", "grid")[index % 3]


def build_strategies(ctx: Any, research: Optional[Dict[str, Any]] = None,
                     *, limit: int = 3) -> List[Dict[str, Any]]:
    """产出 2–3 条推敲过的策略。每条都是完整方案内容，不含风格。"""
    discipline = str(getattr(ctx, "lead_id", "") or "")
    from .. import taxonomy as _tx

    codes = _taxonomy_codes(ctx) or list(
        (getattr(ctx, "taxonomy", {}) or {}).get("codes") or [])
    specs = [_tx.resolve(c) for c in codes]
    # 已有成套策略库的类型（住宅、办公、私家庭院……）继续用老策略；
    # 其余类型（医院、学校、厂房……）用它们自己的方向模板——
    # 否则一座医院会拿到"院中取院／逐层退台"，那是住宅的答案。
    has_dedicated = any(sp and (sp.uses_profile_strategies or sp.strategy_ids)
                        for sp in specs)
    if has_dedicated:
        # 这些类型本来就有成套策略（住宅/办公/私家庭院…）。它们的策略池可能为空
        # （例如办公走的是空间原型 + office_cluster 平面策略），这时**保持原样**，
        # 把决定权交回调用方，不要用方法模板把已有能力顶掉。
        pool = for_project(discipline, getattr(ctx, "profile_id", ""))
        if not pool:
            return []
    else:
        pool = []
    if not pool:
        method = for_taxonomy(ctx, limit=limit)
        if method:
            return [_method_payload(ctx, st, research) for st in method]
        return []

    prec = precedent_signals(research)
    ranked = [_score(s, ctx, prec) for s in pool]
    picked = _pick(ranked, max(2, min(3, limit)))
    facts = _facts(ctx)
    blob = _text(ctx)

    out: List[Dict[str, Any]] = []
    for idx, item in enumerate(picked):
        s: Strategy = item["strategy"]
        prot = s.to_prototype()
        seq = [
            {"step": step, "event": event, "device": device}
            for step, event, device in s.sequence
        ]
        prec_titles: List[str] = []
        for term in s.precedent:
            for title in prec.get(term, []):
                if title not in prec_titles:
                    prec_titles.append(title)
        prec_titles = prec_titles[:3]
        out.append({
            "strategy_id": s.id,
            "role": s.role,
            "discipline": discipline,
            "name": s.name,
            "family": s.family,
            "statement": s.statement,
            "prototype": prot,
            "sequence": {
                "prototype_id": s.id,
                "family": s.family,
                "steps": seq,
                "devices": [d for _, _, d in s.sequence],
                "missing_steps": [x for x in ("第一眼", "转折", "主空间")
                                  if not any(y["step"] == x for y in seq)],
                "note": "序列由设计推敲产出，不是从原型套出的通用事件。",
            },
            "deliberation": {
                "strategy_id": s.id,
                "discipline": discipline,
                "parti": s.parti,
                "key_opportunity": s.opportunity,
                "why_this_strategy": _join(item["why"]) or "本项目未出现可对应的证据，"
                                                           "该策略只作为方向备选，优势尚未成立",
                "experience": [
                    {"step": x["step"], "event": x["event"]} for x in seq
                ],
                "light_view_proportion_material": s.daylight + " " + s.materials_logic,
                "integration": _integration(s, ctx),
                "technical_coordination": list(s.technical),
                "massing": s.massing,
                "levels_program": list(s.levels_program),
                "section": s.section,
                "facade": s.facade,
                "zones": [{"name": n, "share": v} for n, v in s.zones],
                "water": s.water,
                "planting": s.planting,
                "paving": s.paving,
                "precedent_cases": prec_titles,
                "precedent_note": (
                    "以下已核验案例的公开描述中出现同类手法，可作为方向佐证："
                    + "；".join(prec_titles) if prec_titles else
                    "本次检索到的案例未出现与本策略同名的手法，因此不引用案例作佐证。"),
                "evidence_score": item["score"],
                "met_requires": item["met_requires"],
                "unmet_requires": item["unmet_requires"],
                "unverified_requires": item.get("unverified_requires", []),
                "facts_used": dict(facts),
                "same_family_note": item.get("same_family_note", ""),
            },
            "technical": list(s.technical),
            "tradeoffs": list(s.tradeoffs),
            "risks": list(s.risks),
            "cost_note": s.cost_note,
            "maintenance": s.maintenance,
            "advantages": _advantages(s, item, ctx),
            "keywords_hit": [k for k in s.keywords if k in blob],
        })
    return out


def _method_payload(ctx: Any, s: Strategy,
                    research: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """把方向模板写成与推敲策略同形的结果（source=method）。"""
    from .. import taxonomy as _tx

    codes = _taxonomy_codes(ctx) or list(
        (getattr(ctx, "taxonomy", {}) or {}).get("codes") or [])
    spec = _tx.resolve(codes[0]) if codes else None
    seq = [{"step": a, "event": b, "device": c} for a, b, c in s.sequence]
    fam_zh = {"linear": "线性", "radial": "环形 / 放射", "cluster": "组团",
              "layered": "分层 / 递进", "hall": "大厅式", "courtyard": "院落式"}.get(
                  s.family, s.family)
    prot = {
        "prototype_id": s.id, "id": s.id, "profile": s.discipline,
        "name": s.name, "statement": s.statement,
        "spatial_logic": s.parti, "zoning": s.massing, "circulation": s.circulation,
        "daylight": s.daylight, "family": s.family, "family_zh": fam_zh,
        "plan_strategy": "",
        "experience": "；".join(x["event"] for x in seq),
        "answers": [], "risks": list(s.risks), "cost_note": s.cost_note,
        "maintenance": s.maintenance,
    }
    return {
        "strategy_id": s.id,
        "role": s.role,
        "discipline": s.discipline,
        "name": s.name,
        "family": s.family,
        "statement": s.statement,
        "prototype": prot,
        "sequence": {
            "prototype_id": s.id, "family": s.family, "steps": seq,
            "devices": [x["device"] for x in seq],
            "missing_steps": [x for x in ("第一眼", "转折", "主空间")
                              if not any(y["step"] == x for y in seq)],
            "note": "序列来自项目类型的设计方法，不是从通用原型套出来的事件。",
        },
        "deliberation": {
            "strategy_id": s.id,
            "discipline": s.discipline,
            "taxonomy_codes": codes,
            "taxonomy_name": spec.name if spec else "",
            "parti": s.parti,
            "key_opportunity": s.opportunity,
            "why_this_strategy": s.opportunity,
            "experience": [{"step": x["step"], "event": x["event"]} for x in seq],
            "light_view_proportion_material": s.daylight + " " + s.materials_logic,
            "integration": ("按主导专业推进，其余专业做界面协调；"
                            + ("本类型的专业要点：" + "、".join(spec.focus[:4]) if spec else "")),
            "technical_coordination": list(s.technical),
            "massing": s.massing,
            "levels_program": [],
            "section": s.section,
            "facade": s.facade,
            "zones": [],
            "water": "", "planting": "", "paving": "",
            "precedent_cases": [],
            "precedent_note": "本方向由项目类型的设计方法推出，尚未匹配到同名手法案例。",
            "evidence_score": 0.0,
            "met_requires": [], "unmet_requires": [], "unverified_requires": [],
            "facts_used": {},
            "same_family_note": "",
            "source": "method",
            "gap": ("" if spec and spec.strategy_ids else
                    f"本类型（{spec.name if spec else '未识别'}）没有专属推敲策略库，"
                    "以上方向来自该类型的专业方法，深化时须按行业条件复核，"
                    "不能当作已实现的算法能力。"),
        },
        "technical": list(s.technical),
        "tradeoffs": list(s.tradeoffs),
        "risks": list(s.risks),
        "cost_note": s.cost_note,
        "maintenance": s.maintenance,
        "advantages": ["按项目类型的设计方法组织空间，不是套通用户型"],
        "keywords_hit": [],
        "source": "method",
    }


def _advantages(s: Strategy, item: Dict[str, Any], ctx: Any) -> List[str]:
    out: List[str] = []
    if item["score"] >= 20:
        out.append("对业主自己提出的问题有直接回应，且回应的是同一件事")
    if len(item["met_requires"]) >= 2:
        out.append("前提条件已满足：" + "、".join(item["met_requires"]))
    if s.discipline == "landscape":
        out.append("分区、游线、水、竖向、植物五项齐全，可按阶段深化")
    if s.discipline == "architecture":
        out.append("体量、剖面、立面三级关系一致，可直接进入方案深化")
    if s.discipline == "interior":
        out.append("不动结构与外围护，落地风险低于改造类方案")
    if not out:
        out.append("方向本身成立，但优势取决于后续深化——本轮不夸大")
    return out


def summary_lines(result: Sequence[Dict[str, Any]]) -> List[str]:
    """给报告用的一行式对照：三套到底差在哪。"""
    lines = ["| 方案 | 组织逻辑 | 抓的机会 | 主要代价 |", "|---|---|---|---|"]
    for r in result:
        d = r["deliberation"]
        lines.append("| {} {} | {} | {} | {} |".format(
            r["role"], r["name"], _clip(d["parti"], 40),
            _clip(d["key_opportunity"], 40), _clip(r["tradeoffs"][0], 40)))
    return lines


def _clip(text: str, n: int) -> str:
    t = " ".join(str(text or "").split())
    return t if len(t) <= n else t[: n - 1] + "…"


__all__ = [
    "SIX_QUESTIONS", "Strategy", "STRATEGIES", "ARCHITECTURE", "INTERIOR",
    "LANDSCAPE", "PRECEDENT_TERMS", "SIGNAL_WEIGHT", "FALLBACK_NOTE",
    "applies", "build_strategies", "for_discipline", "for_project", "for_taxonomy", "get",
    "precedent_signals", "summary_lines",
]
