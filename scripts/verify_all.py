#!/usr/bin/env python
"""Full verification: tests + catalogue self-check + directory integrity + smoke run.

This is what to run before claiming a change is done.

    python scripts/verify_all.py
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PACKAGE = "omniailab_ai_architect"

REQUIRED_PATHS = [
    "AGENTS.md", "README.md", "README_EN.md", "SKILL.md", "LICENSE", "VERSION",
    PACKAGE + "/stages.py", PACKAGE + "/changes.py", PACKAGE + "/model.py",
    PACKAGE + "/planner.py", PACKAGE + "/workflow.py", PACKAGE + "/stage_state.py",
    PACKAGE + "/routing.py", PACKAGE + "/quantities.py", PACKAGE + "/compliance.py",
    PACKAGE + "/registry.py",
    # v1.1 additions
    PACKAGE + "/providers/omniailab.py", PACKAGE + "/providers/base.py",
    PACKAGE + "/tools/registry.py", PACKAGE + "/tools/capability.py",
    PACKAGE + "/presentation/deck.py", PACKAGE + "/presentation/pptx_writer.py",
    PACKAGE + "/presentation/layouts.py",
    PACKAGE + "/integration/agent_skills.py", PACKAGE + "/integration/installer.py",
    PACKAGE + "/knowledge/loader.py",
    "schemas/project.schema.json", "schemas/case.schema.json",
    "schemas/tool-capability.schema.json", "schemas/presentation.schema.json",
    "workflows/interior-full.yaml",
    "skills/01-brief.md", "skills/18-revisions.md", "skills/design-presentation.md",
    "adapters/specs/blender.md", "adapters/specs/ifc.md",
    "knowledge/architectural-design-principles.md",
    "knowledge/design-presentation-methodology.md",
    "installer/install.py", "installer/manifest.json",
    "compatibility/agent-skills.md",
    "cases/generic-apartment-120.md",
    PACKAGE + "/tests/test_stages.py", PACKAGE + "/tests/test_changes.py",
    PACKAGE + "/tests/test_workflow.py", PACKAGE + "/tests/test_provider.py",
    PACKAGE + "/tests/test_tools.py", PACKAGE + "/tests/test_presentation.py",
    PACKAGE + "/tests/test_scenarios.py", PACKAGE + "/tests/test_integration.py",
    "docs/WORKFLOW.md", "docs/DESIGN_CRITERIA.md", "docs/ARCHITECTURE.md",
    "docs/OMNIAILAB_INTEGRATION.md", "docs/CONTENT_AUDIT.md",
    "docs/MCP_TOOLS.md", "docs/INSTALL.md", "docs/PRESENTATION.md",
    "scripts/run_tests.py",
]


def section(title: str) -> None:
    print()
    print("=" * 78)
    print(title)
    print("=" * 78)


def check_paths() -> int:
    section("1. 目录完整性")
    missing = [p for p in REQUIRED_PATHS if not (ROOT / p).exists()]
    for p in REQUIRED_PATHS:
        if not (ROOT / p).exists():
            print(f"  MISSING  {p}")
    if not missing:
        print(f"  ok  {len(REQUIRED_PATHS)} 项必需文件全部存在")
    return len(missing)


def check_catalogue() -> int:
    section("2. 阶段与能力目录自检")
    from omniailab_ai_architect.stages import CAPABILITIES, STAGE_ORDER, validate_catalog
    from omniailab_ai_architect.registry import criteria_report, load_registry

    issues = validate_catalog()
    print(f"  阶段 {len(STAGE_ORDER)}：{', '.join(STAGE_ORDER)}")
    print(f"  能力 {len(CAPABILITIES)}")
    cross = [c.slug for c in CAPABILITIES if len(c.stages) > 1]
    print(f"  跨阶段能力 {len(cross)}：{', '.join(cross[:8])}{' …' if len(cross) > 8 else ''}")
    recs = load_registry()
    unmapped = [r.slug for r in recs if r.legacy and not r.legacy_file]
    if unmapped:
        print(f"  未找到说明文件的技能：{unmapped}")
    crit = criteria_report()
    print(f"  设计判据：{crit['summary']['criteria_sets']} 组，"
          f"覆盖阶段 {', '.join(crit['summary']['stages_touched'])}")
    print(f"  署名：{crit['signature']}")
    for i in issues:
        print(f"  ISSUE  {i}")
    if not issues:
        print("  ok  目录结构自检通过")
    return len(issues) + len(unmapped)


def check_doctor() -> int:
    section("3. 工具链体检")
    from omniailab_ai_architect.adapters import doctor

    rep = doctor()
    for row in rep["adapters"]:
        mark = "可用" if row["available"] else "缺失"
        print(f"  [{mark}] {row['adapter']:<10} {row['version'] or ''}"
              f"{'　降级→ ' + row['degraded_to'] if row['degraded_to'] else ''}")
    print(f"  可用：{', '.join(rep['available']) or '（无）'}")
    print(f"  缺失：{', '.join(rep['unavailable']) or '（无）'}")
    # DXF and mesh must always be available — they carry the closed loop
    must = {"dxf", "mesh"}
    broken = must - set(rep["available"])
    for b in broken:
        print(f"  FAIL  {b} 适配器不可用——闭环无法成立")
    return len(broken)


def check_smoke() -> int:
    section("4. 全流程冒烟（八阶段 + 变更分析）")
    from omniailab_ai_architect.changes import analyse
    from omniailab_ai_architect.demo import build_demo_project
    from omniailab_ai_architect.stage_state import progress
    from omniailab_ai_architect.workflow import StageRunner

    failures = 0
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        project = build_demo_project(tmp)
        runner = StageRunner(project, tmp / "out", assume_approval=True, project_dir=tmp)
        manifest = runner.run_all(confirm_all=True)
        for o in manifest.outcomes:
            print(f"  [{o.status:<9}] {o.stage_name}")
        if manifest.blocks:
            failures += len(manifest.blocks)
            for b in manifest.blocks:
                print(f"  FAIL  {b}")
        pct = progress(project)["percent"]
        print(f"  阶段进度 {pct}%")
        if pct != 100.0:
            failures += 1

        dxf = sorted(Path(manifest.out_dir).rglob("*.dxf"))
        obj = sorted(Path(manifest.out_dir).rglob("*.obj"))
        print(f"  DXF {len(dxf)} 个，OBJ {len(obj)} 个")
        if not dxf or not obj:
            failures += 1
            print("  FAIL  闭环缺件：必须有 DXF 与 OBJ")

        rep = analyse(project, "我不喜欢客厅的电视背景墙", apply=False)
        assert rep.diagnosis.landing_stage == "S4"
        assert "S3" not in [r.stage for r in rep.rework]
        geo = analyse(project, "把客厅那面墙往外移300mm", apply=False)
        assert geo.diagnosis.geometry_affecting
        print(f"  变更分析：立面→{rep.diagnosis.landing_stage}（不动几何）　"
              f"移墙→{geo.diagnosis.landing_stage}（几何变更）")
    return failures


def check_tests() -> int:
    section("5. 测试套件")
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "run_tests.py")],
        cwd=str(ROOT), capture_output=True, text=True,
    )
    tail = [l for l in proc.stdout.strip().splitlines() if l.strip()][-6:]
    for line in tail:
        print("  " + line)
    if proc.returncode != 0:
        print("  FAIL  测试未全部通过")
    return 0 if proc.returncode == 0 else 1


def check_v11() -> int:
    section("6. v1.1 子系统（合规 / provider / 工具 / 知识 / 汇报 / 安装）")
    failures = 0

    # --- third-party compliance -------------------------------------------
    from omniailab_ai_architect import compliance_audit as ca

    audit = ca.scan(ROOT)
    print(f"  内容自检：扫描 {audit['files_scanned']} 个文本文件，"
          f"需处理 {audit['action_count']} 个")
    if audit["action_count"]:
        failures += audit["action_count"]
        for f in audit["needs_action"]:
            print(f"  FAIL  {f['path']}　{f['disposition']}")
    for need in ("LICENSE", "VERSION", "README_EN.md"):
        if not (ROOT / need).exists():
            failures += 1
            print(f"  FAIL  缺少 {need}")

    # --- knowledge base ---------------------------------------------------
    from omniailab_ai_architect import knowledge

    krep = knowledge.report()
    print(f"  知识库：{krep['count']} 个领域 / {krep['total_lines']} 行，"
          f"问题 {len(krep['issues'])}")
    for i in krep["issues"]:
        print(f"  FAIL  {i}")
    failures += len(krep["issues"])

    # --- providers --------------------------------------------------------
    from omniailab_ai_architect.providers import discover

    prep = discover(ROOT, refresh=True).report()
    print(f"  provider：已连接 {prep['connected'] or '（无）'}，"
          f"未配置 {prep['not_configured'] or '（无）'}")
    if "local" not in prep["connected"]:
        failures += 1
        print("  FAIL  内置本地 provider 不可用——离线闭环被破坏")

    # --- tool registry ----------------------------------------------------
    from omniailab_ai_architect.tools import registry as tool_registry

    treg = tool_registry()
    detect = treg.detect_report()
    print(f"  工具注册表：可用 {detect['available']}")
    for need in ("dxf", "mesh"):
        if need not in detect["available"]:
            failures += 1
            print(f"  FAIL  {need} 不可用——闭环无法成立")
    try:
        treg.guard("blender", "run_blender")
        failures += 1
        print("  FAIL  L4 调用未被权限拦截")
    except Exception:
        pass

    # --- presentation -----------------------------------------------------
    import tempfile as _tempfile

    from omniailab_ai_architect import presentation
    from omniailab_ai_architect.demo import build_demo_project

    with _tempfile.TemporaryDirectory() as td:
        proj = build_demo_project(Path(td))
        drep = presentation.render(proj, "final", out_dir=Path(td), want_pdf=False)
        print(f"  汇报：{drep['slides']} 页，后端 {drep['pptx_backends']}")
        if drep["issues"]:
            failures += len(drep["issues"])
            for i in drep["issues"]:
                print(f"  FAIL  {i}")
        v = treg.verify(drep["files"]["pptx"])
        if not v.get("ok"):
            failures += 1
            print(f"  FAIL  PPTX 未被独立校验通过：{v.get('errors')}")

    # --- agent skills / installer ----------------------------------------
    from omniailab_ai_architect.integration import agent_skills as sk
    from omniailab_ai_architect.integration import installer as inst

    issues = sk.validate()
    print(f"  SKILL.md：{sk.parse().lines} 行 / {sk.parse().bytes_} 字节，"
          f"问题 {len(issues)}")
    for i in issues:
        print(f"  FAIL  {i}")
    failures += len(issues)

    with _tempfile.TemporaryDirectory() as td:
        rep = inst.Installer(source=ROOT, target=Path(td) / "skills").install()
        ok = rep.ok
        print(f"  安装闭环：{'通过' if ok else '未通过'}"
              f"（{len(rep.installed)} 个文件）")
        if not ok:
            failures += 1
            for e in rep.errors:
                print(f"  FAIL  {e}")
    return failures


def main() -> int:
    print("OmniArchitect 完整性验证")
    print(f"项目根目录：{ROOT}")
    total = (check_paths() + check_catalogue() + check_doctor() + check_smoke()
             + check_tests() + check_v11())
    section("结论")
    if total == 0:
        print("  全部通过：目录完整、目录自检通过、闭环成立、测试全绿、v1.1 子系统正常")
        return 0
    print(f"  {total} 项问题，需处理")
    return 1


if __name__ == "__main__":
    sys.exit(main())
