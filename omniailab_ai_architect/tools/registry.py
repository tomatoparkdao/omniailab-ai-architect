"""Unified tool registry.

One place that answers three questions before any work is done:

1. **What can run here?**   -> `detect()` probes each tool for real.
2. **May it run?**           -> `guard()` enforces the L1–L4 risk tiers.
3. **Did it really work?**   -> `verify()` re-opens the artifact with an
                              independent parser. A tool never audits itself.

MCP servers are *declared*, never guessed. The registry reads a
`mcpServers`-shaped JSON file (project `mcp.json`, or an explicit path) and
reports each server as `available` (its command resolves on this host),
`not_configured` (declared but the command is missing), or absent (not
declared at all). It never invents a command, an endpoint or an auth scheme.
"""
from __future__ import annotations

import json
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence

from ..adapters import all_adapters
from ..paths import ROOT
from .capability import (
    ARTIFACT_KIND_CEILING,
    RISK_TIERS,
    CapabilityViolation,
    Operation,
    PermissionRequired,
    ToolCapability,
    interpreter,
    probe_executable,
)

# --------------------------------------------------------------------------
# What each built-in adapter is allowed to claim. Risk tiers are declared
# statically on purpose: a tool cannot raise its own privilege at runtime.
BUILTIN_OPERATIONS: Dict[str, List[Operation]] = {
    "dxf": [
        Operation("draw_plan", "L2", "由统一空间模型绘制平面图，写出 DXF（R12 或 R2010）",
                  produces=["dxf"]),
        Operation("audit", "L1", "独立复核已写出的 DXF", verifiable=False),
        Operation("read_back", "L1", "独立解析 DXF，返回实体/图层统计", verifiable=False),
    ],
    "mesh": [
        Operation("build", "L2", "由空间模型构建三角网格", produces=["obj"]),
        Operation("export", "L2", "导出 OBJ/MTL", produces=["obj"]),
    ],
    "blender": [
        Operation("emit_script", "L2", "生成可在 Blender 运行的场景构建脚本",
                  produces=["py"], verifiable=False),
        Operation("run_blender", "L4", "在宿主上执行 Blender 批处理",
                  destructive=False, reversible=False, produces=["png", "glb"]),
    ],
    "freecad": [
        Operation("emit_script", "L2", "生成 FreeCAD 参数化建模脚本",
                  produces=["py"], verifiable=False),
        Operation("run_freecad", "L4", "在宿主上执行 FreeCAD 批处理",
                  destructive=False, reversible=False, produces=["ifc", "step"]),
    ],
    "ifc": [
        Operation("emit_projection", "L2", "输出 IFC 投影数据与生成脚本",
                  produces=["json"]),
        Operation("write_ifc", "L2", "写出 IFC 文件", produces=["ifc"]),
    ],
    "render": [
        Operation("compose_shots", "L2", "编排一致机位的表现任务包", produces=["json"]),
        Operation("render_local", "L2", "本地合成示意图（非写实渲染）",
                  produces=["png"]),
        Operation("render_ai", "L3", "调用外部模型 provider 生成表现图",
                  produces=["png", "jpg"]),
    ],
}

BUILTIN_LIMITS: Dict[str, List[str]] = {
    "dxf": ["DXF ≠ DWG：需要 DWG 必须由具备许可的后端另存",
            "R12 后端不支持 HATCH 等实体，以等价线型表达"],
    "mesh": ["三角网格不是参数化 BIM：无构件语义与属性",
             "单位 mm、Z 轴向上；不得用作施工尺寸的唯一依据"],
    "blender": ["脚本只有在装有 Blender 的机器上才会真正执行",
                "执行属 L4：必须先 dry-run 再授权"],
    "freecad": ["脚本只有在装有 FreeCAD 的机器上才会真正执行"],
    "ifc": ["没有 IfcOpenShell 时只输出投影 JSON，不谎称写出了 IFC"],
    "render": ["生成式图像不保证尺寸与比例，不得作为施工尺寸依据",
               "本地合成图为示意图，明确标注非写实渲染"],
}

BUILTIN_ARTIFACTS: Dict[str, List[str]] = {
    "dxf": ["dxf"], "mesh": ["obj"], "blender": ["py", "png", "glb"],
    "freecad": ["py", "ifc"], "ifc": ["json", "ifc"], "render": ["json", "png"],
}

OPERATION_TOKEN = "__omni_operation__"


