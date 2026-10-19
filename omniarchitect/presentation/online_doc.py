"""在线文档交付包：把项目的 Markdown、图解、案例与修订记录装成可导入的一包。

客户要的不是"再发一份 PDF"，而是一个能持续更新的地方：需求怎么变的、看过哪些
案例、方案怎么来的、后面 S3–S8 做到哪了。飞书与 Notion 都吃 Markdown，所以
不需要为两家各写一套排版，只要按各自习惯组织目录与图片引用。

两条边界写在这里，而不是靠调用方自觉：

1. **没有授权连接就不创建任何线上文档。** `publish()` 在没有客户端时只返回
   `not_connected` 并说明原因，绝不返回一个编出来的链接。包本身是可交付的成品：
   客户自己导入，或在拿到授权后再发。
2. **客户资料默认不公开。** 包里每份文档都带一句"默认不公开"，`manifest.json`
   记录隐私状态；分享永远是单独的一步，不在构建时顺手做掉。

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from ..research import preview as pv
from .html import FAMILY_CN
from ..stages import STAGES

#: 两家载体的差异只在目录习惯与图片引用，不在内容。
CARRIERS: Dict[str, Dict[str, str]] = {
    "feishu": {
        "label": "飞书",
        "index": "00-项目总览",
        "note": "飞书 导入 Markdown 时会按标题层级建目录；图片若未带入，"
                "从 assets/ 拖入对应小节即可。",
        "env": "FEISHU_APP_ID / FEISHU_APP_SECRET",
    },
    "notion": {
        "label": "Notion",
        "index": "00 Project Home",
        "note": "Notion 导入 Markdown 时把每个文件建成子页面；建议整包（zip）导入，"
                "图片会随 assets/ 一起上传。",
        "env": "NOTION_TOKEN",
    },
}

#: 一个项目空间的五章。顺序就是客户阅读顺序。
PAGES: Tuple[Tuple[str, str, str], ...] = (
    ("01-brief", "01 客户需求与任务书", "需求怎么来的、确认了什么、还有什么没定"),
    ("02-references", "02 案例参考与意向图", "看过哪些真实案例、借的是什么手法、图从哪来"),
    ("03-concepts", "03 概念方案", "每套方案的组织逻辑、图解与代价"),
    ("04-stages", "04 设计进展（S3–S8 为后续）", "每一阶段做到哪、产生什么文件"),
    ("05-changes", "05 修改记录", "什么时候改了什么、为什么改"),
)

STAGE_STATE_CN = {
    "confirmed": "已确认", "pending": "未开始", "in_progress": "进行中",
    "rework": "返工中", "blocked": "受阻", "skipped": "跳过",
}

PRIVACY = ("客户资料默认不公开。本文档包仅供本项目业主与授权团队使用，"
           "对外分享须由业主明确授权后再单独操作。")


# --------------------------------------------------------------------------
# 读已有产物
# --------------------------------------------------------------------------
def _first(root: Optional[Path], pattern: str) -> Optional[Path]:
    if not root:
        return None
    hits = sorted(Path(root).rglob(pattern))
    return hits[0] if hits else None


def _read(path: Optional[Path]) -> str:
    return path.read_text(encoding="utf-8") if path and path.exists() else ""


def _slug(text: str, limit: int = 48) -> str:
    """文件名片段。保留中文：把中文名压成哈希后，客户拿到的是 `435a2cee.zip`。"""
    s = re.sub(r"[^\w\-]+", "-", str(text).lower(), flags=re.UNICODE).strip("-")
    s = re.sub(r"-{2,}", "-", s)
    return (s or hashlib.md5(str(text).encode("utf-8")).hexdigest()[:8])[:limit].strip("-")


def _copy_asset(src: Path, assets: Path) -> str:
    assets.mkdir(parents=True, exist_ok=True)
    target = assets / src.name
    if src.resolve() != target.resolve():
        shutil.copyfile(src, target)
    return f"assets/{target.name}"


# --------------------------------------------------------------------------
# 各章内容
# --------------------------------------------------------------------------
def _page_brief(run: Optional[Path], project: Any) -> str:
    brief = _read(_first(run, "design-brief.md"))
    out = ["# 01 客户需求与设计任务书", "", f"> {PRIVACY}", ""]
    if brief:
        body = re.sub(r"^# .*$", "", brief, count=1, flags=re.M).strip()
        out += [body, ""]
    else:
        cons = getattr(project, "constraints", {}) or {}
        out += ["## 已知条件", ""]
        out += [f"- {k}：{v}" for k, v in cons.items()] or ["- 尚未登记项目条件"]
        out += [""]
    need = _read(_first(run, "user-needs.json"))
    if need:
        try:
            data = json.loads(need)
        except ValueError:
            data = None
        if isinstance(data, dict) and data.get("needs"):
            out += ["## 已登记的使用需求", ""]
            for n in data["needs"][:12]:
                out.append(f"- {n.get('name') or n}")
            out.append("")
    return "\n".join(out)


def _case_rows(research: Optional[Dict[str, Any]],
               project_dir: Optional[Path],
               assets: Path) -> Tuple[str, List[Dict[str, Any]]]:
    """案例章节：每个案例一张手法图 + 来源 + 可借鉴手法。"""
    cases = list((research or {}).get("cases") or [])
    if not cases:
        return ("## 案例参考\n\n本次检索没有得到可核验案例，因此不提供案例图片，"
                "也不编造案例。\n"), []
    out = ["## 案例参考（共 {} 个，均可点开来源页面）".format(len(cases)), ""]
    sources: List[Dict[str, Any]] = []
    for i, c in enumerate(cases, 1):
        vis = pv.resolve(c, project_dir=project_dir, index=i)
        title = str(c.get("title") or f"案例 {i}")
        out += [f"### {i:02d}. [{title}]({c.get('url')})", ""]
        if vis["kind"] == "licensed_photo":
            rel = _copy_asset(Path(vis["image"]), assets)
            out += [f"![{title}]({rel})", "", f"*{vis['credit']}*", ""]
        else:
            # SVG 存盘后再引用：内联 SVG 在 Markdown 里会被当成文本。
            svg_path = assets / f"case-{i:02d}-{_slug(title, 30)}.svg"
            svg_path.parent.mkdir(parents=True, exist_ok=True)
            svg_path.write_text(vis["svg"], encoding="utf-8")
            out += [f"![{title} 手法示意]({_copy_asset(svg_path, assets)})", "",
                    f"*{vis['credit']}*", ""]

        place = "、".join([x for x in (c.get("city"), c.get("country")) if x])
        meta = "　·　".join([x for x in (c.get("architect"), place,
                                         c.get("year"), c.get("area")) if x])
        if meta:
            out += [meta, ""]
        tech = vis.get("techniques") or []
        if tech:
            def _one(t: Dict[str, Any]) -> str:
                kind = pv.KIND_LABEL.get(t["kind"], "")
                return t["label"] if not kind or kind == t["label"] else f"{t['label']}（{kind}）"
            out += ["- 可借鉴手法：" + "、".join(_one(t) for t in tech)]
        else:
            out += ["- 可借鉴手法：案例公开描述里没有可提炼的空间手法，只作方向参考"]
        out += ["- 来源：" + str(c.get("url")),
                "- 核验：" + str(c.get("verify_label") or c.get("verify")), ""]

        sources.append({"title": title, "url": c.get("url"),
                        "architect": c.get("architect"),
                        "verify": c.get("verify"),
                        "rights": "third_party_link_only",
                        "image_shown": vis["kind"]})

    out += ["## 图片使用规则", "",
            "- 案例照片的权利属原作者与摄影师：本文档只放来源链接，不嵌入第三方照片。",
            "- 出现的图是本系统按案例公开文字绘制的手法示意，**不是原案例照片**。",
            "- 需要原创设计意向图时使用 OmniAiLab 原生画布生成，并标注为「原创意向」；"
            "本次未配置画布，因此没有生成任何意向图。", ""]
    return "\n".join(out), sources


def _page_references(research: Optional[Dict[str, Any]],
                     project_dir: Optional[Path], assets: Path) -> Tuple[str, List[Dict[str, Any]]]:
    body, sources = _case_rows(research, project_dir, assets)
    head = ["# 02 案例参考与意向图", "", f"> {PRIVACY}", ""]
    return "\n".join(head) + "\n" + body, sources


def _page_concepts(run: Optional[Path], payload: Dict[str, Any],
                   assets: Path) -> str:
    md = _read(_first(run, "concept-options.md"))
    out = ["# 03 概念方案", "", f"> {PRIVACY}", ""]
    concepts = payload.get("concepts") or []
    if not concepts:
        return "\n".join(out + ["本次未生成概念方案。", ""])

    out += ["## 三套方案一览", "",
            "| 方案 | 组织逻辑 | 空间家族 | 图解 | 案例 |", "|---|---|---|---|---|"]
    for c in concepts:
        d = c.get("deliberation") or {}
        out.append("| {name}（{role}） | {parti} | {fam} | {figs} 张 | {cases} 个 |".format(
            name=c.get("concept_name"), role=c.get("role_label") or "",
            parti=(d.get("parti") or c.get("design_strategy") or "—")[:46],
            fam=FAMILY_CN.get(str((c.get("spatial_prototype") or {}).get("family")), "—"),
            figs=len(c.get("diagrams") or []),
            cases=len((c.get("references") or {}).get("cases") or [])))
    out.append("")

    # 图解紧跟各自方案：先看图，再读文字
    for c in concepts:
        cid = str(c.get("concept_id") or "")
        figs = [d for d in (c.get("diagrams") or []) if Path(str(d.get("path"))).exists()]
        if not figs:
            continue
        out += [f"## 图解 · {c.get('concept_name')}", ""]
        for d in figs:
            src = Path(str(d.get("path")))
            rel = _copy_asset(src, assets)
            label = {"massing": "体量概念图", "section": "剖面与楼层图",
                     "landscape": "景观结构图", "sequence": "空间序列图",
                     "zoning": "分区图", "circulation": "动线概念图",
                     "daylight": "采光策略图", "functional": "功能关系图"}.get(
                         str(d.get("kind")), str(d.get("kind")))
            out += [f"![{c.get('concept_name')} · {label}]({rel})", "",
                    f"*{label}：本系统确定性绘制，关系示意，非按比例*", ""]
    if md:
        out += ["---", "", md.strip(), ""]
    return "\n".join(out)


def _page_stages(project: Any, run: Optional[Path]) -> str:
    state = (getattr(project, "meta", {}) or {}).get("stage_state") or {}
    out = ["# 04 设计进展（S3–S8 为后续）", "", f"> {PRIVACY}", "",
           "只列真实发生的状态；没有开始的阶段写「未开始」，不预告成果。", "",
           "| 阶段 | 名称 | 状态 | 门禁 | 产物 |", "|---|---|---|---|---|"]
    for s in STAGES:
        st = state.get(s.id) or {}
        status = STAGE_STATE_CN.get(str(st.get("status") or "pending"), "未开始")
        # 产物目录按阶段序号命名（02-concept），不是按 "s2"：用阶段号取，
        # 否则每一行都显示"—"，看的人会以为系统什么都没产。
        try:
            num = int(s.id[1:])
        except ValueError:
            num = 0
        made = len(list(Path(run).glob(f"{num:02d}-*"))) if run else 0
        # 产出了但还没过门禁，写"未开始"会与上面的产物目录自相矛盾。
        if status == "未开始" and made:
            status = "已产出 · 待业主确认"
        out.append(f"| {s.id} | {s.name} | {status} | {s.gate.id} {s.gate.label} | "
                   f"{'有' if made else '—'} |")
    out += ["", "## 当前可交付内容", ""]
    key_ext = (".md", ".pptx", ".html", ".json")
    files = (sorted(p.name for p in Path(run).rglob("*") if p.suffix in key_ext)
             if run else [])
    if files:
        out += [f"- {name}" for name in files[:20]]
        extra = len(files) - 20
        if extra > 0:
            out.append(f"- 另有 {extra} 个同目录文件")
    else:
        out.append("- 暂无")
    out.append("")
    return "\n".join(out)


def _page_changes(project: Any) -> str:
    log = getattr(project, "change_log", None) or (
        getattr(project, "meta", {}) or {}).get("change_log") or []
    out = ["# 05 修改记录", "", f"> {PRIVACY}", ""]
    if not log:
        out += ["本版为初始概念版（revision {}），尚无变更记录。".format(
            getattr(project, "revision", 1)), "",
            "后续任何修改都会在此登记：改了什么、为什么改、影响了哪些下游成果。", ""]
        return "\n".join(out)
    out += ["| 时间 | 阶段 | 内容 | 原因 |", "|---|---|---|---|"]
    for item in log[-40:]:
        if not isinstance(item, dict):
            out.append(f"| — | — | {item} | — |")
            continue
        out.append("| {t} | {s} | {w} | {r} |".format(
            t=str(item.get("at") or item.get("time") or "—")[:16],
            s=item.get("stage") or "—",
            w=str(item.get("summary") or item.get("what") or "—")[:60],
            r=str(item.get("reason") or item.get("why") or "—")[:40]))
    out.append("")
    return "\n".join(out)


# --------------------------------------------------------------------------
# 组装
# --------------------------------------------------------------------------
def _index_md(carrier: str, project_name: str, payload: Dict[str, Any],
              pages: Sequence[Tuple[str, str, str]]) -> str:
    cfg = CARRIERS[carrier]
    out = [f"# {project_name}", "",
           f"> OmniAiLab AI Architect　·　概念方案与设计过程文档　·　{cfg['label']}", "",
           f"> {PRIVACY}", "",
           "## 这个空间里有什么", ""]
    for _, title, desc in pages:
        out.append(f"- **{title}** — {desc}")
    out += ["", "## 三套方案", ""]
    for c in payload.get("concepts") or []:
        out.append(f"- {c.get('concept_name')}（{c.get('role_label') or ''}）")
    out += ["", "## 怎么更新这一包", "",
            "重跑一次 S2/S3 后重新生成本文档包，覆盖同名文件即可；"
            "线上文档按同名页面更新，不新建重复页面。", "",
            "## 边界", "",
            "- 结构安全、消防、无障碍、机电负荷与当地法规符合性不在本系统结论范围。",
            "- 案例图为手法示意或已授权图片，均标注来源；不冒充原案例照片。",
            "- 生成式图像不得作为尺寸依据。", ""]
    return "\n".join(out)


def build_package(project: Any, payload: Dict[str, Any],
                  research: Optional[Dict[str, Any]],
                  out_dir: str | Path, *, project_name: str = "",
                  project_dir: Optional[str | Path] = None,
                  run_dir: Optional[str | Path] = None,
                  carriers: Sequence[str] = ("feishu", "notion")) -> Dict[str, Any]:
    """生成可导入的文档包。不创建线上文档，不发任何网络请求。"""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    run = Path(run_dir) if run_dir else None
    pdir = Path(project_dir) if project_dir else None
    name = project_name or str(payload.get("project_id") or "设计项目")
    generated = datetime.now().strftime("%Y-%m-%d %H:%M")

    result: Dict[str, Any] = {"carriers": {}, "files": [], "generated_at": generated,
                              "zip": "", "published": {}}
    from . import html as _html

    for carrier in carriers:
        if carrier not in CARRIERS:
            continue
        root = out / carrier
        root.mkdir(parents=True, exist_ok=True)
        assets = root / "assets"
        assets.mkdir(parents=True, exist_ok=True)

        refs_md, sources = _page_references(research, pdir, assets)
        pages = [
            (PAGES[0][0], PAGES[0][1], _page_brief(run, project)),
            (PAGES[1][0], PAGES[1][1], refs_md),
            (PAGES[2][0], PAGES[2][1], _page_concepts(run, payload, assets)),
            (PAGES[3][0], PAGES[3][1], _page_stages(project, run)),
            (PAGES[4][0], PAGES[4][1], _page_changes(project)),
        ]

        written: List[str] = []
        for slug, title, body in pages:
            p = root / f"{slug}.md"
            p.write_text(body, encoding="utf-8")
            written.append(p.name)

        idx = root / "00-index.md"
        idx.write_text(_index_md(carrier, name, payload,
                                 [(s, t, d) for s, t, d in PAGES]), encoding="utf-8")
        written.insert(0, idx.name)

        # 整页 HTML 提案作为附件：导入器不吃 SVG 时，客户仍有一个能看的版本
        proposal = _html.proposal(payload, assets, project_name=name,
                                  research=research, project_dir=pdir,
                                  filename="proposal.html")
        written.append(f"assets/{proposal.name}")

        manifest = {
            "project": name,
            "carrier": carrier,
            "carrier_label": CARRIERS[carrier]["label"],
            "generated_at": generated,
            "revision": payload.get("revision", 1),
            "pages": written,
            "sources": sources,
            "assets": sorted(p.name for p in assets.iterdir() if p.is_file()),
            "privacy": PRIVACY,
            "publish": {"status": "not_connected", "url": None},
        }
        (root / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

        readme = root / "导入说明.md"
        readme.write_text(
            f"# 导入说明（{CARRIERS[carrier]['label']}）\n\n"
            f"{CARRIERS[carrier]['note']}\n\n"
            "## 步骤\n\n"
            f"1. 打开 {CARRIERS[carrier]['label']}，新建一个文档空间，命名与项目一致。\n"
            "2. 按 00 → 05 的顺序导入 Markdown 文件（或用同目录的 zip 整包导入）。\n"
            "3. 检查图片：若某张图未显示，从 `assets/` 拖入对应小节。\n"
            "4. `assets/proposal.html` 是整页提案，可直接发给客户用浏览器打开。\n\n"
            "## 边界\n\n"
            f"- {PRIVACY}\n"
            "- 未配置已授权连接时，本包不会被自动上传；本目录里的链接只有来源页面，"
            "没有任何伪造的在线文档地址。\n", encoding="utf-8")

        zip_path = out / f"{_slug(name, 30)}-{carrier}.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
            for p in sorted(root.rglob("*")):
                if p.is_file():
                    z.write(p, p.relative_to(root).as_posix())

        result["carriers"][carrier] = {
            "label": CARRIERS[carrier]["label"],
            "root": str(root),
            "pages": len(pages) + 1,
            "assets": len(manifest["assets"]),
            "zip": str(zip_path),
            "manifest": str(root / "manifest.json"),
        }
        result["files"].append(zip_path.name)

    return result


# --------------------------------------------------------------------------
# 发布：没有授权连接就不发
# --------------------------------------------------------------------------
def publish(carrier: str, package_root: str | Path, *,
            client: Any = None, title: str = "") -> Dict[str, Any]:
    """把文档包写入线上空间。**只有拿到已授权的客户端才会真的写。**

    `client` 需要一个方法：`create(title, pages=[(name, markdown, assets_dir)])`
    返回 `{"url": ...}`。仓库里不带任何飞书/Notion 凭证，所以默认走到第一个
    分支：明确说"没有连接"，而不是返回一个看起来像链接的字符串。
    """
    root = Path(package_root)
    if carrier not in CARRIERS:
        return {"status": "unsupported_carrier", "carrier": carrier, "url": None}
    if client is None:
        return {
            "status": "not_connected",
            "carrier": carrier,
            "carrier_label": CARRIERS[carrier]["label"],
            "url": None,
            "reason": ("没有已授权的{}连接（需要的凭证：{}）。"
                       "文档包已生成，可由客户自行导入；本地不会创建任何线上文档。"
                       ).format(CARRIERS[carrier]["label"], CARRIERS[carrier]["env"]),
            "package": str(root),
        }

    pages = []
    for p in sorted(root.glob("[0-9][0-9]-*.md")):
        pages.append((p.stem, p.read_text(encoding="utf-8"), root / "assets"))
    if not pages:
        return {"status": "empty_package", "carrier": carrier, "url": None,
                "reason": "文档包里没有页面，先运行 build_package()。"}

    try:
        res = client.create(title=title or root.name, pages=pages)
    except Exception as exc:                        # 网络/权限错误照实说
        return {"status": "failed", "carrier": carrier, "url": None,
                "reason": f"{type(exc).__name__}: {exc}"}
    url = str((res or {}).get("url") or "")
    if not url:
        return {"status": "failed", "carrier": carrier, "url": None,
                "reason": "客户端没有返回文档地址，视为未发布。"}
    record = {"status": "published", "carrier": carrier, "url": url,
              "published_at": datetime.now().strftime("%Y-%m-%d %H:%M")}
    (root / "published.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    return record


__all__ = ["CARRIERS", "PAGES", "PRIVACY", "build_package", "publish"]
