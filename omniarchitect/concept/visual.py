"""S2 概念视觉：走 OmniAiLab 正式链路，未连接就如实延后。

这一层与 G3 之后的概念效果图**不是同一件事**：

| | S2 概念视觉（本模块） | G3 后概念效果图（`providers.canvas`） |
|---|---|---|
| 依据 | 概念主张 + 风格库 | **已确认的平面** |
| 目的 | 定方向、谈氛围 | 让业主看到自己家的空间 |
| 是否含真实几何 | 否（关系与氛围） | 是（机位、视高、材料取自模型） |
| 产物命名 | concept visual | concept rendering |

所以本模块的产物一律标 `non_authoritative`，并在任务包里写死"不得作为效果图或
尺寸依据"。混用会让业主以为看到的是自己家——这是本项目最不能犯的错之一。

提交链路完全复用 `providers` 注册表：探测 → 选择 → 授权 → 提交 → 轮询 → 取回 →
格式检查 → 资产登记。没有第二套 HTTP 客户端，也不猜平台路径与模型名。

三道锁：平台可用、`submit` 与 `authorize` 同时成立、费用可知且不超上限。任何一道
没开都不提交——未提交不等于没成本，所以结论里写"受控：否"，而不是"大概没事"。

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from ..model import Project
from ..style.compiler import CompiledPrompt, SpaceBrief, compile_prompt
from ..style import load_catalog

IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff"}

#: 幂等台账的文件名（落在 S2 成果目录里，重跑时据此避免重复计费）
LEDGER_NAME = "concept-visual-ledger.json"

STATUS_LABEL = {
    "awaiting_platform": "待平台执行",
    "awaiting_cost_confirmation": "待费用确认",
    "submitted_unknown": "已提交·待核实",
    "generated": "已生成",
    "failed": "失败",
    "not_configured": "平台未配置",
}


def _brief_for(concept: Dict[str, Any], ctx: Any) -> SpaceBrief:
    """Only real facts: no width/depth when there is no geometry."""
    return SpaceBrief(
        space_name=f"{concept['concept_name']}（概念方向）",
        area_m2=ctx.area_available_m2 or (ctx.target_area_m2 or None),
        orientation=_orientation(ctx),
        furniture_needs=[m["name"] for m in (concept.get("material_direction") or [])][:3],
        materials_override=[m["name"] for m in (concept.get("material_direction") or [])],
        lighting_override=list(concept.get("lighting_direction") or []),
        camera="概念意象：等效 24–35mm，视高 1500–1600mm；不指定具体房间",
    )


def _orientation(ctx: Any) -> str:
    from ..intake.interview import load_interview  # local import: avoid cycles

    return ctx.location or ""


def build_jobs(concept: Dict[str, Any], ctx: Any, project: Project,
               *, catalog=None) -> List[Dict[str, Any]]:
    """Compile the prompts this concept needs. Compiling is not generating."""
    cat = catalog or load_catalog()
    jobs: List[Dict[str, Any]] = []
    brief = _brief_for(concept, ctx)
    needs = [o["problem"] for o in ctx.opportunities[:3]] or [n["activity"] for n in ctx.needs[:3]]

    locked = bool((project.meta or {}).get("concept", {}).get("baseline"))
    # 两条基础意象 + 两条版面配方（概念设计板 / 实体材质情绪板）。
    # 版面配方来自 style/recipes.py：它们同样走双开关与幂等台账，
    # 但画面里不许出现文字——标签由排版层叠加。
    for kind, target, label in (
        ("concept_visual", "concept", "设计方向意象"),
        ("moodboard_image", "moodboard", "材料与氛围"),
        ("concept_sheet", "concept-sheet", "概念设计板"),
        ("material_board", "material-moodboard", "实体材质情绪板"),
    ):
        try:
            prompt: CompiledPrompt = compile_prompt(
                concept["style_ids"], brief, target=target, stage="S2",
                revision=project.revision, catalogue=cat, locked=locked,
                user_needs=needs,
            )
        except Exception as exc:                     # unknown style id, etc.
            jobs.append({
                "job_id": f"{concept['concept_id']}-{kind}",
                "concept_id": concept["concept_id"],
                "kind": kind, "target": target, "label": label,
                "status": "failed",
                "reason": f"提示词编译失败：{type(exc).__name__}: {exc}",
                "prompt": {},
            })
            continue
        jobs.append({
            "job_id": f"{concept['concept_id']}-{kind}",
            "concept_id": concept["concept_id"],
            "kind": kind,
            "target": target,
            "label": label,
            "scope": _scope_of(target),
            "status": "awaiting_platform",
            "reason": "尚未提交（需要 --submit 且显式 --authorize）",
            "prompt": prompt.to_dict(),
            "style_ids": list(concept["style_ids"]),
            "consistency_key": prompt.consistency_key,
            "revision": project.revision,
            "non_authoritative": True,
            "text_overlay": list(prompt.text_overlay),
            "note": ("S2 概念视觉：不依据已确认平面，仅表达方向与氛围；"
                     "不得当作空间效果图或尺寸依据。"
                     + ("版面上的文字由排版层叠加，画面内不让模型写字。"
                        if prompt.text_overlay else "")),
        })
    return jobs


def _params(job: Dict[str, Any], project: Project) -> Dict[str, Any]:
    p = job.get("prompt") or {}
    positive = (p.get("positive") or {}).get("zh") or ""
    negative = "；".join((p.get("negative") or {}).get("zh") or [])
    return {
        "prompt": positive,
        "negative_prompt": negative,
        "aspect_ratio": "16:10",
        "style_ids": list(job.get("style_ids") or []),
        "consistency_key": job.get("consistency_key", ""),
        "workflow": "concept",
        "stage": "S2",
        "target": job.get("target", ""),
        "scope": job.get("scope", "image_generation"),
        "job_kind": job.get("kind", ""),
        "label": job.get("label", ""),
        "units": 1,
        "project_id": project.project_id,
        "revision": project.revision,
    }


def _scope_of(target: str) -> str:
    """配方声明的能力域；没登记就按 image_generation 走。"""
    from ..style.provider_bridge import TARGET_SCOPE

    return TARGET_SCOPE.get(target, "image_generation")


def _media_ok(path: str) -> bool:
    p = Path(path)
    if not p.exists() or p.stat().st_size < 1024:
        return False
    return p.suffix.lower() in IMAGE_EXT


@dataclass
class VisualResult:
    jobs: List[Dict[str, Any]] = field(default_factory=list)
    platform_state: str = "not_configured"
    platform_missing: List[str] = field(default_factory=list)
    submit_requested: bool = False
    authorized: bool = False
    submitted: int = 0
    generated: int = 0
    reused: int = 0
    held: int = 0
    unknown: int = 0
    deferred: int = 0
    failed: int = 0
    cost_estimate: Optional[float] = None
    cost_known: bool = True
    cost_cap: Optional[float] = None
    currency: str = "CNY"
    warnings: List[str] = field(default_factory=list)
    files: Dict[str, str] = field(default_factory=dict)

    @property
    def cost_controlled(self) -> bool:
        """费用是否真的受控：必须每一项都有可靠估价，且设定了上限。"""
        return bool(self.cost_known and self.cost_cap is not None and self.submitted)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "platform_state": self.platform_state,
            "platform_missing": list(self.platform_missing),
            "submit_requested": self.submit_requested,
            "authorized": self.authorized,
            "job_count": len(self.jobs),
            "submitted": self.submitted,
            "generated": self.generated,
            "reused": self.reused,
            "held": self.held,
            "unknown": self.unknown,
            "deferred": self.deferred,
            "failed": self.failed,
            "cost_estimate": self.cost_estimate,
            "cost_known": self.cost_known,
            "cost_cap": self.cost_cap,
            "cost_controlled": self.cost_controlled,
            "currency": self.currency,
            "warnings": list(self.warnings),
            "jobs": [dict(j) for j in self.jobs],
        }


def _job_key(job: Dict[str, Any], project: Project) -> str:
    """Stable identity of one *paid* unit of work.

    Everything that would change the picture is in the key: the compiled prompt,
    the consistency key, the revision and the job id. Same key → same task, so a
    second run must reuse the first result instead of paying twice.
    """
    blob = json.dumps({
        "job_id": job.get("job_id", ""),
        "revision": int(project.revision),
        "target": job.get("target", ""),
        "consistency_key": job.get("consistency_key", ""),
        "prompt": job.get("prompt") or {},
    }, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha1(blob.encode("utf-8")).hexdigest()[:16]


def load_ledger(path: str | Path) -> Dict[str, Any]:
    p = Path(path)
    if p.exists():
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            if isinstance(data, dict) and isinstance(data.get("entries"), dict):
                return data
        except Exception:
            pass
    return {"entries": {}}


def _save_ledger(path: Path, ledger: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(ledger, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")


def submit(jobs: Sequence[Dict[str, Any]], project: Project, out_dir: str | Path,
           *, submit: bool = False, authorize: bool = False,
           max_cost: Optional[float] = None,
           project_dir: str | Path | None = None) -> VisualResult:
    """Submit through the provider registry, or mark every job as deferred.

    Three independent locks, all of which must open:

    1. **平台可用** —— 未配置就停在 `awaiting_platform`，不伪造图片；
    2. **双开关** —— `submit=True` 与 `authorize=True` 必须同时具备，
       只给其中一个不构成提交请求；
    3. **费用可知且受限** —— 平台没有声明计价时，任何一次提交都可能超支，
       一律停在 `awaiting_cost_confirmation`，不猜、不假设"大概不贵"。

    提交前查幂等台账：同一个 job_key 已生成过就直接复用，绝不再付一次。
    """
    from ..providers import ProviderError, NotConfigured, discover

    out = Path(out_dir)
    renders = out / "concept-visuals"
    renders.mkdir(parents=True, exist_ok=True)
    ledger_path = out / LEDGER_NAME
    ledger = load_ledger(ledger_path)
    ledger["project_id"] = project.project_id

    res = VisualResult(jobs=[dict(j) for j in jobs], submit_requested=submit,
                       authorized=authorize, cost_cap=max_cost)

    reg = discover(project_dir)
    cap = next((c for c in reg.capabilities() if c.provider == "omniailab"), None)
    res.platform_state = cap.state if cap else "not_registered"
    res.platform_missing = list(cap.missing) if cap else ["provider 未注册"]

    usable = bool(cap and cap.usable and cap.can("image_generation"))
    provider = reg.get("omniailab")

    for job in res.jobs:
        key = _job_key(job, project)
        job["job_key"] = key
        entry = ledger["entries"].get(key) or {}

        if job.get("status") == "failed":
            res.failed += 1
            continue

        # -- 1. 已经付过费的同一件事 -------------------------------------
        if entry.get("status") == "generated" and _media_ok(str(entry.get("output") or "")):
            job["status"] = "generated"
            job["output"] = entry["output"]
            job["outputs"] = list(entry.get("outputs") or [entry["output"]])
            job["reused"] = True
            job["reason"] = "复用本修订已有的生成结果（未重复提交、未重复计费）"
            res.generated += 1
            res.reused += 1
            continue
        if entry.get("status") == "submitted":
            # 上一次发出去了但没等到结果：不能再发一次，否则可能双份计费。
            job["status"] = "submitted_unknown"
            job["reason"] = (f"上一次已提交（job {entry.get('provider_job') or '?'}）但结果未知："
                             "为避免重复计费，本次不再提交，请先向平台核实该任务")
            job["idempotency_key"] = entry.get("idempotency_key", "")
            job["recovery"] = ("按幂等键或任务号在平台核实：已生成则直接取回，"
                               "未生成再重跑。系统不会自动重提。")
            res.unknown += 1
            continue

        if not usable:
            job["status"] = "awaiting_platform"
            job["reason"] = (
                "平台未配置：缺少 " + "；".join(res.platform_missing)
                if res.platform_missing else "平台不可用"
            )
            res.deferred += 1
            continue

        # -- 2. 双开关 ---------------------------------------------------
        if not (submit and authorize):
            missing = []
            if not submit:
                missing.append("--submit")
            if not authorize:
                missing.append("--authorize")
            job["status"] = "awaiting_platform"
            job["reason"] = (f"未提交：缺少 {' 与 '.join(missing)}"
                             "（联网且计费的操作需要两个开关同时打开）")
            res.deferred += 1
            continue

        # -- 3. 费用可知 -------------------------------------------------
        # 能力域先定下来：计价按"这张图属于哪类活儿"查，不按默认值查。
        scope = str(job.get("scope") or "image_generation")
        declared = set(getattr(cap, "scopes", []) or [])
        if declared and scope not in declared:
            job["scope_fallback"] = f"平台未声明 {scope}，按 image_generation 提交"
            scope = "image_generation"
        params = _params(job, project)
        estimate: Optional[float] = None
        if provider is not None:
            try:
                estimate = provider.estimate_cost(scope, params)
            except Exception:
                estimate = None
        if estimate is None:
            res.cost_known = False
            job["status"] = "awaiting_cost_confirmation"
            job["reason"] = ("平台契约未声明计价，无法保证费用不超过上限："
                             "已停止提交，请补充计价声明或先在平台侧确认价格")
            res.held += 1
            if max_cost is not None:
                res.warnings.append(
                    f"{job['job_id']}：已指定上限 {max_cost:.2f}，但没有计价声明，"
                    "无法证明该上限成立，故未提交（不声称费用已受控）")
            continue

        running = (res.cost_estimate or 0.0) + float(estimate)
        res.cost_estimate = round(running, 4)
        if max_cost is not None and running > max_cost:
            job["status"] = "failed"
            job["reason"] = (f"预估费用 {running:.2f} 超过上限 {max_cost:.2f}，"
                             "已按授权额度停止提交")
            res.failed += 1
            continue

        # -- 4. 提交（先记账，避免中途崩溃导致重复付费）-------------------
        ledger["entries"][key] = {
            "job_id": job.get("job_id", ""), "concept_id": job.get("concept_id", ""),
            "kind": job.get("kind", ""), "revision": project.revision,
            "status": "submitted", "output": "", "outputs": [],
            "estimated_cost": float(estimate),
            "at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        }
        _save_ledger(ledger_path, ledger)
        try:
            pjob = reg.generate(scope, params, renders, prefer="omniailab")
        except (NotConfigured, ProviderError) as exc:
            job["status"] = "failed"
            job["reason"] = f"{type(exc).__name__}: {exc}"
            res.failed += 1
            res.warnings.append(f"{job['job_id']} 提交失败：{job['reason']}")
            ledger["entries"][key].update({"status": "failed", "error": str(exc)})
            _save_ledger(ledger_path, ledger)
            continue

        res.submitted += 1
        ledger["entries"][key]["provider_job"] = pjob.job_id
        # 提交已被受理但结果不确定：**不是失败**。记为 submitted（不允许重提），
        # 并把恢复说明带给用户；把它标成 failed 会让下一次运行重付一次钱。
        if pjob.status == "unknown" or pjob.submitted_unknown or pjob.poll_exhausted:
            job["status"] = "submitted_unknown"
            job["reason"] = pjob.error or "已提交，状态未知"
            job["recovery"] = pjob.recovery
            job["idempotency_key"] = pjob.idempotency_key
            res.unknown += 1
            res.warnings.append(
                f"{job['job_id']} 已提交但结果未知（{pjob.error or '状态未知'}）："
                "系统不会自动重提；请先核实任务状态。")
            ledger["entries"][key].update({
                "status": "submitted", "provider_job": pjob.job_id,
                "idempotency_key": pjob.idempotency_key,
                "error": pjob.error, "unknown_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            })
            _save_ledger(ledger_path, ledger)
            continue
        if pjob.status == "succeeded" and pjob.outputs:
            good = [o for o in pjob.outputs if _media_ok(o)]
            bad = [o for o in pjob.outputs if not _media_ok(o)]
            if bad:
                res.warnings.append(
                    f"{job['job_id']} 返回 {len(bad)} 个非图片或过小文件，已剔除：{bad[:2]}")
            if good:
                job["status"] = "generated"
                job["output"] = good[0]
                job["outputs"] = good
                job["reason"] = f"job {pjob.job_id}"
                res.generated += 1
                reg.link_asset(pjob, good, project.project_id, project.revision,
                               "S2", "image_generation")
                ledger["entries"][key].update({"status": "generated",
                                               "output": good[0], "outputs": good})
            else:
                job["status"] = "failed"
                job["reason"] = "平台返回的文件不是可用的图片"
                res.failed += 1
                ledger["entries"][key].update({"status": "failed",
                                               "error": "non-image payload"})
        else:
            job["status"] = "failed"
            job["reason"] = f"job {pjob.job_id}: {pjob.error or pjob.status}"
            res.failed += 1
            ledger["entries"][key].update({"status": "failed",
                                           "error": str(pjob.error or pjob.status)})
        _save_ledger(ledger_path, ledger)

    _save_ledger(ledger_path, ledger)

    if not usable:
        # Queue the intent at registry level too, so it is visible in provider reports.
        for job in res.jobs:
            try:
                reg.defer_creative_task("image_generation", _params(job, project),
                                        job.get("reason", "平台不可用"))
            except Exception:
                pass
        res.warnings.append(
            "平台不可用：已生成完整任务包并登记为待执行，"
            "不生成任何替代图片（品牌策略禁止第三方回退）。"
        )
    if res.reused:
        res.warnings.append(
            f"{res.reused} 个任务复用了本修订已有的生成结果：重跑不会重复计费。")
    if res.held and res.cost_known:
        res.warnings.append(
            f"{res.held} 个任务因费用/状态不确定被拦下：未发出任何请求。")
    return res



def write_package(res: VisualResult, concept_set: Dict[str, Any],
                  ctx: Any, out_dir: str | Path) -> Dict[str, str]:
    """Write `concept-visual-jobs.json` + a human brief. Statuses are verbatim."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    payload = {
        "project_id": project_id_of(concept_set),
        "revision": concept_set.get("revision"),
        "stage": "S2",
        "purpose": "概念方向视觉：表达氛围与方向，不依据已确认平面",
        "platform": "OmniAiLab",
        "third_party_fallback": "forbidden",
        "non_authoritative": True,
        "distinct_from": "G3 后置动作（providers.canvas 的概念效果图，依据已确认平面）",
        **res.to_dict(),
        "next_step": ("把本任务包交给 OmniAiLab 平台执行；产出后逐张核对风格与材料声明是否与本方案一致。"
                      if (res.deferred or res.held) else
                      "已提交，等待平台返回结果。"),
    }
    jf = out / "concept-visual-jobs.json"
    jf.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# S2 概念视觉任务包",
        "",
        f"项目：{project_id_of(concept_set)}　模型修订 r{concept_set.get('revision', '')}"
        f"　阶段 S2",
        "",
        f"平台状态：**{res.platform_state}**　"
        f"提交请求：{'是' if res.submit_requested else '否'}　"
        f"授权：{'是' if res.authorized else '否'}",
        "",
        f"任务 {len(res.jobs)} 项：已生成 {res.generated}（其中复用 {res.reused}）、"
        f"待平台 {res.deferred}、待费用确认 {res.held}、已提交待核实 {res.unknown}、"
        f"失败 {res.failed}、本次实际提交 {res.submitted}",
        "",
        f"费用：预估 {res.cost_estimate if res.cost_estimate is not None else '未知'}"
        f" {res.currency}　上限 "
        f"{('%.2f' % res.cost_cap) if res.cost_cap is not None else '未设定'}"
        f"　受控：{'是' if res.cost_controlled else '否（不代表不花钱，只代表未提交）'}",
        "",
        "| 任务 | 所属概念 | 类型 | 状态 | 说明 |",
        "|---|---|---|---|---|",
    ]
    for job in res.jobs:
        lines.append(
            f"| {job['job_id']} | {job['concept_id']} | {job.get('label', '')} "
            f"| {STATUS_LABEL.get(job['status'], job['status'])} "
            f"| {job.get('reason', '')[:60]} |"
        )
    lines += ["", "## 这些图不是效果图", "",
              "- 依据是概念主张与风格库，**不是**已确认平面；",
              "- 不得作为空间尺寸、材料样板或施工依据；",
              "- 业主确认平面后，G3 后置动作会依据平面重新出一批概念效果图，与这批不是同一批文件。", ""]
    if res.warnings:
        lines += ["## 提示", ""] + [f"- {w}" for w in res.warnings] + [""]
    bf = out / "concept-visual-brief.md"
    bf.write_text("\n".join(lines), encoding="utf-8")
    return {"jobs": str(jf), "brief": str(bf)}


