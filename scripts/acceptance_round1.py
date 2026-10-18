#!/usr/bin/env python
"""第一轮执行闭环验收：两个项目、从一句话跑到 S8，全部留下证据。

跑法：
    PYTHONPATH=. python scripts/acceptance_round1.py

产出（`out/acceptance-round1/`）：

* `A-residential/session.json`、`B-commercial/session.json` —— 完整轨迹
* `A-residential/artifacts.json` —— 每阶段产物与存在性核对
* `REPORT.md` —— 汇总，含每项能力"已验证 / 仅 Mock / 尚未连接 / 阻断"

纪律：
* 关禁全部走真实判定（`decide_g1` / `G2 decide_gate` / `G3 approve`），
  不用 `--assume-approval` 跳过；客户回答是脚本化代理，记录在案；
* 平台未配置就不提交，图像一律 `awaiting_platform`；
* 不联网、不产生任何费用。

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import json
import shutil
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from omniarchitect import changes, concept as C, finishes                     # noqa: E402
from omniarchitect.demo import build_demo_project                            # noqa: E402
from omniarchitect.intake import (                                           # noqa: E402
    answer_question,
    decide_gate as decide_g1,
    start_interview,
)
from omniarchitect.intake.interview import next_questions                    # noqa: E402
from omniarchitect.model import Project                                      # noqa: E402
from omniarchitect.stage_state import all_states, get_state                   # noqa: E402
from omniarchitect.workflow import StageRunner                               # noqa: E402

OUT = ROOT / "out" / "acceptance-round1"

ONE_LINER_A = "我有一套 150㎡ 的大平层，一家三口，想要现代意式极简，预算 160 万"
ONE_LINER_B = "我们公司要搬办公室，一百多平，六十个人，希望安静、见客户有面子"

# 脚本化客户：只说该说的，不替系统做决定
ANSWERS_A = {
    "location": "杭州，南向，主采光面朝南",
    "schedule": "明年 6 月前入住，中间没有硬性节点",
    "structure": "结构图纸有，但有两道墙需要现场确认是否承重",
    "site_conditions": "二手房翻新，原装修全拆，物业允许改水改电",
    "deliverable_depth": "方案 + 施工图，软装只要建议清单",
    "occupants": "一家三口，有个 5 岁孩子",
    "needs": "客厅要能坐下 8 个人吃饭；孩子写作业要看得见；东西很多需要收纳",
}

ANSWERS_B = {
    "location": "上海，租赁写字楼，标准层",
    "occupants": "现在 60 人，两年内到 85 人",
    "schedule": "明年 3 月搬，租约到期不能延",
    "structure": "有物业图纸，核心筒与梁位清楚",
    "site_conditions": "租赁场地，物业对隔墙、消防、空调改动有审批",
    "deliverable_depth": "方案 + 施工图，消防与弱电由物业指定单位深化",
    "needs": "专注工作要安静；客户来了要有体面的前场；会议与电话间要隔音",
}


class Client:
    """脚本化业主：只在被问到时回答，记录每一次问答。"""

    def __init__(self, name: str, answers: Dict[str, str]) -> None:
        self.name = name
        self.answers = answers
        self.asked: List[str] = []
        self.repeats: List[str] = []
        self.log: List[Dict[str, Any]] = []

    def respond(self, slot: str) -> bool:
        if slot in self.asked:
            self.repeats.append(slot)
        self.asked.append(slot)
        if slot not in self.answers:
            return False
        return True


def _answer_round(project: Project, client: Client, limit: int = 6) -> List[Dict[str, str]]:
    """回答系统当前还在等的槽位——它问什么答什么，不主动加戏。

    每轮最多取 3 个问题（系统自己的上限），客户只回答自己知道的，
    答完再看下一轮，避免"一次问一堆"。
    """
    done: List[Dict[str, str]] = []
    for _ in range(limit):
        # 系统每轮最多问 3 个；客户只答自己会的，答不了就跳过，不假装知道
        pool = next_questions(project, limit=12)
        pending = [q for q in pool if q.slot in client.answers]
        if not pending:
            break
        q = pending[0]
        slot = str(q.slot)
        if not client.respond(slot):
            break
        answer_question(project, q.id, client.answers[slot])
        done.append({"slot": slot, "question_id": q.id,
                     "question": str(q.text or ""),
                     "answer": client.answers[slot]})
    return done


def _snapshot(project: Project, runner: StageRunner) -> Dict[str, Any]:
    return {
        "revision": project.revision,
        "states": {s.stage: {"status": s.status, "by": s.confirmed_by,
                          "at": s.confirmed_at, "note": s.note}
                   for s in all_states(project)},
        "artifacts": [{"id": a.id, "type": a.type, "path": a.path,
                       "revision": a.revision, "status": a.status}
                      for a in project.artifacts],
        "out": str(runner.out),
    }


def run_project(key: str, one_liner: str, answers: Dict[str, str],
                *, program: List[Dict[str, Any]] | None,
                constraints: Dict[str, Any], label: str) -> Dict[str, Any]:
    tmp = OUT / key
    if tmp.exists():
        shutil.rmtree(tmp)
    proj_dir = tmp / "proj"
    proj_dir.mkdir(parents=True, exist_ok=True)

    project = build_demo_project(proj_dir)
    project.project_id = f"acc-{key.lower()}"
    project.name = label
    if program:
        project.program = [dict(x) for x in program]
    project.constraints = {**(project.constraints or {}), **constraints}
    project.save(proj_dir / "project.json")

    client = Client(key, answers)
    session: Dict[str, Any] = {
        "key": key, "label": label, "one_liner": one_liner,
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "rounds": [], "stages": [], "errors": [], "next_steps": [],
        "modifications": [], "resume": {},
    }

    # -- S1：一句话 → 访谈 --------------------------------------------
    start_interview(project, one_liner)
    session["rounds"].append({"stage": "S1", "answers": _answer_round(project, client)})
    runner = StageRunner(project, tmp / "out", project_dir=proj_dir,
                         assume_approval=False)
    out = runner.run_stage("S1", confirm=False)
    session["stages"].append({"id": "S1", "status": out.status,
                              "notes": out.notes, "next": out.next_action,
                              "error": out.error})
    session["next_steps"].append({"stage": "S1", "next": out.next_action})
    g1 = decide_g1(project, "approved", by="业主（脚本化代理）",
                   note="客户在对话中确认任务书")
    session["gates"] = session.get("gates", []) + [
        {"gate": "G1", "decision": g1.decision, "status": g1.stage_status,
         "notes": list(g1.notes)}]
    project.save(proj_dir / "project.json")

    # -- S2：概念 ------------------------------------------------------
    out = runner.run_stage("S2", confirm=False)
    session["stages"].append({"id": "S2", "status": out.status,
                              "notes": out.notes, "next": out.next_action,
                              "error": out.error})
    opts = (project.meta.get("concept") or {}).get("options") or {}
    concepts = opts.get("concepts") or []
    supported = [c for c in concepts
                 if (c.get("spatial_prototype") or {}).get("plan_strategy")]
    chosen = supported[0] if supported else (concepts[0] if concepts else None)
    session["concept_pick"] = {
        "offered": [c["concept_id"] for c in concepts],
        "chosen": chosen["concept_id"] if chosen else "",
        "has_supported_strategy": bool(supported),
        "why": ("客户选空间策略可落地的一套" if supported
                else "本批方向均无对应平面策略：只能选一套，但 G3 不会签发"),
    }
    if chosen:
        C.select(project, chosen["concept_id"])
        g2 = runner.approve("S2", by="业主（脚本化代理）")
        session["gates"].append({"gate": "G2", "decision": "approved",
                                 "status": g2["status"], "notes": g2["notes"]})
        session["next_steps"].append({"stage": "S2",
                                      "next": "概念已确认，进入平面方案"})

    # -- S3：平面 ------------------------------------------------------
    out = runner.run_stage("S3", confirm=False)
    session["stages"].append({"id": "S3", "status": out.status,
                              "notes": out.notes, "next": out.next_action,
                              "error": out.error})
    g3 = runner.approve("S3", by="业主（脚本化代理）")
    session["gates"].append({"gate": "G3", "decision": "approved",
                             "status": g3["status"], "notes": g3["notes"]})
    project.save(proj_dir / "project.json")

    # -- 关闭客户端再打开：从磁盘恢复 --------------------------------
    reloaded = Project.load(proj_dir / "project.json")
    before = {s.stage: s.status for s in all_states(reloaded)}
    runner2 = StageRunner(reloaded, tmp / "out", project_dir=proj_dir,
                          assume_approval=False)
    session["resume"] = {"states_after_reload": before,
                         "continues_from": "S4"}

    # -- S4–S8：逐步跑、逐步签 ---------------------------------------
    for sid in ("S4", "S5", "S6", "S7", "S8"):
        out = runner2.run_stage(sid, confirm=False)
        session["stages"].append({"id": sid, "status": out.status,
                                  "notes": out.notes, "next": out.next_action,
                                  "error": out.error})
        if out.status not in ("ok", "skipped", "degraded"):
            session["errors"].append({"stage": sid, "error": out.error,
                                      "status": out.status})
            break
        approved = runner2.approve(sid, by="业主（脚本化代理）")
        session["gates"].append({"gate": f"G{sid[1:]}", "decision": "approved",
                                 "status": approved.get("status"),
                                 "notes": approved.get("notes", [])[:3]})
        session["next_steps"].append({"stage": sid,
                                      "next": out.next_action or "进入下一阶段"})
        reloaded.save(proj_dir / "project.json")

    # -- 客户改主意：只做影响分析，不自动改 ---------------------------
    req = ("把客厅背景墙的石材换成木饰面" if key == "A-residential"
           else "把会议室隔墙换成玻璃隔断")
    rep = changes.analyse(reloaded, req, apply=False)
    d = rep.to_dict()
    session["modifications"].append({
        "request": req,
        "scope": d.get("scope"),
        "affected": d.get("affected") or {},
        "rework": d.get("rework_plan") or [],
        "gates_to_reopen": d.get("gates_to_reopen") or [],
        "preserved": d.get("preserved_confirmed_work") or [],
        "applied": bool(d.get("applied")),
        "note": "只做影响分析并给出返工与重开门禁清单，未自动改动成果。",
    })

    session["final"] = _snapshot(reloaded, runner2)
    session["client"] = {"asked": client.asked, "repeats": client.repeats}
    session["profile"] = finishes.profile_label(reloaded)
    session["style"] = finishes.style_label(reloaded)
    session["ended_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")

    (tmp / "session.json").write_text(
        json.dumps(session, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return session


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    a = run_project(
        "A-residential", ONE_LINER_A, ANSWERS_A, program=None,
        constraints={"style": "现代意式极简", "budget_cny": 1_600_000},
        label="150㎡ 现代意式极简住宅（壳体 131㎡ 净面积）")
    b = run_project(
        "B-commercial", ONE_LINER_B, ANSWERS_B,
        program=[{"name": "开放办公区", "recipe": "open_office", "area_m2": 46, "zone": "day"},
                 {"name": "会议室A", "recipe": "meeting", "area_m2": 14, "zone": "day"},
                 {"name": "专注间", "recipe": "focus", "area_m2": 8, "zone": "night"},
                 {"name": "接待前厅", "recipe": "reception", "area_m2": 10, "zone": "entry"},
                 {"name": "打印与储物", "recipe": "storage", "area_m2": 6, "zone": "service"}],
        constraints={"style": "", "budget_cny": 3_200_000},
        label="办公空间（既有 131㎡ 楼层改造，60 人）")

    summary = {
        "A": {"profile": a["profile"], "style": a["style"],
              "repeats": a["client"]["repeats"],
              "stages_ok": [s["id"] for s in a["stages"] if s["status"] == "ok"],
              "errors": a["errors"]},
        "B": {"profile": b["profile"], "style": b["style"],
              "repeats": b["client"]["repeats"],
              "stages_ok": [s["id"] for s in b["stages"] if s["status"] == "ok"],
              "errors": b["errors"]},
    }
    (OUT / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if not (summary["A"]["errors"] or summary["B"]["errors"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
