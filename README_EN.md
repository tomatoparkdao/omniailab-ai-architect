<h1 align="center">OmniAiLab AI Architect &amp; Interior Designer</h1>

<p align="center">
  <b>An end-to-end AI chief-designer Skill for architecture and interior design — and a design system that forces a decision at every gate</b><br>
  Eight business stages, 29 professional capabilities&nbsp;&nbsp;|&nbsp;&nbsp;Brief to construction drawings and schedules&nbsp;&nbsp;|&nbsp;&nbsp;Editable DXF, 3D meshes and editable PPTX
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Version-1.1.0-1f6feb?style=flat-square" alt="Version 1.1.0">
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-2ea043?style=flat-square" alt="License MIT"></a>
  <a href="https://omniailab.cn/"><img src="https://img.shields.io/badge/Platform-OmniAiLab-8957e5?style=flat-square" alt="Platform OmniAiLab"></a>
  <img src="https://img.shields.io/badge/Pipeline-8_stages_%C3%97_29_capabilities-db6d28?style=flat-square" alt="8 stages × 29 capabilities">
  <img src="https://img.shields.io/badge/Works_with-Codex_%7C_Claude_%7C_WorkBuddy_%7C_OmniAiLab-0969da?style=flat-square" alt="Works with Codex / Claude / WorkBuddy / OmniAiLab">
</p>

<p align="center">
  <a href="README.md">简体中文</a>&nbsp;&nbsp;|&nbsp;&nbsp;<b>English</b>
</p>

