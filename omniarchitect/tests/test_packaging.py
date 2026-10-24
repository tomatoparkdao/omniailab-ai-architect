"""分发白名单守卫：正式安装包里只能是能力，不能是产物。

背景：`installer/manifest.json` 曾把 `projects/demo-120/concept-render/` 里的
PPTX（101 KB）、PNG（141 KB）和运行记录登记成"分发包内容" —— 因为它们躺在
仓库里，而安装器用的是黑名单。黑名单的问题是：**新长出来的东西默认在包里**。

这几条守卫把规则钉死：

1. 白名单是唯一判据，`projects/`、`omniarchitect/tests/`、`scripts/` 一律不进包；
2. `manifest.json` 的文件列表 == 白名单，多一个少一个都算坏；
3. 包里不许有生成物扩展名、不许有本机绝对路径、不许有凭据；
4. 技能目录里出现生成物时，审计必须失败（不是"记一笔"）。

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

from omniarchitect import packaging, workspace
from omniarchitect.integration import agent_skills as sk
from omniarchitect.integration import installer as inst
from omniarchitect.paths import ROOT


def _fake_root(td: Path, skill_text: str = "") -> Path:
    """造一个最小技能根：白名单里的 SKILL.md + VERSION。"""
    (td / "SKILL.md").write_text(skill_text or (ROOT / "SKILL.md").read_text(encoding="utf-8"),
                                 encoding="utf-8")
    (td / "VERSION").write_text("0.0.0\n", encoding="utf-8")
    return td


# --------------------------------------------------------------------------
def test_whitelist_accepts_capability_and_rejects_output() -> None:
    """白名单只认能力：代码 / 知识 / 风格 / Schema / 文档。"""
    for rel in ("SKILL.md", "AGENTS.md", ".gitignore", "VERSION",
                "omniarchitect/cli.py", "knowledge/INDEX.md",
                "schemas/project.schema.json", "skills/intake.md",
                "docs/WORKFLOW.md", "installer/install.py"):
        assert packaging.is_distributable(rel), f"{rel} 应当可以分发"
    for rel in ("projects/demo-120/project.json",
                "projects/demo-120/concept-render/deck/x.pptx",
                "omniarchitect/tests/test_cli.py",
                "scripts/run_tests.py",
                "out/run-20260101/report.md",
                "omniarchitect/__pycache__/x.pyc",
                "docs/ACCEPTANCE_ROUND1.md",
                "random-note.txt"):
        assert not packaging.is_distributable(rel), f"{rel} 不该进包"


def test_payload_has_no_generated_types() -> None:
    """正式分发包里不许出现任何生成物扩展名。"""
    files = packaging.distribution_files(ROOT)
    offenders = [str(p.relative_to(ROOT)).replace("\\", "/") for p in files
                 if p.suffix.lower() in packaging.FORBIDDEN_SUFFIXES]
    assert not offenders, f"分发包里有生成物：{offenders[:5]}"


def test_payload_excludes_projects_and_tests() -> None:
    files = packaging.distribution_files(ROOT)
    bad = [str(p.relative_to(ROOT)).replace("\\", "/") for p in files
           if str(p.relative_to(ROOT)).replace("\\", "/").split("/")[0]
           in {"projects", "out", "cache", "outputs", "archive", "scripts", "tests"}]
    assert not bad, f"分发包混入了运行数据：{bad[:5]}"


def test_manifest_equals_the_whitelist() -> None:
    """清单 = 白名单。`manifest.json` 里的每个路径都必须真的会发出去。"""
    data = sk.build_manifest(ROOT, with_hashes=False)
    listed = {rec["path"] for rec in data["files"]}
    actual = {str(p.relative_to(ROOT)).replace("\\", "/")
              for p in packaging.distribution_files(ROOT)}
    assert listed == actual, (
        f"清单多登记了 {sorted(listed - actual)[:5]}；"
        f"少登记了 {sorted(actual - listed)[:5]}")
    assert data["truncated"] is False
    assert data["total_bytes"] == sum(
        p.stat().st_size for p in packaging.distribution_files(ROOT))


def test_manifest_has_no_machine_specific_root() -> None:
    """清单里不许写本机路径 —— 它会被推到公开仓库。"""
    data = sk.build_manifest(ROOT, with_hashes=False)
    assert data["root"] == ".", f"manifest.root 应当是相对标记，实际 {data['root']!r}"
    text = json.dumps(data, ensure_ascii=False)
    assert str(ROOT).replace("\\", "/") not in text.replace("\\", "/")


def test_committed_manifest_is_up_to_date() -> None:
    """仓库里那份 `installer/manifest.json` 必须与当前白名单一致（否则就是过期清单）。"""
    on_disk = json.loads((ROOT / "installer" / "manifest.json").read_text(encoding="utf-8"))
    fresh = sk.build_manifest(ROOT, with_hashes=False)
    listed = {rec["path"] for rec in on_disk["files"]}
    actual = {rec["path"] for rec in fresh["files"]}
    assert listed == actual, (
        "installer/manifest.json 过期了，请运行 `python -m omniarchitect manifest`："
        f"多 {sorted(listed - actual)[:5]}，少 {sorted(actual - listed)[:5]}")
    assert on_disk["generated_from"] == fresh["generated_from"]


def test_audit_passes_on_the_real_repository() -> None:
    """当前仓库必须过审计：0 违规。"""
    rep = packaging.audit(ROOT)
    assert rep["ok"], "审计未通过：" + "；".join(
        f"[{v['rule']}] {v['detail']}" for v in rep["violations"][:6])
    assert rep["total_bytes"] <= packaging.MAX_TOTAL_BYTES


def test_audit_catches_a_planted_image() -> None:
    """往技能目录塞一张图，审计必须失败（这就是膨胀的开始）。"""
    with workspace.tempdir("audit-png-") as td:
        _fake_root(td)
        (td / "screenshot.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 64)
        rep = packaging.audit(td)
        assert not rep["ok"]
        rules = {v["rule"] for v in rep["violations"]}
        assert "stray-artefact" in rules


def test_audit_catches_an_absolute_path_in_code() -> None:
    """代码里写死本机路径 → 别人装完跑不通，必须拦。"""
    with workspace.tempdir("audit-path-") as td:
        _fake_root(td)
        pkg = td / "omniarchitect"
        pkg.mkdir()
        (pkg / "bad.py").write_text(
            'DB = r"C:\\Users\\someone\\AppData\\omniailab.db"\n', encoding="utf-8")
        rep = packaging.audit(td)
        assert not rep["ok"]
        assert any(v["rule"] == "absolute-path" for v in rep["violations"])


def test_audit_catches_a_planted_secret() -> None:
    """凭据不该进包。"""
    with workspace.tempdir("audit-secret-") as td:
        _fake_root(td)
        (td / "mcp.json.example").write_text(
            '{"headers": {"Authorization": "Bearer abcdefghijklmnopqrstuvwxyz012345"}}',
            encoding="utf-8")
        rep = packaging.audit(td)
        assert not rep["ok"]
        assert any(v["rule"] == "secret" for v in rep["violations"])


def test_audit_catches_a_stale_manifest() -> None:
    """清单登记了不存在的文件（迁移后没重建）→ 审计失败。"""
    with workspace.tempdir("audit-stale-") as td:
        _fake_root(td)
        (td / "installer").mkdir()
        (td / "installer" / "manifest.json").write_text(json.dumps(
            {"root": ".", "files": [{"path": "SKILL.md"}, {"path": "gone.txt"}]}),
            encoding="utf-8")
        rep = packaging.audit(td)
        assert not rep["ok"]
        assert rep["manifest"]["matches"] is False
        assert "gone.txt" in rep["manifest"]["missing"]


def test_audit_tree_catches_artefacts_in_an_installed_copy() -> None:
    """装好的副本里出现 DXF → 安装即坏。"""
    with workspace.tempdir("audit-tree-") as td:
        (td / "SKILL.md").write_text("x", encoding="utf-8")
        (td / "plan.dxf").write_text("0\nEOF\n", encoding="utf-8")
        rep = packaging.audit_tree(td)
        assert not rep["ok"]
        assert rep["violations"][0]["rule"] == "forbidden-type"


# --------------------------------------------------------------------------
def test_copy_install_carries_only_the_whitelist() -> None:
    """copy 模式装出来的文件集合 == 白名单，并且能通过 verify。"""
    with workspace.tempdir("install-copy-") as td:
        target = Path(td) / "skills"
        rep = inst.Installer(source=ROOT, target=target, mode=inst.MODE_COPY).install()
        assert rep.ok, rep.errors
        dest = Path(rep.target)
        expected = {str(p.relative_to(ROOT)).replace("\\", "/")
                    for p in packaging.distribution_files(ROOT)}
        got = {str(p.relative_to(dest)).replace("\\", "/")
               for p in dest.rglob("*") if p.is_file()}
        got.discard(inst.MANIFEST_NAME)
        assert got == expected, (
            f"多装了 {sorted(got - expected)[:5]}；漏装 {sorted(expected - got)[:5]}")
        assert not (dest / "projects").exists()
        assert not (dest / "omniarchitect" / "tests").exists()
        assert (dest / "SKILL.md").exists() and (dest / "knowledge" / "INDEX.md").exists()


def test_copy_install_ignores_a_stray_file_in_the_source() -> None:
    """源目录里多出来的产物不会被带进安装包 —— 黑名单时代它会被带走。"""
    with workspace.tempdir("src-") as td:
        src = _fake_root(td)
        (src / "projects" / "demo").mkdir(parents=True)
        (src / "projects" / "demo" / "deck.pptx").write_bytes(b"PK\x03\x04" + b"0" * 32)
        target = Path(td) / "out-skills"
        rep = inst.Installer(source=src, target=target, mode=inst.MODE_COPY).install()
        dest = Path(rep.target)
        assert (dest / "SKILL.md").exists()
        assert not (dest / "projects").exists(), "projects/ 被带进安装包了"


def test_pointer_install_still_works() -> None:
    """pointer 模式不受影响：三个文件 + 指回真实仓库。"""
    with workspace.tempdir("install-pointer-") as td:
        target = Path(td) / "skills"
        rep = inst.Installer(source=ROOT, target=target, mode=inst.MODE_POINTER).install()
        assert rep.ok, rep.errors
        dest = Path(rep.target)
        assert (dest / "SKILL.md").exists()
        pointer = dest / inst.POINTER_NAME
        assert pointer.exists()
        assert Path(pointer.read_text(encoding="utf-8").strip()) == ROOT
        installed = [p for p in dest.rglob("*") if p.is_file()]
        assert len(installed) <= 4, f"pointer 模式只该有 3–4 个文件，实际 {len(installed)}"
