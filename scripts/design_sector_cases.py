"""四个行业案例：S1 → S2 → S3 真实跑通，产出图纸、数据与客户提案。

不是分类演示：每个案例都走真实入口（`StageRunner`、`concept.generate_bundle`、
`G1/G2/G3` 门禁），数字来自业主原话，图纸来自 S3 的排布结果。

产物（`out/sector-round/<case>/`）：
    design-brief.md        S1 任务书
    concept-options.md     S2 概念（含行业算式、矛盾、缺口）
    diagrams/*.svg         S2 图解
    scheme-comparison.md   S3 面积表、指标、概念一致性、能力边界
    plan-A.svg/.png        方案平面（可直接看图）
    site-plan.svg/.png     总平面关系（学校 / 医院 / 酒店 / 厂房）
    landscape-plan.svg     景观总平面
    index.html             客户提案
    summary.json           本案例的关键结论

用法：
    python scripts/design_sector_cases.py            # 全部
    python scripts/design_sector_cases.py school     # 单个

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from omniarchitect import workflow                                  # noqa: E402
from omniarchitect.concept import gate as concept_gate              # noqa: E402
from omniarchitect.concept.handoff import assess_plan_gate           # noqa: E402
from omniarchitect.intake.interview import record_answer             # noqa: E402
from omniarchitect.model import Project                             # noqa: E402
from omniarchitect.presentation import html as html_mod              # noqa: E402
from omniarchitect.sector import plandraw                           # noqa: E402

OUT = ROOT / "out" / "sector-round"

CASES = {
    "school": {
        "name": "新建 24 班小学（含食堂与体育馆）",
        "constraints": {"project_type": "新建小学", "style": "现代简洁",
                        "location": "杭州", "budget_cny": 120_000_000},
        "answers": {
            "base.project_type": "新建 24 班小学，用地 20000 平方米",
            "base.needs": ("要新建一所 24 班小学，每班 45 人。教学楼 4 层，"
                           "需要学生食堂和一座体育馆，另外要有 200 米跑道。"
                           "放学时家长接送和小学生人流要分开，校园日常封闭管理。"),
            "base.site_conditions": "地块方正，20000 平方米，北侧临城市道路，南侧是居住区",
            "base.commission": "建筑方案 + 景观，室内暂不做",
        },
    },
    "hospital": {
        "name": "新建综合医院（300 床，含门诊医技）",
        "constraints": {"project_type": "新建综合医院", "style": "理性专业",
                        "location": "成都", "budget_cny": 600_000_000},
        "answers": {
            "base.project_type": "新建 300 床综合医院，日门诊 1200 人",
            "base.needs": ("新建一所 300 床综合医院，日门诊量 1200 人左右。"
                           "要设手术部和 ICU，还要有急诊与发热门诊，"
                           "门诊和住院的入口要分开，洁污流线必须分开。"),
            "base.site_conditions": "城市新区地块，约 30000 平方米，南侧城市主干道",
            "base.commission": "建筑方案，医疗工艺由医院方顾问配合",
        },
    },
    "factory": {
        "name": "新建电子制造厂房与仓储（12000 m²）",
        "constraints": {"project_type": "新建工业厂房", "style": "工业理性",
                        "location": "苏州", "budget_cny": 80_000_000},
        "answers": {
            "base.project_type": "新建工业厂房 12000 平方米，柱网 9x9 米",
            "base.needs": ("要建一座电子制造厂房，12000 平方米，柱网 9 米 × 9 米。"
                           "工序是原料入库、SMT 贴片、装配、检测、包装、出货，"
                           "每天约 40 车次进出，要有员工办公和更衣。"),
            "base.site_conditions": "工业园区地块，18000 平方米，东侧是园区道路",
            "base.commission": "建筑方案 + 总平面，工艺设备由厂方提供",
        },
    },
    "hotel": {
        "name": "既有酒店室内精装修（120 间客房）",
        "constraints": {"project_type": "酒店室内精装修", "style": "现代东方",
                        "location": "厦门", "budget_cny": 45_000_000},
        "answers": {
            "base.project_type": "既有酒店室内精装修，120 间客房",
            "base.needs": ("酒店已经建好，这次只做室内精装修。120 间客房，"
                           "要有大堂、全日餐厅和一个小宴会厅，后场布草和员工流线"
                           "不能和客人混在一起。柱网 8 米，管井位置不能改。"),
            "base.site_conditions": "既有建筑，地上 8 层，标准层进深 18 米",
            "base.commission": "只做室内，建筑与结构不动",
        },
    },
    "garden": {
        "name": "私家庭院景观（800 m²，含水景）",
        "constraints": {"project_type": "私家庭院", "style": "现代自然",
                        "location": "苏州", "budget_cny": 800_000},
        "answers": {
            "base.project_type": "独立私家庭院景观设计",
            "base.needs": ("院子 800 平方米，要做现代自然式景观。要有水景、"
                           "能坐下喝茶的地方，家里有两个小孩，平时没太多时间打理。"),
            "base.site_conditions": "方正庭院，现状平整，排水接市政",
            "base.commission": "只做景观",
        },
    },
}


def _latest_run(case_dir: Path) -> Path:
    runs = [d for d in case_dir.glob("run-*") if d.is_dir()]
    return max(runs, key=lambda d: d.stat().st_mtime) if runs else case_dir


def _shot(svg_path: Path, png_path: Path, width: int = 1280) -> bool:
    """SVG → PNG：量出 svg 自身尺寸，截元素而不是整页。

    整页截图会等字体加载后按页面高度重排，扁平 SVG 页容易在 30 s 超时；
    截 `svg` 元素既快又只含图本身。
    """
    try:
        from playwright.sync_api import sync_playwright
    except Exception:                       # noqa: BLE001
        return False
    try:
        with sync_playwright() as pw:
            b = pw.chromium.launch(channel="chrome", headless=True)
            pg = b.new_page(viewport={"width": width, "height": 900})
            pg.goto(svg_path.resolve().as_uri(), wait_until="load")
            pg.wait_for_timeout(300)
            el = pg.query_selector("svg")
            if el is None:
                b.close()
                return False
            el.screenshot(path=str(png_path), timeout=30000)
            b.close()
        return True
    except Exception:                       # noqa: BLE001
        return False


def run_case(key: str, cfg: dict) -> dict:
    out = OUT / key
    out.mkdir(parents=True, exist_ok=True)
    p = Project(project_id=key, name=cfg["name"])
    p.constraints = dict(cfg["constraints"])
    p.meta = {}
    for qid, value in cfg["answers"].items():
        record_answer(p, qid, value)

    runner = workflow.StageRunner(p, out, project_dir=out)
    s1 = runner.stage_S1()
    g1 = runner.approve("S1", by="业主", note="行业案例：业主确认任务书")
    s2 = runner.stage_S2()
    run_dir = _latest_run(out)
    payload_file = next(iter(sorted(run_dir.rglob("concept-options.json"))), None)
    payload = json.loads(payload_file.read_text(encoding="utf-8")) if payload_file else {}

    # G2：选第一套概念，走真实门禁
    g2 = {}
    concepts = payload.get("concepts") or []
    if concepts:
        concept_gate.select(p, str(concepts[0]["concept_id"]))
        g2 = runner.approve("S2", by="业主", note="选定第一套方向")

    s3 = runner.stage_S3()

    # 平面图与总平面
    pngs = []
    schemes = getattr(runner, "schemes", {}) or {}
    if schemes and "A" in schemes:
        walls = p.by_type("wall")
        for v, sch in schemes.items():
            svg = out / f"plan-{v}.svg"
            svg.write_text(plandraw.plan_svg(
                sch, title=f"{cfg['name']} · 方案{v}", base_walls=walls), encoding="utf-8")
            png = out / f"plan-{v}.png"
            if _shot(svg, png):
                pngs.append(str(png))
    for name in ("site-plan.svg", "landscape-plan.svg"):
        # S3 的产物按 run 目录归档，直接在 case 根找会漏（景观就是这种情况）
        svg = out / name
        if not svg.exists():
            found = sorted(out.rglob(name))
            svg = found[-1] if found else svg
        if svg.exists():
            png = out / name.replace(".svg", ".png")
            if _shot(svg, png, width=1200):
                pngs.append(str(png))

    g3 = {}
    try:
        g3 = runner.approve("S3", by="业主", note="行业案例：确认平面")
    except Exception as exc:                # noqa: BLE001
        g3 = {"status": "error", "error": f"{type(exc).__name__}: {exc}"}
    assess = assess_plan_gate(p)

    # 客户提案（复用 presentation/html.py）
    shortlist = next(iter(sorted(run_dir.rglob("reference-shortlist.json"))), None)
    research = (json.loads(shortlist.read_text(encoding="utf-8"))
                if shortlist else {"cases": []})
    page = html_mod.proposal(payload, out, project_name=cfg["name"],
                             research=research, project_dir=out,
                             meta=[f"模型修订 r{payload.get('revision', 1)}"],
                             with_images=False)

    return {
        "key": key,
        "project": cfg["name"],
        "s1": getattr(s1, "status", ""),
        "g1": g1.get("status"),
        "s2": getattr(s2, "status", ""),
        "g2": g2.get("status"),
        "s3": getattr(s3, "status", ""),
        "s3_error": getattr(s3, "error", "") or "",
        "s3_notes": list(getattr(s3, "notes", []) or []),
        "g3": g3.get("status"),
        "g3_blockers": [b["id"] for b in assess.get("blockers") or []],
        "g3_conditions": [c["id"] for c in assess.get("conditions") or []],
        "codes": (payload.get("taxonomy") or {}).get("codes"),
        "concepts": [{"id": c.get("concept_id"), "name": c.get("concept_name")}
                     for c in concepts],
        "proposal": str(page),
        "pngs": pngs,
    }


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    keys = [a for a in sys.argv[1:] if a in CASES] or list(CASES)
    results = []
    for key in keys:
        cfg = CASES[key]
        print(f"\n=== {key}：{cfg['name']}", flush=True)
        r = run_case(key, cfg)
        results.append(r)
        print(f"    S1 {r['s1']} / G1 {r['g1']} 　S2 {r['s2']} / G2 {r['g2']} 　"
              f"S3 {r['s3']} / G3 {r['g3']}", flush=True)
        print(f"    类型 {r['codes']}　平面 {len(r['pngs'])} 张图", flush=True)
        if r["s3_error"]:
            print(f"    S3 说明：{r['s3_error']}", flush=True)
        for n in r["s3_notes"][:3]:
            print(f"    - {n}", flush=True)
        print(f"    G3 blockers {r['g3_blockers']} / conditions {r['g3_conditions']}",
              flush=True)
    (OUT / "summary.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n产物：{OUT}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
