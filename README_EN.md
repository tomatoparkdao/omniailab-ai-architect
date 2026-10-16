<h1 align="center">OmniAiLab AI Architect</h1>

<p align="center">
  <b>An end-to-end AI chief-designer Skill for architecture and interior design — and a design system that forces a judgement at every key point</b><br>
  Eight business stages running 30 professional capabilities　｜　From the design brief to construction drawings and material schedules　｜　Produces editable DXF, 3D models, AI concept renderings and editable PPTX
</p>

<p align="center">
  <a href="https://github.com/tomatoparkdao/omniailab-ai-architect"><img src="https://img.shields.io/badge/%E7%89%88%E6%9C%AC-1.3.0-1f6feb?style=flat-square" alt="版本 1.3.0"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/%E8%AE%B8%E5%8F%AF-MIT-2ea043?style=flat-square" alt="许可 MIT"></a>
  <a href="https://www.omniailabx.com/"><img src="https://img.shields.io/badge/%E5%B9%B3%E5%8F%B0-OmniAiLab-8957e5?style=flat-square" alt="平台 OmniAiLab"></a>
  <a href="https://zcn03zgas1zl.feishu.cn/wiki/K1IWwPuBDiQXufkS76Yc3EMPnTd"><img src="https://img.shields.io/badge/%E6%89%8B%E5%86%8C-%E9%A3%9E%E4%B9%A6%E4%B8%BB%E6%96%87%E6%A1%A3-db6d28?style=flat-square" alt="操作手册（飞书）"></a>
  <img src="https://img.shields.io/badge/%E6%B5%81%E7%A8%8B-8_%E9%98%B6%E6%AE%B5_%C3%97_30_%E8%83%BD%E5%8A%9B-0969da?style=flat-square" alt="8 阶段 × 30 能力">
  <img src="https://img.shields.io/badge/%E5%85%BC%E5%AE%B9-Codex_%7C_Claude_%7C_Cursor_%7C_WorkBuddy-6f42c1?style=flat-square" alt="兼容 Codex / Claude / Cursor / WorkBuddy">
</p>

<p align="center">
  <b>English</b>　｜　<a href="README.md">简体中文</a>
</p>

