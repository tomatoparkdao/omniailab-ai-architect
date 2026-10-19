"""客户可读的 HTML 提案：作品是主角，版面是配角。

上一版被批评得对：卡片、侧栏、大留白、小图被塞进大白框——那是管理后台的
版式，不是设计事务所的版式。这一版按作品的逻辑重排：

1. **视觉分级**。封面与每套方案各有一张满幅图（素材库真实图片），分析图按
   重要度分满宽 / 双联 / 三联三档。图不再被平均对待。
2. **图有身份**。真实素材、手法示意、原创意向、正式效果图四种东西用不同的
   标记与图注区分，页首有图例。混着放最省事，也最容易在交付后说不清。
3. **文字退到图后面**。每套方案先给一句主张、一张图，再给分析；不再用一列
   栏面板把结论挤在边上。代价与前提放成并列的三栏注，读完图再看。
4. **没有素材就老实承认**。素材库取不到图时整块不出现，不缩放一张示意图
   去占它的位置——那正是上一版最大的问题。

只读 S2 已经产出的 JSON 与素材库目录，不重新计算设计结论；没有的东西不画。

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import html
import re
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from ..research import library as lib
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
    "daylight": "采光策略图", "sequence": "空间序列图", "massing": "体量演变图",
    "section": "剖面与楼层图", "landscape": "景观总平面",
    "axon": "室内剖切轴测", "moodboard": "材料与色彩板",
}

#: 每个主导专业先看哪几张图。图种顺序本身就是阅读顺序。
FIGURE_ORDER: Dict[str, Tuple[str, ...]] = {
    "architecture": ("massing", "section", "axon", "sequence", "daylight",
                     "zoning", "circulation", "functional", "landscape"),
    "interior": ("axon", "zoning", "circulation", "daylight", "sequence",
                 "massing", "section", "functional", "landscape"),
    "landscape": ("landscape", "sequence", "daylight", "zoning", "circulation",
                  "axon", "massing", "section", "functional"),
}

#: 每个专业取图时的检索词（素材库标签里真的有的词）
LEAD_WORDS: Dict[str, Tuple[str, ...]] = {
    "architecture": ("别墅", "现代建筑", "庭院", "住宅", "泳池"),
    "interior": ("客厅", "公寓", "卧室", "餐厅", "室内设计"),
    "landscape": ("花园", "庭院", "景观草坪", "户外花园", "树木"),
}

CSS = """
:root{
  --paper:#FAF8F3; --paper-2:#F2EFE6; --ink:#1A1D1A; --body:#2E332E;
  --muted:#6E736A; --line:#DED9CB; --line-soft:#E9E5D8;
  --brand:#2F5D45; --brand-soft:#E8EEE7; --warm:#A97A43; --warm-soft:#F6EDDD;
  --serif:'Songti SC','Noto Serif SC','Source Han Serif SC',Georgia,serif;
  --sans:'Noto Sans SC','PingFang SC','Microsoft YaHei',-apple-system,sans-serif;
}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;background:var(--paper);color:var(--body);
  font-family:var(--sans);font-size:16px;line-height:1.8;
  -webkit-font-smoothing:antialiased;text-rendering:optimizeLegibility}
a{color:var(--brand);text-decoration:none}
a:hover{text-decoration:underline}
.wrap{max-width:1440px;margin:0 auto;padding:0 44px}
.serif{font-family:var(--serif)}

/* ---------- 封面 ---------- */
.cover{position:relative;min-height:86vh;display:flex;align-items:flex-end;
  color:#F4F2EC;overflow:hidden;background:#20241F}
.cover-img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;
  opacity:.92}
.cover:after{content:"";position:absolute;inset:0;
  background:linear-gradient(180deg,rgba(16,20,16,.18) 0%,rgba(16,20,16,.30) 48%,
  rgba(16,20,16,.86) 100%)}
.cover-in{position:relative;z-index:2;width:100%;max-width:1440px;margin:0 auto;
  padding:0 44px 68px}
