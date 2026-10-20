"""素材库取图：从自有素材库拿真实图片，按专业与风格匹配，裁成版面需要的比例。

为什么要这一层
--------------
概念阶段的"图"有两种，混在一起就会出事：

| | 分析图（`concept/diagrams.py`） | 意象图（本模块） |
|---|---|---|
| 回答什么 | 谁挨着谁、怎么走、光从哪来 | 这套方向看起来是什么气质 |
| 依据 | 任务书与推演，可被指认 | 素材库里的视觉资产 |
| 能不能量尺寸 | 不能（标了非比例） | 更不能 |
| 谁画 | 本系统确定性绘制 | **不画**——取真实图片 |

上一版把所有位置都留给确定性 SVG，于是提案里全是线框：客户看不出石材的
质感、看不出光落在墙上的样子。而另一条错路是让图像模型现编一张——在没有
平台授权时那只能是伪造。所以第三条路：**用自有素材库里真实存在的图片**。

纪律（绕不过去）
----------------
1. **只用目录里登记过的条目。** `knowledge/library/catalog.json` 是抓取时页面
   上真实存在的卡片（标题、标签、原图地址），不在目录里的不许出现。
2. **图片本体不入库。** 目录是文本，运行时下载到 `out/` 下的缓存，随交付目录走。
   仓库里因此没有一张二进制图（`scripts/check_assets.py` 守着）。
3. **每张图带出处。** 交付物里印「素材库 · 标题」，附录写来源页。没有出处的图
   不进版面。
4. **取不到就说取不到。** 网络失败、文件过小、格式不对，一律返回空——不拿
   一张替代图顶上。

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import hashlib
import json
import os
import urllib.request
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

ROOT = Path(__file__).resolve().parents[2]
CATALOG = ROOT / "knowledge" / "library" / "catalog.json"

#: 抓取来源：地址的唯一来源是 `paths.REFERENCE_LIBRARY_URL`，这里不抄第二遍。
from ..paths import REFERENCE_LIBRARY_URL as SOURCE_URL  # noqa: E402

SOURCE_LABEL = "Luxora AI 素材库"

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36")

#: 专业信号：命中即说明这张图"是这个专业的东西"
DISCIPLINE_TAGS: Dict[str, Tuple[str, ...]] = {
    "architecture": ("建筑", "建筑设计", "现代建筑", "极简主义建筑", "别墅", "公寓楼",
                     "建筑学", "楼梯", "公共空间", "城市环境", "现代结构", "钢板",
                     "混凝土墙", "玻璃窗", "木梁", "户外游泳池", "屋顶"),
    "interior": ("室内", "室内设计", "现代室内设计", "客厅", "卧室装饰", "餐厅设计",
                 "酒店设计", "酒吧", "水疗用品", "办公空间", "现代办公室", "大堂吧",
                 "家具", "厨房", "浴室装饰", "玄关"),
    "landscape": ("景观", "花园", "户外花园", "景观草坪", "喷泉景观", "庭院", "树木",
                  "户外环境", "绿植", "郁郁葱葱的绿植", "室内植物", "自然景观"),
}

#: 只有氛围、没有空间设计的图：可以做"气质参考"，不能当"这套方案长这样"
ATMOSPHERE_ONLY = ("自然景观", "自然", "日落", "蓝天", "云海", "山脉", "森林",
                   "海浪", "沙漠", "野花", "罂粟花")

#: 明显不是空间设计的图。命中且没有专业信号的一律排除。
NOT_SPACE = ("插画", "油画", "水彩画", "装饰画", "角色设计", "人物肖像", "运动",
             "冲浪", "骑自行车", "美食", "冰淇淋", "甜筒", "护肤", "美容",
             "手袋", "手表", "指环", "时尚", "珠宝", "纸面具", "冰淇淋",
             "玩具", "手工纸", "工艺", "甜点", "静物", "饮料")

#: 版面比例：hero 用宽幅，卡片用 4:3，竖图用 4:5
RATIOS: Dict[str, Tuple[int, int]] = {
    "hero": (16, 9),
    "wide": (3, 2),
    "card": (4, 3),
    "tall": (4, 5),
    "square": (1, 1),
}


# --------------------------------------------------------------------------
# 目录
# --------------------------------------------------------------------------
def load_catalog() -> List[Dict[str, Any]]:
    if not CATALOG.exists():
        return []
    try:
        data = json.loads(CATALOG.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    items = data.get("items") if isinstance(data, dict) else data
    return [i for i in (items or []) if isinstance(i, dict) and i.get("url")]


def _tags(entry: Dict[str, Any]) -> str:
    return " ".join(str(t) for t in (entry.get("tags") or []))


def classify(entry: Dict[str, Any]) -> str:
    """`space` / `material` / `atmosphere` / `other`。

    这三类的用法完全不同：`space` 可以当"这套方向的空间意象"，`material`
    只能当材质参考，`atmosphere` 只能当气质参考。混用会让客户以为某张风景照
    是他家院子的效果。
    """
    tags = _tags(entry) + " " + str(entry.get("title") or "")
    has_space = any(k in tags for k in
                    ("室内设计", "现代室内设计", "建筑设计", "现代建筑", "建筑",
                     "别墅", "公寓", "花园", "景观草坪", "喷泉景观", "公共空间"))
    if "材料特写" in tags or "纹理" in tags and not has_space:
        return "material"
    if has_space:
        return "space"
    if any(k in tags for k in ATMOSPHERE_ONLY):
        return "atmosphere"
    return "other"


def score(entry: Dict[str, Any], *, lead: str = "", style_tags: Sequence[str] = (),
          keywords: Sequence[str] = ()) -> float:
    """Match one library item against this scheme's discipline and style."""
    tags = _tags(entry)
    title = str(entry.get("title") or "")
    hay = tags + " " + title
    kind = classify(entry)
    if kind in ("other",):
        return 0.0
    if any(k in hay for k in NOT_SPACE):
        # 油画、插画、装饰画里也会写"花园""树木"。它们不是空间照片，
        # 除非同时有明确的空间设计标签，否则一律不用。
        if not any(k in tags for k in ("室内设计", "建筑设计", "现代室内设计",
                                       "现代建筑", "公共空间")):
            return 0.0

    s = 0.0
    for disc, keys in DISCIPLINE_TAGS.items():
        hits = sum(1 for k in keys if k in tags)
        if not hits:
            continue
        if disc == lead:
            s += hits * 3.0
        elif lead == "landscape" and disc == "architecture":
            # 庭院方案里，建筑只是背景。给它低权重，否则"别墅外观"永远排第一。
            s += hits * 0.35
        else:
            s += hits * 1.1

    # 景观最容易串味：素材库里带"室内植物"的室内图会靠"植物"命中景观。
    # 场地设计要的是户外——没有户外词的一律重罚，不让咖啡馆冒充庭院。
    if lead == "landscape" and "室内" in tags:
        outdoor = any(k in tags for k in
                      ("户外花园", "景观草坪", "花园", "景观", "树木", "户外环境",
                       "喷泉景观", "庭院"))
        if not outdoor:
            s -= 7.0
    # 景观的封面要"地"而不是"房"：别墅/公寓标签命中就压下去，
    # 否则一张漂亮的外立面照片会占掉本该属于花园的位置。
    if lead == "landscape":
        if any(k in tags for k in ("别墅", "公寓", "公寓楼", "现代建筑", "建筑设计")):
            s -= 4.6
        if "别墅" in tags and not any(k in tags for k in ("花园", "庭院", "户外花园")):
            s -= 1.6
        if any(k in tags for k in ("花园", "庭院", "户外花园", "景观草坪", "喷泉景观")):
            s += 2.6
    for t in style_tags:
        t = str(t).strip()
        if t and t in hay:
            s += 1.4
    for k in keywords:
        k = str(k).strip()
        if len(k) >= 2 and k in hay:
            s += 0.9

    # 画幅：宽图更适合当 hero；极窄或极小的图即使匹配也读不出东西
    w, h = int(entry.get("w") or 0), int(entry.get("h") or 0)
    if w < 700 or h < 380:
        s -= 2.0
    if kind == "space":
        s += 0.8          # 空间图优先于纯氛围
    if kind == "atmosphere":
        s -= 0.4
    if h > w * 1.6:
        s -= 0.8          # 过窄的竖图在提案里放不大
    return s


