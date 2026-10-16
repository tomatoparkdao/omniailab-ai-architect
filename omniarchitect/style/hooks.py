"""Where the style system plugs into the eight-stage design workflow.

A style library that only lives in a folder is a catalogue. This module is what
makes it part of the process: each stage gets a named hook with defined inputs,
defined outputs, and a defined relationship to its gate.

| Stage | Hook | Output |
|---|---|---|
| S2 概念 | style recommendation + moodboard direction | three options, then a locked style |
| S3 平面 | style ↔ space relationship check | conflicts between the style and the actual plan |
| S4 初步设计 | material / form / furniture / lighting extraction | a project-specific spec derived from the style |
| S5 效果表现 | prompt compilation for images and video | bilingual structured prompts + job package |
| S7 施工深化 | material specification & design-intent check | spec table + intent deviations |
| S8 交付 / 汇报 | style comparison deck data | comparison table for the S2–S8 presentation |

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from .catalog import Catalog, load_catalog
from .compiler import SpaceBrief, compile_prompt, compile_view_set  # noqa: F401
from .resources import HOOKED_STAGES
from .provider_bridge import submit  # noqa: F401
from .recommender import RecommendRequest, recommend  # noqa: F401

# The imports above are re-exported on purpose: each stage hook declares the
# `api` it drives, and a test asserts those names resolve to real callables.
# A hook that names a capability nobody implemented is a lie in a config file.

# --------------------------------------------------------------------------
# Frame contract
#
# The eight-stage workflow belongs to this same package: `omniarchitect.stages`
# is the single authority for stage ids, stage names and gate labels.
#
# The style system used to live in a separate project and read an **exported
# snapshot** of that model, because it could not import across repositories.
# Now that the two are one skill, the hooks read the stage model directly —
# no copy, no snapshot file, and no window in which the two can disagree.
from ..stages import STAGES as _CORE_STAGES

_STAGE_BY_ID: Dict[str, Any] = {s.id: s for s in _CORE_STAGES}


def stage_name(stage_id: str) -> str:
    """The stage's official name, straight from the stage model."""
    s = _STAGE_BY_ID.get(stage_id.upper())
    return s.name if s else ""


def gate(stage_id: str) -> Dict[str, str]:
    """The gate that governs a stage — read from the stage model."""
    s = _STAGE_BY_ID.get(stage_id.upper())
    if not s:
        return {"id": "", "label": "", "approver": ""}
    return {"id": s.gate.id, "label": s.gate.label, "approver": s.gate.approver}


def gate_label(stage_id: str) -> str:
    """`G3 平面方案确认` — the exact wording the stage model uses."""
    g = gate(stage_id)
    return f"{g['id']} {g['label']}".strip()


def frame_source() -> Dict[str, Any]:
    """Where the stage/gate vocabulary comes from now that the two are merged."""
    from ..paths import project_version

    return {
        "frame": "omniarchitect.stages",
        "source_project": "omniailab-ai-architect",
        "source_version": project_version(),
        "stage_count": len(_CORE_STAGES),
    }


