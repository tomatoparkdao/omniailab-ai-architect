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
    index.html           单页阅读版（内嵌图解，浏览器直接打开）

用法：
    python scripts/design_three_cases.py            # 联网取案例
    OMNIAILAB_NO_NETWORK=1 python scripts/design_three_cases.py   # 离网，只出概念

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import html
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from omniarchitect import workflow                              # noqa: E402
from omniarchitect.intake.interview import record_answer        # noqa: E402
from omniarchitect.model import Project                          # noqa: E402

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

    return {
        "key": key,
        "project": cfg["name"],
        "s1_status": getattr(s1, "status", ""),
        "s2_status": getattr(s2, "status", ""),
        "out": str(out),
        "run_dir": str(run_dir),
        "lead": payload.get("lead_label", ""),
        "source": payload.get("source", ""),
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


# --------------------------------------------------------------------------
# 单页阅读版：把概念文档与图解放进一个 HTML，客户直接打开就能看
# --------------------------------------------------------------------------
def _svg_inline(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    text = re.sub(r"<\?xml[^>]*\?>", "", text).strip()
    return text


def _md_blocks(md: str) -> str:
    """极简 Markdown → HTML：标题、表格、列表、引用、段落。

    只解析本仓库自己产出的那几种结构，不引入通用解析器。
    """
    out: list[str] = []
    lines = md.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        if line.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                rows.append(lines[i])
                i += 1
            cells = [[c.strip() for c in r.strip("|").split("|")] for r in rows]
            body = [r for r in cells if not all(set(c) <= set("-: ") for c in r)]
            if body:
                out.append("<table>")
                for n, r in enumerate(body):
                    tag = "th" if n == 0 else "td"
                    out.append("<tr>" + "".join(
                        f"<{tag}>{html.escape(c)}</{tag}>" for c in r) + "</tr>")
                out.append("</table>")
            continue
        if line.startswith("### "):
            out.append(f"<h3>{html.escape(line[4:])}</h3>")
        elif line.startswith("## "):
            out.append(f"<h2>{html.escape(line[3:])}</h2>")
        elif line.startswith("# "):
            # 页面已经有一个 h1（项目名）；正文里的 h1 降一级，
            # 否则一份文档会出现两个同等权重的标题。
            out.append(f"<h2>{html.escape(line[2:])}</h2>")
        elif line.startswith("> "):
            out.append(f"<blockquote>{html.escape(line[2:])}</blockquote>")
        elif line.startswith("- "):
            items = []
            while i < len(lines) and lines[i].startswith("- "):
                items.append(html.escape(lines[i][2:]))
                i += 1
            out.append("<ul>" + "".join(f"<li>{x}</li>" for x in items) + "</ul>")
            continue
        elif re.match(r"^\d+\.\s", line):
            items = []
            while i < len(lines) and re.match(r"^\d+\.\s", lines[i]):
                items.append(html.escape(re.sub(r"^\d+\.\s", "", lines[i])))
                i += 1
            out.append("<ol>" + "".join(f"<li>{x}</li>" for x in items) + "</ol>")
            continue
        else:
            out.append(f"<p>{html.escape(line)}</p>")
        i += 1
    return "\n".join(out)


PAGE = """<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<title>{title}</title>
<style>
:root {{ --ink:#1E2328; --muted:#6B7280; --rule:#D6D9DD; --bg:#FBFBFA;
         --accent:#3F7D58; }}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:var(--bg); color:var(--ink);
        font-family:'Microsoft YaHei','Noto Sans SC','PingFang SC',sans-serif;
        line-height:1.75; }}
main {{ max-width:1180px; margin:0 auto; padding:48px 28px 96px; }}
h1 {{ font-size:30px; margin:0 0 6px; }}
h2 {{ font-size:22px; margin:44px 0 12px; padding-bottom:8px;
      border-bottom:1px solid var(--rule); }}
h3 {{ font-size:17px; margin:28px 0 10px; color:var(--accent); }}
p, li {{ font-size:14.5px; }}
table {{ border-collapse:collapse; width:100%; margin:12px 0 20px;
         font-size:13.5px; background:#fff; }}
th, td {{ border:1px solid var(--rule); padding:8px 10px; text-align:left;
          vertical-align:top; }}
th {{ background:#F2F3F1; font-weight:600; }}
blockquote {{ margin:12px 0; padding:10px 14px; border-left:3px solid var(--accent);
              background:#F4F7F4; color:#374151; font-size:13.5px; }}
.fig {{ margin:18px 0 26px; background:#fff; border:1px solid var(--rule);
        border-radius:10px; padding:12px; overflow:auto; }}
.fig svg {{ display:block; width:100%; height:auto; }}
.cap {{ font-size:12.5px; color:var(--muted); margin-top:6px; }}
.meta {{ color:var(--muted); font-size:13px; margin-bottom:8px; }}
</style></head>
<body><main>
<h1>{title}</h1>
<div class="meta">{meta}</div>
{body}
</main></body></html>
"""


def build_html(key: str, cfg: dict, result: dict) -> Path:
    out = Path(result["run_dir"])
    md_path = next(iter(sorted(out.rglob("concept-options.md"))), None)
    md = md_path.read_text(encoding="utf-8") if md_path else ""

    # 图解按 concept_id 分组，插到对应概念段落之后
    svgs = sorted(p for d in out.rglob("concept-diagrams") for p in d.glob("*.svg"))
    by_concept: dict[str, list[Path]] = {}
    for s in svgs:
        cid = s.stem.split("-")[0].upper() + "-" + s.stem.split("-")[1].upper() \
            if "-" in s.stem else s.stem
        by_concept.setdefault(cid.upper(), []).append(s)

    body = _md_blocks(md)
    titles = {"functional": "功能关系图", "zoning": "分区图", "circulation": "动线概念图",
              "daylight": "采光策略图", "sequence": "空间序列图", "massing": "体量概念图",
              "section": "剖面与楼层图", "landscape": "景观结构图"}
    for cid, files in by_concept.items():
        blocks = []
        for f in files:
            kind = f.stem.split("-", 2)[-1] if f.stem.count("-") >= 2 else f.stem
            label = titles.get(kind, kind)
            blocks.append(
                f'<div class="fig">{_svg_inline(f)}'
                f'<div class="cap">{html.escape(label)}（确定性 SVG，非按比例）</div></div>')
        marker = f"<h2>{cid}"
        idx = body.find(marker)
        if idx == -1:
            body += "\n<h2>图解 · {}</h2>".format(cid) + "".join(blocks)
        else:
            # 插在标题之后：读者先看到方案名，再看到图，最后读文字。
            after = body.find("</h2>", idx)
            after = len(body) if after == -1 else after + len("</h2>")
            body = body[:after] + "\n" + "".join(blocks) + body[after:]

    ref = next(iter(sorted(out.rglob("reference-shortlist.md"))), None)
    if ref:
        ref_md = ref.read_text(encoding="utf-8")
        # 清单自己是独立文档，有一个 h1；嵌进来要降一级，否则页面出现两个 h1
        ref_md = re.sub(r"^# ", "## ", ref_md, count=1, flags=re.M)
        body += "\n" + _md_blocks(ref_md)

    meta_bits = [f"主导专业：{result.get('lead') or '—'}",
                 f"概念来源：{'按本项目推敲' if result.get('source') == 'deliberated' else '原型经验库'}",
                 f"S1 {result.get('s1_status')} ／ S2 {result.get('s2_status')}"]
    page = PAGE.format(title=html.escape(cfg["name"]),
                       meta="　·　".join(html.escape(x) for x in meta_bits),
                       body=body)
    path = OUT / key / "index.html"
    path.write_text(page, encoding="utf-8")
    return path


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    online = os.environ.get("OMNIAILAB_NO_NETWORK", "").strip().lower() not in (
        "1", "true", "yes", "on")
    print(f"案例研究：{'联网' if online else '离网（不取案例）'}", flush=True)

    results = []
    for key, cfg in CASES.items():
        print(f"\n=== {key}：{cfg['name']}", flush=True)
        r = run_case(key, cfg)
        build_html(key, cfg, r)
        results.append(r)
        print(f"    S1 {r['s1_status']} ／ S2 {r['s2_status']}　主导：{r['lead']}"
              f"　来源：{r['source']}", flush=True)
        for c in r["concepts"]:
            print(f"    {c['id']} {c['name']}（{c['family']}）"
                  f" 图 {len(c['diagrams'])} 张　案例 {len(c['cases'])} 个", flush=True)

    (OUT / "summary.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n产物：{OUT}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
