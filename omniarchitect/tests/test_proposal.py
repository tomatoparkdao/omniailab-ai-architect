"""概念汇报（proposal / curation / anim / quick）的守卫测试。

这些测试守的是本轮的**成果形态**，不是实现细节。一旦回退，客户又会收到
"二十多页文字 + 一排链接"：

1. 页数 8–12，一页只讲一件事；
2. 主推方向用自有主图版（图纸），不是拿参考照片冒充方案；
3. 参考页必须写出出处与权限，取不到图要说明原因；
4. 上下文字符串被逐字拆开时要拼回去（否则简报里出现"每；层"）；
5. HTML 与 PPTX 页数一致（同一份页面模型）；
6. 概念动画是真能播的 HTML，不是一段文字分镜；
7. S1 判断一页说清，问题不超过三个。

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import tempfile
from pathlib import Path
from types import SimpleNamespace

from omniarchitect.concept import anim as anim_mod
from omniarchitect.concept import curation as cur_mod
from omniarchitect.concept import plate as plate_mod
from omniarchitect.concept import proposal as prop
from omniarchitect.concept import quick as quick_mod


def _tmp() -> Path:
    """自建临时目录。

    `scripts/run_tests.py` 是直接调函数、不跑 pytest 的，所以不能用
    `tmp_path` 这类 fixture——用了会在运行时因缺参数而失败。
    """
    return Path(tempfile.mkdtemp(prefix="proposal-"))


def _concept(cid: str = "C-A", family: str = "cluster") -> dict:
    return {
        "concept_id": cid, "concept_name": "公共核心 · 后场独立",
        "concept_statement": "把公共功能收进一个核，后场走自己的通道。",
        "role_label": "稳妥 · 功能效率优先",
        "design_problem": "客人流线与后勤流线交叉，送餐穿过大堂。",
        "design_strategy": ["公共功能集中在裙房两层", "后场独立成核并设专用货梯"],
        "advantages": ["客人永远看不到后场"],
        "user_experience": "落客区 → 大堂 → 前台，送餐不穿越大堂。",
        "spatial_prototype": {"family": family, "prototype_id": "HOT-CORE",
                              "zoning": "裙房 2 层做公共核，塔楼做客房",
                              "spatial_logic": "核心筒居中，客房沿两侧展开",
                              "circulation": "客人：大堂 → 电梯/楼梯；两条竖向动线不共用",
                              "daylight": "大堂与餐厅需要自然光；宴会厅可无窗"},
        "material_direction": [{"name": "米色石材", "application": "地面与墙面"},
                               {"name": "木饰面", "application": "墙面与门"}],
        "lighting_direction": ["大堂 2700K 暖光", "餐厅重点照明"],
        "style_labels": ["现代东方"], "tradeoffs": ["标准层少 2 间可售房"],
        "aesthetic_policy": {"ratio_rule": "主色 60 / 辅色 30 / 强调 10"},
        "evidence": ["客户要求后场与客人流线分离"],
    }


def _ctx() -> SimpleNamespace:
    return SimpleNamespace(
        project_id="t", revision=3, name="测试项目", profile_id="hospitality",
        profile_label="酒店", lead_id="interior", precision="schematic",
        dimensional_note="无几何", area_available_m2=None, target_area_m2=1200.0,
        style_preference="现代东方", opportunities=[{"problem": "流线交叉"}],
        uncertainty=[], feelings={"安静": ["quiet"]}, feeling_text="喜欢安静",
        brief_lines=lambda: ["项目类型：酒店"],
    )


def _concept_set() -> dict:
    return {"concepts": [_concept("C-A", "cluster"), _concept("C-B", "linear")],
            "count": 2}


def _comparison() -> dict:
    return {"recommendation": {"concept_id": "C-A", "rationale": ["功能效率最高"],
                               "why_not": [{"concept_id": "C-B", "reason": "少 2 间房"}]}}


def _build(tmp: Path) -> dict:
    rules = {"tokens": {"paper": "#FAF8F3", "ink": "#1A1D1A", "accent": "#2F5D45"},
             "source": "视觉.md"}
    return prop.build(SimpleNamespace(name="测试项目", project_id="t", revision=3),
                      _ctx(), _concept_set(), _comparison(), {}, {}, {},
                      curation={"available": False, "shots": [], "reason": "无匹配实景"},
                      judgment={"headline": "酒店；既有空间室内装修", "focus": [],
                                "aesthetic": {"label": "现代东方", "source": "client"},
                                "limits": [], "type_label": "B4 酒店与住宿工装",
                                "nature": "既有空间室内装修"},
                      rules=rules, out_dir=tmp)


def test_page_count_is_within_the_proposal_budget() -> None:
    model = _build(_tmp())
    assert 8 <= model["count"] <= 12, model["count"]
    kinds = [p.kind for p in model["pages"]]
    assert kinds[0] == "cover" and kinds[-1] == "appendix"
    assert "concept" in kinds and "second" in kinds


def test_main_direction_uses_own_plate_not_a_borrowed_photo() -> None:
    model = _build(_tmp())
    page = next(p for p in model["pages"] if p.kind == "concept")
    assert page.figures, "主推方向必须有一张主图"
    fig = page.figures[0]
    assert fig.role == "diagram", fig.role
    assert "自有图解" in fig.credit
    assert Path(fig.path).exists()


def test_plate_is_deterministic_svg_with_scale_and_north() -> None:
    svg = plate_mod.hero_plate(_concept(), heading=False)
    assert svg.startswith("<svg") and "polygon" in svg
    assert "N" in svg                    # 指北
    assert "m" in svg                    # 比例条刻度
    assert "非按比例" in svg


def test_second_direction_is_a_different_spatial_family() -> None:
    model = _build(_tmp())
    page = next(p for p in model["pages"] if p.kind == "second")
    assert "备选" in page.kicker
    assert model["alternative"] == "C-B"


def test_reference_page_carries_credit_and_rights() -> None:
    shot = {"role": "intent", "path": "x.jpg", "title": "酒店接待厅",
            "tags": ["酒店设计", "大堂吧"], "credit": "Luxora AI 素材库 · 酒店接待厅",
            "kind": "space", "explain": {"borrow": ["石材整面"], "limits": ["住宅尺度"]},
            "caption": "酒店设计 · 大堂吧"}
    result = {"available": True, "shots": [shot], "count": 1,
              "rights_note": cur_mod.RIGHTS["proposal"],
              "terms": {"basis": "客户感受词"}}
    md = cur_mod.markdown(result)
    assert "Luxora AI 素材库" in md
    assert "清权" in md


def test_unavailable_reference_says_why_instead_of_substituting() -> None:
    out = cur_mod.curate(Path("out/_unused"), ctx=_ctx(), sector="education",
                         style_labels=["现代简洁"], use_cache=False)
    assert out["available"] is False
    assert out["shots"] == []
    assert "素材" in out["reason"] or "实景" in out["reason"]


def test_char_split_strings_are_rejoined() -> None:
    broken = ["每", "层", " ", "2", "0", " ", "间", "少", "2", "间",
              "尺寸未核实：须在 S3 复核"]
    got = prop._as_list(broken)          # noqa: SLF001  这是要守的解析规则
    assert got[0].startswith("每层")
    assert got[-1].startswith("尺寸未核实")


def test_html_and_pptx_share_the_same_page_count() -> None:
    tmp_path = _tmp()
    model = _build(tmp_path)
    html = prop.write_html(model, tmp_path)
    assert Path(html).exists()
    n_html = Path(html).read_text(encoding="utf-8").count('<section class="page"')
    assert n_html == model["count"]
    info = prop.write_pptx(model, tmp_path)
    if info.get("ok"):
        assert info["slides"] == model["count"], info


def test_motion_is_a_real_playable_html() -> None:
    """有概念数据时才出动画；动画内容按专业画，不是固定体块。"""
    info = anim_mod.build(concept=_concept(), out_dir=_tmp(), discipline="interior")
    text = Path(info["path"]).read_text(encoding="utf-8")
    assert "<svg" in text and "<script>" in text
    assert "setInterval" in text
    assert text.count('class="scene') >= 4
    assert "SEQUENCE" in text, "室内项目的动画应是功能与序列，不是体块生成"
    assert "客房走廊" in text or "公共核" in text


def test_motion_is_skipped_when_the_concept_has_no_evolution_logic() -> None:
    """推不出来就不出动画：宁可少一个动画，不放不相干的专业推演。"""
    thin = {"concept_id": "C-X", "concept_name": "空概念",
            "spatial_prototype": {"family": "cluster"}}
    info = anim_mod.build(concept=thin, out_dir=_tmp(), discipline="interior")
    assert info["path"] == ""
    assert info["skipped"], info


def test_evolution_steps_follow_the_discipline() -> None:
    """建筑／室内／景观各自四条线，不能互相顶替。"""
    evo = prop.evo_mod
    arch = evo.plan(_concept(), "architecture")
    inner = evo.plan(_concept(), "interior")
    land = evo.plan(_concept(), "landscape")
    assert [s.name for s in arch.steps][:2] == ["场地与限界", "体量分解"]
    assert [s.name for s in inner.steps][:2] == ["功能重组", "空间序列"]
    assert [s.name for s in land.steps][:2] == ["场地与边界", "空间层次"]
    for p_ in (arch, inner, land):
        assert p_.ok, p_.reason
        assert len({s.note for s in p_.steps}) >= 3, "四步不能复读同一句话"


def test_evolution_refuses_without_the_data_it_needs() -> None:
    """没有分区也没有序列时，室内推敲必须说"做不了"，而不是编一套。"""
    thin = {"concept_id": "C-Y", "concept_name": "空概念",
            "spatial_prototype": {"family": "cluster"}}
    p_ = prop.evo_mod.plan(thin, "interior")
    assert p_.ok is False
    assert "分区" in p_.reason or "序列" in p_.reason


def test_quick_judgment_is_one_page_and_at_most_three_questions() -> None:
    from omniarchitect.model import Project

    p = Project(project_id="q", name="某小学")
    p.meta = {}
    j = quick_mod.judge(p)
    assert j["questions"] is not None and len(j["questions"]) <= 3
    text = quick_mod.render(j)
    assert len(text.splitlines()) <= 40
    assert "设计定位" in text


def test_plate_follows_the_discipline_it_is_drawn_for() -> None:
    tmp_path = _tmp()
    """景观画平面、室内画标准层、建筑画体块——图必须是他委托的那件事。

    拿建筑体块当庭院的主图、拿建筑外立面照当庭院封面，是这类汇报
    最容易犯的错：客户一眼就知道你没看懂委托范围。
    """
    land = plate_mod.write(_concept(), tmp_path, discipline="landscape",
                           width=800, height=452, annotate=False)
    assert "水面" in Path(land).read_text(encoding="utf-8")
    inner = plate_mod.write(_concept(), tmp_path, discipline="interior",
                            width=800, height=452, annotate=False)
    text = Path(inner).read_text(encoding="utf-8")
    assert "客房带" in text and "公共核" in text
    arch = plate_mod.write(_concept(), tmp_path, discipline="architecture",
                           width=800, height=452, annotate=False)
    assert "入口" in Path(arch).read_text(encoding="utf-8")


def test_landscape_cover_refuses_a_building_photo() -> None:
    house = {"title": "比利时式优雅",
             "tags": ["建筑", "别墅", "景观草坪", "户外花园"]}
    garden = {"title": "柱廊花园", "tags": ["花园", "树木", "绿色色调"]}
    assert prop._is_landscape_shot(garden) is True      # noqa: SLF001
    assert prop._is_landscape_shot(house) is False      # noqa: SLF001


def test_colour_ratio_uses_the_declared_percentages() -> None:
    colour = [{"name": "浅灰白", "pct": 55, "band": "dominant"},
              {"name": "包豪斯红", "pct": 12, "band": "accent"}]
    line = prop._ratio_line(colour)                     # noqa: SLF001
    assert "55%" in line and "12%" in line
    assert "未声明" not in line
    assert "未声明" in prop._ratio_line([])             # noqa: SLF001  空色板要如实说


def test_clip_cuts_at_a_sentence_boundary_not_mid_word() -> None:
    text = "教学区 1,560 m² 分 3 栋，中庭在中间；食堂 356 m² 与体育馆 800 m²"
    cut = prop._clip(text, 30)                          # noqa: SLF001
    assert not cut.endswith("…"), cut
    assert cut in text, cut


def test_style_shortlist_follows_the_project_type() -> None:
    """学校不能先谈非洲当代／美式古典；那两类根本没声明过教育空间。"""
    p = SimpleNamespace(name="某小学", constraints={},
                        meta={"taxonomy": {"codes": ["A3"]}}, program=[])
    a = quick_mod._aesthetic(p, "architecture")         # noqa: SLF001
    labels = [o["label"] for o in a["options"]]
    assert labels, a
    assert "包豪斯" in "".join(labels) or "亲自然" in "".join(labels), labels
    assert "非洲当代" not in labels and "美式古典" not in labels, labels
