"""Canonical Spatial Model (CSM).

Single source of truth for authoritative geometry, dimensions, openings,
levels, spaces, elements and the change log. Every downstream artifact is
derived from this model; nothing else may claim dimensional authority.

Units are millimetres everywhere. Text-to-image output is *never* allowed to
feed back into this model.

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from .errors import ModelError, ValidationError

MM_PER_M = 1000.0
SCHEMA_VERSION = "1.0.0"

ELEMENT_TYPES = (
    "wall", "door", "window", "slab", "ceiling",
    "furniture", "fixture", "other",
)
ARTIFACT_STATUS = (
    "draft", "validated", "stale", "needs_review", "issued",
)


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _num(value: Any, default: float = 0.0) -> float:
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


# --------------------------------------------------------------------------
# geometry helpers (kept dependency-free so the model can always be loaded)
# --------------------------------------------------------------------------
def polygon_area_mm2(points: Sequence[Sequence[float]]) -> float:
    """Signed shoelace area; returns absolute area in mm^2."""
    if len(points) < 3:
        return 0.0
    total = 0.0
    n = len(points)
    for i in range(n):
        x1, y1 = points[i][0], points[i][1]
        x2, y2 = points[(i + 1) % n][0], points[(i + 1) % n][1]
        total += x1 * y2 - x2 * y1
    return abs(total) / 2.0


def polygon_centroid(points: Sequence[Sequence[float]]) -> Tuple[float, float]:
    if not points:
        return (0.0, 0.0)
    a = 0.0
    cx = 0.0
    cy = 0.0
    n = len(points)
    for i in range(n):
        x1, y1 = points[i][0], points[i][1]
        x2, y2 = points[(i + 1) % n][0], points[(i + 1) % n][1]
        cross = x1 * y2 - x2 * y1
        a += cross
        cx += (x1 + x2) * cross
        cy += (y1 + y2) * cross
    if abs(a) < 1e-9:
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        return (sum(xs) / len(xs), sum(ys) / len(ys))
    a *= 0.5
    return (cx / (6.0 * a), cy / (6.0 * a))


# --------------------------------------------------------------------------
@dataclass
class Level:
    id: str
    elevation_mm: float = 0.0
    name: str = ""
    height_mm: float = 2900.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "elevation_mm": self.elevation_mm,
            "name": self.name,
            "height_mm": self.height_mm,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Level":
        return cls(
            id=str(d["id"]),
            elevation_mm=_num(d.get("elevation_mm")),
            name=str(d.get("name") or ""),
            height_mm=_num(d.get("height_mm"), 2900.0),
        )


@dataclass
class Space:
    id: str
    level_id: str
    boundary_mm2d: List[List[float]] = field(default_factory=list)
    name: str = ""
    use: str = ""
    source: str = "generated"
    revision: int = 1
    confidence: float = 1.0
    properties: Dict[str, Any] = field(default_factory=dict)

    @property
    def area_m2(self) -> float:
        return polygon_area_mm2(self.boundary_mm2d) / (MM_PER_M ** 2)

    @property
    def centroid(self) -> Tuple[float, float]:
        return polygon_centroid(self.boundary_mm2d)

    def bbox(self) -> Tuple[float, float, float, float]:
        if not self.boundary_mm2d:
            return (0.0, 0.0, 0.0, 0.0)
        xs = [p[0] for p in self.boundary_mm2d]
        ys = [p[1] for p in self.boundary_mm2d]
        return (min(xs), min(ys), max(xs), max(ys))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "level_id": self.level_id,
            "name": self.name,
            "use": self.use,
            "boundary_mm2d": [[round(p[0], 3), round(p[1], 3)] for p in self.boundary_mm2d],
            "source": self.source,
            "revision": self.revision,
            "confidence": self.confidence,
            "properties": self.properties,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Space":
        return cls(
            id=str(d["id"]),
            level_id=str(d["level_id"]),
            boundary_mm2d=[[_num(p[0]), _num(p[1])] for p in d.get("boundary_mm2d", [])],
            name=str(d.get("name") or ""),
            use=str(d.get("use") or ""),
            source=str(d.get("source") or "generated"),
            revision=int(d.get("revision", 1)),
            confidence=float(d.get("confidence", 1.0)),
            properties=dict(d.get("properties") or {}),
        )


@dataclass
class Element:
    id: str
    type: str
    level_id: str
    geometry: Dict[str, Any] = field(default_factory=dict)
    source: str = "generated"
    revision: int = 1
    properties: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    uncertain: bool = False
    """True when the element was inferred (e.g. a suspected structural wall read
    from a raster plan) and must be confirmed on site before use."""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "level_id": self.level_id,
            "geometry": dict(self.geometry),
            "properties": dict(self.properties),
            "source": self.source,
            "revision": self.revision,
            "confidence": self.confidence,
            "uncertain": self.uncertain,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Element":
        return cls(
            id=str(d["id"]),
            type=str(d["type"]),
            level_id=str(d.get("level_id") or ""),
            geometry=dict(d.get("geometry") or {}),
            properties=dict(d.get("properties") or {}),
            source=str(d.get("source") or "generated"),
            revision=int(d.get("revision", 1)),
            confidence=float(d.get("confidence", 1.0)),
            uncertain=bool(d.get("uncertain", False)),
        )

    # -- typed helpers ----------------------------------------------------
    @property
    def is_opening(self) -> bool:
        return self.type in ("door", "window")

    def wall_axis(self) -> Optional[Tuple[Tuple[float, float], Tuple[float, float]]]:
        if self.type != "wall":
            return None
        g = self.geometry
        if "start" not in g or "end" not in g:
            return None
        return (
            (float(g["start"][0]), float(g["start"][1])),
            (float(g["end"][0]), float(g["end"][1])),
        )

    def wall_length_mm(self) -> float:
        axis = self.wall_axis()
        if not axis:
            return 0.0
        (x1, y1), (x2, y2) = axis
        return math.hypot(x2 - x1, y2 - y1)


@dataclass
class Artifact:
    id: str
    type: str
    revision: int = 1
    status: str = "draft"
    path: str = ""
    depends_on: List[str] = field(default_factory=list)
    produced_by: str = ""
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "revision": self.revision,
            "status": self.status,
            "path": self.path,
            "depends_on": list(self.depends_on),
            "produced_by": self.produced_by,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Artifact":
        return cls(
            id=str(d["id"]),
            type=str(d["type"]),
            revision=int(d.get("revision", 1)),
            status=str(d.get("status") or "draft"),
            path=str(d.get("path") or ""),
            depends_on=[str(x) for x in (d.get("depends_on") or [])],
            produced_by=str(d.get("produced_by") or ""),
            notes=str(d.get("notes") or ""),
        )


@dataclass
class ChangeEntry:
    revision: int
    timestamp: str
    author: str
    kind: str
    targets: List[str] = field(default_factory=list)
    detail: str = ""
    invalidated: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "revision": self.revision,
            "timestamp": self.timestamp,
            "author": self.author,
            "kind": self.kind,
            "targets": list(self.targets),
            "detail": self.detail,
            "invalidated": list(self.invalidated),
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ChangeEntry":
        return cls(
            revision=int(d.get("revision", 1)),
            timestamp=str(d.get("timestamp") or ""),
            author=str(d.get("author") or ""),
            kind=str(d.get("kind") or ""),
            targets=[str(x) for x in (d.get("targets") or [])],
            detail=str(d.get("detail") or ""),
            invalidated=[str(x) for x in (d.get("invalidated") or [])],
        )


@dataclass
class Project:
    """The canonical project document."""

    project_id: str
    revision: int = 1
    units: str = "mm"
    coordinate_system: Dict[str, Any] = field(
        default_factory=lambda: {"origin": [0.0, 0.0, 0.0], "axes": "X east, Y north, Z up"}
    )
    levels: List[Level] = field(default_factory=list)
    spaces: List[Space] = field(default_factory=list)
    elements: List[Element] = field(default_factory=list)
    artifacts: List[Artifact] = field(default_factory=list)
    change_log: List[ChangeEntry] = field(default_factory=list)

    # --- v1.0 optional extensions (schema-backwards compatible) -----------
    name: str = ""
    schema_version: str = SCHEMA_VERSION
    program: List[Dict[str, Any]] = field(default_factory=list)
    constraints: Dict[str, Any] = field(default_factory=dict)
    assumptions: List[str] = field(default_factory=list)
    sources: List[Dict[str, Any]] = field(default_factory=list)
    meta: Dict[str, Any] = field(default_factory=dict)

    # -- lookups -----------------------------------------------------------
    def element(self, element_id: str) -> Element:
        for e in self.elements:
            if e.id == element_id:
                return e
        raise ModelError(f"element '{element_id}' not found")

    def space(self, space_id: str) -> Space:
        for s in self.spaces:
            if s.id == space_id:
                return s
        raise ModelError(f"space '{space_id}' not found")

    def artifact(self, artifact_id: str) -> Artifact:
        for a in self.artifacts:
            if a.id == artifact_id:
                return a
        raise ModelError(f"artifact '{artifact_id}' not found")

    def has(self, object_id: str) -> bool:
        return any(
            o.id == object_id for o in (*self.spaces, *self.elements, *self.artifacts)
        )

    def level(self, level_id: str) -> Level:
        for lv in self.levels:
            if lv.id == level_id:
                return lv
        raise ModelError(f"level '{level_id}' not found")

    def by_type(self, element_type: str) -> List[Element]:
        return [e for e in self.elements if e.type == element_type]

    def spaces_on(self, level_id: str) -> List[Space]:
        return [s for s in self.spaces if s.level_id == level_id]

    @property
    def usable_area_m2(self) -> float:
        return sum(s.area_m2 for s in self.spaces)

    def set_artifact_status(self, artifact_id: str, status: str) -> None:
        if status not in ARTIFACT_STATUS:
            raise ValidationError(f"unknown artifact status '{status}'")
        self.artifact(artifact_id).status = status

    # -- serialisation -----------------------------------------------------
    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "project_id": self.project_id,
            "name": self.name,
            "revision": self.revision,
            "units": self.units,
            "coordinate_system": dict(self.coordinate_system),
            "levels": [l.to_dict() for l in self.levels],
            "spaces": [s.to_dict() for s in self.spaces],
            "elements": [e.to_dict() for e in self.elements],
            "artifacts": [a.to_dict() for a in self.artifacts],
            "change_log": [c.to_dict() for c in self.change_log],
            "program": list(self.program),
            "constraints": dict(self.constraints),
            "assumptions": list(self.assumptions),
            "sources": list(self.sources),
            "meta": dict(self.meta),
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Project":
        return cls(
            project_id=str(d["project_id"]),
            revision=int(d.get("revision", 1)),
            units=str(d.get("units", "mm")),
            coordinate_system=dict(d.get("coordinate_system") or {}),
            levels=[Level.from_dict(x) for x in d.get("levels", [])],
            spaces=[Space.from_dict(x) for x in d.get("spaces", [])],
            elements=[Element.from_dict(x) for x in d.get("elements", [])],
            artifacts=[Artifact.from_dict(x) for x in d.get("artifacts", [])],
            change_log=[ChangeEntry.from_dict(x) for x in d.get("change_log", [])],
            name=str(d.get("name") or ""),
            schema_version=str(d.get("schema_version") or SCHEMA_VERSION),
            program=list(d.get("program") or []),
            constraints=dict(d.get("constraints") or {}),
            assumptions=[str(x) for x in (d.get("assumptions") or [])],
            sources=list(d.get("sources") or []),
            meta=dict(d.get("meta") or {}),
        )

    def save(self, path: str | Path) -> Path:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(
            json.dumps(self.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return p

    @classmethod
    def load(cls, path: str | Path) -> "Project":
        p = Path(path)
        if not p.exists():
            raise ModelError(f"project file not found: {p}")
        return cls.from_dict(json.loads(p.read_text(encoding="utf-8")))

    def fork(self) -> "Project":
        return Project.from_dict(json.loads(json.dumps(self.to_dict())))


# --------------------------------------------------------------------------
# validation
# --------------------------------------------------------------------------
def validate_schema(project: Project, schema_path: str | Path | None = None) -> None:
    """Validate against the JSON Schema shipped with the skill.

    Uses `jsonschema` when it is installed; otherwise falls back to a small
    built-in subset validator covering the keywords this schema actually uses,
    so verification never depends on a package that may not be installable.
    """
    if schema_path is None:
        from .paths import SCHEMAS
        schema_path = SCHEMAS / "project.schema.json"
    schema = json.loads(Path(schema_path).read_text(encoding="utf-8"))
    instance = project.to_dict()
    try:
        import jsonschema
    except Exception:
        issues = _validate_subset(schema, instance)
    else:
        validator = jsonschema.Draft202012Validator(schema)
        errors = sorted(validator.iter_errors(instance), key=lambda e: list(e.path))
        issues = [
            f"{'/'.join(str(p) for p in e.path) or '<root>'}: {e.message}" for e in errors
        ]
    if issues:
        raise ValidationError(f"{len(issues)} schema violation(s)", issues)


def _validate_subset(schema: dict, instance, path: str = "", errors: Optional[list] = None) -> list:
    """Minimal JSON-Schema subset validator (type/required/enum/items/limits)."""
    issues = errors if errors is not None else []
    where = path or "<root>"

    expected = schema.get("type")
    if expected:
        ok = {
            "object": lambda v: isinstance(v, dict),
            "array": lambda v: isinstance(v, list),
            "string": lambda v: isinstance(v, str),
            "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
            "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
            "boolean": lambda v: isinstance(v, bool),
            "null": lambda v: v is None,
        }.get(expected, lambda v: True)
        if not ok(instance):
            issues.append(f"{where}: expected {expected}, got {type(instance).__name__}")
            return issues

    if "enum" in schema and instance not in schema["enum"]:
        issues.append(f"{where}: {instance!r} not in {schema['enum']}")

    if isinstance(instance, (int, float)) and not isinstance(instance, bool):
        if "minimum" in schema and instance < schema["minimum"]:
            issues.append(f"{where}: {instance} < minimum {schema['minimum']}")

    if isinstance(instance, dict):
        for key in schema.get("required", []):
            if key not in instance:
                issues.append(f"{where}: missing required property '{key}'")
        for key, sub in (schema.get("properties") or {}).items():
            if key in instance:
                _validate_subset(sub, instance[key], f"{path}/{key}" if path else key, issues)

    if isinstance(instance, list):
        if "minItems" in schema and len(instance) < schema["minItems"]:
            issues.append(f"{where}: needs >= {schema['minItems']} items")
        if "maxItems" in schema and len(instance) > schema["maxItems"]:
            issues.append(f"{where}: needs <= {schema['maxItems']} items")
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for i, item in enumerate(instance):
                _validate_subset(item_schema, item, f"{path}/{i}" if path else str(i), issues)
    return issues


def validate_semantics(project: Project) -> None:
    """Checks the schema cannot express: referential integrity and dimensional sanity."""
    issues: List[str] = []

    if project.units != "mm":
        issues.append(f"units must be 'mm', got '{project.units}'")

    level_ids = {l.id for l in project.levels}
    if not level_ids:
        issues.append("project has no levels")

    seen: Dict[str, str] = {}
    for obj in (*project.spaces, *project.elements, *project.artifacts):
        if obj.id in seen:
            issues.append(f"duplicate id '{obj.id}'")
        seen[obj.id] = type(obj).__name__

    for s in project.spaces:
        if s.level_id not in level_ids:
            issues.append(f"space {s.id}: unknown level '{s.level_id}'")
        if len(s.boundary_mm2d) < 3:
            issues.append(f"space {s.id}: boundary needs >= 3 points")
        if s.area_m2 <= 0.01:
            issues.append(f"space {s.id}: non-positive area")

    wall_by_id = {e.id: e for e in project.by_type("wall")}

    for e in project.elements:
        if e.level_id and e.level_id not in level_ids:
            issues.append(f"element {e.id}: unknown level '{e.level_id}'")
        if e.type not in ELEMENT_TYPES:
            issues.append(f"element {e.id}: unknown type '{e.type}'")

        if e.type == "wall":
            axis = e.wall_axis()
            if axis is None:
                issues.append(f"element {e.id}: wall needs start/end points")
                continue
            if e.wall_length_mm() < 50:
                issues.append(f"element {e.id}: wall shorter than 50mm")
            th = _num(e.geometry.get("thickness_mm"), 0)
            if th <= 0:
                issues.append(f"element {e.id}: wall thickness must be > 0")

        if e.is_opening:
            host = str(e.geometry.get("host_wall") or "")
            if not host:
                issues.append(f"element {e.id}: opening has no host wall")
                continue
            wall = wall_by_id.get(host)
            if wall is None:
                issues.append(f"element {e.id}: host wall '{host}' does not exist")
                continue
            width = _num(e.geometry.get("width_mm"), 0)
            offset = _num(e.geometry.get("offset_mm"), 0)
            if width <= 0:
                issues.append(f"element {e.id}: opening width must be > 0")
            if offset < -1 or offset + width > wall.wall_length_mm() + 1:
                issues.append(
                    f"element {e.id}: opening ({offset:.0f}+{width:.0f}) "
                    f"exceeds host wall {host} length {wall.wall_length_mm():.0f}"
                )

    # doors must be reachable: every enclosed space needs at least one opening
    door_hosts = {
        str(e.geometry.get("host_wall"))
        for e in project.by_type("door")
        if e.geometry.get("host_wall")
    }
    for s in project.spaces:
        if s.properties.get("requires_door", True) and s.use not in ("envelope", "outdoor"):
            touching = _walls_touching_space(project, s)
            if touching and not (touching & door_hosts):
                issues.append(f"space {s.id} ({s.name or s.use}): no door on any bounding wall")

    if project.revision < 1:
        issues.append("project revision must be >= 1")

    if issues:
        raise ValidationError(f"{len(issues)} semantic violation(s)", issues)


def _walls_touching_space(project: Project, space: Space) -> set[str]:
    """Walls whose midpoint is within 5mm of the space boundary (cheap, robust)."""
    from .geometry import point_in_polygon, distance_to_boundary, polygon_to_shapely

    poly = polygon_to_shapely(space.boundary_mm2d)
    hits: set[str] = set()
    for w in project.by_type("wall"):
        axis = w.wall_axis()
        if not axis:
            continue
        (x1, y1), (x2, y2) = axis
        mx, my = (x1 + x2) / 2.0, (y1 + y2) / 2.0
        if poly is not None:
            if distance_to_boundary(poly, (mx, my)) <= 5.0:
                hits.add(w.id)
        elif point_in_polygon((mx, my), space.boundary_mm2d):
            hits.add(w.id)
    return hits


def load_project(project_dir: str | Path, filename: str = "project.json") -> Project:
    d = Path(project_dir)
    if d.is_file():
        return Project.load(d)
    return Project.load(d / filename)


def validate_all(project: Project, schema_path: str | Path | None = None) -> None:
    validate_schema(project, schema_path)
    validate_semantics(project)


def summary(project: Project) -> Dict[str, Any]:
    counts: Dict[str, int] = {}
    for e in project.elements:
        counts[e.type] = counts.get(e.type, 0) + 1
    return {
        "project_id": project.project_id,
        "name": project.name,
        "revision": project.revision,
        "usable_area_m2": round(project.usable_area_m2, 2),
        "spaces": len(project.spaces),
        "elements": counts,
        "artifacts": len(project.artifacts),
        "uncertain_elements": sum(1 for e in project.elements if e.uncertain),
        "stale_artifacts": [a.id for a in project.artifacts if a.status == "stale"],
    }


def new_id(prefix: str, index: int, width: int = 3) -> str:
    return f"{prefix}-{index:0{width}d}"
