#!/usr/bin/env python
"""Markdown 表格规范检查器 —— 保证 GitHub 上每张表「左右边界对齐」。

为什么需要这个检查器
--------------------
GitHub 的 Markdown 表格按 **内容宽度** 渲染（`width: max-content`），
源码里没有任何语法可以指定表格宽度。于是同一个页面里会出现：

* 内容饱满的表 → 撑满正文区，左右边界贴着内容区边缘；
* 内容偏少的表 → 只占正文区一半，右边界缩进一大截。

肉眼看就是「表格左右不齐」。唯一的解法是**把内容宽度补到正文区宽度之上**：
一旦表的内容宽度超过正文区，浏览器就会把它压到 100%，所有表的左右边界自然一致。

判据换算（`docs/TABLES.md` 记有完整推导）
-----------------------------------------
GitHub 仓库页正文区约 950 px；ASCII 约 8 px/字，中日韩字符约 16 px/字。
把「中日韩字符记 2、其余记 1」得到**显示宽度单位**，正文区约合 119 单位。
本检查器取 `MIN_TABLE_WIDTH = 140`（约 18% 余量），保证在较窄的窗口下也不会掉出满宽。

**量的是「渲染后可见文字」，不是原始 Markdown。** 链接按链接文字计宽、不按 URL，
HTML 标签不计，`<br>` 取换行后最宽的一段。这条容易写错：按原始 Markdown 量宽时，
`[操作手册](https://example.org/very/long/path)` 会把一百多个字符的 URL 算进去，于是窄表被误判为达标——
本仓就因此漏掉过「文档地图」那张只有 81 单位的表。

检查项
------
| 编号 | 规则 | 适用范围 |
|---|---|---|
| T1 | 表头 / 分隔行 / 每个数据行的列数一致 | 全部 Markdown |
| T2 | 表内没有空单元格 | 全部 Markdown |
| T3 | 分隔行统一紧凑写法 `|---|---|`（与 `normalize_attribution` 一致） | 全部 Markdown |
| T4 | 每张表总显示宽度 ≥ `MIN_TABLE_WIDTH` | 落地页（README.md / README_EN.md） |
| T5 | 每张表列数 ≤ `MAX_COLUMNS`，超了应拆表 | 落地页 |

用法
----
    python scripts/check_tables.py            # 报告全部违规
    python scripts/check_tables.py --check    # 同上，供测试与 CI 使用（有违规则退出码 1）
    python scripts/check_tables.py --json
    python scripts/check_tables.py --all      # 连「非落地页的表宽」也按 T4 检查

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# 落地页：GitHub 仓库首页，读者第一眼看到的两份文档。
LANDING_PAGES = ("README.md", "README_EN.md")

# 正文区宽度换算后的硬指标（见模块 docstring）。
MIN_TABLE_WIDTH = 140

# 一张表超过这个列数就该拆表——列再多，单元格必然被压成窄条。
MAX_COLUMNS = 6

SKIP_DIRS = {".git", "out", "__pycache__", ".pytest_cache", "node_modules",
             "build", "dist", ".venv", "venv", "_backup"}

# 项目数据不是本仓的文档产物，不受表格规范约束（与 normalize_attribution 一致）。
SKIP_TOP = {"projects"}

SEP_CELL_RE = re.compile(r"^:?-{3,}:?$")

_IMAGE_RE = re.compile(r"!\[([^\]]*)\]\([^)]*\)")
_LINK_RE = re.compile(r"\[([^\]]*)\]\([^)]*\)")
_TAG_RE = re.compile(r"<(?!/?br\b)[^>]+>", re.I)
_BR_RE = re.compile(r"<br\s*/?>", re.I)
_EMPH_RE = re.compile(r"\*\*|__|`")


def rendered_text(cell: str) -> str:
    """单元格在页面上**实际显示**的文字。

    这一步是测量的关键：链接按**链接文字**计宽，不按 URL ——
    GitHub 只渲染 `[文字](https://example.org/very/long/path)` 里的「文字」，URL 藏在 href 里，
    一个字符都不占宽度。按原始 Markdown 量宽会严重高估，
    于是「看起来满了、其实还是窄的」这种表会被漏掉。
    """
    s = _IMAGE_RE.sub("", cell)                     # 图片不占文字宽度
    s = _LINK_RE.sub(lambda m: m.group(1), s)       # 链接只留链接文字
    s = _TAG_RE.sub("", s)                          # HTML 标签不占宽度
    s = _EMPH_RE.sub("", s)                         # **粗体** / `代码` 的标记
    return s.strip()


def cell_width(cell: str) -> int:
    """单元格的显示宽度；`<br>` 是换行，取最宽的那一行。"""
    parts = _BR_RE.split(rendered_text(cell))
    return max((display_width(p) for p in parts), default=0)


def display_width(text: str) -> int:
    """显示宽度：东亚宽字符记 2，其余记 1（与渲染后的近似像素宽度成正比）。"""
    return sum(2 if unicodedata.east_asian_width(ch) in "WF" else 1 for ch in text)


def _cells(line: str) -> list[str]:
    """把一行表格拆成单元格；支持 `\\|` 转义。"""
    body = line.strip()
    if body.startswith("|"):
        body = body[1:]
    if body.endswith("|") and not body.endswith("\\|"):
        body = body[:-1]
    parts, buf, escaped = [], [], False
    for ch in body:
        if escaped:
            buf.append(ch)
            escaped = False
        elif ch == "\\":
            escaped = True
            buf.append(ch)
        elif ch == "|":
            parts.append("".join(buf).strip())
            buf = []
        else:
            buf.append(ch)
    parts.append("".join(buf).strip())
    return parts


def _is_separator(line: str) -> bool:
    if not line.strip().startswith("|"):
        return False
    cells = _cells(line)
    return bool(cells) and all(SEP_CELL_RE.match(c) for c in cells if c != "")


def iter_tables(text: str):
    """逐张产出表格；跳过代码块内的内容。"""
    lines = text.replace("\r\n", "\n").split("\n")
    fence = ""
    i = 0
    while i < len(lines):
        stripped = lines[i].strip()
        if fence:
            if stripped.startswith(fence):
                fence = ""
            i += 1
            continue
        if stripped.startswith("```") or stripped.startswith("~~~"):
            fence = stripped[:3]
            i += 1
            continue
        if _is_separator(lines[i]) and i > 0 and lines[i - 1].strip().startswith("|"):
            header_line = lines[i - 1]
            j = i + 1
            body: list[str] = []
            while j < len(lines) and lines[j].strip().startswith("|"):
                body.append(lines[j])
                j += 1
            yield {
                "line": i,                       # 表头行（1 基）
                "header": _cells(header_line),
                "separator": _cells(lines[i]),
                "separator_raw": lines[i],
                "body": [_cells(x) for x in body],
            }
            i = j
            continue
        i += 1


def check_text(text: str, rel: str, full_width: bool) -> list[dict]:
    """返回该文件的违规清单。"""
    problems: list[dict] = []
    for n, table in enumerate(iter_tables(text), 1):
        cols = len(table["header"])

        # T5 —— 列数上限（仅落地页）
        if full_width and cols > MAX_COLUMNS:
            problems.append({
                "rule": "T5", "path": rel, "line": table["line"], "table": n,
                "detail": f"表 {n} 有 {cols} 列，超过上限 {MAX_COLUMNS}，应拆表",
            })

        # T1 —— 列数一致
        if len(table["separator"]) != cols:
            problems.append({
                "rule": "T1", "path": rel, "line": table["line"] + 1, "table": n,
                "detail": f"表 {n} 分隔行 {len(table['separator'])} 列，表头 {cols} 列",
            })
        for offset, row in enumerate(table["body"], start=1):
            if len(row) != cols:
                problems.append({
                    "rule": "T1", "path": rel,
                    "line": table["line"] + 1 + offset, "table": n,
                    "detail": f"表 {n} 第 {offset} 行 {len(row)} 列，表头 {cols} 列",
                })

        # T2 —— 空单元格
        for offset, row in enumerate(table["body"]):
            for ci, cell in enumerate(row):
                if not cell:
                    problems.append({
                        "rule": "T2", "path": rel,
                        "line": table["line"] + 2 + offset, "table": n,
                        "detail": f"表 {n} 第 {offset + 1} 行第 {ci + 1} 列为空",
                    })

        # T3 —— 分隔行紧凑写法
        expected = "|" + "---|" * cols
        if cols >= 1 and table["separator_raw"].strip() != expected:
            problems.append({
                "rule": "T3", "path": rel, "line": table["line"] + 1, "table": n,
                "detail": (f"表 {n} 分隔行应写成 {expected}，"
                           f"实为 {table['separator_raw'].strip()}"),
            })

        # T4 —— 总显示宽度（按渲染后可见文字计）
        if full_width:
            widths = [cell_width(c) for c in table["header"]]
            for row in table["body"]:
                for ci, cell in enumerate(row[:len(widths)]):
                    widths[ci] = max(widths[ci], cell_width(cell))
            total = sum(widths)
            if total < MIN_TABLE_WIDTH:
                problems.append({
                    "rule": "T4", "path": rel, "line": table["line"], "table": n,
                    "detail": (f"表 {n} 总宽 {total} 单位 < {MIN_TABLE_WIDTH}："
                               f"在 GitHub 上撑不满正文区，右边界会缩进；"
                               f"请补足真实内容（列宽 {widths}）"),
                })
    return problems


def _markdown_files(root: Path):
    for p in sorted(root.rglob("*.md")):
        rel = str(p.relative_to(root)).replace("\\", "/")
        parts = Path(rel).parts
        if set(parts[:-1]) & SKIP_DIRS:
            continue
        if parts and parts[0] in SKIP_TOP:
            continue
        yield p, rel


def run(root: Path = ROOT, all_files: bool = False) -> dict:
    problems: list[dict] = []
    scanned = 0
    tables = 0
    for path, rel in _markdown_files(root):
        try:
            text = path.read_text(encoding="utf-8")
        except Exception:
            continue
        scanned += 1
        tables += sum(1 for _ in iter_tables(text))
        full_width = all_files or rel in LANDING_PAGES
        problems.extend(check_text(text, rel, full_width))
    return {"root": str(root), "files": scanned, "tables": tables,
            "violations": problems, "count": len(problems)}


def render(report: dict) -> str:
    lines = [f"Markdown 表格规范检查　扫描 {report['files']} 个文件 / "
             f"{report['tables']} 张表"]
    if not report["violations"]:
        lines.append("  违规：0　（T1 列数 / T2 空单元格 / T3 分隔行 / "
                     "T4 总宽 / T5 列数上限 全部通过）")
        return "\n".join(lines)
    by_rule: dict[str, list[dict]] = {}
    for v in report["violations"]:
        by_rule.setdefault(v["rule"], []).append(v)
    for rule in sorted(by_rule):
        lines.append(f"  [{rule}] {len(by_rule[rule])} 处")
        for v in by_rule[rule]:
            lines.append(f"    {v['path']}:{v['line']}  {v['detail']}")
    lines.append(f"  违规合计：{report['count']}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="检查 Markdown 表格是否左右对齐")
    ap.add_argument("--check", action="store_true", help="有违规则退出码 1（供测试用）")
    ap.add_argument("--all", action="store_true", help="对全部 Markdown 也施加表宽检查")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    report = run(all_files=args.all)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(render(report))
    if args.check and report["count"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
