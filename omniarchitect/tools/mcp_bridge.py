"""MCP bridge: turn a design intent into a tool call, or say plainly it is not wired.

`tools/registry.py` already answers one question — "is an MCP server configured?"
That is not the question the design flow asks. The flow needs:

    现在要画一张平面图。这条指令现在能不能真的发出去？
    发不出去时，本地能出什么深度的替代品，差在哪？

So this module does exactly three things:

1. Declares, per professional role, which tools a server *should* expose
   (`CONTRACTS`). A server that only half-implements the contract is reported
   as `partial`, never as `available`.
2. Speaks the actual protocol — JSON-RPC over stdio (`initialize` →
   `tools/list` → `tools/call`) — so "available" means a real handshake
   happened, not that a path exists on disk.
3. On failure returns `not_configured` plus a job package that a human can run.
   It never fabricates a successful call, a screenshot, or a model file.

Nothing here guesses a tool name either: servers differ, so a contract entry
lists acceptable aliases and the configure file may pin one explicitly.

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

PROTOCOL_VERSION = "2024-11-05"

#: What each professional role must be able to do through MCP.
#: `aliases` is a name-matching hint only — the server's real list wins.
CONTRACTS: Dict[str, Dict[str, Any]] = {
    "cad": {
        "label": "CAD MCP",
        "purpose": "按已确认空间模型绘制可编辑平面/立面/剖面并回写 DXF",
        "operations": {
            "draw_plan": {
                "aliases": ("draw_plan", "plan", "create_plan", "cad_draw_plan"),
                "needs": ("rooms", "walls", "level"),
                "produces": ("dxf",),
            },
            "draw_elevation": {
                "aliases": ("draw_elevation", "elevation", "create_elevation"),
                "needs": ("walls", "openings"),
                "produces": ("dxf",),
            },
            "draw_section": {
                "aliases": ("draw_section", "section", "create_section"),
                "needs": ("levels", "walls"),
                "produces": ("dxf",),
            },
            "export_dxf": {
                "aliases": ("export_dxf", "dxf", "save_dxf", "write_dxf"),
                "needs": ("geometry",),
                "produces": ("dxf",),
            },
        },
    },
    "sketchup": {
        "label": "SketchUp MCP",
        "purpose": "建概念体量与构件、出固定机位截图与线稿，供效果图做几何控制",
        "operations": {
            "create_walls": {
                "aliases": ("create_walls", "build_walls", "walls"),
                "needs": ("walls",),
                "produces": ("skp",),
            },
            "create_openings": {
                "aliases": ("create_openings", "openings", "cut_openings", "doors_windows"),
                "needs": ("openings",),
                "produces": ("skp",),
            },
            "capture_view": {
                "aliases": ("capture_view", "screenshot", "export_image", "render_view"),
                "needs": ("camera",),
                "produces": ("png",),
            },
            "export_obj": {
                "aliases": ("export_obj", "export_model", "save_obj", "export_skp"),
                "needs": ("scene",),
                "produces": ("obj", "skp"),
            },
        },
    },
}

#: State vocabulary — shared with the rest of the system, so reports stay honest.
AVAILABLE = "available"
PARTIAL = "partial"
NOT_CONFIGURED = "not_configured"


@dataclass
class ServerSpec:
    id: str
    transport: str = "stdio"
    command: str = ""
    args: List[str] = field(default_factory=list)
    url: str = ""
    env: Dict[str, str] = field(default_factory=dict)
    role: str = ""
    tool_aliases: Dict[str, str] = field(default_factory=dict)


@dataclass
class Proficiency:
    """Verdict for one professional role, with what is missing spelled out."""

    role: str
    label: str
    state: str
    server: str = ""
    transport: str = ""
    missing: List[str] = field(default_factory=list)
    resolved: Dict[str, str] = field(default_factory=dict)
    notes: List[str] = field(default_factory=list)
    error: str = ""

    @property
    def usable(self) -> bool:
        return self.state in (AVAILABLE, PARTIAL)

    def op_tool(self, operation: str) -> Optional[str]:
        return self.resolved.get(operation)

    def to_dict(self) -> Dict[str, Any]:
        return {"role": self.role, "label": self.label, "state": self.state,
                "server": self.server, "transport": self.transport,
                "missing": list(self.missing), "resolved": dict(self.resolved),
                "notes": list(self.notes), "error": self.error}


# ----------------------------------------------------------------------
# configuration
# ----------------------------------------------------------------------
def config_path(project_dir: str | Path | None = None,
                override: str | Path | None = None) -> Optional[Path]:
    """Find an mcp.json: explicit path, project dir, then the skill root."""
    if override:
        p = Path(override)
        return p if p.exists() else None
    candidates = []
    if project_dir:
        candidates.append(Path(project_dir) / "mcp.json")
    candidates.append(Path(__file__).resolve().parents[2] / "mcp.json")
    for p in candidates:
        if p.exists():
            return p
    return None


def _pick_role(sid: str, spec: Dict[str, Any]) -> str:
    """Infer the role from an explicit `role` key, else from the server name."""
    role = str(spec.get("role") or "").strip().lower()
    if role in CONTRACTS:
        return role
    name = sid.lower()
    if "sketchup" in name or name in ("su", "skp"):
        return "sketchup"
    if "cad" in name or "autocad" in name or "dxf" in name:
        return "cad"
    return ""


def load_servers(project_dir: str | Path | None = None,
                 override: str | Path | None = None) -> Dict[str, ServerSpec]:
    path = config_path(project_dir, override)
    if path is None:
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:                     # noqa: BLE001  配置坏了就当没配
        return {}
    servers = data.get("mcpServers") or data.get("servers") or {}
    out: Dict[str, ServerSpec] = {}
    for sid, raw in servers.items():
        spec = raw or {}
        out[sid] = ServerSpec(
            id=sid,
            transport="stdio" if spec.get("command") else ("http" if spec.get("url") else "none"),
            command=str(spec.get("command") or ""),
            args=[str(a) for a in (spec.get("args") or [])],
            url=str(spec.get("url") or ""),
            env={str(k): str(v) for k, v in (spec.get("env") or {}).items()},
            role=_pick_role(sid, spec),
            tool_aliases={str(k): str(v) for k, v in (spec.get("toolAliases") or {}).items()},
        )
    return out


# ----------------------------------------------------------------------
# stdio JSON-RPC client
# ----------------------------------------------------------------------
class StdioClient:
    """A minimal MCP client: initialize, tools/list, tools/call.

    Deliberately small. It does not try to be a full SDK — but everything it
    reports (a handshake, a tool list, a call result) actually happened.
    """

    def __init__(self, spec: ServerSpec, timeout: float = 20.0) -> None:
        self.spec = spec
        self.timeout = timeout
        self._proc: Optional[subprocess.Popen] = None
        self._seq = 0

    # -- lifecycle -------------------------------------------------------
    def start(self) -> None:
        if self._proc is not None:
            return
        exe = shutil.which(self.spec.command) or (
            self.spec.command if Path(self.spec.command).exists() else None)
        if not exe:
            raise RuntimeError(f"命令不可解析：{self.spec.command!r}")
        env = os.environ.copy()
        env.update(self.spec.env)
        self._proc = subprocess.Popen(
            [exe, *self.spec.args],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, encoding="utf-8", errors="replace", env=env, bufsize=1,
        )

    def close(self) -> None:
        proc, self._proc = self._proc, None
        if proc is None:
            return
        try:
            if proc.stdin:
                proc.stdin.close()
            proc.terminate()
            proc.wait(timeout=3)
        except Exception:                 # noqa: BLE001  关不掉也不该拖垮流程
            try:
                proc.kill()
            except Exception:             # noqa: BLE001
                pass

    def __enter__(self) -> "StdioClient":
        self.start()
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()

    # -- rpc -------------------------------------------------------------
    def _send(self, method: str, params: Optional[Dict[str, Any]] = None,
              notify: bool = False) -> Dict[str, Any]:
        if self._proc is None or self._proc.stdin is None or self._proc.stdout is None:
            raise RuntimeError("服务器未启动")
        msg: Dict[str, Any] = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            msg["params"] = params
        if not notify:
            self._seq += 1
            msg["id"] = self._seq
        self._proc.stdin.write(json.dumps(msg, ensure_ascii=False) + "\n")
        self._proc.stdin.flush()
        if notify:
            return {}
        deadline = time.time() + self.timeout
        while time.time() < deadline:
            line = self._proc.stdout.readline()
            if not line:
                break
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue                  # 服务端日志混进 stdout 时跳过
            if data.get("id") == self._seq:
                if "error" in data:
                    raise RuntimeError(str(data["error"].get("message") or data["error"]))
                return data.get("result") or {}
        raise TimeoutError(f"{method} 无响应（{self.timeout:.0f}s）")

    def initialize(self) -> Dict[str, Any]:
        result = self._send("initialize", {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {"roots": {"listChanged": False}, "tools": {}},
            "clientInfo": {"name": "omniailab-ai-architect", "version": "1"},
        })
        self._send("notifications/initialized", {}, notify=True)
        return result

    def list_tools(self) -> List[Dict[str, Any]]:
        try:
            result = self._send("tools/list", {})
        except Exception:                 # noqa: BLE001  有些服务端不支持分页参数
            result = {}
        tools = result.get("tools") or []
        return [t for t in tools if isinstance(t, dict)]

    def call(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        return self._send("tools/call", {"name": name, "arguments": arguments})


# ----------------------------------------------------------------------
# probing
# ----------------------------------------------------------------------
def _match_tool(op: str, spec: ServerSpec, offered: Sequence[str]) -> Optional[str]:
    """Resolve a contract operation to a real tool name.

    Order: explicit alias in mcp.json → exact match → declared aliases →
    case-insensitive contains (last resort, but reported in notes).
    """
    pinned = spec.tool_aliases.get(op)
    if pinned and pinned in offered:
        return pinned
    if op in offered:
        return op
    for alias in CONTRACTS[spec.role]["operations"][op]["aliases"]:
        if alias in offered:
            return alias
    low = {t.lower(): t for t in offered}
    for alias in CONTRACTS[spec.role]["operations"][op]["aliases"]:
        for name in low:
            if alias in name:
                return low[name]
    return None


def probe(role: str, project_dir: str | Path | None = None,
          override: str | Path | None = None,
          timeout: float = 15.0) -> Proficiency:
    """Handshake for real, then judge the contract. Never assumes a tool set."""
    contract = CONTRACTS[role]
    prof = Proficiency(role=role, label=contract["label"], state=NOT_CONFIGURED)
    servers = load_servers(project_dir, override)
    candidates = [s for s in servers.values() if s.role == role]
    if not candidates:
        prof.notes.append(
            f"未找到 role={role} 的 MCP 服务器；在 mcp.json 里加一项并显式写 "
            f"\"role\": \"{role}\"（模板见 mcp.json.example）")
        prof.missing = list(contract["operations"])
        return prof

    spec = candidates[0]
    prof.server, prof.transport = spec.id, spec.transport
    if spec.transport != "stdio":
        prof.state = NOT_CONFIGURED
        prof.error = "只实现了 stdio 握手；HTTP MCP 未做连通性探测"
        prof.missing = list(contract["operations"])
        prof.notes.append(f"url: {spec.url}（不猜测鉴权方式）")
        return prof

    try:
        with StdioClient(spec, timeout=timeout) as client:
            client.initialize()
            tools = client.list_tools()
    except Exception as exc:              # noqa: BLE001  连不上是常态，不是崩溃
        prof.state = NOT_CONFIGURED
        prof.error = f"{type(exc).__name__}: {exc}"
        prof.missing = list(contract["operations"])
        return prof

    offered = [str(t.get("name")) for t in tools if t.get("name")]
    for op in contract["operations"]:
        hit = _match_tool(op, spec, offered)
        if hit:
            prof.resolved[op] = hit
        else:
            prof.missing.append(op)
    if not prof.resolved:
        prof.state = NOT_CONFIGURED
        prof.notes.append(f"握手成功，但没有任何契约内的工具；服务器提供：{offered[:8]}")
    elif prof.missing:
        prof.state = PARTIAL
        prof.notes.append(f"已解析 {len(prof.resolved)} 个工具，缺：{prof.missing}")
    else:
        prof.state = AVAILABLE
    return prof


def probe_all(project_dir: str | Path | None = None,
              override: str | Path | None = None) -> Dict[str, Proficiency]:
    return {role: probe(role, project_dir, override) for role in CONTRACTS}


# ----------------------------------------------------------------------
# calling
# ----------------------------------------------------------------------
@dataclass
class CallResult:
    ok: bool
    state: str
    operation: str
    tool: str = ""
    content: Any = None
    error: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {"ok": self.ok, "state": self.state, "operation": self.operation,
                "tool": self.tool, "error": self.error,
                "content": self.content if self.ok else None}


def call(role: str, operation: str, arguments: Dict[str, Any],
         project_dir: str | Path | None = None,
         override: str | Path | None = None,
         approved: bool = False) -> CallResult:
    """Invoke one contract operation. Refuses rather than pretends.

    `approved` mirrors the tool-permission model: drawing and modelling change
    the project, so an unapproved call returns `needs_approval` instead of
    silently running.
    """
    contract = CONTRACTS.get(role)
    if contract is None:
        return CallResult(False, NOT_CONFIGURED, operation,
                          error=f"未知专业角色 {role!r}")
    if operation not in contract["operations"]:
        return CallResult(False, NOT_CONFIGURED, operation,
                          error=f"{contract['label']} 未声明操作 {operation!r}")
    if not approved:
        return CallResult(False, "needs_approval", operation,
                          error="该操作会改动项目成果，需显式授权（approved=True）")
    prof = probe(role, project_dir, override)
    if not prof.usable:
        return CallResult(False, prof.state, operation, error=prof.error or "未连接")
    tool = prof.op_tool(operation)
    if not tool:
        return CallResult(False, PARTIAL, operation,
                          error=f"{contract['label']} 缺操作 {operation}")
    servers = load_servers(project_dir, override)
    spec = servers.get(prof.server)
    if spec is None:
        return CallResult(False, NOT_CONFIGURED, operation, error="服务器配置已消失")
    try:
        with StdioClient(spec) as client:
            client.initialize()
            result = client.call(tool, arguments)
    except Exception as exc:              # noqa: BLE001
        return CallResult(False, NOT_CONFIGURED, operation, tool=tool,
                          error=f"{type(exc).__name__}: {exc}")
    return CallResult(True, prof.state, operation, tool=tool, content=result)


# ----------------------------------------------------------------------
# job packages
# ----------------------------------------------------------------------
def job_package(role: str, operation: str, arguments: Dict[str, Any],
                prof: Proficiency, target: Path) -> Dict[str, Any]:
    """A runnable description of what a human would do by hand.

    This is what gets written when the server is missing, so the work is not
    lost: the payload is the exact one that would have been sent.
    """
    contract = CONTRACTS[role]
    payload = {
        "role": role,
        "label": contract["label"],
        "operation": operation,
        "state": prof.state,
        "server": prof.server,
        "reason": prof.error or "；".join(prof.notes) or "未配置",
        "expected_tool": prof.op_tool(operation) or "",
        "expected_tool_aliases": list(
            contract["operations"][operation]["aliases"]),
        "arguments": arguments,
        "how_to_run": [
            f"1. 在项目目录的 mcp.json 里登记 {contract['label']}（\"role\": \"{role}\"）",
            "2. 启动该服务器并确认工具名，必要时用 toolAliases 固定映射",
            "3. 重跑本阶段；或用下面的 arguments 手工调用同名工具",
        ],
        "written_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def status(project_dir: str | Path | None = None,
           override: str | Path | None = None) -> Dict[str, Any]:
    """One-call status for CLI and stage notes."""
    profs = probe_all(project_dir, override)
    path = config_path(project_dir, override)
    return {
        "config": str(path) if path else "",
        "servers": {k: v.to_dict() for k, v in profs.items()},
        "usable": [k for k, v in profs.items() if v.usable],
        "not_configured": [k for k, v in profs.items() if not v.usable],
    }


__all__ = ["CONTRACTS", "AVAILABLE", "PARTIAL", "NOT_CONFIGURED",
           "StdioClient", "Proficiency", "CallResult", "ServerSpec",
           "config_path", "load_servers", "probe", "probe_all", "call",
           "job_package", "status"]
