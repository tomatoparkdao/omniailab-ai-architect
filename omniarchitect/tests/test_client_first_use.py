"""普通客户首次使用：问得少、不重复、门禁不糊弄。

这两条最容易被"演示效果"掩盖：
* 同一个信息被反复问 → 客户觉得系统没在听；
* 门禁本该拦却放过去 → 交付了不该交付的东西。

这里用两个真实项目（住宅 / 办公）各跑一遍，断言的是行为，不是界面。

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Dict, List

from omniarchitect import concept as C, finishes
from omniarchitect.demo import build_demo_project
from omniarchitect.intake.gate import decide_gate as decide_g1
from omniarchitect.intake.interview import answer_question, next_questions, start_interview
from omniarchitect.model import Project
from omniarchitect.stage_state import CONFIRMED, all_states
from omniarchitect.workflow import StageRunner

ONE_LINER = "我有一套 150㎡ 的大平层，一家三口，想要现代意式极简，预算 160 万"
ANSWERS: Dict[str, str] = {
    "location": "杭州，南向",
    "schedule": "明年 6 月前入住",
    "structure": "结构图纸有，两道墙待现场确认",
    "site_conditions": "二手房翻新",
    "deliverable_depth": "方案 + 施工图",
}


def _answer_all(project: Project, answers: Dict[str, str]) -> List[str]:
    """模拟客户：只答自己会的；同一槽位不答第二遍。"""
    asked: List[str] = []
    for _ in range(8):
        qs = next_questions(project, limit=3)
        assert len(qs) <= 3, f"一轮问了 {len(qs)} 个问题，超过系统上限 3"
        pick = next((q for q in qs if q.slot in answers and q.slot not in asked), None)
        if pick is None:
            break
        assert pick.slot not in asked
        answer_question(project, pick.id, answers[pick.slot])
        asked.append(pick.slot)
    return asked


def _residential(tmp: Path) -> Project:
    p = build_demo_project(tmp / "proj")
    p.constraints = {**(p.constraints or {}), "style": "现代意式极简",
                     "budget_cny": 1_600_000}
    p.save(tmp / "proj" / "project.json")
    start_interview(p, ONE_LINER)
    return p


# --------------------------------------------------------------------------
def test_client_is_never_asked_the_same_slot_twice():
    with tempfile.TemporaryDirectory() as td:
        p = _residential(Path(td))
        asked = _answer_all(p, ANSWERS)
        assert asked, "系统一个问题都没问"
        assert len(asked) == len(set(asked)), f"重复询问：{asked}"
        # 已回答的槽位不会再出现在后续问题里
        later = {q.slot for q in next_questions(p, limit=10)}
        assert not (set(asked) & later), f"答过的槽位又被问了：{set(asked) & later}"


def test_one_sentence_start_reaches_a_signed_brief():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        p = _residential(tmp)
        _answer_all(p, ANSWERS)
        runner = StageRunner(p, tmp / "out", project_dir=tmp / "proj",
                             assume_approval=False)
        out = runner.run_stage("S1", confirm=False)
        assert out.status == "ok", out.error
        g1 = decide_g1(p, "approved", by="业主")
        assert g1.decision == "approved" and g1.stage_status == CONFIRMED
        assert (p.meta.get("intake") or {}).get("baseline"), "G1 没写任务书基准"


def test_residential_runs_to_s8_with_real_gates():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        p = _residential(tmp)
        _answer_all(p, ANSWERS)
        runner = StageRunner(p, tmp / "out", project_dir=tmp / "proj",
                             assume_approval=False)
        assert runner.run_stage("S1", confirm=False).status == "ok"
        assert decide_g1(p, "approved", by="业主").decision == "approved"

        assert runner.run_stage("S2", confirm=False).status == "ok"
        chosen = next(c for c in p.meta["concept"]["options"]["concepts"]
                      if (c.get("spatial_prototype") or {}).get("plan_strategy"))
        C.select(p, chosen["concept_id"])
        assert runner.approve("S2", by="业主")["status"] == CONFIRMED

        assert runner.run_stage("S3", confirm=False).status == "ok"
        assert runner.approve("S3", by="业主")["status"] == CONFIRMED

        for sid in ("S4", "S5", "S6", "S7", "S8"):
            out = runner.run_stage(sid, confirm=False)
            assert out.status in ("ok", "degraded"), (sid, out.status, out.error)
            assert runner.approve(sid, by="业主")["status"] == CONFIRMED, sid

        states = {s.stage: s.status for s in all_states(p)}
        assert all(states[f"S{i}"] == CONFIRMED for i in range(1, 9)), states
        assert len(p.artifacts) > 8, "S1–S8 跑完却没有足够成果登记"


def test_office_gate_blocks_instead_of_faking_an_approval():
    """办公原型没有对应平面策略 → G3 必须拦，S4 必须起不来。"""
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        p = build_demo_project(tmp / "proj")
        p.project_id = "office-fitout"
        p.name = "办公空间（既有楼层改造）"
        p.program = [
            {"name": "开放办公区", "recipe": "open_office", "area_m2": 46, "zone": "day"},
            {"name": "会议室A", "recipe": "meeting", "area_m2": 14, "zone": "day"},
            {"name": "专注间", "recipe": "focus", "area_m2": 8, "zone": "night"},
            {"name": "接待前厅", "recipe": "reception", "area_m2": 10, "zone": "entry"},
        ]
        p.constraints = {"style": "", "budget_cny": 3_200_000}
        p.save(tmp / "proj" / "project.json")
        start_interview(p, "公司要搬办公室，一百多平，六十人")
        answer_question(p, "off.headcount", "60 人")
        decide_g1(p, "approved", by="业主")
        assert finishes.project_profile(p) == "office"

        runner = StageRunner(p, tmp / "out", project_dir=tmp / "proj",
                             assume_approval=False)
        runner.run_stage("S2", confirm=False)
        supported = [c for c in p.meta["concept"]["options"]["concepts"]
                     if (c.get("spatial_prototype") or {}).get("plan_strategy")]
        assert not supported, "办公方向不该有可落地策略——若有了，本测试要改"
        C.select(p, p.meta["concept"]["options"]["concepts"][0]["concept_id"])
        assert runner.approve("S2", by="业主")["status"] == CONFIRMED
        runner.run_stage("S3", confirm=False)

        g3 = runner.approve("S3", by="业主")
        assert g3["status"] != CONFIRMED, "没有平面策略却签发了 G3"
        ids = " ".join(g3["notes"])
        assert "G3-PROTOTYPE-UNSUPPORTED" in ids
        # 上游没签，S4 不许开跑
        s4 = runner.run_stage("S4", confirm=False)
        assert s4.status == "blocked"
