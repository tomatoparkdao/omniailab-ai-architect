"""Original design knowledge base — progressive loading.

The knowledge base is thirteen domain documents written from general design
principles and public engineering practice. It is *not* a copy of anyone's
private methodology: nothing here is redistributed from a third-party work.

Loading is deliberately progressive so an agent never has to pull the whole
corpus into context:

    1. `index()`        -> the thirteen domains, front-matter only (cheap)
    2. `resolve(...)`   -> which domains a question actually needs
    3. `outline(d)`     -> section headings of one domain (cheap)
    4. `section(d, h)`  -> one section of one domain (targeted)
    5. `load(d)`        -> a whole domain (heavy, opt-in)

`budget()` puts a ceiling on what a stage may pull in, so "load the knowledge"
cannot silently become "load 2600 lines".
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Sequence

from ..paths import KNOWLEDGE

COST_ORDER = {"light": 0, "medium": 1, "heavy": 2}

FRONTMATTER_KEYS = ("domain", "name", "stage_affinity", "loads_when", "load_cost", "version")

# Question keywords -> domain. Kept broad and bilingual on purpose: the router
# only needs to narrow thirteen documents down to two or three.
KEYWORD_MAP: Dict[str, Sequence[str]] = {
    "architectural-design-principles": ("总图", "场地", "体量", "体型", "立面", "剖面",
                                        "功能分区", "建筑", "退线", "朝向"),
    "interior-design-methodology": ("室内", "风格", "界面", "软装", "氛围", "设计语言",
                                    "意式", "极简", "侘寂", "法式"),
    "spatial-planning": ("平面", "分区", "动线", "流线", "房间", "面积", "布局",
                         "户型", "开放式", "几室"),
    "human-ergonomics": ("尺寸", "净宽", "通道", "过道", "家具尺寸", "人体", "尺度",
                         "台面", "洁具", "高差", "踏步"),
    "material-and-finish-selection": ("材料", "饰面", "材质", "木饰面", "石材", "瓷砖",
                                      "地板", "涂料", "收口", "样板", "耐磨"),
    "lighting-design": ("灯光", "照明", "照度", "色温", "显色", "筒灯", "灯带",
                        "洗墙", "采光", "灯具", "调光"),
    "building-systems-coordination": ("机电", "暖通", "空调", "新风", "给排水", "电气",
                                      "净高", "管井", "机房", "消防", "智能化", "点位"),
    "construction-detailing": ("节点", "大样", "构造", "防水", "基层", "收边", "做法",
                               "吊顶", "隔墙", "工艺"),
    "cad-drawing-standards": ("图层", "线型", "线宽", "标注", "图框", "图纸编号",
                              "打印", "出图", "比例", "cad", "dwg", "dxf"),
    "bim-modeling-principles": ("bim", "ifc", "建模", "构件", "参数化", "碰撞",
                                "模型精度", "lod", "协同", "构件属性"),
    "design-review-checklists": ("校核", "评审", "自检", "检查", "退回", "核对",
                                 "审核", "验收", "会审"),
    "design-presentation-methodology": ("汇报", "提案", "ppt", "方案册", "讲标",
                                        "图册", "表达", "沟通", "汇报文件"),
    "ai-concept-visualization": ("概念效果图", "效果图", "渲染", "出图", "提示词", "机位",
                                 "生图", "画布", "概念图", "表现图", "视角", "镜头",
                                 "omnip", "image2.5", "canvas"),
}

HEADING = "## "


# --------------------------------------------------------------------------
@dataclass
class Domain:
    slug: str
    name: str
    path: str
    stage_affinity: List[str] = field(default_factory=list)
    loads_when: str = ""
    load_cost: str = "medium"
    version: str = ""
    sections: List[str] = field(default_factory=list)
    lines: int = 0

    def to_dict(self) -> Dict[str, object]:
        return {
            "domain": self.slug,
            "name": self.name,
            "path": self.path,
            "stage_affinity": list(self.stage_affinity),
            "loads_when": self.loads_when,
            "load_cost": self.load_cost,
            "version": self.version,
            "sections": list(self.sections),
            "lines": self.lines,
        }


@dataclass
class Selection:
    """A ranked, cost-aware answer to 'which knowledge do we need?'."""

    domains: List[Domain]
    scores: Dict[str, int]
    stage: Optional[str]
    estimate_lines: int
    reason: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, object]:
        return {
            "stage": self.stage,
            "domains": [d.slug for d in self.domains],
            "scores": self.scores,
            "estimate_lines": self.estimate_lines,
            "reason": list(self.reason),
        }


def _parse_frontmatter(text: str) -> Dict[str, object]:
    """Parse the front-matter subset the knowledge base uses.

    Supports `key: value`, inline lists `[a, b]` and block lists
    (`key:` followed by indented `- item` lines) — the last one matters, because
    a list silently parsed as an empty string would make a case look incomplete.
    """
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end < 0:
        return {}
    body = text[3:end]
    out: Dict[str, object] = {}
    current: Optional[str] = None
    for raw in body.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if raw[:1] in (" ", "\t"):
            item = raw.strip()
            if item.startswith("- ") or item == "-":
                if current is not None:
                    if not isinstance(out.get(current), list):
                        out[current] = []
                    out[current].append(item[1:].strip().strip("'\""))  # type: ignore[union-attr]
            continue
        if ":" not in raw:
            continue
        key, val = raw.split(":", 1)
        key, val = key.strip(), val.strip()
        if val.startswith("[") and val.endswith("]"):
            out[key] = [v.strip().strip("'\"") for v in val[1:-1].split(",") if v.strip()]
            current = None
        elif not val:
            out[key] = []            # a block list may follow
            current = key
        else:
            out[key] = val.strip("'\"")
            current = None
    return out


def knowledge_dir() -> "object":
    return KNOWLEDGE


# --------------------------------------------------------------------------
def index(validate_files: bool = True) -> List[Domain]:
    """The thirteen domains, front-matter only. Cheap enough to call every turn."""
    if not KNOWLEDGE.exists():
        return []
    out: List[Domain] = []
    for p in sorted(KNOWLEDGE.glob("*.md")):
        if p.stem == "INDEX":
            continue
        text = p.read_text(encoding="utf-8")
        fm = _parse_frontmatter(text)
        sections = [
            ln[len(HEADING):].strip()
            for ln in text.splitlines() if ln.startswith(HEADING)
        ]
        out.append(Domain(
            slug=str(fm.get("domain") or p.stem),
            name=str(fm.get("name") or p.stem),
            path=str(p.relative_to(KNOWLEDGE.parent)),
            stage_affinity=list(fm.get("stage_affinity") or []),   # type: ignore[arg-type]
            loads_when=str(fm.get("loads_when") or ""),
            load_cost=str(fm.get("load_cost") or "medium"),
            version=str(fm.get("version") or ""),
            sections=sections,
            lines=len(text.splitlines()),
        ))
    return out


def get(slug: str) -> Optional[Domain]:
    for d in index():
        if d.slug == slug or d.name == slug:
            return d
    return None


def resolve(question: str, stage: Optional[str] = None,
            limit: int = 3, include: Sequence[str] = ()) -> Selection:
    """Pick the domains a question needs, biased by the current stage."""
    low = (question or "").lower()
    domains = {d.slug: d for d in index()}
    scores: Dict[str, int] = {}
    reason: List[str] = []

    for slug, keys in KEYWORD_MAP.items():
        hits = sum(1 for k in keys if k.lower() in low)
        if hits:
            scores[slug] = scores.get(slug, 0) + hits * 3

    # The stage only *biases* a match — it must never manufacture one, otherwise
    # every stage would score eight domains and the fallback could never fire.
    if scores and stage:
        for d in domains.values():
            if stage in d.stage_affinity and d.slug in scores:
                scores[d.slug] += 1
                reason.append(f"{d.slug}: 阶段 {stage} 加权")

    for slug in include:
        if slug in domains:
            scores[slug] = scores.get(slug, 0) + 5
            reason.append(f"{slug}: 显式指定")

    if not scores:
        # Nothing matched. Fall back to what the stage always needs rather than
        # silently loading everything.
        fallback = {
            "S1": ["design-review-checklists"],
            "S2": ["design-presentation-methodology"],
            "S3": ["spatial-planning", "human-ergonomics",
                   "ai-concept-visualization"],
            "S4": ["interior-design-methodology", "material-and-finish-selection"],
            "S5": ["bim-modeling-principles", "ai-concept-visualization"],
            "S6": ["design-review-checklists"],
            "S7": ["cad-drawing-standards", "construction-detailing"],
            "S8": ["design-presentation-methodology"],
        }.get(stage or "", ["design-review-checklists"])
        for slug in fallback:
            scores[slug] = 2
        reason.append(f"问题未命中关键词，按阶段 {stage or '-'} 的默认领域回退")

    ranked = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))
    chosen = [domains[s] for s, _ in ranked if s in domains][:limit]
    for d in chosen:
        if not any(d.slug in r for r in reason):
            reason.append(f"{d.slug}: 命中关键词（{scores[d.slug]} 分）")
    return Selection(
        domains=chosen,
        scores={k: v for k, v in ranked},
        stage=stage,
        estimate_lines=sum(d.lines for d in chosen),
        reason=reason,
    )


def outline(slug: str) -> List[str]:
    d = get(slug)
    return list(d.sections) if d else []


def section(slug: str, heading: str) -> str:
    """One `##` section of one domain — the default way to read the corpus."""
    d = get(slug)
    if not d:
        return ""
    text = (KNOWLEDGE.parent / d.path).read_text(encoding="utf-8")
    target = heading.strip().lstrip("#").strip()
    lines = text.splitlines()
    out: List[str] = []
    inside = False
    for ln in lines:
        if ln.startswith(HEADING):
            if ln[len(HEADING):].strip() == target:
                inside = True
                out.append(ln)
                continue
            if inside:
                break
        elif inside:
            out.append(ln)
    return "\n".join(out).strip()


def load(slug: str, max_lines: int = 0) -> str:
    """A whole domain. Heavy — prefer `outline()` + `section()`."""
    d = get(slug)
    if not d:
        return ""
    text = (KNOWLEDGE.parent / d.path).read_text(encoding="utf-8")
    if max_lines and len(text.splitlines()) > max_lines:
        head = text.splitlines()[:max_lines]
        return "\n".join(head) + f"\n\n…（已截断，共 {d.lines} 行；请用 section() 精确读取）"
    return text


def budget(stage: str, max_lines: int = 260) -> List[Domain]:
    """Domains affordable for a stage, cheapest first, under a line ceiling."""
    picked: List[Domain] = []
    used = 0
    pool = [d for d in index() if stage in d.stage_affinity]
    pool.sort(key=lambda d: (COST_ORDER.get(d.load_cost, 1), d.lines))
    for d in pool:
        if used + d.lines > max_lines:
            continue
        picked.append(d)
        used += d.lines
    return picked


def search(term: str, limit: int = 20) -> List[Dict[str, object]]:
    """Grep the corpus for a literal term; returns domain/heading/line hits."""
    hits: List[Dict[str, object]] = []
    low = (term or "").lower()
    if not low:
        return hits
    for d in index():
        text = (KNOWLEDGE.parent / d.path).read_text(encoding="utf-8")
        heading = ""
        for i, ln in enumerate(text.splitlines(), 1):
            if ln.startswith(HEADING):
                heading = ln[len(HEADING):].strip()
            if low in ln.lower():
                hits.append({"domain": d.slug, "line": i, "section": heading,
                             "text": ln.strip()[:160]})
                if len(hits) >= limit:
                    return hits
    return hits


def validate() -> List[str]:
    """Consistency check: front-matter present, index in sync, no gaps."""
    issues: List[str] = []
    domains = index()
    if not domains:
        return ["knowledge/ 为空或不存在"]
    for d in domains:
        if not d.stage_affinity:
            issues.append(f"{d.slug}: 缺少 stage_affinity")
        bad = [s for s in d.stage_affinity if s not in {f"S{i}" for i in range(1, 9)}]
        if bad:
            issues.append(f"{d.slug}: 非法阶段 {bad}")
        if d.load_cost not in COST_ORDER:
            issues.append(f"{d.slug}: 非法 load_cost={d.load_cost}")
        if len(d.sections) < 5:
            issues.append(f"{d.slug}: 小节过少（{len(d.sections)}）")
        if d.lines < 60:
            issues.append(f"{d.slug}: 内容过少（{d.lines} 行）")
    idx = KNOWLEDGE / "INDEX.md"
    if not idx.exists():
        issues.append("缺少 knowledge/INDEX.md")
    else:
        itext = idx.read_text(encoding="utf-8")
        for d in domains:
            if d.slug not in itext:
                issues.append(f"INDEX.md 未收录 {d.slug}")
    return issues


def report() -> Dict[str, object]:
    domains = index()
    return {
        "count": len(domains),
        "total_lines": sum(d.lines for d in domains),
        "by_stage": {
            s: [d.slug for d in domains if s in d.stage_affinity]
            for s in (f"S{i}" for i in range(1, 9))
        },
        "domains": [d.to_dict() for d in domains],
        "issues": validate(),
        "provenance": "original — written from general design principles and public engineering practice",
    }


def cases() -> List[Dict[str, object]]:
    """Generic project-type cases. Deliberately not real third-party projects."""
    from ..paths import CASES

    out: List[Dict[str, object]] = []
    if not CASES.exists():
        return out
    for p in sorted(CASES.glob("*.md")):
        fm = _parse_frontmatter(p.read_text(encoding="utf-8"))
        out.append({"file": str(p.relative_to(CASES.parent)), "slug": p.stem, **fm})
    return out


__all__ = [
    "Domain", "Selection", "index", "get", "resolve", "outline", "section",
    "load", "budget", "search", "validate", "report", "cases", "knowledge_dir",
]
