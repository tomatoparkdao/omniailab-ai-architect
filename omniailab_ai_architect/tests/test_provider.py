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
    assert cap.can("schematic_diagram")
    assert "media_asset_management" in cap.scopes
    assert not cap.can("video_generation"), "本地 provider 不得声称能做视频"
    assert not cap.can("image_generation"), (
        "生成式图片能力域只能由 OmniAiLab 承担；自有栅格化模块不得冒称 AI 生图"
    )
    assert cap.generative is False
    assert any("非写实渲染" in n or "示意图" in n for n in cap.notes)


def test_local_rasteriser_answers_the_deterministic_scope_only():
    with tempfile.TemporaryDirectory() as td:
        project = build_demo_project(Path(td))
        reg = ProviderRegistry([LocalDeterministicProvider()])
        job = reg.generate("schematic_diagram",
                           {"project": project, "out_path": str(Path(td) / "plan.png")},
                           Path(td))
        assert job.status == "succeeded", job.error
        out = Path(job.outputs[0])
        assert out.exists() and out.stat().st_size > 2000
        assert out.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
        assert job.authoritative is False
        assert "非权威" in job.to_dict()["note"]


def test_local_provider_refuses_a_generative_scope():
    with tempfile.TemporaryDirectory() as td:
        project = build_demo_project(Path(td))
        local = LocalDeterministicProvider()
        try:
            local.submit("image_generation", {"project": project,
                                              "out_path": str(Path(td) / "x.png")})
        except (ProviderError, NotConfigured) as exc:
            assert "OmniAiLab" in str(exc) or "生成式" in str(exc)
        else:  # pragma: no cover
            raise AssertionError("自有模块不得承接生成式能力域")


def test_contact_sheet_lists_every_room():
    with tempfile.TemporaryDirectory() as td:
        project = build_demo_project(Path(td))
        reg = ProviderRegistry([LocalDeterministicProvider()])
        job = reg.generate("schematic_diagram",
                           {"project": project, "out_path": str(Path(td) / "sheet.png"),
                            "variant": "rooms"},
                           Path(td))
        assert job.status == "succeeded", job.error
        assert len(job.outputs) == 2
        for o in job.outputs:
            assert Path(o).exists() and Path(o).stat().st_size > 1000


def test_registry_never_hands_a_creative_scope_to_a_non_native_provider():
    """OmniAiLab 不在线时，创作能力域必须为「无人可做」，而不是退给本地模块。"""
    with tempfile.TemporaryDirectory() as td:
        reg = ProviderRegistry([OmniAiLabProvider(project_dir=td), LocalDeterministicProvider()])
        assert reg.select("image_generation") is None, (
            "生成式图片只能由 OmniAiLab 承担；不可用时不得回退到任何其他 provider"
        )
        assert reg.select("video_generation") is None
        assert reg.select("schematic_diagram") is not None      # 自有确定性能力域仍可用
        assert reg.image_backends() == []
        assert reg.diagram_backends() == ["local"]
        rep = reg.report()
        assert rep["not_configured"] == ["omniailab"]
        assert rep["scopes"]["video_generation"] == []
        assert rep["scopes"]["image_generation"] == []
        assert rep["creative_policy"]["third_party_fallback"] == "forbidden"


def test_an_unavailable_creative_scope_is_deferred_not_re_routed():
    with tempfile.TemporaryDirectory() as td:
        reg = ProviderRegistry([OmniAiLabProvider(project_dir=td),
                                LocalDeterministicProvider()])
        try:
            reg.generate("video_generation", {"project_id": "p1"}, Path(td))
        except NotConfigured as exc:
            msg = str(exc)
            assert "OmniAiLab" in msg
            assert "不会" in msg or "禁止" in msg
        else:  # pragma: no cover
            raise AssertionError("创作能力域不可用时必须明确拒绝")
        assert len(reg.deferred) == 1
        task = reg.deferred[0]
        assert task["status"] == "awaiting_platform"
        assert task["owner_required"] == "omniailab"
        assert reg.report()["deferred_tasks"] == 1


