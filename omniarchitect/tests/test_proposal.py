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
from omniarchitect.concept import diagrams as dia
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
    land_text = Path(land).read_text(encoding="utf-8")
    # 这个概念没声明水面：图版就不能给他一个池子（备选方案最容易被画错的地方）
    assert "茶座" in land_text and "水景" not in land_text, land_text[:400]
    inner = plate_mod.write(_concept(), tmp_path, discipline="interior",
                            width=800, height=452, annotate=False)
    text = Path(inner).read_text(encoding="utf-8")
    # 没有声明平面组织方式的室内，按工装三段式画：教学／连廊／办公，
    # 绝不套客房图版（客房是酒店标准层的事）
    assert "连廊" in text and "客房" not in text
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


# --------------------------------------------------------------------------
# 图版与推敲图必须同源：一套几何，两处渲染
# --------------------------------------------------------------------------
def _hotel() -> dict:
    return {"concept_id": "C-A", "concept_name": "公共核心 · 后场独立",
            "concept_statement": "大堂、餐饮与会议集中在首层与二层形成一个公共核，后场用独立通道与货梯上下",
            "spatial_prototype": {"family": "cluster", "plan_layout": "public_core",
                                  "zoning": "裙房 2 层做公共核，塔楼做客房",
                                  "circulation": "客人：大堂→电梯；服务：后场货梯→各层服务间",
                                  "daylight": "大堂与餐厅需要自然光"},
            "experience_sequence": ["落客区 → 大堂 → 前台 → 客餐厅"],
            "advantages": ["公共核与后场分离"], "tradeoffs": ["公共核占两层"]}


def _garden(kind: str = "pond") -> dict:
    return {"concept_id": "C-A", "concept_name": "一池静水 · 环形游线",
            "concept_statement": "院子中心放一块静水，园路绕水一圈；茶座在水远岸，回望房子",
            "spatial_prototype": {"family": "courtyard", "massing_kind": kind,
                                  "prototype_id": "DLB-LAN-POND",
                                  "zoning": "以水面为心，园路成环",
                                  "circulation": "环形主路从入口绕水一周回到入口",
                                  "daylight": "水面把光反射进室内"},
            "experience_sequence": ["进入 → 绕行 → 停留"],
            "advantages": ["回应了业主的同一个问题"], "tradeoffs": ["水面维护是长期成本"]}


def test_plate_and_steps_share_one_geometry() -> None:
    """主推图与四步图必须用同一份几何，否则大堂在两张图上会跑到不同位置。"""
    for concept, disc in ((_hotel(), "interior"), (_garden(), "landscape")):
        p = prop.evo_mod.plan(concept, disc, sector="hospitality")
        same = prop.evo_mod.layout_mod.frames(concept, disc, sector="hospitality")
        assert p.frames == same, disc
        assert p.frames, disc


def test_public_core_is_two_frames_and_keeps_the_lobby_off_the_guest_floor() -> None:
    """酒店公共核：公共层与标准层分两幅画，大堂不许出现在客房层里。"""
    frs = prop.evo_mod.layout_mod.frames(_hotel(), "interior", sector="hospitality")
    assert [f.title for f in frs] == ["裙房公共层", "客房标准层"], frs
    public, floor = frs
    pub_labels = {r.label for r in public.regions}
    floor_labels = {r.label for r in floor.regions}
    for need in ("大堂", "前台", "客梯厅", "后场"):
        assert need in pub_labels, pub_labels
    assert "大堂" not in floor_labels and "公共核" not in floor_labels, floor_labels
    for need in ("客房", "走廊", "客梯厅", "服务核"):
        assert need in floor_labels, floor_labels
    assert any("布草" in r.sub for r in floor.regions), "布草与服务梯要写清楚"


def test_guest_flow_and_service_flow_never_cross() -> None:
    """客流在右半、服务流在左半：两条线不许交叉，这是"后场独立"的全部意思。"""
    public = prop.evo_mod.layout_mod.frames(_hotel(), "interior",
                                            sector="hospitality")[0]
    guest = next(l for l in public.links if l.key == "guest_flow")
    svc = next(l for l in public.links if l.key == "service_flow")
    assert min(p[0] for p in guest.pts) > max(p[0] for p in svc.pts)


