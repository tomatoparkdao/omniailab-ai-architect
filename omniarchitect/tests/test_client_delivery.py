"""客户交付层：案例图、提案链接、文档包。

这一组测试守的是**对外承诺**，不是实现细节：图能看但不能是偷来的、链接能点、
没连上就不许出现"已发布"的字样。

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import json
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

from omniarchitect.model import Project
from omniarchitect.presentation import html as html_mod
from omniarchitect.presentation import online_doc
from omniarchitect.research import preview as pv

CASE = {
    "title": "Courtyard House in Kyoto",
    "architect": "Studio A",
    "url": "https://www.archdaily.com/123456/courtyard-house-in-kyoto",
    "source": "ArchDaily",
    "discipline": "architecture",
    "image_url": "https://images.example.com/a.jpg",
    "city": "Kyoto", "country": "Japan", "year": "2024", "area": "180 m²",
    "summary": ("The house is organised around an inner courtyard; a reflecting pond "
                "sits at its centre and the entry compresses before opening up."),
    "verify": "verified",
    "verify_label": "已回读核验：页面可打开，标题一致",
}

REF = {
    "title": CASE["title"], "architect": CASE["architect"], "url": CASE["url"],
    "image_url": CASE["image_url"], "verify": "verified",
    "verify_label": "已回读核验：页面可打开，标题一致",
    "why": "它把私密与通透放进同一个动作里",
    "borrow": ["它的入场处理可以对照你的「接近」这一步"],
    "transform": "借组织逻辑，按本项目尺度重排",
    "limits": ["尺寸不能反推"],
}

PAYLOAD = {
    "project_id": "p1", "revision": 1, "lead_discipline": "architecture",
    "lead_label": "建筑", "source": "deliberated",
    "concepts": [{
        "concept_id": "C-A", "concept_name": "院中取院", "role": "A",
        "role_label": "首推 · 证据最强",
        "concept_statement": "先把房子做成一圈墙，再从中间把院挖出来。",
        "spatial_prototype": {"family": "courtyard"},
        "material_direction": [{"name": "微水泥", "application": "地面"}],
        "lighting_direction": ["院给每一层提供侧向漫射光。"],
        "experience_sequence": {"steps": [{"step": "接近", "event": "沿院墙走"}]},
        "deliberation": {
            "key_opportunity": "对外收住，对内全开。",
            "why_this_strategy": ("回应私密：业主原话提到「私密」；回应采光：业主原话提到"
                                  "「采光」；业主原话提到「私密」「采光」；"
                                  "案例中出现同类手法：courtyard（Courtyard House）"),
            "integration": "建筑定体量，室内沿院开，景观把院做成水院。",
            "technical_coordination": "院侧大玻璃的得热与眩光需机电配合。",
            "unverified_requires": ["退界允许围合"],
        },
        "advantages": ["回应了业主自己提出的问题"],
        "tradeoffs": ["外墙周长增加"],
        "references": {"cases": [REF], "note": "参考案例只用于讨论方向"},
        "diagrams": [],
    }],
}


def _project() -> Project:
    p = Project(project_id="p1", name="测试项目")
    p.constraints = {"project_type": "新建三层别墅"}
    p.meta = {"stage_state": {"S1": {"status": "confirmed"},
                              "S2": {"status": "pending"}}}
    return p


# --------------------------------------------------------------------------
# 案例可视化
# --------------------------------------------------------------------------
def test_third_party_case_never_becomes_an_embedded_photo():
    vis = pv.resolve(CASE)
    assert vis["kind"] == "original_plate", vis
    assert vis["rights"] == "own"
    assert "<svg" in vis["svg"]


def test_plate_is_wellformed_and_labelled_as_our_drawing():
    svg = pv.plate(CASE, index=2)
    ET.fromstring(svg)
    assert "非原案例照片" in svg
    assert "REF 02" in svg


def test_techniques_come_from_the_case_text_only():
    tech = pv.techniques(CASE)
    kinds = {t["kind"] for t in tech}
    assert "courtyard" in kinds
    assert "water" in kinds        # 原文是 reflecting pond
    # 案例没写"退台"，就不许出现
    assert "terrace" not in kinds


def test_same_drawing_kind_appears_once():
    case = dict(CASE, summary="A pond and a pool and water everywhere.")
    kinds = [t["kind"] for t in pv.techniques(case)]
    assert kinds.count("water") == 1


def test_no_technique_means_no_invented_technique():
    assert pv.techniques(dict(CASE, title="House", summary="A building.")) == []


def test_credits_need_license_and_source_to_count():
    with tempfile.TemporaryDirectory() as td:
        refs = Path(td) / "references"
        refs.mkdir()
        (refs / "a.jpg").write_bytes(b"\xff\xd8\xff\xe0fake")
        (refs / "credits.json").write_text(json.dumps(
            {"images": [{"url": CASE["url"], "file": "a.jpg", "license": ""}]},
            ensure_ascii=False), encoding="utf-8")
        assert pv.licensed_image(CASE, Path(td)) is None


def test_registered_licensed_photo_is_used_and_credited():
    with tempfile.TemporaryDirectory() as td:
        refs = Path(td) / "references"
        refs.mkdir()
        (refs / "a.jpg").write_bytes(b"\xff\xd8\xff\xe0fake")
        (refs / "credits.json").write_text(json.dumps(
            {"images": [{"url": CASE["url"], "file": "a.jpg", "license": "CC BY 4.0",
                         "author": "摄影师张三",
                         "source_url": "https://example.com/a"}]},
            ensure_ascii=False), encoding="utf-8")
        vis = pv.resolve(CASE, project_dir=Path(td))
        assert vis["kind"] == "licensed_photo"
        assert "CC BY 4.0" in vis["credit"]
        assert "摄影师张三" in vis["credit"]


def test_case_card_has_a_clickable_source_link():
    card = html_mod.case_card(REF, CASE)
    assert f'href="{CASE["url"]}"' in card
    assert "查看原案例" in card
    assert "target=\"_blank\"" in card
    # 未登记授权时，卡上不许出现指向第三方图床的 <img>
    assert "<img" not in card
    assert "images.adsttc" not in card


# --------------------------------------------------------------------------
# 提案
# --------------------------------------------------------------------------
def test_proposal_renders_cards_figures_and_links():
    with tempfile.TemporaryDirectory() as td:
        out = Path(td)
        # 单测不联网：素材库取图是运行时行为，不该让测试依赖它。
        page = html_mod.proposal(PAYLOAD, out, project_name="测试别墅",
                                 research={"cases": [CASE]}, project_dir=out,
                                 with_images=False)
        text = page.read_text(encoding="utf-8")
        assert CASE["url"] in text
        assert "查看原案例" in text
        assert "手法示意" in text
        assert "院中取院" in text
        assert "<svg" in text


def test_proposal_drops_scoring_noise_from_client_text():
    why = html_mod._client_why(
        "回应私密：业主原话提到「私密」；回应采光：业主原话提到「采光」；"
        "业主原话提到「私密」「采光」；业主提出水景，本策略以水面为主体")
    assert "业主原话提到" not in why
    assert why.count("回应") == 1
    assert "水景" in why


# --------------------------------------------------------------------------
# 在线文档包
# --------------------------------------------------------------------------
def _package(td: Path):
    run = td / "run" / "01-brief"
    run.mkdir(parents=True)
    (run / "design-brief.md").write_text(
        "# 设计任务书\n\n## 功能需求\n\n- 三层住宅，含庭院\n", encoding="utf-8")
    return online_doc.build_package(
        _project(), PAYLOAD, {"cases": [CASE]}, td / "online-doc",
        project_name="测试别墅", project_dir=td, run_dir=td / "run")


def test_package_has_five_pages_for_each_carrier():
    with tempfile.TemporaryDirectory() as td:
        pkg = _package(Path(td))
        assert set(pkg["carriers"]) == {"feishu", "notion"}
        for carrier, info in pkg["carriers"].items():
            root = Path(info["root"])
            mds = sorted(p.name for p in root.glob("[0-9][0-9]-*.md"))
            assert len(mds) == 6, (carrier, mds)   # 00 索引 + 5 章
            assert (root / "manifest.json").exists()
            assert Path(info["zip"]).exists()


def test_package_records_sources_and_privacy():
    with tempfile.TemporaryDirectory() as td:
        pkg = _package(Path(td))
        root = Path(pkg["carriers"]["feishu"]["root"])
        man = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
        assert man["sources"] and man["sources"][0]["url"] == CASE["url"]
        assert "不公开" in man["privacy"]
        assert man["publish"] == {"status": "not_connected", "url": None}


def test_reference_page_shows_plate_and_link():
    with tempfile.TemporaryDirectory() as td:
        pkg = _package(Path(td))
        page = Path(pkg["carriers"]["notion"]["root"]) / "02-references.md"
        text = page.read_text(encoding="utf-8")
        assert CASE["url"] in text
        assert "手法示意" in text or "手法" in text
        assert ".svg" in text
        assert "不是原案例照片" in text


def test_publish_without_connector_never_invents_a_url():
    with tempfile.TemporaryDirectory() as td:
        pkg = _package(Path(td))
        root = Path(pkg["carriers"]["feishu"]["root"])
        res = online_doc.publish("feishu", root)
        assert res["status"] == "not_connected"
        assert res["url"] is None
        assert "feishu" in res["reason"].lower() or "飞书" in res["reason"]
        assert not (root / "published.json").exists()


def test_publish_with_connector_writes_the_returned_url_only():
    class Fake:
        def create(self, title, pages):
            assert pages and pages[0][1].startswith("#")
            return {"url": "https://example.feishu.cn/docx/abc"}

    with tempfile.TemporaryDirectory() as td:
        pkg = _package(Path(td))
        root = Path(pkg["carriers"]["feishu"]["root"])
        res = online_doc.publish("feishu", root, client=Fake(), title="测试别墅")
        assert res["status"] == "published"
        assert res["url"] == "https://example.feishu.cn/docx/abc"
        saved = json.loads((root / "published.json").read_text(encoding="utf-8"))
        assert saved["url"] == res["url"]


def test_stage_page_lists_real_artifacts_only():
    with tempfile.TemporaryDirectory() as td:
        pkg = _package(Path(td))
        text = (Path(pkg["carriers"]["feishu"]["root"]) / "04-stages.md"
                ).read_text(encoding="utf-8")
        assert "S1" in text and "已确认" in text
        assert "S8" in text
        # S3 以后没有产物，不许写成"有"
        assert "S7 | CAD / BIM 施工图深化 | 未开始" in text
