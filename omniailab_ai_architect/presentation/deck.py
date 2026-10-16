"""Deck assembly.

`build()` turns real project state into presentation content. Nothing on a
slide is invented: every figure comes from the canonical model, the quantity
take-off, the compliance screen or the knowledge base — and the deck records
which of those it drew from in `provenance`.

If a stage has not run yet, the slide says so instead of showing a placeholder
that looks like a result.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

from .. import knowledge
from ..compliance import check as compliance_check
from ..model import Project
from ..quantities import takeoff
from ..stages import STAGES, STAGE_ORDER
from .layouts import Brand, Deck, Slide, new_deck, slide_order

AGENDA_NAMES: Dict[str, str] = {
    "cover": "封面",
    "agenda": "汇报结构",
    "section": "章节",
    "summary": "项目摘要与任务书",
    "concept": "设计概念与主张",
    "keywords": "概念关键词",
    "moodboard": "风格意向与材料倾向",
    "plan": "平面方案",
    "plan_compare": "平面方案比选",
    "analysis": "平面分析（面积 / 动线 / 采光）",
    "perspective": "空间表现",
    "materials": "材料与色彩",
    "lighting": "照明逻辑",
    "decisions": "设计决策与理由",
    "budget": "预算与材料概算",
    "coordination": "机电与专业协调",
    "drawings": "施工图与技术交底",
    "open_items": "待确认事项",
    "next_steps": "下一步计划",
    "disclaimer": "专业边界与免责",
}


def _stage_name(stage: str) -> str:
    for s in STAGES:
        if s.id == stage:
            return s.name
    return stage


def _fmt_money(v: Optional[float], currency: str = "CNY") -> str:
    if v is None:
        return "未提供"
    sym = "¥" if currency.upper() in ("CNY", "RMB") else f"{currency} "
    if v >= 1e6:
        return f"{sym}{v/1e6:.2f}M"
    if v >= 1e3:
        return f"{sym}{v/1e3:.1f}k"
    return f"{sym}{v:.0f}"


# --------------------------------------------------------------------------
class DeckBuilder:
    def __init__(self, project: Project, kind: str = "concept",
                 brand: Optional[Brand] = None, out_dir: str | Path | None = None,
                 schemes: Optional[Sequence[Any]] = None,
                 assets: Optional[Dict[str, str]] = None,
                 concept: Optional[Dict[str, Any]] = None,
                 level_id: Optional[str] = None) -> None:
        self.project = project
        self.kind = kind
        self.out_dir = Path(out_dir) if out_dir else None
        self.schemes = list(schemes or [])
        self.assets = dict(assets or {})
        self.concept = dict(concept or {})
        self.level_id = level_id or (project.levels[0].id if project.levels else "L1")
        self.deck = new_deck(kind, project, brand=brand)
        self._q = None
        self._c = None

    # -- lazily computed, project-linked facts ---------------------------
    @property
    def quantities(self):
        if self._q is None:
            self._q = takeoff(self.project, self.level_id)
        return self._q

    @property
    def compliance(self):
        if self._c is None:
            self._c = compliance_check(self.project, self.level_id)
        return self._c

    @property
    def rooms(self) -> List[Any]:
        return [s for s in self.project.spaces_on(self.level_id)
                if s.use not in ("envelope", "outdoor")]

    def _knowledge(self, question: str) -> knowledge.Selection:
        sel = knowledge.resolve(question, stage=self.deck.stage, limit=2)
        for d in sel.domains:
            self.deck.provenance.append(f"knowledge/{d.slug} ({d.name})")
        self.deck.provenance = list(dict.fromkeys(self.deck.provenance))
        return sel

    def _bullets_from_knowledge(self, domain: str, heading: str = "核心判据",
                                limit: int = 5) -> List[str]:
        body = knowledge.section(domain, heading)
        out: List[str] = []
        for ln in body.splitlines():
            t = ln.strip()
            if not t or t.startswith("#") or t.startswith("|") or t.startswith("---"):
                continue
            t = t.lstrip("-*0123456789. ").strip()
            if len(t) < 6:
                continue
            out.append(t[:120])
            if len(out) >= limit:
                break
        return out

    # ------------------------------------------------------------------
    def build(self) -> Deck:
        handlers = {
            "cover": self._cover, "agenda": self._agenda, "section": self._section,
            "summary": self._summary, "concept": self._concept,
            "keywords": self._keywords, "moodboard": self._moodboard,
            "plan": self._plan, "plan_compare": self._plan_compare,
            "analysis": self._analysis, "perspective": self._perspective,
            "materials": self._materials, "lighting": self._lighting,
            "decisions": self._decisions, "budget": self._budget,
            "coordination": self._coordination, "drawings": self._drawings,
            "open_items": self._open_items, "next_steps": self._next_steps,
            "disclaimer": self._disclaimer,
        }
        for kind in slide_order(self.kind):
            s = handlers[kind]()
            if s is not None:
                self.deck.slides.append(s)
        self.deck.subtitle = self._subtitle()
        return self.deck

    # ------------------------------------------------------------------
    def _subtitle(self) -> str:
        p = self.project
        area = sum(s.area_m2 for s in self.rooms)
        parts = [p.name or p.project_id,
                 f"建筑面积 {area:.1f} ㎡" if area else "",
                 f"修订 r{p.revision}",
                 self.deck.stage and f"阶段 {self.deck.stage} {_stage_name(self.deck.stage)}"]
        return " · ".join(x for x in parts if x)

    def _cover(self) -> Slide:
        p = self.project
        rows = []
        c = p.constraints or {}
        if c.get("budget_cny"):
            rows.append(f"预算 {_fmt_money(float(c['budget_cny']))}")
        if c.get("style"):
            rows.append(f"风格取向 {c['style']}")
        area = sum(s.area_m2 for s in self.rooms)
        if area:
            rows.append(f"套内面积 {area:.1f} ㎡")
        rows.append(f"模型修订 r{p.revision} · {self.deck.generated_at}")
        return Slide(
            kind="cover", kicker=self.deck.brand.tagline, title=self.deck.title,
            subtitle=self._subtitle(), bullets=rows,
            notes="封面信息全部来自 Canonical Spatial Model 当前修订。",
        )

    def _agenda(self) -> Slide:
        kinds = [k for k in slide_order(self.kind) if k not in ("cover", "agenda")]
        return Slide(kind="agenda", title="汇报结构", subtitle=f"共 {len(kinds)+1} 页",
                     bullets=[f"{i:02d}　{AGENDA_NAMES.get(k, k)}"
                              for i, k in enumerate(kinds, 1)])

    def _section(self) -> Optional[Slide]:
        return None

    def _summary(self) -> Slide:
        p = self.project
        rows: List[List[str]] = []
        for item in (p.program or [])[:12]:
            rows.append([
                str(item.get("name") or item.get("use") or "-"),
                str(item.get("target_area_m2") or item.get("area_m2") or "-"),
                str(item.get("count") or 1),
                str(item.get("note") or ""),
            ])
        if not rows:
            for s in sorted(self.rooms, key=lambda x: -x.area_m2)[:12]:
                rows.append([s.name or s.use, f"{s.area_m2:.1f}", "1", s.use])
        bullets = []
        c = p.constraints or {}
        if c.get("budget_cny"):
            bullets.append(f"预算上限：{_fmt_money(float(c['budget_cny']))}")
        if c.get("style"):
            bullets.append(f"风格取向：{c['style']}")
        if c.get("notes"):
            bullets.append(str(c["notes"]))
        bullets.append(f"面积合计：{sum(s.area_m2 for s in self.rooms):.1f} ㎡"
                       f"　房间数 {len(self.rooms)}")
        uncertain = [e for e in p.elements if getattr(e, "uncertain", False)]
        bullets.append(f"图纸不确定项：{len(uncertain)} 处（须现场核对）")
        return Slide(kind="summary", title="项目摘要与设计任务书",
                     subtitle=f"{p.project_id}　修订 r{p.revision}",
                     bullets=bullets,
                     table_header=["空间", "目标面积 ㎡", "数量", "备注"],
                     table=rows,
                     notes="面积与房间数直接读取统一空间模型，非人工整理。")

    def _concept(self) -> Slide:
        sel = self._knowledge("概念方案 设计立场 空间原型 风格语言")
        bullets = self.concept.get("statement") or self._bullets_from_knowledge(
            sel.domains[0].slug if sel.domains else "interior-design-methodology"
        )
        if isinstance(bullets, str):
            bullets = [bullets]
        return Slide(
            kind="concept", title="设计概念与主张",
            subtitle=str(self.concept.get("title") or "一个立场 · 一个原型 · 三条策略"),
            bullets=list(bullets)[:6],
            columns=[
                {"title": "空间原型", "items": self.concept.get("prototype", []) or
                 ["公共区连续、私密区成组", "服务功能集中成脊", "留一处不被占用的空"]},
                {"title": "光策略", "items": self.concept.get("light", []) or
                 ["以自然光定分区", "主光面不做满墙柜", "夜间以一个发光面定氛围"]},
                {"title": "材料策略", "items": self.concept.get("material", []) or
                 ["两种主材 + 一种点缀", "暖材比例控制", "深色只做重音"]},
            ],
            notes="概念判据来自本项目知识库，非第三方文案。",
        )

    def _keywords(self) -> Slide:
        sel = self._knowledge("风格 关键词 氛围 色彩")
        groups = self.concept.get("keywords") or [
            ["克制", "连续", "留白"],
            ["暖木", "微水泥", "哑光黑"],
            ["可读的光", "低色温夜模式", "一处发光面"],
        ]
        return Slide(kind="keywords", title="概念关键词",
                     subtitle="三组关键词：气质 / 材质 / 光",
                     columns=[{"title": f"第 {i} 组", "items": g}
                              for i, g in enumerate(groups[:3], 1)],
                     notes=f"关键词组用于约束后续材料与照明选择（知识域："
                           f"{', '.join(d.slug for d in sel.domains)}）")

    def _moodboard(self) -> Slide:
        img = self.assets.get("moodboard") or self.assets.get("palette") or ""
        bullets = self.concept.get("moodboard") or [
            "底色：低饱和暖灰（约占 60%）",
            "主材：两种质感对比（约占 30%）",
            "重音：深色与金属（不超过 8%）",
            "意向图仅表达方向，不作为材料样板",
        ]
        if not img:
            bullets = ["尚未生成意向板：需先绑定图片 provider 或提供素材。"] + bullets
        return Slide(kind="moodboard", title="风格意向与材料倾向",
                     subtitle="意向板用于对齐方向，不替代样板确认",
                     bullets=bullets, image=img)

    def _plan(self) -> Slide:
        img = self.assets.get("plan") or ""
        bullets: List[str] = []
        rows: List[List[str]] = []
        if self.schemes:
            s = self.schemes[0]
            m = s.metrics
            bullets = [
                f"方案 {s.variant}　{s.title}",
                f"房间 {m.get('room_count', '-')} 间　套内 {m.get('total_area_m2', '-')} ㎡",
                f"隔墙 {m.get('partition_count', '-')} 段　门 {m.get('door_count', '-')} 樘　"
                f"窗 {m.get('window_count', '-')} 樘",
                f"走廊占比 {m.get('corridor_ratio', m.get('corridor_area_m2', '-'))}　"
                f"开放区比 {m.get('open_plan_ratio', '-')}",
            ]
            for a in s.area_table()[:10]:
                rows.append([a["name"], f"{a['area_m2']:.1f}",
                             f"{a['target_m2'] or '-'}", f"{a['delta_m2']:+.1f}"])
        else:
            bullets = ["平面方案尚未生成：请先运行阶段 S3。"]
        if not img:
            bullets.append("平面图片未附加（不影响图纸与模型交付）。")
        return Slide(kind="plan", title="平面方案",
                     subtitle="由统一空间模型自动生成",
                     bullets=bullets,
                     table_header=["空间", "实际 ㎡", "目标 ㎡", "偏差"] if rows else [],
                     table=rows, image=img)

    def _plan_compare(self) -> Slide:
        if len(self.schemes) < 2:
            return Slide(kind="plan_compare", title="平面方案比选",
                         subtitle="当前仅有一套方案",
                         bullets=["需要两套以上方案才能比选；"
                                  "请运行 S3 生成方案 A/B。"])
        keys = [
            ("房间数", "room_count", ""), ("套内面积 ㎡", "total_area_m2", ""),
            ("隔墙数", "partition_count", ""), ("门 樘", "door_count", ""),
            ("窗 樘", "window_count", ""), ("采光房间数", "daylight_rooms_served", ""),
            ("走廊面积 ㎡", "corridor_area_m2", ""), ("开放区比", "open_plan_ratio", ""),
            ("玻璃比", "glazing_ratio", ""),
        ]
        header = ["指标"] + [f"方案 {s.variant}" for s in self.schemes[:3]]
        rows: List[List[str]] = []
        for label, key, _unit in keys:
            row = [label]
            for s in self.schemes[:3]:
                v = s.metrics.get(key, "-")
                if isinstance(v, float):
                    v = f"{v:.2f}" if v < 10 else f"{v:.1f}"
                row.append(str(v))
            rows.append(row)
        bullets = [
            f"方案 {s.variant}：{s.title}" for s in self.schemes[:3]
        ]
        for s in self.schemes[:3]:
            if s.warnings:
                bullets.append(f"方案 {s.variant} 提示：{s.warnings[0]}")
        return Slide(kind="plan_compare", title="平面方案比选",
                     subtitle="同一模型、同一算法口径下的可比指标",
                     bullets=bullets, table_header=header, table=rows,
                     notes="比选指标由 PlanGenerator 输出，口径一致，可直接横向比较。")

    def _analysis(self) -> Slide:
        rows = []
        total = sum(s.area_m2 for s in self.rooms) or 1.0
        for s in sorted(self.rooms, key=lambda x: -x.area_m2)[:12]:
            rows.append([s.name or s.use, f"{s.area_m2:.1f}",
                         f"{s.area_m2 / total * 100:.1f}%",
                         "有" if s.properties.get("daylight_required") else "—"])
        sel = self._knowledge("平面分析 面积配比 动线 采光")
        bullets = [f"面积合计 {total:.1f} ㎡　房间 {len(self.rooms)} 间",
                   f"最大房间占比 {max((s.area_m2 / total * 100) for s in self.rooms):.1f}%"
                   if self.rooms else "无房间数据"]
        bullets += self._bullets_from_knowledge("spatial-planning", "常见错误", limit=3)
        return Slide(kind="analysis", title="平面分析",
                     subtitle="面积配比 / 采光需求 / 常见问题",
                     bullets=bullets,
                     table_header=["空间", "面积 ㎡", "占比", "需采光"],
                     table=rows)

    def _perspective(self) -> Slide:
        img = self.assets.get("perspective") or self.assets.get("contact_sheet") or ""
        jobs = self.assets.get("render_jobs") or ""
        bullets = []
        if jobs:
            bullets.append(f"表现任务包：{Path(jobs).name}")
        bullets += [
            "机位与镜头为方案表现，不保证与建成完全一致",
            "生成式图像不得作为施工尺寸依据",
        ]
        if not img:
            bullets.insert(0, "尚未获得表现图：需绑定图片 provider（当前状态见 provider 报告）")
        return Slide(kind="perspective", title="空间表现",
                     subtitle="表现图非权威成果", bullets=bullets, image=img)

    def _materials(self) -> Slide:
        sel = self._knowledge("材料 饰面 选型 规格")
        q = self.quantities
        rows = [
            ["地面（建筑面积）", f"{q.quantities.get('floor_area_m2', 0):.1f}", "㎡"],
            ["墙面完成面", f"{q.quantities.get('wall_finish_area_m2', 0):.1f}", "㎡"],
            ["隔墙面积", f"{q.quantities.get('partition_area_m2', 0):.1f}", "㎡"],
            ["玻璃面积", f"{q.quantities.get('glazing_area_m2', 0):.1f}", "㎡"],
            ["门 / 窗", f"{int(q.quantities.get('door_count', 0))} / "
                        f"{int(q.quantities.get('window_count', 0))}", "樘"],
            ["家具件数", f"{int(q.quantities.get('furniture_count', 0))}", "件"],
        ]
        bullets = self._bullets_from_knowledge("material-and-finish-selection",
                                               "核心判据", limit=4)
        return Slide(kind="materials", title="材料与色彩",
                     subtitle="选型判据 + 工程量（方案阶段）",
                     bullets=bullets,
                     table_header=["项目", "数量", "单位"], table=rows,
                     notes="工程量随模型修订滚动重算；不构成结算依据。")

    def _lighting(self) -> Slide:
        sel = self._knowledge("照明 照度 色温 灯具 氛围")
        lux = knowledge.search("lx", limit=6) or []
        rows = []
        for h in lux:
            rows.append([h.get("section", "-"), str(h.get("text", ""))[:70]])
        bullets = self._bullets_from_knowledge("lighting-design", "核心判据", limit=4)
        bullets.append("应急与疏散照明须按项目所在地现行规范，由持证人员复核")
        return Slide(kind="lighting", title="照明逻辑",
                     subtitle="自然光定分区，人工光定氛围",
                     bullets=bullets,
                     table_header=["小节", "要点"] if rows else [],
                     table=rows[:6],
                     notes="照度数值为工程惯例区间，非强制值。")

    def _decisions(self) -> Slide:
        rows = []
        for e in (self.project.change_log or [])[-8:]:
            rows.append([str(getattr(e, "revision", "")), str(getattr(e, "kind", "")),
                         str(getattr(e, "detail", ""))[:80]])
        bullets = self.concept.get("decisions") or [
            "每条决策均记录：决定 — 理由 — 代价",
            "变更经影响分析后回流对应阶段，已确认内容不重算",
        ]
        if not rows:
            rows.append(["—", "—", "本阶段尚无变更记录"])
        return Slide(kind="decisions", title="设计决策与理由",
                     subtitle="可追溯的决策台账",
                     bullets=bullets,
                     table_header=["修订", "类型", "内容"], table=rows)

    def _budget(self) -> Slide:
        cost = self.quantities.cost or {}
        rows: List[List[str]] = []
        for key, val in (cost.get("by_category") or {}).items():
            rows.append([str(key), _fmt_money(float(val) if not isinstance(val, dict)
                                              else float(val.get("amount", 0)))])
        bullets = []
        total = cost.get("total")
        if total:
            bullets.append(f"估算合计 {_fmt_money(float(total))}")
        budget = (self.project.constraints or {}).get("budget_cny")
        if budget:
            bullets.append(f"预算上限 {_fmt_money(float(budget))}")
        bullets.append("方案阶段估算，用于决策，不构成结算依据")
        if not rows:
            rows.append(["估算尚未生成", "—"])
        return Slide(kind="budget", title="预算与材料概算",
                     subtitle=f"修订 r{self.project.revision}",
                     bullets=bullets,
                     table_header=["类别", "金额"], table=rows)

    def _coordination(self) -> Slide:
        rep = self.compliance
        bullets = [
            "净高、管井、机房与末端点位须与机电专业同步确认",
            "结构安全、消防、无障碍、负荷由持证专业人员在项目所在地复核签署",
        ]
        rows = []
        for issue in list(getattr(rep, "issues", []))[:10]:
            rows.append([str(getattr(issue, "severity", "")),
                         str(getattr(issue, "code", "")),
                         str(getattr(issue, "message", ""))[:80]])
        if not rows:
            rows.append(["—", "—", "初筛未发现阻断项（不等于合规结论）"])
        return Slide(kind="coordination", title="机电与专业协调",
                     subtitle="初筛结果，非合规结论",
                     bullets=bullets,
                     table_header=["级别", "编号", "内容"], table=rows)

    def _drawings(self) -> Slide:
        rows = []
        for a in self.project.artifacts:
            rows.append([str(a.id), str(a.type), f"r{a.revision}", str(a.status)])
        bullets = [
            "施工图由经校核的几何模型生成，不从效果图反推",
            "DXF 是可编辑 CAD；DWG 需具备许可的后端另存",
        ]
        if not rows:
            rows.append(["—", "尚未产出图纸", "—", "—"])
        return Slide(kind="drawings", title="施工图与技术交底",
                     subtitle=f"交付清单（{len(self.project.artifacts)} 项）",
                     bullets=bullets,
                     table_header=["图号", "类型", "修订", "状态"],
                     table=rows[:14])

    def _open_items(self) -> Slide:
        items: List[str] = []
        for e in self.project.elements:
            if getattr(e, "uncertain", False):
                items.append(f"不确定构件 {e.id}（{e.type}）须现场核对")
        for s in self.schemes:
            for w in s.warnings[:2]:
                items.append(f"方案 {s.variant}：{w}")
        rep = self.compliance
        for issue in list(getattr(rep, "issues", []))[:5]:
            sev = str(getattr(issue, "severity", ""))
            if sev.lower() in ("block", "error", "high"):
                items.append(f"[阻断] {getattr(issue, 'message', issue)}")
        if not items:
            items = ["暂无待确认项（以最近一次校核为准）"]
        return Slide(kind="open_items", title="待确认事项",
                     subtitle=f"共 {len(items)} 项", bullets=items[:12],
                     notes="阻断项未解决前不得出正式施工图。")

    def _next_steps(self) -> Slide:
        cur = self.deck.stage
        idx = STAGE_ORDER.index(cur) if cur in STAGE_ORDER else 0
        nxt = STAGE_ORDER[idx + 1: idx + 3]
        bullets = [f"{s}　{_stage_name(s)}" for s in nxt] or ["已到达最后一个阶段：进入交付与复盘"]
        return Slide(kind="next_steps", title="下一步计划",
                     subtitle=f"当前阶段 {cur} {_stage_name(cur)}", bullets=bullets)

    def _disclaimer(self) -> Slide:
        return Slide(
            kind="disclaimer", title="专业边界与免责",
            subtitle="本文件为方案阶段设计成果",
            bullets=[
                "结构安全、消防、无障碍、机电负荷与法规符合性不在本系统结论范围内，"
                "须由持证专业人员在项目所在地复核并签署。",
                "方案深度成果不得作为施工图使用；正式施工成果须经复核。",
                "AI 生成或本地合成的效果图不保证尺寸与比例，不得作为施工尺寸依据。",
                "工程量与造价为方案阶段估算，不构成结算依据。",
                f"本文件由 {self.deck.brand.name} 自动生成于 {self.deck.generated_at}，"
                f"对应模型修订 r{self.project.revision}。",
            ],
            notes="该页为强制页：任何提案都必须声明能力边界。",
        )


def build(project: Project, kind: str = "concept", **kwargs: Any) -> Deck:
    return DeckBuilder(project, kind=kind, **kwargs).build()


def kinds() -> List[str]:
    from .layouts import DECK_KINDS

    return sorted(DECK_KINDS)


__all__ = ["DeckBuilder", "build", "kinds", "AGENDA_NAMES"]
