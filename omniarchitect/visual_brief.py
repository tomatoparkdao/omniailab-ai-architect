"""Professional visual briefs: what to render, from which geometry, and what must not move.

A picture prompt that says "modern interior, high-end" produces a nice image of
somebody else's building. The brief here is built the other way round: the
numbers come out of the model first, and the prompt is written around them.

    geometry  →  开间/进深/层高/墙厚/门窗数量与位置
    material  →  已确认方案里的饰面与主材
    camera    →  固定机位，与 SketchUp 截图同参数，才比得了
    invariants→  哪些东西画面里不许出现、不许改动

Three disciplines, three rule sets. A school entrance and a courtyard gate are
not the same subject and must not share a sentence template.

This module produces a *brief*, not an image. Whether anything is rendered
depends on the provider being wired — and that verdict is recorded, not assumed.

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

#: Things a render must never do. Shared by all disciplines — these are the
#: failure modes that make a picture useless as a design communication.
NEGATIVE_BASE = (
    "不要出现人物、文字、水印、logo；不要改变房间数量与开间进深；"
    "不要增加平面图上没有的门窗或隔墙；不要出现施工脚手架与临时设施；"
    "不要过曝、不要鱼眼畸变、不要卡通或插画质感"
)

#: Per-discipline emphasis. What a reader of that discipline looks at first.
DISCIPLINE_RULES: Dict[str, Dict[str, Any]] = {
    "architecture": {
        "label": "建筑",
        "focus": "体量关系、立面比例与开窗节奏、入口的可识别性、与场地和天空的关系",
        "light": "日光，太阳高度角约 35°，主光来自画面左前方，天气通透",
        "shots": (
            ("A-ENTRY", "主入口人视", 24.0, "入口的可识别性与雨棚、台阶、无障碍坡道的关系"),
            ("A-FACADE", "主立面", 35.0, "开窗节奏、层间比例、材料分缝与转角处理"),
            ("A-AXON", "鸟瞰体量", 28.0, "体量组合、屋顶形态、与周边场地的关系"),
        ),
    },
    "interior": {
        "label": "室内",
        "focus": "空间比例与层高感受、界面材料、家具尺度、自然光与人工光的层次",
        "light": "自然光为主，窗口方向有柔和日光，室内补光克制，色温 3500K 左右",
        "shots": (
            ("I-MAIN", "主要空间", 24.0, "最常用的空间，读得到家具布置与墙地顶关系"),
            ("I-SECOND", "次要空间", 35.0, "过渡空间或次要用房，检验动线是否顺畅"),
            ("I-MATERIAL", "材料特写", 50.0, "主材的质感、接缝与收口，以及光在材料上的表现"),
        ),
    },
    "landscape": {
        "label": "景观",
        "focus": "场地整体结构、园路走向、水景与铺装的边界、植物层次与视线关系",
        "light": "清晨或傍晚的低角度日光，长阴影，空气通透",
        "shots": (
            ("L-OVERALL", "整体鸟瞰", 24.0, "园路、水景、铺装与种植的分区关系"),
            ("L-ENTRY", "入口人视", 35.0, "入口的到达感与第一视线"),
            ("L-NODE", "核心节点", 35.0, "停留节点的尺度、坐具与观景方向"),
        ),
    },
}


@dataclass
class Shot:
    id: str
    label: str
    kind: str
    prompt: str
    negative: str
    camera: Dict[str, Any]
    invariants: List[str] = field(default_factory=list)
    references: List[str] = field(default_factory=list)
    checks: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {"id": self.id, "label": self.label, "kind": self.kind,
                "prompt": self.prompt, "negative": self.negative,
                "camera": self.camera, "invariants": list(self.invariants),
                "references": list(self.references), "checks": list(self.checks)}


# ----------------------------------------------------------------------
#: Uses that describe the site, not a designed room. A 24 000 m² "site ground"
#: is not the biggest room in the school — counting it that way makes the prompt
#: ask for a 24 000 m² interior.
SITE_USES = {"envelope", "site_ground", "site_building", "sport", "forecourt"}

#: Landscape works in zones, not rooms. Calling a planting bed a room is the
#: exact confusion the discipline separation is meant to prevent.
LANDSCAPE_USES = ("water", "planting", "paving", "circulation")


def geometry_facts(project: Any, level_id: Optional[str] = None,
                   discipline: str = "interior") -> Dict[str, Any]:
    """Countable facts a picture has to agree with."""
    if discipline == "landscape":
        spaces = [s for s in project.spaces_on("L-SITE")
                  if s.use in LANDSCAPE_USES and len(s.boundary_mm2d) >= 3]
        unit = "分区"
    else:
        spaces = [s for s in project.spaces
                  if s.use not in SITE_USES and len(s.boundary_mm2d) >= 3
                  and (level_id is None or s.level_id == level_id)]
        unit = "房间"
    out: Dict[str, Any] = {"unit": unit, "rooms": 0, "doors": 0, "windows": 0,
                           "levels": 0, "storey_height_m": 0.0,
                           "envelope_m": None, "wall_thickness_mm": 0,
                           "wet_rooms": 0, "largest_room": None}
    if not spaces:
        return out
    out["rooms"] = len(spaces)
    pts = [p for s in spaces for p in s.boundary_mm2d]
    x0, y0 = min(p[0] for p in pts), min(p[1] for p in pts)
    x1, y1 = max(p[0] for p in pts), max(p[1] for p in pts)
    out["envelope_m"] = (round((x1 - x0) / 1000.0, 2), round((y1 - y0) / 1000.0, 2))
    levels = [lv for lv in project.levels if lv.height_mm]
    out["levels"] = len(levels)
    out["storey_height_m"] = round(max((lv.height_mm for lv in levels), default=0) / 1000.0, 2)
    ids = {s.level_id for s in spaces}
    out["doors"] = sum(1 for d in project.by_type("door") if d.level_id in ids)
    out["windows"] = sum(1 for w in project.by_type("window") if w.level_id in ids)
    thick = [(w.geometry or {}).get("thickness_mm") for w in project.by_type("wall")
             if w.level_id in ids]
    thick = [float(t) for t in thick if t]
    out["wall_thickness_mm"] = int(max(thick)) if thick else 0
    out["wet_rooms"] = sum(1 for s in spaces if s.use in ("bathroom", "wc"))
    biggest = max(spaces, key=lambda s: s.area_m2)
    out["largest_room"] = {"name": biggest.name, "area_m2": round(biggest.area_m2, 1)}
    return out


def _invariants(facts: Dict[str, Any], discipline: str) -> List[str]:
    """The clauses an image model most often violates, stated as hard rules."""
    unit = facts.get("unit") or "房间"
    if discipline == "landscape":
        return [f"{unit}数量固定为 {facts['rooms']} 个，功能分区不得合并或新增",
                "园路走向、水景边界与铺装分区按平面图，不得自行改线",
                f"场地范围约 {facts['envelope_m'][0]:.0f} m × {facts['envelope_m'][1]:.0f} m，"
                "不得放大或缩小" if facts["envelope_m"] else "场地范围按平面图"]
    out = [f"{unit}数量固定为 {facts['rooms']} 间，不得合并或增加",
           f"门窗数量固定：门 {facts['doors']} 樘、窗 {facts['windows']} 樘，位置按平面图"]
    if facts["storey_height_m"]:
        out.append(f"层高 {facts['storey_height_m']:.2f} m，不得加高或压低")
    if facts["envelope_m"]:
        w, d = facts["envelope_m"]
        out.append(f"外轮廓约 {w} m × {d} m，开间进深比例不得改变")
    if facts["wall_thickness_mm"] and discipline == "interior":
        out.append(f"内墙厚度约 {facts['wall_thickness_mm']} mm，不得做成通高玻璃隔断")
    return out


def _camera_block(camera: Dict[str, Any]) -> str:
    if not camera:
        return ""
    lens = camera.get("lens_mm")
    eye = camera.get("eye_mm")
    tgt = camera.get("target_mm")
    bits = []
    if lens:
        bits.append(f"{lens:.0f}mm 等效焦距")
    if eye and len(eye) == 3:
        bits.append(f"视点 [{eye[0]/1000:.1f}, {eye[1]/1000:.1f}, {eye[2]/1000:.1f}] m")
    if tgt and len(tgt) == 3:
        bits.append(f"朝向 [{tgt[0]/1000:.1f}, {tgt[1]/1000:.1f}, {tgt[2]/1000:.1f}] m")
    return "相机：" + "，".join(bits) if bits else ""


def brief(project: Any, discipline: str, *, level_id: Optional[str] = None,
          style: str = "", materials: Optional[Sequence[str]] = None,
          references: Optional[Sequence[Dict[str, str]]] = None,
          cameras: Optional[Sequence[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """Build every shot for one project, bound to its own geometry."""
    rules = DISCIPLINE_RULES.get(discipline)
    if rules is None:
        raise ValueError(f"未支持的专业 {discipline!r}；可选 {list(DISCIPLINE_RULES)}")
    facts = geometry_facts(project, level_id, discipline)
    if not facts["rooms"]:
        raise ValueError("没有已安装的空间几何，无法生成视觉任务书")
    inv = _invariants(facts, discipline)
    style_text = style or "风格未指定：按已确认概念方案的风格与材料执行"
    mat_text = ("主材：" + "；".join(materials)) if materials else "主材：按已确认方案的材料表"
    cams = {c.get("id"): c for c in (cameras or [])}

    shots: List[Shot] = []
    for sid, label, lens, intent in rules["shots"]:
        cam = cams.get({"architecture": {"A-ENTRY": "CAM-EYE", "A-FACADE": "CAM-EYE",
                                          "A-AXON": "CAM-AXON"},
                         "interior": {"I-MAIN": "CAM-EYE", "I-SECOND": "CAM-EYE",
                                      "I-MATERIAL": "CAM-EYE"},
                         "landscape": {"L-OVERALL": "CAM-AXON", "L-ENTRY": "CAM-EYE",
                                       "L-NODE": "CAM-EYE"}}[discipline][sid]) or {}
        parts = [
            f"{rules['label']}概念效果图 · {label}",
            f"{lens:.0f}mm 等效焦距" + (f"，{cam.get('label')}" if cam.get("label") else ""),
            style_text,
            f"项目类型：{project.meta.get('project_type') or project.name or project.project_id}",
            f"空间事实：{facts['rooms']} 个{facts['unit']}"
            + (f"，最大{facts['unit']} {facts['largest_room']['name']} 约 "
               f"{facts['largest_room']['area_m2']} m²" if facts["largest_room"] else "")
            + (f"，层高 {facts['storey_height_m']:.2f} m" if facts["storey_height_m"] else "")
            + (f"，外轮廓约 {facts['envelope_m'][0]:.1f} m × {facts['envelope_m'][1]:.1f} m"
               if facts["envelope_m"] else ""),
            mat_text,
            rules["light"],
            f"重点表达：{intent}",
            "必须保持：" + "；".join(inv),
        ]
        cc = _camera_block(cam)
        if cc:
            parts.append(cc)
        parts.append("写实建筑摄影质感，真实材质反射，柔和阴影，构图克制")
        shots.append(Shot(
            id=sid, label=label, kind=f"{discipline}:{sid}",
            prompt="，".join(p for p in parts if p) + "。",
            negative=NEGATIVE_BASE,
            camera=cam or {"lens_mm": lens},
            invariants=list(inv),
            references=[r.get("url", "") for r in (references or []) if r.get("url")],
            checks=["开口位置与数量是否与平面一致",
                    "空间比例与层高是否可信",
                    "家具/构件是否越界或穿墙",
                    "机位是否与 camera_jobs.json 一致"],
        ))

    return {
        "discipline": discipline,
        "label": rules["label"],
        "project": project.project_id,
        "revision": project.revision,
        "style": style_text,
        "materials": list(materials or []),
        "geometry": facts,
        "invariants": inv,
        "shots": [s.to_dict() for s in shots],
        "provider_state": "",       # 由调用方填入实际探测结果
        "note": "本任务书只定义画什么、依据什么几何；是否真正生成由平台连接状态决定",
    }


def write(pkg: Dict[str, Any], directory: Path) -> List[str]:
    """Write machine-readable and human-readable briefs side by side."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    js = directory / "visual-brief.json"
    js.write_text(json.dumps(pkg, ensure_ascii=False, indent=2), encoding="utf-8")

    g = pkg["geometry"]
    lines = [f"# 视觉任务书 · {pkg['label']}", "",
             f"- 项目：{pkg['project']}（r{pkg['revision']}）",
             f"- 风格：{pkg['style']}",
             f"- 平台状态：{pkg.get('provider_state') or '未探测'}", "",
             "## 一、几何事实（提示词里的数字全部来自这里）", "",
             "| 项目 | 值 |", "|---|---|",
             f"| 房间数 | {g['rooms']} |",
             f"| 门 / 窗 | {g['doors']} / {g['windows']} |",
             f"| 层数 / 层高 | {g['levels']} / {g['storey_height_m']:.2f} m |",
             f"| 外轮廓 | {g['envelope_m'][0] if g['envelope_m'] else '?'} m × "
             f"{g['envelope_m'][1] if g['envelope_m'] else '?'} m |",
             f"| 最大空间 | {g['largest_room']['name'] if g['largest_room'] else '?'}"
             f"（{g['largest_room']['area_m2'] if g['largest_room'] else '?'} m²） |", "",
             "## 二、不可改变项", ""]
    lines += [f"- {x}" for x in pkg["invariants"]]
    lines += ["", "## 三、镜头清单", ""]
    for shot in pkg["shots"]:
        lines += [f"### {shot['id']} {shot['label']}", "",
                  "```text", shot["prompt"], "```", "",
                  "**禁止**：" + shot["negative"], "",
                  "**生成后必查**：" + "；".join(shot["checks"]), ""]
    lines += ["---", "",
              "任务书不构成尺寸依据；图片只表达设计意图，实际尺寸以 CAD 与模型为准。"]
    md = directory / "visual-brief.md"
    md.write_text("\n".join(lines), encoding="utf-8")
    return [str(js), str(md)]


__all__ = ["DISCIPLINE_RULES", "NEGATIVE_BASE", "Shot", "geometry_facts",
           "brief", "write"]
