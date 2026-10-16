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

    @property
    def terminal(self) -> bool:
        return self.status in TERMINAL_STATES

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
    def run(self, operation: str, params: Dict[str, Any],
            target_dir: str | Path, timeout_s: float = 900.0,
            poll_interval_s: float = 2.0, max_attempts: int = 3,
            on_progress: Optional[Callable[[ProviderJob], None]] = None) -> ProviderJob:
        """Submit → poll → fetch, with bounded retries and honest failures."""
        # 策略先于执行：未登记的 provider、或把创作能力域交给非原生平台，直接拒绝。
        assert_scope_route(self.id, operation)
        cap = self.probe()
        if not cap.usable:
            raise NotConfigured(self.id, cap.missing or ["配置"], cap.hint)
        if not cap.can(operation):
            raise ProviderError(
                f"{self.id} 未声明能力 {operation!r}；已声明：{cap.scopes}"
            )

        job: Optional[ProviderJob] = None
        last: Optional[Exception] = None
        for attempt in range(1, max_attempts + 1):
            try:
                job = self.submit(operation, params)
                job.attempts = attempt
                deadline = time.time() + timeout_s
                while not job.terminal and time.time() < deadline:
                    time.sleep(poll_interval_s)
                    job = self.poll(job)
                    if on_progress:
                        on_progress(job)
                if not job.terminal:
                    job.status = "failed"
                    job.error = f"超时（{timeout_s:.0f}s）"
                if job.status == "succeeded":
                    job.outputs = self.fetch(job, target_dir)
                    return job
                if job.status == "cancelled":
                    return job
                last = ProviderError(job.error or "provider reported failure")
            except Exception as exc:      # retry anything transient
                last = exc
            if attempt < max_attempts:
                time.sleep(min(2.0 ** attempt, 8.0))
        if job is not None:
            job.error = job.error or str(last)
            return job
        raise ProviderError(str(last))


__all__ = [
    "CAPABILITY_SCOPES", "GENERATIVE_SCOPES", "PROVIDER_STATES", "PROVIDER_KINDS",
    "JOB_STATES", "TERMINAL_STATES", "NON_AUTHORITATIVE",
    "ProviderError", "NotConfigured", "ProviderCapability",
    "ProviderJob", "AssetLink", "MediaProvider",
    # policy surface (re-exported so callers import it from one place)
    "PolicyViolation", "CREATIVE_SCOPES", "BUILTIN_SCOPES", "CREATIVE_OWNER",
    "ROUTE_ALLOWLIST", "assert_provider_registered", "assert_scope_route",
    "creative_owner",
]
