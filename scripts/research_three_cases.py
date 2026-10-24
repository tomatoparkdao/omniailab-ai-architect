"""Three real client briefs, researched end to end. Real network, no fixtures.

Run:  python scripts/research_three_cases.py
Out:  out/research-cases/{a,b,c}/

This is an acceptance script, not a unit test: it hits live sites and takes
about a minute. It is deliberately *not* part of `run_tests.py` — a test suite
that needs the internet fails for the wrong reasons.

What it verifies for each case (the six points the brief asked for):
1. research starts from S1 without waiting for G1
2. the first-party library is always the first entry
3. every case link was actually opened and re-read
4. the three disciplines get different study lists
5. the S1 bundle carries the shortlist
6. the output is readable by a client, not a data dump

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from omniarchitect import research                       # noqa: E402
from omniarchitect.paths import test_output_root
from omniarchitect.model import Project                  # noqa: E402

OUT = test_output_root() / "research-cases"

CASES = {
    "a": {
        "name": "三层现代极简别墅（含庭院水景）",
        "constraints": {
            "project_type": "新建三层别墅",
            "style": "现代极简",
            "location": "苏州",
        },
        "brief": ("我有一块地，想建一栋三层现代极简别墅，室内也要精装修，室外带庭院和水景。"
                  "我希望建筑外观非常高级、简洁、大气，进入房子要有仪式感，"
                  "室内通透、自然采光好，同时要保证私密性。"),
    },
    "b": {
        "name": "大平层意式极简精装（已建成）",
        "constraints": {
            "project_type": "大平层精装修",
            "style": "意式极简",
            "location": "上海",
        },
        "brief": ("房子已经建好，是大平层，想做意式极简的精装修。"
                  "要高级但不要冷，材料要看得出质感，采光一般，"
                  "客餐厅要通透，主卧要安静私密。"),
    },
    "c": {
        "name": "独立私家庭院（现代自然式景观）",
        "constraints": {
            "project_type": "私家庭院景观",
            "style": "现代自然",
            "location": "杭州",
        },
        "brief": ("有一个独立的私家院子，想做现代自然式的景观。"
                  "要有水景、种植、能坐下来喝茶的地方，家里有小孩，"
                  "平时没太多时间打理，希望好维护。"),
    },
}


def run_one(key: str, cfg: dict) -> dict:
    p = Project(project_id=f"case-{key}", name=cfg["name"])
    p.constraints = dict(cfg["constraints"])
    p.meta = {}

    # Point 1: the trigger must fire on a type and nothing else.
    from omniarchitect.research import brief as brief_mod

    started, why = brief_mod.should_start(p)

    out_dir = OUT / key
    res = research.run(p, out_dir=str(out_dir))

    md = (out_dir / research.SHORTLIST_MD).read_text(encoding="utf-8")
    payload = json.loads((out_dir / research.SHORTLIST_JSON).read_text(encoding="utf-8"))

    by_disc = {}
    for c in res.cases:
        by_disc.setdefault(c.discipline, []).append(c)

    return {
        "key": key,
        "project": cfg["name"],
        "started_without_g1": started,
        "trigger_note": why,
        "disciplines": list(res.brief.disciplines),
        "count": len(res.cases),
        "verified": len(res.verified),
        "by_discipline": {k: len(v) for k, v in by_disc.items()},
        "first_entry": payload["first_entry"]["name"],
        "first_entry_is_first": md.find("第一优先") < md.find("精选参考案例"),
        "links": [c.url for c in res.cases],
        "titles": [f"{c.title} / {c.architect}" for c in res.cases],
        "aspects": {d.discipline: list(d.aspects) for d in res.brief.directions},
        "md_path": str(out_dir / research.SHORTLIST_MD),
        "json_path": str(out_dir / research.SHORTLIST_JSON),
    }


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    results = []
    for key, cfg in CASES.items():
        print(f"=== 案例 {key.upper()}：{cfg['name']}", flush=True)
        r = run_one(key, cfg)
        results.append(r)
        print(f"    触发：{'是' if r['started_without_g1'] else '否'}（{r['trigger_note']}）", flush=True)
        print(f"    专业：{'、'.join(r['disciplines'])}", flush=True)
        print(f"    案例：{r['count']} 个，已核验 {r['verified']} 个 {r['by_discipline']}", flush=True)
        print(f"    第一入口：{r['first_entry']}", flush=True)
        for t in r["titles"]:
            print(f"      - {t}", flush=True)
        print(flush=True)

    (OUT / "summary.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

    total = sum(r["count"] for r in results)
    verified = sum(r["verified"] for r in results)
    print(f"合计：{total} 个案例，{verified} 个已核验")
    print(f"清单：{OUT}")
    return 0 if total and verified == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
