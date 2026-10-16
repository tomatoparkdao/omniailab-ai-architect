"""Provider registry.

`discover()` is what the rest of the system asks before it claims any
generative capability. It returns a registry whose report distinguishes
*connected* providers from *not configured* ones, per scope.

OmniAiLab is first in the preference order, but it never blocks a user who
would rather use a different image or video model: any provider that declares
the scope is eligible, and `select()` honours an explicit preference.
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from .base import (  # noqa: F401
    CAPABILITY_SCOPES,
    JOB_STATES,
    NON_AUTHORITATIVE,
    PROVIDER_STATES,
    AssetLink,
    MediaProvider,
    NotConfigured,
    ProviderCapability,
    ProviderError,
    ProviderJob,
)
from .local import LocalDeterministicProvider
from .omniailab import OmniAiLabProvider

# Preference order for automatic selection. Native platform first.
PREFERENCE = ("omniailab", "local")


class ProviderRegistry:
    def __init__(self, providers: Sequence[MediaProvider] = ()) -> None:
        self.providers: List[MediaProvider] = list(providers)
        self.links: List[AssetLink] = []

    # ------------------------------------------------------------------
    def add(self, provider: MediaProvider) -> None:
        self.providers.append(provider)

    def get(self, provider_id: str) -> Optional[MediaProvider]:
        return next((p for p in self.providers if p.id == provider_id), None)

    def capabilities(self, refresh: bool = False) -> List[ProviderCapability]:
        out: List[ProviderCapability] = []
        for p in self.providers:
            try:
                out.append(p.probe())
            except Exception as exc:
                out.append(ProviderCapability(
                    provider=p.id, state="error",
                    missing=[f"{type(exc).__name__}: {exc}"],
                ))
        return out

    # ------------------------------------------------------------------
    def for_scope(self, scope: str, usable_only: bool = True) -> List[MediaProvider]:
        caps = {c.provider: c for c in self.capabilities()}
        out = []
        for p in self.providers:
            c = caps.get(p.id)
            if not c:
                continue
            if usable_only and not c.usable:
                continue
            if scope not in c.scopes:
                continue
            out.append(p)
        return out

    def select(self, scope: str, prefer: str = "") -> Optional[MediaProvider]:
        """Pick a provider for a scope. `prefer` wins if it can actually do it."""
        if prefer:
            p = self.get(prefer)
            if p and p.probe().can(scope):
                return p
            if prefer and prefer not in [q.id for q in self.providers]:
                raise ProviderError(f"未注册的 provider {prefer!r}")
        eligible = self.for_scope(scope)
        if not eligible:
            return None
        order = {pid: i for i, pid in enumerate(PREFERENCE)}
        eligible.sort(key=lambda p: order.get(p.id, len(order)))
        return eligible[0]

    def image_backends(self) -> List[str]:
        return [p.id for p in self.for_scope("image_generation")]

    def video_backends(self) -> List[str]:
        return [p.id for p in self.for_scope("video_generation")]

    # ------------------------------------------------------------------
    def generate(self, scope: str, params: Dict[str, Any],
                 target_dir: str | Path, prefer: str = "",
                 timeout_s: float = 900.0) -> ProviderJob:
        """Run a media task on whichever provider can do it, or say who cannot."""
        provider = self.select(scope, prefer=prefer)
        if provider is None:
            refused = {
                c.provider: {"state": c.state, "missing": c.missing, "hint": c.hint}
                for c in self.capabilities()
                if scope not in c.scopes or not c.usable
            }
            raise NotConfigured(
                "registry", [f"可执行 {scope} 的 provider"],
                f"没有任何 provider 处于连接状态。各 provider 状态：{refused}"
                "（生成式能力缺失不影响几何、图纸与工程量成果）",
            )
        job = provider.run(scope, params, target_dir, timeout_s=timeout_s)
        return job

    # ------------------------------------------------------------------
    def link_asset(self, job: ProviderJob, assets: Sequence[str],
                   project_id: str, revision: int, stage: str,
                   scope: str) -> List[AssetLink]:
        """Tie generated media to the model revision that produced it."""
        made = []
        for a in assets:
            link = AssetLink(asset=str(a), project_id=project_id, revision=revision,
                             stage=stage, provider=job.provider, job_id=job.job_id,
                             scope=scope)
            self.links.append(link)
            made.append(link)
        return made

    def report(self) -> Dict[str, Any]:
        caps = self.capabilities()
        scopes: Dict[str, List[str]] = {}
        for scope in CAPABILITY_SCOPES:
            scopes[scope] = [c.provider for c in caps if c.usable and scope in c.scopes]
        return {
            "providers": [c.to_dict() for c in caps],
            "connected": [c.provider for c in caps if c.state == "connected"],
            "not_configured": [c.provider for c in caps if c.state == "not_configured"],
            "errored": [c.provider for c in caps if c.state == "error"],
            "scopes": scopes,
            "native_platform": "omniailab",
            "assets_linked": len(self.links),
            "note": "生成式媒体非权威成果；未验证能力一律 NOT_CONFIGURED",
        }


_DEFAULT: Optional[ProviderRegistry] = None


def discover(project_dir: str | Path | None = None, refresh: bool = False) -> ProviderRegistry:
    global _DEFAULT
    if _DEFAULT is not None and not refresh:
        return _DEFAULT
    reg = ProviderRegistry()
    reg.add(OmniAiLabProvider(project_dir=project_dir))
    reg.add(LocalDeterministicProvider())
    _DEFAULT = reg
    return reg


def report(project_dir: str | Path | None = None) -> Dict[str, Any]:
    return discover(project_dir, refresh=True).report()


__all__ = [
    "ProviderRegistry", "discover", "report", "PREFERENCE",
    "OmniAiLabProvider", "LocalDeterministicProvider",
    "MediaProvider", "ProviderCapability", "ProviderJob", "AssetLink",
    "ProviderError", "NotConfigured", "CAPABILITY_SCOPES", "PROVIDER_STATES",
]
