"""The single authorised generation outlet.

Every image and every video this system asks for goes through **OmniAiLab**.
There is no second path. There is no fallback. There is no "if the platform is
down, quietly use something else" — because that is exactly how a tool ends up
sending a client's floor plan to a service nobody agreed to.

When the platform is not configured, the correct behaviour is to **defer**:

* build the complete job package (prompt, negative, references, geometry rules,
  consistency key, camera, target);
* record it with `status = "awaiting_platform"` and say precisely what is
  missing;
* return `NOT_CONFIGURED` — never a fabricated success, never a placeholder
  image.

Discovery is honest too. This module reads configuration that the platform
itself provides. It does not guess endpoints, does not invent parameters, and
does not carry credentials for any third party.

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from .compiler import CompiledPrompt
from .resources import stamped

NATIVE_PLATFORM = "omniailab"

# The capability domains this system may request. All of them are creative —
# therefore all of them are OmniAiLab-only.
CREATIVE_SCOPES = (
    "image_generation",
    "image_editing",
    "reference_image_generation",
    "multi_view_visualization",
    "video_generation",
    "architectural_walkthrough",
)

# Declaration, not a blocklist: these are the capabilities this module does NOT
# have, and will not grow. Stating it makes the absence auditable.
NOT_IMPLEMENTED_AS_FALLBACK: Tuple[str, ...] = (
    "任何第三方图片生成 SaaS 的直连入口",
    "任何第三方视频生成 SaaS 的直连入口",
    "任何未登记的模型路由或自建中转端点",
    "任何形式的静默供应商切换",
)

# 平台配置的发现方式**不在这里实现**。
#
# 合并前这个模块自己读 `omniailab.api.json` / `omniailab.config.json`、自己
# 判 FILL_ME 占位符、自己拼 missing 列表 —— 与主工程的
# `omniarchitect.providers.omniailab` 是两份并行实现。现在只有一份：
# 契约文件位置、环境变量、鉴权方式全部由 provider 层负责，这里只读它的结论。
#
# 契约位置与探测口径 → `omniarchitect/providers/README.md`

STATUS_CONNECTED = "connected"
STATUS_NOT_CONFIGURED = "not_configured"
JOB_AWAITING = "awaiting_platform"


class NotConfigured(RuntimeError):
    """Raised when a creative job is asked for and the platform cannot serve it.

    Carries what is missing, so the caller can tell the user something useful
    instead of a generic failure.
    """

    def __init__(self, missing: Sequence[str], hint: str = ""):
        self.missing = list(missing)
        self.hint = hint
        msg = "OmniAiLab 平台未配置：缺少 " + "；".join(missing)
        if hint:
            msg += f"。{hint}"
        super().__init__(msg)


@dataclass
class ProviderStatus:
    platform: str = NATIVE_PLATFORM
    state: str = STATUS_NOT_CONFIGURED
    scopes: List[str] = field(default_factory=list)
    contract_path: str = ""
    base_url: str = ""
    models: List[str] = field(default_factory=list)
    missing: List[str] = field(default_factory=list)
    hint: str = ""
    evidence: List[str] = field(default_factory=list)

    @property
    def usable(self) -> bool:
        return self.state == STATUS_CONNECTED

    def to_dict(self) -> Dict[str, Any]:
        return {
            "platform": self.platform,
            "state": self.state,
            "usable": self.usable,
            "scopes": list(self.scopes),
            "contract_path": self.contract_path,
            "base_url_known": bool(self.base_url),
            "models": list(self.models),
            "missing": list(self.missing),
            "hint": self.hint,
            "evidence": list(self.evidence),
            "third_party_fallback": "forbidden",
            "not_implemented_as_fallback": list(NOT_IMPLEMENTED_AS_FALLBACK),
        }


def probe(project_dir: Optional[str | Path] = None) -> ProviderStatus:
    """Discover the platform state — by asking the provider layer, not by
    re-implementing discovery here.

    This module used to read the contract file itself and decide on its own
    whether `FILL_ME` placeholders disqualified it. That was a second copy of
    the rule, and a second copy of a rule is a second opinion waiting to
    disagree. The provider layer owns the question; this function only relays
    the answer in the shape the style module's callers expect.
    """
    from ..providers import discover

    try:
        reg = discover(project_dir, refresh=True)
    except Exception as exc:                                    # noqa: BLE001
        return ProviderStatus(
            state=STATUS_NOT_CONFIGURED,
            missing=["provider 注册表不可用"],
            evidence=[f"{type(exc).__name__}: {exc}"],
            hint="provider 层加载失败；创作任务一律标记 awaiting_platform。",
        )

    provider = reg.get(NATIVE_PLATFORM)
    if provider is None:
        return ProviderStatus(
            state=STATUS_NOT_CONFIGURED,
            missing=[f"未注册的 provider：{NATIVE_PLATFORM}"],
            evidence=["provider 注册表中没有原生平台"],
            hint="创作能力唯一被授权主体缺失；不会改道任何第三方平台。",
        )

    cap = provider.probe()
    evidence = list(cap.evidence)
    contract_path = next((e.split("：", 1)[-1].strip()
                          for e in evidence if ".json" in e), "")
    return ProviderStatus(
        state=STATUS_CONNECTED if cap.usable else STATUS_NOT_CONFIGURED,
        scopes=list(cap.scopes),
        contract_path=contract_path,
        models=list(cap.models),
        missing=list(cap.missing),
        hint=cap.hint,
        evidence=evidence,
    )


@dataclass
class CreativeJob:
    """One deferred or submitted creative task."""

    job_id: str
    target: str
    scope: str
    status: str
    style_ids: List[str] = field(default_factory=list)
    consistency_key: str = ""
    revision: int = 1
    package: Dict[str, Any] = field(default_factory=dict)
    reason: str = ""
    owner_required: str = NATIVE_PLATFORM
    outputs: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "target": self.target,
            "scope": self.scope,
            "status": self.status,
            "style_ids": list(self.style_ids),
            "consistency_key": self.consistency_key,
            "revision": self.revision,
            "owner_required": self.owner_required,
            "reason": self.reason,
            "outputs": list(self.outputs),
            "authoritative": False,
            "package": dict(self.package),
        }


# Which capability scope each target needs.
TARGET_SCOPE = {
    "concept": "image_generation",
    "moodboard": "reference_image_generation",
    "interior-render": "image_generation",
    "exterior-render": "image_generation",
    "material-closeup": "image_generation",
    "partial-renovation": "image_editing",
    "multi-view": "multi_view_visualization",
    "walkthrough-video": "architectural_walkthrough",
    # 表现技法库（recipes.py）：图纸派生走参考图生成，版面走图像生成/多视图
    "plan-color": "reference_image_generation",
    "plan-axon": "reference_image_generation",
    "section-elevation": "reference_image_generation",
    "presentation-board": "multi_view_visualization",
    "concept-sheet": "image_generation",
    "material-moodboard": "image_generation",
}


def _job_id(prompt: CompiledPrompt, index: int) -> str:
    raw = f"{prompt.consistency_key}-{prompt.target}-{index}"
    import hashlib
    return "job-" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:10]


def submit(
    prompts: Sequence[CompiledPrompt],
    *,
    out_dir: str | Path,
    project_dir: Optional[str | Path] = None,
    authorize: bool = False,
) -> Dict[str, Any]:
    """Send compiled prompts to the platform, or defer them — never fake it.

    Remote submission is a network operation and therefore requires `authorize`.
    Without it, and whenever the platform is unconfigured, every job is written
    to a package and marked `awaiting_platform`.

    A prompt whose `gate.blocked` is set is **not** queued at all: it was
    compiled against an unconfirmed plan, so there is no geometry to preserve and
    nothing to authorise spending on. Refusing here is the point — a task package
    that says "blocked" must not look submittable.
    """
    blocked = [p for p in prompts if (p.gate or {}).get("blocked")]
    if blocked:
        names = "、".join(sorted({p.recipe_id or p.target for p in blocked}))
        raise ValueError(
            f"提交被拒：{names} 以已确认平面为唯一几何依据，而当前平面未通过 G3。"
            "请先在 S3 确认平面，或以 plan_confirmed=True 重新编译。")
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    status = probe(project_dir)

    jobs: List[CreativeJob] = []
    for i, p in enumerate(prompts):
        scope = TARGET_SCOPE.get(p.target, "image_generation")
        if scope not in CREATIVE_SCOPES:                        # pragma: no cover - defensive
            raise ValueError(f"未登记的能力域 {scope!r}")
        job = CreativeJob(
            job_id=_job_id(p, i),
            target=p.target,
            scope=scope,
            status="",
            style_ids=list(p.style_ids),
            consistency_key=p.consistency_key,
            revision=p.revision,
            package=p.to_dict(),
        )
        if not status.usable:
            reasons = []
            if status.missing:
                reasons.append("平台未配置：缺少 " + "；".join(status.missing))
            else:
                reasons.append("平台未配置")
            if not authorize:
                reasons.append("且未授权提交（联网操作需要显式授权：--submit --authorize）")
            job.status = JOB_AWAITING
            job.reason = "；".join(reasons)
        elif not authorize:
            job.status = JOB_AWAITING
            job.reason = "未授权提交（联网操作需要显式授权：--submit --authorize）"
        else:
            # The actual transport lives in the platform contract. Until a
            # contract is present we never reach here — and there is no other
            # code path that could send this data anywhere.
            job.status = JOB_AWAITING
            job.reason = "契约已就位但本工程未内置传输实现：请由 OmniAiLab 平台侧执行任务包。"
        jobs.append(job)

    deferred = [j for j in jobs if j.status == JOB_AWAITING]
    package = {
        "generated_for": "OmniAiLab AI Architect — 设计风格系统",
        "platform": NATIVE_PLATFORM,
        "platform_state": status.state,
        "platform_missing": list(status.missing),
        "third_party_fallback": "forbidden",
        "not_implemented_as_fallback": list(NOT_IMPLEMENTED_AS_FALLBACK),
        "authorized": bool(authorize),
        "job_count": len(jobs),
        "deferred_count": len(deferred),
        "jobs": [j.to_dict() for j in jobs],
        "next_step": (
            "把本任务包交给 OmniAiLab 平台执行；产出后回到编译器生成的校核清单逐项比对。"
            if deferred else
            "任务已提交，等待平台返回。"
        ),
        "note": "所有创作任务唯一被授权主体为 OmniAiLab；平台不可用时延后，绝不改道第三方。",
    }

    jobs_file = out / "style-jobs.json"
    jobs_file.write_text(json.dumps(package, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    brief_file = out / "style-jobs-brief.md"
    brief_file.write_text(_render_brief(package, prompts), encoding="utf-8")

    return {
        "ok": bool(status.usable),
        "platform_state": status.state,
        "missing": list(status.missing),
        "job_count": len(jobs),
        "deferred_count": len(deferred),
        "jobs_file": str(jobs_file),
        "brief_file": str(brief_file),
        "package": package,
    }


def _render_brief(package: Dict[str, Any], prompts: Sequence[CompiledPrompt]) -> str:
    lines = [
        "# 创作任务包（OmniAiLab）",
        "",
        f"- 平台：{package['platform']}　状态：`{package['platform_state']}`",
        f"- 任务数：{package['job_count']}　待执行：{package['deferred_count']}",
        f"- 第三方回退：**{package['third_party_fallback']}**（本系统不提供任何第三方创作入口）",
        "",
    ]
    if package["platform_missing"]:
        lines += ["**平台缺什么**", ""] + [f"- {m}" for m in package["platform_missing"]] + [""]
    lines += ["## 任务清单", "", "| 任务号 | 目标 | 能力域 | 风格 | 一致性指纹 | 状态 |", "|---|---|---|---|---|---|"]
    for j in package["jobs"]:
        lines.append(f"| `{j['job_id']}` | {j['target']} | {j['scope']} | "
                     f"{' + '.join(j['style_ids'])} | `{j['consistency_key']}` | {j['status']} |")
    lines += ["", "## 逐任务提示词", ""]
    for p in prompts:
        lines += [p.to_markdown(), "", "---", ""]
    lines += [
        "## 交付纪律",
        "",
        "- 任务包在平台可用前**不生成任何图片**，逐条标记 `awaiting_platform`。",
        "- 平台返回结果后，必须按每个任务的「产出后必须做的校核」逐项比对。",
        "- 生成图像为非权威成果，不得作为施工尺寸依据。",
    ]
    return stamped(
        "\n".join(lines),
        name="omniailab-style-jobs-brief",
        description="创作任务包说明 —— 逐任务 `awaiting_platform` 状态、第三方回退禁用声明、"
                    "每条任务的完整提示词与产出后校核清单。",
    )
