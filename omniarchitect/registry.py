"""Registry: the capability catalogue, the stage model, and the design-criteria map.

The stage model itself lives in `stages.py`; this module is the reporting and
provenance layer on top of it.

Design criteria
---------------
`DESIGN_CRITERIA` records which professional judgement criteria this system
applies, at which stages, and through which capabilities. The criteria are this
system's own working position, derived from general design principles and
published engineering practice; they are documented for users in
`docs/DESIGN_CRITERIA.md`.

Every artifact this system emits carries the OmniAiLab signature (`SIGNATURE`).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence

from .paths import SKILLS
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

PROJECT_ATTRIBUTION = {
    "product": "OmniArchitect",
    "display_name": "OmniAiLab AI 建筑与室内设计总设计师",
    "skill": "omniailab-ai-architect",
    "owner": "OmniAiLab",
    "developer": "Mochiball",
    "license": "见 LICENSE",
    "homepage_cn": "https://www.omniailabx.com",
    "homepage_intl": "https://omniailab.cn",
}

# The line every emitted document ends with. Kept here so the writer, the
# workflow and the audit all reference exactly one string.
SIGNATURE = ("> © OmniAiLab ｜ 开发者：Mochiball ｜ "
             "OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— "
             "未经授权禁止复制、传播或二次分发。")

# The READMEs use the short form, as the repository front page does.
SIGNATURE_SHORT = "> © OmniAiLab ｜ 开发者：Mochiball"
SIGNATURE_SHORT_EN = "> © OmniAiLab ｜ Developer: Mochiball"

# --------------------------------------------------------------------------
# Unified front-matter. Every Markdown file in this repository opens with the
# same tail block; file-type-specific keys come first. `scripts/normalize_
# attribution.py` enforces this over the whole tree and `--check` is a test.
# 地址取自 paths（唯一来源），不在这里另写一份。
from .paths import MANUAL_CN_URL as _MANUAL_CN_URL  # noqa: E402
from .paths import REPO_URL as _REPO_URL  # noqa: E402

FRONTMATTER_TAIL: tuple = (
    ("author", "OmniAiLab"),
    ("developer", "Mochiball"),
    ("agent_created", "true"),
    ("开源仓库", _REPO_URL),
    ("操作手册", _MANUAL_CN_URL),
)


def frontmatter_block(name: str, description: str, extra: Optional[dict] = None,
                      version: str = "") -> str:
    """Build the standard front-matter block, ending with a blank line.

    Generated documents use this so their header can never drift from the rest
    of the repository — including the project version, which is read from
    `VERSION` rather than typed twice.
    """
    from .paths import project_version

    lines = [f"name: {name}", f"description: {description}"]
    for k, v in (extra or {}).items():
        lines.append(f"{k}: {v}")
    lines.append(f"version: {version or project_version()}")
    lines.extend(f"{k}: {v}" for k, v in FRONTMATTER_TAIL)
    return "---\n" + "\n".join(lines) + "\n---\n\n"


# upstream slug -> which OmniArchitect stages absorbed it, and what
DESIGN_CRITERIA: Dict[str, Dict[str, object]] = {
    "aesthetic-restraint": {
        "applies_to_stages": ["S2", "S3", "S4"],
        "applies_to_capabilities": ["concept-design", "space-planning",
                                    "interior-design", "material-design"],
        "criteria": [
            "冷暖对峙：冷调打底，暖色点睛，暖材占比 ≤40%；",
            "全场只留一条主导线，天花是第一叙事面；",
            "黑作重音不作块面，占比控制在 3–8%；",
            "同一纹理给出三种密度，避免整面同质；",
            "每个标高至少一处发光的面，光要有落点；",
            "概念四步：锚 → 象 → 法 → 形；",
            "平面四问：好采光面是否被独立房间独占、客户流线是否穿过私密区、"
            "平面上是否有真实主导线、是否留出一个『空的地方』；",
            "意向板六格结构与 60-30-10 配色校验。",
        ],
        "lands_in": "S2 概念方案（意向板与概念自检）、S3 平面评审、S4 材料与色彩体系",
        "out_of_scope": "具体业主信息、第三方实拍图与商业报价表，不进入本系统资产。",
    },
    "concept-diagram-language": {
        "applies_to_stages": ["S2", "S4", "S7"],
        "applies_to_capabilities": ["create-draw", "concept-design", "construction-detailing"],
        "criteria": [
            "批注色彩语义：红=问题与张力、蓝=方向动线与视线、橙=光的动作、绿=亮点、灰=参考；",
            "概念图解三段式：概念主张 + 空间原型 + 光/材质/动线三策略；",
            "图主文辅：图上标签 ≤12 字，说明栏每条 ≤30 字。",
        ],
        "lands_in": "S2 概念图解、S4 立面做法批注、S7 图纸会审表达",
        "out_of_scope": "绘图库源码；图形由本项目自有的绘图基元生成。",
    },
    "moodboard-iteration": {
        "applies_to_stages": ["S2", "S5"],
        "applies_to_capabilities": ["moodboard-aesthetic-iteration", "scene-rendering"],
        "criteria": [
            "意向板 → 关键词三组 → 量化打分 → 跨轮整改追踪的迭代闭环；",
            "200ms 第一印象 + Design Critic 六维 + 60-30-10 拆色诊断；",
            "口径固定：同一项目内评分体系不得中途更换。",
        ],
        "lands_in": "S2 意向板骨架与评分口径、S5 效果图质量门",
        "out_of_scope": "文档排版渲染脚本；本系统自有 PPTX 与 HTML 写出。",
    },
    "building-services-impact": {
        "applies_to_stages": ["S4", "S6", "S7"],
        "applies_to_capabilities": ["building-services", "coordination-check"],
        "criteria": [
            "暖通 / 给排水 / 电气 / 竖向交通 / 消防对空间的影响速查；",
            "机房、管井、净高与吊顶空间占用的判断口径。",
        ],
        "lands_in": "S4 机电初步协调、S6 专业协调清单、S7 点位图",
        "out_of_scope": "具体地区规范条文（须由持证专业人员在项目所在地复核）。",
    },
    "annotation-ledger": {
        "applies_to_stages": ["S6", "S7", "S8"],
        "applies_to_capabilities": ["delivery", "design-review"],
        "criteria": [
            "逐条核销的批注台账机制：跨轮 ledger、问题闭环；",
            "主文档 + 意见 → 批注版交付物的流程约定。",
        ],
        "lands_in": "变更影响分析的数据结构（ChangeEntry + 失效重算 + 跨轮追踪）",
        "out_of_scope": "外部 PDF 批注脚本；批注以结构化 JSON 与本系统自有渲染输出。",
    },
    "proposal-layout": {
        "applies_to_stages": ["S8"],
        "applies_to_capabilities": ["documentation", "design-presentation"],
        "criteria": ["A3 横版设计提案的网格版式与交付文本规范"],
        "lands_in": "S8 交付文档与提案的版式约定",
        "out_of_scope": "外部排版样式文件与样张。",
    },
    "project-fit": {
        "applies_to_stages": ["S1"],
        "applies_to_capabilities": ["design-brief"],
        "criteria": ["能力边界与造价档位匹配的判据（项目该不该接、能不能做）"],
        "lands_in": "S1 任务书阶段的可行性判断；不参与设计生成",
        "out_of_scope": "企业内部资质模板与业主档案。",
    },
    "cost-separation": {
        "applies_to_stages": ["S1", "S8"],
        "applies_to_capabilities": ["cost-check", "quantity-takeoff"],
        "criteria": ["量价分离的估算口径：工程量与单价分开记录，便于逐项校准"],
        "lands_in": "S1 前期估算与 S8 正式清单的口径统一",
        "out_of_scope": "竞价博弈模型；本系统只做方案阶段估算，不出结算文件。",
    },
    "tool-safety-tiers": {
        "applies_to_stages": [],
        "applies_to_capabilities": [],
        "criteria": ["L1–L4 工具安全分级（只读 / 本地写 / 联网 / 执行发送）"],
        "lands_in": "适配器能力声明与人工审核门槛的定级依据",
        "out_of_scope": "外部扫描器。",
    },
}


def criteria_report() -> Dict[str, object]:
    touched = sorted({
        s for v in DESIGN_CRITERIA.values() for s in v["applies_to_stages"]  # type: ignore[union-attr]
    })
    return {
        "attribution": PROJECT_ATTRIBUTION,
        "signature": SIGNATURE,
        "criteria": DESIGN_CRITERIA,
        "summary": {
            "criteria_sets": len(DESIGN_CRITERIA),
            "stages_touched": touched,
            "capabilities_touched": sorted({
                c for v in DESIGN_CRITERIA.values()
                for c in v["applies_to_capabilities"]  # type: ignore[union-attr]
            }),
            "not_applied": [k for k, v in DESIGN_CRITERIA.items() if not v["applies_to_stages"]],
            "note": "判据为本系统自有口径，源自通用设计原理与公开工程惯例；"
                    "说明见 docs/DESIGN_CRITERIA.md。",
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
    brief_file: str = ""
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
            "brief_file": self.brief_file,
            "legacy_file": self.legacy_file,
            "version": self.version,
            "responsibility": self.responsibility,
        }


def load_registry(skills_dir: Path | None = None) -> List[CapabilityRecord]:
    """Capability records, joined with the specialist brief on disk when present.

    说明文件的权威位置是 `skills/<slug>.md`——文件名就是能力名，所以
    「我要 `ergonomics` 这项能力」可以直接定位到文件，不需要中间映射表。
    `legacy` 只记录 v1.0 的编号文件名（历史），此时文件已并入 slug 文件。
    """
    d = skills_dir or SKILLS
    out: List[CapabilityRecord] = []
    for cap in CAPABILITIES:
        rec = CapabilityRecord(
            slug=cap.slug, name=cap.name, stages=list(cap.stages), source=cap.source,
            legacy=cap.legacy, responsibility=cap.responsibility,
        )
        brief = d / f"{cap.slug}.md"
        if brief.exists():
            rec.brief_file = str(brief.relative_to(d.parent))
            rec.version = _frontmatter(brief.read_text(encoding="utf-8")).get("version", "")
        if cap.legacy:
            p = d / f"{cap.legacy}.md"
            if p.exists():
                rec.legacy_file = str(p.relative_to(d.parent))
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
        "attribution": PROJECT_ATTRIBUTION,
    }


def capability(slug: str) -> Optional[CapabilityRecord]:
    for r in load_registry():
        if r.slug == slug:
            return r
    return None


__all__ = [
    "PROJECT_ATTRIBUTION", "SIGNATURE", "SIGNATURE_SHORT", "SIGNATURE_SHORT_EN",
    "FRONTMATTER_TAIL", "frontmatter_block",
    "DESIGN_CRITERIA", "criteria_report",
    "load_registry", "registry_report", "capability",
    "catalog_report", "validate_catalog", "skills_for_stage", "stages_for_skill",
    "capabilities_for_stage", "STAGES", "STAGE_ORDER", "CAPABILITIES",
    "CAPABILITY_BY_SLUG", "GUARDRAILS", "legacy_map",
]
