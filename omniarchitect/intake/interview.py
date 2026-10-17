"""Dynamic interview state machine.

The interview is stateful on purpose: a real brief is built over several
sittings, answers get corrected, and some questions only make sense after
others are answered. So this module persists:

* which profile is in use (a flat is not asked about meeting rooms);
* every answer, with its state (answered / unknown / deferred) and revision;
* which questions were already asked, so nothing is asked twice;
* the completeness of the information slots, which decides how far S1 may go.

Rules that the code enforces rather than documents:

1. one slot is asked once — a different wording for the same slot is skipped;
2. questions with an unmet dependency are not asked;
3. at most three questions per round, ordered by consequence;
4. "不知道" is a valid answer: it becomes an explicit gap, not a blocker loop;
5. correcting an answer after G1 records a revision change instead of
   silently overwriting the confirmed baseline.

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple

from ..model import Project
from .profiles import (
    COMPLETE_AT,
    PRIORITY_ORDER,
    PROFILES,
    QUESTION_INDEX,
    SLOTS,
    Profile,
    Question,
    WORKING_AT,
    critical_slots,
    profile_for,
    slots_for,
)

# Answer states. `assumed` is reserved for values the system had to fill in
# order to keep going; it is always reported, never hidden.
ANSWER_STATES = ("answered", "unknown", "deferred", "assumed")

MAX_QUESTIONS_PER_ROUND = 3
MAX_ROUNDS_WITHOUT_PROGRESS = 3


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _intake(project: Project) -> Dict[str, Any]:
    """Return the *same* intake dict every call.

    Earlier this returned a fresh copy, so two helpers writing through it
    silently overwrote each other (the outer profile_id vanished while the
    interview survived). Holding one object is the fix.
    """
    meta = project.meta if isinstance(project.meta, dict) else {}
    intake = meta.get("intake")
    if not isinstance(intake, dict):
        intake = {}
        meta["intake"] = intake
    project.meta = meta
    return intake


def _store(project: Project) -> Dict[str, Any]:
    intake = _intake(project)
    state = dict(intake.get("interview") or {})
    intake["interview"] = state
    return state


@dataclass
class Answer:
    question_id: str
    value: str = ""
    state: str = "answered"
    at: str = ""
    revision: int = 0
    source: str = "user"
    note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "question_id": self.question_id,
            "value": self.value,
            "state": self.state,
            "at": self.at or _now(),
            "revision": self.revision,
            "source": self.source,
            "note": self.note,
        }


@dataclass
class InterviewState:
    profile_id: str = ""
    start_mode: str = ""
    started_at: str = ""
    updated_at: str = ""
    rounds: int = 0
    answers: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    asked: Dict[str, str] = field(default_factory=dict)
    note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "start_mode": self.start_mode,
            "started_at": self.started_at,
            "updated_at": self.updated_at,
            "rounds": self.rounds,
            "answers": dict(self.answers),
            "asked": dict(self.asked),
            "note": self.note,
        }


# --------------------------------------------------------------------------
# start modes
# --------------------------------------------------------------------------
def detect_start_mode(project: Project, text: str = "") -> str:
    """Which of the three entry situations are we in?

    ``words_only``    a sentence and nothing else
    ``with_assets``   drawings / photos / a written brief exist
    ``complete``      enough is known to write a first brief directly
    """
    prof = profile_for(text, str((project.constraints or {}).get("style") or ""),
                       project.name or "")
    covered = _covered_slots(project)
    ratio = _completeness(prof, covered)
    has_assets = bool(project.sources) or bool(_intake(project).get("sources"))
    needs_count = len([p for p in (project.program or []) if p.get("name")])
    if ratio >= COMPLETE_AT and needs_count >= 3:
        return "complete"
    if has_assets or needs_count >= 3:
        return "with_assets"
    if len((text or "").strip()) <= 200:
        return "words_only"
    return "with_assets"


START_MODE_LABEL = {
    "words_only": "只有一句话需求",
    "with_assets": "已有图纸 / 照片 / 任务书",
    "complete": "资料基本完整",
}


# --------------------------------------------------------------------------
# slot coverage
# --------------------------------------------------------------------------
def _answer_for_slot(project: Project, slot: str) -> Optional[Dict[str, Any]]:
    state = _store(project)
    for qid, ans in (state.get("answers") or {}).items():
        q = QUESTION_INDEX.get(qid)
        if q and q.slot == slot and ans.get("state") in ("answered", "assumed"):
            return ans
    return None


def _covered_slots(project: Project) -> Dict[str, str]:
    """slot -> how it became known (answer id / model field)."""
    covered: Dict[str, str] = {}
    state = _store(project)
    for qid, ans in (state.get("answers") or {}).items():
        q = QUESTION_INDEX.get(qid)
        if q and ans.get("state") in ("answered", "assumed"):
            covered.setdefault(q.slot, qid)

    cons = project.constraints or {}
    if cons.get("location") or cons.get("city"):
        covered.setdefault("location", "constraints:location")
    if cons.get("budget_cny"):
        covered.setdefault("budget", "constraints:budget_cny")
    if cons.get("style"):
        covered.setdefault("style", "constraints:style")
    if cons.get("project_type"):
        covered.setdefault("project_type", "constraints:project_type")
    if project.program:
        covered.setdefault("needs", "program")
    if project.spaces or project.elements:
        covered.setdefault("floor_area", "model:geometry")
        covered.setdefault("drawings", "model:geometry")
    for s in (project.sources or []):
        kind = str(s.get("type") or "")
        if kind in ("cad", "pdf", "image", "scan", "photo"):
            covered.setdefault("drawings", f"source:{s.get('id')}")
        if kind in ("measure", "note"):
            covered.setdefault("site_conditions", f"source:{s.get('id')}")
    return covered


def _completeness(profile: Profile, covered: Dict[str, str]) -> float:
    slots = slots_for(profile)
    total = sum(float(SLOTS[s]["weight"]) for s in slots)
    if not total:
        return 0.0
    got = sum(float(SLOTS[s]["weight"]) for s in slots if s in covered)
    return round(got / total, 3)


def completeness(project: Project) -> Dict[str, Any]:
    """How complete is the brief, in the terms this profile cares about."""
    state = _store(project)
    profile = PROFILES.get(state.get("profile_id") or "") or profile_for(
        project.name or "", str((project.constraints or {}).get("style") or ""))
    covered = _covered_slots(project)
    slots = slots_for(profile)
    ratio = _completeness(profile, covered)
    missing = [s for s in slots if s not in covered]
    critical_missing = [s for s in missing if SLOTS[s]["critical"]]
    if ratio >= COMPLETE_AT:
        verdict = "complete"
    elif ratio >= WORKING_AT:
        verdict = "working"
    else:
        verdict = "thin"
    return {
        "profile": profile.id,
        "profile_label": profile.label,
        "ratio": ratio,
        "verdict": verdict,
        "covered": sorted(covered),
        "missing": missing,
        "missing_critical": critical_missing,
        "covered_detail": dict(covered),
    }


# --------------------------------------------------------------------------
# extract what the client already told us, so we never ask twice
# --------------------------------------------------------------------------
_AREA_RE = r"(\d+(?:\.\d+)?)\s*(?:㎡|平方米|平米|m2|m²|sqm)"
_CITY_RE = r"(?:在|位于|坐标)\s*([\u4e00-\u9fa5]{2,10}?(?:市|区|县|镇))"
_STYLE_WORDS = ("现代", "极简", "意式", "法式", "日式", "北欧", "工业", "侘寂",
                "新中式", "中式", "美式", "轻奢", "奶油", "原木", "复古", "侘寂风")

SEED_NOTE = "从首句需求解析，请在 G1 前确认"

_CN_DIGITS = {"一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5,
              "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}


def _cn_number(token: str) -> int:
    """`三` -> 3, `十二` -> 12, `3` -> 3. Returns 0 when unparseable."""
    token = (token or "").strip()
    if not token:
        return 0
    if token.isdigit():
        return int(token)
    if token in _CN_DIGITS:
        return _CN_DIGITS[token]
    if token.startswith("十") and len(token) == 1:
        return 10
    if token.startswith("十"):
        return 10 + _CN_DIGITS.get(token[1], 0)
    if len(token) == 2 and token[0] in _CN_DIGITS and token[1] == "十":
        return _CN_DIGITS[token[0]] * 10
    if len(token) == 3 and token[1] == "十":
        return _CN_DIGITS.get(token[0], 0) * 10 + _CN_DIGITS.get(token[2], 0)
    return 0


def seed_from_text(project: Project, text: str) -> List[str]:
    """Seed answers from the client's first sentence.

    Asking "how big is it" after the client said "150 m²" is the fastest way to
    look like a form. Everything extracted here is marked as *stated by the
    client*, with a note asking for confirmation at G1 — it is never treated as
    verified.
    """
    import re

    if not (text or "").strip():
        return []
    state = _store(project)
    answers = dict(state.get("answers") or {})
    seeded: List[str] = []

    def put(qid: str, value: str) -> None:
        if qid in answers:
            return
        answers[qid] = Answer(question_id=qid, value=value, state="answered",
                              at=_now(), revision=project.revision,
                              source="text", note=SEED_NOTE).to_dict()
        seeded.append(qid)

    m = re.search(_AREA_RE, text)
    if m:
        put("base.floor_area", f"{m.group(1)} m²（业主原话）")
    m = re.search(_CITY_RE, text)
    if m:
        put("base.location", m.group(1))
    hits = [w for w in _STYLE_WORDS if w in text]
    if hits:
        put("base.style", "、".join(dict.fromkeys(hits)))
    m = re.search(r"([一二三四五六七八九十两\d]{1,3})\s*口", text)
    if m:
        n = _cn_number(m.group(1))
        if n:
            put("res.household", f"{n} 口人（业主原话）")
    m = re.search(r"(\d{1,4})\s*(?:人|位)\s*(?:办公|工位|团队)", text)
    if m:
        put("off.headcount", f"{m.group(1)} 人（业主原话）")
    m = re.search(r"(\d{1,3})\s*(?:间)?\s*客房", text)
    if m:
        put("hos.keys", f"{m.group(1)} 间客房（业主原话）")

    if seeded:
        state["answers"] = answers
        state["updated_at"] = _now()
        _intake(project)["interview"] = state
    return seeded


def _assume_project_type(project: Project, profile: Profile) -> Optional[str]:
    """Record the inferred type as an assumption, not as a client answer.

    The profile guess is useful (it decides which questions to ask) but it is
    still a guess — "办公室改成住宅" is a real project type. So it goes in as
    `assumed` and stays visible in the brief.
    """
    state = _store(project)
    answers = dict(state.get("answers") or {})
    if "base.project_type" in answers:
        return None
    answers["base.project_type"] = Answer(
        question_id="base.project_type", value=profile.label, state="assumed",
        at=_now(), revision=project.revision, source="profile",
        note="按需求描述推断的项目类型；如判断有误请直接纠正",
    ).to_dict()
    state["answers"] = answers
    _intake(project)["interview"] = state
    return "base.project_type"


# --------------------------------------------------------------------------
# interview lifecycle
# --------------------------------------------------------------------------
def start_interview(project: Project, text: str = "",
                    profile_id: str = "") -> InterviewState:
    """Create or resume an interview. Never resets existing answers."""
    intake = _intake(project)
    state = _store(project)
    profile = PROFILES.get(profile_id or "") or profile_for(
        text, project.name or "", str((project.constraints or {}).get("style") or ""))
    if not state.get("profile_id"):
        state["profile_id"] = profile.id
        state["started_at"] = _now()
        # Only guess the entry mode once; a resumed interview must not flip it.
        state["start_mode"] = detect_start_mode(project, text)
        _intake(project)["interview"] = state
        seed_from_text(project, text)
        _assume_project_type(project, profile)
        state = _store(project)
    state["updated_at"] = _now()
    intake["interview"] = state
    intake["profile_id"] = state["profile_id"]
    intake["start_mode"] = state.get("start_mode", "")
    intake["completeness"] = completeness(project)
    from .diligence import store_precision

    store_precision(project)
    return InterviewState(
        profile_id=str(state["profile_id"]),
        start_mode=str(state.get("start_mode") or ""),
        started_at=str(state.get("started_at") or ""),
        updated_at=str(state.get("updated_at") or ""),
        rounds=int(state.get("rounds") or 0),
        answers=dict(state.get("answers") or {}),
        asked=dict(state.get("asked") or {}),
        note=str(state.get("note") or ""),
    )


def load_interview(project: Project) -> InterviewState:
    state = _store(project)
    return InterviewState(
        profile_id=str(state.get("profile_id") or ""),
        start_mode=str(state.get("start_mode") or ""),
        started_at=str(state.get("started_at") or ""),
        updated_at=str(state.get("updated_at") or ""),
        rounds=int(state.get("rounds") or 0),
        answers=dict(state.get("answers") or {}),
        asked=dict(state.get("asked") or {}),
        note=str(state.get("note") or ""),
    )


def save_interview(project: Project, state: InterviewState) -> None:
    state.updated_at = _now()
    _intake(project)["interview"] = state.to_dict()


def _answered(project: Project, qid: str) -> Optional[Dict[str, Any]]:
    return (_store(project).get("answers") or {}).get(qid)


def _dependency_ok(project: Project, q: Question) -> bool:
    if not q.depends_on:
        return True
    ans = _answered(project, q.depends_on)
    if not ans or ans.get("state") != "answered":
        return False
    want = (q.depends_value or "").strip()
    return want.lower() in str(ans.get("value") or "").lower() if want else True


def next_questions(project: Project, limit: int = MAX_QUESTIONS_PER_ROUND,
                   include_asked: bool = False) -> List[Question]:
    """The one to three questions that matter most right now.

    Ordering is by *consequence*: critical first, then the deepest stage the
    answer can change, then profile order. A question whose slot is already
    covered is never returned, even if it was asked under a different wording.
    """
    state = _store(project)
    profile = PROFILES.get(str(state.get("profile_id") or "")) or profile_for(
        project.name or "")
    covered = _covered_slots(project)
    asked = state.get("asked") or {}
    out: List[Question] = []
    for q in profile.questions:
        if q.slot in covered:
            continue
        if not include_asked and q.id in asked:
            continue
        if not _dependency_ok(project, q):
            continue
        out.append(q)
    out.sort(key=lambda q: (PRIORITY_ORDER.get(q.priority, 9),
                            -_stage_index(q.affects),
                            profile.questions.index(q)))
    return out[:max(0, limit)]


def _stage_index(stage_id: str) -> int:
    from ..stages import STAGE_ORDER
    try:
        return STAGE_ORDER.index(stage_id)
    except ValueError:
        return 0


def current_questions(project: Project) -> List[Question]:
    """Questions already handed to the user and not yet answered."""
    state = _store(project)
    asked = state.get("asked") or {}
    answers = state.get("answers") or {}
    return [QUESTION_INDEX[qid] for qid in asked
            if qid not in answers and qid in QUESTION_INDEX]


# Which answers feed the uncertainty register, and how strong the evidence is.
# Without this, the diligence module would stay empty while the client keeps
# saying "不清楚" — the exact failure this round is meant to remove.
_UNCERTAINTY_FROM_ANSWER: Dict[str, Tuple[str, str]] = {
    # question id -> (topic, template)
    "base.structure": ("structural", "结构条件：{value}"),
    "arc.approval": ("regulatory", "报批状态：{value}"),
    "base.drawings": ("dimension", "原始图纸：{value}"),
    "base.site_conditions": ("services", "现场与建筑条件：{value}"),
    "arc.geotech": ("structural", "地基与地勘：{value}"),
    "arc.plot": ("regulatory", "规划条件：{value}"),
}

_NEGATIVE = ("不清楚", "不知道", "没有", "不确定", "没说", "未定", "暂无",
             "没有图纸", "未提供", "还不", "不了解", "不清楚，")
_WEAK_VISUAL = ("拍照", "扫描", "照片", "图片")


def _evidence_state(project: Project, q: Question, value: str,
                    answer_state: str) -> str:
    """Map an answer to one of the five confidence states.

    The mapping is deliberately pessimistic: a client saying "有图纸" gives us
    a *document*, not a verification, and a photo gives us an inference.
    """
    if answer_state == "unknown":
        return "unknown"
    text = value or ""
    if answer_state == "deferred":
        return "unknown"
    if any(w in text for w in _NEGATIVE):
        return "unknown"
    if q.id == "base.drawings":
        if any(w in text for w in _WEAK_VISUAL):
            return "inferred"
        return "documented"
    if answer_state == "assumed":
        return "inferred"
    return "documented"


def _sync_uncertainty(project: Project, q: Question, value: str,
                      answer_state: str) -> Optional[str]:
    """Keep the uncertainty register in step with what the client just said."""
    from .diligence import UncertaintyItem, register_uncertainty

    mapping = _UNCERTAINTY_FROM_ANSWER.get(q.id)
    if not mapping:
        return None
    topic, template = mapping
    state = _evidence_state(project, q, value, answer_state)
    if state == "documented":
        # Documented is good enough not to be an open item; the source register
        # records it instead, and the brief lists it as a known condition.
        return None
    item = UncertaintyItem(
        id=f"U-{topic.upper()}",
        topic=topic,
        statement=template.format(value=value or "未说明"),
        state=state,
        sources=[q.id],
        affects=q.affects,
    )
    register_uncertainty(project, item)
    return item.id


def answer_question(project: Project, qid: str, value: str,
                    state_name: str = "answered", note: str = "") -> Dict[str, Any]:
    """Record an answer. Correcting an earlier answer is allowed and tracked.

    Returns a small report telling the caller whether the change has to go
    through the change-impact path (because the brief was already confirmed).
    """
    q = QUESTION_INDEX.get(qid)
    if q is None:
        raise KeyError(f"unknown question '{qid}'")
    if state_name not in ANSWER_STATES:
        raise ValueError(f"unknown answer state '{state_name}'")
    from ..stage_state import CONFIRMED, get_state

    st = _store(project)
    answers = dict(st.get("answers") or {})
    previous = answers.get(qid)
    was_confirmed = get_state(project, "S1").status == CONFIRMED

    rec = Answer(
        question_id=qid, value=(value or "").strip(), state=state_name,
        at=_now(), revision=project.revision, note=note,
    ).to_dict()
    answers[qid] = rec
    st["answers"] = answers
    asked = dict(st.get("asked") or {})
    asked[qid] = asked.get(qid) or _now()
    st["asked"] = asked
    st["updated_at"] = _now()
    _intake(project)["interview"] = st

    uncertainty_id = _sync_uncertainty(project, q, value, state_name)
    changed = bool(previous) and str(previous.get("value")) != rec["value"]
    result = {
        "uncertainty_registered": uncertainty_id,
        "question_id": qid,
        "slot": q.slot,
        "state": state_name,
        "value": rec["value"],
        "changed": changed,
        "previous": (previous or {}).get("value", ""),
        "requires_change_analysis": bool(changed and was_confirmed),
        "completeness": completeness(project),
    }
    if changed and was_confirmed:
        # The baseline is never overwritten silently: the caller must run the
        # change-impact analysis, which will mark S1 and downstream as rework.
        result["note"] = ("任务书已确认，此次修改需走变更影响分析；"
                          "原确认版仍保留在 S1 修订记录中")
    return result


def record_answer(project: Project, qid: str, value: str, **kw) -> Dict[str, Any]:
    """Alias kept for readability at call sites."""
    return answer_question(project, qid, value, **kw)


def mark_asked(project: Project, qids: Sequence[str]) -> None:
    st = _store(project)
    asked = dict(st.get("asked") or {})
    now = _now()
    for qid in qids:
        asked.setdefault(qid, now)
    st["asked"] = asked
    st["rounds"] = int(st.get("rounds") or 0) + 1
    st["updated_at"] = now
    _intake(project)["interview"] = st


# --------------------------------------------------------------------------
# summary
# --------------------------------------------------------------------------
def summary(project: Project) -> Dict[str, Any]:
    """Everything a caller needs to decide whether to ask, analyse or stop."""
    state = _store(project)
    profile_id = str(state.get("profile_id") or "")
    profile = PROFILES.get(profile_id) or profile_for(project.name or "")
    comp = completeness(project)
    answers = state.get("answers") or {}
    unknown = [k for k, v in answers.items() if v.get("state") == "unknown"]
    deferred = [k for k, v in answers.items() if v.get("state") == "deferred"]
    pending = next_questions(project, limit=99)
    blocking = [q for q in pending if q.priority == "critical"]
    can_proceed = not blocking
    return {
        "profile": profile.id,
        "profile_label": profile.label,
        "start_mode": str(state.get("start_mode") or ""),
        "start_mode_label": START_MODE_LABEL.get(str(state.get("start_mode") or ""), ""),
        "rounds": int(state.get("rounds") or 0),
        "answered": len([1 for v in answers.values()
                         if v.get("state") in ("answered", "assumed")]),
        "unknown": unknown,
        "deferred": deferred,
        "pending_total": len(pending),
        "pending_critical": [q.id for q in blocking],
        "can_proceed": can_proceed,
        "completeness": comp,
        "focus": profile.focus,
    }