STAGE_HOOKS: Dict[str, Dict[str, Any]] = {
    "S2": {
        "name": "概念阶段：风格推荐与 Moodboard",
        "actions": [
            "收集六项输入：空间类型、面积与尺度、预算档位、所在地/气候、用户喜好、可接受的维护投入。",
            "调用推荐引擎产生三套方向不同的方案（稳妥 / 个性 / 混搭），逐套说明优缺点与代价。",
            "等待业主指定其一 —— 未确认前不进入深化。",
            "确认后写入风格锁定文件（带修订号），作为后续所有编译与选材的唯一依据。",
        ],
        "api": ["recommend", "lock_style"],
        "produces": ["style-recommendation.md", "style-lock-r<revision>.json"],
        "gate": gate_label("S2"),
        "rule": "风格未锁定不进入 S3 深化；锁定后若需求或几何改变，必须重新评估是否解锁。",
    },
    "S3": {
        "name": "平面阶段：风格与空间关系检查",
        "actions": [
            "用锁定风格的空间原则逐条对照平面：主要动线、公共与私密分区、采光面分配。",
            "检查风格的尺度要求（净高、开间、家具退距）与本户型实际条件是否冲突。",
            "冲突项写入 warnings，并给出「调整平面」或「调整风格取向」两条可选路径，不代业主决定。",
        ],
        "api": ["style_space_check"],
        "produces": ["style-space-check.md"],
        "gate": gate_label("S3"),
        "rule": "平面确认后风格效果图才允许生成（G3 后置动作）；平面一变，效果图整批作废。",
    },
    "S4": {
        "name": "初步设计：材料、造型、家具、灯光",
        "actions": [
            "从锁定风格提取材料体系、色彩板、家具语汇与照明策略。",
            "与本项目实际做法对齐：把风格的材料替换为当地可采购的同类品，并记录替换理由。",
            "输出可直接进材料表与照明方案的字段（名称、位置、表面处理、色温、照度取向）。",
        ],
        "api": ["material_spec"],
        "produces": ["style-material-spec.json", "style-material-spec.md"],
        "gate": gate_label("S4"),
        "rule": "替换材料不得改变风格的空间逻辑；替换必须记录，不得静默降级。",
    },
    "S5": {
        "name": "效果表现：生图与视频提示词编译",
        "actions": [
            "把风格 + 空间几何 + 材料 + 灯光 + 家具 + 相机 + 业主需求编译为中英双语结构化提示词。",
            "多机位与漫游任务共用同一一致性指纹，保证跨视角的材质与光源一致。",
            "通过 OmniAiLab Provider 提交；平台不可用时输出任务包并标 awaiting_platform。",
            "产出后按校核清单与已确认模型、参考图逐项比对。",
        ],
        "api": ["compile_prompt", "compile_view_set", "submit"],
        "produces": ["style-jobs.json", "style-jobs-brief.md"],
        "gate": gate_label("S5"),
        "rule": "提示词不承载几何——纯提示词无法保证精确几何一致，必须结合已确认模型与参考图校核。",
    },
    "S7": {
        "name": "施工深化：材料规范与设计意图核对",
        "actions": [
            "把风格的材料与构造要求转成采购与施工可用的规格条目（品类、规格、表面处理、拼法）。",
            "核对深化图是否偏离风格意图：缝宽、收口、线脚、拼花方向。",
            "偏离项列为设计意图偏差，交主创裁定；涉及结构/消防/法规的条目标注待专业复核。",
        ],
        "api": ["material_spec", "design_intent_check"],
        "produces": ["style-construction-spec.md", "style-intent-deviation.md"],
        "gate": gate_label("S7"),
        "rule": "本系统只做设计意图层面的核对，不出结构与法规结论。",
    },
    "S8": {
        "name": "交付与汇报：风格对比",
        "actions": [
            "生成风格对比数据：三套候选的空间原则、材料、色彩、造价驱动、维护强度并排。",
            "供汇报使用：把「为什么选它」与「代价是什么」写清，不写「两套都行」。",
            "随交付包记录风格锁定的修订号，便于追责与回溯。",
        ],
        "api": ["comparison_data"],
        "produces": ["style-comparison.json", "style-comparison.md"],
        "gate": gate_label("S8"),
        "rule": "汇报中的效果图必须标注为非权威成果。",
    },
}


