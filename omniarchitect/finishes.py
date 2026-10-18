"""饰面与材料推导 —— 项目没有说过的，不许替它编。

S4/S5/S8 原来各写了一张固定的面层表：客厅餐厅做弧形叠级、墙面微水泥/暖白乳胶漆、
卧室木地板、天花石膏板。这些默认值对住宅勉强成立，换成办公、酒店、商业就是错的：
一个 800㎡ 办公室被安排"主卧木地板"，客户一眼就知道系统没在听。

这一层把"面层从哪来"讲清楚：

| 数据 | 来源 | 缺失时 |
|---|---|---|
| 项目类型 | S1 访谈的 profile | 按项目文本判断，判不出就按建筑类处理 |
| 空间与分区 | `project.spaces` 的 `use` / `zone` | 不编房间，只写"未分区" |
| 材料与色彩 | 选定概念的 `material_direction` / `palette` | 写"待确认（S4 与主创定案）" |
| 做法（平顶/灯槽等） | 分区的通用做法，不带住宅房名 | — |
| 工程用量 | `quantities.takeoff()` | — |

判断标准很简单：**办公项目里不允许出现"卧室""主卧""儿童房"**。这条由测试守着，
不靠写文档的人自觉。

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple

from .model import Project

#: 项目类型 → 中文标签。与 intake profiles 的 id 对齐，不另造一套。
PROFILE_LABEL = {
    "residential": "住宅",
    "office": "办公",
    "hospitality": "酒店 / 民宿",
    "retail": "餐饮 / 零售",
    "exhibition": "展厅",
    "architecture": "建筑 / 新建",
}

#: 分区 → 面向客户的叫法（避免"客厅"这类住宅词流到办公项目）
ZONE_LABEL = {
    "day": "公共区",
    "night": "私密区",
    "service": "服务区",
    "entry": "入口区",
    "wet": "湿区",
    "": "未分区",
}

#: 分区 → 通用面层做法。只写工艺，不写材料品牌，不写住宅房名。
ZONE_CEILING = {
    "day": ("平顶 + 隐藏灯槽（主导线）", "2600"),
    "night": ("平顶 + 窗帘盒（有外窗时）", "2500"),
    "service": ("可检修平顶 + 检修口", "2400"),
    "entry": ("平顶 + 线性灯带导向", "2500"),
    "wet": ("防水石膏板 / 铝扣板", "2400"),
    "": ("平顶", "2600"),
}

ZONE_WALL = {
    "day": "主墙面做整体性材料，其余留白",
    "night": "墙面以柔光饰面为主，减少反射",
    "service": "耐擦洗、可局部更换",
    "entry": "入口端景做一处视觉锚点",
    "wet": "防水基层 + 耐水饰面",
    "": "按材料表",
}

ZONE_FLOOR = {
    "day": "整体无缝或大规格，缝宽统一",
    "night": "脚感优先，接口收在门洞内",
    "service": "耐磨、易清洁",
    "entry": "耐磨且防滑，与公共区对缝",
    "wet": "防滑，找坡向地漏",
    "": "按材料表",
}

PENDING = "待确认（S4 与主创定案）"

#: 住宅专用词。出现在非住宅项目成果里即视为串味。
RESIDENTIAL_WORDS = ("客厅", "主卧", "次卧", "儿童房", "卧室", "厨房", "玄关",
                     "阳台", "书房", "餐厅")


# --------------------------------------------------------------------------
def project_profile(project: Project) -> str:
    """Which design profile this project belongs to. Never assumes residential."""
    meta = project.meta if isinstance(project.meta, dict) else {}
    intake = meta.get("intake") if isinstance(meta.get("intake"), dict) else {}
    pid = str(intake.get("profile_id") or "")
    if pid in PROFILE_LABEL:
        return pid
    from .intake.profiles import profile_for

    text = " ".join([project.name or "", project.project_id,
                     " ".join(str(p.get("name") or "") for p in (project.program or []))])
    return profile_for(text).id


def profile_label(project: Project) -> str:
    return PROFILE_LABEL.get(project_profile(project), "未分类")


def is_residential(project: Project) -> bool:
    return project_profile(project) == "residential"


def style_label(project: Project) -> str:
    """Declared style, or an honest "not specified" — never a default style."""
    declared = str((project.constraints or {}).get("style") or "").strip()
    if declared:
        return declared
    chosen = selected_concept(project)
    labels = list(chosen.get("style_labels") or []) if chosen else []
    if labels:
        return " + ".join(labels) + "（概念方案选定）"
    return "未指定风格（按概念方案的材料方向执行）"


def selected_concept(project: Project) -> Dict[str, Any]:
    """The concept G2 signed, if any. Empty dict when nothing is selected."""
    meta = project.meta if isinstance(project.meta, dict) else {}
    state = meta.get("concept") if isinstance(meta.get("concept"), dict) else {}
    options = state.get("options") or {}
    cid = str(state.get("selected") or "")
    if not cid:
        return {}
    return next((c for c in (options.get("concepts") or [])
                 if c.get("concept_id") == cid), {})


def concept_materials(project: Project) -> List[Dict[str, str]]:
    chosen = selected_concept(project)
    out: List[Dict[str, str]] = []
    for m in (chosen.get("material_direction") or []):
        if isinstance(m, dict) and m.get("name"):
            out.append({"name": str(m["name"]),
                        "application": str(m.get("application") or ""),
                        "finish": str(m.get("finish") or "")})
    return out


def concept_palette(project: Project) -> List[Dict[str, Any]]:
    chosen = selected_concept(project)
    palette = (chosen.get("palette") or {}) if chosen else {}
    rows: List[Dict[str, Any]] = []
    for band in ("dominant", "secondary", "accent"):
        for item in (palette.get(band) or []):
            if isinstance(item, dict) and item.get("hex"):
                rows.append({"band": band, "name": str(item.get("name") or ""),
                             "hex": str(item.get("hex")), "pct": item.get("pct"),
                             "usage": str(item.get("usage") or "")})
    return rows


def zones(project: Project) -> List[Tuple[str, str, List[str]]]:
    """(zone, label, space names) in a stable order — from the real program."""
    order = ["day", "entry", "night", "service", "wet", ""]
    found: Dict[str, List[str]] = {}
    for p in (project.program or []):
        zone = str(p.get("zone") or "")
        name = str(p.get("name") or "").strip()
        if name:
            found.setdefault(zone, []).append(name)
    # 模型里已有空间时以模型为准（它们才是真正要出图/算量的对象）；
    # 只有外壳、还没装方案时退回任务书的功能表。
    live = [s for s in project.spaces if s.use != "envelope"]
    if live:
        found = {}
        for s in live:
            found.setdefault(str(s.properties.get("zone") or ""), []).append(
                s.name or s.use)
    return [(z, ZONE_LABEL.get(z, z), found[z])
            for z in order if z in found] or [("", "未分区", [])]


def _material_for(project: Project, keywords: Sequence[str]) -> str:
    """Pick the concept material whose application mentions this surface."""
    mats = concept_materials(project)
    for m in mats:
        blob = m["name"] + m["application"]
        if any(k in blob for k in keywords):
            return f"{m['name']}（{m['finish'] or m['application'] or '做法待定'}）"
    return PENDING


def ceiling_rows(project: Project) -> List[Dict[str, str]]:
    rows = []
    for zone, label, _names in zones(project):
        method, level = ZONE_CEILING.get(zone, ZONE_CEILING[""])
        rows.append({"zone": label, "method": method, "level": level,
                     "light": "内嵌灯带 3000K" if zone in ("day", "entry") else "—"})
    return rows


def wall_rows(project: Project) -> List[Dict[str, str]]:
    rows = []
    for zone, label, _names in zones(project):
        rows.append({"zone": label, "method": ZONE_WALL.get(zone, ZONE_WALL[""]),
                     "material": _material_for(project, ("墙", "wall", "饰面"))})
    return rows


def floor_rows(project: Project) -> List[Dict[str, str]]:
    rows = []
    for zone, label, _names in zones(project):
        rows.append({"zone": label, "material": _material_for(project, ("地", "floor")),
                     "spec": ZONE_FLOOR.get(zone, ZONE_FLOOR[""])})
    return rows


def palette_rows(project: Project) -> List[Dict[str, str]]:
    chosen = selected_concept(project)
    policy = (chosen.get("aesthetic_policy") or {}) if chosen else {}
    rows = []
    for item in concept_palette(project):
        rows.append({"group": {"dominant": "主色", "secondary": "辅色",
                               "accent": "重音"}.get(item["band"], item["band"]),
                     "material": item["name"], "hex": item["hex"],
                     "pct": f"{item['pct']}%" if item.get("pct") else "—"})
    if rows:
        return rows
    ratio = str(policy.get("ratio_rule") or "")
    return [{"group": "整体", "material": "待确认", "hex": "—",
             "pct": ratio or PENDING}]


def lighting_rows(project: Project) -> List[Dict[str, str]]:
    chosen = selected_concept(project)
    direction = [str(x) for x in (chosen.get("lighting_direction") or []) if x]
    if direction:
        return [{"layer": f"方案 {i + 1}", "method": d, "param": "按概念方案执行"}
                for i, d in enumerate(direction[:4])]
    return [{"layer": "基础", "method": "洗墙 + 筒灯", "param": "3000K / Ra≥90，照度待照明计算"},
            {"layer": "重点", "method": "按功能面定位", "param": "3000K，重点面待定"},
            {"layer": "自然光", "method": "按朝向保留，不补光打平", "param": "—"}]


def material_rows(project: Project, quantities: Any) -> List[Dict[str, str]]:
    """S8 材料表：材料名来自概念，用量来自工程量，档次/替代不猜。"""
    q = getattr(quantities, "quantities", {}) or {}

    def area_of(application: str) -> str:
        if any(k in application for k in ("地", "floor")):
            return f"{q.get('floor_area_m2', 0):.1f} m²"
        if any(k in application for k in ("墙", "wall")):
            return f"{q.get('wall_finish_area_m2', 0):.1f} m²"
        if any(k in application for k in ("天花", "ceiling", "顶")):
            return f"{q.get('ceiling_area_m2', 0):.1f} m²"
        if any(k in application for k in ("柜", "joinery", "家具")):
            return f"{q.get('joinery_area_m2', 0):.1f} m²"
        return "—"

    mats = concept_materials(project)
    if mats:
        return [{"part": m["application"] or "未注明部位", "material": m["name"],
                 "spec": m["finish"] or "做法待定", "tier": "按锁定风格档位",
                 "qty": area_of(m["application"]), "waste": "按材料 5–10%",
                 "alt": "同档位同类品，须报批", "source": "概念方案"}
                for m in mats]

    # 没有概念材料：只列可计量的通用部位，材料明确写"待确认"
    return [
        {"part": "地面", "material": PENDING, "spec": "—", "tier": "待定",
         "qty": f"{q.get('floor_area_m2', 0):.1f} m²", "waste": "8%",
         "alt": "待定", "source": "工程量"},
        {"part": "墙面", "material": PENDING, "spec": "—", "tier": "待定",
         "qty": f"{q.get('wall_finish_area_m2', 0):.1f} m²", "waste": "10%",
         "alt": "待定", "source": "工程量"},
        {"part": "天花", "material": PENDING, "spec": "—", "tier": "待定",
         "qty": f"{q.get('ceiling_area_m2', 0):.1f} m²", "waste": "8%",
         "alt": "待定", "source": "工程量"},
        {"part": "门窗", "material": PENDING, "spec": "—", "tier": "待定",
         "qty": f"门 {q.get('door_count', 0):.0f} 樘 / 窗 {q.get('window_count', 0):.0f} 樘",
         "waste": "0%", "alt": "待定", "source": "工程量"},
    ]


def view_rows(project: Project, limit: int = 4) -> List[Dict[str, str]]:
    """S5 表现清单：名字来自真实空间，住宅项目才有"客厅/主卧"。"""
    rows = [{"no": "01", "name": "全景", "use": "汇报封面",
             "lens": "24mm，1.6m 眼高"}]
    spaces = [s for s in project.spaces if s.use != "envelope"] or \
             [type("S", (), {"name": p.get("name"), "use": p.get("recipe") or "",
                             "area_m2": p.get("area_m2") or 0})()
              for p in (project.program or [])]
    spaces = sorted(spaces, key=lambda s: -(getattr(s, "area_m2", 0) or 0))[:limit]
    for i, s in enumerate(spaces, start=2):
        rows.append({"no": f"{i:02d}", "name": str(getattr(s, "name", "") or "空间"),
                     "use": "主推" if i == 2 else "辅助",
                     "lens": "35mm，房间对角" if i == 2 else "35mm"})
    rows.append({"no": f"{len(rows) + 1:02d}", "name": "轴测", "use": "空间关系",
                 "lens": "50mm 正交倾向"})
    rows.append({"no": f"{len(rows) + 1:02d}", "name": "全景漫游", "use": "交付",
                 "lens": "沿主动线，60s"})
    return rows


def finish_map(project: Project) -> Dict[str, str]:
    """面层字典，给渲染/画布的提示词用。空字典 = 不写材料句。

    顺序：概念材料优先，其次项目 constraints 里的 materials。
    绝不填默认值——默认值是"替客户拍板"，比不写更糟。
    """
    out: Dict[str, str] = {}
    mats = concept_materials(project)
    for surface, keys in (("floor", ("地", "floor")), ("wall", ("墙", "wall")),
                          ("ceiling", ("天花", "顶", "ceiling"))):
        for m in mats:
            blob = m["name"] + m["application"]
            if any(k in blob for k in keys):
                out[surface] = f"{m['name']}（{m['finish'] or m['application'] or '做法待定'}）"
                break
    declared = (project.constraints or {}).get("materials") or {}
    if isinstance(declared, dict):
        for k, v in declared.items():
            if isinstance(v, str) and v.strip() and k not in out:
                out[str(k)] = v.strip()
    return out


def foreign_words(project: Project, text: str) -> List[str]:
    """Words in `text` that do not belong to this project type."""
    if is_residential(project):
        return []
    return [w for w in RESIDENTIAL_WORDS if w in text]


__all__ = [
    "PROFILE_LABEL", "ZONE_LABEL", "RESIDENTIAL_WORDS", "PENDING",
    "project_profile", "profile_label", "is_residential", "style_label",
    "selected_concept", "concept_materials", "concept_palette", "zones",
    "ceiling_rows", "wall_rows", "floor_rows", "palette_rows", "lighting_rows",
    "material_rows", "view_rows", "foreign_words", "finish_map",
]
