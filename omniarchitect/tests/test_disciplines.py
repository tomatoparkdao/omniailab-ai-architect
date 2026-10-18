"""多专业范围：谁在范围、问谁的问题、S2 有没有各专业方向、S3 会不会乱出图。

这组测试对应本轮 P0 的核心：**不同设计类型不能被同一套住宅逻辑套住**。

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from omniarchitect import disciplines as D
from omniarchitect import disciplines as disc
from omniarchitect.intake.interview import answer_question, next_questions, start_interview
from omniarchitect.intake.gate import decide_gate as decide_g1
from omniarchitect.model import Project
from omniarchitect.stage_state import CONFIRMED
from omniarchitect.workflow import StageRunner


def _p(tmp: Path, name: str) -> Project:
    p = Project(project_id="scope-test", name=name)
    p.save(tmp / "project.json")
    return p


# --------------------------------------------------------------------------
# 1. 六种委托的范围判定
# --------------------------------------------------------------------------
def test_six_commission_types_get_different_scopes():
    cases = {
        "住宅装修（拆墙）": ("120㎡ 住宅装修，拆一堵墙，厨房卫生间重做", "residential",
                        {"interior", "structure", "mep"}),
        "纯景观": ("只做院子景观，铺装加种植，室内不动", "architecture",
                 {"landscape"}),
        "结构加固": ("厂房结构加固，楼板承重不够，不做室内", "architecture",
                  {"structure"}),
        "建筑新建": ("新建三层小楼，需要报建，容积率和退线要算", "architecture",
                  {"architecture", "planning"}),
        "办公": ("800㎡ 办公室装修，60 人，要会议室和空调新风", "office",
               {"interior", "mep"}),
    }
    for label, (text, pid, expect_active) in cases.items():
        scope = D.detect([text], profile_id=pid)
        active = set(scope.active())
        assert expect_active <= active, (label, sorted(active))
        if label == "纯景观":
            assert "interior" in scope.out(), "「室内不动」应被识别为明确不做"


def test_out_of_scope_requires_evidence():
    with tempfile.TemporaryDirectory() as td:
        p = _p(Path(td), "景观")
        try:
            D.set_state(p, "interior", D.OUT_OF_SCOPE)
        except D.ScopeError as exc:
            assert "证据" in str(exc)
        else:
            raise AssertionError("没有任何证据就把室内标成不做")
        D.set_state(p, "interior", D.OUT_OF_SCOPE, evidence="客户原话：室内不动")
        assert "interior" in D.load(p).out()


# --------------------------------------------------------------------------
# 2. 问谁的问题
# --------------------------------------------------------------------------
def test_questions_follow_the_scope():
    with tempfile.TemporaryDirectory() as td:
        p = _p(Path(td), "院子景观")
        start_interview(p, "只做院子景观，铺装加种植，室内不动")
        ids = [q.id for q in next_questions(p, limit=12)]
        slots = [q.slot for q in next_questions(p, limit=12)]
        # 室内不在范围：不该追问室内专属问题
        assert "scope.structure_type" not in ids
        assert "storage" not in slots
        # 景观在范围：会问到室外用途
        assert any(s in ("outdoor_program", "site_conditions") for s in slots), slots


def test_scope_is_persisted_and_survives_reload():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        p = _p(tmp, "住宅")
        start_interview(p, "120㎡ 住宅装修，拆一堵墙")
        p.save(tmp / "project.json")
        again = Project.load(tmp / "project.json")
        scope = D.load(again)
        assert scope.entries, "范围没有落盘"
        assert "interior" in scope.active()


# --------------------------------------------------------------------------
# 3. S2：一套概念，多专业方向
# --------------------------------------------------------------------------
def test_concept_carries_one_direction_per_active_discipline():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        p = _p(tmp, "住宅装修")
        start_interview(p, "120㎡ 住宅装修，拆一堵墙，厨房卫生间重做")
        answer_question(p, "base.needs", "收纳不够，厨房太小")
        assert decide_g1(p, "approved", by="业主").decision == "approved"
        from omniarchitect import concept as C

        C.generate_bundle(p, tmp / "out", with_deck=False)
        concepts = p.meta["concept"]["options"]["concepts"]
        scope = D.load(p)
        for c in concepts:
            dirs = c.get("disciplines") or {}
            missing = set(scope.active()) - set(dirs)
            assert not missing, (c["concept_id"], sorted(missing))
            # 缺资料的专业必须标 requires_input，不能假装有结论
            assert any(d["status"] == "requires_input" for d in dirs.values()), dirs


# --------------------------------------------------------------------------
# 4. G2：范围内的专业缺方向就不能确认
# --------------------------------------------------------------------------
def test_g2_blocks_when_a_discipline_direction_is_missing():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        p = _p(tmp, "住宅")
        start_interview(p, "120㎡ 住宅装修，拆一堵墙")
        answer_question(p, "base.needs", "收纳不够")
        decide_g1(p, "approved", by="业主")
        from omniarchitect import concept as C

        C.generate_bundle(p, tmp / "out", with_deck=False)
        # 人为抹掉结构方向，模拟"只做了一半的概念"
        state = p.meta["concept"]
        state["options"]["concepts"][0]["disciplines"].pop("structure", None)
        state["selected"] = state["options"]["concepts"][0]["concept_id"]
        a = C.assess_gate(p)
        assert any(r["id"] == "G2-DISCIPLINE-structure" for r in a.blockers), a.blockers


# --------------------------------------------------------------------------
# 5. S3：非空间类专项不许拿房间算法顶替
# --------------------------------------------------------------------------
def test_s3_refuses_to_fake_a_landscape_plan():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        p = _p(tmp, "院子景观")
        start_interview(p, "只做院子景观，铺装加种植，室内不动")
        answer_question(p, "base.needs", "院子想能坐下喝茶，好打理")
        decide_g1(p, "approved", by="业主")
        runner = StageRunner(p, tmp / "out", project_dir=tmp, assume_approval=False)
        out = runner.run_stage("S3", confirm=False)
        assert out.status == "blocked", out.status
        assert "不能拿房间组合算法冒充" in (out.error or "")
        assert "景观" in (out.error or "") or "结构" in (out.error or "")


# --------------------------------------------------------------------------
# 6. S1 成果：范围、接口、责任、缺料四份必须真落盘
# --------------------------------------------------------------------------
def test_s1_bundle_carries_scope_and_interfaces():
    from omniarchitect.intake.report import (
        DISCIPLINE_BUNDLE_FILES,
        generate_bundle,
    )

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        p = _p(tmp, "三层别墅")
        start_interview(
            p, "有块地，建三层别墅，现代极简，带庭院水池，室内精装，结构机电一并考虑")
        out = tmp / "S1"
        res = generate_bundle(p, out)
        assert res["count"] >= len(DISCIPLINE_BUNDLE_FILES)
        for name in DISCIPLINE_BUNDLE_FILES:
            assert (out / name).exists(), name

        payload = json.loads((out / "discipline-scope.json").read_text(encoding="utf-8"))
        assert {"architecture", "interior", "structure", "mep", "landscape"} <= set(
            payload["active"]), payload["active"]
        # 接口矩阵按"双方是否都在范围"筛过，且有会影响到的阶段
        iface = json.loads(
            (out / "discipline-interface-matrix.json").read_text(encoding="utf-8"))
        ids = {r["id"] for r in iface["interfaces"]}
        assert "IF-STR-LOAD" in ids and "IF-IN-LAND" in ids, ids
        assert iface["counts"]["active"] >= 3

        asks = (out / "information-request-list.md").read_text(encoding="utf-8")
        assert "找谁要" in asks and "要不到的影响" in asks
        resp = (out / "discipline-responsibility-matrix.md").read_text(encoding="utf-8")
        assert "注册结构工程师" in resp and "不代替法定签署" in (resp + asks)


def test_single_discipline_bundle_does_not_invent_a_matrix():
    """纯室内项目不该产出一份"全 not_applicable"的假接口矩阵。

    空表比没有更危险：它会被读成"已核对无冲突"。
    """
    from omniarchitect.intake.report import (
        DISCIPLINE_BUNDLE_FILES,
        S1_BUNDLE_FILES,
        generate_bundle,
    )

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        p = _p(tmp, "只刷墙")
        start_interview(p, "家里墙面重新刷一下，其他都不动")
        out = tmp / "S1"
        res = generate_bundle(p, out)
        # 范围为空（没有专业被识别）时：只出八份核心成果
        if not disc.load(p).active():
            assert res["count"] == len(S1_BUNDLE_FILES)
            for name in DISCIPLINE_BUNDLE_FILES:
                assert not (out / name).exists(), name
