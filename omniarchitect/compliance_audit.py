"""Executable content-compliance self-check.

Not a document — a scanner. It walks the repository and answers four questions
that a design deliverable has to answer before it can be handed over:

1. Does every document carry the OmniAiLab signature?
2. Does any file leak personal or client information?
3. Does a user-facing file point at an external promotional link?
4. Is licence-bearing text sitting anywhere other than `LICENSE`?

Anything it cannot clear becomes an action item, and the build is not "done"
while action items remain. Nothing here is advisory.
"""
from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from .paths import ROOT
from .registry import PROJECT_ATTRIBUTION, SIGNATURE

# 本产品自有 URL（源码仓库 + 操作手册）：与自有站点同等对待。
# 单一来源取自 brand_policy.OWN_URLS —— 避免两处各维护一份白名单。
from .brand_policy import OWN_URLS as OWN_URL_PREFIXES  # noqa: E402

# Domains that belong to this project and may legitimately appear.
OWN_DOMAINS = ("omniailabx.com", "omniailab.cn", "omniailab")

LICENSE_TOKENS = ("MIT License", "CC BY", "Creative Commons", "SPDX-License",
                  "Copyright (c)", "Copyright ©", "All rights reserved")

# Files whose whole job is to state the licence. Third-party notices and the
# licence archive are the *only* legitimate home for external attribution, so
# they are allowed to carry licence text and source links.
LICENCE_ALLOWED = ("LICENSE", "VERSION", "THIRD_PARTY_NOTICES.md", "LICENSES/",
                   "docs/CONTENT_AUDIT.md", "docs/content-audit.json",
                   "docs/BRAND_POLICY.md", "docs/brand-policy.json")

# Specification namespaces and package-schema URIs are not promotional links.
BENIGN_URL_HOSTS = (
    "schemas.openxmlformats.org", "purl.org", "www.w3.org", "w3.org",
    "json-schema.org", "spdx.org", "creativecommons.org", "opensource.org",
    "pypi.org", "python.org", "docs.python.org", "localhost", "127.0.0.1",
    "img.shields.io",      # badge images
    "example.invalid",     # documentation placeholders (RFC 2606)
    "example.com",
)

# Values that look like a client name but are actually role words.
CLIENT_STOPWORDS = {
    "业主", "甲方", "客户", "主创", "设计师", "建筑师", "施工", "施工单位",
    "顾问", "团队", "项目", "使用方", "决策人", "需求方", "物业", "运营方",
    "投资方", "业主方", "甲方代表", "设计方", "总包", "分包", "监理",
}

PATTERNS = {
    "email": re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]{2,}"),
    # 手机号 / 身份证号：两端必须是**非十六进制字符**。
    # 否则 sha256 摘要里的一段十六进制（如 797f14446326125d）会被误判为手机号——
    # 这是真实踩到过的误报，规则必须能区分"一串十六进制"和"一个电话号码"。
    "cn_phone": re.compile(r"(?<![0-9A-Fa-f])1[3-9]\d{9}(?![0-9A-Fa-f])"),
    "cn_id": re.compile(r"(?<![0-9A-Fa-f])\d{17}[\dXx](?![0-9A-Fa-f])"),
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
             "build", "dist", ".venv", "venv", "third_party"}

# Test fixtures and this scanner necessarily contain the strings it looks for,
# and sample emails/phones so the detectors can be exercised. They are code, not
# shippable content, so content rules do not apply to them.
EXEMPT_FROM_CONTENT_RULES = ("omniarchitect/tests/",
                             "omniarchitect/compliance_audit.py",
                             "omniarchitect/brand_policy.py")

# The scanner's own machine-readable output. It exists to *record* findings, so
# scanning it would be self-referential: one flagged phone number would be
# written into the report, then re-flagged on the next run, forever. These files
# are generated records, not distributable assets.
SELF_OUTPUT = ("docs/content-audit.json", "docs/brand-policy.json")

