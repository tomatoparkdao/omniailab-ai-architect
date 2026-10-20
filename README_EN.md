<h1 align="center">OmniAiLab AI Architect for Architecture & Interior Design</h1>

<p align="center">
  <b>AI architect Skill — architecture, interior, landscape as parallel leads; asks first, reasons openly, says no</b><br>
  36 types / 575 subtypes, classified before design　｜　8 stages × 31 capabilities × 47 design styles<br>
  Brief → concept reasoning → layouts → preliminary design → construction-depth DXF → handover<br>
  Renders only after G3, via OmniAiLab　｜　offline, zero deps　｜　no structural / fire / accessibility claims
</p>

<p align="center">
  <a href="https://github.com/tomatoparkdao/omniailab-ai-architect"><img src="https://img.shields.io/badge/%E7%89%88%E6%9C%AC-1.14.0-1f6feb?style=flat-square" alt="Version 1.14.0"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/%E8%AE%B8%E5%8F%AF-MIT-2ea043?style=flat-square" alt="License MIT"></a>
  <a href="https://www.omniailabx.com/"><img src="https://img.shields.io/badge/%E5%B9%B3%E5%8F%B0-OmniAiLab-8957e5?style=flat-square" alt="Platform OmniAiLab"></a>
  <img src="https://img.shields.io/badge/%E9%A2%86%E5%9F%9F-Architecture_%7C_Interior_%7C_Landscape-0e8a16?style=flat-square" alt="Domain Architecture | Interior | Landscape">
  <img src="https://img.shields.io/badge/%E6%B5%81%E7%A8%8B-8_Stages_%C3%97_31_Capabilities-0969da?style=flat-square" alt="8 stages x 31 capabilities">
  <img src="https://img.shields.io/badge/%E4%BA%A4%E4%BB%98-Design_%7C_Construction-1d76db?style=flat-square" alt="Delivery Design | Construction">
  <img src="https://img.shields.io/badge/%E5%85%BC%E5%AE%B9-Codex_%7C_Claude_%7C_Cursor_%7C_WorkBuddy-6f42c1?style=flat-square" alt="Compatible Codex / Claude / Cursor / WorkBuddy">
</p>

<p align="center">
  <a href="README.md">简体中文</a>　｜　<b>English</b>
</p>