def lock_style(
    style_id: str,
    request: RecommendRequest,
    *,
    out_dir: str | Path,
    revision: int = 1,
    by: str = "",
) -> Dict[str, Any]:
    """S2: record the client's choice and bind it to a model revision.

    Runs the recommendation again so the lock file carries the alternatives that
    were actually on the table — six months later, "why this style?" is
    answerable without anyone's memory.
    """
    from pathlib import Path as _Path
    import json as _json

    rs = recommend(request)
    if style_id in {o.style_id for o in rs.options}:
        return rs.lock(style_id, out_dir=out_dir, revision=revision, by=by)

    # Chosen directly rather than from the three options — allowed, but recorded
    # as such, and the revision binding still applies.
    cat = load_catalog()
    entry = cat.get(style_id)                       # raises KeyError if unknown
    payload = {
        "locked_style": style_id,
        "role": "direct",
        "style_label": entry.label,
        "revision": revision,
        "locked_by": by or "业主",
        "request": request.to_dict(),
        "options_considered": [o.to_dict() for o in rs.options],
        "note": "该风格由用户直接指定（不在三套推荐内）。仍记录修订号，"
                "几何或需求变更时应重新评估是否解锁。",
        "reversible": True,
    }
    out = _Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    p = out / f"style-lock-r{revision}.json"
    p.write_text(_json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload


def hook(stage: str) -> Dict[str, Any]:
    """Return the style-system hook for a stage (or an explicit 'no hook')."""
    h = STAGE_HOOKS.get(stage.upper())
    if not h:
        return {
            "stage": stage.upper(),
            "name": "该阶段无风格系统挂钩",
            "stage_name": stage_name(stage.upper()),
            "actions": [],
            "api": [],
            "produces": [],
            "gate": gate_label(stage.upper()),
            "gate_id": gate(stage.upper())["id"],
            "gate_label": gate(stage.upper())["label"],
            "gate_approver": gate(stage.upper())["approver"],
            "frame_source": frame_source(),
            "rule": "风格系统只在 "
                    + " / ".join(HOOKED_STAGES) + " 六个节点介入。",
        }
    sid = stage.upper()
    g = gate(sid)
    return {
        "stage": sid,
        "stage_name": stage_name(sid),
        **h,
        "gate_id": g["id"],
        "gate_label": g["label"],
        "gate_approver": g["approver"],
        "frame_source": frame_source(),
    }


def all_hooks() -> List[Dict[str, Any]]:
    return [hook(s) for s in HOOKED_STAGES]


# --------------------------------------------------------------------------
def style_space_check(
    style_id: str,
    brief: SpaceBrief,
    *,
    catalogue: Optional[Catalog] = None,
) -> Dict[str, Any]:
    """S3: test a style's spatial demands against the actual plan.

    This is deliberately a *conflict report*, not a verdict. Where the style and
    the plan disagree, the user decides which one moves — the system must not
    quietly reshape the plan to suit a mood board.
    """
    cat = catalogue or load_catalog()
    style = cat.load_style(style_id)
    entry = cat.get(style_id)

    conflicts: List[str] = []
    notes: List[str] = []

    # ceiling height
    ceil_range = ((style.get("proportion_and_geometry") or {}).get("ceiling_height_mm") or "")
    if brief.ceiling_mm and ceil_range:
        import re
        nums = [int(n) for n in re.findall(r"\d{3,4}", str(ceil_range))]
        if len(nums) >= 2 and brief.ceiling_mm < nums[0]:
            conflicts.append(
                f"该风格的做法常见净高为 {ceil_range}，本项目净高 {brief.ceiling_mm}mm "
                f"偏低，造型（如天花层次、吊灯、门洞）需要简化或改用替代做法。"
            )
        elif nums:
            notes.append(f"该风格常见净高 {ceil_range}，本项目 {brief.ceiling_mm}mm。")

    # spatial principles vs stated needs
    needs = " ".join(brief.furniture_needs) + " " + (brief.to_change and " ".join(brief.to_change) or "")
    principles = style.get("spatial_principles") or []
    if principles:
        notes.append("该风格的空间原则（逐条对照平面）：" + "；".join(str(p) for p in principles))

    # incompatible declarations
    for item in style.get("incompatible_elements") or []:
        if item and item in needs:
            conflicts.append(f"你的需求里出现了与本风格冲突的元素：{item}")

    # area sanity
    if brief.area_m2 and brief.area_m2 < 90 and entry.budget_tier in ("premium", "luxury"):
        notes.append("小面积 + 高档位风格：需要在材料用量上做减法，否则预算会集中到少量构件上。")

    return {
        "stage": "S3",
        "style_id": style_id,
        "style": entry.label,
        "conflicts": conflicts,
        "notes": notes,
        "decision_paths": [
            "路径一：调整平面（改开间/净高/洞口）以适配风格。",
            "路径二：调整风格取向（在同族内换一个尺度要求更低的风格）。",
        ] if conflicts else [],
        "rule": "两项都不由系统替你决定；请明确选一条路径后再进入 G3 确认。",
        "checked_against": brief.to_dict(),
    }


def material_spec(style_id: str, *, catalogue: Optional[Catalog] = None,
                  substitutions: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """S4/S7: turn a style's material system into procurement-ready rows."""
    cat = catalogue or load_catalog()
    style = cat.load_style(style_id)
    entry = cat.get(style_id)
    substitutions = substitutions or {}

    rows = []
    for m in style.get("materials") or []:
        name_zh = str(m.get("name_zh", ""))
        rows.append({
            "material_zh": name_zh,
            "material_en": str(m.get("name_en", "")),
            "application": str(m.get("application", "")),
            "finish": str(m.get("finish", "")),
            "substituted_to": substitutions.get(name_zh, ""),
            "substitution_reason": ("本项目替换" if name_zh in substitutions else ""),
        })

    return {
        "stage": "S4",
        "style_id": style_id,
        "style": entry.label,
        "materials": rows,
        "palette": [
            {"name_zh": c.get("name_zh"), "name_en": c.get("name_en"),
             "hex": c.get("hex"), "usage": c.get("usage"), "role": c.get("role")}
            for c in style.get("color_palette") or []
        ],
        "lighting": style.get("lighting_strategy") or {},
        "furniture_language": list(style.get("furniture_language") or []),
        "construction_focus": list(style.get("construction_considerations") or []),
        "rule": "替换材料必须记录理由；不得用替换把风格的空间逻辑改掉。",
    }


def design_intent_check(style_id: str, deviations: Sequence[str],
                        *, catalogue: Optional[Catalog] = None) -> Dict[str, Any]:
    """S7: flag where the deepening departs from the locked style's intent."""
    cat = catalogue or load_catalog()
    style = cat.load_style(style_id)
    entry = cat.get(style_id)
    checklist = style.get("quality_checklist") or []
    flagged = []
    for d in deviations:
        text = str(d)
        flagged.append({
            "deviation": text,
            "needs_owner_decision": True,
            "note": "设计意图偏差由主创裁定；涉及结构/消防/法规的须持证专业人员复核。",
        })
    return {
        "stage": "S7",
        "style_id": style_id,
        "style": entry.label,
        "deviations": flagged,
        "checklist": checklist,
        "rule": "本系统只做设计意图层核对，不提供结构与法规结论。",
    }


def comparison_data(
    style_ids: Sequence[str],
    *,
    catalogue: Optional[Catalog] = None,
) -> Dict[str, Any]:
    """S8 / 汇报: side-by-side data for two to three candidate styles."""
    cat = catalogue or load_catalog()
    rows: List[Dict[str, Any]] = []
    for sid in style_ids:
        style = cat.load_style(sid)
        entry = cat.get(sid)
        budget = style.get("budget_considerations") or {}
        lighting = style.get("lighting_strategy") or {}
        rows.append({
            "style_id": sid,
            "style": entry.label,
            "family": entry.family,
            "spatial_principles": list(style.get("spatial_principles") or [])[:3],
            "materials": [m.get("name_zh") for m in (style.get("materials") or [])][:4],
            "palette": [{"hex": c.get("hex"), "name_zh": c.get("name_zh")}
                        for c in (style.get("color_palette") or [])],
            "budget_tier": budget.get("tier", ""),
            "budget_drivers": list(budget.get("drivers") or [])[:3],
            "lighting": {
                "color_temperature_k": lighting.get("color_temperature_k"),
                "principles": list(lighting.get("principles") or [])[:2],
            },
            "incompatible": list(style.get("incompatible_elements") or [])[:3],
            "summary": (style.get("history_and_context") or {}).get("summary", ""),
        })
    return {
        "stage": "S8",
        "count": len(rows),
        "styles": rows,
        "note": "对比用于决策：写清每套的适用条件与代价，不写「两套都行」。",
    }
