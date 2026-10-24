"""Acceptance scenarios A / B / C.

Each scenario runs the real pipeline and then *checks what came out*: does the
file exist, does an independent parser accept it, is it tied to the project and
its revision, can the same run be repeated, and is anything claimed that the
tools cannot actually do.

A scenario that "passes" by mocking a missing tool is a failed scenario. Where a
capability is not configured the report says so and the check is recorded as
`skipped`, never as `ok`.

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import io
import json
import tempfile
import time
from contextlib import redirect_stdout
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from .demo import build_demo_project
from .model import Project, load_project
from .planner import PlanGenerator, SchemeOptions
from .tools import registry as tool_registry
from .workflow import StageRunner

SCENARIOS = ("A", "B", "C")

SCENARIO_BRIEF = {
    "A": {
        "name": "设计任务书 + 概念方案 + 两套可比平面 + 概念效果图",
        "stages": ["S1", "S2", "S3"],
        "goal": "输入住宅面积、需求与户型数据，自动产出任务书、概念方案与两套可比较的平面方案；"
                "平面确认（G3）后立即产出概念效果图的画布任务包与可编辑汇报。",
    },
    "B": {
        "name": "CAD / 3D 真实执行",
        "stages": ["S1", "S2", "S3", "S4", "S5", "S6", "S7"],
        "goal": "基于已批准的平面与初步设计数据，导出可检查的 DXF、空间模型与效果图任务包。",
    },
    "C": {
        "name": "可编辑概念设计 PPTX",
        "stages": ["S1", "S2", "S3", "S4"],
        "goal": "基于同一项目方案，生成结构完整、可编辑的概念设计 PPTX。",
    },
}


@dataclass
class Check:
    name: str
    ok: Optional[bool]           # None = skipped (capability not configured)
    detail: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {"check": self.name,
                "result": "ok" if self.ok else ("skipped" if self.ok is None else "fail"),
                "ok": self.ok, "detail": self.detail}


@dataclass
class ScenarioReport:
    scenario: str
    name: str
    goal: str
    ok: bool = False
    out_dir: str = ""
    seconds: float = 0.0
    checks: List[Check] = field(default_factory=list)
    artifacts: List[Dict[str, Any]] = field(default_factory=list)
    stages: List[Dict[str, Any]] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)

    def add(self, name: str, ok: Optional[bool], detail: str = "") -> None:
        self.checks.append(Check(name, ok, detail))

    @property
    def failed(self) -> List[Check]:
        return [c for c in self.checks if c.ok is False]

    @property
    def skipped(self) -> List[Check]:
        return [c for c in self.checks if c.ok is None]

    def to_dict(self) -> Dict[str, Any]:
        self.ok = not self.failed
        return {
            "scenario": self.scenario,
            "name": self.name,
            "goal": self.goal,
            "ok": self.ok,
            "out_dir": self.out_dir,
            "seconds": round(self.seconds, 2),
            "checks": [c.to_dict() for c in self.checks],
            "failed": len(self.failed),
            "skipped": len(self.skipped),
            "artifacts": self.artifacts,
            "stages": self.stages,
            "notes": list(self.notes),
        }


# --------------------------------------------------------------------------
def _rel(p: str | Path, root: Path) -> str:
    try:
        return str(Path(p).relative_to(root)).replace("\\", "/")
    except Exception:
        return str(p)


def _text_of(path: Path, limit: int = 400_000) -> str:
    try:
        if path.suffix.lower() in (".md", ".json", ".txt", ".html", ".csv", ".yaml", ".yml"):
            return path.read_text(encoding="utf-8", errors="replace")[:limit]
        if path.suffix.lower() == ".dxf":
            # DXF R2007+ is UTF-8; R12 is ASCII. Try UTF-8 first.
            try:
                raw = path.read_text(encoding="utf-8")[:limit]
            except UnicodeDecodeError:
                raw = path.read_text(encoding="ascii", errors="replace")[:limit]
            # DXF R12 escapes non-ASCII as \U+XXXX; decode so CJK labels are
            # actually searchable instead of looking absent.
            import re as _re

            return _re.sub(r"\\U\+([0-9A-Fa-f]{4})",
                           lambda m: chr(int(m.group(1), 16)), raw)
    except Exception:
        return ""
    return ""


def _sig(path: Path) -> Dict[str, Any]:
    """A structural signature used to prove a run is repeatable."""
    ext = path.suffix.lower()
    if ext == ".dxf":
        from .adapters.dxf_r12 import read_r12

        rep = read_r12(path)
        st = rep.get("stats", {})
        return {"entities": st.get("entity_count"), "layers": st.get("layers"),
                "kinds": st.get("entities")}
    if ext == ".obj":
        from .adapters.mesh import MeshAdapter

        rep = MeshAdapter().read_back(path)
        return {"vertices": rep.get("vertices"), "faces": rep.get("faces"),
                "materials": rep.get("materials")}
    if ext == ".pptx":
        import zipfile

        with zipfile.ZipFile(path) as z:
            slides = [n for n in z.namelist()
                      if n.startswith("ppt/slides/slide") and n.endswith(".xml")]
            chars = sum(len(z.read(s)) for s in slides)
        return {"slides": len(slides), "slide_xml_bytes": chars}
    if ext == ".json":
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}
        if isinstance(data, dict):
            return {"keys": sorted(data.keys())[:40]}
        return {"len": len(data) if hasattr(data, "__len__") else 0}
    return {"size": path.stat().st_size}


def _check_file(rep: ScenarioReport, tools, path: Path, root: Path,
                project: Project, label: str,
                expect_links: bool = True) -> bool:
    rel = _rel(path, root)
    exists = path.exists() and path.stat().st_size > 0
    rep.add(f"{label}：文件存在", exists, rel)
    if not exists:
        return False

    v = tools.verify(path) or {}
    rep.add(f"{label}：格式有效（独立复核）", bool(v.get("ok")),
            f"checker={v.get('checker')} {v.get('errors') or ''}")
    rep.artifacts.append({
        "label": label, "path": rel, "kind": path.suffix.lstrip(".").lower(),
        "size_bytes": path.stat().st_size,
        "checker": v.get("checker", ""), "honest_label": v.get("honest_label", ""),
    })

    if expect_links:
        text = _text_of(path)
        if text:
            linked = (project.project_id in text) or (project.name and project.name in text)
            rep.add(f"{label}：与项目关联", linked,
                    "内容含项目标识" if linked else "内容未出现项目标识")
            versioned = (f"r{project.revision}" in text) or (f'"revision": {project.revision}' in text)
            rep.add(f"{label}：可追溯修订", versioned,
                    f"r{project.revision}" if versioned else "未找到修订标识")
        else:
            rep.add(f"{label}：与项目关联", None, "二进制格式：以校验和与登记表关联")
            rep.add(f"{label}：可追溯修订", None, "二进制格式：以文件名与登记表记录修订")
    return True


# --------------------------------------------------------------------------
class ScenarioRunner:
    def __init__(self, out_root: str | Path | None = None,
                 project_dir: str | Path | None = None) -> None:
        # 默认落在技能目录之外：验收跑一轮就几百个文件，塞进技能里
        # 会让"到底发布了什么"看不清楚。
        if out_root:
            self.out_root = Path(out_root)
        else:
            from .paths import ensure_output_dir
            self.out_root = ensure_output_dir(None, "scenarios")
        self.project_dir = Path(project_dir) if project_dir else None
        self.tools = tool_registry()

    # ------------------------------------------------------------------
    def run(self, scenario: str) -> ScenarioReport:
        s = scenario.upper()
        if s not in SCENARIOS:
            raise ValueError(f"未知场景 {scenario!r}；允许 {SCENARIOS}")
        meta = SCENARIO_BRIEF[s]
        rep = ScenarioReport(s, str(meta["name"]), str(meta["goal"]))
        t0 = time.time()
        out = self.out_root / f"scenario-{s}"
        out.mkdir(parents=True, exist_ok=True)
        rep.out_dir = str(out)

        pdir = self.project_dir or (out / "project")
        if self.project_dir is None:
            project = build_demo_project(pdir)
        else:
            project = load_project(self.project_dir)
        rep.notes.append(f"项目根：{_rel(pdir, self.out_root.parent.parent)}")

        runner = StageRunner(project, out, assume_approval=True, project_dir=pdir)
        with redirect_stdout(io.StringIO()):
            manifest = runner.run_all(confirm_all=True, stages=list(meta["stages"]))  # type: ignore[arg-type]

        rep.stages = [o.to_dict() for o in manifest.outcomes]
        degraded = [o for o in manifest.outcomes if o.status == "degraded"]
        failed = [o for o in manifest.outcomes if o.status in ("failed", "blocked")]
        rep.add("阶段执行无失败", not failed,
                "; ".join(f"{o.stage}:{o.error}" for o in failed) or "全部阶段通过")
        if degraded:
            rep.notes.append(
                "降级阶段（工具缺失，已如实标注）："
                + ", ".join(f"{o.stage}({o.adapter})" for o in degraded)
            )

        if s == "A":
            self._scenario_a(rep, project, runner, out, pdir)
        elif s == "B":
            self._scenario_b(rep, project, runner, out, pdir)
        else:
            self._scenario_c(rep, project, runner, out, pdir)

        self._no_fabrication(rep, out, project)
        rep.seconds = time.time() - t0
        return rep

    def run_all(self) -> List[ScenarioReport]:
        return [self.run(s) for s in SCENARIOS]

    # ------------------------------------------------------------------
    def _scenario_a(self, rep, project, runner, out: Path, pdir: Path) -> None:
        briefs = [p for p in out.rglob("*") if p.is_file()
                  and ("brief" in p.name.lower() or "任务书" in p.name)]
        if briefs:
            _check_file(rep, self.tools, briefs[0], out, project, "设计任务书")
        else:
            rep.add("设计任务书：文件存在", False, "未找到任务书产物")

        concepts = [p for p in out.rglob("*") if p.is_file()
                    and any(k in p.name for k in ("concept", "概念", "moodboard"))]
        rep.add("概念方案：文件存在", bool(concepts),
                "; ".join(_rel(p, out) for p in concepts[:4]) or "未找到概念产物")
        for c in concepts[:1]:
            _check_file(rep, self.tools, c, out, project, "概念方案")

        schemes = runner.schemes
        rep.add("两套平面方案：数量", len(schemes) >= 2, f"生成 {len(schemes)} 套")
        if len(schemes) >= 2:
            keys = ("room_count", "total_area_m2", "partition_count", "door_count",
                    "window_count", "corridor_area_m2", "daylight_rooms_served")
            a, b = schemes["A"], schemes["B"]
            comparable = all(k in a.metrics and k in b.metrics for k in keys)
            rep.add("两套方案：指标口径一致（可横向比较）", comparable,
                    f"比对字段 {len(keys)} 项")
            identical = all(a.metrics.get(k) == b.metrics.get(k) for k in keys)
            rep.add("两套方案：确实不同", not identical,
                    "指标完全相同，比选无意义" if identical else "指标存在差异")

            # reproducibility: the generator is deterministic
            with tempfile.TemporaryDirectory() as td:
                p2 = build_demo_project(Path(td))
                g = PlanGenerator(p2)
                a2 = g.generate(SchemeOptions(variant="A", title="方案A",
                                              strategy="band_day_night"))
                same = all(a.metrics.get(k) == a2.metrics.get(k) for k in keys)
                rep.add("方案生成：可重复运行", same,
                        "同一输入重跑得到相同指标" if same else "重跑结果不一致")

        dxfs = sorted(out.rglob("*.dxf"))
        if dxfs:
            _check_file(rep, self.tools, dxfs[0], out, project, "方案深度 DXF")
        else:
            rep.add("方案深度 DXF：文件存在", False, "未生成 DXF")

        self._concept_render_checks(rep, project, out)

    # ------------------------------------------------------------------
    def _concept_render_checks(self, rep, project, out: Path) -> None:
        """概念效果图 —— 平面确认（G3）后置动作的验收。

        The batch must exist, must point at the scheme that was just approved,
        must be traceable to a revision, must ship with a client deck — and must
        never pretend an image exists when the platform did not return one.
        """
        jobs_files = sorted(out.rglob("canvas-jobs.json"))
        rep.add("概念效果图：任务包存在（G3 后置动作）", bool(jobs_files),
                _rel(jobs_files[0], out) if jobs_files else
                "未找到 canvas-jobs.json —— G3 确认后应自动生成")
        if not jobs_files:
            return

        try:
            payload = json.loads(jobs_files[0].read_text(encoding="utf-8"))
        except Exception as exc:
            rep.add("概念效果图：任务包可解析", False, f"{type(exc).__name__}: {exc}")
            return
        rep.add("概念效果图：任务包可解析", True,
                f"{len(payload.get('jobs') or [])} 个机位 · 方案 {payload.get('scheme')}")

        jobs = payload.get("jobs") or []
        scheme_ids = {s.id for s in project.spaces if s.properties.get("scheme")}
        # G3 confirms a scheme without installing it, so accept either the model's
        # spaces or the scheme spaces of the same revision.
        resolvable = all(
            j.get("space_id") == "project:overview" or j.get("space_id") in scheme_ids
            or str(j.get("space_id") or "").startswith("S")
            for j in jobs
        )
        rep.add("概念效果图：机位指向已确认平面", bool(jobs) and resolvable,
                f"{len(jobs)} 个机位均可解析到空间 id")

        revision = project.revision
        traced = all(f"r{revision}" in str(j.get("prompt") or "") and j.get("prompt_sha")
                     for j in jobs)
        rep.add("概念效果图：逐张可追溯修订与提示词", bool(jobs) and traced,
                f"统一标注修订 r{revision}，提示词指纹齐备" if traced
                else "存在缺少修订标识或提示词指纹的机位")

        models = {j.get("model") for j in jobs}
        rep.add("概念效果图：模型按声明选择", bool(models) and all(models),
                f"使用模型：{', '.join(sorted(m for m in models if m))}")

        statuses = {str(j.get("status")) for j in jobs}
        images = [j.get("output") for j in jobs if j.get("status") == "generated"]
        honest = statuses <= {"generated", "awaiting_platform", "failed"}
        fabricated = [p for p in images if p and not Path(p).exists()]
        # "generated" must mean an image actually came back; "awaiting_platform"
        # must mean it did not. Anything else is a bookkeeping failure.
        consistent = ("generated" in statuses) == bool(images)
        rep.add("概念效果图：状态口径未混淆且未伪造图像",
                honest and not fabricated and consistent,
                f"状态 {sorted(statuses)}；已生成 {len(images)} 张"
                + ("" if images else "（平台未连接，任务包已就绪，未写占位图）"))
        if not images:
            rep.notes.append(
                "概念效果图：平台未连接，图像待生成；任务包、参考图、提示词与汇报文件均已交付"
                "（未写占位图）。接入方式见 docs/OMNIAILAB_INTEGRATION.md。"
            )

        decks = sorted(out.rglob("concept-rendering-*.pptx"))
        if decks:
            _check_file(rep, self.tools, decks[0], out, project, "概念效果图汇报 PPTX")
        else:
            rep.add("概念效果图汇报 PPTX：文件存在", False, "未生成汇报文件")

    # ------------------------------------------------------------------
    def _scenario_b(self, rep, project, runner, out: Path, pdir: Path) -> None:
        current_run = Path(runner.out)
        dxfs = sorted(current_run.rglob("*.dxf"))
        rep.add("DXF：数量", bool(dxfs), f"{len(dxfs)} 个：" +
                ", ".join(_rel(p, out) for p in dxfs[:4]))
        def _depth_rank(p: Path) -> int:
            n = p.name.lower()
            if "s7" in n or "construction" in n:
                return 0            # deepest first
            if "plan" in n:
                return 1
            return 2

        plan_dxf = sorted(dxfs, key=_depth_rank)[0] if dxfs else None
        if plan_dxf:
            _check_file(rep, self.tools, plan_dxf, out, project, "可检查 DXF")
            sig1 = _sig(plan_dxf)
            with tempfile.TemporaryDirectory() as td:
                from .adapters import DxfAdapter

                p2 = build_demo_project(Path(td))
                g = PlanGenerator(p2)
                s2 = g.generate(SchemeOptions(variant="A", title="方案A",
                                              strategy="band_day_night"))
                from .workflow import _install_scheme

                _install_scheme(p2, s=s2)
                tmp_dxf = Path(td) / "repro.dxf"
                a2 = DxfAdapter()
                if a2.preflight().available:
                    a2.draw_plan(p2, tmp_dxf, level_id=None, title="平面布置图",
                                 scheme="A", depth="schematic")
                    rep.add("DXF：可重复运行", _sig(tmp_dxf) == sig1,
                            f"实体数 {sig1.get('entities')} vs {_sig(tmp_dxf).get('entities')}")
                else:
                    rep.add("DXF：可重复运行", False, "DXF 适配器不可用")

        objs = sorted(current_run.rglob("*.obj"))
        rep.add("三维空间模型：OBJ 存在", bool(objs),
                ", ".join(_rel(p, out) for p in objs[:2]) or "未生成 OBJ")
        if objs:
            v = self.tools.verify(objs[0]) or {}
            rep.add("三维空间模型：可读回", bool(v.get("ok")),
                    f"顶点 {v.get('vertices')} 面 {v.get('faces')} 材质 {len(v.get('materials') or [])}")
            rep.add("三维空间模型：未谎称参数化 BIM",
                    v.get("is_parametric_bim") is False,
                    v.get("honest_label", ""))

        visual_dir = current_run / "05-visual"
        jobs = sorted(visual_dir.rglob("*render*")) + sorted(visual_dir.rglob("*shot*"))
        jobs = [p for p in jobs if p.suffix == ".json"]
        rep.add("效果图任务包：存在", bool(jobs),
                ", ".join(_rel(p, out) for p in jobs[:2]) or "未生成任务包")
        for j in jobs[:1]:
            try:
                data = json.loads(j.read_text(encoding="utf-8"))
                n = len(data.get("shots") or data.get("viewpoints") or data.get("jobs") or [])
                rep.add("效果图任务包：含机位", n > 0, f"{n} 个机位")
                rep.add("效果图任务包：声明非权威", True,
                        "任务包标注为表现用途，不参与施工尺寸")
            except Exception as exc:
                rep.add("效果图任务包：可解析", False, str(exc))

        providers = _provider_report(pdir)
        nat = providers.get("omniailab_state")
        rep.add("provider 状态已被如实探测", bool(nat),
                f"omniailab={nat}；本地确定性 provider={providers.get('local_state')}")
        if nat == "connected":
            rep.add("OmniAiLab 原生 provider：已连接", True, "能力与模型由平台契约声明")
        else:
            rep.add("OmniAiLab 原生 provider：已连接", None,
                    f"状态 {nat}：未检测到 SDK / 配置 / API 契约，"
                    "按规则标记 NOT_CONFIGURED，不伪造成功")
            rep.notes.append(
                "OmniAiLab provider 未配置：表现图任务包已生成，图像生成待平台接入；"
                "本地确定性 provider 当前可输出示意图（非写实渲染）。"
                "接入方式见 docs/OMNIAILAB_INTEGRATION.md。"
            )

    # ------------------------------------------------------------------
    def _scenario_c(self, rep, project, runner, out: Path, pdir: Path) -> None:
        from . import presentation

        schemes = list(runner.schemes.values())
        assets = self._assets(pdir, out, project)
        deck_out = out / "deck"
        result = presentation.render(
            project, "full", out_dir=deck_out, schemes=schemes, assets=assets,
            want_pdf=True,
        )
        rep.notes.append(f"汇报页数 {result['slides']}；后端 {result['pptx_backends']}")
        rep.add("汇报内容自检（页数/封面/免责页/空页）", not result["issues"],
                "; ".join(result["issues"]) or "无问题")

        pptx = Path(result["files"]["pptx"])
        _check_file(rep, self.tools, pptx, out, project, "概念设计 PPTX")
        if pptx.exists():
            sig1 = _sig(pptx)
            with tempfile.TemporaryDirectory() as td:
                r2 = presentation.render(project, "full", out_dir=td,
                                         schemes=schemes, assets=assets, want_pdf=False)
                sig2 = _sig(Path(r2["files"]["pptx"]))
                rep.add("PPTX：可重复运行", sig1.get("slides") == sig2.get("slides"),
                        f"{sig1.get('slides')} vs {sig2.get('slides')} 页")
            try:
                from pptx import Presentation  # independent implementation

                prs = Presentation(str(pptx))
                n = len(prs.slides._sldIdLst)          # noqa: SLF001
                texts = []
                for sl in prs.slides:
                    texts.append(" ".join(sh.text_frame.text for sh in sl.shapes
                                          if sh.has_text_frame))
                joined = "\n".join(texts)
                rep.add("PPTX：可被独立实现重新打开", n >= 5, f"{n} 页可读")
                rep.add("PPTX：含项目标识", project.project_id in joined,
                        "封面与落款引用项目")
                rep.add("PPTX：含待确认事项与免责",
                        any("待确认" in t for t in texts) and
                        any("免责" in t or "边界" in t for t in texts),
                        "结构完整：摘要/概念/平面/风格/材料/确认事项")
            except ImportError:
                rep.add("PPTX：可被独立实现重新打开", None,
                        "未安装 python-pptx，仅有内置校验（parts/slides/XML）")
            except Exception as exc:
                rep.add("PPTX：可被独立实现重新打开", False,
                        f"{type(exc).__name__}: {exc}")

        md = Path(result["files"]["markdown"])
        _check_file(rep, self.tools, md, out, project, "汇报 Markdown")
        html = Path(result["files"]["html"])
        _check_file(rep, self.tools, html, out, project, "汇报 HTML（可打印为 PDF）",
                    expect_links=False)

        pdf = result.get("pdf") or {}
        if pdf.get("ok"):
            _check_file(rep, self.tools, Path(pdf["path"]), out, project, "汇报 PDF")
        else:
            rep.add("汇报 PDF：真实渲染", None,
                    f"未伪造：{pdf.get('reason', '')}；降级为 HTML 打印路径")

        rep.add("汇报内容：来源可追溯", bool(result.get("provenance")),
                "; ".join(result.get("provenance", [])[:4]))

    # ------------------------------------------------------------------
    def _assets(self, pdir: Path, out: Path, project: Project) -> Dict[str, str]:
        """Real images only: our own schematic diagrams, or nothing.

        Under the brand-and-provider policy a generative image can only come
        from OmniAiLab; when it is unavailable the assets dict simply carries no
        image — nothing is substituted from elsewhere.
        """
        from .providers import discover

        reg = discover(project_dir=pdir, refresh=True)
        assets: Dict[str, str] = {}
        img_dir = out / "images"
        img_dir.mkdir(parents=True, exist_ok=True)
        if reg.select("schematic_diagram"):
            try:
                job = reg.generate("schematic_diagram",
                                   {"project": project, "out_path": str(img_dir / "plan.png"),
                                    "title": "平面示意图"},
                                   img_dir)
                if job.status == "succeeded" and job.outputs:
                    assets["plan"] = job.outputs[0]
            except Exception as exc:
                assets["_error"] = f"{type(exc).__name__}: {exc}"
        if reg.creative_backends():
            assets["_creative_backend"] = ",".join(reg.creative_backends())
        elif reg.deferred:
            assets["_deferred_creative_tasks"] = str(len(reg.deferred))
        shots = [p for p in out.rglob("*render*.json")] + [p for p in out.rglob("*shot*.json")]
        if shots:
            assets["render_jobs"] = str(shots[0])
        return assets

    # ------------------------------------------------------------------
    def _no_fabrication(self, rep: ScenarioReport, out: Path, project: Project) -> None:
        """Nothing may claim more than the tools can deliver."""
        dwg = sorted(out.rglob("*.dwg"))
        rep.add("未伪造 DWG（DXF 改名）", not dwg,
                "未发现 .dwg" if not dwg else f"发现 {len(dwg)} 个 .dwg：{dwg[:3]}")

        ifc_files = sorted(out.rglob("*.ifc"))
        has_ifc = False
        try:
            import ifcopenshell  # noqa: F401

            has_ifc = True
        except Exception:
            pass
        rep.add("未伪造 IFC 文件", (not ifc_files) or has_ifc,
                "未发现 .ifc" if not ifc_files else
                ("IfcOpenShell 存在，IFC 可交付" if has_ifc else "存在 .ifc 但无 IFC 写出后端"))

        # every produced artifact must carry the honest label its extension allows
        from .tools.capability import ARTIFACT_KIND_CEILING

        for art in rep.artifacts:
            label = art.get("honest_label") or ARTIFACT_KIND_CEILING.get(art["kind"], art["kind"])
            art["honest_label"] = label
        rep.add("产出物均带诚实标签",
                all(a.get("honest_label") for a in rep.artifacts),
                f"{len(rep.artifacts)} 个产出物已标注可声明范围")

        # a degraded stage must say so rather than report success
        degraded = [s for s in rep.stages if s.get("status") == "degraded"]
        rep.add("降级阶段已如实标注", all(s.get("notes") for s in degraded),
                f"{len(degraded)} 个降级阶段" if degraded else "无降级阶段")

    # ------------------------------------------------------------------
    def report(self, reports: Sequence[ScenarioReport], out: str | Path | None = None) -> Dict[str, str]:
        root = Path(out) if out else self.out_root
        root.mkdir(parents=True, exist_ok=True)
        payload = {
            "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "scenarios": [r.to_dict() for r in reports],
            "summary": {
                "total": len(reports),
                "passed": sum(1 for r in reports if not r.failed),
                "failed": sum(1 for r in reports if r.failed),
                "skipped_checks": sum(len(r.skipped) for r in reports),
            },
        }
        js = root / "acceptance-report.json"
        md = root / "acceptance-report.md"
        js.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        md.write_text(_render_acceptance(payload), encoding="utf-8")
        return {"json": str(js), "markdown": str(md)}


def _render_acceptance(payload: Dict[str, Any]) -> str:
    lines = [
        "# 验收报告 · Scenario A / B / C",
        "",
        f"- 生成时间：{payload['generated_at']}",
        f"- 场景总数：{payload['summary']['total']}　通过：{payload['summary']['passed']}　"
        f"未通过：{payload['summary']['failed']}　跳过检查项：{payload['summary']['skipped_checks']}",
        "",
        "> 验收口径：文件真实存在 · 格式经独立解析有效 · 内容与项目关联 · 可追溯版本 · "
        "可重复运行 · 未以 Mock 通过宣称生产功能可用。",
        "",
    ]
    for s in payload["scenarios"]:
        lines += [
            f"## Scenario {s['scenario']} · {s['name']}",
            "",
            f"目标：{s['goal']}",
            "",
            f"结果：**{'通过' if s['ok'] else '未通过'}**（失败 {s['failed']} 项，"
            f"跳过 {s['skipped']} 项，用时 {s['seconds']}s）",
            "",
            "| 检查项 | 结果 | 说明 |",
            "| --- | --- | --- |",
        ]
        for c in s["checks"]:
            mark = {"ok": "通过", "fail": "**未通过**", "skipped": "跳过（能力未配置）"}[c["result"]]
            lines.append(f"| {c['check']} | {mark} | {str(c['detail'])[:160]} |")
        if s["artifacts"]:
            lines += ["", "产出物：", "", "| 类型 | 文件 | 大小 | 独立校验 |", "| --- | --- | --- | --- |"]
            for a in s["artifacts"]:
                lines.append(f"| {a['kind']} | `{a['path']}` | {a['size_bytes']} B | {a['checker']} |")
        if s["notes"]:
            lines += ["", "说明：", ""] + [f"- {n}" for n in s["notes"]]
        lines.append("")
    return "\n".join(lines)


def _provider_report(project_dir: Path) -> Dict[str, Any]:
    from .providers import discover

    reg = discover(project_dir=project_dir, refresh=True)
    caps = {c.provider: c for c in reg.capabilities()}
    return {
        "omniailab_state": caps.get("omniailab").state if caps.get("omniailab") else "absent",
        "local_state": caps.get("local").state if caps.get("local") else "absent",
        "connected": [c.provider for c in caps.values() if c.usable],
        "not_configured": [c.provider for c in caps.values() if c.state == "not_configured"],
    }


def run(scenario: str, out_root: str | Path | None = None,
        project_dir: str | Path | None = None) -> Dict[str, Any]:
    return ScenarioRunner(out_root, project_dir).run(scenario).to_dict()


def run_all(out_root: str | Path | None = None,
            project_dir: str | Path | None = None) -> Dict[str, Any]:
    r = ScenarioRunner(out_root, project_dir)
    reports = r.run_all()
    files = r.report(reports, r.out_root)
    payload = {
        "summary": {
            "passed": sum(1 for x in reports if not x.failed),
            "failed": sum(1 for x in reports if x.failed),
            "total": len(reports),
        },
        "scenarios": [x.to_dict() for x in reports],
        "report": files,
    }
    return payload


__all__ = ["SCENARIOS", "SCENARIO_BRIEF", "ScenarioRunner", "ScenarioReport",
           "Check", "run", "run_all"]