> © OmniAiLab ｜ Developer: Mochiball ｜ Platform: [omniailabx.com](https://www.omniailabx.com/) ｜ Repo: [tomatoparkdao/omniailab-ai-architect](https://github.com/tomatoparkdao/omniailab-ai-architect)

---

## In one sentence

Hand it one requirement — even just a floor plan plus a line like "make it Italian minimalist" — and it first pins down function and budget, then advances stage by stage to deliverable drawings, models and schedules. At the end of every stage you only answer "confirmed" or "change item X".

| Scope | What it covers |
|---|---|
| **Applicable · any project type** | Residential flats, large flats, villas, offices, retail, restaurants, hotels, showrooms; both the schematic stage and the development stage are in scope |
| **Applicable · controllable depth** | Ask for "just compare two layouts", or ask for "layouts + 3D + a render task package + construction-depth DXF + material schedules + a presentation deck"; the same single pipeline serves them on demand |
| **Not applicable (said plainly)** | **Final conclusions** on structural safety, fire, accessibility, MEP loads and local code compliance are **not** this system's conclusions; the system only flags issues and gives a to-be-reviewed list, which a licensed professional must verify and sign off in the project's jurisdiction |

| Item | Value | Notes |
|---|---|---|
| Skill invocation name (unique ID) | `omniailab-ai-architect` | All-lowercase with hyphens; tools that support skills invoke it directly, and tools that do not still trigger it from a natural-language description |
| Display name | OmniAiLab AI Architect & Interior Designer | The name shown on the repository page and in the docs — not the invocation name |
| Version | v1.3.0 | Kept identical across `VERSION`, `pyproject.toml`, `SKILL.md` and `installer/manifest.json` |
| Publisher / Developer | OmniAiLab / Mochiball | — |
| License | MIT (see [LICENSE](LICENSE)) | Use and redistribution are governed by that file |
| Native platform | [OmniAiLab China site](https://www.omniailabx.com/) / [International site](https://omniailab.cn/) | Generative image and video capabilities come from the platform; **the system runs normally when it is not connected** |
| Requirements | Python 3.10+ | Zero hard dependencies: DXF, mesh and PPTX all have built-in writers |
| Open-source repo | [tomatoparkdao/omniailab-ai-architect](https://github.com/tomatoparkdao/omniailab-ai-architect) | All source, documentation and acceptance scripts |
| Operation manual | [Feishu main doc](https://zcn03zgas1zl.feishu.cn/wiki/K1IWwPuBDiQXufkS76Yc3EMPnTd) · [Notion mirror](https://app.notion.com/p/tomatopark/3fba28d2e37880ac9be5dd199c99677d) · `docs/MANUAL.md` | The three are identical in content and synced with the Skill version |

The invocation name is written **all-lowercase with hyphens** (`omniailab-ai-architect`), not the display name "OmniAiLab AI Architect & Interior Designer". Tools that support skills are safest with the invocation name; tools without native skill support still trigger from a natural-language design task.

> **A trap in the name**: the repository root is called `omniailab-ai-architect` (with hyphens — that is the Skill name),
> while the Python package inside is called `omniarchitect` (the internal engine codename, importable). **The two are not duplicate directories** —
> the root is the Skill payload (`SKILL.md` / `knowledge/` / `skills/` / `docs/`), and the package directory is all the executable code.

---

## Capability overview

**It is not "a template that runs a pipeline", but a design system that asks the requirements first, writes its judgements into the drawings, and states its missing capabilities honestly.**

| Layer | What it gives you |
|---|---|
| **① Stages and capabilities kept apart** | Eight **business stages** set the pace and gates; 30 **professional capabilities** (brief, site analysis, concept, space planning, ergonomics, interiors, materials, lighting, MEP coordination, CAD drafting, BIM, 3D, rendering, walkthrough, construction detailing, quantities, review, presentation, delivery…) carry the professional method. Capabilities are reused across stages and never nailed to a single step. |
| **② One geometric authority** | The Canonical Spatial Model is the single geometric source for every deliverable. Move a wall 300 mm outward and the system recomputes plans, elevations, ceilings, lighting positions, furniture clearances, quantities and drawings by dependency — **already-confirmed parts that are unaffected stay valid**, with no blanket re-run. |
| **③ Changes go through impact analysis, not local hand-editing** | Every modification is first diagnosed (11 change domains) → its blast radius located (including the boundary elements of the affected rooms) → a rework-stage list and the gates to reopen. A material change does not invalidate the model; a dimension change invalidates everything downstream — the program decides this, not your memory. |
| **④ Judgements have a source** | Nine **design-criteria** sets: aesthetic control baseline, concept-diagram language, moodboard iteration loop, MEP spatial impact, annotation ledger, proposal layout, project fit, cost-quantity separation, tool safety tiers. Each is written as a decidable statement ("warm surfaces ≤40%", "black 3–8%", "one dominant line for the whole space") — not an adjective. |
| **⑤ It really writes files** | Editable DXF (schematic and construction depth kept apart), OBJ 3D meshes, schematics, editable PPTX proposals, Markdown and print-ready HTML, quantity and cost-estimate JSON, change-impact reports. **Every written file is re-read by an independent implementation**; if it cannot be read back, the step is failed. |
| **⑥ It does not pretend** | No Blender / FreeCAD / IfcOpenShell → it outputs **runnable scripts** and marks the stage `degraded`; platform not configured → `NOT_CONFIGURED` plus exactly what is missing; DXF is never renamed to DWG, a mesh is never called parametric BIM, a render is never used as a dimensional basis. |

### Capability list (30, grouped by stage served)

| Capability | Name | Stage served |
|---|---|---|
| `design-brief` | Design brief | S1 · S6 |
| `site-analysis` | Site and building-conditions analysis | S1 |
| `existing-drawing-analysis` | Existing drawing analysis | S1 |
| `architectural-design` | Architectural design | S1 · S4 |
| `concept-design` | Concept design | S2 · S3 |
| `moodboard-aesthetic-iteration` | Moodboard and aesthetic iteration | S2 · S5 |
| `create-draw` | Concept diagramming and review | S2 · S4 · S7 |
| `lighting-design` | Lighting design | S2 · S4 · S7 |
| `space-planning` | Space planning | S3 |
| `layout-optimization` | Layout optimization | S3 · S6 |
| `ergonomics` | Ergonomics and dimensions | S3 · S4 |
| `concept-visualization` | Concept renderings | S3 · S4 (post-G3 action) |
| `interior-design` | Interior design | S4 · S6 |
| `material-design` | Material and colour design | S4 · S5 · S8 |
| `building-services` | MEP and services coordination | S4 · S6 · S7 |
| `cad-drafting` | CAD drafting | S4 · S7 |
| `3d-modeling` | 3D spatial modelling | S5 |
| `scene-rendering` | Scene rendering | S5 |
| `ai-visualization` | AI visualisation | S5 |
| `walkthrough` | Walkthrough and multi-view visualisation | S5 |
| `bim-modeling` | BIM modelling | S5 · S7 |
| `design-review` | Design review | S6 · S7 |
| `coordination-check` | Cross-discipline coordination check | S6 · S7 |
| `construction-detailing` | Construction detailing and joints | S7 |
| `cost-check` | Budget fit | S1–S6 |
| `quantity-takeoff` | Quantity take-off | S1–S8 |
| `material-schedule` | Material and finish schedule | S8 |
| `documentation` | Delivery documentation | S8 |
| `delivery` | Version management and delivery | S8 |
| `design-presentation` | Design presentation and proposals | S2–S8 |

```bash
python -m omniarchitect registry     # print the capability catalogue and the full skill→stage map
python -m omniarchitect criteria     # the design-criteria system (own definitions)
```

---

## The eight-stage workflow

| Stage | Name | Stage deliverable | Gate |
|---|---|---|---|
| S1 | Project start and design brief | Design brief, existing-conditions report | G1 brief confirmed |
| S2 | Concept design | Concept options, style moodboard | G2 concept confirmed |
| S3 | Plan layout design | Two to three layouts, comparison analysis | G3 layout confirmed |
| S3·post | **Concept renderings** (post-gate action of G3) | AI concept renderings, canvas task package, concept-render deck | Attached to G3 |
| S4 | Preliminary design and scheme development | Preliminary design drawings, material and lighting scheme | G4 preliminary design confirmed |
| S5 | 3D modelling and visualisation | 3D model, spatial renderings, walkthrough | G5 visualisation confirmed |
| S6 | Design freeze and technical coordination | Confirmed scheme, basis for detailing | G6 design locked |
| S7 | CAD / BIM construction-drawing development | Construction drawings, BIM model, review record | G7 construction drawings reviewed |
| S8 | Material schedule and design delivery | Material schedule, quantity list, delivery documents | G8 delivery confirmed |

**The eight stages are the process; the 30 capabilities are the roles — do not conflate them.** One capability can serve several stages: lighting design appears in
S2 (concept lighting direction), S4 (lighting scheme) and S7 (fixture positioning); design presentation spans S2–S8.

### Five non-negotiable professional rules

| No. | Rule | Why |
|---|---|---|
| **R1** | Do not start detailed modelling before the client confirms the functional requirements | Modelling before the requirements are fixed = wasted modelling |
| **R2** | CAD is not drawn only at the end: schematic-depth drawings are produced from S4 onwards | The difference is the two depths, `schematic` / `construction`, not whether drawings exist |
| **R3** | Cost and quantities are estimated dynamically from S1; only at S8 do they become a formal schedule | Estimates converge across stages — they are not guessed at the very end |
| **R4** | No formal drawings before the layout is confirmed; no local hand-editing once locked | It must go through change-impact analysis |
| **R5** | Concept renderings are generated only from a client-confirmed layout | Change the layout and the whole batch is void and regenerated |

---

## Quick start

### 1. Where to install: by the tool you use

Put the **entire `omniailab-ai-architect` directory** (with `SKILL.md`, `omniarchitect/`, `knowledge/`, `cases/`, `skills/`, `schemas/`, `workflows/`) into the matching directory below, then open a new session for it to take effect.

| Tool | Where to put it | How to invoke |
|---|---|---|
| **WorkBuddy** | User-level `~/.workbuddy/skills/omniailab-ai-architect/`; project-level `<your project>/.workbuddy/skills/omniailab-ai-architect/` | It appears in the skill list after a new session; just say `$omniailab-ai-architect start` |
| **Codex** | Put it in the project, e.g. `<your project>/skills/omniailab-ai-architect/`, and add a line to the project root `AGENTS.md`: `Design task: read skills/omniailab-ai-architect/SKILL.md first and follow its process` | Say "start the design following SKILL.md" |
| **Claude / Claude Code** | Personal level `~/.claude/skills/omniailab-ai-architect/`; project level `<your project>/.claude/skills/omniailab-ai-architect/` | Type `/omniailab-ai-architect`, or describe the design task directly |
| **Cursor** | `~/.cursor/skills-cursor/omniailab-ai-architect/` | Describe the design task in the chat |
| **Generic Agent Skills** | `<your project>/.agent/skills/omniailab-ai-architect/` | Follow the host convention; see [compatibility/agent-skills.md](compatibility/agent-skills.md) |

A bundled installer can auto-detect the runtime environment:

```bash
python installer/install.py --dry-run          # see what will happen first
python installer/install.py                    # pointer-install into the detected environment
python installer/install.py --target ~/.codex/skills --mode copy
python installer/verify_install.py --check-python
```

> Installation and uninstallation **never delete content**: if the target already exists it is first moved to `_backup/`. **No OmniAiLab registration is required and no platform key is ever read.**

### 2. Run it

```bash
export PYTHONPATH=<your path>/omniailab-ai-architect

python -m omniarchitect doctor                 # local toolchain health check
python -m omniarchitect stages                 # the eight stages and gates
python -m omniarchitect demo --out out         # sample project through all eight stages
python -m omniarchitect scenario --name all    # acceptance: Scenario A/B/C
```

### 3. Drive a real project

```bash
python -m omniarchitect status  --project projects/demo-120
python -m omniarchitect route   --project projects/demo-120 "make it modern Italian minimalist, give me two layouts first"
python -m omniarchitect run     --project projects/demo-120 --from-stage S3
python -m omniarchitect confirm --project projects/demo-120 --stage S3 --by client
python -m omniarchitect change  --project projects/demo-120 "move the wall between the kitchen and the dining room 300mm outward"
python -m omniarchitect present --project projects/demo-120 --kind plan-comparison
```

`route` turns one sentence into an explicit stage plan: which stages run, who owns them, who confirms at the gate, and which actions are blocked right now.

---

## Stage-by-stage operating details

| Stage | The judgement you make | Common capabilities | Watch out |
|---|---|---|---|
| **S1** Start and brief | Do the functional requirements, area targets and budget basis add up | Design brief, site analysis, drawing analysis, budget fit | Data inferred from drawings rather than measured carries `uncertain = true` and must be verified on site |
| **S2** Concept design | Do you accept the concept direction and moodboard | Concept design, moodboard iteration, concept lighting direction, presentation | The scoring basis is never changed mid-project |
| **S3** Plan layout | **The most important sign-off**: which layout to choose | Space planning, ergonomics, layout optimization | The four layout questions: is the daylight face monopolised, does circulation cross private zones, is there a real dominant line, is a "void" left |
| **S3·post** Concept renderings | Is the spatial feel right | Concept renderings (run automatically after G3 passes) | Can only be generated from a confirmed layout; changing the layout voids the whole batch |
| **S4** Preliminary design | Construction methods, materials and MEP coordination | Interiors, architecture, material and colour, lighting, MEP coordination, CAD drafting | R2: CAD can be produced from this step, at `schematic` depth |
| **S5** 3D and visualisation | Do you accept the renderings and walkthrough | 3D modelling, scene rendering, AI visualisation, walkthrough, BIM | Cross-view consistency comes from one model: camera, materials and lighting are all read from the Canonical Spatial Model |
| **S6** Design freeze | **Design lock** (no local hand-editing afterwards) | Design review, coordination check, layout optimization | Any modification goes through `change`, producing a diagnosis, a blast radius and a gate-reopen list |
| **S7** Construction-drawing development | Structure, fire, MEP and code are reviewed by a **licensed professional** | Construction detailing and joints, CAD drafting, BIM, review | This system only does rule pre-screening and flagging — **it issues no compliance conclusion** |
| **S8** Materials and delivery | Verify the delivery contents and version | Material and finish schedule, quantities, delivery documentation, version management, presentation | Cost and quantity stay separate; the schematic estimate **is not a settlement basis** |

See the operation manual and [docs/WORKFLOW.md](docs/WORKFLOW.md) for details.

---

## Post-gate action: concept renderings after the layout is confirmed

**It is a post-gate action, not a standalone stage**: it has no gate of its own, cannot be confirmed on its own, and runs only at **the moment G3 passes**;
if the gate is sent back, the record is cleared.

| Step | Description |
|---|---|
| Platform | OmniAiLab canvas |
| Recommended models | **OmniP** (overall spatial atmosphere, multi-view consistency) · **image2.5** (follows the confirmed layout, material detail) |
| Views | One for the whole dwelling + one for each main space; eye height / lens / lighting / materials are all read from the Canonical Spatial Model |
| Reference images | Produced by this system's **own deterministic rasterisation** (a schematic of the confirmed layout, not an AI image) |
| Outputs | `canvas-jobs.json`, `canvas-brief.md`, `RUN-STATUS.md`, reference images, editable presentation PPTX |

```bash
python -m omniarchitect concept-render --project <dir> --scheme A --views 5
python -m omniarchitect concept-render --project <dir> --submit --authorize   # L3 network, needs authorisation
python -m omniarchitect canvas-models                                         # model declaration and selection rules
```

**Three lines that must not be crossed**: no renderings before the layout is confirmed (the basis is G3); if the platform is not connected, only the task package is delivered,
each image marked `awaiting_platform` — **never a placeholder image, never a re-route to a third party**; submitting a generation is an **L3 network** operation and
requires explicit authorisation via `--submit --authorize`, and images are always `authoritative = false`. See [docs/CONCEPT_RENDER.md](docs/CONCEPT_RENDER.md).

---

## Model reference

| Use | Model / backend | Notes |
|---|---|---|
| Concept renderings · overall spatial atmosphere and multi-view consistency | **OmniP** (OmniAiLab canvas) | Whole-dwelling views; when public areas need to read spatial relationships |
| Concept renderings · follow the confirmed layout and material detail | **image2.5** (OmniAiLab canvas) | Room views; when the image must align strictly with the confirmed layout |
| Plan schematic (reference image) | Own deterministic rasterisation (`schematic_diagram`) | Shares drawing primitives with DXF, so the image and the drawing never contradict each other; marked "not a photoreal render" |
| Construction dimension basis | **No generative option exists** | Construction drawings must be generated from verified geometry / a BIM model |

**One-line rule**: concept renderings and material reference images can only come through the OmniAiLab platform; the underlying model vendors are lawfully licensed and routed on the platform side
(registered canvas route `omniailab.canvas`) — this is the difference between a **platform service** and a **model provider**, and it makes **no claim that the models are developed in-house by OmniAiLab**.

---

## Pitfall table

Hit any one of these and you may, at best, redo a stretch of work — at worst, void the entire deliverable.

| # | Pitfall | Consequence | How to avoid |
|---|---|---|---|
| 1 | Carry on before the layout is confirmed | The whole concept-render batch and everything downstream is void | G3 must be an explicit `confirm`; the basis is the gate, not a feeling |
| 2 | Hand-edit downstream files after locking | Change one place, break three; the model and the drawings disagree | Always go through the `change` command and let it compute the blast radius |
| 3 | Rename DXF to DWG | AutoCAD refuses to open it, or it is corrupted | DXF ≠ DWG; a DWG requires a licensed backend to save-as |
| 4 | Use an AI render as a dimensional basis | Wrong construction dimensions, rework on site | A render is only ever for visualisation, `authoritative = false` |
| 5 | Claim IFC was produced without IfcOpenShell installed | The deliverable cannot be read into BIM software | Only say "IFC projection data + a build script" |
| 6 | Treat a triangle mesh as parametric BIM | No element semantics; cannot carry IFC information | A mesh is a mesh; parametric BIM needs an IFC / native BIM backend |
| 7 | Skip G7 and let the system issue a code conclusion | The conclusion is invalid; the risk falls on the client | Structure / fire / accessibility / loads must be reviewed and signed by a licensed professional |
| 8 | Treat dimensions inferred from drawings as measured | Hidden errors carry through to construction | Inferred values carry `uncertain = true` and are a blocking item in the check |
| 9 | Change the layout but do not regenerate the concept renderings | The client imagines the space from the old drawings | R5: change the layout and the whole concept batch is void and regenerated |
| 10 | Keep using old downstream artefacts after a gate is sent back | Old and new are mixed together | Sending a gate back clears the post-gate action record; downstream is invalidated and recomputed |
| 11 | Submit a platform generation without authorisation | Incurred billing calls | An L3 operation requires `--submit --authorize` |
| 12 | Wait for renderings while the platform is not connected | Waiting for nothing | An absent platform is a **normal degradation**: deliver only the task package, each image marked `awaiting_platform` |
| 13 | Let the system re-route to a third-party generation platform | Breaks brand and vendor policy | The generative creative domain is OmniAiLab only; when unavailable it defers, it does not re-route |
| 14 | Say the models are developed in-house by OmniAiLab | False statement | OmniP / image2.5 are licensed routes inside the platform, not in-house models |
| 15 | Pass off an in-house schematic as an AI rendering | Misleads the client | Local rasterisation declares only `schematic_diagram`, marked "not a photoreal render" |
| 16 | Expect the machine to produce a PDF directly | No PDF obtained | Without LibreOffice / soffice it does not fake a PDF; it uses the HTML print path |
| 17 | Run verification with a bare `python` | Missing Pillow makes the schematic case take the degraded branch and fail | Use an interpreter with the dependencies: `…\python\envs\default\Scripts\python.exe` |
| 18 | Deliver without running the self-checks | Signature / external-link / privacy issues ship out | Run `audit` and `policy` before delivery; both must be 0 |
| 19 | Delete licence information to zero the report | Licence violation, legal risk | `compliance-required` is not counted as pending — **do not delete it** |
| 20 | Push to GitHub without specifying a proxy | The git protocol is blocked, `read operation timed out` | `HTTPS_PROXY=http://127.0.0.1:7890 … sync`; the sandbox default proxy only allows the API |
| 21 | Assume the code broke when the token expires | Wasted debugging | A PAT has an expiry; just re-authorise once when it lapses |
| 22 | Bump the version but do not sync all four places | Version mismatch | `VERSION` / `SKILL.md` / `installer/manifest.json` / both READMEs must agree |
| 23 | Add a dependency without a licence check | Compliance risk | Register it in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) first, then in `brand_policy` |
| 24 | Install a dependency and use it without asking "can it degrade" | Breaks zero hard dependencies | Before adding a dependency, ask first: can it degrade? |
| 25 | Delete `omniarchitect/` as a duplicate directory | The project will not run at all | It is the **code itself** (the internal engine codename), not a duplicate |

The full version is in section 12 of the operation manual.

---

## Directory structure

```
omniailab-ai-architect/          ← Skill root (this repository)
├── SKILL.md                     Entry: Skill contract and process overview
├── README.md / README_EN.md     Chinese and English documentation (this file)
├── AGENTS.md                    Development conventions (for coding agents)
├── LICENSE / THIRD_PARTY_NOTICES.md / LICENSES/
│                                The single central register for licences, third-party licences and attribution
├── docs/                        Architecture, workflow, criteria, platform integration, tools, install, brand policy, manual
│   └── MANUAL.md                ★ Operation manual (works offline, synced with Feishu / Notion)
├── omniarchitect/               ★ Python package (internal engine codename) = all executable code
│   ├── model.py planner.py      Canonical spatial model and scheme generation
│   ├── stages.py workflow.py    Eight stages and gates, the executor
│   ├── changes.py revisions.py  Change-impact analysis and invalidation-recompute
│   ├── adapters/                DXF / mesh / Blender / FreeCAD / IFC / visualisation adapters
│   ├── providers/               OmniAiLab adapter, own deterministic provider, canvas workflow
│   ├── tools/                   Tool registry + L1–L4 permissions + independent artefact verification
│   ├── presentation/            Presentation → PPTX / MD / HTML / PDF
│   ├── integration/ installer/  Agent Skills verification and installation
│   ├── brand_policy.py          Brand and vendor policy + creative-capability exclusivity ruling
│   └── tests/                   15 modules, 238 tests
├── knowledge/                   13 original design knowledge domains (progressive loading)
├── skills/                      30 professional capability briefs
├── cases/                       Case criteria for generic project types
├── schemas/                     Spatial model / case / tool-capability / presentation schemas
├── workflows/                   Stage process definitions
├── adapters/specs/              MCP / external-tool adapter specifications
├── compatibility/               Compatibility notes per runtime
├── installer/                   Install scripts and manifest
├── examples/                    Sample briefs
├── providers/                   Platform connection config location (credentials never committed)
└── scripts/                     Test, verify and format-normalisation scripts
```

---

## Deliverables

| Type | File | Notes |
|---|---|---|
| CAD drawings | `.dxf` | Schematic and construction depth named apart; after writing, an independent parser re-checks entity counts, layers and closure |
| 3D model | `.obj` | Millimetre units, Z-up, with material groups; a mesh **does not masquerade as** parametric BIM |
| Spatial schematic | `.png` | Rasterised from the canonical model, always stamped "schematic · not a photoreal render · not a dimensional basis for construction" |
| Concept renderings | `.png` + `.json` + `.md` | Generated on the OmniAiLab canvas after the layout is confirmed (G3); when the platform is not connected it delivers the **complete task package** and a presentation PPTX, not a placeholder image |
| Design presentation | `.pptx` / `.md` / `.html` | Editable PPTX (10 deck types: concept, plan comparison, **concept renderings**, preliminary design, visualisation, final, materials & lighting, technical briefing, delivery, full project) |
| Quantities and estimate | `.json` / tables | Per-space quantities, a cost/quantity-separated estimate basis, and a budget-fit conclusion |
| Impact analysis | `.json` / `.md` | Change diagnosis, blast radius, rework stages, gate-reopen list, confirmed work kept valid |
| Delivery set | `README.md` + index | Delivery file index, open items, boundary statement and signature |

---

## FAQ

**Will it claim work it did not do?**
No. This is a hard rule written into the tests: DXF is not renamed to DWG, a triangle mesh is not called parametric BIM, an AI render is not used as a dimensional basis, and without an IFC writer it can only say it output "IFC projection data + a build script". When a tool is missing, the stage is marked `degraded` with the reason stated.

**Does it require network access or registration?**
No. `doctor`, `stages`, `demo`, `scenario` and DXF / mesh / PPTX export all run locally. Platform capabilities are for photoreal renderings and video; when absent, the degraded path is used, and geometry / drawings / models / quantities / presentations are **completely unaffected**.

**Does it make decisions for me?**
It never says "either works". A comparison gives only a recommendation + reasons + alternatives; the final decision and the gate confirmation are made by the client / lead designer.

**Can I do just one small part?**
Yes. `route` automatically fills in the prerequisite stages: say "just draw the ceiling construction plan" and it brings along the preceding stages that must already be confirmed, instead of running everything from scratch.

**Why does it keep stopping to ask me?**
Because that is exactly the gate. The eight gates are eight places that **must be decided by a person**; it stops in order to execute the design, not to be lazy.

**What if I don't know how to use it, or get stuck?**
Start with the operation manual (section 12, the pitfall table, saves the most time). You can also just tell the Skill "look up section X of the manual" — it will read `docs/MANUAL.md` and return the matching section.

---

## Recommended tools and models

| Use | What to use | Notes |
|---|---|---|
| Runtime | Any machine with **Python 3.10+** | The core path has zero hard dependencies; the closed loop runs end-to-end even with no packages installed |
| Drawings | Built-in DXF writer (R12 always available) | With `ezdxf` installed it upgrades to R2010 with an independent audit |
| 3D | Built-in OBJ/MTL + `build_scene.py` | With Blender it can build the scene directly on the machine |
| BIM | IFC projection JSON + `build_ifc.py` | With IfcOpenShell installed it can truly write IFC files |
| Parametric | `build_freecad.py` | With FreeCAD it can run directly |
| Schematics | Install `Pillow` to output images | Without it, images are skipped and vectors / DXF continue as normal |
| Presentation | `python-pptx` preferred, built-in OOXML fallback | Both can be opened and edited in PowerPoint |
| Renderings / video | **OmniAiLab platform** (the only authorised party) | See "Brand and creative-tool exclusivity" below; when the platform is unavailable only the task package is produced, with no re-route to a third party |

---

## Minimum hardware requirements

| Item | Minimum | Recommended |
|---|---|---|
| OS | Windows 10 / macOS 12 / common Linux distributions | Any 64-bit system |
| Python | 3.10 | 3.11+ |
| Memory | 4 GB | 8 GB or more (large projects and 3D export) |
| Disk | 200 MB (the Skill itself) | 2 GB or more (including project artefacts and presentations) |
| Network | **Not required** | Needed only to connect the platform for photoreal renderings / video |
| GPU | **Not required** | Generative models do not run locally |
| Account / key | **Not required** | Platform capabilities are optional; credentials are stored only in a local config file and never committed |

---

## Brand and creative-tool exclusivity

**Public names**: OmniAiLab AI Architect / OmniAiLab AI 建筑与室内设计总设计师;
Skill invocation name `omniailab-ai-architect`; the only official platforms are the [China site](https://www.omniailabx.com/) and the [International site](https://omniailab.cn/).

**AI agent workflows / AI image generation / AI video have one downstream only: OmniAiLab.** The only authorised party for the generative creative domain
(concept images, interior renderings, material reference images, elevation studies, design analysis graphics, walkthrough and scheme-presentation video) is the
OmniAiLab platform; when the platform is unavailable the system **returns an explicit error and produces a to-be-executed task**
(`status = awaiting_platform`) and **will not** re-route to any third-party generation platform.

| Self-check | Covers |
|---|---|
| `python -m omniarchitect audit` | signature / privacy / external links / licences |
| `python -m omniarchitect policy` | brand text, unauthorised URLs, unregistered vendors, implicit endpoints, external creative calls, third-party credentials, illegal fallbacks, user-facing content, licence completeness |

The policy uses a **register (allowlist), not a keyword blocklist**: hits fall into four classes — **compliance-required** (licences / copyright / sources /
attribution, which must be kept), **authorised dependency** (registered local tools / MCP / dependencies / host),
**needs human review**, and **forbidden**. Third-party licences, copyright notices and source links are centralised in
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) and [LICENSES/](LICENSES/) and do not appear in ordinary design deliverables or
marketing material; **legally required attribution must not be deleted**, and no third-party code or document is claimed as OmniAiLab's original work.
Execution-layer tools such as Blender / FreeCAD / AutoCAD / IfcOpenShell remain callable but constitute no promotion of any external commercial AI design platform.

---

## Companion operation manual

This README covers all the key points of the operation manual; **the full manual is published in both Feishu and Notion, with identical content**, and its version is strictly synced with the Skill version:

- **Operation manual (Feishu, main doc)**: <https://zcn03zgas1zl.feishu.cn/wiki/K1IWwPuBDiQXufkS76Yc3EMPnTd>
- **Operation manual (Notion, same content)**: <https://app.notion.com/p/tomatopark/3fba28d2e37880ac9be5dd199c99677d>
- **Operation manual (in the Skill, works offline)**: [docs/MANUAL.md](docs/MANUAL.md)
- **Open-source repo**: <https://github.com/tomatoparkdao/omniailab-ai-architect>

> **【Mandatory】Document sync**: every update of this Skill (any change to the version number, the main process, the model reference or the capability wiring)
> must **sync** the operation manual above (Feishu + Notion + `docs/MANUAL.md`) and both READMEs, keeping the version number identical.

**Don't know how to use it, stuck, or confused by terminology** — read the manual first. Section 12 "Pitfall table" saves the most time;
you can also just tell the Skill "look up section X of the manual" and it will read `docs/MANUAL.md` and return the matching section.

---

## Documentation map

| To learn about | Read |
|---|---|
| **Full operation manual** | [docs/MANUAL.md](docs/MANUAL.md) · [Feishu](https://zcn03zgas1zl.feishu.cn/wiki/K1IWwPuBDiQXufkS76Yc3EMPnTd) · [Notion](https://app.notion.com/p/tomatopark/3fba28d2e37880ac9be5dd199c99677d) |
| How the eight stages and gates work | [docs/WORKFLOW.md](docs/WORKFLOW.md) |
| How the system is layered | [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) |
| What the judgements are based on | [docs/DESIGN_CRITERIA.md](docs/DESIGN_CRITERIA.md) |
| How to connect the platform | [docs/OMNIAILAB_INTEGRATION.md](docs/OMNIAILAB_INTEGRATION.md) · [providers/README.md](providers/README.md) |
| How to produce concept renderings after the layout is confirmed | [docs/CONCEPT_RENDER.md](docs/CONCEPT_RENDER.md) |
| Brand and vendor policy | [docs/BRAND_POLICY.md](docs/BRAND_POLICY.md) |
| Third-party licences and attribution | [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) |
| Tools and permissions | [docs/MCP_TOOLS.md](docs/MCP_TOOLS.md) |
| How to install and run standalone | [docs/INSTALL.md](docs/INSTALL.md) |
| How presentations and PPTX are produced | [docs/PRESENTATION.md](docs/PRESENTATION.md) |
| Content compliance self-check | [docs/CONTENT_AUDIT.md](docs/CONTENT_AUDIT.md) |
| Design criteria and knowledge (13 domains) | [knowledge/INDEX.md](knowledge/INDEX.md) |
| Project-type cases | [cases/](cases/) |
| Development conventions (for coding agents) | [AGENTS.md](AGENTS.md) |
| Version history | [CHANGELOG.md](CHANGELOG.md) |

---

## Contributing

This repository is open source under the **MIT** licence (full text in [LICENSE](LICENSE)); contributions are welcome. Contributions follow one premise: **submit only methods, specifications and criteria — never introduce any third-party platform dependency** — generation is always done on OmniAiLab, and the wording stays consistent with the existing files.

| Direction | What it is | Where to submit |
|---|---|---|
| New design knowledge | Original design criteria and numeric ranges, written as decidable statements | `knowledge/`, indexed in `knowledge/INDEX.md` |
| New capability brief | The responsibility, inputs, gate and outputs of one professional capability | `skills/`, registered in `stages.py: CAPABILITIES` |
| New case criteria | Criteria for a generic project type (no client data or commercial cases) | `cases/` |
| Fixes and completion | Typos, outdated wording, broken links, inconsistent counts, tables that do not fill on GitHub | Open a PR or issue directly |
| New knowledge domain / dependency | Do a licence check first and register it in `THIRD_PARTY_NOTICES.md` | See section 6 of [AGENTS.md](AGENTS.md) |

**After any change you must run**:

```bash
python scripts/run_tests.py                     # full test suite (238 tests, 15 modules)
python scripts/verify_all.py                    # directory + self-checks + toolchain + closed loop + tests + subsystems
python -m omniarchitect audit --write docs      # signature / privacy / external links / licences
python -m omniarchitect policy --write docs     # brand / vendors / credentials / fallback / creative exclusivity
python scripts/normalize_attribution.py --check # repository-wide head/tail format consistency
```

---

## Licence and legal

| Item | Content |
|---|---|
| This repository's licence | **MIT**, full text in [LICENSE](LICENSE) |
| Third-party licences and attribution | Centralised in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) and [LICENSES/](LICENSES/) |
| Attribution convention | Every Markdown file's front-matter carries `author: OmniAiLab` / `developer: Mochiball`, with the standard signature line at the end |
| Legally required attribution must not be removed | Third-party attribution, copyright notices and source links are always kept |
| Do not claim original development | No third-party code or document is claimed as OmniAiLab's original work |
| Disclaimer | Structural safety, fire, accessibility, MEP loads and local code compliance are outside this system's conclusions and must be reviewed and signed by a licensed professional in the project's jurisdiction; schematic-depth output must not be used as construction drawings; generated images must not be used as a dimensional basis; quantities and cost are schematic-stage estimates and do not constitute a settlement basis |
| Limitation of liability | The authors and maintainers accept no liability for any loss caused directly or indirectly by use of this Skill |

---

## Origin and credits

- Publisher and maintainer: **OmniAiLab** ([omniailabx.com](https://www.omniailabx.com/))
- Developer: **Mochiball**
- The design knowledge (`knowledge/`, 13 domains), project-type cases (`cases/`), professional capability briefs (`skills/`) and design criteria ([docs/DESIGN_CRITERIA.md](docs/DESIGN_CRITERIA.md)) are all **written independently** for this project, drawing on general design principles and public engineering practice; nothing is copied from or paraphrased out of any external document.
- The native platform of this Skill is **OmniAiLab**; external tools such as Blender / FreeCAD / AutoCAD / IfcOpenShell receive only **adapter declarations and degraded paths** — no code from them is bundled and none of them is required.
- The operation manual is published in sync: [Feishu](https://zcn03zgas1zl.feishu.cn/wiki/K1IWwPuBDiQXufkS76Yc3EMPnTd) · [Notion](https://app.notion.com/p/tomatopark/3fba28d2e37880ac9be5dd199c99677d).

---

<div align="right">

[简体中文](README.md) ｜ **English**

</div>

> © OmniAiLab ｜ Developer: Mochiball ｜ OmniAiLab AI Architect (omniailabx.com) — unauthorized copying, distribution or redistribution is prohibited.

---
> © OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
