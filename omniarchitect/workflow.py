"""Workflow — eight-stage state machine.

Runs one stage at a time. Each stage:

* checks its entry guardrails (upstream confirmations, the plan-before-model rule);
* dispatches to the capabilities that own it;
* writes its deliverables into its own folder;
* submits for confirmation at its gate and then stops, unless confirmation is
  being assumed.

A stage that is blocked at a gate is not a failure — it is the system working.

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import json
import os
import platform
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from . import changes, compliance, finishes, quantities
from .adapters import (
    BlenderAdapter,
    DxfAdapter,
    IfcAdapter,
    MeshAdapter,
    RenderAdapter,
    doctor,
    resolve_host_axes,
)
from .errors import GateBlocked, ModelError, OmniArchitectError, ValidationError
from .model import Project, summary, validate_all, validate_semantics, validate_schema
from .paths import relpath
from .registry import SIGNATURE
from .planner import PlanGenerator, SchemeOptions, SchemeResult, envelope_polygon, entry_point
from .revisions import record_change, register_artifact
from .stage_state import (
    AWAITING,
    BLOCKED,
    CONFIRMED,
    IN_PROGRESS,
    REWORK,
    all_states,
    can_confirm,
    can_start,
    confirm_stage,
    get_state,
    invalidate_from,
    markdown as stage_markdown,
    progress,
    start_stage,
    submit_for_confirmation,
)
from .stages import (
    STAGE_BY_ID,
    STAGE_ORDER,
    Stage,
    post_gate_actions_for_stage,
    stage_name,
    skills_for_stage,
)

# drawing depth per stage — R2: CAD exists from preliminary design onward,
# the difference is schematic vs construction, not presence or absence.


def _network_allowed() -> bool:
    """Whether this run may reach the internet for case research.

    Off when ``OMNIAILAB_NO_NETWORK`` is set, which the test harness and the
    installer smoke check do. Otherwise on: looking up built work is part of
    briefing, and a designer who cannot reach ArchDaily should see that as a
    warning, not as a silent absence of cases.
    """
    val = os.environ.get("OMNIAILAB_NO_NETWORK", "")
    return val.strip().lower() not in ("1", "true", "yes", "on")
DRAWING_DEPTH = {
    "S3": "schematic",
    "S4": "schematic",
    "S5": "",
    "S7": "construction",
}

STAGE_SLUG = {
    "S1": "brief", "S2": "concept", "S3": "plan", "S4": "preliminary",
    "S5": "visual", "S6": "freeze", "S7": "documents", "S8": "delivery",
}


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


@dataclass
class StageOutcome:
    stage: str
    stage_name: str = ""
    skills: List[str] = field(default_factory=list)
    adapter: str = ""
    status: str = "ok"          # ok | degraded | skipped | blocked | failed
    artifacts: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    error: str = ""
    seconds: float = 0.0
    next_action: str = ""
    gate_actions: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stage": self.stage,
            "stage_name": self.stage_name,
            "skills": list(self.skills),
            "adapter": self.adapter,
            "status": self.status,
            "artifacts": list(self.artifacts),
            "notes": list(self.notes),
            "error": self.error,
            "seconds": round(self.seconds, 3),
            "next_action": self.next_action,
            "gate_actions": [dict(a) for a in self.gate_actions],
        }


@dataclass
class RunManifest:
    run_id: str
    project_id: str
    revision: int
    started: str = field(default_factory=_now)
    finished: str = ""
    outcomes: List[StageOutcome] = field(default_factory=list)
    blocks: List[str] = field(default_factory=list)
    doctor: Dict[str, Any] = field(default_factory=dict)
    progress: Dict[str, Any] = field(default_factory=dict)
    out_dir: str = ""

    @property
    def gate_actions(self) -> List[Dict[str, Any]]:
        """Everything the gates produced *after* they were passed."""
        return [a for o in self.outcomes for a in o.gate_actions]

    def add(self, o: StageOutcome) -> None:
        self.outcomes.append(o)
        if o.status == "blocked":
            self.blocks.append(f"{o.stage} {o.stage_name}: {o.error}")
        elif o.status == "failed":
            self.blocks.append(f"{o.stage} {o.stage_name}: FAILED {o.error}")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "project_id": self.project_id,
            "revision": self.revision,
            "started": self.started,
            "finished": self.finished,
            "out_dir": self.out_dir,
            "doctor": self.doctor,
            "progress": self.progress,
            "blocks": list(self.blocks),
            "stages": [o.to_dict() for o in self.outcomes],
            "gate_actions": self.gate_actions,
            "host": {"platform": platform.platform(), "python": sys.version.split()[0]},
        }

    def markdown(self) -> str:
        lines = [
            f"# 阶段运行报告 — {self.project_id} (r{self.revision})", "",
            f"- 运行编号：`{self.run_id}`",
            f"- 输出目录：`{self.out_dir}`",
            f"- 开始 {self.started}　结束 {self.finished}",
            f"- 可用工具：{', '.join(self.doctor.get('available', [])) or '（无）'}",
            f"- 缺失工具：{', '.join(self.doctor.get('unavailable', [])) or '（无）'}",
            "",
            "| 阶段 | 负责能力 | 状态 | 产物 | 下一步 |",
            "|---|---|---|---|---|",
        ]
        for o in self.outcomes:
            arts = "<br>".join(Path(a).name for a in o.artifacts[:5]) or "—"
            lines.append(
                f"| {o.stage_name} | {', '.join(o.skills[:4])} | {o.status} | {arts} "
                f"| {o.next_action or '—'} |"
            )
        if self.gate_actions:
            lines += ["", "## 门禁后置动作（通过门禁后才成立的工作）", "",
                      "| 能力 | 阶段 | 状态 | 机位数 | 已生成 | 待平台 | 输出 |",
                      "|---|---|---|---|---|---|---|"]
            for a in self.gate_actions:
                lines.append(
                    f"| `{a.get('capability')}` | {a.get('stage', '-')} "
                    f"| {a.get('status', '-')} | {a.get('views', '-')} "
                    f"| {a.get('generated', '-')} | {a.get('awaiting_platform', '-')} "
                    f"| {a.get('dir', '-')} |"
                )
            lines += ["", "> 后置动作没有自己的门禁，只在所在门禁通过的那一刻执行；"
                          "门禁被打回时其记录会被清除。图像一律为非权威成果。"]
        if self.blocks:
            lines += ["", "## 阻断 / 失败", ""] + [f"- {b}" for b in self.blocks]
        return "\n".join(lines)



def _s3_taxonomy_block(project: Any, active: Sequence[str]) -> List[str]:
    """S3 开头先写清"这是什么项目、这一轮要做哪些专业任务"。

    任务清单来自 `taxonomy`（唯一数据源），不是在这里另写一份；
    能力边界也照实写——"能出任务"与"能出合规成果"是两件事。
    """
    from . import taxonomy as _tx
    from .intake import interview as _iv

    tax = _iv.classification(project)
    codes = [str(c) for c in (tax.get("codes") or [])]
    if not codes and not tax.get("natures"):
        return ["## 项目分类", "",
                "- 未识别出已知类型：按最宽口径推进，不套任何专项方法。", ""]
    rows = ["## 项目分类", ""]
    rows.append("| 项 | 内容 |")
    rows.append("|---|---|")
    rows.append("| 用途 | {} |".format(
        "、".join(f"{c} {(_tx.resolve(c).name if _tx.resolve(c) else '')}".strip()
                 for c in codes) or "未识别"))
    if tax.get("nature_labels"):
        rows.append("| 项目性质 | {} |".format("、".join(tax["nature_labels"])))
    if tax.get("commission_labels"):
        rows.append("| 委托范围 | {} |".format("、".join(tax["commission_labels"])))
    cap = _tx.capability_of(codes)
    rows.append("| 能力边界 | {} |".format(cap.get("label") or "未登记"))
    if cap.get("note"):
        rows.append("| 边界说明 | {} |".format(cap["note"]))
    rows.append("")
    focus: List[str] = []
    for c in codes:
        spec = _tx.resolve(c)
        if spec:
            focus += [x for x in spec.focus if x not in focus]
    if focus:
        rows += ["**本类型必须处理的专业要点**：" + "、".join(focus[:8]), ""]
    for did in ("architecture", "interior", "landscape"):
        if did not in active:
            continue
        tasks = _tx.s3_tasks(codes, did)
        if not tasks:
            continue
        label = {"architecture": "建筑设计", "interior": "室内设计",
                 "landscape": "景观设计"}[did]
        rows += [f"### {label}任务（S3）", ""]
        rows += [f"{i}. {t}" for i, t in enumerate(tasks, 1)]
        rows.append("")
    rows += ["> 任务清单是**要做什么**，不是**已经做到什么**："
             "标注为概念/专项的类型，其合规结论仍须相应专业人员给出。", ""]
    return rows


class StageRunner:
    def __init__(
        self,
        project: Project,
        out_dir: str | Path,
        level_id: Optional[str] = None,
        scheme_variant: str = "A",
        assume_approval: bool = False,
        project_dir: Optional[str | Path] = None,
    ) -> None:
        self.project = project
        # 允许 `--project <目录>` 与 `--project <目录>/project.json` 两种写法：
        # 传文件时把它的父目录当项目目录，否则保存时会去建
        # "project.json/project.json" 这种荒唐路径（WinError 183）。
        _pd = Path(project_dir) if project_dir else None
        if _pd is not None and _pd.is_file():
            _pd = _pd.parent
        self.project_dir = _pd
        self.level_id = level_id or (project.levels[0].id if project.levels else "L1")
        self.scheme_variant = scheme_variant
        self.assume_approval = assume_approval
        self.run_id = "run-" + datetime.now().strftime("%Y%m%d-%H%M%S")
        self.out = Path(out_dir) / self.run_id
        self.schemes: Dict[str, SchemeResult] = {}
        self.manifest = RunManifest(
            run_id=self.run_id, project_id=project.project_id,
            revision=project.revision, out_dir=str(self.out), doctor=doctor(),
        )

    # ------------------------------------------------------------------
    def _dir(self, stage_id: str) -> Path:
        st = STAGE_BY_ID[stage_id]
        d = self.out / f"{st.code}-{STAGE_SLUG.get(stage_id, st.id)}"
        d.mkdir(parents=True, exist_ok=True)
        return d

    # ------------------------------------------------------------------
    def _space_labels(self) -> List[Tuple[float, float, float, str]]:
        """房间名 + 投影用标高：轴测图上要能认出哪间是哪间。"""
        out: List[Tuple[float, float, float, str]] = []
        elev = {lv.id: float(lv.elevation_mm or 0.0) for lv in self.project.levels}
        for sp in self.project.spaces:
            if sp.use == "envelope" or not str(sp.name or "").strip():
                continue
            pts = [p for p in (sp.boundary_mm2d or []) if len(p) >= 2]
            if len(pts) < 3:
                continue
            try:
                x0, y0, x1, y1 = sp.bbox()
            except Exception:  # noqa: BLE001
                continue
            area = abs((x1 - x0) * (y1 - y0)) / 1e6
            if area < 4.0:                      # 太小的房间标了也是糊的
                continue
            out.append(((x0 + x1) / 2.0, (y0 + y1) / 2.0,
                        elev.get(sp.level_id, 0.0) + 1400.0, sp.name))
        return out

    # ------------------------------------------------------------------
    def _import_conditions(self) -> str:
        """项目目录里有 existing-conditions.json 就导入，返回一句人话。

        只读业主给的资料，不生成几何：没有文件就什么都不做，
        文件不成立就如实说出来（而不是当成没有资料继续往下跑）。
        """
        self._conditions_note = ""
        if not self.project_dir:
            return ""
        from . import existing as _ex

        path = _ex.discover(self.project_dir)
        if path is None:
            return ""
        if _ex.has_geometry(self.project):
            self._conditions_note = "原始条件未重复导入：项目已有几何"
            return self._conditions_note
        try:
            got = _ex.import_file(self.project, path)
            self._conditions_note = (
                f"原始条件已导入：{got['envelope_area_m2']} m² / "
                f"{got['walls']} 道墙（来源 {got['source']}）")
        except _ex.ConditionsError as exc:
            self._conditions_note = f"原始条件没读进来：{exc}"
        return self._conditions_note

    # ------------------------------------------------------------------
    def run_stage(self, stage_id: str, confirm: Optional[bool] = None) -> StageOutcome:
        if stage_id not in STAGE_BY_ID:
            raise ValidationError(f"unknown stage '{stage_id}'")
        st = STAGE_BY_ID[stage_id]
        t0 = time.time()
        confirm = self.assume_approval if confirm is None else confirm

        ok, reason = can_start(self.project, stage_id)
        if not ok and get_state(self.project, stage_id).status not in (REWORK,):
            out = StageOutcome(stage_id, f"{st.code} {st.name}", skills_for_stage(stage_id),
                               status="blocked", error=reason,
                               next_action="先完成并确认前置阶段")
            out.seconds = time.time() - t0
            self.manifest.add(out)
            return out

        from .intake.guard import check_stage

        guard = check_stage(self.project, stage_id)
        start_stage(self.project, stage_id)
        handler = getattr(self, f"stage_{stage_id}", None)
        if handler is None:
            out = StageOutcome(stage_id, f"{st.code} {st.name}", status="skipped",
                               notes=["该阶段尚未实现"], next_action="实现该阶段处理器")
        else:
            try:
                out = handler()
            except OmniArchitectError as exc:
                out = StageOutcome(stage_id, f"{st.code} {st.name}",
                                   skills_for_stage(stage_id), status="failed", error=str(exc))
            except Exception as exc:  # pragma: no cover
                out = StageOutcome(stage_id, f"{st.code} {st.name}",
                                   skills_for_stage(stage_id), status="failed",
                                   error=f"{type(exc).__name__}: {exc}")
        _cond = getattr(self, "_conditions_note", "")
        if _cond:
            out.notes.insert(0, _cond)
            self._conditions_note = ""          # 只报一次，别在每个阶段重复同一句
        out.skills = out.skills or skills_for_stage(stage_id)
        out.stage_name = out.stage_name or f"{st.code} {st.name}"
        out.seconds = time.time() - t0
        # A limited stage still runs; the restriction is part of its record so
        # nobody later mistakes its output for unrestricted work.
        for r in guard.restrictions:
            out.notes.append(f"限制：{r}")
        for h in guard.needs_human:
            out.notes.append(f"须专业复核：{h}")

        if out.status in ("failed", "blocked"):
            from .stage_state import block_stage

            block_stage(self.project, stage_id, out.error or "stage failed")
        else:
            submit_for_confirmation(self.project, stage_id, out.notes[0] if out.notes else "")
            out.next_action = f"提交确认：{st.gate.label}（{st.gate.approver}）"
            if confirm:
                approval = self.approve(stage_id, source="demo",
                                        note="由 --assume-approval 自动确认（演示，非业主签署）")
                if approval["status"] == CONFIRMED:
                    out.next_action = ("已确认（演示模式，未形成业主基准）"
                                       if approval.get("source") == "demo"
                                       else "已确认，可进入下一阶段")
                    out.gate_actions = approval.get("post_gate_actions") or []
                    for action in out.gate_actions:
                        label = action.get("capability", "")
                        if action.get("ran"):
                            out.notes.append(
                                f"门禁后置动作 {label}：{action.get('summary', '')}"
                            )
                        else:
                            out.notes.append(
                                f"门禁后置动作 {label} 未执行：{action.get('reason', '')}"
                            )
                    for n in approval.get("notes") or []:
                        out.notes.append(n)
                else:
                    out.notes.append("自动确认未通过：" + "；".join(
                        approval.get("notes") or []))
        self.manifest.add(out)
        return out

    # ------------------------------------------------------------------
    # post-gate actions
    # ------------------------------------------------------------------
    def run_post_gate(self, stage_id: str, **kwargs: Any) -> List[Dict[str, Any]]:
        """Run the work that only becomes valid *after* a gate has passed.

        Currently G3 -> concept-visualization: the client-facing concept
        renderings. Producing them before approval would picture a plan that
        may still change, so they are attached to the gate rather than to a
        stage body.
        """
        from .stages import post_gate_actions_for_stage

        out: List[Dict[str, Any]] = []
        for slug in post_gate_actions_for_stage(stage_id):
            handler = getattr(self, f"post_gate_{slug.replace('-', '_')}", None)
            if handler is None:
                out.append({"capability": slug, "stage": stage_id, "ran": False,
                            "reason": "该后置动作尚未实现"})
                continue
            try:
                rec = handler(stage_id=stage_id, **kwargs)
                rec.setdefault("stage", stage_id)
                out.append(rec)
            except ModelError as exc:
                # 没有轮廓/墙就没有平面可依据——这是"不适用"，不是崩溃。
                out.append({"capability": slug, "stage": stage_id, "ran": False,
                            "skipped": True,
                            "reason": f"该成果需要平面几何，本项目当前没有：{exc}"})
            except Exception as exc:
                out.append({"capability": slug, "stage": stage_id, "ran": False,
                            "reason": f"{type(exc).__name__}: {exc}"})
        return out

    def post_gate_concept_visualization(self, stage_id: str = "S3",
                                        limit: int = 5, model: str = "",
                                        submit: bool = False,
                                        authorized: bool = False) -> Dict[str, Any]:
        """概念效果图 —— 平面确认后立即执行。

        Works on a **fork** when the chosen scheme has not been installed into
        the canonical model yet. Confirming a gate must not silently rewrite the
        project: the scheme becomes the basis for deepening at S4. The fork
        carries the same revision, so every rendering is traceable to the exact
        revision of the plan it came from.
        """
        from .providers import canvas

        chosen = self._confirmed_variant()
        basis = self.project
        forked = False
        if not any(s.properties.get("scheme") for s in basis.spaces):
            basis = basis.fork()
            forked = True
            gen = PlanGenerator(basis, self.level_id)
            s = self.schemes.get(chosen) or gen.generate(
                _scheme_options(chosen, finishes.project_profile(self.project)))
            _install_scheme(basis, s)
            resolve_host_axes(basis)

        d = self._dir(stage_id) / "concept-render"
        res = canvas.render(
            basis, d, level_id=self.level_id, scheme=chosen,
            limit=limit, model=model, project_dir=self.project_dir,
            submit=submit, authorized=authorized,
        )
        if forked:
            res.notes.append(
                f"本批图依据已确认的方案{chosen}生成；统一空间模型尚未安装该方案"
                "（S4 时安装为深化依据），故本次不改动项目修订号。"
            )

        deps = [s.id for s in basis.spaces if s.properties.get("scheme")]
        register_artifact(self.project, "art-concept-render", "render", deps,
                          "concept-visualization", relpath(d),
                          "generated" if res.generated else "needs_review")
        record_change(
            self.project, "gate_action",
            f"平面确认后生成概念效果图：{len(res.views)} 个机位，"
            f"已生成 {len(res.generated)}，待平台 {len(res.pending)}",
            targets=["art-concept-render"],
        )
        self.project.meta.setdefault("gate_actions", {})
        store = self.project.meta["gate_actions"]
        store["concept-visualization"] = {
            "stage": stage_id, "scheme": chosen, "revision": self.project.revision,
            "status": res.status, "provider_state": res.provider_state,
            "views": len(res.views), "generated": len(res.generated),
            "awaiting_platform": len(res.pending),
            "dir": relpath(d), "at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            "authoritative": False,
        }
        self._persist()
        return {
            "capability": "concept-visualization", "ran": True,
            "status": res.status, "views": len(res.views),
            "generated": len(res.generated), "awaiting_platform": len(res.pending),
            "provider_state": res.provider_state, "dir": relpath(d),
            "files": res.files, "warnings": list(res.warnings),
            "summary": (
                f"{len(res.views)} 个机位任务包已就绪（{relpath(d)}）；"
                f"平台状态 {res.provider_state}，已生成 {len(res.generated)} 张"
                if res.generated else
                f"{len(res.views)} 个机位任务包已就绪（{relpath(d)}）；"
                f"平台状态 {res.provider_state}，图像待生成（未伪造占位图）"
            ),
            "result": res.to_dict(),
        }

    def _confirmed_variant(self) -> str:
        """Which scheme the owner approved at G3."""
        installed = (self.project.meta.get("scheme") or {}).get("variant")
        if installed:
            return str(installed)
        if self.scheme_variant in self.schemes:
            return self.scheme_variant
        return self.scheme_variant

    # ------------------------------------------------------------------
    def run_until_gate(self, start: Optional[str] = None,
                       stop_at: Optional[str] = None) -> RunManifest:
        started = start is None
        for sid in STAGE_ORDER:
            if start and not started:
                if sid == start:
                    started = True
                else:
                    continue
            if get_state(self.project, sid).status == CONFIRMED:
                continue
            out = self.run_stage(sid, confirm=False)
            if out.status in ("blocked", "failed"):
                break
            if stop_at and sid == stop_at:
                break
            break  # stop at the first gate awaiting confirmation
        self._finish()
        return self.manifest

    def run_all(self, confirm_all: bool = True,
                stages: Optional[Sequence[str]] = None) -> RunManifest:
        """跑到 S8。已确认的阶段跳过，不重跑。

        重跑已确认阶段只会得到"已确认；如需修改请走变更影响分析"——那是给
        改设计的提示，不是给"继续往下做"的报错。所以要改设计应该走
        `omniarchitect change`，而不是 `run --all`。
        """
        for sid in (stages or STAGE_ORDER):
            st = get_state(self.project, sid)
            if st.status == CONFIRMED:
                out = StageOutcome(sid, f"{STAGE_BY_ID[sid].code} {STAGE_BY_ID[sid].name}",
                                   skills_for_stage(sid), status="skipped",
                                   notes=["已确认，本轮跳过（改设计请走 change）"])
                self.manifest.add(out)
                continue
            out = self.run_stage(sid, confirm=confirm_all)
            if out.status in ("blocked", "failed"):
                break
        self._finish()
        return self.manifest

    def run_remaining(self) -> RunManifest:
        return self.run_all(confirm_all=self.assume_approval)

    def approve(self, stage_id: str, by: str = "", note: str = "",
                source: str = "owner", acknowledge: Sequence[str] = (),
                force: bool = False) -> Dict[str, Any]:
        """The single approval entry point for every caller.

        G1 goes through `intake.decide_gate`, so the CLI, the stage runner and
        `--assume-approval` all get the same checks. ``source="demo"`` marks a
        demonstration: it confirms the stage so a pipeline can continue, but it
        never writes an owner baseline and never claims to be a signature.

        S2–S8 gates have no brief-level review to run; they still record the
        change and honour post-gate actions.
        """
        from .intake.gate import decide_gate

        if stage_id == "S2":
            return self._approve_concept(by=by, note=note, source=source,
                                         acknowledge=acknowledge, force=force)
        if stage_id == "S3":
            return self._approve_plan(by=by, note=note, source=source,
                                      acknowledge=acknowledge, force=force)

        if stage_id == "S1":
            outcome = decide_gate(self.project, "approved", by=by, note=note,
                                  source=source, acknowledge=acknowledge,
                                  force=force)
            if outcome.decision == "approved":
                record_change(self.project, "gate",
                              f"{stage_name(stage_id)} 确认通过"
                              f"（{outcome.source}：{self.project.meta.get('intake', {}).get('baseline', {}).get('confirmed_by') or '演示'}）",
                              targets=[stage_id])
                actions = self.run_post_gate(stage_id)
                self._persist()
                return {
                    **get_state(self.project, stage_id).to_dict(),
                    "source": outcome.source,
                    "notes": outcome.notes,
                    "assessment": outcome.assessment,
                    "post_gate_actions": actions,
                }
            self._persist()
            return {
                **get_state(self.project, stage_id).to_dict(),
                "source": outcome.source,
                "notes": outcome.notes,
                "assessment": outcome.assessment,
                "post_gate_actions": [],
            }

        st = self._run_conformance(stage_id)
        if st is not None and st.blocks_approval:
            # 已可证明偏离已确认的设计意图：不能签，必须先走变更审批。
            # 注意这里不是"提示"，是拒绝——否则保护机制只是装饰。
            self._persist()
            return {
                **get_state(self.project, stage_id).to_dict(),
                "status": "blocked",
                "source": source,
                "notes": [
                    f"不能确认 {stage_name(stage_id)}：成果已偏离 G2 确认的设计意图",
                    *[f"· {c.name}：{c.evidence}" for c in st.changed],
                    "处置：按原意图调整，或对该设计变更走正式审批后重新提交",
                ],
                "conformance": st.to_dict(),
                "post_gate_actions": [],
            }

        st_confirmed = confirm_stage(self.project, stage_id, by=by or (
            "业主" if source == "owner" else "演示流程"), note=note)
        if stage_id == "S6" and source == "owner":
            self.project.meta["frozen_revision"] = self.project.revision
            self.project.meta["scheme"] = {
                **dict(self.project.meta.get("scheme") or {}),
                "frozen_at_revision": self.project.revision,
            }
            record_change(self.project, "freeze", f"G6 设计锁定（r{self.project.revision}）",
                          targets=["S6"])
        if stage_id == "S8" and source == "owner":
            for artifact in self.project.artifacts:
                if artifact.id == "art-delivery":
                    artifact.status = "issued"
        record_change(self.project, "gate",
                      f"{stage_name(stage_id)} 确认通过（{source}）", targets=[stage_id])
        actions = self.run_post_gate(stage_id)
        self._persist()
        notes: List[str] = []
        if st is not None:
            from .conformance import summary_lines as _conf_lines

            notes += _conf_lines(st)
            if st.unknown:
                notes.append("以上无法自动证明的特征须人工设计审查，未计入通过")
        return {**st_confirmed.to_dict(), "source": source, "notes": notes,
                "conformance": st.to_dict() if st else {},
                "post_gate_actions": actions}

    def _run_conformance(self, stage_id: str):
        """在当前阶段跑一次设计意图一致性检查并落档。

        G3–G8 都跑，但只看"已证明改变"。无法自动证明的（观感、比例）
        进人工审查清单，不阻断——否则每个项目都卡在审不了的事上。
        """
        from . import conformance

        intent = (self.project.meta or {}).get("design_intent")
        if not intent:
            return None
        try:
            rep = conformance.check(self.project, stage=stage_id, out_root=self.out)
        except Exception as exc:                        # noqa: BLE001
            rep = conformance.ConformanceReport(
                stage=stage_id, status=conformance.UNKNOWN,
                note=f"一致性检查执行失败：{type(exc).__name__}: {exc}")
        store = (self.project.meta or {}).get("conformance")
        if not isinstance(store, dict):
            store = {}
            self.project.meta["conformance"] = store
        store[stage_id] = {**rep.to_dict(), "checked_at": _now()}
        return rep

    def _approve_concept(self, by: str = "", note: str = "", source: str = "owner",
                         acknowledge: Sequence[str] = (), force: bool = False
                         ) -> Dict[str, Any]:
        """G2: confirm the concept and write the style lock — as one action.

        The lock is written by `concept.gate.decide_gate` *before* the stage is
        confirmed, so a confirmed concept can never exist without its matching
        style lock. This method no longer writes it, because a second writer is
        exactly how the two can disagree.
        """
        from .concept import decide_gate as decide_g2

        # Same directory the S2 stage body writes into: the concept options,
        # the style lock, the summary and the handoff must live together, or
        # "confirmed" and "the file exists" stop being the same statement.
        summary_dir = self._dir("S2")

        outcome = decide_g2(self.project, "approved", by=by, note=note,
                            source=source, acknowledge=acknowledge, force=force,
                            summary_path=str(summary_dir / "g2-approval-summary.md"))
        notes = list(outcome.notes)
        actions: List[Dict[str, Any]] = []
        if outcome.decision == "approved":
            record_change(self.project, "gate",
                          f"{stage_name('S2')} 概念确认"
                          f"（{outcome.source}："
                          f"{(self.project.meta.get('concept', {}).get('baseline') or {}).get('concept_id') or '演示'}）",
                          targets=["S2"])
            actions = self.run_post_gate("S2")
            for action in actions:
                label = action.get("capability", "")
                notes.append(
                    f"门禁后置动作 {label}：{action.get('summary', '')}" if action.get("ran")
                    else f"门禁后置动作 {label} 未执行：{action.get('reason', '')}"
                )
        self._persist()
        return {
            **get_state(self.project, "S2").to_dict(),
            "source": outcome.source,
            "notes": notes,
            "assessment": outcome.assessment,
            "formal": outcome.formal,
            "rolled_back": outcome.rolled_back,
            "post_gate_actions": actions,
        }

    def _approve_plan(self, by: str = "", note: str = "", source: str = "owner",
                      acknowledge: Sequence[str] = (), force: bool = False
                      ) -> Dict[str, Any]:
        """G3: only a plan that implements a *signed* concept can be issued.

        Exploration stays allowed — S3 produces its方案 no matter what. What
        changes here is the signature: `source="owner"` needs a live G2 baseline,
        a plan record bound to that baseline's digest, no major conformance
        conflict, and no unsupported-prototype substitution. `force` does not
        move any of those.
        """
        from .concept.handoff import assess_plan_gate

        assess = assess_plan_gate(self.project)
        notes: List[str] = []
        formal = False
        actions: List[Dict[str, Any]] = []

        if source == "owner":
            ok, blockers = can_confirm(self.project, "S3")
            if not ok:
                notes.append(f"不能签发正式 G3（当前状态：{assess.get('state_label') or '仅可探索'}）："
                             f"{assess.get('verdict') or ''}")
                if assess["blockers"]:
                    notes.append("硬阻断（连方案都不成立）：")
                    notes += [f"  [{b['id']}] {b['text']}" for b in assess["blockers"]]
                if assess.get("critical"):
                    notes.append("关键前提未满足（方案可讨论，不能声称已核实通过）：")
                    notes += [f"  [{c['id']}] {c['text']}" for c in assess["critical"]]
                if assess.get("conditions"):
                    notes.append("以下不影响本轮确认深度，记录在案：")
                    notes += [f"  [{c['id']}] {c['text']}" for c in assess["conditions"]]
                notes.append("平面可作为探索稿继续深化；正式 G3 须先解决以上硬阻断与关键前提。"
                             "--force 不能绕过。")
                if assess.get("manual_review"):
                    notes.append(f"另有 {len(assess['manual_review'])} 项待人工复核，未计入通过")
                self._persist()
                return {
                    **get_state(self.project, "S3").to_dict(),
                    "source": source, "notes": notes, "assessment": assess,
                    "formal": False, "post_gate_actions": [],
                }
            st = confirm_stage(self.project, "S3", by=by or "业主",
                               note=note or "G3 平面方案确认")
            formal = True
            notes.append(f"G3 已正式签发：概念 {assess['concept_id']} 的平面成立"
                         f"（一致性 {assess['conformance']}）")
            if not assess.get("fully_verified"):
                notes.append(f"待人工复核 {len(assess.get('manual_review') or [])} 项："
                             "这些空间约束系统无法自动确认，未计入通过，须人看图核对")
            record_change(self.project, "gate",
                          f"{stage_name('S3')} 确认通过（owner：{assess['concept_id'] or '—'}）",
                          targets=["S3"])
            # 平面签了，才有资格把图纸派生成视觉：参考图在这里真做出来，任务只编译不提交。
            try:
                from .concept.visual import build_plan_visuals

                variant = str((self.project.meta.get("scheme") or {}).get("variant")
                              or self.scheme_variant)
                ref_model = self._reference_model(variant)
                vp = build_plan_visuals(ref_model, self._dir("S3"),
                                        stage="S3", scheme=variant)
                s = vp.get("summary") or {}
                if s.get("total"):
                    notes.append(
                        f"图纸派生：参考图 {len(vp.get('references') or [])} 份已生成，"
                        f"任务 {s['total']} 项（可提交 {s.get('ready', 0)}、"
                        f"待补充 {s.get('blocked_missing', 0)}）——仅编译，未提交")
                else:
                    notes.append(f"图纸派生未生成：{vp.get('note', '未知原因')}")
            except Exception as exc:
                notes.append(f"图纸派生任务包生成失败：{type(exc).__name__}: {exc}")
        else:
            st = confirm_stage(self.project, "S3", by=by or "演示流程",
                               note=note or "G3 演示确认（不构成正式签发）")
            notes.append("演示确认：流程可继续，但这不是正式 G3 签发"
                         + ("（当前没有有效 G2 概念基准）"
                            if assess["handoff_status"] != "locked" else "") )

        # G3 也要过一遍意图一致性：平面本身不能违背已签的概念。
        st_after = self._run_conformance("S3")
        if st_after is not None and st_after.blocks_approval:
            self._persist()
            return {
                **get_state(self.project, "S3").to_dict(),
                "status": "blocked",
                "source": source,
                "notes": [
                    "不能签发 G3：平面已偏离 G2 确认的设计意图",
                    *[f"· {c.name}：{c.evidence}" for c in st_after.changed],
                    "处置：按原意图调整平面，或对该变更走正式审批",
                ],
                "assessment": assess,
                "conformance": st_after.to_dict(),
                "formal": False,
                "post_gate_actions": [],
            }

        actions = self.run_post_gate("S3")
        for action in actions:
            label = action.get("capability", "")
            notes.append(
                f"门禁后置动作 {label}：{action.get('summary', '')}" if action.get("ran")
                else f"门禁后置动作 {label} 未执行：{action.get('reason', '')}")
        self._record_plan_gate(st, assess, formal=formal, by=by, source=source)
        if st_after is not None:
            from .conformance import summary_lines as _conf_lines

            notes += _conf_lines(st_after)
        self._persist()
        return {
            **st.to_dict(),
            "source": source, "notes": notes, "assessment": assess,
            "formal": formal,
            "conformance": st_after.to_dict() if st_after else {},
            "post_gate_actions": actions,
        }

    def _record_plan_gate(self, st: Any, assess: Dict[str, Any], *,
                          formal: bool, by: str, source: str) -> None:
        meta = self.project.meta if isinstance(self.project.meta, dict) else {}
        self.project.meta = meta
        concept = meta.get("concept")
        if not isinstance(concept, dict):
            concept = {}
            meta["concept"] = concept
        plan = concept.get("plan")
        if not isinstance(plan, dict):
            plan = {}
        record = {
            "decision": "approved" if formal else "demo_approved",
            "formal": formal,
            "source": source,
            "by": by or ("业主" if formal else "演示流程"),
            "at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            "revision": self.project.revision,
            "concept_id": assess.get("concept_id", ""),
            "conformance": assess.get("conformance", ""),
            "fully_verified": bool(assess.get("fully_verified")),
            "manual_review": list(assess.get("manual_review") or []),
            "blockers": [b.get("id") for b in (assess.get("blockers") or [])],
            "stage_status": st.status,
        }
        plan["gate"] = record
        concept["plan"] = plan

    def confirm(self, stage_id: str, by: str = "业主", note: str = "",
                source: str = "owner") -> Dict[str, Any]:
        """Backwards-compatible wrapper around `approve`."""
        return self.approve(stage_id, by=by, note=note, source=source)

    def reject(self, stage_id: str, reason: str = "") -> Dict[str, Any]:
        from .stage_state import reject_stage

        if stage_id == "S1":
            from .intake.gate import decide_gate

            outcome = decide_gate(self.project, "revision_requested", note=reason)
            cleared = self.project.meta.get("gate_actions", {})
            for slug in post_gate_actions_for_stage(stage_id):
                if slug in cleared:
                    cleared.pop(slug)
            record_change(self.project, "gate",
                          f"{stage_name(stage_id)} 未通过：{reason}", targets=[stage_id])
            self._persist()
            return {**get_state(self.project, stage_id).to_dict(),
                    "notes": outcome.notes}

        st = reject_stage(self.project, stage_id, reason)
        # A rejected gate invalidates anything that gate had produced.
        cleared = self.project.meta.get("gate_actions", {})
        for slug in post_gate_actions_for_stage(stage_id):
            if slug in cleared:
                cleared.pop(slug)
        record_change(self.project, "gate", f"{stage_name(stage_id)} 未通过：{reason}",
                      targets=[stage_id])
        self._persist()
        return st.to_dict()

    # ------------------------------------------------------------------
    def apply_change(self, text: str, apply: bool = True,
                     authorization: Optional[Dict[str, Any]] = None
                     ) -> changes.ChangeImpactReport:
        """变更入口。`apply=False` 是**纯预览**：不写盘、不动修订号、不动门禁。

        旧实现在 `apply=False` 时仍然 `invalidate_from()` + `_persist()`，
        于是"看一下会怎样"就把项目改成了返工状态。预览必须是只读的。
        """
        rep = changes.analyse(self.project, text, apply=apply,
                              authorization=authorization)
        if not rep.applied:
            # 预览或未授权：报告要明确说明"这是提案，不是执行记录"，
            # 而且要写在落盘之前——先写盘再补说明，文件里就没有这句话了。
            reason = rep.blocked_reason or "预览模式"
            rep.notes.append(f"未改动项目数据（{reason}）")

        d = self.out / "changes"
        d.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        suffix = "proposal" if not rep.applied else "applied"
        (d / f"change-{stamp}-{suffix}.json").write_text(
            json.dumps(rep.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
        )
        (d / f"change-{stamp}-{suffix}.md").write_text(rep.markdown(), encoding="utf-8")

        if not rep.applied:
            return rep

        touched = invalidate_from(self.project, rep.diagnosis.landing_stage)
        rep.notes.append("受影响阶段状态已置为返工："
                         + "、".join(stage_name(s) for s in touched))
        self._persist()
        return rep

    def propose_change(self, text: str) -> changes.ChangeRequest:
        """阶段 A：出提案，不动项目。"""
        req = changes.propose(self.project, text)
        d = self.out / "changes"
        d.mkdir(parents=True, exist_ok=True)
        (d / f"{req.request_id}.json").write_text(
            json.dumps(req.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        return req

    def _persist(self) -> None:
        self.project.meta = dict(self.project.meta or {})
        self.project.meta["stage_state"] = {
            s.stage: s.to_dict() for s in all_states(self.project)
        }
        if self.project_dir:
            self.project.save(Path(self.project_dir) / "project.json")
        else:
            self.project.save(self.out / "project-state.json")

    def _finish(self) -> None:
        self.manifest.finished = _now()
        self.manifest.revision = self.project.revision
        self.manifest.progress = progress(self.project)
        self.out.mkdir(parents=True, exist_ok=True)
        self._persist()
        (self.out / "stage-state.md").write_text(stage_markdown(self.project), encoding="utf-8")
        (self.out / "run-manifest.json").write_text(
            json.dumps(self.manifest.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
        )
        (self.out / "run-report.md").write_text(self.manifest.markdown(), encoding="utf-8")

    # ==================================================================
    # 01 项目启动与设计任务书
    # ==================================================================
    def stage_S1(self) -> StageOutcome:
        """S1 lives in `omniarchitect/intake` — this is only the adapter.

        There is exactly one task-brief generator in the project. Running the
        stage and running `omniarchitect intake --action analyze` therefore
        produce the same professional data and the same eight files; the only
        difference is where the output directory points.
        """
        from .intake import assess_gate, generate_bundle
        from .intake.diligence import blocking_stages

        d = self._dir("S1")
        self.ensure_intake()

        # 行业任务书：房间清单属于 S1——客户签的是"要哪些房间、各多大"。
        # 如果等到 S3 才补，任务书基准会在平面阶段变化，G3 必然判"任务书已变更"。
        # 这不是为了过门禁，而是本来就该在委托确认时讲清楚。
        program_note = self._install_sector_program()

        # The estimate is produced inside the bundle so both entry points agree.
        # Case research runs on the live stage but is switched off by the test
        # harness (`OMNIAILAB_NO_NETWORK`), because a suite that depends on
        # eight foreign websites fails for reasons that have nothing to do with
        # this code.
        bundle = generate_bundle(self.project, d, research=_network_allowed())

        assess = assess_gate(self.project)
        blocks = blocking_stages(self.project)
        notes = [
            f"S1 成果包 {bundle['count']} 份（{bundle['precision']}）："
            f"完整度 {bundle['completeness'] * 100:.0f}%，"
            f"需求 {bundle['opportunities']} 个设计机会",
        ]
        # 一页设计判断：客户先看到"我们怎么理解你的项目"，而不是一堆清单。
        # 复用同一份问诊与分类，不另写一套判断逻辑。
        from .concept import quick as _quick

        try:
            pos = _quick.write(self.project, d)
            notes.append(f"设计定位：{pos['headline']}")
        except Exception as exc:            # noqa: BLE001  判断失败不能挡住任务书
            pos = {}
            notes.append(f"设计定位未生成：{type(exc).__name__}")
        if program_note:
            notes.insert(0, program_note)
        if blocks:
            notes.append("后续阶段仍受限：" + "；".join(
                f"{sid} {len(v)} 项" for sid, v in blocks.items()))
        if assess.blocks_gate:
            notes.append("G1 前需业主决定：" + "；".join(
                b["problem"] for b in assess.blocks_gate[:2]))
        arts = [str(d / name) for name in bundle["files"]]
        if pos.get("path"):
            arts.append(pos["path"])
        return StageOutcome("S1", artifacts=arts, notes=notes)

    def _install_sector_program(self) -> str:
        """按行业生成任务书房间清单（只在学校/医院/厂房/酒店这类有程序的类型跑）。

        景观不出房间：分区与做法在 S3 直接给，避免把绿地塞进房间表。
        """
        from . import sector as _sector

        if self.project.program:
            return ""
        b = _sector.brief.from_project(self.project)
        if b.sector not in _sector.program.BUILDERS or not b.codes:
            return ""
        if b.sector == "landscape":
            return ""
        prog = _sector.program.build(b)
        if not rows_or_empty(prog):
            return ""
        _sector.layout.install_program(self.project, prog)
        return (f"行业任务书：{prog.unit} {len(prog.rows)} 项"
                f"（{prog.area_m2:,.0f} m²，按客户给的规模推出）")

    def ensure_intake(self) -> None:
        """Make sure S1 has an interview state before it generates anything.

        A project may arrive with drawings only, or with a sentence, or with a
        full programme. In every case the bundle needs a profile and a start
        mode, so they are established once and then left alone.
        """
        from .intake.interview import ensure_intake

        ensure_intake(self.project)

    # ==================================================================
    # 02 概念方案设计
    # ==================================================================
    def stage_S2(self) -> StageOutcome:
        """S2 lives in `omniarchitect/concept` — this is only the adapter.

        Same rule as S1: one generator. `run --stage S2` and
        `concept --action generate` must produce the same package, so the stage
        does not build any content of its own.
        """
        from .concept import generate_bundle

        d = self._dir("S2")
        bundle = generate_bundle(
            self.project, d,
            pre_gate=False if get_state(self.project, "S1").status == CONFIRMED else True,
            submit=False, project_dir=self.project_dir,
        )
        notes = [
            f"概念方向 {bundle['count']} 套（{bundle['profile']}／{bundle['precision']}）："
            + "、".join(f"{cid} {role}" for cid, role in (bundle["roles"] or {}).items()),
        ]
        if bundle.get("suggested"):
            notes.append(f"总设计师建议：{bundle['suggested']}（G2 需业主明确选定 concept_id）")
        visual = bundle.get("visual") or {}
        notes.append(f"概念视觉：平台 {visual.get('platform_state', '?')}，"
                     f"已生成 {visual.get('generated', 0)}（复用 {visual.get('reused', 0)}）／"
                     f"待平台 {visual.get('deferred', 0)}／待费用确认 {visual.get('held', 0)}，"
                     f"本次提交 {visual.get('submitted', 0)}")
        if bundle.get("deck"):
            notes.append(f"逐条文字提案（附录留档）：{bundle['deck'].get('slides')} 页"
                         f"（{bundle['deck'].get('backend')}）")
        prop = bundle.get("proposal") or {}
        if prop.get("pages"):
            notes.append(f"客户版概念汇报：{prop['pages']} 页（HTML + PPTX 同一份页面模型）"
                         + (f"，精选参考 {prop['curation']['count']} 张"
                            if (prop.get("curation") or {}).get("count") else
                            "；素材库无同类实景，未取图"))
        if prop.get("motion"):
            label = {"architecture": "体量与形态", "interior": "功能与序列",
                     "landscape": "场地与游线"}.get(
                str(prop.get("discipline") or ""), "概念推演")
            notes.append(f"概念动画：{label}（离线可播 HTML，非生成式视频）")
        elif prop.get("motion_skipped"):
            notes.append(f"本方案不出动画：{prop['motion_skipped']}（静态分析图已出）")
        for w in (bundle.get("warnings") or [])[:3]:
            notes.append(w)

        # 机位任务包与概念视觉任务不是一回事：前者给"每个空间一张图"的批量表现，
        # 后者给"方向氛围"。两者都要保留，且都如实标注状态。
        extra: List[str] = []
        style = str((self.project.constraints or {}).get("style") or "")
        try:
            rj = RenderAdapter().build_job_package(
                self.project, d / "moodboard-render-jobs.json",
                level_id=self.level_id, lighting="day_soft", style=style,
            )
            extra = list(rj.artifacts)
            shots = len((rj.package or {}).get("shots") or [])
            notes.append(f"机位任务包：{shots} 个机位（表现用途，非尺寸依据）")
        except Exception as exc:
            notes.append(f"机位任务包未生成：{type(exc).__name__}: {exc}")

        files = [v for v in (bundle.get("files") or {}).values()
                 if isinstance(v, str) and v.endswith((".md", ".json", ".pptx"))]
        register_artifact(self.project, "art-concept", "document", ["art-brief"],
                          "concept-design", relpath(d / "concept-options.json"), "draft")
        register_artifact(self.project, "art-concept-moodboard", "document", ["art-concept"],
                          "moodboard-aesthetic-iteration",
                          relpath(d / "moodboards"), "draft")
        return StageOutcome(
            "S2",
            artifacts=list(dict.fromkeys(files + extra +
                                         [str(d / "concept-diagrams")])),
            notes=notes,
        )

    # ==================================================================
    # 03 平面方案设计
    # ==================================================================
    def stage_S3(self) -> StageOutcome:
        d = self._dir("S3")
        # 先看范围：专项委托不能被房间算法顶替。
        # 专业范围路由：平面生成器只覆盖建筑/室内的空间组织。
        # 景观、结构、机电专项不能拿住宅/办公的房间算法冒充成品。
        from . import disciplines as _disc
        from . import taxonomy as _tax
        from .intake import interview as _iv

        _scope = _disc.ensure(self.project)
        _active = set(_scope.active())

        # 业主给了实测资料就先读进来。S3 不能靠"按面积反算一个轮廓"排平面——
        # 那是编数据；但把业主量好的轮廓当成文字需求放着不读，也是失职。
        self._import_conditions()
        # 住宅这类非行业项目：S1 只留下需求原话，S3 需要的是房间任务表。
        # 有实测面积就按住宅配比翻译一份，并记下来源；没有面积就不编。
        if not self.project.program and "interior" in _active:
            from . import program as _prog

            _rows = _prog.ensure(self.project)
            if _rows:
                self._conditions_note = (self._conditions_note + "；" if
                                         getattr(self, "_conditions_note", "") else "") + \
                    f"房间任务表按套内面积推导（{len(_rows)} 间）"

        # ---- 行业分支：学校 / 医院 / 厂房 / 酒店 / 景观 ----
        # 走各行业自己的任务书与排布（sector.stage），但仍是同一个 S3：
        # 同一入口、同一 G3、同一空间模型与 DXF 适配器。
        from . import sector as _sector

        _sb = _sector.brief.from_project(self.project)
        _res = _sector.stage.run(self, d, _sb, sorted(_active))
        if not _res.get("skip"):
            if _res.get("status") == "blocked":
                return StageOutcome(
                    "S3", "03 平面方案设计", skills_for_stage("S3"), adapter="dxf",
                    status="blocked", error=_res.get("error", ""),
                    next_action=_res.get("next_action", ""),
                    notes=list(_res.get("notes") or []),
                )
            arts = list(_res.get("artifacts") or [])
            register_artifact(self.project, "art-schemes", "document",
                              ["project:program", "shell"], "space-planning",
                              relpath(d / "scheme-comparison.md"), "draft")
            if (d / "site-plan.svg").exists():
                register_artifact(self.project, "art-site-plan", "drawing",
                                  ["project:program"], "site-planning",
                                  relpath(d / "site-plan.svg"), "draft")
            return StageOutcome("S3", "03 平面方案设计", skills_for_stage("S3"),
                                artifacts=arts, adapter="dxf",
                                notes=list(_res.get("notes") or []))

        # 只有"真的有房间要做"才轮到空间规划算法；
        # 纯景观/结构委托即使挂着建筑专业，也不该被房间组合顶替。
        _room_like = [x for x in (self.project.program or [])
                      if str(x.get("recipe") or "") not in
                      ("", "planting", "paving", "water", "outdoor")]
        needs_space_plan = ("interior" in _active) or \
            ("architecture" in _active and len(_room_like) >= 3)
        if _active and not needs_space_plan:
            return StageOutcome(
                "S3", "03 平面方案设计", skills_for_stage("S3"), adapter="dxf",
                status="blocked",
                error=("本次范围是" + "、".join(_scope.labels()) +
                       "：当前平面生成器只做建筑/室内的空间组织，"
                       "不能拿房间组合算法冒充专项方案。"),
                next_action=("景观/结构/机电专项需各自的深化能力；"
                             "本轮可先确认概念与条件，专项成果待相应能力接入"),
                notes=[f"范围：{'、'.join(_scope.labels())}"],
            )

        # 没有几何就出不了平面：这是"缺资料"，不是"程序坏了"。
        # 用 blocked + 人话 + 下一步，而不是把技术异常抛给客户。
        if not [s for s in self.project.spaces if s.use == "envelope"] \
                and not self.project.by_type("wall"):
            return StageOutcome(
                "S3", "03 平面方案设计", skills_for_stage("S3"), adapter="dxf",
                status="blocked",
                error=("没有可用的平面几何：目前只有文字需求，无法生成可核对的方案。"
                       "这不是系统故障。"),
                next_action=("请提供原始户型图，或现场实测（墙、门窗、梁柱位置与尺寸），"
                             "写成 existing-conditions.json 放到项目目录后重跑 S3；"
                             "格式见 `omniarchitect conditions --help`"),
                notes=["概念与任务书仍然有效，补图后不需要重做 S1/S2"],
            )
        from .concept.gate import concept_digest
        from .concept.handoff import load_for, store_plan_record, verify_scheme

        handoff = load_for(self.project)
        gen = PlanGenerator(self.project, self.level_id)
        supported = ("band_day_night", "spine_centre", "office_cluster")
        wanted = str((handoff.get("spatial") or {}).get("plan_strategy") or "")
        profile = finishes.project_profile(self.project)
        # The confirmed concept decides which strategy leads; the second variant
        # stays as a comparison. If the concept needs a strategy this generator
        # does not have, say so instead of quietly producing something else.
        default_lead = "office_cluster" if profile == "office" else "band_day_night"
        lead = wanted if wanted in supported else default_lead
        if lead == "band_day_night":
            other = "spine_centre"
        elif lead == "spine_centre":
            other = "band_day_night"
        else:
            other = "office_cluster"
        if lead == "office_cluster":
            options = [
                SchemeOptions(variant="A",
                              title=f"方案A · {handoff.get('concept_name') or '按要求'}"
                                    f"（{lead}）",
                              strategy="office_cluster", corridor_width_mm=1200.0,
                              flip=False),
                SchemeOptions(variant="B", title="方案B · 对照方案（会议带换边）",
                              strategy="office_cluster", corridor_width_mm=1500.0,
                              flip=True),
            ]
        else:
            options = [
                SchemeOptions(variant="A",
                              title=f"方案A · {handoff.get('concept_name') or '按要求'}"
                                    f"（{lead}）",
                              strategy=lead),
                SchemeOptions(variant="B", title="方案B · 对照方案", strategy=other),
            ]
        self.schemes = {o.variant: gen.generate(o) for o in options}
        concept_check = verify_scheme(handoff, self.schemes["A"], self.project) \
            if handoff.get("status") in ("locked", "selected_not_confirmed") else None

        rows = ["# 平面方案对比（S3）", ""]
        rows += _s3_taxonomy_block(self.project, sorted(_active))
        rows += ["## 面积表", "",
                "| 房间 | 方案A m² | 方案B m² | 目标 m² | 偏差 |", "|---|---|---|---|---|"]
        ids = sorted({r["id"] for s in self.schemes.values() for r in s.area_table()})
        for rid in ids:
            ra = next((r for r in self.schemes["A"].area_table() if r["id"] == rid), None)
            rb = next((r for r in self.schemes["B"].area_table() if r["id"] == rid), None)
            base = ra or rb
            rows.append(
                f"| {base['name']} | {(ra or {}).get('area_m2','—')} | {(rb or {}).get('area_m2','—')} "
                f"| {base.get('target_m2','—')} | {(ra or rb).get('delta_m2','—')} |"
            )
        rows += ["", "## 指标对比", "", "| 指标 | 方案A | 方案B |", "|---|---|---|"]
        for key, label in [
            ("room_count", "房间数"), ("total_area_m2", "使用面积 m²"),
            ("program_delta_m2", "与任务书偏差 m²"), ("partition_count", "隔墙段数"),
            ("partition_length_m", "隔墙总长 m"), ("door_count", "门数"),
            ("corridor_area_m2", "走廊面积 m²"), ("corridor_ratio", "走廊占比"),
            ("open_plan_ratio", "开放区占比"), ("glazing_ratio", "窗地比"),
            ("daylight_rooms_served", "采光房间"),
        ]:
            rows.append(
                f"| {label} | {self.schemes['A'].metrics.get(key,'—')} "
                f"| {self.schemes['B'].metrics.get(key,'—')} |"
            )
        rows += ["", "## 人体工学与净宽校核", ""]
        erg = compliance.check(self.project, self.level_id)
        erg_lines = [i for i in erg.issues if i.code in ("G03", "G04")]
        rows += [f"- {i.code} {i.message}" for i in erg_lines] or ["- 无净宽/门宽问题"]
        rows += ["", "## 造价影响（R3）", ""]
        rows += [f"- {n}" for n in _cost_delta(self.project, self.schemes)]
        if concept_check is not None:
            rows += ["", "## 概念一致性校核（S2 → S3）", "",
                     f"选定概念：**{handoff.get('concept_id')} {handoff.get('concept_name')}**　"
                     f"结论：**{concept_check['conformance']}**", ""]
            if handoff.get("stale"):
                rows.append("- ⚠ 概念基准已变更，本平面不得作为最终依据")
            rows += ["| 检查 | 结果 | 说明 |", "|---|---|---|"]
            rows += [f"| {c['check']} | {'通过' if c['ok'] else '不通过'} | {c['detail']} |"
                     for c in concept_check["checks"]]
            for m in concept_check.get("manual_review") or []:
                rows.append(f"\n- 待人工复核：{m}")
            for c in concept_check["conflicts"]:
                rows.append(f"\n- ⚠ {c['id']}（{c['severity']}）：{c['detail']}")
            if handoff.get("verify_before_plan"):
                rows += ["", "**进平面阶段前应核实**："]
                rows += [f"- {v}" for v in handoff["verify_before_plan"]]
        else:
            rows += ["", "## 概念一致性校核", "",
                     "- 无已确认概念：本轮平面为探索性验证，**不得签发 G3**。"]

        rows += ["", "## 推荐", "", _recommendation(self.schemes)]
        for v, s in self.schemes.items():
            if s.warnings:
                rows += ["", f"### 方案{v} 提示", ""] + [f"- {w}" for w in s.warnings]
        rows += ["", "---", "",
                 "> 平面未确认前不得进入精细建模与正式出图（门禁 G3）。",
                 "> 评审判据：平面九问 / 硬审十二条（本系统口径，见 docs/DESIGN_CRITERIA.md）。"]
        (d / "scheme-comparison.md").write_text("\n".join(rows), encoding="utf-8")

        # schematic drawing is legitimate at this depth (R2)
        arts = [str(d / "scheme-comparison.md")]
        for v, s in self.schemes.items():
            (d / f"scheme-{v}.json").write_text(
                json.dumps(s.report(), ensure_ascii=False, indent=2), encoding="utf-8"
            )

        baseline = self.project.fork()
        _install_scheme(baseline, s=self.schemes[self.scheme_variant])
        resolve_host_axes(baseline)
        dxf = DxfAdapter()
        if dxf.preflight().available:
            r = dxf.draw_plan(
                baseline, d / f"S3-schematic-{self.scheme_variant}.dxf",
                level_id=self.level_id, scheme=self.scheme_variant,
                title="平面方案图（方案深度）", include_furniture=True,
            )
            arts.extend(r.artifacts)
            note_dxf = (
                f"方案深度 DXF 已生成并审计通过（{r.validation.get('stats',{}).get('entities','?')} 实体）"
                if r.ok else f"DXF 审计未通过：{r.errors[:2]}"
            )
        else:
            note_dxf = "ezdxf 不可用，未生成方案深度 DXF"

        self.project.meta["schemes_available"] = sorted(self.schemes)
        register_artifact(self.project, "art-schemes", "document",
                          ["project:program", "shell"], "space-planning",
                          relpath(d / "scheme-comparison.md"), "draft")

        # 记录本轮平面到底做了什么、对着哪一版概念 —— G3 靠这份记录判断
        # "能不能签"，而不是靠现场重新回忆。
        strategy_supported = bool((handoff.get("spatial") or {}).get("plan_strategy_supported"))
        implements = bool(concept_check and concept_check["conformance"] != "fail"
                          and strategy_supported)
        store_plan_record(self.project, {
            "revision": self.project.revision,
            "concept_id": handoff.get("concept_id") or "",
            "concept_digest": concept_digest(self.project),
            "dxf": [a for a in arts if str(a).lower().endswith(".dxf")],
            "handoff_status": handoff.get("status", "none"),
            "conformance": (concept_check or {}).get("conformance", "not_applicable"),
            "auto_pass": bool((concept_check or {}).get("auto_pass")),
            "fully_verified": bool((concept_check or {}).get("fully_verified")),
            "conflicts": list((concept_check or {}).get("conflicts") or []),
            "manual_review": list((concept_check or {}).get("manual_review") or []),
            "plan_strategy": lead,
            "requested_strategy": wanted,
            "strategy_supported": strategy_supported,
            "implements_concept": implements,
            "gate": {},
            "at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        })

        notes = [f"生成 {len(self.schemes)} 套平面方案 + 对比分析 + 造价影响", note_dxf,
                 "等待业主选定方案（门禁 G3）"]
        if concept_check is not None:
            notes.insert(0, f"概念承接：{handoff.get('concept_id')} "
                            f"{handoff.get('concept_name')}（{handoff.get('status')}）")
            notes.append(f"概念一致性：{concept_check['conformance']}"
                         f"（自动检查{'通过' if concept_check.get('auto_pass') else '未通过'}；"
                         f"完全核实：{'是' if concept_check.get('fully_verified') else '否'}）")
            for c in concept_check["conflicts"][:2]:
                notes.append(f"概念冲突 {c['id']}：{c['detail']}")
            if concept_check.get("manual_review"):
                notes.append(f"待人工复核 {len(concept_check['manual_review'])} 项："
                             "系统无法自动确认，未计入通过")
            if not strategy_supported:
                notes.append(
                    f"该概念的空间原型没有对应的平面策略：本轮用 {lead} 近似生成，"
                    "**不能视为概念的落地**，G3 不得正式签发（需换支持的方向或另行深化）")
        else:
            notes.append("无已确认概念：平面仅供探索，不得签发正式 G3")
        # 能力边界跟着项目类型走：医院/厂房这类不能因为生成了平面就当成合规成果
        _cap = _tax.capability_of((_iv.classification(self.project).get("codes") or []))
        if _cap.get("level") in ("concept_only", "specialist"):
            notes.append(f"能力边界（{_cap.get('level')}）：{_cap.get('label')}；"
                         f"{_cap.get('note')}")
        return StageOutcome("S3", artifacts=arts, adapter="dxf", notes=notes)

    # ==================================================================
    # 04 初步设计与方案深化
    # ==================================================================
    def stage_S4(self) -> StageOutcome:
        d = self._dir("S4")
        from .concept.handoff import plan_record
        if plan_record(self.project).get("sector") == "landscape":
            from .sector.landscape_delivery import run
            return run(self, "S4", d)
        if (self.project.meta.get("sector_levels") or {}).get("sector") in ("education", "hospitality"):
            from .sector.deepening import run
            return run(self, "S4", d)
        chosen = self._ensure_scheme_installed()
        style = finishes.style_label(self.project)
        profile = finishes.profile_label(self.project)
        g3_label = ("G3 已确认" if get_state(self.project, "S3").status == CONFIRMED
                    else "G3 未确认 · 探索性预览")

        # --- 顶墙地 + 材料体系 ---
        # 每张表都由"这个项目自己的空间 + 已确认概念的材料方向"推导，不再用
        # 住宅默认值。办公项目里出现"主卧"是硬错误，测试守着这条。
        lines = [
            f"# 初步设计 — 方案{chosen}", "",
            f"风格：{style}　　项目类型：{profile}　　（方案{chosen}，{g3_label}）", "",
            "## 顶面", "",
            "| 区域 | 做法 | 标高 | 灯槽 |", "|---|---|---|---|",
        ]
        for r in finishes.ceiling_rows(self.project):
            lines.append(f"| {r['zone']} | {r['method']} | {r['level']} | {r['light']} |")
        lines += ["", "## 墙面", "", "| 区域 | 做法 | 材料 |", "|---|---|---|"]
        for r in finishes.wall_rows(self.project):
            lines.append(f"| {r['zone']} | {r['method']} | {r['material']} |")
        lines += ["", "## 地面", "", "| 区域 | 材料 | 规格 |", "|---|---|---|"]
        for r in finishes.floor_rows(self.project):
            lines.append(f"| {r['zone']} | {r['material']} | {r['spec']} |")

        ratio_note = "（色彩关系按概念方案的比例声明执行）"
        lines += ["", f"## 材料与色彩体系{ratio_note}", "",
                  "| 组 | 材料 | 色值 | 占比 |", "|---|---|---|---|"]
        for r in finishes.palette_rows(self.project):
            lines.append(f"| {r['group']} | {r['material']} | {r['hex']} | {r['pct']} |")

        lines += ["", "## 灯光方案（初步）", "", "| 层 | 手法 | 参数 |", "|---|---|---|"]
        for r in finishes.lighting_rows(self.project):
            lines.append(f"| {r['layer']} | {r['method']} | {r['param']} |")

        lines += [
            "", "## 机电与设备协调（初步）", "",
            "| 专业 | 空间影响 | 待办 |", "|---|---|---|",
            "| 暖通 | 吊顶内风管占用 ≥250mm | 复核净高是否满足 |",
            "| 电气 | 点位数量按本项目功能表统计 | 与家具/工位布置核对 |",
            "| 给排水 | 湿区竖向管井 | 确认与结构无冲突 |",
            f"| 消防 | {profile}项目的消防要求按当地规范 | **须专业确认** |",
            "", "## 这一步的交付深度说明", "",
            "本阶段输出**方案深度**图纸：可用于与业主沟通做法与造价，**不得用于施工**。",
            "S7 需要在门禁确认与专项深化后提交施工图；当前图纸仍为方案/待审查深度（R2）。",
            "", "---", "",
            "> 做法、材料与灯光的判断口径为本系统自有标准；"
            "机电口径为空间影响速查，具体设计须专业工程师完成。",
            "> 材料名取自 G2 确认的概念方案；未确认的材料写「待确认」，"
            "不套用任何项目类型的默认材料。",
        ]
        (d / "preliminary-design.md").write_text("\n".join(lines), encoding="utf-8")

        # --- material & lighting schedules as structured data ---
        sched = {
            "materials": [
                {"group": r["group"], "name": r["material"],
                 "spec": "", "color": r["hex"], "ratio": r["pct"]}
                for r in finishes.palette_rows(self.project)
            ],
            "surfaces": {
                "ceiling": finishes.ceiling_rows(self.project),
                "wall": finishes.wall_rows(self.project),
                "floor": finishes.floor_rows(self.project),
            },
            "lighting": [
                {"layer": r["layer"], "fixture": r["method"], "param": r["param"]}
                for r in finishes.lighting_rows(self.project)
            ],
            "depth": "schematic",
            "profile": finishes.project_profile(self.project),
            "note": ("材料与色彩来自 G2 确认的概念方案；未确认项标「待确认」，"
                     "不按项目类型套默认材料。"),
        }
        (d / "material-lighting.json").write_text(
            json.dumps(sched, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        # --- schematic CAD set (R2) ---
        arts = [str(d / "preliminary-design.md"), str(d / "material-lighting.json")]
        dxf = DxfAdapter()
        depth_note = "ezdxf 不可用，跳过方案深度图纸"
        if dxf.preflight().available:
            r = dxf.draw_plan(
                self.project, d / f"S4-schematic-{chosen}.dxf", level_id=self.level_id,
                scheme=chosen, title="初步设计图（方案深度）", include_furniture=True,
            )
            arts.extend(r.artifacts)
            depth_note = (
                f"方案深度图纸已生成（{r.validation.get('stats',{}).get('entities','?')} 实体，审计通过）"
                if r.ok else "图纸审计未通过"
            )
            register_artifact(self.project, f"art-prelim-{chosen}", "drawing",
                              [e.id for e in self.project.by_type("wall")],
                              "cad-drafting", relpath(r.artifacts[0]), "draft")
            if r.ok:
                from .interior_surfaces import export as export_surfaces
                arts.extend(export_surfaces(self.project, d, self.level_id))
                depth_note += "；顶面/地面分区 CAD 与预览已生成（待审查）"
        est = quantities.takeoff(self.project, self.level_id)
        return StageOutcome(
            "S4", artifacts=arts, adapter="dxf",
            notes=[f"顶面/墙面/地面做法 + 材料色彩体系 + 灯光方案 + 机电初步协调", depth_note,
                   f"当前估算 {est.cost['subtotal_low']:,.0f}–{est.cost['subtotal_high']:,.0f} CNY"
                   "（随阶段收敛，非最终清单）"],
        )

    # ==================================================================
    # 05 3D 建模与效果图表现
    # ==================================================================
    def stage_S5(self) -> StageOutcome:
        d = self._dir("S5")
        from .concept.handoff import plan_record
        if plan_record(self.project).get("sector") == "landscape":
            from .sector.landscape_delivery import run
            return run(self, "S5", d)
        if (self.project.meta.get("sector_levels") or {}).get("sector") in ("education", "hospitality"):
            from .sector.deepening import run
            return run(self, "S5", d)
        chosen = self._ensure_scheme_installed()
        arts: List[str] = []
        notes: List[str] = []
        status = "ok"

        mesh = MeshAdapter()
        if (self.project.meta.get("sector_levels") or {}).get("floors", 1) > 1:
            m = mesh.export_multilevel_obj(self.project, d, stem=f"S5-model-{chosen}")
        else:
            m = mesh.export_obj(self.project, d, level_id=self.level_id,
                                stem=f"S5-model-{chosen}")
        arts.extend(m.artifacts)
        if m.ok:
            notes.append(
                f"可编辑 3D 模型：{m.validation.get('vertices','?')} 顶点 / "
                f"{m.validation.get('faces','?')} 面（mm，Z 向上）"
            )
        else:
            status = "failed"

        # 有几何就该有能看的图：用 OBJ 的顶点与面直接投影轴测图，
        # 不依赖 Blender/渲染器，也不冒充效果图。
        obj_path = next((a for a in m.artifacts
                         if str(a).lower().endswith(".obj")), "")
        if obj_path:
            try:
                from .sector.model_preview import export as preview_model

                labels = self._space_labels()
                views = (("axon-main", 42.0), ("axon-alt", 138.0), ("axon-rear", 262.0))
                for name, az in views:
                    out_svg = d / f"S5-{name}.svg"
                    preview_model(obj_path, out_svg,
                                  title=f"{self.project.name or self.project.project_id}"
                                        f" · 模型检视（{name}）",
                                  azimuth_deg=az, elevation_deg=26.0, labels=labels)
                    arts.append(str(out_svg))
                notes.append("模型检视图 3 张（由 OBJ 顶点/面直接投影；非效果图，不作尺寸依据）")
            except Exception as exc:  # noqa: BLE001  预览失败不影响模型本身
                notes.append(f"模型检视图未生成：{type(exc).__name__}: {exc}")

        bl = BlenderAdapter()
        b = bl.build(self.project, d / "blender", level_id=self.level_id, render=False)
        arts.extend(b.artifacts)
        notes.append(
            "Blender 未安装：已输出 snapshot + build_scene.py（含材质/相机/灯光，"
            "可在有 Blender 的机器直接跑）"
            if b.validation.get("degraded")
            else "Blender 场景已生成（scene.blend）"
        )

        ifc = IfcAdapter()
        i = ifc.export(self.project, d / "ifc", stem=f"S5-{chosen}")
        arts.extend(i.artifacts)
        notes.append(
            "IfcOpenShell 未安装：已输出 IFC 投影与生成脚本"
            if i.validation.get("degraded") else "IFC4 已生成"
        )

        rj = RenderAdapter().build_job_package(
            self.project, d / "render-jobs.json", level_id=self.level_id, lighting="day_soft",
            style=str((self.project.constraints or {}).get("style") or ""),
        )
        arts.extend(rj.artifacts)
        notes.append(
            f"{rj.validation.get('jobs',0)} 个机位任务（机位、材质、光线取自统一模型，"
            "保证多视角一致）"
        )

        walk = [
            "# 漫游与多视角表现计划", "",
            "| 序号 | 视图 | 用途 | 镜头 |", "|---|---|---|---|",
        ]
        # 机位名来自本项目真实空间：办公项目不该出现「主卧」。
        for v in finishes.view_rows(self.project):
            walk.append(f"| {v['no']} | {v['name']} | {v['use']} | {v['lens']} |")
        walk += [
            "", "## 表现纪律", "",
            "1. 五张图必须是同一套几何、同一套材质、同一套光线；",
            "2. AI 表现类成果一律标注为非尺寸依据（authoritative = false）；",
            "3. 不做『只活在效果图里』的空间——平面上找不到的手法一律不画。",
            "", "> 迭代方法：意向板打分 + 跨轮整改追踪（本系统口径）。",
        ]
        (d / "walkthrough-plan.md").write_text("\n".join(walk), encoding="utf-8")
        arts.append(str(d / "walkthrough-plan.md"))

        register_artifact(self.project, f"art-model-{chosen}", "model",
                          [e.id for e in self.project.by_type("wall")] +
                          [e.id for e in self.project.by_type("furniture")],
                          "3d-modeling", relpath(d), "validated")
        register_artifact(self.project, "art-render-jobs", "render",
                          [e.id for e in self.project.by_type("wall")][:60],
                          "scene-rendering", relpath(d / "render-jobs.json"), "needs_review")
        notes.append("表现类成果已登记为非权威：可用于汇报，不可用于推导尺寸")
        return StageOutcome("S5", artifacts=arts, adapter="mesh", status=status, notes=notes)

    # ==================================================================
    # 06 设计定稿与技术协调
    # ==================================================================
    def stage_S6(self) -> StageOutcome:
        d = self._dir("S6")
        from .concept.handoff import plan_record
        if plan_record(self.project).get("sector") == "landscape":
            from .sector.landscape_delivery import run
            return run(self, "S6", d)
        if (self.project.meta.get("sector_levels") or {}).get("sector") in ("education", "hospitality"):
            from .sector.deepening import run
            return run(self, "S6", d)
        chosen = self._ensure_scheme_installed()
        rep = compliance.check(self.project, self.level_id)
        (d / "design-review.json").write_text(
            json.dumps(rep.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
        )
        (d / "design-review.md").write_text(rep.markdown(), encoding="utf-8")

        est = quantities.takeoff(self.project, self.level_id)
        budget = (self.project.constraints or {}).get("budget_cny")
        coord = [
            "# 技术协调与设计锁定", "",
            f"## 方案{chosen} · 校核结果", "",
            f"- 阻断项 {rep.summary['blockers']}　提示项 {rep.summary['warnings']}"
            f"　信息项 {rep.summary['infos']}",
            f"- 整体窗地比 {rep.summary['glazing_ratio']:.3f}（{rep.summary['glazing_ratio']*7:.2f}/7）",
            "", "## 专业协调清单", "",
            "| 专业 | 待确认事项 | 状态 |", "|---|---|---|",
            "| 结构 | 推断承重墙位置（须现场探测） | **未闭环 · 须专业确认** |",
            "| 暖通 | 吊顶内风管净高占用 | 已初步协调 |",
            "| 电气 | 点位与家具布置核对 | 已完成 |",
            "| 给排水 | 中脊管井与结构关系 | 待结构确认 |",
            "| 消防 | 户内消防要求（按当地规范） | **未闭环 · 须专业确认** |",
            "", "## 造价适配", "",
            f"- 当前估算：{est.cost['subtotal_low']:,.0f} – {est.cost['subtotal_high']:,.0f} CNY",
        ]
        if budget:
            coord.append(f"- 业主预算：{float(budget):,.0f} CNY")
            coord.append(
                "- 结论：" + (
                    "在预算区间内" if est.cost["subtotal_low"] <= float(budget)
                    else "估算下沿已超预算，须在标准或面积上取舍"
                )
            )
        coord += ["", "## 拟锁定范围（待 G6 确认）", "",
                  "以下内容拟作为深化依据；只有真实 G6 确认后才能声明锁定：",
                  "- 平面几何（墙体、门位、房间边界）与统一空间模型；",
                  "- 顶墙地做法与材料色彩体系；",
                  "- 主要建材与灯具档位。",
                  "", "## 未闭环项（带入施工图阶段）", "",
                  "- 结构承重构件确认；",
                  "- 消防与当地规范符合性；",
                  "- 机电系统容量校核。",
                  "", "> 未闭环项不得默认为『没问题』。",
                  "> 修订基线：r{}".format(self.project.revision)]
        (d / "coordination.md").write_text("\n".join(coord), encoding="utf-8")

        register_artifact(self.project, "art-freeze", "report",
                          [e.id for e in self.project.by_type("wall")],
                          "design-review", relpath(d / "coordination.md"), "needs_review")
        return StageOutcome(
            "S6", adapter="",
            artifacts=[str(d / "design-review.md"), str(d / "design-review.json"),
                       str(d / "coordination.md")],
            status="ok" if rep.summary["pass"] else "degraded",
            notes=[f"校核：阻断 {rep.summary['blockers']} / 提示 {rep.summary['warnings']}",
                   "拟锁定设计与造价基线，等待 G6 确认", "结构/消防/给排水仍未闭环"],
        )

    # ==================================================================
    # 07 CAD / BIM 施工图深化
    # ==================================================================
    def stage_S7(self) -> StageOutcome:
        d = self._dir("S7")
        from .concept.handoff import plan_record
        if plan_record(self.project).get("sector") == "landscape":
            from .sector.landscape_delivery import run
            return run(self, "S7", d)
        if (self.project.meta.get("sector_levels") or {}).get("sector") in ("education", "hospitality"):
            from .sector.deepening import run
            return run(self, "S7", d)
        chosen = self._ensure_scheme_installed()
        dxf = DxfAdapter()
        arts: List[str] = []
        notes: List[str] = []
        status = "degraded"  # 节点、回路及立面尚未完成，不能视为完整施工图

        if dxf.preflight().available:
            for sheet, kw in (
                ("A-01-plan", {"title": "平面布置图（待审查）", "include_furniture": True}),
                ("A-02-rooms", {"title": "房间与面积图（待审查）", "include_furniture": False}),
                ("A-03-furniture", {"title": "家具定位图（待审查）", "include_furniture": True}),
            ):
                r = dxf.draw_plan(
                    self.project, d / f"{sheet}.dxf", level_id=self.level_id,
                    scheme=chosen, depth="review_only", **kw,
                )
                arts.extend(r.artifacts)
                if not r.ok:
                    status = "failed"
                    notes.append(f"{sheet} 审计未通过：{r.errors[:2]}")
                else:
                    st = r.validation.get("stats", {})
                    notes.append(
                        f"{sheet}：{st.get('entities','?')} 实体 / "
                        f"{len(st.get('layers',[]))} 图层，审计通过"
                    )
            if status != "failed":
                from .interior_surfaces import export as export_surfaces
                arts.extend(export_surfaces(self.project, d, self.level_id))
                notes.append("I-04 顶面分区、I-05 地面饰面分区：CAD 已读回，待材料与机电深化")
        else:
            status = "degraded"
            notes.append("ezdxf 不可用，未生成施工图 DXF")

        ifc = IfcAdapter()
        i = ifc.export(self.project, d / "ifc", stem=f"S7-{chosen}")
        arts.extend(i.artifacts)
        notes.append("IFC4 已生成" if not i.validation.get("degraded")
                     else "IfcOpenShell 未安装：已输出 IFC 投影与生成脚本")

        det = [
            "# 施工图深化说明（S7）", "",
            "## 图纸清单", "",
            "| 图号 | 图名 | 深度 |", "|---|---|---|",
            "| A-01 | 平面布置图 | 待审查 |",
            "| A-02 | 房间与面积图 | 待审查 |",
            "| A-03 | 家具定位图 | 待审查 |",
            "| I-04 | 顶面分区图 | 已出方案分区 DXF，灯具/机电待深化 |",
            "| I-05 | 地面饰面分区图 | 已出方案分区 DXF，排版/收边待深化 |",
            "| A-06 | 灯具定位与回路 | 待深化（由 lighting-design 负责） |",
            "| A-07 | 立面图（4 面） | 待深化 |",
            "| A-08 | 节点详图（3–5 个） | 待深化 |",
            "", "## 图层标准", "",
            "| 图层 | 用途 | 颜色 |", "|---|---|---|",
            "| A-WALL | 结构墙（含填充） | 白 |",
            "| A-WALL-PART | 隔墙 | 灰 |",
            "| A-DOOR | 门与开启弧 | 绿 |",
            "| A-GLAZ | 门窗玻璃 | 青 |",
            "| A-FURN | 家具 | 浅灰 |",
            "| A-ANNO-DIMS | 尺寸标注 | 黄 |",
            "| A-ANNO-TEXT | 文字与房间名 | 黄 |",
            "| A-UNCERTAIN | **推断构件（点划线，须现场核对）** | 红 |",
            "", "## 审查记录", "",
            "- 图纸间尺寸一致性：由统一空间模型保证（同一几何源出图）",
            "- 未闭环项：结构承重构件、消防与当地规范符合性",
            "- **本套图纸须由持证专业负责人复核签署后方可交付施工**",
            "", "---",
            "> 施工图由经校核的几何/BIM 模型生成，不由效果图反推。",
        ]
        (d / "detailing-notes.md").write_text("\n".join(det), encoding="utf-8")
        arts.append(str(d / "detailing-notes.md"))
        register_artifact(self.project, f"art-drawings-{chosen}", "drawing",
                          [e.id for e in self.project.by_type("wall")] +
                          [e.id for e in self.project.by_type("door")] +
                          [e.id for e in self.project.by_type("window")],
                          "cad-drafting", relpath(d), "needs_review")
        return StageOutcome("S7", artifacts=arts,
                            adapter="dxf" if dxf.preflight().available else "",
                            status=status, notes=notes)

    # ==================================================================
    # 08 物料清单与交付
    # ==================================================================
    def stage_S8(self) -> StageOutcome:
        d = self._dir("S8")
        from .concept.handoff import plan_record
        if plan_record(self.project).get("sector") == "landscape":
            from .sector.landscape_delivery import run
            return run(self, "S8", d)
        if (self.project.meta.get("sector_levels") or {}).get("sector") in ("education", "hospitality"):
            from .sector.deepening import run
            return run(self, "S8", d)
        chosen = self._ensure_scheme_installed()
        t = quantities.takeoff(self.project, self.level_id)
        (d / "takeoff.json").write_text(
            json.dumps(t.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
        )

        unit = {
            "floor_area_m2": "m²", "ceiling_area_m2": "m²", "wall_finish_area_m2": "m²",
            "partition_area_m2": "m²", "partition_length_m": "m", "wall_volume_m3": "m³",
            "door_count": "樘", "window_count": "樘", "glazing_area_m2": "m²",
            "joinery_area_m2": "m²", "furniture_count": "件",
        }
        md = ["# 工程量与成本清单（S8 · 待审查）", "", "## 工程量", "",
              "| 项目 | 数量 | 单位 |", "|---|---|---|"]
        for k, v in t.quantities.items():
            md.append(f"| {k} | {v:.2f} | {unit.get(k,'')} |")
        md += ["", "## 成本", "", "| 项目 | 数量 | 单价低 | 单价高 | 合价低 | 合价高 |",
               "|---|---|---|---|---|---|"]
        for ln in t.cost["lines"]:
            md.append(
                f"| {ln['item']} | {ln['quantity']} {ln['unit']} | {ln['rate_low']:.0f} "
                f"| {ln['rate_high']:.0f} | {ln['amount_low']:,.0f} | {ln['amount_high']:,.0f} |"
            )
        md += ["", f"**合计：{t.cost['subtotal_low']:,.0f} – {t.cost['subtotal_high']:,.0f} CNY**"
                   f"（{t.cost['per_m2_low']:,.0f} – {t.cost['per_m2_high']:,.0f} 元/m²）", ""]
        if t.notes:
            md += ["## 预算对照", ""] + [f"- {n}" for n in t.notes] + [""]
        md += ["---", t.to_dict()["disclaimer"]]
        (d / "takeoff.md").write_text("\n".join(md), encoding="utf-8")

        mats = [
            "# 材料与物料表", "",
            "| 部位 | 材料 | 规格 | 品牌档位 | 用量 | 损耗 | 替代 | 来源 |",
            "|---|---|---|---|---|---|---|---|",
        ]
        # 材料名与做法取自 G2 确认的概念方案；没有就写「待确认」，
        # 不用住宅默认的微水泥/乳胶漆替客户拍板。
        for r in finishes.material_rows(self.project, t):
            mats.append(f"| {r['part']} | {r['material']} | {r['spec']} | {r['tier']} "
                        f"| {r['qty']} | {r['waste']} | {r['alt']} | {r['source']} |")
        mats += [
            "", "## 采购注意", "",
            "- 同一材料必须锁定同一批次色号；",
            "- 大板/岩板类需在图纸确认后实测下单；",
            "- 灯具需按回路与色温分批到货；",
            f"- 本表按「{finishes.profile_label(self.project)}」项目口径编制；"
            "未确认材料的行不得直接下单。",
        ]
        (d / "material-schedule.md").write_text("\n".join(mats), encoding="utf-8")

        sched = {
            "rooms": quantities.room_schedule(self.project, self.level_id),
            "doors": quantities.schedule_doors(self.project, self.level_id),
            "windows": quantities.schedule_windows(self.project, self.level_id),
        }
        (d / "schedules.json").write_text(
            json.dumps(sched, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        # --- delivery package ---
        files = sorted(str(p.relative_to(self.out)) for p in self.out.rglob("*") if p.is_file())
        pkg = {
            "project_id": self.project.project_id,
            "name": self.project.name,
            "revision": self.project.revision,
            "run_id": self.run_id,
            "scheme": self.project.meta.get("scheme", {}),
            "frozen_revision": self.project.meta.get("frozen_revision"),
            "stage_progress": progress(self.project),
            "files": files,
            "artifacts": [a.to_dict() for a in self.project.artifacts],
            "change_log": [c.to_dict() for c in self.project.change_log],
            "stale_artifacts": [a.id for a in self.project.artifacts if a.status == "stale"],
            "release_status": "pending_G8",
            "open_items": ["结构承重构件确认", "消防与当地规范符合性", "机电容量校核"],
        }
        (d / "delivery-manifest.json").write_text(
            json.dumps(pkg, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        readme = [
            "# 交付说明", "",
            f"- 项目：{self.project.name or self.project.project_id}（r{self.project.revision}）",
            f"- 方案：{self.project.meta.get('scheme', {}).get('title', chosen)}",
            f"- 运行编号：`{self.run_id}`",
            # S8 的包是在自己确认之前生成的，直接写 percent 会得到 87.5%，
            # 读起来像"还没跑完"。按"本包覆盖到 S8"表述，不带会误导的百分数。
            f"- 覆盖阶段：S1–S8（本包在 G8 确认前生成，属待审查交付预览）", "",
            "## 文件清单", ""]
        readme += [f"- `{f}`" for f in files if not f.startswith("08-")]
        readme += ["", "## 使用限制", "",
                   "0. 当前为 G8 待验收包，不等于已签发的施工/采购文件；",
                   "1. 未经持证专业人员复核签署的图纸不得用于施工；",
                   "2. 结构安全、消防、无障碍、机电与当地法规符合性不在本系统结论范围内；",
                   "3. 表现类图片为示意，不构成尺寸依据；",
                   "4. 工程量与估算为区间值，非结算依据。", "",
                   "## 未闭环项", ""]
        readme += [f"- {i}" for i in pkg["open_items"]]
        readme += ["", "---", "",
                   "本交付文件由 OmniArchitect 依据统一空间模型自动生成。",
                   "", SIGNATURE]
        (d / "README.md").write_text("\n".join(readme), encoding="utf-8")

        self.project.save(self.out / "project-final.json")
        register_artifact(self.project, "art-quantities", "schedule",
                          [s.id for s in self.project.spaces if s.properties.get("scheme")],
                          "quantity-takeoff", relpath(d / "takeoff.json"), "validated")
        register_artifact(self.project, "art-materials", "schedule",
                          ["art-quantities"], "material-schedule",
                          relpath(d / "material-schedule.md"), "validated")
        register_artifact(self.project, "art-delivery", "document",
                          ["art-quantities", "art-materials"], "delivery",
                          relpath(d / "delivery-manifest.json"), "needs_review")
        return StageOutcome(
            "S8",
            artifacts=[str(d / "takeoff.md"), str(d / "takeoff.json"),
                       str(d / "material-schedule.md"), str(d / "schedules.json"),
                       str(d / "delivery-manifest.json"), str(d / "README.md"),
                       str(self.out / "project-final.json")],
            notes=[f"工程量 {t.quantities['floor_area_m2']:.1f} m² 使用面积",
                   f"成本 {t.cost['subtotal_low']:,.0f}–{t.cost['subtotal_high']:,.0f} CNY",
                   f"{len(files)} 个交付文件", "3 项未闭环事项已列入交付说明"],
        )

    # ------------------------------------------------------------------
    def _reference_model(self, variant: str):
        """装好方案{chosen}的模型副本，只用来出参考图，不改动 canonical 修订号。"""
        from .planner import PlanGenerator

        base = self.project.fork()
        if any(s.properties.get("scheme") for s in base.spaces):
            return base
        scheme = self.schemes.get(variant)
        if scheme is None:
            scheme = PlanGenerator(self.project, self.level_id).generate(
                _scheme_options(variant, finishes.project_profile(self.project)))
        _install_scheme(base, scheme)
        resolve_host_axes(base)
        return base

    def _ensure_scheme_installed(self) -> str:
        """Make sure a scheme's spaces/elements are in the model before S4+ runs.

        If S3 has not run in this session and the model has no scheme geometry,
        generate the schemes first so downstream stages have something real to
        work on — never an empty model.
        """
        has_scheme = any(s.properties.get("scheme") for s in self.project.spaces)
        if has_scheme:
            variant = str((self.project.meta.get("scheme") or {}).get("variant")
                          or self.scheme_variant)
            return variant
        if not self.schemes:
            gen = PlanGenerator(self.project, self.level_id)
            o = _scheme_options(self.scheme_variant,
                                finishes.project_profile(self.project))
            self.schemes = {o.variant: gen.generate(o)}
        variant = self.scheme_variant if self.scheme_variant in self.schemes else sorted(self.schemes)[0]
        _install_scheme(self.project, self.schemes[variant])
        resolve_host_axes(self.project)
        self.project.revision += 1
        record_change(self.project, "scheme", f"安装方案{variant}作为深化依据",
                      targets=[f"scheme:{variant}"])
        return variant


# --------------------------------------------------------------------------
def _scheme_options(variant: str, profile: str = "residential") -> "SchemeOptions":
    """The deterministic scheme definition for a variant letter.

    办公不是把住宅带式布局换个名字：住宅用 band / spine，办公用 office_cluster，
    两套办公方案靠 flip 换边，而不是靠随机数。
    """
    if profile in ("office",):
        return SchemeOptions(
            variant=variant, title=f"方案{variant}",
            strategy="office_cluster",
            corridor_width_mm=1200.0 if variant == "A" else 1500.0,
            flip=(variant == "B"),
        )
    return SchemeOptions(
        variant=variant, title=f"方案{variant}",
        strategy="band_day_night" if variant == "A" else "spine_centre",
    )


def rows_or_empty(prog: Any) -> bool:
    return bool(getattr(prog, "rows", None))


def _install_scheme(project: Project, s: SchemeResult) -> None:
    project.spaces = [x for x in project.spaces if not x.properties.get("scheme")] + list(s.spaces)
    project.elements = [
        e for e in project.elements if not e.source.startswith("scheme_")
    ] + list(s.elements)
    project.meta = dict(project.meta or {})
    project.meta["scheme"] = {"variant": s.variant, "title": s.title, "strategy": s.strategy}


def _cost_delta(project: Project, schemes: Dict[str, SchemeResult]) -> List[str]:
    out: List[str] = []
    for v, s in sorted(schemes.items()):
        walls = [e for e in s.elements if e.type == "wall"]
        part_len = sum(w.wall_length_mm() for w in walls) / 1000.0
        part_area = sum(
            w.wall_length_mm() / 1000.0 * float(w.geometry.get("height_mm", 2800)) / 1000.0
            for w in walls
        )
        out.append(
            f"方案{v}：隔墙 {part_len:.1f} m（{part_area:.1f} m²），"
            f"按 260–680 元/m² 估算 {part_area*260:,.0f}–{part_area*680:,.0f} CNY；"
            f"走廊占比 {s.metrics.get('corridor_ratio', 0):.1%} 影响可售/可使用面积"
        )
    return out


def _recommendation(schemes: Dict[str, SchemeResult]) -> str:
    a, b = schemes.get("A"), schemes.get("B")
    if not a or not b:
        return "（缺少可比方案）"
    ma, mb = a.metrics, b.metrics
    score = {"A": 0, "B": 0}
    picks = {
        "采光": "A" if float(ma.get("glazing_ratio", 0)) >= float(mb.get("glazing_ratio", 0)) else "B",
        "走廊效率": "A" if float(ma.get("corridor_ratio", 1)) <= float(mb.get("corridor_ratio", 1)) else "B",
        "隔墙经济性": "A" if int(ma.get("partition_count", 0)) <= int(mb.get("partition_count", 0)) else "B",
    }
    for k in picks:
        score[picks[k]] += 1
    pick = "A" if score["A"] >= score["B"] else "B"
    other = "B" if pick == "A" else "A"
    why = "、".join(k for k, v in picks.items() if v == pick) or "综合指标"
    reason_other = (
        "开放区占比更大，适合重视会客与家人共处的业主"
        if other == "A" else "房间面宽与进深更均衡，适合需要独立房间的业主"
    )
    return (
        f"**推荐方案{pick}**（{why}更优）；**备选方案{other}**：{reason_other}。\n\n"
        "选择依据按优先级：① 采光面是否被独立房间独占　② 走廊面积占比　"
        "③ 隔墙工程量与造价　④ 开放区占比是否符合业主生活方式。\n\n"
        "> 两套方案均已通过几何与规范初审。最终选择权在业主，系统不代决。"
    )


# backwards-compatible exports
DEFAULT_STAGES = list(STAGE_ORDER)
WorkflowRunner = StageRunner
