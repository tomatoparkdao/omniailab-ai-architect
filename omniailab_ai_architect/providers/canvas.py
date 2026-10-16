"""OmniAiLab 画布（canvas）工作流 —— 平面确认后的概念效果图。

为什么单独一个模块
------------------
平面方案通过门禁 G3 之后，业主最先需要的不是施工图，而是「这个空间长什么样」。
这一批图必须是**概念效果图**：由 AI 在平台画布上生成，用来对齐空间感受，
不承担任何尺寸责任。它与 S5 的正式表现有一个明确分工：

* 本模块（S3 门禁后置动作）—— 概念效果图。依据**刚确认的平面**，机位少而精，
  用平台画布逐张生成，供业主建立空间想象；此时方案还在可改状态。
* `adapters/render.py`（S5）—— 正式多视角表现。依据**锁定后的模型**，
  材质、光线、相机全部取自同一份统一空间模型，追求跨视角一致。

三条硬规则
----------
1. **不猜端点**。模型身份与适用取向来自声明文件（`omniailab.models.json`），
   端点、参数与鉴权只能来自平台下发的 API 契约。契约不在，就不发请求。
2. **不伪造图**。平台未连接时，产出的是完整的**可执行任务包**（提示词、参考图、
   机位、模型建议、回填位置），状态逐条标注 `awaiting_platform`，绝不写占位图片。
3. **不发尺寸结论**。每张图的提示词、说明与登记信息都带非权威声明。
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from ..model import Project, polygon_centroid
from ..paths import ROOT
from .base import NotConfigured, ProviderError, ProviderJob

# --------------------------------------------------------------------------
MODEL_CATALOG_FILE = "omniailab.models.json"

# The canvas is one visual workflow; a provider may expose it under any of these
# scopes. We try them in this order and record which one was actually used.
CANVAS_SCOPES: Tuple[str, ...] = (
    "reference_image_generation",
    "multi_view_visualization",
    "image_generation",
    "visual_workflow_execution",
)

# What a view is asking for, in the vocabulary of the declaration file.
NEED_SPATIAL = "spatial_atmosphere"
NEED_REFERENCE = "reference_guided"
NEED_MATERIAL = "material_detail"
NEED_MULTIVIEW = "multi_view"

# Human-facing names, so a client-facing brief never leaks internal keys.
NEED_LABELS: Dict[str, str] = {
    NEED_SPATIAL: "整体空间氛围",
    NEED_REFERENCE: "与已确认平面对齐",
    NEED_MATERIAL: "材质细节可读",
    NEED_MULTIVIEW: "多机位一致",
    "interior_scene": "室内空间",
    "iteration": "改图迭代",
}

ENTITY = "画布概念效果图"

DISCLAIMER = (
    "本批图为 AI 生成的概念效果图，用于空间感受与方向对齐，"
    "不构成尺寸、比例或材料样板依据；施工与报价必须依据经过校核的模型与图纸。"
)

# Room use -> (view label, lens mm, need, priority). Order matters: the first
# views are the ones a client actually looks at.
VIEW_RECIPES: List[Tuple[str, str, int, str, int]] = [
    ("living", "客厅", 35, NEED_REFERENCE, 10),
    ("dining", "餐厅", 35, NEED_REFERENCE, 20),
    ("kitchen", "厨房", 35, NEED_MATERIAL, 30),
    ("bedroom", "卧室", 35, NEED_REFERENCE, 40),
    ("study", "书房", 35, NEED_REFERENCE, 50),
    ("bathroom", "卫生间", 35, NEED_MATERIAL, 60),
    ("circulation", "玄关与动线", 28, NEED_SPATIAL, 70),
    ("storage", "储藏与柜体", 35, NEED_MATERIAL, 80),
    ("service", "家务区", 35, NEED_MATERIAL, 90),
]

LIGHTING = {
    "cs": 5200,
    "key": "自然侧光 + 隐藏灯带补光",
    "notes": "保留窗边亮度层次，不做无阴影的均匀打光",
}

NEGATIVE = (
    "变形几何, 错误的透视, 与平面不符的房间数量, 多出的门窗, 重复家具, 文字, 水印, "
    "logo, 杂乱堆放, 塑料感材质, 过曝死白, 暗部死黑, 鱼眼畸变, 广角变形"
)


# --------------------------------------------------------------------------
# declaration file
# --------------------------------------------------------------------------
DEFAULT_CATALOG: Dict[str, Any] = {
    "schema": "omniailab.models/1",
    "platform": "OmniAiLab",
    "declared_by": "platform-canvas",
    "provenance": "内置兜底声明；建议以 providers/omniailab.models.json 为准",
    "verified_against_contract": False,
    "canvas": {"workflow_id": "canvas", "display_name": "画布",
               "scope": "visual_workflow_execution"},
    "models": [
        {"id": "OmniP", "display_name": "OmniP", "priority": 1,
         "scopes": ["image_generation", "reference_image_generation",
                    "multi_view_visualization", "visual_workflow_execution"],
         "strengths": ["空间与体量关系稳定", "多视角一致"],
         "best_for": [NEED_SPATIAL, NEED_MULTIVIEW, "interior_scene"],
         "note": "整体氛围与多机位一致出图。"},
        {"id": "image2.5", "display_name": "Image 2.5", "priority": 2,
         "scopes": ["image_generation", "image_editing",
                    "reference_image_generation", "multi_view_visualization",
                    "visual_workflow_execution"],
         "strengths": ["参考图保真", "材质细节还原", "改图迭代"],
         "best_for": [NEED_REFERENCE, NEED_MATERIAL, "iteration"],
         "note": "严格跟随已确认平面与材料方案。"},
    ],
    "selection_rules": [
        {"need": NEED_SPATIAL, "model": "OmniP", "why": "空间关系优先"},
        {"need": NEED_MULTIVIEW, "model": "OmniP", "why": "跨视角一致性优先"},
        {"need": NEED_REFERENCE, "model": "image2.5", "why": "与已确认平面对齐优先"},
        {"need": NEED_MATERIAL, "model": "image2.5", "why": "材质细节可读性优先"},
    ],
}


def catalog_path(project_dir: str | Path | None = None) -> Optional[Path]:
    for base in filter(None, [Path(project_dir) if project_dir else None,
                              ROOT / "providers", ROOT]):
        p = Path(base) / MODEL_CATALOG_FILE
        if p.exists():
            return p
    p = Path(__file__).with_name(MODEL_CATALOG_FILE)
    return p if p.exists() else None


def load_catalog(project_dir: str | Path | None = None) -> Dict[str, Any]:
    """Read the declaration file. A broken file is reported, never silently ignored."""
    p = catalog_path(project_dir)
    if not p:
        cat = json.loads(json.dumps(DEFAULT_CATALOG))
        cat["_source"] = ""
        cat["_issues"] = ["未找到模型声明文件，使用内置兜底声明"]
        return cat
    try:
        cat = json.loads(p.read_text(encoding="utf-8"))
    except Exception as exc:
        cat = json.loads(json.dumps(DEFAULT_CATALOG))
        cat["_source"] = str(p)
        cat["_issues"] = [f"声明文件解析失败：{exc}；已回退内置声明"]
        return cat
    cat["_source"] = str(p)
    issues: List[str] = []
    if not cat.get("models"):
        issues.append("声明文件没有 models")
    for m in cat.get("models") or []:
        if not m.get("id"):
            issues.append("存在缺少 id 的模型声明")
        if m.get("id") and not m.get("best_for"):
            issues.append(f"{m['id']} 未声明 best_for，无法参与自动选择")
    cat["_issues"] = issues
    return cat


def _rule_map(cat: Dict[str, Any]) -> Dict[str, Dict[str, str]]:
    return {str(r.get("need")): r for r in (cat.get("selection_rules") or [])
            if r.get("need")}


def select_model(cat: Dict[str, Any], need: str = NEED_REFERENCE,
                 override: str = "",
                 advertised: Optional[Sequence[str]] = None) -> Dict[str, Any]:
    """Pick a model for one view, stating why.

    `advertised` is the platform contract's model list. When it is known, the
    pick must come from it — a declaration that the platform does not advertise
    is reported as a mismatch instead of being used.
    """
    models = [m for m in (cat.get("models") or []) if m.get("id")]
    by_id = {str(m["id"]): m for m in models}
    note = ""
    mismatches: List[str] = []

    def _finish(m: Optional[Dict[str, Any]], why: str, picked_by: str) -> Dict[str, Any]:
        return {
            "model": str(m["id"]) if m else "",
            "display_name": str(m.get("display_name") or m.get("id")) if m else "",
            "need": need,
            "why": why,
            "picked_by": picked_by,
            "declared_source": str(cat.get("_source") or "builtin"),
            "verified_against_contract": bool(cat.get("verified_against_contract")),
            "mismatches": mismatches,
            "note": note,
        }

    if override:
        m = by_id.get(override)
        if m is None:
            # An explicitly requested model that nobody declared is accepted but
            # flagged: the caller may know something the declaration file does not.
            mismatches.append(f"{override} 未在模型声明中登记")
            return _finish({"id": override}, "调用方显式指定", "explicit")
        if advertised is not None and override not in advertised:
            mismatches.append(
                f"{override} 不在平台契约的 models 列表中（契约：{list(advertised)}）"
            )
        return _finish(m, "调用方显式指定", "explicit")

    rule = _rule_map(cat).get(need)
    wanted = str(rule.get("model") or "") if rule else ""
    why = str(rule.get("why") or "") if rule else ""

    if wanted and wanted in by_id:
        if advertised is not None and wanted not in advertised:
            mismatches.append(
                f"取向 {need} 推荐 {wanted}，但平台契约只声明 {list(advertised)}"
            )
            alt = next((mid for mid in advertised if mid in by_id), None)
            if alt:
                return _finish(by_id[alt], f"按契约改用 {alt}", "contract")
            return _finish(None, "契约中无可用的已登记模型", "contract")
        return _finish(by_id[wanted], why or f"取向 {need}", "declaration")

    # No rule matched: fall back to declaration order, still filtered by contract.
    ranked = sorted(models, key=lambda m: int(m.get("priority") or 99))
    if advertised is not None:
        ranked = [m for m in ranked if str(m["id"]) in advertised]
    if ranked:
        note = f"取向 {need} 未在声明中给出规则，按声明顺序选 {ranked[0]['id']}"
        return _finish(ranked[0], note, "declaration")
    return _finish(None, "没有可用模型", "none")


def recommended_models(cat: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    cat = cat or load_catalog()
    return sorted((m for m in (cat.get("models") or []) if m.get("id")),
                  key=lambda m: int(m.get("priority") or 99))


# --------------------------------------------------------------------------
# view + plan model
# --------------------------------------------------------------------------
@dataclass
class ConceptView:
    id: str
    label: str
    space_id: str
    space_name: str
    area_m2: float
    need: str
    camera: Dict[str, Any]
    lighting: Dict[str, Any]
    finishes: Dict[str, str]
    prompt: str
    negative_prompt: str
    model: str
    model_reason: str
    reference: str = ""
    status: str = "awaiting_platform"     # awaiting_platform | generated | failed
    output: str = ""
    detail: str = ""
    prompt_sha: str = ""

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "id": self.id, "label": self.label, "space_id": self.space_id,
            "space_name": self.space_name, "area_m2": round(self.area_m2, 2),
            "need": self.need, "camera": dict(self.camera),
            "lighting": dict(self.lighting), "finishes": dict(self.finishes),
            "prompt": self.prompt, "negative_prompt": self.negative_prompt,
            "model": self.model, "model_reason": self.model_reason,
            "reference": self.reference, "status": self.status,
            "output": self.output, "detail": self.detail,
            "prompt_sha": self.prompt_sha,
            "authoritative": False,
        }
        return d


@dataclass
class ConceptRenderResult:
    project_id: str
    revision: int
    scheme: str
    level_id: str
    stage: str = "S3"
    capability: str = "concept-visualization"
    provider_state: str = "not_configured"
    provider_used: str = ""
    scope_used: str = ""
    status: str = "degraded"          # ok | degraded | partial | blocked
    views: List[ConceptView] = field(default_factory=list)
    artifacts: List[str] = field(default_factory=list)
    files: Dict[str, str] = field(default_factory=dict)
    notes: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    cost_estimate: Optional[float] = None
    currency: str = ""
    seconds: float = 0.0

    @property
    def generated(self) -> List[ConceptView]:
        return [v for v in self.views if v.status == "generated"]

    @property
    def pending(self) -> List[ConceptView]:
        return [v for v in self.views if v.status == "awaiting_platform"]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_id": self.project_id, "revision": self.revision,
            "scheme": self.scheme, "level_id": self.level_id, "stage": self.stage,
            "capability": self.capability, "status": self.status,
            "provider_state": self.provider_state, "provider_used": self.provider_used,
            "scope_used": self.scope_used,
            "views": [v.to_dict() for v in self.views],
            "generated": len(self.generated), "awaiting_platform": len(self.pending),
            "artifacts": list(self.artifacts), "files": dict(self.files),
            "notes": list(self.notes), "warnings": list(self.warnings),
            "cost_estimate": self.cost_estimate, "currency": self.currency,
            "seconds": round(self.seconds, 2),
            "entity": ENTITY,
            "authoritative": False,
            "disclaimer": DISCLAIMER,
        }


# --------------------------------------------------------------------------
def pick_views(project: Project, level_id: str, limit: int = 5,
               include: Sequence[str] = ()) -> List[Tuple[str, str, int, str, Any]]:
    """Choose which rooms get a concept rendering, from the confirmed plan.

    A room is eligible when it exists in the model with a real area. The pick is
    deterministic: recipe order, then area — never a random or invented room.
    """
    spaces = [s for s in project.spaces_on(level_id) if s.use != "envelope"]
    if include:
        wanted = {str(x) for x in include}
        hit = [s for s in spaces if s.id in wanted or s.use in wanted
               or (s.name or "") in wanted]
        if hit:
            spaces = hit
    picked: List[Tuple[str, str, int, str, Any]] = []
    for use, label, lens, need, _prio in VIEW_RECIPES:
        cand = [s for s in spaces if s.use == use and s.area_m2 > 1.0]
        for s in sorted(cand, key=lambda x: -x.area_m2):
            picked.append((s.id, label if s.area_m2 == max(c.area_m2 for c in cand) else s.name or label,
                           lens, need, s))
    # overview first: it is the one image that carries the whole scheme
    picked = picked[:limit]
    return picked


def _camera_for(space: Any, lens: int, level_height_mm: float) -> Dict[str, Any]:
    pts = space.boundary_mm2d or []
    if not pts:
        return {}
    x0 = min(p[0] for p in pts)
    x1 = max(p[0] for p in pts)
    y0 = min(p[1] for p in pts)
    y1 = max(p[1] for p in pts)
    cx, cy = polygon_centroid(pts)
    inset = 450.0
    # stand in the corner nearest the larger of the two openings, keep it simple
    # and deterministic: bottom-left corner of the room's bbox.
    pos = [round(x0 + inset, 1), round(y0 + inset, 1),
           round(min(1550.0, max(1200.0, level_height_mm - 1150.0)), 1)]
    return {
        "position_mm": pos,
        "target_mm": [round(cx, 1), round(cy, 1), 1200.0],
        "lens_mm": lens,
        "sensor_mm": 36,
        "aspect": "16:10",
        "room_extent_m": [round((x1 - x0) / 1000.0, 2), round((y1 - y0) / 1000.0, 2)],
        "eye_height_mm": pos[2],
    }


def overview_camera(project: Project, level_id: str, lens: int = 24) -> Dict[str, Any]:
    """Whole-level framing: the one picture that carries the scheme as a whole."""
    spaces = [s for s in project.spaces_on(level_id) if s.use != "envelope"]
    pts = [p for s in spaces for p in (s.boundary_mm2d or [])]
    if not pts:
        return {}
    x0, x1 = min(p[0] for p in pts), max(p[0] for p in pts)
    y0, y1 = min(p[1] for p in pts), max(p[1] for p in pts)
    dist = max(x1 - x0, y1 - y0)
    return {
        "position_mm": [round((x0 + x1) / 2.0, 1),
                        round(y0 - dist * 0.9, 1),
                        round(dist * 0.75, 1)],
        "target_mm": [round((x0 + x1) / 2.0, 1), round((y0 + y1) / 2.0, 1), 1200.0],
        "lens_mm": lens,
        "sensor_mm": 36,
        "aspect": "16:10",
        "room_extent_m": [round((x1 - x0) / 1000.0, 2), round((y1 - y0) / 1000.0, 2)],
        "eye_height_mm": 0,
        "framing": "axon",
    }


def _finishes_for(project: Project, spaces: Sequence[Any]) -> Dict[str, str]:
    from ..adapters.render import DEFAULT_FINISHES

    out = dict(DEFAULT_FINISHES)
    mats = (project.constraints or {}).get("materials") or {}
    if isinstance(mats, dict):
        for k, v in mats.items():
            if isinstance(v, str) and v.strip():
                out[str(k)] = v.strip()
    return out


def _prompt_for(project: Project, view_label: str, space: Any, camera: Dict[str, Any],
                finishes: Dict[str, str], style: str, revision: int,
                scheme: str) -> str:
    """Compose the view prompt from the canonical model — nothing invented.

    The numbers in the prompt come from the confirmed plan (room area, extent,
    lens, eye height) so a viewer can tell which plan produced which picture.
    """
    extent = camera.get("room_extent_m") or ["?", "?"]
    parts = [
        f"室内空间概念效果图，{view_label}视角",
        f"{camera.get('lens_mm', 35)}mm 镜头，视点高 {camera.get('eye_height_mm', 1500):.0f}mm",
        style or "现代意式极简，克制的暖灰基调",
        f"空间：{space.name or space.use}，使用面积约 {space.area_m2:.1f}㎡，"
        f"开间进深约 {extent[0]}m × {extent[1]}m（取自已确认平面）",
        f"地面 {finishes.get('floor', '')}；墙面 {finishes.get('wall', '')}；"
        f"天花 {finishes.get('ceiling', '')}",
        f"光线：{LIGHTING['key']}，色温约 {LIGHTING['cs']}K，{LIGHTING['notes']}",
        "写实摄影感，真实材质反射与柔和阴影，构图克制，画面内不出现人物与文字",
    ]
    tail = (f"依据：方案{scheme} · 模型修订 r{revision} · 项目 "
            f"{project.name or project.project_id}（{project.project_id}）")
    return "；".join(p for p in parts if p) + f"。{tail}"


def _sha(text: str) -> str:
    import hashlib

    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _overview_prompt(project: Project, total_area: float, extent: Sequence[float],
                     finishes: Dict[str, str], style: str, revision: int,
                     scheme: str, rooms: int) -> str:
    parts = [
        "整体空间概念效果图，轴测剖切视角，读得到全部房间关系",
        "24mm 等效镜头，视点抬高俯视，去掉屋顶",
        style or "现代意式极简，克制的暖灰基调",
        f"空间：套内使用面积约 {total_area:.1f}㎡，共 {rooms} 个房间，"
        f"外轮廓约 {extent[0]}m × {extent[1]}m（取自已确认平面）",
        f"地面 {finishes.get('floor', '')}；墙面 {finishes.get('wall', '')}",
        f"光线：{LIGHTING['key']}，色温约 {LIGHTING['cs']}K",
        "建筑可视化风格，材质真实，构图克制，画面内不出现人物、标注与文字",
    ]
    tail = (f"依据：方案{scheme} · 模型修订 r{revision} · 项目 "
            f"{project.name or project.project_id}（{project.project_id}）")
    return "；".join(p for p in parts if p) + f"。{tail}"


# --------------------------------------------------------------------------
def plan(project: Project, level_id: Optional[str] = None, scheme: str = "A",
         limit: int = 5, include: Sequence[str] = (), model: str = "",
         project_dir: str | Path | None = None,
         advertised: Optional[Sequence[str]] = None) -> Tuple[List[ConceptView], Dict[str, Any]]:
    """Build the per-view plan. Pure: no files, no network."""
    lid = level_id or (project.levels[0].id if project.levels else "L1")
    height = float(next((l.height_mm for l in project.levels if l.id == lid), 2800.0))
    style = str((project.constraints or {}).get("style") or "")
    cat = load_catalog(project_dir)
    spaces = [s for s in project.spaces_on(lid) if s.use != "envelope"]
    fin = _finishes_for(project, spaces)

    views: List[ConceptView] = []
    picked = pick_views(project, lid, limit=max(1, limit - 1 if limit > 1 else 1),
                        include=include)

    # View 01 is the whole scheme — the picture a client looks at first, and the
    # one that most needs the space to read correctly rather than a detail to be
    # sharp. That is what the declaration file recommends OmniP for.
    if spaces and limit > 1 and not include:
        cam = overview_camera(project, lid)
        total = sum(s.area_m2 for s in spaces)
        extent = cam.get("room_extent_m") or [0.0, 0.0]
        prompt = _overview_prompt(project, total, extent, fin, style,
                                  project.revision, scheme, len(spaces))
        sel = select_model(cat, need=NEED_SPATIAL, override=model, advertised=advertised)
        views.append(ConceptView(
            id="01_overview", label="整体空间印象", space_id="project:overview",
            space_name="全户型", area_m2=total, need=NEED_SPATIAL, camera=cam,
            lighting=dict(LIGHTING), finishes=fin, prompt=prompt,
            negative_prompt=NEGATIVE, model=sel["model"],
            model_reason=sel["why"] or sel["note"], prompt_sha=_sha(prompt),
        ))

    offset = len(views)
    for i, (sid, label, lens, need, space) in enumerate(picked, start=offset + 1):
        cam = _camera_for(space, lens, height)
        prompt = _prompt_for(project, label, space, cam, fin, style,
                             project.revision, scheme)
        sel = select_model(cat, need=need, override=model, advertised=advertised)
        views.append(ConceptView(
            id=f"{i:02d}_{space.use}",
            label=label, space_id=space.id, space_name=(space.name or space.use),
            area_m2=space.area_m2, need=need, camera=cam,
            lighting=dict(LIGHTING), finishes=fin,
            prompt=prompt, negative_prompt=NEGATIVE,
            model=sel["model"], model_reason=sel["why"] or sel["note"],
            prompt_sha=_sha(prompt),
        ))
    if not views and include:
        # Explicitly asked for specific rooms that do not exist: say so by
        # returning nothing rather than quietly rendering something else.
        return [], cat
    return views, cat


# --------------------------------------------------------------------------
def render(project: Project, out_dir: str | Path, level_id: Optional[str] = None,
           scheme: str = "A", limit: int = 5, include: Sequence[str] = (),
           model: str = "", project_dir: str | Path | None = None,
           submit: bool = False, authorized: bool = False,
           with_reference: bool = True, deck: bool = True) -> ConceptRenderResult:
    """Produce the concept-rendering package, and generate for real when possible.

    Every path through this function writes files that a human can act on. When
    the platform is not connected it writes the task package and says so per
    view; it never writes a placeholder image.
    """
    t0 = time.time()
    from ..providers import discover

    lid = level_id or (project.levels[0].id if project.levels else "L1")
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    reg = discover(project_dir=project_dir, refresh=True)
    provider = reg.get("omniailab")
    cap = provider.probe() if provider else None
    advertised = list(cap.models) if (cap and cap.models) else None
    if advertised:
        # Cross-check the declaration against what the platform actually says.
        p = catalog_path(project_dir)
        if p:
            try:
                raw = json.loads(p.read_text(encoding="utf-8"))
                missing = [m.get("id") for m in (raw.get("models") or [])
                           if m.get("id") not in advertised]
                if not missing:
                    raw["verified_against_contract"] = True
                    p.write_text(json.dumps(raw, ensure_ascii=False, indent=2),
                                 encoding="utf-8")
            except Exception:
                pass

    views, cat = plan(project, level_id=lid, scheme=scheme, limit=limit,
                      include=include, model=model, project_dir=project_dir,
                      advertised=advertised)

    res = ConceptRenderResult(
        project_id=project.project_id, revision=project.revision,
        scheme=scheme, level_id=lid,
        provider_state=(cap.state if cap else "not_configured"),
        provider_used=(provider.id if (cap and cap.usable and provider) else ""),
        views=views,
    )

    if not views:
        res.status = "blocked"
        res.warnings.append(
            "当前模型里没有可出概念效果图的房间——平面方案尚未落到统一空间模型，"
            "请先运行阶段 S3 生成平面方案。"
        )
        _write_package(project, res, cat, out)
        res.seconds = time.time() - t0
        return res

    # -- reference images (local, deterministic, always available) ---------
    refs: List[str] = []
    if with_reference:
        refs = _write_references(project, res, out, lid, scheme, model)
    for v in res.views:
        v.reference = next((r for r in refs if Path(r).stem.endswith(v.space_id)
                            or Path(r).stem.endswith(v.id)), refs[0] if refs else "")

    # -- submission -------------------------------------------------------
    scope = next((s for s in CANVAS_SCOPES
                  if cap and cap.usable and s in cap.scopes), "")
    if not (cap and cap.usable):
        res.status = "degraded"
        res.notes.append(
            f"OmniAiLab 状态 {res.provider_state}：未生成图像，已输出可直接使用的任务包。"
        )
        if cap and cap.hint:
            res.notes.append(cap.hint)
    elif not scope:
        res.status = "degraded"
        res.notes.append(
            f"平台契约未声明任何画布可用能力域（需要 {', '.join(CANVAS_SCOPES)} 之一）"
        )
    elif not submit:
        res.status = "degraded"
        res.notes.append(
            f"平台已连接（能力域 {scope}），但本次未请求生成："
            "提交属 L3 联网操作，需显式授权。任务包已就绪。"
        )
    elif not authorized:
        res.status = "degraded"
        res.notes.append(
            "提交画布生成属 L3 联网操作且未被授权：已停在授权点，"
            "未发出任何请求（改用 --authorize 授权，或先在画布内手动执行任务包）。"
        )
    else:
        res.scope_used = scope
        from ..tools.registry import registry as tool_registry

        treg = tool_registry()
        treg.guard("render", "render_ai", approved=True)     # L3 ledger record
        _submit_views(project, res, out, scope)

    _write_package(project, res, cat, out)
    if deck:
        _write_deck(project, res, out)
    res.seconds = time.time() - t0
    return res


def _write_deck(project: Project, res: ConceptRenderResult, out: Path) -> None:
    """Turn the batch into a client-facing, editable deck.

    The deck is assembled from `canvas-jobs.json`, so a slide cannot describe a
    view that was never planned, and an ungenerated view shows its reference
    image with an explicit status rather than a stand-in.
    """
    try:
        from .. import presentation

        assets = {
            "renders": res.files.get("jobs", ""),
            "plan": res.files.get("reference_plan", ""),
            "perspective": next((v.output for v in res.generated), "")
                           or res.files.get("reference_plan", ""),
        }
        rep = presentation.render(
            project, "concept-rendering", out_dir=out / "deck",
            assets=assets, level_id=res.level_id, want_pdf=True,
            stem=f"concept-rendering-r{res.revision}",
        )
        res.files["deck_pptx"] = rep["files"].get("pptx", "")
        res.files["deck_md"] = rep["files"].get("markdown", "")
        res.files["deck_html"] = rep["files"].get("html", "")
        res.artifacts.extend(v for k, v in rep["files"].items() if k in
                             ("pptx", "markdown", "html"))
        res.notes.append(
            f"概念效果图汇报已生成：{rep['slides']} 页（可编辑 PPTX，"
            f"后端 {', '.join(rep['pptx_backends'])}）"
        )
        if rep["issues"]:
            res.warnings.extend(f"汇报内容自检：{i}" for i in rep["issues"])
        pdf = rep.get("pdf") or {}
        if pdf.get("ok"):
            res.files["deck_pdf"] = str(pdf.get("path", ""))
        else:
            res.notes.append(f"PDF 未生成：{pdf.get('reason')}（未留空文件）")
    except Exception as exc:
        res.warnings.append(
            f"汇报未生成（{type(exc).__name__}: {exc}）——"
            "任务包与状态文件不受影响。"
        )


# --------------------------------------------------------------------------
def _write_references(project: Project, res: ConceptRenderResult, out: Path,
                      level_id: str, scheme: str, model: str) -> List[str]:
    """Rasterise the confirmed plan + a per-room sheet with the local provider.

    Missing Pillow is reported as a degradation — the prompts stay usable,
    because a reference image can also be supplied by the operator.
    """
    from ..providers import discover

    out_ref = out / "reference"
    out_ref.mkdir(parents=True, exist_ok=True)
    local = discover().get("local")
    made: List[str] = []
    try:
        plan_png = local.plan_png(                     # type: ignore[union-attr]
            project, out_ref / f"plan-r{project.revision}-{scheme}.png",
            level_id=level_id, px_per_m=52.0,
            title="已确认平面（参考图）", scheme=f"方案{scheme}",
        )
        made.append(plan_png)
        sheet = local.submit("multi_view_visualization", {          # type: ignore[union-attr]
            "project": project, "out_path": str(out_ref / f"rooms-r{project.revision}.png"),
            "level_id": level_id,
        })
        made.extend(sheet.outputs)
    except Exception as exc:
        res.warnings.append(
            f"参考图未能生成（{type(exc).__name__}: {exc}）——"
            "提示词与任务包仍可使用，参考图可由操作者自行提供。"
        )
    res.files["reference_plan"] = made[0] if made else ""
    return made


def _submit_views(project: Project, res: ConceptRenderResult, out: Path,
                  scope: str) -> None:
    """Submit each view to the platform canvas, one job per view."""
    from ..providers import discover as _discover

    reg = _discover()
    renders = out / "renders"
    renders.mkdir(parents=True, exist_ok=True)
    any_ok = False
    for v in res.views:
        params = {
            "model": v.model,
            "prompt": v.prompt,
            "negative_prompt": v.negative_prompt,
            "reference_image": v.reference,
            "aspect_ratio": (v.camera.get("aspect") or "16:10"),
            "workflow": "canvas",
            "view_id": v.id,
            "label": v.label,
            "units": 1,
            "project_id": project.project_id,
            "revision": project.revision,
        }
        try:
            job: ProviderJob = reg.generate(scope, params, renders, prefer="omniailab")
        except (NotConfigured, ProviderError) as exc:
            v.status = "failed"
            v.detail = f"{type(exc).__name__}: {exc}"
            res.warnings.append(f"{v.id} 提交失败：{v.detail}")
            continue
        if job.status == "succeeded" and job.outputs:
            v.status = "generated"
            v.output = job.outputs[0]
            v.detail = f"job {job.job_id}"
            any_ok = True
            reg.link_asset(job, job.outputs, project.project_id, project.revision,
                           res.stage, scope)
        else:
            v.status = "failed"
            v.detail = f"job {job.job_id}: {job.error or job.status}"
            res.warnings.append(f"{v.id} 未成功：{v.detail}")
        if job.cost_estimate is not None:
            res.cost_estimate = (res.cost_estimate or 0.0) + float(job.cost_estimate)
            res.currency = job.currency or res.currency
    res.status = "ok" if any_ok and not res.warnings else ("partial" if any_ok else "degraded")
    res.notes.append(
        f"已通过 {scope} 提交 {len(res.views)} 个机位："
        f"成功 {len(res.generated)}，待平台 {len(res.pending)}，"
        f"失败 {len([v for v in res.views if v.status == 'failed'])}。"
    )


# --------------------------------------------------------------------------
def _write_package(project: Project, res: ConceptRenderResult,
                   cat: Dict[str, Any], out: Path) -> None:
    """Write everything a human or the platform needs, with honest statuses."""
    jobs_payload = {
        "schema": "omniailab.canvas-jobs/1",
        "entity": ENTITY,
        "stage": res.stage,
        "capability": res.capability,
        "project_id": project.project_id,
        "revision": project.revision,
        "scheme": res.scheme,
        "level_id": res.level_id,
        "workflow": str((cat.get("canvas") or {}).get("workflow_id") or "canvas"),
        "models_recommended": [m.get("id") for m in recommended_models(cat)],
        "provider": {
            "id": "omniailab",
            "state": res.provider_state,
            "used": res.provider_used,
            "scope_used": res.scope_used,
        },
        "authoritative": False,
        "disclaimer": DISCLAIMER,
        "jobs": [
            {
                "view_id": v.id, "label": v.label, "space_id": v.space_id,
                "space_name": v.space_name, "area_m2": round(v.area_m2, 2),
                "model": v.model, "model_reason": v.model_reason,
                "need": v.need,
                "reference_image": v.reference,
                "prompt": v.prompt, "negative_prompt": v.negative_prompt,
                "camera": v.camera, "lighting": v.lighting, "finishes": v.finishes,
                "aspect_ratio": v.camera.get("aspect") or "16:10",
                "prompt_sha": v.prompt_sha,
                "expected_output": f"renders/{v.id}.png",
                "status": v.status, "output": v.output, "detail": v.detail,
                "authoritative": False,
            }
            for v in res.views
        ],
    }
    jobs_path = out / "canvas-jobs.json"
    jobs_path.write_text(json.dumps(jobs_payload, ensure_ascii=False, indent=2),
                         encoding="utf-8")

    payload_path = out / "canvas-payload.json"
    payload_path.write_text(json.dumps({
        "schema": "omniailab.canvas-payload/1",
        "workflow": str((cat.get("canvas") or {}).get("workflow_id") or "canvas"),
        "platform": {
            "name": "OmniAiLab",
            "canvas": str((cat.get("canvas") or {}).get("display_name") or "画布"),
            "homepages": {"cn": "https://www.omniailabx.com", "intl": "https://omniailab.cn"},
        },
        "provider_state": res.provider_state,
        "note": "本文件描述一次画布执行所需的全部输入；端点与鉴权由平台契约提供，"
                "本文件不包含也不推测任何端点。",
        "inputs": [
            {"view_id": v.id, "model": v.model, "reference_image": v.reference,
             "prompt": v.prompt, "negative_prompt": v.negative_prompt,
             "aspect_ratio": v.camera.get("aspect") or "16:10"}
            for v in res.views
        ],
        "authoritative": False,
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    (out / "RUN-STATUS.md").write_text(_status_md(project, res), encoding="utf-8")

    brief_path = out / "canvas-brief.md"
    brief_path.write_text(_brief_md(project, res, cat), encoding="utf-8")

    snapshot = out / "models.json"
    snapshot.write_text(json.dumps({
        "declaration_source": cat.get("_source") or "builtin",
        "verified_against_contract": bool(cat.get("verified_against_contract")),
        "issues": list(cat.get("_issues") or []),
        "recommended": [{"id": m.get("id"), "display_name": m.get("display_name"),
                         "best_for": m.get("best_for"), "note": m.get("note")}
                        for m in recommended_models(cat)],
        "used_per_view": {v.id: v.model for v in res.views},
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    res.files.update({
        "jobs": str(jobs_path), "payload": str(payload_path),
        "brief": str(brief_path), "status": str(out / "RUN-STATUS.md"),
        "models": str(snapshot),
    })
    res.artifacts.extend([str(jobs_path), str(payload_path), str(brief_path),
                          str(out / "RUN-STATUS.md"), str(snapshot)])
    res.artifacts.extend(v.output for v in res.generated if v.output)


def _status_md(project: Project, res: ConceptRenderResult) -> str:
    lines = [
        f"# 概念效果图执行状态 — {project.project_id} r{res.revision}", "",
        f"- 阶段：{res.stage}（平面方案确认后置动作）　能力：`{res.capability}`",
        f"- 方案：{res.scheme}　机位：{len(res.views)}"
        f"　已生成：{len(res.generated)}　待平台：{len(res.pending)}",
        f"- OmniAiLab provider：{res.provider_state}"
        f"{('（能力域 ' + res.scope_used + '）') if res.scope_used else ''}",
        f"- 整体状态：**{res.status}**",
        "", "| 机位 | 空间 | 面积 ㎡ | 模型 | 状态 | 产出 / 说明 |",
        "|---|---|---|---|---|---|",
    ]
    for v in res.views:
        lines.append(
            f"| {v.id} {v.label} | {v.space_name} | {v.area_m2:.1f} | {v.model} | "
            f"`{v.status}` | {(v.output or v.detail or '任务已在 canvas-jobs.json 中就绪')[:60]} |"
        )
    lines += ["", "## 状态口径", "",
              "- `generated`：平台确实返回了图像文件，已登记为 revision 关联资产；",
              "- `awaiting_platform`：任务包已就绪，尚未生成图像（平台未连接或未授权）；",
              "- `failed`：提交或生成失败，原因逐条记录——不重试成假成功。", ""]
    if res.notes:
        lines += ["## 说明", ""] + [f"- {n}" for n in res.notes] + [""]
    if res.warnings:
        lines += ["## 需要处理", ""] + [f"- {w}" for w in res.warnings] + [""]
    lines += ["---", "", DISCLAIMER, ""]
    return "\n".join(lines)


def _brief_md(project: Project, res: ConceptRenderResult,
              cat: Dict[str, Any]) -> str:
    canvas = cat.get("canvas") or {}
    models = recommended_models(cat)
    lines = [
        f"# 平面确认后的概念效果图 — 画布执行说明", "",
        f"项目：{project.name or project.project_id}（{project.project_id}）"
        f"　模型修订 r{project.revision}　方案 {res.scheme}",
        "", DISCLAIMER, "",
        "## 一、这一步在设计流程里的位置", "",
        "平面方案通过门禁 **G3** 之后立即执行：此时几何已经确认，业主需要先看到空间感受，"
        "再决定是否进入初步设计。所以这批图是**概念效果图**：机位少而精、允许迭代、"
        "明确不承担尺寸责任。",
        "",
        "正式的多视角表现属于阶段 **S5**：那时材质、光线与相机全部取自同一份锁定的"
        "统一空间模型，追求跨视角一致。两批图不要互相替代。",
        "",
        "## 二、推荐模型", "",
        "| 模型 | 适合 | 说明 |", "|---|---|---|",
    ]
    for m in models:
        tags = [NEED_LABELS.get(str(x), str(x)) for x in (m.get("best_for") or [])]
        lines.append(f"| **{m.get('display_name') or m.get('id')}** | "
                     f"{'、'.join(tags)} | {m.get('note') or ''} |")
    lines += [
        "",
        f"声明来源：`{cat.get('_source') or 'builtin'}`"
        f"　与平台契约核对：{'是' if cat.get('verified_against_contract') else '否（平台未连接）'}",
        "",
        "选择口径：需要画面与已确认平面严格对齐、或要读清材质细节时用 **image2.5**；"
        "需要整体空间氛围与多机位一致时用 **OmniP**。这两个模型都由平台画布提供，"
        "使用者可以覆盖本系统的推荐。",
        "",
        "## 三、在画布上怎么执行", "",
    ]
    for i, step in enumerate(canvas.get("typical_flow") or
                             ["新建画布项目并选择模型",
                              "上传参考图（已确认平面 / 房间示意）",
                              "粘贴机位提示词与负向提示词",
                              "逐张生成并按机位编号回填",
                              "如不满意，在画布内局部重绘，保持其余机位不变"], start=1):
        lines.append(f"{i}. {step}")
    lines += [
        "",
        f"工作流标识：`{canvas.get('workflow_id') or 'canvas'}`"
        f"　画布名称：{canvas.get('display_name') or '画布'}",
        "端点与鉴权一律由平台下发的 API 契约提供；本系统不推测、不硬编码。",
        "",
        "## 四、参考图", "",
    ]
    refs = [v.reference for v in res.views if v.reference]
    if refs:
        lines += [f"- `{r}`" for r in dict.fromkeys(refs)]
        lines += ["", "参考图为本地确定性栅格化输出（由统一空间模型直接生成，"
                      "标注「示意图 · 非写实渲染」）。它保证画面与图纸对得上，"
                      "不是效果图本身。"]
    else:
        lines += ["- 未生成参考图（本机缺少 Pillow 或几何为空）："
                  "可自行截取已确认平面图作为参考图，提示词不受影响。"]
    lines += ["", "## 五、机位与提示词", ""]
    for v in res.views:
        lines += [
            f"### {v.id} · {v.label}（{v.space_name}）", "",
            f"- 模型：**{v.model}**（{v.model_reason}）",
            f"- 空间：{v.space_name}　面积约 {v.area_m2:.1f} ㎡"
            f"　开间进深 {(v.camera.get('room_extent_m') or ['?','?'])[0]}m × "
            f"{(v.camera.get('room_extent_m') or ['?','?'])[1]}m",
            f"- 机位：{v.camera.get('lens_mm')}mm，视点高 "
            f"{v.camera.get('eye_height_mm', 0):.0f}mm，画幅 "
            f"{v.camera.get('aspect')}",
            f"- 状态：`{v.status}`"
            + (f"　产出：`{v.output}`" if v.output else ""),
            "", "**提示词**", "", "```text", v.prompt, "```", "",
            "**负向提示词**", "", "```text", v.negative_prompt, "```", "",
        ]
    lines += [
        "## 六、一致性纪律", "",
        "1. 同一批图必须使用同一次设计修订（r%d）：几何一变，全部重出；" % res.revision,
        "2. 参考图固定为同一份已确认平面，不要逐张换参考；",
        "3. 迭代只改单张，不要用新的一批覆盖既有几张——否则同一批图的观感会分裂；",
        "4. 任何一张图都不用来推尺寸、定材料样板或改几何。",
        "",
        "## 七、产出清单", "",
    ]
    for k, v in res.files.items():
        lines.append(f"- `{k}` → `{v}`")
    lines += ["", "---", ""]
    return "\n".join(lines)


__all__ = [
    "MODEL_CATALOG_FILE", "CANVAS_SCOPES", "DEFAULT_CATALOG", "ENTITY",
    "DISCLAIMER", "VIEW_RECIPES", "NEED_LABELS", "ConceptView",
    "ConceptRenderResult", "load_catalog", "catalog_path",
    "recommended_models", "select_model", "pick_views", "plan", "render",
    "overview_camera",
    "NEED_SPATIAL", "NEED_REFERENCE", "NEED_MATERIAL", "NEED_MULTIVIEW",
]
