"""Tool registry: declaration, risk gating, independent verification, honesty."""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from omniailab_ai_architect.adapters.dxf import DxfAdapter  # noqa: E402
from omniailab_ai_architect.demo import build_demo_project  # noqa: E402
from omniailab_ai_architect.tools import (  # noqa: E402
    ARTIFACT_KIND_CEILING,
    FORBIDDEN_CLAIMS,
    RISK_TIERS,
    CapabilityViolation,
    PermissionRequired,
    ToolCapability,
    ToolRegistry,
    honesty_rules,
)


def _drawn_dxf(td: str) -> Path:
    project = build_demo_project(Path(td))
    out = Path(td) / "plan.dxf"
    DxfAdapter().draw_plan(project, out, title="平面布置图")
    return out


# --------------------------------------------------------------------------
def test_every_declared_operation_has_a_valid_risk_tier():
    reg = ToolRegistry(mcp_config=Path("does-not-exist.json"))
    for t in reg.detect(refresh=True).values():
        for op in t.operations:
            assert op.risk in RISK_TIERS, (t.id, op.name)


def test_illegal_risk_tier_is_refused_at_declaration_time():
    try:
        ToolCapability(id="x", name="x", kind="python",
                       operations=[__import__("omniailab_ai_architect.tools.capability",
                                              fromlist=["Operation"]).Operation("o", "L9")])
    except CapabilityViolation:
        pass
    else:  # pragma: no cover
        raise AssertionError("非法风险等级必须在声明期被拒绝")


def test_illegal_availability_is_refused():
    try:
        ToolCapability(id="x", name="x", kind="python", availability="maybe")
    except CapabilityViolation:
        pass
    else:  # pragma: no cover
        raise AssertionError("非法 availability 必须被拒绝")


def test_l4_requires_approval_before_it_runs():
    reg = ToolRegistry(mcp_config=Path("does-not-exist.json"))
    try:
        reg.guard("blender", "run_blender")
    except (PermissionRequired, CapabilityViolation):
        pass
    else:  # pragma: no cover
        raise AssertionError("L4 调用在未授权时必须被拦下")


def test_l3_requires_approval():
    reg = ToolRegistry(mcp_config=Path("does-not-exist.json"))
    try:
        reg.guard("render", "render_ai")
    except PermissionRequired as exc:
        assert exc.risk == "L3"
    else:  # pragma: no cover
        raise AssertionError("L3 调用在未授权时必须被拦下")


def test_l2_runs_without_approval():
    reg = ToolRegistry(mcp_config=Path("does-not-exist.json"))
    cap = reg.guard("dxf", "draw_plan")
    assert cap.id == "dxf"


def test_unknown_operation_and_unknown_tool_are_refused():
    reg = ToolRegistry(mcp_config=Path("does-not-exist.json"))
    for call in (("dxf", "teleport"), ("nope", "draw_plan")):
        try:
            reg.guard(*call)
        except CapabilityViolation:
            pass
        else:  # pragma: no cover
            raise AssertionError(f"{call} 必须被拒绝")


def test_plan_call_states_the_gate_and_the_honest_label():
    reg = ToolRegistry(mcp_config=Path("does-not-exist.json"))
    plan = reg.plan_call("dxf", "draw_plan")
    assert plan["risk"] == "L2"
    assert plan["approval_required"] is False
    assert plan["honest_description"] == [ARTIFACT_KIND_CEILING["dxf"]]
    assert plan["limits"], "必须声明 DXF 不能被称为什么"

    l4 = reg.plan_call("blender", "run_blender")
    assert l4["approval_required"] is True
    assert l4["dry_run_required"] is True


# --------------------------------------------------------------------------
def test_dxf_is_verified_by_an_independent_parser():
    with tempfile.TemporaryDirectory() as td:
        path = _drawn_dxf(td)
        rep = ToolRegistry(mcp_config=Path("does-not-exist.json")).verify(path)
        assert rep["ok"], rep
        assert rep["is_dwg"] is False
        assert rep["honest_label"].startswith("可编辑 2D CAD")
        assert rep["stats"].get("entity_count") or rep["stats"].get("ezdxf_entity_count")


def test_obj_is_labelled_as_mesh_not_parametric_bim():
    with tempfile.TemporaryDirectory() as td:
        from omniailab_ai_architect.adapters.mesh import MeshAdapter

        project = build_demo_project(Path(td))
        out = Path(td) / "mesh"
        MeshAdapter().export_obj(project, out)
        rep = ToolRegistry(mcp_config=Path("does-not-exist.json")).verify(out / "model.obj")
        assert rep["ok"], rep
        assert rep["is_parametric_bim"] is False
        assert "非参数化 BIM" in rep["honest_label"]


