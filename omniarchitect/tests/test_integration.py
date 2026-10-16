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
        if rel.startswith(("out/", "projects/")):
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
            assert any(d in u for d in _ca.OWN_DOMAINS) or \
                any(h in u for h in _ca.BENIGN_URL_HOSTS), f"{rel}: {u}"


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
    bad = []
    for p in sorted(ROOT.rglob("*.md")):
        rel = str(p.relative_to(ROOT)).replace("\\", "/")
        if rel.startswith(("out/", "projects/")):
            continue
        text = p.read_text(encoding="utf-8")
        assert text.startswith("---"), rel
        fm = text.split("---", 2)[1]
        for key, value in [("version", version), *FRONTMATTER_TAIL]:
            if f"{key}: {value}" not in fm:
                bad.append(f"{rel}: {key}")
    assert not bad, bad


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
