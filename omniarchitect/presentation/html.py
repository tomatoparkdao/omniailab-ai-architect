"""客户可读的 HTML 提案：一页看完三套方案，案例带图、链接可点。

这个模块替换的是上一轮那个在脚本里拼字符串的单页阅读版。区别不在"更好看"，
而在三件事：

1. **案例不再是纯文本。** 每个案例一张图：有登记的授权照片就放照片并署名，
   没有就放本系统按案例文字画的手法示意图，旁边一个"查看原案例"按钮。客户
   既看得到东西，也不会误以为那张图是原项目照片。
2. **图有身份。** 真实案例、手法示意、原创意向、正式效果图四种东西在版面上
   用不同的标记区分，页首有图例。混着放最省事，也最容易在交付后说不清。
3. **方案按"设计怎么来的"排，不按字段排。** 机会 → 为什么这样组织 → 人会
   经历什么 → 光视比例材料怎么配合 → 三个专业怎么成整体 → 要谁配合 → 代价。

只读 S2 已经产出的 JSON，不重新计算设计结论；没有的东西不画。

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import html
import re
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from ..research import preview as pv

#: 空间家族的中文说法。原型与推敲策略共用这几个。
FAMILY_CN: Dict[str, str] = {
    "courtyard": "围合院落", "layered": "递进层次", "linear": "线性组织",
    "hall": "单一通厅", "cluster": "组团分散", "loop": "回游环线",
    "spine": "服务脊", "band": "带状分区",
}

#: 图种的中文名。
KIND_CN: Dict[str, str] = {
    "functional": "功能关系图", "zoning": "分区图", "circulation": "动线概念图",
    "daylight": "采光策略图", "sequence": "空间序列图", "massing": "体量概念图",
    "section": "剖面与楼层图", "landscape": "景观结构图",
    "moodboard": "材料与色彩板",
}

#: 每个主导专业先看哪几张图。图种顺序本身就是阅读顺序。
FIGURE_ORDER: Dict[str, Tuple[str, ...]] = {
    "architecture": ("massing", "section", "sequence", "daylight"),
    "interior": ("zoning", "circulation", "daylight", "sequence"),
    "landscape": ("landscape", "sequence", "zoning", "daylight"),
}

CSS = """
:root{
  --ink:#1A1F1C; --muted:#6B7280; --line:#E3E1D9; --paper:#F6F5F1;
  --card:#FFFFFF; --accent:#2F5D45; --accent-soft:#EDF2EC;
  --amber:#A9701F; --amber-soft:#FAF2E3; --dark:#121714; --dark-2:#1B231E;
  --radius:14px;
}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;background:var(--paper);color:var(--ink);
  font-family:'Noto Sans SC','PingFang SC','Microsoft YaHei',-apple-system,sans-serif;
  line-height:1.75;-webkit-font-smoothing:antialiased}
a{color:var(--accent);text-decoration:none}
a:hover{text-decoration:underline}
main{max-width:1180px;margin:0 auto;padding:0 24px 96px}
.serif{font-family:'Songti SC','Noto Serif SC',Georgia,serif}

/* ---------- 封面 ---------- */
.cover{background:var(--dark);color:#F2F4F1;padding:64px 0 52px;position:relative;
  overflow:hidden;margin:0 calc(50% - 50vw)}
.cover-in{max-width:1132px;margin:0 auto;padding:0 24px}
.cover:after{content:"";position:absolute;right:-120px;top:-120px;width:420px;height:420px;
  border:1px solid rgba(255,255,255,.10);border-radius:50%}
