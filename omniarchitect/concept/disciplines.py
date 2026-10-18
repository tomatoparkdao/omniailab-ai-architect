"""专业方向：一套概念，多个专业各自的"怎么做"。

为什么不是"再生成三套"
----------------------
室内、结构、机电、景观不是四个独立方案，它们必须服从同一套空间主张。
所以这里不新建引擎：每个专业方向都从**这套概念自己的空间主张**推导——
概念的 `spatial_logic` / `circulation` / `zoning` / `daylight` / `risks` 就是依据。

判据怎么写
----------
每个专业方向必须能回答一个问题：**这套概念向它提出了什么要求？**

比如同样是住宅：

* 「层次入户」把访客挡在过渡区 → 结构要回答过渡区那堵隔墙能不能砌；
* 「中央庭院」把采光交给内院 → 结构要回答能不能不落柱，景观要回答内院怎么排水；
* 「开放一体」打掉公共区隔墙 → 结构要回答哪些是承重墙。

如果两个概念的结构方向写着同一段话，说明这段是套话，不是推导。

缺资料的写法
------------
数据不够时给"条件"而不是"结论"：结构只写"先鉴定后设计、需结构工程师出计算书"，
不写"采用 200×500 钢梁"——后者是编的。
每个方向带 `status`：`proposed` / `requires_input`，一眼看出哪条还不能用。

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

from typing import Any, Dict, List, Sequence, Tuple

from .. import disciplines as D

PROPOSED = "proposed"
NEEDS_INPUT = "requires_input"

#: 概念里出现这些词，说明它**向结构提出了具体要求**。
#: 命中即说明"这个概念的成立依赖结构条件"，而不是"结构顺便配合一下"。
STRUCTURE_SIGNALS: Tuple[str, ...] = (
    "挑空", "通高", "悬挑", "大跨", "跨度", "夹层", "加建", "拆", "承重",
    "楼板", "开洞", "梁", "柱", "荷载", "下沉", "回填", "错层", "跃层",
)

MEP_SIGNALS: Tuple[str, ...] = (
    "机械通风", "新风", "空调", "地暖", "喷淋", "排烟", "湿区", "排水",
    "立管", "灌溉", "照明", "配电", "弱电", "厨房", "卫", "水景", "泵",
)

LANDSCAPE_SIGNALS: Tuple[str, ...] = (
    "庭院", "花园", "露台", "屋顶", "水池", "水景", "种植", "室外",
    "中庭", "绿化", "内院", "天井", "阳台",
)

PLANNING_SIGNALS: Tuple[str, ...] = (
    "容积率", "退线", "限高", "层数", "体量", "报建", "日照", "用地",
)


def _answer(project: Any, *keys: str) -> str:
    from ..intake.interview import load_interview

    answers = load_interview(project).answers or {}
    for k in keys:
        v = (answers.get(k) or {}).get("value")
        if v:
            return str(v)
    return ""


def _concept_text(concept: Dict[str, Any]) -> str:
    """把概念里所有"说空间怎么用"的字段拼起来，用于判定信号。"""
    proto = concept.get("spatial_prototype") or {}
    parts = [
        str(concept.get("concept_statement") or ""),
        str(concept.get("design_strategy") or ""),
        str(concept.get("user_experience") or ""),
        str(proto.get("spatial_logic") or ""),
        str(proto.get("circulation") or ""),
        str(proto.get("zoning") or ""),
        str(proto.get("daylight") or ""),
        str(proto.get("cost_note") or ""),
        str(proto.get("maintenance") or ""),
        " ".join(str(x) for x in (proto.get("risks") or [])),
        " ".join(str(x) for x in (proto.get("suitable_when") or [])),
    ]
    return " ".join(p for p in parts if p)


def _hits(text: str, words: Sequence[str]) -> List[str]:
    return [w for w in words if w and w in text]


def _quote(text: str, words: Sequence[str], limit: int = 2) -> str:
    """从概念原文里摘出触发的句子，作为判据依据。"""
    if not words:
        return ""
    out: List[str] = []
    for seg in (text.replace("；", "。").split("。")):
        if any(w in seg for w in words) and seg.strip():
            out.append(seg.strip())
        if len(out) >= limit:
            break
    return "；".join(out)


def _direction(did: str, *, goal: str, strategy: str,
               deliverables: List[str], open_questions: List[str],
               status: str = PROPOSED, evidence: str = "",
               demanded_by: Sequence[str] = (),
               interfaces: Sequence[str] = ()) -> Dict[str, Any]:
    d = D.DISCIPLINES[did]
    return {
        "discipline": did,
        "label": d.label,
        "concept_bound": True,          # 这条方向属于当前 concept_id，不是通用建议
        "goal": goal,
        "strategy": strategy,
        "deliverables": deliverables,
        "open_questions": open_questions,
        "status": status,
        "needs_professional": bool(d.needs_professional),
        "demanded_by": list(demanded_by),
        "interfaces": list(interfaces),
        "evidence": evidence,
        "note": d.note,
    }


def for_concept(project: Any, scope: D.DisciplineScope,
                concept: Dict[str, Any], ctx: Any) -> Dict[str, Dict[str, Any]]:
    """按范围给这套概念补齐各专业方向。只做在范围内的专业。

    每个方向都引用概念自己的话作为依据；两个概念拿到同一段话，就说明这里退化成
    了套话——`test_two_concepts_get_different_structure_demands` 守着这条。
    """
    out: Dict[str, Dict[str, Any]] = {}
    proto = concept.get("spatial_prototype") or {}
    text = _concept_text(concept)
    spatial = str(concept.get("spatial_strategy") or proto.get("spatial_logic") or "")
    statement = str(concept.get("concept_statement") or "")
    zoning = str(proto.get("zoning") or "")
    circulation = str(proto.get("circulation") or "")
    daylight = str(proto.get("daylight") or "")
    materials = [str(m.get("name")) for m in (concept.get("material_direction") or [])
                 if isinstance(m, dict) and m.get("name")]
    active = scope.active()

    # ---- 这套概念向各专业提了什么要求 --------------------------------
    struct_words = _hits(text, STRUCTURE_SIGNALS)
    mep_words = _hits(text, MEP_SIGNALS)
    land_words = _hits(text, LANDSCAPE_SIGNALS)
    plan_words = _hits(text, PLANNING_SIGNALS)

    if "architecture" in active:
        open_q = ["用地红线与退线", "限高与容积率", "报建路径"]
        out["architecture"] = _direction(
            "architecture",
            goal="用体量与开口把概念的空间主张立起来",
            strategy=(f"以「{statement}」为形体依据。" +
                      (f"分区逻辑：{zoning}" if zoning else "") +
                      (f"　动线：{circulation}" if circulation else "")),
            deliverables=["总平面", "各层平面", "立面与剖面", "体量示意"],
            open_questions=open_q,
            status=(PROPOSED if _answer(project, "scope.planning_approval")
                    else NEEDS_INPUT),
            evidence=("概念空间策略：" + spatial[:60]) if spatial else "概念空间策略未形成",
            demanded_by=plan_words,
            interfaces=["IF-PLAN-FAR"] if "planning" in active else [],
        )

    if "interior" in active:
        has_material = bool(materials)
        out["interior"] = _direction(
            "interior",
            goal="把概念落到人每天接触的界面、家具与光",
            strategy=((spatial or "按概念的分区与动线组织室内") +
                      (f"；材料按已锁定风格执行：{'、'.join(materials[:4])}" if has_material else "")),
            deliverables=["平面布置", "顶墙地做法", "家具与固定件", "材料表"],
            open_questions=[] if has_material else ["材料方向待 G2 锁定"],
            status=PROPOSED if has_material else NEEDS_INPUT,
            evidence=f"材料 {len(materials)} 项来自概念",
            demanded_by=mep_words[:2],
            interfaces=[i for i in ("IF-ARCH-IN", "IF-MEP-HEIGHT", "IF-STR-OPENING",
                                    "IF-MEP-WET") if _iface_active(i, active)],
        )

    if "structure" in active:
        e = scope.entries.get("structure")
        unverified = bool(e and e.state in (D.INFERRED, D.UNKNOWN, D.REQUIRED))
        if struct_words:
            # 这套概念真的向结构提了要求：列出它要回答的具体问题
            asks = _structure_asks(struct_words, proto)
            strategy = ("这套概念要求结构回答：" + "；".join(asks) +
                        "。做法是先鉴定、再定拆改，不做无依据的假定。")
            goal = "确认这套空间主张在结构上能不能成立"
            demanded: Sequence[str] = struct_words
            status = NEEDS_INPUT          # 有要求但没资料 → 待输入
        else:
            strategy = ("这套概念不改变结构体系：结构按现状复核即可，"
                        "重点是确认后续深化不产生新的荷载或开洞需求。")
            goal = "确认不改结构的前提下，后续深化不会反悔"
            asks = ["现状结构是否需要复核"]
            demanded = ()
            status = PROPOSED if not unverified else NEEDS_INPUT
        out["structure"] = _direction(
            "structure",
            goal=goal,
            strategy=strategy,
            deliverables=["结构现状说明", "拆改可行性条件",
                          "加固/新增构件方案（由结构工程师出）"],
            open_questions=["现有结构图纸", *[a for a in asks[:2]],
                            "荷载变化"],
            status=status,
            evidence=((e.evidence if e else "") or "未提供结构资料") +
                     ("；概念触发：" + "、".join(struct_words[:4]) if struct_words else ""),
            demanded_by=demanded,
            interfaces=[i for i in ("IF-STR-SPACE", "IF-STR-OPENING", "IF-STR-LOAD")
                        if _iface_active(i, active)],
        )

    if "mep" in active:
        e = scope.entries.get("mep")
        unverified = bool(e and e.state in (D.INFERRED, D.UNKNOWN, D.REQUIRED))
        if mep_words or daylight:
            asks = _mep_asks(mep_words, daylight, proto)
            strategy = ("这套概念要求机电配套：" + "；".join(asks) +
                        "。负荷与管综由机电工程师计算，系统只提条件。")
            status = NEEDS_INPUT
        else:
            strategy = ("这套概念不新增机电系统：按现有容量核对点位即可，"
                        "重点是末端位置随家具走。")
            asks = ["现有容量是否够用"]
            status = PROPOSED if not unverified else NEEDS_INPUT
        out["mep"] = _direction(
            "mep",
            goal="让机电容量与点位配得上这套空间，而不是后期打补丁",
            strategy=strategy,
            deliverables=["点位与容量提资", "管综走向示意", "消防与排烟条件"],
            open_questions=["机电系统现状", "可用容量", "消防审批要求"],
            status=status,
            evidence=((e.evidence if e else "") or "未提供机电资料") +
                     ("；概念触发：" + "、".join((mep_words + ([daylight] if daylight else []))[:4])
                      if (mep_words or daylight) else ""),
            demanded_by=mep_words,
            interfaces=[i for i in ("IF-MEP-HEIGHT", "IF-MEP-WET", "IF-MEP-LAND",
                                    "IF-FACADE-MEP") if _iface_active(i, active)],
        )

    if "landscape" in active:
        program = _answer(project, "scope.landscape_program", "outdoor_program")
        if land_words:
            strategy = (
                f"这套概念把室外当作{_land_role(land_words)}："
                + (_quote(text, land_words, 1) or "") +
                "。先定竖向与排水，再定铺装与种植；室外的水与电在方案阶段就要有位置。")
            status = PROPOSED if program else NEEDS_INPUT
        else:
            strategy = ("这套概念不需要新增室外空间：景观按现状维护处理，"
                        "不参与空间组织。")
            status = PROPOSED if program else NEEDS_INPUT
        out["landscape"] = _direction(
            "landscape",
            goal="把室外做成室内能借用的空间，而不是剩下的空地",
            strategy=strategy,
            deliverables=["景观分区图", "竖向与排水", "铺装与种植做法"],
            open_questions=[] if program else ["室外主要用途（铺装/种植/水景/屋顶花园）"],
            status=status,
            evidence=program or ("概念触发：" + "、".join(land_words[:4])
                                 if land_words else "尚未说明室外用途"),
            demanded_by=land_words,
            interfaces=[i for i in ("IF-WATER-FR", "IF-MEP-LAND", "IF-IN-LAND",
                                    "IF-STR-LOAD", "IF-PLAN-LAND")
                        if _iface_active(i, active)],
        )

    if "planning" in active:
        approval = _answer(project, "scope.planning_approval")
        out["planning"] = _direction(
            "planning",
            goal="先确认这个方案在规划上可不可行，再谈好不好看",
            strategy=("按项目所在地的规划条件逐项核对指标；本系统只列条件与缺口，"
                      "不出法定结论" +
                      (f"。这套概念涉及：{'、'.join(plan_words[:3])}" if plan_words else "")),
            deliverables=["规划指标核对表", "报批路径与前置条件"],
            open_questions=[] if approval else ["是否需要报建、已知的容积率/退线/限高"],
            status=PROPOSED if approval else NEEDS_INPUT,
            evidence=approval or "未说明报批要求",
            demanded_by=plan_words,
            interfaces=[i for i in ("IF-PLAN-FAR", "IF-PLAN-LAND")
                        if _iface_active(i, active)],
        )
    return out


def _iface_active(iid: str, active: Sequence[str]) -> bool:
    for it in D.INTERFACES:
        if it.id == iid:
            return all(x in active for x in it.pair)
    return False


def _land_role(words: Sequence[str]) -> str:
    if any(w in words for w in ("内院", "中庭", "天井")):
        return "采光与通风的来源"
    if any(w in words for w in ("屋顶", "露台")):
        return "多出来的一层可用空间（同时是防水与荷载的负担）"
    if any(w in words for w in ("水池", "水景")):
        return "空间焦点（同时是防水、排水与设备的负担）"
    return "室内空间的延伸"


def _structure_asks(words: Sequence[str], proto: Dict[str, Any]) -> List[str]:
    """把结构信号翻成"这套概念必须由结构回答的问题"。"""
    asks: List[str] = []
    if any(w in words for w in ("挑空", "通高", "大跨", "跨度", "悬挑")):
        asks.append("通高/大跨处能不能不落柱、允许的最大跨度是多少")
    if any(w in words for w in ("拆", "承重", "开洞")):
        asks.append("要打掉的隔墙是不是承重墙、开洞限值多少")
    if any(w in words for w in ("夹层", "加建", "错层", "跃层")):
        asks.append("新增楼层的荷载由谁承担、原基础是否够")
    if any(w in words for w in ("下沉", "回填")):
        asks.append("下沉部位的底板与防水做法")
    if any(w in words for w in ("楼板", "荷载")):
        asks.append("楼板允许附加荷载（含家具与种植）")
    if not asks:
        asks.append("这套概念对结构的实际要求（须按原文判读）")
    return asks[:3]


def _mep_asks(words: Sequence[str], daylight: str,
              proto: Dict[str, Any]) -> List[str]:
    asks: List[str] = []
    if any(w in words for w in ("机械通风", "新风", "空调")):
        asks.append("无窗或内区空间的通风路径与设备位置")
    if any(w in words for w in ("湿区", "厨房", "卫", "排水", "立管")):
        asks.append("湿区位置能否对上原立管，是否需要降板或同层排水")
    if any(w in words for w in ("灌溉", "水景", "泵")):
        asks.append("室外灌溉与水体循环的水源、电量与检修口")
    if any(w in words for w in ("照明", "配电")):
        asks.append("照明回路的容量与分区控制")
    if any(w in words for w in ("喷淋", "排烟")):
        asks.append("消防设施是否因空间改造而需要重新报审")
    if "引光" in daylight or "高窗" in daylight:
        asks.append("高窗/玻璃砖处的通风与遮阳如何解决")
    if not asks:
        asks.append("末端点位随家具布置的调整范围")
    return asks[:3]


def summary_lines(directions: Dict[str, Dict[str, Any]]) -> List[str]:
    lines: List[str] = []
    for did, d in directions.items():
        flag = "" if d["status"] == PROPOSED else "（待补资料）"
        lines.append(f"- {d['label']}{flag}：{d['strategy'][:60]}")
    return lines


__all__ = ["for_concept", "summary_lines", "PROPOSED", "NEEDS_INPUT",
           "STRUCTURE_SIGNALS", "MEP_SIGNALS", "LANDSCAPE_SIGNALS"]
