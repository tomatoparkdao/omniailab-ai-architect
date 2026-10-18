"""S2 概念设计引擎的验收测试（对应任务书场景 A–L）。

原则：测"能不能被反驳"，而不是测"有没有返回一个字典"。
所以每个场景都去检查**具体内容**——空间家族是否真的不同、有没有住宅词漏到
办公项目、色值是否真的采自风格库、未配置平台时有没有假装生成。

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import json
import pathlib
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List

from omniarchitect import concept as C
from omniarchitect.concept import handoff as handoff_mod
from omniarchitect.demo import build_demo_project
from omniarchitect.intake.gate import decide_gate as decide_g1
from omniarchitect.intake.interview import answer_question, start_interview
from omniarchitect.model import Project
from omniarchitect.stage_state import CONFIRMED, get_state

from omniarchitect.concept import visual as vis

SVG_NS = "{http://www.w3.org/2000/svg}"


# --------------------------------------------------------------------------
# fixtures
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


def _office(tmp: Path) -> Project:
    p = Project(project_id="office-800", name="800㎡ 办公空间")
    p.program = [
        {"name": "开放办公区", "recipe": "open_office", "area_m2": 320, "zone": "day"},
        {"name": "会议室A", "recipe": "meeting", "area_m2": 45, "zone": "day"},
        {"name": "专注间", "recipe": "focus", "area_m2": 40, "zone": "night"},
        {"name": "接待前厅", "recipe": "reception", "area_m2": 60, "zone": "day"},
        {"name": "打印与储物", "recipe": "storage", "area_m2": 25, "zone": "service"},
    ]
    p.constraints = {"budget_cny": 3_200_000}
    start_interview(p, "800㎡ 办公空间，60 人，设计团队")
    answer_question(p, "off.headcount", "60 人，两年内可能到 85 人")
    answer_question(p, "off.meeting", "每天 3-5 场，客户来访多，需要正式接待")
    answer_question(p, "off.visitor", "访客不少，但不需要进到工位区")
    answer_question(p, "base.needs", "专注工作要安静；客户来了要有体面的前场；打印区不要吵到工位")
    decide_g1(p, "approved", by="业主")
    return p


def _hospitality(tmp: Path) -> Project:
    p = Project(project_id="hotel-30", name="30 间客房民宿")
    p.program = [
        {"name": "大堂", "recipe": "lobby", "area_m2": 120, "zone": "day"},
        {"name": "客房层", "recipe": "guestroom", "area_m2": 900, "zone": "night"},
        {"name": "餐厅", "recipe": "restaurant", "area_m2": 180, "zone": "day"},
        {"name": "后勤区", "recipe": "service", "area_m2": 90, "zone": "service"},
    ]
    start_interview(p, "30 间客房的度假民宿，做精品路线")
    answer_question(p, "hos.positioning", "客群以情侣与家庭度假为主，客单价中高")
    answer_question(p, "hos.back_of_house", "布草与垃圾需要独立后场通道，不能被客人看到")
    answer_question(p, "base.needs", "客人到店要有仪式感；后勤不要被看到；房间要安静")
    decide_g1(p, "approved", by="业主")
    return p


def _no_geometry(tmp: Path) -> Project:
    p = Project(project_id="diag-150", name="150㎡ 大平层")
    p.constraints = {"style": "现代意式极简"}
    start_interview(p, "150㎡ 大平层，一家三口，现代意式极简")
    answer_question(p, "base.needs", "客厅要能坐 8 个人；孩子写作业要看得见")
    decide_g1(p, "approved", by="业主")
    return p


# --------------------------------------------------------------------------
# A. 住宅：三套方向必须有实质差异
# --------------------------------------------------------------------------
def test_a_residential_directions_differ_spatially():
    with tempfile.TemporaryDirectory() as td:
        p = _residential(Path(td))
        res = C.generate_bundle(p, Path(td) / "out", with_deck=False)
        assert res["count"] >= 2
        opts = json.loads((Path(td) / "out" / "concept-options.json").read_text(encoding="utf-8"))
        protos = [c["spatial_prototype"]["prototype_id"] for c in opts["concepts"]]
        families = [c["spatial_prototype"]["family"] for c in opts["concepts"]]
        assert len(set(protos)) == len(protos), "同一原型被用了两次"
        assert len(set(families)) >= 2, f"三套方向的空间家族没有差别：{families}"
        # 每套都要有证据与机会引用（或明确说明依据来自需求矩阵）
        for c in opts["concepts"]:
            assert c["evidence"], c["concept_id"]
            assert c["design_problem"], c["concept_id"]
            assert c["concept_statement"] != opts["concepts"][0]["concept_statement"] or \
                c["concept_id"] == opts["concepts"][0]["concept_id"]
        # 不能只换颜色：材料方向可以相同（同一风格），空间策略必须不同
        logics = {c["spatial_prototype"]["spatial_logic"] for c in opts["concepts"]}
        assert len(logics) == len(opts["concepts"])


# --------------------------------------------------------------------------
# B. 办公：不得出现住宅话术
# --------------------------------------------------------------------------
def test_b_office_has_no_residential_vocabulary():
    with tempfile.TemporaryDirectory() as td:
        p = _office(Path(td))
        C.generate_bundle(p, Path(td) / "out", with_deck=False)
        blob = (Path(td) / "out" / "concept-options.md").read_text(encoding="utf-8")
        for word in ("客厅", "主卧", "儿童房", "玄关", "卧室", "厨房"):
            assert word not in blob, f"办公项目里出现了住宅词：{word}"
        opts = json.loads((Path(td) / "out" / "concept-options.json").read_text(encoding="utf-8"))
        assert opts["profile_id"] == "office"
        text = json.dumps(opts, ensure_ascii=False)
        assert any(w in text for w in ("专注", "协作", "组团", "前厅", "访客")), text[:200]


# --------------------------------------------------------------------------
# C. 酒店/商业：概念要体现运营与客群
# --------------------------------------------------------------------------
def test_c_hospitality_concepts_address_operations():
    with tempfile.TemporaryDirectory() as td:
        p = _hospitality(Path(td))
        opts = json.loads(
            (C.generate_bundle(p, Path(td) / "out", with_deck=False)
             and (Path(td) / "out" / "concept-options.json").read_text(encoding="utf-8")))
        assert opts["profile_id"] == "hospitality"
        text = json.dumps(opts, ensure_ascii=False)
        assert any(w in text for w in ("到达", "后勤", "客群", "院落", "序列")), text[:300]
        for word in ("儿童房", "主卧"):
            assert word not in text


# --------------------------------------------------------------------------
# D. 指定风格：保留，不被评分更高的替换
# --------------------------------------------------------------------------
def test_d_client_style_is_respected():
    with tempfile.TemporaryDirectory() as td:
        p = _residential(Path(td), style="现代意式极简")
        opts = json.loads(
            (C.generate_bundle(p, Path(td) / "out", with_deck=False)
             and (Path(td) / "out" / "concept-options.json").read_text(encoding="utf-8")))
        assert opts["preferred_style_resolved"] == "italian-minimal"
        for c in opts["concepts"]:
            assert c["style_ids"][0] == "italian-minimal", c["concept_id"]
            assert "不替换" in c["style_basis"] or "锁定" in c["style_basis"]
        # 差异要来自空间策略，而不是换风格
        assert len({c["spatial_prototype"]["family"] for c in opts["concepts"]}) >= 2


# --------------------------------------------------------------------------
# E. 无图纸：可出方向，不可声称按尺寸成立
# --------------------------------------------------------------------------
def test_e_diagnostic_project_cannot_claim_dimensions():
    with tempfile.TemporaryDirectory() as td:
        p = _no_geometry(Path(td))
        res = C.generate_bundle(p, Path(td) / "out", with_deck=False)
        assert res["precision"] == "diagnostic"
        ctx = res["context"]
        assert ctx["can_claim_dimensions"] is False
        assert res["count"] >= 2
        blob = (Path(td) / "out" / "concept-options.md").read_text(encoding="utf-8")
        assert "不按比例" in blob or "非按比例" in blob
        assert "不得声称概念已通过精确尺寸可行性校核" in " ".join(res["warnings"]) or \
            "无几何" in " ".join(res["warnings"])


# --------------------------------------------------------------------------
# F. Moodboard：真的有色板，不是 Markdown 标题
# --------------------------------------------------------------------------
def test_f_moodboard_svg_carries_real_colours():
    with tempfile.TemporaryDirectory() as td:
        p = _residential(Path(td))
        C.generate_bundle(p, Path(td) / "out", with_deck=False)
        boards = sorted((Path(td) / "out" / "moodboards").glob("mb-*.svg"))
        assert boards, "没有生成任何意向板"
        root = ET.parse(boards[0]).getroot()
        rects = [e for e in root.iter(f"{SVG_NS}rect")
                 if (e.get("fill") or "").startswith("#") and e.get("fill") != "#FFFFFF"]
        fills = {e.get("fill") for e in rects}
        # 风格库里的真实色值必须出现在图上
        style = json.loads((Path("knowledge/styles/italian-minimal.json")
                            .read_text(encoding="utf-8")))
        declared = {c["hex"].upper() for c in style["color_palette"]}
        assert declared & fills, f"色板未使用风格库色值：{sorted(fills)[:6]}"
        md = boards[0].with_suffix(".md").read_text(encoding="utf-8")
        assert "| 颜色 | 色值 | 占比 |" in md
        assert any(m.get("name_zh") and m["name_zh"] in md
                   for m in style["materials"]), "材料名未出现在意向板"


# --------------------------------------------------------------------------
# G. 平台未配置：任务包完整，但不假装生成
# --------------------------------------------------------------------------
def test_g_unconfigured_platform_defers_every_job():
    with tempfile.TemporaryDirectory() as td:
        p = _residential(Path(td))
        res = C.generate_bundle(p, Path(td) / "out", with_deck=False)
        visual = res["visual"]
        assert visual["generated"] == 0
        assert visual["deferred"] == visual["job_count"] > 0
        jobs = json.loads((Path(td) / "out" / "concept-visual-jobs.json")
                          .read_text(encoding="utf-8"))
        assert jobs["third_party_fallback"] == "forbidden"
        assert jobs["non_authoritative"] is True
        for job in jobs["jobs"]:
            assert job["status"] == "awaiting_platform"
            assert "生成" not in job.get("output", "")
        assert not list((Path(td) / "out" / "concept-visuals").glob("*.[pjJ][npN][gG]*"))


# --------------------------------------------------------------------------
# H. 模拟平台：提交 → 取回 → 校验 → 登记（不打真实网络）
# --------------------------------------------------------------------------
class _StubProvider:
    """Produces a real file so the fetch/size/type checks are actually exercised."""

    id = "omniailab"
    kind = "own-builtin"

    def __init__(self) -> None:
        self.calls = 0

    def probe(self):
        from omniarchitect.providers.base import ProviderCapability

        return ProviderCapability(provider="omniailab", state="connected",
                                  provider_kind="own-builtin",
                                  scopes=["image_generation", "video_generation"],
                                  models=["stub-model"])

    def estimate_cost(self, operation: str, params: Dict[str, Any]):
        return 0.5

    def run(self, operation, params, target_dir, timeout_s=30.0, **_kw):
        from omniarchitect.providers.base import ProviderJob

        self.calls += 1
        out = Path(target_dir) / f"stub-{self.calls}.png"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 2048)
        return ProviderJob(job_id=f"stub-{self.calls}", provider="omniailab",
                           operation=operation, status="succeeded",
                           outputs=[str(out)], cost_estimate=0.5)


class _StubRegistry:
    def __init__(self, provider: _StubProvider, *, usable: bool = True) -> None:
        self.provider = provider
        self.usable = usable
        self.linked: List[str] = []

    def capabilities(self):
        cap = self.provider.probe()
        if not self.usable:
            cap.state = "not_configured"
            cap.missing = ["api_key"]
        return [cap]

    def get(self, pid: str):
        return self.provider if pid == "omniailab" else None

    def generate(self, scope, params, target_dir, prefer=""):
        return self.provider.run(scope, params, target_dir)

    def link_asset(self, job, assets, project_id, revision, stage, scope):
        self.linked.extend(assets)
        return []

    def defer_creative_task(self, scope, params, reason):
        return {"status": "awaiting_platform"}


class _patched_discover:
    """Patch `providers.discover` for the duration of a test.

    `scripts/run_tests.py` calls test functions with no arguments, so pytest
    fixtures (including `monkeypatch`) are not available here.
    """

    def __init__(self, registry: Any) -> None:
        self.registry = registry
        self._orig = None

    def __enter__(self):
        import omniarchitect.providers as providers

        self._orig = providers.discover
        providers.discover = lambda *a, **k: self.registry
        return self.registry

    def __exit__(self, *exc):
        import omniarchitect.providers as providers

        providers.discover = self._orig
        return False


def _one_concept(p: Project) -> Dict[str, Any]:
    ctx = C.build_context(p)
    return C.generate_concepts(ctx, limit=2)["concepts"][0]


def test_h_platform_submission_round_trip():
    with tempfile.TemporaryDirectory() as td:
        p = _residential(Path(td))
        concept = _one_concept(p)
        jobs = vis.build_jobs(concept, C.build_context(p), p)

        stub = _StubProvider()
        reg = _StubRegistry(stub)
        ctx = _patched_discover(reg)
        ctx.__enter__()
        try:
            res = vis.submit(jobs, p, Path(td) / "out", submit=False, authorize=False)
            assert res.generated == 0 and res.deferred == len(jobs), "未授权不得提交"
            # 只打开 authorize 也不构成提交请求：两个开关必须同时成立
            res = vis.submit(jobs, p, Path(td) / "out", submit=False, authorize=True)
            assert res.submitted == 0 and stub.calls == 0, "只给 authorize 就提交了"

            res = vis.submit(jobs, p, Path(td) / "out", submit=True, authorize=True)
            assert res.submitted == len(jobs)
            assert res.generated == len(jobs), [j.get("reason") for j in res.jobs]
            for job in res.jobs:
                assert job["status"] == "generated"
                assert Path(job["output"]).exists()
                assert Path(job["output"]).stat().st_size > 1024
            assert reg.linked, "生成后必须把资产登记到项目"
            assert res.cost_estimate and res.cost_estimate > 0
        finally:
            ctx.__exit__()


def test_h_cost_cap_stops_submission():
    with tempfile.TemporaryDirectory() as td:
        p = _residential(Path(td))
        jobs = vis.build_jobs(_one_concept(p), C.build_context(p), p)
        with _patched_discover(_StubRegistry(_StubProvider())):
            res = vis.submit(jobs, p, Path(td) / "out", submit=True, authorize=True,
                             max_cost=0.4)
        assert res.generated == 0
        assert all("超过上限" in (j.get("reason") or "") for j in res.jobs)


def test_h_non_image_payload_is_rejected():
    from omniarchitect.providers.base import ProviderJob

    class _BadStub(_StubProvider):
        def run(self, operation, params, target_dir, timeout_s=30.0, **_kw):
            out = Path(target_dir) / "broken.bin"
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(b"not an image" * 200)
            return ProviderJob(job_id="bad", provider="omniailab",
                               operation=operation, status="succeeded",
                               outputs=[str(out)])

    with tempfile.TemporaryDirectory() as td:
        p = _residential(Path(td))
        jobs = vis.build_jobs(_one_concept(p), C.build_context(p), p)
        with _patched_discover(_StubRegistry(_BadStub())):
            res = vis.submit(jobs, p, Path(td) / "out", submit=True, authorize=True)
        assert res.generated == 0
        assert res.failed == len(jobs)


# --------------------------------------------------------------------------
# I. G2：未选不定，确认后形成基准与风格锁定
# --------------------------------------------------------------------------
def test_i_g2_requires_a_concept_and_writes_baseline():
    with tempfile.TemporaryDirectory() as td:
        p = _residential(Path(td))
        C.generate_bundle(p, Path(td) / "out", with_deck=False)
        assess = C.assess_gate(p)
        assert assess.can_approve is False
        assert any("尚未选定" in r for r in assess.blocked_reasons)

        blocked = C.decide_gate(p, "approved", by="业主")
        assert blocked.decision == "blocked"
        assert get_state(p, "S2").status != CONFIRMED

        C.select(p, "C-B")
        ok = C.decide_gate(p, "approved", by="业主张先生",
                           summary_path=str(Path(td) / "out" / "g2-approval-summary.md"))
        assert ok.decision == "approved", ok.notes
        assert get_state(p, "S2").status == CONFIRMED
        base = C.check_baseline(p)
        assert base["has_baseline"] and base["concept_id"] == "C-B"
        lock = C.lock_style_for(p, Path(td) / "out")
        assert lock["style_ids"] and lock["revision"] == p.revision
        assert (Path(td) / "out" / f"style-lock-r{p.revision}.json").exists()


def test_i_demo_approval_never_writes_a_baseline():
    with tempfile.TemporaryDirectory() as td:
        p = _residential(Path(td))
        C.generate_bundle(p, Path(td) / "out", with_deck=False)
        C.select(p, "C-A")
        out = C.decide_gate(p, "approved", source="demo", note="演示")
        assert out.decision == "approved"
        assert C.check_baseline(p)["has_baseline"] is False
        assert (p.meta.get("concept") or {}).get("demo_approval")


# --------------------------------------------------------------------------
# J. S3 承接：能读，也能报冲突
# --------------------------------------------------------------------------
def test_j_s3_reads_handoff_and_detects_conflicts():
    with tempfile.TemporaryDirectory() as td:
        p = _residential(Path(td))
        C.generate_bundle(p, Path(td) / "out", with_deck=False)
        C.select(p, "C-B")           # 动静横分 → band_day_night
        C.decide_gate(p, "approved", by="业主",
                      summary_path=str(Path(td) / "out" / "g2-approval-summary.md"))
        h = handoff_mod.load_for(p)
        assert h["status"] == "locked"
        assert h["spatial"]["plan_strategy"] == "band_day_night"
        assert h["adjacency"] or h["separation"]

        class _Scheme:
            strategy = "spine_centre"          # 与概念要求不符
            metrics = {"corridor_ratio": 0.42, "room_count": 8,
                       "daylight_rooms_served": "3/8"}

            def area_table(self):
                return [{"name": "主卧"}, {"name": "客厅"}]

        out = handoff_mod.verify_scheme(h, _Scheme(), p)
        assert out["conformance"] == "fail"
        ids = {c["id"] for c in out["conflicts"]}
        assert "H-STRATEGY" in ids and "H-CORRIDOR" in ids

        class _Good:
            strategy = "band_day_night"
            metrics = {"corridor_ratio": 0.11, "room_count": 8,
                       "daylight_rooms_served": "8/8"}

            def area_table(self):
                return [{"name": "主卧"}, {"name": "客厅"}, {"name": "厨房"},
                        {"name": "玄关"}]

        good = handoff_mod.verify_scheme(h, _Good(), p)
        assert good["conformance"] == "pass", good["conflicts"]


def test_j_handoff_file_is_written_and_reloadable():
    with tempfile.TemporaryDirectory() as td:
        p = _residential(Path(td))
        C.generate_bundle(p, Path(td) / "out", with_deck=False)
        C.select(p, "C-B")
        C.decide_gate(p, "approved", by="业主",
                      summary_path=str(Path(td) / "out" / "g2-approval-summary.md"))
        path = Path(td) / "out" / "concept-handoff.json"
        assert path.exists()
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["concept_id"] == "C-B"
        assert data["gate"]["confirmed"] is True
        assert data["style"]["style_ids"]


# --------------------------------------------------------------------------
# K. 变更回流
# --------------------------------------------------------------------------
def test_k_changing_concept_after_g2_reopens_downstream():
    with tempfile.TemporaryDirectory() as td:
        p = _residential(Path(td))
        C.generate_bundle(p, Path(td) / "out", with_deck=False)
        C.select(p, "C-A")
        C.decide_gate(p, "approved", by="业主",
                      summary_path=str(Path(td) / "out" / "g2-approval-summary.md"))
        from omniarchitect.stage_state import confirm_stage

        confirm_stage(p, "S3", by="业主")
        before = len(p.change_log)
        out = C.select(p, "C-B")
        assert out["requires_change_analysis"] is True
        assert "S2" in out["reopened_stages"]
        assert get_state(p, "S2").status != CONFIRMED
        assert get_state(p, "S3").status != CONFIRMED
        assert len(p.change_log) == before + 1
        assert "更换概念" in p.change_log[-1].detail


def test_k_editing_brief_after_g1_blocks_g2():
    with tempfile.TemporaryDirectory() as td:
        p = _residential(Path(td))
        C.generate_bundle(p, Path(td) / "out", with_deck=False)
        answer_question(p, "base.needs", "改主意了：客厅不需要坐 8 个人")
        assess = C.assess_gate(p)
        assert assess.can_approve is False
        assert any("任务书基准已变更" in r for r in assess.blocked_reasons)


# --------------------------------------------------------------------------
# 结构性检查：调色判断不该全项目通用
# --------------------------------------------------------------------------
def test_aesthetic_rules_are_conditional_not_universal():
    from omniarchitect.concept import palette as pal

    cat = __import__("omniarchitect.style", fromlist=["load_catalog"]).load_catalog()
    minimal = pal.aesthetic_policy(cat.load_style("italian-minimal"), "residential")
    assert "AESTHETIC-RESTRAINT" in minimal["applied"]
    assert "WARM-CAP" in minimal["applied"]

    warm_style = cat.load_style("african-contemporary")
    warm_policy = pal.aesthetic_policy(warm_style, "residential")
    assert "AESTHETIC-RESTRAINT" not in warm_policy["applied"], \
        "暖调风格不应被强制套用克制型判据"

    hotel = pal.aesthetic_policy(cat.load_style("italian-minimal"), "hospitality")
    assert "WARM-CAP" not in hotel["applied"], "酒店类项目不该有 40% 暖材上限"
    assert hotel["warm_cap_pct"] is None


def test_palette_check_does_not_pass_unevaluated_items():
    from omniarchitect.concept import palette as pal

    policy = {"applied": ["WARM-CAP", "BLACK-ACCENT"], "profile": "residential",
              "warm_cap_pct": 40, "ratio_rule": "风格声明", "ratio_target": [40, 30, 30],
              "palette": {"entries": []}}
    out = pal.check_palette(policy, {"warm_pct": None, "dark_pct": None, "ratio": None})
    unevaluated = [c for c in out["checks"] if not c["evaluated"]]
    assert unevaluated, "未声明数值时必须记为无法校核"
    assert out["passed"] is True   # 无失败项，但项本身未被评估
