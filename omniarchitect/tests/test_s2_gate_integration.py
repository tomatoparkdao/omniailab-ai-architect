"""S2 / G2 / S3 集成验收：把"能通过"和"不能通过"分成两条真实路径来测。

这一组测试全部是负向或半负向的：先证明**不该发生的事真的被挡住**，再证明
正常流程还能走通。只测"返回了一个 dict"没有意义——那正是上一轮的问题所在。

| 编号 | 场景 |
|---|---|
| A | authorize=True / submit=False：不提交 |
| B | 费用未知且指定上限：不得越权收费 |
| C | 重复运行：不得重复付费 |
| D | 无 concept_id + force：G2 拒绝 |
| E | 风格锁定失败：G2 不得宣布成功（并验证回滚后可恢复） |
| F | S2 方案与 S3 平面重大冲突：G3 拒绝 |
| G | 无有效 G2 基准：G3 不能正式签发 |
| H | 人工待核实条件不得被伪装成通过 |
| I | 正常 G2 → S3 → G3 全程走通 |
| J | 全量历史测试与九段审计（由 scripts 提供，不在本模块） |

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from omniarchitect import concept as C
from omniarchitect.concept import handoff as handoff_mod
from omniarchitect.concept import visual as vis
from omniarchitect.demo import build_demo_project
from omniarchitect.intake.gate import decide_gate as decide_g1
from omniarchitect.intake.interview import answer_question, start_interview
from omniarchitect.model import Project
from omniarchitect.stage_state import CONFIRMED, can_confirm, get_state
from omniarchitect.workflow import StageRunner


# --------------------------------------------------------------------------
# fixtures / stubs
# --------------------------------------------------------------------------
def _residential(tmp: Path, *, style: str = "现代意式极简") -> Project:
    p = build_demo_project(tmp / "proj")
    p.constraints = {**(p.constraints or {}), "style": style, "budget_cny": 1_600_000}
    p.save(tmp / "proj" / "project.json")
    start_interview(p, "150㎡ 大平层，一家三口，现代意式极简")
    answer_question(p, "res.household", "一家三口，有一个 5 岁孩子")
    answer_question(p, "res.daily_rhythm", "晚上陪孩子写作业，周末在家做饭")
    answer_question(p, "base.needs",
                    "客厅要能坐下 8 个人吃饭；孩子写作业要看得见；东西很多需要收纳")
    decide_g1(p, "approved", by="业主")
    return p


def _runner(p: Project, root: Path, **kw: Any) -> StageRunner:
    return StageRunner(p, root / "out", project_dir=root / "proj", **kw)


class _StubProvider:
    """Records every provider call so "did we pay twice" is answerable."""

    id = "omniailab"
    kind = "own-builtin"

    def __init__(self, cost: Optional[float] = 0.5) -> None:
        self.calls = 0
        self.cost = cost

    def probe(self):
        from omniarchitect.providers.base import ProviderCapability

        return ProviderCapability(provider="omniailab", state="connected",
                                  provider_kind="own-builtin",
                                  scopes=["image_generation", "video_generation"],
                                  models=["stub-model"])

    def estimate_cost(self, operation: str, params: Dict[str, Any]):
        return self.cost

    def run(self, operation, params, target_dir, timeout_s=30.0, **_kw):
        from omniarchitect.providers.base import ProviderJob

        self.calls += 1
        out = Path(target_dir) / f"stub-{self.calls}.png"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 2048)
        return ProviderJob(job_id=f"stub-{self.calls}", provider="omniailab",
                           operation=operation, status="succeeded",
                           outputs=[str(out)], cost_estimate=self.cost)


class _StubRegistry:
    def __init__(self, provider: _StubProvider) -> None:
        self.provider = provider
        self.linked: List[str] = []

    def capabilities(self):
        return [self.provider.probe()]

    def get(self, pid: str):
        return self.provider if pid == "omniailab" else None

    def generate(self, scope, params, target_dir, prefer=""):
        return self.provider.run(scope, params, target_dir)

    def link_asset(self, job, assets, project_id, revision, stage, scope):
        self.linked.extend(assets)
        return []

    def defer_creative_task(self, scope, params, reason):
        return {"status": "awaiting_platform"}


class _patched:
    """`scripts/run_tests.py` calls tests without fixtures, so patch by hand."""

    def __init__(self, target: Any, name: str, value: Any) -> None:
        self.target, self.name, self.value, self.orig = target, name, value, None

    def __enter__(self):
        self.orig = getattr(self.target, self.name)
        setattr(self.target, self.name, self.value)
        return self

    def __exit__(self, *exc):
        setattr(self.target, self.name, self.orig)
        return False


def _patched_discover(reg: _StubRegistry) -> _patched:
    import omniarchitect.providers as providers

    return _patched(providers, "discover", lambda *a, **k: reg)


def _jobs(p: Project) -> List[Dict[str, Any]]:
    ctx = C.build_context(p)
    concept = C.generate_concepts(ctx, limit=2)["concepts"][0]
    return vis.build_jobs(concept, ctx, p)


# --------------------------------------------------------------------------
# A. authorize 单独打开不构成提交
# --------------------------------------------------------------------------
def test_a_authorize_alone_never_submits():
    with tempfile.TemporaryDirectory() as td:
        p = _residential(Path(td))
        jobs = _jobs(p)
        stub = _StubProvider()
        with _patched_discover(_StubRegistry(stub)):
            res = vis.submit(jobs, p, Path(td) / "out", submit=False, authorize=True)
        assert res.submitted == 0 and stub.calls == 0, "只给 authorize 就提交了"
        assert res.generated == 0
        assert res.deferred == len(jobs)
        assert all("--submit" in (j.get("reason") or "") for j in res.jobs), \
            [j.get("reason") for j in res.jobs]

        # 反过来：submit 单独打开同样不提交
        stub2 = _StubProvider()
        with _patched_discover(_StubRegistry(stub2)):
            res = vis.submit(jobs, p, Path(td) / "out", submit=True, authorize=False)
        assert res.submitted == 0 and stub2.calls == 0
        assert all("--authorize" in (j.get("reason") or "") for j in res.jobs)


# --------------------------------------------------------------------------
# B. 费用未知：不得越权收费
# --------------------------------------------------------------------------
def test_b_unknown_cost_is_held_even_with_a_cap():
    with tempfile.TemporaryDirectory() as td:
        p = _residential(Path(td))
        jobs = _jobs(p)
        stub = _StubProvider(cost=None)          # 契约里没有计价
        with _patched_discover(_StubRegistry(stub)):
            res = vis.submit(jobs, p, Path(td) / "out", submit=True, authorize=True,
                             max_cost=10.0)
        assert stub.calls == 0, "费用未知却提交了"
        assert res.submitted == 0 and res.generated == 0
        assert res.cost_known is False
        assert res.cost_controlled is False, "费用未知不得声称受控"
        assert res.held == len(jobs)
        assert all(j["status"] == "awaiting_cost_confirmation" for j in res.jobs)
        assert any("无法证明" in w or "无法保证" in w for w in res.warnings), res.warnings

        # 连上限都不给，更不能称为"受控"
        stub2 = _StubProvider(cost=None)
        with _patched_discover(_StubRegistry(stub2)):
            res2 = vis.submit(jobs, p, Path(td) / "out2", submit=True, authorize=True)
        assert stub2.calls == 0 and res2.cost_controlled is False


# --------------------------------------------------------------------------
# C. 重复运行不重复付费
# --------------------------------------------------------------------------
def test_c_rerunning_never_pays_twice():
    with tempfile.TemporaryDirectory() as td:
        p = _residential(Path(td))
        jobs = _jobs(p)
        stub = _StubProvider()
        out = Path(td) / "out"
        with _patched_discover(_StubRegistry(stub)):
            first = vis.submit(jobs, p, out, submit=True, authorize=True, max_cost=100)
            assert first.submitted == len(jobs) and stub.calls == len(jobs)

            again = _jobs(p)                     # 重新编译同一批任务
            second = vis.submit(again, p, out, submit=True, authorize=True, max_cost=100)

        assert stub.calls == len(jobs), f"重跑又付费了：{stub.calls} 次调用"
        assert second.submitted == 0
        assert second.reused == len(jobs)
        assert second.generated == len(jobs)
        assert all(j.get("reused") for j in second.jobs)
        for job in second.jobs:
            assert Path(job["output"]).exists(), "复用的产物必须真实存在"

        ledger = vis.load_ledger(out / vis.LEDGER_NAME)
        assert len(ledger["entries"]) == len(jobs)


def test_c2_regenerating_the_whole_bundle_does_not_pay_again():
    """`generate` 是最容易被反复执行的动作，它自己必须幂等。"""
    with tempfile.TemporaryDirectory() as td:
        p = _residential(Path(td))
        stub = _StubProvider()
        out = Path(td) / "out"
        with _patched_discover(_StubRegistry(stub)):
            first = C.generate_bundle(p, out, with_deck=False, submit=True,
                                      authorize=True, max_cost=100)
            calls = stub.calls
            assert calls > 0 and first["visual"]["submitted"] == calls

            second = C.generate_bundle(p, out, with_deck=False, submit=True,
                                       authorize=True, max_cost=100)

        assert stub.calls == calls, f"重跑 generate 又付费了：{stub.calls} vs {calls}"
        assert second["visual"]["submitted"] == 0
        assert second["visual"]["reused"] == calls


# --------------------------------------------------------------------------
# D. 没有 concept_id：force 也不行
# --------------------------------------------------------------------------
def test_d_g2_needs_a_concept_id_even_with_force():
    with tempfile.TemporaryDirectory() as td:
        p = _residential(Path(td))
        C.generate_bundle(p, Path(td) / "out", with_deck=False)

        out = C.decide_gate(p, "approved", by="业主", force=True)
        assert out.decision == "blocked", out.notes
        assert out.formal is False
        assert get_state(p, "S2").status != CONFIRMED
        assert any("G2-NO-SELECTION" in n for n in out.notes), out.notes
        assert any("force" in n.lower() for n in out.notes), out.notes

        # 一个概念都没有时同样拒绝（连演示都不该说"通过"）
        empty = _residential(Path(td) / "empty")
        empty.meta["concept"] = {}
        out2 = C.decide_gate(empty, "approved", by="业主", force=True)
        assert out2.decision == "blocked"
        assert any("G2-NO-CONCEPT" in n for n in out2.notes)


def test_d2_old_entries_and_demo_mode_cannot_impersonate_a_signature():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        p = _residential(tmp)
        runner = _runner(p, tmp)
        runner.run_stage("S2", confirm=False)

        # 旧入口 confirm() 走同一套判定：没选定概念就不能过
        st = runner.confirm("S2", by="业主")
        assert st["status"] != CONFIRMED, "旧入口绕过了 G2"
        assert C.check_baseline(p)["has_baseline"] is False

        # --assume-approval 只让流程继续，不写基准、不称签署
        demo = _runner(p, tmp, assume_approval=True)
        out = demo.run_stage("S2", confirm=True)
        assert out.status == "ok"
        assert get_state(p, "S2").status == CONFIRMED
        assert C.check_baseline(p)["has_baseline"] is False, "演示模式写了概念基准"
        decision = (p.meta["concept"].get("last_decision") or {})
        assert decision.get("formal") is False
        assert (p.meta["concept"].get("demo_approval") or {}).get("formal") is False


# --------------------------------------------------------------------------
# E. 风格锁定失败 → 不得宣布成功
# --------------------------------------------------------------------------
def test_e_style_lock_failure_rolls_back_and_is_recoverable():
    import omniarchitect.style.hooks as hooks

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        p = _residential(tmp)
        runner = _runner(p, tmp)
        runner.run_stage("S2", confirm=False)
        C.select(p, "C-B")
        out_dir = runner.out / "02-concept"

        def _boom(*a, **k):
            raise OSError("磁盘只读（模拟锁定写入失败）")

        with _patched(hooks, "lock_style", _boom):
            res = runner.approve("S2", by="业主")
        assert res["status"] != CONFIRMED, "锁定失败却确认成功了"
        assert res.get("formal") is False
        assert res.get("rolled_back") is True
        assert C.check_baseline(p)["has_baseline"] is False, "回滚后不得留下基准"
        assert not (p.meta.get("concept") or {}).get("style_lock")
        assert not list(out_dir.glob("style-lock-r*.json")), "不应留下锁定文件"

        # 恢复后重试必须能走通（回滚不是把项目弄坏）
        ok = runner.approve("S2", by="业主")
        assert ok["status"] == CONFIRMED, ok.get("notes")
        assert ok.get("formal") is True
        assert C.check_baseline(p)["has_baseline"] is True
        lock_file = Path(str((p.meta["concept"].get("style_lock") or {}).get("file") or ""))
        assert lock_file.is_file(), "确认了却没有锁定文件"


def test_e2_style_lock_conflict_needs_explicit_acceptance():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        p = _residential(tmp)
        runner = _runner(p, tmp)
        runner.run_stage("S2", confirm=False)
        C.select(p, "C-B")

        # 模拟"上一轮已经锁了另一个风格"
        out_dir = runner.out / "02-concept"
        out_dir.mkdir(parents=True, exist_ok=True)
        fake = out_dir / f"style-lock-r{p.revision}.json"
        fake.write_text(json.dumps({"locked_style": "wabi-sabi",
                                    "revision": p.revision}, ensure_ascii=False),
                        encoding="utf-8")
        p.meta["concept"]["style_lock"] = {
            "style_ids": ["wabi-sabi"], "primary": "wabi-sabi",
            "revision": p.revision, "file": str(fake),
        }

        assess = C.assess_gate(p)
        assert "G2-STYLE-LOCK-CONFLICT" in assess.acknowledgeable_ids
        blocked = runner.approve("S2", by="业主")
        assert blocked["status"] != CONFIRMED
        assert any("G2-STYLE-LOCK-CONFLICT" in n for n in blocked["notes"])

        # 用一段"看着像"的文字消阻断 → 直接报错，不能当成已接受
        try:
            C.decide_gate(p, "approved", by="业主",
                          acknowledge=["风格锁定不一致"])
        except ValueError as exc:
            assert "未知风险编号" in str(exc)
        else:
            raise AssertionError("随意文本被当作风险编号接受了")

        ok = C.decide_gate(p, "approved", by="业主",
                           acknowledge=["G2-STYLE-LOCK-CONFLICT"],
                           summary_path=str(out_dir / "g2-approval-summary.md"))
        assert ok.decision == "approved", ok.notes
        payload = json.loads(fake.read_text(encoding="utf-8"))
        chosen = (p.meta["concept"]["options"]["concepts"][1]["style_ids"][0])
        assert payload["locked_style"] == chosen, "锁定文件未按选定概念重写"
        history = p.meta["concept"].get("style_lock_history") or []
        assert history and history[-1]["superseded"] == ["wabi-sabi"]

        # 同一概念再确认一次：只有一个文件、不再增加历史
        again = C.decide_gate(p, "approved", by="业主",
                              summary_path=str(out_dir / "g2-approval-summary.md"))
        assert again.decision == "approved"
        assert len(list(out_dir.glob("style-lock-r*.json"))) == 1
        assert len(p.meta["concept"].get("style_lock_history") or []) == len(history)


# --------------------------------------------------------------------------
# F. 概念与平面重大冲突 → G3 拒绝
# --------------------------------------------------------------------------
def test_f_concept_conflict_blocks_g3():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        p = _residential(tmp)
        runner = _runner(p, tmp)
        runner.run_stage("S2", confirm=False)

        options = json.loads((runner.out / "02-concept" / "concept-options.json")
                            .read_text(encoding="utf-8"))
        unsupported = [c for c in options["concepts"]
                       if not (c.get("spatial_prototype") or {}).get("plan_strategy")]
        assert unsupported, "这批方向里应当存在'现有算法不支持'的原型"

        cid = unsupported[0]["concept_id"]
        C.select(p, cid)
        g2 = runner.approve("S2", by="业主")
        assert g2["status"] == CONFIRMED, g2.get("notes")

        s3 = runner.run_stage("S3", confirm=False)
        assert s3.status == "ok"
        assert any("不能视为概念的落地" in n or "不得正式签发" in n for n in s3.notes), s3.notes

        rec = handoff_mod.plan_record(p)
        assert rec["conformance"] == "fail", rec
        assert rec["implements_concept"] is False
        assert any(c["id"] == "H-STRATEGY-UNSUPPORTED" for c in rec["conflicts"])

        g3 = runner.approve("S3", by="业主")
        assert g3["status"] != CONFIRMED, "概念冲突却签发了 G3"
        assert g3.get("formal") is False
        ids = " ".join(g3["notes"])
        assert "G3-CONCEPT-CONFLICT" in ids and "G3-PROTOTYPE-UNSUPPORTED" in ids


# --------------------------------------------------------------------------
# G. 没有有效 G2 基准 → 不能正式签发 G3（但允许探索）
# --------------------------------------------------------------------------
def test_g_no_baseline_blocks_formal_g3_but_allows_exploration():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        p = _residential(tmp)
        runner = _runner(p, tmp)
        runner.run_stage("S2", confirm=False)          # 生成但不确认、不选定
        s3 = runner.run_stage("S3", confirm=False)     # 探索性平面：允许
        assert s3.status == "ok", s3.error

        ok, blockers = can_confirm(p, "S3")
        assert ok is False
        assert any(b["id"] == "G3-NO-CONCEPT-BASELINE" for b in blockers)

        g3 = runner.approve("S3", by="业主", force=True)
        assert g3["status"] != CONFIRMED, "无概念基准却签发了正式 G3"
        assert g3.get("formal") is False
        assert any("G3-NO-CONCEPT-BASELINE" in n for n in g3["notes"])
        assert any("force" in n.lower() for n in g3["notes"])

        # 演示通道仍然可用，但绝不声称正式签发
        demo = runner.approve("S3", source="demo")
        assert demo["status"] == CONFIRMED
        assert demo.get("formal") is False
        assert any("不是正式 G3 签发" in n for n in demo["notes"])
        gate_rec = (p.meta["concept"].get("plan") or {}).get("gate") or {}
        assert gate_rec.get("formal") is False


def test_g2_stale_baseline_blocks_formal_g3():
    """概念基准在平面生成之后被改动 → 这份平面不再对应已签的概念。"""
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        p = _residential(tmp)
        runner = _runner(p, tmp)
        runner.run_stage("S2", confirm=False)
        C.select(p, "C-B")
        assert runner.approve("S2", by="业主")["status"] == CONFIRMED
        runner.run_stage("S3", confirm=False)

        # 业主改主意：需求变了 → 任务书基准失效 → 概念基准随之失效
        answer_question(p, "base.needs", "改主意了：客厅不需要坐 8 个人，改成一个阅读角")

        assess = handoff_mod.assess_plan_gate(p)
        assert assess["formal_ready"] is False
        assert assess["stale"] is True
        ids = {b["id"] for b in assess["blockers"]}
        assert "G3-STALE-BASELINE" in ids, assess["blockers"]

        g3 = runner.approve("S3", by="业主")
        assert g3["status"] != CONFIRMED
        assert any("G3-STALE-BASELINE" in n for n in g3["notes"])


# --------------------------------------------------------------------------
# H. 待人工复核不得被算作"通过"
# --------------------------------------------------------------------------
def test_h_manual_review_is_never_counted_as_passed():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        p = _residential(tmp)
        runner = _runner(p, tmp)
        runner.run_stage("S2", confirm=False)
        C.select(p, "C-B")
        assert runner.approve("S2", by="业主")["status"] == CONFIRMED

        handoff = handoff_mod.load_for(p)
        assert handoff.get("separation"), "本夹具应带有隔离类要求"

        class _Scheme:
            strategy = "band_day_night"
            metrics = {"corridor_ratio": 0.11, "room_count": 8,
                       "daylight_rooms_served": "8/8"}

            def area_table(self):
                return [{"name": "主卧"}, {"name": "客厅"}, {"name": "厨房"},
                        {"name": "玄关"}]

        v = handoff_mod.verify_scheme(handoff, _Scheme(), p)
        assert v["conformance"] == "pass"
        assert v["manual_review_required"] > 0
        assert v["fully_verified"] is False, "待人工复核却被当成完全核实"

        runner.run_stage("S3", confirm=False)
        rec = handoff_mod.plan_record(p)
        assert rec["manual_review"], rec
        assert rec["fully_verified"] is False

        g3 = runner.approve("S3", by="业主")
        assert g3["status"] == CONFIRMED
        assert g3["assessment"]["fully_verified"] is False
        assert any("未计入通过" in n or "待人工复核" in n for n in g3["notes"]), g3["notes"]
        assert (p.meta["concept"]["plan"]["gate"] or {}).get("fully_verified") is False


# --------------------------------------------------------------------------
# I. 正常路径：G2 → S3 → G3 一次走通
# --------------------------------------------------------------------------
def test_i_normal_path_g2_s3_g3():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        p = _residential(tmp)
        runner = _runner(p, tmp)
        runner.run_stage("S2", confirm=False)

        supported = [c for c in (p.meta["concept"]["options"]["concepts"])
                     if (c.get("spatial_prototype") or {}).get("plan_strategy")]
        assert supported
        cid = supported[0]["concept_id"]
        C.select(p, cid)

        g2 = runner.approve("S2", by="业主张先生")
        assert g2["status"] == CONFIRMED, g2.get("notes")
        assert g2.get("formal") is True

        base = C.check_baseline(p)
        assert base["has_baseline"] and base["concept_id"] == cid
        lock = p.meta["concept"].get("style_lock") or {}
        assert lock and Path(str(lock["file"])).is_file()
        handoff = handoff_mod.load_for(p)
        assert handoff["status"] == "locked"
        assert handoff["gate"]["confirmed"] is True

        s3 = runner.run_stage("S3", confirm=False)
        assert s3.status == "ok", s3.error
        rec = handoff_mod.plan_record(p)
        assert rec["conformance"] != "fail", rec
        assert rec["implements_concept"] is True

        g3 = runner.approve("S3", by="业主张先生")
        assert g3["status"] == CONFIRMED, g3.get("notes")
        assert g3.get("formal") is True
        assert (p.meta["concept"]["plan"]["gate"] or {}).get("formal") is True
        assert (runner.out / "02-concept" / "concept-handoff.json").exists()

        # 交付物与状态一致：确认后不得出现"确认了但没有锁定/没有交接"
        assert Path(str((p.meta["concept"].get("style_lock") or {})["file"])).exists()
