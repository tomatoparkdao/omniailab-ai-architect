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

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from ..model import Project
from ..style.compiler import CompiledPrompt, SpaceBrief, compile_prompt
from ..style import load_catalog

IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff"}

STATUS_LABEL = {
    "awaiting_platform": "待平台执行",
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

    for kind, target, label in (
        ("concept_visual", "concept", "设计方向意象"),
        ("moodboard_image", "moodboard", "材料与氛围"),
    ):
        try:
            prompt: CompiledPrompt = compile_prompt(
                concept["style_ids"], brief, target=target, stage="S2",
                revision=project.revision, catalogue=cat, locked=False,
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
            "scope": "image_generation",
            "status": "awaiting_platform",
            "reason": "尚未提交（需要 --submit 且显式 --authorize）",
            "prompt": prompt.to_dict(),
            "style_ids": list(concept["style_ids"]),
            "consistency_key": prompt.consistency_key,
            "revision": project.revision,
            "non_authoritative": True,
            "note": ("S2 概念视觉：不依据已确认平面，仅表达方向与氛围；"
                     "不得当作空间效果图或尺寸依据。"),
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
        "job_kind": job.get("kind", ""),
        "label": job.get("label", ""),
        "units": 1,
        "project_id": project.project_id,
        "revision": project.revision,
    }


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
    authorized: bool = False
    submitted: int = 0
    generated: int = 0
    deferred: int = 0
    failed: int = 0
    cost_estimate: Optional[float] = None
    currency: str = "CNY"
    warnings: List[str] = field(default_factory=list)
    files: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "platform_state": self.platform_state,
            "platform_missing": list(self.platform_missing),
            "authorized": self.authorized,
            "job_count": len(self.jobs),
            "submitted": self.submitted,
            "generated": self.generated,
            "deferred": self.deferred,
            "failed": self.failed,
            "cost_estimate": self.cost_estimate,
            "currency": self.currency,
            "warnings": list(self.warnings),
            "jobs": [dict(j) for j in self.jobs],
        }


def submit(jobs: Sequence[Dict[str, Any]], project: Project, out_dir: str | Path,
           *, authorize: bool = False, max_cost: Optional[float] = None,
           project_dir: str | Path | None = None) -> VisualResult:
    """Submit through the provider registry, or mark every job as deferred.

    Nothing here invents an endpoint, a model name or a price. When the platform
    is not configured the jobs stay `awaiting_platform` and the concept package
    is still complete — that is a valid outcome, not a failure to hide.
    """
    from ..providers import ProviderError, NotConfigured, discover

    out = Path(out_dir)
    renders = out / "concept-visuals"
    renders.mkdir(parents=True, exist_ok=True)
    res = VisualResult(jobs=[dict(j) for j in jobs], authorized=authorize)

    reg = discover(project_dir)
    cap = next((c for c in reg.capabilities() if c.provider == "omniailab"), None)
    res.platform_state = cap.state if cap else "not_registered"
    res.platform_missing = list(cap.missing) if cap else ["provider 未注册"]

    usable = bool(cap and cap.usable and cap.can("image_generation"))

    for job in res.jobs:
        if job.get("status") == "failed":
            res.failed += 1
            continue
        if not usable:
            job["status"] = "awaiting_platform"
            job["reason"] = (
                "平台未配置：缺少 " + "；".join(res.platform_missing)
                if res.platform_missing else "平台不可用"
            )
            res.deferred += 1
            continue
        if not authorize:
            job["status"] = "awaiting_platform"
            job["reason"] = "未授权提交（联网与计费操作需要显式 --authorize）"
            res.deferred += 1
            continue

        params = _params(job, project)
        estimate = None
        provider = reg.get("omniailab")
        if provider is not None:
            try:
                estimate = provider.estimate_cost("image_generation", params)
            except Exception:
                estimate = None
        if estimate is not None:
            res.cost_estimate = (res.cost_estimate or 0.0) + float(estimate)
        if max_cost is not None and res.cost_estimate is not None \
                and res.cost_estimate > max_cost:
            job["status"] = "failed"
            job["reason"] = (f"预估费用 {res.cost_estimate:.2f} 超过上限 {max_cost:.2f}，"
                             "已按授权额度停止提交")
            res.failed += 1
            continue

        try:
            pjob = reg.generate("image_generation", params, renders, prefer="omniailab")
        except (NotConfigured, ProviderError) as exc:
            job["status"] = "failed"
            job["reason"] = f"{type(exc).__name__}: {exc}"
            res.failed += 1
            res.warnings.append(f"{job['job_id']} 提交失败：{job['reason']}")
            continue

        res.submitted += 1
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
            else:
                job["status"] = "failed"
                job["reason"] = "平台返回的文件不是可用的图片"
                res.failed += 1
        else:
            job["status"] = "failed"
            job["reason"] = f"job {pjob.job_id}: {pjob.error or pjob.status}"
            res.failed += 1

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
                      if res.deferred else
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
        f"平台状态：**{res.platform_state}**　授权：{'是' if res.authorized else '否'}",
        "",
        f"任务 {len(res.jobs)} 项：已生成 {res.generated}、待平台 {res.deferred}、"
        f"失败 {res.failed}、已提交 {res.submitted}",
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


__all__ = ["build_jobs", "submit", "write_package", "VisualResult", "STATUS_LABEL"]
