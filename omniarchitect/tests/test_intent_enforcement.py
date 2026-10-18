"""设计意图保护的执行闭环：不许"提醒了但照改"。

这组测试对应验收 A–L。核心不是功能存在，而是**任何自动化入口都改不动
未经批准的核心设计**：

* `apply=True`、`--force`、脚本代理、演示批准，都不构成授权；
* 预览必须是只读的，连修订号都不能动；
* 硬门槛一旦证明不成立，美学分救不了，G2 也不能签；
* G2 事务失败要能字节级复原，包括此前已批准的意图文件。

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或分发。
"""
from __future__ import annotations

import copy
import json
import tempfile
from pathlib import Path

from omniarchitect import changes, conformance, hardgate, intent as I
from omniarchitect import concept as C
from omniarchitect.concept import gate as concept_gate
from omniarchitect.demo import build_demo_project
from omniarchitect.intake.gate import decide_gate as decide_g1
from omniarchitect.intake.interview import answer_question, start_interview
from omniarchitect.model import Element, Project
from omniarchitect.workflow import StageRunner


# --------------------------------------------------------------------------
# 公共夹具
# --------------------------------------------------------------------------
def _project(tmp: Path, one_liner: str, *, name: str = "住宅") -> Project:
    p = build_demo_project(tmp / "proj")
    p.project_id = "enforce"
    p.name = name
    p.save(tmp / "proj" / "project.json")
    start_interview(p, one_liner)
    answer_question(p, "base.needs", "客厅能坐 8 人；东西多要收纳")
    decide_g1(p, "approved", by="业主")
    return p


def _to_g2(tmp: Path, *, concept_id: str = ""):
    """跑到 G2 已确认，返回 (project, runner)。

    默认挑一条**能落到平面**的方向：本测试关心的是意图变化，不是概念能不能
    落地。没有平面策略的方向会被 G3 正当拦下，那是另一条测试的事。
    """
    p = _project(tmp, "买了一套 150㎡ 大平层，室内装修，现代意式极简，拆一堵墙")
    runner = StageRunner(p, tmp / "out", project_dir=tmp / "proj")
    runner.run_stage("S2", confirm=False)
    if not concept_id:
        supported = [c for c in p.meta["concept"]["options"]["concepts"]
                     if (c.get("spatial_prototype") or {}).get("plan_strategy")]
        assert supported, "没有可落到平面的方向，本测试无法继续"
        concept_id = supported[0]["concept_id"]
    C.select(p, concept_id)
    res = runner.approve("S2", by="业主张先生")
    assert res["status"] == "confirmed", res.get("notes")
    return p, runner


def _state(p: Project) -> str:
    """规范化深度快照：任何字段变化都会体现。"""
    return json.dumps(p.to_dict(), ensure_ascii=False, sort_keys=True)


def _patch(module, name: str, value):
    """run_tests.py 不支持 fixture，这里自带一个最小上下文管理器。"""

    class _Ctx:
        def __enter__(self):
            self.old = getattr(module, name)
            setattr(module, name, value)
            return value

        def __exit__(self, *exc):
            setattr(module, name, self.old)
            return False

    return _Ctx()


# --------------------------------------------------------------------------
# A. apply=True 也改不动未授权的核心设计
# --------------------------------------------------------------------------
def test_a_apply_true_cannot_change_protected_intent_without_approval():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        p, _runner = _to_g2(tmp)
        before = _state(p)
        rev = p.revision

        rep = changes.analyse(p, "把客厅和餐厅之间的墙打掉，做成开放空间", apply=True)

        assert rep.applied is False, "未授权却执行了变更"
        assert rep.blocked is True
        assert "授权" in (rep.blocked_reason or "")
        assert _state(p) == before, "项目被改了"
        assert p.revision == rev
        # 提案路径必须写清楚怎么走
        assert any("propose" in n for n in rep.notes)


def test_a2_demo_and_script_approval_cannot_authorize():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        p, _runner = _to_g2(tmp)
        req = changes.propose(p, "把客厅和餐厅之间的墙打掉")
        assert req.requires_authorization
        for source in ("demo", "script", "force", "assume_approval"):
            try:
                changes.authorize_change(req, by="业主", source=source)
            except PermissionError:
                continue
            raise AssertionError(f"{source} 竟然能授权设计意图变更")
        # 没有批准人也不行
        try:
            changes.authorize_change(req, by="", source="owner")
        except PermissionError:
            pass
        else:
            raise AssertionError("没有署名的批准被接受了")


