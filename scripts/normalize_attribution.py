#!/usr/bin/env python
"""统一全仓文件的「开头 + 结尾」格式（幂等，可反复运行）。

统一格式
--------
**Markdown 开头**：YAML front-matter，文件类型专属字段在前，标准尾部字段在后：

```
---
<文件类型专属字段：domain / name / description / capability / stages / ...>
version: 1.3.0
author: OmniAiLab
developer: Mochiball
agent_created: true
开源仓库: 待发布
操作手册: 待发布
---
```

**Markdown 结尾**：标准署名行（`registry.SIGNATURE`，唯一定义处）：

```
---
> © OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
```

**Python 开头**：模块 docstring 末尾（或文件头注释）带同一行署名。
**YAML / CMD / TXT**：文件头注释带署名。
**JSON**：用标准 `$comment` 字段携带署名（JSON 无注释，`$comment` 是规范允许的写法）。

用法
----
    python scripts/normalize_attribution.py            # 就地统一（幂等）
    python scripts/normalize_attribution.py --check    # 只报告不一致，不写文件
    python scripts/normalize_attribution.py --json

设计取舍
--------
- **只动标准尾部字段与署名**，其余字段原顺序保留，绝不重排或删除文件类型专属字段
  （`cases/*.md` 的 YAML 列表、`skills/*.md` 的 `capability`/`stages` 等必须原样保留）。
- **保留 CRLF**：本仓 Markdown 为 CRLF，不做换行符归一，避免整文件 diff 噪声。
- `--check` 供守卫测试使用，保证格式不会随时间漂移。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from omniarchitect.paths import project_version  # noqa: E402
from omniarchitect.registry import SIGNATURE  # noqa: E402

# 仓库与手册地址：唯一来源在 omniarchitect/paths.py
from omniarchitect.paths import (  # noqa: E402
    MANUAL_CN_URL,
    MANUAL_NOTION_URL,
    REPO_URL as OPEN_REPO_URL,
)

# Markdown 统一尾部：键 -> 固定值（version 由 VERSION 决定）
# 后两项就是「手册与源码就地在任何一个文件里可查」的机制：技能读到任一 .md 的
# front-matter，就能拿到操作手册与仓库地址，不需要额外配置。
TAIL_KEYS: Tuple[str, ...] = ("version", "author", "developer", "agent_created",
                              "开源仓库", "操作手册")
TAIL_FIXED: Dict[str, str] = {
    "author": "OmniAiLab",
    "developer": "Mochiball",
    "agent_created": "true",
    "开源仓库": OPEN_REPO_URL,
    "操作手册": MANUAL_CN_URL,
}

# README 是 GitHub 首页：按参考仓库（omniailab-ai-director）的做法**不加 front-matter**，
# 直接以居中的 HTML 标题开始，避免首页顶部被渲染成一张元数据表。
NO_FRONTMATTER: Tuple[str, ...] = ("README.md", "README_EN.md")

# 英文 README 用英文页脚署名（与参考仓库做法一致）；其余文件用中文标准署名。
EN_SIGNATURE_FILES: Tuple[str, ...] = ("README_EN.md",)
EN_SIGNATURE = (
    "> © OmniAiLab ｜ Developer: Mochiball ｜ OmniAiLab AI Architect for "
    "Architecture & Interior Design (omniailabx.com) — unauthorised copying, "
    "distribution and re-sharing are prohibited."
)

# Python / 注释类文件使用的署名（= SIGNATURE 去掉 Markdown 引用前缀）
ATTRIBUTION = SIGNATURE.lstrip("> ").strip()
SHORT_ATTRIBUTION = "© OmniAiLab ｜ 开发者：Mochiball"

# 没有 front-matter 的文件，补一份最小可用的（name/description 由内容推断）
MINIMAL_FM_FILES: Dict[str, Dict[str, str]] = {
    "README.md": {
        "name": "omniailab-readme",
        "description": "OmniAiLab AI 建筑与室内设计总设计师（omniailab-ai-architect）中文说明："
                       "能力概览、八阶段工作流、安装与快速开始、命令速查、品牌与合规边界。",
    },
    "README_EN.md": {
        "name": "omniailab-readme-en",
        "description": "OmniAiLab AI Architect (omniailab-ai-architect) — English README: "
                       "capability overview, eight-stage workflow, install, quick start, "
                       "command reference, brand and compliance boundaries.",
    },
    "providers/README.md": {
        "name": "omniailab-providers-readme",
        "description": "OmniAiLab 平台连接说明：API 契约填写模板、凭据放置位置、"
                       "三步接入流程，以及创作能力独占的硬规则。",
    },
}

SKIP_DIRS = {".git", "out", "__pycache__", ".pytest_cache", "node_modules",
             "build", "dist", ".venv", "venv", "_backup"}

# 运行时产物，不参与统一（它们由生成器负责格式）
GENERATED_FILES = ("docs/BRAND_POLICY.md", "docs/CONTENT_AUDIT.md",
                   "docs/brand-policy.json", "docs/content-audit.json")

# 项目数据不参与统一：统一空间模型的 schema 不接受多余字段，
# 且这些是用户项目数据，不是本仓的文档产物。
SKIP_TOP = {"projects"}

FM_RE = re.compile(r"\A(?:\ufeff)?---[ \t]*\r?\n(.*?)\r?\n---[ \t]*\r?\n", re.S)

# 表格分隔行：`|---|---|` 与 `| --- | --- |` 都是合法 Markdown，但全仓只能有一种。
# 参考仓库 tomatoparkdao/omniailab-ai-director 一律用紧凑写法，本仓统一到它。
TABLE_SEP_RE = re.compile(r"^[ \t]*\|[\s:|-]+\|[ \t]*$")


# --------------------------------------------------------------------------
def _iter(root: Path, pattern: str):
    for p in sorted(root.rglob(pattern)):
        if p.is_dir():
            continue
        parts = p.relative_to(root).parts
        if set(parts[:-1]) & SKIP_DIRS:
            continue
        if parts and parts[0] in SKIP_TOP:
            continue
        rel = str(p.relative_to(root)).replace("\\", "/")
        if rel in GENERATED_FILES:
            continue
        yield p, rel


def _normalize_tail(fm_body: str, version: str) -> str:
    """把标准尾部字段抽出来、按固定顺序追加到最后。其余字段原样保留。"""
    lines = fm_body.split("\n")
    kept: List[str] = []
    key_re = re.compile(r"^(" + "|".join(re.escape(k) for k in TAIL_KEYS) + r")[ \t]*:")
    for line in lines:
        if key_re.match(line):
            continue
        kept.append(line)
    while kept and not kept[-1].strip():
        kept.pop()
    tail = [f"version: {version}"] + [f"{k}: {v}" for k, v in TAIL_FIXED.items()]
    return "\n".join(kept + tail)


def normalize_tables(text: str, nl: str) -> Tuple[str, int]:
    """把 Markdown 表格分隔行统一成紧凑写法 `|---|---|`。

    代码块（``` / ~~~）内的内容一律不动——那里可能有示例文本。
    返回 (新文本, 改动行数)。
    """
    lines = text.split(nl)
    out: List[str] = []
    fence = ""
    changed = 0
    for line in lines:
        stripped = line.strip()
        if fence:
            out.append(line)
            if stripped.startswith(fence):
                fence = ""
            continue
        if stripped.startswith("```") or stripped.startswith("~~~"):
            fence = stripped[:3]
            out.append(line)
            continue
        if TABLE_SEP_RE.match(line):
            cols = line.count("|") - 1
            if cols >= 1:
                compact = "|" + "---|" * cols
                if compact != line:
                    changed += 1
                out.append(compact)
                continue
        out.append(line)
    return nl.join(out), changed


