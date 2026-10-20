"""行业推敲：从数据和矛盾推出组织方式，而不是套固定句子。

一条 `Move` 必须能回答三件事：

1. 它用的是哪几个数（`uses`）——没有数字支撑的方向不写；
2. 它解决哪条矛盾（`answers`）——解决不了矛盾的"方向"只是换个说法；
3. 它要付什么代价（`costs`）——代价写得出来的方案才可信。

方向本身不承诺合规：医院的手术部流程、学校的办学标准、厂房的工艺，
最终仍由相应专业与主管部门判定。

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Sequence, Tuple

from .brief import SectorBrief


@dataclass
class Move:
    name: str
    parti: str                       # 一句话的组织逻辑（含数）
    why: str                         # 为什么适用于这个项目（对应哪条矛盾）
    massing: str = ""
    section: str = ""
    circulation: str = ""
    facade: str = ""
    daylight: str = ""
    materials: str = ""
    sequence: Tuple[Tuple[str, str, str], ...] = ()
    technical: Tuple[str, ...] = ()
    costs: Tuple[str, ...] = ()
    risks: Tuple[str, ...] = ()
    family: str = "cluster"
    diagram: str = "zoning"
    #: S3 用：房间带顺序（从入口到后场）。空表示由程序按 zone 推。
    bands: Tuple[str, ...] = ()
    uses: Tuple[str, ...] = ()       # 用到的输入键
    answers: Tuple[str, ...] = ()    # 回应哪几条矛盾（前缀匹配即可）

    def to_dict(self) -> Dict[str, object]:
        return {
            "name": self.name, "parti": self.parti, "why": self.why,
            "massing": self.massing, "section": self.section,
            "circulation": self.circulation, "facade": self.facade,
            "daylight": self.daylight, "materials": self.materials,
            "sequence": [list(x) for x in self.sequence],
            "technical": list(self.technical), "costs": list(self.costs),
            "risks": list(self.risks), "family": self.family,
            "diagram": self.diagram, "bands": list(self.bands),
            "uses": list(self.uses), "answers": list(self.answers),
        }


def _n(b: SectorBrief, key: str, default: float = 0.0) -> float:
    return b.get(key, default)


def _m2(v: float) -> str:
    return f"{v:,.0f} m²"


# --------------------------------------------------------------------------
# 教育
# --------------------------------------------------------------------------
def _education(b: SectorBrief) -> List[Move]:
    classes = _n(b, "classes")
    students = _n(b, "students")
    teaching = _n(b, "teaching_m2")
    canteen = _n(b, "canteen_m2")
    gym = _n(b, "gym_m2")
    total = _n(b, "building_m2")
    site = _n(b, "site_area")
    far = _n(b, "far")
    per_class = students / classes if classes else 45.0
    floors = max(1.0, round(total / max(teaching / max(floors_guess(classes), 1), 1)))
    # 组团按"年级组"分，2–3 组最常用；分太多等于没有组团
    groups = max(2.0, min(3.0, round(classes / 8.0) or 2.0))

    out: List[Move] = []
    out.append(Move(
        name="教学组团 · 共享中庭",
        parti=(f"{classes:.0f} 班拆成 {groups:.0f} 个组团，每组约 {classes / groups:.0f} 班"
               f"（{teaching / groups:,.0f} m² 教室），组团之间用一个共享中庭串起来"),
        why=(f"每班 {per_class:.0f} 人、共 {students:.0f} 人，课间十分钟要完成的换场是"
             f"「教室→专用教室→厕所」三点。把专用教室放在中庭边上，{groups:.0f} 个组团"
             "都能在 1 层内到达，不用穿过别的年级"),
        massing=(f"教学区 {teaching:,.0f} m² 分 {groups:.0f} 栋（每栋 "
                 f"{max(2.0, round(teaching / groups / 600)):.0f} 层），中庭在中间；"
                 + (f"食堂 {_m2(canteen)} 与体育馆 {_m2(gym)} 作为独立体量贴场地边缘"
                    if canteen or gym else "配套体量贴场地边缘")),
        section=(f"中庭做通高（{max(6.0, round(students / 100)):.0f} m 量级），"
                 "顶部采光；教室层高按 3.9 m 控制，走廊一侧留观察窗"),
        circulation="主入口 → 中庭（集散）→ 各年级组团；后勤与食堂货运另设一个次入口",
        facade="普通教室朝南或东，专业教室可朝北；山墙少开窗以控制夏季得热",
        daylight=f"教室窗地比不低于 1:5；中庭补足进深中段的采光",
        sequence=(("到达", "从校门看见中庭，人流在此分流", "集散中庭"),
                  ("上课", f"进入本年级组团，{classes / groups:.0f} 间教室围绕共享空间", "组团"),
                  ("课间", f"专用教室与厕所都在 {groups:.0f} 个组团的服务半径内", "短路径")),
        technical=("食堂需独立排烟与隔油；体育馆大跨需结构配合",),
        costs=(f"中庭占了 {max(120.0, students * 0.25):,.0f} m² 建筑面积但不排课，"
               "折算进容积率；组团式比单栋长条多出 2 处楼梯与卫生间"),
        risks=("组团式对场地宽度有要求：地块进深不足 60 m 时组团会被压成一条",),
        family="cluster", diagram="zoning",
        bands=("teaching", "special", "office", "service"),
        uses=("classes", "students", "teaching_m2"),
        answers=("容积率", "建筑密度"),
    ))
    out.append(Move(
        name="线性教学楼 · 连廊串联",
        parti=(f"{classes:.0f} 间普通教室排成一条（按 8.4 m 开间计约 "
               f"{classes * 8.4:,.0f} m 长），专用教室与办公挂在连廊北侧"),
        why=(f"用地进深有限时，一条 {classes * 8.4:,.0f} m 的线形教学楼最省造价；"
             "连廊同时是雨天通道与临时展示面，比分散布置少 2 部楼梯"),
        massing=(f"主体量 {classes * 8.4:,.0f} m × 18 m，{max(1.0, round(teaching / (classes * 8.4 * 18), 1)):.0f} 层；"
                 "连廊在教室北侧，宽 3 m"),
        section="教室单侧采光，进深控制在 7.5 m 以内；连廊侧设高窗补光",
        circulation=f"入口在长边中部，到最远教室约 {classes * 8.4 / 2:,.0f} m（步行 "
                    f"{classes * 8.4 / 2 / 60:.1f} 分钟）",
        facade="长向立面重复开窗，端部做楼梯与卫生间实墙",
        daylight="单侧采光，进深超 7.5 m 的部分需要高窗或导光",
        sequence=(("到达", "校门正对连廊中段", "中段入口"),
                  ("上课", f"沿连廊走 {classes * 8.4 / 4:,.0f} m 到本班", "连廊"),
                  ("课间", "专用教室集中在连廊两端", "端部")),
        technical=("长向温度变形需设变形缝或后浇带",),
        costs=(f"走廊面积约 {classes * 8.4 * 3:,.0f} m²，比组团式多 30% 以上；"
               "但结构规整、单价低"),
        risks=("最远教室到厕所超过 60 m 时，课间使用会很紧张",),
        family="linear", diagram="zoning",
        bands=("teaching", "special", "office", "service"),
        uses=("classes", "teaching_m2"),
        answers=("容积率",),
    ))
    out.append(Move(
        name="校园社区化 · 公共临街",
        parti=((f"体育馆 {_m2(gym)}、" if gym else "体育馆与报告厅") +
               f"报告厅与图书馆沿街独立成区，{classes:.0f} 班教学区退到内部"),
        why=("学校同时承担社区功能时（周末开放、家长接送、社会考试），"
             "先把「哪些能对外开放」切出来，教学区才能做成封闭管理。"
             "这一条只在客户明确提到对外开放/社区使用时才成立"),
        massing="临街一排公共体量 + 内部教学院落；两者之间用围墙与门禁分开",
        section="公共体量做通高门厅，独立疏散；教学区按普通层高",
        circulation="社会流线沿街直接进入公共体量，不穿越校园；学生流线从侧门进入教学区",
        facade="临街面更公共（玻璃、雨棚），教学区界面收实",
        daylight="公共体量可大面玻璃，教学区按教室采光标准",
        sequence=(("到达", "从街上直接进入体育馆/报告厅", "临街门厅"),
                  ("分流", "学生从侧门进教学区，与访客分开", "门禁"),
                  ("上课", "教学区内部自成一体", "院落")),
        technical=("对外开放区域需独立计量水电与安防",),
        costs=("多一套门禁与管理人员；临街体量退线要满足疏散与噪声要求",),
        risks=("社区化运营会带来停车与噪声压力，须先有运营方案",),
        family="courtyard", diagram="zoning",
        bands=("public", "teaching", "special", "office", "service"),
        uses=("classes", "gym_m2"),
        answers=("建筑密度",),
    ))
    return out


def floors_guess(classes: float) -> float:
    """班级数推层数的粗算：每层 6–8 班是常见容量。"""
    return max(2.0, min(5.0, round(classes / 8.0) or 2.0))


# --------------------------------------------------------------------------
# 医疗
# --------------------------------------------------------------------------
def _healthcare(b: SectorBrief) -> List[Move]:
    beds = _n(b, "beds")
    op = _n(b, "outpatient")
    total = _n(b, "building_m2")
    tech = _n(b, "tech_m2")
    ors = _n(b, "ors")
    icu = _n(b, "icu_beds")
    units = _n(b, "opd_units")
    spec = b.signals.get("specialties") or []

    return [
        Move(
            name="医技居中 · 门诊环绕",
            parti=(f"医技部（{_m2(tech)}，含 {ors:.0f} 间手术室与 {icu:.0f} 床 ICU）放在"
                   f"首层与二层中央，{units:.0f} 个门诊单元围绕它排列，住院部在其上方"),
            why=(f"日门诊 {op:.0f} 人、{beds:.0f} 床，最频繁的路径是「挂号→检查→回诊」。"
                 "医技居中能把这条路径压到同一楼层内完成；放在端部，"
                 f"每天要多走 {op * 0.4:,.0f} 人次的长距离"),
            massing=(f"裙房 {max(2.0, round((total - _n(b, 'ward_m2')) / max(total / 4, 1))):.0f} 层做门诊+医技，"
                     f"主楼做住院（{_m2(_n(b, 'ward_m2'))}）；裙房进深按医技设备需求定"),
            section=(f"手术部与 ICU 贴在一起（{ors:.0f} 间手术室 → {icu:.0f} 床 ICU 的转运"
                     "距离控制在 50 m 内），中间设专用医梯"),
            circulation="门诊人流从南侧广场进；急诊与发热门诊独立入口；住院探视从另一侧；污物走专用梯",
            facade="门诊面用大玻璃与遮阳，住院面按病房开窗模数",
            daylight=f"候诊区需要自然光，{_n(b, 'waiting_m2'):,.0f} m² 候诊不宜全在暗处",
            sequence=(("到达", "门诊广场 → 挂号/自助 → 分诊", "门诊大厅"),
                      ("检查", "从诊室到医技在同一层完成", "医技核心"),
                      ("住院", "需要住院的经医梯上到病房层", "住院主楼")),
            technical=("手术部需独立净化空调与医用气体；影像需屏蔽与荷载配合",),
            costs=("医技居中会让裙房进深加大、暗房间增多，机械通风与照明成本上升",),
            risks=("本条不含医疗工艺结论：手术部、ICU、产房、负压病房的流程须医疗工艺顾问确认",
                   "洁污分流需两端各留一部污物梯，否则只能靠管理弥补"),
            family="radial", diagram="zoning",
            bands=("public", "outpatient", "tech", "ward"),
            uses=("beds", "outpatient", "tech_m2"),
            answers=("洁污", "门诊"),
        ),
        Move(
            name="洁污双廊 · 模块化单元",
            parti=(f"每条走廊只管一件事：一条洁净（医护、病人、洁净供应），一条污物"
                   f"（污衣、垃圾、遗体）。{units:.0f} 个门诊单元做成同一模块，"
                   "每个模块 12 m 宽 × 一个柱网进深"),
            why=("床位与门诊量都上规模后，靠管理维持洁污分离不可靠；"
                 "做成双廊，污物永远不与病人同一条走廊。"
                 "模块化让科室调整时只换标识，不动管线"),
            massing=f"规整柱网（建议 8.4 m）的板式或 L 形；{beds:.0f} 床分 "
                    f"{max(1.0, round(beds / 50)):.0f} 个护理单元，每单元 50 床左右",
            section="每层净高按设备管线留 4.2 m；污物梯与洁梯成对布置在两端",
            circulation="医护从洁廊进入，病人从候诊进入，污物从污廊离开；三条线不交叉",
            facade="按护理单元开窗，病房面避免西晒",
            daylight="病房窗地比 1:6 以上；护士站能看见病房门",
            sequence=(("到达", "分诊台先分流：普通/发热/急诊", "分诊"),
                      ("就诊", "进入模块化单元，检查在单元内或同层", "单元"),
                      ("离开", "取药与离院动线不逆行", "出口")),
            technical=("双廊意味着每层多一条 2.4 m 走廊，建筑面积增加约 8–10%",),
            costs=(f"按 {total:,.0f} m² 计，双廊多出约 {total * 0.09:,.0f} m² 的交通面积，"
                   "但换来的是可运营的洁污分离"),
            risks=("双廊对进深要求高：进深不足 30 m 时两条走廊会挤掉房间",),
            family="grid", diagram="functional",
            bands=("outpatient", "tech", "ward", "service"),
            uses=("beds", "outpatient"),
            answers=("洁污",),
        ),
        Move(
            name="诊疗街 · 水平发展",
            parti=(f"用一条 {op * 0.06:,.0f} m 长的室内「诊疗街」串起 {units:.0f} 个单元，"
                   f"医技放在街的中段，住院部从街的端部垂直上去"),
            why=("用地较宽、限高较严时，水平展开比竖向叠加更好用："
                 "病人不用换电梯，科室也能按街段分期开放"),
            massing=f"2–3 层裙房沿诊疗街展开，住院塔楼落在街端；总建筑量 {_m2(total)}",
            section="诊疗街做通高采光顶，两侧单元进深 12–15 m",
            circulation="一条主街 + 分支单元；急救车从街的另一端直接到急诊",
            facade="街的端部做大玻璃，作为识别点",
            daylight="采光顶补足街内照度，减少白天照明",
            sequence=(("到达", "进入诊疗街，挂号沿街布置", "街口"),
                      ("就诊", "按街段找科室，不需要换层", "街段"),
                      ("检查", "医技在街中段，步行 3 分钟内", "中段")),
            technical=("采光顶需考虑消防排烟与夏季得热",),
            costs=(f"水平发展的占地是竖向方案的 {max(1.4, 1.0):.1f} 倍以上，"
                   "用地成本会转到室外工程"),
            risks=("街太长会出现「找不到科室」，需要靠分段命名与色彩导视",),
            family="linear", diagram="circulation",
            bands=("public", "outpatient", "tech", "service"),
            uses=("outpatient", "opd_units"),
            answers=("门诊",),
        ),
    ]


# --------------------------------------------------------------------------
# 工业
# --------------------------------------------------------------------------
def _industrial(b: SectorBrief) -> List[Move]:
    area = _n(b, "area")
    bay = _n(b, "bay", 8.4)
    annex = _n(b, "annex_m2")
    docks = _n(b, "docks")
    process = b.signals.get("process") or []
    flow = "→".join(process[:6]) if process else "（工艺顺序未给）"
    clean = any(w in " ".join(process) for w in ("洁净", "无尘"))

    return [
        Move(
            name="工艺流线主导 · 单层大跨",
            parti=(f"按 {flow} 的顺序从一端排到另一端：{area:,.0f} m² 单层，"
                   f"柱网 {bay:.1f} × {bay:.1f} m，约 {max(1.0, round(area / (bay * bay))):.0f} 个柱格"),
            why=(f"客户给出的工序是 {flow}：单层能让物料只走一个方向，"
                 f"{docks:.0f} 个卸货位全部集中在出货端，避免回头运输"),
            massing=(f"主厂房 {area:,.0f} m² 单层（檐高按工艺定），"
                     f"办公与生活配套 {annex:,.0f} m² 贴在入口侧，与生产区分开"),
            section="单层大跨，屋面设采光带与排烟窗；设备基础单独出图",
            circulation=f"原料从一端进，成品从另一端出；{docks:.0f} 个装卸位不与人流交叉",
            facade="生产面以功能为主（通风、采光带），办公面才做形象",
            daylight="屋面采光带按工艺需求，避免直射影响精密工段",
            sequence=(("到达", "货车进入装卸区，司机不进入生产区", "装卸场"),
                      ("生产", f"沿 {flow} 单向流动", "主厂房"),
                      ("出货", "成品直接装车，不回头", "出货端")),
            technical=("大跨与设备荷载需结构专项；洁净区需独立空调与压差控制" if clean
                       else "设备基础、动力管沟需与工艺同步",),
            costs=(f"单层占地 {area:,.0f} m²，用地利用率低；但结构简单、物流最短",),
            risks=("用地紧张时单层会把绿地与停车挤掉，须先算总图指标",),
            family="linear", diagram="zoning",
            bands=("production", "warehouse", "office", "service"),
            uses=("area", "bay", "docks"),
            answers=("单层", "工艺"),
        ),
        Move(
            name="模块化厂房 · 两层加货梯",
            parti=(f"{area:,.0f} m² 拆成两层各 {area / 2:,.0f} m²，"
                   f"货梯 {max(1.0, round(area / 6000)):.0f} 部成对布置在中部，"
                   "首层做仓储与出货，二层做生产"),
            why=("用地受限、或工艺允许上下分层时，两层能把占地减半；"
                 "代价是层间物流必须靠货梯，产能上限由货梯决定"),
            massing=f"两层矩形厂房，柱网 {bay:.1f} × {bay:.1f} m，货梯与楼梯成组放在长边中部",
            section="一层净高按仓储与货车定，二层按设备与管线定；楼面荷载分区标注",
            circulation="首层：收货→仓储→货梯；二层：生产→检测→货梯下到首层出货",
            facade="两层均设装卸门，但只有首层做车辆停靠",
            daylight="二层靠天窗与侧窗，首层靠装卸门与高窗",
            sequence=(("到达", "货车停靠首层装卸区", "首层"),
                      ("生产", "物料经货梯上二层，单向流动", "二层"),
                      ("出货", "成品下到首层，与原料不交叉", "首层出货口")),
            technical=("楼面活荷载与货梯井道需结构配合；消防按丙类厂房核",),
            costs=(f"两层比单层多 {max(1.0, round(area / 6000)):.0f} 部货梯与一套竖向交通，"
                   "但用地减半"),
            risks=("货梯一旦故障，二层产能归零：须评估工艺是否允许停机",),
            family="grid", diagram="massing",
            bands=("warehouse", "production", "office", "service"),
            uses=("area", "bay"),
            answers=("单层",),
        ),
        Move(
            name="厂前区分离 · 物流环",
            parti=(f"把 {annex:,.0f} m² 办公与生活配套放在厂前区，生产区用一条环形道路"
                   f"包住，{docks:.0f} 个装卸位分别设在原料端与成品端"),
            why=("货车与员工必须分开：员工从厂前区步行进入，货车绕到背面装卸；"
                 "环形道路同时满足消防车道与回车"),
            massing=f"厂前区 2–3 层（{annex:,.0f} m²），生产区单层或双层大跨",
            section="厂前区做正常层高，生产区按工艺",
            circulation="人车分流：人行主入口在正面，货运环道在外圈，装卸位不占用消防车道",
            facade="厂前区做企业形象（玻璃、标识），生产区做功能立面",
            daylight="厂前区按办公标准采光",
            sequence=(("到达", "员工从正面进厂，货车绕到背面", "厂前区"),
                      ("生产", "从厂前区经更衣/通道进入生产区", "生产区"),
                      ("离开", "员工与货车各有出口", "分流")),
            technical=("环形道路宽度需满足消防与回车；装卸位要留足够等候区",),
            costs=(f"环道与厂前区会占掉约 {(area * 0.12):,.0f} m² 用地",),
            risks=("地块过窄时环道做不出来，只能做尽端式回车场",),
            family="courtyard", diagram="circulation",
            bands=("office", "production", "warehouse", "service"),
            uses=("annex_m2", "docks"),
            answers=("物流",),
        ),
    ]


# --------------------------------------------------------------------------
# 酒店 / 住宿（室内主导时用）
# --------------------------------------------------------------------------
def _hospitality(b: SectorBrief) -> List[Move]:
    keys = _n(b, "keys")
    guest = _n(b, "guest_m2")
    public = _n(b, "public_m2")
    boh = _n(b, "boh_m2")
    per = 45.0
    per_floor = max(8.0, round(keys / 6.0)) if keys else 0.0
    floors = max(1.0, round(keys / per_floor)) if keys else 0.0
    areas = b.signals.get("areas") or []

    return [
        Move(
            name="客房模数 · 走廊尽端服务",
            parti=(f"{keys:.0f} 间客房按 {per:.0f} m²/间（开间 4.2 m × 进深 8.4 m）排成"
                   f"{floors:.0f} 层、每层 {per_floor:.0f} 间；服务间与布草放在走廊尽端"),
            why=(f"{guest:,.0f} m² 客房是这家酒店的主体。把服务间放在尽端，"
                 f"服务员到最远房间约 {per_floor * 4.2 / 2:,.0f} m，"
                 "比居中布置少穿越一次客房门"),
            massing="标准层一条走廊两侧排房；电梯厅居中偏一侧，端部做服务间",
            section="走廊净宽 1.8 m，客房净高 2.7 m；卫生间降板 300 mm 走管",
            circulation="客人从电梯厅进入走廊；布草车与垃圾走同一服务间，不与客人同乘电梯",
            facade="按客房开间做窗，卫生间高窗或机械排风",
            daylight="客房窗地比 1:6；走廊尽头设采光窗避免暗走道",
            sequence=(("到达", "电梯厅 → 走廊 → 房门", "电梯厅"),
                      ("入住", "进门先看窗，再看床", "客房"),
                      ("服务", "服务间在尽端，减少打扰", "尽端")),
            technical=("卫生间排水立管集中在管井；客房隔声按 45 dB 控制",),
            costs=(f"每层 {per_floor:.0f} 间比 {per_floor + 4:.0f} 间少 2 间可售房，"
                   "但服务距离更短"),
            risks=("既有建筑柱网若小于 8 m，客房开间会被结构定死，房型数量难调",),
            family="linear", diagram="zoning",
            bands=("guest", "public", "boh"),
            uses=("keys", "guest_m2"),
            answers=("后场",),
        ),
        Move(
            name="公共核心 · 后场独立",
            parti=(f"大堂、餐饮与会议（{_m2(public)}）集中在首层与二层形成一个公共核，"
                   f"后场 {_m2(boh)} 用独立通道与货梯上下，客人永远看不到"),
            why=("酒店的评价一半来自公区。把餐饮与会议叠在公共核里，"
                 "宴会散场与早餐高峰可以共用前厅；后场独立成一条竖向通道，"
                 "布草、垃圾、收货都不经过大堂"),
            massing=f"裙房 2 层做公共核（{_m2(public)}），塔楼做客房",
            section="宴会厅做通高；厨房与宴会厅同层，送餐距离最短",
            circulation="客人：大堂→电梯/楼梯；服务：后场货梯→各层服务间；两条竖向动线不共用",
            facade="公共核做大玻璃与雨棚，形成入口识别",
            daylight="大堂与餐厅需要自然光；宴会厅可无窗",
            sequence=(("到达", "落客区 → 大堂 → 前台", "大堂"),
                      ("用餐", "餐厅与厨房同层，送餐不穿越大堂", "餐饮"),
                      ("回房", "从大堂经客梯上客房层", "客梯")),
            technical=("厨房排烟、隔油、燃气需专项；宴会厅消防按人数核疏散",),
            costs=(f"后场按 {boh / max(keys, 1):.1f} m²/间 设置，"
                   "低于 12 m²/间时运营会明显吃紧"),
            risks=("公共核与客房层共用电梯时，宴会散场会挤占住客电梯",),
            family="cluster", diagram="functional",
            bands=("public", "boh", "guest"),
            uses=("keys", "public_m2", "boh_m2"),
            answers=("后场",),
        ),
        Move(
            name="既有结构顺势 · 房型重组",
            parti=(f"不动柱网与管井，用 {min(3, max(2, round(len(areas) or 2)))} 种房型"
                   "去适配现有开间：标准间、转角房、连通房，把不规则处做成特色房"),
            why=("既有建筑改造里，结构就是边界条件。与其硬做统一房型，"
                 "不如让房型跟着结构走，把柱边、转角做成可售的差异房"),
            massing="沿用既有体量，只调内部隔墙与卫生间位置",
            section="利用既有梁下净高，卫生间局部降板或抬高",
            circulation="沿用既有电梯与疏散楼梯，服务间靠近原管井",
            facade="外立面按改造范围决定，窗洞不改时房型受窗位约束",
            daylight="按既有窗洞排房，避免出现无窗房",
            sequence=(("到达", "沿用原入口，重塑大堂", "大堂"),
                      ("入住", "按结构分出的房型引导", "房型"),
                      ("服务", "服务间贴原管井", "后场")),
            technical=("拆改边界须结构鉴定；消防疏散宽度按现行规范复核",),
            costs=("房型不统一会增加布草与保洁的复杂度，但省下结构改造费",),
            risks=("既有管井位置固定，卫生间一味追求统一会导致排水坡度过长",),
            family="grid", diagram="zoning",
            bands=("guest", "public", "boh"),
            uses=("keys",),
            answers=("后场",),
        ),
    ]


# --------------------------------------------------------------------------
# 景观
# --------------------------------------------------------------------------
def _landscape(b: SectorBrief) -> List[Move]:
    site = _n(b, "site_area")
    green = _n(b, "green_m2")
    paving = _n(b, "paving_m2")
    water = _n(b, "water_m2")
    low_care = "好维护" in " ".join(b.assumptions + b.tensions) or False

    return [
        Move(
            name="一池静水 · 环水游线",
            parti=(f"{water:,.0f} m² 水面（占 {water / site:.0%}）偏在一侧，"
                   f"园路沿水绕行一圈约 {2 * (site ** 0.5 + site ** 0.5 * 0.3):,.0f} m，"
                   f"绿地 {green:,.0f} m² 分三层种植"),
            why=("水是场地的视觉中心，也是维护成本的中心。把水做成一块静止的浅水面，"
                 "比溪流少一套循环设备；园路绕水走，人一直看得见水"),
            massing=f"水面偏西北，铺装 {paving:,.0f} m² 集中在建筑出口与茶席",
            section="水面标高低于铺装 100–150 mm，岸线做 300 mm 宽卵石带",
            circulation="入口→转折→茶席→绕水回入口；主路 1.2 m，支路 0.9 m",
            facade="",
            daylight="乔木给西晒面遮阴，水面对天光形成反射",
            sequence=(("进入", "先看见水，不看见全园", "入口转折"),
                      ("停留", "茶席背靠种植、面向水面", "茶席"),
                      ("回望", "绕水一圈回到入口", "环线")),
            technical=("水池需循环与补水；乔木位置避让管线",),
            costs=(f"水面 {water:,.0f} m² 的年维护（清淤、补水、过滤）是硬支出",),
            risks=("有儿童时水深须控制在 300 mm 以内或做护栏",),
            family="courtyard", diagram="landscape",
            bands=("water", "planting", "paving"),
            uses=("site_area", "water_m2"),
            answers=("水面",),
        ),
        Move(
            name="旱溪台地 · 少水多绿",
            parti=(f"取消常水面，用 {green * 0.2:,.0f} m² 旱溪与台地组织排水，"
                   f"绿地提高到 {green:,.0f} m²（{green / site:.0%}）"),
            why=("业主要低维护时，水景是最先变成负担的东西。旱溪平时是景观，"
                 "雨天是排水通道，一套做法两件事"),
            massing="按 300–500 mm 高差做 2–3 级台地，旱溪沿最低处走",
            section="台地高差 300–450 mm，用条石收边；旱溪纵坡不小于 0.5%",
            circulation="沿等高线走的主路 + 下到旱溪的支路",
            facade="",
            daylight="台地朝南面种喜阳植物，背面种耐阴",
            sequence=(("进入", "从高处看见台地层次", "入口平台"),
                      ("下行", "沿旱溪走到最低处", "旱溪"),
                      ("停留", "在台地边缘的坐凳停留", "台地")),
            technical=("旱溪要与市政雨水口对接；台地挡土需结构配合",),
            costs=("土方与挡土墙是一次性投入，之后几乎不用维护水面",),
            risks=("旱溪做得浅会积水发臭，纵坡必须算",),
            family="layered", diagram="landscape",
            bands=("planting", "paving", "water"),
            uses=("green_m2", "site_area"),
            answers=("水面", "维护"),
        ),
        Move(
            name="林下茶席 · 边界种植",
            parti=(f"沿边界种 {max(6, round(site / 60)):.0f} 株乔木形成围合，"
                   f"中间留出 {paving * 0.5:,.0f} m² 的硬质活动面与一组茶席"),
            why=("私密性靠边界而不是靠围墙。乔木带把邻居的视线挡住，"
                 "中间才能空出来做活动"),
            massing="边界 3–5 m 宽种植带，中心硬质场地",
            section="种植带做微地形（抬高 200–300 mm），排水向中心",
            circulation="一条主园路串起入口、茶席、活动场地",
            facade="",
            daylight="乔木遮西晒，中心场地保证冬季有日照",
            sequence=(("进入", "穿过种植带进入中心", "入口"),
                      ("停留", "茶席在半围合处", "茶席"),
                      ("活动", "中心硬质场地给小孩", "场地")),
            technical=("乔木与建筑基础保持 3 m 以上距离",),
            costs=("乔木按胸径计价，边界一周的乔木是主要景观造价",),
            risks=("种植过密会影响一层采光与通风",),
            family="cluster", diagram="landscape",
            bands=("planting", "paving"),
            uses=("site_area", "green_m2"),
            answers=("私密",),
        ),
    ]


# --------------------------------------------------------------------------
# 其它类型：仍然按数据给，不编
# --------------------------------------------------------------------------
def _generic(b: SectorBrief) -> List[Move]:
    area = _n(b, "area") or _n(b, "site_area")
    label = b.sector_label or "本项目"
    if not area:
        return []
    return [
        Move(
            name="功能优先 · 分区清晰",
            parti=f"{area:,.0f} m² 按「公共—使用—后勤」三段排布，公共段贴入口",
            why=f"没有拿到{label}的具体运营数据，只能先按功能关系排；"
                "一旦补上人数、班次或工艺，分区顺序应重排",
            massing=f"单一体量或 L 形，公共段 {area * 0.25:,.0f} m²，后勤段 {area * 0.2:,.0f} m²",
            section="按常规层高，设备集中段局部降板",
            circulation="公共与后勤各有入口，使用区在中间",
            facade="公共面开放，后场收实",
            daylight="主要使用空间优先采光",
            sequence=(("到达", "进入公共段", "入口"),
                      ("使用", "进入主要功能区", "中部"),
                      ("离开", "后勤独立通道", "后侧")),
            technical=("设备与结构条件待补",),
            costs=("按常规做法估，缺运营数据时误差较大",),
            risks=("这条方向是「数据不足下的通用解」，不能当作业主需求的回应",),
            family="cluster", diagram="zoning",
            uses=("area",),
        )
    ]


BUILDERS = {
    "education": _education,
    "healthcare": _healthcare,
    "industrial": _industrial,
    "hospitality": _hospitality,
    "landscape": _landscape,
}


def moves(brief: SectorBrief, *, limit: int = 3) -> List[Move]:
    """按行业给出 2–3 条方向；没有数据就只给一条并标明局限。"""
    fn = BUILDERS.get(brief.sector, _generic)
    out = fn(brief) or _generic(brief)
    # 只保留能落地的数量：没有数字支撑的方向排后面（而不是删掉，因为它可能
    # 回答的是"客户在意但还没给数"的那一条）
    def score(m: Move) -> float:
        return len([u for u in m.uses if u in brief.quant or u in brief.inputs]) + \
            (0.5 if m.answers else 0.0)
    out = sorted(out, key=lambda m: -score(m))[:max(1, limit)]
    return out


__all__ = ["BUILDERS", "Move", "moves"]
