"""Tool adapters. Import order defines the doctor report order.

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

from typing import Dict, List

from .base import Adapter, AdapterResult, Capability
from .blender import BlenderAdapter
from .dxf import DxfAdapter
from .drawing import resolve_host_axes
from .freecad import FreeCadAdapter
from .ifc import IfcAdapter
from .mesh import MeshAdapter
from .render import RenderAdapter

__all__ = [
    "Adapter", "AdapterResult", "Capability",
    "DxfAdapter", "MeshAdapter", "BlenderAdapter", "FreeCadAdapter",
    "IfcAdapter", "RenderAdapter", "resolve_host_axes",
    "all_adapters", "doctor",
]


def all_adapters() -> List[Adapter]:
    return [DxfAdapter(), MeshAdapter(), BlenderAdapter(), FreeCadAdapter(), IfcAdapter(), RenderAdapter()]


def doctor() -> Dict[str, object]:
    """Preflight every adapter. Called before any workflow run."""
    rows = []
    for a in all_adapters():
        try:
            cap = a.preflight()
        except Exception as exc:  # pragma: no cover
            cap = Capability(name=a.name, available=False, notes=[f"preflight error: {exc}"])
        rows.append(cap.to_dict())
    return {
        "host": Adapter.host_info(),
        "adapters": rows,
        "available": [r["adapter"] for r in rows if r["available"]],
        "unavailable": [r["adapter"] for r in rows if not r["available"]],
    }
