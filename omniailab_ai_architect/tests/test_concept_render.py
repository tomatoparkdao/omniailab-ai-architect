"""Concept renderings after plan approval — the OmniAiLab canvas path.

What these tests defend:

* the batch is attached to **gate G3**, not to a stage body, so it can never
  picture a plan the client has not approved;
* every view points at a space that exists in the canonical model, and carries
  the revision it was produced from;
* the package is real work product even with no platform: prompts, references,
  statuses, per-view jobs and a client deck all exist on disk;
* nothing is fabricated — with no platform there are **no image files**, and the
  L3 network submission refuses to fire without explicit authorisation.
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from omniailab_ai_architect.demo import build_demo_project  # noqa: E402
from omniailab_ai_architect.providers import canvas  # noqa: E402
from omniailab_ai_architect.providers.base import (  # noqa: E402
    MediaProvider,
    ProviderCapability,
    ProviderJob,
)
from omniailab_ai_architect.stages import (  # noqa: E402
    CAPABILITY_BY_SLUG,
    POST_GATE_ACTIONS,
    post_gate_actions_for_stage,
)
from omniailab_ai_architect.workflow import StageRunner  # noqa: E402


def _confirmed_plan(td: str):
    """Run S1→S3 and confirm G3, i.e. the state the client renderings start from."""
    project = build_demo_project(Path(td))
    runner = StageRunner(project, Path(td) / "out", assume_approval=True,
                         project_dir=Path(td))
    outcomes = {}
    for sid in ("S1", "S2", "S3"):
        outcomes[sid] = runner.run_stage(sid, confirm=True)
    return project, runner, outcomes


def _installed_plan(td: str):
    """The state canvas.render expects: the confirmed scheme is in the model.

    G3 confirms a scheme without installing it (S4 does that). Unit tests of the
    canvas therefore step into S4 once, which is exactly when the installation
    happens in the real pipeline.
    """
    project, runner, _ = _confirmed_plan(td)
    runner.run_stage("S4", confirm=False)
    return project, runner


# --------------------------------------------------------------------------
# a stand-in for a *connected* OmniAiLab, so the authorised path is exercised
# with real files rather than being asserted about in the abstract
_ONE_PX_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
    b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)


class _StubCanvasProvider(MediaProvider):
    """Declares what a connected platform would declare; records every call."""

    id = "omniailab"
    name = "OmniAiLab (stub)"
    kind = "native-platform"

    def __init__(self, scopes=("reference_image_generation",),
                 models=("OmniP", "image2.5")) -> None:
        self.scopes = list(scopes)
        self.advertised = list(models)
        self.calls: list = []

    def probe(self) -> ProviderCapability:
        return ProviderCapability(
            provider=self.id, state="connected", scopes=list(self.scopes),
            models=list(self.advertised), auth="bearer", endpoint_known=True,
            evidence=["stub provider (test only)"],
        )

    def submit(self, operation: str, params: dict) -> ProviderJob:
        self.calls.append((operation, dict(params)))
        return ProviderJob(job_id=f"stub-{len(self.calls)}", provider=self.id,
                           operation=operation, status="succeeded",
                           raw={"params": dict(params)})

    def poll(self, job: ProviderJob) -> ProviderJob:
        return job

    def fetch(self, job: ProviderJob, target_dir) -> list:
        target = Path(target_dir)
        target.mkdir(parents=True, exist_ok=True)
        view_id = str((job.raw.get("params") or {}).get("view_id") or job.job_id)
        p = target / f"{view_id}.png"
        p.write_bytes(_ONE_PX_PNG)
        return [str(p)]


class _patched_discover:
    """Point the provider registry at the stub for the duration of a test."""

    def __init__(self, stub: _StubCanvasProvider) -> None:
        self.stub = stub

    def __enter__(self):
        from omniailab_ai_architect import providers as pkg
        from omniailab_ai_architect.providers import (
            LocalDeterministicProvider,
            ProviderRegistry,
        )

        self._orig = pkg.discover

        def _discover(project_dir=None, refresh: bool = False) -> ProviderRegistry:
            reg = ProviderRegistry()
            reg.add(self.stub)
            reg.add(LocalDeterministicProvider())
            return reg

        pkg.discover = _discover          # type: ignore[assignment]
        return self.stub

    def __exit__(self, *exc) -> None:
        from omniailab_ai_architect import providers as pkg

        pkg.discover = self._orig         # type: ignore[assignment]


# --------------------------------------------------------------------------
# wiring
# --------------------------------------------------------------------------
def test_concept_visualization_is_a_declared_capability_with_a_home():
    cap = CAPABILITY_BY_SLUG.get("concept-visualization")
    assert cap is not None, "概念效果图必须是一项已登记的专业能力"
    assert set(cap.stages) <= {"S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8"}
    assert "S3" in cap.stages
    assert cap.source == "OmniAiLab"


def test_the_batch_is_attached_to_gate_g3_and_not_to_a_stage_body():
    assert post_gate_actions_for_stage("S3") == ["concept-visualization"]
    assert POST_GATE_ACTIONS == {"G3": ["concept-visualization"]}
    for gate, actions in POST_GATE_ACTIONS.items():
        assert gate.startswith("G")
        for slug in actions:
            assert slug in CAPABILITY_BY_SLUG


def test_confirming_g3_produces_the_concept_render_package():
    with tempfile.TemporaryDirectory() as td:
        project, runner, outcomes = _confirmed_plan(td)
        notes = " ".join(outcomes["S3"].notes)
        assert "门禁后置动作 concept-visualization" in notes, outcomes["S3"].notes

        store = project.meta.get("gate_actions", {})
        assert "concept-visualization" in store, store
        entry = store["concept-visualization"]
        assert entry["stage"] == "S3"
        assert entry["views"] >= 1
        assert entry["authoritative"] is False
        assert entry["revision"] == project.revision

        base = Path(td) / entry["dir"]
        assert (base / "canvas-jobs.json").exists()
        assert (base / "canvas-brief.md").exists()
        assert (base / "RUN-STATUS.md").exists()


def test_rejecting_g3_clears_the_batch():
    with tempfile.TemporaryDirectory() as td:
        project, runner, _ = _confirmed_plan(td)
        assert "concept-visualization" in project.meta.get("gate_actions", {})
        runner.reject("S3", "面积要重算")
        assert "concept-visualization" not in project.meta.get("gate_actions", {})


# --------------------------------------------------------------------------
# content
# --------------------------------------------------------------------------
def test_every_view_points_at_a_real_space_in_the_confirmed_plan():
    with tempfile.TemporaryDirectory() as td:
        project, runner = _installed_plan(td)
        res = canvas.render(project, Path(td) / "cr", scheme="A", limit=5,
                            project_dir=Path(td))
        # G3 confirms a scheme without installing it into the model (that is S4's
        # job), so a view may reference a scheme space that is not yet canonical.
        ids = {s.id for s in project.spaces}
        ids |= {s.id for scheme in runner.schemes.values() for s in scheme.spaces}
        assert res.views, "已确认平面必须能产出概念效果图机位"
        for v in res.views:
            if v.space_id == "project:overview":
                assert v.label == "整体空间印象"
            else:
                assert v.space_id in ids, f"{v.id} 指向了不存在的空间"
            assert v.prompt_sha
            assert v.negative_prompt
            # the prompt must carry the revision it was drawn from
            assert f"r{project.revision}" in v.prompt
            assert project.project_id in v.prompt


def test_models_are_picked_by_declared_rules_not_by_guessing():
    with tempfile.TemporaryDirectory() as td:
        project, _runner = _installed_plan(td)
        res = canvas.render(project, Path(td) / "cr", limit=5,
                            project_dir=Path(td))
        by_id = {v.id: v for v in res.views}
        assert by_id["01_overview"].model == "OmniP", "整户型机位按声明应用 OmniP"
        assert all(v.model for v in res.views)
        assert all(v.model_reason for v in res.views)
        cats = canvas.DEFAULT_CATALOG
        assert [m["id"] for m in canvas.recommended_models(cats)] == ["OmniP", "image2.5"]


def test_an_explicit_model_override_wins():
    with tempfile.TemporaryDirectory() as td:
        project, _runner = _installed_plan(td)
        res = canvas.render(project, Path(td) / "cr", limit=3, model="OmniP",
                            project_dir=Path(td))
        assert {v.model for v in res.views} == {"OmniP"}


def test_a_contract_that_advertises_other_models_wins_and_records_the_gap():
    cat = canvas.load_catalog()
    sel = canvas.select_model(cat, canvas.NEED_REFERENCE, advertised=["OmniP"])
    assert sel["model"] == "OmniP"
    assert sel["mismatches"], "与契约不一致时必须记录偏差，不能静默沿用推荐"


def test_reference_images_are_real_raster_files_from_the_model():
    with tempfile.TemporaryDirectory() as td:
        project, _runner = _installed_plan(td)
        res = canvas.render(project, Path(td) / "cr", limit=3, project_dir=Path(td))
        ref = res.files.get("reference_plan") or ""
        if not ref:
            # Pillow missing is an honest degradation, not a failure
            assert res.warnings
            return
        p = Path(ref)
        assert p.exists() and p.stat().st_size > 1000
        assert p.read_bytes().startswith(b"\x89PNG")
        assert all(v.reference for v in res.views)


# --------------------------------------------------------------------------
# honesty
# --------------------------------------------------------------------------
def test_without_a_platform_nothing_is_generated_and_that_is_stated():
    with tempfile.TemporaryDirectory() as td:
        project, _runner = _installed_plan(td)
        res = canvas.render(project, Path(td) / "cr", limit=4, project_dir=Path(td))
        assert res.provider_state == "not_configured"
        assert res.status == "degraded"
        assert not res.generated
        assert res.pending, "任务包必须就绪，逐条标注待平台"
        assert all(v.status == "awaiting_platform" for v in res.views)

        renders = Path(td) / "cr" / "renders"
        images = list(renders.rglob("*.png")) + list(renders.rglob("*.jpg")) \
            if renders.exists() else []
        assert not images, "未连接平台时不得留下任何占位图片"

        payload = json.loads(Path(res.files["jobs"]).read_text(encoding="utf-8"))
        assert payload["authoritative"] is False
        assert payload["provider"]["state"] == "not_configured"
        assert payload["provider"]["scope_used"] == ""
        assert all(j["authoritative"] is False for j in payload["jobs"])


def test_submitting_without_authorisation_stops_at_the_permission_gate():
    """A connected platform must still not be called without explicit consent."""
    with tempfile.TemporaryDirectory() as td:
        project, _runner = _installed_plan(td)
        stub = _StubCanvasProvider()
        with _patched_discover(stub):
            res = canvas.render(project, Path(td) / "cr", limit=3,
                                project_dir=Path(td), submit=True,
                                authorized=False)
        assert stub.calls == [], "未授权时一条请求都不许发出"
        assert res.scope_used == ""
        assert not res.generated
        assert any("L3" in n or "授权" in n for n in res.notes), res.notes


def test_with_authorisation_a_connected_platform_really_produces_assets():
    """The happy path: platform connected + authorised → files, links, statuses."""
    with tempfile.TemporaryDirectory() as td:
        project, _runner = _installed_plan(td)
        stub = _StubCanvasProvider()
        with _patched_discover(stub):
            res = canvas.render(project, Path(td) / "cr", limit=3,
                                project_dir=Path(td), submit=True,
                                authorized=True)
        assert len(stub.calls) == len(res.views), "每个机位一次提交"
        assert res.scope_used == "reference_image_generation"
        assert res.generated, "授权后必须真的产出图像"
        assert res.status in ("ok", "partial")
        for v in res.generated:
            assert v.output and Path(v.output).exists()
            assert v.output.endswith(".png")
            assert v.detail.startswith("job ")


def test_connected_platform_but_no_declared_canvas_scope_degrades_honestly():
    with tempfile.TemporaryDirectory() as td:
        project, _runner = _installed_plan(td)
        stub = _StubCanvasProvider(scopes=["image_generation"], models=["OmniP"])
        # advertised models no longer include image2.5 → the contract wins
        with _patched_discover(stub):
            res = canvas.render(project, Path(td) / "cr", limit=3,
                                project_dir=Path(td), submit=True,
                                authorized=True)
        assert res.scope_used == "image_generation"
        assert {v.model for v in res.views} == {"OmniP"}, "契约未声明 image2.5，不得硬用"
        assert res.generated


# --------------------------------------------------------------------------
# deliverable
# --------------------------------------------------------------------------
def test_the_batch_ships_with_an_editable_deck_verified_independently():
    with tempfile.TemporaryDirectory() as td:
        project, _runner = _installed_plan(td)
        res = canvas.render(project, Path(td) / "cr", limit=4, project_dir=Path(td))
        pptx = res.files.get("deck_pptx") or ""
        if not pptx:
            assert res.warnings
            return
        assert Path(pptx).exists() and Path(pptx).stat().st_size > 5000

        from omniailab_ai_architect.tools import registry as tool_registry

        rep = tool_registry().verify(pptx)
        assert rep and rep.get("ok"), rep


def test_canvas_jobs_matches_its_published_schema():
    with tempfile.TemporaryDirectory() as td:
        project, _runner = _installed_plan(td)
        res = canvas.render(project, Path(td) / "cr", limit=3, project_dir=Path(td))
        payload = json.loads(Path(res.files["jobs"]).read_text(encoding="utf-8"))
        schema_path = Path(__file__).resolve().parents[2] / "schemas" / "concept-render.schema.json"
        assert schema_path.exists()
        try:
            import jsonschema
        except ImportError:           # pragma: no cover
            return
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        jsonschema.Draft202012Validator(schema).validate(payload)


def test_render_without_a_plan_says_what_to_do_instead_of_inventing_views():
    with tempfile.TemporaryDirectory() as td:
        project = build_demo_project(Path(td))     # no scheme installed yet
        res = canvas.render(project, Path(td) / "cr", project_dir=Path(td))
        assert res.status == "blocked"
        assert not res.views
        assert res.warnings and "S3" in res.warnings[0]