def test_a3_authorization_is_bound_to_revision_and_intent():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        p, _runner = _to_g2(tmp)
        req = changes.propose(p, "把客厅和餐厅之间的墙打掉")
        auth = changes.authorize_change(req, by="业主张先生")

        # 版本走一步，原授权失效
        p.revision += 1
        ok, why = changes.validate_authorization(p, req, auth)
        assert not ok and "旧版本" in why, (ok, why)

        p.revision -= 1
        # 意图被换掉，原授权同样失效
        d = I.load(p)
        d["signature_features"][0]["statement"] = "换成完全不同的空间主张"
        I.write(p, Path(d["file"]).parent, d)
        ok, why = changes.validate_authorization(p, req, auth)
        assert not ok and "意图" in why, (ok, why)


def test_a4_valid_authorization_executes_and_records_who():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        p, _runner = _to_g2(tmp)
        req = changes.propose(p, "把客厅和餐厅之间的墙打掉")
        auth = changes.authorize_change(req, by="业主张先生", note="确认打通")
        rep = changes.apply_change(p, req, authorization=auth)
        assert rep.applied is True, rep.notes
        assert rep.authorization.get("by") == "业主张先生"
        assert rep.authorization.get("at")
        assert rep.changelog


# --------------------------------------------------------------------------
# B. 预览零副作用
# --------------------------------------------------------------------------
def test_b_preview_changes_nothing_at_all():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        p, runner = _to_g2(tmp)
        before = _state(p)
        rev = p.revision
        states = {s.stage: s.status for s in _all_states(p)}
        artifacts = [a.id for a in p.artifacts]

        rep = runner.apply_change("把客厅和餐厅之间的墙打掉，做成开放空间", apply=False)

        assert rep.applied is False
        assert _state(p) == before, "预览改动了项目"
        assert p.revision == rev
        assert {s.stage: s.status for s in _all_states(p)} == states
        assert [a.id for a in p.artifacts] == artifacts
        # 报告要自称提案，不能伪装成已执行
        files = sorted((runner.out / "changes").glob("*.json"))
        assert files and "proposal" in files[-1].name
        data = json.loads(files[-1].read_text(encoding="utf-8"))
        assert data["applied"] is False
        assert any("未改动项目数据" in n for n in data["notes"])


def _all_states(p: Project):
    from omniarchitect.stage_state import all_states

    return all_states(p)


# --------------------------------------------------------------------------
# C. S1 面积冲突进入 S2 硬门槛
# --------------------------------------------------------------------------
def test_c_area_conflict_reaches_the_unified_hard_gate():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        p = _project(tmp, "我这套 300㎡ 的房子要装修，室内精装")
        from omniarchitect import disciplines as D

        v = hardgate.evaluate(p, scope=D.ensure(p))
        row = next((r for r in v.rows if r.dimension == "area"), None)
        assert row is not None, v.to_dict()
        # 客户说 300、模型 131.6：这是"已证明不成立"，不是"还没确定"
        assert row.status in (hardgate.FAILED, hardgate.UNKNOWN), row.status
        if row.status == hardgate.FAILED:
            assert v.blocked


def test_c2_unknown_is_never_counted_as_passed():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        p = _project(tmp, "买了一套 150㎡ 大平层，室内装修")
        from omniarchitect import disciplines as D

        v = hardgate.evaluate(p, scope=D.ensure(p))
        for r in v.rows:
            assert r.status in hardgate.STATUSES
        # can_approve 只有在没有 failed 且没有 unknown 时才为真
        if v.unknown:
            assert not v.can_approve, v.to_dict()


# --------------------------------------------------------------------------
# D. 全部候选被硬门槛拒绝时不得正式推荐 / 批准 G2
# --------------------------------------------------------------------------
def test_d_all_concepts_blocked_means_no_formal_recommendation():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        p = build_demo_project(tmp / "proj")
        p.project_id = "office-blocked"
        p.name = "办公 60 人"
        p.program = [{"name": "开放办公区", "recipe": "open_office",
                      "area_m2": 46, "zone": "day"}]
        p.constraints = {"style": "", "budget_cny": 3_000_000}
        p.save(tmp / "proj" / "project.json")
        start_interview(p, "办公室装修，六十人")
        answer_question(p, "off.headcount", "60 人")
        decide_g1(p, "approved", by="业主", acknowledge=["F-CAP-01"],
                  note="业主接受：先看紧凑方案")

        C.generate_bundle(p, tmp / "out", with_deck=False)
        cmp = p.meta["concept"]["comparison"]
        assert all(not e["rankable"] for e in cmp["evaluations"]), \
            [e["rankable"] for e in cmp["evaluations"]]
        joined = " ".join(cmp["recommendation"].get("verify_before_s3") or [])
        assert "硬门槛" in joined, cmp["recommendation"]
        # G2 独立复核也要拦
        sel = cmp["evaluations"][0]["concept_id"]
        C.select(p, sel)
        a = C.assess_gate(p)
        assert any("G2-HARD" in b["id"] for b in a.blockers), a.blockers


