"""Canonical model, validation, revision control and invalidation.

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import tempfile
from pathlib import Path

from omniarchitect.demo import build_demo_project
from omniarchitect.errors import ValidationError
from omniarchitect.model import Project, summary, validate_semantics, validate_schema
from omniarchitect.revisions import (
    apply_geometry_change,
    dependents_of,
    invalidate,
    register_artifact,
)


def _proj(tmp: Path):
    return build_demo_project(tmp)


def test_demo_project_is_schema_and_semantically_valid():
    with tempfile.TemporaryDirectory() as td:
        p = _proj(Path(td))
        validate_schema(p)
        validate_semantics(p)
        s = summary(p)
        assert s["revision"] == 1
        assert len(s["elements"])


def test_roundtrip_preserves_everything():
    with tempfile.TemporaryDirectory() as td:
        p = _proj(Path(td))
        raw = p.to_dict()
        again = Project.from_dict(raw)
        assert again.to_dict() == raw


def test_uncertain_elements_are_preserved_and_counted():
    """Inferred structure must stay flagged — it may not be treated as fact."""
    with tempfile.TemporaryDirectory() as td:
        p = _proj(Path(td))
        flagged = [e.id for e in p.elements if e.uncertain]
        assert flagged, "the demo deliberately carries inferred elements"
        assert summary(p)["uncertain_elements"] == len(flagged)


def test_dangling_level_is_rejected():
    with tempfile.TemporaryDirectory() as td:
        p = _proj(Path(td))
        p.spaces[0].level_id = "L9"
        try:
            validate_semantics(p)
        except ValidationError as exc:
            assert any("L9" in i for i in exc.issues)
        else:
            raise AssertionError("a dangling level reference must be rejected")


def test_opening_longer_than_its_host_wall_is_rejected():
    with tempfile.TemporaryDirectory() as td:
        p = _proj(Path(td))
        win = p.by_type("window")[0]
        win.geometry["width_mm"] = 99999
        try:
            validate_semantics(p)
        except ValidationError as exc:
            assert any("exceeds host wall" in i for i in exc.issues)
        else:
            raise AssertionError("an opening wider than its wall must be rejected")


def test_duplicate_ids_are_rejected():
    with tempfile.TemporaryDirectory() as td:
        p = _proj(Path(td))
        clone = p.elements[0].to_dict()
        from omniarchitect.model import Element

        p.elements.append(Element.from_dict(clone))
        try:
            validate_semantics(p)
        except ValidationError as exc:
            assert any("duplicate id" in i for i in exc.issues)
        else:
            raise AssertionError("duplicate ids must be rejected")


def test_geometry_change_bumps_revisions_and_invalidates_dependents():
    with tempfile.TemporaryDirectory() as td:
        p = _proj(Path(td))
        wall = p.by_type("wall")[0]
        register_artifact(p, "art-drawings", "drawing", [wall.id], "cad-drafting")
        register_artifact(p, "art-issued", "document", ["art-drawings"], "delivery")

        before_rev, before_el = p.revision, wall.revision
        rep = apply_geometry_change(p, wall.id, {}, detail="move wall")
        assert p.revision == before_rev + 1
        assert p.element(wall.id).revision == before_el + 1
        assert set(rep.stale) == {"art-drawings", "art-issued"}
        assert p.artifact("art-issued").status == "stale"


def test_invalidation_is_transitive():
    with tempfile.TemporaryDirectory() as td:
        p = _proj(Path(td))
        e = p.elements[0]
        register_artifact(p, "a", "drawing", [e.id])
        register_artifact(p, "b", "model", ["a"])
        register_artifact(p, "c", "render", ["b"])
        register_artifact(p, "unrelated", "document", ["nothing"])
        assert dependents_of(p, [e.id]) == ["a", "b", "c"]
        assert invalidate(p, [e.id]) == ["a", "b", "c"]
        assert p.artifact("unrelated").status == "draft"


def test_invalidation_survives_an_accidental_cycle():
    with tempfile.TemporaryDirectory() as td:
        p = _proj(Path(td))
        register_artifact(p, "x", "drawing", ["y"])
        register_artifact(p, "y", "drawing", ["x"])
        # must terminate rather than hang
        assert isinstance(dependents_of(p, ["x"]), list)


def test_change_log_records_every_change():
    with tempfile.TemporaryDirectory() as td:
        p = _proj(Path(td))
        wall = p.by_type("wall")[0]
        apply_geometry_change(p, wall.id, {}, detail="测试变更")
        assert p.change_log
        assert "测试变更" in p.change_log[-1].detail


def test_save_and_load_roundtrip_on_disk():
    with tempfile.TemporaryDirectory() as td:
        p = _proj(Path(td))
        out = Path(td) / "sub" / "project.json"
        p.save(out)
        again = Project.load(out)
        assert again.project_id == p.project_id
        assert len(again.elements) == len(p.elements)
