"""专业范围（discipline scope）—— 先确定"这件事归谁管"，再谈画什么。

为什么需要这一层
----------------
"室内设计"只是其中一种范围。真实委托里常见的是：只做景观、只做结构加固、
建筑与室内一体、机电专项、或者一个需要报批的新建。旧实现默认所有项目都走
"住宅/办公的房间组合"，于是：

* 纯景观项目被要求填"卧室数量"；
* 结构加固项目被要求选"设计风格"；
* 建筑项目被当成室内项目，平面策略直接错位。

这一层只做三件事，**不产生任何几何**：

1. 定义一个项目到底涉及哪些专业，每个专业此刻是「已明确 / 他人要求 / 推断 /
   未知 / 不在范围」；
2. 把"该问谁的问题"路由出去——不在范围的专业不许被追问；
3. 把"缺资料"和"缺专业签署"记成可追踪的状态，而不是悄悄当成没问题。

状态口径（`SCOPE_STATES`）严格区分"没提"和"明确不做"：
`out_of_scope` 只能来自客户明说或任务书声明，推断不出来。

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

# --------------------------------------------------------------------------
# 状态：不要把"没问"当成"不用做"
DECLARED = "declared"            # 客户/任务书明确要做
REQUIRED = "required"            # 本专业被其他专业的成果牵动，必须有人做
INFERRED = "inferred"            # 从项目描述推断，尚未确认
UNKNOWN = "unknown"              # 需要，但资料不足，无法判断深度
OUT_OF_SCOPE = "out_of_scope"    # 明确不做（需证据）

SCOPE_STATES = (DECLARED, REQUIRED, INFERRED, UNKNOWN, OUT_OF_SCOPE)
ACTIVE_STATES = (DECLARED, REQUIRED, INFERRED, UNKNOWN)

STATE_LABEL = {
    DECLARED: "已明确在范围内",
    REQUIRED: "被其他专业牵动，必须有",
    INFERRED: "推断在范围内（未确认）",
    UNKNOWN: "在范围内但资料不足",
    OUT_OF_SCOPE: "明确不在范围",
}


@dataclass(frozen=True)
class Discipline:
    id: str
    label: str
    keywords: Tuple[str, ...]
    deliverable: str          # 这个专业最终交什么
    question_slots: Tuple[str, ...] = ()
    needs_professional: bool = True   # 是否必须持证/注册专业人员签署
    note: str = ""


#: 专业清单。只登记本系统真的能产出或真的会拦的，不铺空头支票。
DISCIPLINES: Dict[str, Discipline] = {
    "architecture": Discipline(
        id="architecture", label="建筑",
        keywords=("建筑", "新建", "扩建", "改建", "外立面", "立面改造", "报建",
                  "总平", "体量", "方案报批"),
        deliverable="建筑方案（总平、平面、立面、剖面、体量）",
        question_slots=("site_area", "floors", "coverage", "setbacks", "approval"),
        note="涉及报批与规范符合性，须当地注册建筑师复核",
    ),
    "interior": Discipline(
        id="interior", label="室内",
        keywords=("室内", "装修", "精装", "软装", "全屋", "样板间", "改造",
                  "空间设计", "布局"),
        deliverable="室内方案（平面布置、顶墙地、家具与材料）",
        question_slots=("needs", "storage", "style", "deliverable_depth"),
    ),
    "structure": Discipline(
        id="structure", label="结构",
        keywords=("结构", "承重", "加固", "梁", "柱", "楼板", "拆墙", "开洞",
                  "荷载", "基础", "钢结构", "抗震"),
        deliverable="结构方案与计算（构件尺寸、加固做法、荷载复核）",
        question_slots=("structure", "loads", "demolition"),
        note="结构安全结论必须由注册结构工程师签署，系统只做条件梳理",
    ),
    "mep": Discipline(
        id="mep", label="机电",
        keywords=("机电", "暖通", "空调", "新风", "给排水", "电气", "强弱电",
                  "消防", "喷淋", "排烟", "智能化", "配电"),
        deliverable="机电方案（负荷、点位、管综、消防）",
        question_slots=("hvac", "electrical", "plumbing", "fire"),
        note="负荷与消防须专业工程师计算并复核，系统不代替计算",
    ),
    "landscape": Discipline(
        id="landscape", label="景观",
        keywords=("景观", "庭院", "院子", "花园", "园林", "屋顶花园", "露台", "绿化",
                  "铺装", "水景", "植物", "室外", "院落", "天井绿化"),
        deliverable="景观方案（竖向、铺装、种植、水景、照明）",
        question_slots=("site_area", "outdoor_program", "planting", "drainage"),
    ),
    "planning": Discipline(
        id="planning", label="规划 / 报批",
        keywords=("规划", "容积率", "日照", "退线", "限高", "用地", "报批",
                  "审批", "指标"),
        deliverable="规划指标核对与报批路径说明",
        question_slots=("site_area", "far", "height_limit", "setbacks", "approval"),
        note="指标口径按项目所在地规范，系统只给条件与缺口，不出法定结论",
    ),
}

DISCIPLINE_ORDER: Tuple[str, ...] = tuple(DISCIPLINES)

#: 新建迹象：出现这些，说明不只是装修，很可能包含建筑本体
NEW_BUILD_HINTS: Tuple[str, ...] = (
    "新建", "自建", "盖房", "盖一栋", "地块", "有块地", "宅基地",
    "建一栋", "建两栋", "层别墅", "报建", "毛坯", "从地", "土建",
)

#: 只要做室内，结构就"被牵动"（拆改、荷载、开洞都绕不开）
TRIGGERS: Dict[str, Tuple[str, ...]] = {
    "structure": ("拆", "改", "开洞", "加固", "承重", "楼板", "夹层", "加建"),
    "mep": ("卫", "厨", "空调", "新风", "消防", "热水", "地暖", "配电"),
    "landscape": ("庭院", "露台", "屋顶", "花园", "室外", "景观"),
    "planning": ("报建", "报批", "审批", "容积率", "退线", "限高"),
}


class ScopeError(ValueError):
    """范围声明本身有问题（比如把必需专业标成不做却没有依据）。"""


@dataclass
class ScopeEntry:
    discipline: str
    state: str = UNKNOWN
    evidence: str = ""            # 为什么这么判（原话/图纸/任务书条目）
    confirmed_by: str = ""        # 谁确认的（客户/主创/专业人员）
    depth: str = ""               # 方案 / 施工图 / 仅咨询
    needs_professional: bool = True
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        d = DISCIPLINES.get(self.discipline)
        return {
            "discipline": self.discipline,
            "label": d.label if d else self.discipline,
            "state": self.state,
            "state_label": STATE_LABEL.get(self.state, self.state),
            "active": self.state in ACTIVE_STATES,
            "evidence": self.evidence,
            "confirmed_by": self.confirmed_by,
            "depth": self.depth,
            "needs_professional": bool(self.needs_professional),
            "deliverable": d.deliverable if d else "",
            "notes": list(self.notes),
        }


@dataclass
class DisciplineScope:
    entries: Dict[str, ScopeEntry] = field(default_factory=dict)
    basis: Tuple[str, ...] = ()      # 判定依据的原话
    profile_id: str = ""

    # -- 查询 -----------------------------------------------------------
    def entry(self, did: str) -> ScopeEntry:
        if did not in self.entries:
            self.entries[did] = ScopeEntry(discipline=did, state=UNKNOWN)
        return self.entries[did]

    def active(self) -> List[str]:
        return [d for d in DISCIPLINE_ORDER
                if d in self.entries and self.entries[d].state in ACTIVE_STATES]

    def out(self) -> List[str]:
        return [d for d in DISCIPLINE_ORDER
                if d in self.entries and self.entries[d].state == OUT_OF_SCOPE]

    def needs_data(self) -> List[str]:
        # REQUIRED 表示"必须有"，但资料同样没到位——不能因为它是必需的就不列缺口
        return [d for d in self.active()
                if self.entries[d].state in (INFERRED, UNKNOWN, REQUIRED)]

    def labels(self, ids: Optional[Iterable[str]] = None) -> List[str]:
        ids = list(ids if ids is not None else self.active())
        return [DISCIPLINES[d].label if d in DISCIPLINES else d for d in ids]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "active": self.active(),
            "active_labels": self.labels(),
            "out_of_scope": self.out(),
            "needs_data": self.needs_data(),
            "basis": list(self.basis),
            "entries": [self.entries[d].to_dict() for d in DISCIPLINE_ORDER
                        if d in self.entries],
            "note": ("out_of_scope 必须来自客户明说或任务书声明；"
                     "推断不会把任何专业标成不做。"),
        }


# --------------------------------------------------------------------------
#: 否定必须按**短语**匹配，不能按单字。
#: 用单字会立刻出事：「别墅」里的「别」、「无窗」里的「无」都会被当成否定，
#: 于是"带庭院水池的三层别墅"被判成"明确不做景观"。
NEGATION_PATTERNS: Tuple[str, ...] = (
    "不做", "不要", "不用", "不需", "无需", "不考虑", "不涉及", "不含",
    "不动", "不改", "不碰", "不加", "不换", "不在范围", "除外", "免做",
    "别做", "勿动", "暂无", "不用做", "先不做", "这次不做", "本次不做",
)


#: 分句边界。否定只在**同一分句内**生效——否则"室内不动，院子做景观"会把
#: 后半句的"景观"也否掉。
CLAUSE_SEPS = "。，；！？、\n\r\t"


def _clause_at(text: str, pos: int) -> Tuple[int, int]:
    """返回包含 pos 的分句区间 [start, end)。"""
    start = 0
    for i in range(pos - 1, -1, -1):
        if text[i] in CLAUSE_SEPS:
            start = i + 1
            break
    end = len(text)
    for i in range(pos, len(text)):
        if text[i] in CLAUSE_SEPS:
            end = i
            break
    return start, end


def _negated(text: str, kw: str) -> bool:
    """关键词所在分句里出现否定短语，才算"明确不做"。

    三条都是踩过的坑：按单字判会把「别墅」「无窗」误判；不限分句会把
    "室内不动，院子做景观" 里的景观也否掉；两种误判的后果都是把要做的事
    判成不做，比漏判更危险。
    """
    start = text.find(kw)
    while start != -1:
        a, b = _clause_at(text, start)
        clause = text[a:b]
        if any(p in clause for p in NEGATION_PATTERNS):
            return True
        start = text.find(kw, start + 1)
    return False


def _hits(text: str, keywords: Sequence[str]) -> List[str]:
    return [k for k in keywords if k and k in text and not _negated(text, k)]


def detect(texts: Sequence[str], *, profile_id: str = "",
           declared_out: Sequence[str] = (),
           declared_in: Sequence[str] = ()) -> DisciplineScope:
    """从原话与已有声明推断范围。只推断"要做"，不推断"不做"。

    `declared_out` / `declared_in` 必须由调用方给出**证据**（客户原话或任务书），
    否则不做标记——把"没提"当成"不做"是这一层最危险的错误。
    """
    blob = " ".join(t for t in texts if t)
    scope = DisciplineScope(profile_id=profile_id)
    for did in DISCIPLINE_ORDER:
        d = DISCIPLINES[did]
        hits = _hits(blob, d.keywords)
        if hits:
            scope.entries[did] = ScopeEntry(
                discipline=did, state=INFERRED,
                evidence=f"文中出现：{'、'.join(hits[:4])}",
                needs_professional=d.needs_professional)
            continue
        negated = [k for k in d.keywords if k and k in blob and _negated(blob, k)]
        if negated:
            # 客户原话里明确说了"不做"，这才允许标 out_of_scope
            scope.entries[did] = ScopeEntry(
                discipline=did, state=OUT_OF_SCOPE,
                evidence=f"客户原话含否定：{'、'.join(negated[:3])}",
                confirmed_by="客户原话",
                needs_professional=d.needs_professional)

    # 新建信号：客户说"有块地/建三层/自建别墅"，本质是建筑委托，
    # 不能因为没出现"建筑"两个字就当成室内装修。
    # 只标 inferred（待确认），因为"别墅"也可能只是室内委托。
    # 注意：必须用 get 判断"是否已有记录"，不能调 entry()——entry() 会顺手造一条
    # UNKNOWN，而 UNKNOWN 属于在范围，等于凭空把建筑拉进范围。
    if "architecture" not in scope.entries:
        build_hits = _hits(blob, NEW_BUILD_HINTS)
        if build_hits:
            scope.entries["architecture"] = ScopeEntry(
                discipline="architecture", state=INFERRED,
                evidence=f"新建迹象：{'、'.join(build_hits[:4])}（需确认是否含建筑设计）",
                needs_professional=DISCIPLINES["architecture"].needs_professional)

    # 项目类型本身隐含的专业：建筑/室内是"载体"，结构机电是"被牵动"
    building_profiles = ("residential", "office", "hospitality", "retail", "exhibition")
    # 只有当客户没有把话说成"专项委托"时，才预设室内是主专业。
    # 反例："只想重新设计我家的花园" —— 项目类型仍是住宅，但这次不做室内；
    # 若照旧预设，客户会被问一堆卧室与收纳的问题。
    specialty_hits = _hits(blob, (
        DISCIPLINES["landscape"].keywords + DISCIPLINES["structure"].keywords
        + DISCIPLINES["planning"].keywords))
    if profile_id in building_profiles:
        if "interior" not in scope.entries and not specialty_hits:
            scope.entries["interior"] = ScopeEntry(
                discipline="interior", state=REQUIRED,
                evidence=f"项目类型「{profile_id}」默认涉及室内设计")
        for did, trigger_words in (("structure", TRIGGERS["structure"]),
                                   ("mep", TRIGGERS["mep"])):
            if _hits(blob, trigger_words) and did not in scope.entries:
                scope.entries[did] = ScopeEntry(
                    discipline=did, state=REQUIRED,
                    evidence=f"项目内容涉及：{'、'.join(_hits(blob, trigger_words)[:3])}",
                    needs_professional=DISCIPLINES[did].needs_professional)
    if profile_id == "architecture":
        # 项目类型判为建筑类，只说明"很可能是建筑主导"，不说明客户一定委托了
        # 建筑本体——纯景观/纯结构加固的委托也可能落在这个类型里。
        # 所以标 inferred 让 S1 问一句，而不是直接当成已委托。
        if "architecture" not in scope.entries:
            scope.entries["architecture"] = ScopeEntry(
                discipline="architecture", state=INFERRED,
                evidence="项目类型判为建筑类（需确认是否含建筑本体设计）",
                needs_professional=DISCIPLINES["architecture"].needs_professional)

    for did in declared_in:
        e = scope.entry(did)
        e.state = DECLARED
        e.confirmed_by = e.confirmed_by or "客户声明"
    for did in declared_out:
        e = scope.entry(did)
        if e.state in (DECLARED, REQUIRED) and not e.evidence:
            raise ScopeError(f"{did} 既被声明要做又被声明不做，缺少证据无法裁决")
        e.state = OUT_OF_SCOPE
        e.confirmed_by = e.confirmed_by or "客户声明"
        e.evidence = e.evidence or "客户明确不做"
    scope.basis = tuple(t for t in texts if t)
    return scope


# --------------------------------------------------------------------------
# 项目读写：只存在 meta 里，schema 向后兼容，不新增必填字段
def load(project: Any) -> DisciplineScope:
    raw = ((getattr(project, "meta", {}) or {}).get("scope") or {})
    scope = DisciplineScope(profile_id=str(raw.get("profile_id") or ""),
                            basis=tuple(raw.get("basis") or ()))
    for item in raw.get("entries") or []:
        did = str(item.get("discipline") or "")
        if did not in DISCIPLINES:
            continue
        scope.entries[did] = ScopeEntry(
            discipline=did, state=str(item.get("state") or UNKNOWN),
            evidence=str(item.get("evidence") or ""),
            confirmed_by=str(item.get("confirmed_by") or ""),
            depth=str(item.get("depth") or ""),
            needs_professional=bool(item.get("needs_professional", True)),
            notes=list(item.get("notes") or []),
        )
    return scope


def store(project: Any, scope: DisciplineScope) -> Dict[str, Any]:
    project.meta = dict(getattr(project, "meta", {}) or {})
    payload = scope.to_dict()
    project.meta["scope"] = payload
    return payload


def ensure(project: Any, *, profile_id: str = "") -> DisciplineScope:
    """读不到就从项目文本推断一次并落盘（幂等）。"""
    scope = load(project)
    if scope.entries:
        return scope
    from .intake.interview import load_interview

    answers = (load_interview(project).answers or {})
    texts = [str(getattr(project, "name", "") or "")]
    texts += [str((v or {}).get("value") or "") for v in answers.values()]
    detected = detect(texts, profile_id=profile_id or str(
        (answers.get("profile_id") or "")))
    store(project, detected)
    return detected


def set_state(project: Any, discipline: str, state: str, *,
              evidence: str = "", confirmed_by: str = "",
              depth: str = "") -> DisciplineScope:
    if discipline not in DISCIPLINES:
        raise ScopeError(f"未知专业 {discipline!r}")
    if state not in SCOPE_STATES:
        raise ScopeError(f"未知状态 {state!r}")
    if state == OUT_OF_SCOPE and not evidence:
        raise ScopeError("标为不做必须给出证据（客户原话或任务书条目）")
    scope = load(project)
    e = scope.entry(discipline)
    e.state = state
    if evidence:
        e.evidence = evidence
    if confirmed_by:
        e.confirmed_by = confirmed_by
    if depth:
        e.depth = depth
    store(project, scope)
    return scope


def route_question_slots(scope: DisciplineScope) -> Tuple[Tuple[str, ...], Tuple[str, ...]]:
    """返回 (需要的槽位, 被排除的槽位)。

    不在范围的专业，其专属问题不再追问——这是"只做景观不该被问卧室"的落点。
    """
    needed: List[str] = []
    excluded: List[str] = []
    for did in DISCIPLINE_ORDER:
        d = DISCIPLINES[did]
        e = scope.entries.get(did)
        if e is None:
            # 没有记录 = 这次没有依据说它在范围内。不追问，也不判成不做。
            continue
        target = excluded if e.state == OUT_OF_SCOPE else needed
        target.extend(d.question_slots)
    return tuple(dict.fromkeys(needed)), tuple(dict.fromkeys(excluded))


# --------------------------------------------------------------------------
# 专业接口：两个专业之间真正会打架的地方
#
# 这张表不是"协作精神"，而是必须逐条回答的物理约束。它决定一件事：
# 单专业不能在自己不了解对方条件时宣布完成。
@dataclass(frozen=True)
class Interface:
    id: str
    pair: Tuple[str, str]           # 谁与谁
    issue: str                      # 打架的是什么
    from_discipline: str            # 谁先给条件
    needs: str                      # 需要什么才能定
    fails_when: str                 # 什么情况下这条接口一定没解决
    blocks_stage: str = "S3"        # 影响到哪个阶段


#: 只在**双方都在范围内**时才生效。范围外的专业不进矩阵。
INTERFACES: Tuple[Interface, ...] = (
    Interface("IF-STR-SPACE", ("structure", "architecture"),
              "结构梁柱、剪力墙与挑空、通高、大开间的关系",
              "structure", "梁高与跨度、是否允许梁上翻、柱位可否偏移",
              "建筑图上有跨越楼层的通高空间但结构未给出梁位",
              "S3"),
    Interface("IF-STR-LOAD", ("structure", "landscape"),
              "屋顶花园、水景、大乔木的附加荷载与结构承载力",
              "structure", "屋面允许附加荷载（kN/㎡）与可种植区域",
              "景观在屋面布置水池或乔木而结构未复核附加荷载",
              "S3"),
    Interface("IF-STR-OPENING", ("structure", "interior"),
              "拆墙、开洞、加夹层对承重体系的影响",
              "structure", "哪些墙是承重墙、开洞限值与加固做法",
              "室内平面有拆改而结构未判定承重属性",
              "S3"),
    Interface("IF-MEP-HEIGHT", ("mep", "interior"),
              "吊顶净高与风管、桥架、喷淋、排水坡度",
              "mep", "主风管断面、桥架宽度、喷淋支管走向、排水坡向",
              "吊顶标高已定但未核风管与梁底净空",
              "S4"),
    Interface("IF-MEP-WET", ("mep", "interior"),
              "卫生间、厨房移位与排水立管、地漏、防水",
              "mep", "立管位置、可否增设、降板或同层排水的可行性",
              "卫浴位置改变但未确认立管与排水坡向",
              "S3"),
    Interface("IF-MEP-LAND", ("mep", "landscape"),
              "景观照明、灌溉、水景循环与电气安全、给排水接驳",
              "mep", "室外配电回路、灌溉水源与水压、水景循环方式",
              "景观有水体或照明但无配电与水源条件",
              "S3"),
    Interface("IF-WATER-FR", ("architecture", "landscape"),
              "水池、种植池、屋顶绿化的防水与排水",
              "architecture", "防水做法与泛水高度、排水找坡与溢流",
              "有水体或种植池但没有防水与排水做法",
              "S3"),
    Interface("IF-FACADE-MEP", ("architecture", "mep"),
              "立面百叶、设备平台、通风开口与建筑外观",
              "mep", "室外机位置、进排风面积、油烟与排烟出口",
              "立面已完成但设备无出口或无进风面积",
              "S4"),
    Interface("IF-PLAN-FAR", ("planning", "architecture"),
              "容积率、退线、限高、日照与建筑体量",
              "planning", "用地指标、退线要求、限高、日照标准来源",
              "体量已定但未核对规划指标或指标来源不明",
              "S2"),
    Interface("IF-PLAN-LAND", ("planning", "landscape"),
              "绿地率、透水率、乔木覆盖率与景观布置",
              "planning", "绿地率与透水率要求及计算口径",
              "景观铺装方案未核算绿地率或透水率",
              "S3"),
    Interface("IF-IN-LAND", ("interior", "landscape"),
              "室内绿化、中庭的日照、灌溉、排水、荷载与维护",
              "landscape", "植物选型与光照需求、灌溉方式、承重与排水",
              "室内有大型植物或种植池但无灌溉与排水方案",
              "S3"),
    Interface("IF-ARCH-IN", ("architecture", "interior"),
              "建筑空间、层高、结构梁底与室内吊顶、门窗洞口",
              "architecture", "净高、梁底标高、洞口尺寸与开启方向",
              "室内吊顶标高超过结构梁底",
              "S3"),
)


def interfaces_for(scope: DisciplineScope) -> List[Dict[str, Any]]:
    """只保留**双方都在范围内**的接口。

    范围外的专业不进矩阵——但要注意：`out_of_scope` 不等于"没有接口"，
    所以这里额外标出"对方被排除"的情况，交给 G1 条件去提示。
    """
    active = set(scope.active())
    out: List[Dict[str, Any]] = []
    for it in INTERFACES:
        a, b = it.pair
        both = a in active and b in active
        one_side = (a in active) != (b in active)
        if not both and not one_side:
            continue
        row = {
            "id": it.id,
            "pair": list(it.pair),
            "pair_labels": [DISCIPLINES[x].label for x in it.pair if x in DISCIPLINES],
            "issue": it.issue,
            "from": it.from_discipline,
            "from_label": DISCIPLINES[it.from_discipline].label,
            "needs": it.needs,
            "fails_when": it.fails_when,
            "blocks_stage": it.blocks_stage,
            "state": "active" if both else "one_side_out",
            "note": ("双方都在范围内，必须逐条回答" if both
                     else "有一方明确不在范围：需确认该接口由谁承担，"
                          "不能默认没问题"),
        }
        out.append(row)
    return out


def information_requests(scope: DisciplineScope) -> List[Dict[str, str]]:
    """缺什么资料，谁去要，要不到会怎样。

    这是给客户的清单，不是内部状态表——所以每条都写"要不到的影响"。
    """
    asks: List[Dict[str, str]] = []
    seen = set()
    for did in scope.needs_data():
        d = DISCIPLINES.get(did)
        if d is None:
            continue
        for slot in d.question_slots:
            key = (did, slot)
            if key in seen:
                continue
            seen.add(key)
            asks.append({
                "discipline": did,
                "discipline_label": d.label,
                "item": SLOT_LABEL.get(slot, slot),
                "owner": "客户 / 物业 / 原设计单位",
                "impact": SLOT_IMPACT.get(slot, f"缺此项时{d.label}只能给条件，不能定案"),
            })
    # 结构、机电在没有实测/图纸时，永远需要这一条
    active = set(scope.active())
    if "structure" in active and "structure" in scope.needs_data():
        asks.append({
            "discipline": "structure", "discipline_label": "结构",
            "item": "原结构图纸或现场检测报告（承重墙、梁柱位置、板厚）",
            "owner": "物业 / 原设计单位 / 检测机构",
            "impact": "没有它不能判定拆改可行性，也不能出结构方案",
        })
    if "planning" in active:
        asks.append({
            "discipline": "planning", "discipline_label": "规划 / 报批",
            "item": "用地规划条件（用地面积、容积率、退线、限高）及来源文件",
            "owner": "客户 / 当地规划部门",
            "impact": "缺它不能承诺方案可报批，体量只能做示意",
        })
    return asks


#: 槽位的中文名与"要不到会怎样"
SLOT_LABEL = {
    "site_area": "用地/场地面积与边界",
    "floors": "层数与各层功能",
    "coverage": "建筑密度与覆盖率",
    "setbacks": "退线要求",
    "approval": "报批状态与已知规划条件",
    "far": "容积率指标",
    "height_limit": "限高",
    "structure": "原结构资料（承重墙、梁柱、板厚）",
    "loads": "荷载条件（使用荷载、特殊设备）",
    "demolition": "拆改范围与可否拆",
    "hvac": "空调与通风方式",
    "electrical": "用电容量与配电条件",
    "plumbing": "给排水与立管位置",
    "fire": "消防要求与既有设施",
    "outdoor_program": "室外要做什么（铺装/种植/水景/屋顶花园）",
    "planting": "植物偏好与维护条件",
    "drainage": "排水与雨水去向",
    "needs": "使用需求与行为",
    "storage": "收纳需求",
    "style": "风格偏好",
    "deliverable_depth": "交付深度",
}

SLOT_IMPACT = {
    "structure": "不能判定拆改可行性，结构方案只能写待核实",
    "loads": "不能做荷载复核，屋面/夹层只能按常规假定",
    "site_area": "面积口径不清，容量与造价都算不准",
    "far": "不能核对容积率，体量只能做示意",
    "approval": "不能承诺可报批",
    "drainage": "水景与种植池的排水无法定案，防水做法也不能定",
    "planting": "植物选型只能给方向，不能给清单",
    "hvac": "吊顶净高无法确定",
}


def render_scope_markdown(project_name: str, rev: int, scope: DisciplineScope) -> str:
    lines = [f"# 设计范围 — {project_name}", "",
             f"模型修订 r{rev}", "", "## 一句话", ""]
    lines += [f"- {ln}" for ln in summary_lines(scope)]
    lines += ["", "## 逐专业状态", "",
              "| 专业 | 状态 | 依据 | 交付物 | 需专业签署 |",
              "|---|---|---|---|---|"]
    for did in DISCIPLINE_ORDER:
        e = scope.entries.get(did)
        if e is None:
            continue
        d = DISCIPLINES[did]
        lines.append(f"| {d.label} | {STATE_LABEL.get(e.state, e.state)} | "
                     f"{e.evidence or '—'} | {d.deliverable} | "
                     f"{'是' if d.needs_professional else '否'} |")
    lines += ["", "## 判定口径", "",
              "- 「明确不在范围」只能来自客户原话或任务书声明，推断不出来；",
              "- 「推断在范围」表示还没确认，不能当成已委托；",
              "- 「在范围内但资料不足」会限制后续深度，并不等于不做。", ""]
    return "\n".join(lines)


def render_interface_markdown(project_name: str, rev: int,
                              rows: Sequence[Dict[str, Any]]) -> str:
    lines = [f"# 专业接口矩阵 — {project_name}", "",
             f"模型修订 r{rev}", "",
             "> 这张表列的是**会打架的物理约束**，不是协作口号。",
             "> 任何一条没有明确答案，对应阶段就不能宣布完成。", "",
             "| 编号 | 涉及专业 | 冲突点 | 谁先给条件 | 需要什么 | 什么情况下算没解决 | 影响阶段 |",
             "|---|---|---|---|---|---|---|"]
    for r in rows:
        pair = " / ".join(r["pair_labels"])
        lines.append(f"| {r['id']} | {pair} | {r['issue']} | {r['from_label']} | "
                     f"{r['needs']} | {r['fails_when']} | {r['blocks_stage']} |")
    one_side = [r for r in rows if r["state"] == "one_side_out"]
    if one_side:
        lines += ["", "## 有一方明确不在范围（不等于没有接口）", ""]
        for r in one_side:
            lines.append(f"- **{r['id']}**（{' / '.join(r['pair_labels'])}）：{r['issue']}。"
                         f"该接口需确认由谁承担——不做某个专业，风险不会消失。")
    lines += ["", "## 怎么用", "",
              "- S2 概念阶段：每条接口都要在方案里有位置（不是留到施工图再想）；",
              "- G3 之前：接口中标注在 S3 影响的项必须有答案，否则不签发；",
              "- 变更时：改动涉及哪条接口，就按那条接口的双方一起返工。", ""]
    return "\n".join(lines)


def render_responsibility_markdown(project_name: str, rev: int,
                                   scope: DisciplineScope) -> str:
    lines = [f"# 专业责任与人工复核边界 — {project_name}", "",
             f"模型修订 r{rev}", "",
             "> 系统出条件、方案与校核清单；**不代替法定签署**——"
             "法定签署只能由持证专业人员在项目所在地完成。", "",
             "| 专业 | 系统能出到什么 | 必须人工复核 | 谁签 |",
             "|---|---|---|---|"]
    for did in scope.active():
        d = DISCIPLINES[did]
        lines.append(f"| {d.label} | {d.deliverable} | "
                     f"{'结构安全、荷载、抗震、配筋' if did == 'structure' else ''}"
                     f"{'负荷计算、消防合规、系统选型' if did == 'mep' else ''}"
                     f"{'规划指标符合性、报批可行性' if did == 'planning' else ''}"
                     f"{'空间与做法可行性、现场条件' if did == 'architecture' else ''}"
                     f"{'防水排水、植物适应性、维护条件' if did == 'landscape' else ''}"
                     f"{'设备末端与收口、材料实际效果' if did == 'interior' else ''}"
                     f" | {'注册' + d.label + '工程师' if did in ('structure', 'mep') else '建筑师 / 主创'} |")
    lines += ["", "## 不在系统结论范围的", "",
              "- 结构安全性与抗震验算；",
              "- 消防合规判定与疏散计算；",
              "- 机电负荷、容量与系统水力计算；",
              "- 当地法规符合性（须按项目所在地规范复核）；",
              "- 无障碍、节能等专项审查。", "",
              "以上均须持证专业人员在项目所在地按当地规范复核签署。", ""]
    return "\n".join(lines)


def render_information_requests_markdown(project_name: str,
                                         asks: Sequence[Dict[str, str]]) -> str:
    lines = [f"# 需要补的资料 — {project_name}", "",
             "> 按影响从大到小排。缺一项不阻塞讨论，但会限制能做到多深。", ""]
    if not asks:
        lines.append("目前没有明显缺口。")
        lines.append("")
        return "\n".join(lines)
    lines += ["| 专业 | 需要的资料 | 找谁要 | 要不到的影响 |", "|---|---|---|---|"]
    for a in asks:
        lines.append(f"| {a['discipline_label']} | {a['item']} | {a['owner']} | {a['impact']} |")
    lines.append("")
    return "\n".join(lines)


def summary_lines(scope: DisciplineScope) -> List[str]:
    """给客户看的一段话，不是状态码堆砌。"""
    active = scope.active()
    if not active:
        return ["尚不清楚要做什么专业的成果——先说清楚是装修、建筑、景观还是结构加固。"]
    lines = ["这次涉及：" + "、".join(scope.labels(active))]
    if scope.out():
        lines.append("明确不做：" + "、".join(scope.labels(scope.out())))
    need = scope.needs_data()
    if need:
        lines.append("还缺资料：" + "、".join(scope.labels(need))
                     + "（会限制后续能出到什么深度）")
    pros = [DISCIPLINES[d].label for d in active
            if DISCIPLINES[d].needs_professional]
    if pros:
        lines.append("需要专业签署：" + "、".join(pros)
                     + "（系统只出条件与方案，不代替法定签署）")
    return lines


__all__ = [
    "DISCIPLINES", "DISCIPLINE_ORDER", "SCOPE_STATES", "ACTIVE_STATES",
    "STATE_LABEL", "DECLARED", "REQUIRED", "INFERRED", "UNKNOWN", "OUT_OF_SCOPE",
    "Discipline", "ScopeEntry", "DisciplineScope", "ScopeError",
    "detect", "load", "store", "ensure", "set_state",
    "route_question_slots", "summary_lines",
    "INTERFACES", "Interface", "interfaces_for",
    "information_requests", "render_scope_markdown", "render_interface_markdown",
    "render_responsibility_markdown", "render_information_requests_markdown",
]
