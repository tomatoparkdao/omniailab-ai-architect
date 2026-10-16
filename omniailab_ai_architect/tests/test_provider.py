"""Provider layer: discovery, honesty, orchestration, asset linking."""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from omniailab_ai_architect.demo import build_demo_project  # noqa: E402
from omniailab_ai_architect.providers import (  # noqa: E402
    CAPABILITY_SCOPES,
    LocalDeterministicProvider,
    NotConfigured,
    OmniAiLabProvider,
    ProviderCapability,
    ProviderError,
    ProviderJob,
    ProviderRegistry,
    discover,
)
from omniailab_ai_architect.providers.base import MediaProvider  # noqa: E402


# --------------------------------------------------------------------------
def test_unconfigured_omnilab_reports_not_configured_with_reasons():
    with tempfile.TemporaryDirectory() as td:
        p = OmniAiLabProvider(project_dir=td)
        cap = p.probe()
    assert cap.state == "not_configured"
    assert cap.usable is False
    assert cap.endpoint_known is False
    assert cap.missing, "必须逐条说明缺什么"
    assert any("契约" in m for m in cap.missing)
    assert cap.hint


def test_unconfigured_provider_refuses_to_submit():
    with tempfile.TemporaryDirectory() as td:
        p = OmniAiLabProvider(project_dir=td)
        try:
            p.submit("image_generation", {})
        except NotConfigured as exc:
            assert "未配置" in str(exc)
        else:  # pragma: no cover
            raise AssertionError("未配置的 provider 必须拒绝提交，而不是伪造成功")


def test_endpoints_are_never_guessed():
    """A config without an API contract must NOT be treated as connected."""
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "omniailab.config.json").write_text(json.dumps({
            "base_url": "https://example.invalid",
            "api_key": "x" * 12,
        }), encoding="utf-8")
        cap = OmniAiLabProvider(project_dir=root).probe()
    assert cap.state == "not_configured", cap.to_dict()
    assert cap.endpoint_known is False
    assert any("契约" in m for m in cap.missing)


def test_broken_contract_is_reported_not_swallowed():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "providers").mkdir()
        (root / "providers" / "omniailab.api.json").write_text("{ not json", encoding="utf-8")
        cap = OmniAiLabProvider(project_dir=root).probe()
    assert cap.state == "error"
    assert cap.missing


def test_incomplete_contract_lists_exact_problems():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "providers").mkdir()
        (root / "providers" / "omniailab.api.json").write_text(json.dumps({
            "base_url": "https://example.invalid",
            "auth": "made-up-scheme",
            "endpoints": {"submit": "/j"},
        }), encoding="utf-8")
        cap = OmniAiLabProvider(project_dir=root).probe()
    assert cap.state == "not_configured"
    joined = " ".join(cap.missing)
    assert "auth" in joined and "poll" in joined and "models" in joined


def test_capability_rejects_unknown_scope_and_state():
    for bad in ({"state": "yes"}, {"state": "connected", "scopes": ["teleport"]}):
        try:
            ProviderCapability(provider="x", **bad)
        except ProviderError:
            pass
        else:  # pragma: no cover
            raise AssertionError(f"非法能力声明必须被拒绝：{bad}")


# --------------------------------------------------------------------------
def test_local_provider_is_connected_and_honest():
    cap = LocalDeterministicProvider().probe()
    assert cap.state == "connected"
    assert "image_generation" in cap.scopes
    assert cap.can("multi_view_visualization")
    assert not cap.can("video_generation"), "本地 provider 不得声称能做视频"
    assert any("非写实渲染" in n or "示意图" in n for n in cap.notes)


def test_local_provider_writes_a_real_png():
    with tempfile.TemporaryDirectory() as td:
        project = build_demo_project(Path(td))
        reg = ProviderRegistry([LocalDeterministicProvider()])
        job = reg.generate("image_generation",
                           {"project": project, "out_path": str(Path(td) / "plan.png")},
                           Path(td))
        assert job.status == "succeeded", job.error
        out = Path(job.outputs[0])
        assert out.exists() and out.stat().st_size > 2000
        assert out.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
        assert job.authoritative is False
        assert "非权威" in job.to_dict()["note"]


