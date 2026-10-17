"""User & lifestyle analysis: what the space is *for*, not what it is called.

"需要一个大厅" is not a requirement, it is a wish with no constraint attached.
A living room used for eight-person dinners, one used for children's homework
and one used for receiving clients produce three different rooms. This module
turns stated wishes into rows that a designer can actually check:

activity → who → how often → how many → what it needs → how private →
what it must sit next to → how sure we are.

Nothing is invented. Rows come from the interview answers, the project
program, or explicit source documents, and each row carries its provenance.

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from ..model import Project
from .interview import load_interview
from .profiles import QUESTION_INDEX

# Room recipe -> the activities it normally hosts. These are *defaults to be
# confirmed*, so rows built from them are marked `inferred`.
PROGRAM_ACTIVITY: Dict[str, Tuple[str, ...]] = {
    "living": ("家庭聚集 / 观看", "待客"),
    "dining": ("用餐 / 聚餐",),
    "kitchen": ("备餐 / 烹饪",),
    "master_bedroom": ("睡眠 / 更衣",),
    "bedroom": ("睡眠 / 学习",),
    "study": ("专注工作 / 阅读",),
    "bathroom": ("洗浴 / 如厕",),
    "entry": ("进出 / 换鞋 / 暂存",),
    "storage": ("收纳 / 储物",),
    "balcony": ("晾晒 / 休憩",),
    "corridor": ("通行",),
}

# Activity inference from the client's own wording. Deliberately small and
# transparent: every hit is reported with the phrase that triggered it.
ACTIVITY_CUES: Tuple[Tuple[str, str, str], ...] = (
    ("吃饭|聚餐|宴请|坐.*人.*吃", "聚餐 / 待客", "多人同时用餐，需要桌位与通行同时成立"),
    ("孩子|儿童|作业|写作业", "儿童活动 / 学习", "需要视线可达与噪声隔离同时成立"),
    ("看电视|影音|电影|投影|音响", "影音娱乐", "需要视线与声学处理，避免干扰睡眠区"),
    ("办公|工作|开会|视频会|远程", "居家办公 / 专注", "需要安静与背景控制，不能靠走道"),
    ("衣帽间|更衣", "更衣 / 收纳", "需要固定容积与照明，不能靠床尾柜替代"),
    ("收纳|储物|衣柜|行李箱|杂物", "收纳", "按物品体积与取用频率分配，不按剩余空间填"),
    ("做饭|烹饪|开火|下厨", "烹饪", "涉及排烟、补风与油污，决定厨房是否封闭"),
    ("客人|访客|接待|会客", "待客", "涉及公共区开放度与独立客卫"),
    ("健身|瑜伽|器械", "运动", "涉及净高、地面做法与设备荷载"),
    ("老人|长辈|照护|轮椅", "照护 / 无障碍", "涉及净宽、扶手预埋与夜间照明"),
    ("宠物|猫|狗", "宠物活动", "涉及耐污材料与清洗点"),
    ("收藏|展示|摆件|酒", "收藏展示", "涉及照明与防尘，常被当成装饰忽略"),
)

PRIORITY_LABEL = {"must": "必须", "should": "应该", "could": "可以"}


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass
class NeedRow:
    id: str
    activity: str
    users: str = ""
    frequency: str = ""
    headcount: Optional[int] = None
    space_need: str = ""
    equipment: str = ""
    privacy: str = "中"           # 高 / 中 / 低
    acoustic: str = ""
    adjacency: str = ""
    separation: str = ""
    priority: str = "should"
    future: str = ""
    source: str = ""
    state: str = "inferred"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "activity": self.activity,
            "users": self.users,
            "frequency": self.frequency,
            "headcount": self.headcount,
            "space_need": self.space_need,
            "equipment": self.equipment,
            "privacy": self.privacy,
            "acoustic": self.acoustic,
            "adjacency": self.adjacency,
            "separation": self.separation,
            "priority": self.priority,
            "priority_label": PRIORITY_LABEL.get(self.priority, self.priority),
            "future": self.future,
            "source": self.source,
            "state": self.state,
        }


def _answers(project: Project) -> Dict[str, Dict[str, Any]]:
    return dict(load_interview(project).answers or {})


def _answer_text(project: Project, qid: str) -> str:
    ans = _answers(project).get(qid) or {}
    return str(ans.get("value") or "") if ans.get("state") in ("answered", "assumed") else ""


def _split_list(value: str) -> List[str]:
    for sep in ("；", ";", "、", "，", ",", "\n", "|"):
        if sep in value:
            return [p.strip() for p in value.split(sep) if p.strip()]
    return [value.strip()] if value.strip() else []


def _headcount_from(text: str) -> Optional[int]:
    import re

    m = re.search(r"(\d{1,3})\s*(?:个)?人", text)
    if m:
        try:
            return int(m.group(1))
        except ValueError:
            return None
    return None


def _rows_from_needs(project: Project) -> List[NeedRow]:
    """Turn each stated need into a row, inferring the activity from wording."""
    rows: List[NeedRow] = []
    users = _answer_text(project, "res.household") or _answer_text(
        project, "off.headcount") or ""
    rhythm = _answer_text(project, "res.daily_rhythm")
    raw = _answer_text(project, "base.needs")
    items = _split_list(raw)
    for i, item in enumerate(items, 1):
        activity, constraint = "", ""
        for pattern, act, cons in ACTIVITY_CUES:
            import re

            if re.search(pattern, item):
                activity, constraint = act, cons
                break
        rows.append(NeedRow(
            id=f"N{i:02d}",
            activity=activity or item,
            users=users,
            frequency=rhythm if rhythm and activity else "",
            headcount=_headcount_from(item),
            space_need=constraint or item,
            priority="must" if i <= 3 else "should",
            source="base.needs",
            state="documented" if activity else "inferred",
        ))
    return rows


def _rows_from_program(project: Project) -> List[NeedRow]:
    """Rooms already in the program, marked as inferred activity."""
    rows: List[NeedRow] = []
    for i, p in enumerate(project.program or [], 1):
        name = str(p.get("name") or "").strip()
        if not name:
            continue
        recipe = str(p.get("recipe") or "")
        acts = PROGRAM_ACTIVITY.get(recipe) or ()
        for act in (acts or (f"待确认用途：{name}",)):
            rows.append(NeedRow(
                id=f"P{i:02d}",
                activity=act,
                space_need=(f"目标面积 {p.get('area_m2')} m²" if p.get("area_m2") else ""),
                priority="must" if recipe in ("living", "master_bedroom", "kitchen",
                                              "dining") else "should",
                source=f"program:{name}",
                state="inferred",
            ))
    return rows


def _rows_from_rhythm(project: Project) -> List[NeedRow]:
    """The daily rhythm question often reveals a need nobody listed."""
    rows: List[NeedRow] = []
    rhythm = _answer_text(project, "res.daily_rhythm")
    if not rhythm:
        return rows
    import re

    for pattern, act, cons in ACTIVITY_CUES:
        if re.search(pattern, rhythm):
            rows.append(NeedRow(
                id=f"R{len(rows)+1:02d}",
                activity=act,
                frequency=rhythm,
                space_need=cons,
                priority="should",
                source="res.daily_rhythm",
                state="inferred",
            ))
    return rows


def _dedupe(rows: Sequence[NeedRow]) -> List[NeedRow]:
    seen: Dict[str, NeedRow] = {}
    for r in rows:
        key = r.activity.strip()
        if not key:
            continue
        if key in seen:
            # Keep the stronger evidence and the richer detail.
            old = seen[key]
            rank = {"verified": 0, "documented": 1, "inferred": 2,
                    "unknown": 3, "conflicting": 4}
            if rank.get(r.state, 9) < rank.get(old.state, 9):
                seen[key] = r
            elif not seen[key].frequency and r.frequency:
                seen[key].frequency = r.frequency
            continue
        seen[key] = r
    return list(seen.values())


def build_need_matrix(project: Project) -> Dict[str, Any]:
    """The structured functional matrix, with gaps stated rather than filled."""
    rows = _dedupe(_rows_from_needs(project) + _rows_from_program(project)
                   + _rows_from_rhythm(project))
    for i, r in enumerate(rows, 1):
        r.id = f"N{i:02d}"

    gaps: List[str] = []
    base_needs = _answer_text(project, "base.needs")
    if not base_needs:
        gaps.append("核心功能需求尚未回答：当前矩阵只覆盖已有 program，不含业主真实用途")
    if any(not r.headcount for r in rows if "聚餐" in r.activity):
        gaps.append("聚餐人数未确认：无法校核餐桌尺寸与通行")
    if rows and all(r.state == "inferred" for r in rows):
        gaps.append("所有需求行均为推断：需在 G1 前由业主逐条确认用途")

    counts = {"must": 0, "should": 0, "could": 0}
    for r in rows:
        counts[r.priority] = counts.get(r.priority, 0) + 1

    return {
        "project_id": project.project_id,
        "revision": project.revision,
        "generated_at": _now(),
        "rows": [r.to_dict() for r in rows],
        "counts": counts,
        "gaps": gaps,
        "note": ("行内 state 表示来源强度：verified 已核验 / documented 有文件依据 / "
                 "inferred 推断 / unknown 未知 / conflicting 来源冲突。"
                 "推断行不得直接当作面积或布置依据。"),
    }


def markdown(matrix: Dict[str, Any]) -> str:
    lines = ["| # | 活动 | 使用者 | 频率 | 人数 | 空间与设备 | 隐私 | 来源状态 | 优先级 |",
             "|---|---|---|---|---|---|---|---|---|"]
    for r in matrix["rows"]:
        lines.append(
            f"| {r['id']} | {r['activity']} | {r['users'] or '—'} | {r['frequency'] or '—'} "
            f"| {r['headcount'] or '—'} | {r['space_need'] or '—'} | {r['privacy']} "
            f"| {r['state']} | {r['priority_label']} |"
        )
    return "\n".join(lines)
