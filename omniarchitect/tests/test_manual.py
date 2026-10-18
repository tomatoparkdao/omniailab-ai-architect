"""操作手册：可被技能调用（离线可读、主题可定位、出错点会提醒）。

用户要求「操作过程中遇到不会的都要提醒去参考操作手册，并且手册要能被技能调用」。
这个模块就是那套机制的落点，所以这些断言必须一直在。

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from omniarchitect import manual as M  # noqa: E402
from omniarchitect.paths import ROOT  # noqa: E402


def test_manual_exists_locally_and_is_readable_offline():
    p = M.manual_path()
    assert p is not None, "手册必须随 Skill 一起分发，才能在断网时被读"
    text = p.read_text(encoding="utf-8")
    assert len(text.splitlines()) > 200, "手册不能是占位文件"
    assert "# 建筑与室内设计 Skill 操作手册" in text


def test_manual_carries_the_eight_field_frontmatter():
    """手册自身也遵守八项 front-matter，其中后两项正好是仓库与手册地址。"""
    text = (ROOT / M.MANUAL_LOCAL).read_text(encoding="utf-8")
    assert text.startswith("---")
    fm = text.split("---", 2)[1]
    for key in ("name", "description", "version", "author", "developer",
                "agent_created", "开源仓库", "操作手册"):
        assert f"{key}:" in fm, key
    assert M.REPO in fm
    assert M.MANUAL_CN in fm


def test_three_locations_are_registered_and_consistent():
    assert M.MANUAL_CN.startswith("https://")
    assert M.MANUAL_NOTION.startswith("https://")
    assert M.REPO.startswith("https://")
    # 手册里必须同时给出三处，读者任一入口都能拿到其余两处
    text = (ROOT / M.MANUAL_LOCAL).read_text(encoding="utf-8")
    for url in (M.MANUAL_CN, M.MANUAL_NOTION, M.REPO):
        assert url in text, url


def test_repository_url_is_in_every_markdown_frontmatter():
    """front-matter 的「开源仓库」必须是真的地址，不能再是「待发布」。"""
    missing = []
    for p in sorted(ROOT.rglob("*.md")):
        rel = str(p.relative_to(ROOT)).replace("\\", "/")
        if rel.startswith(("out/", "projects/")) or rel in ("README.md", "README_EN.md"):
            continue
        fm = p.read_text(encoding="utf-8").split("---", 2)
        if len(fm) < 3:
            continue
        if M.REPO not in fm[1]:
            missing.append(rel)
    assert not missing, missing


def test_every_topic_maps_to_a_section_that_really_exists():
    """主题表不能指向不存在的章节——否则「去查手册」会指向空气。"""
    text = (ROOT / M.MANUAL_LOCAL).read_text(encoding="utf-8")
    headings = [ln.strip() for ln in text.splitlines() if ln.startswith("#")]
    bad = []
    for topic, section in M.topics().items():
        # 章节号（如 "12." 或 "5.4"）必须能在手册标题里找到
        num = section.split(" ")[0]
        if not any(h.startswith("#") and num in h for h in headings):
            bad.append(f"{topic} -> {section}")
    assert not bad, bad


def test_the_section_title_still_says_what_the_topic_means():
    """章节号对上还不够：编号对了而标题被改掉，指过去照样是错的。

    这里比的是标题正文（去掉编号后的部分），避免只靠 "6.2" 这种编号蒙对。
    """
    text = (ROOT / M.MANUAL_LOCAL).read_text(encoding="utf-8")
    headings = [ln.strip() for ln in text.splitlines() if ln.startswith("#")]
    bad = []
    for topic, section in M.topics().items():
        num, _, title = section.partition(" ")
        if not title:
            continue
        if not any(h.startswith("#") and num in h and title in h for h in headings):
            bad.append(f"{topic} -> {section}")
    assert not bad, bad


def test_hint_names_the_section_and_the_manual():
    h = M.hint("degraded")
    assert "操作手册" in h
    assert M.section_of("degraded") in h
    # 未登记的主题也要有兜底，不能抛错
    assert M.section_of("不存在的主题") == M.SECTIONS["pitfalls"]


def test_pointer_lists_all_three_entries():
    txt = M.pointer("platform")
    assert M.MANUAL_LOCAL in txt
    assert M.MANUAL_CN in txt
    assert M.MANUAL_NOTION in txt
    assert M.REPO in txt


def test_cli_manual_command_reads_a_section_offline(capsys=None):
    from omniarchitect.cli import build_parser

    args = build_parser().parse_args(["manual", "--read", "--section", "避坑总表"])
    assert args.read is True
    assert "避坑" in args.section


def test_cli_manual_topic_and_json_modes_are_wired():
    from omniarchitect.cli import build_parser

    a = build_parser().parse_args(["manual", "--topic", "platform"])
    assert a.topic == "platform"
    b = build_parser().parse_args(["manual", "--json"])
    assert b.json is True


def test_render_help_advertises_the_manual():
    """`--help` 里就要能看到手册，否则用户永远不知道有手册。"""
    from omniarchitect.cli import build_parser

    help_text = build_parser().format_help()
    assert "操作手册" in help_text
    assert M.MANUAL_CN in help_text
    assert M.REPO in help_text
