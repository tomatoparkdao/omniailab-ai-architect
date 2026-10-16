"""Native DXF R12 writer and reader — no third-party dependency.

AutoCAD R12 (AC1009) ASCII DXF is the most widely readable DXF dialect there
is; every CAD package still opens it. Writing it directly means the system can
produce a real, editable drawing on a machine that has no `ezdxf`, no AutoCAD
and no internet.

The reader is deliberately independent of the writer: it re-parses the file
from disk and reports what it actually found, so a "successful export" has to
survive being read back.
"""
from __future__ import annotations

import math
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .drawing import LAYERS, Prim

HEADER = """0
SECTION
2
HEADER
9
$ACADVER
1
AC1009
9
$INSUNITS
70
4
9
$MEASUREMENT
70
1
0
ENDSEC
"""


def _tag(code: int, value: Any) -> str:
    return f"{code}\n{value}\n"


def write_r12(prims: Sequence[Prim], path: str | Path) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    out: List[str] = [HEADER]

    # --- TABLES / LAYER --------------------------------------------------
    out.append("0\nSECTION\n2\nTABLES\n")
    used = sorted({pr.layer for pr in prims} | set(LAYERS))
    out.append("0\nTABLE\n2\nLAYER\n70\n%d\n" % len(used))
    for name in used:
        spec = LAYERS.get(name, {"color": 7, "linetype": "CONTINUOUS"})
        out.append(_tag(0, "LAYER") + _tag(2, name) + _tag(70, 0)
                   + _tag(62, spec["color"]) + _tag(6, spec["linetype"]))
    out.append("0\nENDTAB\n0\nENDSEC\n")

    # --- ENTITIES --------------------------------------------------------
    out.append("0\nSECTION\n2\nENTITIES\n")
    for pr in prims:
        out.append(_entity(pr))
    out.append("0\nENDSEC\n0\nEOF\n")

    p.write_text("".join(out), encoding="ascii", errors="replace")
    return p


def _entity(pr: Prim) -> str:
    if pr.kind == "line" and len(pr.points) >= 2:
        (x1, y1), (x2, y2) = pr.points[0], pr.points[1]
        return (_tag(0, "LINE") + _tag(8, pr.layer)
                + _tag(10, f"{x1:.3f}") + _tag(20, f"{y1:.3f}") + _tag(30, "0.0")
                + _tag(11, f"{x2:.3f}") + _tag(21, f"{y2:.3f}") + _tag(31, "0.0"))
    if pr.kind == "circle":
        cx, cy = pr.center
        return (_tag(0, "CIRCLE") + _tag(8, pr.layer)
                + _tag(10, f"{cx:.3f}") + _tag(20, f"{cy:.3f}") + _tag(30, "0.0")
                + _tag(40, f"{pr.radius:.3f}"))
    if pr.kind == "arc":
        cx, cy = pr.center
        return (_tag(0, "ARC") + _tag(8, pr.layer)
                + _tag(10, f"{cx:.3f}") + _tag(20, f"{cy:.3f}") + _tag(30, "0.0")
                + _tag(40, f"{pr.radius:.3f}")
                + _tag(50, f"{pr.start_angle:.3f}") + _tag(51, f"{pr.end_angle:.3f}"))
    if pr.kind == "polyline" and pr.points:
        s = _tag(0, "POLYLINE") + _tag(8, pr.layer) + _tag(66, 1) \
            + _tag(70, 1 if pr.closed else 0)
        for x, y in pr.points:
            s += (_tag(0, "VERTEX") + _tag(8, pr.layer)
                  + _tag(10, f"{x:.3f}") + _tag(20, f"{y:.3f}") + _tag(30, "0.0"))
        s += _tag(0, "SEQEND") + _tag(8, pr.layer)
        return s
    if pr.kind == "text" and pr.text:
        cx, cy = pr.center
        safe = _escape(pr.text.replace("\n", " ")[:250])
        return (_tag(0, "TEXT") + _tag(8, pr.layer)
                + _tag(10, f"{cx:.3f}") + _tag(20, f"{cy:.3f}") + _tag(30, "0.0")
                + _tag(40, f"{pr.height:.3f}") + _tag(1, safe)
                + _tag(72, 1) + _tag(73, 2)
                + _tag(11, f"{cx:.3f}") + _tag(21, f"{cy:.3f}") + _tag(31, "0.0"))
    return ""


