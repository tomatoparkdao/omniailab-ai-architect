"""DXF adapter — real, editable CAD output.

Two backends, one drawing model:

* **ezdxf** when it is installed (R2010, richer entities);
* **native R12 writer** when it is not — AutoCAD R12 DXF is the most widely
  readable dialect there is, and writing it directly means the system can still
  produce a real drawing on a machine with no CAD toolchain and no internet.

Whichever backend runs, the file is re-opened by an independent parser and
audited before the export is reported as valid. A DXF that cannot be read back
is a failed deliverable, not a success.

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from ..errors import AdapterUnavailable, ModelError
from ..model import Project
from .base import Adapter, AdapterResult, Capability
from .drawing import LAYERS, Prim, build_primitives, resolve_host_axes  # noqa: F401
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

    def draw_landscape(self, project: Project, out_path: str | Path,
                       title: str = "景观总平面（方案深度）") -> AdapterResult:
        """Draw the actual L-SITE polygons; no room or wall geometry is invented."""
        spaces = [s for s in project.spaces_on("L-SITE")
                  if s.use in ("water", "planting", "paving", "circulation")
                  and len(s.boundary_mm2d) >= 3]
        if not spaces:
            raise ModelError("no landscape polygons on L-SITE")
        layer = {"water": "L-ZONE-WATER", "planting": "L-ZONE-PLANT",
                 "paving": "L-ZONE-PAVE", "circulation": "L-ZONE-PATH"}
        prims = []
        path_labelled = False
        for space in spaces:
            if space.properties.get("infill_kind"):
                continue
            points = [(float(x), float(y)) for x, y in space.boundary_mm2d]
            prims.append(Prim("polyline", layer[space.use], points, closed=True))
            show_label = space.use != "circulation" or not path_labelled
            if show_label:
                prims.append(Prim("text", "L-ANNO",
                                  text="环形游线（分段建模）" if space.use == "circulation" else space.name,
                                  center=space.centroid, height=180))
                if space.use == "circulation":
                    path_labelled = True
            if show_label and "design_z_mm" in space.properties:
                cx, cy = space.centroid
                z = float(space.properties["design_z_mm"]) / 1000.0
                prims.append(Prim("text", "L-ANNO", text=f"建议相对标高 {z:+.2f}m",
                                  center=(cx, cy - 350), height=110))
        infill = [s for s in spaces if s.properties.get("infill_kind")]
        if infill:
            from shapely.geometry import Polygon
            from shapely.ops import unary_union

            for kind, label, target_layer in (
                ("lawn", "中央草坪与地被", "L-ZONE-LAWN"),
                ("gravel", "透水砂砾活动地面", "L-ZONE-GRAVEL"),
            ):
                selected = [Polygon(s.boundary_mm2d) for s in infill
                            if s.properties.get("infill_kind") == kind]
                if not selected:
                    continue
                merged = unary_union(selected)
                polygons = [merged] if merged.geom_type == "Polygon" else list(merged.geoms)
                for polygon in polygons:
                    for ring in [polygon.exterior, *polygon.interiors]:
                        prims.append(Prim("polyline", target_layer,
                                          [(float(x), float(y)) for x, y in list(ring.coords)[:-1]],
                                          closed=True))
                pt = merged.representative_point()
                prims.append(Prim("text", "L-ANNO", text=label,
                                  center=(pt.x, pt.y), height=160))
        for tree in project.by_type("other"):
            if tree.level_id != "L-SITE" or tree.properties.get("landscape_kind") != "tree":
                continue
            center = tree.geometry.get("center") or []
            if len(center) != 2:
                continue
            point = (float(center[0]), float(center[1]))
            prims.append(Prim("circle", "L-TREE", center=point,
                              radius=float(tree.geometry.get("crown_radius_mm") or 1100)))
            prims.append(Prim("circle", "L-TREE", center=point, radius=130))
        for node in project.by_type("other"):
            if node.level_id != "L-SITE" or node.properties.get("landscape_kind") != "view_node":
                continue
            center = node.geometry.get("center") or []
            if len(center) != 2:
                continue
            point = (float(center[0]), float(center[1]))
            prims.append(Prim("circle", "L-NODE", center=point,
                              radius=float(node.geometry.get("radius_mm") or 350)))
            prims.append(Prim("text", "L-ANNO", text=str(node.properties.get("name") or "停留点"),
                              center=(point[0], point[1]-600), height=120))
        points = [p for s in spaces for p in s.boundary_mm2d]
        x0, y0 = min(p[0] for p in points), min(p[1] for p in points)
        x1, y1 = max(p[0] for p in points), max(p[1] for p in points)
        prims.append(Prim("text", "L-ANNO", text=title,
                          center=((x0 + x1) / 2, y0 - 1200), height=250))
        path = Path(out_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        if self.backend == "ezdxf":
            self._write_ezdxf(prims, path)
        else:
            write_r12(prims, path)
        audit = self.audit(path, required_layer_prefix="L-ZONE")
        return AdapterResult(adapter=self.name, ok=bool(audit.get("ok")),
                             artifacts=[str(path)], revision=project.revision,
                             validation=audit, errors=list(audit.get("errors") or []))

    def draw_primitives(self, primitives: Sequence[Prim], out_path: str | Path,
                        required_layer_prefix: str, revision: int = 1) -> AdapterResult:
        """Write a specialist sheet with the existing DXF backends and audit."""
        if not primitives:
            raise ModelError("empty drawing")
        path = Path(out_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        if self.backend == "ezdxf":
            self._write_ezdxf(primitives, path)
        else:
            write_r12(primitives, path)
        audit = self.audit(path, required_layer_prefix=required_layer_prefix)
        return AdapterResult(adapter=self.name, ok=bool(audit.get("ok")),
                             revision=revision, artifacts=[str(path)],
                             validation=audit, errors=list(audit.get("errors") or []))

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
    def audit(self, path: str | Path,
              required_layer_prefix: str = "A-WALL") -> Dict[str, Any]:
        """Re-open and audit. Uses ezdxf's recoverer when present, otherwise the
        native reader — either way a backend never audits itself."""
        p = Path(path)
        try:
            import ezdxf
        except Exception:
            out = read_r12(p, required_layer_prefix=required_layer_prefix)
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
            native = read_r12(p, required_layer_prefix=required_layer_prefix)
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
                and any(l.startswith(required_layer_prefix) for l in layers)
            )
            if not result["ok"] and not result["errors"]:
                result["errors"].append("audit failed: missing required geometry or zero entities")
        except Exception as exc:
            result["errors"].append(f"recovery failed: {exc}")
            native = read_r12(p, required_layer_prefix=required_layer_prefix)
            result["native"] = native
            result["ok"] = bool(native.get("ok"))
        return result