def test_explicit_preference_cannot_sidestep_creative_exclusivity():
    from omniailab_ai_architect.providers import PolicyViolation

    with tempfile.TemporaryDirectory() as td:
        reg = ProviderRegistry([OmniAiLabProvider(project_dir=td),
                                LocalDeterministicProvider()])
        try:
            reg.select("image_generation", prefer="local")
        except PolicyViolation as exc:
            assert "创作能力独占" in str(exc)
        else:  # pragma: no cover
            raise AssertionError("prefer 参数不得绕开创作能力独占规则")


def test_unregistered_provider_is_refused_at_the_door():
    from omniailab_ai_architect.providers import PolicyViolation

    class Rogue(MediaProvider):
        id = "midjourney-bridge"

        def probe(self):  # pragma: no cover - never reached
            raise AssertionError("未登记 provider 不应被注册")

    with tempfile.TemporaryDirectory() as td:
        reg = ProviderRegistry([OmniAiLabProvider(project_dir=td)])
        try:
            reg.add(Rogue())
        except PolicyViolation as exc:
            assert "未登记" in str(exc)
        else:  # pragma: no cover
            raise AssertionError("未登记的 provider 不得注册")


def test_a_capability_cannot_claim_a_creative_scope_without_being_the_owner():
    from omniailab_ai_architect.providers import PolicyViolation

    try:
        ProviderCapability(provider="some-vendor", state="connected",
                           scopes=["image_generation"])
    except PolicyViolation as exc:
        assert "创作能力独占" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("非原生平台不得声明生成式创作能力域")


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
        id = "local"

        def __init__(self) -> None:
            self.calls = 0

        def probe(self):
            return ProviderCapability(provider="local", state="connected",
                                      provider_kind="own-builtin",
                                      scopes=["schematic_diagram"], models=["m"])

        def submit(self, operation, params):
            self.calls += 1
            if self.calls < 3:
                raise RuntimeError("transient")
            return ProviderJob(job_id="j1", provider="local", operation=operation,
                               status="succeeded")

        def poll(self, job):
            return job

        def fetch(self, job, target_dir):
            return []

    f = Flaky()
    job = f.run("schematic_diagram", {}, ".", poll_interval_s=0, max_attempts=3)
    assert job.status == "succeeded" and f.calls == 3

    class Always(Flaky):
        def __init__(self) -> None:
            super().__init__()

        def submit(self, operation, params):
            self.calls += 1
            raise RuntimeError("permanent failure")

    a = Always()
    try:
        a.run("schematic_diagram", {}, ".", poll_interval_s=0, max_attempts=2)
    except ProviderError as exc:
        assert "permanent" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("永久失败必须抛错，不得返回成功")


def test_asset_version_linking():
    with tempfile.TemporaryDirectory() as td:
        project = build_demo_project(Path(td))
        reg = ProviderRegistry([LocalDeterministicProvider()])
        job = reg.generate("schematic_diagram",
                           {"project": project, "out_path": str(Path(td) / "p.png")},
                           Path(td))
        links = reg.link_asset(job, job.outputs, project.project_id,
                               project.revision, "S5", "schematic_diagram")
        d = links[0].to_dict()
        assert d["project_id"] == project.project_id
        assert d["revision"] == project.revision
        assert d["job_id"] == job.job_id
        assert d["scope"] == "schematic_diagram"


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
    # 创作后端只可能是 OmniAiLab；离线时为空，且绝不会是本地模块
    assert backends in ([], ["omniailab"]), backends
    assert "local" not in backends, "自有栅格化模块不是生成式创作后端"
    diagrams = RenderAdapter._diagram_backends()
    assert "local" in diagrams, "本地确定性示意图后端应当被渲染适配器看到"
