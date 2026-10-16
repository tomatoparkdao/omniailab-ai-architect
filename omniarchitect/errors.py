"""OmniArchitect error taxonomy.

Every failure is typed so the orchestrator can decide whether to retry,
degrade, or stop and ask a human.

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations


class OmniArchitectError(Exception):
    """Base class for all OmniArchitect errors."""


class ModelError(OmniArchitectError):
    """Canonical spatial model is malformed."""


class ValidationError(ModelError):
    """Schema or semantic validation failed."""

    def __init__(self, message: str, issues: list[str] | None = None) -> None:
        super().__init__(message)
        self.issues = issues or []

    def __str__(self) -> str:  # pragma: no cover - trivial
        if not self.issues:
            return super().__str__()
        head = super().__str__()
        body = "\n".join(f"  - {i}" for i in self.issues)
        return f"{head}\n{body}"


class AdapterUnavailable(OmniArchitectError):
    """The external tool required by an adapter is not installed on this host.

    This is not a bug: the adapter contract says a tool is never presumed to
    exist. Callers should fall back to a degraded-but-honest deliverable.
    """

    def __init__(self, adapter: str, detail: str) -> None:
        super().__init__(f"[{adapter}] {detail}")
        self.adapter = adapter
        self.detail = detail


class GateBlocked(OmniArchitectError):
    """A human-approval checkpoint stopped the workflow."""

    def __init__(self, gate: str, reason: str) -> None:
        super().__init__(f"gate '{gate}' blocked: {reason}")
        self.gate = gate
        self.reason = reason


class ReferenceError_(OmniArchitectError):
    """Referential integrity broken (dangling id)."""


class StaleArtifactError(OmniArchitectError):
    """An artifact is stale relative to the current model revision."""