def normalize_markdown(path: Path, rel: str, version: str, check: bool) -> List[str]:
    raw = path.read_bytes()
    text = raw.decode("utf-8")
    nl = "\r\n" if "\r\n" in text else "\n"
    changes: List[str] = []

    m = FM_RE.match(text)
    if rel in NO_FRONTMATTER:
        # GitHub 首页不加 front-matter：已有则移除，正文原样保留。
        if m:
            body = text[m.end():]
            while body.startswith(nl):
                body = body[len(nl):]
            new_text = body
            changes.append("移除 front-matter（README 按参考仓库做法不带元数据）")
        else:
            new_text = text
    elif m:
        body = text[m.end():]
        fm_body = m.group(1).replace("\r\n", "\n").replace("\r", "\n")
        new_fm_body = _normalize_tail(fm_body, version)
        if new_fm_body != fm_body:
            changes.append("front-matter 尾部字段已归位/补全")
        new_text = f"---{nl}{new_fm_body}{nl}---{nl}{body}"
        if not body.startswith(nl):
            new_text = f"---{nl}{new_fm_body}{nl}---{nl}{nl}{body}"
    else:
        defaults = MINIMAL_FM_FILES.get(rel)
        if defaults is None:
            # 推断一个最小可用头，避免出现空字段
            slug = rel.rsplit("/", 1)[-1].replace(".md", "").replace(".", "-")
            defaults = {"name": f"omniailab-{slug}",
                        "description": f"{slug} —— OmniAiLab AI 建筑与室内设计总设计师的说明文档。"}
        fm_lines = [f"{k}: {v}" for k, v in defaults.items()]
        fm_lines += [f"version: {version}"] + [f"{k}: {v}" for k, v in TAIL_FIXED.items()]
        new_text = f"---{nl}" + nl.join(fm_lines) + f"{nl}---{nl}{nl}" + text
        changes.append("新增 front-matter")

    if rel in EN_SIGNATURE_FILES:
        # 英文 README 的页脚只留英文署名：先清掉两种署名的残留，再统一追加。
        tmp = new_text
        for sig in (SIGNATURE, EN_SIGNATURE):
            if sig in tmp:
                tmp = tmp.replace(f"---{nl}{sig}", "").replace(sig, "")
        new_text = tmp.rstrip("\r\n") + f"{nl}{nl}---{nl}{EN_SIGNATURE}{nl}"
        if new_text != text:
            changes.append("页脚统一为英文署名")
    elif SIGNATURE not in new_text:
        new_text = new_text.rstrip("\r\n") + f"{nl}{nl}---{nl}{SIGNATURE}{nl}"
        changes.append("补写结尾署名行")

    new_text, table_changes = normalize_tables(new_text, nl)
    if table_changes:
        changes.append(f"表格分隔行统一为 |---|---|（{table_changes} 行）")

    if not check and new_text != text:
        path.write_bytes(new_text.encode("utf-8"))
    return changes


