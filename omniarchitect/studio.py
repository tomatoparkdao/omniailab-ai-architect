"""Design studio hand-off: one call that assembles the visual/3D chain.

Stages produce drawings. What a client-facing design process also needs is the
hand-off between drawing, picture and model:

    CAD 模型  →  视觉任务书（提示词绑定几何）
              →  线稿（给图像模型当几何控制）
              →  SketchUp 交接包（脚本或 MCP）
              →  一致性核查
              →  交接说明（哪些连上了、哪些没有、怎么补）

Doing this in one command matters for honesty: the same run records the MCP
verdict once, and that verdict is what the README and the JSON both carry. If
they were produced by separate calls they would eventually disagree.

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from . import consistency, sketchup, visual_brief
from .providers import discover
from .registry import SIGNATURE
from .tools import mcp_bridge

#: Which discipline a project belongs to, from what the model already knows.
def discipline_of(project: Any) -> str:
    sector = (project.meta.get("sector_levels") or {}).get("sector") or ""
    if sector in ("education", "hospitality", "office", "housing", "healthcare"):
        # A hospitality/office/housing building is still drawn as architecture
        # unless the project was set up as an interior fit-out.
        if sector == "hospitality" and project.meta.get("fitout"):
            return "interior"
        return "architecture"
    if project.spaces_on("L-SITE") and not any(
            s.use not in visual_brief.SITE_USES and s.level_id != "L-SITE"
            for s in project.spaces):
        return "landscape"
    if project.spaces_on("L-SITE"):
        return "landscape"
    if any(s.use in ("guest", "living", "bedroom", "kitchen") for s in project.spaces):
        return "interior"
    return "architecture"


def _style_text(project: Any) -> str:
    rec = (project.meta.get("concept") or {})
    style = str(rec.get("style") or rec.get("style_name") or "").strip()
    if style:
        return style
    chosen = (project.meta.get("scheme") or {}).get("title")
    return str(chosen or "")


def _materials(project: Any) -> List[str]:
    out: List[str] = []
    for item in (project.meta.get("concept") or {}).get("materials") or []:
        name = item.get("name") if isinstance(item, dict) else str(item)
        if name:
            out.append(str(name))
    if out:
        return out[:8]
    from . import finishes
    try:
        for row in finishes.material_rows(project, None)[:8]:
            if row.get("material"):
                out.append(f"{row.get('part', '')}：{row['material']}")
    except Exception:                     # noqa: BLE001  材料表不可用不阻断交接
        pass
    return out


def _provider_state(project: Any) -> Dict[str, Any]:
    reg = discover()
    # A provider declares several scopes at once, so the report is per-scope.
    scopes: Dict[str, str] = {}
    for cap in reg.capabilities():
        for scope in getattr(cap, "scopes", ()) or ():
            scopes.setdefault(scope, cap.state)
    rep = reg.report()
    # Generative scopes belong to OmniAiLab only. If no provider claims them the
    # honest state is "not configured", not "unknown" — the missing list below
    # says exactly what the platform has to hand over.
    generative = "not_configured" if rep.get("not_configured") else "connected"
    for scope in ("image_generation", "image_editing",
                  "reference_image_generation", "multi_view_visualization",
                  "video_generation", "architectural_walkthrough"):
        scopes.setdefault(scope, generative)
    missing: List[str] = []
    for entry in rep.get("providers") or []:
        if entry.get("provider") == "omniailab":
            missing = list(entry.get("missing") or [])
            break
    return {
        "image_generation": scopes.get("image_generation", generative),
        "image_editing": scopes.get("image_editing", generative),
        "reference_image_generation": scopes.get("reference_image_generation", generative),
        "usable_image_backends": reg.image_backends(),
        "missing": missing,
        "note": "平台未连接时任务包保留，状态如实写入；不生成替代图",
    }


def package(project: Any, out_dir: str | Path, *,
            discipline: Optional[str] = None,
            level_id: Optional[str] = None,
            style: str = "",
            obj_path: Optional[str | Path] = None,
            project_dir: Optional[str | Path] = None,
            want_sketchup: bool = True) -> Dict[str, Any]:
    """Build the whole hand-off and write it to `out_dir`."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    disc = discipline or discipline_of(project)
    style_text = style or _style_text(project) or "按已确认概念方案的风格执行"

    mcp = mcp_bridge.status(project_dir)
    cams = sketchup.camera_jobs(project, level_id)
    brief_pkg = visual_brief.brief(project, disc, level_id=level_id,
                                   style=style_text, materials=_materials(project),
                                   cameras=cams)
    prov = _provider_state(project)
    brief_pkg["provider_state"] = prov["image_generation"]
    files: List[str] = visual_brief.write(brief_pkg, out)

    # Linework: the geometry an image model is allowed to see.
    linework_path = None
    try:
        payload = sketchup.scene_payload(project, level_id)
        linework_path = sketchup.linework(payload, out / "linework.svg")
        files.append(str(linework_path))
    except ValueError as exc:
        brief_pkg.setdefault("warnings", []).append(f"线稿未生成：{exc}")

    su_job: Dict[str, Any] = {"state": mcp_bridge.NOT_CONFIGURED}
    if want_sketchup:
        su_job = sketchup.write_job(project, out / "sketchup", level_id=level_id,
                                    project_dir=project_dir)
        files += [str(out / "sketchup" / n) for n in
                  ("sketchup-job.json", "build_model.rb", "camera_jobs.json")]

    cons = consistency.report(project, brief_pkg, obj_path=obj_path, level_id=level_id)

    (out / "mcp-status.json").write_text(
        json.dumps(mcp, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "consistency.json").write_text(
        json.dumps(cons, ensure_ascii=False, indent=2), encoding="utf-8")
    files += [str(out / "mcp-status.json"), str(out / "consistency.json")]

    readme = _readme(project, disc, style_text, brief_pkg, mcp, su_job, cons, prov)
    (out / "README.md").write_text(readme, encoding="utf-8")
    files.append(str(out / "README.md"))

    return {"discipline": disc, "brief": brief_pkg, "sketchup": su_job,
            "consistency": cons, "mcp": mcp, "provider": prov, "files": files}


def _readme(project: Any, disc: str, style: str, brief_pkg: Dict[str, Any],
            mcp: Dict[str, Any], su: Dict[str, Any], cons: Dict[str, Any],
            prov: Dict[str, Any]) -> str:
    label = visual_brief.DISCIPLINE_RULES[disc]["label"]
    g = brief_pkg["geometry"]
    lines = [f"# 设计交付交接 · {project.name or project.project_id}", "",
             f"- 专业：{label}　版本：r{project.revision}",
             f"- 风格：{style}", "",
             "## 一、这次交接包含什么", "",
             "| 成果 | 文件 | 状态 |", "|---|---|---|"]
    lines.append(f"| 视觉任务书 | `visual-brief.md` / `.json` | "
                 f"{len(brief_pkg['shots'])} 个镜头，提示词已绑定几何 |")
    lines.append("| 几何控制线稿 | `linework.svg` | 只有墙线洞口，无填充 |")
    lines.append(f"| SketchUp 交接 | `sketchup/build_model.rb` | "
                 f"{su.get('state')}；{su.get('counts', {}).get('walls', 0)} 道墙、"
                 f"{su.get('counts', {}).get('openings', 0)} 个洞口标记 |")
    lines.append("| 一致性核查 | `consistency.json` | "
                 f"{'通过' if not cons['blocking'] else '有阻断项'} |")
    lines.append(f"| 图像平台 | `mcp-status.json` | "
                 f"image_generation = {prov['image_generation']} |")

    lines += ["", "## 二、几何事实（一切提示词与模型的共同依据）", "",
              "| 项目 | 值 |", "|---|---|",
              f"| {g['unit']}数 | {g['rooms']} |",
              f"| 门 / 窗 | {g['doors']} / {g['windows']} |",
              f"| 层高 | {g['storey_height_m']:.2f} m |"
              if g["storey_height_m"] else "| 层高 | 不适用（景观/单层） |",
              f"| 外轮廓 | {g['envelope_m'][0]:.1f} m × {g['envelope_m'][1]:.1f} m |"
              if g["envelope_m"] else "| 外轮廓 | 未计算 |"]

    lines += ["", "## 三、连接状态（不粉饰）", ""]
    for role in ("cad", "sketchup"):
        prof = mcp["servers"].get(role) or {}
        state = prof.get("state", "not_configured")
        if state == mcp_bridge.AVAILABLE:
            detail = f"已握手，解析到 {len(prof.get('resolved') or {})} 个工具"
        elif state == mcp_bridge.PARTIAL:
            detail = f"部分可用，缺 {', '.join(prof.get('missing') or [])}"
        else:
            detail = "未连接：" + (prof.get("error") or "未找到配置")
        lines.append(f"- **{prof.get('label') or role}**：{state} —— {detail}")
    lines.append(f"- **图像平台**：{prov['image_generation']}"
                 + ("；可用后端：" + "、".join(prov["usable_image_backends"])
                    if prov["usable_image_backends"] else "；无可用后端，任务包保留"))

    lines += ["", "## 四、下一步怎么做", ""]
    if su.get("state") == mcp_bridge.NOT_CONFIGURED:
        lines += ["1. SketchUp：打开 SketchUp → Ruby 控制台 → "
                  "`load '<本目录>/sketchup/build_model.rb'`",
                  "   脚本按模型坐标建墙与洞口标记；Make 版无实体工具，"
                  "洞口切割须人工完成。"]
    else:
        lines += ["1. SketchUp：已连接 MCP，建模调用结果见 `sketchup/sketchup-job.json`。"]
    if prov["image_generation"] in ("not_configured", "unknown"):
        lines += ["2. 效果图：平台未连接，`visual-brief.json` 里的 prompt 可直接粘贴到"
                  "平台使用；未生成任何替代图。"]
    else:
        lines += ["2. 效果图：按 `visual-brief.json` 的镜头与 prompt 提交。"]
    lines += [f"3. 出图后用同一机位（`sketchup/camera_jobs.json`）截图，"
              "与效果图逐张比对开洞与比例。", ""]

    if cons["blocking"]:
        lines += ["## 五、阻断项", ""] + [f"- {b}" for b in cons["blocking"]] + [""]
    lines += ["## 六、仍需人工判断", "",
              "- 效果图中的开口位置、比例与家具尺度是否忠于平面，程序不能判定；",
              "- 洞口切割、结构构件与机电点位须专业人员在模型里完成；",
              "- 本交接不构成尺寸依据，也不能替代持证人员审查。", "",
              "---", "", SIGNATURE]
    return "\n".join(lines)


def status(project: Any, project_dir: Optional[str | Path] = None) -> Dict[str, Any]:
    """Cheap status: what is wired and what would be produced."""
    return {"discipline": discipline_of(project),
            "mcp": mcp_bridge.status(project_dir),
            "provider": _provider_state(project)}


__all__ = ["discipline_of", "package", "status"]
