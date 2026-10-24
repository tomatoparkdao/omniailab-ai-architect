"""设计意图保护：建筑、室内、景观三个真实案例的漂移检测证据。

三个案例都用真实模型数据验证，不靠语言判断：
* 建筑：G2 签"无柱通透"，S4 加柱 → 必须报 changed；
* 室内：G2 签"无主灯完整平顶"，S4 顶面出现外露风口 → 必须报 changed；
* 景观：G2 签"庭院水景为核心"，成果里水景消失 → 必须报 changed。

同时给出一个反例：只换墙面颜色，不得报 changed、不得重开门禁。

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from omniarchitect import changes, conformance as CONF, intent as I     # noqa: E402
from omniarchitect.paths import test_output_root
from omniarchitect.demo import build_demo_project                       # noqa: E402
from omniarchitect.intake.gate import decide_gate                       # noqa: E402
from omniarchitect.intake.interview import answer_question, start_interview  # noqa: E402
from omniarchitect.model import Element                                 # noqa: E402
from omniarchitect.workflow import StageRunner                          # noqa: E402

OUT = test_output_root() / "acceptance-round4"


def _set_feature(p: Any, feature: Dict[str, Any], keep_others: bool = False) -> None:
    d = I.load(p)
    if keep_others:
        d["signature_features"][0] = feature
    else:
        d["signature_features"] = [feature]
    I.write(p, Path(d["file"]).parent, d)


def _to_g2(tmp: Path, one_liner: str, name: str):
    p = build_demo_project(tmp / "proj")
    p.project_id = name
    p.name = name
    p.save(tmp / "proj" / "project.json")
    start_interview(p, one_liner)
    answer_question(p, "base.needs", "客厅能坐 8 人；东西多要收纳")
    decide_gate(p, "approved", by="业主")
    runner = StageRunner(p, tmp / "out", project_dir=tmp / "proj")
    runner.run_stage("S2", confirm=False)
    from omniarchitect import concept as C

    concepts = p.meta["concept"]["options"]["concepts"]
    supported = [c for c in concepts
                 if (c.get("spatial_prototype") or {}).get("plan_strategy")]
    C.select(p, (supported or concepts)[0]["concept_id"])
    res = runner.approve("S2", by="业主张先生")
    assert res["status"] == "confirmed", res.get("notes")
    return p, runner


def case_architecture(tmp: Path) -> Dict[str, Any]:
    p, runner = _to_g2(tmp, "买了一套 150㎡ 大平层，室内精装，拆一堵墙", "建筑-无柱")
    _set_feature(p, {
        "id": "SF-01", "kind": "spatial", "name": "无柱通透空间",
        "statement": "客厅做大跨度无柱空间，视线完全通透",
        "technical_dependencies": [{"discipline": "structure",
                                    "need": "跨度与梁高、能否不落柱"}],
    })
    runner.run_stage("S3", confirm=False)
    runner.approve("S3", by="业主")
    runner.run_stage("S4", confirm=False)
    sp = max([s for s in p.spaces if s.use != "envelope"], key=lambda s: s.area_m2)
    xs = [q[0] for q in sp.boundary_mm2d]
    ys = [q[1] for q in sp.boundary_mm2d]
    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    p.elements.append(Element(id="C-DEMO", type="column", level_id=sp.level_id,
                              geometry={"start": [cx - 120, cy - 120],
                                        "end": [cx + 120, cy + 120],
                                        "kind": "internal"}))
    rep = CONF.check(p, stage="S4", out_root=runner.out)
    gate = runner.approve("S4", by="业主")
    return {
        "case": "建筑：无柱空间被加柱",
        "conformance": rep.to_dict(),
        "gate_status": gate["status"],
        "gate_notes": list(gate.get("notes") or [])[:3],
    }


def case_interior(tmp: Path) -> Dict[str, Any]:
    p, runner = _to_g2(tmp, "买了一套 150㎡ 大平层，室内精装，拆一堵墙", "室内-无主灯")
    _set_feature(p, {
        "id": "SF-01", "kind": "surface", "name": "无主灯天花",
        "statement": "天花做无主灯完整平顶，不做局部吊顶，不出现外露格栅",
        "technical_dependencies": [{"discipline": "mep",
                                    "need": "风管断面、桥架宽度、检修口位置"}],
    })
    out = runner.out
    (out / "04-preliminary").mkdir(parents=True, exist_ok=True)
    (out / "04-preliminary" / "material-lighting.json").write_text(
        json.dumps({"surfaces": {"ceiling": [
            {"zone": "客厅", "method": "外露风口 + 明装检修口", "level": "H2800"},
            {"zone": "餐厅", "method": "外露风口", "level": "H2800"}]},
            "lighting": [{"layer": "基础", "fixture": "主灯吊灯"}]},
            ensure_ascii=False), encoding="utf-8")
    rep = CONF.check(p, stage="S4", out_root=out)
    return {"case": "室内：无主灯天花出现外露风口",
            "conformance": rep.to_dict(),
            "gate_status": "not_run", "gate_notes": []}


def case_landscape(tmp: Path) -> Dict[str, Any]:
    p = build_demo_project(tmp / "proj")
    p.project_id = "景观-水景"
    p.name = "庭院"
    p.save(tmp / "proj" / "project.json")
    start_interview(p, "院子要做一个水景，中间有水池，铺装加种植")
    answer_question(p, "base.needs", "能坐下喝茶")
    p.meta["design_intent"] = {
        "design_intent_id": "DI-WATER-CASE",
        "lead_discipline": "landscape", "lead_label": "景观",
        "revision": p.revision,
        "signature_features": [{
            "id": "SF-01", "kind": "water", "name": "庭院水景",
            "statement": "庭院中央做水池作为视觉核心，水面与铺装齐平",
            "technical_dependencies": [{"discipline": "mep", "need": "循环与补水"}],
        }],
    }
    rep = CONF.check(p, stage="S3")
    return {"case": "景观：水景在成果里消失",
            "conformance": rep.to_dict(),
            "gate_status": "not_run", "gate_notes": []}


def case_repaint(tmp: Path) -> Dict[str, Any]:
    p, _runner = _to_g2(tmp, "买了一套 150㎡ 大平层，室内精装，拆一堵墙", "反例-换颜色")
    rep = changes.analyse(p, "客厅墙面换个颜色，暖灰改成奶白", apply=False)
    d = rep.to_dict()["design_intent"]
    return {"case": "反例：只换墙面颜色",
            "requires_formal": d.get("requires_formal"),
            "verdict": d.get("verdict"),
            "scope": rep.scope,
            "note": "低风险面层调整不得触发变更审批，也不得重开门禁"}


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for name, fn in (("architecture", case_architecture),
                     ("interior", case_interior),
                     ("landscape", case_landscape),
                     ("repaint", case_repaint)):
        tmp = OUT / name
        if tmp.exists():
            shutil.rmtree(tmp)
        tmp.mkdir(parents=True, exist_ok=True)
        try:
            row = fn(tmp)
        except Exception as exc:                        # noqa: BLE001
            row = {"case": name, "error": f"{type(exc).__name__}: {exc}"}
        rows.append(row)
        (OUT / f"{name}.json").write_text(
            json.dumps(row, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        status = (row.get("conformance") or {}).get("status") or row.get("verdict") or row.get("error")
        print(f"[{name}] {status}")

    summary = {"evidence_level": "scripted_e2e", "cases": rows}
    (OUT / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("written:", OUT / "summary.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
