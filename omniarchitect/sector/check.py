"""G3 的专业核验：不只看"有没有生成文件"，要看"有没有设计数据"。

三件事：

1. **有数据才算方案**。只有任务清单、没有房间/分区数据的项目，不能标成
   "专业方案已完成"——那就把 G3 变成了文件存在性检查。
2. **类型限制要进条件**。医院的手术部、学校的办学标准、厂房的工艺，
   本系统只做关系与任务梳理；这些以"条件"形式留在门禁结论里，不当通过。
3. **建议轮廓要复原**。按任务书反算的轮廓是设计起点，不是实测；
   签发前必须写明"须按实测与建筑条件复核"。

这里不改 G3 的判据，只在既有判据上补一段**按专业与类型**的核验。

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

from typing import Any, Dict, List, Sequence

#: 各行业"算有设计数据"的最低要求：房间数或分区数。
MIN_DESIGN_UNITS = {
    "education": 6, "healthcare": 6, "industrial": 3, "hospitality": 6,
    "landscape": 3,
}


def assess(project: Any, record: Dict[str, Any],
           active: Sequence[str] = ()) -> Dict[str, List[Dict[str, str]]]:
    """返回 {blockers, conditions}。record 是 S3 写下的平面记录。"""
    blockers: List[Dict[str, str]] = []
    conditions: List[Dict[str, str]] = []
    if not record:
        return {"blockers": blockers, "conditions": conditions}

    from .. import taxonomy as _tx

    sector = str(record.get("sector") or "")
    data = dict(record.get("design_data") or {})
    rooms = int(record.get("rooms") or 0)
    need = MIN_DESIGN_UNITS.get(sector, 0)

    # 1) 行业项目必须有设计数据
    if need and rooms < need:
        blockers.append({
            "id": "G3-NO-DESIGN-DATA",
            "text": (f"本项目是{sector}类，但本轮只有 {rooms} 个单位的设计数据"
                     f"（至少需要 {need}）：任务清单不是专业方案，不能签发 G3"),
        })

    # 1b) 景观：分区是"按占比试排"，不是测绘图
    if sector == "landscape" and rooms:
        conditions.append({
            "id": "G3-LANDSCAPE-SCHEMATIC",
            "text": ("景观分区按场地面积与占比试排：水形、岸线、竖向与放线须现场实测后另出，"
                     "本图的占比只能用于讨论，不能作为施工依据"),
        })

    # 2) 建议轮廓：可以推进，但必须复核
    if data.get("proposed_envelope"):
        env = data.get("envelope") or {}
        conditions.append({
            "id": "G3-PROPOSED-ENVELOPE",
            "text": (f"平面轮廓是按任务书反算的建议轮廓（约 "
                     f"{float(env.get('area_m2') or 0):,.0f} m²，"
                     f"{float(env.get('width_mm') or 0) / 1000:.1f} × "
                     f"{float(env.get('depth_mm') or 0) / 1000:.1f} m）："
                     "签发前须用实测/建筑条件复核，复核后重出平面"),
        })

    # 3) 类型的专业限制：从 taxonomy 的能力档位来
    codes = [str(c) for c in (data.get("codes") or [])]
    cap = _tx.capability_of(codes) if codes else {}
    if cap.get("level") == "specialist":
        conditions.append({
            "id": "G3-SPECIALIST-REVIEW",
            "text": (f"{cap.get('label')}：{cap.get('note')}——"
                     "本系统给的是功能关系与任务梳理，不是该专业的合规成果"),
        })
    elif cap.get("level") == "concept_only":
        conditions.append({
            "id": "G3-CONCEPT-ONLY",
            "text": ("本类型目前到概念与关系深度："
                     + (cap.get("note") or "方案可讨论，不能当施工或报建依据")),
        })

    # 4) 缺关键输入：本轮是按假设排的，必须写明
    missing = list(data.get("missing_inputs") or [])
    if missing:
        conditions.append({
            "id": "G3-MISSING-INPUT",
            "text": "本轮缺关键输入，按假设推进：" + "；".join(missing[:3]),
        })

    return {"blockers": blockers, "conditions": conditions}


__all__ = ["MIN_DESIGN_UNITS", "assess"]