def project_id_of(concept_set: Dict[str, Any]) -> str:
    return str(concept_set.get("project_id") or "")


# --------------------------------------------------------------------------
# G3 之后：图纸派生（平面图上色 / 3D 立轴 / 三视图展示板）
# --------------------------------------------------------------------------
PLAN_TARGETS: tuple = ("plan-color", "plan-axon", "presentation-board")


def build_plan_visuals(project: Project, out_dir: str | Path, *,
                       stage: str = "S3",
                       references: Sequence[str] = (),
                       targets: Sequence[str] = PLAN_TARGETS) -> Dict[str, Any]:
    """平面确认后，按表现技法库生成"图纸派生"任务包。

    这一步只**编译**，不提交：G3 通过不等于授权花钱。任务包里的每条都标
    `plan_confirmed=True`（因为平面确实签了），但状态停在
    `awaiting_authorization`，等显式授权再走 `submit()`。
    """
    from ..style import recipes as recipe_lib
    from ..style.compiler import compile_prompt
    from ..style import load_catalog

    state = (project.meta or {}).get("concept") or {}
    selected = str(state.get("selected") or "")
    chosen = next((c for c in ((state.get("options") or {}).get("concepts") or [])
                   if c.get("concept_id") == selected), None)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    if chosen is None:
        payload = {"stage": stage, "plan_confirmed": True, "jobs": [],
                   "note": "没有已确认的概念：不做图纸派生（不拿默认风格顶替）。"}
        (out / "drawing-visuals.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return payload

    total = sum(float(s.area_m2 or 0) for s in project.spaces if s.use != "envelope")
    brief = SpaceBrief(space_name="全户型", area_m2=total or None,
                       references=list(references))
    cat = load_catalog()
    jobs: List[Dict[str, Any]] = []
    for target in targets:
        recipe = recipe_lib.get(target)
        if recipe is None:
            continue
        try:
            prompt = compile_prompt(chosen["style_ids"], brief, target=target,
                                    stage=stage, revision=project.revision,
                                    catalogue=cat, locked=True, plan_confirmed=True,
                                    reference_note="参考图为已确认平面的图纸导出")
        except Exception as exc:
            jobs.append({"job_id": f"{selected}-{target}", "target": target,
                         "status": "failed",
                         "reason": f"提示词编译失败：{type(exc).__name__}: {exc}"})
            continue
        jobs.append({
            "job_id": f"{selected}-{target}",
            "concept_id": selected,
            "target": target,
            "label": recipe.name_zh,
            "family": recipe.family,
            "scope": recipe.scope,
            "status": "awaiting_authorization",
            "reason": "平面已确认，但生成属联网计费操作：需显式授权后提交",
            "references": list(references),
            "prompt": prompt.to_dict(),
            "text_overlay": list(prompt.text_overlay),
            "style_ids": list(chosen["style_ids"]),
            "consistency_key": prompt.consistency_key,
            "revision": project.revision,
            "non_authoritative": True,
            "note": "表现图，不是图纸；不得据其量尺寸、报审或下料。",
        })

    payload = {
        "project_id": project.project_id,
        "revision": project.revision,
        "stage": stage,
        "concept_id": selected,
        "plan_confirmed": True,
        "platform": "OmniAiLab",
        "third_party_fallback": "forbidden",
        "non_authoritative": True,
        "jobs": jobs,
        "note": ("图纸派生：以已确认平面为唯一几何依据。"
                 "任务已编译但未提交——授权后才产生费用。"),
    }
    (out / "drawing-visuals.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# 图纸派生视觉任务包（G3 之后）", "",
        f"概念：{selected}　模型修订 r{project.revision}　阶段 {stage}", "",
        "| 任务 | 类型 | 状态 | 说明 |", "|---|---|---|---|",
    ]
    for j in jobs:
        lines.append(f"| {j['label']} | {j['target']} | {j['status']} | "
                     f"{j.get('reason', '')[:40]} |")
    lines += ["", "## 纪律", "",
              "- 以已确认平面为唯一几何依据，逐项对齐后再着色；",
              "- 画面内不出现文字与尺寸数字：标注由 DXF 矢量层叠加；",
              "- 表现图，不是图纸；不得据此量尺寸、报审或下料。", ""]
    (out / "drawing-visuals.md").write_text("\n".join(lines), encoding="utf-8")
    return payload


__all__ = ["build_jobs", "submit", "write_package", "VisualResult", "STATUS_LABEL",
           "load_ledger", "LEDGER_NAME", "build_plan_visuals", "PLAN_TARGETS"]
