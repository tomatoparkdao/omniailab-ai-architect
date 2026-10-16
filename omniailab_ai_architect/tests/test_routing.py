"""Routing: a request becomes an explicit, gated stage plan.

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import tempfile
from pathlib import Path

from omniailab_ai_architect.demo import build_demo_project
from omniailab_ai_architect.routing import route
from omniailab_ai_architect.stage_state import confirm_stage


def test_planning_request_routes_to_the_plan_stage():
    plan = route("帮我看一下平面布局，出两套平面方案")
    stages = [t.stage for t in plan.tasks]
    assert "S3" in stages
    assert stages[0] == "S1", "upstream stages must be run or checked first"


def test_drawing_request_routes_through_the_lock():
    plan = route("出施工图和节点详图")
    stages = [t.stage for t in plan.tasks]
    assert "S7" in stages
    assert stages.index("S6") < stages.index("S7")


def test_full_pipeline_keyword_expands_to_all_eight_stages():
    plan = route("从原始户型图开始，全流程做一遍")
    assert [t.stage for t in plan.tasks] == ["S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8"]


def test_change_request_is_recognised_and_routed_to_rework():
    with tempfile.TemporaryDirectory() as td:
        p = build_demo_project(Path(td))
        plan = route("我不喜欢客厅的电视背景墙", p)
        assert plan.is_change
        assert plan.change_landing_stage == "S4"
        assert plan.change_geometry_affecting is False
        assert "S3" not in plan.rework_stages


def test_guardrails_report_why_a_stage_cannot_start_yet():
    with tempfile.TemporaryDirectory() as td:
        p = build_demo_project(Path(td))
        plan = route("出施工图", p)
        blocked = {b["stage"] for b in plan.guardrail_blocks}
        assert blocked, "an unconfirmed project must produce guardrail blocks"
        assert any("未确认" in b["reason"] or "不得" in b["reason"]
                   for b in plan.guardrail_blocks)


def test_guardrails_clear_once_upstream_is_confirmed():
    with tempfile.TemporaryDirectory() as td:
        p = build_demo_project(Path(td))
        for s in ("S1", "S2", "S3"):
            confirm_stage(p, s, by="业主")
        plan = route("出施工图", p)
        statuses = {t.stage: t.status for t in plan.tasks}
        assert statuses["S4"] == "ready"


def test_non_negotiables_are_always_stated():
    plan = route("随便做点什么")
    text = " ".join(plan.non_negotiable)
    for key in ("R1", "R2", "R3", "R4"):
        assert key in text
    assert "效果图" in text and "尺寸依据" in text


def test_route_markdown_is_readable():
    with tempfile.TemporaryDirectory() as td:
        p = build_demo_project(Path(td))
        md = route("从小户型开始全案设计", p).markdown()
        assert "阶段任务" in md
        assert "不可协商" in md
        assert "请持证" not in md
        assert "须持证专业人员复核签署" in md
