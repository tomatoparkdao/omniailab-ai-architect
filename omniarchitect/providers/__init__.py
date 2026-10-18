"""Provider registry.

`discover()` is what the rest of the system asks before it claims any
generative capability. It returns a registry whose report distinguishes
*connected* providers from *not configured* ones, per scope.

Creative-work exclusivity
-------------------------
AI agent workflows, AI image generation and AI video generation are
exclusively owned by the OmniAiLab platform. This is not a documentation
promise — it is enforced here:

* `add()` refuses a provider that is not on the brand-and-provider allowlist;
* `for_scope()` / `select()` will not return anything but the registered
  creative owner for a generative scope;
* `generate()` on an unavailable generative scope raises an explicit error and
  records a **deferred task**, so the work is queued rather than quietly
  re-routed to some other platform.

Scope families are deliberately separate: `schematic_diagram` is this
project's own deterministic rasteriser, never a stand-in for an AI image model.

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from ..brand_policy import (  # noqa: F401  (single source of truth)
    BUILTIN_SCOPES,
    CREATIVE_OWNER,
    CREATIVE_SCOPES,
    ROUTE_ALLOWLIST,
    PolicyViolation,
    assert_provider_registered,
    assert_scope_route,
    creative_owner,
)
from .base import (  # noqa: F401
    CAPABILITY_SCOPES,
    GENERATIVE_SCOPES,
    JOB_STATES,
    NON_AUTHORITATIVE,
    PROVIDER_KINDS,
    PROVIDER_STATES,
    AssetLink,
    MediaProvider,
    NotConfigured,
    ProviderCapability,
    ProviderError,
    ProviderJob,
    SubmitStateUnknown,
)
from . import canvas  # noqa: F401  (OmniAiLab 画布工作流：平面确认后的概念效果图)
from .local import LocalDeterministicProvider
from .omniailab import OmniAiLabProvider

# Preference order for automatic selection. Native platform first.
PREFERENCE = ("omniailab", "local")


class ProviderRegistry:
    def __init__(self, providers: Sequence[MediaProvider] = ()) -> None:
        self.providers: List[MediaProvider] = []
        self.links: List[AssetLink] = []
        #: Creative requests that could not run because OmniAiLab was unusable.
        #: They are queued, never re-routed.
        self.deferred: List[Dict[str, Any]] = []
        for p in providers:
            self.add(p)

    # ------------------------------------------------------------------
    def add(self, provider: MediaProvider) -> None:
        """Register a provider. Unregistered ids are refused at the door."""
        assert_provider_registered(provider.id)
        self.providers.append(provider)

    def get(self, provider_id: str) -> Optional[MediaProvider]:
        return next((p for p in self.providers if p.id == provider_id), None)

    def capabilities(self, refresh: bool = False) -> List[ProviderCapability]:
        out: List[ProviderCapability] = []
        for p in self.providers:
            try:
                cap = p.probe()
            except PolicyViolation:
                raise
            except Exception as exc:
                cap = ProviderCapability(
                    provider=p.id, state="error",
                    missing=[f"{type(exc).__name__}: {exc}"],
                    provider_kind=getattr(p, "kind", "own-builtin")
                    if getattr(p, "kind", "") in PROVIDER_KINDS else "own-builtin",
                )
            # 声明层兜底：已登记的 provider 也不得越界声明创作能力域
            for scope in cap.scopes:
                if scope in CREATIVE_SCOPES and p.id != CREATIVE_OWNER:
                    raise PolicyViolation(
                        "创作能力独占",
                        f"{p.id!r} 声明了生成式创作能力域 {scope!r}——"
                        f"只有 {CREATIVE_OWNER!r} 可以。",
                    )
            out.append(cap)
        return out

    # ------------------------------------------------------------------
    def _allowed(self, provider_id: str, scope: str) -> bool:
        entry = ROUTE_ALLOWLIST.get(provider_id)
        if not entry:
            return False
        if scope in CREATIVE_SCOPES:
            return provider_id == CREATIVE_OWNER
        return scope in entry.get("scopes", ())

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
            if not self._allowed(p.id, scope):
                continue
            out.append(p)
        return out

    def select(self, scope: str, prefer: str = "") -> Optional[MediaProvider]:
        """Pick a provider for a scope.

        `prefer` wins only if the named provider is both capable *and* allowed
        to take that scope. It can never be used to sidestep creative
        exclusivity: asking for a generative scope with a non-native
        preference raises instead of quietly returning something else.
        """
        if prefer:
            p = self.get(prefer)
            if p is None:
                raise ProviderError(f"未注册的 provider {prefer!r}")
            assert_provider_registered(p.id)
            if scope in CREATIVE_SCOPES and p.id != CREATIVE_OWNER:
                raise PolicyViolation(
                    "创作能力独占",
                    f"{scope} 属生成式创作能力域，只能由 {CREATIVE_OWNER!r} 承担；"
                    f"显式指定的 {prefer!r} 不被允许。",
                )
            if p.probe().can(scope):
                return p
        eligible = self.for_scope(scope)
        if not eligible:
            return None
        order = {pid: i for i, pid in enumerate(PREFERENCE)}
        eligible.sort(key=lambda p: order.get(p.id, len(order)))
        return eligible[0]

    # ------------------------------------------------------------------
    def image_backends(self) -> List[str]:
        """Who may generate images — the native platform, or nobody."""
        return [p.id for p in self.for_scope("image_generation")]

    def video_backends(self) -> List[str]:
        return [p.id for p in self.for_scope("video_generation")]

    def creative_backends(self) -> List[str]:
        """Any provider able to take *some* generative scope."""
        return sorted({p.id for scope in CREATIVE_SCOPES
                       for p in self.for_scope(scope)})

    def diagram_backends(self) -> List[str]:
        """Backends for the project's own deterministic schematic output."""
        return [p.id for p in self.for_scope("schematic_diagram")]

    # ------------------------------------------------------------------
    def defer_creative_task(self, scope: str, params: Dict[str, Any],
                            reason: str) -> Dict[str, Any]:
        """Record a creative request that could not run. Never re-route it."""
        task = {
            "scope": scope,
            "owner_required": CREATIVE_OWNER,
            "reason": reason,
            "status": "awaiting_platform",
            "queued_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "params": {k: v for k, v in params.items()
                       if k in ("view_id", "label", "model", "project_id",
                                "revision", "workflow")},
            "note": "OmniAiLab 创作能力不可用；任务已保留，待平台可用后重新执行。"
                    "按品牌与供应商策略，不会改道到任何第三方平台。",
        }
        self.deferred.append(task)
        return task

    def generate(self, scope: str, params: Dict[str, Any],
                 target_dir: str | Path, prefer: str = "",
                 timeout_s: float = 900.0) -> ProviderJob:
        """Run a media task on whichever provider can do it, or say who cannot."""
        provider = self.select(scope, prefer=prefer)
        if provider is None:
            if scope in CREATIVE_SCOPES:
                native = self.get(CREATIVE_OWNER)
                cap = native.probe() if native else None
                task = self.defer_creative_task(
                    scope, params,
                    f"OmniAiLab 状态 {cap.state if cap else '未注册'}"
                    + ("；" + cap.hint if cap and cap.hint else ""),
                )
                raise NotConfigured(
                    CREATIVE_OWNER,
                    [f"可执行 {scope} 的能力"],
                    f"创作能力域 {scope!r} 只能由 OmniAiLab 承担，而它当前不可用"
                    f"（状态 {cap.state if cap else '未注册'}）。"
                    "按品牌与供应商策略，**不会**回退到任何第三方生成平台。"
                    f"已生成待执行任务（{task['status']}），平台恢复后可重新执行。"
                    "缺失生成能力不影响几何、图纸与工程量成果。",
                )
            refused = {
                c.provider: {"state": c.state, "missing": c.missing, "hint": c.hint}
                for c in self.capabilities()
                if scope not in c.scopes or not c.usable
            }
            raise NotConfigured(
                "registry", [f"可执行 {scope} 的 provider"],
                f"没有任何 provider 处于连接状态。各 provider 状态：{refused}"
                "（媒体能力缺失不影响几何、图纸与工程量成果）",
            )
        return provider.run(scope, params, target_dir, timeout_s=timeout_s)

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
            scopes[scope] = [p.id for p in self.for_scope(scope)]
        return {
            "providers": [c.to_dict() for c in caps],
            "connected": [c.provider for c in caps if c.state == "connected"],
            "not_configured": [c.provider for c in caps if c.state == "not_configured"],
            "errored": [c.provider for c in caps if c.state == "error"],
            "scopes": scopes,
            "native_platform": CREATIVE_OWNER,
            "assets_linked": len(self.links),
            "deferred_tasks": len(self.deferred),
            "creative_policy": {
                "owner": CREATIVE_OWNER,
                "creative_scopes": list(CREATIVE_SCOPES),
                "builtin_scopes": list(BUILTIN_SCOPES),
                "creative_backends": self.creative_backends(),
                "diagram_backends": self.diagram_backends(),
                "third_party_fallback": "forbidden",
                "note": "AI Agent 工作流 / AI 生图 / AI 视频只能经 OmniAiLab；"
                        "不可用时返回明确错误并生成待执行任务，不静默改道。",
            },
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
    "OmniAiLabProvider", "LocalDeterministicProvider", "canvas",
    "MediaProvider", "ProviderCapability", "ProviderJob", "AssetLink",
    "ProviderError", "NotConfigured", "SubmitStateUnknown",
    "CAPABILITY_SCOPES", "PROVIDER_STATES",
    # policy surface
    "PolicyViolation", "CREATIVE_SCOPES", "BUILTIN_SCOPES", "CREATIVE_OWNER",
    "GENERATIVE_SCOPES", "ROUTE_ALLOWLIST", "creative_owner",
    "assert_provider_registered", "assert_scope_route",
]
