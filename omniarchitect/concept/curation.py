"""精选参考：先在已建的素材索引里找，找不到就说找不到。

为什么要有这一层
----------------
`research/library.py` 负责"能从素材库取到图"，本模块负责回答客户真正关心的
四个问题：

1. 为什么是这几张？（和这个项目的哪句话对得上）
2. 它解决了什么空间问题？（不是"好看"，是"进深大所以用通高玻璃"）
3. 哪些做法值得借鉴？（可落地的做法，不是风格形容词）
4. 哪些不能照搬？（住宅尺度、住宅层高、别人的场地条件）

纪律
----
* **只用目录里登记过的条目。** 索引是 `knowledge/library/catalog.json`，
  没登记的不许出现；匹配不上就返回 `available=False` 并说明原因——
  学校、医院、厂房在现有素材库里确实没有对应实景，这时宁可让图版以自有
  轴测与分析图为主，也不拿一张咖啡馆的照片冒充教学楼。
* **不虚构案例事实。** 说明文字只描述标签里真实存在的视觉信息（材料、光线、
  构图），不编造建筑面积、造价、获奖、事务所。
* **权限如实分级。** 素材库里的第三方摄影，可用于本项目提案并注明出处，
  但不得用于公开宣传或再分发；公开使用前须另行清权。
* **同一轮不重复检索。** 结果写进 `assets/curation.json`，同一修订号复用。

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from ..research import library as lib

#: 版面槽位：封面主图 + 三张意向 + 两张材质细部。
#: 数量按"少而准"定：3–5 个重点参考，复杂项目由调用方加槽位。
WANT: Tuple[Tuple[str, str], ...] = (
    ("hero", "space"), ("card", "space"), ("card", "space"),
    ("card", "space"), ("card", "material"), ("card", "material"),
)

ROLE_CN = {"hero": "主图", "intent": "意向", "detail": "细部"}

#: 专业 → 素材库主导专业（`library.score` 的 lead 参数）
LEAD = {
    "residential": "interior", "interior": "interior", "hospitality": "interior",
    "landscape": "landscape", "architecture": "architecture", "urban": "architecture",
}

#: 行业 → 检索硬条件。`None` 表示"这个类型在现有索引里没有可信的实景"，
#: 此时不取图，并给出原因，而不是降级成一张不相干的照片。
SECTOR_REQUIRE: Dict[str, Optional[Tuple[str, ...]]] = {
    "hospitality": ("酒店设计", "大堂吧", "卧室装饰", "水疗用品", "客厅"),
    "residential": ("室内设计", "客厅", "卧室装饰", "极简室内"),
    "office": ("办公空间", "现代办公室", "公共空间", "室内设计"),
    "landscape": ("花园", "庭院", "户外花园", "景观草坪", "喷泉景观", "树木"),
    "architecture": ("现代建筑", "建筑设计", "别墅", "公共空间", "建筑"),
    "education": None,
    "healthcare": None,
    "industrial": None,
    "generic": ("室内设计", "现代建筑", "公共空间"),
}

#: 取不到图的原因（对客户要说清"为什么这页没有实景"）
UNAVAILABLE = {
    "education": "素材库目前没有中小学教学楼的实景照片，本方向以自有轴测、"
                 "体块演变与功能分析图表达，不拿别的建筑照片冒充学校",
    "healthcare": "医院涉及医疗工艺与隐私，素材库没有可用的院内实景，"
                  "本方向以自有分析与体块图表达，院区照片须院方提供",
    "industrial": "厂房涉及客户工艺与产线保密，素材库没有对应实景，"
                  "本方向以工艺流线与体块图表达",
}

#: 权限分档：可进本项目提案 / 公开使用前须清权
RIGHTS = {
    "proposal": "素材库授权参考（仅限本项目提案，注明出处；公开宣传或再分发须另清权）",
    "link": "第三方作品，仅提供链接与出处，不嵌入版面",
}

#: 客户审美词 → 检索关键词（不是翻译引擎，只处理真实会出现的说法）
MOOD_WORDS: Dict[str, Tuple[str, ...]] = {
    "安静": ("极简主义", "中性色调", "自然光"),
    "高级": ("米色石材", "石材", "黄铜"),
    "温暖": ("暖色调", "木质墙板", "木制家具"),
    "自然": ("自然光", "室内植物", "绿色植物"),
    "明亮": ("自然光", "玻璃窗", "白色"),
    "克制": ("极简主义", "黑白灰", "单色"),
    "质感": ("石材", "微水泥", "木制家具"),
    "东方": ("木质墙板", "木梁", "侘寂"),
    "度假": ("户外游泳池", "棕榈树影", "户外花园"),
    "绿": ("绿色植物", "郁郁葱葱的绿植", "绿色色调"),
}


def _cache_path(out_dir: str | Path) -> Path:
    return Path(out_dir) / "assets" / "curation.json"


def load_cache(out_dir: str | Path) -> Dict[str, Any]:
    p = _cache_path(out_dir)
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _save_cache(out_dir: str | Path, key: str, payload: Dict[str, Any]) -> None:
    p = _cache_path(out_dir)
    p.parent.mkdir(parents=True, exist_ok=True)
    data = load_cache(out_dir)
    data[key] = payload
    p.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")


def _mood_keywords(ctx: Any) -> List[str]:
    words: List[str] = []
    for w in (getattr(ctx, "feelings", None) or {}):
        words.extend(MOOD_WORDS.get(str(w), ()))
    text = str(getattr(ctx, "feeling_text", "") or "")
    for k, v in MOOD_WORDS.items():
        if k in text:
            words.extend(v)
    return list(dict.fromkeys(words))


def terms(ctx: Any, *, sector: str = "", style_labels: Sequence[str] = ()) -> Dict[str, Any]:
    """把"客户怎么说"翻成"索引能查的条件"，并留下推理链。"""
    profile = str(getattr(ctx, "profile_id", "") or "")
    lead = LEAD.get(profile, "architecture")
    req = SECTOR_REQUIRE.get(sector if sector in SECTOR_REQUIRE else "generic")
    keywords = list(dict.fromkeys(_mood_keywords(ctx)))
    style_words = [s for s in style_labels if s]
    # 客户点名要的东西优先：房间名、业态词直接进关键词
    for n in (getattr(ctx, "needs", None) or [])[:6]:
        name = str(n.get("name") or n.get("label") or "").strip()
        if 2 <= len(name) <= 8:
            keywords.append(name)
    return {
        "lead": lead,
        "require": list(req or ()),
        "style": style_words[:4],
        "keywords": keywords[:8],
        "sector": sector,
        "basis": ("检索条件来自：客户原话里的感受词 + 选定风格 + 任务书房间名；"
                  "不是按图片好看程度挑的"),
    }


#: 各行业"不该拿来当参考"的东西。
#:
#: 私家庭院拿建筑外立面照顶替景观意向、酒店拿普通住宅客厅顶替大堂，
#: 是这类提案最常见的凑数手法——索引层就先挡掉。
AVOID: Dict[str, Tuple[str, ...]] = {
    "hospitality": ("咖啡店", "咖啡馆", "餐厅设计", "酒吧", "住宅", "公寓", "别墅"),
    "landscape": ("别墅", "公寓", "住宅", "卧室", "客厅", "餐厅设计", "咖啡店", "酒吧"),
    "education": ("酒吧", "夜店", "水疗"),
    "healthcare": ("酒吧", "夜店", "别墅"),
    "industrial": ("卧室", "客厅", "水疗", "酒吧"),
}


def _avoid_for(sector: str) -> Tuple[str, ...]:
    return AVOID.get(sector, ())


def _caption(shot: Dict[str, Any]) -> str:
    tags = [str(t) for t in (shot.get("tags") or [])]
    keep = [t for t in tags if t not in ("室内", "建筑", "室内设计", "建筑设计", "现代建筑")
            and len(t) <= 8]
    return " · ".join(keep[:3])


def explain(shot: Dict[str, Any], *, sector: str = "",
            feeling: str = "") -> Dict[str, List[str]]:
    """四个问题的答案，只用标签里真实存在的视觉信息。"""
    tags = " ".join(str(t) for t in (shot.get("tags") or []))
    why: List[str] = []
    if feeling:
        why.append(f"与您说的「{feeling}」对得上：{_caption(shot) or '整体气质克制'}")
    stone = next((t for t in ("米色石材", "石材", "大理石纹", "微水泥", "混凝土") if t in tags), "")
    wood = next((t for t in ("木质墙板", "木制家具", "木梁", "木柜") if t in tags), "")
    light = next((t for t in ("自然光", "暖色调灯光", "柔和的阳光", "光与影") if t in tags), "")
    if stone or wood:
        why.append("材料关系清楚：" + " + ".join(x for x in (stone, wood, light) if x))

    solve: List[str] = []
    if "自然光" in tags or "玻璃窗" in tags:
        solve.append("用通高开窗把光带进进深——可对照本案的采光难点看是否适用")
    if "极简主义" in tags or "单色" in tags or "黑白灰" in tags:
        solve.append("靠「少材料、大面整」压住杂乱——看它的分缝与收口，不搬颜色")
    if "室内植物" in tags or "郁郁葱葱的绿植" in tags:
        solve.append("用一处集中的绿，替代分散的小装饰，视线有落点")
    if not solve:
        solve.append("用统一的材料基调把多个功能区收成一体")

    borrow = [f"{stone} 的整面用法" if stone else "",
              f"{wood} 与浅色墙面的分缝比例" if wood else "",
              "一盏主灯 + 洗墙的层次，而不是满天花筒灯" if light else ""]
    borrow = [b for b in borrow if b]

    limits = ["住宅层高与住宅家具尺度不能直接搬到公共空间",
              "照片按「展示」布置，实际使用的家具与软装量须按本项目使用人数重新定"]
    if "别墅" in tags:
        limits.append("这是住宅外立面，不能当公共建筑的形象参考")
    return {"why": why[:2], "solve": solve[:2], "borrow": borrow[:3], "limits": limits[:2]}


def curate(out_dir: str | Path, *, ctx: Any, sector: str = "",
           style_labels: Sequence[str] = (), want: Sequence[Tuple[str, str]] = WANT,
           max_items: int = 5, exclude: Iterable[str] = (),
           use_cache: bool = True) -> Dict[str, Any]:
    """取 3–5 个重点参考；取不到就说原因，不给替代图。"""
    t = terms(ctx, sector=sector, style_labels=style_labels)
    key = f"{getattr(ctx, 'project_id', '')}|r{getattr(ctx, 'revision', 0)}|{sector}|" \
          f"{','.join(t['style'])}|{max_items}"
    if use_cache:
        cached = load_cache(out_dir).get(key)
        if cached and all(Path(s["path"]).exists() for s in cached.get("shots") or []):
            cached["cache"] = "hit"
            return cached

    if t["require"] == [] and SECTOR_REQUIRE.get(sector) is None:
        out = {"available": False, "reason": UNAVAILABLE.get(sector, "素材库无对应实景"),
               "terms": t, "shots": [], "cache": "miss"}
        _save_cache(out_dir, key, out)
        return out

    shots: List[Dict[str, Any]] = []
    slots = list(want)[: max(1, max_items)]
    got = lib.gallery(
        out_dir, lead=t["lead"], style_tags=t["style"], keywords=t["keywords"],
        want=slots, exclude=list(exclude), require=tuple(t["require"] or ()),
        avoid=_avoid_for(sector),
    )
    for i, rec in enumerate(got):
        role = "hero" if i == 0 else ("detail" if rec.get("kind") == "material" else "intent")
        feeling = next(iter((getattr(ctx, "feelings", None) or {})), "")
        shots.append({
            **rec,
            "role": role,
            "role_cn": ROLE_CN[role],
            "caption": _caption(rec),
            "rights": RIGHTS["proposal"],
            "explain": explain(rec, sector=sector, feeling=feeling),
        })

    import os

    offline = bool(os.environ.get("OMNIAILAB_NO_NETWORK"))
    out = {
        "available": bool(shots),
        "reason": ("" if shots else
                   ("离线校验模式：命中候选但未下载（联网运行时会取图）"
                    if offline else
                    "索引里没有与本项目空间用途匹配的实景，"
                    "不拿风格相近但用途不对的照片充数")),
        "terms": t,
        "shots": shots,
        "count": len(shots),
        "rights_note": ("素材库图片为第三方摄影，可用于本项目提案并注明出处；"
                        "公开宣传或再分发前须另清权"),
        "cache": "miss",
    }
    _save_cache(out_dir, key, out)
    return out


def by_role(result: Dict[str, Any], role: str) -> List[Dict[str, Any]]:
    return [s for s in (result.get("shots") or []) if s.get("role") == role]


def markdown(result: Dict[str, Any]) -> str:
    """给 `concept-options.md` 附一段可读的参考说明。"""
    lines: List[str] = ["## 精选参考（本项目提案用图）", ""]
    if not result.get("available"):
        lines += [f"- 未取图：{result.get('reason')}", ""]
        return "\n".join(lines)
    lines.append(f"- {result.get('rights_note')}")
    lines.append(f"- {result.get('terms', {}).get('basis', '')}")
    lines.append("")
    for s in result.get("shots") or []:
        role_cn = str(s.get("role_cn") or ROLE_CN.get(str(s.get("role") or ""), "参考"))
        lines.append(f"**{role_cn}｜{s.get('title', '')}**　（{s.get('credit', '')}）")
        lines.append("")
        for w in ((s.get("explain") or {}).get("why") or [])[:1]:
            lines.append(f"- 为什么：{w}")
        for b in ((s.get("explain") or {}).get("borrow") or [])[:2]:
            lines.append(f"- 可以借：{b}")
        for lim in ((s.get("explain") or {}).get("limits") or [])[:1]:
            lines.append(f"- 不能照搬：{lim}")
        lines.append("")
    return "\n".join(lines)


__all__ = ["AVOID", "LEAD", "MOOD_WORDS", "RIGHTS", "ROLE_CN", "SECTOR_REQUIRE",
           "UNAVAILABLE",
           "WANT", "by_role", "curate", "explain", "load_cache", "markdown", "terms"]