def test_landscape_tea_seat_sits_across_the_water_from_the_gate() -> None:
    """茶座在远岸：它必须在水面的另一侧，而且看房子的视线要真的穿过水面。"""
    fr = prop.evo_mod.layout_mod.frames(_garden(), "landscape")[0]
    water = next(r for r in fr.regions if r.kind == "water")
    seat = next(n for n in fr.nodes if n.key == "seat")
    gate = next(n for n in fr.nodes if n.key == "gate")
    wx, wy, ww, wh = water.box
    wcx, wcy = wx + ww / 2, wy + wh / 2
    # 与入口分处水面两侧
    assert (seat.y - wcy) * (gate.y - wcy) < 0, (seat.y, gate.y, wcy)
    # 视线穿水
    sight = next(l for l in fr.links if l.key == "sight_back")
    (ax, ay), (bx, by) = sight.pts[0], sight.pts[-1]
    mid_y = (ay + by) / 2
    assert wy < mid_y < wy + wh, (mid_y, wy, wh)
    assert ax < wcx < bx or bx < wcx < ax


def test_entry_path_touches_the_ring_and_never_crosses_the_water() -> None:
    """入口必须接上环路；环在内圈、水在外圈，路不许从水面上走。"""
    fr = prop.evo_mod.layout_mod.frames(_garden(), "landscape")[0]
    ring = fr.rings[0]
    entry = next(l for l in fr.links if l.key == "entry")
    x, y = entry.pts[-1]
    # 落在环的椭圆上（容差 2%）
    v = ((x - ring.cx) / ring.rx) ** 2 + ((y - ring.cy) / ring.ry) ** 2
    assert abs(v - 1.0) < 0.05, v
    water = next(r for r in fr.regions if r.kind == "water")
    wx, wy, ww, wh = water.box
    for lk in fr.links:
        if lk.kind != "path":
            continue
        for px, py in lk.pts:
            inside = (wx < px < wx + ww) and (wy < py < wy + wh)
            assert not inside, (lk.key, px, py)
    assert ring.rx > ww / 2 and ring.ry > wh / 2


def test_dry_stream_alternative_draws_no_water_at_all() -> None:
    """备选是"不做池子"：图里不能出现任何水面，必须有旱溪与台地。"""
    fr = prop.evo_mod.layout_mod.frames(_garden("terraces"), "landscape")[0]
    kinds = {r.kind for r in fr.regions}
    assert "water" not in kinds, kinds
    labels = {r.label for r in fr.regions}
    assert {"高台地", "低台地", "旱溪", "茶座"} <= labels, labels
    svg = plate_mod.plan_plate(_garden("terraces"), discipline="landscape",
                               width=940, height=448, annotate=False)
    assert "#DDE7EE" not in svg, "旱溪方案里出现了水面填充色"


def test_every_landscape_variant_has_its_own_layout_and_a_fixed_house() -> None:
    """三套景观概念要画出三种不同的场地结构；房子是场地条件，位置不许变。"""
    shapes, houses = [], []
    for kind in ("pond", "terraces", "grove"):
        fr = prop.evo_mod.layout_mod.frames(_garden(kind), "landscape")[0]
        shapes.append(tuple(sorted(r.key for r in fr.regions)))
        houses.append(next(r.box for r in fr.regions if r.key == "house"))
    assert len(set(shapes)) == 3, shapes
    assert len(set(houses)) == 1, houses


def test_labels_stay_in_the_frame_and_never_overlap() -> None:
    """标签位置由几何算出：不许出界、不许互相遮挡。"""
    cases = ((_hotel(), "interior", (56.0, 120.0, 529.0, 260.0)),
             (_garden(), "landscape", (56.0, 96.0, 422.0, 330.0)),
             (_garden("terraces"), "landscape", (56.0, 96.0, 422.0, 330.0)))
    for concept, disc, area in cases:
        for fr in prop.evo_mod.layout_mod.frames(concept, disc, sector="hospitality"):
            s = dia.Svg(1200, 560)
            labels = prop.evo_mod.layout_mod.draw(s, fr, area,
                                                  prop.evo_mod._pal(None))  # noqa: SLF001
            assert labels, fr.title
            x0, y0, w, h = area
            for i, a in enumerate(labels):
                ax, ay, aw, ah = a["rect"]
                assert x0 - 4 <= ax and ax + aw <= x0 + w + 4, (a["text"], a["rect"])
                assert y0 - 4 <= ay and ay + ah <= y0 + h + 34, (a["text"], a["rect"])
                for b in labels[i + 1:]:
                    bx, by, bw, bh = b["rect"]
                    overlap = not (ax + aw <= bx or bx + bw <= ax
                                   or ay + ah <= by or by + bh <= ay)
                    assert not overlap, (a["text"], b["text"])
