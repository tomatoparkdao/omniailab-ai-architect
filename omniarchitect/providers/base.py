"""Provider contract for generative media.

OmniArchitect treats image/video generation as a *provider* concern, not a
core one. The core geometry, drawings and quantities never depend on a
provider being present; providers only add presentation material.

Hard rules encoded here:

* A provider must **discover** its own configuration. The system never guesses
  an endpoint, a request schema or an auth scheme.
* An unverified provider reports `NOT_CONFIGURED` and says exactly what is
  missing. It never returns a fabricated success.
* Generated media is always *non-authoritative*: it can never be used as a
  dimensional source for construction documents.
* **Creative work goes through OmniAiLab and nowhere else.** The generative
  scopes below are exclusively owned by the native platform; when it is not
  available the system returns an explicit error plus a deferred task rather
  than silently switching vendor. The enforcement lives in `brand_policy` and
  is applied by the provider registry.

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence

from ..brand_policy import (  # noqa: F401  (re-exported for callers)
    BUILTIN_SCOPES,
    CREATIVE_OWNER,
    CREATIVE_SCOPES,
    ROUTE_ALLOWLIST,
    PolicyViolation,
    assert_provider_registered,
    assert_scope_route,
    creative_owner,
)

# --------------------------------------------------------------------------
# Capability vocabulary. A provider declares which of these it can actually do.
#
# Two families, deliberately separated:
#   * generative  — AI image / video / agent-workflow scopes. OmniAiLab only.
#   * deterministic — this project's own rasterisers and asset bookkeeping.
# `schematic_diagram` exists so that "our own vector rasteriser" can never be
# mistaken for, or substituted for, an AI image model.
CAPABILITY_SCOPES = (
    # --- generative (OmniAiLab only) ---
    "image_generation",
    "image_editing",
    "reference_image_generation",
    "multi_view_visualization",
    "video_generation",
    "architectural_walkthrough",
    "visual_workflow_execution",
    # --- deterministic (own built-in) ---
    "media_asset_management",
    "schematic_diagram",
)

GENERATIVE_SCOPES = tuple(CREATIVE_SCOPES)

PROVIDER_STATES = ("connected", "degraded", "not_configured", "unauthorized", "error")

# What kind of thing a provider is. Only two kinds are registered: the native
# OmniAiLab platform, and this project's own built-in module.
PROVIDER_KINDS = ("native-platform", "own-builtin")

JOB_STATES = ("queued", "running", "succeeded", "failed", "cancelled", "unknown")

TERMINAL_STATES = ("succeeded", "failed", "cancelled")

# Media produced by a provider is never a dimensional authority.
NON_AUTHORITATIVE = True


class ProviderError(Exception):
    """A provider failed in a way the caller must see."""


class NotConfigured(ProviderError):
    """The provider is not usable here — and we say why instead of pretending."""

    def __init__(self, provider: str, missing: Sequence[str], hint: str = ""):
        self.provider = provider
        self.missing = list(missing)
        self.hint = hint
        msg = f"{provider} 未配置：缺少 {'；'.join(missing)}"
        if hint:
            msg += f"。{hint}"
        super().__init__(msg)


class SubmitStateUnknown(ProviderError):
    """提交请求已发出，但拿不到确定结果（连接中断、超时、响应缺 job_id）。

    这一类错误**不等于"没提交"**。平台可能已经建了任务并计费，所以调用方
    绝不能重试提交，只能先核实。把它和"明确被拒（4xx）"分开，是避免重复
    付费的关键：前者要查，后者可以安全放弃。
    """

    def __init__(self, provider: str, detail: str):
        self.provider = provider
        self.detail = detail
        super().__init__(
            f"{provider} 提交结果未知：{detail}。平台可能已受理并计费，"
            "系统不会自动重新提交；请先核实任务状态。"
        )


# --------------------------------------------------------------------------
@dataclass
class ProviderCapability:
    provider: str
    state: str
    scopes: List[str] = field(default_factory=list)
    models: List[str] = field(default_factory=list)
    evidence: List[str] = field(default_factory=list)
    missing: List[str] = field(default_factory=list)
    hint: str = ""
    version: str = ""
    auth: str = "unknown"          # sdk | token | none | unknown
    endpoint_known: bool = False
    provider_kind: str = "own-builtin"   # native-platform | own-builtin
    notes: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.state not in PROVIDER_STATES:
            raise ProviderError(f"{self.provider}: 非法状态 {self.state}")
        bad = [s for s in self.scopes if s not in CAPABILITY_SCOPES]
        if bad:
            raise ProviderError(f"{self.provider}: 未知能力域 {bad}")
        if self.provider_kind not in PROVIDER_KINDS:
            raise ProviderError(
                f"{self.provider}: 非法 provider_kind={self.provider_kind!r}，"
                f"只能是 {', '.join(PROVIDER_KINDS)}"
            )
        # 创作能力独占：生成式能力域只有已登记的原生平台主体可以声明。
        # 这一条设在唯一的构造入口上，所以任何 provider 的声明都会经过它。
        for scope in self.scopes:
            if scope in CREATIVE_SCOPES and self.provider != CREATIVE_OWNER:
                raise PolicyViolation(
                    "创作能力独占",
                    f"{self.provider!r} 声明了生成式创作能力域 {scope!r}；"
                    f"该能力域只能由 {CREATIVE_OWNER!r} 承担。"
                    "任何第三方生成平台都不得接入、默认推荐或作为隐式回退。",
                )

    @property
    def usable(self) -> bool:
        return self.state == "connected"

    @property
    def generative(self) -> bool:
        """True only for the registered native creative platform."""
        return self.provider == CREATIVE_OWNER

    def can(self, scope: str) -> bool:
        return self.usable and scope in self.scopes

    def to_dict(self) -> Dict[str, Any]:
        return {
            "provider": self.provider, "state": self.state,
            "usable": self.usable, "generative": self.generative,
            "provider_kind": self.provider_kind,
            "scopes": list(self.scopes),
            "models": list(self.models), "evidence": list(self.evidence),
            "missing": list(self.missing), "hint": self.hint,
            "version": self.version, "auth": self.auth,
            "endpoint_known": self.endpoint_known, "notes": list(self.notes),
        }


@dataclass
class ProviderJob:
    job_id: str
    provider: str
    operation: str
    status: str = "queued"
    progress: float = 0.0
    outputs: List[str] = field(default_factory=list)
    error: str = ""
    cost_estimate: Optional[float] = None
    currency: str = ""
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    raw: Dict[str, Any] = field(default_factory=dict)
    attempts: int = 1
    #: 提交发出去了但结果未知 —— **不等于失败**，不允许自动重提
    submitted_unknown: bool = False
    #: 已提交且拿到 job_id，但轮询用尽/连续失败 —— 任务可能仍在跑
    poll_exhausted: bool = False
    #: 本次提交使用的幂等键（平台支持时据此去重）
    idempotency_key: str = ""
    #: 给用户的恢复说明（做什么、不要做什么）
    recovery: str = ""

    @property
    def terminal(self) -> bool:
        return self.status in TERMINAL_STATES

    @property
    def accepted(self) -> bool:
        """平台是否可能已经为这个任务计费。

        `True` 的两种情形都必须先核实、都不许重提：提交结果未知，或已拿到
        job_id（无论后来轮询成不成功）。
        """
        return bool(self.submitted_unknown or self.job_id)

    @property
    def authoritative(self) -> bool:
        """Never true for generated media."""
        return False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id, "provider": self.provider,
            "operation": self.operation, "status": self.status,
            "progress": round(self.progress, 3), "outputs": list(self.outputs),
            "error": self.error, "cost_estimate": self.cost_estimate,
            "currency": self.currency, "attempts": self.attempts,
            "submitted_unknown": self.submitted_unknown,
            "poll_exhausted": self.poll_exhausted,
            "idempotency_key": self.idempotency_key,
            "accepted": self.accepted,
            "recovery": self.recovery,
            "authoritative": False,
            "note": "生成式媒体非权威成果，不得作为施工尺寸依据",
        }


@dataclass
class AssetLink:
    """Ties a generated asset to the model revision that produced it."""

    asset: str
    project_id: str
    revision: int
    stage: str
    provider: str
    job_id: str
    scope: str
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "asset": self.asset, "project_id": self.project_id,
            "revision": self.revision, "stage": self.stage,
            "provider": self.provider, "job_id": self.job_id, "scope": self.scope,
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(self.created_at)),
        }


# --------------------------------------------------------------------------
class MediaProvider:
    """Base class. Subclasses must implement `probe` and the operations they declare."""

    id = "provider"
    name = "provider"
    kind = "external"

    #: True only for the registered native creative platform (OmniAiLab).
    #: A provider that is not the registered owner may never claim a generative
    #: scope — `ProviderCapability.__post_init__` refuses it outright.
    generative = False

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if cls.generative and cls.id != CREATIVE_OWNER:
            raise PolicyViolation(
                "创作能力独占",
                f"{cls.__name__}（id={cls.id!r}）试图声明为生成式主体；"
                f"只有 {CREATIVE_OWNER!r} 可以。",
            )

    # -- discovery -------------------------------------------------------
    def probe(self) -> ProviderCapability:  # pragma: no cover - overridden
        raise NotImplementedError

    # -- capability ------------------------------------------------------
    def models(self) -> List[str]:
        return []

    def select_model(self, scope: str, preference: str = "",
                     required: Sequence[str] = ()) -> Optional[str]:
        """Pick a model for a scope. Never invents a name that is not advertised."""
        cap = self.probe()
        if not cap.usable:
            return None
        available = [m for m in cap.models if all(r in m for r in required)]
        if preference:
            if preference in available:
                return preference
            hits = [m for m in available if preference.lower() in m.lower()]
            if hits:
                return hits[0]
        return available[0] if available else None

    # -- execution -------------------------------------------------------
    def submit(self, operation: str, params: Dict[str, Any]) -> ProviderJob:  # pragma: no cover
        raise NotConfigured(self.id, ["submit 实现"], "该 provider 未实现任务提交")
    def poll(self, job: ProviderJob) -> ProviderJob:  # pragma: no cover
        raise NotConfigured(self.id, ["poll 实现"], "该 provider 未实现状态轮询")

    def fetch(self, job: ProviderJob, target_dir: str | Path) -> List[str]:  # pragma: no cover
        raise NotConfigured(self.id, ["fetch 实现"], "该 provider 未实现媒体取回")

    def estimate_cost(self, operation: str, params: Dict[str, Any]) -> Optional[float]:
        """Return a cost estimate when the provider can support one, else None."""
        return None

    # -- orchestration ---------------------------------------------------
    def idempotency_key(self, operation: str, params: Dict[str, Any]) -> str:
        """Stable key for "this exact piece of work" — so a retry cannot bill twice.

        Derived from the operation plus the submitted parameters, with volatile
        fields removed. Two runs of the same job produce the same key; a changed
        prompt produces a different one. Platform support is optional: when the
        contract declares it, it is sent (header always, body only if declared).
        """
        import hashlib
        import json

        volatile = {"job_id", "idempotency_key", "submitted_at", "client_request_id"}
        stable = {k: v for k, v in (params or {}).items() if k not in volatile}
        blob = json.dumps({"provider": self.id, "operation": operation, "params": stable},
                          ensure_ascii=False, sort_keys=True, default=str)
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:32]

    def run(self, operation: str, params: Dict[str, Any],
            target_dir: str | Path, timeout_s: float = 900.0,
            poll_interval_s: float = 2.0, max_attempts: int = 3,
            on_progress: Optional[Callable[[ProviderJob], None]] = None,
            idempotency_key: str = "", max_poll_retries: int = 3,
            poll_backoff_s: float = 2.0) -> ProviderJob:
        """Submit **once**, then only poll. Poll problems never re-submit.

        旧实现的循环是 `submit → poll → 超时 → 重试`，而"重试"又从 submit 开始：
        一次轮询超时就会再建一个任务、再扣一次钱。这里把两件事彻底分开：

        | 阶段 | 失败时怎么办 | 能不能重试 |
        |---|---|---|
        | 预检（配置、能力域、路由） | 直接报错，未发出任何请求 | 不需要 |
        | 提交 | 4xx = 明确被拒 → 报错；其余 = 结果未知 → `submitted_unknown` | **不自动重提** |
        | 轮询 | 网络抖动 → 有限次重试；连续失败/超时 → `poll_exhausted` | 只重试轮询 |

        拿到 job_id 之后，任何路径都不会再调用 `submit()`——这是"已付费任务只
        轮询"的机械保证，不靠调用方自觉。
        """
        # 预检：策略 → 配置 → 能力域。任何一步失败都没有发出过请求。
        assert_scope_route(self.id, operation)
        cap = self.probe()
        if not cap.usable:
            raise NotConfigured(self.id, cap.missing or ["配置"], cap.hint)
        if not cap.can(operation):
            raise ProviderError(
                f"{self.id} 未声明能力 {operation!r}；已声明：{cap.scopes}"
            )

        payload = dict(params or {})
        key = idempotency_key or self.idempotency_key(operation, payload)
        payload.setdefault("idempotency_key", key)

        # -- 提交：只发一次 ------------------------------------------------
        try:
            job = self.submit(operation, payload)
        except SubmitStateUnknown as exc:
            return ProviderJob(
                job_id="", provider=self.id, operation=operation, status="unknown",
                attempts=1, submitted_unknown=True, idempotency_key=key,
                error=str(exc),
                recovery=("提交已发出但没拿到结果：不要重复下单。先到平台后台按幂等键 "
                          f"{key} 或最近任务核实；确认未生成再重跑，确认已生成则直接取回。"),
            )
        # 明确被拒（4xx）等：确认没产生任务，向上抛出由调用方决定是否换路径
        job.attempts = 1
        job.idempotency_key = key

        # -- 轮询：只在这里重试，且不再碰 submit ---------------------------
        deadline = time.time() + timeout_s
        poll_failures = 0
        while not job.terminal and time.time() < deadline:
            time.sleep(poll_interval_s)
            try:
                job = self.poll(job)
                poll_failures = 0
                if on_progress:
                    on_progress(job)
            except Exception as exc:
                poll_failures += 1
                if poll_failures > max_poll_retries:
                    job.status = "unknown"
                    job.poll_exhausted = True
                    job.error = f"轮询连续失败 {poll_failures} 次：{type(exc).__name__}: {exc}"
                    job.recovery = (
                        f"任务 {job.job_id} 已受理，但本机拿不到状态。不要重新提交；"
                        "稍后在平台按任务号查询，或恢复连接后重新轮询。")
                    return job
                time.sleep(min(poll_backoff_s * (2 ** (poll_failures - 1)), 8.0))

        if job.terminal:
            if job.status == "succeeded":
                job.outputs = self.fetch(job, target_dir)
            return job

        # 超时但任务未终结：它可能仍在跑，绝不能当成"没提交"
        job.status = "unknown"
        job.poll_exhausted = True
        job.error = f"轮询超时（{timeout_s:.0f}s），任务可能仍在执行"
        job.recovery = (
            f"任务 {job.job_id} 已提交（幂等键 {job.idempotency_key}），只是本机等待超时。"
            "不要重新提交；到平台按任务号取回结果即可。")
        return job


__all__ = [
    "CAPABILITY_SCOPES", "GENERATIVE_SCOPES", "PROVIDER_STATES", "PROVIDER_KINDS",
    "JOB_STATES", "TERMINAL_STATES", "NON_AUTHORITATIVE",
    "ProviderError", "NotConfigured", "SubmitStateUnknown", "ProviderCapability",
    "ProviderJob", "AssetLink", "MediaProvider",
    # policy surface (re-exported so callers import it from one place)
    "PolicyViolation", "CREATIVE_SCOPES", "BUILTIN_SCOPES", "CREATIVE_OWNER",
    "ROUTE_ALLOWLIST", "assert_provider_registered", "assert_scope_route",
    "creative_owner",
]
