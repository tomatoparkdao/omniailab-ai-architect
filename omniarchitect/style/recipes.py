"""表现技法库 —— 把"这张图怎么说清楚"沉淀成可审计的配方。

为什么是配方而不是提示词文本
----------------------------
一段好用的提示词里通常混着四种东西：**几何约束**（哪里不能动）、**投影约定**
（透视还是正投影）、**布光与背景**（决定它像不像建筑图）、**版面规则**（哪里放
文字）。整段抄进代码，第二天就没人知道哪一句是安全约束、哪一句只是口味。

所以这里把每一类拆成字段：几何约束进 `geometry_rules`，投影与布光进正向提示词，
文字进 `text_overlay`（由我们排版，不让模型画），边界进 `checks`（产出后必须
核对的项）。改一条约束只改一个字段，审计也只看字段。

六条配方分两族
--------------
| 族 | 配方 | 需要的输入 | 最早可用 |
|---|---|---|---|
| drawing 图纸派生 | `plan-color` `plan-axon` `section-elevation` | 已确认平面（立面/剖面同理） | G3 之后 |
| board 版面 | `presentation-board` `concept-sheet` `material-moodboard` | 平面 / S2 概念包 | 展示板要 G3，其余 S2 |

三条必须改掉的原始写法
----------------------
1. **"红色尺寸标注"** —— 图像模型写出来的数字是编的。尺寸只能由我们的 DXF 矢量层
   叠加，模型侧一律禁止出现任何文字与数字。照抄会把编造的数字送进业主手里。
2. **"用简短标签说明"** —— 同理。配方标 `text_policy="overlay"`，模型只出图形并
   留出文字区，标签由 presentation 层排真字。
3. **"平面图上色"不是平面图** —— 几何一旦被模型重画就不可核对。上色图、立轴图、
   剖面图全部只是**表现图**，不得当图纸、不得量尺寸、不得送审。

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

# 族
DRAWING = "drawing"
BOARD = "board"

# 文字策略
TEXT_NONE = "none"        # 画面内不得出现任何文字/数字
TEXT_OVERLAY = "overlay"  # 模型留出文字区，文字由系统排版叠加

FAMILY_LABEL = {DRAWING: "图纸派生", BOARD: "版面"}


@dataclass(frozen=True)
class VisualRecipe:
    """One way of turning approved design information into a picture."""

    id: str
    name_zh: str
    name_en: str
    family: str
    stages: Tuple[str, ...]
    scope: str
    #: 必须以已确认平面/图纸为参考图，否则没有几何依据
    requires_plan: bool = True
    #: 必须以参考图作为唯一几何来源（不是"建议"，是"必须"）
    requires_reference: bool = True
    projection_zh: str = ""
    projection_en: str = ""
    #: 正向提示词里的固定句（分号连接后进入提示词）
    framing_zh: Tuple[str, ...] = ()
    framing_en: Tuple[str, ...] = ()
    #: 几何/保真约束（进 geometry_rules，也进正向提示词）
    guards_zh: Tuple[str, ...] = ()
    guards_en: Tuple[str, ...] = ()
    #: 额外负向约束
    negative_zh: Tuple[str, ...] = ()
    negative_en: Tuple[str, ...] = ()
    #: 模型可以自由发挥的部分（其余不得增删）
    may_invent: Tuple[str, ...] = ()
    #: 版面文字策略与应叠加的标签（仅 overlay 有意义）
    text_policy: str = TEXT_NONE
    text_overlay: Tuple[str, ...] = ()
    #: 产出后必须人工/程序核对的项（追加到 mandate）
    checks: Tuple[str, ...] = ()
    note: str = ""

    # -- 与 compiler 的 TARGET_PROFILE 兼容的画像 ------------------------
    def profile(self) -> Dict[str, Any]:
        return {
            "zh": self.name_zh,
            "en": self.name_en,
            "focus_zh": "；".join(self.framing_zh) or self.name_zh,
            "focus_en": "; ".join(self.framing_en) or self.name_en,
            "lens_zh": self.projection_zh,
            "may_invent": self.may_invent,
            "family": self.family,
            "text_policy": self.text_policy,
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name_zh": self.name_zh,
            "name_en": self.name_en,
            "family": self.family,
            "family_label": FAMILY_LABEL.get(self.family, self.family),
            "stages": list(self.stages),
            "scope": self.scope,
            "requires_plan": self.requires_plan,
            "requires_reference": self.requires_reference,
            "projection_zh": self.projection_zh,
            "projection_en": self.projection_en,
            "guards_zh": list(self.guards_zh),
            "guards_en": list(self.guards_en),
            "text_policy": self.text_policy,
            "text_overlay": list(self.text_overlay),
            "checks": list(self.checks),
            "may_invent": list(self.may_invent),
            "note": self.note,
        }


#: 所有配方共用的一条：图像不承载几何。
NO_TEXT_ZH = "画面内不得出现任何文字、数字、尺寸标注、比例尺或水印"
NO_TEXT_EN = ("no text, numerals, dimension strings, scale bars or watermarks anywhere "
              "in the frame")
NO_DIMENSION_ZH = "不得标注或暗示任何尺寸数字；标注由出图方在矢量层叠加"
NO_DIMENSION_EN = ("do not write or imply any dimension figure; annotation is overlaid "
                   "by the authoring side in vector")


RECIPES: Dict[str, VisualRecipe] = {
    # ---------------------------------------------------------------- drawing
    "plan-color": VisualRecipe(
        id="plan-color", name_zh="平面图上色", name_en="coloured plan view",
        family=DRAWING, stages=("S3", "S4", "S5"), scope="reference_image_generation",
        projection_zh="接近顶视的三维俯视（≤20° 微透视），正交感强",
        projection_en="near-top-down 3D view (≤20° tilt) with an orthographic feel",
        framing_zh=(
            "把参考图里的建筑平面转成三维俯视上色图：地面、墙面与固定家具上色，"
            "房间关系一眼可读",
            "柔和自然光、轻阴影、简洁渲染；建筑外围只留中性地面，不加任何环境配景",
        ),
        framing_en=(
            "turn the floor plan in the reference image into a colourised 3D top-down view: "
            "floors, walls and fixed joinery coloured, room relationships readable at a glance",
            "soft daylight, light shadows, restrained rendering; neutral ground only outside "
            "the building, no surrounding context",
        ),
        guards_zh=(
            "以参考图平面为**唯一**几何依据：房间数量、分隔、墙体厚度、门窗洞口位置与"
            "连通关系逐一对齐，不得增删或合并房间",
            "不得为了构图调整开间进深、层高或家具位置；家具不得穿过墙体与洞口",
        ),
        guards_en=(
            "the reference plan is the ONLY geometric source: room count, partitions, wall "
            "thickness, opening positions and connectivity match item by item; never add, "
            "remove or merge rooms",
            "never adjust bay depth, storey height or furniture positions for composition; "
            "furniture may not pass through walls or openings",
        ),
        negative_zh=(
            "多出或缺失的房间", "被合并或打通的隔墙", "移动过的门窗", "俯视透视过强像轴测",
            "彩色平面图配色（高饱和色块）", NO_TEXT_ZH, NO_DIMENSION_ZH,
        ),
        negative_en=(
            "extra or missing rooms", "merged or removed partitions", "relocated doors and windows",
            "exaggerated perspective that reads as axonometric",
            "flat marketing colour-block plan style", NO_TEXT_EN, NO_DIMENSION_EN,
        ),
        may_invent=("地面与墙面的具体材质表现", "家具软装的细节", "光影强弱"),
        checks=(
            "把上色图与已确认平面叠合，逐间核对房间数量、隔墙位置与门窗洞口是否一致；"
            "不一致即作废重出。",
            "上色图是表现图，**不得**用于核对面积、开间或任何尺寸。",
        ),
        note="业主最容易误当成平面图的一张：必须与平面图并排放，且标明为表现图。",
    ),

    "plan-axon": VisualRecipe(
        id="plan-axon", name_zh="平面转 3D 立轴图", name_en="isometric cutaway from plan",
        family=DRAWING, stages=("S3", "S4", "S5"), scope="reference_image_generation",
        projection_zh="等距轴测，视点抬高 30–45°，去掉屋顶的开放式剖切",
        projection_en="isometric axon, 30–45° raised viewpoint, open-roof cutaway",
        framing_zh=(
            "按参考图平面生成等距剖切轴测：墙体、楼板与开口的厚度可读，家具按平面就位",
            "模型放在干净的中性底座上，浅色背景，无周边环境，像建筑模型照片",
            "单侧柔和自然光，轻阴影；避免强烈明暗对比",
        ),
        framing_en=(
            "build an isometric cutaway from the reference plan: wall, slab and opening "
            "thicknesses legible, furniture placed as drawn",
            "the model sits on a clean neutral base against a pale studio background with no "
            "surroundings, like a photograph of an architectural model",
            "single-side soft daylight, gentle shadows; avoid strong contrast",
        ),
        guards_zh=(
            "剖切高度统一且不得为了好看降低；墙体厚度与开口位置按参考图，不得加窗加门",
            "结构与构件（梁、柱、管井）只在模型确有的位置出现",
        ),
        guards_en=(
            "one consistent cut height, never lowered for looks; wall thickness and opening "
            "positions follow the reference plan, no added windows or doors",
            "structure and services (beams, columns, shafts) appear only where the model has them",
        ),
        negative_zh=(
            "屋顶未去掉或半透明屋顶", "剖切高度忽高忽低", "多出的楼层或夹层",
            "轴测角度小于 20°（退化成俯视）", "环境配景与树木", NO_TEXT_ZH, NO_DIMENSION_ZH,
        ),
        negative_en=(
            "roof left on or ghosted roof", "inconsistent cut heights",
            "extra floors or mezzanines", "axon angle below 20° (degenerates into top view)",
            "site context or trees", NO_TEXT_EN, NO_DIMENSION_EN,
        ),
        may_invent=("底座材质", "背景纸色", "家具软装细节"),
        checks=(
            "逐间核对剖切后可见的隔墙与开口是否与平面一致；层高按模型，不得目测。",
            "立轴图是表现图，不得据其量取净高或开间。",
        ),
        note="这一张最能说明「空间关系」，也最容易被模型加夹层——所以门槛写死在 guards 里。",
    ),

    "section-elevation": VisualRecipe(
        id="section-elevation", name_zh="正投影立面 / 剖面", name_en="orthographic elevation / section",
        family=DRAWING, stages=("S4", "S5"), scope="reference_image_generation",
        projection_zh="严格正投影，无透视；正面剖切，剖切位置与图纸一致",
        projection_en="strict orthographic projection, no perspective; frontal section at the drawn cut line",
        framing_zh=(
            "按参考图绘制正投影剖面图：墙、楼板、天花的剖面清楚，结构厚度可读",
            "展现相邻房间的内部布置；家具、门窗与立面图保持一致",
            "浅色中性背景，柔和阴影，少量色彩点缀；画面是图纸气质，不是透视渲染",
        ),
        framing_en=(
            "draw an orthographic section from the reference: walls, slabs and ceilings clearly "
            "cut, structural thickness readable",
            "show the interior arrangement of adjacent rooms; furniture, doors and windows "
            "consistent with the elevation",
            "pale neutral background, soft shadows, restrained colour accents; a drawing, "
            "not a perspective render",
        ),
        guards_zh=(
            "层高、楼板厚度、梁高与吊顶标高按模型，不得为构图压缩",
            "剖切位置必须在图纸标注的位置；不得移动剖切线以避开难画的部位",
        ),
        guards_en=(
            "storey height, slab thickness, beam depth and ceiling level follow the model; "
            "never compressed for composition",
            "the cut is taken exactly at the drawn section line; never moved to avoid a "
            "difficult junction",
        ),
        negative_zh=(
            "透视缩短", "消失点", "剖切位置漂移", "未剖到的房间被画成剖到",
            "阴影过重像效果图", NO_TEXT_ZH, NO_DIMENSION_ZH,
        ),
        negative_en=(
            "foreshortening", "vanishing points", "drifted cut plane",
            "rooms shown cut that are not on the cut line", "heavy rendering that reads as a render",
            NO_TEXT_EN, NO_DIMENSION_EN,
        ),
        may_invent=("材质表现", "家具软装细节", "光影"),
        checks=(
            "与图纸剖面对照：层高、板厚、梁位、门窗高度逐项一致；不一致即作废。",
            "本图不是施工立面/剖面图，不得用于报审、下料或指导施工。",
        ),
        note="剖面最容易「看起来对」：因为没有透视，错一点也顺眼——所以必须叠图核对。",
    ),

    # ------------------------------------------------------------------ board
    "presentation-board": VisualRecipe(
        id="presentation-board", name_zh="室内设计展示板", name_en="interior presentation board",
        family=BOARD, stages=("S3", "S4", "S5"), scope="multi_view_visualization",
        requires_plan=True,
        projection_zh="三栏版面：左平面配置、中正立面、右 3D 透视；统一图幅与线宽",
        projection_en="three-panel board: plan at left, orthographic elevation at centre, 3D perspective at right; unified sheet and line weight",
        framing_zh=(
            "分割式设计版面，同一位业主提案里并置三种视图：平面配置图、正立面图、3D 透视",
            "建筑制图风格：线条利落清晰、极简渲染、白色背景、高解析度、专业呈现",
            "以半透明人物剪影作为比例参照，人物静态、与画面同一透视、身高约 1700mm",
        ),
        framing_en=(
            "a divided presentation sheet placing three views side by side: plan, orthographic "
            "elevation and 3D perspective",
            "architectural drawing style: crisp lines, minimal rendering, white background, "
            "high resolution, professional presentation",
            "translucent human silhouettes as scale reference only: static, in the same "
            "projection, about 1700 mm tall",
        ),
        guards_zh=(
            "三块视图必须来自同一方案、同一模型修订：房间数量、隔墙、门窗与家具一致",
            "版面上为文字与标注**留出空白区**，但画面内不得画出任何文字或数字",
        ),
        guards_en=(
            "all three panels come from one scheme and one model revision: room count, "
            "partitions, openings and furniture agree",
            "leave empty zones for text and annotation, but draw no text or numerals anywhere",
        ),
        negative_zh=(
            "三块视图互相对不上", "三块视图风格不统一", "彩色高饱和营销图风格",
            "变形的人体比例", NO_TEXT_ZH, NO_DIMENSION_ZH,
        ),
        negative_en=(
            "panels that contradict each other", "inconsistent style across panels",
            "saturated marketing-graphic look", "distorted human proportions",
            NO_TEXT_EN, NO_DIMENSION_EN,
        ),
        may_invent=("版面留白的比例", "背景纸色", "人物剪影位置"),
        text_policy=TEXT_OVERLAY,
        text_overlay=("方案名称与图名", "视图标签（平面 / 立面 / 透视）", "比例尺",
                      "尺寸标注（由 DXF 矢量层生成）", "项目与修订号", "非权威声明"),
        checks=(
            "三块视图逐块与已确认平面/立面比对，任一块不一致整版作废。",
            "版面上的尺寸标注必须来自 DXF 矢量层；模型若画出数字，一律裁掉重排。",
            "人物剪影只作比例参照，不得据此判断净高或净宽。",
        ),
        note="这张板是给业主看的「提案封面」：好看但必须经得起叠图核对。",
    ),

    "concept-sheet": VisualRecipe(
        id="concept-sheet", name_zh="详细概念设计板", name_en="detailed concept sheet",
        family=BOARD, stages=("S2", "S4"), scope="image_generation",
        requires_plan=False,
        projection_zh="情绪板式版面：分区网格，非透视，正对画面",
        projection_en="moodboard-style sheet: zoned grid, no perspective, square to the frame",
        framing_zh=(
            "为指定空间做一页专业概念设计板，以情绪板的版面语言呈现核心概念",
            "分区包含：概念主题区、色彩配置区、材质样片区、家具语汇区、照明方向区、"
            "关键设计元素区",
            "各分区之间保持构图平衡、风格统一，第一眼能传达整体设计方向与氛围",
        ),
        framing_en=(
            "one professional concept sheet for the named space, in the layout language of a "
            "moodboard",
            "zones for: concept theme, colour palette, material swatches, furniture vocabulary, "
            "lighting direction, key design elements",
            "balanced composition and one consistent style across zones; the design direction "
            "reads at first glance",
        ),
        guards_zh=(
            "色板与材料取样必须来自**已锁定风格库**的声明值，不得自由发挥其它色系",
            "版面上为标签留出空白；画面内不得出现任何文字或数字",
        ),
        guards_en=(
            "palette and material samples must come from the LOCKED style record; do not "
            "improvise another colour family",
            "leave empty zones for labels; draw no text or numerals",
        ),
        negative_zh=(
            "与锁定风格冲突的色系", "同一版面出现两种风格语言", "过度装饰的边框与花纹",
            NO_TEXT_ZH, NO_DIMENSION_ZH,
        ),
        negative_en=(
            "colour family conflicting with the locked style", "two visual languages on one sheet",
            "ornate borders and patterns", NO_TEXT_EN, NO_DIMENSION_EN,
        ),
        may_invent=("样片的摆放方式", "分区间距", "背景纸色"),
        text_policy=TEXT_OVERLAY,
        text_overlay=("概念标题", "色彩名称与占比", "材料名称与做法", "家具语汇标签",
                      "照明要点", "关键设计元素说明"),
        checks=(
            "色彩与材料逐项对照锁定风格库的 hex 与材料名；对不上即重出。",
            "标签必须由排版层写入真实文字，不得沿用模型生成的任何字形。",
            "概念板不承载几何：不得据其核对房间数量、开间或任何尺寸。",
        ),
        note="概念板不承载几何：它的证据是风格库，不是平面。",
    ),

    "material-moodboard": VisualRecipe(
        id="material-moodboard", name_zh="实体材质情绪板", name_en="physical material moodboard",
        family=BOARD, stages=("S2", "S4"), scope="image_generation",
        requires_plan=False, requires_reference=False,
        projection_zh="静物俯拍或 45° 近景，浅景深，无透视变形",
        projection_en="still-life top or 45° close view, shallow depth of field, no distortion",
        framing_zh=(
            "高阶建筑材质情绪板：实体材质样本与触感磁贴的排列，充满艺术感与层次",
            "采用精致的叠加手法（overlapping）呈现，样片之间相互压叠、留出投影",
            "柔和侧光，真实反射与细微瑕疵；背景为浅色中性纸面",
        ),
        framing_en=(
            "a high-end architectural material moodboard: physical samples and tactile swatches "
            "arranged with depth and artistry",
            "refined overlapping composition, swatches layered over one another with real shadows",
            "soft raking light, honest reflections and micro-imperfections, pale neutral paper ground",
        ),
        guards_zh=(
            "材质种类与色系必须对应锁定风格库声明的材料，不得混入无关材质",
            "画面内不得出现任何文字、色号或品牌标识",
        ),
        guards_en=(
            "material types and colour family must match the locked style record; no unrelated "
            "materials",
            "no text, colour codes or brand marks in frame",
        ),
        negative_zh=(
            "塑料感与过度抛光", "色号卡与品牌吊牌", "平铺目录式排列（无层次）",
            NO_TEXT_ZH, NO_DIMENSION_ZH,
        ),
        negative_en=(
            "plastic sheen and over-polishing", "colour cards or brand tags",
            "flat catalogue grid without layering", NO_TEXT_EN, NO_DIMENSION_EN,
        ),
        may_invent=("样片叠放方式", "背景纸色", "投影方向"),
        checks=(
            "材料与色系逐项对照锁定风格库；这张是氛围参考，**不是**材料样板确认。",
            "实际选材以材料表与实物样板为准，不得据生成图下单。",
        ),
        note="与拼贴式 moodboard 的区别：这一张是「实物摄影」，用来谈质感，不用来谈排版。",
    ),
}

#: 需要已确认平面（G3 之后）才能提交的配方
PLAN_GATED: Tuple[str, ...] = tuple(
    rid for rid, r in RECIPES.items() if r.requires_plan)

#: 版面型配方（文字由系统叠加）
OVERLAY_TARGETS: Tuple[str, ...] = tuple(
    rid for rid, r in RECIPES.items() if r.text_policy == TEXT_OVERLAY)


def get(recipe_id: str) -> Optional[VisualRecipe]:
    return RECIPES.get(recipe_id)


def ids() -> Tuple[str, ...]:
    return tuple(RECIPES)


def by_family(family: str) -> List[VisualRecipe]:
    return [r for r in RECIPES.values() if r.family == family]


def target_profiles() -> Dict[str, Dict[str, Any]]:
    """`TARGET_PROFILE` 的增量部分 —— 画像只有一处定义，不在 compiler 里重写。"""
    return {rid: r.profile() for rid, r in RECIPES.items()}


def gate_of(recipe_id: str, plan_confirmed: bool) -> Dict[str, Any]:
    """这条配方此刻能不能用于正式成果。"""
    r = RECIPES.get(recipe_id)
    if r is None:
        return {"requires_plan": False, "plan_confirmed": True, "blocked": False}
    blocked = bool(r.requires_plan and not plan_confirmed)
    return {
        "requires_plan": r.requires_plan,
        "plan_confirmed": bool(plan_confirmed),
        "blocked": blocked,
        "reason": ("该配方以已确认平面为唯一几何依据，未确认前只能用于探索" if blocked else ""),
    }


def from_dict(payload: Dict[str, Any]) -> VisualRecipe:
    """Rebuild a recipe from a prompt package (used when reading a task file back)."""
    rid = str(payload.get("id") or "")
    return RECIPES.get(rid) or VisualRecipe(
        id=rid or "unknown", name_zh=str(payload.get("name_zh") or rid),
        name_en=str(payload.get("name_en") or rid),
        family=str(payload.get("family") or DRAWING),
        stages=tuple(payload.get("stages") or ("S3",)),
        scope=str(payload.get("scope") or "image_generation"),
        text_policy=str(payload.get("text_policy") or TEXT_NONE),
        text_overlay=tuple(payload.get("text_overlay") or ()),
        checks=tuple(payload.get("checks") or ()),
    )


__all__ = ["RECIPES", "VisualRecipe", "PLAN_GATED", "OVERLAY_TARGETS", "TEXT_NONE",
           "TEXT_OVERLAY", "DRAWING", "BOARD", "FAMILY_LABEL", "get", "ids",
           "by_family", "target_profiles", "gate_of", "from_dict"]
