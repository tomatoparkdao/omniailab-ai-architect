"""DXF adapter — real, editable CAD output.

Two backends, one drawing model:

* **ezdxf** when it is installed (R2010, richer entities);
* **native R12 writer** when it is not — AutoCAD R12 DXF is the most widely
  readable dialect there is, and writing it directly means the system can still
  produce a real drawing on a machine with no CAD toolchain and no internet.

Whichever backend runs, the file is re-opened by an independent parser and
audited before the export is reported as valid. A DXF that cannot be read back
is a failed deliverable, not a success.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from ..errors import AdapterUnavailable, ModelError
from ..model import Project
from .base import Adapter, AdapterResult, Capability
from .drawing import LAYERS, build_primitives, resolve_host_axes  # noqa: F401
from .dxf_r12 import read_r12, write_r12


class DxfAdapter(Adapter):
    name = "dxf"
    tool = "DXF"

    def preflight(self) -> Capability:
        try:
            import ezdxf

            return Capability(
                name=self.name,
                available=True,
                version=str(getattr(ezdxf, "__version__", "unknown")),
                executable="python:ezdxf",
                operations=["draw_plan", "audit", "read_back", "export_dxf"],
                notes=["backend: ezdxf (R2010)"],
            )
        except Exception:
            return Capability(
                name=self.name,
                available=True,           # the native backend always works
                version="builtin-r12",
                executable="python:builtin",
                operations=["draw_plan", "audit", "read_back", "export_dxf"],
                notes=[
                    "backend: native DXF R12 writer (AC1009)",
                    "ezdxf 未安装：使用内置写出器；中文以 \\U+XXXX 转义保留",
                    "R12 不支持的实体（HATCH 等）以双线/剖面线等价形式表达",
                ],
            )

    @property
    def backend(self) -> str:
        try:
            import ezdxf  # noqa: F401

            return "ezdxf"
        except Exception:
            return "r12"

    # ------------------------------------------------------------------
    def draw_plan(
        self,
        project: Project,
        out_path: str | Path,
        level_id: Optional[str] = None,
        title: str = "平面布置图",
        scheme: str = "",
        depth: str = "schematic",
        include_furniture: bool = True,
        include_dims: bool = True,
        include_titleblock: bool = True,
    ) -> AdapterResult:
        resolve_host_axes(project)
        prims = build_primitives(
            project, level_id=level_id, include_furniture=include_furniture,
            include_dims=include_dims, include_titleblock=include_titleblock,
            title=title, scheme=scheme, depth=depth,
        )
        if not prims:
            raise ModelError("no drawable geometry — a plan needs spaces and walls")

        p = Path(out_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        res = AdapterResult(adapter=self.name, ok=True, revision=project.revision)
        res.log.append(f"backend={self.backend} depth={depth} primitives={len(prims)}")

        if self.backend == "ezdxf":
            self._write_ezdxf(prims, p)
        else:
            write_r12(prims, p)
        res.artifacts.append(str(p))

        audit = self.audit(p)
        res.validation = audit
        res.validation["backend"] = self.backend
        res.validation["drawing_depth"] = depth
        if not audit.get("ok"):
            res.ok = False
            res.errors.extend(audit.get("errors", []))
        counts = audit.get("stats", {}).get("entities", {})
        res.log.append(
            f"entities={audit.get('stats', {}).get('entity_count', 0)} "
            f"layers={len(audit.get('stats', {}).get('layers', []))} "
            f"({', '.join(f'{k}:{v}' for k, v in sorted(counts.items()))})"
        )
        return res

    # ------------------------------------------------------------------
    @staticmethod
    def _write_ezdxf(prims, path: Path) -> None:
        import ezdxf

        doc = ezdxf.new("R2010", setup=True)
        doc.header["$INSUNITS"] = 4
        doc.header["$MEASUREMENT"] = 1
        for name, spec in LAYERS.items():
            if name not in doc.layers:
                doc.layers.add(name, color=spec["color"], linetype=spec["linetype"])
        msp = doc.modelspace()
        from ezdxf.enums import TextEntityAlignment

        for pr in prims:
            if pr.kind == "line":
                msp.add_line(pr.points[0], pr.points[1], dxfattribs={"layer": pr.layer})
            elif pr.kind == "polyline":
                msp.add_lwpolyline(pr.points, close=pr.closed, dxfattribs={"layer": pr.layer})
            elif pr.kind == "circle":
                msp.add_circle(pr.center, pr.radius, dxfattribs={"layer": pr.layer})
            elif pr.kind == "arc":
                msp.add_arc(pr.center, pr.radius, pr.start_angle, pr.end_angle,
                            dxfattribs={"layer": pr.layer})
            elif pr.kind == "text":
                t = msp.add_text(pr.text, height=pr.height, dxfattribs={"layer": pr.layer})
                t.set_placement(pr.center, align=TextEntityAlignment.MIDDLE_CENTER)
        doc.saveas(str(path))

    # ------------------------------------------------------------------
    def audit(self, path: str | Path) -> Dict[str, Any]:
        """Re-open and audit. Uses ezdxf's recoverer when present, otherwise the
        native reader — either way a backend never audits itself."""
        p = Path(path)
        try:
            import ezdxf
        except Exception:
            out = read_r12(p)
            out["auditor"] = "native-r12"
            return out

        result: Dict[str, Any] = {"ok": False, "file": str(p), "errors": [],
                                  "auditor": "ezdxf.recover"}
        if not p.exists() or p.stat().st_size == 0:
            result["errors"].append("file missing or empty")
            return result
        try:
            # `ezdxf.recover` is a submodule; it is not imported by `import ezdxf`
            from ezdxf import recover as _recover

            doc, auditor = _recover.readfile(str(p))
            result["errors"] = [str(e) for e in auditor.errors][:20]
            result["fixes"] = [str(f) for f in auditor.fixes][:20]
            msp = doc.modelspace()
            kinds: Dict[str, int] = {}
            for e in msp:
                kinds[e.dxftype()] = kinds.get(e.dxftype(), 0) + 1
            layers = sorted({e.dxf.layer for e in msp if e.dxf.hasattr("layer")})
            native = read_r12(p)
            labels = []
            for e in msp:
                if e.dxftype() in ("TEXT", "MTEXT"):
                    try:
                        labels.append(e.dxf.text if e.dxftype() == "TEXT" else e.text)
                    except Exception:
                        pass
            # stats shape is identical to the native auditor's so that callers
            # never have to know which backend produced the audit
            result["stats"] = {
                "entities": kinds,
                "entity_count": sum(kinds.values()),
                "kinds": kinds,
                "layers": layers,
                "size_bytes": p.stat().st_size,
                "acadver": doc.dxfversion,
                "text_labels": len(labels),
                "sample_labels": [l for l in labels if l and l.strip()][:6],
                "native_entity_count": native.get("stats", {}).get("entity_count"),
            }
            result["native"] = native
            result["ok"] = (
                not result["errors"]
                and sum(kinds.values()) > 0
                and any(l.startswith("A-WALL") for l in layers)
            )
            if not result["ok"] and not result["errors"]:
                result["errors"].append("audit failed: missing walls or zero entities")
        except Exception as exc:
            result["errors"].append(f"recovery failed: {exc}")
            native = read_r12(p)
            result["native"] = native
            result["ok"] = bool(native.get("ok"))
        return result