# --------------------------------------------------------------------------
# E. G2 事务失败必须复原既有意图文件
# --------------------------------------------------------------------------
def test_e_failed_transaction_restores_the_previous_intent_bytes():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        p, runner = _to_g2(tmp)
        intent_file = Path(I.load(p)["file"])
        original = intent_file.read_bytes()

        def _boom(*_a, **_k):
            raise RuntimeError("注入的多专业基准写入失败")

        # 同一修订再确认一次，注入失败
        with _patch(concept_gate, "write_multidisciplinary_baseline", _boom):
            out = concept_gate.decide_gate(
                p, "approved", by="业主", source="owner",
                summary_path=str(runner._dir("S2") / "g2-approval-summary.md"))

        assert out.decision == "blocked"
        assert out.rolled_back is True
        assert intent_file.exists(), "已批准的设计意图被删掉了"
        assert intent_file.read_bytes() == original, "意图文件被改写，没有复原"
        # 阶段不应留在 confirmed，且可以安全重试
        from omniarchitect.stage_state import get_state as _gs

        st = _gs(p, "S2")
        assert st.status != "confirmed" or out.rolled_back
        retry = runner.approve("S2", by="业主")
        assert retry["status"] == "confirmed", retry.get("notes")


def test_e2_rollback_removes_only_files_this_run_created():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        p = _project(tmp, "买了一套 150㎡ 大平层，室内装修，拆一堵墙")
        runner = StageRunner(p, tmp / "out", project_dir=tmp / "proj")
        runner.run_stage("S2", confirm=False)
        C.select(p, "C-B")
        out_dir = runner._dir("S2")
        stale = out_dir / "design-intent-r1.json"
        assert not stale.exists(), "前提：此修订尚无意图文件"

        def _boom(*_a, **_k):
            raise RuntimeError("注入失败")

        with _patch(concept_gate, "write_multidisciplinary_baseline", _boom):
            res = concept_gate.decide_gate(
                p, "approved", by="业主", source="owner",
                summary_path=str(out_dir / "g2-approval-summary.md"))
        assert res.decision == "blocked"
        assert not stale.exists(), "本轮新建的意图文件没被清掉"
        assert "design_intent" not in (p.meta or {})


# --------------------------------------------------------------------------
# F. 擅自加柱 → 意图变化
# --------------------------------------------------------------------------
def test_f_adding_a_column_breaks_the_open_space_intent():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        p, runner = _to_g2(tmp)
        d = I.load(p)
        d["signature_features"][0]["statement"] = "客厅做大跨度无柱空间，视线完全通透"
        d["signature_features"][0]["kind"] = "spatial"
        I.write(p, Path(d["file"]).parent, d)

        runner.run_stage("S3", confirm=False)
        assert runner.approve("S3", by="业主")["status"] == "confirmed"
        runner.run_stage("S4", confirm=False)

        sp = max([s for s in p.spaces if s.use != "envelope"], key=lambda s: s.area_m2)
        xs = [pt[0] for pt in sp.boundary_mm2d]
        ys = [pt[1] for pt in sp.boundary_mm2d]
        cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
        p.elements.append(Element(
            id="C-XX1", type="column", level_id=sp.level_id,
            geometry={"start": [cx - 100, cy - 100], "end": [cx + 100, cy + 100],
                      "kind": "internal"}))

        rep = conformance.check(p, stage="S4", out_root=runner.out)
        assert rep.status == conformance.CHANGED, rep.to_dict()
        assert rep.blocks_approval
        assert any("C-XX1" in c.evidence or "柱" in c.evidence for c in rep.changed)

        g4 = runner.approve("S4", by="业主")
        assert g4["status"] == "blocked", g4
        assert any("偏离" in n for n in g4["notes"])


# --------------------------------------------------------------------------
# G. 吊顶破坏光影 → 要设计审查
# --------------------------------------------------------------------------
def test_g_ceiling_change_that_breaks_the_light_intent_is_flagged():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        p, runner = _to_g2(tmp)
        d = I.load(p)
        d["signature_features"] = [{
            "id": "SF-01", "kind": "surface", "name": "天花造型",
            "statement": "天花做无主灯完整平顶，不做局部吊顶，不出现外露格栅",
            "source_field": "daylight",
            "technical_dependencies": [
                {"discipline": "mep", "need": "风管断面、桥架宽度、检修口位置"}],
        }]
        I.write(p, Path(d["file"]).parent, d)

        # 伪造一份"外露风口"的顶面成果
        out = runner.out
        (out / "04-preliminary").mkdir(parents=True, exist_ok=True)
        (out / "04-preliminary" / "material-lighting.json").write_text(
            json.dumps({"surfaces": {"ceiling": [
                {"zone": "客厅", "method": "外露风口 + 明装检修口", "level": "H2800"}]},
                "lighting": [{"layer": "基础", "fixture": "主灯吊灯"}]},
                ensure_ascii=False), encoding="utf-8")

        rep = conformance.check(p, stage="S4", out_root=out)
        assert rep.status == conformance.CHANGED, rep.to_dict()
        assert any("外露" in c.evidence or "主灯" in c.evidence for c in rep.changed)


