"""概念演示动画：先让客户看懂体块怎么长出来的。

概念阶段不一定需要"视频"。真正有用的是一个**能在浏览器里播放**的演示：
体块从占满退界，到断开、切缺口、连桥与入口，四步走完，讲清设计的必然性。

产物是 `concept-motion.html`：单文件、离线可播、可暂停/重播/逐帧，
每一帧都是**自有矢量图**（`concept/iso.py`），不是生成式图像，所以不存在
"伪造效果图"的问题；反过来，它也不是效果图，页脚会写明"体块关系示意"。

不接第三方视频平台、不发起付费生成任务：平台未配置时，本模块照样交付
一个真能播的动画；需要生成式氛围短片时，仍走 `providers/canvas.py` 的授权链路。

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from . import iso as iso_mod
from .iso import Iso, draw_box, draw_ground, draw_shadow, tree

FILE = "concept-motion.html"

#: 四步体块推演（单位 m）。每一步只改一件事，客户才看得懂因果。
STEPS: Tuple[Dict[str, Any], ...] = (
    {"n": "01", "name": "占满可建范围", "note": "先按退界与限高做满，确认最大可建体量",
     "g": ["full"]},
    {"n": "02", "name": "断成两段", "note": "中间让出院子／中庭，进深从 32 m 收到 13 m",
     "g": ["bar_n", "bar_s", "court"]},
    {"n": "03", "name": "切出缺口", "note": "每段再切一口，主要房间都能有两面采光",
     "g": ["bar_n1", "bar_n2", "bar_s", "court"]},
    {"n": "04", "name": "连桥与入口", "note": "连桥把两段重新连起来，入口留出灰空间",
     "g": ["bar_n1", "bar_n2", "bar_s", "court", "bridge", "canopy", "trees", "people"]},
)


class _Canvas:
    """只画不排版的极简 SVG 画布，接口对齐 `diagrams.Svg`，好让 iso 直接用。"""

    def __init__(self) -> None:
        self.body: List[str] = []

    def polygon(self, pts: Sequence[Tuple[float, float]], *, fill: str = "none",
                stroke: str = "none", sw: float = 1.0, opacity: float = 1.0,
                dash: str = "") -> None:
        p = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.body.append(
            f'<polygon points="{p}" fill="{fill}" stroke="{stroke}" '
            f'stroke-width="{sw:.2f}" opacity="{opacity:.3f}"{d}/>')

    def line(self, x1: float, y1: float, x2: float, y2: float, *, stroke: str = "#999",
             sw: float = 1.0, opacity: float = 1.0, dash: str = "") -> None:
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.body.append(
            f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
            f'stroke="{stroke}" stroke-width="{sw:.2f}" opacity="{opacity:.3f}"{d}/>')

    def polyline(self, pts: Sequence[Tuple[float, float]], **kw: Any) -> None:
        self.polygon(pts, **kw)

    def circle(self, cx: float, cy: float, r: float, *, fill: str = "none",
               stroke: str = "none", sw: float = 1.0, opacity: float = 1.0) -> None:
        self.body.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" '
                         f'fill="{fill}" stroke="{stroke}" stroke-width="{sw:.2f}" '
                         f'opacity="{opacity:.3f}"/>')

    def ellipse(self, cx: float, cy: float, rx: float, ry: float, *, fill: str = "none",
                stroke: str = "none", sw: float = 1.0, opacity: float = 1.0) -> None:
        self.body.append(f'<ellipse cx="{cx:.1f}" cy="{cy:.1f}" rx="{rx:.1f}" '
                         f'ry="{ry:.1f}" fill="{fill}" stroke="{stroke}" '
                         f'stroke-width="{sw:.2f}" opacity="{opacity:.3f}"/>')

    def rect(self, x: float, y: float, w: float, h: float, *, fill: str = "none",
             stroke: str = "none", sw: float = 1.0, opacity: float = 1.0) -> None:
        self.body.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" '
                         f'fill="{fill}" stroke="{stroke}" stroke-width="{sw:.2f}" '
                         f'opacity="{opacity:.3f}"/>')

    def path(self, d: str, *, fill: str = "none", stroke: str = "none",
             sw: float = 1.0, opacity: float = 1.0) -> None:
        self.body.append(f'<path d="{d}" fill="{fill}" stroke="{stroke}" '
                         f'stroke-width="{sw:.2f}" opacity="{opacity:.3f}"/>')


#: 体块清单：名字 → (x, y, z, w, d, h)
BOXES: Dict[str, Tuple[float, float, float, float, float, float]] = {
    "full": (8, 4, 0, 40, 32, 10),
    "bar_n": (8, 4, 0, 40, 13, 10),
    "bar_s": (8, 23, 0, 40, 13, 10),
    "bar_n1": (8, 4, 0, 17, 13, 10),
    "bar_n2": (31, 4, 0, 17, 13, 10),
    "bridge": (16, 16, 6.0, 24, 8, 2.4),
    "canopy": (20, 17, 0, 16, 5, 3.4),
}


def _scene(names: Sequence[str], *, pal: Dict[str, str], w: int, h: int) -> str:
    c = _Canvas()
    iso = Iso(w * 0.50, h * 0.30, scale=min(w, h) / 44.0, z_scale=1.0)
    draw_ground(iso, c, 2, 0, 54, 40, fill=pal["ground"], edge=pal["line"], grid=0)  # type: ignore[arg-type]
    if "court" in names:
        c.polygon(iso.pts([(8, 17, 0.05), (48, 17, 0.05), (48, 23, 0.05), (8, 23, 0.05)]),
                  fill=pal["court"], stroke="none", sw=0)
    for name in names:
        box = BOXES.get(name)
        if box is None:
            continue
        x, y, z, bw, bd, bh = box
        if name in ("bridge",):
            continue
        if name != "canopy":
            draw_shadow(iso, c, x, y, bw, bd, opacity=0.10)  # type: ignore[arg-type]
        roof = name != "canopy"
        draw_box(iso, c, x, y, z, bw, bd, bh, fill=pal["mass"], edge=pal["ink"],  # type: ignore[arg-type]
                 sw=1.2, roof=roof)
    if "bridge" in names:
        x, y, z, bw, bd, bh = BOXES["bridge"]
        draw_box(iso, c, x, y, z, bw, bd, bh, fill=pal["mass2"], edge=pal["ink"],  # type: ignore[arg-type]
                 sw=1.1)
    if "trees" in names:
        for tx, ty in ((5, 2), (52, 6), (6, 37), (51, 36), (28, 20)):
            tree(iso, c, tx, ty, r=0.55, h=2.0, crown=pal["green"])  # type: ignore[arg-type]
    if "people" in names:
        for px, py in ((28, 37), (34, 36), (12, 15)):
            x1, y1 = iso.p(px, py, 0)
            c.circle(x1, y1, 2.2, fill=pal["ink"], opacity=0.85)
            c.line(x1, y1, x1, y1 - 8, stroke=pal["ink"], sw=1.6)
    body = "".join(c.body)
    return (f'<svg viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg" '
            f'preserveAspectRatio="xMidYMid meet">{body}</svg>')


def build(project: Any = None, concept: Optional[Dict[str, Any]] = None, *,
          out_dir: str | Path = ".", title: str = "",
          steps: Optional[Sequence[Dict[str, Any]]] = None,
          theme: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """Write the standalone animation. Always returns a path, even without a concept."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    pal = {"paper": "#FAF8F3", "ink": "#1E2328", "line": "#D6D2C6",
           "mass": "#E4EDE3", "mass2": "#C9DCC8", "ground": "#F2F0E8",
           "court": "#EFE3D2", "green": "#C6D6BE"}
    for k, v in (theme or {}).items():
        if k in pal and isinstance(v, str) and v.startswith("#"):
            pal[k] = v
    items = list(steps or STEPS)
    scenes = [_scene(s["g"], pal=pal, w=720, h=500) for s in items]
    name = (title or getattr(project, "name", "") or "概念演示").strip()
    cid = str((concept or {}).get("concept_id") or "")
    cname = str((concept or {}).get("concept_name") or "")
    lead = str((concept or {}).get("concept_statement") or
               "体块不是造型，是被场地、采光与流线一步步逼出来的结果。")

    frames = "".join(
        f'<figure class="scene{" on" if i == 0 else ""}" data-i="{i}">{scenes[i]}'
        f'<figcaption><b>{s["n"]}</b><span>{s["name"]}</span></figcaption></figure>'
        for i, s in enumerate(items))
    caps = "".join(
        f'<div class="cap{" on" if i == 0 else ""}" data-i="{i}">'
        f'<em>{s["n"]}</em><h3>{s["name"]}</h3><p>{s["note"]}</p></div>'
        for i, s in enumerate(items))
    dots = "".join(f'<button class="dot{" on" if i == 0 else ""}" data-go="{i}" '
                   f'aria-label="{s["n"]}"></button>' for i, s in enumerate(items))

    html = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{name} · 概念生成动画</title>
