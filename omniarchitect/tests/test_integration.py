"""Agent Skills compatibility, installer safety, and third-party auditing.

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from omniarchitect import compliance_audit as ca  # noqa: E402
from omniarchitect.integration import agent_skills as sk  # noqa: E402
from omniarchitect.integration import installer as inst  # noqa: E402
from omniarchitect.paths import ROOT  # noqa: E402

# 全仓文档扫描统一跳过的目录：运行时产物、用户项目数据与工具缓存。
# `.pytest_cache/` 是真实踩过的坑——pytest 会在里面写一个 README.md，
# 既没有 front-matter 也没有本仓署名，不跳过就会让格式类测试无故失败。
SCAN_SKIP_PREFIXES = ("out/", "projects/", ".git/", ".pytest_cache/",
                      "__pycache__/", "_backup/", ".venv/", "node_modules/")


# --------------------------------------------------------------------------
# SKILL.md contract
# --------------------------------------------------------------------------
def test_skill_md_parses_and_validates():
    m = sk.parse()
    assert m.name == "omniailab-ai-architect"
    assert sk.NAME_RE.match(m.name)
    assert m.description and len(m.description) <= 1024
    assert m.version
    assert sk.validate() == [], sk.validate()


def test_skill_md_stays_small_enough_for_progressive_disclosure():
    m = sk.parse()
    assert m.lines <= 400, m.lines
    assert m.bytes_ <= 24000, m.bytes_


def test_every_relative_reference_in_skill_md_exists():
    m = sk.parse()
    refs = m.references + m.soft_references
    assert refs, "SKILL.md 必须指向它的载荷文件"
    top = {p.name for p in ROOT.iterdir()}
    for ref in refs:
        if ref.split("/")[0] not in top:
            continue            # 用户自备路径
        assert (ROOT / ref).exists(), ref


def test_invalid_skill_md_is_rejected():
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "SKILL.md"
        p.write_text("---\nname: Bad_Name\ndescription: x\n---\n# t\n", encoding="utf-8")
        issues = sk.validate(p)
        assert any("name" in i for i in issues)
        assert any("version" in i for i in issues)


def test_manifest_declares_standalone_operation():
    data = sk.build_manifest()
    assert data["standalone"]["requires_platform_account"] is False
    assert data["standalone"]["requires_network"] is False
    assert data["standalone"]["hard_dependencies"] == []
    assert data["file_count"] > 50
    assert data["issues"] == []


def test_runtime_detection_reports_presence_without_installing():
    rep = sk.detect_runtimes()
    assert rep
    for info in rep.values():
        assert "present" in info and "installed" in info
        assert isinstance(info["present"], bool)


def test_installer_never_deletes_an_existing_installation():
    with tempfile.TemporaryDirectory() as td:
        target = Path(td) / "skills"
        ins = inst.Installer(source=ROOT, target=target)
        first = ins.install()
        assert first.verification["ok"], first.verification
        marker = Path(first.target) / "SKILL.md"
        assert marker.exists()

        second = ins.install()                    # 重复安装
        assert second.backed_up, "重复安装必须先备份"
        for b in second.backed_up:
            assert Path(b).exists(), "备份必须真实存在"
            assert (Path(b) / "SKILL.md").exists()
        assert second.verification["ok"]


def test_dry_run_writes_nothing():
    with tempfile.TemporaryDirectory() as td:
        target = Path(td) / "skills"
        rep = inst.Installer(source=ROOT, target=target).install(dry_run=True)
        assert rep.dry_run is True
        assert rep.actions
        assert not target.exists(), "试运行不得创建任何目录"


def test_copy_mode_carries_the_payload_and_pointer_mode_does_not():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        ptr = inst.Installer(source=ROOT, target=root / "p").install()
        cp = inst.Installer(source=ROOT, target=root / "c",
                            mode=inst.MODE_COPY).install()
        assert (Path(ptr.target) / inst.POINTER_NAME).exists()
        assert not (Path(ptr.target) / "knowledge").exists()
        assert (Path(cp.target) / "knowledge" / "INDEX.md").exists()
        assert (Path(cp.target) / "omniarchitect" / "model.py").exists()


def test_installer_refuses_when_no_runtime_is_found():
    with tempfile.TemporaryDirectory() as td:
        empty_home = Path(td) / "home"
        empty_home.mkdir()
        import os

        old = os.environ.get("HOME")
        os.environ["HOME"] = str(empty_home)
        try:
            ins = inst.Installer(source=ROOT, target=None)
            ins.source = ROOT
            ins.target = None
            try:
                ins.resolve_target(project_dir=Path(td))
            except RuntimeError as exc:
                assert "未检测到" in str(exc) or "--target" in str(exc)
        finally:
            if old is None:
                os.environ.pop("HOME", None)
            else:
                os.environ["HOME"] = old


def test_verify_install_detects_a_broken_pointer():
    with tempfile.TemporaryDirectory() as td:
        target = Path(td) / "skills"
        rep = inst.Installer(source=ROOT, target=target).install()
        assert inst.verify(rep.target)["ok"]
        (Path(rep.target) / inst.POINTER_NAME).write_text(str(Path(td) / "gone"),
                                                          encoding="utf-8")
        bad = inst.verify(rep.target)
        assert bad["ok"] is False
        assert any("不存在" in e for e in bad["errors"])


def test_uninstall_moves_rather_than_deletes():
    with tempfile.TemporaryDirectory() as td:
        target = Path(td) / "skills"
        rep = inst.Installer(source=ROOT, target=target).install()
        res = inst.Installer(source=ROOT, target=target).uninstall()
        assert res["removed"] is True
        assert not Path(rep.target).exists()
        moved = Path(res["moved_to"])
        assert moved.exists() and (moved / "SKILL.md").exists()


def test_compatibility_report_is_machine_readable():
    rep = sk.compatibility_report()
    assert rep["skill"] == "omniailab-ai-architect"
    assert rep["progressive_disclosure"] is True
    assert rep["issues"] == []
    assert "standalone" in rep["modes"]


# --------------------------------------------------------------------------
# content audit
# --------------------------------------------------------------------------
def test_audit_scan_is_clean_and_reports_a_reason():
    rep = ca.scan(ROOT)
    assert rep["files_scanned"] > 100
    assert rep["action_count"] == 0, [f["path"] for f in rep["needs_action"]]
    assert rep["conclusion"]


def test_every_document_carries_the_omniailab_signature():
    from omniarchitect.registry import (
        SIGNATURE,
        SIGNATURE_SHORT,
        SIGNATURE_SHORT_EN,
    )

    missing = []
    for p in sorted(ROOT.rglob("*.md")):
        rel = str(p.relative_to(ROOT)).replace("\\", "/")
        if rel.startswith(SCAN_SKIP_PREFIXES):
            continue
        text = p.read_text(encoding="utf-8")
        if not any(mark in text for mark in
                   (SIGNATURE, SIGNATURE_SHORT, SIGNATURE_SHORT_EN)):
            missing.append(rel)
    assert not missing, f"缺少署名：{missing}"


def test_no_borrowed_branding_anywhere_in_the_tree():
    # These strings must not appear anywhere: the material is our own.
    banned = ("arch-skills", "gujun", "gu jun", "chodo", "顾俊")
    offenders = []
    for p in sorted(ROOT.rglob("*")):
        if p.is_dir() or p.suffix.lower() not in (".md", ".py", ".json", ".yaml",
                                                  ".yml", ".toml", ".txt"):
            continue
        rel = str(p.relative_to(ROOT)).replace("\\", "/")
        if rel.startswith(("out/", "projects/", "omniarchitect/tests/")):
            continue        # the test file itself must name the banned strings
        low = p.read_text(encoding="utf-8", errors="replace").lower()
        for b in banned:
            if b in low:
                offenders.append(f"{rel}: {b}")
    assert not offenders, offenders


def test_user_facing_files_carry_no_external_promotion():
    from omniarchitect import compliance_audit as _ca

    for rel in ("SKILL.md", "README.md", "README_EN.md"):
        text = (ROOT / rel).read_text(encoding="utf-8")
        urls = _ca.PATTERNS["url"].findall(text)
        for u in urls:
            assert (any(d in u for d in _ca.OWN_DOMAINS)
                    or any(u.startswith(p) for p in _ca.OWN_URL_PREFIXES)
                    or any(h in u for h in _ca.BENIGN_URL_HOSTS)), f"{rel}: {u}"


def test_a_user_facing_file_with_external_promotion_is_flagged():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "knowledge").mkdir()
        (root / "knowledge" / "x.md").write_text(
            "更多内容见 https://example-shop.example.com/sale 与 https://promo.example.net\n\n"
            "---\n" + ca.SIGNATURE + "\n", encoding="utf-8")
        rep = ca.scan(root)
        assert rep["action_count"] == 1
        f = rep["needs_action"][0]
        assert f["disposition"] == "user-facing-external-link"


def test_a_document_without_the_signature_is_flagged():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "docs").mkdir()
        (root / "docs" / "note.md").write_text("# 说明\n\n没有署名的文档。", encoding="utf-8")
        rep = ca.scan(root)
        assert rep["action_count"] == 1
        assert rep["needs_action"][0]["disposition"] == "missing-signature"


def test_hex_digests_are_not_mistaken_for_phone_numbers():
    """sha256 摘要里的一段十六进制曾被误判为手机号（真实踩到过的误报）。"""
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "installer").mkdir()
        (root / "installer" / "manifest.json").write_text(
            '{\n  "files": [{"path": "pyproject.toml", "size": 2161,\n'
            '              "sha256_16": "797f14446326125d"}]\n}\n', encoding="utf-8")
        rep = ca.scan(root)
        assert rep["action_count"] == 0, rep["needs_action"]


def test_real_phone_numbers_are_still_caught():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "notes.md").write_text(
            "手机：13800138000\n座机 010-88886666\n", encoding="utf-8")
        rep = ca.scan(root)
        assert rep["needs_action"][0]["disposition"] == "review-privacy"
        assert "cn_phone" in rep["needs_action"][0]["hits"]


def test_the_scanners_own_output_does_not_flag_itself():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "docs").mkdir()
        # 模拟上一轮报告里记录过一个手机号：不得因此自我循环
        (root / "docs" / "content-audit.json").write_text(
            '{"hits": {"cn_phone": ["13800138000"]}}', encoding="utf-8")
        rep = ca.scan(root)
        assert rep["action_count"] == 0, rep["needs_action"]
        f = [x for x in rep["by_disposition"].items()]
        assert dict(f).get("generated-ok") == 1


def test_client_names_and_emails_are_flagged_for_redaction():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "notes.md").write_text(
            "业主：张三\n联系 someone@example.com\n手机 13800138000\n", encoding="utf-8")
        rep = ca.scan(root)
        f = rep["needs_action"][0]
        assert f["disposition"] == "review-privacy"
        assert "client_name" in f["hits"] or "email" in f["hits"]


def test_role_words_are_not_mistaken_for_client_names():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "spec.md").write_text(
            "业主：确认后进入下一阶段\n甲方：主创团队\n客户：设计方\n\n"
            "---\n" + ca.SIGNATURE + "\n", encoding="utf-8")
        rep = ca.scan(root)
        assert rep["action_count"] == 0, rep["needs_action"]


def test_report_rendering_and_writing():
    with tempfile.TemporaryDirectory() as td:
        rep = ca.scan(ROOT)
        md = ca.render_markdown(rep)
        assert "# 内容合规自检报告" in md
        assert "署名与归属" in md
        assert ca.SIGNATURE in md
        out = ca.write_report(td)
        for key in ("markdown", "json"):
            assert Path(out[key]).exists()
        data = json.loads(Path(out["json"]).read_text(encoding="utf-8"))
        assert data["files_scanned"] == rep["files_scanned"]


def test_spec_namespaces_are_not_treated_as_promotional_links():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "SKILL.md").write_text(
            "---\nname: x\ndescription: d\nversion: 1\n---\n"
            "XML: http://schemas.openxmlformats.org/xxx and https://purl.org/dc\n\n"
            "---\n" + ca.SIGNATURE + "\n", encoding="utf-8")
        rep = ca.scan(root)
        assert rep["action_count"] == 0, rep["needs_action"]


# --------------------------------------------------------------------------
# unified header / footer format
# --------------------------------------------------------------------------
def _normalizer():
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "normalize_attribution", ROOT / "scripts" / "normalize_attribution.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)          # type: ignore[union-attr]
    return mod


def test_every_file_already_matches_the_unified_format():
    """全仓「开头 + 结尾」格式已经统一；任何漂移都会在这里失败。"""
    mod = _normalizer()
    rep = mod.run(check=True, root=ROOT)
    assert rep["changed_count"] == 0, rep["changed"]
    assert rep["total"] > 100


def test_the_normalizer_is_idempotent():
    mod = _normalizer()
    first = mod.run(check=True, root=ROOT)
    second = mod.run(check=True, root=ROOT)
    assert first["changed_count"] == second["changed_count"] == 0


def test_frontmatter_tail_is_identical_in_every_markdown():
    from omniarchitect.registry import FRONTMATTER_TAIL
    from omniarchitect.paths import project_version

    version = project_version()
    # README 是 GitHub 首页：按参考仓库做法不带 front-matter（见 normalize_attribution）
    no_fm = ("README.md", "README_EN.md")
    bad = []
    for p in sorted(ROOT.rglob("*.md")):
        rel = str(p.relative_to(ROOT)).replace("\\", "/")
        if rel in no_fm or rel.startswith(SCAN_SKIP_PREFIXES):
            continue
        text = p.read_text(encoding="utf-8")
        assert text.startswith("---"), rel
        fm = text.split("---", 2)[1]
        for key, value in [("version", version), *FRONTMATTER_TAIL]:
            if f"{key}: {value}" not in fm:
                bad.append(f"{rel}: {key}")
    assert not bad, bad


def test_readme_carries_no_frontmatter_and_links_repo_and_manual():
    """README 按参考仓库做法不带元数据，但必须带仓库地址与手册地址。"""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "normalize_attribution", ROOT / "scripts" / "normalize_attribution.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)          # type: ignore[union-attr]

    for rel in ("README.md", "README_EN.md"):
        text = (ROOT / rel).read_text(encoding="utf-8")
        assert not text.startswith("---"), f"{rel} 不应有 front-matter"
        assert mod.OPEN_REPO_URL in text, f"{rel} 缺少仓库地址"
        assert mod.MANUAL_CN_URL in text or mod.MANUAL_NOTION_URL in text, \
            f"{rel} 缺少操作手册地址"


def test_readme_install_table_lists_tools_in_the_reference_order():
    """安装表里的工具与排序必须与参考仓库 omniailab-ai-director 一致。

    顺序：Codex（推荐主用）→ Claude / Claude Code → WorkBuddy → OmniAiLab。
    这份顺序是给第一次用的人的引导路径，漂移了就等于换了一套上手方式。
    """
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    i = text.index("### 一、装到哪")
    j = text.index("### 二、")
    block = text[i:j]
    want = ["**Codex**", "**Claude", "**WorkBuddy**", "**OmniAiLab**"]
    positions = [block.index(tok) for tok in want]
    assert positions == sorted(positions), "安装表工具顺序须为 Codex → Claude → WorkBuddy → OmniAiLab"
    assert "克隆安装（推荐）" in block, "安装表后必须给出克隆安装（推荐）"


def test_readme_guides_the_first_time_user_through_five_steps():
    """快速开始必须是给小白看的五步，且含「你只需要回答两种话」的引导。"""
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    for heading in ("### 一、装到哪：按你用的工具",
                    "### 二、资料从哪来（三选一）",
                    "### 三、启动指令",
                    "### 四、启动前必须想清楚的两件事",
                    "### 五、全程你只需要回答两种话"):
        assert heading in text, f"快速开始缺少小节：{heading}"


def test_generated_reports_carry_the_same_header_and_footer():
    from omniarchitect.paths import project_version

    with tempfile.TemporaryDirectory() as td:
        out = ca.write_report(td)
        md = Path(out["markdown"]).read_text(encoding="utf-8")
    assert md.startswith("---")
    assert f"version: {project_version()}" in md.split("---", 2)[1]
    assert "author: OmniAiLab" in md
    assert "developer: Mochiball" in md
    assert ca.SIGNATURE in md


def test_every_python_module_carries_the_attribution():
    missing = []
    for p in sorted(ROOT.rglob("*.py")):
        rel = str(p.relative_to(ROOT)).replace("\\", "/")
        if rel.startswith(("out/", "projects/")):
            continue
        if "© OmniAiLab" not in p.read_text(encoding="utf-8", errors="replace"):
            missing.append(rel)
    assert not missing, missing


def test_shebang_scripts_keep_their_shebang_first():
    for rel in ("scripts/run_tests.py", "scripts/verify_all.py",
                "scripts/normalize_attribution.py"):
        first = (ROOT / rel).read_text(encoding="utf-8").splitlines()[0]
        assert first.startswith("#!"), f"{rel}: {first!r}"


# --------------------------------------------------------------------------
# The version is declared in seven places. It is also machine-read.
# `openai.yaml` carries the version at the end of `display_name` rather than in
# its own field — that is the shape the reference skill (omniailab-ai-director)
# uses, and the shape the user signed off on. The test matches it rather than
# "fixing" it into a different structure.
VERSION_DECLARATIONS = (
    ("VERSION", "{v}"),
    ("pyproject.toml", 'version = "{v}"'),
    ("SKILL.md", "version: {v}"),
    ("installer/manifest.json", '"version": "{v}"'),
    ("openai.yaml", ' {v}"'),
    ("README.md", "v{v}"),
    ("README_EN.md", "v{v}"),
)


def test_version_file_holds_only_the_version_number():
    """`VERSION` is read by machines, so it may not carry a human signature.

    This file once picked up the standard footer during a whole-repo
    normalisation pass. `project_version()` reads the first line, so every
    check still passed — which is precisely why it survived two rounds of
    audits. A strict parser (`cat VERSION`, a packaging script) would not be so
    forgiving, so the file is now pinned to exactly one line.
    """
    import re
    from omniarchitect.paths import project_version

    raw = (ROOT / "VERSION").read_text(encoding="utf-8")
    lines = [line.strip() for line in raw.splitlines() if line.strip()]
    assert len(lines) == 1, f"VERSION 应只有一行版本号，实际 {len(lines)} 行：{lines}"
    assert re.fullmatch(r"\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.\-]+)?", lines[0]), lines[0]
    assert project_version() == lines[0]
    assert "OmniAiLab" not in raw, "VERSION 是机器读取文件，不得含署名注释"
    assert "#" not in raw, "VERSION 不得含注释"


def test_version_agrees_across_every_declaration():
    """Seven places name the version. Silent disagreement ships a wrong number."""
    from omniarchitect.paths import project_version

    v = project_version()
    problems = []
    for rel, template in VERSION_DECLARATIONS:
        path = ROOT / rel
        if not path.exists():
            problems.append(f"{rel}: 文件不存在")
            continue
        needle = template.format(v=v)
        if needle not in path.read_text(encoding="utf-8"):
            problems.append(f"{rel}: 未找到 {needle!r}")
    assert not problems, problems


# --------------------------------------------------------------------------
# Markdown table spec (docs/TABLES.md)
# --------------------------------------------------------------------------
def _table_checker():
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "check_tables", ROOT / "scripts" / "check_tables.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)          # type: ignore[union-attr]
    return mod


def test_every_table_follows_the_table_spec():
    """表格规范（docs/TABLES.md）：列数一致、无空格、紧凑分隔行、落地页撑满正文区。

    GitHub 的表格宽度由内容撑开，源码无法指定宽度——所以「左右对齐」只能靠
    内容宽度达标来保证。这条测试就是那个判据，不允许随内容改动悄悄退化。
    """
    mod = _table_checker()
    report = mod.run(root=ROOT)
    assert report["count"] == 0, [
        f'{v["rule"]} {v["path"]}:{v["line"]} {v["detail"]}'
        for v in report["violations"]
    ]
    assert report["files"] > 50, report["files"]
    assert report["tables"] > 100, report["tables"]


def test_landing_page_tables_are_wide_enough():
    """中英文 README 的每一张表都必须 ≥ MIN_TABLE_WIDTH，否则右边界缩进。

    宽度按**渲染后可见文字**量（链接按链接文字、不按 URL）。按原始 Markdown 量会高估，
    从而放过窄表——本仓就因此漏过「文档地图」那张只有 81 单位的表。
    """
    mod = _table_checker()
    for rel in mod.LANDING_PAGES:
        text = (ROOT / rel).read_text(encoding="utf-8")
        for n, table in enumerate(mod.iter_tables(text), 1):
            widths = [mod.cell_width(c) for c in table["header"]]
            for row in table["body"]:
                for ci, cell in enumerate(row[:len(widths)]):
                    widths[ci] = max(widths[ci], mod.cell_width(cell))
            assert sum(widths) >= mod.MIN_TABLE_WIDTH, (
                f"{rel} 表 {n}（行 {table['line']}）总宽 {sum(widths)} "
                f"< {mod.MIN_TABLE_WIDTH}，列宽 {widths}"
            )


# --------------------------------------------------------------------------
# manual carrier naming (飞书 / Notion)
# --------------------------------------------------------------------------
def test_the_manual_carrier_is_named_feishu_and_notion_only():
    """手册载体只写「飞书」「Notion」，不带任何限定词。

    这条规则返工过两次：第一次带了限定词，第二次换成了另一个限定词，仍不合要求。
    最终口径是**只写载体名本身**。

    注意三个坑：
    * 徽章文案是 URL 编码的（`%E9%A3%9E%E4%B9%A6...`），只 grep 原文会漏 —— 必须**解码后**再查一遍；
    * 禁用词是**拼接构造**的，不是字面量。否则本文件自己就会命中「全文搜索禁止出现」这条检查，
      等于要求全仓唯一例外是检查器本身——那不如让检查器自己也不出现这些词。
    """
    from urllib.parse import unquote

    feishu, notion = "飞书", "Notion"
    banned = (
        feishu + "主" + "文档",      # 手册载体不带「主」
        feishu + "文档",             # 也不带「文档」——只写载体名
        notion + " 镜像",
        notion + "镜像",
        notion + "（镜像）",
    )
    skip_dirs = {"out", "projects", ".git", "__pycache__", ".pytest_cache", "_backup"}
    exts = {".md", ".py", ".json", ".yaml", ".yml", ".toml", ".txt", ".cfg"}

    bad = []
    for p in sorted(ROOT.rglob("*")):
        if not p.is_file() or p.suffix.lower() not in exts:
            continue
        rel = str(p.relative_to(ROOT)).replace("\\", "/")
        if set(Path(rel).parts[:-1]) & skip_dirs:
            continue
        text = p.read_text(encoding="utf-8", errors="ignore")
        for form, body in (("原文", text), ("URL 解码后", unquote(text))):
            for term in banned:
                if term in body:
                    bad.append(f"{rel}：出现禁用写法（{form}）")
    assert not bad, bad


# --------------------------------------------------------------------------
# manual URLs (single canonical form)
# --------------------------------------------------------------------------
def test_manual_urls_carry_no_tracking_parameters():
    """手册地址只有一种写法：`paths.py` 里的常量，不带任何查询参数。

    两个载体都会在「复制链接」时附带来源标记（飞书的 from、Notion 的 pvs）。
    那些参数**不改变文档权限**，只会让同一份地址在仓库里出现两种写法，
    读者无法判断哪个才是准的。所以地址一律取
    `paths.MANUAL_CN_URL` / `MANUAL_NOTION_URL`，不得出现变体。
    """
    from urllib.parse import unquote

    from omniarchitect.paths import MANUAL_CN_URL, MANUAL_NOTION_URL

    assert "?" not in MANUAL_CN_URL, f"飞书地址不得带查询参数：{MANUAL_CN_URL}"
    assert "?" not in MANUAL_NOTION_URL, f"Notion 地址不得带查询参数：{MANUAL_NOTION_URL}"
    assert MANUAL_NOTION_URL.startswith("https://tomatopark.notion.site/"), MANUAL_NOTION_URL

    feishu_id = MANUAL_CN_URL.rsplit("/", 1)[-1]
    notion_id = MANUAL_NOTION_URL.rsplit("/", 1)[-1].removeprefix("Skill-")
    skip_dirs = {"out", "projects", ".git", "__pycache__", ".pytest_cache", "_backup"}
    exts = {".md", ".py", ".json", ".yaml", ".yml", ".toml", ".txt"}

    bad: list[str] = []
    seen_cn = seen_intl = 0
    for p in sorted(ROOT.rglob("*")):
        if not p.is_file() or p.suffix.lower() not in exts:
            continue
        rel = str(p.relative_to(ROOT)).replace("\\", "/")
        if set(Path(rel).parts[:-1]) & skip_dirs:
            continue
        text = p.read_text(encoding="utf-8", errors="ignore")
        for form, body in (("原文", text), ("URL 解码后", unquote(text))):
            if feishu_id + "?" in body:
                bad.append(f"{rel}：飞书地址带查询参数（{form}）")
            if notion_id + "?" in body:
                bad.append(f"{rel}：Notion 地址带查询参数（{form}）")
        seen_cn += text.count(MANUAL_CN_URL)
        seen_intl += text.count(MANUAL_NOTION_URL)

    assert not bad, bad
    assert seen_cn > 80, f"规范飞书地址只出现 {seen_cn} 次，疑似被换成了别的写法"
    assert seen_intl > 5, f"规范 Notion 地址只出现 {seen_intl} 次，疑似被换成了别的写法"


# --------------------------------------------------------------------------
# reference library & directing skill (first-party entries)
# --------------------------------------------------------------------------
def test_reference_and_director_entries_are_first_party():
    """参考图素材库与导演技能的地址只有一种写法，且都登记为自有 URL。

    这两个入口都是本项目自有的，所以可以出现在用户面文档里；但地址若出现变体
    （例如重新带上「复制链接」的来源参数），读者就无法判断哪个是准的。
    """
    import re
    from urllib.parse import unquote

    from omniarchitect import brand_policy as bp
    from omniarchitect.paths import DIRECTOR_SKILL_URL, REFERENCE_LIBRARY_URL

    assert "?" not in REFERENCE_LIBRARY_URL, REFERENCE_LIBRARY_URL
    assert "?" not in DIRECTOR_SKILL_URL, DIRECTOR_SKILL_URL
    assert REFERENCE_LIBRARY_URL.startswith("https://tomatopark.notion.site/"), REFERENCE_LIBRARY_URL
    assert DIRECTOR_SKILL_URL.startswith("https://github.com/tomatoparkdao/"), DIRECTOR_SKILL_URL

    # 自有 URL 登记表必须真的覆盖这两个地址，否则合规审计会把它们当外部推广链接
    for url in (REFERENCE_LIBRARY_URL, DIRECTOR_SKILL_URL):
        assert any(url.startswith(own) for own in bp.OWN_URLS), f"未登记为自有 URL：{url}"

    skip_dirs = {"out", "projects", ".git", "__pycache__", ".pytest_cache", "_backup"}
    exts = {".md", ".py", ".json", ".yaml", ".yml", ".toml", ".txt"}
    url_re = re.compile(r"https?://[^\s)\"'<>\]），。；、]+")

    # 允许两种形态：规范地址本身，或 OWN_URLS 里登记过的自有前缀
    # （登记表用前缀匹配，`.../Luxora-AI-` 这类短写是正当的）。
    # 但带查询参数的完整地址两种都不是 —— 那才是要抓的变体。
    allowed = {REFERENCE_LIBRARY_URL, DIRECTOR_SKILL_URL, *bp.OWN_URLS}

    bad: list[str] = []
    seen_lib = seen_dir = 0
    for p in sorted(ROOT.rglob("*")):
        if not p.is_file() or p.suffix.lower() not in exts:
            continue
        rel = str(p.relative_to(ROOT)).replace("\\", "/")
        if set(Path(rel).parts[:-1]) & skip_dirs:
            continue
        text = p.read_text(encoding="utf-8", errors="ignore")
        for form, body in (("原文", text), ("URL 解码后", unquote(text))):
            for url in url_re.findall(body):
                if "Luxora-AI" in url and url not in allowed:
                    bad.append(f"{rel}：素材库地址出现变体（{form}）：{url}")
                if "omniailab-ai-director" in url and url not in allowed:
                    bad.append(f"{rel}：导演技能地址出现变体（{form}）：{url}")
        seen_lib += text.count(REFERENCE_LIBRARY_URL)
        seen_dir += text.count(DIRECTOR_SKILL_URL)

    assert not bad, bad
    assert seen_lib >= 3, f"素材库地址只出现 {seen_lib} 次，疑似被换掉"
    assert seen_dir >= 3, f"导演技能地址只出现 {seen_dir} 次，疑似被换掉"


def test_reference_command_lists_both_entries():
    """`python -m omniarchitect reference` 要能直接把两个入口和边界打出来。"""
    from omniarchitect.reference import ENTRIES, as_list

    assert set(ENTRIES) == {"reference", "video"}
    entries = as_list()
    assert [e["id"] for e in entries] == ["reference", "video"]
    for e in entries:
        assert e["url"].startswith("https://"), e
        assert e["boundary"], e          # 没有边界说明就等于在教人越界
        assert e["doc"].startswith("docs/"), e
        assert (ROOT / e["doc"]).exists(), f"细则文档缺失：{e['doc']}"