# --------------------------------------------------------------------------
@dataclass
class InvocationRecord:
    tool: str
    operation: str
    risk: str
    approved: bool
    dry_run: bool
    ok: bool = False
    artifacts: List[str] = field(default_factory=list)
    verification: List[Dict[str, Any]] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tool": self.tool, "operation": self.operation, "risk": self.risk,
            "approved": self.approved, "dry_run": self.dry_run, "ok": self.ok,
            "artifacts": list(self.artifacts), "verification": self.verification,
            "errors": list(self.errors),
        }


class ToolRegistry:
    """Discover, gate and verify every tool the system can drive."""

    def __init__(self, mcp_config: str | Path | None = None,
                 extra_configs: Sequence[str | Path] = ()) -> None:
        self.mcp_config = Path(mcp_config) if mcp_config else (ROOT / "mcp.json")
        self.extra_configs = [Path(p) for p in extra_configs]
        self._tools: Optional[Dict[str, ToolCapability]] = None
        self.log: List[InvocationRecord] = []

    # -- discovery -------------------------------------------------------
    def detect(self, refresh: bool = False) -> Dict[str, ToolCapability]:
        if self._tools is not None and not refresh:
            return self._tools
        tools: Dict[str, ToolCapability] = {}
        for adapter in all_adapters():
            cap = adapter.preflight()
            ops = BUILTIN_OPERATIONS.get(adapter.name, [])
            state = "available" if cap.available else "degraded"
            # `available` here means the adapter can *do something useful*.
            # When the real tool is missing the adapter still ships a degraded
            # deliverable — that is a reduced tool, not a configured one.
            if not cap.available and cap.degraded_to:
                state = "unavailable"
            tools[adapter.name] = ToolCapability(
                id=adapter.name,
                name=f"{cap.name} adapter",
                kind="python",
                transport="inprocess",
                availability=state,
                version=cap.version,
                executable=cap.executable,
                operations=list(ops),
                degraded_to=cap.degraded_to,
                notes=list(cap.notes),
                limits=list(BUILTIN_LIMITS.get(adapter.name, [])),
                verified=bool(cap.available) and adapter.name in ("dxf", "mesh"),
                verification="round-trip parse" if adapter.name in ("dxf", "mesh") else "",
            )
        for tid, cap in self._mcp_tools().items():
            if tid not in tools:
                tools[tid] = cap
        self._tools = tools
        return tools

    # -- MCP -------------------------------------------------------------
    def _mcp_tools(self) -> Dict[str, ToolCapability]:
        out: Dict[str, ToolCapability] = {}
        configs = [self.mcp_config, *self.extra_configs]
        for cfg in configs:
            if not cfg.exists():
                continue
            try:
                data = json.loads(cfg.read_text(encoding="utf-8"))
            except Exception as exc:
                out[f"mcp-config-error:{cfg.name}"] = ToolCapability(
                    id=f"mcp-config-error:{cfg.name}",
                    name=f"MCP 配置无法解析（{cfg}）", kind="mcp",
                    transport="none", availability="not_configured",
                    notes=[str(exc)],
                )
                continue
            servers = data.get("mcpServers") or data.get("servers") or {}
            for sid, spec in servers.items():
                command = (spec or {}).get("command") or ""
                url = (spec or {}).get("url") or ""
                if command:
                    exe = probe_executable([command]) or (
                        command if Path(command).exists() else None
                    )
                    state = "available" if exe else "not_configured"
                    transport = "stdio"
                    notes = [f"command: {command} {' '.join((spec or {}).get('args') or [])}"]
                    if not exe:
                        notes.append(f"命令 {command!r} 在本机不可解析——服务器不会启动")
                elif url:
                    state = "not_configured"
                    transport = "http"
                    notes = [f"url: {url}", "远端 MCP 未做连通性探测：不猜测鉴权方式"]
                else:
                    state = "not_configured"
                    transport = "none"
                    notes = ["配置项既无 command 也无 url"]
                out[sid] = ToolCapability(
                    id=sid,
                    name=f"MCP server: {sid}",
                    kind="mcp",
                    transport=transport,
                    availability=state,
                    executable=command or url,
                    operations=[],
                    notes=notes,
                    limits=[
                        "MCP 能力由服务器自身声明；未经握手前不假设其工具集",
                        "L3/L4 操作必须先确认再执行",
                    ],
                )
        return out

    # -- lookup / gating -------------------------------------------------
    def resolve(self, tool_id: str) -> ToolCapability:
        tools = self.detect()
        if tool_id not in tools:
            raise CapabilityViolation(f"未注册的工具 {tool_id!r}")
        return tools[tool_id]

    def guard(self, tool_id: str, operation: str, approved: bool = False,
              dry_run: bool = False) -> ToolCapability:
        cap = self.resolve(tool_id)
        cap.guard(operation, approved=approved, dry_run=dry_run)
        return cap

    def plan_call(self, tool_id: str, operation: str) -> Dict[str, Any]:
        """Describe a call without running it — what would happen, and the gate."""
        cap = self.resolve(tool_id)
        op = cap.operation(operation)
        if op is None:
            raise CapabilityViolation(f"{tool_id} 未声明操作 {operation!r}")
        return {
            "tool": tool_id,
            "operation": operation,
            "risk": op.risk,
            "risk_label": RISK_TIERS[op.risk]["label"],
            "approval_required": bool(RISK_TIERS[op.risk].get("approval")),
            "dry_run_required": bool(RISK_TIERS[op.risk].get("dry_run_first")),
            "availability": cap.availability,
            "produces": list(op.produces),
            "honest_description": [
                ARTIFACT_KIND_CEILING.get(k, k) for k in op.produces
            ],
            "limits": list(cap.limits),
        }

    def run(self, tool_id: str, operation: str, func: Callable[..., Any],
            approved: bool = False, dry_run: bool = False,
            verify: bool = True, **kwargs: Any) -> InvocationRecord:
        """Execute a guarded call and verify whatever it produced."""
        cap = self.guard(tool_id, operation, approved=approved, dry_run=dry_run)
        op = cap.operation(operation)
        assert op is not None
        rec = InvocationRecord(tool=tool_id, operation=operation, risk=op.risk,
                               approved=approved, dry_run=dry_run)
        try:
            result = func(**kwargs)
        except Exception as exc:
            rec.errors.append(f"{type(exc).__name__}: {exc}")
            self.log.append(rec)
            return rec

        arts: List[str] = []
        ok = True
        if hasattr(result, "artifacts"):
            arts = [str(a) for a in result.artifacts]
            ok = bool(getattr(result, "ok", True))
            if getattr(result, "errors", None):
                rec.errors.extend(str(e) for e in result.errors)
        elif isinstance(result, (str, Path)):
            arts = [str(result)]
        elif isinstance(result, (list, tuple)):
            arts = [str(a) for a in result]
        rec.artifacts = arts
        rec.ok = ok
        if verify:
            for a in arts:
                rep = self.verify(a)
                if rep:
                    rec.verification.append(rep)
                    if not rep.get("ok", True):
                        rec.ok = False
                        rec.errors.extend(rep.get("errors", []))
        self.log.append(rec)
        return rec

    # -- verification ----------------------------------------------------
    def verify(self, path: str | Path) -> Optional[Dict[str, Any]]:
        """Re-open an artifact with an independent parser."""
        p = Path(path)
        if not p.exists():
            return {"ok": False, "file": str(p), "checker": "existence",
                    "errors": ["file does not exist"]}
        ext = p.suffix.lower().lstrip(".")
        checker = VERIFIERS.get(ext)
        if not checker:
            size = p.stat().st_size
            return {"ok": size > 0, "file": str(p), "checker": f"size-only({ext})",
                    "stats": {"size_bytes": size},
                    "errors": [] if size > 0 else ["empty file"]}
        try:
            rep = checker(p)
        except Exception as exc:
            return {"ok": False, "file": str(p), "checker": ext,
                    "errors": [f"{type(exc).__name__}: {exc}"]}
        rep.setdefault("file", str(p))
        rep.setdefault("checker", ext)
        return rep

    # -- reporting -------------------------------------------------------
    def detect_report(self) -> Dict[str, Any]:
        tools = self.detect(refresh=True)
        return {
            "interpreter": interpreter(),
            "tools": [t.to_dict() for t in tools.values()],
            "available": sorted(t.id for t in tools.values() if t.availability == "available"),
            "degraded": sorted(t.id for t in tools.values() if t.availability == "degraded"),
            "unavailable": sorted(t.id for t in tools.values() if t.availability == "unavailable"),
            "not_configured": sorted(
                t.id for t in tools.values() if t.availability == "not_configured"
            ),
            "mcp_config": str(self.mcp_config) if self.mcp_config.exists() else "",
        }

    def honesty_report(self) -> Dict[str, Any]:
        from .capability import FORBIDDEN_CLAIMS

        return {
            "forbidden_claims": [dict(c) for c in FORBIDDEN_CLAIMS],
            "artifact_ceilings": dict(ARTIFACT_KIND_CEILING),
        }


