"""S2 概念提案的可编辑 PPTX。

版式原则：图先于字。一页只讲一件事，文字控制在可读的条数内；图解与色板以
文件形式随提案附上，页面上引用文件名而不是塞进大段说明。

图片状态如实标注：已生成的写 `已生成`，未生成的写 `待平台`，**不放占位效果图**。
业主分不清"概念意象"与"你家的效果图"时，后面所有阶段都会被误解。

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from ..presentation.layouts import Deck, Slide, new_deck
from ..presentation.pptx_writer import write_html, write_markdown, write_pptx

DECK_KIND = "concept-options"


def _short(text: str, limit: int = 96) -> str:
    t = str(text or "").strip().replace("\n", " ")
    return t if len(t) <= limit else t[:limit - 1] + "…"


def _reference_slide(concept: Dict[str, Any]) -> Optional[Slide]:
    """One page of real cases for this concept — links only, no photographs.

    The four questions are printed in full because that is the part the client
    is actually deciding on: what we borrowed, how it becomes *their* scheme,
    and what must not be copied. If there is no case, there is no page; an
    empty page with the word "reference" on it would read as if we had one.
    """
    refs = (concept.get("references") or {}).get("cases") or []
    if not refs:
        return None

    rows: List[List[str]] = []
    for r in refs[:2]:
        rows.append([_short(str(r.get("title") or ""), 30),
                     _short(str(r.get("architect") or "—"), 20),
                     _short(str(r.get("url") or ""), 46)])

    bullets: List[str] = []
    first = refs[0]
    for label, key in (("为什么参考", "why"), ("借什么", "borrow"),
                       ("怎么变成你的方案", "transform"), ("不能照搬", "limits")):
        vals = first.get(key)
        if isinstance(vals, str):
            vals = [vals]
        for v in (vals or [])[:1]:
            if v:
                bullets.append(f"{label}：{_short(str(v), 88)}")

    return Slide(
        kind="analysis",
        kicker=f"{concept['concept_id']} · 参考案例",
        title=f"{concept['concept_name']} · 参考哪些真实案例",
        subtitle="点开链接可看原项目的实景照片",
        table_header=["案例", "事务所", "链接"],
        table=rows,
        bullets=bullets,
        notes=("图为第三方作品，权利属原作者与摄影师；本页只给链接，不嵌入图片。"
               "参考案例用于讨论方向，不代表本项目效果图。"),
    )


def build(project: Any, ctx: Any, concept_set: Dict[str, Any],
          comparison: Dict[str, Any], moodboards: Dict[str, Dict[str, Any]],
          diagrams: Dict[str, List[Dict[str, str]]],
          visual: Optional[Dict[str, Any]] = None) -> Deck:
    """Assemble the proposal. One page per idea; no page that only holds prose."""
    deck = new_deck(DECK_KIND, project,
                    title=f"{getattr(project, 'name', '') or project.project_id} · 概念设计提案",
                    subtitle=f"三套方向 · {ctx.profile_label}")
    concepts = concept_set.get("concepts") or []
    rec = comparison.get("recommendation") or {}
    by_id = {c["concept_id"]: c for c in concepts}

    deck.slides.append(Slide(
        kind="cover",
        kicker="CONCEPT DESIGN · S2",
        title=f"{getattr(project, 'name', '') or project.project_id}",
        subtitle=f"概念设计提案 · {ctx.profile_label} · r{project.revision}",
        bullets=["三套空间策略方向，同一套已确认任务书",
                 "每套含空间图解、材料与配色、代价与风险", "请在 G2 明确选择其中一套"],
        notes="G2 需要业主确认的是 concept_id，不是一个风格名。",
    ))

    deck.slides.append(Slide(
        kind="agenda", title="这份提案怎么读",
        bullets=["先看任务书与设计机会：我们要解决什么",
                 "再看三个方向：它们在空间组织上哪里不同",
                 "然后看比较与推荐：各自的代价",
                 "最后是 G2 确认页：需要你决定的具体事项"],
    ))

    opp_lines = [f"{o['opportunity_id']}　{_short(o['problem'], 60)}"
                 for o in (ctx.opportunities or [])][:5]
    deck.slides.append(Slide(
        kind="summary", title="已确认的任务书与设计机会",
        kicker="FROM S1 · 已通过 G1",
        bullets=[
            f"项目类型：{ctx.profile_label}　资料精度：{ctx.precision}",
            (f"可用面积：{ctx.area_available_m2:.0f} m²　" if ctx.area_available_m2
             else "可用面积：无几何数据　")
            + (f"需求面积：{ctx.target_area_m2:.0f} m²" if ctx.target_area_m2
               else "需求面积未量化"),
            f"业主指定风格：{ctx.style_preference or '未指定'}",
            f"S1 识别到 {len(ctx.opportunities)} 项设计机会，本轮必须回应",
            "限制：" + ("；".join(u["statement"] for u in ctx.uncertainty[:2]) or "无阻断项"),
        ],
        notes="机会条目来自 S1 的 design-opportunities.md，不是本轮编的。",
    ))
    if opp_lines:
        deck.slides.append(Slide(kind="analysis", title="S1 的设计机会（本轮的设计起点）",
                                 bullets=opp_lines,
                                 notes="每一套方向都要说明它回应了哪几条。"))

    deck.slides.append(Slide(
        kind="section", kicker="PART 1", title="三个方向",
        bullets=[f"{c['concept_id']} · {c['concept_name']}：{c['role_label']}" for c in concepts],
        notes="三个方向的空间家族不同；若相同，说明生成有问题。",
    ))

    for c in concepts:
        p = c.get("spatial_prototype") or {}
        deck.slides.append(Slide(
            kind="concept",
            kicker=f"{c['concept_id']} · {c['role_label']}",
            title=c["concept_name"],
            subtitle=c["concept_statement"],
            bullets=[
                f"空间家族：{p.get('family_zh', '')}　原型：{p.get('prototype_id', '')}",
                f"要解决的问题：{_short(c['design_problem'], 70)}",
                f"体验：{_short(c['user_experience'], 70)}",
            ],
            notes="；".join(c.get("evidence") or [])[:400],
        ))
        deck.slides.append(Slide(
            kind="analysis", title=f"{c['concept_id']} · 空间策略",
            bullets=[_short(p.get("spatial_logic", ""), 110),
                     f"动线：{_short(p.get('circulation', ''), 100)}",
                     f"分区：{_short(p.get('zoning', ''), 100)}",
                     f"采光：{_short(p.get('daylight', ''), 100)}"],
            notes="图解文件：" + "、".join(d["kind"] for d in diagrams.get(c["concept_id"], [])),
        ))

        mb = moodboards.get(c["concept_id"]) or {}
        colour = ((mb.get("slots") or {}).get("colour") or {}).get("entries") or []
        deck.slides.append(Slide(
            kind="materials",
            kicker=c["concept_id"],
            title=f"{c['concept_name']} · 材料与配色",
            subtitle=f"风格：{' + '.join(c.get('style_labels') or [])}　"
                     f"配色关系：{(c.get('aesthetic_policy') or {}).get('ratio_rule', '')}",
            table_header=["颜色", "色值", "占比"],
            table=[[e["name"], e["hex"], f"{e['pct']}%" if e.get("pct") else "—"]
                   for e in colour[:5]],
            bullets=[f"{m['name']} — {_short(m.get('application', ''), 40)}"
                     for m in (c.get("material_direction") or [])][:4],
            notes=f"色板文件：{Path(mb.get('board_svg', '')).name or '未生成'}",
        ))
        deck.slides.append(Slide(
            kind="perspective", kicker=c["concept_id"], title=f"{c['concept_name']} · 视觉与代价",
            bullets=[f"光：{_short(x, 80)}" for x in (c.get("lighting_direction") or [])][:3]
                    + [f"造价：{_short(c.get('cost_impact', ''), 80)}",
                       f"维护：{_short(c.get('maintenance_impact', ''), 80)}",
                       f"取舍：{_short('；'.join(c.get('tradeoffs') or []), 100)}"],
            notes="本页为方向说明，不含 AI 生成图；概念意象图状态见视觉任务页。",
        ))
        # 参考案例页：每套方向都要能指着一个真实案例说清"借什么、怎么变、什么不照搬"。
        # 页面上只有链接，没有第三方图片——图的权利不在我们手里。
        ref_slide = _reference_slide(c)
        if ref_slide is not None:
            deck.slides.append(ref_slide)

    # 比较
    rows: List[List[str]] = []
    names = [r["name"] for r in comparison.get("criteria") or []]
    for e in comparison.get("evaluations") or []:
        cells = [str(r["score"]) if r.get("evaluated") else "—" for r in e["rows"]]
        rows.append([f"{e['concept_id']} {by_id.get(e['concept_id'], {}).get('concept_name', '')}"]
                    + cells + [f"{e['weighted']}"])
    deck.slides.append(Slide(
        kind="plan_compare", title="方案比较（只在有证据的项上打分）",
        table_header=["方向"] + names + ["加权"],
        table=rows,
        bullets=["「—」= 资料不足，未评估；不折算成中间分",
                 "分数用于呈现取舍，不替代决策"],
        notes="未评估项比例过高时，分数不足以拉开差距，请看文字说明。",
    ))

    deck.slides.append(Slide(
        kind="decisions", title="总设计师推荐",
        subtitle=f"推荐：{rec.get('concept_id', '')} {rec.get('concept_name', '')}",
        bullets=[_short(x, 96) for x in (rec.get("rationale") or [])][:4]
                + [f"不优先 {w['concept_id']}：{_short(w['reason'], 80)}" for w in (rec.get("why_not") or [])][:2],
        notes="推荐为专业意见，最终由业主决定。",
    ))

    visual = visual or {}
    deck.slides.append(Slide(
        kind="open_items", title="视觉成果与真实状态",
        bullets=[
            f"平台状态：{visual.get('platform_state', '未探测')}",
            f"任务 {visual.get('job_count', 0)} 项：已生成 {visual.get('generated', 0)}、"
            f"待平台 {visual.get('deferred', 0)}、失败 {visual.get('failed', 0)}",
            "S2 概念意象不依据已确认平面，不能当效果图或尺寸依据",
            "平面确认后（G3 后置动作）会另出一批概念效果图",
        ],
        notes="未生成的图不放假图；状态以 concept-visual-jobs.json 为准。",
    ))

    deck.slides.append(Slide(
        kind="open_items", title="进 S3 之前需要核实",
        bullets=[_short(x, 100) for x in (rec.get("verify_before_s3") or [])][:5]
                + [f"专业复核：{_short(h, 90)}" for h in ((by_id.get(rec.get("concept_id", ""), {})
                                                            .get("technical_risks") or []))][:2],
        notes="这些不是建议，是条件；未核实前 S3 不得出正式平面。",
    ))

    deck.slides.append(Slide(
        kind="next_steps", title="G2 需要你确认的具体内容",
        bullets=["选定 concept_id（不是风格名）",
                 "确认空间策略：分区、动线、采光原则",
                 "确认风格与关键材料/色彩倾向",
                 "确认允许 S3 深化的条件",
                 "确认仍未解决的风险由谁承担",
                 "确认人姓名与日期（形成概念基准）"],
        notes="确认后系统写入 concept-baseline，S3 以此为唯一设计输入。",
    ))

    deck.slides.append(Slide(
        kind="disclaimer", title="边界与免责",
        bullets=[
            "结构安全、消防、无障碍、机电负荷与当地法规符合性不在本系统结论范围，须由持证专业人员在项目所在地复核签署",
            "概念图解表达空间关系，非按比例；不得作为尺寸依据",
            "S2 概念视觉由 AI 生成，仅表达方向与氛围，不是你家空间的效果图",
            "方案深度成果不得直接作为施工图使用",
        ],
        notes="与本项目全仓统一的免责口径一致。",
    ))
    return deck


def write(deck: Deck, out_dir: str | Path, stem: str = "concept-presentation") -> Dict[str, Any]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    issues = deck.validate()
    if issues:
        deck.warnings.extend(issues)
    pptx = write_pptx(deck, out / f"{stem}.pptx")
    md_path = write_markdown(deck, out / f"{stem}.md")
    html_path = write_html(deck, out / f"{stem}.html")
    return {
        "pptx": pptx,
        "markdown": str(md_path),
        "html": str(html_path),
        "issues": issues,
        "slide_count": len(deck.slides),
    }


__all__ = ["DECK_KIND", "build", "write"]