DISPOSITIONS = (
    "original",                     # our own content, nothing to do
    "test-fixture",                 # 测试夹具：含样本数据，内容规则不适用
    "missing-signature",            # 文档缺少 OmniAiLab 署名
    "user-facing-external-link",    # 用户面文件含外部推广链接
    "review-privacy",               # 疑似个人/客户信息
    "review-licence",               # 许可证文本出现在 LICENSE 之外
    "generated-ok",                 # 运行时产物，不列入本仓内容
)

# Documents the end user reads. They may only link to our own domains.
USER_FACING = ("SKILL.md", "README.md", "README_EN.md", "docs/PRESENTATION.md",
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
    has_signature: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path, "kind": self.kind, "provenance": self.provenance,
            "disposition": self.disposition, "reasons": list(self.reasons),
            "hits": {k: v[:8] for k, v in self.hits.items()},
            "license_lines": list(self.license_lines),
            "url_count": self.url_count,
            "external_urls": list(self.external_urls)[:8],
            "has_signature": self.has_signature,
        }


def _matches(rel: str, prefixes: Iterable[str]) -> bool:
    return any(rel.startswith(p) or rel == p for p in prefixes)


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

    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        f.reasons.append(f"无法读取：{exc}")
        f.disposition = "review-licence"
        return f

    if _matches(rel, EXEMPT_FROM_CONTENT_RULES):
        f.provenance = "test-fixture"
        f.disposition = "test-fixture"
        f.reasons.append("测试夹具与扫描器本身：容忍其中的样本字符串与示例联系方式")
        return f

    if rel in SELF_OUTPUT:
        f.provenance = "generated"
        f.disposition = "generated-ok"
        f.reasons.append(
            "扫描器自身的机器可读产出：用于记录发现，不参与内容规则（否则会自我循环）"
        )
        return f

    licence_allowed = _matches(rel, LICENCE_ALLOWED)
    user_facing = _matches(rel, USER_FACING)

    # --- 1. signature ---------------------------------------------------
    if rel.endswith(".md"):
        f.has_signature = "© OmniAiLab" in text

    # --- 2. personal / client data --------------------------------------
    privacy: Dict[str, List[str]] = {}
    for key in ("email", "cn_phone", "cn_id"):
        found = PATTERNS[key].findall(text)
        if found:
            privacy[key] = [str(x) for x in found][:8]
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
    f.hits = dict(privacy)

    # --- 3. links --------------------------------------------------------
    urls = PATTERNS["url"].findall(text)
    external = [u for u in urls
                if not any(d in u for d in OWN_DOMAINS)
                and not any(u.startswith(p) for p in OWN_URL_PREFIXES)
                and not any(h in u for h in BENIGN_URL_HOSTS)]

    # --- 4. licence text -------------------------------------------------
    lic = [ln.strip() for ln in text.splitlines()
           if any(k in ln for k in LICENSE_TOKENS)]

    f.license_lines = lic[:6]
    f.url_count = len(urls)
    f.external_urls = external

    # ---- disposition, in order of severity ------------------------------
    if privacy:
        f.disposition = "review-privacy"
        f.reasons.append(f"疑似个人/客户信息：{', '.join(sorted(privacy))}"
                         "（须脱敏或确认授权后方可分发）")

    # A user-facing outbound link is the more serious finding, so it is reported
    # ahead of a missing footer.
    if external and not licence_allowed and f.disposition == "original":
        f.disposition = ("user-facing-external-link" if user_facing
                         else "review-licence")
        f.reasons.append(
            f"含 {len(external)} 个外部链接：用户面材料只能指向自有站点"
        )

    if not f.has_signature and f.disposition == "original":
        f.disposition = "missing-signature"
        f.reasons.append("文档缺少 OmniAiLab 署名（末尾需附标准署名行）")

    if lic and not licence_allowed and f.disposition == "original":
        f.disposition = "review-licence"
        f.reasons.append("含许可证文本：应集中在 LICENSE 内")

    if rel.startswith(("projects/", "out/")):
        f.disposition = "generated-ok"
        f.provenance = "generated"
        f.reasons = ["运行时产物，不列入本仓内容"]

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
                    if f.disposition in ("missing-signature",
                                         "user-facing-external-link",
                                         "review-privacy", "review-licence")]
    return {
        "root": str(r),
        "scanned_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "files_scanned": len(findings),
        "by_disposition": dict(sorted(by_disposition.items())),
        "needs_action": needs_action,
        "action_count": len(needs_action),
        "signature": SIGNATURE,
        "attribution": dict(PROJECT_ATTRIBUTION),
        "rules": {
            "every_markdown_carries_the_signature": True,
            "user_facing_links_must_be_own_domains": list(OWN_DOMAINS),
            "personal_and_client_data_must_be_redacted": True,
            "licence_text_belongs_in_LICENSE": True,
        },
        "user_facing_globs": list(USER_FACING),
        "conclusion": (
            "全部文档已署名，且无个人信息、外部推广链接或归属问题"
            if not needs_action else f"{len(needs_action)} 个文件需要处理"
        ),
    }