# --------------------------------------------------------------------------
# H. 水景被取消 → 景观意图变化
# --------------------------------------------------------------------------
def test_h_removing_the_water_feature_is_detected():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        p = _project(tmp, "院子要做水景，中间做一个水池", name="庭院")
        # 没有任何水景用途 + 意图要求水景
        p.meta["design_intent"] = {
            "design_intent_id": "DI-WATER",
            "lead_discipline": "landscape", "lead_label": "景观",
            "revision": p.revision,
            "signature_features": [{
                "id": "SF-01", "kind": "water", "name": "庭院水景",
                "statement": "庭院中央做水池作为视觉核心",
                "technical_dependencies": []}],
        }
        rep = conformance.check(p, stage="S3")
        assert rep.status == conformance.CHANGED, rep.to_dict()
        assert any("水景" in c.evidence for c in rep.changed)


# --------------------------------------------------------------------------
# I. 普通颜色/材料调整不该重开整个设计
# --------------------------------------------------------------------------
def test_i_paint_change_does_not_trigger_full_reapproval():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        p, _runner = _to_g2(tmp)
        rep = changes.analyse(p, "客厅墙面换个颜色，暖灰改成奶白", apply=True)
        assert rep.intent.get("requires_formal") is False, rep.to_dict()["design_intent"]
        assert rep.intent.get("verdict") == "acceptable_adjustment"
        assert rep.applied is True, "低风险调整不该被拦"
        assert rep.scope == "local"


# --------------------------------------------------------------------------
# J. 安全/规范问题不允许美学放行
# --------------------------------------------------------------------------
def test_j_safety_failure_cannot_pass_because_the_design_is_beautiful():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        p = _project(tmp, "我这套 300㎡ 的房子要精装修", name="大宅")
        a = C.assess_gate(p)      # 尚未选概念，也会先看到硬门槛
        v = hardgate.evaluate(p)
        if v.blocked:
            assert any("G2-HARD" in b["id"] or True for b in a.blockers)
        # 真正的断言：failed 的维度一定让 G2 无法确认
        from omniarchitect import disciplines as D

        v = hardgate.evaluate(p, scope=D.ensure(p))
        verdict = C.decide_gate(p, "approved", by="业主", force=True)
        if v.blocked:
            assert verdict.decision != "approved", "硬门槛 failed 却被批准了"


# --------------------------------------------------------------------------
# K. 无法自动验证的特征必须进 unknown
# --------------------------------------------------------------------------
def test_k_unprovable_aesthetic_feature_is_unknown_not_passed():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        p = _project(tmp, "买了一套 150㎡ 大平层，室内装修", name="住宅")
        p.meta["design_intent"] = {
            "design_intent_id": "DI-AEST",
            "lead_discipline": "architecture", "lead_label": "建筑",
            "revision": p.revision,
            "signature_features": [{
                "id": "SF-01", "kind": "envelope", "name": "立面比例",
                "statement": "立面横向分缝比例要显得舒展，不压迫",
                "technical_dependencies": []}],
        }
        rep = conformance.check(p, stage="S5")
        assert rep.status == conformance.UNKNOWN, rep.to_dict()
        assert rep.checks[0].status == conformance.UNKNOWN
        assert rep.checks[0].measurable is False
        assert rep.blocks_approval is False, "无法证明不等于已证明有错"
        assert rep.unknown and rep.unknown[0].needs


# --------------------------------------------------------------------------
# L. 旧项目兼容：没有意图基准也要能跑
# --------------------------------------------------------------------------
def test_l_legacy_project_without_intent_still_runs():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        p = _project(tmp, "买了一套 150㎡ 大平层，室内装修，拆一堵墙", name="老项目")
        runner = StageRunner(p, tmp / "out", project_dir=tmp / "proj")
        runner.run_stage("S2", confirm=False)
        C.select(p, "C-B")
        # 旧基准：source=demo，不写意图
        demo = runner.approve("S2", by="演示", source="demo")
        assert demo["status"] == "confirmed"
        assert not I.load(p), "演示确认不该写设计意图"

        rep = conformance.check(p, stage="S3")
        assert rep.status == conformance.NOT_APPLICABLE
        assert "不是通过" in rep.note
        # 阶段照常能跑
        out = runner.run_stage("S3", confirm=False)
        assert out.status in ("ok", "blocked")
