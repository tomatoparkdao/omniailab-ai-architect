"""G3 的专业核验：不只看"有没有生成文件"，要看"有没有设计数据、站在什么几何上"。

四件事：

1. **有数据才算方案**。只有任务清单、没有房间/分区数据的项目，不能标成
   "专业方案已完成"——那就把 G3 变成了文件存在性检查。
2. **几何依据分四档**。实测 / 已有图纸 / 业主估算 / 系统建议。前两档可以撑起
   正式确认（图纸仍须现场核对）；后两档只能做探索。把建议轮廓说成"已核实"，
   是这类系统最容易犯的错。
3. **关键前提与条件项分开**。缺工艺顺序、缺日门诊量这类输入会改变房间数量与
   面积，属于关键前提；"专项顾问复核""实测放线"属于条件项——记录在案，
   不阻断讨论，但也不能被写成"已通过"。
4. **功能类别要齐**。房间数达标不等于功能正确：医院没有医技、学校没有专用
   教室、厂房没有仓储，都不成立。这一项与"概念结构是否落地"一起，构成
   功能与流线的可判定部分。

这里不改 G3 的判据结构，只把"专业核验"这一段的结论分档输出。

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

from typing import Any, Dict, List, Sequence

#: 各行业"算有设计数据"的最低要求：房间数或分区数。
MIN_DESIGN_UNITS = {
    "education": 6, "healthcare": 6, "industrial": 3, "hospitality": 6,
    "landscape": 3,
}

#: 各行业必须具备的功能类别：中文名 → 可接受的 `space.use`（同一功能常有多种写法）。
#: 医技在平面上是 `lab`/`tech`，仓储在厂房里是 `storage`，后场是 `storage`——
#: 只认一个字符串会把真做了的方案判成缺项，也会把"改 tag 就过关"变成漏洞。
REQUIRED_USES: Dict[str, Dict[str, tuple]] = {
    "education": {"普通教室": ("teaching",), "专用教室": ("study",),
                  "教师办公": ("office",), "卫生间": ("bathroom",)},
    "healthcare": {"诊室": ("diagnosis",), "医技": ("tech", "lab"),
                   "候诊": ("public", "waiting"), "公共卫生间": ("bathroom",)},
    "industrial": {"生产区": ("production",), "仓储": ("warehouse", "storage"),
                   "办公/更衣": ("office",)},
    "hospitality": {"客房": ("guest",), "后场": ("boh", "storage", "service")},
    "landscape": {"绿地与种植": ("planting",), "铺装": ("paving",)},
}

#: 关键输入：缺了会改变房间数量或面积，属于"关键前提"，不是"待完善"。
CRITICAL_INPUTS = {
    "education": ("班数", "学生人数"),
    "healthcare": ("床位规模", "日门诊量"),
    "industrial": ("生产工艺顺序", "柱网与设备尺寸"),
    "hospitality": ("客房数",),
    "landscape": ("场地面积",),
}

#: 必须由持证专业/顾问确认的内容。写进条件，不当作已验证。
CONSULTANT = {
    "education": "办学规模与专用教室配置标准、消防疏散与校车接送组织",
    "healthcare": "医疗工艺（手术部/ICU/负压/洁污流程）、院感与医用气体",
    "industrial": "工艺设备基础与动力管沟、火灾危险性分类与消防设施",
    "hospitality": "厨房排烟隔油与燃气、消防疏散与客房隔声",
    "landscape": "结构（挡土/驳岸）、给排水与苗木规格",
}


def assess(project: Any, record: Dict[str, Any],
           active: Sequence[str] = ()) -> Dict[str, Any]:
    """返回 {blockers, critical, conditions}。

    * blockers —— 连"有设计数据"都不成立，S3 成果不能提交；
    * critical —— 关键前提未满足：方案可以讨论，不能声称已核实通过；
    * conditions —— 记录在案的条件项，不阻断确认。
    """
    blockers: List[Dict[str, str]] = []
    critical: List[Dict[str, str]] = []
    conditions: List[Dict[str, str]] = []
    if not record:
        return {"blockers": blockers, "critical": critical, "conditions": conditions}

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

    # 1b) 功能类别：数够不等于功能对
    # 旧记录（v1.12 及以前）没有 categories 字段：不做追溯指责，保持已签项目兼容。
    cats = {str(x) for x in (data.get("categories") or [])}
    req = REQUIRED_USES.get(sector) or {}
    lacking = [label for label, uses in req.items()
               if not (set(uses) & cats)] if ("categories" in data and req) else []
    if req and lacking:
        critical.append({
            "id": "G3-FUNCTION-INCOMPLETE",
            "text": ("本类型缺少必需功能：" + "、".join(lacking)
                     + "——房间数量达标不等于功能完整，须补齐后重排"),
        })
    elif req and "categories" in data:
        conditions.append({
            "id": "G3-FUNCTION-COVERED",
            "text": "必需功能类别已齐：" + "、".join(req.keys())
                    + "（数量与位置另见概念结构校核）",
        })

    # 2) 几何依据：四档分开，别把假设说成实测
    basis = str(data.get("geometry_basis") or "")
    bnote = str(data.get("geometry_note") or "")
    size = data.get("envelope") or {}
    _area = float(size.get("area_m2") or 0)
    _w = float(size.get("width_mm") or 0)
    _d = float(size.get("depth_mm") or 0)
    dims = (f"约 {_area:,.0f} m²"
            + (f"，{_w / 1000:.1f} × {_d / 1000:.1f} m" if _w and _d
               else "（只有面积，没有边界坐标）"))
    if basis == "proposed" or data.get("proposed_envelope"):
        critical.append({
            "id": "G3-PROPOSED-ENVELOPE",
            "text": (f"平面轮廓是按任务书反算的建议轮廓（{dims}），不是实测或已出图边界："
                     "本轮只能作为方案探索，正式 G3 须先用实测/建筑条件复核并重出平面"),
        })
    elif basis == "client":
        critical.append({
            "id": "G3-ESTIMATED-ENVELOPE",
            "text": (f"平面/分区依据业主提供的估算范围（{dims}）：估算不等于实测，"
                     "不能作为正式确认的几何依据"),
        })
    elif basis == "drawing":
        conditions.append({
            "id": "G3-DRAWING-ENVELOPE",
            "text": (f"平面依据已有图纸边界（{dims}）：可作设计依据，"
                     "但图纸标注不等于现场实测，签发后仍须现场核对；" + bnote),
        })
    elif basis == "surveyed":
        conditions.append({
            "id": "G3-SURVEYED-ENVELOPE",
            "text": f"平面依据实测边界（{dims}）——几何来源已核实",
        })

    # 3) 缺关键输入：分"会改变设计"和"待完善"两档
    missing = [str(x) for x in (data.get("missing_inputs") or [])]
    key_terms = CRITICAL_INPUTS.get(sector, ())
    hard = [m for m in missing if any(t in m for t in key_terms)]
    soft = [m for m in missing if m not in hard]
    if hard:
        critical.append({
            "id": "G3-MISSING-INPUT",
            "text": ("缺会改变设计的输入，本轮按假设推进：" + "；".join(hard[:3])
                     + "——补齐后须重算房间数量与面积，当前结果不能作为确认依据"),
        })
    if soft:
        conditions.append({
            "id": "G3-MISSING-INPUT-MINOR",
            "text": "待完善（不影响本轮确认深度）：" + "；".join(soft[:3]),
        })

    # 4) 由假设推出的数：标明，不当成客户给定的条件
    assumed = [str(x) for x in (data.get("assumptions") or [])]
    if assumed:
        conditions.append({
            "id": "G3-ASSUMPTION-USED",
            "text": "本轮用到系统暂定的假设（结果随假设变化，不是现行规范强制值）："
                    + "；".join(assumed[:4]),
        })

    # 5) 类型的专业限制：从 taxonomy 的能力档位来
    codes = [str(c) for c in (data.get("codes") or [])]
    cap = _tx.capability_of(codes) if codes else {}
    consultant = CONSULTANT.get(sector, "")
    if cap.get("level") == "specialist":
        conditions.append({
            "id": "G3-SPECIALIST-REVIEW",
            "text": (f"{cap.get('label')}：{cap.get('note')}——"
                     "本系统给的是功能关系与任务梳理，不是该专业的合规成果"
                     + (f"；须顾问确认：{consultant}" if consultant else "")),
        })
    elif cap.get("level") == "concept_only":
        conditions.append({
            "id": "G3-CONCEPT-ONLY",
            "text": ("本类型目前到概念与关系深度："
                     + (cap.get("note") or "方案可讨论，不能当施工或报建依据")),
        })
    elif consultant:
        conditions.append({
            "id": "G3-CONSULTANT-SCOPE",
            "text": f"已验证：功能分区、房间关系、交通组织；依赖专业顾问：{consultant}",
        })

    # 6) 景观：分区是"按占比试排"，不是测绘图
    if sector == "landscape" and rooms:
        conditions.append({
            "id": "G3-LANDSCAPE-SCHEMATIC",
            "text": ("景观分区按场地面积与占比试排：水形、岸线、竖向与放线须现场实测后另出，"
                     "本图的占比只能用于讨论，不能作为施工依据"),
        })

    # 7) 概念结构：S3 已逐条判过；这里只把"未落实"转成门禁语言
    struct = list(record.get("structures") or [])
    if struct:
        ok = [str(x.get("label")) for x in struct if x.get("ok")]
        bad = [str(x.get("label")) for x in struct if not x.get("ok") and x.get("critical")]
        if ok:
            conditions.append({
                "id": "G3-STRUCTURE-CHECKED",
                "text": "以下空间结构已在图上核对成立：" + "、".join(ok[:6]),
            })
        if bad:
            critical.append({
                "id": "G3-CONCEPT-STRUCTURE",
                "text": "概念要求的结构未在图上成立：" + "、".join(bad[:4]),
            })

    return {"blockers": blockers, "critical": critical, "conditions": conditions}


__all__ = ["CONSULTANT", "CRITICAL_INPUTS", "MIN_DESIGN_UNITS", "REQUIRED_USES", "assess"]
