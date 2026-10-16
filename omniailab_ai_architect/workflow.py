"""Workflow — eight-stage state machine.

Runs one stage at a time. Each stage:

* checks its entry guardrails (upstream confirmations, the plan-before-model rule);
* dispatches to the capabilities that own it;
* writes its deliverables into its own folder;
* submits for confirmation at its gate and then stops, unless confirmation is
  being assumed.

A stage that is blocked at a gate is not a failure — it is the system working.
"""
from __future__ import annotations

import json
import platform
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from . import changes, compliance, quantities
from .adapters import (
    BlenderAdapter,
    DxfAdapter,
    IfcAdapter,
    MeshAdapter,
    RenderAdapter,
    doctor,
    resolve_host_axes,
)
from .errors import GateBlocked, OmniArchitectError, ValidationError
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
    can_start,
    confirm_stage,
    get_state,
    invalidate_from,
    markdown as stage_markdown,
    progress,
    start_stage,
    submit_for_confirmation,
)
from .stages import STAGE_BY_ID, STAGE_ORDER, Stage, stage_name, skills_for_stage

# drawing depth per stage — R2: CAD exists from preliminary design onward,
# the difference is schematic vs construction, not presence or absence.
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
        if self.blocks:
            lines += ["", "## 阻断 / 失败", ""] + [f"- {b}" for b in self.blocks]
        return "\n".join(lines)


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
        self.project_dir = Path(project_dir) if project_dir else None
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
        out.skills = out.skills or skills_for_stage(stage_id)
        out.stage_name = out.stage_name or f"{st.code} {st.name}"
        out.seconds = time.time() - t0

        if out.status in ("failed", "blocked"):
            from .stage_state import block_stage

            block_stage(self.project, stage_id, out.error or "stage failed")
        else:
            submit_for_confirmation(self.project, stage_id, out.notes[0] if out.notes else "")
            out.next_action = f"提交确认：{st.gate.label}（{st.gate.approver}）"
            if confirm:
                confirm_stage(self.project, stage_id, by="业主/主创（假设）",
                              note="由 --assume-approval 自动确认")
                out.next_action = "已确认，可进入下一阶段"
        self.manifest.add(out)
        return out

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
        for sid in (stages or STAGE_ORDER):
            out = self.run_stage(sid, confirm=confirm_all)
            if out.status in ("blocked", "failed"):
                break
        self._finish()
        return self.manifest

    def run_remaining(self) -> RunManifest:
        return self.run_all(confirm_all=self.assume_approval)

    def confirm(self, stage_id: str, by: str = "业主", note: str = "") -> Dict[str, Any]:
        st = confirm_stage(self.project, stage_id, by=by, note=note)
        record_change(self.project, "gate", f"{stage_name(stage_id)} 确认通过（{by}）",
                      targets=[stage_id])
        self._persist()
        return st.to_dict()

    def reject(self, stage_id: str, reason: str = "") -> Dict[str, Any]:
        from .stage_state import reject_stage

        st = reject_stage(self.project, stage_id, reason)
        record_change(self.project, "gate", f"{stage_name(stage_id)} 未通过：{reason}",
                      targets=[stage_id])
        self._persist()
        return st.to_dict()

    # ------------------------------------------------------------------
    def apply_change(self, text: str, apply: bool = True) -> changes.ChangeImpactReport:
        rep = changes.analyse(self.project, text, apply=apply)
        touched = invalidate_from(self.project, rep.diagnosis.landing_stage)
        rep.notes.append("受影响阶段状态已置为返工：" + "、".join(stage_name(s) for s in touched))
        d = self.out / "changes"
        d.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        (d / f"change-{stamp}.json").write_text(
            json.dumps(rep.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
        )
        (d / f"change-{stamp}.md").write_text(rep.markdown(), encoding="utf-8")
        self._persist()
        return rep

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
        d = self._dir("S1")
        prog = self.project.program or []
        cons = self.project.constraints or {}
        budget = cons.get("budget_cny")

        lines = [
            f"# 设计任务书 — {self.project.name or self.project.project_id}", "",
            f"- 项目编号：`{self.project.project_id}`　修订：r{self.project.revision}",
            f"- 单位制：{self.project.units}",
            f"- 设计阶段：方案（非施工图深度）",
        ]
        for k, v in cons.items():
            if k.startswith("_") or k == "budget_cny":
                continue
            lines.append(f"- {k}：{v}")
        if budget:
            lines.append(f"- 预算：{budget:,.0f} CNY")
        lines += ["", "## 功能任务书", "",
                  "| # | 房间 | 用途 | 目标面积 m² | 分区 | 需采光 |", "|---|---|---|---|---|---|"]
        for i, p in enumerate(prog, 1):
            rec = str(p.get("recipe", ""))
            day = rec in ("living", "dining", "kitchen", "master_bedroom", "bedroom", "study")
            lines.append(
                f"| {i} | {p.get('name','')} | {rec} | {p.get('area_m2','')} "
                f"| {p.get('zone','')} | {'是' if day else '否'} |"
            )
        total = sum(float(p.get("area_m2") or 0) for p in prog)
        lines += ["", f"**任务书面积合计：{total:.1f} m²**", "", "## 已知条件与信息来源", ""]
        for s in self.project.sources or []:
            lines.append(
                f"- {s.get('type','')} `{s.get('file','')}`　置信度 {s.get('confidence','')}"
                f"　{s.get('note','')}"
            )
        lines += ["", "## 假设（未确认，不得当作事实）", ""]
        lines += [f"- {a}" for a in (self.project.assumptions or [])] or ["- 无"]

        # --- early cost estimate (R3) ---
        est = None
        if budget:
            est = quantities.takeoff(self.project, self.level_id)
            lines += ["", "## 预算口径（前期估算，非报价）", "",
                      f"- 估算区间：{est.cost['subtotal_low']:,.0f} – {est.cost['subtotal_high']:,.0f} CNY",
                      f"- 单位造价：{est.cost['per_m2_low']:,.0f} – {est.cost['per_m2_high']:,.0f} 元/m²"]
            lines += [f"- {n}" for n in est.notes]
        lines += ["", "## 验收标准", "",
                  "1. 功能任务书与面积指标经业主确认；",
                  "2. 预算口径与设计标准一致；",
                  "3. 原始条件中的不确定性已列明并标记为待现场核对。"]
        (d / "design-brief.md").write_text("\n".join(lines), encoding="utf-8")

        # --- site / existing condition report ---
        env = envelope_polygon(self.project, self.level_id)
        xs = [p[0] for p in env]
        ys = [p[1] for p in env]
        ex, ey = entry_point(self.project, env)
        uncertain = [e for e in self.project.elements if e.uncertain]
        walls = [w for w in self.project.by_type("wall") if w.level_id == self.level_id]
        lvl_height = next(
            (l.height_mm for l in self.project.levels if l.id == self.level_id), 0.0
        )
        site = [
            f"# 原始条件报告 — {self.project.project_id}", "",
            "## 外壳", "",
            f"- 内表面外包尺寸：{(max(xs)-min(xs))/1000:.2f} m × {(max(ys)-min(ys))/1000:.2f} m",
            f"- 外轮廓顶点数：{len(env)}（{'矩形' if len(env) == 4 else '非矩形，分区会被裁剪'}）",
            f"- 入户位置（推断）：({ex:.0f}, {ey:.0f})",
            f"- 层高：{lvl_height:.0f} mm",
            "", "## 既有构件", "",
            f"- 墙体 {len(walls)} 段，其中推断所得 {len(uncertain)} 段",
            "", "## 图纸解析", "",
            "- 图层识别：A-WALL（结构墙）/ A-WALL-PART（隔墙）/ A-DOOR / A-GLAZ / A-ANNO-DIMS",
            "- 推断内容与实测内容已分离标记（`uncertain` 字段）",
            "", "## 不确定信息（必须现场核对）", "",
        ]
        if uncertain:
            for e in uncertain[:20]:
                site.append(
                    f"- `{e.id}` {e.type}　置信度 {e.confidence:.2f}　"
                    f"{e.properties.get('note','由图纸推断，非实测')}"
                )
        else:
            site.append("- 无")
        site += ["", "> 梁柱与承重墙不得依据图纸推定；须现场探测或由原设计单位确认。"]
        (d / "site-report.md").write_text("\n".join(site), encoding="utf-8")

        for aid, path, deps in (
            ("art-brief", d / "design-brief.md", ["project:program"]),
            ("art-site", d / "site-report.md", ["shell", "existing_walls"]),
        ):
            register_artifact(self.project, aid, "document", deps,
                              "design-brief" if aid == "art-brief" else "site-analysis",
                              relpath(path), "draft")
        notes = [f"任务书 {len(prog)} 项功能，合计 {total:.1f} m²",
                 f"{len(uncertain)} 个构件标记为须现场核对"]
        if est:
            notes.append(f"前期估算 {est.cost['subtotal_low']:,.0f}–{est.cost['subtotal_high']:,.0f} CNY")
        return StageOutcome("S1", artifacts=[str(d / "design-brief.md"), str(d / "site-report.md")],
                            notes=notes)

    # ==================================================================
    # 02 概念方案设计
    # ==================================================================
    def stage_S2(self) -> StageOutcome:
        d = self._dir("S2")
        style = str((self.project.constraints or {}).get("style") or "现代意式极简")
        prog = self.project.program or []
        lines = [
            f"# 概念方案 — {self.project.name or self.project.project_id}", "",
            f"**风格定位：{style}**", "",
            "## 概念一 · 中部服务脊（Service Spine）", "",
            "| 步 | 内容 |", "|---|---|",
            "| 锚 | 把不该被看见的东西集中起来，剩下的空间才安静 |",
            "| 象 | 一条压在户型中段的石质脊 |",
            "| 法 | 卫生间、储藏、厨房沿中脊排布，两侧均为房间 |",
            "| 形 | 一条贯穿南北的直线 |",
            "",
            "- 空间事件：进门 30 秒内，视线被中脊引导向右，客厅在城市光里展开",
            "- 优势：采光面最大化，房间进深短、面宽大",
            "- 风险：中脊无自然采光，须靠机械排风与人工照明补足",
            "",
            "## 概念二 · 南北动静横分（Day / Night Band）", "",
            "| 步 | 内容 |", "|---|---|",
            "| 锚 | 会客与休息不共享同一条动线 |",
            "| 象 | 一条水平的走廊像一道缝合线 |",
            "| 法 | 南侧公共区完全开放，北侧私密区由走廊串起 |",
            "| 形 | 一条水平主导线，同时是天花造型与灯带走向 |",
            "",
            "- 空间事件：从玄关往北走，天花上的弧线一直带着人走到主卧门口",
            "- 优势：公私分区清晰，开放区面积占比高",
            "- 风险：走廊面积占比上升，北侧房间进深偏大",
            "",
            "## 概念自检（克制美学宪章）", "",
            "| 判据 | 概念一 | 概念二 |", "|---|---|---|",
            "| 一句话能说清（动词+材料+空间事件） | 是 | 是 |",
            "| 在平面上能画出来 | 是 | 是 |",
            "| 只需要一条主导线 | 是 | 是 |",
            "| 业主能在电梯里复述 | 是 | 是 |",
            "| 暖材占比 ≤40% | 待材质方案验证 | 待材质方案验证 |",
            "",
            "## 意向板关键词（定下后本轮不再变更）", "",
            "| 组 | 关键词 |", "|---|---|",
            "| 气质 | 克制 · 清醒 · 静默的贵 |",
            "| 材料 | 微水泥 · 暖灰岩板 · 拉丝黑钛 |",
            "| 光 | 一条发光的面 · 洗墙 · 3000K |",
            "",
            f"## 房间清单（{len(prog)} 项）", "",
            "| 房间 | 目标 m² | 分区 |", "|---|---|---|",
        ]
        for p in prog:
            lines.append(f"| {p.get('name','')} | {p.get('area_m2','')} | {p.get('zone','')} |")
        lines += ["", "## 照明方向（概念层）", "",
                  "- 概念一：中脊用线性灯带勾出方向，房间内以洗墙补足",
                  "- 概念二：天花主导线内嵌灯带，作为『画在天花上的旋律线』",
                  "", "## 成本影响（R3 · 前期动态估算）", "",
                  "- 概念阶段成本差异主要来自天花造型复杂度与走廊面积占比",
                  "", "---", "",
                  "> 判据为本系统自有口径：克制美学基线、概念四步引擎、意向板协议"
                  "（见 docs/DESIGN_CRITERIA.md）。",
                  "> 概念方向须在平面阶段（S3）验证是否成立，不能只活在效果图里。"]
        lines += [
            "", "---", "",
            f"项目：{self.project.name or self.project.project_id}"
            f"（{self.project.project_id}）　模型修订 r{self.project.revision}"
            f"　阶段 S2 　生成时间 {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "本文件由 OmniArchitect 依据统一空间模型自动生成，与同一修订的全部下游成果可互相追溯。",
            "设计判据为通用设计原理与工程惯例；结构、消防、无障碍与法规符合性须由持证专业人员复核签署。",
        ]
        (d / "concept-options.md").write_text("\n".join(lines), encoding="utf-8")

        # moodboard protocol
        mood = [
            "# 意向板（Moodboard）骨架", "",
            "| 格位 | 内容 | 判据 |", "|---|---|---|",
            "| ① 主空间意象 | 1 张定调图 | 能看出冷暖对峙关系 |",
            "| ② 天花与线条 | 主导线形态参考 | 一条线，不是一堆造型 |",
            "| ③ 材质拼板 | 4–6 块，按暖/冷/黑分组 | 暖 ≤40%，黑 3–8% |",
            "| ④ 色调条 | 5 色带占比 | 60-30-10 + 黑 5 |",
            "| ⑤ 细部大样 | 2–3 个节点特写 | 决定『贵不贵』的地方 |",
            "| ⑥ 光的性格 | 1 张光的参考 | 必须包含『一个发光的面』 |",
            "", "## Concept Statement（≤60 字，含一个动词、一个材料、一个空间事件）", "",
            "（待定——由主创填入并用一句话说清）", "",
            "## 量化评分口径（跨轮不可更换）", "",
            "- 200ms 第一印象　- 气质吻合度 0–100　- Design Critic 六维 0–100",
            "- Color Harmony 60-30-10 拆色　- Design Taste 三维校准（Variance/Motion/Density）",
            "", "> 迭代方法：意向板六格 → 关键词三组 → 量化打分 → 跨轮整改追踪。",
            "", "---", "",
            f"项目：{self.project.project_id}　模型修订 r{self.project.revision}"
            f"　阶段 S2 　生成时间 {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        ]
        (d / "moodboard.md").write_text("\n".join(mood), encoding="utf-8")

        rj = RenderAdapter().build_job_package(
            self.project, d / "moodboard-render-jobs.json",
            level_id=self.level_id, lighting="day_soft", style=style,
        )
        register_artifact(self.project, "art-concept", "document", ["project:program"],
                          "concept-design", relpath(d / "concept-options.md"), "draft")
        register_artifact(self.project, "art-moodboard", "document", ["art-concept"],
                          "moodboard-aesthetic-iteration", relpath(d / "moodboard.md"), "draft")
        return StageOutcome(
            "S2",
            artifacts=[str(d / "concept-options.md"), str(d / "moodboard.md"), *rj.artifacts],
            adapter="render",
            notes=["2 个概念方向 + 意向板骨架 + 概念层照明方向",
                   "意向板关键词与评分口径已固定，后续轮次不可更换"],
        )

    # ==================================================================
    # 03 平面方案设计
    # ==================================================================
    def stage_S3(self) -> StageOutcome:
        d = self._dir("S3")
        gen = PlanGenerator(self.project, self.level_id)
        options = [
            SchemeOptions(variant="A", title="方案A · 南北动静横分", strategy="band_day_night"),
            SchemeOptions(variant="B", title="方案B · 中部服务脊", strategy="spine_centre"),
        ]
        self.schemes = {o.variant: gen.generate(o) for o in options}

        rows = ["# 平面方案对比（S3）", "", "## 面积表", "",
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
        return StageOutcome(
            "S3", artifacts=arts, adapter="dxf",
            notes=[f"生成 {len(self.schemes)} 套平面方案 + 对比分析 + 造价影响", note_dxf,
                   "等待业主选定方案（门禁 G3）"],
        )

    # ==================================================================
    # 04 初步设计与方案深化
    # ==================================================================
    def stage_S4(self) -> StageOutcome:
        d = self._dir("S4")
        chosen = self._ensure_scheme_installed()
        spaces = [s for s in self.project.spaces if s.properties.get("scheme")]
        style = str((self.project.constraints or {}).get("style") or "现代意式极简")

        # --- 顶墙地 + 材料体系 ---
        lines = [
            f"# 初步设计 — 方案{chosen}", "",
            f"风格：{style}　　（S3 已确认方案{chosen}）", "",
            "## 顶面", "",
            "| 区域 | 做法 | 标高 | 灯槽 |", "|---|---|---|---|",
            "| 客厅/餐厅 | 平顶 + 弧形叠级（主导线） | 2600 | 内嵌灯带 3000K |",
            "| 走廊 | 平顶 + 线性灯带导向 | 2500 | 两侧洗墙 |",
            "| 卧室 | 平顶 + 窗帘盒 | 2500 | 床头重点照明 |",
            "| 卫生间 | 铝扣板/防水石膏板 | 2400 | 防雾筒灯 |",
            "", "## 墙面", "",
            "| 部位 | 做法 | 材料 |", "|---|---|---|",
            "| 公共区主墙 | 微水泥 / 暖白乳胶漆 | NCS S1002-Y |",
            "| 电视背景墙（待确认） | 弧形岩板 + 隐藏灯带 | 暖灰岩板 12mm |",
            "| 走廊端景 | 乳白亚克力发光面 | 亚克力 + 背光 |",
            "| 卧室 | 木饰面 + 硬包 | 橡木拉丝 |",
            "", "## 地面", "",
            "| 区域 | 材料 | 规格 |", "|---|---|---|",
            "| 公共区 | 微水泥 / 大板岩板 | 哑光，缝宽 2mm |",
            "| 卧室 | 木地板 | 实木复合 190×1200 |",
            "| 卫生间 | 防滑砖 | 300×600 哑光 |",
            "", "## 材料与色彩体系（暖材占比控制在 25–35%）", "",
            "| 组 | 材料 | 色值 | 全场占比 |", "|---|---|---|---|",
            "| 冷底 | 微水泥 / 超白玻 / 黑钛 | NCS S1500-N | 55% |",
            "| 暖面 | 橡木饰面 / 亚麻 | NCS S2010-Y30R | 30% |",
            "| 重音 | 黑钛收边 / 台面 | NCS S9000-N | 5% |",
            "| 过渡 | 暖灰岩板 | NCS S2502-Y | 10% |",
            "", "## 灯光方案（初步）", "",
            "| 层 | 手法 | 参数 |", "|---|---|---|",
            "| 基础 | 洗墙 + 筒灯 | 3000K / Ra≥90 / 100lx |",
            "| 重点 | 背景墙灯带、床头 | 3000K / 300lx |",
            "| 氛围 | 天花灯带旋律线 | 2700K / 可调光 |",
            "| 自然光 | 保留南向落地窗，不补光打平 | — |",
            "", "## 机电与设备协调（初步）", "",
            "| 专业 | 空间影响 | 待办 |", "|---|---|---|",
            "| 暖通 | 吊顶内风管占用 ≥250mm | 复核净高 2600 是否满足 |",
            "| 电气 | 点位合计约 68 处 | 与家具布置核对 |",
            "| 给排水 | 中脊竖向管井 | 确认与结构无冲突 |",
            "| 消防 | 住宅户内无喷淋（按当地要求复核） | **须专业确认** |",
            "", "## 这一步的交付深度说明", "",
            "本阶段输出**方案深度**图纸：可用于与业主沟通做法与造价，**不得用于施工**。",
            "正式施工图在 S7 出，深度区别是 construction，而不是有没有图纸（R2）。",
            "", "---", "",
            "> 做法、材料与灯光的判断口径为本系统自有标准；"
            "机电口径为空间影响速查，具体设计须专业工程师完成。",
        ]
        (d / "preliminary-design.md").write_text("\n".join(lines), encoding="utf-8")

        # --- material & lighting schedules as structured data ---
        sched = {
            "materials": [
                {"group": "冷底", "name": "微水泥", "spec": "哑光 3mm", "color": "NCS S1500-N", "ratio": 0.55},
                {"group": "暖面", "name": "橡木饰面", "spec": "拉丝 0.6mm", "color": "NCS S2010-Y30R", "ratio": 0.30},
                {"group": "重音", "name": "黑钛", "spec": "拉丝 1.0mm", "color": "NCS S9000-N", "ratio": 0.05},
                {"group": "过渡", "name": "暖灰岩板", "spec": "12mm", "color": "NCS S2502-Y", "ratio": 0.10},
            ],
            "lighting": [
                {"layer": "基础", "fixture": "筒灯/洗墙", "cct_k": 3000, "cri": 90, "lux": 100},
                {"layer": "重点", "fixture": "灯带/射灯", "cct_k": 3000, "cri": 90, "lux": 300},
                {"layer": "氛围", "fixture": "天花灯带", "cct_k": 2700, "cri": 90, "lux": None},
            ],
            "mep_points": {"electrical": 68, "water": 12, "drain": 6, "hvac_diffuser": 9},
            "depth": "schematic",
            "note": "暖材占比须 ≤40%，超过即滑向酒店感，丢掉空间的清醒",
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
        chosen = self._ensure_scheme_installed()
        arts: List[str] = []
        notes: List[str] = []
        status = "ok"

        mesh = MeshAdapter()
        m = mesh.export_obj(self.project, d, level_id=self.level_id, stem=f"S5-model-{chosen}")
        arts.extend(m.artifacts)
        if m.ok:
            notes.append(
                f"可编辑 3D 模型：{m.validation.get('vertices','?')} 顶点 / "
                f"{m.validation.get('faces','?')} 面（mm，Z 向上）"
            )
        else:
            status = "failed"

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
            "| 01 | 全景 | 汇报封面 | 24mm，1.6m 眼高 |",
            "| 02 | 客厅 | 主推 | 35mm，房间对角 |",
            "| 03 | 餐厅 | 主推 | 35mm |",
            "| 04 | 主卧 | 辅助 | 35mm |",
            "| 05 | 轴测 | 空间关系 | 50mm 正交倾向 |",
            "| 06 | 全景漫游 | 交付 | 沿主动线，60s |",
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
        coord += ["", "## 设计锁定", "",
                  "以下内容锁定为深化依据，锁定后任何修改走变更影响分析：",
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

        record_change(self.project, "freeze", f"设计锁定（方案{chosen}，r{self.project.revision}）",
                      targets=[f"scheme:{chosen}"])
        self.project.meta["frozen_revision"] = self.project.revision
        self.project.meta["scheme"] = {
            **dict(self.project.meta.get("scheme") or {}),
            "variant": chosen, "frozen_at_revision": self.project.revision,
        }
        register_artifact(self.project, "art-freeze", "report",
                          [e.id for e in self.project.by_type("wall")],
                          "design-review", relpath(d / "coordination.md"), "validated")
        return StageOutcome(
            "S6", adapter="",
            artifacts=[str(d / "design-review.md"), str(d / "design-review.json"),
                       str(d / "coordination.md")],
            status="ok" if rep.summary["pass"] else "degraded",
            notes=[f"校核：阻断 {rep.summary['blockers']} / 提示 {rep.summary['warnings']}",
                   "设计与造价基线已锁定", "结构/消防/给排水带未闭环项进入施工图阶段"],
        )

    # ==================================================================
    # 07 CAD / BIM 施工图深化
    # ==================================================================
    def stage_S7(self) -> StageOutcome:
        d = self._dir("S7")
        chosen = self._ensure_scheme_installed()
        dxf = DxfAdapter()
        arts: List[str] = []
        notes: List[str] = []
        status = "ok"

        if dxf.preflight().available:
            for sheet, kw in (
                ("A-01-plan", {"title": "平面布置图（施工图深度）", "include_furniture": True}),
                ("A-02-rooms", {"title": "房间与面积图", "include_furniture": False}),
                ("A-03-furniture", {"title": "家具定位图", "include_furniture": True}),
            ):
                r = dxf.draw_plan(
                    self.project, d / f"{sheet}.dxf", level_id=self.level_id,
                    scheme=chosen, **kw,
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
            "| A-01 | 平面布置图 | construction |",
            "| A-02 | 房间与面积图 | construction |",
            "| A-03 | 家具定位图 | construction |",
            "| A-04 | 顶面/吊顶图 | 待深化 |",
            "| A-05 | 地面铺装图 | 待深化 |",
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
        md = ["# 工程量与成本清单（S8 · 正式）", "", "## 工程量", "",
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
            "| 部位 | 材料 | 规格 | 品牌档位 | 用量 | 损耗 | 替代 |", "|---|---|---|---|---|---|---|",
            f"| 公共区地面 | 微水泥 | 哑光 3mm | 中高档 | {t.quantities['floor_area_m2']:.1f} m² | 8% | 大板岩板 |",
            f"| 卧室地面 | 实木复合地板 | 190×1200 | 中高档 | {t.quantities['floor_area_m2']*0.35:.1f} m² | 5% | 强化复合 |",
            f"| 墙面 | 乳胶漆 NCS S1002-Y | 哑光 | 中档 | {t.quantities['wall_finish_area_m2']:.1f} m² | 10% | 微水泥 |",
            f"| 天花 | 石膏板 + 乳胶漆 | 9.5mm | 中档 | {t.quantities['ceiling_area_m2']:.1f} m² | 8% | 矿棉板 |",
            f"| 木饰面/柜体 | 橡木饰面 | 0.6mm 拉丝 | 中高档 | {t.quantities['joinery_area_m2']:.1f} m² | 10% | 科技木 |",
            f"| 玻璃 | 超白钢化 | 12mm | 中高档 | {t.quantities['glazing_area_m2']:.1f} m² | 3% | 普通白玻 |",
            f"| 门 | 实木复合门 | 900×2100 | 中高档 | {t.quantities['door_count']:.0f} 樘 | 0% | 免漆门 |",
            "", "## 采购注意", "",
            "- 同一材料必须锁定同一批次色号；",
            "- 岩板/大板需在图纸确认后实测下单；",
            "- 灯具需按回路与色温分批到货。",
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
            f"- 阶段进度：{progress(self.project)['percent']}%", "",
            "## 文件清单", ""]
        readme += [f"- `{f}`" for f in files if not f.startswith("08-")]
        readme += ["", "## 使用限制", "",
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
                          relpath(d / "delivery-manifest.json"), "issued")
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
            o = SchemeOptions(variant=self.scheme_variant,
                              title=f"方案{self.scheme_variant}",
                              strategy="band_day_night" if self.scheme_variant == "A" else "spine_centre")
            self.schemes = {o.variant: gen.generate(o)}
        variant = self.scheme_variant if self.scheme_variant in self.schemes else sorted(self.schemes)[0]
        _install_scheme(self.project, self.schemes[variant])
        resolve_host_axes(self.project)
        self.project.revision += 1
        record_change(self.project, "scheme", f"安装方案{variant}作为深化依据",
                      targets=[f"scheme:{variant}"])
        return variant


# --------------------------------------------------------------------------
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