.cover-top{font-size:12px;letter-spacing:.26em;text-transform:uppercase;
  color:#B9C7BA;margin-bottom:22px}
.cover h1{font-family:var(--serif);font-weight:600;letter-spacing:-.01em;
  font-size:clamp(40px,5.2vw,74px);line-height:1.06;margin:0 0 18px;max-width:16em}
.cover .sub{font-size:17px;color:#D6D9D0;max-width:44em;margin:0 0 40px;line-height:1.8}
.cover-meta{display:flex;gap:56px;flex-wrap:wrap;border-top:1px solid rgba(255,255,255,.22);
  padding-top:22px}
.cover-meta div{font-size:12px;letter-spacing:.1em;color:#A9B6AC}
.cover-meta b{display:block;font-family:var(--serif);font-size:30px;color:#F4F2EC;
  font-weight:600;letter-spacing:0;margin-bottom:2px}

/* ---------- 图例 ---------- */
.legend{display:grid;grid-template-columns:repeat(4,1fr);gap:0;
  border-bottom:1px solid var(--line);margin:0 0 8px}
.legend div{padding:20px 22px 20px 0;font-size:12.5px;color:var(--muted);line-height:1.65}
.legend b{display:block;color:var(--ink);font-size:13px;font-weight:600;margin-bottom:3px}
.dot{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:7px;
  vertical-align:1px}
.dot.case{background:#9AA3AE}.dot.plate{background:var(--brand)}
.dot.own{background:var(--warm)}.dot.final{background:#191C19}

/* ---------- 段落系统 ---------- */
.sec{padding:52px 0 10px}
.sec-label{font-size:11px;letter-spacing:.24em;color:var(--brand);
  text-transform:uppercase;margin:0 0 10px}
.sec-title{font-family:var(--serif);font-size:clamp(24px,2.4vw,32px);font-weight:600;
  margin:0 0 26px;letter-spacing:-.01em;line-height:1.3}

/* ---------- 总览 ---------- */
.jumps{display:grid;grid-template-columns:repeat(3,1fr);gap:26px}
.jump{display:block;color:inherit;border-top:2px solid var(--ink);padding-top:14px}
.jump:hover{text-decoration:none}
.jump:hover h3{color:var(--brand)}
.jump .thumb{overflow:hidden;background:var(--paper-2);margin-bottom:14px}
.jump .thumb img{display:block;width:100%;aspect-ratio:4/3;object-fit:cover;
  transition:transform .5s ease}
.jump:hover .thumb img{transform:scale(1.03)}
.jump .no{font-size:11px;letter-spacing:.2em;color:var(--muted)}
.jump h3{font-family:var(--serif);font-size:22px;font-weight:600;margin:6px 0 6px;
  transition:color .2s}
.jump p{font-size:13.5px;color:var(--muted);margin:0;line-height:1.7}

/* ---------- 方案 ---------- */
.concept{padding:88px 0 40px;border-top:1px solid var(--line);margin-top:64px}
.c-head{display:grid;grid-template-columns:minmax(0,1fr) 360px;gap:48px;
  align-items:start;margin-bottom:30px}
.c-no{font-size:12px;letter-spacing:.22em;color:var(--brand);margin-bottom:14px}
.c-no span{color:var(--muted);letter-spacing:.08em}
.c-title{font-family:var(--serif);font-size:clamp(32px,4vw,56px);font-weight:600;
  line-height:1.1;margin:0;letter-spacing:-.015em}
.c-facts{border-top:1px solid var(--line);padding-top:14px;margin-top:6px}
.c-facts dl{margin:0;display:grid;grid-template-columns:auto 1fr;gap:6px 16px}
.c-facts dt{font-size:11px;letter-spacing:.12em;color:var(--muted)}
.c-facts dd{margin:0;font-size:13px;color:var(--body);line-height:1.6}

.statement{font-size:18px;line-height:1.95;color:var(--body);max-width:50em;
  margin:0 0 34px}

/* ---------- 图 ---------- */
.hero{margin:0 0 10px}
.hero img{display:block;width:100%;aspect-ratio:16/9;object-fit:cover;
  background:var(--paper-2)}
.hero.tall img{aspect-ratio:4/3}
.cap{display:flex;justify-content:space-between;gap:16px;align-items:baseline;
  border-top:1px solid var(--line);margin-top:10px;padding-top:9px;
  font-size:12px;color:var(--muted);line-height:1.6}
.cap .fno{font-family:var(--serif);font-size:11px;letter-spacing:.14em;
  color:var(--ink);white-space:nowrap}
.cap .who{text-align:right;white-space:nowrap;color:#8A8F86}

.figs{display:grid;grid-template-columns:1fr;gap:26px;margin:0}
.figs.pair{grid-template-columns:1fr 1fr}
.figs.pair .fig:first-child{grid-column:span 2}
.fig{background:transparent}
.fig svg{display:block;width:100%;height:auto}
.fig .frame{border:1px solid var(--line);background:#fff;padding:0}

/* ---------- 三栏注（替代侧栏面板） ---------- */
.notes{display:grid;grid-template-columns:repeat(3,1fr);gap:0;
  border-top:1px solid var(--line);margin:44px 0 0}
.notes > div{padding:22px 30px 6px 0;border-right:1px solid var(--line-soft)}
.notes > div:last-child{border-right:0;padding-right:0}
.notes h5{font-size:11px;letter-spacing:.18em;color:var(--muted);margin:0 0 10px;
  font-weight:600;text-transform:uppercase}
.notes p,.notes li{font-size:14px;line-height:1.8;color:var(--body);margin:0}
.notes ul{margin:0;padding-left:16px}
.notes li{margin:0 0 4px}
.notes .warn h5{color:var(--warm)}
.notes .warn li{color:#5B4B34}
.notes b{color:var(--ink)}

/* ---------- 材料带 ---------- */
.mats{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));
  gap:18px;margin:0 0 8px}
.mat{border-top:1px solid var(--line);padding-top:10px}
.mat .ph{aspect-ratio:4/3;overflow:hidden;background:var(--paper-2);margin-bottom:10px}
.mat .ph img{display:block;width:100%;height:100%;object-fit:cover}
.mat .n{font-size:14.5px;font-weight:600;color:var(--ink);line-height:1.4}
.mat .a{font-size:12px;color:var(--muted);line-height:1.6;margin-top:2px}
.sws{display:flex;gap:0;margin-top:10px;border:1px solid var(--line)}
.sw{flex:1;height:16px}

/* ---------- 案例 ---------- */
.cases{display:grid;grid-template-columns:1fr 1fr;gap:34px}
.case{border-top:2px solid var(--ink);padding-top:14px;display:flex;
  flex-direction:column}
.case .thumb{overflow:hidden;background:var(--paper-2);margin-bottom:12px}
.case .thumb svg,.case .thumb img{display:block;width:100%;height:auto}
.case .thumb .badge{display:inline-block;font-size:10px;letter-spacing:.14em;
  padding:2px 8px;border:1px solid var(--line);color:var(--muted);
  background:var(--paper);margin-bottom:8px}
.case-kicker{font-size:10.5px;letter-spacing:.16em;color:var(--muted);margin-bottom:6px}
.case h4{font-family:var(--serif);font-size:19px;line-height:1.4;font-weight:600;
  margin:0 0 4px}
.case h4 a{color:var(--ink)}
.case h4 a:hover{color:var(--brand);text-decoration:none}
.by{font-size:12px;color:var(--muted);margin:0 0 8px}
.why2{font-size:13.5px;color:var(--body);margin:0 0 10px;line-height:1.75}
.tech{display:flex;gap:6px;flex-wrap:wrap;margin:0 0 10px}
.tech span{font-size:11px;padding:2px 8px;border:1px solid var(--line);
  color:#5B6157}
.points{margin:0 0 10px;padding-left:16px}
.points li{font-size:12.5px;color:var(--muted);line-height:1.7}
.case-foot{margin-top:auto;display:flex;align-items:center;justify-content:space-between;
  gap:10px;padding-top:10px}
.btn{font-size:12.5px;font-weight:600;padding:8px 0;color:var(--brand);
  border-bottom:1px solid var(--brand)}
.btn:hover{text-decoration:none;opacity:.75}
.rights{font-size:10.5px;color:var(--muted);text-align:right;line-height:1.45}

/* ---------- 表格 / 结语 ---------- */
table{border-collapse:collapse;width:100%;margin:16px 0 20px;font-size:13px}
th,td{border-bottom:1px solid var(--line);padding:9px 10px;text-align:left;
  vertical-align:top}
th{font-weight:600;color:var(--ink);border-bottom:1px solid var(--ink)}
blockquote{margin:18px 0;padding:20px 24px;border-left:2px solid var(--brand);
  background:#fff;font-size:14px;line-height:1.85;color:var(--body)}
ul.plain{padding-left:18px}
ul.plain li{font-size:14.5px;margin:5px 0}
footer{margin:80px 0 0;padding:26px 0 40px;border-top:1px solid var(--ink);
  font-size:12px;color:var(--muted);line-height:1.9}
footer b{color:var(--ink)}
.sig{font-family:var(--serif);color:var(--ink)}

@media (max-width:1100px){
  .wrap{padding:0 28px}
  .c-head{grid-template-columns:1fr;gap:22px}
  .c-facts{max-width:420px}
  .legend{grid-template-columns:1fr 1fr}
  .notes{grid-template-columns:1fr}
  .notes > div{border-right:0;border-bottom:1px solid var(--line-soft);
    padding:18px 0}
  .jumps{grid-template-columns:1fr}
  .cases{grid-template-columns:1fr}
  .figs.pair{grid-template-columns:1fr}
  .figs.pair .fig:first-child{grid-column:span 1}
}
@media (max-width:720px){
  body{font-size:15px}
  .cover{min-height:70vh}
  .cover-meta{gap:26px}
  .cover-meta b{font-size:24px}
  .legend{grid-template-columns:1fr}
  .concept{padding:56px 0 24px}
  .mats{grid-template-columns:1fr 1fr}
}
@media print{
  body{background:#fff}
  .cover{min-height:auto;page-break-after:always}
  .concept{page-break-before:always}
  a{color:#000}
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

        回应私密：业主原话提到「私密」；回应采光：业主原话提到「采光」…

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


def _cap(fno: str, label: str, note: str = "", who: str = "") -> str:
    """统一图注：编号 + 图名 + 一句说明 + 右端归属。"""
    right = who or "本系统确定性绘制 · 关系示意 · 非按比例"
    return (f'<div class="cap"><span><span class="fno">{_h(fno)}</span>'
            f'　{_h(label)}{("　" + _h(note)) if note else ""}</span>'
            f'<span class="who">{_h(right)}</span></div>')


def _figure(path: str | Path, kind: str, *, fno: str = "", note: str = "") -> str:
    label = KIND_CN.get(kind, kind)
    return ('<figure class="fig">' + _svg_inline(path) +
            _cap(fno or "FIG", label, note) + "</figure>")


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

    points = [str(x) for x in (ref.get("borrow") or [])][:2] if show_points else []
    verify = str(ref.get("verify_label") or merged.get("verify_label") or "")
    # 「已回读核验：页面可打开，标题一致」在卡片上太长，卡上只要结论，
    # 细节留给来源清单。判据不变，只是不在这张卡上展开。
    verify = verify.split("：")[0]
    disc = {"architecture": "建筑", "interior": "室内",
            "landscape": "景观"}.get(str(merged.get("discipline") or ""), "")

    return f"""
<article class="case">
  <div class="thumb">{thumb}<div><span class="badge">{_h(badge)}</span></div></div>
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
</article>"""


# --------------------------------------------------------------------------
# 方案段
# --------------------------------------------------------------------------
def _seq_steps(concept: Dict[str, Any]) -> List[Dict[str, Any]]:
    seq = concept.get("experience_sequence") or {}
    steps = seq.get("steps") if isinstance(seq, dict) else seq
    return [s for s in (steps or []) if isinstance(s, dict)]


def _materials(concept: Dict[str, Any],
               photos: Sequence[Dict[str, Any]] = ()) -> str:
    """材料带：有素材照片就放照片，没有就只给名称与做法（不拿色块冒充材质）。"""
    mats = [m for m in (concept.get("material_direction") or [])
            if isinstance(m, dict) and m.get("name")]
    if not mats:
        return '<p style="font-size:14px;color:var(--muted)">本方案未指定材料方向。</p>'
    cells = []
    for i, m in enumerate(mats[:6]):
        ph = ""
        if i < len(photos) and photos[i].get("path"):
            ph = (f'<div class="ph"><img src="{_h(photos[i]["file"])}" '
                  f'alt="{_h(photos[i]["title"])}"></div>')
        cells.append(
            f'<div class="mat">{ph}'
            f'<div class="n">{_h(m.get("name"))}</div>'
            f'<div class="a">{_h(_clip(m.get("application") or "", 26))}'
            f'{("　·　" + _h(_clip(m.get("finish") or "", 16))) if m.get("finish") else ""}'
            f'</div></div>')
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
    return (f'<div class="sws">{sw}</div>'
            f'<div style="font-size:12px;color:var(--muted);margin-top:6px">{names}</div>')


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
    # 推敲层给的原文里夹着字段名（parti / massing / zones…）。客户不该看到
    # "parti；" 这种词——它是我们的中间产物，不是设计语言。
    cleaned = re.sub(r"\b(parti|massing|section|facade|zoning|zones|levels_program|"
                     r"logic_key|strong_water)\b\s*[；;：:，,]?\s*", "", cleaned).strip()
    if len(cleaned) >= 30:
        return cleaned
    strategy = _clip(concept.get("design_strategy") or "", 150)
    if not strategy:
        return cleaned or "—"
    return (cleaned + "；" + strategy) if cleaned else strategy


def _hero_block(img: Optional[Dict[str, Any]], fno: str, label: str,
                note: str = "") -> str:
    if not img:
        return ""
    who = f'{img.get("source", "")} · {img.get("title", "")}'
    return (f'<div class="hero"><img src="{_h(img["file"])}" '
            f'alt="{_h(img.get("title"))}"></div>' + _cap(fno, label, note, who))


def concept_section(concept: Dict[str, Any], idx: int, *, lead: str,
                    research_index: Dict[str, Dict[str, Any]],
                    project_dir: Optional[Path], out_dir: Path,
                    photos: Sequence[Dict[str, Any]] = (),
                    fno_start: int = 1) -> Tuple[str, int]:
    d = concept.get("deliberation") or {}
    cid = str(concept.get("concept_id") or f"C{idx}")
    proto = concept.get("spatial_prototype") or {}
    family = FAMILY_CN.get(str(proto.get("family") or ""), str(proto.get("family") or ""))
    role = str(concept.get("role_label") or "")

    figs = _ordered_figures(concept, lead)
    seq = _seq_steps(concept)
    # 序列图与步骤条是同一件事：步骤条已经把"人怎么走"讲清楚了，
    # 再放一张同内容的矢量图是重复。只保留前三张大图里的序列图。
    figs = [(k, p) for k, p in figs if not (k == "sequence" and seq)]

    fno = fno_start
    fig_html: List[str] = []
    for i, (kind, path) in enumerate(figs[:4]):
        fno += 1
        cls = "figs" if i == 0 else "figs pair"
        block = _figure(path, kind, fno=f"FIG.{fno:02d}")
        if i == 0:
            fig_html.append(f'<div class="figs">{block}</div>')
        elif i == 1:
            fig_html.append(f'<div class="figs pair">{block}')
        elif i == 2:
            fig_html.append(block + "</div>")
        else:
            fig_html.append(f'<div class="figs">{block}</div>')
    if len(fig_html) == 2 and not fig_html[1].rstrip().endswith("</div>"):
        fig_html[1] = fig_html[1] + "</div>"
    figs_block = "".join(fig_html)

    # 意向板：色板 + 材料 + 案例格。它内容多，满宽放，不缩进半栏。
    board = str((concept.get("moodboard") or {}).get("board_svg") or "")
    board_html = ""
    if board and Path(board).exists():
        fno += 1
        board_html = (f'<div class="figs" style="margin-top:34px">'
                      + _figure(board, "moodboard", fno=f"FIG.{fno:02d}",
                                note="色板与材料取自风格库与本方案材料方向")
                      + "</div>")

    seq_html = ""
    if seq:
        seq_html = '<ol class="plain" style="columns:2;column-gap:44px">' + "".join(
            f'<li style="break-inside:avoid;margin-bottom:12px">'
            f'<b>{_h(s.get("step"))}</b>　{_h(_clip(s.get("event"), 58))}</li>'
            for s in seq[:6]) + "</ol>"

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
                  f'<p style="color:var(--muted);font-size:14px">'
                  f'{_h((concept.get("references") or {}).get("note") or "本次无可用案例")}</p>')

    trade = "".join(f"<li>{_h(_clip(x, 64))}</li>" for x in (concept.get("tradeoffs") or [])[:3])
    risks = "".join(f"<li>{_h(_clip(x, 60))}</li>" for x in (concept.get("technical_risks") or [])[:2])
    adv = "".join(f"<li>{_h(_clip(x, 64))}</li>" for x in (concept.get("advantages") or [])[:3])
    unverified = d.get("unverified_requires") or []

    hero = _hero_block(photos[0] if photos else None, f"FIG.{fno_start:02d}",
                       f"{family} · 空间意象", "素材库参考图，非本项目效果图")

    facts = [
        ("主导专业", {"architecture": "建筑", "interior": "室内",
                      "landscape": "景观"}.get(lead, lead)),
        ("空间家族", family or "—"),
        ("专业配合", _clip(d.get("integration") or "按主导专业推进", 22)),
    ]
    facts_html = "".join(
        f"<dt>{_h(k)}</dt><dd>{_h(v)}</dd>" for k, v in facts if v)

    return f"""
<section class="concept" id="{_h(cid.lower())}">
  <div class="c-head">
    <div>
      <div class="c-no">方案 {idx:02d}　<span>{_h(role)}</span></div>
      <h2 class="c-title">{_h(concept.get("concept_name"))}</h2>
    </div>
    <div class="c-facts"><dl>{facts_html}</dl></div>
  </div>
  <p class="statement">{_h(concept.get("concept_statement"))}</p>
  {hero}
  <div style="margin-top:44px"></div>
  <div class="notes" style="margin-top:0">
    <div>
      <h5>最有价值的设计机会</h5>
      <p>{_h(_clip(d.get("key_opportunity") or concept.get("design_problem"), 210))}</p>
    </div>
    <div>
      <h5>为什么这样组织</h5>
      <p>{_h(_clip(_why_line(concept), 240))}</p>
    </div>
    <div>
      <h5>适合这个方案的理由</h5>
      <ul>{adv or '<li>—</li>'}</ul>
    </div>
  </div>

  <div class="sec-label" style="margin-top:56px">Drawings</div>
  <h3 class="sec-title">方案怎么成立：{_h(KIND_CN.get(figs[0][0], "") if figs else "图解")}</h3>
  {figs_block}
  {board_html}

  {f'<div class="sec-label" style="margin-top:56px">Sequence</div><h3 class="sec-title">人进到这里，会经历什么</h3>{seq_html}' if seq_html else ''}
  {f'<div class="notes">{quad}</div>' if quad else ''}

  <div class="sec-label" style="margin-top:56px">Materials</div>
  <h3 class="sec-title">材料与色彩</h3>
  {_materials(concept, photos[1:])}
  {_swatches(concept)}

  <div class="notes" style="margin-top:40px">
    <div class="warn">
      <h5>代价与前提</h5>
      <ul>{trade or '<li>—</li>'}</ul>
    </div>
    <div>
      <h5>要结构与机电配合的地方</h5>
      <p>{_h(_clip(d.get("technical_coordination") or "—", 160))}</p>
      {f'<ul style="margin-top:6px">{risks}</ul>' if risks else ''}
    </div>
    <div>
      <h5>尚待核实</h5>
      <ul>{''.join(f'<li>{_h(x)}</li>' for x in unverified[:3]) or '<li>—</li>'}</ul>
    </div>
  </div>

  <div class="sec-label" style="margin-top:56px">Precedents</div>
  <h3 class="sec-title">案例参考 · 借的是手法，不是外观</h3>
  {case_block}
</section>""", fno + 1


# --------------------------------------------------------------------------
# 整页
# --------------------------------------------------------------------------
LEGEND = """
<div class="legend">
  <div><b><span class="dot case"></span>真实案例</b>第三方作品。给来源入口，不把照片搬进提案。</div>
  <div><b><span class="dot plate"></span>手法示意</b>本系统按案例公开文字画的关系图，不是原案例照片。</div>
  <div><b><span class="dot own"></span>素材库参考</b>自有素材库中的空间意象，用来说明方向，不是本项目效果图。</div>
  <div><b><span class="dot final"></span>正式效果图</b>G3 平面确认后生成。本次尚未进入 G3，因此页面里没有。</div>
</div>"""


def proposal(payload: Dict[str, Any], out_dir: str | Path, *,
             project_name: str = "", research: Optional[Dict[str, Any]] = None,
             project_dir: Optional[str | Path] = None,
             meta: Optional[Sequence[str]] = None,
             filename: str = "index.html",
             with_images: bool = True) -> Path:
    """把 concept-options 渲染成一页客户提案。返回写出的文件路径。

    `with_images=False` 时完全不碰素材库（离线/无网环境）：版面会自动落到
    "无图"形态，而不是拿一张示意图去占 hero 的位置。
    """
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    concepts = list(payload.get("concepts") or [])
    lead = str(payload.get("lead_discipline") or
               (concepts[0].get("deliberation") or {}).get("discipline") or "")
    rindex = _case_index(research)
    pdir = Path(project_dir) if project_dir else None

    name = project_name or str(payload.get("project_id") or "设计提案")
    lead_label = str(payload.get("lead_label") or "")

    # 素材：封面一张、每方案一张 hero + 最多两张材料图。同一条目只用一次。
    cover_imgs: List[Dict[str, Any]] = []
    per_concept: Dict[str, List[Dict[str, Any]]] = {}
    if with_images:
        used: List[str] = []
        # 庭院方案的封面要"地"不要"房"：带别墅/公寓标签的条目直接排除。
        avoid = (("别墅", "公寓", "室内", "卧室", "客厅", "酒吧", "餐厅", "办公")
                 if lead == "landscape" else ())
        require = (("花园", "庭院", "树木", "景观草坪", "户外花园", "喷泉景观")
                   if lead == "landscape" else ())
        try:
            cover_imgs = lib.gallery(
                out, lead=lead, style_tags=(), keywords=LEAD_WORDS.get(lead, ()),
                want=[("hero", "space")], exclude=used, avoid=avoid,
                require=require)
            used += [c.get("title", "") for c in cover_imgs]
            for c in concepts:
                got = lib.gallery(
                    out, lead=lead,
                    style_tags=[str(x) for x in (c.get("style_labels") or [])],
                    keywords=LEAD_WORDS.get(lead, ()),
                    want=[("hero", "space"), ("card", "material"), ("card", "material")],
                    exclude=used, avoid=avoid, require=require)
                used += [g.get("title", "") for g in got]
                per_concept[str(c.get("concept_id"))] = got
        except Exception:
            cover_imgs, per_concept = [], {}
    cover = cover_imgs[0] if cover_imgs else None

    # 统计只数真实存在的东西，不写"预计"
    n_figs = sum(len(_diagram_files(c)) for c in concepts)
    n_cases = sum(len((c.get("references") or {}).get("cases") or []) for c in concepts)
    n_imgs = (1 if cover else 0) + sum(len(v) for v in per_concept.values())
    techs = set()
    for c in concepts:
        for r in (c.get("references") or {}).get("cases") or []:
            full = rindex.get(str(r.get("url") or ""), {})
            for t in pv.techniques(full):
                techs.add(t["kind"])

    jumps = "".join(
        f'<a class="jump" href="#{_h(str(c.get("concept_id")).lower())}">'
        + (f'<div class="thumb"><img src="{_h((per_concept.get(str(c.get("concept_id"))) or [{}])[0].get("file", ""))}" '
           f'alt=""></div>'
           if (per_concept.get(str(c.get("concept_id"))) or [{}])[0].get("file") else "")
        + f'<div class="no">方案 {i:02d}　{_h(c.get("role_label"))}</div>'
        f'<h3>{_h(c.get("concept_name"))}</h3>'
        f'<p>{_h(_clip((c.get("deliberation") or {}).get("parti") or c.get("design_strategy"), 62))}</p>'
        f'</a>'
        for i, c in enumerate(concepts, 1))

    body = ""
    fno = 2                      # FIG.01 是封面
    for i, c in enumerate(concepts, 1):
        photos = per_concept.get(str(c.get("concept_id"))) or []
        section, fno = concept_section(c, i, lead=lead, research_index=rindex,
                                       project_dir=pdir, out_dir=out,
                                       photos=photos, fno_start=fno)
        body += section

    meta_line = "　·　".join([x for x in (lead_label and f"{lead_label}主导",
                                          f"S2 概念 {len(concepts)} 套",
                                          *list(meta or [])) if x])

    cover_style = ""
    cover_img_html = ""
    if cover:
        cover_img_html = (f'<img class="cover-img" src="{_h(cover["file"])}" '
                          f'alt="{_h(cover.get("title"))}">')
    else:
        cover_style = ' style="min-height:62vh"'

    page = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{_h(name)} · 概念方案</title>
<style>{CSS}</style></head>
<body>
<header class="cover"{cover_style}>
  {cover_img_html}
  <div class="cover-in">
    <div class="cover-top">OmniAiLab AI Architect　·　Concept Proposal　·　S2</div>
    <h1>{_h(name)}</h1>
    <p class="sub">{_h(meta_line or "设计提案")}</p>
    <div class="cover-meta">
      <div><b>{len(concepts)}</b>套组织逻辑不同的方案</div>
      <div><b>{n_figs}</b>张专业图解</div>
      <div><b>{n_cases}</b>个已核验案例</div>
      <div><b>{n_imgs}</b>张素材库参考图</div>
    </div>
  </div>
</header>

<div class="wrap">
{_cap("FIG.01", "封面 · 空间意象", "素材库参考图，非本项目效果图",
      (cover.get("source", "") + " · " + cover.get("title", "")) if cover else "") if cover else ""}
{LEGEND}

<div class="sec">
  <div class="sec-label">Overview</div>
  <h2 class="sec-title">三套方案，差在组织逻辑，不差在材料</h2>
  <div class="jumps">{jumps or '<p>本次未生成概念方案。</p>'}</div>
</div>

{body}

<div class="sec">
  <div class="sec-label">Sources &amp; Boundaries</div>
  <h2 class="sec-title">图从哪来，用到哪为止</h2>
  <blockquote>
  案例来自可公开访问的项目页面，标题与链接经过回读核验；案例照片的权利属原作者与摄影师，
  本提案不下载、不重新托管、不嵌入，页面上出现的案例图是本系统按公开文字绘制的手法示意。
  空间意象图取自自有素材库（Luxora AI），用于说明设计方向，<b>不是本项目的效果图</b>；
  正式效果图须在 G3 平面确认后依据平面生成。
  </blockquote>

<footer>
  <span class="sig"><b>OmniAiLab AI 建筑与室内设计总设计师</b></span>　·　本页由 S2 概念阶段产出，用于讨论设计方向。<br>
  结构安全、消防、无障碍、机电负荷与当地法规符合性不在本系统结论范围，须由持证专业人员在项目所在地复核签署；
  方案深度成果不得直接作为施工图；生成式图像与素材库参考图均不得作为尺寸依据。<br>
  © OmniAiLab ｜ 开发者：Mochiball ｜ omniailabx.com — 未经授权禁止复制、传播或二次分发。
</footer>
</div>
</body></html>"""

    path = out / filename
    path.write_text(page, encoding="utf-8")
    return path


__all__ = ["FAMILY_CN", "FIGURE_ORDER", "KIND_CN", "case_card", "concept_section",
           "proposal", "LEAD_WORDS"]
