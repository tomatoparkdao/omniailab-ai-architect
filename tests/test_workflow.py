"""Tests for the eight-stage workflow, the state machine and the guardrails."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from omniarchitect.demo import build_demo_project
from omniarchitect.stage_state import (
    AWAITING,
    BLOCKED,
    CONFIRMED,
    can_start,
    confirm_stage,
    get_state,
    markdown,
    next_runnable,
    progress,
    reject_stage,
)
from omniarchitect.workflow import StageRunner


def _proj(tmp: Path):
    return build_demo_project(tmp)


def test_cannot_model_before_the_brief_is_confirmed():
    """R1 — no fine modelling before the client confirms the functional brief."""
    with tempfile.TemporaryDirectory() as d:
        p = _proj(Path(d))
        ok, reason = can_start(p, "S5")
        assert not ok
        assert "任务书" in reason or "前置阶段" in reason


def test_cannot_draw_formally_before_the_plan_is_confirmed():
    """R4 — the most expensive step nobody wants to repeat."""
    with tempfile.TemporaryDirectory() as d:
        p = _proj(Path(d))
        ok, reason = can_start(p, "S7")
        assert not ok
        assert reason


def test_gate_blocks_then_confirmation_unlocks():
    with tempfile.TemporaryDirectory() as d:
        p = _proj(Path(d))
        r = StageRunner(p, Path(d) / "out", assume_approval=False)
        out = r.run_stage("S1", confirm=False)
        assert out.status == "ok"
        assert get_state(p, "S1").status == AWAITING
        assert out.next_action.startswith("提交确认")

        # S2 is still gated on S1
        blocked = r.run_stage("S2", confirm=False)
        assert blocked.status == "blocked"

        r.confirm("S1", by="业主")
        assert get_state(p, "S1").status == CONFIRMED
        now_ok = r.run_stage("S2", confirm=False)
        assert now_ok.status == "ok"


def test_reject_sends_a_stage_back_for_rework():
    with tempfile.TemporaryDirectory() as d:
        p = _proj(Path(d))
        r = StageRunner(p, Path(d) / "out", assume_approval=False)
        r.run_stage("S1", confirm=False)
        r.reject("S1", reason="面积指标要重算")
        st = get_state(p, "S1")
        assert st.status == "rework"
        assert st.confirmed_at == ""
        assert "面积指标" in st.note


def test_full_run_confirms_all_eight_stages():
    with tempfile.TemporaryDirectory() as d:
        p = _proj(Path(d))
        r = StageRunner(p, Path(d) / "out", assume_approval=True)
        m = r.run_all(confirm_all=True)
        assert not m.blocks, m.blocks
        assert [o.stage for o in m.outcomes] == ["S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8"]
        assert progress(p)["percent"] == 100.0
        assert (Path(m.out_dir) / "run-manifest.json").exists()
        assert (Path(m.out_dir) / "stage-state.md").exists()


def test_run_stops_at_the_first_unconfirmed_gate():
    with tempfile.TemporaryDirectory() as d:
        p = _proj(Path(d))
        r = StageRunner(p, Path(d) / "out", assume_approval=False)
        m = r.run_until_gate()
        assert len(m.outcomes) == 1
        assert m.outcomes[0].stage == "S1"
        assert get_state(p, "S1").status == AWAITING


def test_s3_produces_two_comparable_schemes():
    with tempfile.TemporaryDirectory() as d:
        p = _proj(Path(d))
        r = StageRunner(p, Path(d) / "out", assume_approval=True)
        r.run_stage("S1", confirm=True)
        out = r.run_stage("S2", confirm=True)
        assert out.status == "ok"
        out3 = r.run_stage("S3", confirm=False)
        assert out3.status == "ok"
        assert set(r.schemes) == {"A", "B"}
        ma, mb = r.schemes["A"].metrics, r.schemes["B"].metrics
        assert ma["total_area_m2"] > 100
        assert mb["total_area_m2"] > 100
        assert ma["strategy"] != mb["strategy"]
        # the two schemes really differ in layout, not just in name
        assert ma["partition_count"] != mb["partition_count"] or \
            abs(ma["corridor_area_m2"] - mb["corridor_area_m2"]) > 0.1


def test_deliverables_and_progress_are_persisted():
    with tempfile.TemporaryDirectory() as d:
        p = _proj(Path(d))
        r = StageRunner(p, Path(d) / "out", assume_approval=True, project_dir=Path(d))
        r.run_all(confirm_all=True)
        saved = json.loads((Path(d) / "project.json").read_text(encoding="utf-8"))
        assert "stage_state" in saved["meta"]
        assert saved["meta"]["stage_state"]["S8"]["status"] == CONFIRMED
        assert "阶段推进状态" in markdown(p)


def test_next_runnable_reports_blocking_reason():
    with tempfile.TemporaryDirectory() as d:
        p = _proj(Path(d))
        sid, reason = next_runnable(p)
        assert sid == "S1"
        confirm_stage(p, "S1", by="业主")
        sid2, _ = next_runnable(p)
        assert sid2 == "S2"