def pick(*, lead: str = "", style_tags: Sequence[str] = (),
         keywords: Sequence[str] = (), limit: int = 8,
         exclude: Iterable[str] = (), kinds: Sequence[str] = ("space",),
         catalog: Optional[Sequence[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
    """Top-N library items for one scheme. Empty list is a valid answer."""
    items = list(catalog if catalog is not None else load_catalog())
    taken = {str(x) for x in exclude}
    scored: List[Tuple[float, Dict[str, Any]]] = []
    for e in items:
        if str(e.get("url")) in taken or str(e.get("title")) in taken:
            continue
        k = classify(e)
        if kinds and k not in kinds:
            continue
        sc = score(e, lead=lead, style_tags=style_tags, keywords=keywords)
        if sc <= 0:
            continue
        scored.append((sc, e))
    scored.sort(key=lambda kv: -kv[0])
    out: List[Dict[str, Any]] = []
    for sc, e in scored[:limit]:
        out.append({**e, "kind": classify(e), "score": round(sc, 2)})
    return out


# --------------------------------------------------------------------------
# 下载与裁剪
# --------------------------------------------------------------------------
def _cache_name(entry: Dict[str, Any], ratio: str) -> str:
    key = hashlib.sha1(f"{entry.get('url')}|{ratio}".encode("utf-8")).hexdigest()[:16]
    return f"{key}.jpg"


def _download(url: str, dest: Path) -> Optional[Path]:
    # 离线校验模式（测试、无网机器）：不发起请求。
    # 原来这里会等满 45 s 超时，一次取 5 张图就是近 4 分钟——
    # 测试超时的真凶就在这。
    if os.environ.get("OMNIAILAB_NO_NETWORK"):
        return None
    if dest.exists() and dest.stat().st_size > 4096:
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={
        "User-Agent": UA, "Referer": SOURCE_URL, "Accept": "image/*,*/*;q=0.8"})
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            data = r.read()
        if len(data) < 4096:
            return None
        dest.write_bytes(data)
        return dest
    except Exception:
        return None


def crop_to(src: Path, dest: Path, ratio: str = "hero", *, focus: str = "centre") -> Optional[Path]:
    """Crop to the layout ratio. Falls back to a byte copy without Pillow."""
    tw, th = RATIOS.get(ratio, RATIOS["hero"])
    target_ar = tw / th
    try:
        from PIL import Image
    except ImportError:
        if src != dest:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(src.read_bytes())
        return dest if dest.exists() else None
    try:
        im = Image.open(src).convert("RGB")
    except Exception:
        return None
    w, h = im.size
    if w <= 0 or h <= 0:
        return None
    cur = w / h
    if cur > target_ar:                      # too wide → trim sides
        nw = int(round(h * target_ar))
        x0 = (w - nw) // 2
        box = (x0, 0, x0 + nw, h)
    else:                                    # too tall → trim top/bottom
        nh = int(round(w / target_ar))
        if focus == "top":
            y0 = 0
        elif focus == "bottom":
            y0 = h - nh
        else:
            y0 = int((h - nh) * 0.42)        # 略微偏上：建筑主体通常在上半
        box = (0, max(0, y0), w, min(h, max(0, y0) + nh))
    im = im.crop(box)
    if im.width > 1800:
        im = im.resize((1800, int(round(1800 * im.height / im.width))),
                       Image.LANCZOS)
    dest.parent.mkdir(parents=True, exist_ok=True)
    im.save(dest, "JPEG", quality=88, optimize=True, progressive=True)
    return dest if dest.exists() else None


def fetch(entry: Dict[str, Any], out_dir: str | Path, *, ratio: str = "hero",
          focus: str = "centre") -> Optional[Dict[str, Any]]:
    """Download + crop one item into the delivery folder.

    Returns the local record, or ``None`` when the file could not be obtained.
    ``None`` is a result, not an error: the caller must show the slot as
    unavailable rather than substitute another picture.
    """
    out = Path(out_dir)
    assets = out / "assets"
    name = _cache_name(entry, ratio)
    raw = assets / "_raw" / name
    if _download(str(entry.get("url")), raw) is None:
        return None
    dest = assets / name
    got = crop_to(raw, dest, ratio, focus=focus)
    if got is None:
        return None
    return {
        "file": f"assets/{dest.name}",
        "path": str(dest),
        "title": str(entry.get("title") or ""),
        "tags": list(entry.get("tags") or []),
        "kind": str(entry.get("kind") or classify(entry)),
        "ratio": ratio,
        "source": SOURCE_LABEL,
        "source_url": SOURCE_URL,
        "credit": f"{SOURCE_LABEL} · {entry.get('title')}",
    }


def gallery(out_dir: str | Path, *, lead: str = "", style_tags: Sequence[str] = (),
            keywords: Sequence[str] = (), want: Sequence[Tuple[str, str]] = (),
            exclude: Iterable[str] = (), avoid: Sequence[str] = (),
            require: Sequence[str] = (),
            catalog: Optional[Sequence[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
    """Pick and fetch a small set: ``(ratio, kind)`` pairs, in order.

    `want` 是"版面需要的槽位"，例如 ``[("hero", "space"), ("card", "space"),
    ("card", "material")]``。按槽位取图，才能保证 hero 有一张能撑住整幅的宽图，
    而不是三张竖图都被裁成一条。
    """
    items = list(catalog if catalog is not None else load_catalog())
    used: List[str] = list(exclude)
    out: List[Dict[str, Any]] = []
    for ratio, kind in want:
        kinds = (kind,) if kind else ("space",)
        pool = items
        if avoid:
            pool = [e for e in pool if not any(a in _tags(e) for a in avoid)]
        if require and kinds == ("space",):
            # 硬条件只约束"空间意象"：庭院方案的空间图必须是花园/庭院/树木，
            # 否则宁可不出图。材质图不适用这条——材质本来就不长花园的样子。
            pool = [e for e in pool if any(r in _tags(e) for r in require)]
        cands = pick(lead=lead, style_tags=style_tags, keywords=keywords,
                     limit=14, exclude=used, kinds=kinds, catalog=pool)
        if not cands and kind != "space":
            cands = pick(lead=lead, style_tags=style_tags, keywords=keywords,
                         limit=6, exclude=used, kinds=("space",),
                         catalog=pool)
        got = None
        for c in cands:
            rec = fetch(c, out_dir, ratio=ratio)
            if rec is None:
                used.append(str(c.get("url")))
                continue
            rec["score"] = c.get("score")
            got = rec
            used.append(str(c.get("url")))
            used.append(str(c.get("title")))
            break
        if got:
            out.append(got)
    return out


__all__ = ["CATALOG", "SOURCE_URL", "SOURCE_LABEL", "RATIOS", "load_catalog",
           "classify", "score", "pick", "fetch", "crop_to", "gallery"]
