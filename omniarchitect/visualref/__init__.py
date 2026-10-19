"""项目级视觉规范（`视觉.md`）的对外接口。

一句话：**把客户喜欢的审美变成后续每一张图都能读到的规则**，而且只读一个文件。

四个动作：

| 动作 | 什么时候用 | 产物 |
|---|---|---|
| `guide()` | S1 问诊、客户还没给参考 | 一段引导语（含素材库入口），不阻断流程 |
| `from_refs()` | 客户给了图片 / PDF / PPT / 文档 / 链接 | `<project>/视觉.md` |
| `theme()` | 每次画图、排版、出 PPTX | 纸色、墨色、线宽、留白、是否衬线 |
| `update()` | 客户改口味（"这套排版太普通"） | 版本 +1，只改表达不动设计 |

`视觉.md` 的机读块由 `brief.render()` 写、`brief.load()` 读。人来读的是同一份文件
的正文——所以不会出现"文档说一套、程序跑另一套"。

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from . import brief as _brief
from . import extract as _extract
from . import sources as _sources
from .brief import (CHANGE_CUES, DISCIPLINE_NOTES, FILENAME, GUIDE_TEXT, ORIGIN_CN,
                    SCHEMA, compose, detect_change, exists, guide, load, path_for,
                    render, theme, update, write)

__all__ = [
    "FILENAME", "SCHEMA", "GUIDE_TEXT", "ORIGIN_CN", "DISCIPLINE_NOTES",
    "CHANGE_CUES", "compose", "render", "write", "load", "theme", "update",
    "detect_change", "guide", "exists", "path_for",
    "from_refs", "scan_refs", "describe", "DEFAULTS",
]

#: 参考文件在项目里的默认落点
REFS_DIR = "references"


def refs_dir(project_dir: str | Path) -> Path:
    return Path(project_dir) / REFS_DIR


def scan_refs(paths: Sequence[str | Path]) -> List[Dict[str, Any]]:
    """逐个读取参考文件/目录。读不到的留在列表里，带原因。"""
    out: List[Dict[str, Any]] = []
    for p in paths:
        out.extend(_sources.scan(p))
    return out


def from_refs(project: Any, paths: Sequence[str | Path] = (), *,
              client_text: str = "", lead: str = "",
              style_labels: Sequence[str] = (),
              project_dir: str | Path | None = None,
              write_file: bool = True) -> Dict[str, Any]:
    """读参考文件 → 合成规则 → 写 `视觉.md`。返回规则本身。

    没有任何参考文件也能调用：会得到一份以专业默认值为基础的规范，
    并在 `sources` 里如实写明"客户未提供参考文件"。
    """
    refs = scan_refs(paths) if paths else []
    rules = compose(project, refs, client_text=client_text, lead=lead,
                    style_labels=style_labels)
    if write_file:
        write(rules, project, project_dir)
    return rules


def describe(project: Any, project_dir: str | Path | None = None) -> Dict[str, Any]:
    """给 CLI 与报告用的一句话摘要：有没有规范、版本、来源构成。"""
    data = load(project, project_dir)
    if not data:
        return {"present": False, "path": str(path_for(project, project_dir)),
                "note": "尚未生成视觉规范：当前按风格库与专业默认执行"}
    prov = data.get("provenance") or {}
    counts: Dict[str, int] = {}
    for v in prov.values():
        counts[str(v)] = counts.get(str(v), 0) + 1
    return {
        "present": True,
        "path": str(path_for(project, project_dir)),
        "version": data.get("version"),
        "updated_at": data.get("updated_at"),
        "tokens": data.get("tokens"),
        "by_source": counts,
        "sources": len(data.get("sources") or []),
        "banned": len(data.get("banned") or []),
    }


DEFAULTS = _extract.DEFAULTS
