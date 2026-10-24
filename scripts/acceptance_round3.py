"""六组跨专业案例验收：从一句自然语言开始，跑到当前能跑的最深处。

为什么要有这个脚本
------------------
单元测试证明"每个零件对"，但证明不了"整条链在真实委托下走得通"。
这六个案例覆盖六种**范围完全不同**的委托：

    A 住宅室内装修 —— 结构与机电只做协调
    B 新建三层别墅 —— 五个专业全开
    C 独立庭院景观 —— 只有景观，不许调房间算法
    D 酒店室内中庭 —— 室内 + 室内景观，重点在环境与荷载
    E 办公改造     —— 容量矛盾必须在 S1 暴露
    F 综合项目变更 —— 先确认，再加泳池/屋顶花园，看影响是否跨专业

每个案例都记：范围判定、问了几轮、G1 结论、S2 出了什么、G2 是否锁定、
S3 走到哪、被什么挡住、还缺什么资料。**跑不到的阶段写"未达成"，不写成通过。**

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import json
import shutil
import sys
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from omniarchitect import changes, concept as C, disciplines as D          # noqa: E402
from omniarchitect.paths import test_output_root
from omniarchitect.demo import build_demo_project                          # noqa: E402
from omniarchitect.intake.gate import assess_gate, decide_gate             # noqa: E402
from omniarchitect.intake.interview import (                               # noqa: E402
    answer_question, next_questions, start_interview,
)
from omniarchitect.intake.report import generate_bundle                    # noqa: E402
from omniarchitect.model import Project                                    # noqa: E402
from omniarchitect.workflow import StageRunner                             # noqa: E402

OUT = test_output_root() / "acceptance-round3"


class Client:
    """脚本代理客户：只回答自己知道的，不假装知道。"""

    def __init__(self, answers: Dict[str, str], name: str) -> None:
        self.answers = answers
        self.name = name
        self.asked: List[str] = []
        self.repeats = 0

    def respond(self, slot: str) -> bool:
        if slot in self.asked:
            self.repeats += 1
        self.asked.append(slot)
        return slot in self.answers


def _answer_round(project: Project, client: Client, limit: int = 8) -> List[Dict[str, str]]:
    done: List[Dict[str, str]] = []
    for _ in range(limit):
        pool = next_questions(project, limit=12)
        pending = [q for q in pool if q.slot in client.answers
                   and q.slot not in client.asked]
        if not pending:
            break
        q = pending[0]
        client.respond(q.slot)
        answer_question(project, q.id, client.answers[q.slot])
        done.append({"slot": q.slot, "question": q.text, "answer": client.answers[q.slot]})
    return done


CASES: List[Dict[str, Any]] = [
    {
        "key": "A-residential",
        "label": "150㎡ 住宅室内装修",
        "expect_disciplines": {"interior"},
        "one_liner": "我这套 150㎡ 的房子想重新装修，现代意式极简，拆一堵墙",
        "answers": {
            "location": "杭州，南向", "schedule": "明年 6 月前入住",
            "structure": "有结构图，但不确定哪道墙承重",
            "site_conditions": "二手房翻新，原装修全拆",
            "deliverable_depth": "方案 + 施工图",
            "occupants": "一家三口，孩子 5 岁",
            "needs": "客厅能坐 8 个人吃饭；东西多要收纳",
        },
        "constraints": {"style": "现代意式极简", "budget_cny": 1_600_000},
    },
    {
        "key": "B-villa",
        "label": "新建三层别墅（多专业全开）",
        "expect_disciplines": {"architecture", "structure", "mep", "interior", "landscape"},
        "one_liner": ("有块地，想建一栋三层别墅，现代极简，室内要精装修，"
                      "带庭院、景观水池、室内绿化，结构和机电也要一并考虑"),
        "answers": {
            "location": "苏州郊县，地块约 800㎡",
            "schedule": "两年内建成",
            "structure": "还没做地勘，也没有结构方案",
            "site_conditions": "空地，市政水电已到边界，雨污需自处理",
            "deliverable_depth": "建筑方案 + 室内方案 + 景观方案，施工图另行委托",
            "needs": "一家五口，常有客人；要有庭院和水池；室内要有绿植空间",
        },
        "constraints": {"style": "现代极简", "budget_cny": 8_000_000},
    },
    {
        "key": "C-garden",
        "label": "独立庭院景观",
        "expect_disciplines": {"landscape"},
        "one_liner": "只想重新做我家的院子景观，铺装加种植，室内不动",
        "answers": {
            "location": "成都，院子约 60㎡，北向有遮挡",
            "site_conditions": "老院子，排水不畅，下雨会积水",
            "deliverable_depth": "方案 + 施工做法",
            "needs": "能坐下喝茶，好打理，不要草坪",
        },
        "constraints": {"budget_cny": 180_000},
    },
    {
        "key": "D-atrium",
        "label": "酒店室内中庭（室内 + 室内景观）",
        "expect_disciplines": {"interior", "landscape"},
        "one_liner": ("酒店大堂要做一个室内中庭，种大树、做水景，"
                      "室内精装一起设计，层高两层通高"),
        "answers": {
            "location": "杭州，既有酒店改造，大堂约 300㎡，通高 7.2m",
            "structure": "有原结构图，楼板承重按办公荷载设计",
            "site_conditions": "营业中改造，只能夜间施工",
            "deliverable_depth": "方案 + 施工图",
            "needs": "要有度假感；植物要好养；水景不能吵",
        },
        "constraints": {"style": "度假现代", "budget_cny": 2_400_000},
    },
    {
        "key": "E-office",
        "label": "办公改造（容量矛盾）",
        "expect_disciplines": {"interior", "mep"},
        "one_liner": "公司要搬办公室，一百多平，六十个人，要会议室和空调新风",
        "answers": {
            "location": "上海，租赁写字楼标准层",
            "occupants": "现在 60 人，两年内到 85 人",
            "schedule": "明年 3 月搬，租约到期不能延",
            "structure": "有物业图纸，核心筒与梁位清楚",
            "site_conditions": "租赁场地，物业对隔墙消防空调有审批",
            "deliverable_depth": "方案 + 施工图",
            "needs": "专注工作要安静；客户来了要有体面的前场",
        },
        "constraints": {"style": "", "budget_cny": 3_200_000},
        "program": [
            {"name": "开放办公区", "recipe": "open_office", "area_m2": 46, "zone": "day"},
            {"name": "会议室A", "recipe": "meeting", "area_m2": 14, "zone": "day"},
            {"name": "专注间", "recipe": "focus", "area_m2": 8, "zone": "night"},
            {"name": "接待前厅", "recipe": "reception", "area_m2": 10, "zone": "entry"},
            {"name": "打印储物", "recipe": "storage", "area_m2": 6, "zone": "service"},
        ],
        "resolve": "reduce_headcount",
    },
]


def _new_project(tmp: Path, case: Dict[str, Any]) -> Project:
    p = build_demo_project(tmp / "proj")
    p.project_id = case["key"].lower()
    p.name = case["label"]
    if case.get("program"):
        p.program = list(case["program"])
    p.constraints = dict(case.get("constraints") or {})
    p.save(tmp / "proj" / "project.json")
    return p


def _run_case(case: Dict[str, Any]) -> Dict[str, Any]:
    tmp = OUT / case["key"]
    if tmp.exists():
        shutil.rmtree(tmp)
    (tmp / "proj").mkdir(parents=True, exist_ok=True)

    p = _new_project(tmp, case)
    start_interview(p, case["one_liner"])
    scope = D.load(p)
    client = Client(dict(case["answers"]), case["key"])

    s: Dict[str, Any] = {
        "key": case["key"], "label": case["label"],
        "one_liner": case["one_liner"],
        "evidence_level": "scripted_e2e",
        "evidence_note": ("客户由脚本代理应答、几何来自 demo 壳体；"
                          "本用例证明引擎与门禁行为，不代表真实业主授权"),
        "scope": {
            "active": scope.active(),
            "active_labels": scope.labels(),
            "out_of_scope": scope.out(),
            "expected": sorted(case["expect_disciplines"]),
            "as_expected": set(case["expect_disciplines"]) <= set(scope.active()),
        },
        "stages": [], "gates": [], "errors": [],
    }

    s["rounds"] = [{"stage": "S1", "answers": _answer_round(p, client)}]

    runner = StageRunner(p, tmp / "out", project_dir=tmp / "proj",
                         assume_approval=False)

    # ---- S1 -----------------------------------------------------------
    out = runner.run_stage("S1", confirm=False)
    s["stages"].append({"id": "S1", "status": out.status, "error": out.error,
                        "next": out.next_action, "notes": out.notes[:3]})
    bundle = [f.name for f in (tmp / "proj" / "out" / "S1").glob("*")] \
        if (tmp / "proj" / "out" / "S1").exists() else []

    assessment = assess_gate(p)
    s["g1_assessment"] = {
        "blocks": [b["id"] for b in assessment.blocks_gate],
        "conditions": list(assessment.conditions)[:4],
        "needs_human": list(assessment.needs_human),
    }

    # ---- G1 -----------------------------------------------------------
    g1 = decide_gate(p, "approved", by="业主（脚本化代理）",
                     note="客户在对话中确认任务书")
    s["gates"].append({"gate": "G1", "decision": g1.decision,
                       "status": g1.stage_status, "notes": list(g1.notes)[:3]})
    if g1.decision != "approved" and case.get("resolve") == "reduce_headcount":
        # 门禁把矛盾摆出来之后，客户做取舍；系统重新判定，不强行放行
        answer_question(p, "off.headcount", "实际常驻 25 人，其余轮用工位")
        s["client_decision"] = {
            "action": "减少常驻人数到 25 人，其余轮用工位",
            "why": "人均可用面积从 2.2㎡ 提到 5.3㎡，仍属紧凑，需在方案里说明",
        }
        g1 = decide_gate(p, "approved", by="业主（脚本化代理）",
                         note="客户做出取舍后重新提交")
        s["gates"].append({"gate": "G1", "decision": g1.decision,
                           "status": g1.stage_status,
                           "notes": list(g1.notes)[:3]})
    p.save(tmp / "proj" / "project.json")

    if g1.decision != "approved":
        s["stopped_at"] = "G1"
        s["stop_reason"] = list(g1.notes)[:6]
        s["client"] = {"asked": client.asked, "repeats": client.repeats}
        return s

    # ---- S2 -----------------------------------------------------------
    out = runner.run_stage("S2", confirm=False)
    s["stages"].append({"id": "S2", "status": out.status, "error": out.error,
                        "notes": out.notes[:3]})
    concepts = (p.meta.get("concept", {}).get("options") or {}).get("concepts") or []
    s["s2"] = {
        "concepts": [c["concept_id"] for c in concepts],
        "names": [c.get("concept_name") for c in concepts],
        "families": sorted({((c.get("spatial_prototype") or {}).get("family") or "")
                            for c in concepts}),
        "per_concept_disciplines": {
            c["concept_id"]: sorted((c.get("disciplines") or {}).keys())
            for c in concepts
        },
    }
    # 各专业方向是否真的因概念而异
    struct_texts = {c["concept_id"]: ((c.get("disciplines") or {})
                                     .get("structure") or {}).get("strategy", "")
                    for c in concepts}
    s["s2"]["structure_directions_distinct"] = len(set(struct_texts.values())) == len(
        [v for v in struct_texts.values() if v])

    if out.status != "ok" or not concepts:
        s["stopped_at"] = "S2"
        s["stop_reason"] = [out.error or "无概念产出"]
        s["client"] = {"asked": client.asked, "repeats": client.repeats}
        return s

    # ---- G2 -----------------------------------------------------------
    supported = [c for c in concepts
                 if (c.get("spatial_prototype") or {}).get("plan_strategy")]
    pick = supported[0] if supported else concepts[0]
    C.select(p, pick["concept_id"])
    g2 = runner.approve("S2", by="业主（脚本化代理）")
    s["gates"].append({"gate": "G2", "decision": g2["status"],
                       "notes": list(g2.get("notes") or [])[:4],
                       "concept": pick["concept_id"],
                       "has_supported_strategy": bool(supported)})
    base_files = [f.name for f in (tmp / "out").rglob(
        "multidisciplinary-concept-baseline-r*.json")]
    s["s2"]["multidisciplinary_baseline"] = base_files[:1]

    if g2["status"] != "confirmed":
        s["stopped_at"] = "G2"
        s["stop_reason"] = list(g2.get("notes") or [])[:6]
        s["client"] = {"asked": client.asked, "repeats": client.repeats}
        return s

    # ---- S3 -----------------------------------------------------------
    out = runner.run_stage("S3", confirm=False)
    s["stages"].append({"id": "S3", "status": out.status, "error": out.error,
                        "next": out.next_action, "notes": out.notes[:3]})
    if out.status != "ok":
        s["stopped_at"] = "S3"
        s["stop_reason"] = [out.error or out.status]
        s["client"] = {"asked": client.asked, "repeats": client.repeats}
        return s

    g3 = runner.approve("S3", by="业主（脚本化代理）")
    s["gates"].append({"gate": "G3", "decision": g3["status"],
                       "notes": list(g3.get("notes") or [])[:5]})
    if g3["status"] != "confirmed":
        s["stopped_at"] = "G3"
        s["stop_reason"] = list(g3.get("notes") or [])[:6]
        s["client"] = {"asked": client.asked, "repeats": client.repeats}
        return s

    # 走到这里说明范围与几何都成立，后面的阶段按领域能力跑。
    # 真实路径是"跑一阶段 → 业主确认 → 再跑下一阶段"，不能一口气跑完再补签：
    # 那样 S6 会正确地拒绝在未确认的上游成果上继续。
    for sid in ("S4", "S5", "S6", "S7", "S8"):
        o = runner.run_stage(sid, confirm=False)
        s["stages"].append({"id": sid, "status": o.status, "error": o.error,
                            "next": o.next_action, "notes": o.notes[:2]})
        if o.status not in ("ok", "skipped", "degraded"):
            s["stopped_at"] = sid
            s["stop_reason"] = [o.error or o.status]
            break
        gate = "G" + sid[1:]
        res = runner.approve(sid, by="业主（脚本化代理）")
        s["gates"].append({"gate": gate, "decision": res["status"],
                           "notes": list(res.get("notes") or [])[:2]})
        if res["status"] != "confirmed":
            s["stopped_at"] = gate
            s["stop_reason"] = list(res.get("notes") or [])[:5]
            break
    else:
        s["stopped_at"] = ""

    s["s1_bundle"] = bundle
    s["client"] = {"asked": client.asked, "repeats": client.repeats}
    return s


def _run_change_case() -> Dict[str, Any]:
    """F 案：先确认综合概念，再加泳池/屋顶花园，看影响是否跨专业。"""
    tmp = OUT / "F-change"
    if tmp.exists():
        shutil.rmtree(tmp)
    (tmp / "proj").mkdir(parents=True, exist_ok=True)
    p = build_demo_project(tmp / "proj")
    p.project_id = "f-change"
    p.name = "别墅变更"
    p.save(tmp / "proj" / "project.json")
    start_interview(p, "三层别墅，带庭院水池，室内精装，结构机电一并考虑")
    decide_gate(p, "approved", by="业主（脚本化代理）")

    reqs = ["院子里加一个泳池", "屋顶改成花园", "客厅墙面换个颜色"]
    rows = []
    for req in reqs:
        rep = changes.analyse(p, req, apply=False)
        d = rep.to_dict()
        rows.append({
            "request": req,
            "domain": d["diagnosis"]["label"],
            "landing_stage": d["diagnosis"]["landing_stage"],
            "scope": d["scope"],
            "cross_discipline": [
                {"id": x["id"], "disciplines": x["disciplines"],
                 "not_just": x["not_just"]}
                for x in rep.cross_discipline
            ],
            "risks": rep.risks[:4],
            "applied": d["applied"],
        })
    return {
        "key": "F-change", "label": "综合项目变更（先确认，再加泳池/屋顶花园）",
        "evidence_level": "scripted_e2e",
        "one_liner": "三层别墅，带庭院水池，室内精装，结构机电一并考虑",
        "scope": {"active": D.load(p).active(), "active_labels": D.load(p).labels()},
        "changes": rows,
        "note": "变更只做影响分析，未自动应用到项目（applied=False）。",
    }


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    results: List[Dict[str, Any]] = []
    for case in CASES:
        try:
            r = _run_case(case)
        except Exception as exc:                        # noqa: BLE001
            r = {"key": case["key"], "label": case["label"],
                 "error": f"{type(exc).__name__}: {exc}",
                 "trace": traceback.format_exc()[-800:]}
        results.append(r)
        (OUT / case["key"] / "session.json").write_text(
            json.dumps(r, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"[{r.get('key')}] scope={'/'.join(r.get('scope', {}).get('active_labels') or [])}"
              f" stopped_at={r.get('stopped_at', '-')}")

    try:
        f = _run_change_case()
    except Exception as exc:                            # noqa: BLE001
        f = {"key": "F-change", "error": f"{type(exc).__name__}: {exc}"}
    results.append(f)
    (OUT / "F-change").mkdir(parents=True, exist_ok=True)
    (OUT / "F-change" / "session.json").write_text(
        json.dumps(f, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[F-change] cross={len(f.get('changes') or [])}")

    summary = {
        "evidence_level": "scripted_e2e",
        "note": ("六组案例覆盖六种范围不同的委托。跑不到的阶段记 stopped_at，"
                 "不写成通过。"),
        "cases": [
            {
                "key": r.get("key"), "label": r.get("label"),
                "scope": r.get("scope", {}).get("active"),
                "scope_as_expected": (r.get("scope", {}).get("as_expected")
                                      if "as_expected" in (r.get("scope") or {}) else None),
                "stages": [(x["id"], x["status"]) for x in (r.get("stages") or [])],
                "gates": [(g["gate"], g.get("decision")) for g in (r.get("gates") or [])],
                "stopped_at": r.get("stopped_at"),
                "repeats": (r.get("client") or {}).get("repeats"),
                "changes": len(r.get("changes") or []),
            }
            for r in results
        ],
    }
    (OUT / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary["cases"], ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
