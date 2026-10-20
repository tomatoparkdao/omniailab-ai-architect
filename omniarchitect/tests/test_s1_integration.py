"""S1 integration tests: one engine, one gate, real cross-stage limits.

Each test maps to an acceptance scenario in the integration brief:

A  one sentence → interview → bundle → G1
B  G1 approved → S2 runs
C  unverified structure limits the structural work in S4
D  unverified dimensions limit the precision-dependent work in S3
E  the old confirm entry cannot bypass the G1 review
F  --assume-approval never impersonates the client
G  unknown → verified lifts the limitation
H  editing after G1 reopens the affected stages
I  the eight-stage pipeline still runs end to end

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from omniarchitect.demo import build_demo_project
from omniarchitect.intake import (
    DISCIPLINE_BUNDLE_FILES,
    S1_BUNDLE_FILES,
    RESEARCH_BUNDLE_FILES,
    S1_JUDGMENT_FILES,
    answer_question,
    assess_gate,
    check_stage,
    close_uncertainty,
    decide_gate,
    generate_bundle,
    register_uncertainty,
    start_interview,
)
from omniarchitect.intake.diligence import UncertaintyItem, register_source, SourceEntry
from omniarchitect.intake.gate import check_baseline
from omniarchitect.model import Project
from omniarchitect.stage_state import CONFIRMED, get_state
from omniarchitect.workflow import StageRunner

ONE_LINER = "我有一套 150㎡ 的大平层在杭州市，一家三口，希望做现代意式极简"


def _runner(p: Project, root: Path, **kw) -> StageRunner:
    return StageRunner(p, root / "out", project_dir=root / "proj", **kw)


def _no_geometry(tmp: Path) -> Project:
    p = Project(project_id="T-NOGEO", name="150㎡ 大平层",
                constraints={"style": "现代意式极简"})
    (tmp / "proj").mkdir(parents=True, exist_ok=True)
    p.save(tmp / "proj" / "project.json")
    return p


# --------------------------------------------------------------------------
# A. one sentence all the way to G1
# --------------------------------------------------------------------------
def test_a_one_sentence_runs_the_whole_s1_engine():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        p = _no_geometry(tmp)
        assert not p.levels, "这个场景就是要没有几何"

        runner = _runner(p, tmp)
        start_interview(p, ONE_LINER)
        answer_question(p, "base.needs", "客厅要能坐下 8 个人吃饭；东西很多需要收纳")

        out = runner.run_stage("S1")
        assert out.status == "ok", out.error
        # 八份核心成果必须在；多专业六份随范围追加，也必须在。
        produced = {Path(a).name for a in out.artifacts}
        assert set(S1_BUNDLE_FILES) <= produced, set(S1_BUNDLE_FILES) - produced
        assert set(DISCIPLINE_BUNDLE_FILES) <= produced, (
            set(DISCIPLINE_BUNDLE_FILES) - produced)
        # 案例研究两份是条件产出：联网才有。这里不联网，所以不该出现；
        # 关键是清单与实际产出一致——不许"清单说有、目录里没有"。
        assert not (set(RESEARCH_BUNDLE_FILES) & produced), (
            f"离网时不该写出案例清单：{set(RESEARCH_BUNDLE_FILES) & produced}")
        # 一页判断（design-position.md）也是 S1 的产出：客户先看判断，再看任务书。
        assert produced == (set(S1_BUNDLE_FILES) | set(DISCIPLINE_BUNDLE_FILES)
                            | set(S1_JUDGMENT_FILES)), produced

        # 无几何时精度为诊断级，并写进产出
        assert p.meta["intake"]["precision"] == "diagnostic"
        brief = (Path(out.artifacts[0]).parent / "design-brief.md").read_text(encoding="utf-8")
        assert "诊断级" in brief

        approval = runner.approve("S1", by="业主")
        assert approval["status"] == CONFIRMED
        assert p.meta["intake"]["baseline"]["source"] == "owner"


# --------------------------------------------------------------------------
# B. G1 approved → S2 runs
# --------------------------------------------------------------------------
def test_b_s2_runs_after_g1():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        p = build_demo_project(tmp / "proj")
        p.save(tmp / "proj" / "project.json")
        runner = _runner(p, tmp)
        runner.run_stage("S1")

        assess = assess_gate(p)
        assert not assess.blocks_gate, assess.blocks_gate

        approval = runner.approve("S1", by="业主")
        assert approval["status"] == CONFIRMED

        s2 = runner.run_stage("S2")
        assert s2.status == "ok", s2.error


# --------------------------------------------------------------------------
# C / D. cross-stage limits
# --------------------------------------------------------------------------
def _with_uncertainties(p: Project) -> Project:
    register_uncertainty(p, UncertaintyItem(
        id="U-STRUCTURAL", topic="structural",
        statement="结构条件：只有原始结构图，未现场核实",
        state="documented", affects="S4"))
    register_uncertainty(p, UncertaintyItem(
        id="U-DIMENSION", topic="dimension",
        statement="原始图纸：只有拍照/扫描件",
        state="inferred", affects="S3"))
    return p


def test_c_unverified_structure_limits_s4_without_blocking_it():
    with tempfile.TemporaryDirectory() as d:
        p = _with_uncertainties(build_demo_project(Path(d) / "proj"))
        g = check_stage(p, "S4")
        assert g.allowed and not g.blocked, "S4 不应被整体拦下"
        assert g.restrictions, "必须写明哪些工作受限"
        assert any("结构" in r or "拆改" in r for r in g.restrictions)
        assert g.needs_human, "结构未核验必须要求专业复核"

        # 施工图阶段则整体受阻
        s7 = check_stage(p, "S7")
        assert s7.blocked, "施工图不得基于未证实的结构条件"


def test_d_unverified_dimension_limits_s3():
    with tempfile.TemporaryDirectory() as d:
        p = _with_uncertainties(build_demo_project(Path(d) / "proj"))
        g = check_stage(p, "S3")
        assert g.allowed and not g.blocked
        assert any("真实尺寸" in r or "精确尺寸" in r for r in g.restrictions)

        # 概念阶段不受影响
        s2 = check_stage(p, "S2")
        assert not s2.blocked
        assert all("不得给出任何实际尺寸" in r or "拆改" in r for r in s2.restrictions)


def test_cd_limits_show_up_on_the_stage_outcome():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        p = build_demo_project(tmp / "proj")
        p.save(tmp / "proj" / "project.json")
        _with_uncertainties(p)
        runner = _runner(p, tmp)
        runner.run_stage("S1")
        runner.approve("S1", by="业主", acknowledge=())
        runner.run_stage("S2")
        runner.approve("S2", by="业主")
        out = runner.run_stage("S3")
        assert out.status == "ok"
        assert any("限制" in n for n in out.notes), out.notes


# --------------------------------------------------------------------------
# E. the old entry cannot bypass the review
# --------------------------------------------------------------------------
def test_e_confirm_goes_through_the_same_review():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        p = build_demo_project(tmp / "proj")
        p.program = [{"name": f"房间{i}", "recipe": "bedroom", "area_m2": 40}
                     for i in range(10)]
        p.save(tmp / "proj" / "project.json")
        runner = _runner(p, tmp)
        runner.run_stage("S1")

        # 旧的 confirm() 也走同一套 G1 判定：需求矛盾时不能通过
        st = runner.confirm("S1", by="业主")
        assert st["status"] != CONFIRMED, "旧入口绕过了 G1"
        assert st["assessment"]["blocks_gate"], "必须回报需业主决定的事项"

        # 逐项确认后才允许
        ok = runner.approve("S1", by="业主", acknowledge=["F-AREA-01"])
        assert ok["status"] == CONFIRMED


# --------------------------------------------------------------------------
# F. demo approval is not a signature
# --------------------------------------------------------------------------
def test_f_assume_approval_does_not_impersonate_the_client():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        p = build_demo_project(tmp / "proj")
        p.save(tmp / "proj" / "project.json")
        runner = _runner(p, tmp, assume_approval=True)
        out = runner.run_stage("S1")
        assert out.status == "ok"

        intake = p.meta["intake"]
        assert get_state(p, "S1").status == CONFIRMED
        assert not intake.get("baseline"), "演示不得写入业主基准"
        demo = intake.get("demo_approval") or {}
        assert demo.get("source") == "demo"
        assert "演示" in str(demo.get("confirmed_by"))
        assert check_baseline(p)["demo_only"] is True
        assert check_baseline(p)["has_baseline"] is False


# --------------------------------------------------------------------------
# G. verified lifts the limitation
# --------------------------------------------------------------------------
def test_g_verified_condition_lifts_the_limitation():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        p = build_demo_project(tmp / "proj")
        register_uncertainty(p, UncertaintyItem(
            id="U-STRUCTURAL", topic="structural",
            statement="结构条件：不清楚", state="unknown", affects="S4"))
        assert check_stage(p, "S7").blocked

        close_uncertainty(p, "U-STRUCTURAL", evidence="现场探测已确认")
        assert not check_stage(p, "S7").blocked
        assert not check_stage(p, "S4").restrictions
        assert not [u for u in p.meta["intake"]["uncertainty"] if u["open"]]


def test_g_baseline_reports_limitation_change_as_benign():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        p = _no_geometry(tmp)
        start_interview(p, ONE_LINER)
        answer_question(p, "base.needs", "客厅要能坐下 6 个人吃饭")
        decide_gate(p, "approved", by="业主")

        register_uncertainty(p, UncertaintyItem(
            id="U-DIM", topic="dimension", statement="尺寸未核实",
            state="unknown", affects="S3"))
        b = check_baseline(p)
        assert b["change_kind"] == "limitations"
        assert b["requires_change_analysis"] is False, "限制变化不是需求变更"


# --------------------------------------------------------------------------
# H. editing after G1 reopens stages
# --------------------------------------------------------------------------
def test_h_editing_after_g1_reopens_the_affected_stages():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        p = _no_geometry(tmp)
        start_interview(p, ONE_LINER)
        answer_question(p, "base.budget", "硬装 80 万")
        answer_question(p, "base.needs", "客厅要能坐下 6 个人吃饭")
        decide_gate(p, "approved", by="业主")
        assert get_state(p, "S1").status == CONFIRMED

        result = answer_question(p, "base.budget", "硬装 60 万")
        assert result["requires_change_analysis"] is True
        assert result["reopened_stages"], "必须真的把阶段状态改掉"
        assert get_state(p, "S1").status != CONFIRMED
        assert p.change_log, "变更必须进 change_log"
        assert check_baseline(p)["change_kind"] == "brief"
        assert check_baseline(p)["requires_change_analysis"] is True


# --------------------------------------------------------------------------
# I. pipeline still runs
# --------------------------------------------------------------------------
def test_i_full_pipeline_still_runs_with_assumed_approval():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        p = build_demo_project(tmp / "proj")
        p.save(tmp / "proj" / "project.json")
        runner = _runner(p, tmp, assume_approval=True)
        manifest = runner.run_all(confirm_all=True)
        failed = [o.stage for o in manifest.outcomes if o.status in ("failed", "blocked")]
        assert not failed, [(o.stage, o.error) for o in manifest.outcomes
                            if o.status in ("failed", "blocked")]


# --------------------------------------------------------------------------
# one engine: the two entry points agree
# --------------------------------------------------------------------------
def test_the_two_entry_points_produce_the_same_bundle():
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        p = build_demo_project(tmp / "proj")
        p.save(tmp / "proj" / "project.json")

        runner = _runner(p, tmp)
        out = runner.run_stage("S1")
        run_dir = Path(out.artifacts[0]).parent

        p2 = Project.load(tmp / "proj" / "project.json")
        cli_dir = tmp / "cli"
        generate_bundle(p2, cli_dir)

        for name in ("user-needs.json", "source-register.json",
                     "uncertainty-register.json"):
            a = json.loads((run_dir / name).read_text(encoding="utf-8"))
            b = json.loads((cli_dir / name).read_text(encoding="utf-8"))
            a.pop("generated_at", None)
            b.pop("generated_at", None)
            assert a == b, f"{name} 两个入口不一致"


def test_measure_filename_alone_does_not_upgrade_precision():
    """只登记文件名不给精度升级——documented 不等于 verified。"""
    from omniarchitect.intake.diligence import precision_level

    with tempfile.TemporaryDirectory() as d:
        p = build_demo_project(Path(d) / "proj")
        before = precision_level(p)
        register_source(p, SourceEntry(id="S-FAKE", kind="measure",
                                       file="我-量-过-了.pdf", confidence="verified"))
        assert precision_level(p) == before
        assert not check_stage(p, "S7").blocked, "文件名不该改变任何阶段准入"
