"""Tool capability model.

Every tool OmniArchitect can drive declares itself here before anything is
executed. The point is to make honesty structural: a tool cannot claim a
capability it has not declared, and a declared capability carries a risk tier,
an availability state and the limits on what its output may be called.

Risk tiers (L1–L4) are the security classification the fusion map credits to
`skill-safety-audit`; they gate execution here.

    L1  read-only            — inspect files, parse drawings, query state
    L2  local write          — create/modify files inside the project
    L3  network              — call an external service or model provider
    L4  execute / send       — run third-party code, drive a host app, publish

Anything at L3 or above needs explicit approval before it runs, and L4 always
runs with a dry-run preview first.
"""
from __future__ import annotations

import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

# --------------------------------------------------------------------------
RISK_TIERS: Dict[str, Dict[str, Any]] = {
    "L1": {"label": "只读", "description": "读取文件、解析图纸、查询状态；不写入任何位置",
           "approval": False},
    "L2": {"label": "本地写入", "description": "在项目目录内创建或修改文件",
           "approval": False},
    "L3": {"label": "联网", "description": "调用外部服务、模型 provider 或远端 API",
           "approval": True},
    "L4": {"label": "执行/发送", "description": "运行第三方代码、驱动宿主软件、对外发布",
           "approval": True, "dry_run_first": True},
}

AVAILABILITY = ("available", "degraded", "unavailable", "not_configured")

# --------------------------------------------------------------------------
# Claims that may never be made about an artifact. Each entry is
# (claim, why it is false, what must be said instead).
FORBIDDEN_CLAIMS: List[Dict[str, str]] = [
    {
        "claim": "DXF 文件改名为 DWG 即为 DWG",
        "why": "DWG 是封闭的二进制格式；改名不改变文件内容，AutoCAD 会拒绝或损坏打开。",
        "instead": "只能声明输出了 DXF（R12 / R2010）。需要 DWG 时必须由具备许可的 "
                   "AutoCAD/MCP 后端另存。",
    },
    {
        "claim": "三角网格（OBJ/GLB/STL）是参数化 BIM 模型",
        "why": "网格没有构件语义、属性与参数关系，不能承载 IFC 的构件级信息。",
        "instead": "只能声明输出了三维网格模型；参数化 BIM 需 IFC/原生 BIM 后端。",
    },
    {
        "claim": "AI 生成效果图可作为施工尺寸依据",
        "why": "生成式图像不保证尺寸、比例与几何真实性。",
        "instead": "施工图必须由经过校核的几何/BIM 模型生成；效果图只用于表现。",
    },
    {
        "claim": "未安装 IfcOpenShell 也输出了合规 IFC 文件",
        "why": "没有 IFC 写出能力时只能输出投影 JSON 与生成脚本。",
        "instead": "声明输出为 IFC 投影数据 + 可在有环境的机器上运行的生成脚本。",
    },
    {
        "claim": "本系统已通过结构安全 / 消防 / 无障碍校核",
        "why": "这些结论不在系统能力范围内。",
        "instead": "系统只做规则初筛与提示，须由持证专业人员在项目所在地复核签署。",
    },
]

ARTIFACT_KIND_CEILING: Dict[str, str] = {
    # artifact extension -> the strongest honest description
    "dxf": "可编辑 2D CAD 图纸（DXF）",
    "dwg": "仅当由已授权的 DWG 后端写出时才成立",
    "obj": "三维网格模型（非参数化 BIM）",
    "glb": "三维网格模型（非参数化 BIM）",
    "stl": "三维网格模型（非参数化 BIM）",
    "ifc": "需 IFC 写出后端；否则仅为投影数据",
    "png": "表现图 / 示意图（不得作为尺寸依据）",
    "jpg": "表现图 / 示意图（不得作为尺寸依据）",
    "svg": "矢量示意图（不得作为尺寸依据）",
    "pptx": "可编辑演示文稿",
    "pdf": "只读交付件",
    "md": "文本交付件",
    "json": "数据交换件",
}


class CapabilityViolation(Exception):
    """Raised when a tool tries to claim more than it can honestly deliver."""


class PermissionRequired(Exception):
    """Raised when an operation needs approval that was not granted."""

    def __init__(self, tool_id: str, operation: str, risk: str, message: str):
        super().__init__(message)
        self.tool_id = tool_id
        self.operation = operation
        self.risk = risk


# --------------------------------------------------------------------------
@dataclass
class Operation:
    name: str
    risk: str                       # L1..L4
    summary: str = ""
    destructive: bool = False
    reversible: bool = True
    produces: List[str] = field(default_factory=list)   # artifact extensions
    verifiable: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name, "risk": self.risk,
            "risk_label": RISK_TIERS.get(self.risk, {}).get("label", "?"),
            "summary": self.summary, "destructive": self.destructive,
            "reversible": self.reversible, "produces": list(self.produces),
            "verifiable": self.verifiable,
            "approval_required": bool(RISK_TIERS.get(self.risk, {}).get("approval")),
        }


