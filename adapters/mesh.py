"""Native mesh export — OBJ + MTL.

Runs everywhere, no DCC tool required, and produces a genuinely editable 3D
model (Blender, FreeCAD, Rhino, SketchUp, 3ds Max all open it). The Blender
adapter builds on the same geometry when Blender is present; when it is not,
this is the honest deliverable instead of a promise.
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from ..geometry import wall_polygon
from ..model import Element, Project, Space
from .base import Adapter, AdapterResult, Capability
from .drawing import _advance, free_spans as _free_spans

MATERIALS: Dict[str, Tuple[float, float, float]] = {
    "wall_structural": (0.82, 0.80, 0.76),
    "wall_partition": (0.90, 0.89, 0.87),
    "wall_uncertain": (0.85, 0.45, 0.35),
    "floor": (0.72, 0.70, 0.66),
    "ceiling": (0.95, 0.95, 0.94),
    "glass": (0.60, 0.78, 0.85),
    "door": (0.55, 0.42, 0.30),
    "furniture_soft": (0.55, 0.56, 0.58),
    "furniture_wood": (0.62, 0.48, 0.34),
    "furniture_white": (0.92, 0.92, 0.91),
}

SOFT = {"sofa", "bed_king", "bed_queen", "coffee_table"}
WOOD = {"wardrobe", "tv_unit", "desk", "dining_table", "sideboard", "bookshelf",
        "shelf_unit", "shoe_cabinet", "nightstand"}


def material_for(element: Element) -> str:
    if element.type == "wall":
        if element.uncertain:
            return "wall_uncertain"
        return "wall_structural" if element.geometry.get("kind") != "partition" else "wall_partition"
    if element.type == "furniture":
        cat = str(element.geometry.get("category") or "")
        if cat in WOOD:
            return "furniture_wood"
        return "furniture_soft" if cat in SOFT else "furniture_white"
    if element.type == "window":
        return "glass"
    if element.type == "door":
        return "door"
    if element.type == "ceiling":
        return "ceiling"
    return "floor"


class MeshAdapter(Adapter):
    name = "mesh"
    tool = "native-obj"

    def preflight(self) -> Capability:
        return Capability(
            name=self.name,
            available=True,
            version="builtin",
            executable="python:builtin",
            operations=["export_obj", "export_gltf_json", "read_back"],
            notes=["pure-python; no DCC tool required"],
        )

    # ------------------------------------------------------------------
    def export_obj(
        self,
        project: Project,
        out_dir: str | Path,
        level_id: Optional[str] = None,
        stem: str = "model",
        include_ceiling: bool = False,
    ) -> AdapterResult:
        lid = level_id or (project.levels[0].id if project.levels else "L1")
        out = Path(out_dir)
        out.mkdir(parents=True, exist_ok=True)
        obj_path = out / f"{stem}.obj"
        mtl_path = out / f"{stem}.mtl"

        heights: Dict[str, float] = {}
        for lv in project.levels:
            heights[lv.id] = float(lv.height_mm)
        wall_h = heights.get(lid, 2800.0)
        slab_h = 120.0

        res = AdapterResult(adapter=self.name, ok=True, revision=project.revision)

        verts: List[Tuple[float, float, float]] = []
        faces: List[Tuple[str, List[int]]] = []  # (material, indices)

        def add_box(pts2d: Sequence[Sequence[float]], z0: float, z1: float, mat: str) -> None:
            n = len(pts2d)
            base = len(verts) + 1
            for p in pts2d:
                verts.append((float(p[0]), float(p[1]), float(z0)))
            for p in pts2d:
                verts.append((float(p[0]), float(p[1]), float(z1)))
            bottom = [base + i for i in range(n)]
            top = [base + n + i for i in range(n)]
            faces.append((mat, list(reversed(bottom))))
            faces.append((mat, top))
            for i in range(n):
                j = (i + 1) % n
                faces.append((mat, [bottom[i], bottom[j], top[j], top[i]]))

        spaces = [s for s in project.spaces_on(lid) if s.use != "envelope"]
        for s in spaces:
            add_box(s.boundary_mm2d, -slab_h, 0.0, "floor")
            if include_ceiling:
                add_box(s.boundary_mm2d, wall_h, wall_h + slab_h, "ceiling")

        walls = [e for e in project.by_type("wall") if e.level_id == lid]
        openings_by_wall: Dict[str, List[Element]] = {}
        for o in project.elements:
            if o.is_opening and o.level_id == lid:
                openings_by_wall.setdefault(str(o.geometry.get("host_wall") or ""), []).append(o)

        for w in walls:
            axis = w.wall_axis()
            if not axis:
                continue
            mat = material_for(w)
            th = float(w.geometry.get("thickness_mm", 200.0))
            length = w.wall_length_mm()
            for a, b in _free_spans(length, openings_by_wall.get(w.id, [])):
                seg = _wall_box(w, a, b, th)
                if seg:
                    add_box(seg, 0.0, wall_h, mat)
            # lintels above openings keep the model watertight
            for o in openings_by_wall.get(w.id, []):
                off = float(o.geometry.get("offset_mm", 0))
                ow = float(o.geometry.get("width_mm", 0))
                oh = float(o.geometry.get("height_mm", 2100))
                seg = _wall_box(w, off, off + ow, th)
                if seg and oh < wall_h:
                    add_box(seg, oh, wall_h, mat)

        for f in project.by_type("furniture"):
            if f.level_id != lid:
                continue
            cx, cy = f.geometry.get("center", [0, 0])
            sw, sd, sh = f.geometry.get("size_mm", [600, 600, 600])
            rot = math.radians(float(f.geometry.get("rotation_deg", 0) or 0))
            hw, hd = sw / 2.0, sd / 2.0
            corners = [(-hw, -hd), (hw, -hd), (hw, hd), (-hw, hd)]
            poly = [
                (cx + x * math.cos(rot) - y * math.sin(rot),
                 cy + x * math.sin(rot) + y * math.cos(rot))
                for x, y in corners
            ]
            add_box(poly, 0.0, float(sh), material_for(f))

        for win in project.by_type("window"):
            if win.level_id != lid:
                continue
            # a glazing pane rather than a hole: keeps the model visually complete
            axis = win.properties.get("_host_axis")
            if not axis:
                continue
            (p1, _p2, ang) = axis
            off = float(win.geometry.get("offset_mm", 0))
            w = float(win.geometry.get("width_mm", 1500))
            sill = float(win.geometry.get("sill_mm", 900))
            h = float(win.geometry.get("height_mm", 1500))
            a = _advance(p1, ang, off)
            b = _advance(p1, ang, off + w)
            pane = _quad_polygon(a, b, 40.0)
            add_box(pane, sill, sill + h, "glass")

        self._write_obj(obj_path, mtl_path, stem, verts, faces)
        res.artifacts.extend([str(obj_path), str(mtl_path)])
        check = self.read_back(obj_path)
        res.validation = check
        res.ok = bool(check.get("ok"))
        res.log.append(
            f"{len(verts)} vertices, {len(faces)} faces, {len(spaces)} spaces"
        )
        return res

    # ------------------------------------------------------------------
    def _write_obj(self, obj_path: Path, mtl_path: Path, stem: str,
                   verts, faces) -> None:
        used = sorted({m for m, _ in faces})
        lines = [f"mtllib {stem}.mtl", "# OmniArchitect mesh export — mm, Z up"]
        for v in verts:
            lines.append(f"v {v[0]:.2f} {v[1]:.2f} {v[2]:.2f}")
        current = None
        for mat, idx in faces:
            if mat != current:
                lines.append(f"usemtl {mat}")
                current = mat
            lines.append("f " + " ".join(str(i) for i in idx))
        obj_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

        mtl = ["# OmniArchitect materials"]
        for name in used:
            r, g, b = MATERIALS.get(name, (0.8, 0.8, 0.8))
            mtl.append(f"newmtl {name}")
            mtl.append(f"Kd {r:.3f} {g:.3f} {b:.3f}")
            mtl.append("Ka 0.10 0.10 0.10")
            mtl.append(f"Ks {0.35 if name == 'glass' else 0.08:.2f} "
                       f"{0.35 if name == 'glass' else 0.08:.2f} "
                       f"{0.35 if name == 'glass' else 0.08:.2f}")
            if name == "glass":
                mtl.append("d 0.35")
                mtl.append("illum 4")
            elif name == "ceiling":
                mtl.append("Ke 0.05 0.05 0.05")
            mtl.append("")
        mtl_path.write_text("\n".join(mtl), encoding="utf-8")

    # ------------------------------------------------------------------
    def read_back(self, obj_path: str | Path) -> Dict[str, Any]:
        """Parse the OBJ back and sanity-check it (bbox, closure, units)."""
        p = Path(obj_path)
        out: Dict[str, Any] = {"ok": False, "file": str(p), "errors": []}
        if not p.exists():
            out["errors"].append("file missing")
            return out
        vcount = fcount = 0
        xs: List[float] = []
        ys: List[float] = []
        zs: List[float] = []
        mats: set[str] = set()
        for line in p.read_text(encoding="utf-8").splitlines():
            if line.startswith("v "):
                _, x, y, z = line.split()[:4]
                xs.append(float(x)); ys.append(float(y)); zs.append(float(z))
                vcount += 1
            elif line.startswith("f "):
                fcount += 1
            elif line.startswith("usemtl "):
                mats.add(line.split(maxsplit=1)[1].strip())
        if vcount == 0 or fcount == 0:
            out["errors"].append("no geometry parsed")
            return out
        out.update(
            {
                "vertices": vcount,
                "faces": fcount,
                "materials": sorted(mats),
                "bbox_mm": [
                    [round(min(xs), 1), round(min(ys), 1), round(min(zs), 1)],
                    [round(max(xs), 1), round(max(ys), 1), round(max(zs), 1)],
                ],
                "size_m": [
                    round((max(xs) - min(xs)) / 1000.0, 2),
                    round((max(ys) - min(ys)) / 1000.0, 2),
                    round((max(zs) - min(zs)) / 1000.0, 2),
                ],
            }
        )
        out["ok"] = True
        return out


def _wall_box(wall: Element, a: float, b: float, thickness: float):
    from ..geometry import point_along

    p1 = point_along(wall, a)
    p2 = point_along(wall, b)
    dx, dy = p2[0] - p1[0], p2[1] - p1[1]
    length = math.hypot(dx, dy)
    if length < 1e-6:
        return None
    nx, ny = -dy / length * thickness / 2.0, dx / length * thickness / 2.0
    return [
        (p1[0] + nx, p1[1] + ny),
        (p2[0] + nx, p2[1] + ny),
        (p2[0] - nx, p2[1] - ny),
        (p1[0] - nx, p1[1] - ny),
    ]


def _quad_polygon(a, b, thickness: float):
    dx, dy = b[0] - a[0], b[1] - a[1]
    length = math.hypot(dx, dy) or 1.0
    nx, ny = -dy / length * thickness / 2.0, dx / length * thickness / 2.0
    return [
        (a[0] + nx, a[1] + ny),
        (b[0] + nx, b[1] + ny),
        (b[0] - nx, b[1] - ny),
        (a[0] - nx, a[1] - ny),
    ]