def _escape(text: str) -> str:
    """DXF R12 files are ASCII. Non-ASCII is written as the `\\U+XXXX` escape
    that AutoCAD, LibreCAD and FreeCAD all understand, so Chinese room names
    survive instead of degrading to '?'."""
    out: List[str] = []
    for ch in text:
        if ord(ch) < 128:
            out.append(ch)
        else:
            out.append(f"\\U+{ord(ch):04X}")
    return "".join(out)


def _unescape(text: str) -> str:
    import re as _re

    return _re.sub(r"\\U\+([0-9A-Fa-f]{4})", lambda m: chr(int(m.group(1), 16)), text)


# --------------------------------------------------------------------------
def read_r12(path: str | Path) -> Dict[str, Any]:
    """Independent re-parse of a DXF file. Never trust the writer."""
    p = Path(path)
    out: Dict[str, Any] = {"ok": False, "file": str(p), "errors": [], "stats": {}}
    if not p.exists() or p.stat().st_size == 0:
        out["errors"].append("file missing or empty")
        return out
    try:
        raw = p.read_text(encoding="ascii", errors="replace")
    except Exception as exc:
        out["errors"].append(f"unreadable: {exc}")
        return out

    lines = raw.splitlines()
    if len(lines) < 20:
        out["errors"].append("file too short to be a DXF")
        return out

    codes: List[Tuple[int, str]] = []
    try:
        for i in range(0, len(lines) - 1, 2):
            codes.append((int(lines[i].strip()), lines[i + 1]))
    except ValueError:
        out["errors"].append("malformed group-code / value pairs")
        return out

    sections: List[str] = []
    entities: Counter = Counter()
    layers: set[str] = set()
    current_layer = ""
    in_entities = False
    pending_entity: Optional[str] = None
    for code, val in codes:
        if code == 0:
            if val == "SECTION":
                sections.append("")
            elif val == "ENDSEC":
                pass
            elif val == "EOF":
                pass
            if in_entities and val not in ("SECTION", "ENDSEC", "EOF", "VERTEX", "SEQEND"):
                entities[val] += 1
                pending_entity = val
            if in_entities and val == "VERTEX":
                entities["VERTEX"] += 1
            current_layer = ""
        elif code == 2 and sections and sections[-1] == "":
            sections[-1] = val
            in_entities = sections[-1] == "ENTITIES"
        elif code == 8:
            layers.add(val)

    total = sum(v for k, v in entities.items() if k not in ("VERTEX", "SEQEND"))
    out["stats"] = {
        "size_bytes": p.stat().st_size,
        "sections": [s for s in sections if s],
        "entities": dict(entities),
        "entity_count": total,
        "layers": sorted(layers),
        "acadver": "AC1009" if "$ACADVER" in raw else "unknown",
    }
    if "ENTITIES" not in sections:
        out["errors"].append("no ENTITIES section")
    if total == 0:
        out["errors"].append("ENTITIES section contains no drawable entities")
    if not any(l.startswith("A-WALL") for l in layers):
        out["errors"].append("no wall geometry on A-WALL layers")
    if "AC1009" not in raw:
        out["errors"].append("missing AC1009 version header")
    labels = [_unescape(v) for c, v in codes if c == 1]
    out["stats"]["text_labels"] = len(labels)
    out["stats"]["sample_labels"] = [l for l in labels if l.strip()][:6]
    if not any(ord(ch) > 127 for l in labels for ch in l):
        out["warnings"] = [
            "未检出中文标注：若项目使用中文名称，请确认 \\U+ 转义写入正常"
        ]
    out["ok"] = not out["errors"]
    return out