# --------------------------------------------------------------------------
# Independent artifact verifiers. Deliberately not the code that wrote them.
def _verify_dxf(p: Path) -> Dict[str, Any]:
    from ..adapters.dxf_r12 import read_r12

    rep = read_r12(p)
    try:
        import ezdxf  # noqa: F401
        from ezdxf import recover

        doc, auditor = recover.readfile(str(p))
        kinds: Dict[str, int] = {}
        for e in doc.modelspace():
            kinds[e.dxftype()] = kinds.get(e.dxftype(), 0) + 1
        rep["stats"]["ezdxf_entity_count"] = sum(kinds.values())
        rep["stats"]["ezdxf_kinds"] = kinds
        rep["ezdxf_auditor_errors"] = [str(x) for x in auditor.errors][:10]
    except Exception:
        rep["stats"]["ezdxf_entity_count"] = None
    # DXF is the only honest label for a .dxf file
    rep["is_dwg"] = False
    rep["honest_label"] = "可编辑 2D CAD 图纸（DXF）"
    return rep


def _verify_obj(p: Path) -> Dict[str, Any]:
    from ..adapters.mesh import MeshAdapter

    rep = MeshAdapter().read_back(p)
    rep["is_parametric_bim"] = False
    rep["honest_label"] = "三维网格模型（非参数化 BIM）"
    return rep


