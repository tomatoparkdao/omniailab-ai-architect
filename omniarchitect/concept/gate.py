"""G2 概念确认：不是确认一个风格名，而是签一份设计依据。

G1 签的是"要做什么"，G2 签的是"往哪个方向做"。所以 G2 必须同时锁定：

概念 ID · 设计主张 · 空间策略 · 风格（可含组合）· 关键材料与色彩 · 视觉语言 ·
允许 S3 深化的条件 · 未解决风险 · 项目修订 · 确认人。

只确认风格名是最常见的偷懒：风格不决定房间怎么组织，锁定风格却放行 S3，
等于让平面阶段重新猜一次业主想要什么。

与 S1 一致的两条纪律：
* `source="demo"` 只确认状态，**不写概念基准**，不得被引用为业主签署；
* 确认后改动概念/风格/需求，必须走变更回流，不能只返回一个标志位。

**硬性条件不能被确认，也不能被 force 绕过。** 没有概念/没有选定 concept_id/
任务书基准已变，这三件事不是"风险值得接受"，而是"还没有可签的东西"。能被
`--acknowledge` 处理的只有明确编号的风险项（风格锁定冲突等），且必须写编号，
不能写一段"看着像"的文字——用文字片段消阻断，等于没有阻断。

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from ..model import Project
from ..stage_state import (
    block_stage,
    confirm_stage,
    get_state,
    invalidate_from,
    reject_stage,
)

DECISIONS = ("approved", "revision_requested", "blocked")
SOURCES = ("owner", "demo")

HARD = "hard"          # 没有可签的东西：任何手段都不能通过
SOFT = "soft"          # 风险明确、可由业主逐项书面接受

DECISION_LABEL = {
    "approved": "通过 · 形成概念基准",
    "revision_requested": "退回修改",
    "blocked": "阻断 · 需先解决前置条件",
}
SOURCE_LABEL = {"owner": "业主签署", "demo": "演示（不形成基准）"}

#: 可被 `--acknowledge` 明确接受的编号（硬性条件的编号不在此列）
ACKNOWLEDGEABLE = (
    "G2-STYLE-LOCK-CONFLICT",
    "G2-COND-NO-OPPORTUNITY",
    "G2-COND-PROTOTYPE-UNSUPPORTED",
    "G2-COND-DIMENSION-UNVERIFIED",
    "G2-HUMAN-STRUCTURAL",
    "G2-HUMAN-REGULATORY",
)


def _now() -> str:
    return datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%dT%H:%M:%S")


def _concept(project: Project) -> Dict[str, Any]:
    """Return the **same** concept dict every call (a copy would silently diverge)."""
    meta = project.meta if isinstance(project.meta, dict) else {}
    state = meta.get("concept")
    if not isinstance(state, dict):
        state = {}
        meta["concept"] = state
    project.meta = meta
    return state


def _risk(pid: str, text: str, kind: str = HARD) -> Dict[str, str]:
    return {"id": pid, "text": text, "kind": kind}


@dataclass
class GateAssessment:
    """What stands between this concept set and S2 being confirmed."""

    has_options: bool = False
    selected: str = ""
    blockers: List[Dict[str, str]] = field(default_factory=list)
    condition_items: List[Dict[str, str]] = field(default_factory=list)
    human_items: List[Dict[str, str]] = field(default_factory=list)
    pre_gate: bool = False
    style_conflict: List[str] = field(default_factory=list)

    # -- 兼容既有调用方的文本视图 --------------------------------------
    @property
    def blocked_reasons(self) -> List[str]:
        return [b["text"] for b in self.blockers]

    @property
    def conditions(self) -> List[str]:
        return [c["text"] for c in self.condition_items]

    @property
    def needs_human(self) -> List[str]:
        return [h["text"] for h in self.human_items]

    # -- 判定 ----------------------------------------------------------
    @property
    def hard_blockers(self) -> List[Dict[str, str]]:
        return [b for b in self.blockers if b.get("kind") == HARD]

    @property
    def soft_blockers(self) -> List[Dict[str, str]]:
        return [b for b in self.blockers if b.get("kind") == SOFT]

    @property
    def acknowledgeable_ids(self) -> List[str]:
        seen = [b["id"] for b in self.soft_blockers]
        seen += [c["id"] for c in self.condition_items]
        seen += [h["id"] for h in self.human_items]
        return sorted(set(seen))

    @property
    def can_approve(self) -> bool:
        return self.has_options and bool(self.selected) and not self.blockers

    def to_dict(self) -> Dict[str, Any]:
        return {
            "has_options": self.has_options,
            "selected": self.selected,
            "can_approve": self.can_approve,
            "blocked_reasons": list(self.blocked_reasons),
            "blockers": [dict(b) for b in self.blockers],
            "hard_blockers": [dict(b) for b in self.hard_blockers],
            "conditions": list(self.conditions),
            "condition_items": [dict(c) for c in self.condition_items],
            "needs_human": list(self.needs_human),
            "human_items": [dict(h) for h in self.human_items],
            "acknowledgeable_ids": self.acknowledgeable_ids,
            "pre_gate": self.pre_gate,
            "style_conflict": list(self.style_conflict),
        }


def assess_gate(project: Project) -> GateAssessment:
    """Judge only what G2 is responsible for: may S3 start on this concept?"""
    from ..intake.gate import check_baseline

    state = _concept(project)
    options = state.get("options") or {}
    a = GateAssessment(has_options=bool((options.get("concepts") or [])))
    if not a.has_options:
        a.blockers.append(_risk(
            "G2-NO-CONCEPT",
            "尚未生成概念方案：先运行 concept --action generate",
        ))
        return a

    a.selected = str(state.get("selected") or "")
    if not a.selected:
        a.blockers.append(_risk(
            "G2-NO-SELECTION",
            "尚未选定概念：G2 必须明确 concept_id，确认一个风格名不等于确认方案",
        ))
    elif not any(c["concept_id"] == a.selected for c in options["concepts"]):
        a.blockers.append(_risk(
            "G2-UNKNOWN-CONCEPT", f"选定的 {a.selected} 不在本批方案中"))

    # S1 的可行性结论必须进入 G2 依据：面积口径、容量、会议位
    from ..intake.feasibility import run_feasibility

    feas = run_feasibility(project)
    # G1 时业主书面接受过的限制，到 G2 不再重复阻断，但必须继续写在条件里
    _raw = ((project.meta or {}).get("intake") or {}).get("baseline") or {}
    acked = {str(x) for x in (_raw.get("acknowledged") or [])}
    for c in feas.get("conflicts") or []:
        if c["category"] not in ("area", "capacity"):
            continue
        if c["severity"] not in ("blocker", "major"):
            continue
        if c["id"] in acked:
            a.condition_items.append({
                "id": f"G2-ACKED-{c['id']}",
                "text": f"业主已在 G1 书面接受：{c['problem']}（{c['evidence']}）",
                "source": "S1 可行性 · 已接受",
            })
            continue
        if c["severity"] == "blocker":
            a.blockers.append(_risk(
                f"G2-FEAS-{c['id']}",
                f"{c['problem']}：概念不能建立在明显装不下的前提上，"
                "先解决容量或面积口径",
                SOFT if c.get("needs_human") is False else HARD,
            ))
        else:
            a.condition_items.append({
                "id": f"G2-COND-{c['id']}",
                "text": f"{c['problem']}（{c['evidence']}）",
                "source": "S1 可行性",
            })

    a.pre_gate = bool(options.get("pre_gate"))
    if a.pre_gate:
        a.blockers.append(_risk(
            "G2-PRE-GATE",
            "本批概念是在 G1 确认前生成的探索稿：不能作为正式设计依据，"
            "须在 G1 通过后重跑 generate 再提交 G2",
        ))

    base = check_baseline(project)
    if base.get("requires_change_analysis"):
        a.blockers.append(_risk(
            "G2-BRIEF-CHANGED",
            f"任务书基准已变更（{base.get('change_kind')}）：概念须按新任务书重做后再提交 G2",
        ))

    # 专业范围：在范围内的专业没有方向，G2 不能算"概念已确认"
    from .. import disciplines as _disc

    chosen = next((c for c in (options.get("concepts") or [])
                   if c.get("concept_id") == a.selected), None)
    _scope = _disc.ensure(project)
    chosen_dirs = set(((chosen or {}).get("disciplines") or {}).keys())
    for did in _scope.active():
        if did not in chosen_dirs:
            a.blockers.append(_risk(
                f"G2-DISCIPLINE-{did}",
                f"{_disc.DISCIPLINES[did].label}在本次范围内，但选定的概念没有该专业方向："
                "多专业项目不能只确认其中一半",
            ))

    # 风格锁定冲突：同一修订下不得存在两个不同的锁定结果
    lock = state.get("style_lock") or {}
    if lock and chosen:
        locked = set(lock.get("style_ids") or [])
        want = set(chosen.get("style_ids") or [])
        if locked and locked != want:
            text = f"已锁定风格 {sorted(locked)} 与选定概念声明的 {sorted(want)} 不一致"
            a.style_conflict.append(text)
            a.blockers.append(_risk(
                "G2-STYLE-LOCK-CONFLICT",
                text + "：确认将以新概念重写锁定文件（原锁定留档），需显式接受",
                SOFT,
            ))

    for c in (options.get("concepts") or []):
        if c["concept_id"] == a.selected:
            if not c.get("s1_opportunity_refs"):
                a.condition_items.append({
                    "id": "G2-COND-NO-OPPORTUNITY",
                    "text": "该方向未直接回应对应机会条目，需在 G2 说明原因",
                })
            if (c.get("spatial_prototype") or {}).get("plan_strategy") == "":
                a.condition_items.append({
                    "id": "G2-COND-PROTOTYPE-UNSUPPORTED",
                    "text": "S3 现有平面算法不支持该原型，需与主创确认落地方式"
                            "（S3 无法据此签发正式 G3）",
                })
            if any("尺寸未核实" in t for t in (c.get("tradeoffs") or [])):
                a.condition_items.append({
                    "id": "G2-COND-DIMENSION-UNVERIFIED",
                    "text": "尺寸未核实：S3 可做空间验证，但不得据此出正式平面",
                })
            break

    risk_topics = {u.get("topic") for u in (project.meta.get("intake", {})
                                            .get("uncertainty") or []) if u.get("open")}
    if "structural" in risk_topics:
        a.human_items.append({
            "id": "G2-HUMAN-STRUCTURAL",
            "text": "结构条件未核实：概念可确认，结构拆改须持证专业人员复核后方可推进",
        })
    if "regulatory" in risk_topics:
        a.human_items.append({
            "id": "G2-HUMAN-REGULATORY",
            "text": "报批条件未确认：不得据此出具报审图",
        })
    return a


# --------------------------------------------------------------------------
def _payload(project: Project) -> Dict[str, Any]:
    """Exactly what G2 signs — nothing about presentation aesthetics."""
    state = _concept(project)
    options = state.get("options") or {}
    chosen = next((c for c in (options.get("concepts") or [])
                   if c["concept_id"] == state.get("selected")), None)
    return {
        "project_id": project.project_id,
        "revision": project.revision,
        "concept_id": state.get("selected") or "",
        "concept_name": (chosen or {}).get("concept_name", ""),
        "concept_statement": (chosen or {}).get("concept_statement", ""),
        "prototype": ((chosen or {}).get("spatial_prototype") or {}).get("prototype_id", ""),
        "spatial_strategy": ((chosen or {}).get("spatial_prototype") or {}).get("spatial_logic", ""),
        "style_ids": (chosen or {}).get("style_ids") or [],
        "materials": [m.get("name") for m in ((chosen or {}).get("material_direction") or [])],
        "palette": ((chosen or {}).get("palette") or {}).get("dominant") or [],
        "opportunities": (chosen or {}).get("s1_opportunity_refs") or [],
    }


def concept_digest(project: Project) -> str:
    blob = json.dumps(_payload(project), ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


# --------------------------------------------------------------------------
# 风格锁定：G2 的一部分，不是 G2 之后的补办手续
# --------------------------------------------------------------------------
class StyleLockConflict(RuntimeError):
    """同一修订下已存在另一个风格锁定，且本次没有显式接受覆盖。"""


def style_lock_path(out_dir: str | Path, revision: int) -> Path:
    return Path(out_dir) / f"style-lock-r{revision}.json"


def multi_baseline_path(out_dir: str | Path, revision: int) -> Path:
    return Path(out_dir) / f"multidisciplinary-concept-baseline-r{revision}.json"


def _write_design_intent(project: Project, out_dir: str | Path,
                         chosen: Dict[str, Any]) -> Dict[str, Any]:
    """G2 时把设计意图落盘。没有概念就没有意图，直接抛错由事务回滚。"""
    from .. import disciplines as _disc
    from .. import intent as _intent
    from .. import leadership as _lead

    scope = _disc.ensure(project)
    lead = _lead.ensure(project, scope)
    built = _intent.build(project, chosen, lead)
    if not built.get("signature_features"):
        raise ValueError(
            "选定概念没有可识别的核心设计特征（spatial_logic / zoning / "
            "circulation / daylight 都为空）：G2 不能签一份没有设计意图的基准")
    _intent.write(project, out_dir, built)
    return built


def write_multidisciplinary_baseline(project: Project, out_dir: str | Path, *,
                                     chosen: Dict[str, Any], by: str = "",
                                     acknowledged: Sequence[str] = ()) -> Dict[str, Any]:
    """锁定"这次确认的到底是哪些专业、各自的什么方向"。

    风格锁定文件只管观感，管不了"结构按什么原则、景观做到什么范围"。多专业项目
    如果只有风格锁，就会出现"建筑方向已确认、景观概念却对应另一方案"这种状态。
    所以这里单独落一份基准，逐专业写：方向、状态、还缺什么、谁签。

    范围外的专业写 `not_applicable`，不伪造批准。
    """
    from .. import disciplines as _disc
    from .. import leadership as _lead

    scope = _disc.ensure(project)
    lead = _lead.ensure(project, scope)
    dirs = chosen.get("disciplines") or {}
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    rows: List[Dict[str, Any]] = []
    not_applicable: List[str] = []
    pending: List[Dict[str, Any]] = []
    for did in _disc.DISCIPLINE_ORDER:
        d = _disc.DISCIPLINES[did]
        if did not in scope.active():
            not_applicable.append(did)
            rows.append({
                "discipline": did, "label": d.label, "state": "not_applicable",
                "direction": "", "status": "",
                "note": "不在本次委托范围：不视为已批准，也不代表没有接口",
            })
            continue
        item = dirs.get(did)
        if not item:
            raise ValueError(f"{d.label}在范围内，但选定概念没有该专业方向：G2 不能只签一半")
        rows.append({
            "discipline": did, "label": d.label, "state": "locked",
            "direction": item.get("strategy", ""),
            "goal": item.get("goal", ""),
            "status": item.get("status", ""),
            "deliverables": list(item.get("deliverables") or []),
            "open_questions": list(item.get("open_questions") or []),
            "interfaces": list(item.get("interfaces") or []),
            "needs_professional": bool(item.get("needs_professional")),
            "signed_by": (f"{d.label}专业人员" if item.get("needs_professional")
                          else by or "主创"),
            "evidence": item.get("evidence", ""),
        })
        if item.get("status") != "proposed":
            pending.append({"discipline": did, "label": d.label,
                            "needs": list(item.get("open_questions") or [])})

    iface = _disc.interfaces_for(scope)
    payload = {
        "project_id": project.project_id,
        "revision": project.revision,
        "concept_id": chosen.get("concept_id", ""),
        "concept_name": chosen.get("concept_name", ""),
        "concept_statement": chosen.get("concept_statement", ""),
        "confirmed_by": by or "业主",
        "confirmed_at": _now(),
        "source": "owner",
        "active": [r["discipline"] for r in rows if r["state"] == "locked"],
        "not_applicable": not_applicable,
        "leadership": lead.to_dict(),
        "disciplines": rows,
        "interfaces": iface,
        "pending_inputs": pending,
        "acknowledged": list(acknowledged),
        "note": ("每个专业方向都绑定同一个 concept_id：不是五份互不相关的方案。"
                 "not_applicable 表示不在本次委托范围，不等于已核对无冲突。"),
    }
    path = multi_baseline_path(out, project.revision)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")
    payload["file"] = str(path)
    return payload


def write_style_lock(project: Project, out_dir: str | Path, *,
                     acknowledged: Sequence[str] = (), by: str = "") -> Dict[str, Any]:
    """Write the canonical lock for the selected concept, or raise.

    Called **before** the stage is confirmed, so "confirmed but no lock file"
    cannot happen: if this raises, nothing was signed.
    """
    from ..style.hooks import lock_style
    from ..style.recommender import RecommendRequest

    state = _concept(project)
    options = state.get("options") or {}
    selected = str(state.get("selected") or "")
    chosen = next((c for c in (options.get("concepts") or [])
                   if c["concept_id"] == selected), None)
    if chosen is None:
        raise ValueError("尚未选定概念，不能锁定风格")
    want = list(chosen.get("style_ids") or [])
    if not want:
        raise ValueError(f"概念 {selected} 未声明风格，无法写入锁定文件")

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = style_lock_path(out, project.revision)

    previous: Optional[Dict[str, Any]] = None
    if path.exists():
        try:
            previous = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            previous = None
    if previous:
        prev_ids = [str(previous.get("locked_style") or "")]
        prev_ids += [str(s) for s in (previous.get("style_bundle") or [])]
        prev_ids = [s for s in prev_ids if s]
        if prev_ids and set(prev_ids) != set(want) \
                and "G2-STYLE-LOCK-CONFLICT" not in set(acknowledged):
            raise StyleLockConflict(
                f"r{project.revision} 已锁定 {sorted(prev_ids)}，本次要写 {sorted(want)}："
                "须显式接受覆盖（--acknowledge G2-STYLE-LOCK-CONFLICT）或先解除锁定")

    request = RecommendRequest(
        space_type=str(options.get("style_request", {}).get("space_type") or ""),
        preferences=want,
        stage="S2",
    )
    payload = lock_style(want[0], request, out_dir=out, revision=project.revision,
                         by=by or "业主")
    if not path.exists():
        raise RuntimeError(f"风格锁定文件未写出：{path}")

    state["style_lock"] = {
        "style_ids": want,
        "primary": want[0],
        "labels": list(chosen.get("style_labels") or []),
        "revision": project.revision,
        "file": str(path),
        "concept_id": selected,
        "alternatives": payload.get("options_considered") or [],
        "at": _now(),
    }
    if previous:
        prev_ids = [str(previous.get("locked_style") or "")]
        prev_ids += [str(s) for s in (previous.get("style_bundle") or [])]
        prev_ids = [s for s in dict.fromkeys(prev_ids) if s]
        # 同一修订、同一风格重复确认：不写第二条历史，避免"两个版本"的错觉
        if set(prev_ids) != set(want):
            state.setdefault("style_lock_history", []).append({
                "revision": project.revision,
                "superseded": prev_ids,
                "replaced_by": want,
                "at": _now(),
                "file": str(path),
            })
    return state["style_lock"]


def _snapshot(project: Project, state: Dict[str, Any]) -> Dict[str, Any]:
    store = project.meta.get("stage_state") or {}
    return {"concept": dict(state), "stage": dict(store.get("S2") or {})}


def _restore(project: Project, state: Dict[str, Any], snap: Dict[str, Any]) -> None:
    """Put the project exactly back where it was before the attempt."""
    state.clear()
    state.update(snap["concept"])
    store = project.meta.get("stage_state")
    if not isinstance(store, dict):
        store = {}
        project.meta["stage_state"] = store
    if snap.get("stage"):
        store["S2"] = snap["stage"]
    else:
        store.pop("S2", None)


def _file_snapshot(out_dir: Optional[Path], revision: int) -> List[Dict[str, Any]]:
    """Remember the bytes of every file the transaction is about to touch.

    只回滚内存状态是不够的：锁定文件写出来、交接文件重建了，而阶段状态又退回
    未确认，磁盘上就会留下"已签"的痕迹。所以事务前先存内容，失败时按内容复原。
    """
    if out_dir is None:
        return []
    targets = [style_lock_path(out_dir, revision),
               Path(out_dir) / "concept-handoff.json"]
    snap: List[Dict[str, Any]] = []
    for p in targets:
        if p.exists():
            try:
                snap.append({"path": p, "existed": True, "bytes": p.read_bytes()})
            except OSError:
                snap.append({"path": p, "existed": False, "bytes": b""})
        else:
            snap.append({"path": p, "existed": False, "bytes": b""})
    return snap


def _file_restore(snap: Sequence[Dict[str, Any]]) -> List[str]:
    """Undo file writes: restore old bytes, delete files that did not exist."""
    restored: List[str] = []
    for item in snap:
        p = Path(item["path"])
        try:
            if item["existed"]:
                if not p.exists() or p.read_bytes() != item["bytes"]:
                    p.write_bytes(item["bytes"])
                    restored.append(p.name)
            elif p.exists():
                p.unlink()
                restored.append(f"{p.name}（已移除）")
        except OSError:
            continue
    return restored


def select(project: Project, concept_id: str) -> Dict[str, Any]:
    """Choose a concept — but do not lock it yet. Locking happens at G2."""
    state = _concept(project)
    options = state.get("options") or {}
    if not options.get("concepts"):
        raise ValueError("尚未生成概念方案")
    if not any(c["concept_id"] == concept_id for c in options["concepts"]):
        raise ValueError(f"未知概念 {concept_id}；可选："
                         + "、".join(c["concept_id"] for c in options["concepts"]))
    previous = str(state.get("selected") or "")
    state["selected"] = concept_id
    state["selected_at"] = _now()
    from .handoff import refresh as _refresh_handoff

    _refresh_handoff(project)

    changed_after_gate = bool(state.get("baseline")) and previous and previous != concept_id
    result: Dict[str, Any] = {"selected": concept_id, "previous": previous,
                              "requires_change_analysis": changed_after_gate,
                              "reopened_stages": []}
    if changed_after_gate:
        # Same rule as S1: a real change after signature reopens, not just reports.
        from ..revisions import record_change

        reopened = invalidate_from(project, "S2")
        record_change(project, "concept",
                      f"G2 之后更换概念：{previous} → {concept_id}",
                      targets=["S2"], invalidated=reopened)
        result["reopened_stages"] = reopened
        result["note"] = ("概念基准已建立后更换方向：S2 与下游已置为返工，"
                          "原基准保留在记录中，须重新提交 G2")
    return result


@dataclass
class Outcome:
    decision: str
    stage_status: str
    source: str
    notes: List[str] = field(default_factory=list)
    baseline: Dict[str, Any] = field(default_factory=dict)
    forced: bool = False
    assessment: Dict[str, Any] = field(default_factory=dict)
    formal: bool = False
    rolled_back: bool = False
    acknowledged: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision": self.decision,
            "decision_label": DECISION_LABEL.get(self.decision, self.decision),
            "stage_status": self.stage_status,
            "source": self.source,
            "source_label": SOURCE_LABEL.get(self.source, self.source),
            "notes": list(self.notes),
            "baseline": dict(self.baseline),
            "forced": self.forced,
            "formal": self.formal,
            "rolled_back": self.rolled_back,
            "acknowledged": list(self.acknowledged),
            "assessment": dict(self.assessment),
        }


def decide_gate(project: Project, decision: str, by: str = "", note: str = "",
                source: str = "owner", acknowledge: Sequence[str] = (),
                force: bool = False, summary_path: str = "") -> Outcome:
    """Apply one G2 decision. Single entry point for every caller.

    `force` 保留在签名里只是为了报错说得清楚：它**不能**绕过硬性条件，
    也不替代逐项书面接受。真正的通过只有一条路径——有概念、有选定的
    concept_id、任务书基准有效，并且风格锁定文件真的写出来了。
    """
    if decision not in DECISIONS:
        raise ValueError(f"unknown decision '{decision}'（应为 {'/'.join(DECISIONS)}）")
    if source not in SOURCES:
        raise ValueError(f"unknown source '{source}'（应为 {'/'.join(SOURCES)}）")

    ack = sorted({str(x).strip() for x in acknowledge if str(x).strip()})
    unknown = [x for x in ack if x not in ACKNOWLEDGEABLE]
    if unknown:
        raise ValueError(
            f"未知风险编号 {unknown}：acknowledge 只能引用明确编号，"
            f"不能写一段文字片段。可用编号：{list(ACKNOWLEDGEABLE)}")

    state = _concept(project)
    _opts = state.get("options") or {}
    chosen = next((c for c in (_opts.get("concepts") or [])
                   if c.get("concept_id") == str(state.get("selected") or "")), None)
    assess = assess_gate(project)
    out_dir = Path(summary_path).parent if summary_path else None
    notes: List[str] = []
    forced_flag = False
    rolled_back = False

    if decision == "approved":
        hard = assess.hard_blockers
        soft_open = [b for b in assess.soft_blockers if b["id"] not in ack]
        if hard or soft_open:
            if source == "owner":
                decision = "blocked"
                notes.append("不能通过 G2：")
                notes += [f"  [{b['id']}] {b['text']}" for b in hard + soft_open]
                if hard:
                    notes.append("以上为硬性条件（还没有可签的东西）—— --force 不能绕过。")
                if soft_open:
                    notes.append("可用 --acknowledge "
                                 + "、".join(b["id"] for b in soft_open)
                                 + " 逐项书面接受后重试。")
            else:
                notes.append(
                    "演示模式：前置条件未满足（"
                    + "、".join(f"[{b['id']}]" for b in hard + soft_open)
                    + "）：本次只让流程继续，不构成业主签署，也不形成概念基准")
        if force and (hard or soft_open):
            notes.append("--force 已忽略：G2 不提供强制通过。")

    st = get_state(project, "S2")
    baseline: Dict[str, Any] = {}
    formal = False

    if decision == "approved":
        by_label = by or ("业主/主创" if source == "owner" else "演示流程")
        payload = _payload(project)
        snapshot = _snapshot(project, state)
        files = _file_snapshot(out_dir, project.revision)
        try:
            # 1) 先写风格锁定：写不出来就什么都不签
            if source == "owner":
                write_style_lock(project, out_dir or Path("."),
                                 acknowledged=ack, by=by_label)
                # 1b) 多专业基准：逐专业锁定方向，范围外的记 not_applicable。
                #     不能只锁风格——风格管不了结构与景观的边界。
                multi = write_multidisciplinary_baseline(
                    project, out_dir or Path("."), chosen=chosen or {},
                    by=by_label, acknowledged=ack)
                # 1c) 设计意图：把"最不能动的几样"落成可核对清单。
                #     没有这份清单，技术协调就只能靠"记得别改"，那等于没保护。
                intent = _write_design_intent(project, out_dir or Path("."),
                                              chosen or {})
            else:
                multi = {}
                intent = {}
            # 2) 再确认阶段
            st = confirm_stage(project, "S2", by=by_label,
                               note=note or ("G2 概念确认" if source == "owner"
                                             else "G2 演示确认（--assume-approval）"))
            entry = {
                **payload,
                "digest": concept_digest(project),
                "confirmed_at": st.confirmed_at,
                "confirmed_by": st.confirmed_by,
                "source": source,
                "forced": False,
                "formal": source == "owner",
                "acknowledged": ack,
                "conditions": list(assess.conditions),
                "condition_ids": [c["id"] for c in assess.condition_items],
                "needs_human": list(assess.needs_human),
                "human_ids": [h["id"] for h in assess.human_items],
                "summary_path": summary_path,
                "multidisciplinary": {
                    "file": multi.get("file", ""),
                    "active": list(multi.get("active") or []),
                    "not_applicable": list(multi.get("not_applicable") or []),
                    "pending_inputs": list(multi.get("pending_inputs") or []),
                } if multi else {},
                # 主导专业与协作原则：决定后续 S3–S8 谁对齐谁
                "leadership": (multi.get("leadership") or {}),
                "design_intent": {
                    "design_intent_id": intent.get("design_intent_id", ""),
                    "lead_discipline": intent.get("lead_discipline", ""),
                    "features": [f["id"] for f in (intent.get("signature_features") or [])],
                } if intent else {},
            }
            # 3) 登记基准 / 演示记录
            if source == "owner":
                state["baseline"] = entry
                state["demo_approval"] = None
            else:
                state["demo_approval"] = entry
            # 4) 交接状态必须同步，否则 S3 会读到旧快照
            from .handoff import refresh as _refresh

            _refresh(project, out_dir)
            # 5) 自检：确认了就必须有锁定文件
            if source == "owner":
                lock_file = Path(str((state.get("style_lock") or {}).get("file") or ""))
                if not lock_file.is_file():
                    raise RuntimeError(f"风格锁定文件不存在：{lock_file}")
                if str((state.get("baseline") or {}).get("concept_id")) != str(
                        state.get("selected") or ""):
                    raise RuntimeError("基准登记的概念与当前选定不一致")
                multi_file = Path(str(((state.get("baseline") or {})
                                       .get("multidisciplinary") or {}).get("file") or ""))
                if multi_file and not multi_file.is_file():
                    raise RuntimeError(f"多专业基准文件不存在：{multi_file}")
                intent_file = Path(str((((project.meta or {}).get("design_intent")
                                        or {}).get("file")) or ""))
                if not intent_file.is_file():
                    raise RuntimeError(f"设计意图基准文件不存在：{intent_file or '（未写入）'}")
        except Exception as exc:
            _restore(project, state, snapshot)
            restored = _file_restore(files)
            # 设计意图是本事务内新建的，快照里没有它，回滚要单独清掉，
            # 否则会留下一份"没有门禁背书的意图基准"。
            stray = (project.meta or {}).pop("design_intent", None)
            try:
                if isinstance(stray, dict) and stray.get("file"):
                    Path(str(stray["file"])).unlink(missing_ok=True)
            except OSError:
                pass
            decision = "blocked"
            rolled_back = True
            st = get_state(project, "S2")
            notes.append(
                f"关键步骤失败，已回滚，本次不形成概念基准：{type(exc).__name__}: {exc}")
            if restored:
                notes.append("已复原磁盘文件：" + "、".join(restored))
        else:
            formal = source == "owner"
            baseline = entry
            if source == "owner":
                notes.append(f"已形成概念基准：{entry['concept_id']} / r{project.revision} / "
                             f"{entry['digest']}")
                lock = state.get("style_lock") or {}
                notes.append(f"风格已锁定：{' + '.join(lock.get('labels') or [])}"
                             f"（{Path(str(lock.get('file'))).name}）")
            else:
                notes.append("演示模式：未写入概念基准，S3 不得引用本次确认作为设计依据")
            if ack:
                notes.append("已书面接受：" + "、".join(ack))
    elif decision == "revision_requested":
        st = reject_stage(project, "S2", reason=note or "业主对方案提出修改")
        baseline = state.get("baseline") or {}
        notes.append("已退回修改；概念基准未变更，S2 需重新提交 G2")
    else:
        st = block_stage(project, "S2", note or "存在前置条件未解决")
        baseline = state.get("baseline") or {}
        notes.append("已阻断：解决前置条件后重新提交 G2")

    for c in assess.conditions[:2]:
        notes.append(f"附条件推进：{c}")
    for h in assess.needs_human[:2]:
        notes.append(f"须专业复核：{h}")
    state["last_decision"] = {
        "decision": decision, "source": source, "by": by, "note": note,
        "at": _now(), "revision": project.revision, "summary_path": summary_path,
        "formal": formal, "acknowledged": ack, "rolled_back": rolled_back,
    }
    return Outcome(decision=decision, stage_status=st.status, source=source,
                   notes=notes, baseline=baseline, forced=forced_flag,
                   assessment=assess.to_dict(), formal=formal,
                   rolled_back=rolled_back, acknowledged=ack)


def check_baseline(project: Project) -> Dict[str, Any]:
    """Has the signed concept changed since G2?"""
    state = _concept(project)
    base = state.get("baseline") or {}
    demo = state.get("demo_approval") or {}
    if not base:
        return {"has_baseline": False, "changed": False, "demo_only": bool(demo),
                "reason": "仅有演示确认，未形成可引用概念基准" if demo else "尚未通过 G2"}
    current = concept_digest(project)
    changed = current != base.get("digest")
    return {
        "has_baseline": True,
        "changed": changed,
        "demo_only": False,
        "baseline_digest": base.get("digest"),
        "current_digest": current,
        "concept_id": base.get("concept_id"),
        "style_ids": list(base.get("style_ids") or []),
        "baseline_revision": base.get("revision"),
        "current_revision": project.revision,
        "confirmed_at": base.get("confirmed_at"),
        "confirmed_by": base.get("confirmed_by"),
        "requires_change_analysis": changed,
        "reason": ("概念/风格/材料已变更，须重做 S2 与下游" if changed
                   else "与已确认概念基准一致"),
    }


def approval_summary(project: Project, extra: str = "") -> str:
    """What the client actually signs — human-readable, no scores."""
    state = _concept(project)
    options = state.get("options") or {}
    chosen = next((c for c in (options.get("concepts") or [])
                   if c["concept_id"] == state.get("selected")), {})
    assess = assess_gate(project)
    p = chosen.get("spatial_prototype") or {}
    lines = [
        "# G2 概念确认摘要",
        "",
        f"项目：{project.name or project.project_id}（{project.project_id}）　"
        f"模型修订 r{project.revision}",
        "",
        "## 一、要确认的是这一套",
        "",
        f"- 概念编号：**{chosen.get('concept_id', '未选定')}**",
        f"- 概念名称：{chosen.get('concept_name', '—')}",
        f"- 设计主张：{chosen.get('concept_statement', '—')}",
        f"- 空间原型：{p.get('name', '—')}（{p.get('family_zh', '—')}）",
        "",
        "## 二、空间策略",
        "",
        p.get("spatial_logic", "—"),
        "",
        f"- 动线：{p.get('circulation', '—')}",
        f"- 分区：{p.get('zoning', '—')}",
        f"- 采光：{p.get('daylight', '—')}",
        "",
        "## 三、视觉语言",
        "",
        f"- 风格：{' + '.join(chosen.get('style_labels') or []) or '—'}",
        f"- 风格依据：{chosen.get('style_basis', '—')}",
        f"- 配色关系：{(chosen.get('aesthetic_policy') or {}).get('ratio_rule', '—')}",
        "",
        "| 材料 | 用在 | 做法 |",
        "|---|---|---|",
    ]
    for m in (chosen.get("material_direction") or []):
        lines.append(f"| {m.get('name', '')} | {m.get('application', '')} | {m.get('finish', '')} |")
    lines += ["", "**光**："]
    lines += [f"- {x}" for x in (chosen.get("lighting_direction") or [])] or ["- —"]

    lines += ["", "## 四、允许 S3 深化的条件", ""]
    lines += [f"- {c}" for c in assess.conditions] or ["- 无附加条件"]
    lines += ["", "## 五、需专业复核的事项", ""]
    lines += [f"- {h}" for h in assess.needs_human] or ["- 无"]
    lines += ["", "## 六、仍未解决的风险", ""]
    risks = (chosen.get("technical_risks") or [])[:4]
    lines += [f"- {r}" for r in risks] or ["- 无已知技术风险记录"]

    gaps = [r for r in assess.blocked_reasons]
    lines += ["", "## 七、还没解决的问题", ""]
    lines += [f"- {g}" for g in gaps] or ["- 无阻断项；其余待核实事项见 S1 不确定清单"]

    if extra:
        lines += ["", "## 补充说明", "", extra]
    lines += ["", "---", "",
              "> 确认后本套即成为 S3 的设计依据。之后修改概念、风格或需求，"
              "系统会重新计算受影响的成果并要求重新确认，原确认版保留在修订记录中。"]
    return "\n".join(lines)


__all__ = ["DECISIONS", "SOURCES", "ACKNOWLEDGEABLE", "GateAssessment", "Outcome",
           "assess_gate", "decide_gate", "select", "concept_digest", "check_baseline",
           "approval_summary", "write_style_lock", "style_lock_path",
           "StyleLockConflict"]
