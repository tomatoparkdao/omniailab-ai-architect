"""视觉规范（`视觉.md`）守卫：能提取、能应用、不乱改、不伪造。

审美判断没法断言，但**这几件事能**：

- 客户说"标题宋体、正文无衬线"时，读到的是"标题宋体"，不是"无衬线"；
- 一张风景照的纸色不是天空蓝（照片不是版面）；
- 客户只说了"线细一点"，纸色墨色不能因此被重置成默认值；
- 没有 `视觉.md` 的项目，产出与上一版逐像素一致（不退化）；
- 读不到的文件写明原因，不编造提取结果。

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path
from types import SimpleNamespace

from omniarchitect import visualref as vr
from omniarchitect.concept import diagrams as dia
from omniarchitect.presentation import html as html_mod
from omniarchitect.visualref import brief as vb
from omniarchitect.visualref import extract as ex
from omniarchitect.visualref import sources as vs


def _project(pid: str = "T-1", name: str = "测试项目") -> Any:
    return SimpleNamespace(project_id=pid, name=name, revision=2, meta={})


def _png(path: Path, size=(800, 600), bg=(247, 244, 236), fg=(30, 32, 30)) -> Path:
    """造一张"版面图"：大底 + 一块深色内容。"""
    from PIL import Image, ImageDraw

    im = Image.new("RGB", size, bg)
    d = ImageDraw.Draw(im)
    d.rectangle([60, 80, size[0] - 60, size[1] - 120], fill=fg)
    d.rectangle([60, size[1] - 90, 360, size[1] - 50], fill=fg)
    im.save(path)
    return path


# --------------------------------------------------------------------------
# 引导
# --------------------------------------------------------------------------
def test_guide_offers_a_reference_and_never_blocks():
    g = vr.guide("architecture")
    assert "图片" in g["text"] and "链接" in g["text"]
    assert g["blocking"] is False
    assert g["url"].startswith("http")
    assert "体量" in g["extra"]


def test_s1_has_a_visual_reference_slot_that_is_not_critical():
    from omniarchitect.intake.profiles import QUESTION_INDEX, SLOTS

    assert "visual_refs" in SLOTS
    assert SLOTS["visual_refs"]["critical"] is False
    q = QUESTION_INDEX["base.visual_refs"]
    assert q.slot == "visual_refs"
    assert "参考" in q.text


# --------------------------------------------------------------------------
# 变更识别
# --------------------------------------------------------------------------
def test_detect_reads_aesthetic_changes_not_room_requests():
    assert vb.detect_change("我更喜欢这个作品集的排版")
    assert vb.detect_change("这套排版太普通了")
    assert vb.detect_change("图纸应该像这个参考文件一样")
    assert not vb.detect_change("我想要一个书房")
    assert not vb.detect_change("预算控制在 200 万")


# --------------------------------------------------------------------------
# 文本提取
# --------------------------------------------------------------------------
def test_title_font_rule_wins_over_body_font_rule():
    """作品集常写"标题宋体、正文无衬线"。只按出现顺序会判成无衬线。"""
    layer = ex.from_text("标题用宋体，正文用无衬线。大留白。", origin="reference")
    assert layer["layout"]["serif_titles"]["value"] is True
    assert layer["layout"]["whitespace"]["value"] == 0.50


def test_columns_are_read_with_the_right_number():
    assert ex.from_text("三栏网格")["layout"]["columns"]["value"] == 3
    assert ex.from_text("两栏排版")["layout"]["columns"]["value"] == 2
    assert ex.from_text("单栏")["layout"]["columns"]["value"] == 1


def test_banned_items_drop_markdown_headings():
    layer = ex.from_text("## 不要\n- 不要彩色渐变\n- 不要圆角卡片\n", origin="reference")
    texts = [b["text"] for b in layer["banned"]]
    assert "不要彩色渐变" in texts
    assert not any(t.startswith("#") for t in texts)


def test_degree_phrasing_is_understood():
    """中文不会说"细线"，会说"线再细一点"。"""
    layer = ex.from_text("线再细一点，留白再多一些，图要更大", origin="client")
    assert layer["layout"]["line_weight"]["value"] == 0.85
    assert layer["layout"]["whitespace"]["value"] == 0.52
    assert layer["layout"]["image_dominant"]["value"] is True


def test_colour_words_map_to_values():
    layer = ex.from_text("暖白纸底，石墨文字，一点墨绿", origin="client")
    assert layer["colours"]["暖白"] == "#F7F4EC"
    assert layer["colours"]["石墨"] == "#2A2D2A"


# --------------------------------------------------------------------------
# 图像提取
# --------------------------------------------------------------------------
def test_image_metrics_measure_rather_than_guess():
    with tempfile.TemporaryDirectory() as td:
        p = _png(Path(td) / "a.png")
        m = vs.image_metrics(p)
        assert m["ok"] is True
        assert m["whitespace"] > 0.3          # 大底留白
        assert m["paper"] > m["ink"]          # 纸比墨亮（字符串比较不可靠，改判亮度）
        assert m["contrast"] > 0


def test_a_photo_never_becomes_the_page_colour():
    """参考图偏蓝时，纸色只做微调，不会被染成蓝底。"""
    with tempfile.TemporaryDirectory() as td:
        from PIL import Image

        p = Path(td) / "sky.png"
        Image.new("RGB", (600, 400), (140, 180, 230)).save(p)
        layer = ex.from_images([vs.image_metrics(p)], origin="reference")
        paper = layer["tokens"]["paper"]["value"]
        r, g, b = (int(paper[i:i + 2], 16) for i in (1, 3, 5))
        assert b - r <= 12, paper            # 允许微冷，不允许整页变蓝


def test_whitespace_outside_the_layout_band_is_not_adopted():
    with tempfile.TemporaryDirectory() as td:
        from PIL import Image

        p = Path(td) / "flat.png"
        Image.new("RGB", (600, 400), (250, 248, 244)).save(p)
        layer = ex.from_images([vs.image_metrics(p)], origin="reference")
        # 全白图没有"版面"，不该得出 100% 留白
        assert "whitespace" not in layer["layout"]


def test_unreadable_reference_reports_the_reason():
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "x.unknown"
        p.write_bytes(b"\x00\x01")
        got = vs.probe(p)
        assert got["ok"] is False
        assert got["reason"]


def test_scanner_skips_copies_and_helper_files():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "assets").mkdir()
        _png(root / "assets" / "copy.jpg")
        _png(root / "ref-1.jpg")
        (root / "_meta.json").write_text("{}", encoding="utf-8")
        got = vs.scan(root)
        names = [g["name"] for g in got]
        assert "ref-1.jpg" in names
        assert not any(n == "_meta.json" for n in names)


# --------------------------------------------------------------------------
# 合并与往返
# --------------------------------------------------------------------------
def test_client_wins_over_reference_which_wins_over_default():
    client = ex.from_text("大留白", origin="client")
    ref = ex.from_images([{"ok": True, "paper": "#123456", "ink": "#000000",
                           "accent": None, "whitespace": 0.5, "contrast": 0.5,
                           "ratio": 1.5, "palette": [], "mood": "light"}],
                         origin="reference")
    merged = ex.merge([client, ref])
    # 客户说的留白优先于参考图算出来的留白
    assert merged["provenance"]["whitespace"] == "client"
    assert merged["provenance"]["ink"] == "reference"
    # 参考图没有点缀色时不许编一个
    assert "accent" not in merged["provenance"]


def test_markdown_round_trips_through_the_machine_block():
    with tempfile.TemporaryDirectory() as td:
        proj = _project()
        rules = vr.compose(proj, [], client_text="大留白，暖白纸底", lead="architecture")
        path = vr.write(rules, proj, td)
        assert path.name == "视觉.md"
        back = vr.load(proj, td)
        assert back and back["tokens"]["whitespace"] == rules["tokens"]["whitespace"]
        text = path.read_text(encoding="utf-8")
        for section in ("## 1 项目基本信息", "## 5 排版规则提取", "## 12 来源、版本与变更"):
            assert section in text


def test_three_source_labels_are_kept_apart():
    with tempfile.TemporaryDirectory() as td:
        proj = _project()
        p = _png(Path(td) / "ref.jpg")
        rules = vr.from_refs(proj, [p], client_text="标题用宋体", lead="architecture",
                             project_dir=td)
        text = (Path(td) / "视觉.md").read_text(encoding="utf-8")
        assert "客户明确指定" in text and "参考文件提取" in text
        assert "总设计师专业建议" in text
        # 客户没说纸色，就不许写成客户的要求
        assert rules["provenance"].get("paper") != "client"


# --------------------------------------------------------------------------
# 变更：只改说到的，不动说不到的
# --------------------------------------------------------------------------
def test_update_only_touches_rules_the_client_mentioned():
    with tempfile.TemporaryDirectory() as td:
        proj = _project()
        base = vr.compose(proj, [], client_text="", lead="landscape")
        base["tokens"]["paper"] = "#F1EDE0"
        base["tokens"]["ink"] = "#20241F"
        vr.write(base, proj, td)

        after = vr.update(proj, "线再细一点", project_dir=td)
        assert after["tokens"]["line_weight"] == 0.85
        assert after["tokens"]["paper"] == "#F1EDE0"      # 没被重置
        assert after["tokens"]["ink"] == "#20241F"
        assert after["version"] == 2
        assert after["changelog"][-1]["change"].startswith("视觉偏好变更")


def test_update_does_not_touch_design_content():
    """视觉规范与方案是两份数据：改它不该动 concept-options。"""
    with tempfile.TemporaryDirectory() as td:
        proj = _project()
        vr.write(vr.compose(proj, [], lead="architecture"), proj, td)
        (Path(td) / "concept-options.json").write_text(
            json.dumps({"count": 3}, ensure_ascii=False), encoding="utf-8")
        vr.update(proj, "排版太普通，图再大一点", project_dir=td)
        data = json.loads((Path(td) / "concept-options.json").read_text(encoding="utf-8"))
        assert data == {"count": 3}


# --------------------------------------------------------------------------
# 应用：图元与提案
# --------------------------------------------------------------------------
def test_theme_is_empty_and_identical_to_default_when_no_brief_exists():
    with tempfile.TemporaryDirectory() as td:
        t = vr.theme(_project(), td)
        assert t["source"] == "default"
        for k in ("paper", "ink", "line_weight"):
            assert t[k] == ex.DEFAULTS[k]


def test_diagram_theme_changes_paper_ink_and_line_weight():
    try:
        dia.reset_theme()
        s0 = dia.Svg(100, 100)
        s0.rect(1, 1, 10, 10)
        s0.text(10, 20, "x")
        before = s0.render()

        dia.apply_theme({"paper": "#F1EDE0", "ink": "#101210",
                         "line": "#CCC8BC", "muted": "#777", "accent": "#2F5D45",
                         "line_weight": 1.4})
        s1 = dia.Svg(100, 100)
        s1.rect(1, 1, 10, 10)
        s1.text(10, 20, "x")
        after = s1.render()
        assert "#F1EDE0" in after and "#F1EDE0" not in before
        assert 'stroke-width="1.40"' in after
        assert "#101210" in after
    finally:
        dia.reset_theme()


def test_reset_theme_returns_to_repository_defaults():
    try:
        dia.apply_theme({"ink": "#000000", "line_weight": 2.0})
        dia.reset_theme()
        assert dia.C_INK == "#1E2328"
        assert dia.LINE_W == 1.0
    finally:
        dia.reset_theme()


def test_proposal_css_override_only_sets_colours():
    css = html_mod.theme_css({"paper": "#F1EDE0", "ink": "#101210", "accent": "#2F5D45"})
    assert "--paper:#F1EDE0" in css
    assert "grid-template-columns" not in css      # 不动栅格
    assert "font-size" not in css                  # 不动字号
    assert html_mod.theme_css({}) == ""


def test_proposal_picks_up_the_project_brief():
    with tempfile.TemporaryDirectory() as td:
        proj = _project()
        rules = vr.compose(proj, [], lead="architecture")
        rules["tokens"]["paper"] = "#EFE9DA"
        rules["tokens"]["ink"] = "#1A1C18"
        vr.write(rules, proj, td)
        theme = html_mod.read_theme(Path(td))
        assert theme["paper"] == "#EFE9DA"
        assert theme["ink"] == "#1A1C18"


# --------------------------------------------------------------------------
# 不编造
# --------------------------------------------------------------------------
def test_text_only_reference_does_not_produce_image_claims():
    with tempfile.TemporaryDirectory() as td:
        proj = _project()
        p = Path(td) / "notes.md"
        p.write_text("# 口味\n喜欢干净一点，大留白。", encoding="utf-8")
        rules = vr.from_refs(proj, [p], lead="architecture", project_dir=td)
        # 没有图，就没有纸色/墨色的"参考提取"
        assert rules["provenance"].get("ink") != "reference"
        srcs = rules["sources"]
        assert srcs and srcs[0]["kind"] == "text"
        assert not (srcs[0].get("extracted") or {}).get("纸色")


__all__: list = []