<style>
:root{{--paper:{pal["paper"]};--ink:{pal["ink"]};--line:{pal["line"]};
--accent:#2F5D45;--muted:#6E736A;
--sans:'PingFang SC','Noto Sans SC','Microsoft YaHei',sans-serif;
--serif:'Songti SC','Noto Serif SC','SimSun',serif}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:#161815;color:var(--ink);font-family:var(--sans);
display:flex;align-items:center;justify-content:center;min-height:100vh;padding:24px}}
.stage{{width:min(1280px,100%);background:var(--paper);border-radius:6px;
overflow:hidden;display:grid;grid-template-columns:1fr 380px;grid-template-rows:auto 1fr auto}}
header{{grid-column:1/-1;display:flex;justify-content:space-between;align-items:baseline;
padding:22px 34px 0}}
header .k{{font-size:11px;letter-spacing:.22em;color:var(--accent);font-weight:600}}
header .p{{font-size:11px;letter-spacing:.12em;color:var(--muted)}}
.scenes{{position:relative;height:520px}}
.scene{{position:absolute;inset:0;display:flex;flex-direction:column;justify-content:center;
opacity:0;transform:translateY(10px) scale(.985);
transition:opacity .7s ease,transform .7s ease;pointer-events:none}}
.scene.on{{opacity:1;transform:none}}
.scene svg{{width:100%;height:470px;display:block}}
.scene figcaption{{position:absolute;left:34px;bottom:8px;font-size:11px;
letter-spacing:.14em;color:var(--muted)}}
.scene figcaption b{{color:var(--accent);margin-right:10px}}
aside{{border-left:1px solid var(--line);padding:26px 32px;display:flex;
flex-direction:column;justify-content:center;gap:8px;position:relative}}
aside .t{{font-family:var(--serif);font-size:30px;line-height:1.28;margin-bottom:6px}}
aside .l{{font-size:13.5px;line-height:1.75;color:var(--muted);margin-bottom:16px}}
.cap{{position:absolute;left:32px;right:32px;bottom:26px;opacity:0;transition:opacity .5s}}
.cap.on{{opacity:1}}
.cap em{{font-style:normal;font-size:12px;color:var(--accent);font-weight:700;
letter-spacing:.1em}}
.cap h3{{font-family:var(--serif);font-size:20px;margin:4px 0 6px;font-weight:600}}
.cap p{{font-size:12.5px;line-height:1.7;color:var(--muted)}}
footer{{grid-column:1/-1;display:flex;align-items:center;gap:14px;padding:12px 34px;
border-top:1px solid var(--line)}}
.dots{{display:flex;gap:8px}}
.dot{{width:26px;height:3px;border:0;background:var(--line);cursor:pointer;padding:0}}
.dot.on{{background:var(--accent)}}
.play{{border:1px solid var(--line);background:none;color:var(--ink);border-radius:20px;
padding:4px 14px;font-size:11.5px;cursor:pointer;letter-spacing:.08em}}
footer .n{{margin-left:auto;font-size:10.5px;color:var(--muted);letter-spacing:.06em}}
@media(max-width:900px){{.stage{{grid-template-columns:1fr}}
aside{{border-left:0;border-top:1px solid var(--line)}}}}
</style></head>
<body><div class="stage">
<header><div class="k">MASS EVOLUTION · 概念生成</div>
<div class="p">{name}　{cid} {cname}</div></header>
<div class="scenes">{frames}</div>
<aside><div class="t">{cname or "体块推演"}</div>
<div class="l">{lead}</div>
<div class="cap-wrap">{caps}</div>
</aside>
<footer><div class="dots">{dots}</div>
<button class="play" id="play">暂停</button>
<span class="n">自有矢量图解 · 体块关系示意，不作尺寸依据</span></footer>
</div>
<script>
(function(){{
  const N={len(items)};
  const scenes=[...document.querySelectorAll('.scene')];
  const caps=[...document.querySelectorAll('.cap')];
  const dots=[...document.querySelectorAll('.dot')];
  let i=0,t=null,playing=true;
  function show(k){{
    i=(k+N)%N;
    scenes.forEach((s,j)=>s.classList.toggle('on',j===i));
    caps.forEach((c,j)=>c.classList.toggle('on',j===i));
    dots.forEach((d,j)=>d.classList.toggle('on',j===i));
  }}
  function tick(){{show(i+1);}}
  function start(){{stop();playing=true;document.getElementById('play').textContent='暂停';
    t=setInterval(tick,2600);}}
  function stop(){{if(t)clearInterval(t);t=null;}}
  document.getElementById('play').onclick=()=>{{
    if(playing){{stop();playing=false;
      document.getElementById('play').textContent='播放';}}
    else{{start();}}
  }};
  dots.forEach(d=>d.onclick=()=>{{show(+d.dataset.go);
    if(playing){{stop();t=setInterval(tick,2600);}}}});
  document.addEventListener('keydown',e=>{{
    if(e.key===' '){{
      e.preventDefault();
      document.getElementById('play').click();}}
    if(e.key==='ArrowRight')show(i+1);
    if(e.key==='ArrowLeft')show(i-1);
  }});
  show(0);
  start();
}})();
</script></body></html>"""
    path = out / FILE
    path.write_text(html, encoding="utf-8")
    return {"path": str(path), "steps": len(items), "name": name}


__all__ = ["FILE", "STEPS", "build"]