def test_contact_sheet_lists_every_room():
    with tempfile.TemporaryDirectory() as td:
        project = build_demo_project(Path(td))
        reg = ProviderRegistry([LocalDeterministicProvider()])
        job = reg.generate("multi_view_visualization",
                           {"project": project, "out_path": str(Path(td) / "sheet.png")},
                           Path(td))
        assert job.status == "succeeded", job.error
        assert len(job.outputs) == 2
        for o in job.outputs:
            assert Path(o).exists() and Path(o).stat().st_size > 1000


def test_registry_selects_only_usable_providers():
    with tempfile.TemporaryDirectory() as td:
        reg = ProviderRegistry([OmniAiLabProvider(project_dir=td), LocalDeterministicProvider()])
        chosen = reg.select("image_generation")
        assert chosen is not None and chosen.id == "local"
        assert reg.select("video_generation") is None
        rep = reg.report()
        assert rep["not_configured"] == ["omniailab"]
        assert rep["scopes"]["video_generation"] == []


def test_registry_refuses_when_nothing_can_do_the_scope():
    with tempfile.TemporaryDirectory() as td:
        reg = ProviderRegistry([OmniAiLabProvider(project_dir=td)])
        try:
            reg.generate("video_generation", {}, Path(td))
        except NotConfigured as exc:
            assert "没有任何 provider" in str(exc)
        else:  # pragma: no cover
            raise AssertionError("无可用 provider 时必须明确拒绝")


def test_scope_cannot_be_faked_by_an_unusable_provider():
    with tempfile.TemporaryDirectory() as td:
        p = OmniAiLabProvider(project_dir=td)
        assert p.probe().can("image_generation") is False
        try:
            p.run("image_generation", {}, Path(td))
        except NotConfigured:
            pass
        else:  # pragma: no cover
            raise AssertionError("不可用的 provider 不得执行任务")


def test_failed_job_is_retried_then_reported():
    class Flaky(MediaProvider):
        id = "flaky"

        def __init__(self) -> None:
            self.calls = 0

        def probe(self):
            return ProviderCapability(provider="flaky", state="connected",
                                      scopes=["image_generation"], models=["m"])

        def submit(self, operation, params):
            self.calls += 1
            if self.calls < 3:
                raise RuntimeError("transient")
            return ProviderJob(job_id="j1", provider="flaky", operation=operation,
                               status="succeeded")

        def poll(self, job):
            return job

        def fetch(self, job, target_dir):
            return []

    f = Flaky()
    job = f.run("image_generation", {}, ".", poll_interval_s=0, max_attempts=3)
    assert job.status == "succeeded" and f.calls == 3

    class Always(Flaky):
        def __init__(self) -> None:
            super().__init__()

        def submit(self, operation, params):
            self.calls += 1
            raise RuntimeError("permanent failure")

    a = Always()
    try:
        a.run("image_generation", {}, ".", poll_interval_s=0, max_attempts=2)
    except ProviderError as exc:
        assert "permanent" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("永久失败必须抛错，不得返回成功")


def test_asset_version_linking():
    with tempfile.TemporaryDirectory() as td:
        project = build_demo_project(Path(td))
        reg = ProviderRegistry([LocalDeterministicProvider()])
        job = reg.generate("image_generation",
                           {"project": project, "out_path": str(Path(td) / "p.png")},
                           Path(td))
        links = reg.link_asset(job, job.outputs, project.project_id,
                               project.revision, "S5", "image_generation")
        d = links[0].to_dict()
        assert d["project_id"] == project.project_id
        assert d["revision"] == project.revision
        assert d["job_id"] == job.job_id
        assert d["scope"] == "image_generation"


def test_discover_is_deterministic_and_has_both_providers():
    with tempfile.TemporaryDirectory() as td:
        reg = discover(td, refresh=True)
        ids = [c.provider for c in reg.capabilities()]
    assert "omniailab" in ids and "local" in ids
    assert set(CAPABILITY_SCOPES) >= set(reg.report()["scopes"])


def test_render_adapter_consults_the_provider_registry():
    from omniailab_ai_architect.adapters.render import RenderAdapter

    backends = RenderAdapter._configured_backends()
    assert isinstance(backends, list)
    assert "local" in backends, "本地 provider 可用时渲染适配器应当看到它"
