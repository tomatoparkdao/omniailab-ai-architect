"""Installer: put OmniArchitect into an Agent runtime without touching anything else.

Design rules
------------
* **Never destructive.** An existing installation is moved aside to a timestamped
  backup, never deleted. `uninstall` moves it aside too.
* **Dry-run first.** `plan()` shows every action before a single byte moves.
* **Whitelist, not blacklist.** What ships is declared in
  `omniarchitect.packaging`; anything not declared never enters the package —
  including files that happen to sit in the repo after a demo run.
* **Verifiable.** After installing, the entry point is re-parsed, the pointer is
  resolved back to a real checkout, and the copied tree is audited for
  generated artefacts. The report says whether it worked.
* **Standalone by default.** No platform account, no key, no network.

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import json
import os
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from .. import packaging
from ..paths import ROOT
from . import agent_skills as sk

SKILL_DIR_NAME = "omniailab-ai-architect"
POINTER_NAME = "omniailab-home.txt"
MANIFEST_NAME = "manifest.json"
BACKUP_DIR = "_backup"

MODE_POINTER = "pointer"
MODE_COPY = "copy"

#: 仅用于门面判断（白名单在 packaging 里）。保留名字是为了兼容老调用方。
EXCLUDE_DIRS = packaging.DIST_SKIP_DIR_NAMES
EXCLUDE_SUFFIX = {".pyc", ".pyo"}


@dataclass
class Action:
    kind: str          # mkdir | copy | write | backup | skip | keep
    source: str = ""
    target: str = ""
    note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {"action": self.kind, "source": self.source,
                "target": self.target, "note": self.note}


@dataclass
class InstallReport:
    target: str = ""
    mode: str = ""
    dry_run: bool = True
    actions: List[Action] = field(default_factory=list)
    backed_up: List[str] = field(default_factory=list)
    installed: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    verification: Dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not self.errors and bool(self.verification.get("ok", not self.dry_run))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target": self.target, "mode": self.mode, "dry_run": self.dry_run,
            "ok": self.ok,
            "actions": [a.to_dict() for a in self.actions],
            "backed_up": list(self.backed_up),
            "installed": list(self.installed),
            "errors": list(self.errors),
            "verification": dict(self.verification),
        }


def _payload(root: Path) -> List[Path]:
    """正式分发文件：白名单决定，不看目录里"还剩什么"。"""
    return packaging.distribution_files(root)


class Installer:
    def __init__(self, source: str | Path | None = ROOT,
                 target: str | Path | None = None,
                 mode: str = MODE_POINTER) -> None:
        self.source = Path(os.path.expanduser(str(source))) if source else ROOT
        self.target = Path(os.path.expanduser(str(target))) if target else None
        if mode not in (MODE_POINTER, MODE_COPY):
            raise ValueError(f"未知安装模式 {mode!r}")
        self.mode = mode

    # ------------------------------------------------------------------
    def resolve_target(self, project_dir: str | Path | None = None) -> Path:
        """`--target` is the runtime's *skills root*; the skill dir is appended.

        Passing the skill directory itself is also accepted, so both
        `~/.codex/skills` and `~/.codex/skills/omniailab-ai-architect` do what
        the user means — and neither can overwrite the skills root.
        """
        if self.target:
            t = Path(os.path.expanduser(str(self.target)))
            return t if t.name == SKILL_DIR_NAME else (t / SKILL_DIR_NAME)
        auto = sk.default_target(project_dir or self.source)
        if auto:
            return Path(auto) / SKILL_DIR_NAME
        raise RuntimeError(
            "未检测到任何 Agent 运行环境；请显式指定 --target 目录。"
            f"已知目标：{', '.join(sorted(sk.KNOWN_TARGETS))}"
        )

    def plan(self, project_dir: str | Path | None = None) -> InstallReport:
        dest = self.resolve_target(project_dir)
        rep = InstallReport(target=str(dest), mode=self.mode, dry_run=True)

        rep.actions.append(Action("mkdir", target=str(dest.parent),
                                  note="技能目录（已存在则保留）"))
        if dest.exists():
            backup = dest.parent / BACKUP_DIR / f"{SKILL_DIR_NAME}-{_stamp()}"
            rep.actions.append(Action("backup", source=str(dest),
                                      target=str(backup),
                                      note="已存在安装 → 先备份再覆盖，绝不删除"))
        rep.actions.append(Action("copy", source="SKILL.md",
                                  target=str(dest / "SKILL.md"),
                                  note="Agent Skills 入口（始终复制）"))
        if self.mode == MODE_POINTER:
            rep.actions.append(Action(
                "write", source=str(self.source),
                target=str(dest / POINTER_NAME),
                note="指针安装：真实工具链留在原仓库，不复制知识库与脚本"))
            rep.actions.append(Action(
                "write", target=str(dest / MANIFEST_NAME),
                note="安装清单（含版本与来源校验）"))
        else:
            files = _payload(self.source)
            size = sum(f.stat().st_size for f in files if f.exists())
            rep.actions.append(Action(
                "copy", source=str(self.source), target=str(dest),
                note=f"白名单复制 {len(files)} 个文件 / {size / 1024 / 1024:.2f} MB"
                     "（不含项目、测试、开发脚本、缓存）"))
            for f in files[:40]:
                rep.actions.append(Action("copy", source=str(f.relative_to(self.source)),
                                          target=str(dest / f.relative_to(self.source))))
            if len(files) > 40:
                rep.actions.append(Action("copy", note=f"…其余 {len(files) - 40} 个文件"))
        return rep

    # ------------------------------------------------------------------
    def install(self, project_dir: str | Path | None = None,
                dry_run: bool = False) -> InstallReport:
        rep = self.plan(project_dir)
        rep.dry_run = dry_run
        if dry_run:
            return rep

        dest = Path(rep.target)
        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            if dest.exists():
                backup = dest.parent / BACKUP_DIR / f"{SKILL_DIR_NAME}-{_stamp()}"
                backup.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(dest), str(backup))
                rep.backed_up.append(str(backup))
            dest.mkdir(parents=True, exist_ok=True)

            shutil.copy2(self.source / "SKILL.md", dest / "SKILL.md")
            rep.installed.append(str(dest / "SKILL.md"))

            if self.mode == MODE_POINTER:
                (dest / POINTER_NAME).write_text(
                    str(self.source) + "\n", encoding="utf-8")
                rep.installed.append(str(dest / POINTER_NAME))
            else:
                for f in _payload(self.source):
                    rel = f.relative_to(self.source)
                    t = dest / rel
                    t.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(f, t)
                    rep.installed.append(str(t))

            sk.write_manifest(dest / MANIFEST_NAME, self.source, with_hashes=True)
            rep.installed.append(str(dest / MANIFEST_NAME))
        except Exception as exc:
            rep.errors.append(f"{type(exc).__name__}: {exc}")
            return rep

        rep.verification = verify(dest)
        if not rep.verification.get("ok"):
            rep.errors.extend(rep.verification.get("errors", []))
        return rep

    # ------------------------------------------------------------------
    def uninstall(self, project_dir: str | Path | None = None,
                  dry_run: bool = False) -> Dict[str, Any]:
        dest = self.resolve_target(project_dir)
        if not dest.exists():
            return {"ok": True, "removed": False, "target": str(dest),
                    "note": "目标不存在，无需卸载"}
        backup = dest.parent / BACKUP_DIR / f"{SKILL_DIR_NAME}-uninstalled-{_stamp()}"
        if dry_run:
            return {"ok": True, "dry_run": True, "target": str(dest),
                    "would_move_to": str(backup),
                    "note": "卸载只移不删：内容会保留在备份目录"}
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(dest), str(backup))
        return {"ok": True, "removed": True, "target": str(dest),
                "moved_to": str(backup),
                "note": "已移入备份目录，未删除任何内容"}


# --------------------------------------------------------------------------
def verify(target: str | Path) -> Dict[str, Any]:
    """Re-read an installed skill and resolve it back to a working checkout."""
    dest = Path(os.path.expanduser(str(target)))
    errs: List[str] = []
    out: Dict[str, Any] = {"target": str(dest), "ok": False, "errors": errs}
    if not dest.exists():
        errs.append(f"安装目录不存在：{dest}")
        return out

    skill = dest / "SKILL.md"
    if not skill.exists():
        errs.append("缺少 SKILL.md")
    else:
        issues = sk.validate(skill)
        out["skill_issues"] = issues
        errs.extend(i for i in issues if "引用不存在" not in i)
        out["skill"] = sk.parse(skill).to_dict()

    pointer = dest / POINTER_NAME
    if pointer.exists():
        home = Path(pointer.read_text(encoding="utf-8").strip())
        out["home"] = str(home)
        out["home_exists"] = home.exists()
        pkg = home / "omniarchitect" / "__init__.py"
        out["package_found"] = pkg.exists()
        if not home.exists():
            errs.append(f"指针指向的仓库不存在：{home}")
        elif not pkg.exists():
            errs.append(f"指针指向的目录不是 OmniArchitect 仓库：{home}")
        else:
            skills = home / "knowledge" / "INDEX.md"
            out["knowledge_found"] = skills.exists()
    else:
        out["mode"] = "copy"
        out["knowledge_found"] = (dest / "knowledge" / "INDEX.md").exists()

    mf = dest / MANIFEST_NAME
    if mf.exists():
        try:
            data = json.loads(mf.read_text(encoding="utf-8"))
            out["manifest_skill"] = data.get("skill", {}).get("name", "")
            out["manifest_files"] = data.get("file_count")
            out["manifest_issues"] = data.get("issues", [])
            listed = {str(r.get("path", "")).replace("\\", "/")
                      for r in data.get("files", [])}
            listed.discard("")
            if out.get("mode") == "copy":
                # 只有 copy 模式才该在本地看到全部清单文件。pointer 模式的清单
                # 描述的是"指向的那个仓库发什么"，本地只有 3 个文件，属正常。
                missing = sorted(p for p in listed if not (dest / p).exists())
                actual = {str(p.relative_to(dest)).replace("\\", "/")
                          for p in dest.rglob("*") if p.is_file()}
                unlisted = sorted(p for p in actual - listed
                                  if p != MANIFEST_NAME
                                  and not p.endswith("/manifest.json"))
                out["manifest_missing"] = missing[:10]
                out["unlisted_files"] = unlisted[:10]
                if missing:
                    errs.append(f"清单登记但安装目录缺失 {len(missing)} 个文件：{missing[:5]}")
                if unlisted:
                    errs.append(f"安装目录有 {len(unlisted)} 个文件未登记进清单：{unlisted[:5]}")
        except Exception as exc:
            errs.append(f"manifest 损坏：{exc}")
    else:
        errs.append("缺少 manifest.json")

    # 装完之后再查一遍"里面有没有生成物"——白名单是第一道防线，
    # 这里是不信任自己的第二道。
    tree = packaging.audit_tree(dest)
    out["payload_issues"] = tree["violations"]
    if not tree["ok"]:
        errs.extend(f"安装目录混入不该分发的文件：{v['detail']}"
                    for v in tree["violations"][:5])
    out["installed_files"] = tree["file_count"]
    out["installed_mb"] = tree["total_mb"]

    out["ok"] = not errs
    return out


def _stamp() -> str:
    return time.strftime("%Y%m%d-%H%M%S")


def install(target: str | Path | None = None, source: str | Path = ROOT,
            mode: str = MODE_POINTER, dry_run: bool = False,
            project_dir: str | Path | None = None) -> Dict[str, Any]:
    inst = Installer(source=source, target=target, mode=mode)
    return inst.install(project_dir=project_dir, dry_run=dry_run).to_dict()


def plan(target: str | Path | None = None, source: str | Path = ROOT,
         mode: str = MODE_POINTER, project_dir: str | Path | None = None) -> Dict[str, Any]:
    return Installer(source=source, target=target, mode=mode).plan(project_dir).to_dict()


__all__ = [
    "Installer", "InstallReport", "Action", "verify", "install", "plan",
    "MODE_POINTER", "MODE_COPY", "SKILL_DIR_NAME", "POINTER_NAME", "MANIFEST_NAME",
]
