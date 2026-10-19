"""项目级视觉规范：生成、读取、更新 `视觉.md`。

为什么是一个文件而不是一套新系统
--------------------------------
风格库回答"这套设计是什么风格"，`视觉.md` 回答"**这个项目的图，长什么样才算对**"。
前者是内容，后者是表达；两者不能互相替代，也不该各存一份。

所以这里只做三件事：

1. **compose** —— 把客户原话、参考文件的客观指标、专业默认值按优先级合并；
2. **render / load** —— 写成一份人可读的 Markdown，其中第 0 节是一个 fenced JSON
   块，程序直接从这里读规则。单一文件，人机双读，不会漂移；
3. **theme** —— 把规则压成渲染层要的几个量（纸色、墨色、线宽、留白、是否衬线）。

`theme()` 在文件不存在时返回与当前实现一致的默认值。**没有 `视觉.md` 的项目，
产出的版面与上一版逐像素一致**——加这套能力不允许让原有审美下降。

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from ..paths import PROJECTS, REFERENCE_LIBRARY_URL
from . import extract as ex
from . import sources as src

FILENAME = "视觉.md"
BLOCK_START = "```json visual-rules"
BLOCK_END = "```"
SCHEMA = 1

ORIGIN_CN = {"client": "客户明确指定", "reference": "参考文件提取",
             "pro": "总设计师专业建议"}

#: 不同专业对"图"的默认要求。客户没提时按这个走，客户提了按客户的。
DISCIPLINE_NOTES: Dict[str, Dict[str, str]] = {
    "architecture": {
        "massing": "体量用等距轴测、分档明暗与投影；演变按「做满 → 减去 → 加入场地」三步或四步",
        "section": "剖面用实心剖切面，楼板有厚度，院井通高可读，必须有 1.7 m 人体尺度",
        "plan": "总平面区分建筑轮廓、硬质、绿地、水景、路径；不放线、不标尺寸",
    },
    "interior": {
        "axon": "室内用剖切轴测：切掉靠近观察者的两面墙，家具、光斑、视线同框",
        "material": "材料以实拍质感呈现，不用色块代替；每块写清用在哪",
        "light": "光要有方向与色温，同一批图共用一套光照假设",
    },
    "landscape": {
        "plan": "总平面分层：底（草）→ 建筑与铺装（硬）→ 水（软而深）→ 种植（三种冠幅）→ 路径（双线）→ 标注与指北",
        "planting": "植物按冠幅与疏密分级，不用等大圆点；水岸有过渡种植",
        "path": "园路绕行不穿水，宽度按使用强度分级",
    },
}


# --------------------------------------------------------------------------
# 路径
# --------------------------------------------------------------------------
def path_for(project: Any, project_dir: str | Path | None = None) -> Path:
    if project_dir:
        return Path(project_dir) / FILENAME
    pid = str(getattr(project, "project_id", "") or "")
    return PROJECTS / (pid or "_unknown") / FILENAME


def exists(project: Any, project_dir: str | Path | None = None) -> bool:
    return path_for(project, project_dir).exists()


# --------------------------------------------------------------------------
# 生成
# --------------------------------------------------------------------------
def _disciplines(project: Any, lead: str) -> List[str]:
    out: List[str] = []
    try:
        from .. import disciplines as disc

        scope = disc.ensure(project)
        out = [d for d in scope.active() if d in ("architecture", "interior", "landscape")]
    except Exception:                              # noqa: BLE001
        out = []
    if lead and lead not in out:
        out.insert(0, lead)
    return out or ([lead] if lead else [])


def compose(project: Any, refs: Sequence[Dict[str, Any]], *,
            client_text: str = "", lead: str = "",
            style_labels: Sequence[str] = ()) -> Dict[str, Any]:
    """按优先级合并：客户原话 > 参考文件 > 专业默认。"""
    text_layer = ex.from_text(client_text, origin="client") if client_text else {}
    readable = [r for r in refs if r.get("ok")]
    images = [r for r in readable if r.get("kind") == "image"]
    docs = [r for r in readable if r.get("kind") in ("text", "pdf", "pptx", "docx", "link")]

    doc_layers = []
    for d in docs:
        layer = ex.from_text(str(d.get("text") or ""), origin="reference")
        if layer["layout"] or layer["banned"] or layer["colours"]:
            doc_layers.append(layer)
    image_layer = ex.from_images([r for r in images], origin="reference")

    layers = [x for x in (text_layer, *doc_layers, image_layer) if x]
    merged = ex.merge(layers) if layers else ex.merge([{}])

    tokens = merged["tokens"]
    # 颜色词优先于图像主色：客户说"暖白"比从图上算出来的灰更准
    for word, hexv in merged["colours"].items():
        key = ("paper" if word in ("暖白", "米白", "象牙", "纸白", "奶白", "米色", "浅米")
               else "ink" if word in ("石墨", "炭黑", "墨黑", "纯黑", "深灰") else "accent")
        tokens[key] = hexv
        merged["provenance"][key] = "client"

    return {
        "schema": SCHEMA,
        "project_id": str(getattr(project, "project_id", "") or ""),
        "project_name": str(getattr(project, "name", "") or ""),
        "revision": int(getattr(project, "revision", 1) or 1),
        "version": 1,
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "lead": lead,
        "disciplines": _disciplines(project, lead),
        "style_labels": [str(x) for x in style_labels],
        "tokens": {k: tokens[k] for k in
                   ("paper", "ink", "muted", "line", "accent", "whitespace",
                    "contrast", "serif_titles", "columns", "image_ratio",
                    "line_weight", "numbered_captions", "image_dominant",
                    "full_bleed", "no_cards") if k in tokens},
        "provenance": merged["provenance"],
        "banned": merged["banned"],
        "notes": merged["notes"],
        "client_text": " ".join(str(client_text or "").split())[:600],
        "sources": [_source_summary(r) for r in refs],
        "changelog": [{"at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                       "by": "compose", "change": "首次生成"}],
    }


def _source_summary(r: Dict[str, Any]) -> Dict[str, Any]:
    item: Dict[str, Any] = {
        "name": r.get("name") or Path(str(r.get("path") or "")).name,
        "kind": r.get("kind") or "",
        "path": r.get("path") or "",
        "ok": bool(r.get("ok")),
        "reason": r.get("reason") or "",
    }
    if r.get("kind") == "image" and r.get("ok"):
        item["extracted"] = {
            "画幅": f'{r.get("width")}×{r.get("height")}（{r.get("ratio")}）',
            "纸色": r.get("paper"), "墨色": r.get("ink"),
            "点缀": r.get("accent"),
            "留白占比": r.get("whitespace"),
            "对比度": r.get("contrast"),
        }
    elif r.get("ok"):
        item["extracted"] = {
            "字符数": len(str(r.get("text") or "")),
            "页数": r.get("page_count") or r.get("slide_count") or "",
        }
    return item


# --------------------------------------------------------------------------
# 渲染
# --------------------------------------------------------------------------
def _prov(rules: Dict[str, Any], key: str) -> str:
    return ORIGIN_CN.get(str((rules.get("provenance") or {}).get(key) or "pro"),
                         "总设计师专业建议")


def _fmt(v: Any) -> str:
    if isinstance(v, bool):
        return "是" if v else "否"
    if isinstance(v, float):
        return f"{v:.2f}".rstrip("0").rstrip(".")
    return str(v)


def render(rules: Dict[str, Any]) -> str:
    t = rules.get("tokens") or {}
    prov = rules.get("provenance") or {}
    dis = [d for d in (rules.get("disciplines") or []) if d in DISCIPLINE_NOTES]
    payload = json.dumps(rules, ensure_ascii=False, indent=1)

    lines: List[str] = [
        f"# 视觉规范 · {rules.get('project_name') or rules.get('project_id') or '项目'}",
        "",
        "> 这份文件定义本项目所有图与版面的表达方式。所有交付物（图解、意向板、",
        "> 客户提案、PPTX、飞书与 Notion 文档）都从这里读规则，不各自定义风格。",
        "> 第 0 节是机读块，程序解析它；其余章节给人看。",
        "",
        "## 0 机读规则（程序读取，勿手改结构）",
        "",
        BLOCK_START,
        payload,
        BLOCK_END,
        "",
        "## 1 项目基本信息",
        "",
        "| 项 | 值 |",
        "|---|---|",
        f"| 项目 | {rules.get('project_name') or '—'} |",
        f"| 编号 | {rules.get('project_id') or '—'} |",
        f"| 模型修订 | r{rules.get('revision')} |",
        f"| 主导专业 | {rules.get('lead') or '未定'} |",
        f"| 适用专业 | {'、'.join(dis) or '—'} |",
        f"| 规范版本 | v{rules.get('version')}（{rules.get('updated_at')}） |",
        "",
        "## 2 客户审美诉求与禁止项",
        "",
        f"**客户原话**：{rules.get('client_text') or '（客户未提供文字表述）'}",
        "",
        "| 禁止项 | 来源 |",
        "|---|---|",
    ]
    banned = rules.get("banned") or []
    if banned:
        for b in banned:
            lines.append(f"| {b['text']} | {ORIGIN_CN.get(b.get('source'), b.get('source'))} |")
    else:
        lines.append("| 客户未提出明确禁止项 | — |")

    lines += ["", "## 3 参考文件清单", "",
              "| 文件 | 类型 | 可读 | 提取到 |", "|---|---|---|---|"]
    for s in rules.get("sources") or []:
        got = "、".join(f"{k} {v}" for k, v in (s.get("extracted") or {}).items()
                        if v not in (None, "", "None")) or ("—" if s.get("ok") else s.get("reason"))
        lines.append(f"| {s.get('name')} | {s.get('kind')} | "
                     f"{'是' if s.get('ok') else '否'} | {got} |")
    if not (rules.get("sources") or []):
        lines.append("| 客户未提供参考文件 | — | — | 按风格库与专业默认推进 |")

    lines += ["", "## 4 空间审美提取", ""]
    if any(s.get("kind") == "image" and s.get("ok") for s in rules.get("sources") or []):
        lines += ["| 指标 | 值 | 来源 |", "|---|---|---|",
                  f"| 纸色 | `{t.get('paper')}` | {_prov(rules, 'paper')} |",
                  f"| 墨色 | `{t.get('ink')}` | {_prov(rules, 'ink')} |",
                  f"| 点缀色 | `{t.get('accent')}` | {_prov(rules, 'accent')} |",
                  f"| 明暗关系 | 对比度 {_fmt(t.get('contrast'))} | {_prov(rules, 'contrast')} |"]
    else:
        lines.append("参考文件不含图像，**不推断空间色彩**；配色按风格库与本项目材料方向执行。")

    lines += ["", "## 5 排版规则提取", "",
              "| 规则 | 值 | 来源 |", "|---|---|---|",
              f"| 留白占比 | {_fmt(t.get('whitespace'))} | {_prov(rules, 'whitespace')} |",
              f"| 图幅比例 | {t.get('image_ratio')} | {_prov(rules, 'image_ratio')} |",
              f"| 标题字族 | {'衬线' if t.get('serif_titles') else '无衬线'} | {_prov(rules, 'serif_titles')} |",
              f"| 栅格列数 | {t.get('columns')} | {_prov(rules, 'columns')} |",
              f"| 线宽系数 | {_fmt(t.get('line_weight'))} | {_prov(rules, 'line_weight')} |",
              f"| 图注编号 | {'启用' if t.get('numbered_captions') else '不用'} | {_prov(rules, 'numbered_captions')} |",
              f"| 图占主导 | {'是' if t.get('image_dominant') else '否'} | {_prov(rules, 'image_dominant')} |",
              f"| 满幅图 | {'允许' if t.get('full_bleed') else '不用'} | {_prov(rules, 'full_bleed')} |"]

    lines += ["", "## 6 风格、色彩、字体与材质", "",
              f"**风格方向**：{'、'.join(rules.get('style_labels') or []) or '按 S2 风格推荐执行'}",
              "",
              "| 色彩角色 | 色值 | 用途 |", "|---|---|---|",
              f"| 纸 | `{t.get('paper')}` | 页面与图纸底 |",
              f"| 墨 | `{t.get('ink')}` | 标题与正文 |",
              f"| 次级 | `{t.get('muted')}` | 图注、说明、编号 |",
              f"| 线 | `{t.get('line')}` | 分隔线、图框 |",
              f"| 强调 | `{t.get('accent')}` | 编号、结论、少量标记 |",
              "",
              "强调色只用于**小面积**：编号、结论句、关键标记。大面积铺色视为违反本规范。",
              "",
              "## 7 分专业图解要求", "",
              "| 专业 | 图解 | 要求 |", "|---|---|---|"]
    for d in dis or ["architecture"]:
        for k, v in DISCIPLINE_NOTES.get(d, {}).items():
            lines.append(f"| {d} | {k} | {v} |")
    if not dis:
        lines.append("| — | — | 主导专业未定，按 S1 完成后补齐 |")

    lines += ["", "## 8 体块、轴测、剖面与分析图", "",
              "| 项 | 要求 |", "|---|---|",
              "| 体量 | 等距或 2:1 轴测，三面分档明暗，带投影；不用俯视矩形拼贴 |",
              "| 演变 | 至少三步，每步必须有可见差别（做满 → 减去 → 加入场地） |",
              "| 剖面 | 实心剖切面 + 楼板厚度 + 人体尺度；不含尺寸数字 |",
              "| 分析图 | 线宽统一，填充不超过三档明度；一图只回答一个问题 |",
              "| 标注 | 只标能指认的对象（房间名、活动名、材料名），不标推断值 |",
              "",
              "## 9 图片与效果图", "",
              "| 项 | 要求 |", "|---|---|",
              f"| 主图比例 | {t.get('image_ratio')} |",
              "| 摄影构图 | 主图留出文字区；不裁掉建筑主体；不用带水印的图 |",
              "| Moodboard | 色板取自风格库声明值，材料写清用在哪 |",
              "| 效果图 | 仅在 G3 平面确认后生成，标注机位与修订号 |",
              "| 禁止 | 生成图不得作为尺寸依据；素材图不得声称是本项目效果图 |",
              "",
              "## 10 各交付渠道的适配", "",
              "| 渠道 | 适配方式 |", "|---|---|",
              "| HTML 提案 | 直接使用本规范的色值与栅格；图注编号 FIG.xx |",
              "| PPTX | 沿用同一色值与标题层级，页面比例按 16:9 重排 |",
              "| 飞书 | 同上色值；图片按 1600px 宽导出，附件不压缩 |",
              "| Notion | 同上色值；表格不跨页，图注跟在图下 |",
              "",
              "各渠道只做**排版能力差异**的适配，不重新定义风格。",
              "",
              "## 11 视觉质量检查", "",
              "| 检查项 | 判据 |", "|---|---|",
              "| 图是否够大 | 主图占版心宽度 ≥ 80% |",
              "| 文字是否可读 | 图内标注在交付尺寸下 ≥ 10px |",
              "| 留白是否有信息价值 | 不得出现无信息的空白区块 |",
              "| 配色是否越界 | 强调色面积 ≤ 8% |",
              "| 图注是否可追溯 | 每张图有编号与来源说明 |",
              "| 是否退化 | 与上一版对比，不得减少图种或降低图幅 |",
              "",
              "## 12 来源、版本与变更", "",
              f"- 规范版本：v{rules.get('version')}",
              f"- 模型修订：r{rules.get('revision')}",
              f"- 更新时间：{rules.get('updated_at')}",
              f"- 素材库入口：{REFERENCE_LIBRARY_URL}",
              "",
              "| 时间 | 动作 | 变更 |", "|---|---|---|"]
    for c in rules.get("changelog") or []:
        lines.append(f"| {c.get('at')} | {c.get('by')} | {c.get('change')} |")

    lines += ["", "> 本文件中的规则按来源标注：客户明确指定、参考文件提取、总设计师专业建议。",
              "> 未经客户确认的偏好不写成客户要求。",
              "",
              "---",
              "",
              "> © OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师"
              "（omniailabx.com）— 未经授权禁止复制、传播或二次分发。",
              ""]
    return "\n".join(lines)


# --------------------------------------------------------------------------
# 读写
# --------------------------------------------------------------------------
def write(rules: Dict[str, Any], project: Any,
          project_dir: str | Path | None = None) -> Path:
    p = path_for(project, project_dir)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(render(rules), encoding="utf-8")
    return p


def load(project: Any, project_dir: str | Path | None = None) -> Optional[Dict[str, Any]]:
    """读回规则。文件不存在或机读块损坏时返回 None（调用方回退默认值）。"""
    p = path_for(project, project_dir)
    if not p.exists():
        return None
    try:
        text = p.read_text(encoding="utf-8")
    except OSError:
        return None
    i = text.find(BLOCK_START)
    if i < 0:
        return None
    j = text.find(BLOCK_END, i + len(BLOCK_START))
    if j < 0:
        return None
    raw = text[i + len(BLOCK_START):j].strip()
    try:
        data = json.loads(raw)
    except ValueError:
        return None
    return data if isinstance(data, dict) else None


THEME_KEYS = ("paper", "ink", "muted", "line", "accent", "whitespace",
              "contrast", "line_weight", "serif_titles", "numbered_captions",
              "image_dominant", "full_bleed", "no_cards", "image_ratio")


def theme(project: Any, project_dir: str | Path | None = None) -> Dict[str, Any]:
    """渲染层要的量。没有规范文件 → 与上一版完全一致的默认值。"""
    data = load(project, project_dir)
    base = {k: ex.DEFAULTS[k] for k in THEME_KEYS if k in ex.DEFAULTS}
    if not data:
        base["source"] = "default"
        return base
    tokens = data.get("tokens") or {}
    for k in THEME_KEYS:
        if k in tokens and tokens[k] not in (None, ""):
            base[k] = tokens[k]
    base["source"] = "视觉.md"
    return base


# --------------------------------------------------------------------------
# 更新
# --------------------------------------------------------------------------
CHANGE_CUES = ("喜欢", "不喜欢", "换成", "改成", "像这个", "参考这个", "太普通",
               "排版", "字体", "配色", "颜色", "留白", "图太小", "字太小",
               "高级", "质感", "风格")


#: 态度词与视觉对象词。两个都命中才算"视觉偏好变更"，
#: 只命中一个的多半是别的意思（"我想要个书房"不该改版面）。
ATTITUDE = ("喜欢", "觉得", "太", "想", "希望", "要", "不要", "别", "能", "更",
            "应该", "像", "照这个", "参照")
VISUAL = ("排版", "版式", "版面", "字体", "字", "配色", "颜色", "色调", "风格",
          "留白", "图", "作品集", "参考", "高级", "质感", "干净", "克制")


def detect_change(text: str) -> bool:
    """一句话是不是"视觉偏好变更"。判据是**同时在说图和说态度**。"""
    s = str(text or "")
    if len(s) < 4:
        return False
    has_att = any(k in s for k in ATTITUDE)
    has_vis = any(k in s for k in VISUAL)
    return has_att and has_vis


def update(project: Any, feedback: str, *, project_dir: str | Path | None = None,
           by: str = "client", new_refs: Sequence[Dict[str, Any]] = ()) -> Dict[str, Any]:
    """客户改口味：只改表达规则，不动设计内容；版本 +1 并留变更记录。

    **设计内容不在这个文件里**，所以更新它永远不会丢方案。这一条是刻意的：
    客户说"排版太普通"时，改的应该是版面，不该是院子的位置。
    """
    rules = load(project, project_dir) or compose(project, [], lead="")
    layer = ex.from_text(feedback, origin="client")

    tokens = dict(rules.get("tokens") or {})
    prov = dict(rules.get("provenance") or {})
    # 只写**这一句话里真的说到的**规则。早期版本在这里调了一次 merge，
    # 而 merge 返回的是"含默认值的全集"，于是客户只说了句"线细一点"，
    # 整份规范的纸色墨色就被重置成了默认值——那不是变更，是抹除。
    for k, v in ((layer.get("layout") or {})).items():
        tokens[k] = v["value"]
        prov[k] = "client"
    for word, hexv in (layer.get("colours") or {}).items():
        key = ("paper" if word in ("暖白", "米白", "象牙", "纸白", "奶白", "米色", "浅米")
               else "ink" if word in ("石墨", "炭黑", "墨黑", "纯黑", "深灰") else "accent")
        tokens[key] = hexv
        prov[key] = "client"

    banned = list(rules.get("banned") or [])
    for b in layer.get("banned") or []:
        # 一句话里既抱怨又提要求时，整句进 changelog 就够了；
        # banned 只收能当条目读的短句。
        if len(b["text"]) <= 30 and b["text"] not in [x["text"] for x in banned]:
            banned.append(b)

    sources = list(rules.get("sources") or [])
    for r in new_refs:
        sources.append(_source_summary(r))

    rules = {
        **rules,
        "tokens": tokens,
        "provenance": prov,
        "banned": banned,
        "sources": sources,
        "version": int(rules.get("version") or 1) + 1,
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "client_text": (str(rules.get("client_text") or "") + "　" +
                        " ".join(feedback.split())[:200]).strip(),
        "changelog": list(rules.get("changelog") or []) + [{
            "at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "by": by,
            "change": "视觉偏好变更：" + " ".join(feedback.split())[:80]}],
    }
    write(rules, project, project_dir)
    return rules


# --------------------------------------------------------------------------
# 引导
# --------------------------------------------------------------------------
GUIDE_TEXT = (
    "您有没有喜欢的建筑、室内或景观设计案例，以及喜欢的作品集、排版样本或参考文档？"
    "可以发图片、PDF、PPT、Markdown 文件或网页链接。"
    "我可以参考它们的审美和视觉表达方式，形成适合您这个项目的设计视觉规范。"
)


def guide(lead: str = "") -> Dict[str, Any]:
    """S1 的引导语。没有参考不阻断流程——这句话本身要写在返回值里。"""
    extra = {
        "architecture": "建筑可以看体量、立面节奏与剖面表达；",
        "interior": "室内可以看材料质感、灯光气氛与版面层级；",
        "landscape": "景观可以看总平面分层、植物与水的表现；",
    }.get(lead, "")
    return {
        "text": GUIDE_TEXT,
        "first_stop": "Luxora AI 参考图素材库",
        "url": REFERENCE_LIBRARY_URL,
        "extra": extra,
        "blocking": False,
        "note": ("没有参考文件也可以继续：系统会用已有的风格库与专业判断先出方向，"
                 "您看到之后再说哪里不对，同样能形成规范。"),
    }


__all__ = ["FILENAME", "SCHEMA", "path_for", "exists", "compose", "render",
           "write", "load", "theme", "update", "detect_change", "guide",
           "DISCIPLINE_NOTES", "ORIGIN_CN", "GUIDE_TEXT"]