def _verify_json(p: Path) -> Dict[str, Any]:
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"ok": False, "errors": [f"invalid JSON: {exc}"]}
    return {"ok": True, "errors": [], "stats": {"top_level": type(data).__name__}}


def _verify_pptx(p: Path) -> Dict[str, Any]:
    errors: List[str] = []
    stats: Dict[str, Any] = {}
    if not zipfile.is_zipfile(p):
        return {"ok": False, "errors": ["not a zip container — not an OOXML file"]}
    with zipfile.ZipFile(p) as z:
        names = z.namelist()
        stats["parts"] = len(names)
        if "[Content_Types].xml" not in names:
            errors.append("missing [Content_Types].xml")
        ct = z.read("[Content_Types].xml").decode("utf-8", "replace")
        if "presentationml" not in ct:
            errors.append("content types do not declare presentationml")
        slides = [n for n in names if n.startswith("ppt/slides/slide") and n.endswith(".xml")]
        stats["slides"] = len(slides)
        if not slides:
            errors.append("no slide parts")
        for s in slides:
            body = z.read(s).decode("utf-8", "replace")
            if "<p:sld" not in body:
                errors.append(f"{s}: not a slide XML")
                break
        layouts = [n for n in names if n.startswith("ppt/slideLayouts/")]
        stats["layouts"] = len(layouts)
    return {"ok": not errors, "errors": errors, "stats": stats,
            "honest_label": "可编辑演示文稿（PPTX）"}


def _verify_png(p: Path) -> Dict[str, Any]:
    raw = p.read_bytes()[:32]
    ok = raw.startswith(b"\x89PNG\r\n\x1a\n")
    return {"ok": ok, "errors": [] if ok else ["not a PNG file"],
            "stats": {"size_bytes": p.stat().st_size},
            "honest_label": "表现图 / 示意图（不得作为尺寸依据）"}


def _verify_md(p: Path) -> Dict[str, Any]:
    text = p.read_text(encoding="utf-8", errors="replace")
    return {"ok": bool(text.strip()), "errors": [],
            "stats": {"lines": len(text.splitlines()), "chars": len(text)}}


VERIFIERS: Dict[str, Callable[[Path], Dict[str, Any]]] = {
    "dxf": _verify_dxf,
    "obj": _verify_obj,
    "json": _verify_json,
    "pptx": _verify_pptx,
    "png": _verify_png,
    "md": _verify_md,
}


def registry() -> ToolRegistry:
    return ToolRegistry()


__all__ = [
    "ToolRegistry", "InvocationRecord", "VERIFIERS", "BUILTIN_OPERATIONS",
    "BUILTIN_LIMITS", "registry", "CapabilityViolation", "PermissionRequired",
]
