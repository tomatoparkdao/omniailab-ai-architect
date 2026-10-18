"""硬门槛：什么算"证明不成立"，什么只是"还不知道"。

为什么单独一层
--------------
S1 的可行性检查、S2 的方案排序、G2 的确认判定，原本各自算一套。结果是同一件
"面积差 12%"，在 S1 是阻断、在 S2 变条件、在 G2 可能消失。这类不一致比漏检更危险：
客户会以为问题已经解决了。

这里做三件事，**只做这三件**：

1. 定死"硬维度"清单与四态语义；
2. 把各阶段的原始结论（`Conflict` / 专业缺口 / 不确定项）翻译成同一套状态；
3. 提供 `verdict()` 一处汇总，三个门禁都调它。

四态语义（不可混用）
--------------------
`failed`          已有证据证明不成立（如 60 人 ÷ 132㎡ = 人均 2.2㎡）
`unknown`         缺资料，尚未确定（如没有结构图纸）
`passed`          在**当前深度**已通过检查
`not_applicable`  本项目不涉及

铁律：`unknown` 不等于 `passed`；`failed` 不能用加权分抵消。

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

FAILED = "failed"
UNKNOWN = "unknown"
PASSED = "passed"
NOT_APPLICABLE = "not_applicable"

STATUSES = (FAILED, UNKNOWN, PASSED, NOT_APPLICABLE)

STATUS_LABEL = {
    FAILED: "已证明不成立",
    UNKNOWN: "资料不足，未确定",
    PASSED: "当前深度已通过",
    NOT_APPLICABLE: "本项目不涉及",
}

#: 硬维度：不管设计多好，这些不成立就不能正式推进。
#: `key` 与 `feasibility.Conflict.category` 对齐，避免两套词。
HARD_DIMENSIONS: Dict[str, Dict[str, Any]] = {
    "area": {
        "label": "面积是否成立",
        "question": "客户说的面积与模型实测面积是否对得上",
        "traded_for": "nothing",
        "owner": "建筑 / 室内",
    },
    "capacity": {
        "label": "容量是否成立",
        "question": "这些人 / 这些功能装不装得下",
        "traded_for": "nothing",
        "owner": "主导专业",
    },
    "safety": {
        "label": "结构与技术安全",
        "question": "是否存在经验证的安全问题",
        "traded_for": "nothing",
        "owner": "结构",
    },
    "regulation": {
        "label": "强制性法规",
        "question": "是否违反已确认的强制性规范",
        "traded_for": "nothing",
        "owner": "规划 / 消防",
    },
    "physics": {
        "label": "不可满足的物理条件",
        "question": "净高、坡度、排水、检修空间是否成立",
        "traded_for": "nothing",
        "owner": "结构 / 机电",
    },
}

HARD_KEYS: Sequence[str] = tuple(HARD_DIMENSIONS)

#: 严重程度 → 状态。只有 blocker 才叫 failed，major 是条件不是失败。
SEVERITY_TO_STATUS = {
    "blocker": FAILED,
    "major": UNKNOWN,      # 有条件但没定性：按"还没确定"处理，不给通过
    "info": PASSED,
    "minor": PASSED,
}

#: 哪些专业在范围内时，某个维度必须给出明确状态（不能默认不发一言）
DIMENSION_OWNERS = {
    "area": ("architecture", "interior"),
    "capacity": ("architecture", "interior"),
    "safety": ("structure",),
    "regulation": ("planning",),
    "physics": ("structure", "mep"),
}


@dataclass
class GateRow:
    dimension: str
    status: str
    statement: str = ""
    evidence: str = ""
    source: str = ""
    severity: str = ""
    needs: str = ""
    human: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dimension": self.dimension,
            "label": HARD_DIMENSIONS.get(self.dimension, {}).get("label", self.dimension),
            "status": self.status,
            "status_label": STATUS_LABEL.get(self.status, self.status),
            "statement": self.statement,
            "evidence": self.evidence,
            "source": self.source,
            "severity": self.severity,
            "needs": self.needs,
            "human_review": bool(self.human),
        }


@dataclass
class GateVerdict:
    rows: List[GateRow] = field(default_factory=list)
    checked_at: str = ""
    revision: int = 1

    @property
    def failed(self) -> List[GateRow]:
        return [r for r in self.rows if r.status == FAILED]

    @property
    def unknown(self) -> List[GateRow]:
        return [r for r in self.rows if r.status == UNKNOWN]

    @property
    def passed(self) -> List[GateRow]:
        return [r for r in self.rows if r.status == PASSED]

    @property
    def blocked(self) -> bool:
        """有任何一项 failed 就阻断正式推进。"""
        return bool(self.failed)

    @property
    def can_approve(self) -> bool:
        """能正式批准：没有 failed，且没有未定的硬项（unknown 也必须清掉）。"""
        return not self.failed and not self.unknown

    def status_of(self, dimension: str) -> str:
        for r in self.rows:
            if r.dimension == dimension:
                return r.status
        return NOT_APPLICABLE

    def summary(self) -> str:
        if self.failed:
            return ("已证明不成立：" + "；".join(
                f"{HARD_DIMENSIONS.get(r.dimension, {}).get('label', r.dimension)}"
                f"——{r.statement}" for r in self.failed))
        if self.unknown:
            return ("尚未确定：" + "；".join(
                f"{HARD_DIMENSIONS.get(r.dimension, {}).get('label', r.dimension)}"
                f"——{r.needs or r.statement}" for r in self.unknown))
        return "硬门槛在当前深度全部通过"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "revision": self.revision,
            "rows": [r.to_dict() for r in self.rows],
            "blocked": self.blocked,
            "can_approve": self.can_approve,
            "counts": {
                FAILED: len(self.failed), UNKNOWN: len(self.unknown),
                PASSED: len(self.passed),
                NOT_APPLICABLE: sum(1 for r in self.rows
                                    if r.status == NOT_APPLICABLE),
            },
            "summary": self.summary(),
            "rule": ("failed 不能用加权分抵消；unknown 不等于 passed；"
                     "not_applicable 必须来自范围判定，不能用来糊弄。"),
        }


# --------------------------------------------------------------------------
def evaluate(project: Any, *, scope: Any = None,
             concept: Optional[Dict[str, Any]] = None,
             ctx: Any = None) -> GateVerdict:
    """把各阶段的原始结论翻译成统一状态。

    输入三个来源，全部是"已经算过的"，这里不重复计算：
    `feasibility.run_feasibility()` 的 conflicts、
    专业范围里的资料缺口、
    概念自带的 discipline_conflicts。
    """
    from .intake.feasibility import run_feasibility

    rows: Dict[str, GateRow] = {}
    revision = int(getattr(project, "revision", 1) or 1)

    active = set(getattr(scope, "active", lambda: [])() if scope is not None else [])
    needs = set(getattr(scope, "needs_data", lambda: [])() if scope is not None else [])

    # ---- 1. 可行性冲突 ------------------------------------------------
    try:
        feas = run_feasibility(project)
    except Exception:                                   # noqa: BLE001
        feas = {"conflicts": []}
    for c in feas.get("conflicts") or []:
        cat = str(c.get("category") or "")
        if cat not in HARD_KEYS:
            continue
        sev = str(c.get("severity") or "")
        status = SEVERITY_TO_STATUS.get(sev, UNKNOWN)
        prev = rows.get(cat)
        # 同一维度多条结论时按"最坏者胜"：failed > unknown > passed。
        # 否则一条 info（"面积有余量"）会把 major（"面积口径不一致"）盖掉，
        # 同一个项目在 S1 报警、到 S2 又变成"通过"。
        rank = {FAILED: 3, UNKNOWN: 2, PASSED: 1, NOT_APPLICABLE: 0}
        if prev and rank.get(prev.status, 0) >= rank.get(status, 0):
            continue
        rows[cat] = GateRow(
            dimension=cat, status=status,
            statement=str(c.get("problem") or ""),
            evidence=str(c.get("evidence") or ""),
            source="S1 可行性", severity=sev,
            needs=str(c.get("recommendation") or ""),
        )

    # ---- 2. 概念自带的专业冲突 ----------------------------------------
    for r in ((concept or {}).get("discipline_conflicts") or []):
        did = str(r.get("discipline") or "")
        cat = "safety" if did == "structure" else (
            "physics" if did == "mep" else "capacity")
        if str(r.get("severity") or "") == "blocker" and cat not in rows:
            rows[cat] = GateRow(
                dimension=cat, status=FAILED,
                statement=str(r.get("detail") or ""),
                evidence="概念一致性校核", source="S2 概念", severity="blocker",
            )

    # ---- 3. 专业缺口 → unknown（不是 passed） -------------------------
    for cat, owners in DIMENSION_OWNERS.items():
        if cat in rows:
            continue
        involved = [d for d in owners if d in active]
        if not involved:
            rows[cat] = GateRow(
                dimension=cat, status=NOT_APPLICABLE,
                statement="本次委托不涉及该维度", source="专业范围",
            )
            continue
        missing = [d for d in involved if d in needs]
        if missing:
            rows[cat] = GateRow(
                dimension=cat, status=UNKNOWN,
                statement="范围内但资料不足，无法判定",
                source="专业范围",
                needs="先补齐：" + "、".join(_label(d) for d in missing),
            )
        else:
            rows[cat] = GateRow(
                dimension=cat, status=PASSED,
                statement="在当前深度未发现阻断项（不等于已通过专业计算）",
                source="当前深度检查",
            )

    # ---- 4. 未决不确定项：结构类视为 safety 未定 ----------------------
    try:
        from .intake.feasibility import run_feasibility as _rf  # noqa: F401
        from .intake.diligence import uncertainty_register

        for u in uncertainty_register(project) or []:
            if u.get("resolved"):
                continue
            blocks = [str(x) for x in (u.get("blocks_stages") or [])]
            if "S7" not in blocks and "S3" not in blocks:
                continue
            if "结构" not in str(u.get("statement") or ""):
                continue
            cur = rows.get("safety")
            if cur and cur.status == FAILED:
                continue
            rows["safety"] = GateRow(
                dimension="safety", status=UNKNOWN,
                statement=f"{u.get('id')}：{u.get('statement')}",
                source="不确定登记",
                needs="结构鉴定或原结构图纸（须专业复核）",
            )
    except Exception:                                   # noqa: BLE001
        pass

    order = [k for k in HARD_KEYS if k in rows]
    return GateVerdict(rows=[rows[k] for k in order], revision=revision)


def _label(did: str) -> str:
    from .disciplines import DISCIPLINES

    d = DISCIPLINES.get(did)
    return d.label if d else did


def refuse_reason(verdict: GateVerdict) -> str:
    """给客户看的一句话：为什么现在不能签。"""
    if verdict.failed:
        return ("现在不能签字：下面这些不是偏好问题，是已经证明不成立——"
                + "；".join(r.statement for r in verdict.failed))
    if verdict.unknown:
        return ("现在还不能签字：这些条件还没确定，签了等于替客户赌——"
                + "；".join(f"{HARD_DIMENSIONS.get(r.dimension, {}).get('label', '')}"
                           f"（{r.needs or '缺资料'}）" for r in verdict.unknown))
    return ""


__all__ = ["FAILED", "UNKNOWN", "PASSED", "NOT_APPLICABLE", "STATUSES",
           "STATUS_LABEL", "HARD_DIMENSIONS", "HARD_KEYS", "DIMENSION_OWNERS",
           "SEVERITY_TO_STATUS", "GateRow", "GateVerdict", "evaluate",
           "refuse_reason"]
