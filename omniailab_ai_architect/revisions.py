"""Revision control and dependency invalidation.

The rule the whole system hangs on: when authoritative geometry changes, every
artifact derived from it becomes *stale* until regenerated. Nothing may be
silently re-issued against an old revision.

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Iterable, List, Optional, Sequence, Set

from .errors import ModelError
from .model import Artifact, ChangeEntry, Element, Project


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass
class InvalidationReport:
    revision: int
    changed: List[str]
    stale: List[str]
    untouched: List[str]

    def to_dict(self) -> Dict[str, object]:
        return {
            "revision": self.revision,
            "changed": list(self.changed),
            "stale": list(self.stale),
            "untouched": list(self.untouched),
        }

    def __str__(self) -> str:
        if not self.stale:
            return f"r{self.revision}: {len(self.changed)} change(s), nothing to invalidate"
        return (
            f"r{self.revision}: {len(self.changed)} change(s) → "
            f"{len(self.stale)} artifact(s) stale: {', '.join(self.stale)}"
        )


def _artifact_graph(project: Project) -> Dict[str, Set[str]]:
    """artifact id -> set of artifact ids that depend on it (transitively)."""
    direct: Dict[str, Set[str]] = {
        a.id: set(d for d in a.depends_on if _is_artifact(project, d)) for a in project.artifacts
    }
    closure: Dict[str, Set[str]] = {}
    visiting: Set[str] = set()

    def walk(node: str) -> Set[str]:
        if node in closure:
            return closure[node]
        if node in visiting:  # cycle guard — broken graphs must not hang the run
            return set()
        visiting.add(node)
        acc: Set[str] = set()
        for child in direct.get(node, ()):  # noqa: B007
            acc.add(child)
            acc |= walk(child)
        visiting.discard(node)
        closure[node] = acc
        return acc

    for a in project.artifacts:
        walk(a.id)
    return closure


def _is_artifact(project: Project, object_id: str) -> bool:
    return any(a.id == object_id for a in project.artifacts)


def dependents_of(project: Project, object_ids: Sequence[str]) -> List[str]:
    """All artifacts that must be regenerated when `object_ids` change."""
    hits: Set[str] = set()
    for a in project.artifacts:
        if any(d in object_ids for d in a.depends_on):
            hits.add(a.id)
    # transitive: an artifact depending on a stale artifact also goes stale
    changed = True
    while changed:
        changed = False
        for a in project.artifacts:
            if a.id in hits:
                continue
            if any(d in hits for d in a.depends_on):
                hits.add(a.id)
                changed = True
    return sorted(hits)


def invalidate(project: Project, changed: Sequence[str]) -> List[str]:
    """Mark every dependent artifact stale. Returns their ids."""
    victims = dependents_of(project, changed)
    for vid in victims:
        project.artifact(vid).status = "stale"
    return victims


def record_change(
    project: Project,
    kind: str,
    detail: str,
    targets: Sequence[str] = (),
    author: str = "omniailab-ai-architect",
    invalidated: Sequence[str] = (),
) -> ChangeEntry:
    entry = ChangeEntry(
        revision=project.revision,
        timestamp=_now(),
        author=author,
        kind=kind,
        targets=list(targets),
        detail=detail,
        invalidated=list(invalidated),
    )
    project.change_log.append(entry)
    return entry


def apply_geometry_change(
    project: Project,
    element_id: str,
    patch: Dict[str, object],
    author: str = "omniailab-ai-architect",
    detail: str = "",
) -> InvalidationReport:
    """Patch an element's geometry, bump revisions, and cascade invalidation.

    This is the single acceptable way to move a wall. Any other path would
    leave the model internally inconsistent.
    """
    element: Element = project.element(element_id)
    for key, value in patch.items():
        if key in ("start", "end", "thickness_mm", "height_mm", "offset_mm", "width_mm"):
            element.geometry[key] = value
        else:
            element.properties[key] = value

    element.revision += 1
    project.revision += 1
    stale = invalidate(project, [element_id])
    record_change(
        project,
        kind="geometry",
        detail=detail or f"{element_id} geometry updated: {patch}",
        targets=[element_id],
        author=author,
        invalidated=stale,
    )
    untouched = [a.id for a in project.artifacts if a.id not in stale]
    return InvalidationReport(
        revision=project.revision, changed=[element_id], stale=stale, untouched=untouched
    )


def apply_space_change(
    project: Project,
    space_id: str,
    patch: Dict[str, object],
    author: str = "omniailab-ai-architect",
    detail: str = "",
) -> InvalidationReport:
    space = project.space(space_id)
    for key, value in patch.items():
        if key in ("boundary_mm2d", "name", "use"):
            setattr(space, key, value)
        else:
            space.properties[key] = value
    space.revision += 1
    project.revision += 1
    stale = invalidate(project, [space_id])
    record_change(
        project,
        kind="geometry",
        detail=detail or f"{space_id} updated: {list(patch)}",
        targets=[space_id],
        author=author,
        invalidated=stale,
    )
    untouched = [a.id for a in project.artifacts if a.id not in stale]
    return InvalidationReport(
        revision=project.revision, changed=[space_id], stale=stale, untouched=untouched
    )


def mark_validated(project: Project, artifact_id: str, path: str = "") -> Artifact:
    a = project.artifact(artifact_id)
    a.status = "validated"
    a.revision = project.revision
    if path:
        a.path = path
    record_change(project, kind="artifact", detail=f"{artifact_id} validated", targets=[artifact_id])
    return a


def register_artifact(
    project: Project,
    artifact_id: str,
    artifact_type: str,
    depends_on: Sequence[str],
    produced_by: str = "",
    path: str = "",
    status: str = "draft",
) -> Artifact:
    try:
        existing = project.artifact(artifact_id)
    except ModelError:
        existing = None
    if existing is not None:
        existing.type = artifact_type
        existing.depends_on = list(depends_on)
        existing.produced_by = produced_by
        existing.path = path
        existing.revision = project.revision
        existing.status = status
        return existing
    a = Artifact(
        id=artifact_id,
        type=artifact_type,
        revision=project.revision,
        status=status,
        path=path,
        depends_on=list(depends_on),
        produced_by=produced_by,
    )
    project.artifacts.append(a)
    return a
