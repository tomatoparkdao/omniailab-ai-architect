"""按 S2 选定的 parti 排平面：把"概念"画成能被认出来的空间结构。

`layout.build_schemes` 原来只有一件事：同一份房间清单，带序正着排一遍、
反着排一遍（`flip`）。那能比出"哪条带该贴入口"，但它不是概念落地——
学校选"组团中庭"，排出来的还是一根走廊两条带。

这里按 `parti.PROFILES` 的剖面构成排：几条带、哪条是走廊/中庭/街、
有没有西端块。房间仍由 `planner._strip` 摆放，墙门窗家具仍由
`PlanGenerator._make_spaces/_make_elements/_metrics` 生成——**没有第二套几何**。

两套方案的差别是**组织逻辑**不同（A = 选定概念，B = 另一种 parti），
不是把同一张图左右翻一下。

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

from ..model import Project
from ..planner import PlanGenerator, RoomSpec, SchemeOptions, SchemeResult
# 复用既有排布原语：不是新写一套，而是把"带"换成 parti 给的剖面
from ..planner import _strip, _strip_fill
from . import parti as parti_mod
from .program import ProgramRow, SectorProgram

Rect = Tuple[float, float, float, float]


@dataclass
class Slot:
    label: str
    depth: float
    rows: List[RoomSpec] = field(default_factory=list)
    synth: str = ""                 # 合成空间的 recipe（corridor / hall）
    name: str = ""                  # 合成空间的名字
    key: str = ""                   # 合成空间的 key


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _match(row: ProgramRow, takes: Sequence[str]) -> bool:
    return row.zone in takes or row.band in takes


def assign(program: SectorProgram, prof: parti_mod.Profile) -> Dict[str, Any]:
    """把房间分到 parti 的各条带。

    先按 `takes`（房间的 zone 或带）匹配；同一条带要分两半的
    （客房南北两排、诊室夹医技），用 `split` 把前一带的一半挪到后一带。
    西端块先匹配，避免被后面的带抢走。
    """
    groups: Dict[str, List[ProgramRow]] = {b.label: [] for b in prof.bands}
    west: List[ProgramRow] = []
    for r in program.rows:
        if prof.west and _match(r, prof.west):
            west.append(r)
            continue
        for b in prof.bands:
            if not b.synth and _match(r, b.takes):
                groups[b.label].append(r)
                break
        else:
            # 没匹配上的房间不能丢：落到最后一个能装房间的带里，并留在报告里
            for b in reversed(prof.bands):
                if not b.synth:
                    groups[b.label].append(r)
                    break
    # 分半：同 takes 的相邻带，a 拿前半、b 拿后半。
    # 注意中间可能隔着走廊（合成带），所以要往回找"分半的 a"，不是看前一条。
    for i, b in enumerate(prof.bands):
        if b.split != "b":
            continue
        prev = next((x for x in reversed(prof.bands[:i])
                     if x.split == "a" and x.takes == b.takes), None)
        if prev is None:
            continue
        rows = groups.get(prev.label) or []
        k = int(math.ceil(len(rows) / 2.0))
        groups[prev.label] = rows[:k]
        groups[b.label] = rows[k:]
    return {"bands": groups, "west": west}


def _depth_of(row: ProgramRow, sector: str) -> float:
    """这条带至少要有多深：取带深声明与该房间的最小进深中的大者。

    不用 `DEPTH_BY_SECTOR` 的行业大值——那是给"一整条通用带"准备的，
    例如厂房 workshop 60 m。parti 已经把带分好，这里只需要"排得下"。
    """
    from ..planner import ROOM_RECIPES
    del sector
    return float(ROOM_RECIPES.get(row.recipe, {}).get("min_depth", 3000))


# --------------------------------------------------------------------------
# 外轮廓：由 parti 的剖面反算（轮廓跟着组织方式走，不是一律板式）
# --------------------------------------------------------------------------
def profile_size(program: SectorProgram, sector: str, kind: str) -> Optional[Dict[str, Any]]:
    prof = parti_mod.PROFILES.get(kind)
    if prof is None or not prof.bands:
        return None
    g = assign(program, prof)
    depths: List[Tuple[str, float]] = []
    w_room = 0.0
    for b in prof.bands:
        rows = g["bands"].get(b.label, [])
        if b.synth:
            depths.append((b.label, float(b.depth_mm)))
            continue
        d = max([b.depth_mm] + [_depth_of(r, sector) for r in rows])
        depths.append((b.label, d))
        area = sum(r.area_m2 for r in rows)
        if rows:
            w_room = max(w_room, area * 1e6 / d)
    h = sum(d for _l, d in depths)
    west_area = sum(r.area_m2 for r in g["west"])
    w_west = west_area * 1e6 / h if (west_area and h) else 0.0
    w = w_room + w_west
    if w <= 0:
        return None
    # 取整到 300 mm，避免 69.83 m 这种假精度
    w = math.ceil(w / 300.0) * 300.0
    h = math.ceil(h / 300.0) * 300.0
    return {"width_mm": w, "depth_mm": h, "bands": depths, "west_mm": w_west,
            "groups": g, "note": f"轮廓按「{parti_mod.KIND_LABEL.get(kind, kind)}」"
                                 "的剖面构成反算：带深由房间类型定，宽度由最挤的一条带定"}


# --------------------------------------------------------------------------
# 排布
# --------------------------------------------------------------------------
def _synth(by_key: Dict[str, RoomSpec], key: str, name: str, recipe: str,
           area: float) -> RoomSpec:
    sp = RoomSpec(key=key, name=name, target_area_m2=max(area, 1.0),
                  zone="service", recipe=recipe)
    by_key[key] = sp
    return sp


def _pad(band: Rect, rows: Sequence[RoomSpec], placed: Dict[str, Rect],
         by_key: Dict[str, RoomSpec], res: List[str], tag: str = "") -> None:
    """带里剩一点宽度就摊给房间；剩得多就画成"预留"，不留空白。"""
    x0, y0, x1, y1 = band
    if not placed:
        return
    used = sum(placed[r.key][2] - placed[r.key][0] for r in rows if r.key in placed)
    span = x1 - x0
    residual = span - used
    if residual <= 1.0:
        return
    if residual <= span * 0.22:
        k = span / used if used > 0 else 1.0
        for r in rows:
            rect = placed.get(r.key)
            if rect is None:
                continue
            placed[r.key] = (x0 + (rect[0] - x0) * k, rect[1],
                             x0 + (rect[2] - x0) * k, rect[3])
            if k > 1.10:
                got = (placed[r.key][2] - placed[r.key][0]) * (y1 - y0) / 1e6
                res.append(f"{r.name}：按带宽放大到 {got:.1f}㎡（任务书 "
                           f"{r.target_area_m2:.1f}㎡）——楼层轮廓比房间需求宽，"
                           "差额不是任务书的要求" + (f"［{tag}］" if tag else ""))
        return
    key = "reserve" + str(len(placed))
    _synth(by_key, key, "预留（交通 / 辅助）", "hall", residual * (y1 - y0) / 1e6)
    placed[key] = (x1 - residual, y0, x1, y1)
    res.append("走廊尽头留出 {:.1f} m 宽作为预留：任务书没有占满这一带，"
               "不替客户编房间".format(residual / 1000))


def _stack(core: Rect, slots: Sequence[Slot], *, flip: bool = False,
           res: Optional[List[str]] = None) -> Tuple[Dict[str, Rect], Dict[str, RoomSpec]]:
    """按 parti 的剖面把带从入口侧摞起来。flip 只用于对照方案的方向调整。"""
    x0, y0, x1, y1 = core
    W = x1 - x0
    placed: Dict[str, Rect] = {}
    by_key: Dict[str, RoomSpec] = {}
    warn = res if res is not None else []
    y = y0
    for i, slot in enumerate(slots):
        d = slot.depth
        band = (x0, y1 - (y + d - y0), x1, y1 - (y - y0)) if flip else (x0, y, x1, y + d)
        if slot.synth:
            key = slot.key or ("corridor" if slot.synth == "corridor" and "corridor" not in placed
                               else f"sp{i}")
            _synth(by_key, key, slot.name or "交通空间", slot.synth, d * W / 1e6)
            placed[key] = band
        elif slot.rows:
            want = sorted(slot.rows, key=lambda s: s.priority)
            p, dev, residual = _strip(band, want, "x")
            placed.update(p)
            for spec in want:
                by_key[spec.key] = spec
            warn.extend(dev.values())
            if residual > 0:
                _pad(band, want, placed, by_key, warn, tag=slot.label)
        y += d
    return placed, by_key


def _block(core: Rect, rows: Sequence[RoomSpec], width: float, *,
           east: bool = False, vertical: bool = True,
           res: Optional[List[str]] = None) -> Tuple[Dict[str, Rect], Dict[str, RoomSpec],
                                                    Dict[str, str]]:
    """端部块：候诊区、厂前区这类不参与水平带的空间。

    返回 `(placed, by_key, dev)`，与 `_strip` 同一口径——调用方按三值解包，
    偏差（放不下/被放大）由调用方并入 `res`，不在这里悄悄叠加。
    """
    x0, y0, x1, y1 = core
    rect = (x1 - width, y0, x1, y1) if east else (x0, y0, x0 + width, y1)
    out: Dict[str, RoomSpec] = {s.key: s for s in rows}
    dev: Dict[str, str] = {}
    if not rows:
        return {}, out, dev
    if vertical:
        placed, dev, residual = _strip(rect, sorted(rows, key=lambda s: s.priority), "y")
        if residual > 1.0 and residual <= (y1 - y0) * 0.22:
            k = (y1 - y0) / max(sum(placed[r.key][3] - placed[r.key][1] for r in rows), 1.0)
            for r in rows:
                p = placed[r.key]
                placed[r.key] = (p[0], y0 + (p[1] - y0) * k, p[2], y0 + (p[3] - y0) * k)
    else:
        placed, dev, residual = _strip(rect, sorted(rows, key=lambda s: s.priority), "x")
    if res is not None:
        res.extend(dev.values())
    return placed, out, dev


def _specs(gen: PlanGenerator) -> List[RoomSpec]:
    return gen.read_program()


def _interleave(rows: Sequence[RoomSpec], blocks: Sequence[RoomSpec]
                ) -> List[RoomSpec]:
    """把候诊这类"分组公共空间"插进诊室带：每几间诊室一处候诊。

    诊室一条排到底、候诊全挤在端部，图上是"一排小格子 + 一个大空块"，
    既不像门诊，也会在带尽头留下没人用的面积。
    """
    rows = list(rows)
    blocks = list(blocks)
    if not blocks or not rows:
        return rows
    groups = max(1, min(len(blocks), int(math.ceil(len(rows) / 4.0))))
    per = int(math.ceil(len(rows) / float(groups)))
    out: List[RoomSpec] = []
    bi = 0
    for i, r in enumerate(rows):
        out.append(r)
        if (i + 1) % per == 0 and bi < len(blocks):
            out.append(blocks[bi])
            bi += 1
    out.extend(blocks[bi:])
    return out


def _by_zone(specs: Sequence[RoomSpec]) -> Dict[str, List[RoomSpec]]:
    out: Dict[str, List[RoomSpec]] = {}
    for s in specs:
        out.setdefault(s.zone or s.band, []).append(s)
    return out


def _half(rows: Sequence[RoomSpec]) -> Tuple[List[RoomSpec], List[RoomSpec]]:
    """一条带里的房间分两半：南侧与北侧。"""
    rows = list(rows)
    mid = int(math.ceil(len(rows) / 2.0))
    return rows[:mid], rows[mid:]


def _split_by_frontage(rows: Sequence[RoomSpec], north_free: float,
                       south_free: float) -> Tuple[List[RoomSpec], List[RoomSpec]]:
    """按两条带各自剩下的面宽分客房。

    一条带里塞了电梯厅或后场，就少排几间客房；否则那条带被压扁、
    另一条带尽头留出一大块"预留"——图上就是一块空地，不像酒店平面。
    """
    rows = list(rows)
    if len(rows) < 2:
        return rows, []
    total = max(north_free, 0.0) + max(south_free, 0.0)
    if total <= 0:
        return _half(rows)
    k = int(round(len(rows) * max(north_free, 0.0) / total))
    k = max(1, min(len(rows) - 1, k))
    return rows[:k], rows[k:]


# --------------------------------------------------------------------------
# 各组织方式
# --------------------------------------------------------------------------
def _cluster_atrium(gen: PlanGenerator, opts: SchemeOptions,
                    res: List[str]) -> Tuple[Dict[str, Rect], Dict[str, RoomSpec]]:
    """教室带（组团厅分隔）— 共享中庭 — 专用/办公/后勤带。"""
    _env, core = gen.shell(opts)
    x0, y0, x1, y1 = core
    H = y1 - y0
    specs = _specs(gen)
    g = _by_zone(specs)
    teach = sorted(g.get("teaching", []), key=lambda s: s.priority)
    north = sorted(g.get("special", []) + g.get("office", []) + g.get("service", []),
                   key=lambda s: s.priority)
    atrium_d = _clamp(H * 0.26, 5000.0, 8000.0)
    rest = H - atrium_d
    d_south = max(7200.0, rest * 0.56)
    d_north = rest - d_south
    groups = max(2, min(3, int(round(len(teach) / 4.0)) or 2))
    per = int(math.ceil(len(teach) / groups)) or 1

    placed: Dict[str, Rect] = {}
    by_key: Dict[str, RoomSpec] = {}
    # 南带：教室 + 组团厅（每 per 间教室插一处，把长条切成组团）
    south = (x0, y0, x1, y0 + d_south)
    seq: List[RoomSpec] = []
    hall_n = 0
    for i, s in enumerate(teach):
        if i and i % per == 0:
            hall_n += 1
            seq.append(_synth(by_key, f"hall{hall_n}",
                              f"组团厅 {hall_n}", "hall",
                              3600.0 * d_south / 1e6))
        seq.append(s)
        by_key[s.key] = s
    p, dev, residual = _strip(south, seq, "x")
    placed.update(p)
    res.extend(dev.values())
    if residual > 0:
        _pad(south, seq, placed, by_key, res, "教学带")

    # 中庭：按组分成几处，中间用连桥相接。
    # 一整条通长"中庭"其实就是条宽走廊——图上读不出"组团"，也就没落实概念。
    link = 2400.0 if groups > 1 else 0.0
    seg = (x1 - x0 - link * (groups - 1)) / groups
    ay0, ay1 = y0 + d_south, y0 + d_south + atrium_d
    for i in range(groups):
        sx = x0 + i * (seg + link)
        key = f"atrium{i + 1}"
        _synth(by_key, key, f"组团中庭 {i + 1}（采光顶）", "hall", seg * atrium_d / 1e6)
        placed[key] = (sx, ay0, sx + seg, ay1)
        if i < groups - 1:
            lk = f"link{i + 1}"
            _synth(by_key, lk, f"连桥 {i + 1}", "corridor", link * atrium_d / 1e6)
            placed[lk] = (sx + seg, ay0, sx + seg + link, ay1)

    # 北带
    north_rect = (x0, y0 + d_south + atrium_d, x1, y1)
    p2, dev2, residual2 = _strip(north_rect, north, "x")
    placed.update(p2)
    for s in north:
        by_key[s.key] = s
    res.extend(dev2.values())
    if residual2 > 0:
        _pad(north_rect, north, placed, by_key, res, "后勤带")
    return placed, by_key


def _linear_corridor(gen: PlanGenerator, opts: SchemeOptions,
                     res: List[str]) -> Tuple[Dict[str, Rect], Dict[str, RoomSpec]]:
    """教室带 — 贯通连廊 — 专用/办公/后勤带：两侧都挂房间，没有空段。

    与"组团中庭"的差别不在镜像，而在剖面：这里中庭退成一条连廊，
    教室连成一排（年级段靠端部），专用教室与办公整层集中在北侧。
    """
    _env, core = gen.shell(opts)
    x0, y0, x1, y1 = core
    H = y1 - y0
    specs = _specs(gen)
    g = _by_zone(specs)
    teach = sorted(g.get("teaching", []), key=lambda s: s.priority)
    back = sorted(g.get("special", []) + g.get("office", []) + g.get("service", []),
                  key=lambda s: s.priority)
    corr_d = 3000.0
    # 带深按"面积 ÷ 轮廓宽"定，两条带一起按比例吃满进深：
    # 用固定比例切分时，教室带会比需要更深、房间被压窄，尽头空出一大块"预留"。
    W = max(x1 - x0, 1.0)
    a_rooms = sum(s.target_area_m2 for s in teach) * 1e6
    a_back = sum(s.target_area_m2 for s in back) * 1e6
    want_r, want_b = a_rooms / W, a_back / W
    avail = max(H - corr_d, 6000.0)
    k = avail / max(want_r + want_b, 1.0)
    rooms_d = max(6000.0, want_r * k)
    placed: Dict[str, Rect] = {}
    by_key = {s.key: s for s in teach + back}
    p, dev, residual = _strip((x0, y0, x1, y0 + rooms_d), teach, "x")
    placed.update(p)
    res.extend(dev.values())
    if residual > 0:
        _pad((x0, y0, x1, y0 + rooms_d), teach, placed, by_key, res, "教室带")
    _synth(by_key, "corridor", "连廊（贯通全长）", "corridor", corr_d * (x1 - x0) / 1e6)
    placed["corridor"] = (x0, y0 + rooms_d, x1, y0 + rooms_d + corr_d)
    north = (x0, y0 + rooms_d + corr_d, x1, y1)
    p2, dev2, residual2 = _strip(north, back, "x")
    placed.update(p2)
    res.extend(dev2.values())
    if residual2 > 0:
        _pad(north, back, placed, by_key, res, "专用/办公带")
    return placed, by_key


def _public_front(gen: PlanGenerator, opts: SchemeOptions,
                  res: List[str]) -> Tuple[Dict[str, Rect], Dict[str, RoomSpec]]:
    """公共带 — 校园街（门禁分界）— 教学带 — 办公后勤带。"""
    _env, core = gen.shell(opts)
    x0, y0, x1, y1 = core
    H = y1 - y0
    specs = _specs(gen)
    g = _by_zone(specs)
    public = sorted(g.get("public", []) + g.get("outpatient", []), key=lambda s: s.priority)
    teach = sorted(g.get("teaching", []) + g.get("special", []), key=lambda s: s.priority)
    back = sorted(g.get("office", []) + g.get("service", []), key=lambda s: s.priority)
    street_d = 4200.0
    if not public:
        res.append("本层没有可对外独立的公共功能：公共临街只能在总平面与首层落地，"
                   "标准层只体现「教学区独立成组 + 门禁分界」")
        return _cluster_atrium(gen, opts, res)
    pub_d = max(6000.0, min(H * 0.26, 9000.0))
    rest = H - pub_d - street_d
    teach_d = max(7200.0, rest * 0.62)
    back_d = rest - teach_d
    placed: Dict[str, Rect] = {}
    by_key = {s.key: s for s in public + teach + back}
    p, dev, r1 = _strip((x0, y0, x1, y0 + pub_d), public, "x")
    placed.update(p)
    res.extend(dev.values())
    if r1 > 0:
        _pad((x0, y0, x1, y0 + pub_d), public, placed, by_key, res, "公共带")
    _synth(by_key, "street", "校园街（门禁分界）", "hall", street_d * (x1 - x0) / 1e6)
    placed["street"] = (x0, y0 + pub_d, x1, y0 + pub_d + street_d)
    p2, dev2, r2 = _strip((x0, y0 + pub_d + street_d, x1, y0 + pub_d + street_d + teach_d),
                          teach, "x")
    placed.update(p2)
    res.extend(dev2.values())
    if r2 > 0:
        _pad((x0, y0 + pub_d + street_d, x1, y0 + pub_d + street_d + teach_d),
             teach, placed, by_key, res, "教学带")
    p3, dev3, r3 = _strip((x0, y1 - back_d, x1, y1), back, "x")
    placed.update(p3)
    res.extend(dev3.values())
    if r3 > 0:
        _pad((x0, y1 - back_d, x1, y1), back, placed, by_key, res, "后勤带")
    return placed, by_key


def _tech_core(gen: PlanGenerator, opts: SchemeOptions,
               res: List[str]) -> Tuple[Dict[str, Rect], Dict[str, RoomSpec]]:
    """门诊大厅（端部）— 诊室带（候诊分组插入）/ 廊 / 医技带 / 廊 / 诊室带。"""
    _env, core = gen.shell(opts)
    x0, y0, x1, y1 = core
    H = y1 - y0
    specs = _specs(gen)
    g = _by_zone(specs)
    clinic = sorted(g.get("outpatient", []), key=lambda s: s.priority)
    tech = sorted(g.get("tech", []) + g.get("service", []), key=lambda s: s.priority)
    pub = sorted(g.get("public", []), key=lambda s: s.priority)
    # 候诊按门诊单元分设：夹在诊室之间，患者不用穿过整条走廊去等号
    wait = [s for s in pub if "候诊" in s.name]
    hall = [s for s in pub if "候诊" not in s.name]
    hall_w = 0.0
    if hall:
        hall_w = _clamp(sum(s.target_area_m2 for s in hall) * 1e6 / max(H, 1.0),
                        3000.0, 24000.0)
    corr = 2400.0
    body = H - 2 * corr
    # 医技带深度按"医技面积 ÷ 带长"定：固定比例切分会把医技带撑得比房间需求深，
    # 尽头留出一大块"预留"——那正是把平面画成条形图的样子。
    tech_area = sum(s.target_area_m2 for s in tech) * 1e6
    tech_d = _clamp(tech_area / max(x1 - x0, 1.0), 7000.0, 14000.0)
    tech_d = min(tech_d, max(7000.0, body - 9000.0))
    clinic_d = (body - tech_d) / 2.0
    bx1 = x1 - hall_w if hall else x1
    placed: Dict[str, Rect] = {}
    by_key: Dict[str, RoomSpec] = {}
    a, b = _half(clinic)
    wa, wb = _half(wait)
    # 北侧诊室（含候诊）/ 医技 / 南侧诊室（含候诊）
    p1, d1, r1 = _strip((x0, y0, bx1, y0 + clinic_d), _interleave(b, wb), "x")
    placed.update(p1)
    by_key.update({s.key: s for s in b + wb})
    res.extend(d1.values())
    if r1 > 0:
        _pad((x0, y0, bx1, y0 + clinic_d), b + wb, placed, by_key, res, "诊室带")
    if hall:
        ph, dh, rh = _strip((bx1, y0, x1, y1), hall, "y")
        placed.update(ph)
        by_key.update({s.key: s for s in hall})
        res.extend(dh.values())
        if rh > 0:
            _pad((bx1, y0, x1, y1), hall, placed, by_key, res, "门诊大厅")
    _synth(by_key, "corridor", "门诊走廊", "corridor", corr * (bx1 - x0) / 1e6)
    placed["corridor"] = (x0, y0 + clinic_d, bx1, y0 + clinic_d + corr)
    y2 = y0 + clinic_d + corr
    p2, d2, r2 = _strip((x0, y2, bx1, y2 + tech_d), tech, "x")
    placed.update(p2)
    by_key.update({s.key: s for s in tech})
    res.extend(d2.values())
    if r2 > 0:
        _pad((x0, y2, bx1, y2 + tech_d), tech, placed, by_key, res, "医技带")
    _synth(by_key, "corridor2", "医技走廊", "corridor", corr * (bx1 - x0) / 1e6)
    placed["corridor2"] = (x0, y2 + tech_d, bx1, y2 + tech_d + corr)
    y3 = y2 + tech_d + corr
    p3, d3, r3 = _strip((x0, y3, bx1, y1), _interleave(a, wa), "x")
    placed.update(p3)
    by_key.update({s.key: s for s in a + wa})
    res.extend(d3.values())
    if r3 > 0:
        _pad((x0, y3, bx1, y1), a + wa, placed, by_key, res, "诊室带")
    return placed, by_key


def _medical_street(gen: PlanGenerator, opts: SchemeOptions,
                    res: List[str]) -> Tuple[Dict[str, Rect], Dict[str, RoomSpec]]:
    """候诊带 — 诊疗街 — 诊室带 — 医技带。"""
    _env, core = gen.shell(opts)
    x0, y0, x1, y1 = core
    H = y1 - y0
    specs = _specs(gen)
    g = _by_zone(specs)
    wait = sorted(g.get("public", []), key=lambda s: s.priority)
    clinic = sorted(g.get("front", []), key=lambda s: s.priority)
    tech = sorted(g.get("tech", []) + g.get("service", []), key=lambda s: s.priority)
    street_d = 4800.0
    wait_d = _clamp(H * 0.22, 5000.0, 9000.0)
    clinic_d = _clamp(H * 0.18, 4200.0, 6000.0)
    tech_d = H - street_d - wait_d - clinic_d
    placed: Dict[str, Rect] = {}
    by_key = {s.key: s for s in wait + clinic + tech}
    y = y0
    if wait:
        p, d, r = _strip((x0, y, x1, y + wait_d), wait, "x")
        placed.update(p)
        res.extend(d.values())
        if r > 0:
            _pad((x0, y, x1, y + wait_d), wait, placed, by_key, res, "候诊带")
        y += wait_d
    _synth(by_key, "street", "诊疗街（贯通全宽）", "hall", street_d * (x1 - x0) / 1e6)
    placed["street"] = (x0, y, x1, y + street_d)
    y += street_d
    p2, d2, r2 = _strip((x0, y, x1, y + clinic_d), clinic, "x")
    placed.update(p2)
    res.extend(d2.values())
    if r2 > 0:
        _pad((x0, y, x1, y + clinic_d), clinic, placed, by_key, res, "诊室带")
    y += clinic_d
    p3, d3, r3 = _strip((x0, y, x1, y + tech_d), tech, "x")
    placed.update(p3)
    res.extend(d3.values())
    if r3 > 0:
        _pad((x0, y, x1, y + tech_d), tech, placed, by_key, res, "医技带")
    return placed, by_key


def _dual_corridor(gen: PlanGenerator, opts: SchemeOptions,
                   res: List[str]) -> Tuple[Dict[str, Rect], Dict[str, RoomSpec]]:
    """诊室 — 洁净走廊 — 医技 — 污物走廊 — 服务带；候诊在西端块。"""
    _env, core = gen.shell(opts)
    x0, y0, x1, y1 = core
    H = y1 - y0
    specs = _specs(gen)
    g = _by_zone(specs)
    clinic = sorted(g.get("front", []), key=lambda s: s.priority)
    tech = sorted(g.get("tech", []), key=lambda s: s.priority)
    svc = sorted(g.get("service", []), key=lambda s: s.priority)
    wait = sorted(g.get("public", []), key=lambda s: s.priority)
    clean, dirty = 2400.0, 2000.0
    body = H - clean - dirty - 3000.0
    clinic_d = _clamp(body * 0.26, 4500.0, 6000.0)
    tech_d = body - clinic_d
    wait_w = _clamp(sum(s.target_area_m2 for s in wait) * 1e6 / max(H, 1.0),
                    3000.0, 24000.0) if wait else 0.0
    bx1 = x1 - wait_w if wait else x1
    placed: Dict[str, Rect] = {}
    by_key: Dict[str, RoomSpec] = {}
    y = y0
    p1, d1, r1 = _strip((x0, y, bx1, y + clinic_d), clinic, "x")
    placed.update(p1)
    by_key.update({s.key: s for s in clinic})
    res.extend(d1.values())
    if r1 > 0:
        _pad((x0, y, bx1, y + clinic_d), clinic, placed, by_key, res, "诊室带")
    y += clinic_d
    _synth(by_key, "corridor", "洁净走廊（医护/病人/洁净供应）", "corridor",
           clean * (bx1 - x0) / 1e6)
    placed["corridor"] = (x0, y, bx1, y + clean)
    y += clean
    p2, d2, r2 = _strip((x0, y, bx1, y + tech_d), tech, "x")
    placed.update(p2)
    by_key.update({s.key: s for s in tech})
    res.extend(d2.values())
    if r2 > 0:
        _pad((x0, y, bx1, y + tech_d), tech, placed, by_key, res, "医技带")
    y += tech_d
    _synth(by_key, "corridor2", "污物走廊（污衣/垃圾/遗体）", "corridor",
           dirty * (bx1 - x0) / 1e6)
    placed["corridor2"] = (x0, y, bx1, y + dirty)
    y += dirty
    p3, d3, r3 = _strip((x0, y, bx1, y1), svc, "x")
    placed.update(p3)
    by_key.update({s.key: s for s in svc})
    res.extend(d3.values())
    if r3 > 0:
        _pad((x0, y, bx1, y1), svc, placed, by_key, res, "服务带")
    if wait:
        # `_block(res=res)` 已把偏差并入 res；这里只收坐标，别把 RoomSpec 塞进警告
        pw, _bw, _dw = _block((bx1, y0, x1, y1), wait, x1 - bx1, res=res)
        placed.update(pw)
        by_key.update({s.key: s for s in wait})
    return placed, by_key


def _process_line(gen: PlanGenerator, opts: SchemeOptions,
                  res: List[str]) -> Tuple[Dict[str, Rect], Dict[str, RoomSpec]]:
    """西端厂前区 + 单层大跨：原料 → 生产 → 成品 沿长向推进，装卸分两端。"""
    _env, core = gen.shell(opts)
    x0, y0, x1, y1 = core
    specs = _specs(gen)
    g = _by_zone(specs)
    annex = sorted(g.get("office", []), key=lambda s: s.priority)
    svc = sorted(g.get("service", []), key=lambda s: s.priority)
    raw = [s for s in specs if "原料" in s.name]
    prod = [s for s in specs if s.name.startswith("生产") or "生产区" in s.name]
    fin = [s for s in specs if "成品" in s.name]
    clean = [s for s in specs if "洁净" in s.name]
    rest = [s for s in specs if s not in raw + prod + fin + clean + annex + svc]
    H = y1 - y0
    annex_area = sum(s.target_area_m2 for s in annex + svc)
    annex_w = _clamp(annex_area * 1e6 / max(H, 1.0), 6000.0, 30000.0)
    placed: Dict[str, Rect] = {}
    by_key = {s.key: s for s in specs}
    if annex or svc:
        pw, _bw, _dw = _block((x0, y0, x0 + annex_w, y1), annex + svc, annex_w, res=res)
        placed.update(pw)
    hx0 = x0 + annex_w if (annex or svc) else x0
    dock_w = min(4000.0, (x1 - hx0) * 0.06)
    # 沿长向：原料 → 洁净 → 生产 → 其他 → 成品
    band = (hx0, y0, x1, y1)
    seq = raw + clean + prod + rest + fin
    p, dev, residual = _strip(band, seq, "x")
    placed.update(p)
    res.extend(dev.values())
    # 装卸分两端：各自的端部留一条 4 m 深的平台，标出方向
    _synth(by_key, "dock_in", "原料卸货平台（西端）", "corridor", dock_w * 3000 / 1e6)
    placed["dock_in"] = (hx0 + 600.0, y0 + 600.0, hx0 + 600.0 + dock_w * 0.35, y0 + 3600.0)
    _synth(by_key, "dock_out", "成品发货平台（东端）", "corridor", dock_w * 3000 / 1e6)
    placed["dock_out"] = (x1 - 600.0 - dock_w * 0.35, y0 + 600.0, x1 - 600.0, y0 + 3600.0)
    del residual
    return placed, by_key


def _stacked_module(gen: PlanGenerator, opts: SchemeOptions,
                    res: List[str]) -> Tuple[Dict[str, Rect], Dict[str, RoomSpec]]:
    """厂前区在前 + 一条大跨带；货梯成组居中（两层方案的当层表达）。"""
    _env, core = gen.shell(opts)
    x0, y0, x1, y1 = core
    H = y1 - y0
    specs = _specs(gen)
    g = _by_zone(specs)
    front = sorted(g.get("office", []) + g.get("service", []), key=lambda s: s.priority)
    hall = sorted(g.get("production", []) + g.get("warehouse", []),
                  key=lambda s: s.priority)
    front_d = _clamp(H * 0.18, 6000.0, 9000.0)
    placed: Dict[str, Rect] = {}
    by_key = {s.key: s for s in specs}
    p, dev, r = _strip((x0, y0, x1, y0 + front_d), front, "x")
    placed.update(p)
    res.extend(dev.values())
    if r > 0:
        _pad((x0, y0, x1, y0 + front_d), front, placed, by_key, res, "厂前区")
    hall_rect = (x0, y0 + front_d, x1, y1)
    p2, dev2, r2 = _strip(hall_rect, hall, "x")
    placed.update(p2)
    res.extend(dev2.values())
    if r2 > 0:
        _pad(hall_rect, hall, placed, by_key, res, "生产带")
    cw = max(3600.0, (x1 - x0) * 0.06)
    cx = x0 + (x1 - x0) / 2.0 - cw / 2.0
    _synth(by_key, "core", "货梯与楼梯（居中成组）", "corridor", cw * 6000 / 1e6)
    placed["core"] = (cx, hall_rect[1], cx + cw, min(hall_rect[1] + 6000.0, hall_rect[3]))
    return placed, by_key


def _front_yard(gen: PlanGenerator, opts: SchemeOptions,
                res: List[str]) -> Tuple[Dict[str, Rect], Dict[str, RoomSpec]]:
    """厂前区在前 — 生产带 — 仓储带。"""
    _env, core = gen.shell(opts)
    x0, y0, x1, y1 = core
    H = y1 - y0
    specs = _specs(gen)
    g = _by_zone(specs)
    front = sorted(g.get("office", []) + g.get("service", []), key=lambda s: s.priority)
    prod = sorted(g.get("production", []), key=lambda s: s.priority)
    wh = sorted(g.get("warehouse", []), key=lambda s: s.priority)
    front_d = _clamp(H * 0.12, 6000.0, 9000.0)
    rest = H - front_d
    prod_d = max(7200.0, rest * 0.62)
    wh_d = rest - prod_d
    placed: Dict[str, Rect] = {}
    by_key = {s.key: s for s in specs}
    for (label, rows, rect) in (
            ("厂前区", front, (x0, y0, x1, y0 + front_d)),
            ("生产带", prod, (x0, y0 + front_d, x1, y0 + front_d + prod_d)),
            ("仓储带", wh, (x0, y1 - wh_d, x1, y1))):
        if not rows:
            continue
        p, dev, r = _strip(rect, rows, "x")
        placed.update(p)
        res.extend(dev.values())
        if r > 0:
            _pad(rect, rows, placed, by_key, res, label)
    return placed, by_key


def _guest_wing(gen: PlanGenerator, opts: SchemeOptions,
                res: List[str]) -> Tuple[Dict[str, Rect], Dict[str, RoomSpec]]:
    """双面客房走廊：电梯厅在带端，服务后场在另一端。"""
    _env, core = gen.shell(opts)
    x0, y0, x1, y1 = core
    specs = _specs(gen)
    g = _by_zone(specs)
    guest = sorted(g.get("guest", []), key=lambda s: s.priority)
    lift = sorted(g.get("public", []), key=lambda s: s.priority)
    boh = sorted(g.get("boh", []) + g.get("service", []), key=lambda s: s.priority)
    corr = 1800.0
    d = (y1 - y0 - corr) / 2.0
    placed: Dict[str, Rect] = {}
    by_key: Dict[str, RoomSpec] = {}
    # 北带要装电梯厅与后场，客房少排几间，南带补上——两条带前端都排满
    fixed_w = sum(s.target_area_m2 for s in lift + boh) * 1e6 / max(d, 1.0)
    ga, gb = _split_by_frontage(guest, (x1 - x0) - fixed_w, x1 - x0)
    # 北带 = 电梯厅 + 客房 + 后场（东端）
    row = lift + ga + boh
    p, dev, r = _strip((x0, y0 + d + corr, x1, y1), row, "x")
    placed.update(p)
    by_key.update({s.key: s for s in row})
    res.extend(dev.values())
    if r > 0:
        _pad((x0, y0 + d + corr, x1, y1), row, placed, by_key, res, "客房带")
    _synth(by_key, "corridor", "客房走廊", "corridor", corr * (x1 - x0) / 1e6)
    placed["corridor"] = (x0, y0 + d, x1, y0 + d + corr)
    p2, dev2, r2 = _strip((x0, y0, x1, y0 + d), gb, "x")
    placed.update(p2)
    by_key.update({s.key: s for s in gb})
    res.extend(dev2.values())
    if r2 > 0:
        _pad((x0, y0, x1, y0 + d), gb, placed, by_key, res, "客房带")
    return placed, by_key


def _public_core(gen: PlanGenerator, opts: SchemeOptions,
                 res: List[str]) -> Tuple[Dict[str, Rect], Dict[str, RoomSpec]]:
    """竖向核居中 + 客房分布两侧 + 后场在楼层一端的独立块。

    与"客房翼"的差别是组织逻辑：这里的电梯厅插在客房带中间（住客到两端房间
    的步行距离接近），后场收成端部一块、由后勤门与客房走廊隔开；
    客房翼则把电梯厅与后场都放在走廊两端。
    """
    _env, core = gen.shell(opts)
    x0, y0, x1, y1 = core
    H = y1 - y0
    specs = _specs(gen)
    g = _by_zone(specs)
    guest = sorted(g.get("guest", []), key=lambda s: s.priority)
    lift = sorted(g.get("public", []), key=lambda s: s.priority)
    boh = sorted(g.get("boh", []) + g.get("service", []) + g.get("storage", []),
                 key=lambda s: s.priority)
    corr = 1800.0
    d = (H - corr) / 2.0
    boh_area = sum(s.target_area_m2 for s in boh) * 1e6
    boh_w = _clamp(boh_area / max(d, 1.0) + 1500.0, 3600.0, 12000.0) if boh else 0.0
    gx1 = x1 - boh_w if boh else x1
    fixed = sum(s.target_area_m2 for s in lift) * 1e6 / max(d, 1.0)
    ga, gb = _split_by_frontage(guest, max(0.0, gx1 - x0 - fixed), x1 - x0)
    placed: Dict[str, Rect] = {}
    by_key: Dict[str, RoomSpec] = {}
    # 北带：客房 — 竖向核（居中）— 客房
    left, right = _half(ga)
    row_a = left + lift + right
    p, dev, r = _strip((x0, y0 + d + corr, gx1, y1), row_a, "x")
    placed.update(p)
    by_key.update({s.key: s for s in row_a})
    res.extend(dev.values())
    if r > 0:
        _pad((x0, y0 + d + corr, gx1, y1), row_a, placed, by_key, res, "客房带")
    _synth(by_key, "corridor", "客房走廊", "corridor", corr * (x1 - x0) / 1e6)
    placed["corridor"] = (x0, y0 + d, x1, y0 + d + corr)
    # 南带：客房（整幅，客人一侧不受后场影响）
    p2, dev2, r2 = _strip((x0, y0, x1, y0 + d), gb, "x")
    placed.update(p2)
    by_key.update({s.key: s for s in gb})
    res.extend(dev2.values())
    if r2 > 0:
        _pad((x0, y0, x1, y0 + d), gb, placed, by_key, res, "客房带")
    # 后场核：北带东端一块，西侧一条 1.2 m 后勤通道把它与客房隔开
    if boh:
        _synth(by_key, "corridor2", "后勤通道（不与客人混用）", "corridor",
               1200.0 * d / 1e6)
        placed["corridor2"] = (gx1, y0 + d + corr, gx1 + 1200.0, y1)
        bx0 = gx1 + 1200.0
        p3, dev3, r3 = _strip((bx0, y0 + d + corr, x1, y1), boh, "y")
        placed.update(p3)
        by_key.update({s.key: s for s in boh})
        res.extend(dev3.values())
        if r3 > 0:
            _pad((bx0, y0 + d + corr, x1, y1), boh, placed, by_key, res, "后场核")
    return placed, by_key


BUILDERS = {
    "cluster_atrium": _cluster_atrium,
    "linear_corridor": _linear_corridor,
    "public_front": _public_front,
    "tech_core": _tech_core,
    "medical_street": _medical_street,
    "dual_corridor": _dual_corridor,
    "process_line": _process_line,
    "stacked_module": _stacked_module,
    "front_yard": _front_yard,
    "guest_wing": _guest_wing,
    "public_core": _public_core,
}


def _patch_metrics(res: SchemeResult) -> None:
    """走廊指标只看走廊；中庭/诊疗街单列，不能把中庭算成走廊。"""
    rooms = [s for s in res.spaces if s.use not in ("envelope", "outdoor")]
    total = sum(s.area_m2 for s in rooms) or 1e-9
    circ = [s for s in rooms if s.use == "circulation"]
    corr = [s for s in circ if any(w in s.name for w in ("走廊", "连廊"))]
    spine = [s for s in circ if s not in corr]
    res.metrics["circulation_area_m2"] = round(sum(s.area_m2 for s in circ), 2)
    res.metrics["corridor_area_m2"] = round(sum(s.area_m2 for s in corr), 2)
    res.metrics["corridor_ratio"] = round(sum(s.area_m2 for s in corr) / total, 3)
    res.metrics["spine_area_m2"] = round(sum(s.area_m2 for s in spine), 2)
    res.metrics["spine_ratio"] = round(sum(s.area_m2 for s in spine) / total, 3)
    res.metrics["spine_names"] = [s.name for s in spine]


def build(kind: str, gen: PlanGenerator, opts: SchemeOptions,
          warnings: Optional[List[str]] = None) -> SchemeResult:
    """按一种 parti 出一套方案。kind 为空时返回 None 由调用方回落。"""
    fn = BUILDERS.get(kind)
    if fn is None:
        return None                                   # type: ignore[return-value]
    res_warn: List[str] = list(warnings or [])
    placed, by_key = fn(gen, opts, res_warn)
    env, _core = gen.shell(opts)
    res = SchemeResult(variant=opts.variant, title=opts.title,
                       strategy=f"concept_{kind}")
    res.spaces = gen._make_spaces(placed, by_key, opts, env, res)
    res.elements = gen._make_elements(placed, by_key, opts, res, env, res.spaces)
    res.metrics = gen._metrics(res, by_key, opts, placed)
    _patch_metrics(res)
    res.metrics["parti"] = kind
    # 指标里也写真实策略：沿用 opts 的默认值会让报告说成 band_day_night
    res.metrics["strategy"] = res.strategy
    res.metrics["parti_label"] = parti_mod.KIND_LABEL.get(kind, kind)
    res.warnings = res_warn + list(res.warnings)
    res.warnings = list(dict.fromkeys(res.warnings))
    return res


__all__ = ["BUILDERS", "Slot", "assign", "build", "profile_size"]
