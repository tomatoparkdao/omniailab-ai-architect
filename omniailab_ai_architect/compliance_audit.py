"""Executable third-party content audit.

Not a document — a scanner. It walks the repository, classifies every text file
by provenance, flags the things that must not reach an end user (other firms'
brand names, commercial homepages, licence-bearing copies), and emits a
disposition per file.

The licence obligations that *must* survive are declared here so they cannot be
dropped by accident: the upstream repository stays vendored and unmodified, and
its attribution is required in both `THIRD_PARTY_NOTICES.md` and any deliverable
that uses criteria derived from it.
"""
from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

from .paths import ROOT

# --------------------------------------------------------------------------
# Licence obligations that must be preserved. Removing these would breach the
# upstream licence, so the audit treats them as "keep" rather than "remove".
UPSTREAM = {
    "project": "arch-skills",
    "url": "https://github.com/gujun1502/arch-skills",
    "author": "Gu Jun",
    "license": "MIT (code) · CC BY 4.0 (documentation)",
    "required_attribution": "Gu Jun / arch-skills",
    "vendored_at": "third_party/arch-skills",
}

# Domains that belong to this project and may legitimately appear.
OWN_DOMAINS = ("omniailabx.com", "omniailab.cn", "omniailab")

# Strings that must never appear in what an end user sees. Each gets an
# explanation so the fix is obvious.
WATCHLIST: List[Dict[str, str]] = [
    {"token": "arch-skills", "kind": "upstream-name",
     "why": "上游项目名；只允许出现在合规/署名文件中"},
    {"token": "gujun1502", "kind": "upstream-url",
     "why": "上游仓库地址；只允许出现在合规/署名文件中"},
    {"token": "Gu Jun", "kind": "author-name",
     "why": "上游作者；署名义务，只允许出现在合规文件中"},
    {"token": "chodo", "kind": "commercial-site",
     "why": "第三方商业站点；用户面材料不得出现"},
    {"token": "arch-skills.com", "kind": "commercial-site",
     "why": "第三方推广站点；用户面材料不得出现"},
]

# Files that legitimately carry upstream attribution (author / project / repo).
# The licence requires the credit to survive, so it is concentrated here.
ATTRIBUTION_ALLOWED = (
    "THIRD_PARTY_NOTICES.md",
    "docs/THIRD_PARTY_AUDIT.md",
    "docs/ARCH_SKILLS_INTEGRATION.md",
    "AGENTS.md",
    "LICENSES/",
    "compliance/",
    "third_party/",
    "omniailab_ai_architect/",      # runtime constants that name the upstream source
    "docs/third-party-audit.json",  # machine-generated report of this scan
    # The test suite must contain the banned strings in order to assert their
    # absence elsewhere; that is data, not content.
)

# Commercial promotion may appear *only* in the notices themselves — and in this
# scanner, which has to know the tokens in order to find them.
COMMERCIAL_ALLOWED = (
    "THIRD_PARTY_NOTICES.md",
    "docs/THIRD_PARTY_AUDIT.md",
    "docs/third-party-audit.json",
    "third_party/",
    "omniailab_ai_architect/compliance_audit.py",
)

LICENSE_TOKENS = ("MIT License", "CC BY", "Creative Commons", "SPDX-License",
                  "Copyright (c)", "Copyright ©", "All rights reserved")

# Specification namespaces and package-schema URIs are not promotional links.
BENIGN_URL_HOSTS = (
    "schemas.openxmlformats.org", "purl.org", "www.w3.org", "w3.org",
    "json-schema.org", "spdx.org", "creativecommons.org", "opensource.org",
    "pypi.org", "python.org", "docs.python.org", "localhost", "127.0.0.1",
)

# Values that look like a client name but are actually role words.
CLIENT_STOPWORDS = {
    "业主", "甲方", "客户", "主创", "设计师", "建筑师", "施工", "施工单位",
    "顾问", "团队", "项目", "使用方", "决策人", "需求方", "物业", "运营方",
    "投资方", "业主方", "甲方代表", "设计方", "总包", "分包", "监理",
}

