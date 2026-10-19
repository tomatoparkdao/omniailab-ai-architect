"""三案例端到端：真实跑 S1 → G1 → S2，产出客户可直接阅读的设计成果。

不是演示脚本：它调用的是 `workflow.StageRunner` 与 `concept.generate_bundle`
这两个生产入口，问诊答案通过 `record_answer` 写进项目状态，G1 通过
`runner.approve()` 走真实门禁。唯一"人造"的部分是三位业主的诉求文本——那本来
就该由业主提供。

产物（每个案例一份目录）：
    design-brief.md      S1 任务书
    concept-options.md   S2 概念方案（含六问、序列、楼层、分区、技术协同）
    diagrams/*.svg       体量 / 剖面 / 景观结构 / 功能 / 动线 / 采光 / 序列
    deck.pptx            提案
    reference-shortlist.md  案例参考（联网时）
    index.html           客户提案：图文案例卡 + 图解 + 链接可点
    online-doc/          可导入飞书 / Notion 的文档包（Markdown + 图 + zip）

用法：
    python scripts/design_three_cases.py            # 联网取案例
    OMNIAILAB_NO_NETWORK=1 python scripts/design_three_cases.py   # 离网，只出概念

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from omniarchitect import workflow                              # noqa: E402
from omniarchitect.intake.interview import record_answer        # noqa: E402
from omniarchitect.model import Project                          # noqa: E402
from omniarchitect.presentation import html as html_mod, online_doc  # noqa: E402

OUT = ROOT / "out" / "design-round1"

CASES = {
    "A-villa": {
        "name": "三层现代极简别墅（建筑 + 室内 + 庭院整体）",
        "constraints": {"project_type": "新建三层别墅", "style": "现代极简",
                        "location": "苏州", "budget_cny": 9_000_000},
        "answers": {
            "base.project_type": "新建三层别墅",
            "base.needs": ("我有一块地，想建一栋三层现代极简别墅，室内也要精装修，"
                           "室外带庭院和水景。我希望建筑外观非常高级、简洁、大气，"
                           "进入房子要有仪式感，室内通透、自然采光好，同时要保证私密性。"),
            "base.feeling": ("外观高级简洁大气，进门要有仪式感，室内通透自然采光好，"
                             "同时保证私密"),
            "base.site_conditions": "独立地块，方正，南侧可看景，北侧临村道",
            "base.structure": "新建框架结构，可做悬挑与转换，需结构专业复核",
        },
    },
    "B-flat": {
        "name": "既有大平层精装修（只委托室内）",
        "constraints": {"project_type": "大平层精装修", "style": "意式极简",
                        "location": "上海", "budget_cny": 1_800_000},
        "answers": {
            "base.project_type": "大平层精装修",
            "base.needs": ("房子已经建好，是大平层，150 平米，想做意式极简的精装修。"
                           "要高级但不要冷，材料要看得出质感，客餐厅要通透，"
                           "主卧要安静私密。室内设计是这次唯一的委托，建筑本体不动。"),
            "base.feeling": "高级但不要冷，看得出质感，客餐厅通透，主卧安静私密",
            "base.site_conditions": "已建成住宅，承重墙与管井位置固定，外围护不动",
            "base.structure": "既有结构，不拆改承重构件",
        },
    },
    "C-garden": {
        "name": "独立私家庭院（只委托景观）",
        "constraints": {"project_type": "私家庭院景观", "style": "现代自然",
                        "location": "杭州", "budget_cny": 600_000},
        "answers": {
            "base.project_type": "私家庭院景观",
            "base.needs": ("有一个独立的私家院子，想做现代自然式的景观。要有水景、种植、"
                           "能坐下来喝茶的地方，家里有小孩，平时没太多时间打理，"
                           "希望好维护。这次只做院子，建筑和室内不动。"),
            "base.feeling": "现代自然、安静、好打理",
            "base.site_conditions": "独立庭院，现状基本平整，排水接市政，有自来水与电源",
        },
    },
}


def _latest_run(case_dir: Path) -> Path:
    """最新的 run 目录。

    这里刻意**不删除**上一次的产物：一是不做破坏性操作，二是保留历史可以对比
    「这次改动到底改变了什么」。读取时只认最新一次。
    """
    runs = [d for d in case_dir.glob("run-*") if d.is_dir()]
    return max(runs, key=lambda d: d.stat().st_mtime) if runs else case_dir


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
    runner.approve("S1", by="业主", note="三案例实测：业主确认任务书")
    s2 = runner.stage_S2()

    run_dir = _latest_run(out)
    found = sorted(run_dir.rglob("concept-options.json"))
    payload = (json.loads(found[0].read_text(encoding="utf-8")) if found else {})

    shortlist = next(iter(sorted(run_dir.rglob("reference-shortlist.json"))), None)
    research = (json.loads(shortlist.read_text(encoding="utf-8"))
                if shortlist else {"cases": []})

    # 客户提案：案例带图、链接可点、权利分层（presentation/html.py）
    page = html_mod.proposal(payload, out, project_name=cfg["name"],
                             research=research, project_dir=out,
                             meta=[f"模型修订 r{payload.get('revision', 1)}"])

    # 在线文档包：飞书 / Notion 各一套可导入的 Markdown + 图（不联网、不发链接）
    # 生产入口显式带图：提案与文档包里要用素材库的真实空间意向。
    package = online_doc.build_package(
        p, payload, research, out / "online-doc", project_name=cfg["name"],
        project_dir=out, run_dir=run_dir, with_images=True)

    return {
        "key": key,
        "project": cfg["name"],
        "s1_status": getattr(s1, "status", ""),
        "s2_status": getattr(s2, "status", ""),
        "out": str(out),
        "run_dir": str(run_dir),
        "lead": payload.get("lead_label", ""),
        "source": payload.get("source", ""),
        "proposal": str(page),
        "doc_package": package,
        "concepts": [
            {
                "id": c.get("concept_id"),
                "name": c.get("concept_name"),
                "family": (c.get("spatial_prototype") or {}).get("family"),
                "prototype": (c.get("spatial_prototype") or {}).get("prototype_id"),
                "parti": (c.get("deliberation") or {}).get("parti", ""),
                "opportunity": (c.get("deliberation") or {}).get("key_opportunity", ""),
                "cases": [r.get("title") for r in
                          ((c.get("references") or {}).get("cases") or [])],
                "diagrams": [d.get("kind") for d in (c.get("diagrams") or [])],
            }
            for c in payload.get("concepts") or []
        ],
    }


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    online = os.environ.get("OMNIAILAB_NO_NETWORK", "").strip().lower() not in (
        "1", "true", "yes", "on")
    print(f"案例研究：{'联网' if online else '离网（不取案例）'}", flush=True)

    results = []
    for key, cfg in CASES.items():
        print(f"\n=== {key}：{cfg['name']}", flush=True)
        r = run_case(key, cfg)
        results.append(r)
        print(f"    S1 {r['s1_status']} ／ S2 {r['s2_status']}　主导：{r['lead']}"
              f"　来源：{r['source']}", flush=True)
        for c in r["concepts"]:
            print(f"    {c['id']} {c['name']}（{c['family']}）"
                  f" 图 {len(c['diagrams'])} 张　案例 {len(c['cases'])} 个", flush=True)
        for carrier, info in (r["doc_package"]["carriers"] or {}).items():
            print(f"    文档包 {info['label']}：{info['pages']} 页 / "
                  f"{info['assets']} 个附件 → {info['root']}", flush=True)

    (OUT / "summary.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n产物：{OUT}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
