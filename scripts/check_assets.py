#!/usr/bin/env python
"""Asset guard: keep this repository pushable to GitHub.

A design repository attracts binary files — reference photographs, site videos,
moodboard scans, exported renders, delivered PPTX, font files. They are exactly
the files that cannot go into git: they bloat the history permanently, they make
clones slow, and above all they are *not data*, so no test can check them and no
reviewer can diff them.

The rule for this project is flat:

* a single file of **1 MB or more is a large file** — it must not be committed;
* **media binaries are not committed at all**, whatever their size — video,
  photos, PSD, audio, archives, fonts, Office files and PDF;
* if the information in such a file is actually needed, it goes in as
  **structured data** (JSON metadata) plus an external reference — never as the
  file itself.

Runtime output is out of scope: it lives in the external workspace
(`omniarchitect/workspace.py` — projects / outputs / tests / cache / archive),
never inside the skill folder, so a large render living there is not a finding.
But "the repo is clean" does not mean "the package is clean": `--distribution`
audits the whitelist payload as well, i.e. the files that actually ship.

    python scripts/check_assets.py            # check, exit 1 on any finding
    python scripts/check_assets.py --json     # machine-readable
    python scripts/check_assets.py --list     # show the largest files
    python scripts/check_assets.py --distribution   # also audit the installable package

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

HERE = Path(__file__).resolve()
ROOT = HERE.parents[1]

# --- thresholds -----------------------------------------------------------
MAX_FILE_BYTES = 1 * 1024 * 1024          # 1 MB — the stated limit

# --- media and binary types that are never committed ----------------------
MEDIA_TYPES: Dict[str, Tuple[str, ...]] = {
    "视频": ("mp4", "mov", "avi", "mkv", "webm", "flv", "wmv", "m4v", "mpg",
             "mpeg", "3gp", "ts"),
    "图片与位图": ("png", "jpg", "jpeg", "gif", "webp", "bmp", "tif", "tiff",
                   "heic", "heif", "psd", "ai", "eps", "raw", "cr2", "nef"),
    "音频": ("mp3", "wav", "flac", "aac", "m4a", "ogg", "wma", "aiff"),
    "压缩包": ("zip", "rar", "7z", "tar", "gz", "bz2", "xz", "tgz"),
    "字体": ("ttf", "otf", "woff", "woff2", "eot"),
    "Office 二进制": ("pptx", "docx", "xlsx", "ppt", "doc", "xls", "odt",
                      "ods", "odp"),
    "PDF 与可执行": ("pdf", "exe", "dll", "so", "dylib", "dmg", "iso", "bin"),
}

# Directories never scanned when git is unavailable.
SKIP_DIRS = {".git", "out", "__pycache__", ".pytest_cache", "build", "dist",
             "node_modules", ".venv", "venv", ".idea", ".vscode",
             "renders", "concept-render", "private", "_backup", "_pre-rename-copy"}


def _ext(name: str) -> str:
    return Path(name).suffix.lower().lstrip(".")


def _media_kind(ext: str) -> str:
    for kind, exts in MEDIA_TYPES.items():
        if ext in exts:
            return kind
    return ""


def _candidates_from_git(root: Path = ROOT) -> List[Path] | None:
    """Exactly the files git would push, or None if git is unavailable."""
    try:
        tracked = subprocess.run(["git", "ls-files"], cwd=str(root),
                                 capture_output=True, text=True,
                                 encoding="utf-8", errors="replace")
        if tracked.returncode != 0:
            return None
        untracked = subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard"],
            cwd=str(root), capture_output=True, text=True,
            encoding="utf-8", errors="replace")
        names = [n for n in (tracked.stdout or "").splitlines() if n.strip()]
        names += [n for n in (untracked.stdout or "").splitlines() if n.strip()]
    except Exception:                                            # noqa: BLE001
        return None
    out: List[Path] = []
    for n in names:
        p = (root / n).resolve()
        if p.is_file():
            out.append(p)
    return out or []


def _candidates_from_walk(root: Path = ROOT) -> List[Path]:
    out: List[Path] = []
    for p in root.rglob("*"):
        if p.is_dir():
            continue
        rel = p.relative_to(root)
        if set(rel.parts[:-1]) & SKIP_DIRS:
            continue
        out.append(p)
    return out


def collect(root: Path = ROOT) -> List[Tuple[Path, int]]:
    files = _candidates_from_git(root)
    if files is None:
        files = _candidates_from_walk(root)
    rows: List[Tuple[Path, int]] = []
    for p in files:
        try:
            rows.append((p, p.stat().st_size))
        except OSError:
            continue
    return rows


def scan(max_bytes: int = MAX_FILE_BYTES, root: Path = ROOT) -> Dict[str, Any]:
    rows = collect(root)
    too_big: List[Dict[str, Any]] = []
    media: List[Dict[str, Any]] = []
    for p, size in rows:
        rel = str(p.relative_to(root)).replace("\\", "/")
        ext = _ext(p.name)
        kind = _media_kind(ext)
        if kind:
            media.append({"path": rel, "bytes": size, "kb": round(size / 1024, 1),
                          "kind": kind, "ext": ext})
        if size >= max_bytes:
            too_big.append({"path": rel, "bytes": size,
                            "mb": round(size / 1024 / 1024, 3), "ext": ext})

    biggest = sorted(rows, key=lambda r: r[1], reverse=True)[:10]
    findings = len(too_big) + len(media)
    guidance = []
    if too_big:
        guidance.append(
            f"有 {len(too_big)} 个文件达到或超过 "
            f"{max_bytes / 1024 / 1024:.0f} MB —— 不得提交。"
            "若其中的信息确有必要保留，请转为结构化数据（JSON 元数据）+ 外部引用，"
            "而不是把文件本身放进仓库。"
        )
    if media:
        kinds = sorted({m["kind"] for m in media})
        guidance.append(
            f"有 {len(media)} 个媒体/二进制文件（{'、'.join(kinds)}）—— 一律不入库。"
            "确实需要时，请在数据文件里记录其**外部位置与摘要**，由使用方按需获取。"
        )
    return {
        "root": str(root).replace("\\", "/"),
        "max_bytes": max_bytes,
        "files_scanned": len(rows),
        "total_bytes": sum(r[1] for r in rows),
        "total_mb": round(sum(r[1] for r in rows) / 1024 / 1024, 2),
        "oversize": too_big,
        "media": media,
        "findings": findings,
        "biggest": [{"path": str(p.relative_to(root)).replace("\\", "/"),
                     "kb": round(s / 1024, 1)} for p, s in biggest],
        "guidance": guidance,
        "conclusion": ("通过：无超限文件，无媒体/二进制文件" if findings == 0
                       else f"不通过：{findings} 项待处理"),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="仓库资产守卫（大文件 / 媒体二进制）")
    ap.add_argument("--max-mb", type=float, default=1.0,
                    help="单个文件的上限（MB），默认 1.0")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--list", action="store_true", help="列出最大的 10 个文件")
    ap.add_argument("--distribution", action="store_true",
                    help="同时审计**最终安装包**（白名单产物），不只是仓库里的文件")
    a = ap.parse_args()

    rep = scan(int(a.max_mb * 1024 * 1024))
    if a.distribution:
        # 仓库干净不等于分发包干净：白名单产物才是真正发出去的那一堆。
        # 判据与 `python -m omniarchitect package` 同一份（omniarchitect.packaging）。
        sys.path.insert(0, str(ROOT))
        from omniarchitect import packaging
        dist = packaging.audit(ROOT)
        rep["distribution"] = {
            "ok": dist["ok"],
            "file_count": dist["file_count"],
            "total_mb": dist["total_mb"],
            "largest": dist["largest"],
            "violations": dist["violations"],
        }
        rep["findings"] += len(dist["violations"])
        rep["conclusion"] = (
            "通过：无超限文件，无媒体/二进制文件，分发包干净"
            if rep["findings"] == 0 else f"不通过：{rep['findings']} 项待处理")

    if a.json:
        print(json.dumps(rep, ensure_ascii=False, indent=2))
        return 0 if rep["findings"] == 0 else 1

    print("仓库资产守卫 —— 大文件与媒体二进制")
    print(f"  项目根：{rep['root']}")
    print(f"  扫描文件：{rep['files_scanned']} 个 / 合计 {rep['total_mb']} MB")
    print(f"  上限：{rep['max_bytes'] // 1024 // 1024} MB")
    if "distribution" in rep:
        d = rep["distribution"]
        print(f"  分发包：{d['file_count']} 个文件 / {d['total_mb']} MB　"
              + ("干净" if d["ok"] else f"{len(d['violations'])} 项违规"))
        for v in d["violations"][:8]:
            print(f"    [{v['rule']}] {v['detail']}")

    if a.list or rep["findings"] == 0:
        print("  最大的文件：")
        for b in rep["biggest"]:
            print(f"    {b['kb']:>9.1f} KB  {b['path']}")

    if rep["oversize"]:
        print(f"\n  ! 超限文件（≥ {rep['max_bytes'] // 1024 // 1024} MB）：")
        for f in rep["oversize"]:
            print(f"    {f['mb']:>9.3f} MB  {f['path']}")
    if rep["media"]:
        print(f"\n  ! 媒体/二进制文件（一律不入库）：")
        for m in rep["media"][:30]:
            print(f"    {m['kb']:>9.1f} KB  [{m['kind']}]  {m['path']}")
        if len(rep["media"]) > 30:
            print(f"    …… 另有 {len(rep['media']) - 30} 个")

    for g in rep["guidance"]:
        print(f"\n  → {g}")

    print(f"\n  结论：{rep['conclusion']}")
    return 0 if rep["findings"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