@dataclass
class ToolCapability:
    """What a tool is, what it may do, and how far its output may be trusted."""

    id: str
    name: str
    kind: str                       # python | mcp | cli | service
    transport: str = "inprocess"    # inprocess | stdio | http | none
    availability: str = "unavailable"
    version: str = ""
    executable: str = ""
    operations: List[Operation] = field(default_factory=list)
    requires: List[str] = field(default_factory=list)
    degraded_to: str = ""
    notes: List[str] = field(default_factory=list)
    limits: List[str] = field(default_factory=list)
    attribution: str = ""
    verified: bool = False
    verification: str = ""

    def __post_init__(self) -> None:
        if self.availability not in AVAILABILITY:
            raise CapabilityViolation(
                f"{self.id}: 非法 availability={self.availability}，"
                f"只能是 {', '.join(AVAILABILITY)}"
            )
        for op in self.operations:
            if op.risk not in RISK_TIERS:
                raise CapabilityViolation(f"{self.id}.{op.name}: 非法风险等级 {op.risk}")

    # ------------------------------------------------------------------
    def operation(self, name: str) -> Optional[Operation]:
        return next((o for o in self.operations if o.name == name), None)

    @property
    def usable(self) -> bool:
        return self.availability in ("available", "degraded")

    def guard(self, operation: str, approved: bool, dry_run: bool = False) -> None:
        """Refuse loudly rather than silently doing something the user did not OK."""
        op = self.operation(operation)
        if op is None:
            raise CapabilityViolation(f"{self.id} 未声明操作 {operation!r}")
        if not self.usable:
            raise CapabilityViolation(
                f"{self.id} 当前状态为 {self.availability}，无法执行 {operation}"
                + (f"；降级方案：{self.degraded_to}" if self.degraded_to else "")
            )
        tier = RISK_TIERS[op.risk]
        if tier.get("approval") and not approved:
            raise PermissionRequired(
                self.id, operation, op.risk,
                f"{self.id}.{operation} 属 {op.risk}（{tier['label']}），需要显式授权。",
            )
        if op.risk == "L4" and not dry_run and not approved:
            raise PermissionRequired(
                self.id, operation, op.risk,
                f"{self.id}.{operation} 属 L4，必须先 dry-run 预览再授权执行。",
            )

    def claim_check(self, artifact_kind: str, claim: str) -> Optional[str]:
        """Return the honest correction if `claim` overstates `artifact_kind`."""
        kind = artifact_kind.lower().lstrip(".")
        ceiling = ARTIFACT_KIND_CEILING.get(kind)
        if not ceiling:
            return None
        for rule in FORBIDDEN_CLAIMS:
            if rule["claim"].startswith(claim[:6]) or claim in rule["claim"]:
                return rule["instead"]
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "name": self.name, "kind": self.kind,
            "transport": self.transport, "availability": self.availability,
            "version": self.version, "executable": self.executable,
            "requires": list(self.requires), "degraded_to": self.degraded_to,
            "notes": list(self.notes), "limits": list(self.limits),
            "attribution": self.attribution,
            "verified": self.verified, "verification": self.verification,
            "operations": [o.to_dict() for o in self.operations],
        }


# --------------------------------------------------------------------------
def probe_executable(names: Sequence[str]) -> Optional[str]:
    for n in names:
        p = shutil.which(n)
        if p:
            return p
    return None


def probe_python_module(name: str) -> Optional[str]:
    import importlib

    try:
        m = importlib.import_module(name)
    except Exception:
        return None
    return str(getattr(m, "__version__", "unknown"))


def interpreter() -> str:
    return f"{Path(sys.executable).name} {sys.version.split()[0]}"


def forbidden_claim(artifact_kind_or_claim: str) -> Optional[Dict[str, str]]:
    """Look up the honesty rule for a claim or an artifact kind."""
    low = artifact_kind_or_claim.lower()
    for rule in FORBIDDEN_CLAIMS:
        if low in rule["claim"].lower() or low in rule["instead"].lower():
            return rule
    return None


def honesty_rules() -> List[Dict[str, str]]:
    return [dict(r) for r in FORBIDDEN_CLAIMS]


__all__ = [
    "RISK_TIERS", "AVAILABILITY", "FORBIDDEN_CLAIMS", "ARTIFACT_KIND_CEILING",
    "Operation", "ToolCapability", "CapabilityViolation", "PermissionRequired",
    "probe_executable", "probe_python_module", "interpreter",
    "forbidden_claim", "honesty_rules",
]