def normalize_python(path: Path, check: bool) -> List[str]:
    text = path.read_text(encoding="utf-8")
    if "© OmniAiLab" in text:
        return []
    # shebang 必须留在第 1 行，不能被署名挤下去
    shebang = ""
    body = text
    if text.startswith("#!"):
        cut = text.find("\n")
        if cut != -1:
            shebang, body = text[:cut + 1], text[cut + 1:]
    m = re.match(r"(?s)\A(\ufeff?)(\"\"\"|''')(.*?)\2", body)
    if m:
        head, quote, doc = m.group(1), m.group(2), m.group(3)
        new_body = f"{head}{quote}{doc.rstrip()}\n\n{ATTRIBUTION}\n{quote}" + body[m.end():]
        change = "模块 docstring 末尾补署名"
    else:
        new_body = f"# {ATTRIBUTION}\n" + body
        change = "文件头补署名注释"
    if not check:
        path.write_text(shebang + new_body, encoding="utf-8")
    return [change]


def normalize_yaml(path: Path, check: bool) -> List[str]:
    text = path.read_text(encoding="utf-8")
    if "© OmniAiLab" in text:
        return []
    nl = "\r\n" if "\r\n" in text else "\n"
    new_text = (f"# {ATTRIBUTION}{nl}{nl}" + text.rstrip("\r\n")
                + f"{nl}{nl}# ---{nl}# {SIGNATURE.lstrip('> ')}{nl}")
    if not check:
        path.write_text(new_text, encoding="utf-8")
    return ["文件头与结尾补署名注释"]


