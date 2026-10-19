"""从参考文件里提取可执行的视觉规则 —— 只提取能被指认的东西。

「高级」「极简」「有质感」不是规则。规则是：

- 纸色 `#F6F3EA`、墨色 `#22261F`、点缀色占比不超过 8%（从图像主色算出来的）；
- 留白占版面 46%（落在纸色亮度带内的像素占比）；
- 标题衬线、正文无衬线；图注编号 `FIG.01`；
- 禁止项：不要彩色渐变、不要投影卡片、不要高饱和大色块（客户原话）。

每条规则都带 `source`：

| source | 含义 | 举例 |
|---|---|---|
| `client` | 客户明确说的 | "排版要像竞赛展板，字少图大" |
| `reference` | 从参考文件算出来或读出来的 | 图像主色、文本里写明的三栏 |
| `pro` | 总设计师补的（客户没说、参考也没给） | 图注必须带归属 |

`pro` 不是"我猜你喜欢"，是"这一项没人定，按专业惯例先定，客户可以推翻"。
生成 `视觉.md` 时这三类分开标注，不把专业建议伪装成客户要求。

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

#: 中文颜色词 → 色值。只收设计语境里真正常用的，不做色卡全集。
COLOR_WORDS: Dict[str, str] = {
    "暖白": "#F7F4EC", "米白": "#F3EFE3", "象牙": "#F6F1E3", "纸白": "#FAF8F2",
    "奶白": "#F5F1E6", "米色": "#E8E2D2", "浅米": "#EFEADC",
    "石墨": "#2A2D2A", "炭黑": "#1B1E1B", "墨黑": "#141714", "纯黑": "#0E100E",
    "深灰": "#3C403C", "中灰": "#8A8F88", "浅灰": "#E3E0D6",
    "墨绿": "#2F5D45", "深绿": "#24402F", "橄榄绿": "#6B7350", "苔绿": "#54634A",
    "陶土": "#A9703F", "赭石": "#8C5A34", "木色": "#B08A57", "胡桃": "#6B4A32",
    "黄铜": "#A98A4B", "古铜": "#8A6A3A",
    "蓝灰": "#6B7C86", "雾蓝": "#93A7B0", "灰蓝": "#7E909A",
    "赤陶": "#B4664A", "砖红": "#9A4B38",
}

#: 版式语义 → 规则改动。命中即写一条，`evidence` 保留原句。
LAYOUT_CUES: Tuple[Tuple[Tuple[str, ...], str, Any], ...] = (
    (("大留白", "留白多", "留白大", "空一点", "空一些", "呼吸感", "别填满", "不要填满"),
     "whitespace", 0.50),
    (("紧凑", "信息密", "密一点", "多放内容"), "whitespace", 0.30),
    (("图大", "图为主", "以图为主", "字少", "少字", "大字", "图片主导"),
     "image_dominant", True),
    (("三栏", "三列"), "columns", 3),
    (("两栏", "双栏", "二栏"), "columns", 2),
    (("单栏", "一栏"), "columns", 1),
    (("宋体", "衬线", "明朝", "serif"), "serif_titles", True),
    (("黑体", "无衬线", "sans", "Helvetica", "思源黑"), "serif_titles", False),
    (("细线", "线条细", "线细", "发丝线"), "line_weight", 0.9),
    (("粗线", "线条粗", "线框重"), "line_weight", 1.5),
    (("高对比", "黑白分明", "对比强"), "contrast", 0.68),
    (("低对比", "柔和", "灰调", "莫兰迪"), "contrast", 0.38),
    (("不要卡片", "别用卡片", "去掉卡片", "非卡片"), "no_cards", True),
    (("满幅", "通栏", "出血", "全幅"), "full_bleed", True),
    (("编号", "图注", "图号", "编号系统"), "numbered_captions", True),
    (("网格", "栅格"), "grid", True),
)

#: 程度式说法：中文里"留白再多一些""线再细一点"不会写成"大留白""细线"。
#: 用正则跳过中间的语气词，否则客户改了三遍，规范一条都没动。
REGEX_CUES: Tuple[Tuple[str, str, Any], ...] = (
    (r"留白[^，。；,;]{0,8}(多|大|够|足)", "whitespace", 0.52),
    (r"(紧凑|密)[^，。；,;]{0,6}(一点|一些|点)", "whitespace", 0.30),
    (r"图[^，。；,;]{0,8}(更?大|放大|再大|更大|满幅|通栏)", "image_dominant", True),
    (r"图[^，。；,;]{0,8}(小|缩)", "image_dominant", False),
    (r"线[^，。；,;]{0,8}(细|轻|淡|收)", "line_weight", 0.85),
    (r"线[^，。；,;]{0,8}(粗|重|框)", "line_weight", 1.4),
    (r"(颜色|配色)[^，。；,;]{0,8}(克制|素|少|淡)", "contrast", 0.38),
    (r"(对比|黑白)[^，。；,;]{0,8}(强|硬|分明)", "contrast", 0.68),
    (r"(三|两|二|单)[^，。；,;]{0,4}(栏|列)", "columns", 3),
)

#: 禁止语义
BAN_CUES = ("不要", "别用", "避免", "禁止", "不喜欢", "受不了", "太俗", "厌恶",
            "不想要", "千万别", "拒绝")

#: 判断这条参考"测重什么"
DISCIPLINE_CUES = {
    "architecture": ("建筑", "体量", "立面", "剖面", "轴测", "结构", "别墅", "住宅"),
    "interior": ("室内", "软装", "家具", "材质", "灯光", "厅", "卧", "厨", "卫"),
    "landscape": ("景观", "庭院", "植物", "水景", "园路", "种植", "铺装", "花园"),
}

#: 无参考时的专业默认值。必须与当前实现一致——加这套能力不能让原有版面变差。
DEFAULTS: Dict[str, Any] = {
    "paper": "#FAF8F3",
    "ink": "#1A1D1A",
    "muted": "#6E736A",
    "line": "#DED9CB",
    "accent": "#2F5D45",
    "whitespace": 0.40,
    "contrast": 0.55,
    "serif_titles": True,
    "columns": 12,
    "image_ratio": "16:9",
    "line_weight": 1.0,
    "numbered_captions": True,
    "image_dominant": True,
    "full_bleed": True,
    "no_cards": True,
}


def _clauses(text: str) -> List[str]:
    return [c.strip() for c in re.split(r"[。；;\n]+", str(text or "")) if c.strip()]


def _first_hit(clause: str, words: Iterable[str]) -> Optional[str]:
    for w in words:
        if w and w in clause:
            return w
    return None


# --------------------------------------------------------------------------
# 文本
# --------------------------------------------------------------------------
def from_text(text: str, *, origin: str = "client") -> Dict[str, Any]:
    """从参考文字里读规则。只认写明的，不补全。"""
    out: Dict[str, Any] = {"tokens": {}, "layout": {}, "banned": [],
                           "colours": {}, "notes": [], "keywords": []}
    body = str(text or "")
    if not body.strip():
        return out

    for colour_word, hexv in COLOR_WORDS.items():
        if colour_word in body:
            out["colours"][colour_word] = hexv
            out["keywords"].append(colour_word)

    # 字族：先看"标题"那一句。A 类作品集常写"标题宋体、正文无衬线"，
    # 只按出现顺序取会把标题规则错判成正文规则。
    m = re.search(r"(标题|主标题|题目)[^。；\n]{0,20}?(宋体|衬线|黑体|无衬线|sans|serif)",
                  body, re.IGNORECASE)
    if m:
        out["layout"]["serif_titles"] = {
            "value": not any(w in m.group(2).lower() for w in ("黑体", "无衬线", "sans")),
            "evidence": m.group(0)[:70], "matched": m.group(2), "source": origin}

    for pattern, key, value in REGEX_CUES:
        m2 = re.search(pattern, body)
        if not m2:
            continue
        # 栏数单独处理：'两栏' 不该写成 3
        if key == "columns":
            word = m2.group(0)
            value = 1 if word.startswith("单") else 2 if word.startswith(("两", "二")) else 3
        out["layout"].setdefault(key, {
            "value": value, "evidence": m2.group(0)[:70],
            "matched": m2.group(0), "source": origin})

    for cues, key, value in LAYOUT_CUES:
        if key in out["layout"]:
            continue
        for clause in _clauses(body):
            hit = _first_hit(clause, cues)
            if not hit:
                continue
            out["layout"][key] = {"value": value, "evidence": clause[:70],
                                  "matched": hit, "source": origin}
            break

    for clause in _clauses(body):
        raw = clause.strip()
        # 去掉 markdown 标记：`## 不要` 是标题，不是一条禁止项
        item = re.sub(r"^[#>*\-\s]+", "", raw).strip()
        if len(item) < 4 or len(item) > 80:
            continue
        if not any(c in item for c in BAN_CUES):
            continue
        # "不要"后面必须有具体对象，否则是空话
        tail = item[min(item.find(c) + len(c) for c in BAN_CUES if c in item):].strip(" ：:，,")
        if len(tail) < 2:
            continue
        if item not in [b["text"] for b in out["banned"]]:
            out["banned"].append({"text": item, "source": origin})

    # 页面/文档形态的描述（画幅、页数、比例）
    for m in re.finditer(r"(\d{1,2})\s*[:：]\s*(\d{1,2})", body):
        a, b = int(m.group(1)), int(m.group(2))
        if 1 <= a <= 40 and 1 <= b <= 40 and a != b:
            out["layout"].setdefault("image_ratio",
                                     {"value": f"{a}:{b}", "evidence": m.group(0),
                                      "matched": m.group(0), "source": origin})
            break
    for m in re.finditer(r"(横版|竖版|A3|A4|16\s*比\s*9|4\s*比\s*3)", body):
        out["notes"].append({"text": f"提到版式形态：{m.group(0)}", "source": origin})
        break

    # 专业倾向
    for disc, words in DISCIPLINE_CUES.items():
        if sum(1 for w in words if w in body) >= 2:
            out["keywords"].append(disc)
    return out


# --------------------------------------------------------------------------
# 图像
# --------------------------------------------------------------------------
def _median(values: Sequence[float]) -> float:
    s = sorted(values)
    if not s:
        return 0.0
    mid = len(s) // 2
    return s[mid] if len(s) % 2 else (s[mid - 1] + s[mid]) / 2


def from_images(metrics: Sequence[Dict[str, Any]], *,
                origin: str = "reference") -> Dict[str, Any]:
    """从若干张参考图算规则：取中位数，避免一张偏色的图带跑整套配色。"""
    ok = [m for m in metrics if m.get("ok")]
    out: Dict[str, Any] = {"tokens": {}, "layout": {}, "banned": [],
                           "colours": {}, "notes": [], "keywords": []}
    if not ok:
        return out

    inks = [m["ink"] for m in ok if m.get("ink")]
    accents = [m["accent"] for m in ok if m.get("accent")]
    whites = [float(m.get("whitespace") or 0) for m in ok]
    contrast = [float(m.get("contrast") or 0) for m in ok]
    ratios = [float(m.get("ratio") or 0) for m in ok]

    # 照片不是版面。一张风景照的"最亮色"是天空，拿它当页面底色会把整份提案
    # 染成灰蓝。所以纸色不直接取图，只按参考图的**冷暖**做极小幅度微调；
    # 真正的纸色由文本规则（客户说"暖白"）或专业默认值决定。
    rgbs = []
    for m in ok:
        pl = m.get("palette") or []
        if not pl:
            continue
        best = max(pl, key=lambda p: p.get("share") or 0)
        h = str(best.get("hex") or "").lstrip("#")
        if len(h) == 6:
            rgbs.append((int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)))
    if rgbs:
        mr = sum(c[0] for c in rgbs) / len(rgbs)
        mb = sum(c[2] for c in rgbs) / len(rgbs)
        base = DEFAULTS["paper"].lstrip("#")
        br, bg, bb = int(base[0:2], 16), int(base[2:4], 16), int(base[4:6], 16)
        shift = max(-5, min(5, int((mb - mr) * 0.2)))   # 冷则加蓝，暖则加红
        tinted = "#{:02X}{:02X}{:02X}".format(
            max(0, min(255, br - max(0, shift))),
            max(0, min(255, bg)),
            max(0, min(255, bb + max(0, shift))))
        out["tokens"]["paper"] = {
            "value": tinted, "source": origin,
            "evidence": ("由参考图冷暖微调（非直接取色）：参考图偏"
                         + ("冷" if mb > mr else "暖"))}
    if inks:
        out["tokens"]["ink"] = {"value": inks[0], "source": origin,
                                "evidence": f"{len(ok)} 张参考图的墨色"}
    if accents:
        out["tokens"]["accent"] = {"value": accents[0], "source": origin,
                                   "evidence": "参考图里占比 2%–30% 的高饱和色"}
    # 留白同理：只有"像版面"的参考图（有底色也有内容）才采信，
    # 一张天空占一半的建筑照不等于"版面留白 50%"。
    wm = round(_median(whites), 2) if whites else 0.0
    if whites and 0.26 <= wm <= 0.74 and len(ok) >= 1:
        out["layout"]["whitespace"] = {
            "value": wm, "source": origin,
            "evidence": f"参考图底色占比中位数 {wm}（按版面留白采样）",
            "matched": "whitespace"}
    elif whites:
        out["notes"].append({
            "text": f"参考图底色占比 {wm}，超出常见版面区间，未按留白采信",
            "source": origin})
    if contrast:
        out["layout"]["contrast"] = {
            "value": round(_median(contrast), 2), "source": origin,
            "evidence": f"亮度标准差中位数 {round(_median(contrast), 2)}",
            "matched": "contrast"}
    if ratios:
        r = _median(ratios)
        near = min(((16 / 9, "16:9"), (4 / 3, "4:3"), (3 / 2, "3:2"),
                    (1.0, "1:1"), (4 / 5, "4:5"), (210 / 297, "A4 竖")),
                   key=lambda kv: abs(kv[0] - r))
        out["layout"]["image_ratio"] = {
            "value": near[1], "source": origin,
            "evidence": f"参考图长宽比中位数 {r:.2f}", "matched": "ratio"}

    darkness = sum(1 for m in ok if m.get("mood") == "dark")
    if darkness > len(ok) / 2:
        out["notes"].append({"text": "参考图整体偏暗调，深色底为主", "source": origin})
    elif all(m.get("mood") == "light" for m in ok):
        out["notes"].append({"text": "参考图整体为浅底，深色只用于文字与小面积", "source": origin})
    return out


# --------------------------------------------------------------------------
# 合并
# --------------------------------------------------------------------------
def merge(layers: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """按顺序合并，**后者不覆盖前者的显式值**。

    优先级：客户明确说的 > 参考文件算出来的 > 专业默认。
    调用方按这个顺序传 `layers`，这里只做"先到先得 + 记录来源"。
    """
    tokens: Dict[str, Any] = {}
    layout: Dict[str, Any] = {}
    banned: List[Dict[str, Any]] = []
    notes: List[Dict[str, Any]] = []
    colours: Dict[str, str] = {}

    for layer in layers:
        for k, v in (layer.get("tokens") or {}).items():
            tokens.setdefault(k, v)
        for k, v in (layer.get("layout") or {}).items():
            layout.setdefault(k, v)
        for b in layer.get("banned") or []:
            if b["text"] not in [x["text"] for x in banned]:
                banned.append(b)
        for n in layer.get("notes") or []:
            notes.append(n)
        colours.update(layer.get("colours") or {})

    resolved: Dict[str, Any] = dict(DEFAULTS)
    unresolved: Dict[str, Any] = {}
    for k, v in tokens.items():
        resolved[k] = v["value"]
        unresolved[k] = v["source"]
    for k, v in layout.items():
        if k in ("whitespace", "contrast", "columns", "line_weight"):
            resolved[k] = v["value"]
        elif k == "image_ratio":
            resolved[k] = v["value"]
        else:
            resolved[k] = v["value"]
        unresolved[k] = v["source"]

    # 由对比度推导 muted / line，避免参考图只给了两个颜色就断链
    ink, paper = str(resolved["ink"]), str(resolved["paper"])
    resolved.setdefault("muted", _mix(ink, paper, 0.45))
    resolved.setdefault("line", _mix(ink, paper, 0.86))
    if unresolved.get("muted") is None:
        unresolved["muted"] = "pro"
    if unresolved.get("line") is None:
        unresolved["line"] = "pro"

    return {
        "tokens": resolved,
        "provenance": unresolved,
        "banned": banned,
        "notes": notes,
        "colours": colours,
    }


def _hex_rgb(h: str) -> Tuple[int, int, int]:
    h = h.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    try:
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    except ValueError:
        return 128, 128, 128


def _mix(a: str, b: str, t: float) -> str:
    ar, ag, ab = _hex_rgb(a)
    br, bg, bb = _hex_rgb(b)
    t = max(0.0, min(1.0, t))
    return "#{:02X}{:02X}{:02X}".format(
        int(round(ar + (br - ar) * t)),
        int(round(ag + (bg - ag) * t)),
        int(round(ab + (bb - ab) * t)))


__all__ = ["COLOR_WORDS", "LAYOUT_CUES", "REGEX_CUES", "BAN_CUES", "DEFAULTS",
           "from_text", "from_images", "merge"]
