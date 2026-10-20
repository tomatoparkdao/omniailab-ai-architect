"""Parti：把 S2 选定的概念翻译成"平面必须能被看出来的几件事"。

这条链路原来断在这里：S2 的概念写着"医技居中、门诊环绕""洁污双廊""组团中庭"，
S3 读到的却只是一个 `plan_strategy="zone_bands"`，于是所有行业项目都排成
同一套带序，A/B 只差一次 `flip`。概念在图纸上没有留下任何可识别的结构。

本模块做三件事，都不新造几何：

1. `PROFILES` —— 每种组织方式对应的**剖面构成**（几条带、多深、哪条是走廊/
   中庭/街、是否有西端块）。外轮廓由此反算，所以轮廓跟着 parti 走，
   而不是所有项目都排成一条板式。
2. `resolve()` —— 从交接文件里读出"这套概念要用哪种组织方式"，读不到就
   如实说读不到（`declared=False`），不用通用带序冒充。
3. `inspect()` —— 在**已生成的平面**上找这些结构：中庭在不在、两条走廊
   平不平行、原料库是不是在生产区之前。找不到就是没落实，不靠声明通过。

判定只用可量的几何（位置、邻接、顺序、宽度），不判断"好不好看"；
量不出来的（比如"视线是否通透"）进人工复核，不算通过。

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple


@dataclass(frozen=True)
class Band:
    """一条水平带。`synth` 非空时这条带不是房间，是走廊 / 中庭 / 街。"""

    label: str
    depth_mm: float
    takes: Tuple[str, ...] = ()
    synth: str = ""
    name: str = ""
    #: 同一条带要分两半（客房南北两排、诊室夹医技）：a = 前半，b = 后半
    split: str = ""


@dataclass(frozen=True)
class Profile:
    bands: Tuple[Band, ...]
    west: Tuple[str, ...] = ()          # 西端块接收哪些 row.band
    west_name: str = ""
    note: str = ""


@dataclass(frozen=True)
class Device:
    """概念在平面上必须被看见的一件事。`critical` 决定它能否阻断 G3。"""

    key: str
    label: str
    critical: bool = True


#: 每种组织方式的剖面构成。顺序 = 从入口侧（南）到后场侧（北）。
PROFILES: Dict[str, Profile] = {
    # 教育：教室带（含组团厅）— 共享中庭 — 专用/办公/后勤带
    "cluster_atrium": Profile(
        bands=(Band("teaching", 7500, ("teaching",)),
               Band("atrium", 6000, synth="hall", name="共享中庭（采光顶）"),
               Band("north", 7500, ("special", "office", "service"))),
        note="南北两条教学带夹一条通高中庭，中庭代替走廊。"),
    # 教育：房间带 — 连廊 — 办公/后勤带（连廊靠后侧，单侧采光）
    "linear_corridor": Profile(
        bands=(Band("rooms", 7800, ("teaching", "special")),
               Band("corridor", 3000, synth="corridor", name="连廊"),
               Band("back", 6000, ("office", "service"))),
        note="一条连廊贯通全长，专用教室挂在连廊两端。"),
    # 教育/社区：公共带 — 校园街 — 教学带 — 办公后勤带
    "public_front": Profile(
        bands=(Band("public", 6000, ("public",)),
               Band("street", 4200, synth="hall", name="校园街（门禁分界）"),
               Band("teaching", 7500, ("teaching", "special")),
               Band("back", 6000, ("office", "service"))),
        note="临街公共体量在前，教学区退后，中间一条校园街做门禁分界。"),
    # 医疗：诊室带 — 廊 — 医技核心 — 廊 — 诊室带；候诊在西端块
    "tech_core": Profile(
        bands=(Band("clinic_a", 5000, ("outpatient",), split="a"),
               Band("corr_a", 2400, synth="corridor", name="门诊走廊"),
               Band("tech", 12000, ("tech", "service")),
               Band("corr_b", 2400, synth="corridor", name="医技走廊"),
               Band("clinic_b", 5000, ("outpatient",), split="b")),
        west=("public",), west_name="候诊区",
        note="医技成一条核心带，诊室在它的南北两侧，候诊独立在西端。"),
    # 医疗：候诊带 — 诊疗街 — 诊室带 — 医技带
    "medical_street": Profile(
        bands=(Band("waiting", 8000, ("public",)),
               Band("street", 4800, synth="hall", name="诊疗街"),
               Band("clinic", 5000, ("outpatient",)),
               Band("tech", 12000, ("tech", "service"))),
        note="一条贯通全宽的诊疗街，街两侧是诊室与医技，候诊沿街。"),
    # 医疗：诊室 — 洁净走廊 — 医技 — 污物走廊 — 服务带；候诊在西端块
    "dual_corridor": Profile(
        bands=(Band("clinic", 5000, ("outpatient",)),
               Band("clean", 2400, synth="corridor", name="洁净走廊"),
               Band("tech", 12000, ("tech",)),
               Band("dirty", 2000, synth="corridor", name="污物走廊"),
               Band("service", 3000, ("service",))),
        west=("public",), west_name="候诊区",
        note="房间夹在洁净走廊与污物走廊之间，污物从背侧服务带离开。"),
    # 工业：西端厂前区 + 单层大跨（原料—生产—成品沿长向）
    "process_line": Profile(
        bands=(Band("hall", 60000, ("production", "warehouse")),),
        west=("office", "service"), west_name="厂前区（办公/更衣/配电）",
        note="单层大跨沿长向单向流动，厂前区独立在西端。"),
    # 工业：厂前区在前，生产与仓储并列两条带
    "stacked_module": Profile(
        bands=(Band("front", 8000, ("office", "service")),
               Band("hall", 45000, ("production", "warehouse"))),
        note="厂前区在入口侧成带，生产与仓储在一条大跨带里并列。"),
    # 工业：厂前区在前，生产带 + 仓储带并列
    "front_yard": Profile(
        bands=(Band("front", 8000, ("office", "service")),
               Band("production", 48000, ("production",)),
               Band("warehouse", 24000, ("warehouse",))),
        note="厂前区在前，生产与仓储前后分带，装卸分设两端。"),
    # 酒店：客房带 — 走廊 — 客房带（电梯厅与后场在带端）
    "guest_wing": Profile(
        bands=(Band("guest_a", 8000, ("guest",), split="a"),
               Band("corridor", 1800, synth="corridor", name="客房走廊"),
               Band("guest_b", 8000, ("guest",), split="b")),
        note="双面客房走廊，两端分别是电梯厅与后场服务。"),
    # 酒店：客房带 — 走廊 — 客房带 — 服务廊 — 后场脊
    "public_core": Profile(
        bands=(Band("guest_a", 8000, ("guest",), split="a"),
               Band("corridor", 1800, synth="corridor", name="客房走廊"),
               Band("guest_b", 8000, ("guest",), split="b"),
               Band("boh_corr", 1500, synth="corridor", name="后勤通道"),
               Band("boh", 3200, ("boh", "service"))),
        note="后场独立成一条脊，用后勤通道与客房走廊完全分开。"),
    # 景观不排房间：这三项只用于图纸组织与占比表达
    "water_loop": Profile(bands=(), note="一块静水偏在一侧，园路绕水成环。"),
    "terrace": Profile(bands=(), note="2–3 级台地 + 旱溪排水线，水景让位于地形。"),
    "grove_edge": Profile(bands=(), note="边界乔木带围合，中心留活动场地，林下茶席。"),
}

#: 第二套对照方案的组织方式：必须换一种组织逻辑，不是镜像翻转。
ALT: Dict[str, str] = {
    "cluster_atrium": "linear_corridor",
    "linear_corridor": "cluster_atrium",
    "public_front": "cluster_atrium",
    "tech_core": "dual_corridor",
    "medical_street": "dual_corridor",
    "dual_corridor": "medical_street",
    "process_line": "front_yard",
    "stacked_module": "process_line",
    "front_yard": "process_line",
    "guest_wing": "public_core",
    "public_core": "guest_wing",
    "water_loop": "terrace",
    "terrace": "water_loop",
    "grove_edge": "water_loop",
}

KIND_LABEL: Dict[str, str] = {
    "cluster_atrium": "组团中庭",
    "linear_corridor": "线形连廊",
    "public_front": "公共临街",
    "tech_core": "医技居中",
    "medical_street": "诊疗街",
    "dual_corridor": "洁污双廊",
    "process_line": "单向工艺流线",
    "stacked_module": "两层模块",
    "front_yard": "厂前区分离",
    "guest_wing": "客房翼",
    "public_core": "公共核",
    "water_loop": "环水游线",
    "terrace": "台地旱溪",
    "grove_edge": "林下围合",
}

#: 概念名 → 组织方式。只用于**旧项目**（S2 还没写 plan_layout 的）回溯，
#: 新项目一律读 S2 落盘的 `plan_layout`，不靠名字猜。
NAME_KIND: Dict[str, str] = {
    "教学组团": "cluster_atrium", "共享中庭": "cluster_atrium",
    "线性教学楼": "linear_corridor", "连廊串联": "linear_corridor",
    "校园社区化": "public_front", "公共临街": "public_front",
    "医技居中": "tech_core", "门诊环绕": "tech_core",
    "洁污双廊": "dual_corridor", "模块化单元": "dual_corridor",
    "诊疗街": "medical_street", "水平发展": "medical_street",
    "工艺流线": "process_line", "单层大跨": "process_line",
    "模块化厂房": "stacked_module", "两层加货梯": "stacked_module",
    "厂前区分离": "front_yard", "物流环": "front_yard",
    "客房模数": "guest_wing", "走廊尽端服务": "guest_wing",
    "公共核心": "public_core", "后场独立": "public_core",
    "一池静水": "water_loop", "环水游线": "water_loop",
    "旱溪台地": "terrace", "少水多绿": "terrace",
    "林下茶席": "grove_edge", "边界种植": "grove_edge",
}

DEVICES: Dict[str, Tuple[Device, ...]] = {
    "cluster_atrium": (
        Device("atrium", "共享中庭（按组团成组或通宽，采光顶）"),
        Device("clusters", "教学组团 ≥2 组（组团厅分隔）"),
        Device("special_near_atrium", "专用教室贴中庭", False),
        Device("service_end", "后勤房间集中在一端", False),
    ),
    "linear_corridor": (
        Device("corridor_full", "连廊贯通全长"),
        Device("special_ends", "专用教室分布在连廊两端"),
        Device("one_side_daylight", "教室单侧采光（全部贴同一外墙）", False),
    ),
    "public_front": (
        Device("public_band", "公共带独立成段且贴入口"),
        Device("gate_line", "公共区与教学区之间有门禁分界线"),
        Device("teaching_group", "教学区独立成组", False),
    ),
    "tech_core": (
        Device("tech_center", "医技成带且位于平面中部"),
        Device("outpatient_around", "诊室在医技南北两侧"),
        Device("waiting_front", "候诊独立成块、贴入口侧"),
        Device("clean_dirty_ends", "洁净库与污物暂存分处两端", False),
    ),
    "medical_street": (
        Device("street", "诊疗街贯通全宽"),
        Device("tech_on_street", "医技贴街，可从街上直接进入"),
        Device("units_both_sides", "诊室沿街两侧展开", False),
        Device("waiting_on_street", "候诊沿街布置", False),
    ),
    "dual_corridor": (
        Device("two_corridors", "洁净走廊与污物走廊平行且各自贯通"),
        Device("rooms_between", "房间夹在两条走廊之间"),
        Device("dirty_back_exit", "污物从背侧服务带离开"),
        Device("waiting_front", "候诊独立成块、贴入口侧", False),
    ),
    "process_line": (
        Device("process_order", "原料→生产→成品沿一个方向推进"),
        Device("docks_both_ends", "进出货分处两端"),
        Device("office_front", "厂前区独立在入口端", False),
    ),
    "stacked_module": (
        Device("vertical_core", "货梯与竖向交通成组居中"),
        Device("process_order", "原料→生产→成品单向顺序"),
        Device("office_front", "厂前区独立在入口端", False),
    ),
    "front_yard": (
        Device("production_block", "生产区独立成块"),
        Device("office_front", "厂前区在前、与生产分开"),
        Device("warehouse_end", "仓储贴装卸端", False),
    ),
    "guest_wing": (
        Device("double_loaded", "一条走廊两侧排客房"),
        Device("boh_end", "服务后场在走廊尽端"),
        Device("module_even", "客房开间基本均等", False),
    ),
    "public_core": (
        Device("boh_spine", "后场集中成块、不与客房混排"),
        Device("guest_double", "客房双面布置"),
        Device("public_front", "公共/竖向交通贴前场", False),
    ),
    "water_loop": (
        Device("water_single", "水面成一块（不是满宽条带）"),
        Device("path_loop", "园路环水闭合"),
        Device("shore_nodes", "岸边有停留节点", False),
        Device("planting_layers", "边界与内部种植分层", False),
    ),
    "terrace": (
        Device("terraces", "台地分级 ≥2 级"),
        Device("swale", "旱溪成一条排水线"),
        Device("planting_zones", "向阳/背阴分区种植", False),
    ),
    "grove_edge": (
        Device("tree_belt", "边界乔木带围合"),
        Device("central_clear", "中心留出活动场地"),
        Device("tea_deck", "林下茶席有落脚点", False),
    ),
}


@dataclass
class Parti:
    kind: str = ""
    label: str = ""
    concept_id: str = ""
    concept_name: str = ""
    sector: str = ""
    devices: Tuple[Device, ...] = ()
    declared: bool = False
    reason: str = ""
    alt: str = ""

    @property
    def profile(self) -> Optional[Profile]:
        return PROFILES.get(self.kind)

    @property
    def supported(self) -> bool:
        """S2 是否明确给出了可执行的平面组织方式。"""
        return bool(self.kind and self.kind in PROFILES and self.declared)

    def to_dict(self) -> Dict[str, Any]:
        p = self.profile
        return {
            "kind": self.kind,
            "label": self.label or KIND_LABEL.get(self.kind, ""),
            "concept_id": self.concept_id,
            "concept_name": self.concept_name,
            "sector": self.sector,
            "declared": self.declared,
            "supported": self.supported,
            "reason": self.reason,
            "alt": self.alt,
            "devices": [{"key": d.key, "label": d.label, "critical": d.critical}
                        for d in self.devices],
            "bands": [{"label": b.label, "depth_mm": round(b.depth_mm),
                       "synth": b.synth, "name": b.name} for b in (p.bands if p else ())],
            "west": list(p.west) if p else [],
            "west_name": p.west_name if p else "",
            "note": p.note if p else "",
        }


def resolve(handoff: Dict[str, Any], *, sector: str = "") -> Parti:
    """从交接文件解析 parti。读不到就返回 declared=False，不猜。"""
    design = (handoff or {}).get("design") or {}
    concept_id = str((handoff or {}).get("concept_id") or "")
    name = str((handoff or {}).get("concept_name") or "")
    kind = str(design.get("plan_layout") or "")
    declared = bool(kind and kind in PROFILES)
    reason = "" if declared else ""
    if not declared:
        # 旧项目：S2 没有写 plan_layout。用概念名回溯一次，并标明是推断。
        for token, k in NAME_KIND.items():
            if token in name:
                kind, reason = k, "S2 未声明平面组织方式，按概念名回溯（需复核）"
                break
        else:
            kind, reason = "", "S2 未声明这套概念的平面组织方式，S3 只能按通用带序探索"
    status = str((handoff or {}).get("status") or "")
    if status not in ("locked", "selected_not_confirmed"):
        return Parti(sector=sector, reason="没有已选定概念：不做 parti 排布")
    out = Parti(kind=kind, label=KIND_LABEL.get(kind, ""), concept_id=concept_id,
                concept_name=name, sector=str(design.get("sector") or sector),
                devices=DEVICES.get(kind, ()), declared=declared, reason=reason,
                alt=ALT.get(kind, ""))
    if kind and not out.sector:
        out.sector = sector
    return out


# --------------------------------------------------------------------------
# 在已生成的平面上找结构
# --------------------------------------------------------------------------
def _rect(sp: Any) -> Tuple[float, float, float, float]:
    b = sp.bbox()
    return (min(b[0], b[2]), min(b[1], b[3]), max(b[0], b[2]), max(b[1], b[3]))


def measure(scheme: Any) -> Dict[str, Any]:
    """把平面压成一组可判定的量：房间框、走廊、总宽高、朝向边。"""
    rooms = [s for s in scheme.spaces if s.use not in ("envelope", "outdoor")]
    if not rooms:
        return {"rooms": [], "w": 0.0, "h": 0.0, "total": 0.0}
    rs = []
    for s in rooms:
        x0, y0, x1, y1 = _rect(s)
        rs.append({"key": str(s.properties.get("scheme_key") or s.id), "name": s.name,
                   "use": s.use, "x0": x0, "y0": y0, "x1": x1, "y1": y1,
                   "w": x1 - x0, "h": y1 - y0,
                   "cx": (x0 + x1) / 2.0, "cy": (y0 + y1) / 2.0,
                   "area": float(s.area_m2 or 0.0)})
    x0 = min(r["x0"] for r in rs)
    y0 = min(r["y0"] for r in rs)
    x1 = max(r["x1"] for r in rs)
    y1 = max(r["y1"] for r in rs)
    return {"rooms": rs, "x0": x0, "y0": y0, "x1": x1, "y1": y1,
            "w": x1 - x0, "h": y1 - y0,
            "total": sum(r["area"] for r in rs) or 1.0}


def _has(r: Dict[str, Any], *words: str) -> bool:
    return any(w in r["name"] for w in words)


def _pick(m: Dict[str, Any], *words: str) -> List[Dict[str, Any]]:
    return [r for r in m["rooms"] if _has(r, *words)]


def _circ(m: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [r for r in m["rooms"] if r["use"] == "circulation"]


def _span_x(r: Dict[str, Any], m: Dict[str, Any]) -> float:
    return r["w"] / m["w"] if m["w"] else 0.0


def _touch(r: Dict[str, Any], o: Dict[str, Any], tol: float = 600.0) -> bool:
    """两空间是否共边（水平或垂直）。"""
    x = min(r["x1"], o["x1"]) - max(r["x0"], o["x0"])
    y = min(r["y1"], o["y1"]) - max(r["y0"], o["y0"])
    return (abs(y) <= tol and x > 500) or (abs(x) <= tol and y > 500)


def _stacked_between(m: Dict[str, Any], band: Dict[str, Any]) -> Tuple[bool, bool]:
    """band 的上方 / 下方是否都有房间。"""
    below = [r for r in m["rooms"] if r is not band and abs(r["y1"] - band["y0"]) <= 600]
    above = [r for r in m["rooms"] if r is not band and abs(r["y0"] - band["y1"]) <= 600]
    return bool(below), bool(above)


def _check_atrium(m: Dict[str, Any]) -> Tuple[bool, str]:
    """中庭要么通宽一条，要么按组团分成几处、合起来仍占满全宽。

    "组团中庭"本来就该分成几处——要求单块通宽，等于逼着把中庭画成一条宽走廊，
    图上读不出组团，概念也就没落地。
    """
    a = _pick(m, "中庭")
    if not a:
        return False, "平面里没有中庭"
    area = sum(r["area"] for r in a) / m["total"]
    spans = [_span_x(r, m) for r in a]
    widest = max(spans)
    ok = area >= 0.04 and (widest >= 0.7
                           or (len(a) >= 2 and sum(spans) >= 0.6))
    if len(a) >= 2:
        head = f"{len(a)} 处中庭合计宽占 {sum(spans):.0%}（单处最宽 {widest:.0%}）"
    else:
        head = f"{a[0]['name']} 宽占 {widest:.0%}"
    return ok, head + f"、面积占 {area:.1%}" + ("" if ok else "（需通宽或成组占满、且 ≥4%）")


def _check_clusters(m: Dict[str, Any]) -> Tuple[bool, str]:
    halls = _pick(m, "组团")
    teach = [r for r in m["rooms"] if r["use"] in ("teaching", "study")]
    groups = len(halls) + 1 if teach else 0
    ok = len(teach) >= 4 and groups >= 2
    return ok, (f"{len(teach)} 间教学空间分成 {groups} 个组团"
                f"（{len(halls)} 处组团厅分隔）"
                if teach else "没有教学空间")


def _check_special_near_atrium(m: Dict[str, Any]) -> Tuple[bool, str]:
    a = _pick(m, "中庭")
    sp = _pick(m, "专用")
    if not (a and sp):
        return False, "缺中庭或专用教室"
    hit = [s["name"] for s in sp if any(_touch(s, x) for x in a)]
    return bool(hit), f"贴中庭的专用教室 {len(hit)}/{len(sp)}"


def _check_service_end(m: Dict[str, Any]) -> Tuple[bool, str]:
    svc = [r for r in m["rooms"] if r["use"] in ("bathroom", "storage", "service")]
    if not svc:
        return False, "没有后勤房间"
    west = [r for r in svc if r["cx"] <= m["x0"] + m["w"] * 0.32]
    east = [r for r in svc if r["cx"] >= m["x1"] - m["w"] * 0.32]
    ok = len(west) == len(svc) or len(east) == len(svc)
    return ok, f"后勤 {len(svc)} 间，西端 {len(west)} / 东端 {len(east)}"


def _check_corridor_full(m: Dict[str, Any]) -> Tuple[bool, str]:
    for r in _circ(m):
        if _has(r, "连廊", "走廊") and _span_x(r, m) >= 0.85:
            return True, f"{r['name']} 贯通 {_span_x(r, m):.0%}"
    return False, "没有一条贯通全长的连廊"


def _check_special_ends(m: Dict[str, Any]) -> Tuple[bool, str]:
    sp = _pick(m, "专用")
    if not sp:
        return False, "没有专用教室"
    lo = [r for r in sp if r["cx"] <= m["x0"] + m["w"] * 0.3]
    hi = [r for r in sp if r["cx"] >= m["x1"] - m["w"] * 0.3]
    ok = bool(lo and hi)
    return ok, f"专用教室 {len(sp)} 间，西端 {len(lo)} / 东端 {len(hi)}"


def _check_one_side_daylight(m: Dict[str, Any]) -> Tuple[bool, str]:
    teach = [r for r in m["rooms"] if r["use"] in ("teaching", "study")]
    if not teach:
        return False, "没有教学空间"
    south = [r for r in teach if abs(r["y0"] - m["y0"]) <= 600]
    north = [r for r in teach if abs(r["y1"] - m["y1"]) <= 600]
    ok = len(south) == len(teach) or len(north) == len(teach)
    return ok, f"{len(south)} 间贴南侧、{len(north)} 间贴北侧（共 {len(teach)} 间）"


def _check_public_band(m: Dict[str, Any]) -> Tuple[bool, str]:
    pub = [r for r in m["rooms"] if r["use"] == "public" and not _has(r, "候诊")]
    if not pub:
        return False, "本层没有公共功能（公共体量在总平面的独立区块）"
    front = [r for r in pub if r["cy"] <= m["y0"] + m["h"] * 0.4]
    return bool(front), f"公共空间 {len(pub)} 处，其中 {len(front)} 处贴入口侧"


def _check_gate_line(m: Dict[str, Any]) -> Tuple[bool, str]:
    line = _pick(m, "校园街", "门禁", "闸")
    return bool(line), ("有门禁分界线：" + line[0]["name"]) if line else "没有门禁分界线"


def _check_teaching_group(m: Dict[str, Any]) -> Tuple[bool, str]:
    teach = [r for r in m["rooms"] if r["use"] in ("teaching", "study")]
    return len(teach) >= 4, f"教学空间 {len(teach)} 间"


def _check_tech_center(m: Dict[str, Any]) -> Tuple[bool, str]:
    tech = [r for r in m["rooms"] if r["use"] in ("tech", "lab")]
    if not tech:
        return False, "没有医技空间"
    area = sum(r["area"] for r in tech) or 1.0
    cy = sum(r["cy"] * r["area"] for r in tech) / area
    rel = (cy - m["y0"]) / m["h"] if m["h"] else 0.0
    ok = 0.25 <= rel <= 0.75
    return ok, f"医技重心在进深 {rel:.0%} 处（中部为 25–75%）"


def _check_outpatient_around(m: Dict[str, Any]) -> Tuple[bool, str]:
    tech = [r for r in m["rooms"] if r["use"] in ("tech", "lab")]
    clinic = [r for r in m["rooms"] if r["use"] == "diagnosis"]
    if not (tech and clinic):
        return False, "缺医技或诊室"
    ty0 = min(r["y0"] for r in tech)
    ty1 = max(r["y1"] for r in tech)
    below = [r for r in clinic if r["y1"] <= ty0 + 600]
    above = [r for r in clinic if r["y0"] >= ty1 - 600]
    ok = bool(below and above)
    return ok, f"诊室：医技南侧 {len(below)} 间 / 北侧 {len(above)} 间"


def _check_waiting_front(m: Dict[str, Any]) -> Tuple[bool, str]:
    w = _pick(m, "候诊")
    if not w:
        return False, "没有候诊区"
    r = max(w, key=lambda x: x["area"])
    edge = min(abs(r["x0"] - m["x0"]), abs(r["y0"] - m["y0"]),
               abs(r["x1"] - m["x1"]), abs(r["y1"] - m["y1"]))
    ok = edge <= 600
    return ok, f"{r['name']} 距平面外缘 {edge / 1000:.1f} m"


def _check_clean_dirty_ends(m: Dict[str, Any]) -> Tuple[bool, str]:
    clean = _pick(m, "洁净")
    dirty = _pick(m, "污物")
    if not (clean and dirty):
        return False, "缺洁净库或污物暂存"
    gap = abs(max(r["cx"] for r in clean) - min(r["cx"] for r in dirty))
    ok = gap >= m["w"] * 0.5
    return ok, f"洁净与污物相距 {gap / 1000:.1f} m（平面宽 {m['w'] / 1000:.1f} m）"


def _check_street(m: Dict[str, Any]) -> Tuple[bool, str]:
    st = _pick(m, "诊疗街", "医疗街")
    if not st:
        return False, "没有诊疗街"
    good = [r for r in st if _span_x(r, m) >= 0.85]
    return bool(good), f"诊疗街贯通 {_span_x(good[0], m):.0%}" if good else "诊疗街未贯通"


def _check_tech_on_street(m: Dict[str, Any]) -> Tuple[bool, str]:
    st = _pick(m, "诊疗街", "医疗街")
    tech = [r for r in m["rooms"] if r["use"] in ("tech", "lab")]
    if not (st and tech):
        return False, "缺诊疗街或医技"
    hit = [r for r in tech if any(_touch(r, s) for s in st)]
    return bool(hit), f"医技 {len(hit)}/{len(tech)} 处贴街"


def _check_units_both_sides(m: Dict[str, Any]) -> Tuple[bool, str]:
    st = _pick(m, "诊疗街", "医疗街")
    clinic = [r for r in m["rooms"] if r["use"] == "diagnosis"]
    if not (st and clinic):
        return False, "缺诊疗街或诊室"
    s = st[0]
    below = [r for r in clinic if r["y1"] <= s["y0"] + 600]
    above = [r for r in clinic if r["y0"] >= s["y1"] - 600]
    ok = bool(below and above)
    return ok, f"诊室：街南 {len(below)} / 街北 {len(above)}"


def _check_waiting_on_street(m: Dict[str, Any]) -> Tuple[bool, str]:
    st = _pick(m, "诊疗街", "医疗街")
    w = _pick(m, "候诊")
    if not (st and w):
        return False, "缺诊疗街或候诊"
    hit = [r for r in w if any(_touch(r, s) for s in st)]
    return bool(hit), f"{len(hit)}/{len(w)} 处候诊临街"


def _check_two_corridors(m: Dict[str, Any]) -> Tuple[bool, str]:
    full = [r for r in _circ(m) if _has(r, "走廊") and _span_x(r, m) >= 0.8]
    ok = len(full) >= 2
    names = "、".join(r["name"] for r in full)
    return ok, f"贯通走廊 {len(full)} 条" + (f"：{names}" if names else "")


def _check_rooms_between(m: Dict[str, Any]) -> Tuple[bool, str]:
    full = sorted([r for r in _circ(m) if _has(r, "走廊") and _span_x(r, m) >= 0.8],
                  key=lambda r: r["cy"])
    if len(full) < 2:
        return False, "走廊不足两条"
    lo, hi = full[0], full[-1]
    between = [r for r in m["rooms"]
               if r["use"] not in ("circulation",) and lo["y1"] <= r["y0"] and r["y1"] <= hi["y0"]]
    ok = len(between) >= 2
    return ok, f"两条走廊之间有 {len(between)} 个房间"


def _check_dirty_back_exit(m: Dict[str, Any]) -> Tuple[bool, str]:
    dirty = _pick(m, "污物")
    corr = [r for r in _circ(m) if _has(r, "污") or _has(r, "走廊")]
    if not dirty:
        return False, "没有污物房间"
    # 取最靠北的那条走廊：污物室必须与它相邻（而不是穿过病人区）
    north = max(corr, key=lambda r: r["cy"]) if corr else None
    ok = bool(north and any(_touch(d, north) for d in dirty))
    return ok, ("污物贴背侧走廊" if ok else "污物未与背侧走廊相邻")


def _check_process_order(m: Dict[str, Any]) -> Tuple[bool, str]:
    raw = _pick(m, "原料")
    prod = _pick(m, "生产")
    fin = _pick(m, "成品")
    if not (raw and prod and fin):
        return False, f"缺工序房间（原料 {len(raw)}/生产 {len(prod)}/成品 {len(fin)}）"
    cx = [sum(r["cx"] for r in g) / len(g) for g in (raw, prod, fin)]
    ok = cx[0] < cx[1] < cx[2]
    return ok, "沿长向位置：原料 {:.1f} m → 生产 {:.1f} m → 成品 {:.1f} m".format(
        cx[0] / 1000, cx[1] / 1000, cx[2] / 1000) if ok else \
        f"顺序不对：原料 {cx[0] / 1000:.1f} / 生产 {cx[1] / 1000:.1f} / 成品 {cx[2] / 1000:.1f} m"


def _check_docks_both_ends(m: Dict[str, Any]) -> Tuple[bool, str]:
    docks = _pick(m, "卸货", "发货", "装卸")
    if len(docks) < 2:
        return False, f"装卸空间 {len(docks)} 处（需两端各一处）"
    lo = min(r["cx"] for r in docks)
    hi = max(r["cx"] for r in docks)
    ok = (hi - lo) >= m["w"] * 0.6
    return ok, f"装卸相距 {(hi - lo) / 1000:.1f} m"


def _check_office_front(m: Dict[str, Any]) -> Tuple[bool, str]:
    off = [r for r in m["rooms"] if r["use"] == "office"]
    if not off:
        return False, "没有办公/更衣房间"
    west = [r for r in off if r["cx"] <= m["x0"] + m["w"] * 0.35]
    ok = len(west) == len(off)
    return ok, f"办公 {len(off)} 间，西端 {len(west)} 间"


def _check_production_block(m: Dict[str, Any]) -> Tuple[bool, str]:
    prod = [r for r in m["rooms"] if r["use"] == "production"]
    if not prod:
        return False, "没有生产区"
    area = sum(r["area"] for r in prod)
    return area / m["total"] >= 0.25, f"生产区占使用面积 {area / m['total']:.0%}"


def _check_warehouse_end(m: Dict[str, Any]) -> Tuple[bool, str]:
    wh = [r for r in m["rooms"] if r["use"] == "warehouse"]
    if not wh:
        return False, "没有仓储"
    edge = min(min(abs(r["cx"] - m["x0"]), abs(r["cx"] - m["x1"])) for r in wh)
    return edge <= m["w"] * 0.3, f"仓储距端部 {edge / 1000:.1f} m"


def _check_vertical_core(m: Dict[str, Any]) -> Tuple[bool, str]:
    core = _pick(m, "货梯", "电梯", "楼梯")
    if not core:
        return False, "没有竖向交通空间"
    r = core[0]
    rel = abs(r["cx"] - (m["x0"] + m["w"] / 2)) / (m["w"] / 2) if m["w"] else 1.0
    return rel <= 0.6, f"{r['name']} 偏离中部 {rel:.0%}"


def _check_double_loaded(m: Dict[str, Any]) -> Tuple[bool, str]:
    guest = [r for r in m["rooms"] if r["use"] == "guest"]
    corr = [r for r in _circ(m) if _has(r, "走廊") and _span_x(r, m) >= 0.7]
    if not (guest and corr):
        return False, "缺客房或走廊"
    c = corr[0]
    below = [r for r in guest if r["y1"] <= c["y0"] + 600]
    above = [r for r in guest if r["y0"] >= c["y1"] - 600]
    ok = len(below) >= 3 and len(above) >= 3
    return ok, f"走廊两侧客房：{len(below)} / {len(above)}"


def _check_boh_end(mh: Dict[str, Any]) -> Tuple[bool, str]:
    svc = [r for r in mh["rooms"] if r["use"] in ("boh", "service", "storage")]
    if not svc:
        return False, "没有后场房间"
    east = [r for r in svc if r["cx"] >= mh["x1"] - mh["w"] * 0.35]
    ok = len(east) >= max(1, len(svc) - 1)
    return ok, f"后场 {len(svc)} 间，集中在东端 {len(east)} 间"


def _check_module_even(mh: Dict[str, Any]) -> Tuple[bool, str]:
    guest = [r for r in mh["rooms"] if r["use"] == "guest"]
    if len(guest) < 3:
        return False, "客房数量不足"
    ws = [r["w"] for r in guest]
    mean = sum(ws) / len(ws)
    cv = (sum((w - mean) ** 2 for w in ws) / len(ws)) ** 0.5 / mean if mean else 1.0
    return cv <= 0.25, f"开间离散度 {cv:.0%}（≤25% 视为同一模数）"


def _check_boh_spine(mh: Dict[str, Any]) -> Tuple[bool, str]:
    """后场是否集中成一块、且不与客房混排。

    不按"占满 50% 宽"判：后场面积常常只有楼层的 10–15%，摊在通长上必然很浅；
    真正的判据是**集中度**（后场面积 ÷ 后场包围盒）与**不混排**（不与客房交叠）。
    """
    boh = [r for r in mh["rooms"] if r["use"] in ("boh", "service", "storage")]
    if not boh:
        return False, "没有后场带"
    bx0 = min(r["x0"] for r in boh)
    by0 = min(r["y0"] for r in boh)
    bx1 = max(r["x1"] for r in boh)
    by1 = max(r["y1"] for r in boh)
    area = sum(r["area"] for r in boh)
    # 面积是 m²，坐标是 mm：包围盒先折成 m² 再比，否则集中度永远是 0
    box = max((bx1 - bx0) * (by1 - by0) / 1e6, 1e-6)
    conc = area / box
    guest = [r for r in mh["rooms"] if r["use"] == "guest"]
    mixed = [r["name"] for r in guest
             if r["x0"] < bx1 and r["x1"] > bx0 and r["y0"] < by1 and r["y1"] > by0]
    ok = conc >= 0.55 and area / mh["total"] >= 0.035 and not mixed
    return ok, (f"后场集中成 1 块（{area:,.0f} m²，占 {area / mh['total']:.0%}，"
                f"集中度 {conc:.0%}）"
                + (f"，与客房交叠 {len(mixed)} 处" if mixed else "，与客房无交叠"))


def _check_guest_double(mh: Dict[str, Any]) -> Tuple[bool, str]:
    guest = [r for r in mh["rooms"] if r["use"] == "guest"]
    return len(guest) >= 6, f"客房 {len(guest)} 间"


def _check_public_front(mh: Dict[str, Any]) -> Tuple[bool, str]:
    core = _pick(mh, "电梯", "大堂", "前台")
    if not core:
        return False, "没有电梯厅/大堂"
    r = core[0]
    edge = min(abs(r["y0"] - mh["y0"]), abs(r["y1"] - mh["y1"]))
    return edge <= mh["h"] * 0.45, f"{r['name']} 距外墙 {edge / 1000:.1f} m"


CHECKS = {
    "atrium": _check_atrium,
    "clusters": _check_clusters,
    "special_near_atrium": _check_special_near_atrium,
    "service_end": _check_service_end,
    "corridor_full": _check_corridor_full,
    "special_ends": _check_special_ends,
    "one_side_daylight": _check_one_side_daylight,
    "public_band": _check_public_band,
    "gate_line": _check_gate_line,
    "teaching_group": _check_teaching_group,
    "tech_center": _check_tech_center,
    "outpatient_around": _check_outpatient_around,
    "waiting_front": _check_waiting_front,
    "clean_dirty_ends": _check_clean_dirty_ends,
    "street": _check_street,
    "tech_on_street": _check_tech_on_street,
    "units_both_sides": _check_units_both_sides,
    "waiting_on_street": _check_waiting_on_street,
    "two_corridors": _check_two_corridors,
    "rooms_between": _check_rooms_between,
    "dirty_back_exit": _check_dirty_back_exit,
    "process_order": _check_process_order,
    "docks_both_ends": _check_docks_both_ends,
    "office_front": _check_office_front,
    "production_block": _check_production_block,
    "warehouse_end": _check_warehouse_end,
    "vertical_core": _check_vertical_core,
    "double_loaded": _check_double_loaded,
    "boh_end": _check_boh_end,
    "module_even": _check_module_even,
    "boh_spine": _check_boh_spine,
    "guest_double": _check_guest_double,
    "public_front": _check_public_front,
}


def inspect(parti: Parti, scheme: Any,
            evidence: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """在平面上逐条找结构。`evidence` 用于景观这类没有房间的图纸。"""
    out: List[Dict[str, Any]] = []
    if not parti.devices:
        return {"devices": [], "implemented": False, "critical_missing": [],
                "note": "该概念没有登记可判定的空间结构"}
    m = measure(scheme) if scheme is not None else {"rooms": [], "w": 0.0, "h": 0.0,
                                                    "total": 0.0}
    for d in parti.devices:
        if evidence and d.key in evidence:
            item = dict(evidence[d.key])
            ok = bool(item.get("ok"))
            detail = str(item.get("detail") or "")
        else:
            fn = CHECKS.get(d.key)
            if fn is None:
                out.append({"key": d.key, "label": d.label, "ok": False,
                            "detail": "该结构没有判定方法，须人工看图", "critical": d.critical})
                continue
            try:
                ok, detail = fn(m)
            except Exception as exc:                      # noqa: BLE001
                ok, detail = False, f"判定失败：{type(exc).__name__}: {exc}"
        out.append({"key": d.key, "label": d.label, "ok": bool(ok),
                    "detail": detail, "critical": d.critical})
    missing = [d["label"] for d in out if d["critical"] and not d["ok"]]
    return {
        "devices": out,
        "implemented": not missing,
        "critical_missing": missing,
        "note": ("implemented=True 表示概念要求的结构在图上都找得到；"
                 "找不到不等于画错，但那就不是这套概念的平面"),
    }


def markdown(parti: Parti, result: Optional[Dict[str, Any]] = None) -> List[str]:
    """报告里的"概念 → 平面"对照表。"""
    rows = ["## 概念 → 平面（S2 选定概念的落点）", ""]
    if not parti.kind:
        rows += [f"- {parti.reason or '没有可执行的平面组织方式'}", ""]
        return rows
    rows += [f"- 选定概念：**{parti.concept_id} {parti.concept_name}**",
             f"- 组织方式：**{parti.label}**（`{parti.kind}`）"
             + ("　由 S2 声明" if parti.declared else f"　⚠ {parti.reason}"),
             f"- 对照方案：{KIND_LABEL.get(parti.alt, parti.alt or '通用带序')}"
             f"（换一种组织逻辑，不是镜像翻转）"]
    if parti.profile and parti.profile.note:
        rows.append(f"- 剖面构成：{parti.profile.note}")
    rows.append("")
    if result:
        rows += ["| 概念要求的结构 | 图上是否成立 | 依据 |", "|---|---|---|"]
        for d in result.get("devices") or []:
            rows.append(f"| {d['label']}{'' if d['critical'] else '（次要）'} "
                        f"| {'成立' if d['ok'] else '**未找到**'} | {d['detail']} |")
        rows += ["", "> 「未找到」的结构就是这套概念没有落到的部分："
                     "不能拿通用带状平面当成概念实现。"]
    return rows


__all__ = ["ALT", "CHECKS", "DEVICES", "Device", "KIND_LABEL", "Parti", "PROFILES",
           "Profile", "Band", "inspect", "markdown", "measure", "resolve"]