> © OmniAiLab ｜ Developer: Mochiball ｜ Platform: [omniailabx.com](https://www.omniailabx.com/)

Not just producing renderings — AI taking part in the whole architecture and interior design process. **It does not merely run a pipeline: the first thing it does is pin down function, site and budget**, then lets the lead discipline set the order of reasoning — architecture decides massing and section first, interior decides reorganisation and interfaces first, landscape decides zoning and routes first. From there it advances stage by stage to deliverable drawings, models and material schedules, and at the end of every stage you only answer "confirmed" or "change item X". One Skill covering 8 design stages, 31 professional capabilities and 47 design styles, working with the OmniAiLab AI creation platform and professional MCP tools.

| Item | Value | Notes |
|---|---|---|
| Skill invocation name (unique ID) | `omniailab-ai-architect` | All-lowercase with hyphens; tools that support skills invoke it directly, and tools that do not still trigger it from a natural-language description |
| Display name | OmniAiLab AI Architect for Architecture & Interior Design | The name shown on the repository page and in the docs — not the invocation name |
| Version | v1.14.0 | Kept identical across `VERSION`, `pyproject.toml`, `SKILL.md`, `installer/manifest.json`, `openai.yaml` and both READMEs |
| Project taxonomy | 36 types / 575 subtypes | 15 architectural, 12 interior, 9 landscape; multiple uses allowed, with project nature and commissioned scope as separate dimensions (`docs/PROJECT_TAXONOMY.md`) |
| Publisher / Developer | OmniAiLab / Mochiball | — |
| License | MIT (see [LICENSE](LICENSE)) | Use and redistribution are governed by that file |
| Operation manual | [Feishu](https://zcn03zgas1zl.feishu.cn/wiki/K1IWwPuBDiQXufkS76Yc3EMPnTd) / [Notion](https://tomatopark.notion.site/Skill-3fba28d2e37880ac9be5dd199c99677d) / `docs/MANUAL.md` | Invocation, three-step start, per-stage rules, capability index, pitfalls, FAQ, deliverable list |
| Repository | [tomatoparkdao/omniailab-ai-architect](https://github.com/tomatoparkdao/omniailab-ai-architect) | All source, documentation and acceptance scripts; **currently a private repository** — once public, `git clone` and issues work directly |
| Requirements | Python 3.10+ | Zero hard dependencies: DXF, mesh and PPTX all have built-in writers |
| Native platform | [OmniAiLab China site](https://www.omniailabx.com/) / [International site](https://omniailab.cn/) | Generative image and video capabilities come from the platform; **the system runs normally when it is not connected** |

The invocation name is **all-lowercase with hyphens** (`omniailab-ai-architect`), not the display name "OmniAiLab AI Architect for Architecture & Interior Design". Tools with native skill support are best driven by the invocation name; tools without it still trigger from a natural-language description of the design task.

> **One naming trap**: the repository root is `omniailab-ai-architect` (hyphenated — that is the Skill name), while the Python package inside is `omniarchitect` (the internal engine code name, importable). **They are not duplicate directories** — the root is the Skill payload (`SKILL.md` / `knowledge/` / `skills/` / `docs/`), and the package directory holds all executable code.


---

## It decides what kind of project this is before deciding how to design it

"Design me a hotel" can mean a new hotel building or a fit-out of an existing one — different
disciplines, different deliverables. S1 therefore records three separate things: **use** (36 types,
multi-label), **project nature** (new build, extension, fit-out, landscape-only, adaptive reuse,
heritage) and **commissioned scope** (which of architecture / interior / landscape is actually
bought). The name is not the contract — saying "hotel interior" does not trigger a hotel building.

That classification drives S2 (a hospital reasons around medical process and clean/dirty separation;
a school around age groups and teaching clusters; a factory around process flow) and S3 (task lists
such as department area schedules, guest-room modules, catchment grading). Capability boundaries are
stated per type: housing reaches room-level layouts, a hospital gets concept and task structuring
only, a factory needs process data from the client side.

```bash
python -m omniarchitect taxonomy                      # 36 types
python -m omniarchitect taxonomy --show A4            # hospital: focus / directions / S3 tasks
python -m omniarchitect taxonomy --detect "existing hotel interior fit-out"
```

## In one sentence

Hand it one requirement — even just a floor plan plus a line like "make it Italian minimalist" — and it first pins down function and budget, then advances stage by stage to deliverable drawings, models and material schedules. At the end of every stage you only answer "confirmed" or "change item X".

**It does not say "this scheme is more modern". It says "walking in here you meet a wall first; three steps to the left and it opens up."** Every direction it proposes at S2 comes with a verifiable spatial experience and a direct answer to what you asked for.

| Scope | What it covers |
|---|---|
| **Applicable · any project type** | Residential flats, large flats, villas, offices, retail, restaurants, hotels, showrooms; both the schematic stage and the development stage are in scope. **Architecture, interior and landscape can each be the lead discipline**: a new build is led by architecture, an existing space takes interior only, a standalone courtyard takes landscape only — the lead discipline sets the order of reasoning, and non-lead disciplines do **interface coordination** only (equipment positions, lighting connections, setbacks, interface finishes) |
| **Applicable · controllable depth** | Ask for "just compare two layouts", or ask for "layouts + 3D + a render task package + construction-depth DXF + material schedules + a presentation deck"; the same single pipeline serves them on demand |
| **Not applicable (said plainly)** | **Final conclusions** on structural safety, fire, accessibility, MEP loads and local code compliance are **not** this system's conclusions; the system only flags issues and gives a to-be-reviewed list, which a licensed professional must verify and sign off in the project's jurisdiction |

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
| **⑦ Design style system** | A structured library of **47 architectural and interior design styles** (eight families: modern / oriental / classic / deco-retro / industrial / natural-organic / regional / experimental), each with 20 professional fields (history, spatial principles, proportion, palette, materials, furniture language, lighting, applicable spaces, cost and construction notes, compatible and conflicting elements, positive prompt components, geometry preservation rules, negative constraints, quality checklist). **Index and data are separate**: query `catalog.json` (179 tags) first, then load a single style on demand — never all 47 at once. Ships a three-option recommender and a bilingual prompt compiler (14 targets: 8 spatial views plus 6 drawing-derived and board recipes — coloured plan, isometric axon, orthographic section, three-panel presentation board, concept sheet, physical material moodboard; the drawing-derived ones require G3 and their text is overlaid by the layout layer). |
| **⑧ Design capability: spatial experience** | The prototype says how rooms are arranged, the style says what it looks like — the layer in between, **what a person actually experiences walking through**, used to be missing. **11 spatial devices** (compression and release, prospect and refuge, threshold, enfilade, framing, borrowed view, rhythm and repetition, layering of light, material honesty, proportion driving ceiling height, arrival sequence), each with its mechanism, execution, **how to verify it on the drawing**, and what goes wrong when misused. **The 22 prototypes belong to different spatial families**, so their natural strengths differ — which is why three directions never say the same sentence. Tell it "I want it bright, don't let me see straight through the door", and S1 records it, then S2 answers each point: deliverable (`met`), stretched (`at_risk`), or not asked (`not_stated`) — **if you never said it, it will not decide for you**. |
| **⑨ Technology yields to design** | Structure and MEP are **supporting disciplines, not approval gates**. When a concept calls for a double-height void, it does not judge "not feasible"; it returns three implementation paths — raised edge beam / steel frame / local cantilever — each stating **what it gains, what it costs, and which licensed professional must sign off**. 8 technical goals, 24 paths (structure: double-height void / removing load-bearing walls / added load / long span; MEP: exposed ceiling / relocating wet zones / windowless space / open kitchen). **What is physically impossible is called impossible** (a skylight on a middle floor, natural light in a basement), with alternatives, and no fake options. |

### Capability list (30, grouped by stage served)

| Capability | Name | Stage served | What it does |
|---|---|---|---|
| `design-brief` | Design brief | S1 · S6 | Turns needs, budget and acceptance into a checkable brief |
| `site-analysis` | Site and building-conditions analysis | S1 | Reads site, orientation, daylight and limits into constraints |
| `existing-drawing-analysis` | Existing drawing analysis | S1 | Separates verifiable facts from inference in drawings |
| `architectural-design` | Architectural design | S1 · S4 | Organises programme, site and orientation into massing |
| `concept-design` | Concept design | S2 · S3 | Turns the brief into a testable claim and spatial prototype |
| `moodboard-aesthetic-iteration` | Moodboard and aesthetic iteration | S2 · S5 | Anchors aesthetic goals, scores them, tracks fixes; references split into research and delivery tiers |
| `create-draw` | Concept diagramming and review | S2 · S4 · S7 | Draws judgements with agreed semantics; reviews stay auditable |
| `lighting-design` | Lighting design | S2 · S4 · S7 | Unifies daylight and artificial light into one strategy |
| `space-planning` | Space planning | S3 | Turns brief and concept into rooms, areas and circulation |
| `layout-optimization` | Layout optimization | S3 · S6 | Compares proportions, depth and openness with trade-offs |
| `ergonomics` | Ergonomics and dimensions | S3 · S4 | Converts "is it enough" into checkable clearances and heights |
| `concept-visualization` | Concept renderings | S3 · S4 (post-gate action of G3) | Generates concept images on the approved plan via OmniAiLab |
| `interior-design` | Interior design | S4 · S6 | Develops the plan into interfaces, ceilings and finishes |
| `material-design` | Material and colour design | S4 · S5 · S8 | Yields purchasable, buildable, maintainable materials and samples |
| `building-services` | MEP and services coordination | S4 · S6 · S7 | Turns MEP and fire needs into coordination points and clearances |
| `cad-drafting` | CAD drafting | S4 · S7 | Produces drawing sets at schematic and construction depth |
| `3d-modeling` | 3D spatial modelling | S5 | Turns the confirmed model into an editable 3D scene |
| `scene-rendering` | Scene rendering | S5 | Renders batches by camera, material and light; views stay consistent |
| `ai-visualization` | AI visualisation | S5 | Generates supporting visuals via OmniAiLab; marked non-authoritative |
| `walkthrough` | Walkthrough and multi-view visualisation | S5 | Turns spatial sequence into panoramas and walkthroughs; hands off to the directing skill when narrative is needed |
| `bim-modeling` | BIM modelling | S5 · S7 | Turns the model into parametric components for take-off |
| `design-review` | Design review | S6 · S7 | Screens output against a checkable list: pass / conditional / return |
| `coordination-check` | Cross-discipline coordination check | S6 · S7 | Finds clashes among structure, MEP, ceiling heights and details |
| `construction-detailing` | Construction detailing and joints | S7 | Develops intent into buildable junctions and details |
| `cost-check` | Budget fit | S1–S6 | Estimates from S1 on and judges budget fit with range bands |
| `quantity-takeoff` | Quantity take-off | S1–S8 | Rolls quantities each stage; formal bill only at S8 |
| `material-schedule` | Material and finish schedule | S8 | Specs, quantities, waste and substitutes; price kept apart |
| `documentation` | Delivery documentation | S8 | Assembles an indexed, bounded and signed archive |
| `delivery` | Version management and delivery | S8 | Tracks changes by revision and freezes the delivered version |
| `design-presentation` | Design presentation and proposals | S2–S8 | Turns stage output into decision-ready proposals and PPTX |

```bash
python -m omniarchitect registry     # print the capability catalogue and the full skill→stage map
python -m omniarchitect criteria     # the design-criteria system (own definitions)
```

---

## Quick start

> **First time here? Just follow these five steps.** It does not open by asking "what is your design requirement"; instead it gathers what it needs in the order below.

### 1. Where to install it: by the tool you use

Put the **entire `omniailab-ai-architect` directory** (with `SKILL.md`, `omniarchitect/`, `knowledge/`, `cases/`, `skills/`, `schemas/`, `workflows/`, `docs/`) into the matching directory below, then open a new session for it to take effect.

| Tool | Where to put it | How to invoke |
|---|---|---|
| **Codex** (recommended primary) | No native skill directory: put the folder in the project, e.g. `<your project>/skills/omniailab-ai-architect/`, then add a line to the project-root `AGENTS.md`: <br>`Design task: read skills/omniailab-ai-architect/SKILL.md first and follow its process.` | Say "start the design following SKILL.md". After reading `AGENTS.md` it loads this skill. |
| **Claude / Claude Code** | Personal level: `~/.claude/skills/omniailab-ai-architect/`<br><br>Project level: `<your project>/.claude/skills/omniailab-ai-architect/` | Type **`/omniailab-ai-architect`**; or describe the task directly (e.g. "run the full design workflow for this floor plan") and it will match and load from the description. |
| **WorkBuddy** | User level (global): `~/.workbuddy/skills/omniailab-ai-architect/`<br><br>Project level (this project only): `<your project>/.workbuddy/skills/omniailab-ai-architect/` | It appears in the skill list after a new session; just say **`$omniailab-ai-architect 开始`**. |
| **OmniAiLab** (omniailabx) | [Download from the website](https://www.omniailabx.com/) (version per the website); after installing, put the whole folder into its **skills directory** (the client shows where it is) | It appears in the skill list after a new session; just say **`$omniailab-ai-architect 开始`**. |
| **Other Agent Skills hosts** | Follow the host convention, e.g. `<your project>/.agent/skills/omniailab-ai-architect/`; for Cursor use `~/.cursor/skills-cursor/omniailab-ai-architect/` | Describe the design task in the chat; see [compatibility/agent-skills.md](compatibility/agent-skills.md). |

> **The whole folder must be copied together — you cannot copy only SKILL.md.** The 31 capability briefs are in `skills/`, the 15 knowledge domains in `knowledge/`, the criteria in [docs/DESIGN_CRITERIA.md](docs/DESIGN_CRITERIA.md), the operation manual in [docs/MANUAL.md](docs/MANUAL.md), the templates in `schemas/` and `workflows/`, and the executable code in `omniarchitect/`; miss one directory and the run breaks its links.

**Clone install (recommended)**

```bash
git clone https://github.com/tomatoparkdao/omniailab-ai-architect.git \
  ~/.workbuddy/skills/omniailab-ai-architect
```

> This repository is a **private repository**: cloning needs GitHub authorisation (a token over HTTPS, or SSH). To update later, just run `git pull` in that directory. You can also file an issue in the repository.

A bundled installer can auto-detect the runtime environment (**no OmniAiLab registration is required and no platform key is ever read**):

```bash
python installer/install.py --dry-run          # see what will happen first
python installer/install.py                    # pointer-install into the detected environment
python installer/install.py --target ~/.codex/skills --mode copy
python installer/verify_install.py --check-python
```

> Installation and uninstallation **never delete content**: if the target already exists it is first moved to `_backup/`.

### 2. Where the material comes from (pick one of three)

1. **You upload the original drawings / design brief directly** — it reads them, parses them with `existing-drawing-analysis`, and goes straight into S1.
2. **You give nothing and just say "start"** — it first asks four things (project type / functional requirements / budget basis and delivery depth / what material you have), and **will not invent a set of requirements on its own**; only when you explicitly say "run the sample project" does it use the built-in 120㎡ residential sample.
3. **You give one requirement in a single line** (e.g. "120㎡ three-bedroom, modern Italian minimalist, budget 300k") — it first organises a confirmable version of the design brief for you to confirm, and only then enters S1.

> **One more question is worth answering carefully**: it will always ask "if you had to describe in one sentence how you want to feel when you push the door open, what would you say?".
> This question **deliberately offers no options** — options would frame your answer into the few we preloaded. That one sentence is the basis for every aesthetic direction at S2:
> say "bright, make it feel bigger" and it works with borrowed views and layered light; say "don't let me see straight through the door" and it works with threshold and transition.
> **If you already said it in your first sentence, it records it and does not ask twice.**

### 3. The starting command

```text
$omniailab-ai-architect 开始
```

Just say "start" — it will **not** ask back "what is your requirement", but instead asks directly: project type, functional requirements, budget basis, and what material you have.

Command line works too (it all runs locally; no platform and no key needed):

```bash
export PYTHONPATH=<your path>/omniailab-ai-architect
python -m omniarchitect doctor                 # local toolchain health check
python -m omniarchitect stages                 # the eight stages and gates
python -m omniarchitect demo --out out         # sample project through all eight stages
python -m omniarchitect scenario --name all    # acceptance: Scenario A/B/C
```

Driving a real project:

```bash
python -m omniarchitect status  --project projects/demo-120
python -m omniarchitect route   --project projects/demo-120 "make it modern Italian minimalist, give me two layouts first"
python -m omniarchitect run     --project projects/demo-120 --from-stage S3
python -m omniarchitect confirm --project projects/demo-120 --stage S3 --by client
python -m omniarchitect change  --project projects/demo-120 "move the wall between the kitchen and the dining room 300mm outward"
python -m omniarchitect present --project projects/demo-120 --kind plan-comparison
```

`route` turns one sentence into an explicit stage plan: which stages run, who owns them, who confirms at the gate, and which actions are blocked right now.

### 4. Two things to settle before you start

- **The functional requirements must be confirmed by the client.** R1: detailed modelling may not start before the client confirms the functional requirements — modelling before the requirements are fixed = wasted modelling. A major mid-course change to the functions (especially adding or removing rooms) voids every layout already confirmed and all downstream deliverables.
- **Fix the target delivery depth first.** Just "compare two layouts", or "layouts + 3D + a render task package + construction-depth DXF + material schedules + a presentation deck"? The same single pipeline serves them on demand, but the depth must be stated at S1 — deepening mid-course widens the rework.

### 5. All you ever need to say is one of two things

1. **Go ahead to the next stage** — it must be one of these four words; nothing else opens the gate:

```text
confirm / pass / finalise / continue
```

2. **To change something, point at where** — it redoes the work in place at the current stage and does not move on:

```text
The living-room daylight face of layout 3 is monopolised — rearrange it
Change the master-bedroom wardrobe from 600 deep to 550 deep
```

**When you only want one capability**, name it directly — there is no need to run the whole workflow:

| What you want | Copy this line and just say it | What it gives you |
|---|---|---|
| Design brief | `Just do the brief — turn my requirements into a verifiable brief` | functional brief + area targets + budget basis + acceptance criteria |
| Layout comparison | `Just do the layouts — give me two or three comparable options` | multiple layouts + comparable metrics + area mix + cost impact |
| Human-scale check | `Just do the dimensions — check whether the corridors and furniture clearances are enough` | a numeric check list for clear corridor widths / furniture clearances / sanitary-fixture clearances |
| Materials and finishes | `Just do the materials — give me a procurable, buildable material system` | material selection + specification layout + sample list |
| Lighting | `Just do the lighting — give me an illuminance, colour-temperature and fixture-position scheme` | illuminance standards / colour temperature / colour rendering / fixture positions and circuit suggestions |
| Concept renderings | `Just do the concept renderings, I have confirmed the layout` | canvas task package (views + prompts + reference images) + per-image status; marked `awaiting_platform` when no platform is connected |
| CAD drawings | `Just do the drawings — issue schematic-depth DXF` | editable DXF (schematic depth `schematic`) + an independent parse re-check result |
| Quantities and cost | `Just do the quantities — work out the quantities and estimate for this scheme` | per-space quantities + a cost/quantity-separated estimate + a budget-fit conclusion |
| Design presentation | `Just do the presentation — turn this stage's output into a proposal` | editable PPTX (with disclaimer and boundary pages) + Markdown + HTML |

> **The more specific the information, the less the rework.** The three most useful things: ① original drawings or on-site measured dimensions; ② functional requirements and number of occupants; ③ budget basis and hard constraints (what must not appear, what must appear). Giving these three at step one saves far more than adding them later.

---

## End-to-end at a glance

| Stage | Name | Stage deliverable | Gate |
|---|---|---|---|
| S1 | Project start and design brief | Design brief, existing-conditions report | G1 brief confirmed |
| S2 | Concept design | Concept options, style moodboard | G2 concept scheme confirmed |
| S3 | Plan layout design | Two to three layouts, comparison analysis | G3 layout scheme confirmed |
| S3·post | **Concept renderings** (post-gate action of G3) | AI concept renderings, canvas task package, concept-render deck | Attached to G3 |
| S4 | Preliminary design and scheme development | Preliminary design drawings, material and lighting scheme | G4 preliminary design confirmed |
| S5 | 3D modelling and visualisation | 3D model, spatial renderings, walkthrough | G5 visualisation deliverables confirmed |
| S6 | Design freeze and technical coordination | Confirmed scheme, basis for detailing | G6 design locked |
| S7 | CAD / BIM construction-drawing development | Construction drawings, BIM model, review record | G7 construction drawings reviewed |
| S8 | Material schedule and design delivery | Material schedule, quantity list, delivery documents | G8 delivery acceptance |

**The eight stages are the process; the 31 capabilities are the roles — do not conflate them.** One capability can serve several stages: lighting design appears in
S2 (concept lighting direction), S4 (lighting scheme) and S7 (fixture positioning); design presentation spans S2–S8.

### Five non-negotiable professional rules

| No. | Rule | Why |
|---|---|---|
| **R1** | Do not start detailed modelling before the client confirms the functional requirements | Modelling before the requirements are fixed = wasted modelling |
| **R2** | CAD is not drawn only at the end: schematic-depth drawings are produced from S4 onwards | The difference is the two depths, `schematic` / `construction`, not whether drawings exist |
| **R3** | Cost and quantities are estimated dynamically from S1; only at S8 do they become a formal schedule | Estimates converge across stages — they are not guessed at the very end |
| **R4** | No formal drawings before the layout is confirmed; no local hand-editing once locked | It must go through change-impact analysis |
| **R5** | Concept renderings are generated only from a client-confirmed layout | Change the layout and the whole batch is void and regenerated |
| **R6** | Technical feasibility is not the premise of design but its result | Decide what it must become first, then choose the implementation path. A double-height void is not a veto but three approaches with their costs; **only the physically impossible is called impossible**, and then an alternative follows |
| **R7** | If the client never said how they want it to feel, do not decide for them | `not_stated` stays `not_stated`. Recommending "warm and cosy" out of nowhere disguises our preference as their requirement |

---

## Stage-by-stage operating details

| Stage | The judgement you make | Common capabilities | Watch out |
|---|---|---|---|
| **S1** Start and brief | Do the functional requirements, area targets and budget basis add up | Design brief, site analysis, drawing analysis, budget fit | Data inferred from drawings rather than measured carries `uncertain = true` and must be verified on site. **The "how do you want it to feel" question is worth answering carefully** — it feeds every aesthetic judgement at S2 |
| **S2** Concept design | Do you accept the concept direction and moodboard; **is the experience of walking through right** | Concept design, moodboard iteration, concept lighting direction, presentation | The scoring basis is never changed mid-project. Every direction comes with a four-beat experience (first sight / turn / main space / what you remember) and the devices behind it; **three directions are different spaces, not different colours** |
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
| 15 | Pass off an in-house schematic as an AI render | Misleads the client | Local rasterisation declares only `schematic_diagram`, marked "not a photoreal render" |
| 16 | Expect the machine to produce a PDF directly | No PDF obtained | Without LibreOffice / soffice it does not fake a PDF; it uses the HTML print path |
| 17 | Run verification with a bare `python` | Missing Pillow makes the schematic case take the degraded branch and fail | Use an interpreter with the dependencies: `…\python\envs\default\Scripts\python.exe` |
| 18 | Deliver without running the self-checks | Signature / external-link / privacy issues ship out | Run `audit` and `policy` before delivery; both must be 0 |
| 19 | Delete licence information to zero the report | Licence violation, legal risk | `compliance-required` is not counted as pending — **do not delete it** |
| 20 | Push to GitHub without specifying a proxy | The git protocol is blocked, `read operation timed out` | `HTTPS_PROXY=http://127.0.0.1:7890 … sync`; the sandbox default proxy only allows the API |
| 21 | Assume the code broke when the token expires | Wasted debugging | A PAT has an expiry; just re-authorise once when it lapses |
| 22 | Bump the version but do not sync | Version mismatch | `VERSION` / `pyproject.toml` / `SKILL.md` / `installer/manifest.json` / `openai.yaml` and both READMEs must agree |
| 23 | Add a dependency without a licence check | Compliance risk | Register it in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) first, then in `brand_policy` |
| 24 | Install a dependency and use it without asking "can it degrade" | Breaks zero hard dependencies | Before adding a dependency, ask first: can it degrade? |
| 25 | Delete `omniarchitect/` as a duplicate directory | The project will not run at all | It is the **code itself** (the internal engine codename), not a duplicate |
| 26 | Committing reference photos / site videos / exported renders | The push fails and history is bloated forever | A single file of 1 MB or more, or any media binary, is never committed (`scripts/check_assets.py` guards this); if it must be kept, record its **external location and digest** in a JSON data file |
| 27 | Picking a style without reading the spatial experience, then signing off G2 | You get a scheme that photographs well and lives badly | G2 recognises a `concept_id`; read "what you experience walking through" before choosing |
| 28 | Treating a technical difficulty in the concept as a veto | Good design gets rejected by drawing progress, and work grows more conservative | A technical requirement triggers **implementation paths** (with cost and sign-off), not a veto; only the physically impossible is `blocked` |
| 29 | Reading implementation paths as if the engineering were already done | Building on "how it could be done" as if it were "it is safe" | Every path carries `sign_off`: structural calculations, load calculations, fire and code conclusions still require a licensed professional's signature |

The full version is in section 12 of the operation manual. Criteria for the spatial-experience layer and implementation paths are in [docs/DESIGN_CAPABILITY.md](docs/DESIGN_CAPABILITY.md).

---

## Directory structure

```
omniailab-ai-architect/          ← Skill root (this repository)
├── SKILL.md                     Entry: Skill contract and process overview
├── README.md / README_EN.md     Chinese and English documentation (this file)
├── AGENTS.md                    Development conventions (for coding agents)
├── openai.yaml                  Interface metadata (display name / default prompt / implicit-invocation switch)
├── CHANGELOG.md                 Version history
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
│   ├── style/                   Design style system (library / recommendation / prompt compiler / stage hooks)
│   ├── design/                  Design capability: spatial devices and sequences, client-feeling fit, structure/MEP paths
│   └── tests/                   test modules (full regression)
├── knowledge/                   13 original design knowledge domains (progressive loading)
│   └── styles/                  47 design styles, structured + catalog.json index
├── skills/                      31 professional capability briefs (filename = capability name, loadable by name)
├── cases/                       Case criteria for generic project types
├── schemas/                     Spatial model / case / tool-capability / presentation schemas
├── workflows/                   Stage process definitions
├── adapters/specs/              MCP / external-tool adapter specifications
├── compatibility/               Compatibility notes per runtime
├── installer/                   Install scripts and manifest
├── examples/                    Example library (opening prompts / deliverable checklist / sample brief; copy as-is)
├── providers/                   Platform connection config location (credentials never committed)
└── scripts/                     Test, verify, format-normalisation and asset-guard scripts
```

---

## Deliverables

| Type | File | Notes |
|---|---|---|
| CAD drawings | `.dxf` | Schematic and construction depth named apart; after writing, an independent parser re-checks entity counts, layers and closure |
| 3D model | `.obj` | Millimetre units, Z-up, with material groups; a mesh **does not masquerade as** parametric BIM |
| Spatial schematic | `.png` | Rasterised from the canonical model, always stamped "schematic · not a photoreal render · not a dimensional basis for construction" |
| Concept schemes | `.md` + `.json` + `.svg` | Each direction includes a spatial-experience sequence (first sight / turn / main space / what you remember) with the devices behind it, its answer to the client's stated feeling, deterministic diagrams and a real-colour moodboard |
| Technical implementation paths | `.json` + `.md` | Structure and MEP paths with their costs and the licensed discipline that must sign off; alternatives for physically impossible items |
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

**What makes it say one scheme is better than another?**
Not adjectives. Eleven checkable spatial devices (e.g. "entry-to-main-space ceiling ratio ≥1:1.3", "is there a solid surface within 600mm behind the main seat") each carry a way to verify them on the drawing; on top of that comes the sentence you said yourself, judged as a strength, adequate, or barely met. When none of the three can produce a criterion, it will not hand you a score.

**Will structure and MEP block my design again?**
No. They are supporting disciplines, and they only appear when your concept actually touches them — and what comes back is implementation paths (how, what it gains, what it costs, who signs), not a verdict. The only exception is what is physically impossible, such as a skylight on a middle floor or natural light in a basement; then it says so plainly and offers an alternative.

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

- **Operation manual (Feishu)**: <https://zcn03zgas1zl.feishu.cn/wiki/K1IWwPuBDiQXufkS76Yc3EMPnTd>
- **Operation manual (Notion)**: <https://tomatopark.notion.site/Skill-3fba28d2e37880ac9be5dd199c99677d>
- **Operation manual (in the Skill, works offline)**: [docs/MANUAL.md](docs/MANUAL.md)
- **Open-source repo**: <https://github.com/tomatoparkdao/omniailab-ai-architect>

> **【Mandatory】Document sync**: every update of this Skill (any change to the version number, the main process, the model reference or the capability wiring)
> must **sync** the operation manual above (Feishu + Notion + `docs/MANUAL.md`) and both READMEs, keeping the version number identical.

**Don't know how to use it, stuck, or confused by terminology** — read the manual first. Section 12 "Pitfall table" saves the most time;
you can also just tell the Skill "look up section X of the manual" and it will read `docs/MANUAL.md` and return the matching section.

---

## Getting help

Hit a problem, want to report a bug or suggest a feature — this order saves the most time:

| Channel | Where | Best for |
|---|---|---|
| **Operation manual (offline, fastest)** | [docs/MANUAL.md](docs/MANUAL.md) | Install, commands, errors, terminology; **section 12, the pitfall table**, saves the most time |
| **Operation manual (online)** | [Feishu](https://zcn03zgas1zl.feishu.cn/wiki/K1IWwPuBDiQXufkS76Yc3EMPnTd) · [Notion](https://tomatopark.notion.site/Skill-3fba28d2e37880ac9be5dd199c99677d) | Same as above; supports commenting and sharing with colleagues |
| **Ask inside the Skill** | Tell the Skill "look up section X of the manual" or "look up the manual's pitfall table" | It reads `docs/MANUAL.md` and returns the matching section — no flipping through it yourself |
| **Locate from the command line** | `python -m omniarchitect manual --topic <topic>` | 23 topics → manual chapter mapping; use it when unsure which section to read |
| **Repository issue** | [tomatoparkdao/omniailab-ai-architect/issues](https://github.com/tomatoparkdao/omniailab-ai-architect/issues) | Report bugs, suggest features; leaving it in the repository is the least likely to be lost |
| **OmniAiLab official** | [China site](https://www.omniailabx.com/) · [International site](https://omniailab.cn/) | Platform capabilities, model routing and account matters |

> Before asking, read this README's [Pitfall table](#pitfall-table) and the matching operation-manual section. When you ask, include
> **the project type, the current stage, the tool you use (Codex / Claude / WorkBuddy / OmniAiLab) and the verbatim error**,
> and it is easier to settle in one go.

---

## Documentation map

| To learn about | Read | What's inside |
|---|---|---|
| **Full operation manual** | [docs/MANUAL.md](docs/MANUAL.md) · [Feishu](https://zcn03zgas1zl.feishu.cn/wiki/K1IWwPuBDiQXufkS76Yc3EMPnTd) · [Notion](https://tomatopark.notion.site/Skill-3fba28d2e37880ac9be5dd199c99677d) | 15 chapters: install, commands, errors, glossary; §12 pitfall table saves the most time |
| How the eight stages and gates work | [docs/WORKFLOW.md](docs/WORKFLOW.md) | Each stage's gate, deliverables, return rules and post-gate actions |
| **How S1 starts (one sentence is enough)** | [docs/S1_INTAKE.md](docs/S1_INTAKE.md) | Three entry situations, per-type interview, five confidence states, five feasibility checks, design opportunities and the G1 baseline |
| **How S2 concepts are produced and compared** | [docs/S2_CONCEPT.md](docs/S2_CONCEPT.md) | Spatial prototype library, evidence-driven direction picking, conditional aesthetic rules, deterministic diagrams, real colour boards, the G2 baseline and the S3 handoff |
| **Why the schemes read like an architect's (spatial-experience layer)** | [docs/DESIGN_CAPABILITY.md](docs/DESIGN_CAPABILITY.md) | 11 spatial devices and how to verify them, how the 22 prototypes differ by spatial family, the three-state client-feeling verdict, 24 structure/MEP implementation paths with sign-off responsibility |
| How the system is layered | [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Entry / sub-capabilities / execution layer / canonical spatial model |
| What the judgements are based on | [docs/DESIGN_CRITERIA.md](docs/DESIGN_CRITERIA.md) | Nine criteria sets, each written as a checkable statement |
| How to connect the platform | [docs/OMNIAILAB_INTEGRATION.md](docs/OMNIAILAB_INTEGRATION.md) · [providers/README.md](providers/README.md) | Contract fields, credential location, three steps, creative-exclusivity rules |
| How to produce concept renderings after the layout is confirmed | [docs/CONCEPT_RENDER.md](docs/CONCEPT_RENDER.md) | G3 post-gate action: cameras, prompts, task pack and three red lines |
| Finding reference images and building moodboards | [docs/REFERENCE_SOURCES.md](docs/REFERENCE_SOURCES.md) | How to use the library: takeaways yes, images no; red lines and a five-step method |
| Making the scheme video more engaging | [docs/VIDEO_PRODUCTION.md](docs/VIDEO_PRODUCTION.md) | When to hand off to the directing skill, which part, and why the generator stays the same |
| Brand and vendor policy | [docs/BRAND_POLICY.md](docs/BRAND_POLICY.md) | Nine rules, four hit classes and the creative-exclusivity verdict |
| Third-party licences and attribution | [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) | Optional dependencies and host software registered item by item |
| Tools and permissions | [docs/MCP_TOOLS.md](docs/MCP_TOOLS.md) | L1–L4 permission tiers, tool registry and file data flows |
| How to install and run standalone | [docs/INSTALL.md](docs/INSTALL.md) | Where to place it per host, how to verify, how to stay offline |
| How presentations and PPTX are produced | [docs/PRESENTATION.md](docs/PRESENTATION.md) | Ten presentation types, layout rules and the brand template |
| Content compliance self-check | [docs/CONTENT_AUDIT.md](docs/CONTENT_AUDIT.md) | Scan results for attribution / privacy / links / licences |
| Why tables must be left-right aligned | [docs/TABLES.md](docs/TABLES.md) | Width maths, five hard rules, correct fixes and checker usage |
| Design criteria and knowledge (13 domains) | [knowledge/INDEX.md](knowledge/INDEX.md) | Thirteen original domains, progressive loading and lookup |
| Project-type cases | [cases/](cases/) | Three generic brief samples: apartment, office, restaurant |
| Development conventions (for coding agents) | [AGENTS.md](AGENTS.md) | Collaboration rules, forbidden zones and mandatory commands |
| Version history | [CHANGELOG.md](CHANGELOG.md) | What changed in each version, why, and the verification result |

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
python scripts/run_tests.py                     # full test suite (all modules, zero external deps)
python scripts/verify_all.py                    # directory + self-checks + toolchain + closed loop + tests + subsystems + asset size
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
- The operation manual is published in sync: [Feishu](https://zcn03zgas1zl.feishu.cn/wiki/K1IWwPuBDiQXufkS76Yc3EMPnTd) · [Notion](https://tomatopark.notion.site/Skill-3fba28d2e37880ac9be5dd199c99677d).

---

<div align="right">

[简体中文](README.md) ｜ **English**

</div>

---
> © OmniAiLab ｜ Developer: Mochiball ｜ OmniAiLab AI Architect for Architecture & Interior Design (omniailabx.com) — unauthorised copying, distribution and re-sharing are prohibited.