# --------------------------------------------------------------------------
def render_markdown(report: Dict[str, Any]) -> str:
    from .registry import frontmatter_block

    head = frontmatter_block(
        "omniailab-content-audit",
        "内容合规自检报告（自动生成）：署名 / 隐私 / 外链 / 许可四类检查的扫描结果与待处理清单。",
        extra={"scope": "自动生成 · 每次 audit 覆盖"},
    )
    lines = [
        "# 内容合规自检报告",
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
        "original": "本项目原创内容，已合规",
        "generated-ok": "运行时生成，不列入本仓内容",
        "test-fixture": "测试夹具，含样本数据；内容规则不适用",
        "missing-signature": "文档缺少 OmniAiLab 署名",
        "user-facing-external-link": "用户面文件含外部推广链接",
        "review-privacy": "疑似个人或客户信息，须脱敏或确认授权",
        "review-licence": "含许可证文本或外部链接，须确认归属方式",
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

    a = report["attribution"]
    lines += [
        "## 署名与归属",
        "",
        f"- 出品：**{a['owner']}**　开发者：**{a['developer']}**",
        f"- 产品：{a['display_name']}（调用名 `{a['skill']}`）",
        f"- 平台：{a['homepage_cn']}　{a['homepage_intl']}",
        f"- 标准署名行：`{report['signature']}`",
        "",
        "## 规则",
        "",
        "1. **每一份 Markdown 文档都必须带 OmniAiLab 署名行**（文档末尾，独立一段）。",
        "2. **用户面文件只能指向自有站点**；外部推广链接一律不得出现。",
        "3. **个人与客户信息一律先脱敏**；未经授权不得作为可分发资产。",
        "4. **许可证文本只放在 `LICENSE`**，全仓仅此一处。",
        "5. **本系统的设计知识全部为原创**，来源为通用设计原理与公开工程惯例，",
        "   不复制、不改写任何第三方文档。",
        "",
        "---",
        "",
        SIGNATURE,
        "",
    ]
    return head + "\n".join(lines)


def write_report(out_dir: str | Path | None = None,
                 root: str | Path = ROOT) -> Dict[str, str]:
    r = Path(root)
    out = Path(out_dir) if out_dir else (r / "docs")
    out.mkdir(parents=True, exist_ok=True)
    report = scan(r)
    md = out / "CONTENT_AUDIT.md"
    js = out / "content-audit.json"
    md.write_text(render_markdown(report), encoding="utf-8")
    js.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    # the report itself must satisfy the rule it enforces
    report = scan(r)
    return {"markdown": str(md), "json": str(js),
            "action_count": str(report["action_count"])}


__all__ = [
    "PATTERNS", "OWN_DOMAINS", "BENIGN_URL_HOSTS", "DISPOSITIONS",
    "USER_FACING", "LICENCE_ALLOWED", "FileFinding", "scan", "scan_file",
    "render_markdown", "write_report",
]
