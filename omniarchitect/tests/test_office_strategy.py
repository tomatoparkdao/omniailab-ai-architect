"""办公平面策略：必须真的是一套办公布局，而且能失败。

三条底线：

1. 不是把住宅 `band_day_night` 换个名字——开放办公是一整块连续空间，
   会议与接待共用前场带，专注/服务在后场竖排；
2. 两套方案有可解释的差别（会议带换边 + 通道宽度），不是随机数；
3. 人数装不下时，S3 的一致性校核要真的判失败，G3 不能签。

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import tempfile
from pathlib import Path

from omniarchitect import concept as C
from omniarchitect.demo import build_demo_project
from omniarchitect.intake.gate import decide_gate as decide_g1
from omniarchitect.intake.interview import answer_question, start_interview
from omniarchitect.model import Project
from omniarchitect.planner import PlanGenerator, SchemeOptions
from omniarchitect.workflow import StageRunner


def _office(tmp: Path, headcount: int) -> Project:
    p = build_demo_project(tmp / "proj")
    p.project_id = "office-fitout"
    p.name = "办公空间（既有楼层改造）"
    p.program = [
        {"name": "开放办公区", "recipe": "open_office", "area_m2": 46, "zone": "day"},
        {"name": "会议室A", "recipe": "meeting", "area_m2": 14, "zone": "day"},
        {"name": "专注间", "recipe": "focus", "area_m2": 8, "zone": "night"},
        {"name": "接待前厅", "recipe": "reception", "area_m2": 10, "zone": "entry"},
        {"name": "打印储物", "recipe": "storage", "area_m2": 6, "zone": "service"},
    ]
    p.constraints = {"style": "", "budget_cny": 3_200_000}
    p.save(tmp / "proj" / "project.json")
    start_interview(p, f"办公室，{headcount} 人")
    answer_question(p, "off.headcount", f"{headcount} 人")
    return p


# --------------------------------------------------------------------------
# 1. 布局本身：是办公，不是住宅带
# --------------------------------------------------------------------------
def test_office_layout_is_not_a_residential_band():
    with tempfile.TemporaryDirectory() as td:
        p = _office(Path(td), 25)
        gen = PlanGenerator(p, "L1")
        a = gen.generate(SchemeOptions(variant="A", strategy="office_cluster",
                                       corridor_width_mm=1200.0, flip=False))
        b = gen.generate(SchemeOptions(variant="B", strategy="office_cluster",
                                       corridor_width_mm=1500.0, flip=True))

        assert a.strategy == "office_cluster"
        names = {s.name for s in a.spaces}
        assert {"接待前厅", "会议室A", "开放办公区", "专注间"} <= names, names
        # 开放办公必须是一整块连续空间
        opens = [s for s in a.spaces if s.properties.get("recipe") == "open_office"]
        assert len(opens) == 1 and opens[0].area_m2 > 40, [s.area_m2 for s in opens]
        # 有走廊，且访客区与工位区被通道分开
        corr = [s for s in a.spaces if s.use == "circulation"]
        assert corr and corr[0].area_m2 > 5
        # 两套方案确实不同：开放办公形状或走廊宽度变了
        def shape(scheme):
            return {(s.name, round(s.area_m2, 1)) for s in scheme.spaces}
        assert shape(a) != shape(b), "两套办公方案完全一样，等于没做对比"


def test_office_scheme_reports_area_shortfalls():
    with tempfile.TemporaryDirectory() as td:
        p = _office(Path(td), 25)
        gen = PlanGenerator(p, "L1")
        res = gen.generate(SchemeOptions(variant="A", strategy="office_cluster"))
        for s in res.spaces:
            target = s.properties.get("target_area_m2")
            if target:
                assert s.area_m2 > 0.8, f"{s.name} 只有 {s.area_m2:.1f}㎡"
        # 有差额就要说出来，不能静默压缩
        for w in res.warnings:
            assert "实得" in w or "裁剪" in w or "未分配" in w or "超出" in w


# --------------------------------------------------------------------------
# 2. 可行 → G3 正式通过
# --------------------------------------------------------------------------
def test_feasible_office_passes_g3():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        p = _office(tmp, 25)
        assert decide_g1(p, "approved", by="业主").decision == "approved"
        runner = StageRunner(p, tmp / "out", project_dir=tmp / "proj",
                             assume_approval=False)
        assert runner.run_stage("S2", confirm=False).status == "ok"
        supported = [c for c in p.meta["concept"]["options"]["concepts"]
                     if (c.get("spatial_prototype") or {}).get("plan_strategy")]
        assert supported, "办公方向应至少有一个已实现策略"
        C.select(p, supported[0]["concept_id"])
        assert runner.approve("S2", by="业主")["status"] == "confirmed"
        assert runner.run_stage("S3", confirm=False).status == "ok"
        g3 = runner.approve("S3", by="业主")
        assert g3["status"] == "confirmed", g3["notes"]
        assert any("一致性 pass" in n for n in g3["notes"])


# --------------------------------------------------------------------------
# 3. 装不下 → G3 必须失败
# --------------------------------------------------------------------------
def test_infeasible_headcount_fails_the_consistency_check():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        p = _office(tmp, 60)
        # G1 先拦；业主书面接受后再看平面自己能不能成立
        from omniarchitect.intake.gate import assess_gate as assess_g1

        assert "F-CAP-01" in [b["id"] for b in assess_g1(p).blocks_gate]
        assert decide_g1(p, "approved", by="业主",
                         acknowledge=["F-CAP-01"]).decision == "approved"
        runner = StageRunner(p, tmp / "out", project_dir=tmp / "proj",
                             assume_approval=False)
        runner.run_stage("S2", confirm=False)
        supported = [c for c in p.meta["concept"]["options"]["concepts"]
                     if (c.get("spatial_prototype") or {}).get("plan_strategy")]
        C.select(p, supported[0]["concept_id"])
        runner.approve("S2", by="业主")
        runner.run_stage("S3", confirm=False)

        from omniarchitect.concept.handoff import plan_record

        rec = plan_record(p)
        assert rec["conformance"] == "fail", rec
        assert any(c["id"] == "H-CAPACITY" for c in rec["conflicts"]), rec["conflicts"]

        g3 = runner.approve("S3", by="业主")
        assert g3["status"] != "confirmed", "装不下的平面被签发了"
        assert "G3-CONCEPT-CONFLICT" in " ".join(g3["notes"])
