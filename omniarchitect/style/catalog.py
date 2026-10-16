"""Style catalog: a light index plus on-demand loading of full records.

The point of this module is memory discipline. There are 47 style records and
each is a substantial document; loading all of them to answer "which styles
suit a 120 m² flat on a mid budget?" would be wasteful and would also drag the
entire knowledge base into a host agent's context.

So: `catalog.json` holds **only** the searchable index (id, names, family,
tags, stages, budget tier, applicable spaces, and a one-line summary). Full
records are read from `knowledge/styles/<style_id>.json` only when a style is
actually selected.

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set

from .resources import CATALOG_FILE, STYLE_DIR, project_version, style_files
from .validation import check_style_file, load_schema

# Fields copied into the index. Everything else stays in the full record.
_INDEX_FIELDS = (
    "style_id", "display_name_zh", "display_name_en", "family", "tags", "stages",
)


@dataclass
class StyleEntry:
    """One row of the index — enough to search and display, not to compile."""

    style_id: str
    display_name_zh: str
    display_name_en: str
    family: str = ""
    tags: List[str] = field(default_factory=list)
    stages: List[str] = field(default_factory=list)
    budget_tier: str = ""
    applicable_spaces: List[str] = field(default_factory=list)
    compatible_styles: List[str] = field(default_factory=list)
    summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "style_id": self.style_id,
            "display_name_zh": self.display_name_zh,
            "display_name_en": self.display_name_en,
            "family": self.family,
            "tags": list(self.tags),
            "stages": list(self.stages),
            "budget_tier": self.budget_tier,
            "applicable_spaces": list(self.applicable_spaces),
            "compatible_styles": list(self.compatible_styles),
            "summary": self.summary,
        }

    @property
    def label(self) -> str:
        return f"{self.display_name_zh}（{self.display_name_en}）"


def _summarize(style: Dict[str, Any], limit: int = 96) -> str:
    """First sentence of the historical summary, truncated for the index."""
    text = (style.get("history_and_context") or {}).get("summary", "")
    text = " ".join(str(text).split())
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "…"


def build_catalog(style_dir: Optional[Path] = None) -> Dict[str, Any]:
    """Read every style file and produce the index. Also validates as it goes."""
    d = style_dir or STYLE_DIR
    schema = load_schema()
    styles: List[Dict[str, Any]] = []
    problems: Dict[str, List[str]] = {}

    for p in style_files(d):
        issues = check_style_file(p)
        if issues:
            problems[p.name] = issues
            continue
        raw = json.loads(p.read_text(encoding="utf-8"))
        entry = {k: raw.get(k) for k in _INDEX_FIELDS}
        entry["budget_tier"] = (raw.get("budget_considerations") or {}).get("tier", "")
        entry["applicable_spaces"] = list(raw.get("applicable_spaces") or [])
        entry["compatible_styles"] = list(raw.get("compatible_styles") or [])
        entry["summary"] = _summarize(raw)
        styles.append(entry)

    by_family: Dict[str, List[str]] = {}
    by_tag: Dict[str, List[str]] = {}
    by_stage: Dict[str, List[str]] = {}
    by_space_word: Dict[str, List[str]] = {}
    for entry in styles:
        by_family.setdefault(entry.get("family") or "unclassified", []).append(entry["style_id"])
        for tag in entry.get("tags") or []:
            by_tag.setdefault(tag, []).append(entry["style_id"])
        for st in entry.get("stages") or []:
            by_stage.setdefault(st, []).append(entry["style_id"])
        for sp in entry.get("applicable_spaces") or []:
            by_space_word.setdefault(sp, []).append(entry["style_id"])

    return {
        "name": "OmniAiLab Design Style Catalog",
        "version": project_version(),
        "schema_id": schema.get("$id", ""),
        "generated_from": "knowledge/styles/",
        "count": len(styles),
        "families": {k: sorted(v) for k, v in sorted(by_family.items())},
        "tags": {k: sorted(v) for k, v in sorted(by_tag.items())},
        "stages": {k: sorted(v) for k, v in sorted(by_stage.items())},
        "applicable_spaces": {k: sorted(v) for k, v in sorted(by_space_word.items())},
        "invalid": problems,
        "styles": styles,
    }


class Catalog:
    """Searchable style index with on-demand loading of full records."""

    def __init__(self, data: Dict[str, Any], style_dir: Optional[Path] = None):
        self.data = data
        self.style_dir = style_dir or STYLE_DIR
        self._entries: List[StyleEntry] = [
            StyleEntry(
                style_id=s.get("style_id", ""),
                display_name_zh=s.get("display_name_zh", ""),
                display_name_en=s.get("display_name_en", ""),
                family=s.get("family", "") or "",
                tags=list(s.get("tags") or []),
                stages=list(s.get("stages") or []),
                budget_tier=s.get("budget_tier", "") or "",
                applicable_spaces=list(s.get("applicable_spaces") or []),
                compatible_styles=list(s.get("compatible_styles") or []),
                summary=s.get("summary", "") or "",
            )
            for s in data.get("styles", [])
        ]
        self._by_id = {e.style_id: e for e in self._entries}
        self._full_cache: Dict[str, Dict[str, Any]] = {}

    # -- basics ---------------------------------------------------------
    def __len__(self) -> int:
        return len(self._entries)

    def __contains__(self, style_id: object) -> bool:
        return style_id in self._by_id

    def __iter__(self):
        return iter(self._entries)

    @property
    def ids(self) -> List[str]:
        return [e.style_id for e in self._entries]

    @property
    def families(self) -> Dict[str, List[str]]:
        return dict(self.data.get("families", {}))

    @property
    def tags(self) -> Dict[str, List[str]]:
        return dict(self.data.get("tags", {}))

    @property
    def invalid(self) -> Dict[str, List[str]]:
        return dict(self.data.get("invalid", {}))

    def entry(self, style_id: str) -> Optional[StyleEntry]:
        return self._by_id.get(style_id)

    def get(self, style_id: str) -> StyleEntry:
        e = self._by_id.get(style_id)
        if e is None:
            raise KeyError(f"未知风格 {style_id!r}；可用：{', '.join(self.ids[:6])} …")
        return e

    # -- on-demand loading ----------------------------------------------
    def load_style(self, style_id: str) -> Dict[str, Any]:
        """Read the full record. Cached per process; nothing is preloaded."""
        if style_id in self._full_cache:
            return self._full_cache[style_id]
        path = self.style_dir / f"{style_id}.json"
        if not path.exists():
            raise KeyError(f"风格文件不存在：{path}")
        raw = json.loads(path.read_text(encoding="utf-8"))
        self._full_cache[style_id] = raw
        return raw

    def summary_table(self, ids: Optional[Sequence[str]] = None) -> List[Dict[str, str]]:
        rows = []
        for e in self._entries:
            if ids is not None and e.style_id not in ids:
                continue
            rows.append({
                "style_id": e.style_id,
                "style": e.label,
                "family": e.family,
                "tier": e.budget_tier,
                "summary": e.summary,
            })
        return rows

    # -- search ---------------------------------------------------------
    def search(
        self,
        *,
        tags: Iterable[str] = (),
        family: str = "",
        stage: str = "",
        budget_tier: str = "",
        space: str = "",
        text: str = "",
        match_all_tags: bool = False,
        limit: int = 0,
    ) -> List[StyleEntry]:
        """Filter the index. Empty criteria return everything.

        `tags` matches any by default; set `match_all_tags=True` to require all.
        `text` does a case-insensitive substring match on id, names and summary.
        """
        want_tags: Set[str] = {t.strip().lower() for t in tags if t and t.strip()}
        needle = text.strip().lower()
        out: List[StyleEntry] = []
        for e in self._entries:
            if family and e.family != family:
                continue
            if stage and stage not in e.stages:
                continue
            if budget_tier and e.budget_tier != budget_tier:
                continue
            if space and not any(space in s for s in e.applicable_spaces):
                continue
            if want_tags:
                have = {t.lower() for t in e.tags}
                if match_all_tags:
                    if not want_tags.issubset(have):
                        continue
                elif not (want_tags & have):
                    continue
            if needle:
                blob = " ".join([e.style_id, e.display_name_zh, e.display_name_en,
                                 e.summary, " ".join(e.tags)]).lower()
                if needle not in blob:
                    continue
            out.append(e)
        return out[:limit] if limit else out

    def compatible_with(self, style_id: str) -> List[StyleEntry]:
        """Styles the given style declares itself compatible with."""
        e = self.get(style_id)
        return [self._by_id[c] for c in e.compatible_styles if c in self._by_id]

    def report(self) -> Dict[str, Any]:
        return {
            "count": len(self._entries),
            "version": self.data.get("version", ""),
            "families": {k: len(v) for k, v in self.families.items()},
            "tag_count": len(self.tags),
            "invalid": self.invalid,
            "note": "索引只含可搜索字段；完整风格记录在按需加载时才读取。",
        }


def load_catalog(*, refresh: bool = False,
                 style_dir: Optional[Path] = None,
                 catalog_file: Optional[Path] = None) -> Catalog:
    """Load the index, building it from `knowledge/styles/` when needed."""
    cf = catalog_file or CATALOG_FILE
    d = style_dir or STYLE_DIR
    if refresh or not cf.exists():
        data = build_catalog(d)
        cf.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return Catalog(data, d)
    data = json.loads(cf.read_text(encoding="utf-8"))
    # A catalog built from a different set of files is stale — rebuild.
    if data.get("count") != len(style_files(d)):
        data = build_catalog(d)
        cf.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return Catalog(data, d)
