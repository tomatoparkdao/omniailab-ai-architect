"""Acceptance scenarios A / B / C.

These run the real pipeline, so they are the slowest part of the suite. They are
also the part that proves the system is not a mock: every check re-opens the
artifact with an independent parser.
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from omniailab_ai_architect import scenarios as sc  # noqa: E402

CACHE: dict = {}


def _run_all() -> dict:
    """Run the three scenarios once and share the result across tests."""
    if "all" not in CACHE:
        CACHE["td"] = tempfile.TemporaryDirectory()
        CACHE["all"] = sc.run_all(Path(CACHE["td"].name) / "scenarios")
    return CACHE["all"]


# --------------------------------------------------------------------------
def test_all_three_scenarios_pass():
    res = _run_all()
    assert res["summary"]["total"] == 3
    assert res["summary"]["failed"] == 0, [
        (r["scenario"], [c for c in r["checks"] if c["result"] == "fail"])
        for r in res["scenarios"] if not r["ok"]
    ]


def test_scenario_a_produces_brief_concept_and_two_comparable_plans():
    a = next(r for r in _run_all()["scenarios"] if r["scenario"] == "A")
    checks = {c["check"]: c["result"] for c in a["checks"]}
    for need in ("阶段执行无失败", "设计任务书：文件存在", "概念方案：文件存在",
                 "两套平面方案：数量", "两套方案：指标口径一致（可横向比较）",
                 "两套方案：确实不同", "方案生成：可重复运行",
                 "方案深度 DXF：文件存在", "方案深度 DXF：格式有效（独立复核）"):
        assert checks.get(need) == "ok", (need, checks.get(need))
    kinds = {a_["kind"] for a_ in a["artifacts"]}
    assert {"md", "dxf"} <= kinds, kinds


def test_scenario_b_produces_inspectable_dxf_and_a_spatial_model():
    b = next(r for r in _run_all()["scenarios"] if r["scenario"] == "B")
    checks = {c["check"]: c["result"] for c in b["checks"]}
    for need in ("DXF：数量", "可检查 DXF：格式有效（独立复核）", "DXF：可重复运行",
                 "三维空间模型：OBJ 存在", "三维空间模型：可读回",
                 "三维空间模型：未谎称参数化 BIM", "效果图任务包：存在",
                 "效果图任务包：含机位", "未伪造 DWG（DXF 改名）", "未伪造 IFC 文件"):
        assert checks.get(need) == "ok", (need, checks.get(need))
    assert any(a["kind"] == "dxf" for a in b["artifacts"])


def test_scenario_b_does_not_skip_a_gate():
    b = next(r for r in _run_all()["scenarios"] if r["scenario"] == "B")
    stages = [s["stage"] for s in b["stages"]]
    assert "S6" in stages and "S7" in stages
    assert stages.index("S6") < stages.index("S7")
    assert all(s["status"] not in ("blocked", "failed") for s in b["stages"]), b["stages"]


def test_scenario_c_produces_an_editable_pptx_with_the_required_structure():
    c = next(r for r in _run_all()["scenarios"] if r["scenario"] == "C")
    checks = {x["check"]: x["result"] for x in c["checks"]}
    for need in ("汇报内容自检（页数/封面/免责页/空页）", "概念设计 PPTX：文件存在",
                 "概念设计 PPTX：格式有效（独立复核）", "PPTX：可重复运行",
                 "汇报 Markdown：文件存在", "汇报内容：来源可追溯"):
        assert checks.get(need) == "ok", (need, checks.get(need))
    assert any(a["kind"] == "pptx" for a in c["artifacts"])


def test_unconfigured_platform_is_skipped_not_failed():
    b = next(r for r in _run_all()["scenarios"] if r["scenario"] == "B")
    check = next(c for c in b["checks"] if c["check"] == "OmniAiLab 原生 provider：已连接")
    assert check["result"] in ("ok", "skipped")
    if check["result"] == "skipped":
        assert "NOT_CONFIGURED" in check["detail"]
        assert any("未配置" in n for n in b["notes"])


def test_pdf_is_skipped_not_faked_when_no_renderer_is_present():
    c = next(r for r in _run_all()["scenarios"] if r["scenario"] == "C")
    check = next(c_ for c_ in c["checks"] if c_["check"] == "汇报 PDF：真实渲染")
    assert check["result"] in ("ok", "skipped")
    if check["result"] == "skipped":
        assert "未伪造" in check["detail"]


def test_acceptance_report_is_written_in_both_formats():
    res = _run_all()
    for key in ("json", "markdown"):
        p = Path(res["report"][key])
        assert p.exists() and p.stat().st_size > 200
    data = json.loads(Path(res["report"]["json"]).read_text(encoding="utf-8"))
    assert data["summary"]["failed"] == 0
    text = Path(res["report"]["markdown"]).read_text(encoding="utf-8")
    assert "Scenario A" in text and "Scenario C" in text
    assert "未以 Mock 通过宣称生产功能可用" in text


def test_every_artifact_carries_an_honest_label():
    for r in _run_all()["scenarios"]:
        for a in r["artifacts"]:
            assert a["honest_label"], (r["scenario"], a["path"])
            assert a["size_bytes"] > 0, (r["scenario"], a["path"])


def test_unknown_scenario_is_rejected():
    try:
        sc.run("Z", Path(tempfile.mkdtemp()))
    except ValueError:
        pass
    else:  # pragma: no cover
        raise AssertionError("未知场景必须被拒绝")