def normalize_cmd_or_txt(path: Path, check: bool) -> List[str]:
    text = path.read_text(encoding="utf-8")
    if "© OmniAiLab" in text:
        return []
    nl = "\r\n" if "\r\n" in text else "\n"
    is_cmd = path.suffix.lower() == ".cmd"
    mark = "::" if is_cmd else "#"
    stripped = text.lstrip()
    prefix = ""
    rest = text
    if is_cmd and stripped.lower().startswith("@echo off"):
        cut = text.lower().index("@echo off") + len("@echo off")
        prefix = text[:cut] + nl
        rest = text[cut:].lstrip("\r\n")
    new_text = (prefix + f"{mark} {ATTRIBUTION}{nl}{nl}" + rest.rstrip("\r\n")
                + f"{nl}{nl}{mark} ---{nl}{mark} {SIGNATURE.lstrip('> ')}{nl}")
    if not check:
        path.write_text(new_text, encoding="utf-8")
    return ["文件头与结尾补署名"]


def normalize_json(path: Path, check: bool) -> List[str]:
    """JSON 没有注释语法，用标准 `$comment` 字段承载署名（不重排原有格式）。"""
    text = path.read_text(encoding="utf-8")
    if "© OmniAiLab" in text:
        return []
    brace = text.find("{")
    if brace == -1:
        return []
    eol = "\r\n" if "\r\n" in text else "\n"
    new_text = (text[:brace + 1]
                + f'{eol}  "$comment": "{ATTRIBUTION}",' + text[brace + 1:])
    try:
        json.loads(new_text)
    except Exception:
        return []
    if not check:
        path.write_text(new_text, encoding="utf-8")
    return ["新增 $comment 署名（JSON 无注释语法）"]


def run(check: bool = False, root: Path = ROOT) -> Dict[str, object]:
    version = project_version()
    report: Dict[str, object] = {"version": version, "changed": [], "skipped": [],
                                 "total": 0, "check": check}
    changed: List[Dict[str, str]] = []

    for p, rel in _iter(root, "*.md"):
        report["total"] = int(report["total"]) + 1
        ch = normalize_markdown(p, rel, version, check)
        if ch:
            changed.append({"path": rel, "changes": "；".join(ch)})

    for p, rel in _iter(root, "*.py"):
        report["total"] = int(report["total"]) + 1
        ch = normalize_python(p, check)
        if ch:
            changed.append({"path": rel, "changes": "；".join(ch)})

    for p, rel in _iter(root, "*.yaml"):
        report["total"] = int(report["total"]) + 1
        ch = normalize_yaml(p, check)
        if ch:
            changed.append({"path": rel, "changes": "；".join(ch)})

    for pattern in ("*.cmd", "*.txt"):
        for p, rel in _iter(root, pattern):
            report["total"] = int(report["total"]) + 1
            ch = normalize_cmd_or_txt(p, check)
            if ch:
                changed.append({"path": rel, "changes": "；".join(ch)})

    for p, rel in _iter(root, "*.json"):
        # 受 schema 严格约束的数据文件不加署名注释。
        #
        # `knowledge/styles/*.json` 由 `design-style.schema.json` 校验，而该 schema 是
        # `additionalProperties: false` —— 多一个 `$comment` 键就会让**每一条风格**校验
        # 失败。这类文件的署名在 catalog 与文档层，不在数据本身。
        if rel.startswith("knowledge/styles/"):
            continue
        report["total"] = int(report["total"]) + 1
        ch = normalize_json(p, check)
        if ch:
            changed.append({"path": rel, "changes": "；".join(ch)})

    report["changed"] = changed
    report["changed_count"] = len(changed)
    return report


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="统一全仓文件的开头与结尾署名格式")
    ap.add_argument("--check", action="store_true", help="只报告不一致，不写文件")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    rep = run(check=args.check)
    if args.json:
        print(json.dumps(rep, ensure_ascii=False, indent=2))
        return 0 if rep["changed_count"] == 0 or not args.check else 1
    print(f"统一格式{'检查' if args.check else '处理'}　项目版本 {rep['version']}"
          f"　扫描 {rep['total']} 个文件")
    for c in rep["changed"]:            # type: ignore[union-attr]
        print(f"  {'✗' if args.check else '·'} {c['path']}　{c['changes']}")
    print(f"  {'不一致' if args.check else '已处理'}：{rep['changed_count']} 个文件")
    return 0 if rep["changed_count"] == 0 or not args.check else 1


if __name__ == "__main__":
    sys.exit(main())