> © OmniAiLab ｜ Developer: Mochiball ｜ Platform: [omniailab.cn](https://omniailab.cn/)

**An end-to-end AI chief-designer Skill for architecture and interior design.** It does not just answer questions: **it starts by demanding the client's brief and the existing conditions**, turns them into a brief that can be signed off, then moves through eight stages the way a real project does — concept, plan layout, preliminary design, 3D and visualisation, design freeze, construction drawings, schedules and delivery. **One confirmation gate at the end of every stage**: you answer "confirmed" or "change item X". Every drawing, model, render, schedule and deck reads **the same** updated spatial dataset — one change never produces eight contradictory interpretations.

| Item | Value | Notes |
|---|---|---|
| Skill invocation name (unique ID) | `omniailab-ai-architect` | All-lowercase with hyphens. Tools with native Skill support invoke it directly; tools without it also trigger it from a natural-language task description |
| Display name | OmniAiLab AI Architect & Interior Designer | The name shown on the repository page and in the docs — not the invocation name |
| Version | v1.1.0 | Kept identical across `VERSION`, `pyproject.toml`, `SKILL.md` and this README |
| Publisher / Developer | OmniAiLab / Mochiball | — |
| License | MIT (see [LICENSE](LICENSE)) | Use and redistribution are governed by that file |
| Native platform | [OmniAiLab international](https://omniailab.cn/) / [China](https://www.omniailabx.com/) | Generative image and video capabilities come from the platform; **the Skill runs fully without it** |
| Requirements | Python 3.11+ | Zero hard dependencies: DXF, mesh and PPTX all have built-in writers |
| Open-source repo | Not published yet | Distributed as a local folder for now |

The invocation name is **all-lowercase with hyphens** (`omniailab-ai-architect`) — it is not the display name. Tools with native Skill support work best with the invocation name; tools without it will still trigger on a natural-language description.

---

## In one sentence

Hand it a requirement — even just a floor plan plus "make it Italian minimalist" — and it will first pin down function and budget, then move stage by stage to deliverable drawings, models and schedules. At the end of each stage you only answer "confirmed" or "change item X".

- **Any project type** — apartments, large flats, villas, offices, retail, restaurants, hotels, showrooms; schematic depth and construction depth are both in scope.
- **Controllable depth** — "just compare two layouts", or "layouts + 3D + a render task package + construction-depth DXF + schedules + a presentation deck"; the same pipeline serves both.
- **Explicitly out of scope** — final conclusions on structural safety, fire, accessibility, MEP loads or local code compliance are **not** this system's call. It flags issues and produces a to-be-reviewed list; a licensed professional must verify and sign off locally.

---

## What's inside

**Not "a template that runs a pipeline", but a design system that asks first, writes its reasoning into the drawings, and states its missing capabilities out loud.**

| Layer | What it gives you |
|---|---|
| **① Stages separate from capabilities** | Eight **business stages** control pace and gates; 29 **professional capabilities** (brief, site analysis, concept, space planning, ergonomics, interiors, materials, lighting, MEP coordination, CAD drafting, BIM, 3D, rendering, walkthrough, construction detailing, quantities, review, presentation, delivery…) carry the professional method. Capabilities are reused across stages and never nailed to one step. |
| **② One geometric authority** | The Canonical Spatial Model is the single geometric source for every deliverable. Move a wall 300 mm outward and the system recomputes plans, elevations, ceilings, lighting positions, furniture clearances, quantities and drawings by dependency — **already-confirmed work that is unaffected stays valid** instead of being rebuilt wholesale. |
| **③ Changes go through impact analysis** | Every change is diagnosed (11 change domains) → its blast radius located (including boundary elements of the affected rooms) → a rework plan and the list of gates to reopen. A material change does not invalidate geometry; a dimension change invalidates everything downstream. The program decides this, not your memory. |
| **④ Judgements have a source** | Nine **design criteria** sets: aesthetic control baseline, concept-diagram language, moodboard iteration loop, MEP spatial impact, annotation ledger, proposal layout, project fit, cost/quantity separation, tool safety tiers. Each is written as a decidable statement ("warm surfaces ≤40%", "black 3–8%", "one dominant line for the whole space") — not as an adjective. |
| **⑤ It actually writes files** | Editable DXF (schematic and construction depth kept apart), OBJ 3D meshes, schematics, editable PPTX decks, Markdown and print-ready HTML, quantity and cost-estimate JSON, change-impact reports. **Every written file is re-read by an independent implementation**; if it cannot be read back, the step failed. |
| **⑥ It does not pretend** | No Blender / FreeCAD / IfcOpenShell → it emits **runnable scripts** and marks the stage `degraded`; platform not configured → `NOT_CONFIGURED` with the exact missing pieces; DXF is never renamed to DWG, a triangle mesh is never called parametric BIM, a render is never a dimensional reference. |

---

## The eight-stage workflow

| Stage | Name | Deliverables | Gate |
| --- | --- | --- | --- |
| S1 | Project start & design brief | Design brief, existing-conditions report | G1 brief confirmed |
| S2 | Concept design | Concept options, aesthetic direction board | G2 concept confirmed |
| S3 | Plan layout | Two to three comparable layouts, comparison | G3 layout confirmed |
| S4 | Preliminary design & development | Preliminary drawings, material and lighting scheme | G4 preliminary confirmed |
| S5 | 3D modelling & visualisation | 3D model, spatial renders, walkthrough | G5 visual confirmed |
| S6 | Design freeze & technical coordination | Frozen scheme, basis for detailing | G6 design locked |
| S7 | CAD / BIM construction drawings | Construction drawings, BIM model, review record | G7 drawings reviewed |
| S8 | Schedules & delivery | Material schedule, quantity list, delivery set | G8 delivery confirmed |

### Four non-negotiable professional rules

1. **No detailed modelling before the client confirms the functional brief;**
2. **CAD starts at S4** — the difference is `schematic` vs `construction` depth, not whether drawings exist at all;
3. **Cost and quantities are estimated dynamically from S1**, and only become a formal schedule at S8;
4. **No formal drawings before the layout is confirmed**; once locked, no local hand-editing — changes go through impact analysis.

---

## Quick start

### 1. Where to install

Copy the **entire `omniailab-ai-architect` folder** (including `SKILL.md`, `omniailab_ai_architect/`, `knowledge/`, `cases/`, `skills/`, `schemas/`, `workflows/`) into the folder below, then open a new session.

| Tool | Where | How to invoke |
|---|---|---|
| **WorkBuddy** | User-level: `~/.workbuddy/skills/omniailab-ai-architect/`<br>Project-level: `<project>/.workbuddy/skills/omniailab-ai-architect/` | It appears in the skill list; say `$omniailab-ai-architect start` |
| **Codex** | Put it in the project, e.g. `<project>/skills/omniailab-ai-architect/`, and add one line to the project `AGENTS.md`: `Design tasks: read skills/omniailab-ai-architect/SKILL.md first and follow it` | Say "start the design following SKILL.md" |
| **Claude / Claude Code** | Personal: `~/.claude/skills/omniailab-ai-architect/`<br>Project: `<project>/.claude/skills/omniailab-ai-architect/` | Type `/omniailab-ai-architect`, or describe the task |
| **OmniAiLab** | Into the client's skills folder (the client shows the location) | It appears in the skill list |
| **Other agents** | Any runtime that supports a standard `SKILL.md` | See [compatibility/agent-skills.md](compatibility/agent-skills.md) |

A bundled installer can detect the runtimes on your machine:

```bash
python installer/install.py --dry-run          # see what would happen first
python installer/install.py                    # pointer-install into detected runtimes
python installer/install.py --target ~/.codex/skills --mode copy
python installer/verify_install.py --check-python
```

> Install and uninstall **never delete content**: an existing target is moved into `_backup/`. **No OmniAiLab registration is required and no platform key is ever read.**

### 2. Run it

```bash
export PYTHONPATH=<your path>/omniailab-ai-architect

python -m omniailab_ai_architect doctor                 # toolchain check
python -m omniailab_ai_architect stages                 # the eight stages and their gates
python -m omniailab_ai_architect demo --out out         # sample project, all eight stages
python -m omniailab_ai_architect scenario --name all    # acceptance: Scenario A/B/C
```

### 3. Drive a real project

```bash
python -m omniailab_ai_architect status  --project projects/demo-120
python -m omniailab_ai_architect route   --project projects/demo-120 "Italian minimalist, give me two layouts first"
python -m omniailab_ai_architect run     --project projects/demo-120 --from-stage S3
python -m omniailab_ai_architect confirm --project projects/demo-120 --stage S3 --by client
python -m omniailab_ai_architect change  --project projects/demo-120 "move the kitchen/dining wall 300mm outward"
python -m omniailab_ai_architect present --project projects/demo-120 --kind plan-comparison
```

`route` turns one sentence into an explicit stage plan: which stages run, who owns them, who confirms at the gate, and which actions are blocked right now.

---

## What you actually get

| Type | File | Notes |
| --- | --- | --- |
| CAD drawings | `.dxf` | Schematic and construction depth named apart; re-read by an independent parser to check entity counts, layers and closure |
| 3D model | `.obj` | Millimetres, Z-up, material groups; a mesh is **never** passed off as parametric BIM |
| Spatial schematic | `.png` | Rasterised from the canonical model, always stamped "schematic · not a photoreal render · not a dimensional reference" |
| Design deck | `.pptx` / `.md` / `.html` | Editable PPTX — nine deck types: concept, plan comparison, preliminary, visual, final, materials & lighting, technical briefing, delivery, full |
| Quantities & estimate | `.json` / tables | Per-room quantities, cost/quantity separation, budget-fit conclusion |
| Impact analysis | `.json` / `.md` | Diagnosis, blast radius, rework stages, gates to reopen, confirmed work preserved |
| Delivery set | `README.md` + index | File index, open items, boundary statement and signature |

---

## Tools, permissions and platform

The tool registry states **what each tool can do, how risky it is, and how strong its output may be called**.

| Tier | Meaning | Confirmation |
| --- | --- | --- |
| L1 | Read-only: parse drawings, query state | No |
| L2 | Local write: create/modify files inside the project | No |
| L3 | Network: call external services or model providers | **Yes** |
| L4 | Execute/send: run third-party code, drive host software | **Yes, and a dry-run first** |

```bash
python -m omniailab_ai_architect tools     # registry + permission tiers
python -m omniailab_ai_architect honesty   # the list of claims we may not make
python -m omniailab_ai_architect providers # platform and generative provider status
```

**Platform integration is discovered, not guessed**: official SDK, local config, a platform-issued API contract, environment variables. With none of them the state is `NOT_CONFIGURED` and the missing pieces are listed explicitly. No endpoint, parameter or auth scheme is ever invented; see [docs/OMNIAILAB_INTEGRATION.md](docs/OMNIAILAB_INTEGRATION.md).

---

## Documentation map

| To learn about | Read |
| --- | --- |
| How the eight stages and gates work | [docs/WORKFLOW.md](docs/WORKFLOW.md) |
| How the system is layered | [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) |
| What the judgements are based on | [docs/DESIGN_CRITERIA.md](docs/DESIGN_CRITERIA.md) |
| How to connect the platform | [docs/OMNIAILAB_INTEGRATION.md](docs/OMNIAILAB_INTEGRATION.md) |
| Tools and permissions | [docs/MCP_TOOLS.md](docs/MCP_TOOLS.md) |
| Install and standalone use | [docs/INSTALL.md](docs/INSTALL.md) |
| Decks and PPTX output | [docs/PRESENTATION.md](docs/PRESENTATION.md) |
| Content compliance self-check | [docs/CONTENT_AUDIT.md](docs/CONTENT_AUDIT.md) |
| Design knowledge (12 domains) | [knowledge/INDEX.md](knowledge/INDEX.md) |
| Project-type case criteria | [cases/](cases/) |
| Development conventions (for coding agents) | [AGENTS.md](AGENTS.md) |
| Version history | [CHANGELOG.md](CHANGELOG.md) |

---

## FAQ

**Will it claim work it did not do?**
No. This is a hard rule backed by tests: DXF is not renamed DWG, a triangle mesh is not parametric BIM, an AI render is not a dimensional reference, and without an IFC writer we only claim "IFC projection data + a build script". When a tool is missing the stage is marked `degraded` with the reason.

**Does it need network access or registration?**
No. `doctor`, `stages`, `demo`, `scenario` and DXF / mesh / PPTX export all run locally. Platform capabilities are for photoreal renders and video; when absent, the degraded path is used.

**Does it make decisions for me?**
It never says "either works". A comparison gives a recommendation, the reasoning and the alternatives; the decision and the gate confirmation belong to the client or the lead designer.

**Can I ask for just one small piece?**
Yes. `route` closes over prerequisites: say "just draw the ceiling construction plan" and it brings along the upstream stages that must already be confirmed, instead of starting from zero.

---

## Disclaimer and boundaries

- Structural safety, fire, accessibility, MEP loads and local code compliance are **out of scope** and must be verified and signed by a licensed professional in the project's jurisdiction;
- Schematic-depth output **must not** be used as construction drawings; generated images **must not** be used as dimensional references;
- Quantities and cost figures are schematic-stage estimates and **do not constitute a settlement basis**;
- The authors and maintainers accept no liability for any loss arising from use of this Skill.

---

## Credits

- Published and maintained by **OmniAiLab** ([omniailab.cn](https://omniailab.cn/) · [omniailabx.com](https://www.omniailabx.com/))
- Developer: **Mochiball**
- The design knowledge (`knowledge/`, 12 domains), project-type cases (`cases/`), capability briefs (`skills/`) and design criteria ([docs/DESIGN_CRITERIA.md](docs/DESIGN_CRITERIA.md)) are **written from scratch** for this project, drawing on general design principles and published engineering practice. Nothing is copied from or paraphrased out of any external document.
- The native platform for this Skill is **OmniAiLab**; external tools such as Blender / FreeCAD / AutoCAD / IfcOpenShell are covered by **adapter declarations and degraded paths only** — no code from them is bundled and none of them is required.

---

<div align="right">

[简体中文](README.md) ｜ **English**

</div>

> © OmniAiLab ｜ Developer: Mochiball ｜ omniailab.cn
