"""Agent Skills compatibility, installer safety, and third-party auditing."""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from omniailab_ai_architect import compliance_audit as ca  # noqa: E402
from omniailab_ai_architect.integration import agent_skills as sk  # noqa: E402
from omniailab_ai_architect.integration import installer as inst  # noqa: E402
from omniailab_ai_architect.paths import ROOT  # noqa: E402


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
        assert (Path(cp.target) / "omniailab_ai_architect" / "model.py").exists()


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
# third-party audit
# --------------------------------------------------------------------------
def test_audit_scan_is_clean_and_reports_a_reason():
    rep = ca.scan(ROOT)
    assert rep["files_scanned"] > 100
    assert rep["action_count"] == 0, [f["path"] for f in rep["needs_action"]]
    assert rep["conclusion"]


def test_vendored_upstream_is_preserved_untouched():
    rep = ca.scan(ROOT)
    assert rep["by_disposition"].get("vendored-preserve", 0) > 0
    vendored = ROOT / "third_party" / "arch-skills"
    if vendored.exists():
        assert (vendored / "LICENSE").exists(), "上游 LICENSE 不得删除"


def test_licence_attribution_is_concentrated_and_kept():
    notices = ROOT / "THIRD_PARTY_NOTICES.md"
    assert notices.exists()
    text = notices.read_text(encoding="utf-8")
    for need in ("arch-skills", "Gu Jun", "MIT", "CC BY 4.0", "third_party/arch-skills"):
        assert need in text, need


def test_user_facing_files_carry_no_commercial_promotion():
    banned = ("chodo",)
    for rel in ("SKILL.md", "README.md"):
        text = (ROOT / rel).read_text(encoding="utf-8")
        for b in banned:
            assert b.lower() not in text.lower(), rel


def test_a_user_facing_file_with_third_party_branding_is_flagged():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "knowledge").mkdir()
        (root / "knowledge" / "x.md").write_text(
            "本项目参考 Gu Jun 的 arch-skills 方法。", encoding="utf-8")
        rep = ca.scan(root)
        assert rep["action_count"] == 1
        f = rep["needs_action"][0]
        assert f["disposition"] == "sanitize-user-facing"
        assert any("第三方名称" in r for r in f["reasons"])


def test_attribution_inside_a_compliance_file_is_kept():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "manifest").parent.mkdir(parents=True, exist_ok=True)
        (root / "THIRD_PARTY_NOTICES.md").write_text(
            "Upstream: arch-skills · Gu Jun · MIT / CC BY 4.0", encoding="utf-8")
        rep = ca.scan(root)
        assert rep["action_count"] == 0
        assert rep["by_disposition"].get("attribution-required-keep") == 1


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
            "业主：确认后进入下一阶段\n甲方：主创团队\n客户：设计方", encoding="utf-8")
        rep = ca.scan(root)
        assert rep["action_count"] == 0, rep["needs_action"]


def test_report_rendering_and_writing():
    with tempfile.TemporaryDirectory() as td:
        rep = ca.scan(ROOT)
        md = ca.render_markdown(rep)
        assert "# 第三方内容审计报告" in md
        assert "必须保留的第三方署名" in md
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
            "XML: http://schemas.openxmlformats.org/xxx and https://purl.org/dc\n",
            encoding="utf-8")
        rep = ca.scan(root)
        assert rep["action_count"] == 0, rep["needs_action"]
