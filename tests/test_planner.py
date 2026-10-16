"""Plan generation: completeness, dimensions and honest deviation reporting."""
from __future__ import annotations

import tempfile
from pathlib import Path

from omniarchitect.demo import build_demo_project
from omniarchitect.planner import PlanGenerator, SchemeOptions, envelope_polygon


def _gen(tmp: Path):
    p = build_demo_project(tmp)
    return p, PlanGenerator(p)


def _scheme(g, variant, strategy):
    return g.generate(SchemeOptions(variant=variant, title=f"方案{variant}", strategy=strategy))


def test_both_strategies_produce_a_complete_plan():
    """Every room in the brief must be placed — a plan that drops the kitchen
    is not a plan."""
    with tempfile.TemporaryDirectory() as td:
        p, g = _gen(Path(td))
        for variant, strategy in (("A", "band_day_night"), ("B", "spine_centre")):
            s = _scheme(g, variant, strategy)
            assert s.metrics["missing_rooms"] == []
            assert s.metrics["room_count"] >= len(p.program)
            assert s.metrics["total_area_m2"] > 100


def test_every_enclosed_room_gets_a_door():
    with tempfile.TemporaryDirectory() as td:
        p, g = _gen(Path(td))
        s = _scheme(g, "A", "band_day_night")
        need = [sp for sp in s.spaces if sp.properties.get("requires_door")]
        hosted = {
            str(e.geometry.get("host_wall"))
            for e in s.elements
            if e.type == "door" and e.geometry.get("host_wall")
        }
        wall_ids = {e.id for e in s.elements if e.type == "wall"}
        assert hosted & wall_ids
        # at least one door per enclosed (non-open-plan) room
        closed = [sp for sp in need if not sp.properties.get("open_plan")]
        assert len(hosted) >= len(closed)


def test_rooms_do_not_overlap():
    from omniarchitect.geometry import polygon_to_shapely

    with tempfile.TemporaryDirectory() as td:
        p, g = _gen(Path(td))
        s = _scheme(g, "A", "band_day_night")
        polys = [(sp, polygon_to_shapely(sp.boundary_mm2d)) for sp in s.spaces]
        for i in range(len(polys)):
            for j in range(i + 1, len(polys)):
                a, pa = polys[i]
                b, pb = polys[j]
                if pa is None or pb is None:
                    continue
                assert pa.intersection(pb).area < 0.05e6, f"{a.id} overlaps {b.id}"


def test_daylight_rooms_are_reported_whether_or_not_they_got_a_window():
    with tempfile.TemporaryDirectory() as td:
        p, g = _gen(Path(td))
        s = _scheme(g, "A", "band_day_night")
        served, total = s.metrics["daylight_rooms_served"].split("/")
        assert int(total) > 0
        if int(served) < int(total):
            assert any("没有可利用的外墙" in w for w in s.warnings)


def test_dimension_shortfalls_are_declared_not_hidden():
    with tempfile.TemporaryDirectory() as td:
        p, g = _gen(Path(td))
        s = _scheme(g, "A", "band_day_night")
        for w in s.warnings:
            assert "低于最小值" not in w or "mm" in w


def test_the_two_schemes_are_genuinely_different():
    with tempfile.TemporaryDirectory() as td:
        p, g = _gen(Path(td))
        a = _scheme(g, "A", "band_day_night")
        b = _scheme(g, "B", "spine_centre")
        assert a.strategy != b.strategy
        assert a.metrics["corridor_area_m2"] != b.metrics["corridor_area_m2"] or \
            a.metrics["partition_count"] != b.metrics["partition_count"]


def test_envelope_notch_is_respected():
    with tempfile.TemporaryDirectory() as td:
        p, g = _gen(Path(td))
        env = envelope_polygon(p, "L1")
        assert len(env) == 6, "demo shell should be a notched rectangle"
        s = _scheme(g, "A", "band_day_night")
        # nothing may sit inside the notched-out core
        for sp in s.spaces:
            for x, y in sp.boundary_mm2d:
                assert not (x > 10600 and y > 8200), f"{sp.id} sits in the core notch"


def test_unknown_strategy_fails_loudly():
    from omniarchitect.errors import ModelError

    with tempfile.TemporaryDirectory() as td:
        p, g = _gen(Path(td))
        try:
            g.generate(SchemeOptions(variant="Z", strategy="does_not_exist"))
        except ModelError as exc:
            assert "does_not_exist" in str(exc)
        else:
            raise AssertionError("an unknown strategy must not silently succeed")
