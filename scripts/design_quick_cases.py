"""三个项目的概念汇报验收：公共建筑 / 室内 / 景观。

每个项目只从**一句客户需求**开始，走真实的 S1 → G1 → S2：不预先给几何、
不预先给风格、不预先挑参考。要看的是：

1. S1 是否只问该问的，并给出一页设计定位；
2. S2 是否主动取了参考（取不到就说明原因），而不是等指令；
3. 汇报是否 8–12 页、图为主、每页只讲一件事；
4. PPTX 与 HTML 是否真的能打开、是同一份内容；
5. 概念动画是否真的能在浏览器里播。

产物（`out/concept-round/<case>/`）：
    design-position.md          S1 一页判断
    02-concept/concept-proposal.html   客户版汇报（可翻页）
    02-concept/concept-proposal.pptx   同一份内容的可编辑 PPTX
    02-concept/concept-motion.html     体块演变动画（可播放）
    02-concept/concept-proposal.md     逐页文字稿
    shots/p01.png …            逐页截图（审阅用）
    summary.json               本案例结论

用法：
    python scripts/design_quick_cases.py            # 全部
    python scripts/design_quick_cases.py school     # 单个

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from omniarchitect import workflow                              # noqa: E402
from omniarchitect.paths import test_output_root
from omniarchitect.intake.interview import record_answer        # noqa: E402
from omniarchitect.model import Project                         # noqa: E402

OUT = test_output_root() / "concept-round"

CASES = {
    "school": {
        "name": "新建 24 班小学",
        "client_says": ("要建一所 24 班小学，每班 45 人，用地 20000 平方米，北侧临城市道路，"
                        "南侧是居住区。要有食堂和一座体育馆，放学接送不要和小学生挤在一起。"),
        "constraints": {"project_type": "新建小学", "location": "杭州",
                        "budget_cny": 120_000_000},
        "answers": {
            "base.project_type": "新建 24 班小学，用地 20000 平方米",
            "base.needs": ("24 班小学，每班 45 人。要学生食堂和一座体育馆，另外要有 200 米跑道。"
                           "放学时家长接送和小学生人流要分开，校园日常封闭管理。"),
            "base.site_conditions": "地块方正，20000 平方米，北侧临城市道路，南侧是居住区",
            "base.commission": "建筑方案 + 景观，室内暂不做",
        },
    },
    "hotel": {
        "name": "既有酒店室内精装修（120 间客房）",
        "client_says": ("酒店已经建好，这次只做室内精装修。120 间客房，要有大堂、全日餐厅和"
                        "一个小宴会厅，后场布草和员工流线不能和客人混在一起。柱网 8 米，"
                        "管井位置不能改。喜欢安静、暖一点的东方感。"),
        "constraints": {"project_type": "酒店室内精装修", "style": "现代东方",
                        "location": "厦门", "budget_cny": 45_000_000},
        "answers": {
            "base.project_type": "既有酒店室内精装修，120 间客房",
            "base.needs": ("酒店已经建好，这次只做室内精装修。120 间客房，要有大堂、全日餐厅和"
                           "一个小宴会厅，后场布草和员工流线不能和客人混在一起。"
                           "柱网 8 米，管井位置不能改。"),
            "base.site_conditions": "既有建筑，地上 8 层，标准层进深 18 米",
            "base.commission": "只做室内，建筑与结构不动",
        },
    },
    "garden": {
        "name": "私家庭院景观（800 m²）",
        "client_says": ("院子 800 平方米，想做现代自然式。要有水景、能坐下喝茶的地方，"
                        "家里两个小孩，平时没太多时间打理。"),
        "constraints": {"project_type": "私家庭院", "style": "现代自然",
                        "location": "苏州", "budget_cny": 800_000},
        "answers": {
            "base.project_type": "独立私家庭院景观设计",
            "base.needs": ("院子 800 平方米，要做现代自然式景观。要有水景、能坐下喝茶的地方，"
                           "家里有两个小孩，平时没太多时间打理。"),
            "base.site_conditions": "方正庭院，现状平整，排水接市政",
            "base.commission": "只做景观",
        },
    },
}


def _latest(case_dir: Path, pattern: str) -> Path | None:
    hits = sorted(case_dir.rglob(pattern), key=lambda p: p.stat().st_mtime)
    return hits[-1] if hits else None


def _shots(html: Path, out: Path, limit: int = 12) -> list[str]:
    out.mkdir(parents=True, exist_ok=True)
    try:
        from playwright.sync_api import sync_playwright
    except Exception:                      # noqa: BLE001
        return []
    got: list[str] = []
    try:
        with sync_playwright() as pw:
            b = pw.chromium.launch(channel="chrome", headless=True)
            pg = b.new_page(viewport={"width": 1360, "height": 800})
            pg.goto(html.resolve().as_uri(), wait_until="load")
            pg.wait_for_timeout(1200)
            for i, el in enumerate(pg.query_selector_all(".page")[:limit], 1):
                p = out / f"p{i:02d}.png"
                el.screenshot(path=str(p), timeout=30000)
                got.append(str(p))
            b.close()
    except Exception:                      # noqa: BLE001
        return got
    return got


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
    g1 = runner.approve("S1", by="业主", note="确认任务书")
    s2 = runner.stage_S2()

    html = _latest(out, "concept-proposal.html")
    pptx = _latest(out, "concept-proposal.pptx")
    motion = _latest(out, "concept-motion.html")
    pos = _latest(out, "design-position.md")
    shots = _shots(html, out / "shots") if html else []
    payload = _latest(out, "concept-proposal.json")
    data = json.loads(payload.read_text(encoding="utf-8")) if payload else {}

    summary = {
        "key": key,
        "name": cfg["name"],
        "client_says": cfg["client_says"],
        "s1_notes": list(s1.notes),
        "g1": g1.get("status") if isinstance(g1, dict) else str(g1),
        "design_position": pos.read_text(encoding="utf-8") if pos else "",
        "s2_notes": list(s2.notes),
        "pages": data.get("pages") or [],
        "page_count": (data.get("files") or {}).get("pages", 0),
        "recommended": data.get("recommended", ""),
        "alternative": data.get("alternative", ""),
        "curation": data.get("curation") or {},
        "files": {
            "html": str(html) if html else "",
            "pptx": str(pptx) if pptx else "",
            "motion": str(motion) if motion else "",
            "position": str(pos) if pos else "",
        },
        "shots": shots,
    }
    (out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1),
                                      encoding="utf-8")
    return summary


def main(argv: list[str]) -> int:
    keys = [a for a in argv[1:] if a in CASES] or list(CASES)
    rows = []
    for k in keys:
        r = run_case(k, CASES[k])
        rows.append(r)
        print(f"[{k}] {r['page_count']} 页　推荐 {r['recommended']}／备选 {r['alternative']}　"
              f"参考 {r['curation'].get('count', 0)} 张　截图 {len(r['shots'])} 张", flush=True)
        for n in r["s2_notes"][:2]:
            print(f"    - {n}", flush=True)
    (OUT / "summary.json").write_text(
        json.dumps([{k: v for k, v in r.items() if k != "design_position"} for r in rows],
                   ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
