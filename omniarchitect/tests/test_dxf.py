"""DXF output: the file must be real, readable and complete.

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import tempfile
from pathlib import Path

from omniarchitect.adapters import DxfAdapter, MeshAdapter, resolve_host_axes
from omniarchitect.adapters.dxf_r12 import read_r12, write_r12
from omniarchitect.adapters.drawing import build_primitives
from omniarchitect.demo import build_demo_project
from omniarchitect.planner import PlanGenerator, SchemeOptions
from omniarchitect.workflow import _install_scheme


def _prepared(tmp: Path):
    p = build_demo_project(tmp)
    g = PlanGenerator(p)
    s = g.generate(SchemeOptions(variant="A", title="方案A", strategy="band_day_night"))
    _install_scheme(p, s)
    resolve_host_axes(p)
    return p, s


def test_native_backend_produces_a_drawable_file():
    with tempfile.TemporaryDirectory() as td:
        p, _ = _prepared(Path(td))
        out = Path(td) / "plan.dxf"
        write_r12(build_primitives(p, level_id="L1"), out)
        assert out.exists() and out.stat().st_size > 5000
        report = read_r12(out)
        assert report["ok"], report["errors"]
        assert "ENTITIES" in report["stats"]["sections"]
        assert report["stats"]["entity_count"] > 50
        assert any(l.startswith("A-WALL") for l in report["stats"]["layers"])


def test_native_reader_catches_a_broken_file():
    with tempfile.TemporaryDirectory() as td:
        bad = Path(td) / "broken.dxf"
        bad.write_text("0\nSECTION\n2\nHEADER\n0\nENDSEC\n0\nEOF\n", encoding="ascii")
        report = read_r12(bad)
        assert not report["ok"]
        assert report["errors"], "a malformed file must produce errors"


def test_adapter_draws_and_audits_without_ezdxf():
    with tempfile.TemporaryDirectory() as td:
        p, _ = _prepared(Path(td))
        adapter = DxfAdapter()
        cap = adapter.preflight()
        assert cap.available, "the native backend must always be available"
        res = adapter.draw_plan(p, Path(td) / "A-plan.dxf", level_id="L1",
                                title="平面布置图", depth="construction")
        assert res.ok, res.errors
        assert res.validation["drawing_depth"] == "construction"
        stats = res.validation["stats"]
        assert stats["entity_count"] > 50
        assert any(l.startswith("A-WALL") for l in stats["layers"])


def test_chinese_labels_survive_as_unicode_escapes():
    with tempfile.TemporaryDirectory() as td:
        p, _ = _prepared(Path(td))
        out = Path(td) / "labels.dxf"
        write_r12(build_primitives(p, level_id="L1"), out)
        raw = out.read_text(encoding="ascii", errors="replace")
        assert "\\U+" in raw, "CJK text must be written as DXF \\U+ escapes"
        report = read_r12(out)
        assert report["stats"]["text_labels"] > 0
        assert any(ord(ch) > 127 for l in report["stats"]["sample_labels"] for ch in l)


def test_openings_are_cut_out_of_walls():
    """A door must leave a gap — otherwise the drawing shows a sealed room."""
    from omniarchitect.adapters.drawing import free_spans

    with tempfile.TemporaryDirectory() as td:
        p, s = _prepared(Path(td))
        wall = next(e for e in s.elements if e.type == "wall")
        doors = [e for e in s.elements
                 if e.type == "door" and e.geometry.get("host_wall") == wall.id]
        spans = free_spans(wall.wall_length_mm(), doors)
        if doors:
            assert sum(b - a for a, b in spans) < wall.wall_length_mm()


def test_mesh_export_is_readable_and_sized_in_millimetres():
    with tempfile.TemporaryDirectory() as td:
        p, _ = _prepared(Path(td))
        res = MeshAdapter().export_obj(p, Path(td) / "model", level_id="L1", stem="plan-A")
        assert res.ok, res.errors
        check = res.validation
        assert check["vertices"] > 0 and check["faces"] > 0
        size = check["size_m"]
        assert 10 < size[0] < 20 and 8 < size[1] < 15
        assert 2.5 < size[2] < 3.2


def test_mesh_read_back_rejects_an_empty_file():
    with tempfile.TemporaryDirectory() as td:
        empty = Path(td) / "empty.obj"
        empty.write_text("# nothing\n", encoding="utf-8")
        report = MeshAdapter().read_back(empty)
        assert not report["ok"]
