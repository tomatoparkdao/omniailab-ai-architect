"""Project-type intake profiles.

A single questionnaire for every project is the fastest way to make a chief
designer look like a form. A 150 m² flat, a 60-person office and a 40-key
guesthouse are decided by different things, so each type gets its own question
set, its own critical fields and its own benchmark notes.

Design rules encoded here:

* every question names the ``slot`` it fills, so the same answer can never be
  asked twice through two different wordings;
* ``affects`` records the deepest stage the answer can influence — that is what
  decides whether a gap blocks S2 or only S4;
* ``priority`` is about *consequence of not knowing*, not about how nice the
  answer would be to have;
* benchmarks are **reference ranges from the project's own knowledge base**,
  never presented as statutory limits.

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

# --------------------------------------------------------------------------
# information slots — the unit of "do we know this yet"
# --------------------------------------------------------------------------
# weight: how much the slot contributes to overall completeness
# critical: without it, no task brief can claim to be a basis for design
# label: shown to the user, never a code name
SLOTS: Dict[str, Dict[str, object]] = {
    "project_type": {"weight": 3, "critical": True, "label": "项目类型与用途"},
    "location": {"weight": 2, "critical": True, "label": "项目所在地"},
    "floor_area": {"weight": 3, "critical": True, "label": "面积或规模"},
    "occupants": {"weight": 2, "critical": False, "label": "使用者与人数"},
    "needs": {"weight": 3, "critical": True, "label": "核心功能需求"},
    "budget": {"weight": 2, "critical": True, "label": "预算口径"},
    "schedule": {"weight": 1, "critical": False, "label": "工期目标"},
    "drawings": {"weight": 2, "critical": False, "label": "原始图纸"},
    "site_conditions": {"weight": 2, "critical": False, "label": "现场与建筑条件"},
    "structure": {"weight": 2, "critical": False, "label": "结构与机电信息"},
    "style": {"weight": 1, "critical": False, "label": "审美与风格倾向"},
    "deliverable_depth": {"weight": 1, "critical": False, "label": "交付深度"},
}

# Completeness verdicts. Thresholds are deliberately conservative: a brief that
# claims 75% coverage with guesses is worse than an honest 40%.
COMPLETE_AT = 0.75
WORKING_AT = 0.40


@dataclass(frozen=True)
class Question:
    """One interview question, tied to a slot and to the stage it can affect."""

    id: str
    text: str
    slot: str
    priority: str                 # critical | important | deferrable
    affects: str                  # deepest stage this answer can change
    kind: str = "text"            # text | number | enum | bool | list
    options: Tuple[str, ...] = ()
    why: str = ""
    depends_on: str = ""          # another question id
    depends_value: str = ""       # required answer for `depends_on`
    examples: Tuple[str, ...] = ()

    def to_dict(self) -> Dict[str, object]:
        return {
            "id": self.id,
            "text": self.text,
            "slot": self.slot,
            "priority": self.priority,
            "affects": self.affects,
            "kind": self.kind,
            "options": list(self.options),
            "why": self.why,
            "depends_on": self.depends_on,
            "depends_value": self.depends_value,
            "examples": list(self.examples),
        }


@dataclass(frozen=True)
class Benchmark:
    """A reference range taken from the project knowledge base.

    ``source`` is mandatory: a number without a source is an opinion.
    """

    item: str
    value: str
    source: str
    note: str = ""


@dataclass(frozen=True)
class Profile:
    id: str
    label: str
    keywords: Tuple[str, ...]
    focus: str
    questions: Tuple[Question, ...]
    benchmarks: Tuple[Benchmark, ...] = ()
    # Rooms / functional units that this type is normally made of. Used to spot
    # "the brief forgot the obvious", never to fill the brief automatically.
    expected_spaces: Tuple[str, ...] = ()
    metier_notes: Tuple[str, ...] = ()

    def question(self, qid: str) -> Question:
        for q in self.questions:
            if q.id == qid:
                return q
        raise KeyError(qid)

    def to_dict(self) -> Dict[str, object]:
        return {
            "id": self.id,
            "label": self.label,
            "focus": self.focus,
            "questions": [q.to_dict() for q in self.questions],
            "benchmarks": [
                {"item": b.item, "value": b.value, "source": b.source, "note": b.note}
                for b in self.benchmarks
            ],
            "expected_spaces": list(self.expected_spaces),
            "metier_notes": list(self.metier_notes),
        }


# --------------------------------------------------------------------------
# shared questions — asked of every type, worded once
# --------------------------------------------------------------------------
_Q_TYPE = Question(
    id="base.project_type", slot="project_type", priority="critical", affects="S2",
    text="这个项目是什么类型、主要做什么用？",
    kind="enum",
    options=("住宅公寓", "大平层", "别墅", "办公", "酒店民宿", "餐饮", "商业零售",
             "展厅文化", "新建建筑"),
    why="项目类型决定后面问什么。住宅问家庭结构与生活场景，办公问组织结构与会议频率，"
        "问反了等于白问。",
    examples=("150㎡ 大平层，一家三口自住", "800㎡ 办公，60 人"),
)
_Q_LOCATION = Question(
    id="base.location", slot="location", priority="critical", affects="S4",
    text="项目在哪个城市或地区？",
    why="规范体系、气候条件、材料供应与造价水平都跟着地区走；没有地区，"
        "任何造价数字都只是一句空话。",
)
_Q_AREA = Question(
    id="base.floor_area", slot="floor_area", priority="critical", affects="S3",
    text="建筑面积或可设计面积大概多少？是实测、图纸标注，还是口头估计？",
    kind="text",
    why="面积是可行性判断的分母。同时要说清来源——图纸标注与口头估计的可信度差一个等级。",
    examples=("150㎡，购房合同建筑面积", "约 120㎡ 使用面积，中介说的"),
)
_Q_NEEDS = Question(
    id="base.needs", slot="needs", priority="critical", affects="S2",
    text="最想解决的 3 件事是什么？请按重要性说，不要按房间名字说。",
    kind="list",
    why="按房间罗列会漏掉真实用途。同样是「大客厅」，家庭聚会、儿童活动、影音、待客"
        "对空间的要求完全不同。",
    examples=("客厅要能坐下 8 个人吃饭", "孩子写作业要看得见", "主卧要能放衣帽间"),
)
_Q_BUDGET = Question(
    id="base.budget", slot="budget", priority="critical", affects="S4",
    text="预算大概在什么范围？这个数字包含哪些内容（硬装、软装、家电、设计费）？",
    kind="text",
    why="预算口径比金额本身更重要。只说「100 万」而没说含不含软装与家电，"
        "后面必然吵一次。",
    examples=("硬装 80 万，不含家具家电", "总预算 200 万，含设计费"),
)
_Q_SCHEDULE = Question(
    id="base.schedule", slot="schedule", priority="important", affects="S4",
    text="希望什么时候入住或开业？中间有没有必须卡住的时间点？",
    why="工期决定设计深度能做到哪一步。赶工期最常见的代价是施工图仓促、现场改。",
)
_Q_DRAWINGS = Question(
    id="base.drawings", slot="drawings", priority="important", affects="S3",
    text="手上有原始图纸吗？CAD、PDF、照片都算，是哪一种？",
    kind="enum",
    options=("有 CAD/DXF", "有 PDF 图纸", "只有拍照/扫描件", "没有图纸", "不确定"),
    why="图纸格式决定能提取到什么精度。照片只能看关系，量不出尺寸。",
)
_Q_SITE = Question(
    id="base.site_conditions", slot="site_conditions", priority="important",
    affects="S3",
    text="房子或场地现在的状态是什么？毛坯、老房翻新，还是在营业中要改？",
    why="现状决定拆除量、临时设施与施工组织，也决定哪些限制不能碰。",
)
_Q_STRUCTURE = Question(
    id="base.structure", slot="structure", priority="important", affects="S4",
    text="承重墙、梁柱位置清楚吗？有没有结构图纸或物业的限制说明？",
    why="结构不清楚时可以做方案讨论，但不能承诺任何拆改——这是硬边界。",
)
_Q_STYLE = Question(
    id="base.style", slot="style", priority="deferrable", affects="S2",
    text="审美上有明确方向吗？如果没有，也可以说「暂时没想好」。",
    why="风格可以在概念阶段收敛；它不该拖住任务书。",
)
_Q_DEPTH = Question(
    id="base.deliverable_depth", slot="deliverable_depth", priority="deferrable",
    affects="S7",
    text="这次要交付到哪一步：只要方案，还是要施工图？",
    kind="enum",
    options=("只要概念方案", "方案 + 效果图", "方案 + 施工图", "全流程含现场配合", "还没定"),
    why="交付深度决定工作量与责任边界，也决定哪些成果必须有人签字。",
)

BASE_QUESTIONS: Tuple[Question, ...] = (
    _Q_TYPE, _Q_LOCATION, _Q_AREA, _Q_NEEDS, _Q_BUDGET, _Q_SCHEDULE,
    _Q_DRAWINGS, _Q_SITE, _Q_STRUCTURE, _Q_STYLE, _Q_DEPTH,
)


# --------------------------------------------------------------------------
# 1. residential
# --------------------------------------------------------------------------
RESIDENTIAL = Profile(
    id="residential",
    label="住宅 / 公寓 / 别墅",
    keywords=("住宅", "公寓", "大平层", "别墅", "家装", "自住", "户型",
              "residential", "apartment", "villa", "flat", "house"),
    focus="家庭结构、日常行为、生活场景、收纳与隐私，而不是房间数量",
    questions=BASE_QUESTIONS + (
        Question(
            id="res.household", slot="occupants", priority="critical", affects="S3",
            text="常住几口人？年龄大概什么范围？有没有老人、小孩或需要照护的人？",
            why="家庭结构直接决定卧室配置、卫浴数量与无障碍要求，是住宅最关键的一条。",
            examples=("夫妻 + 一个 5 岁孩子", "三代同住，老人 70 岁"),
        ),
        Question(
            id="res.daily_rhythm", slot="needs", priority="critical", affects="S3",
            text="工作日和周末在家最常做的三件事是什么？大概什么时间做？",
            why="使用频率与时段决定空间该靠近谁、该隔音到什么程度。"
                "「偶尔用」和「每天用两小时」是两种设计。",
            examples=("晚上 8 点后全家在客厅看电视", "周末在厨房做一整天饭"),
        ),
        Question(
            id="res.guest", slot="needs", priority="important", affects="S3",
            text="多久会来一次客人？来的时候一般在哪待着、待到多晚？",
            why="待客方式决定公共区要开放到什么程度，也决定要不要独立客卫。",
        ),
        Question(
            id="res.kitchen", slot="needs", priority="important", affects="S3",
            text="厨房怎么用：天天开火、偶尔做、还是基本不开？接受开放式吗？",
            kind="enum",
            options=("天天开火，重油烟", "每周几次", "偶尔", "基本不做饭", "不确定"),
            why="烹饪强度决定厨房是否必须封闭，也决定排烟与补风怎么走。",
        ),
        Question(
            id="res.storage", slot="needs", priority="important", affects="S3",
            text="东西多吗？有没有必须收起来的大件（行李箱、婴儿车、乐器、雪具）？",
            kind="list",
            why="收纳是最容易被图纸忽略、又最容易在入住三个月后爆掉的一项。",
        ),
        Question(
            id="res.work", slot="needs", priority="deferrable", affects="S3",
            text="需要在家办公吗？是偶尔回邮件，还是每天开视频会？",
            why="视频会需要安静与背景控制，和「放张桌子」不是一回事。",
        ),
        Question(
            id="res.future", slot="needs", priority="deferrable", affects="S4",
            text="未来 5–10 年家庭结构可能怎么变（生育、老人同住、孩子离家）？",
            why="能改的房间比不能改的房间值钱。提前知道变化，才知道哪里留余地。",
        ),
        Question(
            id="res.privacy", slot="needs", priority="important", affects="S3",
            text="家里谁需要独处空间？谁的作息和別人不一样？",
            why="作息冲突靠隔音与分区解决，不靠多一个房间解决。",
        ),
    ),
    benchmarks=(
        Benchmark("主卧净宽", "≥3.3 m 时可放双人床 + 两侧通行",
                  "knowledge/human-ergonomics.md", "常见工程惯例，非强制标准"),
        Benchmark("主通道净宽", "1200–1500 mm（双人并行）",
                  "knowledge/human-ergonomics.md"),
        Benchmark("单人通行净宽", "600–750 mm（最低舒适）",
                  "knowledge/human-ergonomics.md"),
        Benchmark("卫浴数量", "主卫 + 客卫为常见配置；三代同住通常需要两个以上",
                  "knowledge/spatial-planning.md", "按人数与早晚高峰校核，非规范条文"),
        Benchmark("收纳占比", "住宅收纳面积占总面积 8–12% 属常见区间",
                  "knowledge/interior-design-methodology.md", "按家庭物品量校核"),
    ),
    expected_spaces=("玄关", "客厅", "餐厅", "厨房", "主卧", "次卧", "卫生间", "储藏"),
    metier_notes=(
        "住宅的核心冲突不是「房间不够」，而是「动线与作息打架」。",
        "先问行为再问房间：房间是行为的结果，不是起点。",
        "收纳与家务动线要当独立系统设计，不能当剩余空间填。",
    ),
)

# --------------------------------------------------------------------------
# 2. office
# --------------------------------------------------------------------------
OFFICE = Profile(
    id="office",
    label="办公空间",
    keywords=("办公", "办公室", "写字楼", "工位", "总部", "office", "workplace"),
    focus="组织结构、会议频率、专注与协作的比例、增长弹性",
    questions=BASE_QUESTIONS + (
        Question(
            id="off.headcount", slot="occupants", priority="critical", affects="S3",
            text="现在多少人在这里办公？未来两年计划扩到多少？",
            why="工位数是办公面积的分子，增长计划决定要不要预留弹性区。",
            examples=("现在 40 人，一年内到 60 人"),
        ),
        Question(
            id="off.org", slot="needs", priority="critical", affects="S3",
            text="组织怎么分部门？哪些部门必须挨着，哪些必须分开？",
            why="部门关系决定分区，比「要几个会议室」重要得多。",
        ),
        Question(
            id="off.work_mode", slot="needs", priority="critical", affects="S3",
            text="大家主要是坐下写东西，还是开会、讨论、打电话多？比例大概怎样？",
            why="专注与协作的比例决定开放区与封闭区的配比；配反了，会议室永远不够、"
                "工位永远空着。",
            examples=("70% 专注 / 30% 讨论", "销售团队一天到晚打电话"),
        ),
        Question(
            id="off.meeting", slot="needs", priority="important", affects="S3",
            text="一天大概多少场会？最大的一场多少人？有没有客户来访的正式接待？",
            why="会议室的规格与数量按真实会议分布定，不按「每 10 人一间」这类经验值硬套。",
        ),
        Question(
            id="off.visitor", slot="needs", priority="important", affects="S3",
            text="访客多吗？访客需要进到办公区里面吗？",
            why="访客动线决定前台与门禁怎么设，也决定哪些区域要能被「看见但不进入」。",
        ),
        Question(
            id="off.facility", slot="needs", priority="important", affects="S4",
            text="有没有特殊空间需求：机房、实验室、直播间、打印区、茶水与餐区？",
            kind="list",
            why="这些空间对荷载、供电、排风、净高有硬要求，方案阶段不预留后面改不动。",
        ),
        Question(
            id="off.lease", slot="site_conditions", priority="important", affects="S4",
            text="是自有还是租赁？物业对隔墙、消防、空调、门禁有什么限制？",
            why="租赁物业的限制经常直接否掉一个方案，越早知道越省事。",
        ),
        Question(
            id="off.brand", slot="style", priority="deferrable", affects="S2",
            text="办公空间要不要对外体现品牌形象？有 VI 或色彩规范吗？",
            why="品牌要求影响材料档次与公共区投入比例。",
        ),
    ),
    benchmarks=(
        Benchmark("人均使用面积", "开放式办公常见 8–12 m²/人，含走道与共享区更高",
                  "knowledge/spatial-planning.md", "按工位类型与协作比例校核"),
        Benchmark("会议区配比", "会议与协作面积占总面积 20–30% 属常见区间",
                  "knowledge/spatial-planning.md"),
        Benchmark("公共走廊净宽", "1.5–2.4 m（按人流）",
                  "knowledge/architectural-design-principles.md"),
        Benchmark("工位净距", "背靠背工位之间按椅背通行校核",
                  "knowledge/human-ergonomics.md"),
        Benchmark("机房与设备", "按设备散热与检修通道校核，须机电专业确认",
                  "knowledge/building-systems-coordination.md"),
    ),
    expected_spaces=("前台", "开放办公区", "会议室", "专注室", "茶水区", "打印区", "卫生间"),
    metier_notes=(
        "办公设计的核心是「协作密度」，不是「工位密度」。",
        "会议室不够往往不是数量问题，而是开放区太吵、没有电话间。",
        "租赁物业的限制要先问，否则方案会在消防与空调上返工。",
    ),
)

# --------------------------------------------------------------------------
# 3. hospitality
# --------------------------------------------------------------------------
HOSPITALITY = Profile(
    id="hospitality",
    label="酒店 / 民宿",
    keywords=("酒店", "民宿", "客栈", "度假", "客房", "hotel", "resort",
              "guesthouse", "hostel"),
    focus="目标客群、运营定位、客房结构、服务动线与后勤效率",
    questions=BASE_QUESTIONS + (
        Question(
            id="hos.positioning", slot="needs", priority="critical", affects="S3",
            text="这个店卖给谁？客人为什么选它而不是隔壁？",
            why="定位决定客房面积、公区比例与材料档次；定位不清，后面每个决定都会摇摆。",
            examples=("周末周边游的年轻情侣", "商务出差，要能开发票"),
        ),
        Question(
            id="hos.keys", slot="floor_area", priority="critical", affects="S3",
            text="计划做多少间客房？房型怎么配（大床、双床、套房）？",
            why="客房数与房型配比是运营模型的基础，也决定公区面积的上限。",
        ),
        Question(
            id="hos.operation", slot="needs", priority="critical", affects="S4",
            text="谁在运营？前台、早餐、保洁是自营还是外包？",
            why="运营方式决定后勤面积与流线；外包与自营对后场的要求完全不同。",
        ),
        Question(
            id="hos.service", slot="needs", priority="important", affects="S3",
            text="提供哪些服务：早餐、咖啡、酒吧、洗衣、接送？",
            kind="list",
            why="每多一项服务就多一条动线与一块后场，不能只在图上加个房间。",
        ),
        Question(
            id="hos.back_of_house", slot="needs", priority="important", affects="S4",
            text="布草、垃圾、货物怎么进出？有没有独立的后场通道？",
            why="客人与后勤动线交叉是酒店最常见的硬伤，改造代价极高。",
        ),
        Question(
            id="hos.sound", slot="needs", priority="important", affects="S4",
            text="客房之间、客房与公区之间的隔音要求高吗？",
            why="隔音是住宿体验的第一投诉项，且必须在隔墙做法里解决。",
        ),
        Question(
            id="hos.regulation", slot="structure", priority="important", affects="S7",
            text="有没有特种行业许可、消防与卫生的前置要求？",
            why="住宿业的报批门槛比家装高，方案要能过审才有意义。",
        ),
    ),
    benchmarks=(
        Benchmark("客房净面积", "经济型 18–22 m²、舒适型 25–35 m² 属常见区间",
                  "knowledge/spatial-planning.md", "按定位与房价带校核，非标准"),
        Benchmark("公区与客房面积比", "按定位差异很大，须与运营模型一起定",
                  "knowledge/spatial-planning.md"),
        Benchmark("走廊净宽", "客房层走廊按行李与推车通行校核",
                  "knowledge/human-ergonomics.md"),
        Benchmark("隔声", "客房隔墙与楼板做法按住宿业通行要求执行",
                  "knowledge/interior-design-methodology.md", "具体指标以当地规范为准"),
    ),
    expected_spaces=("入口大堂", "前台", "客房", "布草间", "后勤通道", "早餐厅", "公共卫生间"),
    metier_notes=(
        "酒店设计的第一约束是运营，不是审美。",
        "客房数与公区面积是一对跷跷板，靠定位平衡。",
        "后勤动线必须在平面上先跑通，再谈材料与氛围。",
    ),
)

# --------------------------------------------------------------------------
# 4. retail / F&B
# --------------------------------------------------------------------------
RETAIL = Profile(
    id="retail",
    label="餐饮 / 商业零售",
    keywords=("餐饮", "餐厅", "咖啡", "咖啡店", "酒吧", "零售", "商铺", "门店",
              "商业", "retail", "restaurant", "cafe", "bar", "shop", "fnb"),
    focus="目标消费者、营业模式、客流与坪效、后场与设备",
    questions=BASE_QUESTIONS + (
        Question(
            id="ret.positioning", slot="needs", priority="critical", affects="S3",
            text="卖给谁？客单价大概多少？客人是快速吃完走，还是坐着待很久？",
            why="翻台率与停留时长直接决定座位数与面积配比，是商业设计的第一道算术。",
            examples=("工作日午市白领，客单 45 元，40 分钟吃完", "周末下午咖啡，坐两小时"),
        ),
        Question(
            id="ret.turnover", slot="needs", priority="critical", affects="S3",
            text="预计一天多少客流？高峰期集中在什么时段？",
            why="峰值客流决定厨房产能、卫生间数量与排队区，而不是平均客流。",
        ),
        Question(
            id="ret.menu", slot="needs", priority="critical", affects="S4",
            text="菜单结构大概是什么？有没有明火、油烟、冷藏、制冰的大设备？",
            kind="list",
            why="设备清单决定后场面积、供电容量与排烟路径；菜单改了厨房就得重做。",
        ),
        Question(
            id="ret.back_of_house", slot="needs", priority="important", affects="S4",
            text="后场怎么安排：备餐、洗碗、储藏、员工更衣与休息？",
            why="后场面积被压缩是餐饮失败的高频原因，且营业后无法补救。",
        ),
        Question(
            id="ret.regulation", slot="structure", priority="important", affects="S7",
            text="排烟、隔油、消防、食品经营许可有什么前置条件？",
            why="餐饮的排烟与隔油往往是审批卡点，方案阶段必须确认可行性。",
        ),
        Question(
            id="ret.facade", slot="style", priority="important", affects="S4",
            text="门头与橱窗能改吗？物业或街区对招牌有什么限制？",
            why="门头是商业的第一媒体，但经常受物业与街区导则限制。",
        ),
        Question(
            id="ret.brand", slot="style", priority="deferrable", affects="S2",
            text="有品牌视觉系统吗（标志、色彩、字体）？",
            why="有 VI 时设计要服从它；没有时设计要顺手建立一套。",
        ),
    ),
    benchmarks=(
        Benchmark("餐位面积", "正餐 1.5–2.0 m²/座、快餐 1.0–1.4 m²/座属常见区间",
                  "knowledge/spatial-planning.md", "按业态与停留时长校核，非标准"),
        Benchmark("后场占比", "餐饮后场占总面积 25–35% 属常见区间",
                  "knowledge/spatial-planning.md", "低于此值通常会在运营中暴露"),
        Benchmark("通道净宽", "服务通道与客人通道宜分开，净宽按推车与错身校核",
                  "knowledge/human-ergonomics.md"),
        Benchmark("排烟与补风", "必须与机电专业共同确认，不得凭经验估算",
                  "knowledge/building-systems-coordination.md"),
    ),
    expected_spaces=("入口与等候", "用餐区", "吧台", "厨房", "洗碗间", "储藏", "员工区",
                     "卫生间"),
    metier_notes=(
        "商业空间先算账再画图：座位数 × 翻台 × 客单 = 营业额上限。",
        "后场是商业设计的良心，压缩它的方案通常在半年内出问题。",
        "排烟、隔油、消防是审批硬门槛，不是设计可选项。",
    ),
)

# --------------------------------------------------------------------------
# 5. exhibition / culture / public
# --------------------------------------------------------------------------
EXHIBITION = Profile(
    id="exhibition",
    label="展厅 / 文化与公共空间",
    keywords=("展厅", "展陈", "博物馆", "美术馆", "文化", "图书", "公共空间",
              "exhibition", "gallery", "museum", "cultural"),
    focus="叙事顺序、人流组织、展品保护与公共安全",
    questions=BASE_QUESTIONS + (
        Question(
            id="exh.story", slot="needs", priority="critical", affects="S3",
            text="观众进来后应该按什么顺序看？想让他最后记住什么？",
            why="展陈是叙事，不是摆东西。顺序决定动线、分区与视线控制。",
        ),
        Question(
            id="exh.flow", slot="needs", priority="critical", affects="S3",
            text="预计同时在场多少人？是自由参观还是有讲解带队？",
            why="峰值人数决定通道宽度、疏散与停留节点，也决定讲解动线怎么让开。",
        ),
        Question(
            id="exh.collection", slot="needs", priority="important", affects="S4",
            text="展品是什么类型？有没有对温湿度、照度、紫外敏感的东西？",
            kind="list",
            why="展品保护要求会直接改写照明方案与空调系统，后期无法补救。",
        ),
        Question(
            id="exh.technical", slot="structure", priority="important", affects="S4",
            text="有没有大型展具、悬挂、投影或声光电设备？荷载与供电怎么解决？",
            why="悬挂与大型展具涉及结构安全，必须由结构专业确认。",
        ),
        Question(
            id="exh.safety", slot="structure", priority="critical", affects="S7",
            text="疏散、消防、无障碍有没有已知的硬性要求？",
            why="公共空间的安全要求高于住宅与办公，须按当地规范执行并由持证人员复核。",
        ),
        Question(
            id="exh.operation", slot="needs", priority="deferrable", affects="S3",
            text="展期多长？以后要不要换展？",
            why="短期展与常设展对材料与构造的要求完全不同。",
        ),
    ),
    benchmarks=(
        Benchmark("观众通道净宽", "按峰值人流与疏散计算，不得只按日常参观估算",
                  "knowledge/architectural-design-principles.md", "以现行规范为准"),
        Benchmark("观展距离", "大幅面展品需留出后退观看距离，按画幅高度校核",
                  "knowledge/human-ergonomics.md"),
        Benchmark("展品照度", "按展品材质分级控制，敏感材质须限紫外",
                  "knowledge/lighting-design.md", "具体指标以保护要求为准"),
        Benchmark("疏散与无障碍", "公共空间按当地规范执行，须持证人员复核",
                  "knowledge/design-review-checklists.md"),
    ),
    expected_spaces=("入口序厅", "主展区", "次要展区", "休息区", "服务台", "储藏与布展通道",
                     "公共卫生间"),
    metier_notes=(
        "展陈设计先写脚本再排平面：观众走一遍，故事才成立。",
        "展品保护要求会反过来决定照明与空调，不能最后补。",
        "公共安全的结论必须由持证专业人员签署，不在本系统结论范围。",
    ),
)

# --------------------------------------------------------------------------
# 6. new building
# --------------------------------------------------------------------------
ARCHITECTURE = Profile(
    id="architecture",
    label="新建建筑项目",
    keywords=("新建", "建筑", "自建", "盖房", "宅基地", "园区", "楼", "building",
              "new build", "architecture"),
    focus="用途与规模、用地与规划条件、交通组织、报批与专业协作范围",
    questions=BASE_QUESTIONS + (
        Question(
            id="arc.use", slot="needs", priority="critical", affects="S2",
            text="这栋楼建成后做什么用？有没有混合功能？",
            why="用途决定规范体系、荷载、疏散与设备标准，混用还要处理分区。",
        ),
        Question(
            id="arc.scale", slot="floor_area", priority="critical", affects="S3",
            text="计划建几层、总建筑面积多少、檐口高度大概多少？",
            why="规模与高度直接触发不同的审批与消防要求。",
        ),
        Question(
            id="arc.plot", slot="site_conditions", priority="critical", affects="S3",
            text="用地红线、退界、容积率、限高这些规划条件清楚吗？",
            why="规划条件是设计的边界条件，不清楚就无法判断方案能不能报批。",
        ),
        Question(
            id="arc.access", slot="site_conditions", priority="important", affects="S3",
            text="场地怎么进出？消防车道、停车、货运能不能满足？",
            why="交通组织经常是报批的卡点，也决定总平面的基本形态。",
        ),
        Question(
            id="arc.geotech", slot="structure", priority="important", affects="S4",
            text="有没有地勘报告？地基条件、地下水位了解吗？",
            why="没有地勘就无法确定基础形式，也无法控制造价风险。",
        ),
        Question(
            id="arc.approval", slot="structure", priority="critical", affects="S7",
            text="报批流程走到哪一步？立项、规划许可、施工许可分别是什么状态？",
            why="报批状态决定设计能做到哪个深度，也决定哪些图纸必须报审。",
        ),
        Question(
            id="arc.consultants", slot="deliverable_depth", priority="important",
            affects="S7",
            text="结构、机电、幕墙、景观这些专业由谁负责？边界怎么划？",
            why="专业协作边界不清，最后一定会在图纸交接处出问题。",
        ),
    ),
    benchmarks=(
        Benchmark("退界与间距", "按当地规划管理技术规定执行，不得凭经验推算",
                  "knowledge/architectural-design-principles.md", "以现行规定为准"),
        Benchmark("消防车道", "净宽 4.0 m 起，转弯半径按消防车型校核",
                  "knowledge/architectural-design-principles.md", "以现行规范为准"),
        Benchmark("层高与净高", "按设备与吊顶需求倒推，先定净高再定层高",
                  "knowledge/building-systems-coordination.md"),
        Benchmark("得房率", "可租售或可使用面积与建筑面积之比，须注明是否含公摊",
                  "knowledge/architectural-design-principles.md"),
    ),
    expected_spaces=("入口", "门厅", "主要功能空间", "垂直交通", "设备用房", "卫生间"),
    metier_notes=(
        "建筑项目的顺序是：先规划条件，再体量，再平面，最后立面。",
        "报批状态是硬约束，不是设计后期才考虑的事。",
        "结构、机电、幕墙必须由相应专业签署，不在本系统结论范围。",
    ),
)


PROFILES: Dict[str, Profile] = {
    p.id: p for p in (RESIDENTIAL, OFFICE, HOSPITALITY, RETAIL, EXHIBITION, ARCHITECTURE)
}

# Question lookup across every profile (ids are globally unique by prefix).
#: 专业专属问题：只有该专业在范围内时才问。
#: 内容刻意只问"影响下一步能做什么"的事，不追求把专业问全。
SCOPE_QUESTIONS: Tuple[Question, ...] = (
    Question(
        id="scope.structure_type", slot="structure_detail",
        text="结构这块：是只做局部加固、要拆改承重构件，还是新建结构？现有结构图纸有吗？",
        priority="critical", affects="S3",
        why="决定结构专业是咨询、复核还是必须出计算书",
        examples=("只加固梁", "要拆一面承重墙", "加夹层钢结构"),
    ),
    Question(
        id="scope.mep_depth", slot="mep_depth",
        text="机电要做到什么深度：只要点位与容量核对，还是要出系统图与管综？",
        priority="important", affects="S7",
        why="决定机电是配合提资还是独立出图",
        examples=("只要点位", "要出管综", "消防单独分包"),
    ),
    Question(
        id="scope.landscape_program", slot="outdoor_program",
        text="室外这块主要要什么：铺装与动线、种植、水景，还是屋顶花园？",
        priority="important", affects="S3",
        why="景观方案的分区与工程量都从这里来",
        examples=("铺装+种植", "要水景", "屋顶花园"),
    ),
    Question(
        id="scope.planning_approval", slot="approval",
        text="这个项目需要报建或报批吗？有没有已知的容积率、退线、限高要求？",
        priority="critical", affects="S3",
        why="涉及法定指标，缺了就不能承诺方案可报",
        examples=("需要报建", "已有规划条件", "不用报"),
    ),
)

QUESTION_INDEX: Dict[str, Question] = {}
for _p in PROFILES.values():
    for _q in _p.questions:
        QUESTION_INDEX.setdefault(_q.id, _q)
for _q in SCOPE_QUESTIONS:
    QUESTION_INDEX.setdefault(_q.id, _q)

# Slot -> question ids, used to decide "already answered elsewhere".
SLOT_QUESTIONS: Dict[str, List[str]] = {}
for _q in QUESTION_INDEX.values():
    SLOT_QUESTIONS.setdefault(_q.slot, []).append(_q.id)

PRIORITY_ORDER = {"critical": 0, "important": 1, "deferrable": 2}


def profile_for(*texts: str) -> Profile:
    """Pick the profile that best matches the given text.

    Falls back to residential only when nothing matches *and* the text looks
    like a dwelling; otherwise architecture, because "we don't know yet" should
    ask the widest questions rather than the narrowest.
    """
    blob = " ".join(t for t in texts if t).lower()
    if not blob.strip():
        return ARCHITECTURE
    best: Optional[Tuple[int, Profile]] = None
    for p in PROFILES.values():
        hits = sum(1 for k in p.keywords if k.lower() in blob)
        if hits and (best is None or hits > best[0]):
            best = (hits, p)
    if best:
        return best[1]
    if any(w in blob for w in ("住", "家", "㎡", "平米", "平层", "房")):
        return RESIDENTIAL
    return ARCHITECTURE


def slots_for(profile: Profile) -> List[str]:
    """Slots this profile cares about, in slot-registry order."""
    used = {q.slot for q in profile.questions} | {"project_type", "location",
                                                  "floor_area", "needs", "budget"}
    return [s for s in SLOTS if s in used]


def critical_slots(profile: Profile) -> List[str]:
    return [s for s in slots_for(profile) if SLOTS[s]["critical"]]
