"""Stage guard: what an unresolved condition actually prevents.

The previous round only knew "this stage is blocked". That is too coarse in
both directions: it lets a documented-but-unverified structure approval slip
through, and it would freeze an entire stage because one local dimension is
missing.

This module answers a narrower, more useful question per stage:

* **blocked** — the stage's core output would be invalid, so do not run it;
* **limited** — the stage may run, but specific work inside it is forbidden;
* **needs_human** — a responsible professional must sign before it counts.

Only conditions recorded in the intake uncertainty register are considered.
The model's own `uncertain` flags stay with the existing validation rules, so
old projects and the demo pipeline behave exactly as before.

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

from ..model import Project
from .diligence import precision_level, uncertainty_register

# effect, message. `block` means the stage cannot run; `limit` means it can run
# but this work item may not be produced; `warn` is a caution only.
_TOPIC_EFFECT: Dict[str, Dict[str, Tuple[str, str]]] = {
    "structural": {
        "S2": ("limit", "可以讨论不依赖拆改的概念方案，但不得把承接的拆改当作前提"),
        "S3": ("limit", "平面不得以拆除承重构件或新增结构洞口为前提"),
        "S4": ("limit", "不得出结构拆改、新增洞口与结构加固相关图纸"),
        "S5": ("limit", "模型不得删改承重构件，构件尺寸须标注待核验"),
        "S7": ("block", "施工图不得基于未证实的结构条件"),
    },
    "dimension": {
        "S2": ("warn", "概念方向可继续，但不得给出任何实际尺寸"),
        "S3": ("limit", "可做方案比较与示意，不得出「以真实尺寸成立」的正式平面"),
        "S4": ("limit", "不得出依赖精确尺寸的图纸与工程量"),
        "S5": ("limit", "模型与效果图须标注尺寸待核验，不得作为制作依据"),
        "S7": ("block", "未证实的尺寸不得用于施工图"),
        "S8": ("limit", "工程量不得作为结算、报价或采购依据"),
    },
    "regulatory": {
        "S3": ("warn", "不涉审批的平面研究可继续"),
        "S4": ("limit", "不得承诺满足尚未确认的法规条件"),
        "S7": ("block", "报批条件未确认，不得出报审图"),
    },
    "services": {
        "S4": ("limit", "不得承诺净高、点位与设备容量，须机电专业复核"),
        "S7": ("limit", "机电相关图纸须标注待复核，不得直接施工"),
    },
    "budget": {
        "S2": ("warn", "造价结论只能给区间并注明假设"),
        "S4": ("warn", "材料档次须标为待预算确认"),
    },
    "aesthetic": {
        "S2": ("warn", "风格在概念阶段收敛，不构成准入限制"),
    },
    "scope": {
        "S1": ("warn", "交付范围未定，交付清单须标注待确认"),
        "S8": ("warn", "交付清单须标注待确认"),
    },
}

STAGES_GUARDED = ("S2", "S3", "S4", "S5", "S7", "S8")


@dataclass
class GuardResult:
    stage: str
    allowed: bool = True
    blocked: bool = False
    restrictions: List[str] = field(default_factory=list)
    blocked_work: List[str] = field(default_factory=list)
    needs_human: List[str] = field(default_factory=list)
    reasons: List[str] = field(default_factory=list)
    triggered: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stage": self.stage,
            "allowed": self.allowed,
            "blocked": self.blocked,
            "restrictions": list(self.restrictions),
            "blocked_work": list(self.blocked_work),
            "needs_human": list(self.needs_human),
            "reasons": list(self.reasons),
            "triggered": list(self.triggered),
        }

    def summary(self) -> str:
        if self.blocked:
            return "；".join(self.reasons) or "阶段被阻断"
        if self.restrictions:
            return "；".join(self.restrictions)
        return ""


def _open_items(project: Project) -> List[Dict[str, Any]]:
    return [u for u in uncertainty_register(project) if u.get("open")]


def check_stage(project: Project, stage_id: str) -> GuardResult:
    """Evaluate one stage against the registered open conditions."""
    res = GuardResult(stage=stage_id)
    if stage_id not in STAGES_GUARDED:
        return res

    for item in _open_items(project):
        topic = str(item.get("topic") or "")
        rule = (_TOPIC_EFFECT.get(topic) or {}).get(stage_id)
        if not rule:
            continue
        effect, message = rule
        # A condition only bites the stage it was declared to affect — a local
        # gap must not stop unrelated work in the same stage.
        declared = item.get("blocks_stages") or []
        if stage_id not in declared and effect == "block":
            continue
        label = f"{item.get('id','')}（{item.get('state_label','')}）：{item.get('statement','')}"
        res.triggered.append(str(item.get("id") or ""))
        if effect == "block":
            res.blocked = True
            res.allowed = False
            res.reasons.append(f"{label} → {message}")
            res.blocked_work.append(message)
        elif effect == "limit":
            res.restrictions.append(f"{label} → {message}")
            res.blocked_work.append(message)
        else:
            res.restrictions.append(f"{label} → {message}")
        if item.get("needs_human"):
            res.needs_human.append(f"{item.get('id','')}：{item.get('action_needed','')}")

    # Precision is a separate, coarser gate: with no geometry at all, the
    # dimension-dependent stages produce nothing usable.
    level = precision_level(project)
    if level == "diagnostic" and stage_id in ("S4", "S5", "S7"):
        res.blocked = True
        res.allowed = False
        res.reasons.append(
            "资料仅支持诊断级：没有可用几何与尺寸依据，本阶段成果无法成立。"
            "请先补充图纸或实测数据"
        )
        res.blocked_work.append("依赖精确几何的全部成果")
    return res


def allowed_work(project: Project, stage_id: str) -> Dict[str, Any]:
    """Positive framing for reports: what *can* still be done in this stage."""
    res = check_stage(project, stage_id)
    return {
        "stage": stage_id,
        "allowed": res.allowed,
        "blocked": res.blocked,
        "may_do": [] if res.blocked else ["该阶段中不受下列限制的工作均可开展"],
        "may_not_do": res.blocked_work,
        "needs_human": res.needs_human,
        "reasons": res.reasons,
    }


def signature_blockers(project: Project) -> List[str]:
    """Conditions that no approval level may wave through.

    Structure, fire safety and statutory compliance are not commercial
    decisions; they cannot be forced by a client, a demo flag or a CLI switch.
    """
    out: List[str] = []
    for item in _open_items(project):
        if item.get("topic") in ("structural", "regulatory") and item.get("needs_human"):
            out.append(f"{item.get('id','')}：{item.get('statement','')}")
    return out
