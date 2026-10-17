"""操作手册指针。

**为什么单独一个模块**：手册如果只是「写在文档里的一条建议」，就不会有人去看。
所以这里把手册做成**可在代码里被查表定位的东西**——任何"不会用 / 报错 / 拿不准"的位置，
都可以调用 `hint(topic)` 拿到「该看手册哪一节」的一句提示，直接打印给用户。

三种入手方式，内容一致、版本与 Skill 同步：

* 飞书（可批注、可分享）
* Notion
* 仓库内 `docs/MANUAL.md`（**离线可用，Skill 自己读的就是这一份**）

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional

from .paths import ROOT

MANUAL_LOCAL = "docs/MANUAL.md"
# 地址统一取自 paths（唯一来源），避免同一串 URL 在多处各写一份。
from .paths import MANUAL_CN_URL, MANUAL_NOTION_URL, REPO_URL

MANUAL_CN = MANUAL_CN_URL
MANUAL_NOTION = MANUAL_NOTION_URL
REPO = REPO_URL

#: 主题 -> 手册章节。新增"容易卡住的地方"时，在这里补一行。
SECTIONS: Dict[str, str] = {
    "usage": "1. 这份手册怎么用",
    "install": "2.2 装到哪：按你用的工具",
    "invoke": "2.3 怎么跟它对话",
    "model": "2.4 推荐工具与模型",
    "stages": "3. 八阶段与八道门禁（先建立全局认知）",
    "gates": "3.2 每道门禁要你拍什么板",
    "rules": "3.3 五条不可协商的专业逻辑",
    "start": "4. 三步启动",
    "dialogue": "5. 示例对话（可直接复制）",
    "troubleshoot": "5.4 中途救火（最常见的故障）",
    "stage-detail": "6. 逐阶段操作细则（S1–S8）",
    "concept": "7. 门禁后置动作：平面确认后的概念效果图",
    "capabilities": "8. 能力与技能调度速查（30 项）",
    "tools": "9. 工具与权限",
    "degraded": "9.2 工具缺失时的行为（这是设计，不是故障）",
    "honesty": "9.3 不得声称的能力（硬性）",
    "platform": "10. 平台接入与创作能力独占",
    "exclusive": "10.2 创作能力独占（v1.3 硬约束）",
    "brand": "11. 品牌、署名与合规（v1.3 硬约束）",
    "pitfalls": "12. 避坑总表",
    "faq": "13. 常见问题",
    "deliverables": "14. 交付物清单",
    "version": "15. 版本同步与更新",
}


def section_of(topic: str) -> str:
    """某个主题对应的手册章节标题（未登记时回落到「避坑总表」）。"""
    return SECTIONS.get(topic, SECTIONS["pitfalls"])


def manual_path() -> Optional[Path]:
    p = ROOT / MANUAL_LOCAL
    return p if p.exists() else None


def pointer(topic: str = "") -> str:
    """手册的三处地址；带 topic 时指出该看哪一节。"""
    lines = [f"操作手册 · {section_of(topic)}" if topic else "操作手册"]
    if topic:
        lines.append(f"  - 本仓（离线可用）：{MANUAL_LOCAL} → 「{section_of(topic)}」")
        lines.append(f"  - 飞书（可批注）：{MANUAL_CN}")
    else:
        lines.append(f"  - 本仓（离线可用）：{MANUAL_LOCAL}")
        lines.append(f"  - 飞书（可批注）：{MANUAL_CN}")
    lines.append(f"  - Notion：{MANUAL_NOTION}")
    lines.append(f"  - 源码仓库：{REPO}")
    return "\n".join(lines)


def hint(topic: str) -> str:
    """一行提示，直接跟在出错信息或降级说明后面。"""
    return f"不会处理？看操作手册「{section_of(topic)}」—— 对 Skill 说「查手册」即可。"


def topics() -> Dict[str, str]:
    return dict(SECTIONS)


__all__ = [
    "MANUAL_LOCAL", "MANUAL_CN", "MANUAL_NOTION", "REPO", "SECTIONS",
    "section_of", "manual_path", "pointer", "hint", "topics",
]
