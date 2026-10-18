"""设计意图保护：把"方案里最不能动的那几样"写成可核对的清单。

为什么需要
----------
技术和设计冲突时，最容易发生的不是争论，而是**静默替换**：

* 大跨度客厅被"顺手"加了两根柱；
* 无主灯天花被"顺手"排满了风口与检修口；
* 水景被"顺手"改成旱景，因为循环泵不好放。

每一次都说得通，加起来方案就没了。所以要把核心美学特征显式登记成
`signature_features`，技术协调**只能提出正式影响说明**，不能直接改。

设计意图不等于设计任性
----------------------
`technical_dependencies` 记录每条特征依赖什么技术条件。依赖不成立时，
意图必须让路——但让路的方式分三级：

1. 先找保留意图的技术路径（换体系、移位、隐蔽、绕行）；
2. 保留不成，比较代价，交出取舍；
3. 确实不可行，做**最小必要修改**，并留下变更记录。

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

# --------------------------------------------------------------------------
# 特征从哪来：按主导专业从概念自身的字段提取，不是套模板
SOURCES_BY_LEAD: Dict[str, Sequence[tuple]] = {
    "architecture": (
        ("spatial_logic", "空间组织原则"),
        ("zoning", "分区与围合关系"),
        ("circulation", "到达序列与动线"),
        ("daylight", "采光与开口策略"),
    ),
    "interior": (
        ("zoning", "空间分区与通透关系"),
        ("circulation", "使用动线与视线"),
        ("daylight", "室内光影策略"),
        ("experience", "到达与停留体验"),
    ),
    "landscape": (
        ("spatial_logic", "景观空间结构"),
        ("zoning", "分区与视线关系"),
        ("circulation", "游线组织"),
        ("daylight", "日照与阴影条件"),
    ),
}

#: 特征的类型判定：命中即标出它属于哪类"不能动的美学"
FEATURE_KINDS: Sequence[tuple] = (
    ("spatial", ("挑空", "通高", "大跨", "无柱", "连续", "通透", "开放")),
    ("envelope", ("立面", "轮廓", "体量", "悬挑", "屋顶", "外墙")),
    ("surface", ("天花", "背景墙", "整墙", "连续石材", "拼缝", "护墙")),
    ("light", ("无主灯", "光", "采光", "灯槽", "洗墙", "暗藏")),
    ("water", ("水景", "水池", "泳池", "跌水", "水面")),
    ("planting", ("植物", "乔木", "种植", "绿墙", "层次")),
    ("sequence", ("序列", "轴线", "到达", "过渡", "递进", "动线")),
)

#: 每类特征默认依赖什么技术条件（用于冲突时定位要问谁）
DEPENDENCIES: Dict[str, Sequence[Dict[str, str]]] = {
    "spatial": ({"discipline": "structure", "need": "跨度与梁高、能否不落柱"},),
    "envelope": ({"discipline": "structure", "need": "悬挑长度与受力路径"},
                 {"discipline": "mep", "need": "立面开口与设备进排风"}),
    "surface": ({"discipline": "mep", "need": "风管断面、桥架宽度、检修口位置"},
                {"discipline": "structure", "need": "梁底标高与净高"}),
    "light": ({"discipline": "mep", "need": "灯位回路、色温与调光"},
              {"discipline": "structure", "need": "灯槽深度与梁位关系"}),
    "water": ({"discipline": "structure", "need": "水深与池壁荷载"},
              {"discipline": "mep", "need": "循环过滤、补水与电气安全"}),
    "planting": ({"discipline": "structure", "need": "种植土厚度与附加荷载"},
                 {"discipline": "mep", "need": "灌溉水源、排水与照明"}),
    "sequence": ({"discipline": "architecture", "need": "隔墙位置与洞口"},
                 {"discipline": "mep", "need": "过渡区的通风与照明"}),
}

#: 保留设计意图的技术路径（按依赖类型给具体方向，不是"请专业研究"）
TECHNICAL_PATHS: Dict[str, Sequence[str]] = {
    "span": ("优化柱网，把柱移到非视觉焦点处",
             "改用钢结构或钢混组合，减小梁高",
             "采用局部转换或预应力，换取无柱空间",
             "调整梁上翻或梁下净高分配，保住通高效果"),
    "cantilever": ("优化悬挑受力路径（根部加高、设置拉杆或斜撑）",
                   "改用轻质悬挑构造，减小自重",
                   "分段悬挑 + 中间支承，视觉上仍连续"),
    "ceiling": ("改隐蔽风口 / 线性风口，避免外露格栅",
                "检修口整合进灯槽或造型分缝",
                "设备移位或管线绕行，局部降低吊顶而非整体压低",
                "设备与装饰一体化（风口做成造型构件）"),
    "water": ("设备下沉或移到室外隐蔽处，管线绕行",
              "改用一体化循环机组，减少明露管件",
              "调整水面标高与池壁做法，保住视觉中心"),
    "planting": ("改用轻质种植土与浅根植物，控制附加荷载",
                 "容器种植替代固定种植池，便于维护与更换",
                 "分区承重：视觉焦点区做加固，其余区减载"),
    "opening": ("调整开口尺寸与分格，保留通透感",
                "改用高透玻璃与窄边框，减少结构占位",
                "设备进排风改走屋面或侧向，不在主立面开百叶"),
    "wall": ("先确认是否承重：非承重可直接拆，承重不得拆",
             "承重墙改用门洞 + 过梁，保留通路与受力",
             "用可开启隔断 / 玻璃移门替代拆墙，视觉连通但仍可分隔",
             "局部开洞 + 边柱加固，换取视线通透"),
}


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def _text_of(concept: Dict[str, Any]) -> Dict[str, str]:
    p = concept.get("spatial_prototype") or {}
    return {
        "spatial_logic": str(p.get("spatial_logic") or ""),
        "zoning": str(p.get("zoning") or ""),
        "circulation": str(p.get("circulation") or ""),
        "daylight": str(p.get("daylight") or ""),
        "experience": str(concept.get("user_experience") or p.get("experience") or ""),
    }


def _kind_of(text: str) -> str:
    for kind, words in FEATURE_KINDS:
        if any(w in text for w in words):
            return kind
    return "spatial"


def build(project: Any, concept: Dict[str, Any], lead: Any) -> Dict[str, Any]:
    """从概念自身提取设计意图。没有依据的特征不写。

    `lead` 是 `Leadership`；主导专业决定"哪些字段算核心意图"。
    室内主导时不会把建筑立面写成受保护特征——那不是这次委托的美学主张。
    """
    fields = _text_of(concept)
    lead_id = getattr(lead, "lead", "interior")
    sources = SOURCES_BY_LEAD.get(lead_id, SOURCES_BY_LEAD["interior"])

    features: List[Dict[str, Any]] = []
    for i, (key, label) in enumerate(sources, start=1):
        text = fields.get(key, "").strip()
        if len(text) < 8:
            continue                     # 没写清楚的不算特征，避免凑数
        kind = _kind_of(text)
        features.append({
            "id": f"SF-{i:02d}",
            "kind": kind,
            "name": label,
            "statement": text,
            "source_field": key,
            "why_protected": f"这是{getattr(lead, 'lead_label', lead_id)}对"
                             f"「{label}」的核心主张，技术协调不得静默改写",
            "technical_dependencies": [dict(d) for d in DEPENDENCIES.get(kind, ())],
        })

    materials = [str(m.get("name")) for m in (concept.get("material_direction") or [])
                 if isinstance(m, dict) and m.get("name")]
    principles = [str(x) for x in (concept.get("lighting_direction") or [])][:3]
    goals = [s for s in (fields.get("experience", ""),
                         concept.get("concept_statement", "")) if s][:2]

    intent = {
        "design_intent_id": "",
        "lead_discipline": lead_id,
        "lead_label": getattr(lead, "lead_label", lead_id),
        "joint_lead_discipline": getattr(lead, "joint_lead", ""),
        "mode": getattr(lead, "mode", ""),
        "concept_id": concept.get("concept_id", ""),
        "design_principles": principles or [str(concept.get("concept_statement") or "")],
        "signature_features": features,
        "protected_visual_elements": [
            {"id": f"PV-{i:02d}", "kind": f["kind"], "name": f["name"],
             "statement": f["statement"]}
            for i, f in enumerate(features, start=1)
        ],
        "spatial_experience_goals": [g for g in goals if g],
        "material_direction": materials,
        "acceptable_adjustments": [
            "在不改变视觉特征的前提下调整材料品牌或同档替代",
            "在不降低净高的前提下调整设备形式与位置",
            "在不改变空间序列的前提下调整家具尺寸",
            "经业主确认后可调整非核心界面的做法",
        ],
        "technical_dependencies": sorted({
            f"{d['discipline']}:{d['need']}"
            for f in features for d in f["technical_dependencies"]
        }),
        "revision": int(getattr(project, "revision", 1) or 1),
        "created_at": _now(),
        "note": ("特征来自概念原文，不是模板。技术方案需要改变这些特征时，"
                 "必须出具正式影响说明并经业主确认，不得静默替换。"),
    }
    seed = "|".join([str(concept.get("concept_id") or ""), lead_id,
                     *[f["statement"] for f in features]])
    intent["design_intent_id"] = "DI-" + hashlib.sha1(
        seed.encode("utf-8")).hexdigest()[:10]
    return intent


def write(project: Any, out_dir: str | Path, intent: Dict[str, Any]) -> Path:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    p = out / f"design-intent-r{intent.get('revision', 1)}.json"
    p.write_text(json.dumps(intent, ensure_ascii=False, indent=2) + "\n",
                 encoding="utf-8")
    meta = getattr(project, "meta", None)
    if not isinstance(meta, dict):
        project.meta = {}
        meta = project.meta
    meta["design_intent"] = {**intent, "file": str(p)}
    return p


def load(project: Any) -> Optional[Dict[str, Any]]:
    raw = (getattr(project, "meta", {}) or {}).get("design_intent") or {}
    return dict(raw) or None


# --------------------------------------------------------------------------
# 冲突检测：这次改动是否动了受保护特征
def protect_check(project: Any, text: str) -> Dict[str, Any]:
    """判断改动是否触及设计意图。

    只做"字面触及"的判断——不做语义猜测。触及不一定否决，但必须走正式说明。
    """
    intent = load(project)
    if not intent:
        return {"has_intent": False, "touched": [], "requires_formal": False,
                "note": "尚无 G2 确认的设计意图基准：只能做一般性影响分析"}

    touched: List[Dict[str, Any]] = []
    for f in intent.get("signature_features") or []:
        stmt = str(f.get("statement") or "")
        kind = str(f.get("kind") or "")
        # 两条通道：特征原文里的术语 → 精确命中；
        # 类型触发词 → 保守命中（可能动到该类特征）。
        own = [w for w in _keywords(stmt) if w in text]
        trig = [w for w in KIND_TRIGGERS.get(kind, ()) if w in text]
        matched = list(dict.fromkeys(own + trig))
        if own or (trig and len(trig) >= 1):
            touched.append({
                "feature_id": f["id"], "name": f["name"], "kind": kind,
                "statement": stmt, "matched": matched[:5],
                "matched_exact": own,
                "matched_by_kind": trig,
                "basis": ("特征原文命中：" + "、".join(own)) if own
                         else ("按「" + str(f.get("name")) + "」同类触发："
                               + "、".join(trig)),
                "technical_dependencies": f.get("technical_dependencies") or [],
            })
    return {
        "has_intent": True,
        "design_intent_id": intent.get("design_intent_id", ""),
        "lead_discipline": intent.get("lead_discipline", ""),
        "lead_label": intent.get("lead_label", ""),
        "touched": touched,
        "requires_formal": bool(touched),
        "note": ("触及核心设计特征：技术调整必须先出正式影响说明，"
                 "不得静默修改。" if touched else
                 "未触及核心设计特征，可按常规变更处理。"),
    }


#: 设计术语词典：用于判断"改动请求是否提到这条特征"。
#: 不用分词器（中文分词在"过渡区/公共区"这类词上会把复合词切碎），
#: 用一张受控词表做集合交集，宁可多命中一次、多要一份说明，
#: 也不静默放过一次改动。
TERMS: Sequence[str] = (
    "客厅", "餐厅", "卧室", "主卧", "次卧", "厨房", "卫生间", "浴室", "玄关",
    "过渡区", "公共区", "私密区", "家政", "书房", "儿童房", "阳台", "露台",
    "走廊", "动线", "视线", "序列", "分区", "隔断", "屏风", "隔墙", "墙",
    "开放", "通透", "连续", "挑空", "通高", "大跨", "无柱", "跨度",
    "采光", "高窗", "玻璃砖", "天窗", "日照", "遮挡", "阴影", "光",
    "天花", "吊顶", "背景墙", "主墙", "整墙", "石材", "木饰面", "拼缝",
    "灯槽", "主灯", "灯带", "洗墙", "色温", "照度",
    "水景", "水池", "泳池", "跌水", "水面", "循环", "泵",
    "庭院", "院子", "花园", "屋顶", "植物", "乔木", "种植", "绿化", "铺装",
    "园路", "台阶", "地形", "竖向", "排水",
    "立面", "悬挑", "体量", "轮廓", "外墙", "幕墙", "开口", "窗",
    "收纳", "柜体", "家具", "风口", "检修口", "风管", "桥架", "喷淋", "净高",
)

#: 类型触发词：请求提到这些，就视为可能动到该类型的美学特征。
#: 这是"保守触发"——目的是把冲突摆到台面上，而不是替谁下结论。
KIND_TRIGGERS: Dict[str, Sequence[str]] = {
    # 「墙」单独出现太容易误触：换个墙面颜色也会命中"空间分区"。
    # 只有"拆/打/开/合并/隔断"这类**改动空间关系**的词才算碰到分区。
    "spatial": ("隔墙", "开放", "打通", "打掉", "拆", "合并", "拆分", "隔断",
                "跨度", "加柱", "柱子"),
    "envelope": ("立面", "外墙", "幕墙", "窗", "开口", "悬挑", "体量", "轮廓", "屋顶"),
    "surface": ("天花", "吊顶", "背景墙", "墙面", "石材", "木饰面", "风口", "检修口", "造型"),
    "light": ("灯", "照", "光", "色温", "灯槽", "洗墙", "主灯"),
    "water": ("水景", "水池", "泳池", "循环", "泵", "防水"),
    "planting": ("植物", "乔木", "种植", "绿化", "灌溉", "土"),
    "sequence": ("玄关", "过渡", "动线", "序列", "走廊", "入口"),
}

#: 只改表面、不动空间关系的请求。命中这些且不含结构词时，
#: 不要求走"保留技术路径"——那是浪费，也会让保护机制失去可信度。
SURFACE_ONLY: Sequence[str] = (
    "换个颜色", "换颜色", "改成哑光", "换个材质", "换材质", "换石材", "换木饰面",
    "刷漆", "重新刷", "贴壁纸", "换壁纸", "换个面层", "做同色", "色号",
)


def _keywords(text: str) -> List[str]:
    """从特征原文里取可匹配的设计术语。"""
    return [t for t in TERMS if t in str(text)]


# --------------------------------------------------------------------------
# Design-First 冲突处理：六级顺序，不允许跳过
def resolve(project: Any, text: str, *, lead: Any = None) -> Dict[str, Any]:
    """按六级顺序给出处理路径。**不自动修改设计**，只给判断与选项。"""
    check = protect_check(project, text)
    if not check.get("has_intent"):
        return {"levels": [], "verdict": "no_intent", **check}

    levels: List[Dict[str, Any]] = []
    # 第一级：确认冲突是否真实存在
    levels.append({
        "level": 1,
        "name": "确认冲突是否真实存在",
        "done": False,
        "action": ("核对受影响的特征是否真的被本次改动触碰；"
                   "未经核实的猜测不得用来改变设计"),
        "basis": ("触及特征：" + "、".join(t["name"] for t in check["touched"]))
                 if check["touched"] else "未触及核心特征，无需进入技术路径比较",
    })

    if not check["touched"]:
        return {"levels": levels, "verdict": "no_conflict", **check,
                "note": "未触及设计意图，按常规变更流程处理。"}

    # 只改面层、不动空间关系：属于 design intent 里已列明的"可接受调整"，
    # 不必走技术路径比较。把它也拦下来会让保护机制变成噪音。
    if _surface_only(text):
        levels.append({
            "level": 2,
            "name": "属于可接受调整范围",
            "done": True,
            "action": ("只改面层做法或同档替代，不改变视觉特征与空间关系："
                       "按材料变更处理，保持色号与拼缝原则一致"),
        })
        return {"levels": levels, "verdict": "acceptable_adjustment", **check,
                "requires_formal": False,
                "note": "面层级调整，未改变设计特征；仅需记录材料变更。"}

    # 第二级：辅助专业先给保留意图的技术路径
    paths: List[Dict[str, Any]] = []
    for t in check["touched"]:
        for dep in t["technical_dependencies"]:
            key = _path_key(t["kind"], dep.get("need", ""), text)
            for opt in TECHNICAL_PATHS.get(key, ()):
                paths.append({"feature": t["name"], "discipline": dep["discipline"],
                              "path": opt, "kind": key})
    # 去重但保留顺序
    seen = set()
    paths = [p for p in paths
             if not ((p["path"] in seen) or seen.add(p["path"]))]
    levels.append({
        "level": 2,
        "name": "先找保留设计意图的技术路径",
        "done": False,
        "action": "由结构 / 机电提出至少一种能保住特征的技术实现方案",
        "options": paths[:6],
        "rule": "不能因为某种结构方式较复杂，就自动否定原设计",
    })

    # 第三级：多路径比较
    levels.append({
        "level": 3,
        "name": "比较各路径的代价",
        "done": False,
        "compare_on": ["对外观的影响", "对空间与净高的影响", "技术复杂程度",
                       "施工难度", "造价影响", "工期影响", "所需专业计算与复核"],
        "rule": "技术复杂但可行 ≠ 劣质设计；必须如实披露代价，不能直接判死",
    })

    # 第四级：推荐最少损害美学的方案
    levels.append({
        "level": 4,
        "name": "推荐最少损害设计意图的方案",
        "done": False,
        "rule": "在满足安全与规范的前提下，优先推荐保留特征的方案",
    })

    # 第五级：确不可行才改设计
    levels.append({
        "level": 5,
        "name": "确不可行时提出最小必要修改",
        "done": False,
        "action": "由总设计师提出改动范围最小的方案，并说明为什么保留不下来",
        "rule": "最小必要 = 只改必须改的那一处，不顺带调整其他特征",
    })

    # 第六级：变更审批
    levels.append({
        "level": 6,
        "name": "重新影响分析与审批",
        "done": False,
        "action": "涉及已确认设计意图的变更，须重开 G2 并写入变更记录",
        "rule": "不得在上一次确认的基准上直接覆盖",
    })

    return {
        "levels": levels,
        "verdict": "needs_technical_path",
        "design_intent_id": check.get("design_intent_id", ""),
        "lead_label": check.get("lead_label", ""),
        "requires_formal": True,
        "note": ("本轮只给出处理顺序与技术方向，不代替结构计算，也不自动改设计。"
                 "安全与规范不可突破；在此前提下最大限度保留设计意图。"),
    }


def _surface_only(text: str) -> bool:
    """只改面层，不动空间关系。"""
    if not any(w in text for w in SURFACE_ONLY):
        return False
    return not any(w in text for w in ("拆", "打掉", "打通", "改结构", "加柱",
                                       "悬挑", "跨度", "加层", "开洞"))


def _path_key(kind: str, need: str, text: str = "") -> str:
    # 请求本身说"打墙/拆墙"，走承重判定，而不是柱网优化——两者代价差一个量级
    if any(w in text for w in ("拆墙", "打墙", "墙打掉", "把墙", "隔墙拆", "打通")):
        return "wall"
    if kind == "spatial":
        return "span"
    if kind == "envelope":
        return "cantilever" if "悬挑" in need else "opening"
    if kind == "surface":
        return "ceiling"
    if kind == "water":
        return "water"
    if kind == "planting":
        return "planting"
    if kind == "light":
        return "ceiling"
    return "span"


def summary_lines(intent: Dict[str, Any]) -> List[str]:
    lines = [f"- 设计意图：`{intent.get('design_intent_id', '')}`"
             f"（主导：{intent.get('lead_label', '')}）"]
    for f in (intent.get("signature_features") or [])[:5]:
        lines.append(f"- 受保护特征 {f['id']}｜{f['name']}：{str(f['statement'])[:48]}")
    deps = intent.get("technical_dependencies") or []
    if deps:
        lines.append(f"- 技术依赖 {len(deps)} 项：" + "；".join(deps[:3]))
    return lines


__all__ = ["build", "write", "load", "protect_check", "resolve", "summary_lines",
           "TECHNICAL_PATHS", "DEPENDENCIES", "FEATURE_KINDS"]