PATTERNS = {
    "email": re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]{2,}"),
    "cn_phone": re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)"),
    "cn_id": re.compile(r"(?<!\d)\d{17}[\dXx](?!\d)"),
    "url": re.compile(r"https?://[^\s)\]\"'><]+"),
    "client_name": re.compile(
        r"(业主|甲方|客户)\s*[:：]\s*([\u4e00-\u9fa5]{2,4})"
        r"(?=\s*(?:$|[，。；、,;]|（|先生|女士|总|老师))",
        re.MULTILINE,
    ),
}

# A captured "name" that contains any of these is a sentence, not a person.
NON_NAME_CHARS = set("后前的了请须应需由可要是与和及等返回进确认真实个这那如何怎么为" 
                     "对关于按照依据条件情况说明内容此处下面以下上述如下")

TEXT_EXT = {".md", ".py", ".json", ".yaml", ".yml", ".toml", ".txt", ".csv",
            ".html", ".js", ".ts", ".tsx", ".jsx", ".css", ".xml", ".ini",
            ".cfg", ".cmd", ".sh", ".ps1"}

SKIP_DIRS = {".git", "out", "__pycache__", ".pytest_cache", "node_modules",
             "build", "dist", ".venv", "venv"}

# Test fixtures necessarily contain the strings the scanner looks for, and
# sample emails/phones so the detectors can be exercised. They are code, not
# shippable content, so content rules do not apply to them.
EXEMPT_FROM_CONTENT_RULES = ("omniailab_ai_architect/tests/",)

DISPOSITIONS = (
    "original",                    # our own content, nothing to do
    "test-fixture",                # 测试夹具：含样本数据，内容规则不适用
    "vendored-preserve",           # upstream copy: keep verbatim
    "attribution-required-keep",   # licence-mandated credit: keep
    "sanitize-user-facing",        # strip third-party promo from a user-facing file
    "review-privacy",              # possible personal/client data
    "review-licence",              # licence-bearing text outside the notices
    "generated-ok",                # produced at runtime; no provenance concern
)

USER_FACING = ("SKILL.md", "README.md", "docs/PRESENTATION.md",
               "docs/INSTALL.md", "docs/MCP_TOOLS.md", "docs/OMNIAILAB_INTEGRATION.md",
               "templates/", "skills/", "cases/", "knowledge/")


# --------------------------------------------------------------------------
@dataclass
class FileFinding:
    path: str
    kind: str = ""
    provenance: str = "original"
    disposition: str = "original"
    reasons: List[str] = field(default_factory=list)
    hits: Dict[str, List[str]] = field(default_factory=dict)
    license_lines: List[str] = field(default_factory=list)
    url_count: int = 0
    external_urls: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path, "kind": self.kind, "provenance": self.provenance,
            "disposition": self.disposition, "reasons": list(self.reasons),
            "hits": {k: v[:8] for k, v in self.hits.items()},
            "license_lines": list(self.license_lines),
            "url_count": self.url_count,
            "external_urls": list(self.external_urls)[:8],
        }


def _is_user_facing(rel: str) -> bool:
    return any(rel.startswith(p) or rel == p for p in USER_FACING)


def _is_attribution_allowed(rel: str) -> bool:
    return any(rel.startswith(p) or rel == p for p in ATTRIBUTION_ALLOWED)


def _iter_files(root: Path) -> Iterable[Path]:
    for p in sorted(root.rglob("*")):
        if p.is_dir():
            continue
        rel_parts = p.relative_to(root).parts
        if set(rel_parts[:-1]) & SKIP_DIRS:
            continue
        if p.suffix.lower() not in TEXT_EXT:
            continue
        yield p


