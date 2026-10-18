"""设计意图一致性：G2 签的那几样，到 S8 还在不在。

为什么需要这一层
----------------
G2 保存了设计意图，但 S3 之后的每一步都可能悄悄把它改掉：加了两根柱、
天花多了一排风口、水景改成旱景。这些改动单独看都"合理"，加起来方案就没了。

这一层在每个门禁前回答一个问题：**最终成果还是不是客户签的那套设计？**

三种结论，不能混
----------------
`passed`                     结构化比对通过（**不等于**美学判断通过）
`changed_requires_approval`  已可证明发生改变，必须走变更审批
`unknown_needs_review`       无法自动证明（美学、材质观感等），交人工
`not_applicable`             该特征在本阶段无可比对对象

铁律：检查失败或无法判断时**不得**返回 passed。

能用数据证明的，就不许用嘴说
----------------------------
每条特征先按类型选一条**确定性检查**（数墙、数水景、读做法表）。
这些检查只用本项目的模型与成果文件，不联网、不调用生成模型。
查不出来的（例如"视觉重心是否还在"）老实标 unknown。

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

PASSED = "passed"
CHANGED = "changed_requires_approval"
UNKNOWN = "unknown_needs_review"
NOT_APPLICABLE = "not_applicable"

STATUSES = (PASSED, CHANGED, UNKNOWN, NOT_APPLICABLE)

STATUS_LABEL = {
    PASSED: "结构化比对通过",
    CHANGED: "已发生改变，需变更审批",
    UNKNOWN: "无法自动证明，需人工设计审查",
    NOT_APPLICABLE: "本阶段无可比对对象",
}

#: 检查方法说明：让报告能讲清"这条结论是怎么来的"
METHODS = {
    "wall_count": "在目标空间范围内统计内隔墙与柱的数量（模型几何）",
    "water_present": "在空间/功能表里查找水景类用途（模型与任务书）",
    "planting_present": "在空间/功能表里查找种植类用途（模型与任务书）",
    "ceiling_fixtures": "读 S4 顶面做法表，统计外露风口/检修口与主灯（成果文件）",
    "lighting_intent": "读 S4 灯光方案，检查是否出现主灯类做法（成果文件）",
    "corridor_present": "检查是否仍存在走廊类交通空间（模型）",
    "manual_only": "该特征属观感/比例判断，无确定性数据可比",
}

WATER_RECIPES = ("water", "pool", "水景", "水池", "泳池", "跌水")
PLANT_RECIPES = ("planting", "绿化", "种植", "植物", "green")
CORRIDOR_USES = ("circulation", "corridor", "走廊")


@dataclass
class Check:
    feature_id: str
    name: str
    kind: str
    status: str = UNKNOWN
    method: str = ""
    evidence: str = ""
    needs: str = ""
    measurable: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "feature_id": self.feature_id,
            "name": self.name,
            "kind": self.kind,
            "status": self.status,
            "status_label": STATUS_LABEL.get(self.status, self.status),
            "method": self.method,
            "method_note": METHODS.get(self.method, ""),
            "evidence": self.evidence,
            "needs": self.needs,
            "measurable": bool(self.measurable),
        }


@dataclass
class ConformanceReport:
    stage: str = ""
    status: str = NOT_APPLICABLE
    checks: List[Check] = field(default_factory=list)
    revision: int = 1
    design_intent_id: str = ""
    intent_digest: str = ""
    scope_disciplines: List[str] = field(default_factory=list)
    note: str = ""

    @property
    def changed(self) -> List[Check]:
        return [c for c in self.checks if c.status == CHANGED]

    @property
    def unknown(self) -> List[Check]:
        return [c for c in self.checks if c.status == UNKNOWN]

    @property
    def passed(self) -> List[Check]:
        return [c for c in self.checks if c.status == PASSED]

    @property
    def blocks_approval(self) -> bool:
        """已证明改变 → 阻断门禁。无法证明 → 不阻断，但必须进人工审查。"""
        return bool(self.changed)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stage": self.stage,
            "status": self.status,
            "status_label": STATUS_LABEL.get(self.status, self.status),
            "revision": self.revision,
            "design_intent_id": self.design_intent_id,
            "intent_digest": self.intent_digest,
            "scope_disciplines": list(self.scope_disciplines),
            "checks": [c.to_dict() for c in self.checks],
            "counts": {
                PASSED: len(self.passed), CHANGED: len(self.changed),
                UNKNOWN: len(self.unknown),
                NOT_APPLICABLE: sum(1 for c in self.checks
                                    if c.status == NOT_APPLICABLE),
            },
            "blocks_approval": self.blocks_approval,
            "note": self.note or (
                "passed 只表示结构化比对通过，不代表美学判断通过；"
                "unknown 必须进人工设计审查，不得当作通过。"),
        }

    def markdown(self) -> str:
        lines = [f"# 设计意图一致性 — {self.stage or '当前'}", "",
                 f"- 结论：**{STATUS_LABEL.get(self.status, self.status)}**",
                 f"- 设计意图：`{self.design_intent_id}`（模型 r{self.revision}）", "",
                 "| 特征 | 类型 | 结论 | 检查方法 | 证据 |",
                 "|---|---|---|---|---|"]
        for c in self.checks:
            lines.append(f"| {c.name} | {c.kind} | {STATUS_LABEL.get(c.status, c.status)} "
                         f"| {METHODS.get(c.method, c.method)} | {c.evidence[:40]} |")
        if self.changed:
            lines += ["", "## 需要变更审批", ""]
            lines += [f"- **{c.name}**：{c.evidence}" for c in self.changed]
            lines += ["", "> 这些不是技术细节，是客户签过的设计。"
                          "要么按原意图找技术路径，要么走正式变更审批。"]
        if self.unknown:
            lines += ["", "## 需人工设计审查（不阻断，但不得算通过）", ""]
            lines += [f"- {c.name}：{c.needs or METHODS.get(c.method, '')}"
                      for c in self.unknown]
        lines.append("")
        return "\n".join(lines)


# --------------------------------------------------------------------------
def _matches(text: str, words: Sequence[str]) -> bool:
    return any(w and w in text for w in words)


def _space_label(s: Any) -> str:
    return str(getattr(s, "name", "") or (getattr(s, "properties", {}) or {}).get("recipe")
               or getattr(s, "use", "") or "")


def _recipes(project: Any) -> Tuple[str, List[str]]:
    """把功能表与空间用途合成一段文本 + 用途清单，供水景/种植判断。"""
    bits: List[str] = []
    uses: List[str] = []
    for sp in getattr(project, "spaces", []) or []:
        if getattr(sp, "use", "") == "envelope":
            continue
        props = getattr(sp, "properties", {}) or {}
        bits.append(str(sp.name or ""))
        bits.append(str(props.get("recipe") or ""))
        uses.append(str(props.get("recipe") or sp.use or ""))
    for p in getattr(project, "program", []) or []:
        bits.append(str(p.get("name") or ""))
        bits.append(str(p.get("recipe") or ""))
        uses.append(str(p.get("recipe") or ""))
    return " ".join(bits), uses


def _inside(box: Tuple[float, float, float, float],
            x: float, y: float) -> bool:
    x0, y0, x1, y1 = box
    return min(x0, x1) <= x <= max(x0, x1) and min(y0, y1) <= y <= max(y0, y1)


def _space_box(s: Any) -> Optional[Tuple[float, float, float, float]]:
    pts = getattr(s, "boundary_mm2d", None) or []
    if len(pts) < 3:
        return None
    xs = [float(p[0]) for p in pts]
    ys = [float(p[1]) for p in pts]
    return (min(xs), min(ys), max(xs), max(ys))


def _point_in_poly(x: float, y: float, poly: Sequence[Sequence[float]]) -> bool:
    """射线法。只判"在内部"，边界上的点按外部处理。"""
    n = len(poly)
    inside = False
    for i in range(n):
        x0, y0 = float(poly[i][0]), float(poly[i][1])
        x1, y1 = float(poly[(i + 1) % n][0]), float(poly[(i + 1) % n][1])
        if (y0 > y) != (y1 > y):
            t = (y - y0) / ((y1 - y0) or 1e-9)
            if x < x0 + t * (x1 - x0):
                inside = not inside
    return inside


def _dist_to_segment(px: float, py: float, ax: float, ay: float,
                     bx: float, by: float) -> float:
    dx, dy = bx - ax, by - ay
    if dx == 0 and dy == 0:
        return ((px - ax) ** 2 + (py - ay) ** 2) ** 0.5
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    cx, cy = ax + t * dx, ay + t * dy
    return ((px - cx) ** 2 + (py - cy) ** 2) ** 0.5


def _on_boundary(x: float, y: float, poly: Sequence[Sequence[float]],
                 tol: float = 80.0) -> bool:
    """点是否贴着空间轮廓（80mm 容差）。贴边的是分隔墙，不是插入的柱。"""
    n = len(poly)
    for i in range(n):
        a, b = poly[i], poly[(i + 1) % n]
        if _dist_to_segment(x, y, float(a[0]), float(a[1]),
                            float(b[0]), float(b[1])) <= tol:
            return True
    return False


def _walls_inside(project: Any, space: Any) -> List[str]:
    """统计**真正插在空间内部**的墙与柱。

    不能用包围盒判定：相邻空间共享一道墙，包围盒一定重叠，会把走廊边墙
    当成"私自加墙"。这里要求两端都在多边形内部、且都不贴边。
    """
    poly = getattr(space, "boundary_mm2d", None) or []
    if len(poly) < 3:
        return []
    found: List[str] = []
    for e in getattr(project, "elements", []) or []:
        if getattr(e, "type", "") not in ("wall", "column"):
            continue
        g = getattr(e, "geometry", {}) or {}
        if str(g.get("kind") or "") in ("external", "exterior", "envelope"):
            continue
        a, b = g.get("start"), g.get("end")
        if not (isinstance(a, (list, tuple)) and isinstance(b, (list, tuple))):
            continue
        if len(a) < 2 or len(b) < 2:
            continue
        ax, ay = float(a[0]), float(a[1])
        bx, by = float(b[0]), float(b[1])
        if not (_point_in_poly(ax, ay, poly) and _point_in_poly(bx, by, poly)):
            continue
        if _on_boundary(ax, ay, poly) or _on_boundary(bx, by, poly):
            continue
        found.append(str(getattr(e, "id", "")))
    return found


def _read_json(root: Optional[Path], pattern: str) -> Optional[Dict[str, Any]]:
    if root is None or not Path(root).exists():
        return None
    hits = sorted(Path(root).rglob(pattern))
    if not hits:
        return None
    try:
        return json.loads(hits[-1].read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _primary_space(project: Any, lead: str) -> Any:
    spaces = [s for s in (getattr(project, "spaces", []) or [])
              if getattr(s, "use", "") != "envelope"]
    if not spaces:
        return None
    return max(spaces, key=lambda s: getattr(s, "area_m2", 0.0))


# --------------------------------------------------------------------------
def check(project: Any, *, stage: str = "S3", out_root: Any = None,
          intent: Optional[Dict[str, Any]] = None) -> ConformanceReport:
    """按已确认的设计意图逐条验证当前成果。

    只读：不修改项目、不写盘、不调用任何外部模型。
    """
    from . import intent as _intent

    data = intent if intent is not None else (_intent.load(project) or {})
    rev = int(getattr(project, "revision", 1) or 1)
    rep = ConformanceReport(stage=stage, revision=rev,
                            design_intent_id=str(data.get("design_intent_id") or ""))
    if not data:
        rep.status = NOT_APPLICABLE
        rep.note = "尚无 G2 确认的设计意图：无法做一致性验证（不是通过）。"
        return rep

    try:
        from . import disciplines as _disc

        rep.scope_disciplines = list(_disc.load(project).active()
                                     if _disc.load(project) else [])
    except Exception:                                   # noqa: BLE001
        rep.scope_disciplines = []

    rep.intent_digest = _digest(data)
    root = Path(out_root) if out_root else None
    text_all, uses = _recipes(project)
    words = text_all + " " + " ".join(uses)

    for f in data.get("signature_features") or []:
        kind = str(f.get("kind") or "")
        stmt = str(f.get("statement") or "")
        c = Check(feature_id=str(f.get("id") or ""), name=str(f.get("name") or ""),
                  kind=kind)

        if kind == "water":
            c.method = "water_present"
            present = _matches(words, WATER_RECIPES) or _matches(words, ("水景", "水池"))
            if present:
                c.status, c.measurable = PASSED, True
                c.evidence = "功能表/空间中仍存在水景类用途"
            else:
                c.status, c.measurable = CHANGED, True
                c.evidence = ("设计意图要求水景，但当前功能表与空间里没有水景类用途："
                              "水景被取消或被改成旱景")
                c.needs = "按原意图恢复水景，或走变更审批"

        elif kind == "planting":
            c.method = "planting_present"
            present = _matches(words, PLANT_RECIPES)
            c.status, c.measurable = (PASSED if present else CHANGED), True
            c.evidence = ("仍存在种植类用途" if present
                          else "设计意图要求种植/绿化，但当前范围内没有种植类用途")
            c.needs = "" if present else "恢复种植或走变更审批"

        elif kind == "spatial":
            c.method = "wall_count"
            space = _primary_space(project, "")
            if space is None:
                c.status = NOT_APPLICABLE
                c.evidence = "当前尚无空间几何可比对"
            else:
                box = _space_box(space)
                walls = _walls_inside(project, space)
                wants_open = _matches(stmt, ("无柱", "大跨", "通透", "连续", "开放"))
                if not walls:
                    c.status, c.measurable = PASSED, True
                    c.evidence = f"「{_space_label(space)}」范围内无墙柱插入"
                elif wants_open:
                    c.status, c.measurable = CHANGED, True
                    c.evidence = (f"「{_space_label(space)}」范围内出现 {len(walls)} 处"
                                  f"墙/柱（{', '.join(walls[:4])}），"
                                  "与「无柱/通透」的意图冲突")
                    c.needs = "按原意图调整结构或走变更审批"
                else:
                    c.status, c.measurable = PASSED, True
                    c.evidence = (f"「{_space_label(space)}」范围内有 {len(walls)} 处隔墙，"
                                  "意图未要求无柱，属正常分隔")
                del box

        elif kind in ("surface", "light"):
            c.method = ("ceiling_fixtures" if kind == "surface" else "lighting_intent")
            mat = _read_json(root, "material-lighting.json")
            if mat is None:
                c.status = UNKNOWN
                c.evidence = "尚未生成顶面/灯光成果表，无法结构化比对"
                c.needs = "待 S4 成果生成后复核，或由主创看图判断"
            else:
                ceiling = (mat.get("surfaces") or {}).get("ceiling") or []
                light = mat.get("lighting") or []
                blob = " ".join(str(r.get("method") or "") + str(r.get("light") or "")
                                for r in ceiling if isinstance(r, dict))
                blob += " " + " ".join(str(r.get("fixture") or "")
                                       for r in light if isinstance(r, dict))
                exposed = blob.count("外露") + blob.count("明装风口")
                main_light = "主灯" in blob or "吊灯" in blob or "吸顶灯" in blob
                wants_clean = _matches(stmt, ("无主灯", "完整", "平顶", "不做局部吊顶", "连续"))
                if wants_clean and (exposed > 0 or main_light):
                    c.status, c.measurable = CHANGED, True
                    detail = []
                    if exposed:
                        detail.append(f"{exposed} 处外露风口/明装")
                    if main_light:
                        detail.append("出现主灯类做法")
                    c.evidence = "与「" + stmt[:20] + "」冲突：" + "、".join(detail)
                    c.needs = "改用隐蔽/线性风口、检修口整合，或走变更审批"
                else:
                    c.status, c.measurable = PASSED, True
                    c.evidence = "顶面与灯光做法未违背该特征"

        elif kind == "sequence":
            c.method = "corridor_present"
            has = any(str(u) in CORRIDOR_USES for u in uses) or "走廊" in text_all
            if not uses:
                c.status = NOT_APPLICABLE
                c.evidence = "当前无空间用途可比对"
            else:
                c.status, c.measurable = (PASSED if has else CHANGED), True
                c.evidence = ("仍存在交通/走廊空间" if has
                              else "意图依赖的序列与走廊在空间中已不存在")

        else:
            c.method = "manual_only"
            c.status = UNKNOWN
            c.measurable = False
            c.evidence = "该特征属观感/比例判断，无确定性数据可比"
            c.needs = "由主创或客户看图确认"

        rep.checks.append(c)

    if not rep.checks:
        rep.status = NOT_APPLICABLE
        rep.note = "设计意图里没有可验证的特征。"
        return rep

    if rep.changed:
        rep.status = CHANGED
    elif rep.unknown:
        rep.status = UNKNOWN
    elif rep.passed:
        rep.status = PASSED
    else:
        rep.status = NOT_APPLICABLE
    return rep


def _digest(data: Dict[str, Any]) -> str:
    import hashlib

    seed = "|".join([str(data.get("design_intent_id") or ""),
                     str(data.get("revision") or ""),
                     *[str(f.get("statement") or "")
                       for f in (data.get("signature_features") or [])]])
    return hashlib.sha1(seed.encode("utf-8")).hexdigest()[:12]


def summary_lines(rep: ConformanceReport) -> List[str]:
    lines = [f"- 设计意图一致性：**{STATUS_LABEL.get(rep.status, rep.status)}**"
             f"（{rep.stage or '当前'}，`{rep.design_intent_id}`）"]
    for c in rep.changed[:3]:
        lines.append(f"  · 已改变：{c.name}——{c.evidence[:56]}")
    if rep.unknown:
        lines.append(f"  · 待人工审查 {len(rep.unknown)} 项："
                     + "、".join(c.name for c in rep.unknown[:3]))
    return lines


__all__ = ["PASSED", "CHANGED", "UNKNOWN", "NOT_APPLICABLE", "STATUSES",
           "STATUS_LABEL", "METHODS", "Check", "ConformanceReport",
           "check", "summary_lines"]
