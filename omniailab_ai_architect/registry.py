"""Registry: the capability catalogue, the stage model, and the third-party
fusion map with the attribution its licence requires.

The stage model itself lives in `stages.py`; this module is the reporting and
provenance layer on top of it.

Attribution for third-party material
------------------------------------
Upstream project: arch-skills (https://github.com/gujun1502/arch-skills)
Author: Gu Jun · https://arch-skills.com · https://www.chodo.ai
Licence: code MIT · documentation (SKILL.md, references/, templates/) CC BY 4.0.

Only methodology and knowledge were absorbed into the runtime. No upstream
source file is redistributed inside the code path; the full upstream material
is vendored unmodified at `third_party/arch-skills/` with its own LICENSE files
intact. Any deliverable that uses an absorbed judgement criterion carries the
attribution inline as well as here.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence

from .paths import ARCH_SKILLS, SKILLS
from .stages import (
    CAPABILITIES,
    CAPABILITY_BY_SLUG,
    GUARDRAILS,
    STAGE_ORDER,
    STAGES,
    capabilities_for_stage,
    catalog_report,
    legacy_map,
    skills_for_stage,
    stages_for_skill,
    validate_catalog,
)

ARCH_ATTRIBUTION = {
    "project": "arch-skills",
    "url": "https://github.com/gujun1502/arch-skills",
    "author": "Gu Jun",
    "author_url": "https://www.chodo.ai",
    "homepage": "https://arch-skills.com",
    "license": "MIT (code) · CC BY 4.0 (documentation)",
    "attribution_line": "Gu Jun / arch-skills.com",
    "vendored_at": "third_party/arch-skills",
    "note": "只吸收方法论与判据；未在运行时代码路径中分发上游源文件。",
}

# upstream slug -> which OmniArchitect stages absorbed it, and what
ARCH_FUSION: Dict[str, Dict[str, object]] = {
    "asset-management-interior": {
        "absorbed_into_stages": ["S2", "S3", "S4"],
        "absorbed_by_capabilities": ["concept-design", "space-planning",
                                     "interior-design", "material-design"],
        "absorbed": [
            "克制美学宪章：冷底暖眼 / 一条主导线定全场 / 天花是第一叙事面 / 黑是重音不是块面 / "
            "一个纹理三种密度 / 每层至少一处发光的面",
            "概念四步引擎：锚 → 象 → 法 → 形",
            "平面判据：好采光面是否被独立房间独占、客户流线是否穿过私密区、"
            "平面上是否有真实主导线、是否留出一个『空的地方』",
            "Moodboard 六格意象结构与暖材 ≤40%、黑 3–8% 的配比规则",
        ],
        "lands_in": "S2 概念方案（意向板与概念自检）、S3 平面评审、S4 材料与色彩体系",
        "not_absorbed": "具体业主信息、案例实拍图、品牌报价表",
    },
    "create-draw": {
        "absorbed_into_stages": ["S2", "S4", "S7"],
        "absorbed_by_capabilities": ["create-draw", "concept-design", "construction-detailing"],
        "absorbed": [
            "红蓝笔图形语义：红=问题/张力、蓝=方向/动线/视线、橙=光的动作、绿=亮点、灰=参考",
            "概念图解的表达方式：概念主张 + 空间原型 + 光/材质/动线三策略",
            "图主文辅纪律：图上标签 ≤12 字，说明栏每条 ≤30 字",
        ],
        "lands_in": "S2 概念图解、S4 立面做法批注、S7 图纸会审表达",
        "not_absorbed": "drawkit.py 绘图库与其 SVG 坐标脚本（未进入运行时代码路径）",
    },
    "moodboard-aesthetic-iteration": {
        "absorbed_into_stages": ["S2", "S5"],
        "absorbed_by_capabilities": ["moodboard-aesthetic-iteration", "scene-rendering"],
        "absorbed": [
            "意向板 → 关键词三组 → 量化打分 → 跨轮整改追踪的迭代闭环",
            "200ms 第一印象 + Design Critic 六维 + Color Harmony 60-30-10 诊断框架",
            "口径固定原则：同一项目内评分体系不可中途更换",
        ],
        "lands_in": "S2 意向板骨架与评分口径、S5 效果图质量门",
        "not_absorbed": "md_to_pdf.py 渲染脚本与其 PDF 模板",
    },
    "building-services-electrical": {
        "absorbed_into_stages": ["S4", "S6", "S7"],
        "absorbed_by_capabilities": ["building-services", "coordination-check"],
        "absorbed": [
            "HVAC / 给排水 / 电气 / 竖向交通 / 消防对空间的影响速查",
            "机房、管井、净高与吊顶空间占用的判断口径",
        ],
        "lands_in": "S4 机电初步协调、S6 专业协调清单、S7 点位图",
        "not_absorbed": "具体地区规范条文（须由持证专业人员在项目所在地复核）",
    },
    "red-blue-pen-annotation": {
        "absorbed_into_stages": ["S6", "S7", "S8"],
        "absorbed_by_capabilities": ["delivery", "design-review"],
        "absorbed": [
            "逐条核销的批注台账机制（跨轮 ledger、问题闭环）",
            "主文档 + 意见 → 批注版交付物的流程约定",
        ],
        "lands_in": "变更影响分析的数据结构（ChangeEntry + 失效重算 + 跨轮追踪）",
        "not_absorbed": "annotate.py / extract_pdf.py 等 PDF 处理脚本",
    },
    "design-text-typst": {
        "absorbed_into_stages": ["S8"],
        "absorbed_by_capabilities": ["documentation"],
        "absorbed": ["A3 横版设计提案的网格版式与交付文本规范"],
        "lands_in": "S8 交付文档的版式约定",
        "not_absorbed": "Typst 样式文件与样张",
    },
    "tender-bid-review": {
        "absorbed_into_stages": ["S1"],
        "absorbed_by_capabilities": ["design-brief"],
        "absorbed": ["能力边界与造价档位匹配的判据（项目该不该接、能不能做）"],
        "lands_in": "S1 任务书阶段的可行性判断；不参与设计生成",
        "not_absorbed": "company-profile 模板与业主档案（含企业隐私）",
    },
    "bid-pricing-engine": {
        "absorbed_into_stages": ["S1", "S8"],
        "absorbed_by_capabilities": ["cost-check", "quantity-takeoff"],
        "absorbed": ["量价分离的估算口径"],
        "lands_in": "S1 前期估算与 S8 正式清单的口径统一",
        "not_absorbed": "蒙特卡洛投标竞价引擎（jsx）与其博弈模型",
    },
    "skill-safety-audit": {
        "absorbed_into_stages": [],
        "absorbed_by_capabilities": [],
        "absorbed": ["L1–L4 安全等级分类法（只读 / 本地写 / 联网 / 执行发送）"],
        "lands_in": "适配器能力声明与人工审核门槛的定级依据",
        "not_absorbed": "audit.py 扫描器",
    },
    "article-academic": {
        "absorbed_into_stages": [],
        "absorbed_by_capabilities": [],
        "absorbed": [],
        "lands_in": "未纳入：属内容创作能力，与设计生产链无关",
        "not_absorbed": "全部",
    },
}


def fusion_report() -> Dict[str, object]:
    absorbed_stages = sorted({
        s for v in ARCH_FUSION.values() for s in v["absorbed_into_stages"]  # type: ignore[union-attr]
    })
    return {
        "attribution": ARCH_ATTRIBUTION,
        "map": ARCH_FUSION,
        "summary": {
            "upstream_skills": len(ARCH_FUSION),
            "stages_touched": absorbed_stages,
            "capabilities_touched": sorted({
                c for v in ARCH_FUSION.values()
                for c in v["absorbed_by_capabilities"]  # type: ignore[union-attr]
            }),
            "declined": [k for k, v in ARCH_FUSION.items() if not v["absorbed_into_stages"]],
        },
    }


FRONTMATTER = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.S)


def _frontmatter(text: str) -> Dict[str, str]:
    m = FRONTMATTER.match(text)
    if not m:
        return {}
    out: Dict[str, str] = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            out[k.strip()] = v.strip()
    return out


@dataclass
class CapabilityRecord:
    slug: str
    name: str
    stages: List[str]
    source: str
    legacy: str
    legacy_file: str = ""
    version: str = ""
    responsibility: str = ""

    def to_dict(self) -> Dict[str, object]:
        return {
            "slug": self.slug,
            "name": self.name,
            "stages": list(self.stages),
            "source": self.source,
            "legacy": self.legacy,
            "legacy_file": self.legacy_file,
            "version": self.version,
            "responsibility": self.responsibility,
        }


def load_registry(skills_dir: Path | None = None) -> List[CapabilityRecord]:
    d = skills_dir or SKILLS
    out: List[CapabilityRecord] = []
    for cap in CAPABILITIES:
        rec = CapabilityRecord(
            slug=cap.slug, name=cap.name, stages=list(cap.stages), source=cap.source,
            legacy=cap.legacy, responsibility=cap.responsibility,
        )
        if cap.legacy:
            p = d / f"{cap.legacy}.md"
            if p.exists():
                rec.legacy_file = str(p.relative_to(d.parent))
                rec.version = _frontmatter(p.read_text(encoding="utf-8")).get("version", "")
        out.append(rec)
    return out


def registry_report() -> Dict[str, object]:
    records = load_registry()
    return {
        "stage_count": len(STAGES),
        "capability_count": len(CAPABILITIES),
        "stages": [s.to_dict() for s in STAGES],
        "capabilities": [r.to_dict() for r in records],
        "legacy_coverage": legacy_map(),
        "guardrails": GUARDRAILS,
        "catalog_issues": validate_catalog(),
        "attribution": ARCH_ATTRIBUTION,
    }


def capability(slug: str) -> Optional[CapabilityRecord]:
    for r in load_registry():
        if r.slug == slug:
            return r
    return None


def arch_skills_present() -> bool:
    return ARCH_SKILLS.exists() and (ARCH_SKILLS / "README.md").exists()


__all__ = [
    "ARCH_ATTRIBUTION", "ARCH_FUSION", "fusion_report",
    "load_registry", "registry_report", "capability", "arch_skills_present",
    "catalog_report", "validate_catalog", "skills_for_stage", "stages_for_skill",
    "capabilities_for_stage", "STAGES", "STAGE_ORDER", "CAPABILITIES",
    "CAPABILITY_BY_SLUG", "GUARDRAILS", "legacy_map",
]