def scan_file(root: Path, path: Path) -> Optional[FileFinding]:
    rel = str(path.relative_to(root)).replace("\\", "/")
    f = FileFinding(path=rel, kind=path.suffix.lower().lstrip("."))

    if rel.startswith("third_party/"):
        f.provenance = "upstream-vendored"
        f.disposition = "vendored-preserve"
        f.reasons.append("上游仓库原样保留（含其自带 LICENSE），不得修改")
        return f

    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        f.reasons.append(f"无法读取：{exc}")
        f.disposition = "review-licence"
        return f

    if any(rel.startswith(p) for p in EXEMPT_FROM_CONTENT_RULES):
        f.provenance = "test-fixture"
        f.disposition = "test-fixture"
        f.reasons.append("测试夹具：容忍其中的样本字符串与示例联系方式")
        return f

    allowed_attribution = _is_attribution_allowed(rel)
    allowed_commercial = any(rel.startswith(p) or rel == p for p in COMMERCIAL_ALLOWED)
    user_facing = _is_user_facing(rel)

    # 1) third-party watchlist — attribution vs commercial are treated apart
    watch_hits: Dict[str, List[str]] = {}
    commercial_hit = False
    for item in WATCHLIST:
        if item["token"].lower() in text.lower():
            watch_hits.setdefault(item["kind"], []).append(item["token"])
            if item["kind"] == "commercial-site":
                commercial_hit = True
    f.hits = {k: v for k, v in watch_hits.items()}

    # 2) personal / client data
    privacy: Dict[str, List[str]] = {}
    for key in ("email", "cn_phone", "cn_id"):
        found = PATTERNS[key].findall(text)
        if found:
            privacy[key] = [str(x) for x in found][:8]
    f.hits = dict(f.hits)
    names = []
    for m in PATTERNS["client_name"].findall(text):
        value = m[1]
        if value in CLIENT_STOPWORDS or any(value[:2] == s[:2] for s in CLIENT_STOPWORDS):
            continue
        if any(ch in NON_NAME_CHARS for ch in value):
            continue          # 看起来是句子，不是人名
        names.append(value)
    if names:
        privacy["client_name"] = names[:8]
    f.hits.update(privacy)

    # 3) links
    urls = PATTERNS["url"].findall(text)
    external = [u for u in urls
                if not any(d in u for d in OWN_DOMAINS)
                and not any(h in u for h in BENIGN_URL_HOSTS)]

    lic = [ln.strip() for ln in text.splitlines()
           if any(k in ln for k in LICENSE_TOKENS)]

    f.license_lines = lic[:6]
    f.url_count = len(urls)
    f.external_urls = external

    # ---- disposition, in order of severity ----------------------------
    if commercial_hit and not allowed_commercial:
        f.disposition = "sanitize-user-facing" if user_facing else "review-licence"
        f.reasons.append("出现第三方商业推广站点/名称：必须移除，"
                         "只允许保留在 THIRD_PARTY_NOTICES.md")
    elif watch_hits and not allowed_attribution:
        f.disposition = "sanitize-user-facing" if user_facing else "review-licence"
        f.reasons.append(
            f"命中第三方名称 {sorted(watch_hits.values())[0]}："
            "用户面材料须改写为原创表述；署名义务集中到 THIRD_PARTY_NOTICES.md"
        )
    elif watch_hits and allowed_attribution:
        f.disposition = "attribution-required-keep"
        f.reasons.append("命中署名义务：按上游许可保留（已集中在合规文件内）")

    if privacy:
        f.disposition = "review-privacy"
        f.reasons.append(f"疑似个人/客户信息：{', '.join(sorted(privacy))}"
                         "（须脱敏或确认授权后方可分发）")

    if external and user_facing and f.disposition in ("original", ""):
        f.reasons.append(f"用户面文件含 {len(external)} 个外部链接：逐条确认必要性")
        f.disposition = "sanitize-user-facing"

    if lic and not allowed_attribution and f.disposition == "original":
        f.reasons.append("含许可证文本：应集中到 THIRD_PARTY_NOTICES.md")
        f.disposition = "review-licence"

    if rel.startswith(("projects/", "out/")):
        f.disposition = "generated-ok"
        f.provenance = "generated"

    return f


def scan(root: str | Path = ROOT, include_generated: bool = False) -> Dict[str, Any]:
    r = Path(root)
    findings: List[FileFinding] = []
    for p in _iter_files(r):
        rel = str(p.relative_to(r)).replace("\\", "/")
        if not include_generated and rel.startswith(("out/", "projects/")):
            continue
        try:
            f = scan_file(r, p)
        except Exception:
            continue
        if f:
            findings.append(f)

    by_disposition: Dict[str, int] = {}
    for f in findings:
        by_disposition[f.disposition] = by_disposition.get(f.disposition, 0) + 1

    needs_action = [f.to_dict() for f in findings
                    if f.disposition in ("sanitize-user-facing", "review-privacy",
                                         "review-licence")]
    return {
        "root": str(r),
        "scanned_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "files_scanned": len(findings),
        "by_disposition": dict(sorted(by_disposition.items())),
        "needs_action": needs_action,
        "action_count": len(needs_action),
        "upstream": dict(UPSTREAM),
        "watchlist": [dict(w) for w in WATCHLIST],
        "attribution_allowed_in": list(ATTRIBUTION_ALLOWED),
        "user_facing_globs": list(USER_FACING),
        "conclusion": (
            "无第三方商业内容需要处理" if not needs_action
            else f"{len(needs_action)} 个文件需要处理"
        ),
    }


