"""阶段数据完整性：住宅默认值不得流进办公 / 酒店项目。

这条审计来自一个真实风险：S4/S5/S8 原来各写死了一张住宅面层表
（客厅餐厅、微水泥、暖白乳胶漆、主卧木地板）。住宅项目看着没问题，
换成办公、酒店就是"系统没在听"——而且它还会以专业成果的形式交付出去。

这里不测"有没有生成文件"，只测**内容对不对**：

* 非住宅项目成果里不得出现住宅房间词；
* 客户没说风格时，不得默认成意式极简；
* S4/S8 的材料必须来自 G2 确认的概念，而不是模板。

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Dict, List

from omniarchitect import finishes as F
from omniarchitect.demo import build_demo_project
from omniarchitect.intake.gate import decide_gate as decide_g1
from omniarchitect.intake.interview import answer_question, start_interview
from omniarchitect.model import Project
from omniarchitect.workflow import StageRunner

OFFICE_PROGRAM: List[Dict[str, object]] = [
    {"name": "开放办公区", "recipe": "open_office", "area_m2": 46, "zone": "day"},
    {"name": "会议室A", "recipe": "meeting", "area_m2": 14, "zone": "day"},
    {"name": "专注间", "recipe": "focus", "area_m2": 8, "zone": "night"},
    {"name": "接待前厅", "recipe": "reception", "area_m2": 10, "zone": "entry"},
    {"name": "打印与储物", "recipe": "storage", "area_m2": 6, "zone": "service"},
]

HOTEL_PROGRAM: List[Dict[str, object]] = [
    {"name": "大堂", "recipe": "lobby", "area_m2": 30, "zone": "day"},
    {"name": "客房A", "recipe": "guestroom", "area_m2": 60, "zone": "night"},
    {"name": "餐厅", "recipe": "restaurant", "area_m2": 18, "zone": "day"},
    {"name": "后勤区", "recipe": "service", "area_m2": 10, "zone": "service"},
]


def _office(tmp: Path) -> Project:
    """有壳体的办公改造项目：几何来自既有楼层，功能是办公。"""
    p = build_demo_project(tmp / "proj")
    p.project_id = "office-fitout"
    p.name = "800㎡ 办公空间（既有楼层改造）"
    p.program = [dict(x) for x in OFFICE_PROGRAM]
    p.constraints = {"budget_cny": 3_200_000}
    p.save(tmp / "proj" / "project.json")
    start_interview(p, "800㎡ 办公空间，60 人，设计团队，做既有楼层改造")
    answer_question(p, "off.headcount", "60 人，两年内到 85 人")
    answer_question(p, "off.meeting", "每天 3-5 场，客户来访多")
    answer_question(p, "off.visitor", "访客不少，但不进工位区")
    answer_question(p, "base.needs", "专注工作要安静；客户来了要有体面的前场")
    # 60 人挤进 131㎡：G1 会先拦下，业主书面接受"减少常驻人数"后才继续
    decide_g1(p, "approved", by="业主", acknowledge=["F-CAP-01"],
              note="业主接受：先按 40 人常驻设计，其余轮用")
    return p


def _hotel(tmp: Path) -> Project:
    p = build_demo_project(tmp / "proj")
    p.project_id = "hotel-30"
    p.name = "30 间客房精品民宿"
    p.program = [dict(x) for x in HOTEL_PROGRAM]
    p.constraints = {"style": "现代意式极简", "budget_cny": 6_000_000}
    p.save(tmp / "proj" / "project.json")
    start_interview(p, "30 间客房的度假民宿，做精品路线")
    answer_question(p, "hos.positioning", "情侣与家庭度假为主，客单价中高")
    answer_question(p, "hos.back_of_house", "布草与垃圾需要独立后场通道")
    answer_question(p, "base.needs", "客人到店要有仪式感；后勤不要被看到")
    decide_g1(p, "approved", by="业主")
    return p


def _run_all(p: Project, tmp: Path) -> Dict[str, str]:
    """跑到 S8，返回 S4/S5/S8 的产物文本（按阶段目录前缀聚合）。"""
    runner = StageRunner(p, tmp / "out", assume_approval=True, project_dir=tmp / "proj")
    for sid in ("S2", "S3", "S4", "S5", "S6", "S7", "S8"):
        runner.run_stage(sid, confirm=True)
    codes = {"S4": "04", "S5": "05", "S8": "08"}
    texts: Dict[str, str] = {}
    for f in sorted((tmp / "out").rglob("*.md")):
        stage = next((sid for sid, code in codes.items()
                      if any(part.startswith(code + "-") for part in f.parts)), "")
        if stage:
            texts[stage] = texts.get(stage, "") + f.read_text(encoding="utf-8")
    return texts


# --------------------------------------------------------------------------
# 1. 办公项目不许出现住宅房间词
# --------------------------------------------------------------------------
def test_office_output_has_no_residential_rooms():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        p = _office(tmp)
        assert F.project_profile(p) == "office", F.project_profile(p)
        texts = _run_all(p, tmp)
        assert texts, "S4/S5/S8 没有产出文本"
        blob = "\n".join(texts.values())
        found = F.foreign_words(p, blob)
        assert not found, f"办公项目成果里出现住宅用词：{found}"
        # 应出现办公自己的词
        assert any(w in blob for w in ("办公", "会议", "前厅", "专注")), blob[:400]


# --------------------------------------------------------------------------
# 2. 没有声明风格时，不许默认意式极简
# --------------------------------------------------------------------------
def test_undeclared_style_is_not_filled_in_with_a_default():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        p = _office(tmp)
        assert not (p.constraints or {}).get("style")
        label = F.style_label(p)
        assert "未指定" in label, label
        assert "意式" not in label
        s4 = _run_all(p, tmp).get("S4", "")
        assert "现代意式极简" not in s4, "未声明风格时被默认成意式极简"
        assert "未指定风格" in s4


# --------------------------------------------------------------------------
# 3. S4/S8 的材料必须来自 G2 确认的概念
# --------------------------------------------------------------------------
def test_concept_materials_reach_s4_and_s8():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        p = build_demo_project(tmp / "proj")
        p.constraints = {**(p.constraints or {}), "style": "现代意式极简",
                         "budget_cny": 1_600_000}
        p.save(tmp / "proj" / "project.json")
        start_interview(p, "150㎡ 大平层，一家三口，现代意式极简")
        answer_question(p, "base.needs", "客厅要能坐 8 个人；孩子写作业要看得见")
        decide_g1(p, "approved", by="业主")

        from omniarchitect import concept as C

        runner = StageRunner(p, tmp / "out", project_dir=tmp / "proj")
        runner.run_stage("S2", confirm=False)
        C.select(p, "C-B")
        assert runner.approve("S2", by="业主")["status"] == "confirmed"

        names = [m["name"] for m in F.concept_materials(p)]
        assert names, "概念方案没有材料方向"

        runner.run_stage("S3", confirm=False)
        runner.approve("S3", by="业主")
        for sid in ("S4", "S5", "S6", "S7", "S8"):
            runner.run_stage(sid, confirm=True)

        s4 = (tmp / "out" / "S4" / "preliminary-design.md").read_text(encoding="utf-8") \
            if (tmp / "out" / "S4" / "preliminary-design.md").exists() else ""
        s8 = (tmp / "out" / "S8" / "material-schedule.md").read_text(encoding="utf-8") \
            if (tmp / "out" / "S8" / "material-schedule.md").exists() else ""
        if not s4:
            s4 = "".join(f.read_text(encoding="utf-8")
                         for f in (tmp / "out").rglob("preliminary-design.md"))
            s8 = "".join(f.read_text(encoding="utf-8")
                         for f in (tmp / "out").rglob("material-schedule.md"))
        assert any(n in s4 for n in names), f"S4 没用概念材料：{names}"
        assert any(n in s8 for n in names), f"S8 材料表没接概念材料：{names}"
        assert "待确认（S4 与主创定案）" not in s8, "有概念材料时不该还写待确认"


# --------------------------------------------------------------------------
# 4. 酒店项目用自己的空间，不用住宅房名
# --------------------------------------------------------------------------
def test_hotel_project_uses_its_own_spaces():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        p = _hotel(tmp)
        assert F.project_profile(p) == "hospitality"
        zones = F.zones(p)
        names = [n for _z, _l, ns in zones for n in ns]
        assert any("大堂" in n for n in names), names
        assert not any(w in " ".join(names) for w in ("客厅", "主卧")), names
