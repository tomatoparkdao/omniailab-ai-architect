"""概念演示动画：讲清这套方案是怎么成立的。

动画不是"每个项目配一段视频"。它只在**真有演变逻辑**时出现：

* 建筑：场地限界 → 体量分解 → 加入要素 → 结果形态；
* 室内：功能重组 → 空间序列 → 界面与通透 → 核心空间；
* 景观：场地与边界 → 空间层次 → 园路与节点 → 水景与种植。

步骤由 `concept/evolution.py` 从本项目的概念数据推出来（分区、序列、采光、
主张）。推不出来时 `plan()` 会说缺什么，这里返回 ``skipped``——调用方出
**静态分析图**，不拿不相干的建筑体块动画凑数。v1.14 就是四步固定体块：
酒店室内被演成体块生成，私家庭院被演成建筑加法，客户一眼看出不是他的项目。

产物是 `concept-motion.html`：单文件、离线可播、可暂停/重播/逐帧，每一帧都是
自有矢量图（`concept/iso.py`），不是生成式图像，也不冒充效果图。

不接第三方视频平台、不发起付费生成任务。需要生成式氛围短片时，仍走
`providers/canvas.py` 的授权链路。

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from . import evolution as evo

FILE = "concept-motion.html"


def build(project: Any = None, concept: Optional[Dict[str, Any]] = None, *,
          out_dir: str | Path = ".", title: str = "",
          steps: Optional[Sequence[Dict[str, Any]]] = None,
          theme: Optional[Dict[str, str]] = None,
          discipline: str = "") -> Dict[str, Any]:
    """Write the standalone animation, or say why this project gets none.

    返回 ``{"path": "", "skipped": 原因}`` 是正常结果：没有演变逻辑时，
    少一个动画比多一个错的专业推演好。
    """
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    disc = discipline or _discipline_of(concept)
    pal = evo._pal(theme)                          # noqa: SLF001  同一套配色

    if steps is None:
        if not concept:
            return {"path": "", "steps": 0, "skipped": "没有概念数据，不出动画"}
        plan = evo.plan(concept, disc)
        if not plan.ok:
            return {"path": "", "steps": 0, "skipped": plan.reason}
        images = evo.scenes(concept, disc, width=720, height=500, theme=theme)
        items = [{"n": s.n, "name": s.name, "note": s.note} for s in plan.steps]
        lead = (list(plan.labels) or [""])[0]
    else:
        images = [str(s.get("svg") or "") for s in steps]
        items = [{"n": s.get("n", ""), "name": s.get("name", ""),
                  "note": s.get("note", "")} for s in steps]
        lead = ""

    if not images:
        return {"path": "", "steps": 0, "skipped": "没有可画的步骤"}

    name = (title or getattr(project, "name", "") or "概念演示").strip()
    cid = str((concept or {}).get("concept_id") or "")
    cname = str((concept or {}).get("concept_name") or "")
    statement = str((concept or {}).get("concept_statement") or lead or
                    "方案不是造型，是被场地、使用与光线一步步逼出来的结果。")

    frames = "".join(
        f'<figure class="scene{" on" if i == 0 else ""}" data-i="{i}">{img}'
        f'<figcaption><b>{s["n"]}</b><span>{s["name"]}</span></figcaption></figure>'
        for i, (s, img) in enumerate(zip(items, images)))
    caps = "".join(
        f'<div class="cap{" on" if i == 0 else ""}" data-i="{i}">'
        f'<em>{s["n"]}</em><h3>{s["name"]}</h3><p>{s["note"]}</p></div>'
        for i, s in enumerate(items))
    dots = "".join(f'<button class="dot{" on" if i == 0 else ""}" data-go="{i}" '
                   f'aria-label="{s["n"]}"></button>' for i, s in enumerate(items))
    kicker = {"architecture": "MASSING · 体量与形态",
              "interior": "SEQUENCE · 功能与序列",
              "landscape": "SITE · 场地与游线"}.get(disc, "CONCEPT · 概念推演")

    html = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{name} · 概念推演</title>
<style>
:root{{--paper:{pal["paper"]};--ink:{pal["ink"]};--line:{pal["line"]};
--accent:{pal["accent"]};--muted:{pal["muted"]};
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
<header><div class="k">{kicker}</div>
<div class="p">{name}　{cid} {cname}</div></header>
<div class="scenes">{frames}</div>
<aside><div class="t">{cname or "概念推演"}</div>
<div class="l">{statement}</div>
<div class="cap-wrap">{caps}</div>
</aside>
<footer><div class="dots">{dots}</div>
<button class="play" id="play">暂停</button>
<span class="n">自有矢量图解 · 空间关系示意，不作尺寸依据</span></footer>
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
    t=setInterval(tick,3000);}}
  function stop(){{if(t)clearInterval(t);t=null;}}
  document.getElementById('play').onclick=()=>{{
    if(playing){{stop();playing=false;
      document.getElementById('play').textContent='播放';}}
    else{{start();}}
  }};
  dots.forEach(d=>d.onclick=()=>{{show(+d.dataset.go);
    if(playing){{stop();t=setInterval(tick,3000);}}}});
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
    return {"path": str(path), "steps": len(items), "name": name,
            "discipline": disc, "skipped": ""}


def _discipline_of(concept: Optional[Dict[str, Any]]) -> str:
    proto = (concept or {}).get("spatial_prototype") or {}
    disc = str(proto.get("profile") or "").strip()
    if disc in evo.DISCIPLINE_STEPS:
        return disc
    for d in (concept or {}).get("disciplines") or ():
        key = str((d or {}).get("id") if isinstance(d, dict) else d)
        if key in evo.DISCIPLINE_STEPS:
            return key
    return "architecture"


__all__ = ["FILE", "build"]