# --------------------------------------------------------------------------
def render_markdown(report: Dict[str, Any]) -> str:
    lines = [
        "# 第三方内容审计报告",
        "",
        f"- 扫描时间：{report['scanned_at']}",
        f"- 扫描根目录：`{report['root']}`",
        f"- 扫描文本文件：**{report['files_scanned']}**",
        f"- 结论：**{report['conclusion']}**",
        "",
        "## 处置分布",
        "",
        "| 处置 | 文件数 | 含义 |",
        "| --- | --- | --- |",
    ]
    meaning = {
        "original": "本项目原创内容，无需处理",
        "generated-ok": "运行时生成，不涉及来源问题",
        "vendored-preserve": "上游副本原样保留（含其 LICENSE），禁止修改",
        "attribution-required-keep": "许可要求的署名，必须保留",
        "test-fixture": "测试夹具，含样本数据；内容规则不适用",
        "sanitize-user-facing": "用户面文件含第三方名称/链接，须移除或改写",
        "review-privacy": "疑似个人或客户信息，须脱敏或确认授权",
        "review-licence": "含许可证文本或第三方名称，须确认归属方式",
    }
    for k, v in report["by_disposition"].items():
        lines.append(f"| `{k}` | {v} | {meaning.get(k, '')} |")
    lines.append("")

    if report["needs_action"]:
        lines += ["## 需要处理的文件", "",
                  "| 文件 | 处置 | 原因 |", "| --- | --- | --- |"]
        for f in report["needs_action"]:
            reasons = "；".join(f["reasons"])[:220] or "-"
            lines.append(f"| `{f['path']}` | `{f['disposition']}` | {reasons} |")
        lines.append("")
    else:
        lines += ["## 需要处理的文件", "", "无。", ""]

    lines += [
        "## 必须保留的第三方署名",
        "",
        f"- 项目：**{report['upstream']['project']}** — {report['upstream']['url']}",
        f"- 作者：**{report['upstream']['author']}**",
        f"- 许可：{report['upstream']['license']}",
        f"- 本地副本：`{report['upstream']['vendored_at']}`（原样保留，不修改）",
        f"- 允许出现署名信息的文件：{', '.join('`%s`' % x for x in report['attribution_allowed_in'])}",
        "",
        "## 处置规则",
        "",
        "1. **用户面文件（SKILL.md / README / skills / knowledge / cases / templates / presentation）**", 
        "   不得出现第三方品牌名、商业推广站点或跳转链接。",
        "2. **署名义务不可删**：许可证要求的作者、来源与许可标识集中在本文件与 `THIRD_PARTY_NOTICES.md`。",
        "3. **要去掉某份第三方文档的再分发依赖**，只能从通用设计原理与公开工程惯例出发独立原创，",
        "   不得复制或仅作同义改写。",
        "4. **疑似个人或客户信息**一律先脱敏并确认授权，未经授权不得作为可再分发资产。",
        "5. **上游仓库**（`third_party/arch-skills/`）保持原样，其自带 LICENSE 不得删除。",
        "",
    ]
    return "\n".join(lines)


def write_report(out_dir: str | Path | None = None,
                 root: str | Path = ROOT) -> Dict[str, str]:
    r = Path(root)
    out = Path(out_dir) if out_dir else (r / "docs")
    out.mkdir(parents=True, exist_ok=True)
    report = scan(r)
    md = out / "THIRD_PARTY_AUDIT.md"
    js = out / "third-party-audit.json"
    md.write_text(render_markdown(report), encoding="utf-8")
    js.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"markdown": str(md), "json": str(js),
            "action_count": str(report["action_count"])}


__all__ = [
    "UPSTREAM", "WATCHLIST", "ATTRIBUTION_ALLOWED", "DISPOSITIONS",
    "FileFinding", "scan", "scan_file", "render_markdown", "write_report",
]
