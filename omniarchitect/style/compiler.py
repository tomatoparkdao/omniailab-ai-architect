"""Style-to-Prompt Compiler.

Turns a locked design style plus the actual space (geometry, materials, lighting,
furniture, camera, client needs) into a **structured bilingual prompt** that can
be handed to the OmniAiLab platform.

What this module will not do is promise something it cannot deliver. A prompt
does not contain geometry. Text cannot guarantee that a generated image matches
the approved plan, that two viewpoints agree, or that a wall stayed where it was.
So the compiler emits, alongside the prompt:

* **geometry_preservation rules** — what must not move, and in what terms;
* **a consistency key** — a fingerprint over style set + revision + scene, so
  that several viewpoints share one identity instead of drifting apart;
* **a verification mandate** — the checks that must be performed *on the
  generated result* against the approved model and reference images.

If those checks are skipped, the output is a picture, not a design deliverable.

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

from .catalog import Catalog, load_catalog
from .resources import PROMPT_TARGETS, TARGET_STAGES, stamped

# --------------------------------------------------------------------------
# Per-target framing. Each target is a different *job*, not the same prompt
# with a different noun: a material close-up and a walkthrough differ in what
# belongs in frame, what may be invented, and what must stay fixed.
TARGET_PROFILE: Dict[str, Dict[str, Any]] = {
    "concept": {
        "zh": "概念图", "en": "concept illustration",
        "focus_zh": "空间关系、体块与氛围方向；不追求材质细节与精确尺寸",
        "focus_en": "spatial relationships, massing and atmosphere; material detail and exact dimensions are out of scope",
        "lens_zh": "等效 24–35mm，视高 1500–1600mm，水平构图",
        "may_invent": ("软装细节", "绿植", "装饰品"),
    },
    "moodboard": {
        "zh": "情绪板", "en": "moodboard collage",
        "focus_zh": "材料样板、色彩关系、质感与光线的并置",
        "focus_en": "material swatches, colour relationships, texture and light side by side",
        "lens_zh": "平铺俯视或正面样板视角，无透视变形",
        "may_invent": ("样板摆放方式", "背景纸色"),
    },
    "interior-render": {
        "zh": "室内效果图", "en": "interior rendering",
        "focus_zh": "室内空间完整视野：界面、家具、材质、光线与透视关系",
        "focus_en": "a full interior view: surfaces, furniture, materials, light and perspective",
        "lens_zh": "等效 24–28mm，视高 1400–1600mm，两点透视",
        "may_invent": ("小型软装", "织物褶皱", "装饰摆件"),
    },
    "exterior-render": {
        "zh": "建筑外观图", "en": "exterior architectural rendering",
        "focus_zh": "体量、立面构成、开窗节奏、材料与既有环境关系",
        "focus_en": "massing, facade composition, window rhythm, materials and context",
        "lens_zh": "等效 35–50mm 或移轴，视高 1600mm，避免夸张透视",
        "may_invent": ("天空", "植被", "远处配景建筑"),
    },
    "material-closeup": {
        "zh": "材料特写", "en": "material close-up",
        "focus_zh": "单一材料的表面、纹理、接缝与光影；排除无关元素",
        "focus_en": "a single material's surface, texture, joint and raking light; nothing else in frame",
        "lens_zh": "等效 85–100mm 微距或中长焦，浅景深",
        "may_invent": ("灰尘与细微瑕疵",),
    },
    "partial-renovation": {
        "zh": "局部改造", "en": "partial renovation",
        "focus_zh": "只改动指定部位；原有墙体、门窗、结构构件位置严格不变",
        "focus_en": "change only the named area; walls, openings and structure stay exactly where they are",
        "lens_zh": "与现状照片一致的机位与焦段，便于逐项比对",
        "may_invent": (),
    },
    "multi-view": {
        "zh": "多视角效果图", "en": "multi-view rendering set",
        "focus_zh": "同一空间在多个机位下保持材质、家具与光线一致",
        "focus_en": "one space across several viewpoints, with materials, furniture and light held consistent",
        "lens_zh": "各机位统一焦段与视高，仅改变朝向",
        "may_invent": ("各角度可见的小型软装",),
    },
    "walkthrough-video": {
        "zh": "漫游视频", "en": "walkthrough video",
        "focus_zh": "相机沿既定路径运动，空间与材质在运动中保持稳定、不跳变",
        "focus_en": "camera moves along a set path while space and materials stay stable, without flicker or drift",
        "lens_zh": "等效 24mm，视高 1500mm，匀速推移",
        "may_invent": ("运动路径上的过渡元素",),
    },
}

# Applies to every target. These are the reasons a generated picture is not
# yet a design result.
UNIVERSAL_MANDATE = (
    "把生成结果与**已确认的统一空间模型**逐项比对：开间进深、墙体与门窗位置、层高。",
    "把生成结果与**参考图**（已确认平面的确定性栅格化）比对空间关系是否成立。",
    "多机位或多张产出之间比对：材质、色温、家具形态是否一致；不一致则以模型为准重出。",
    "涉及结构、消防、无障碍、机电负荷与法规符合性的内容，必须由持证专业人员在项目所在地复核签署。",
    "生成图像为非权威成果，**不得作为施工尺寸依据**。",
)

DEFAULT_NEGATIVE_ZH = (
    "改变墙体或门窗位置", "改变房间比例与层高", "添加不存在的结构构件",
    "乱码文字与错字招牌", "失真的人体比例", "过度 HDR 与塑料感",
    "与锁定风格冲突的材质", "品牌 logo 与商标", "水印与画面外文字",
)

DEFAULT_NEGATIVE_EN = (
    "altered wall or window positions", "altered room proportions or ceiling height",
    "structural elements that do not exist", "garbled text or signage",
    "distorted human proportions", "over-processed HDR and plastic sheen",
    "materials conflicting with the locked style", "brand logos and trademarks",
    "watermarks or out-of-frame text",
)

GEOMETRY_RULES_COMMON = (
    "所有墙体、门窗洞口、梁柱的位置与尺寸保持与已确认模型一致。",
    "房间的开间、进深与净高不得被调整以适配构图。",
    "家具与固定件只能布置在模型允许的位置，不得穿过墙体或洞口。",
)


@dataclass
class SpaceBrief:
    """The real space, as taken from the canonical model — not invented."""

    space_name: str = ""                  # 客厅 / 主卧 / 外立面 …
    area_m2: Optional[float] = None
    width_mm: Optional[int] = None        # 开间
    depth_mm: Optional[int] = None        # 进深
    ceiling_mm: Optional[int] = None      # 净高
    orientation: str = ""                 # 朝向与主要采光面
    openings: Sequence[str] = ()          # 门、窗、洞口的位置与尺寸描述
    existing_elements: Sequence[str] = () # 改造时需保留的既有构件
    to_change: Sequence[str] = ()         # 局部改造时允许改动的部位
    materials_override: Sequence[str] = ()
    lighting_override: Sequence[str] = ()
    furniture_needs: Sequence[str] = ()
    camera: str = ""                      # 机位描述（可覆盖默认）
    style_ratio: Dict[str, float] = field(default_factory=dict)  # 混搭比例
    references: Sequence[str] = ()        # 参考图路径（已确认平面的栅格化等）

    def to_dict(self) -> Dict[str, Any]:
        return {
            "space_name": self.space_name,
            "area_m2": self.area_m2,
            "width_mm": self.width_mm,
            "depth_mm": self.depth_mm,
            "ceiling_mm": self.ceiling_mm,
            "orientation": self.orientation,
            "openings": list(self.openings),
            "existing_elements": list(self.existing_elements),
            "to_change": list(self.to_change),
            "materials_override": list(self.materials_override),
            "lighting_override": list(self.lighting_override),
            "furniture_needs": list(self.furniture_needs),
            "camera": self.camera,
            "style_ratio": dict(self.style_ratio),
            "references": list(self.references),
        }

    def geometry_lines_zh(self) -> List[str]:
        out: List[str] = []
        if self.space_name:
            out.append(f"空间：{self.space_name}")
        if self.width_mm and self.depth_mm:
            out.append(f"开间 × 进深：{self.width_mm} × {self.depth_mm} mm")
        if self.ceiling_mm:
            out.append(f"净高：{self.ceiling_mm} mm")
        if self.area_m2:
            out.append(f"面积：约 {self.area_m2:g} m²")
        if self.orientation:
            out.append(f"朝向与采光：{self.orientation}")
        if self.openings:
            out.append("门窗与洞口：" + "；".join(self.openings))
        return out

    def geometry_lines_en(self) -> List[str]:
        out: List[str] = []
        if self.space_name:
            out.append(f"space: {self.space_name}")
        if self.width_mm and self.depth_mm:
            out.append(f"width × depth: {self.width_mm} × {self.depth_mm} mm")
        if self.ceiling_mm:
            out.append(f"clear ceiling height: {self.ceiling_mm} mm")
        if self.area_m2:
            out.append(f"area: about {self.area_m2:g} m²")
        if self.orientation:
            out.append(f"orientation and daylight: {self.orientation}")
        if self.openings:
            out.append("openings: " + "; ".join(self.openings))
        return out


@dataclass
class CompiledPrompt:
    """A prompt is only half the deliverable; the mandate is the other half."""

    target: str
    stage: str
    style_ids: List[str]
    style_labels: List[str]
    consistency_key: str
    revision: int
    positive_zh: str
    positive_en: str
    negative_zh: List[str] = field(default_factory=list)
    negative_en: List[str] = field(default_factory=list)
    structured: Dict[str, Any] = field(default_factory=dict)
    geometry_rules: List[str] = field(default_factory=list)
    lock_note: str = ""
    mandate: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    # -- export ---------------------------------------------------------
    def to_dict(self) -> Dict[str, Any]:
        return {
            "target": self.target,
            "stage": self.stage,
            "style_ids": list(self.style_ids),
            "style_labels": list(self.style_labels),
            "consistency_key": self.consistency_key,
            "revision": self.revision,
            "positive": {"zh": self.positive_zh, "en": self.positive_en},
            "negative": {"zh": list(self.negative_zh), "en": list(self.negative_en)},
            "structured": dict(self.structured),
            "geometry_preservation": list(self.geometry_rules),
            "style_lock": self.lock_note,
            "verification_mandate": list(self.mandate),
            "warnings": list(self.warnings),
            "authoritative": False,
            "disclaimer": (
                "提示词不承载几何。任何产出都必须与已确认模型和参考图比对后方可用于设计沟通；"
                "生成图像不得作为施工尺寸依据。"
            ),
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)

    def to_markdown(self, *, frontmatter: bool = False) -> str:
        """Render the job package as Markdown.

        `frontmatter=True` is used when the result is *written to disk* — files
        in this project carry the unified header. Terminal output stays clean.
        """
        k = TARGET_PROFILE.get(self.target, {})
        lines = [
            f"# 提示词任务包 —— {k.get('zh', self.target)}",
            "",
            f"- 目标类型：`{self.target}`（{k.get('en', '')}）",
            f"- 建议阶段：{self.stage}",
            f"- 风格：{' + '.join(self.style_labels)}",
            f"- 一致性指纹：`{self.consistency_key}`",
            f"- 模型修订：r{self.revision}",
        ]
        if self.lock_note:
            lines.append(f"- {self.lock_note}")
        for w in self.warnings:
            lines.append(f"- ⚠ {w}")
        lines += ["", f"**画面重点**：{k.get('focus_zh', '')}",
                  f"**机位倾向**：{k.get('lens_zh', '')}", ""]
        lines += ["## 正向提示词（中文）", "", "```text", self.positive_zh.strip(), "```", ""]
        lines += ["## Positive prompt (English)", "", "```text", self.positive_en.strip(), "```", ""]
        lines += ["## 负向约束（中文）", ""]
        lines += [f"- {n}" for n in self.negative_zh] or ["- （无）"]
        lines += ["", "## Negative constraints (English)", ""]
        lines += [f"- {n}" for n in self.negative_en] or ["- （none）"]
        lines += ["", "## 几何保持（必须遵守）", ""]
        lines += [f"- {g}" for g in self.geometry_rules] or ["- （无）"]
        lines += ["", "## 产出后必须做的校核（不能跳过）", ""]
        lines += [f"- [ ] {m}" for m in self.mandate]
        lines += [
            "", "---", "",
            "> 提示词**不承载几何**。纯提示词无法保证精确的几何一致性——"
            "必须结合已确认模型、参考图与生成结果逐项校核。生成图像为非权威成果，不得作为施工尺寸依据。",
        ]
        body = "\n".join(lines)
        if not frontmatter:
            return body
        return stamped(
            body,
            name=f"omniailab-style-prompt-{self.target}",
            description=f"提示词任务包 —— {k.get('zh', self.target)}（`{self.target}`）："
                        f"中英双语分层结构、几何保持规则与产出后校核清单；"
                        f"风格 {' + '.join(self.style_labels)}，一致性指纹 {self.consistency_key}。",
        )


def _fingerprint(style_ids: Sequence[str], revision: int,
                 ratio: Dict[str, float]) -> str:
    """Stable identity for a *style revision* — the anti-drift key.

    Deliberately independent of the room and the camera. The thing that must not
    drift across five rooms or six viewpoints is the material and lighting
    language, and that language is fixed by the style set plus the model
    revision. Keying it on the room name would give every room its own identity
    and make cross-room consistency unenforceable — which is the exact failure
    this key exists to prevent.
    """
    payload = json.dumps({
        "styles": sorted(style_ids),
        "revision": revision,
        "ratio": {k: round(float(v), 3) for k, v in sorted(ratio.items())},
    }, ensure_ascii=False, sort_keys=True)
    return "sp-" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]


def compile_prompt(
    style_ids: Sequence[str],
    brief: Optional[SpaceBrief] = None,
    *,
    target: str = "interior-render",
    stage: str = "",
    revision: int = 1,
    catalogue: Optional[Catalog] = None,
    locked: bool = False,
    user_needs: Sequence[str] = (),
    extra_negative: Sequence[str] = (),
    reference_note: str = "",
) -> CompiledPrompt:
    """Compile a bilingual, structured prompt for one target.

    `locked=True` asserts the style has been approved at a gate. Compiling is
    still permitted without a lock — for exploration — but the prompt then says
    so, and the output is marked as not-yet-approved.
    """
    if target not in PROMPT_TARGETS:
        raise ValueError(f"未知目标类型 {target!r}；可用：{', '.join(PROMPT_TARGETS)}")
    cat = catalogue or load_catalog()
    brief = brief or SpaceBrief()
    stage = stage or (TARGET_STAGES.get(target, ("S5",))[0])
    profile = TARGET_PROFILE[target]

    styles = [cat.load_style(s) for s in style_ids]
    entries = [cat.get(s) for s in style_ids]
    labels = [e.label for e in entries]

    # -- style layer ----------------------------------------------------
    main_zh = styles[0]["positive_prompt_components"]["zh"]
    main_en = styles[0]["positive_prompt_components"]["en"]
    blend_zh: List[str] = []
    blend_en: List[str] = []
    for s, e in list(zip(styles, entries))[1:]:
        comp_zh = s["positive_prompt_components"]["zh"]
        blend_zh.append(f"{e.display_name_zh}（{comp_zh.get('material', '')}）")
        comp_en = s["positive_prompt_components"]["en"]
        blend_en.append(f"{e.display_name_en} ({comp_en.get('material', '')})")

    # Blend ratio: explicit if given, otherwise the main style dominates.
    ratio = (dict(brief.style_ratio) or {style_ids[0]: 1.0}) if style_ids else {}

    # -- geometry layer -------------------------------------------------
    geo_zh = brief.geometry_lines_zh()
    geo_en = brief.geometry_lines_en()

    # -- assemble positive -----------------------------------------------
    zh_parts: List[str] = [
        f"【风格】{labels[0]}。{main_zh.get('space', '')}",
        f"【材质】{main_zh.get('material', '')}",
        f"【光线】{main_zh.get('lighting', '')}",
        f"【家具】{main_zh.get('furniture', '')}",
        f"【机位】{brief.camera or main_zh.get('camera', '') or profile['lens_zh']}",
        f"【氛围】{main_zh.get('atmosphere', '')}",
    ]
    if blend_zh:
        zh_parts.insert(1, "【混搭（次要）】" + "；".join(blend_zh) +
                        "。混搭只借材质与色板，不改主风格的空间逻辑。")
    if geo_zh:
        zh_parts.insert(1, "【空间（取自已确认模型，不得改动）】" + "；".join(geo_zh))
    if brief.materials_override:
        zh_parts.append("【本项目材料】" + "；".join(brief.materials_override))
    if brief.lighting_override:
        zh_parts.append("【本项目光线条件】" + "；".join(brief.lighting_override))
    if brief.furniture_needs:
        zh_parts.append("【客户功能需求】" + "；".join(brief.furniture_needs))
    if user_needs:
        zh_parts.append("【其它要求】" + "；".join(user_needs))
    keywords = list(main_zh.get("keywords") or [])
    if keywords:
        zh_parts.append("【关键词】" + "，".join(keywords))
    if target == "partial-renovation" and brief.to_change:
        zh_parts.append("【只允许改动】" + "；".join(brief.to_change))
    if target == "partial-renovation" and brief.existing_elements:
        zh_parts.append("【必须原样保留】" + "；".join(brief.existing_elements))
    zh_parts.append(f"【画面目标】{profile['focus_zh']}")

    en_parts: List[str] = [
        f"[style] {entries[0].display_name_en}. {main_en.get('space', '')}",
        f"[materials] {main_en.get('material', '')}",
        f"[light] {main_en.get('lighting', '')}",
        f"[furniture] {main_en.get('furniture', '')}",
        f"[camera] {brief.camera or main_en.get('camera', '') or profile['lens_zh']}",
        f"[atmosphere] {main_en.get('atmosphere', '')}",
    ]
    if blend_en:
        en_parts.insert(1, "[blend (secondary)] " + "; ".join(blend_en) +
                        ". The blend borrows materials and palette only; it does not change the primary spatial logic.")
    if geo_en:
        en_parts.insert(1, "[space, taken from the approved model — do not alter] " + "; ".join(geo_en))
    if brief.materials_override:
        en_parts.append("[project materials] " + "; ".join(brief.materials_override))
    if brief.lighting_override:
        en_parts.append("[lighting conditions] " + "; ".join(brief.lighting_override))
    if brief.furniture_needs:
        en_parts.append("[client requirements] " + "; ".join(brief.furniture_needs))
    if user_needs:
        en_parts.append("[other requirements] " + "; ".join(user_needs))
    en_keywords = list(main_en.get("keywords") or [])
    if en_keywords:
        en_parts.append("[keywords] " + ", ".join(en_keywords))
    if target == "partial-renovation" and brief.to_change:
        en_parts.append("[change only] " + "; ".join(brief.to_change))
    if target == "partial-renovation" and brief.existing_elements:
        en_parts.append("[keep exactly as-is] " + "; ".join(brief.existing_elements))
    en_parts.append(f"[shot purpose] {profile['focus_en']}")

    positive_zh = "\n".join(zh_parts)
    positive_en = "\n".join(en_parts)

    # -- negatives ------------------------------------------------------
    neg_zh = list(dict.fromkeys(list(styles[0]["negative_constraints"]["zh"]) + list(DEFAULT_NEGATIVE_ZH)))
    neg_en = list(dict.fromkeys(list(styles[0]["negative_constraints"]["en"]) + list(DEFAULT_NEGATIVE_EN)))
    for s in styles[1:]:
        neg_zh += [n for n in s["negative_constraints"]["zh"] if n not in neg_zh]
        neg_en += [n for n in s["negative_constraints"]["en"] if n not in neg_en]
    for n in extra_negative:
        if n and n not in neg_zh:
            neg_zh.append(n)

    # -- geometry preservation -------------------------------------------
    geo_rules = list(GEOMETRY_RULES_COMMON)
    for s in styles:
        for r in s.get("geometry_preservation_rules") or []:
            if r not in geo_rules:
                geo_rules.append(r)
    if target == "partial-renovation":
        geo_rules = [
            "**局部改造强约束**：除指定改动部位外，所有墙体、门窗、梁柱、管井位置与尺寸保持原样。",
            *geo_rules,
        ]

    # -- consistency key --------------------------------------------------
    # One key per (style set, revision) — shared by every room and viewpoint.
    key = _fingerprint(style_ids, revision, ratio)

    # -- warnings (honesty layer) -----------------------------------------
    warnings: List[str] = []
    if not locked:
        warnings.append("风格尚未在门禁确认（未锁定）。本提示词用于探索；业主确认后应重新编译并锁定。")
    if not brief.width_mm or not brief.depth_mm:
        warnings.append("未提供开间/进深。缺几何信息时，生成结果的比例关系不可信。")
    if not brief.references:
        warnings.append("未附参考图。建议附上已确认平面的确定性栅格化图，作为空间关系的比对基准。")
    if target in ("multi-view", "walkthrough-video") and len(style_ids) == 1:
        warnings.append("多机位/漫游任务建议以同一个一致性指纹批量提交，避免各机位材质漂移。")
    if target == "partial-renovation" and not brief.existing_elements:
        warnings.append("局部改造未声明「必须原样保留」的既有构件，容易改过头。")

    lock_note = ("风格已锁定（门禁确认），提示词以锁定结果为准。" if locked
                 else "风格未锁定：仅供方向探索。")

    return CompiledPrompt(
        target=target,
        stage=stage,
        style_ids=list(style_ids),
        style_labels=labels,
        consistency_key=key,
        revision=revision,
        positive_zh=positive_zh,
        positive_en=positive_en,
        negative_zh=neg_zh,
        negative_en=neg_en,
        structured={
            "target": target,
            "stage": stage,
            "style": {
                "primary": {"id": entries[0].style_id, "name_zh": entries[0].display_name_zh,
                            "name_en": entries[0].display_name_en},
                "blend": [{"id": e.style_id, "name_zh": e.display_name_zh, "name_en": e.display_name_en}
                          for e in entries[1:]],
                "ratio": ratio,
            },
            "space": brief.to_dict(),
            "layers": {
                "space": main_zh.get("space", ""),
                "material": main_zh.get("material", ""),
                "lighting": main_zh.get("lighting", ""),
                "furniture": main_zh.get("furniture", ""),
                "camera": brief.camera or main_zh.get("camera", ""),
                "atmosphere": main_zh.get("atmosphere", ""),
                "keywords": keywords,
            },
            "consistency": {
                "key": key,
                "share_across_views": True,
                "scope": "同一（风格集合 + 模型修订）下的所有房间与机位共用同一指纹；"
                         "产出后据此比对材质与光源方向是否漂移",
                "view": {"space": brief.space_name, "camera": brief.camera,
                         "width_mm": brief.width_mm, "depth_mm": brief.depth_mm},
            },
            "references": list(brief.references),
            "reference_note": reference_note,
            "authoritative": False,
        },
        geometry_rules=geo_rules,
        lock_note=lock_note,
        mandate=list(UNIVERSAL_MANDATE),
        warnings=warnings,
    )


def compile_view_set(
    style_ids: Sequence[str],
    views: Sequence[SpaceBrief],
    *,
    target: str = "multi-view",
    stage: str = "",
    revision: int = 1,
    catalogue: Optional[Catalog] = None,
    locked: bool = False,
) -> Dict[str, Any]:
    """Compile one prompt per viewpoint, all sharing a single consistency key.

    Sharing the key is the point: it is the mechanical way to make "keep the
    materials identical across viewpoints" auditable rather than aspirational.
    """
    cat = catalogue or load_catalog()
    prompts = [
        compile_prompt(style_ids, v, target=target, stage=stage, revision=revision,
                       catalogue=cat, locked=locked)
        for v in views
    ]
    keys = {p.consistency_key for p in prompts}
    same = len(keys) == 1
    return {
        "target": target,
        "style_ids": list(style_ids),
        "revision": revision,
        "view_count": len(prompts),
        "consistency_key": next(iter(keys)) if same else "",
        "consistent": same,
        "note": ("所有机位共用同一一致性指纹（口径 = 风格集合 + 模型修订号）："
                 "可据指纹批量提交，产出后逐张比对材质与光源方向是否漂移。"
                 if same else
                 "各机位指纹不一致——说明风格集合或模型修订号有差异，需先统一再提交。"),
        "prompts": [p.to_dict() for p in prompts],
        "mandate": list(UNIVERSAL_MANDATE),
    }
