#!/usr/bin/env python
"""Full verification: tests + catalogue self-check + directory integrity + smoke run.

This is what to run before claiming a change is done.

    python scripts/verify_all.py

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PACKAGE = "omniarchitect"

REQUIRED_PATHS = [
    "AGENTS.md", "README.md", "README_EN.md", "SKILL.md", "LICENSE", "VERSION",
    "THIRD_PARTY_NOTICES.md", "LICENSES/README.md",
    PACKAGE + "/stages.py", PACKAGE + "/changes.py", PACKAGE + "/model.py",
    PACKAGE + "/planner.py", PACKAGE + "/workflow.py", PACKAGE + "/stage_state.py",
    PACKAGE + "/routing.py", PACKAGE + "/quantities.py", PACKAGE + "/compliance.py",
    PACKAGE + "/registry.py", PACKAGE + "/brand_policy.py",
    PACKAGE + "/manual.py",
    # v1.20 → v1.21：运行工作区与分发白名单
    PACKAGE + "/workspace.py", PACKAGE + "/packaging.py",
    "docs/MANUAL.md",
    # v1.1 additions
    PACKAGE + "/providers/omniailab.py", PACKAGE + "/providers/base.py",
    PACKAGE + "/providers/canvas.py", PACKAGE + "/providers/omniailab.models.json",
    PACKAGE + "/tools/registry.py", PACKAGE + "/tools/capability.py",
    PACKAGE + "/presentation/deck.py", PACKAGE + "/presentation/pptx_writer.py",
    PACKAGE + "/presentation/layouts.py",
    PACKAGE + "/integration/agent_skills.py", PACKAGE + "/integration/installer.py",
    PACKAGE + "/knowledge/loader.py",
    "schemas/project.schema.json", "schemas/case.schema.json",
    "schemas/concept-render.schema.json",
    "schemas/tool-capability.schema.json", "schemas/presentation.schema.json",
    "workflows/interior-full.yaml",
    "skills/design-brief.md", "skills/space-planning.md",
    "skills/design-presentation.md", "skills/delivery.md",
    "skills/concept-visualization.md", "skills/building-services.md",
    "adapters/specs/blender.md", "adapters/specs/ifc.md",
    "knowledge/architectural-design-principles.md",
    "knowledge/ai-concept-visualization.md",
    "knowledge/design-presentation-methodology.md",
    "installer/install.py", "installer/manifest.json",
    "compatibility/agent-skills.md",
    "cases/generic-apartment-120.md",
    "docs/TABLES.md", "scripts/check_tables.py",
    PACKAGE + "/tests/test_stages.py", PACKAGE + "/tests/test_changes.py",
    PACKAGE + "/tests/test_workflow.py", PACKAGE + "/tests/test_provider.py",
    PACKAGE + "/tests/test_tools.py", PACKAGE + "/tests/test_presentation.py",
    PACKAGE + "/tests/test_scenarios.py", PACKAGE + "/tests/test_integration.py",
    PACKAGE + "/tests/test_concept_render.py",
    PACKAGE + "/tests/test_brand_policy.py",
    "providers/omniailab.api.example.json", "providers/README.md",
    "docs/WORKFLOW.md", "docs/DESIGN_CRITERIA.md", "docs/ARCHITECTURE.md",
    "docs/OMNIAILAB_INTEGRATION.md", "docs/CONTENT_AUDIT.md",
    "docs/BRAND_POLICY.md", "docs/CONCEPT_RENDER.md",
    "docs/REFERENCE_SOURCES.md", "docs/VIDEO_PRODUCTION.md",
    "omniarchitect/reference.py",
    "docs/S1_INTAKE.md", "omniarchitect/intake/__init__.py",
    "docs/S2_CONCEPT.md", "omniarchitect/concept/__init__.py",
    "omniarchitect/concept/prototypes.py", "omniarchitect/concept/handoff.py",
    "omniarchitect/intake/guard.py", "omniarchitect/intake/gate.py",
    "schemas/intake.schema.json",
    "docs/MCP_TOOLS.md", "docs/INSTALL.md", "docs/PRESENTATION.md",
    "scripts/run_tests.py",
    "scripts/normalize_attribution.py",
    "scripts/check_assets.py",
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
    from omniarchitect.stages import CAPABILITIES, STAGE_ORDER, validate_catalog
    from omniarchitect.registry import criteria_report, load_registry

    issues = validate_catalog()
    print(f"  阶段 {len(STAGE_ORDER)}：{', '.join(STAGE_ORDER)}")
    print(f"  能力 {len(CAPABILITIES)}")
    cross = [c.slug for c in CAPABILITIES if len(c.stages) > 1]
    print(f"  跨阶段能力 {len(cross)}：{', '.join(cross[:8])}{' …' if len(cross) > 8 else ''}")
    recs = load_registry()
    # 说明文件的权威位置是 skills/<能力名>.md（文件名 = 能力名，可直接按名加载）。
    unmapped = [r.slug for r in recs if not r.brief_file]
    if unmapped:
        print(f"  未找到说明文件的能力：{unmapped}")
    else:
        print(f"  能力说明文件：{len(recs)}/{len(CAPABILITIES)} 齐全（skills/<能力名>.md）")
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
    from omniarchitect.adapters import doctor

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
    from omniarchitect.changes import analyse
    from omniarchitect.demo import build_demo_project
    from omniarchitect.stage_state import progress
    from omniarchitect.workflow import StageRunner

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
    from omniarchitect import compliance_audit as ca

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

    # --- brand and provider policy ----------------------------------------
    from omniarchitect import brand_policy as bpr

    pol = bpr.scan(ROOT)
    print(f"  品牌与供应商策略：扫描 {pol.files_scanned} 个文件，"
          f"规则 {len(bpr.RULES)} 条，禁止项 {len(pol.forbidden)}，"
          f"待审 {len(pol.needs_review)}，合规必要 {len(pol.compliance_required)}，"
          f"已授权依赖 {len(pol.authorized_dependency)}")
    if not pol.ok:
        failures += pol.action_count
        for h in pol.forbidden + pol.needs_review:
            print(f"  FAIL  {h.path}:{h.line} {h.rule} {h.token} — {h.reason}")
    for need in (bpr.NOTICE_FILE, bpr.LICENCE_DIR + "/README.md", "LICENSE"):
        if not (ROOT / need).exists():
            failures += 1
            print(f"  FAIL  缺少许可证登记文件 {need}")

    # 创作能力独占必须可执行，而不是只写在文档里
    from omniarchitect.providers import (
        CREATIVE_OWNER,
        CREATIVE_SCOPES,
        LocalDeterministicProvider,
        OmniAiLabProvider,
        PolicyViolation,
        ProviderRegistry,
    )

    local_cap = LocalDeterministicProvider().probe()
    if set(local_cap.scopes) & set(CREATIVE_SCOPES):
        failures += 1
        print("  FAIL  自有模块声明了生成式创作能力域")
    import tempfile as _tf2

    with _tf2.TemporaryDirectory() as td:
        reg = ProviderRegistry([OmniAiLabProvider(project_dir=td),
                                LocalDeterministicProvider()])
        if reg.creative_backends():
            failures += 1
            print("  FAIL  OmniAiLab 离线时仍报告有创作后端")
        leaked = [s for s in CREATIVE_SCOPES if reg.select(s) is not None]
        if leaked:
            failures += 1
            print(f"  FAIL  创作能力域被交给非原生平台：{leaked}")
    try:
        ProviderRegistry([OmniAiLabProvider(project_dir=ROOT)]).add(
            type("Rogue", (), {"id": "unregistered-vendor-x"})())
    except PolicyViolation:
        pass
    else:
        failures += 1
        print("  FAIL  未登记 provider 未被拒绝注册")
    print(f"  创作能力独占：唯一被授权主体 {CREATIVE_OWNER}；"
          f"离线时创作后端为空且不回退第三方")

    # --- knowledge base ---------------------------------------------------
    from omniarchitect import knowledge

    krep = knowledge.report()
    print(f"  知识库：{krep['count']} 个领域 / {krep['total_lines']} 行，"
          f"问题 {len(krep['issues'])}")
    for i in krep["issues"]:
        print(f"  FAIL  {i}")
    failures += len(krep["issues"])

    # --- providers --------------------------------------------------------
    from omniarchitect.providers import discover

    prep = discover(ROOT, refresh=True).report()
    print(f"  provider：已连接 {prep['connected'] or '（无）'}，"
          f"未配置 {prep['not_configured'] or '（无）'}")
    if "local" not in prep["connected"]:
        failures += 1
        print("  FAIL  内置本地 provider 不可用——离线闭环被破坏")

    # --- tool registry ----------------------------------------------------
    from omniarchitect.tools import registry as tool_registry

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

    from omniarchitect import presentation
    from omniarchitect.demo import build_demo_project

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

    # --- concept renderings (post-gate G3, OmniAiLab canvas) --------------
    from omniarchitect.providers import canvas
    from omniarchitect.stages import (
        POST_GATE_ACTIONS,
        post_gate_actions_for_stage,
        validate_catalog,
    )

    if validate_catalog():
        failures += len(validate_catalog())
        for i in validate_catalog():
            print(f"  FAIL  {i}")
    if post_gate_actions_for_stage("S3") != ["concept-visualization"]:
        failures += 1
        print("  FAIL  G3 未挂载概念效果图后置动作")
    cat = canvas.load_catalog()
    print(f"  概念效果图：G3 后置动作 {POST_GATE_ACTIONS['G3']}；"
          f"画布模型 {[m.get('id') for m in canvas.recommended_models(cat)]}")
    for i in cat.get("_issues") or []:
        failures += 1
        print(f"  FAIL  模型声明：{i}")

    # --- agent skills / installer ----------------------------------------
    from omniarchitect.integration import agent_skills as sk
    from omniarchitect.integration import installer as inst

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


def check_style() -> int:
    section("7. 设计风格系统（内部专业模块）")
    try:
        from omniarchitect.stages import STAGES
        from omniarchitect.style import all_hooks, load_catalog
        from omniarchitect.style import validation as sv
        from omniarchitect.style.hooks import STAGE_HOOKS
    except Exception as exc:                                    # noqa: BLE001
        print(f"  FAIL  风格模块无法导入：{type(exc).__name__}: {exc}")
        return 1

    fails = 0

    bad = sv.check_style_dir()
    if bad:
        print(f"  FAIL  {len(bad)} 条风格数据未通过 Schema 校验：{list(bad)[:3]}")
        fails += len(bad)
    else:
        print("  ok  风格数据全部通过 Schema 校验")

    try:
        cat = load_catalog(refresh=True)
    except Exception as exc:                                    # noqa: BLE001
        print(f"  FAIL  索引构建失败：{exc}")
        return fails + 1
    if len(cat) < 40:
        print(f"  FAIL  风格条目仅 {len(cat)} 条（预期不少于 40）")
        fails += 1
    else:
        print(f"  ok  风格索引 {len(cat)} 条（按需加载，不整体读入上下文）")

    by_id = {st.id: st for st in STAGES}
    drift = []
    for sid, h in STAGE_HOOKS.items():
        if sid not in by_id:
            drift.append(f"{sid}: 阶段模型中没有这个阶段")
            continue
        want = f"{by_id[sid].gate.id} {by_id[sid].gate.label}"
        if h["gate"] != want:
            drift.append(f"{sid}: 挂钩 {h['gate']!r} ≠ 阶段模型 {want!r}")
    if drift:
        print(f"  FAIL  挂钩与阶段模型不一致：{drift}")
        fails += len(drift)
    else:
        print(f"  ok  {len(all_hooks())} 条挂钩的门禁措辞与阶段模型逐字符一致")

    proc = subprocess.run([sys.executable, "-m", PACKAGE, "style", "catalog"],
                          capture_output=True, text=True, encoding="utf-8",
                          cwd=str(ROOT))
    if proc.returncode != 0:
        print(f"  FAIL  CLI `style catalog` 执行失败：{(proc.stderr or '')[:200]}")
        fails += 1
    else:
        print("  ok  CLI `omniarchitect style` 可用")
    return fails


def check_assets() -> int:
    section("8. 资产体积（大文件 / 媒体二进制）")
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "check_assets.py"), "--json"],
        capture_output=True, text=True, encoding="utf-8", cwd=str(ROOT))
    try:
        rep = json.loads(proc.stdout or "{}")
    except Exception:                                            # noqa: BLE001
        print("  FAIL  资产守卫无法解析输出")
        print(f"    {(proc.stderr or proc.stdout or '')[:300]}")
        return 1
    print(f"  扫描 {rep.get('files_scanned', 0)} 个文件 / "
          f"合计 {rep.get('total_mb', 0)} MB / 上限 "
          f"{rep.get('max_bytes', 0) // 1024 // 1024} MB")
    over = rep.get("oversize") or []
    media = rep.get("media") or []
    if over:
        print(f"  FAIL  {len(over)} 个文件达到或超过上限：")
        for f in over[:10]:
            print(f"    {f['mb']:>9.3f} MB  {f['path']}")
    if media:
        print(f"  FAIL  {len(media)} 个媒体/二进制文件不得入库：")
        for m in media[:10]:
            print(f"    {m['kb']:>9.1f} KB  [{m['kind']}]  {m['path']}")
    if over or media:
        for g in rep.get("guidance", []):
            print(f"  → {g}")
        return len(over) + len(media)
    worst = (rep.get("biggest") or [{"kb": 0, "path": "-"}])[0]
    print(f"  ok  无超限文件、无媒体二进制；最大文件 "
          f"{worst['kb']} KB（{worst['path']}）")
    return 0


def check_tables() -> int:
    section("9. Markdown 表格规范（左右对齐）")
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "check_tables.py"), "--json"],
        capture_output=True, text=True, encoding="utf-8", cwd=str(ROOT))
    try:
        rep = json.loads(proc.stdout or "{}")
    except Exception:                                            # noqa: BLE001
        print("  FAIL  表格检查器无法解析输出")
        print(f"    {(proc.stderr or proc.stdout or '')[:300]}")
        return 1
    print(f"  扫描 {rep.get('files', 0)} 个文件 / {rep.get('tables', 0)} 张表")
    bad = rep.get("violations") or []
    if bad:
        by_rule: dict[str, int] = {}
        for v in bad:
            by_rule[v["rule"]] = by_rule.get(v["rule"], 0) + 1
        print(f"  FAIL  {len(bad)} 处违规：" +
              "　".join(f"{k}×{v}" for k, v in sorted(by_rule.items())))
        for v in bad[:10]:
            print(f"    {v['rule']}  {v['path']}:{v['line']}  {v['detail']}")
        print("  → 规范见 docs/TABLES.md（落地页每张表总显示宽度须 ≥ 140）")
        return len(bad)
    print("  ok  T1 列数一致 / T2 无空单元格 / T3 分隔行紧凑 / "
          "T4 落地页表宽 ≥140 / T5 列数 ≤6")
    return 0


def check_distribution() -> int:
    """第 10 段：分发包审计 —— 查的是**真要发出去的那一堆文件**。

    和资产段（第 8 段）的区别：那个扫 Git 里的文件，这个扫白名单产物，
    并且真的装一份出来看看装出来的东西干不干净。
    """
    section("10. 分发包审计（白名单 / 夹带 / 清单一致性）")
    from omniarchitect import packaging
    from omniarchitect.integration import installer as ins

    fails = 0
    rep = packaging.audit(ROOT)
    print(f"  白名单 {rep['file_count']} 个文件 / "
          f"{rep['total_mb']} MB（预算 {packaging.MAX_TOTAL_BYTES // 1024 // 1024} MB）"
          f"／最大 {rep['largest'][0]} {rep['largest'][1] // 1024} KB")
    if rep["violations"]:
        fails += len(rep["violations"])
        for v in rep["violations"][:10]:
            print(f"  FAIL  [{v['rule']}] {v['detail']}")
    else:
        print("  ok  白名单内无生成物、无绝对路径、无凭据、manifest 与包内容一致")

    # 真的装一份 copy 包，再查一遍装出来的东西
    with tempfile.TemporaryDirectory(prefix="omniailab-dist-") as td:
        result = ins.install(target=Path(td) / "skills", mode=ins.MODE_COPY)
        if not result.get("ok"):
            fails += 1
            print(f"  FAIL  copy 安装失败：{(result.get('errors') or ['-'])[0]}")
        else:
            dest = Path(result["target"])
            tree = packaging.audit_tree(dest)
            got = sum(1 for p in dest.rglob("*") if p.is_file())
            print(f"  ok  copy 包安装成功：{got} 个文件 / {tree['total_mb']} MB，"
                  "verify 通过（清单逐条对齐 + 无生成物）")
            if not tree["ok"]:
                fails += len(tree["violations"])
                for v in tree["violations"][:5]:
                    print(f"  FAIL  {v['detail']}")
        # pointer 也要能用
        ptr = ins.install(target=Path(td) / "ptr", mode=ins.MODE_POINTER)
        if ptr.get("ok"):
            print("  ok  pointer 包安装成功（SKILL.md + 指针 + 清单）")
        else:
            fails += 1
            print(f"  FAIL  pointer 安装失败：{(ptr.get('errors') or ['-'])[0]}")
    return fails


def main() -> int:
    print("OmniArchitect 完整性验证")
    print(f"项目根目录：{ROOT}")
    total = (check_paths() + check_catalogue() + check_doctor() + check_smoke()
             + check_tests() + check_v11() + check_style() + check_assets()
             + check_tables() + check_distribution())
    section("结论")
    if total == 0:
        print("  全部通过：目录完整、目录自检通过、闭环成立、测试全绿、"
              "v1.1 子系统正常、风格系统就绪、资产体积达标、表格规范达标、"
              "分发包干净")
        return 0
    print(f"  {total} 项问题，需处理")
    return 1


if __name__ == "__main__":
    sys.exit(main())