def test_a_dxf_renamed_to_dwg_is_still_not_a_dwg():
    with tempfile.TemporaryDirectory() as td:
        src = _drawn_dxf(td)
        fake = Path(td) / "fake.dwg"
        fake.write_bytes(src.read_bytes())
        rep = ToolRegistry(mcp_config=Path("does-not-exist.json")).verify(fake)
        assert rep.get("is_dwg") is False
        assert rep["checker"] == "dwg", "按扩展名分派校验器，但结论按内容给出"
        assert "DXF" in " ".join(rep["errors"]) + rep["honest_label"]


def test_empty_and_missing_files_fail_verification():
    reg = ToolRegistry(mcp_config=Path("does-not-exist.json"))
    with tempfile.TemporaryDirectory() as td:
        empty = Path(td) / "empty.json"
        empty.write_text("", encoding="utf-8")
        assert reg.verify(empty)["ok"] is False
        assert reg.verify(Path(td) / "nope.json")["ok"] is False


def test_pptx_verification_checks_the_ooxml_container():
    with tempfile.TemporaryDirectory() as td:
        project = build_demo_project(Path(td))
        from omniailab_ai_architect import presentation

        rep = presentation.render(project, "concept", out_dir=Path(td), want_pdf=False)
        v = ToolRegistry(mcp_config=Path("does-not-exist.json")).verify(rep["files"]["pptx"])
        assert v["ok"], v
        assert v["stats"]["slides"] >= 4

        broken = Path(td) / "broken.pptx"
        broken.write_text("not a zip", encoding="utf-8")
        assert ToolRegistry(mcp_config=Path("does-not-exist.json")).verify(broken)["ok"] is False


# --------------------------------------------------------------------------
def test_honesty_rules_cover_the_five_known_traps():
    claims = " ".join(c["claim"] for c in honesty_rules())
    for trap in ("DWG", "参数化 BIM", "施工尺寸", "IFC", "结构安全"):
        assert trap in claims, trap
    assert all(c["why"] and c["instead"] for c in FORBIDDEN_CLAIMS)


def test_artifact_ceilings_never_update_a_mesh_to_bim():
    assert "非参数化 BIM" in ARTIFACT_KIND_CEILING["obj"]
    assert "非参数化 BIM" in ARTIFACT_KIND_CEILING["glb"]
    assert "不得作为尺寸依据" in ARTIFACT_KIND_CEILING["png"]
    assert "可编辑演示文稿" in ARTIFACT_KIND_CEILING["pptx"]


def test_mcp_servers_are_read_not_guessed():
    with tempfile.TemporaryDirectory() as td:
        cfg = Path(td) / "mcp.json"
        cfg.write_text(json.dumps({"mcpServers": {
            "definitely-not-installed-xyz": {"command": "definitely-not-installed-xyz"},
            "remote-thing": {"url": "https://example.invalid/mcp"},
        }}), encoding="utf-8")
        rep = ToolRegistry(mcp_config=cfg).detect_report()
        tools = {t["id"]: t for t in rep["tools"]}
        assert tools["definitely-not-installed-xyz"]["availability"] == "not_configured"
        assert tools["remote-thing"]["availability"] == "not_configured"
        assert tools["remote-thing"]["transport"] == "http"
        assert any("不猜测" in n or "未做连通性探测" in n
                   for n in tools["remote-thing"]["notes"])


def test_broken_mcp_config_is_reported_as_such():
    with tempfile.TemporaryDirectory() as td:
        cfg = Path(td) / "mcp.json"
        cfg.write_text("{ broken", encoding="utf-8")
        rep = ToolRegistry(mcp_config=cfg).detect_report()
        assert any(t["id"].startswith("mcp-config-error") for t in rep["tools"])


def test_run_verifies_what_it_produced():
    with tempfile.TemporaryDirectory() as td:
        project = build_demo_project(Path(td))
        reg = ToolRegistry(mcp_config=Path("does-not-exist.json"))
        out = Path(td) / "run.dxf"
        rec = reg.run("dxf", "draw_plan",
                      DxfAdapter().draw_plan,
                      project=project, out_path=out, title="平面布置图")
        assert rec.ok, rec.errors
        assert rec.verification and rec.verification[0]["ok"]


def test_run_reports_failure_instead_of_pretending():
    def explode(**kwargs):
        raise RuntimeError("adapter blew up")

    reg = ToolRegistry(mcp_config=Path("does-not-exist.json"))
    rec = reg.run("dxf", "audit", explode)
    assert rec.ok is False
    assert any("adapter blew up" in e for e in rec.errors)
