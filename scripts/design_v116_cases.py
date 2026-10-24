"""v1.16 局部修正的四个项目验收：住宅 / 办公 / 酒店 / 庭院。

只回答四个问题：

1. 图版是否符合真实委托类型（住宅里不出现教学，办公里不出现客房）；
2. 核心功能标签是否准确且可见（入口、公共核、大堂、后场、水景、茶座）；
3. 同一功能在主图与四步图里是否同一位置；
4. 图纸与概念文字是否一致（旱溪方案第四步不能叫"水景"）。

每个项目都从一句客户需求走真实 S1 → G1 → S2，不预置几何与风格。
产物在 `out/v116/<case>/`：每套方向的 `plate-*.png` / `steps-*.png`、
汇报的逐页截图 `shots/p*.png`、`summary.json`。

用法：
    python scripts/design_v116_cases.py            # 全部
    python scripts/design_v116_cases.py home office

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from omniarchitect import workflow                              # noqa: E402
from omniarchitect.paths import test_output_root
from omniarchitect.concept import evolution as evo              # noqa: E402
from omniarchitect.concept import plate as plate_mod            # noqa: E402
from omniarchitect.concept import proposal as prop              # noqa: E402
from omniarchitect.intake.interview import record_answer        # noqa: E402
from omniarchitect.model import Project                         # noqa: E402

OUT = test_output_root() / "v116"

CASES = {
    "home": {
        "name": "150 m² 住宅家装",
        "discipline": "interior",
        "constraints": {"project_type": "住宅室内装修", "location": "成都",
                        "budget_cny": 600_000},
        "answers": {
            "base.project_type": "150 平方米三居室住宅室内装修，毛坯交付",
            "base.needs": ("一家四口住，两个孩子分别 7 岁和 3 岁。最想解决三件事："
                           "进门没有地方放东西；做饭时看不到孩子；主卧想要一个能关起来的书房。"),
            "base.site_conditions": "毛坯房，南北通透，承重墙在图纸上标了，物业不许改外墙",
            "base.commission": "只做室内硬装与固定家具",
        },
    },
    "office": {
        "name": "500 m² 企业办公室",
        "discipline": "interior",
        "constraints": {"project_type": "办公空间室内设计", "location": "深圳",
                        "budget_cny": 3_000_000},
        "answers": {
            "base.project_type": "500 平方米企业办公室室内设计，租赁写字楼",
            "base.needs": ("60 人办公，两年内扩到 80 人。销售团队电话多，需要能关起来；"
                           "研发要安静，最好和销售分开；客户来访只到接待区，不进展厅以外的区域。"),
            "base.site_conditions": "租赁楼层，物业不许动消防与空调主管，隔墙可拆",
            "base.commission": "只做室内",
        },
    },
    "hotel": {
        "name": "120 间客房酒店室内精装",
        "discipline": "interior",
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
    "school": {
        "name": "24 班小学新建",
        "discipline": "architecture",
        "constraints": {"project_type": "小学教学楼", "location": "杭州",
                        "budget_cny": 120_000_000},
        "answers": {
            "base.project_type": "24 班完全小学新建，含教学楼、食堂与体育馆",
            "base.needs": ("24 个班，每年级 4 个班。教学楼要能独立管理，家长接送不进教学区；"
                           "食堂要能分两批错峰就餐；体育馆放学后对社区开放，需要单独出入口。"
                           "用地北侧是城市干道，噪音要注意。"),
            "base.site_conditions": "新征用地约 2.4 公顷，场地基本平整，北侧临城市干道",
            "base.commission": "建筑方案到施工图配合",
        },
    },
    "garden": {
        "name": "800 m² 私家庭院",
        "discipline": "landscape",
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


def _missing_in(svg: Path) -> list[str]:
    """图注里的"未放置标注"清单。空 = 这张图的锚点标签都画上了。"""
    text = svg.read_text(encoding="utf-8")
    got = re.search(r"未放置标注：([^<]+)", text)
    return [x for x in got.group(1).split("、") if x] if got else []


def _render_plates(case_dir: Path, concepts: list[dict], discipline: str,
                   sector: str) -> list[dict]:
    """每一套方向都出一张主图 + 一张四步图，并记下缺了哪些标签。"""
    out_dir = case_dir / "plates"
    out_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []
    for c in concepts:
        cid = str(c.get("concept_id") or "x").lower()
        main = plate_mod.write(c, out_dir, discipline=discipline, sector=sector,
                               width=1200, height=496, stem=f"plate-{cid}")
        steps = evo.strip(c, discipline, width=700, height=470, sector=sector)
        steps_path = out_dir / f"steps-{cid}.svg"
        if steps:
            steps_path.write_text(steps, encoding="utf-8")
        rows.append({
            "concept_id": c.get("concept_id"),
            "name": c.get("concept_name"),
            "family": (c.get("spatial_prototype") or {}).get("family"),
            "layout": (c.get("spatial_prototype") or {}).get("plan_layout")
            or (c.get("spatial_prototype") or {}).get("massing_kind"),
            "plate": prop._png(main, out_dir / "png") if main else "",   # noqa: SLF001
            "steps": prop._png(steps_path, out_dir / "png") if steps else "",  # noqa: SLF001
            "missing_labels": _missing_in(Path(main)) if main else [],
            "step_names": [s.name for s in evo.plan(c, discipline, sector=sector).steps],
        })
    return rows


def _shots(html: Path, out: Path, limit: int = 12) -> list[str]:
    """逐页截图：审图要看的是渲染出来的那一页，不是 SVG 源码。"""
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
            # 底部的翻页条与左右按钮是查看器自己的控件，属于浏览器壳，不属于版面。
            # 不关掉，元素截图会把它们一起框进来，看着像图注被裁掉了。
            pg.add_style_tag(content="#bar,#nav{display:none!important}")
            pg.wait_for_timeout(120)
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
    runner.stage_S1()
    runner.approve("S1", by="业主", note="确认任务书")
    runner.stage_S2()

    options = _latest(out, "concept-options.json")
    data = json.loads(options.read_text(encoding="utf-8")) if options else {}
    concepts = data.get("concepts") or []
    sector = ""
    try:
        from omniarchitect.sector import brief as sb

        sector = sb.from_project(p).sector
    except Exception:                      # noqa: BLE001  非行业项目就是普通项目
        sector = ""

    plates = _render_plates(out, concepts, cfg["discipline"], sector)
    html = _latest(out, "concept-proposal.html")
    # 先交出渲染用的浏览器单例，再另起一个上下文截图：
    # 同一个线程里两个 Playwright 实例会互相踢，截图会静默失败。
    prop.release()
    shots = _shots(html, out / "shots") if html else []
    pptx = _latest(out, "concept-proposal.pptx")
    motion = _latest(out, "concept-motion.html")
    payload = _latest(out, "concept-proposal.json")
    pdata = json.loads(payload.read_text(encoding="utf-8")) if payload else {}
    summary = {
        "key": key, "name": cfg["name"], "discipline": cfg["discipline"],
        "sector": sector,
        "recommended": data.get("recommended") or pdata.get("recommended", ""),
        "pages": (pdata.get("files") or {}).get("pages", 0),
        "page_titles": [f"{x.get('title', '')}" for x in pdata.get("pages") or []],
        "plates": plates,
        "files": {"html": str(html) if html else "", "pptx": str(pptx) if pptx else "",
                  "motion": str(motion) if motion else ""},
        "shots": shots,
    }
    (out / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    return summary


def main(argv: list[str]) -> int:
    keys = [a for a in argv[1:] if a in CASES] or list(CASES)
    rows = []
    for k in keys:
        r = run_case(k, CASES[k])
        rows.append(r)
        print(f"[{k}] {r['pages']} 页　方向 {len(r['plates'])} 套　推荐 "
              f"{r['recommended']}", flush=True)
        for pl in r["plates"]:
            print(f"    {pl['concept_id']} {pl['name']}｜{pl['step_names']}｜缺标注 "
                  f"{pl['missing_labels'] or '无'}", flush=True)
    prop.release()
    (OUT / "summary.json").write_text(
        json.dumps([{k: v for k, v in r.items() if k != "page_titles"} for r in rows],
                   ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