.cover-top{font-size:12px;letter-spacing:.22em;color:#8FA697;text-transform:uppercase}
.cover h1{font-size:44px;line-height:1.18;margin:18px 0 10px;font-weight:600}
.cover .lede{color:#BEC7C0;font-size:15px;margin:0 0 30px;max-width:760px}
.stats{display:flex;gap:44px;flex-wrap:wrap;border-top:1px solid rgba(255,255,255,.12);
  padding-top:22px}
.stats div{font-size:12px;color:#9DA9A1;letter-spacing:.06em}
.stats b{display:block;font-size:26px;color:#F2F4F1;font-weight:600;letter-spacing:0}

/* ---------- 图例 ---------- */
.legend{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:26px 0 0}
.legend div{background:var(--card);border:1px solid var(--line);border-radius:10px;
  padding:12px 14px;font-size:12px;color:var(--muted);line-height:1.6}
.legend b{display:block;color:var(--ink);font-size:13px;margin-bottom:2px}
.dot{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:6px;
  vertical-align:1px}
.dot.case{background:#9AA3AE}.dot.plate{background:var(--accent)}
.dot.own{background:var(--amber)}.dot.final{background:var(--dark)}

/* ---------- 总览 ---------- */
.sec-label{font-size:12px;letter-spacing:.2em;color:var(--accent);
  text-transform:uppercase;margin:60px 0 8px}
.sec-title{font-size:26px;margin:0 0 18px;font-weight:600}
.cards{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}
.jump{display:block;background:var(--card);border:1px solid var(--line);
  border-radius:var(--radius);padding:22px 22px 18px;transition:.18s;
  color:inherit}
.jump:hover{border-color:#B9C8BE;transform:translateY(-2px);text-decoration:none;
  box-shadow:0 10px 28px rgba(20,30,24,.07)}
.jump .no{font-size:11px;letter-spacing:.14em;color:var(--muted)}
.jump h3{font-size:20px;margin:8px 0 6px;font-weight:600}
.jump p{font-size:13px;color:var(--muted);margin:0 0 14px;line-height:1.7}
.jump .tags{display:flex;gap:6px;flex-wrap:wrap}
.tag{font-size:11px;padding:3px 9px;border-radius:999px;background:var(--accent-soft);
  color:var(--accent);border:1px solid #D7E2D8}

/* ---------- 方案 ---------- */
.concept{margin-top:64px;padding-top:34px;border-top:1px solid var(--line)}
.c-head{max-width:820px}
.c-eyebrow{font-size:12px;letter-spacing:.16em;color:var(--muted)}
.c-head h2{font-size:34px;margin:8px 0 12px;font-weight:600;letter-spacing:-.01em}
.statement{font-size:16.5px;line-height:1.9;color:#333A35;margin:0}
.c-grid{display:grid;grid-template-columns:minmax(0,1fr) 300px;gap:38px;margin-top:26px}
.side h4{font-size:11px;letter-spacing:.16em;color:var(--muted);margin:0 0 8px;
  text-transform:uppercase}
.panel{background:var(--card);border:1px solid var(--line);border-radius:12px;
  padding:16px 18px;margin-bottom:14px}
.panel p,.panel li{font-size:12.8px;line-height:1.75;color:#3C443E;margin:0}
.panel ul{margin:0;padding-left:16px}
.panel li+li{margin-top:5px}
.panel.warn{background:var(--amber-soft);border-color:#EBDCBE}
.panel.warn h4{color:var(--amber)}
.panel.dark{background:var(--dark-2);border-color:var(--dark-2);color:#DDE4DE}
.panel.dark p{color:#C6D0C8}
.panel.dark h4{color:#8FA697}

.callout{background:var(--accent-soft);border-left:3px solid var(--accent);
  border-radius:0 12px 12px 0;padding:18px 20px;margin:0 0 16px}
.callout h4{margin:0 0 6px;font-size:12px;letter-spacing:.14em;color:var(--accent)}
.callout p{margin:0;font-size:15px;line-height:1.85}
.why{margin:0 0 22px;font-size:14px;color:#414A43}
.why b{color:var(--ink)}
.block-h{font-size:13px;letter-spacing:.12em;color:var(--muted);margin:34px 0 12px;
  padding-bottom:6px;border-bottom:1px solid var(--line)}

/* ---------- 图 ---------- */
.figs{display:grid;grid-template-columns:1fr;gap:16px}
.figs.two{grid-template-columns:1fr 1fr}
.figs.two .fig:only-child{grid-column:span 1}
.fig{background:var(--card);border:1px solid var(--line);border-radius:12px;
  padding:10px 10px 6px;overflow:hidden}
.fig svg{display:block;width:100%;height:auto;border-radius:6px}
.cap{font-size:11.5px;color:var(--muted);padding:8px 4px 4px;letter-spacing:.02em}
.cap b{color:var(--ink);font-weight:600;margin-right:6px}

/* ---------- 序列 ---------- */
.seq{list-style:none;margin:0;padding:0;display:grid;
  grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px}
.seq li{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px 14px}
.seq .k{font-size:11px;letter-spacing:.1em;color:var(--accent)}
.seq .e{font-size:12.5px;color:#3C443E;line-height:1.65;margin-top:4px}

/* ---------- 四问 ---------- */
.quad{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.quad div{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 16px}
.quad h5{margin:0 0 6px;font-size:11px;letter-spacing:.12em;color:var(--muted)}
.quad p{margin:0;font-size:12.8px;line-height:1.7;color:#3C443E}

/* ---------- 材料 ---------- */
.mats{display:grid;grid-template-columns:1fr 1fr;gap:8px}
.mat{border:1px solid var(--line);border-radius:9px;padding:9px 10px;background:var(--card)}
.mat .n{font-size:12.5px;font-weight:600}
.mat .a{font-size:11px;color:var(--muted);line-height:1.5}
.sws{display:flex;gap:6px;flex-wrap:wrap;margin-top:4px}
.sw{width:30px;height:12px;border-radius:3px;border:1px solid rgba(0,0,0,.06)}

/* ---------- 案例卡 ---------- */
.cases{display:grid;grid-template-columns:1fr 1fr;gap:16px}
.case{background:var(--card);border:1px solid var(--line);border-radius:var(--radius);
  overflow:hidden;display:flex;flex-direction:column}
.thumb{position:relative;background:#F1F2EE;border-bottom:1px solid var(--line)}
.thumb svg{display:block;width:100%;height:auto}
.thumb img{display:block;width:100%;height:auto}
.thumb .badge{position:absolute;left:10px;top:10px;font-size:10.5px;padding:3px 8px;
  border-radius:999px;background:rgba(255,255,255,.92);color:var(--ink);
  border:1px solid var(--line);letter-spacing:.04em}
.case-body{padding:14px 16px 16px;display:flex;flex-direction:column;gap:6px;flex:1}
.case-kicker{font-size:10.5px;letter-spacing:.12em;color:var(--muted)}
.case h4{margin:0;font-size:15.5px;line-height:1.45;font-weight:600}
.case h4 a{color:var(--ink)}
.case h4 a:hover{color:var(--accent);text-decoration:none}
.by{font-size:11.5px;color:var(--muted);margin:0}
.why2{font-size:12.5px;color:#3C443E;margin:4px 0 0;line-height:1.7}
.tech{display:flex;gap:6px;flex-wrap:wrap;margin-top:2px}
.tech span{font-size:11px;padding:2px 8px;border-radius:6px;background:#F2F4F1;
  border:1px solid var(--line);color:#3C443E}
.points{margin:4px 0 0;padding-left:15px}
.points li{font-size:12px;color:var(--muted);line-height:1.65}
.case-foot{margin-top:auto;padding-top:10px;display:flex;align-items:center;
  justify-content:space-between;gap:8px}
.btn{display:inline-flex;align-items:center;gap:6px;font-size:12.5px;font-weight:600;
  padding:8px 14px;border-radius:9px;background:var(--accent);color:#fff}
.btn:hover{background:#254A37;text-decoration:none}
.rights{font-size:10.5px;color:var(--muted);text-align:right;line-height:1.4}
.src{margin:6px 0 0;font-size:11px;color:var(--muted);word-break:break-all}
.src a{color:#4B6B58}

/* ---------- 表格与其他 ---------- */
table{border-collapse:collapse;width:100%;margin:14px 0 18px;font-size:12.5px;
  background:var(--card)}
th,td{border:1px solid var(--line);padding:8px 10px;text-align:left;vertical-align:top}
th{background:#F1F3EF;font-weight:600}
blockquote{margin:14px 0;padding:12px 16px;border-left:3px solid var(--accent);
  background:var(--card);color:#3C443E;font-size:13px}
ul.plain{padding-left:18px}
ul.plain li{font-size:13.5px;margin:4px 0}
footer{margin-top:72px;padding-top:22px;border-top:1px solid var(--line);
  font-size:11.5px;color:var(--muted);line-height:1.8}
footer b{color:var(--ink)}
@media (max-width:960px){
  .c-grid{grid-template-columns:1fr}
  .cards,.cases,.quad,.mats,.figs.two,.legend{grid-template-columns:1fr 1fr}
  .cover h1{font-size:32px}
}
@media print{
  body{background:#fff} .jump:hover{transform:none;box-shadow:none}
  .concept{break-inside:avoid} .case{break-inside:avoid}
}
"""


# --------------------------------------------------------------------------
# 小工具
# --------------------------------------------------------------------------
def _h(x: Any) -> str:
    return html.escape(str(x if x is not None else ""))


def _clip(text: Any, n: int) -> str:
    s = " ".join(str(text or "").split())
    return s if len(s) <= n else s[:n].rstrip("，、；,;") + "…"


def _svg_inline(path: str | Path) -> str:
    text = Path(path).read_text(encoding="utf-8")
    text = text.lstrip("\ufeff")
    for head in ("<?xml ", "<!DOCTYPE"):
        while text.startswith(head):
            text = text[text.find(">") + 1:].lstrip()
    return text


def _client_why(text: Any) -> str:
    """把"为什么这样组织"的**内部推演**改写成客户能读的一句话。

    `why_this_strategy` 是打分的副产物，原样印出来是这样的：

        回应私密：业主原话提到「私密」；回应采光：业主原话提到「采光」；回应采光：
        业主原话提到「采光」；业主原话提到「私密」「采光」「通透」…

    同一个词被重复列了三四遍，客户读到的是"系统在给自己找证据"，而不是
    "为什么这样设计"。这里做三件事：合并同类"回应"、去掉纯证据句、去重。
    """
    raw = " ".join(str(text or "").split())
    if not raw:
        return ""
    topics: List[str] = []
    rest: List[str] = []
    for seg in raw.split("；"):
        seg = seg.strip().strip("。")
        if not seg:
            continue
        if seg.startswith("回应") and ("：" in seg or ":" in seg):
            body = seg.split("：", 1)[-1] if "：" in seg else seg.split(":", 1)[-1]
            if body.startswith("业主"):
                topics.append(seg.split("：", 1)[0].replace("回应", "").strip())
            continue
        if "业主原话提到" in seg:
            continue
        if seg.startswith("案例中出现同类手法"):
            tail = seg.split("：", 1)[-1]
            m = re.match(r"\s*([A-Za-z\- ]+)（(.+)）\s*$", tail)
            if m:
                zh = pv.PRECEDENT_TERMS.get(m.group(1).strip().lower(), "")
                seg = "同类手法也见于《{}》".format(m.group(2))
                if zh:
                    seg += f"（{zh}）"
            else:
                seg = "同类手法也见于" + tail
        if seg not in rest:
            rest.append(seg)
    head = ""
    if topics:
        uniq = list(dict.fromkeys(t for t in topics if t))
        head = "回应了业主提出的" + "、".join(uniq[:4])
    out = "；".join([x for x in [head] + rest if x])
    return _clip(out, 200)


def _figure(path: str | Path, kind: str, note: str = "") -> str:
    label = KIND_CN.get(kind, kind)
    return ('<figure class="fig">' + _svg_inline(path) +
            f'<figcaption class="cap"><b>{_h(label)}</b>'
            f'{_h(note or "本系统确定性绘制 · 关系示意、非按比例")}</figcaption>'
            "</figure>")


def _diagram_files(concept: Dict[str, Any]) -> List[Tuple[str, str]]:
    out: List[Tuple[str, str]] = []
    for d in concept.get("diagrams") or []:
        kind, path = str(d.get("kind") or ""), str(d.get("path") or "")
        if path and Path(path).exists():
            out.append((kind, path))
    return out


def _ordered_figures(concept: Dict[str, Any], lead: str) -> List[Tuple[str, str]]:
    files = _diagram_files(concept)
    order = FIGURE_ORDER.get(lead, FIGURE_ORDER["architecture"])
    rank = {k: i for i, k in enumerate(order)}
    return sorted(files, key=lambda kv: (rank.get(kv[0], 50), kv[0]))


def _case_index(research: Optional[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    return {str(c.get("url") or ""): c for c in (research or {}).get("cases") or []}


def _stage_image(path: Path, out_dir: Path) -> str:
    """把已授权的本地图片复制进交付目录，返回相对路径。"""
    assets = out_dir / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    target = assets / path.name
    if path.resolve() != target.resolve():
        shutil.copyfile(path, target)
    return f"assets/{target.name}"


# --------------------------------------------------------------------------
# 案例卡
# --------------------------------------------------------------------------
def case_card(ref: Dict[str, Any], full: Optional[Dict[str, Any]] = None, *,
              index: int = 1, project_dir: Optional[Path] = None,
              out_dir: Optional[Path] = None, show_points: bool = True) -> str:
    """一张案例卡：图 + 名称 + 事务所 + 来源 + 理由 + 可借鉴手法。

    图的来源由 `preview.resolve()` 决定，这里不另做判断：只有登记过授权的
    本地图片才会被复制进 `assets/`；其余一律用本系统绘制的手法示意。
    """
    merged = {**(full or {}), **{k: v for k, v in ref.items() if v}}
    url = str(merged.get("url") or "")
    visual = pv.resolve(merged, project_dir=project_dir, index=index)

    if visual["kind"] == "licensed_photo" and out_dir:
        rel = _stage_image(Path(visual["image"]), out_dir)
        thumb = f'<img src="{_h(rel)}" alt="{_h(merged.get("title"))}">'
        badge = "授权图片"
    else:
        thumb = visual.get("svg") or ""
        badge = "手法示意"

    techs = visual.get("techniques") or []
    chips = "".join(f'<span>{_h(t["label"])}</span>' for t in techs[:3])

    why = str(ref.get("why") or "").strip()
    # `fits` 为空时后端只会给一句"它在「X」这个方向上…"，同一方案的两张卡会
    # 一字不差，读起来像没做功课。改用这个案例自己的手法描述。
    if "这个方向上是我们这次找到的可核验案例" in why and techs:
        why = "它用「{}」处理同类问题，是这次找到的可核验案例".format(
            "、".join(t["label"] for t in techs[:2]))

    place = "、".join([x for x in (merged.get("city"), merged.get("country")) if x])
    byline = "　·　".join([x for x in (
        merged.get("architect") or "事务所未标注",
        place,
        merged.get("year") or "",
    ) if x])

    # "怎么用到这个方案"是概念级的建议：同一方案的两张卡都印一遍，
    # 客户会以为复制粘贴了。只在第一张上说。
    points = [str(x) for x in (ref.get("borrow") or [])][:2] if show_points else []
    verify = str(ref.get("verify_label") or merged.get("verify_label") or "")
    # 「已回读核验：页面可打开，标题一致」在卡片上太长，卡上只要结论，
    # 细节留给来源清单。判据不变，只是不在这张卡上展开。
    verify = verify.split("：")[0]
    disc = {"architecture": "建筑", "interior": "室内",
            "landscape": "景观"}.get(str(merged.get("discipline") or ""), "")

    return f"""
<article class="case">
  <div class="thumb">{thumb}<span class="badge">{_h(badge)}</span></div>
  <div class="case-body">
    <div class="case-kicker">REF {index:02d}　{_h(disc)}{_h("　·　" + verify if verify else "")}</div>
    <h4><a href="{_h(url)}" target="_blank" rel="noopener noreferrer">{_h(merged.get("title"))}</a></h4>
    <p class="by">{_h(byline)}</p>
    <p class="why2">{_h(_clip(why, 120))}</p>
    {f'<div class="tech">{chips}</div>' if chips else ''}
    {('<ul class="points">' + ''.join(f'<li>{_h(_clip(p, 70))}</li>' for p in points) + '</ul>') if points else ''}
    <div class="case-foot">
      <a class="btn" href="{_h(url)}" target="_blank" rel="noopener noreferrer">查看原案例 ↗</a>
      <span class="rights">{_h(visual.get("rights_label"))}<br>{_h(_clip(visual.get("note"), 34))}</span>
    </div>
  </div>
</article>"""


# --------------------------------------------------------------------------
# 方案段
# --------------------------------------------------------------------------
def _seq_steps(concept: Dict[str, Any]) -> List[Dict[str, Any]]:
    seq = concept.get("experience_sequence") or {}
    steps = seq.get("steps") if isinstance(seq, dict) else seq
    return [s for s in (steps or []) if isinstance(s, dict)]


def _materials(concept: Dict[str, Any]) -> str:
    mats = [m for m in (concept.get("material_direction") or [])
            if isinstance(m, dict) and m.get("name")]
    if not mats:
        return '<p style="font-size:12.5px;color:#6B7280">本方案未指定材料方向。</p>'
    cells = []
    for m in mats[:6]:
        cells.append(
            f'<div class="mat"><div class="n">{_h(m.get("name"))}</div>'
            f'<div class="a">{_h(_clip(m.get("application") or "", 26))}</div></div>')
    return '<div class="mats">' + "".join(cells) + "</div>"


def _swatches(concept: Dict[str, Any]) -> str:
    pal = concept.get("palette") or {}
    items: List[Dict[str, Any]] = []
    for band in ("dominant", "secondary", "accent"):
        items.extend([c for c in (pal.get(band) or []) if c.get("hex")])
    if not items:
        return ""
    sw = "".join(
        f'<span class="sw" title="{_h(c.get("name"))} {_h(c.get("hex"))}" '
        f'style="background:{_h(c.get("hex"))}"></span>' for c in items[:9])
    names = "、".join(_h(c.get("name")) for c in items[:4] if c.get("name"))
    return f'<div class="sws">{sw}</div><div class="a" style="margin-top:6px">{names}</div>'


def _drop_shared_lead(first: Any, second: Any, probe: int = 14) -> str:
    """两段话开头是同一句时，第二段去掉那一句。

    `lighting_direction[0]` 与 `light_view_proportion_material` 都以
    「空间侧：院给每一层的同一侧提供侧向漫射光…」开头，并排放进四个格子
    会读成重复粘贴。比较前先去掉「空间侧／风格侧」这类前缀——它们让两句话
    表面不同、读起来完全一样。
    """
    def _norm(t: str) -> str:
        return re.sub(r"^(空间侧|风格侧|专业侧)[：:]\s*", "", t).strip()

    a = _norm(" ".join(str(first or "").split()))
    b = _norm(" ".join(str(second or "").split()))
    if not b:
        return ""
    if a and b[:probe] == a[:probe]:
        for sep in ("。", "；"):
            idx = b.find(sep)
            if 0 < idx < len(b) - 1:
                b = b[idx + 1:].lstrip()
                break
        else:
            return ""
    return b


def _why_line(concept: Dict[str, Any]) -> str:
    """客户版"为什么这样组织"。

    洗干净之后如果只剩"回应了业主提出的采光、私密"这半句，就补上策略本身
    的说法，否则客户读到的是一句空话。
    """
    d = concept.get("deliberation") or {}
    cleaned = _client_why(d.get("why_this_strategy"))
    if len(cleaned) >= 30:
        return cleaned
    strategy = _clip(concept.get("design_strategy") or "", 150)
    if not strategy:
        return cleaned or "—"
    return (cleaned + "；" + strategy) if cleaned else strategy


def concept_section(concept: Dict[str, Any], idx: int, *, lead: str,
                    research_index: Dict[str, Dict[str, Any]],
                    project_dir: Optional[Path], out_dir: Path) -> str:
    d = concept.get("deliberation") or {}
    cid = str(concept.get("concept_id") or f"C{idx}")
    proto = concept.get("spatial_prototype") or {}
    family = FAMILY_CN.get(str(proto.get("family") or ""), str(proto.get("family") or ""))
    role = str(concept.get("role_label") or "")

    figs = _ordered_figures(concept, lead)
    main_figs = "".join(_figure(p, k) for k, p in figs[:2])

    steps = _seq_steps(concept)
    # 序列图与上面的步骤条是同一件事：步骤条已经把"人怎么走"讲清楚了，
    # 再放一张 1200×760 的矢量序列图，内容只占中间四成，缩到半栏后基本看不清。
    # 只保留在前两张大图里的序列图；它作为第三张时略过。
    rest = [(k, p) for k, p in figs[2:6] if not (k == "sequence" and steps)]
    rest_figs = "".join(_figure(p, k) for k, p in rest)

    # 意向板（色板 + 材料 + 案例卡）本来就是为方案画的，直接放进提案：
    # 没有房间数据时它比一张空分区图有用得多。它内容多，占整栏，不挤半栏。
    board = str((concept.get("moodboard") or {}).get("board_svg") or "")
    board_html = ""
    if board and Path(board).exists():
        board_html = ('<div class="block-h">材料与色彩板</div><div class="figs">'
                      + _figure(board, "moodboard",
                                "色板与材料取自风格库与本方案材料方向；图为确定性绘制")
                      + "</div>")

    seq_html = ""
    if steps:
        seq_html = '<ol class="seq">' + "".join(
            f'<li><div class="k">{_h(s.get("step"))}</div>'
            f'<div class="e">{_h(_clip(s.get("event"), 58))}</div></li>'
            for s in steps[:6]) + "</ol>"

    light = (concept.get("lighting_direction") or [""])[0]
    quad_items = [
        ("光线", light),
        ("视线与比例", _drop_shared_lead(light, d.get("light_view_proportion_material"))),
        ("界面与立面", d.get("facade") or ""),
        ("楼层如何分工", "；".join(d.get("levels_program") or [])),
    ]
    quad = "".join(
        f'<div><h5>{_h(k)}</h5><p>{_h(_clip(v, 130))}</p></div>'
        for k, v in quad_items if v)

    refs = (concept.get("references") or {}).get("cases") or []
    cards = "".join(
        case_card(r, research_index.get(str(r.get("url") or "")),
                  index=i + 1, project_dir=project_dir, out_dir=out_dir,
                  show_points=(i == 0))
        for i, r in enumerate(refs))
    case_block = ('<div class="cases">' + cards + "</div>" if cards else
                  f'<p style="color:#6B7280;font-size:13px">'
                  f'{_h((concept.get("references") or {}).get("note") or "本次无可用案例")}</p>')

    adv = "".join(f"<li>{_h(_clip(x, 60))}</li>" for x in (concept.get("advantages") or [])[:3])
    trade = "".join(f"<li>{_h(_clip(x, 60))}</li>" for x in (concept.get("tradeoffs") or [])[:4])
    risks = "".join(f"<li>{_h(_clip(x, 56))}</li>"
                    for x in (concept.get("technical_risks") or [])[:3])
    unverified = d.get("unverified_requires") or []
    unv = "".join(f"<li>{_h(x)}</li>" for x in unverified[:3])

    return f"""
<section class="concept" id="{_h(cid.lower())}">
  <div class="c-head">
    <div class="c-eyebrow">方案 {idx:02d}　·　{_h(role)}　·　{_h(family)}</div>
    <h2>{_h(concept.get("concept_name"))}</h2>
    <p class="statement">{_h(concept.get("concept_statement"))}</p>
  </div>
  <div class="c-grid">
    <div class="c-main">
      <div class="callout">
        <h4>最有价值的设计机会</h4>
        <p>{_h(d.get("key_opportunity") or concept.get("design_problem"))}</p>
      </div>
      <p class="why"><b>为什么这样组织：</b>{_h(_why_line(concept))}</p>
      <div class="figs">{main_figs}</div>
      {f'<div class="block-h">人进到这里，会经历什么</div>{seq_html}' if seq_html else ''}
      {f'<div class="block-h">光线、视线、比例与材料怎么配合</div><div class="quad">{quad}</div>' if quad else ''}
      {board_html}
      {f'<div class="block-h">更多图解</div><div class="figs two">{rest_figs}</div>' if rest_figs else ''}
      <div class="block-h">案例参考 · 借的是手法，不是外观</div>
      {case_block}
    </div>
    <aside class="side">
      <div class="panel">
        <h4>材料方向</h4>
        {_materials(concept)}
        {_swatches(concept)}
      </div>
      <div class="panel dark">
        <h4>三个专业怎么成整体</h4>
        <p>{_h(_clip(d.get("integration") or "本方案按主导专业推进，其余专业做界面协调。", 220))}</p>
      </div>
      <div class="panel">
        <h4>要结构与机电配合的地方</h4>
        <p>{_h(_clip(d.get("technical_coordination") or "—", 200))}</p>
        {f'<ul style="margin-top:8px">{risks}</ul>' if risks else ''}
      </div>
      <div class="panel warn">
        <h4>代价与前提</h4>
        <ul>{trade or '<li>—</li>'}</ul>
        {f'<p style="margin-top:8px"><b>尚待核实：</b>{"、".join(_h(x) for x in unverified[:3])}</p>' if unverified else ''}
      </div>
      {f'<div class="panel"><h4>适合这个方案的理由</h4><ul>{adv}</ul></div>' if adv else ''}
      <div class="panel">
        <h4>造价与维护</h4>
        <p>{_h(_clip(concept.get("cost_impact") or "—", 110))}</p>
        <p style="margin-top:6px">{_h(_clip(concept.get("maintenance_impact") or "", 110))}</p>
      </div>
    </aside>
  </div>
</section>"""


# --------------------------------------------------------------------------
# 整页
# --------------------------------------------------------------------------
LEGEND = """
<div class="legend">
  <div><b><span class="dot case"></span>真实案例</b>第三方作品。给来源入口，不把照片搬进提案。</div>
  <div><b><span class="dot plate"></span>手法示意</b>本系统按案例公开文字画的关系图，不是原案例照片。</div>
  <div><b><span class="dot own"></span>原创意向</b>OmniAiLab 画布生成，只表达氛围，不是本项目效果图。</div>
  <div><b><span class="dot final"></span>正式效果图</b>G3 平面确认后生成。本次尚未进入 G3，因此页面里没有。</div>
</div>"""


def proposal(payload: Dict[str, Any], out_dir: str | Path, *,
             project_name: str = "", research: Optional[Dict[str, Any]] = None,
             project_dir: Optional[str | Path] = None,
             meta: Optional[Sequence[str]] = None,
             filename: str = "index.html") -> Path:
    """把 concept-options 渲染成一页客户提案。返回写出的文件路径。"""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    concepts = list(payload.get("concepts") or [])
    lead = str(payload.get("lead_discipline") or
               (concepts[0].get("deliberation") or {}).get("discipline") or "")
    rindex = _case_index(research)
    pdir = Path(project_dir) if project_dir else None

    name = project_name or str(payload.get("project_id") or "设计提案")
    lead_label = str(payload.get("lead_label") or "")

    # 统计只数真实存在的东西，不写"预计"
    n_figs = sum(len(_diagram_files(c)) for c in concepts)
    n_cases = sum(len((c.get("references") or {}).get("cases") or []) for c in concepts)
    techs = set()
    for c in concepts:
        for r in (c.get("references") or {}).get("cases") or []:
            full = rindex.get(str(r.get("url") or ""), {})
            for t in pv.techniques(full):
                techs.add(t["kind"])

    jumps = "".join(
        f'<a class="jump" href="#{_h(str(c.get("concept_id")).lower())}">'
        f'<div class="no">方案 {i:02d}　{_h(c.get("role_label"))}</div>'
        f'<h3>{_h(c.get("concept_name"))}</h3>'
        f'<p>{_h(_clip((c.get("deliberation") or {}).get("parti")
                       or c.get("design_strategy"), 74))}</p>'
        f'<div class="tags"><span class="tag">'
        f'{_h(FAMILY_CN.get(str((c.get("spatial_prototype") or {}).get("family")), "—"))}</span>'
        f'<span class="tag">图 {len(_diagram_files(c))}</span>'
        f'<span class="tag">案例 {len((c.get("references") or {}).get("cases") or [])}</span>'
        f'</div></a>'
        for i, c in enumerate(concepts, 1))

    body = "".join(concept_section(c, i, lead=lead, research_index=rindex,
                                   project_dir=pdir, out_dir=out)
                   for i, c in enumerate(concepts, 1))

    meta_line = "　·　".join([x for x in (lead_label and f"{lead_label}主导",
                                          f"S2 概念 {len(concepts)} 套",
                                          *list(meta or [])) if x])

    page = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{_h(name)} · 概念方案</title>
<style>{CSS}</style></head>
<body><main>
<header class="cover">
 <div class="cover-in">
  <div class="cover-top">OmniAiLab AI Architect　·　概念方案</div>
  <h1>{_h(name)}</h1>
  <p class="lede">{_h(meta_line or "设计提案")}</p>
  <div class="stats">
    <div><b>{len(concepts)}</b>套组织逻辑不同的方案</div>
    <div><b>{n_figs}</b>张概念图解</div>
    <div><b>{n_cases}</b>个已核验案例</div>
    <div><b>{len(techs)}</b>类可借鉴手法</div>
  </div>
 </div>
</header>

{LEGEND}

<div class="sec-label">Overview</div>
<div class="sec-title">三套方案，差在组织逻辑，不差在材料</div>
<div class="cards">{jumps or '<p>本次未生成概念方案。</p>'}</div>

{body}

<div class="sec-label">Sources</div>
<div class="sec-title">案例来源与使用边界</div>
<blockquote>
本页所有案例均来自可公开访问的案例页面，标题与链接经过回读核验。案例照片的权利属原作者与摄影师，
本提案不下载、不重新托管、不嵌入；页面上出现的图是本系统按案例公开文字绘制的手法示意。
需要原创设计意向图时使用 OmniAiLab 原生画布生成，并标注为「原创意向」，不与真实案例照片混用。
</blockquote>

<footer>
  <b>OmniAiLab AI 建筑与室内设计总设计师</b>　·　本页由 S2 概念阶段产出，用于讨论设计方向。<br>
  结构安全、消防、无障碍、机电负荷与当地法规符合性不在本系统结论范围，须由持证专业人员在项目所在地复核签署；
  方案深度成果不得直接作为施工图；生成式图像不得作为尺寸依据。<br>
  © OmniAiLab ｜ 开发者：Mochiball ｜ omniailabx.com — 未经授权禁止复制、传播或二次分发。
</footer>
</main></body></html>"""

    path = out / filename
    path.write_text(page, encoding="utf-8")
    return path


__all__ = ["FAMILY_CN", "FIGURE_ORDER", "KIND_CN", "case_card", "concept_section",
           "proposal"]
