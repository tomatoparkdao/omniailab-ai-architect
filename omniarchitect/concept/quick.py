"""S1 快速判断：先把项目看准，再谈问题清单。

首席设计师见客户，第一轮不会掏出四十页问卷。他会先给出判断：

* 这是哪一类项目（建筑／室内／景观，业态与子类）；
* 委托到底做到哪一步；
* 功能重点是哪三条；
* 审美方向在哪（客户说了就照办，没说就给三个可选方向）；
* 主要限制是什么；
* 建议客户提供什么参考。

这份判断写成 `design-position.md`（一页），S2 的概念汇报直接读它，
保证"客户看到的第一页"和"系统内部的任务书"说的是同一件事。

不新增阶段、不新增门禁：仍然走 `intake` 既有问诊，只是把输出压成一页判断，
并复用 `interview.next_questions`（每轮最多三问、已答不重问）。

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple

from .. import taxonomy as tax
from ..intake import interview as iv

FILE = "design-position.md"

#: 专业 → 风格库里的空间词。只用来"给三个可选方向"，不做风格裁决。
PROFILE_SPACE = {
    "residential": ("住宅", "别墅", "公寓", "居住"),
    "interior": ("酒店", "餐饮", "办公", "商业", "住宅", "零售"),
    "hospitality": ("酒店", "餐饮", "商业"),
    "landscape": ("景观", "庭院", "花园", "户外"),
    "architecture": ("公共建筑", "文化", "教育", "办公", "商业"),
    "urban": ("城市", "公共空间", "街区"),
}

#: 建议客户提供的参考（不阻断，只引导）
ASK_ASSETS: Sequence[str] = (
    "喜欢的空间照片或建成项目（3–5 张即可，注明喜欢哪一点）",
    "现状照片或已有图纸（没有也能先做概念）",
    "喜欢的作品集／版式样本（决定汇报的排版气质）",
)


def _discipline_label(project: Any, codes: Sequence[str]) -> str:
    from .. import disciplines as disc

    try:
        scope = disc.load(project)
        labels = scope.labels()
    except Exception:                     # noqa: BLE001
        labels = []
    if labels:
        return "、".join(labels)
    return "建筑"


def _focus(project: Any) -> List[Dict[str, str]]:
    """功能重点：取任务书里**成组**的条目，而不是逐间罗列。

    客户要看的是"客房、餐饮、后场"这三件事，不是"标准大床房 1/2/3"。
    同一组房间按名称去掉序号后合并，合并后按面积取前三组。
    """
    import re

    def group_of(name: str) -> str:
        return re.sub(r"[\s\-_]*(\d+|[A-Za-z])$", "", str(name or "")).strip() or str(name)

    buckets: Dict[str, Dict[str, Any]] = {}
    for item in (project.program or []):
        name = str(item.get("name") or "").strip()
        if not name:
            continue
        key = group_of(name)
        b = buckets.setdefault(key, {"name": key, "n": 0, "area": 0.0})
        b["n"] += 1
        b["area"] += float(item.get("area_m2") or 0)
    rows = sorted(buckets.values(), key=lambda b: -b["area"])[:3]
    if rows:
        return [{"name": r["name"],
                 "note": (f"{r['area'] / max(r['n'], 1):,.0f} m² ×{r['n']}"
                          if r["n"] > 1 else f"{r['area']:,.0f} m²")}
                for r in rows]
    out: List[Dict[str, str]] = []
    for n in (getattr(project, "meta", {}).get("intake", {}) or {}).get("needs") or []:
        name = str(n.get("name") or "")
        if name:
            out.append({"name": name, "note": str(n.get("note") or "按任务书口径")})
    return out[:3]


#: 按项目类型给的风格短名单（有序）。这不是"关键词命中的前三个"，
#: 而是设计师按这类项目该谈什么来排的：教育要克制耐用，医疗要洁净可维护，
#: 工业要工艺优先，酒店要有记忆点，住宅要住得下去。
#: 名单只决定**先谈哪三个方向**，最终仍由客户的偏好与原话覆盖。
TYPE_STYLES: Dict[str, Tuple[str, ...]] = {
    # ---- 公共建筑 ----
    "A3": ("bauhaus", "biophilic", "modernist-classic"),          # 教育
    "A4": ("modern-minimalism", "biophilic", "bauhaus"),          # 医疗
    "A5": ("modern-minimalism", "corporate-contemporary", "bauhaus"),
    "A6": ("contemporary-luxury", "wabi-sabi", "tropical-resort"),  # 酒店
    "A7": ("modern-minimalism", "corporate-contemporary", "italian-minimal"),
    "A8": ("modern-minimalism", "brutalist", "organic-modern"),     # 文化展陈
    "A9": ("corporate-contemporary", "modern-minimalism", "bauhaus"),
    "A10": ("modern-minimalism", "brutalist", "parametric-futurism"),
    "A14": ("chinese-neo-classical", "japanese-zen", "modern-minimalism"),
    # ---- 居住建筑 ----
    "A1": ("modern-minimalism", "japandi", "chinese-neo-classical"),
    "A2": ("modern-minimalism", "corporate-contemporary", "organic-modern"),
    # ---- 工业与农业 ----
    "A12": ("industrial-loft", "warehouse-conversion", "modern-minimalism"),
    "A13": ("industrial-loft", "rustic-natural", "modern-minimalism"),
    # ---- 室内 ----
    "B1": ("japandi", "modern-minimalism", "wabi-sabi"),
    "B2": ("italian-minimal", "contemporary-luxury", "japandi"),
    "B3": ("corporate-contemporary", "modern-minimalism", "industrial-loft"),
    "B4": ("contemporary-luxury", "wabi-sabi", "art-deco"),
    "B5": ("industrial-loft", "rustic-natural", "modern-minimalism"),
    "B8": ("modern-minimalism", "biophilic", "japandi"),
    # ---- 景观 ----
    "C2": ("japanese-zen", "biophilic", "modern-minimalism"),
    "C3": ("biophilic", "modern-minimalism", "rustic-natural"),
    "C5": ("biophilic", "organic-modern", "rustic-natural"),
}

#: 类型未知时，按主导专业给一组通用方向（仍然要能对着这类项目讲得通）
PROFILE_STYLES: Dict[str, Tuple[str, ...]] = {
    "architecture": ("modern-minimalism", "bauhaus", "biophilic"),
    "interior": ("modern-minimalism", "japandi", "contemporary-luxury"),
    "landscape": ("biophilic", "japanese-zen", "rustic-natural"),
    "residential": ("modern-minimalism", "japandi", "wabi-sabi"),
    "hospitality": ("contemporary-luxury", "wabi-sabi", "tropical-resort"),
    "urban": ("modern-minimalism", "biophilic", "corporate-contemporary"),
}


def _type_codes(project: Any) -> List[str]:
    """已识别的项目类型代码（S1 判定结果，不是这里再猜一遍）。"""
    tax = (getattr(project, "meta", {}) or {}).get("taxonomy") or {}
    codes = [str(c) for c in (tax.get("codes") or []) if c]
    if not codes:
        prov = (getattr(project, "meta", {}) or {}).get("taxonomy_provisional") or {}
        codes = [str(c) for c in (prov.get("codes") or []) if c]
    return codes


def _aesthetic(project: Any, profile_id: str) -> Dict[str, Any]:
    pref = str((project.constraints or {}).get("style") or "").strip()
    if pref:
        return {"source": "client", "label": pref, "options": [],
                "note": "客户已点名，S2 尊重该方向，只在表达上做差异化，不替换成别的风格"}
    from ..style import catalog as sc

    try:
        cat = sc.load_catalog()
        by_id = {e.style_id: e for e in cat}
    except Exception:                     # noqa: BLE001
        return {"source": "none", "label": "", "options": [], "note": "风格库未加载"}

    codes = _type_codes(project)
    ids: List[str] = []
    basis = ""
    for c in codes:
        for sid in TYPE_STYLES.get(c, ()):
            if sid not in ids:
                ids.append(sid)
        if ids:
            basis = f"{c} {_type_name(c)}".strip()
            break
    if not ids:
        ids = list(PROFILE_STYLES.get(profile_id, PROFILE_STYLES["architecture"]))
        basis = "按主导专业"

    # 客户原话里点到某个风格，就把它提到第一位（客户说过的优先于系统推荐）
    said = str(getattr(project, "name", "") or "") + " " + " ".join(
        str(v) for v in (getattr(project, "constraints", {}) or {}).values()
        if isinstance(v, str))
    for n in (getattr(project, "meta", {}) or {}).get("intake", {}).get("answers", []):
        said += " " + str(n.get("answer") or "")
    hoist = [sid for sid in ids
             if sid in by_id and (by_id[sid].display_name_zh in said
                                  or by_id[sid].display_name_en.lower() in said.lower())]
    ids = hoist + [i for i in ids if i not in hoist]

    picks: List[Dict[str, str]] = []
    for sid in ids[:3]:
        e = by_id.get(sid)
        if e is None:
            continue
        picks.append({"id": e.style_id, "label": e.display_name_zh,
                      "why": (e.summary or "")[:52]})
    return {"source": "pro", "label": "", "options": picks, "basis": basis,
            "note": "客户未指定风格：按项目类型先给三个方向，G2 之前再收到一套"}


def _type_name(code: str) -> str:
    from .. import taxonomy as tax

    spec = tax.TYPES.get(code)
    return f"{spec.name}" if spec else ""


def _limits(project: Any) -> List[str]:
    """限制只取"登记在案的"：不确定项 + 任务书假设。不临时编。"""
    from ..intake import diligence as dil

    out: List[str] = []
    for u in dil.uncertainty_register(project):
        if u.get("open") is False:
            continue
        s = str(u.get("statement") or "").strip()
        if s and s not in out:
            out.append(s)
    intake = project.meta.get("intake") or {}
    for a in intake.get("assumptions") or []:
        s = str(a).strip()
        if s and s not in out and len(out) < 4:
            out.append(s)
    return out[:4]


def judge(project: Any) -> Dict[str, Any]:
    """一页判断。全部字段都能追溯到客户原话或任务书，不猜。"""
    c = iv.classification(project)
    codes = list(c.get("codes") or iv.taxonomy_codes(project))
    texts = iv._classify_texts(project)          # noqa: SLF001  同一口径，不另写一份
    blob = " ".join(texts)
    profile_id = str((project.meta.get("intake") or {}).get("profile_id") or "architecture")
    primary = tax.resolve(codes[0]) if codes else None
    aest = _aesthetic(project, profile_id)
    comp = iv.completeness(project)
    questions = [
        {"qid": q.id, "text": q.text, "why": getattr(q, "why", "")}
        for q in iv.next_questions(project, limit=3)
    ]
    return {
        "name": project.name or project.project_id,
        "discipline": _discipline_label(project, codes),
        "codes": codes,
        "type_label": (f"{codes[0]} {primary.name}" if primary and codes else "待确认类型"),
        "type_note": ("、".join(primary.focus[:3]) if primary else ""),
        "nature": "、".join(tax.NATURE_LABELS.get(n, n) for n in tax.natures(blob))
        or "待确认",
        "commission": "、".join(tax.COMMISSION_LABELS.get(c, c)
                              for c in tax.commissions(blob, codes=codes)) or "待确认",
        "focus": _focus(project),
        "aesthetic": aest,
        "limits": _limits(project),
        "completeness": comp.get("ratio", comp.get("completeness", 0.0)),
        "questions": questions,
        "assets_ask": list(ASK_ASSETS),
        "start_mode": iv.detect_start_mode(project, blob),
    }


def headline(j: Dict[str, Any]) -> str:
    """一句话判断（给汇报第一页与 S1 报告共用）。"""
    parts = [j["type_label"], j["nature"], j["commission"]]
    line = "；".join(p for p in parts if p and p != "待确认")
    if j["focus"]:
        line += "。重点：" + "、".join(f["name"] for f in j["focus"])
    return line


def render(j: Dict[str, Any]) -> str:
    lines: List[str] = [f"# 设计定位 · {j['name']}", "", f"**{headline(j)}**", ""]
    lines += ["| 项 | 判断 | 依据 |", "|---|---|---|",
              f"| 项目性质 | {j['type_label']} | 客户原话分类，代码 {('、'.join(j['codes']) or '—')} |",
              f"| 委托范围 | {j['commission']} | 任务书里的委托说明 |",
              f"| 功能重点 | " + ("、".join(f"{x['name']}（{x['note']}）" for x in j["focus"]) or "待补")
              + " | 需求矩阵 |",
              f"| 审美方向 | " + (j["aesthetic"]["label"] or
                                  "、".join(o["label"] for o in j["aesthetic"].get("options") or [])
                                  or "待定") + f" | {j['aesthetic']['note']} |",
              f"| 主要限制 | " + ("；".join(j["limits"]) or "无阻断项") + " | 任务书不确定项 |",
              ""]
    if j["questions"]:
        lines += ["## 还需要您回答的（最多三问，已答不问）", ""]
        for q in j["questions"]:
            lines.append(f"- **{q['text']}**" + (f"（{q['why']}）" if q["why"] else ""))
        lines.append("")
    lines += ["## 建议您提供（不影响先做概念）", ""]
    lines += [f"- {a}" for a in j["assets_ask"]]
    lines += ["", "## 下一步", "",
              "确认以上判断 → G1 → 概念设计（先看方向，再看图纸）。"
              "预算、测绘、法规等未定项会在相应阶段标为待确认，不阻断概念探索。", ""]
    return "\n".join(lines)


def write(project: Any, out_dir: str | Path) -> Dict[str, Any]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    j = judge(project)
    path = out / FILE
    path.write_text(render(j), encoding="utf-8")
    return {"path": str(path), "judgment": j, "headline": headline(j)}


__all__ = ["ASK_ASSETS", "FILE", "PROFILE_SPACE", "headline", "judge", "render", "write"]
