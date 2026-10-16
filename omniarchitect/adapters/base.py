"""Adapter contract.

Every external tool is reached through an adapter that must answer a preflight
question first: *does this tool exist on this host, and what can it actually
do?* A tool is never presumed present. When it is missing the adapter returns a
degraded deliverable and says so — it never fabricates success.

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import json
import platform
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from ..errors import AdapterUnavailable
from ..model import Project


@dataclass
class Capability:
    """What an adapter can actually do on this host, right now."""

    name: str
    available: bool
    version: str = ""
    executable: str = ""
    operations: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    degraded_to: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "adapter": self.name,
            "available": self.available,
            "version": self.version,
            "executable": self.executable,
            "operations": self.operations,
            "degraded_to": self.degraded_to,
            "notes": self.notes,
        }


@dataclass
class AdapterResult:
    adapter: str
    ok: bool
    artifacts: List[str] = field(default_factory=list)
    revision: int = 0
    log: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    validation: Dict[str, Any] = field(default_factory=dict)
    authoritative: bool = True
    """False for anything derived from a generative model: renders, walkthroughs."""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "adapter": self.adapter,
            "ok": self.ok,
            "artifacts": list(self.artifacts),
            "revision": self.revision,
            "log": list(self.log),
            "errors": list(self.errors),
            "validation": dict(self.validation),
            "authoritative": self.authoritative,
        }


class Adapter:
    """Base class. Subclasses implement `preflight` and one or more operations."""

    name = "adapter"
    tool = "?"

    def preflight(self) -> Capability:  # pragma: no cover - overridden
        raise NotImplementedError

    # -- helpers -----------------------------------------------------------
    @staticmethod
    def which(*names: str) -> Optional[str]:
        for n in names:
            p = shutil.which(n)
            if p:
                return p
        return None

    @staticmethod
    def write_json(path: Path, payload: Any) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    @staticmethod
    def host_info() -> Dict[str, str]:
        return {
            "platform": platform.platform(),
            "python": sys.version.split()[0],
            "machine": platform.machine(),
        }


class SubprocessAdapter(Adapter):
    """Adapter whose work is performed by an external executable."""

    search_names: Sequence[str] = ()

    def preflight(self) -> Capability:  # pragma: no cover - overridden
        raise NotImplementedError

    def run_script(self, script: Path, args: Sequence[str] = ()) -> AdapterResult:
        import subprocess

        cap = self.preflight()
        if not cap.available:
            raise AdapterUnavailable(self.name, f"{self.tool} not found on this host")
        cmd = [cap.executable, str(script), *args]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
        res = AdapterResult(adapter=self.name, ok=proc.returncode == 0)
        res.log.append(" ".join(cmd))
        if proc.stdout:
            res.log.extend(proc.stdout.splitlines()[-40:])
        if proc.returncode != 0:
            res.errors.append(proc.stderr.strip()[-2000:] or f"exit code {proc.returncode}")
        return res
