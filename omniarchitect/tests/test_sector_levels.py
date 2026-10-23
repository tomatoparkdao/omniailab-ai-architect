"""The whole building, not just a labelled typical floor, is modelled.

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

from types import SimpleNamespace

from omniarchitect.model import Project, validate_all
from omniarchitect.sector import brief, layout, levels, program
from omniarchitect.workflow import _install_scheme


def _project(sector: str, text: str, code: str) -> tuple[Project, dict]:
    ctx = SimpleNamespace(name=text, lead_id="architecture", profile_id="architecture",
                          taxonomy={"codes": [code], "ancillary": []},
                          taxonomy_codes=(code,), answers={}, program=[],
                          area_available_m2=None, target_area_m2=0.0, location="")
    b = brief.build(ctx)
    p = Project(project_id=sector)
    prog = program.build(b)
    layout.install_program(p, prog)
    env = layout.envelope_size(prog, sector)
    layout.install_envelope(p, env)
    schemes = layout.build_schemes(p, prog, sector, env)
    _install_scheme(p, schemes["A"])
    state = levels.install(p, prog, b, None, env, schemes["A"])
    validate_all(p)
    return p, state


def test_school_24_classes_across_four_real_levels() -> None:
    p, state = _project("education", "新建 24 班小学，每班 45 人", "A3")
    assert state["counts"] == [6, 6, 6, 6]
    assert len(p.levels) == 4
    assert sum(s.use == "teaching" for s in p.spaces) == 24
    assert len({e.id for e in p.elements}) == len(p.elements)
    assert all(p.element(e.geometry["host_wall"]).level_id == e.level_id
               for e in p.elements if e.type in ("door", "window"))


def test_hotel_120_keys_short_top_floor() -> None:
    p, state = _project("hospitality", "既有酒店室内精装修 120 间客房", "B4")
    assert state["counts"] == [16, 16, 16, 16, 16, 16, 16, 8]
    assert len(p.levels) == 8
    assert sum(s.use == "guest" for s in p.spaces) == 120
    assert sum(s.use == "guest" for s in p.spaces_on("L8")) == 8
