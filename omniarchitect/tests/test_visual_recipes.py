"""表现技法库（图纸派生 / 版面）的验收测试。

这一组的重点不是"能不能编译"，而是**照抄那几条提示词会犯的错有没有被挡住**：

* 图像模型不得写字、更不得写尺寸数字（它会编）；
* 图纸派生配方没有参考图就只是猜几何；
* 平面未过 G3 时，这些图只能探索，不能排队花钱；
* 版面文字必须落到叠加清单里，而不是留在模型输出里。

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import tempfile
from pathlib import Path

from omniarchitect.style import recipes as R
from omniarchitect.style import compiler as K
from omniarchitect.style import provider_bridge as B
from omniarchitect.style.resources import PROMPT_TARGETS, TARGET_STAGES

CAT = K.load_catalog()


def _brief(**kw) -> K.SpaceBrief:
    base = dict(space_name="客厅", width_mm=4200, depth_mm=6000, ceiling_mm=2800)
    base.update(kw)
    return K.SpaceBrief(**base)


def _compile(target: str, *, plan: bool = True, **kw) -> K.CompiledPrompt:
    return K.compile_prompt(["italian-minimal"], _brief(**kw), target=target,
                            catalogue=CAT, plan_confirmed=plan)


# --------------------------------------------------------------------------
# 1. 三处登记必须一致：配方 / 目标类型 / 阶段 / 能力域
# --------------------------------------------------------------------------
def test_recipe_ids_are_registered_everywhere():
    for rid in R.ids():
        assert rid in PROMPT_TARGETS, f"{rid} 未登记为提示词目标类型"
        assert rid in TARGET_STAGES, f"{rid} 未登记阶段"
        assert rid in B.TARGET_SCOPE, f"{rid} 未登记创作能力域"
        assert B.TARGET_SCOPE[rid] in B.CREATIVE_SCOPES, rid
    # 阶段登记必须与配方自身一致，不能两处各写一套
    for rid, rec in R.RECIPES.items():
        assert tuple(TARGET_STAGES[rid]) == tuple(rec.stages), rid


# --------------------------------------------------------------------------
# 2. 画像只有一个来源
# --------------------------------------------------------------------------
def test_profile_comes_from_the_recipe_not_a_second_copy():
    for rid, rec in R.RECIPES.items():
        prof = K.TARGET_PROFILE[rid]
        assert prof["zh"] == rec.name_zh
        assert prof["lens_zh"] == rec.projection_zh
        assert prof["family"] == rec.family


# --------------------------------------------------------------------------
# 3. 投影约定压过风格库机位
# --------------------------------------------------------------------------
def test_recipe_projection_overrides_the_style_camera():
    plan = _compile("plan-color")
    assert "顶视" in plan.positive_zh or "俯视" in plan.positive_zh
    # 风格库里"一点透视、低于人眼"这类机位不能接管俯视图
    assert "低于人眼" not in plan.positive_zh, plan.positive_zh
    for rid in ("plan-axon", "section-elevation"):
        p = _compile(rid)
        assert R.RECIPES[rid].projection_zh in p.positive_zh, rid


def test_section_is_orthographic_and_forbids_perspective():
    p = _compile("section-elevation")
    assert "正投影" in p.positive_zh
    joined = " ".join(p.negative_zh)
    assert "透视" in joined and ("消失点" in joined or "缩短" in joined)


# --------------------------------------------------------------------------
# 4. 图纸派生必须带参考图，否则要明确警告（不是静默出图）
# --------------------------------------------------------------------------
def test_drawing_recipes_warn_when_no_reference_is_attached():
    for rid in ("plan-color", "plan-axon", "section-elevation", "presentation-board"):
        p = _compile(rid, references=())
        assert any("参考图" in w and "猜几何" in w for w in p.warnings), (rid, p.warnings)

    with_ref = _compile("plan-color", references=("plan.png",))
    assert any("唯一几何依据" in line for line in [with_ref.positive_zh])
    assert not any("猜几何" in w for w in with_ref.warnings)


# --------------------------------------------------------------------------
# 5. 未确认平面：探索可以，提交不行（关键负向）
# --------------------------------------------------------------------------
def test_unconfirmed_plan_marks_exploration_and_blocks_submission():
    p = _compile("plan-color", plan=False)
    assert p.gate["blocked"] is True
    assert p.positive_zh.startswith("【探索稿·平面未确认】")
    assert any("不得提交" in w for w in p.warnings)

    with tempfile.TemporaryDirectory() as td:
        try:
            B.submit([p], out_dir=Path(td))
        except ValueError as exc:
            assert "G3" in str(exc) and "plan-color" in str(exc)
        else:
            raise AssertionError("未确认平面的配方被排队了")
        assert not (Path(td) / "style-jobs.json").exists(), "被拒的任务不得留下任务包"

    ok = _compile("plan-color", plan=True)
    with tempfile.TemporaryDirectory() as td:
        rep = B.submit([ok], out_dir=Path(td))
        assert rep["job_count"] == 1
        assert rep["deferred_count"] == 1, "平台未配置时应登记为待执行，而不是假装提交"
        assert (Path(td) / "style-jobs.json").exists()


def test_concept_sheet_does_not_need_a_confirmed_plan():
    p = _compile("concept-sheet", plan=False)
    assert p.gate["blocked"] is False
    assert not p.positive_zh.startswith("【探索稿")
    with tempfile.TemporaryDirectory() as td:
        assert B.submit([p], out_dir=Path(td))["job_count"] == 1


# --------------------------------------------------------------------------
# 6. 文字：不让模型写，改由排版层叠加
# --------------------------------------------------------------------------
def test_board_text_is_never_drawn_by_the_model():
    for rid in ("presentation-board", "concept-sheet"):
        p = _compile(rid)
        assert p.text_overlay, f"{rid} 没有文字叠加清单"
        joined_neg = " ".join(p.negative_zh) + " ".join(p.negative_en)
        assert "不得出现任何文字" in joined_neg
        assert "dimension" in joined_neg or "尺寸" in joined_neg
        # 正向里只允许"留出空白"，不允许"写上标签"
        assert "留出空白" in p.positive_zh
        assert "写上" not in p.positive_zh
        assert any("不让模型写" in w for w in p.warnings), p.warnings

    board = _compile("presentation-board")
    assert any("DXF" in t for t in board.text_overlay), board.text_overlay


def test_no_recipe_asks_the_model_for_dimensions():
    """尺寸数字只能来自 DXF 矢量层；任何配方都不得让模型画。"""
    boundary = ("不得", "不是")
    forbidden_use = ("量取", "尺寸", "图纸", "报审", "下单", "样板", "依据", "施工",
                     "净高", "净宽")
    for rid in R.ids():
        rec = R.RECIPES[rid]
        assert rec.checks, rid
        assert any(any(b in c for b in boundary) and any(f in c for f in forbidden_use)
                   for c in rec.checks), (rid, rec.checks)
        for line in rec.framing_zh + rec.guards_zh:
            assert "标注尺寸" not in line and "写上尺寸" not in line, (rid, line)


# --------------------------------------------------------------------------
# 7. 一致性指纹不受配方影响：同风格同修订，跨视图共用一个身份
# --------------------------------------------------------------------------
def test_consistency_key_is_shared_across_recipes():
    keys = {_compile(rid).consistency_key for rid in R.ids()}
    assert len(keys) == 1, keys


# --------------------------------------------------------------------------
# 8. 门禁列表与配方声明必须自洽
# --------------------------------------------------------------------------
def test_plan_gate_list_is_derived_not_hand_maintained():
    expected = {rid for rid, rec in R.RECIPES.items() if rec.requires_plan}
    assert set(R.PLAN_GATED) == expected
    for rid in R.PLAN_GATED:
        assert R.gate_of(rid, plan_confirmed=False)["blocked"] is True
        assert R.gate_of(rid, plan_confirmed=True)["blocked"] is False
    assert R.gate_of("concept-sheet", plan_confirmed=False)["blocked"] is False


def test_material_moodboard_does_not_require_a_reference_but_keeps_the_boundary():
    p = _compile("material-moodboard", plan=False)
    rec = R.RECIPES["material-moodboard"]
    assert rec.requires_reference is False
    assert not any("猜几何" in w for w in p.warnings)
    assert any("不是" in c and "材料样板" in c for c in rec.checks)


# --------------------------------------------------------------------------
# 9. S2 环节：任务包里必须有这两条版面配方
# --------------------------------------------------------------------------
def test_s2_bundle_carries_the_board_recipes():
    import json
    import tempfile
    from pathlib import Path

    from omniarchitect import concept as C
    from omniarchitect.demo import build_demo_project
    from omniarchitect.intake.gate import decide_gate as decide_g1
    from omniarchitect.intake.interview import answer_question, start_interview

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        p = build_demo_project(tmp / "proj")
        p.constraints = {**(p.constraints or {}), "style": "现代意式极简"}
        p.save(tmp / "proj" / "project.json")
        start_interview(p, "150㎡ 大平层，一家三口，现代意式极简")
        answer_question(p, "base.needs", "客厅要能坐 8 个人；东西很多需要收纳")
        decide_g1(p, "approved", by="业主")

        C.generate_bundle(p, tmp / "out", with_deck=False)
        payload = json.loads((tmp / "out" / "concept-visual-jobs.json")
                             .read_text(encoding="utf-8"))
        targets = {j["target"] for j in payload["jobs"]}
        assert "concept-sheet" in targets, targets
        assert "material-moodboard" in targets, targets
        # 不仅有任务，还要带着"文字由排版层叠加"的清单
        sheet = next(j for j in payload["jobs"] if j["target"] == "concept-sheet")
        assert sheet["text_overlay"], "概念设计板没有文字叠加清单"
        assert "概念标题" in sheet["text_overlay"]
        assert payload["non_authoritative"] is True
        assert payload["third_party_fallback"] == "forbidden"


# --------------------------------------------------------------------------
# 10. G3 之后：图纸派生任务包要自动生成，但绝不自动提交
# --------------------------------------------------------------------------
def test_g3_emits_drawing_recipes_without_spending():
    import json
    import tempfile
    from pathlib import Path

    from omniarchitect import concept as C
    from omniarchitect.demo import build_demo_project
    from omniarchitect.intake.gate import decide_gate as decide_g1
    from omniarchitect.intake.interview import answer_question, start_interview
    from omniarchitect.workflow import StageRunner

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        p = build_demo_project(tmp / "proj")
        p.constraints = {**(p.constraints or {}), "style": "现代意式极简"}
        p.save(tmp / "proj" / "project.json")
        start_interview(p, "150㎡ 大平层，一家三口，现代意式极简")
        answer_question(p, "base.needs", "客厅要能坐 8 个人；东西很多需要收纳")
        decide_g1(p, "approved", by="业主")

        runner = StageRunner(p, tmp / "out", project_dir=tmp / "proj")
        runner.run_stage("S2", confirm=False)
        chosen = next(c for c in p.meta["concept"]["options"]["concepts"]
                      if (c.get("spatial_prototype") or {}).get("plan_strategy"))
        C.select(p, chosen["concept_id"])
        assert runner.approve("S2", by="业主")["status"] == "confirmed"
        runner.run_stage("S3", confirm=False)
        res = runner.approve("S3", by="业主")
        assert res["status"] == "confirmed", res.get("notes")

        f = next((tmp / "out").rglob("drawing-visuals.json"), None)
        assert f, "G3 通过后没有生成图纸派生任务包"
        payload = json.loads(f.read_text(encoding="utf-8"))
        targets = {j["target"] for j in payload["jobs"]}
        assert {"plan-color", "plan-axon", "presentation-board"} <= targets, targets
        assert payload["plan_confirmed"] is True
        for j in payload["jobs"]:
            assert j["status"] == "awaiting_authorization", j["status"]
            assert j["references"], "图纸派生没有带参考图"
        # 只有编译，没有生成：台账里不存在任何已提交/已生成记录
        import omniarchitect.concept.visual as V

        for ledger in (tmp / "out").rglob(V.LEDGER_NAME):
            entries = (V.load_ledger(ledger).get("entries") or {}).values()
            assert not [e for e in entries if e.get("status") in ("submitted", "generated")]
        assert not list((tmp / "out").rglob("drawing-visuals/*.png"))
