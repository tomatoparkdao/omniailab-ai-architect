"""P0：付费任务的提交安全 —— 一次任务只能扣一次钱。

这里测的不是"能不能生成"，而是**出错时会不会重复付费**：

* 轮询超时 → 只许继续查，不许重新提交；
* 轮询连续失败 → 标记"已提交、状态未知"，停止自动重试；
* 提交发出后连接断了 → `submitted_unknown`，绝不能当成"没发生"；
* 同一份参数两次运行 → 幂等键相同（平台可据此去重）。

前三条任何一条退化成"重试整个流程"，都会变成给客户多扣一次钱。

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any, Dict, List

from omniarchitect.providers.base import (
    MediaProvider,
    NotConfigured,
    ProviderCapability,
    ProviderError,
    ProviderJob,
    SubmitStateUnknown,
)


class _Stub(MediaProvider):
    """A platform that can misbehave in each of the ways that cost money."""

    id = "omniailab"
    name = "stub"
    kind = "native-platform"
    generative = True

    def __init__(self, mode: str = "ok") -> None:
        self.mode = mode
        self.submits = 0
        self.polls = 0
        self.fetches = 0
        #: 服务端真正建了几个任务（用于判断"客户端以为没提交，其实已受理"）
        self.server_jobs: List[str] = []

    def probe(self) -> ProviderCapability:
        return ProviderCapability(provider="omniailab", state="connected",
                                  provider_kind="native-platform",
                                  scopes=["image_generation"], models=["stub-model"])

    def estimate_cost(self, operation: str, params: Dict[str, Any]) -> float:
        return 1.0

    def submit(self, operation: str, params: Dict[str, Any]) -> ProviderJob:
        self.submits += 1
        if self.mode == "rejected":
            raise ProviderError("POST /jobs -> HTTP 400: prompt rejected")
        # 服务端先受理（建任务、计费），随后客户端拿不到响应
        job_id = f"job-{len(self.server_jobs) + 1}"
        self.server_jobs.append(job_id)
        if self.mode == "accepted_but_lost":
            raise SubmitStateUnknown(self.id, "ConnectionResetError: 连接被重置")
        return ProviderJob(job_id=job_id, provider=self.id, operation=operation,
                           status="queued")

    def poll(self, job: ProviderJob) -> ProviderJob:
        self.polls += 1
        if self.mode == "flaky_poll":
            raise ConnectionError("读超时")
        if self.mode == "timeout":
            job.status = "running"
            return job
        if self.mode == "ok" and self.polls >= 2:
            job.status = "succeeded"
            job.outputs = ["http://example.invalid/a.png"]
            return job
        job.status = "running"
        return job

    def fetch(self, job: ProviderJob, target_dir: str | Path) -> List[str]:
        self.fetches += 1
        out = Path(target_dir) / "a.png"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 2048)
        return [str(out)]


def _run(p: _Stub, **kw: Any) -> ProviderJob:
    kw.setdefault("timeout_s", 0.05)
    kw.setdefault("poll_interval_s", 0.005)
    kw.setdefault("max_poll_retries", 2)
    kw.setdefault("poll_backoff_s", 0.001)
    with tempfile.TemporaryDirectory() as td:
        return p.run("image_generation", {"prompt": "x", "units": 1}, td, **kw)


# --------------------------------------------------------------------------
# 1. 轮询超时 ≠ 提交失败
# --------------------------------------------------------------------------
def test_poll_timeout_never_resubmits():
    p = _Stub("timeout")
    job = _run(p)
    assert p.submits == 1, f"轮询超时后又提交了 {p.submits} 次"
    assert len(p.server_jobs) == 1
    assert job.status == "unknown"
    assert job.poll_exhausted is True
    assert job.submitted_unknown is False, "拿到了 job_id，不该说提交结果未知"
    assert job.job_id and job.accepted is True
    assert "不要重新提交" in job.recovery


# --------------------------------------------------------------------------
# 2. 轮询连续失败 → 停止重试，任务仍算已受理
# --------------------------------------------------------------------------
def test_repeated_poll_failure_stops_without_resubmitting():
    p = _Stub("flaky_poll")
    job = _run(p, timeout_s=30.0, max_poll_retries=2)
    assert p.submits == 1
    assert job.status == "unknown"
    assert job.poll_exhausted is True
    assert job.accepted is True
    assert p.polls == 3, f"应在 {2} 次重试后停止，实际轮询 {p.polls} 次"
    assert "任务" in job.recovery and "不要重新提交" in job.recovery


# --------------------------------------------------------------------------
# 3. 服务端已受理、客户端连接中断 → submitted_unknown，不是"没发生"
# --------------------------------------------------------------------------
def test_server_accepted_but_connection_dropped_is_unknown_not_absent():
    p = _Stub("accepted_but_lost")
    job = _run(p)
    assert p.submits == 1
    assert len(p.server_jobs) == 1, "服务端确实建了任务"
    assert job.submitted_unknown is True
    assert job.status == "unknown"
    assert job.accepted is True, "结果未知必须视为『可能已计费』"
    assert job.idempotency_key in job.recovery
    assert "核实" in job.recovery
    # 关键：没有第二次提交
    assert p.submits == 1


# --------------------------------------------------------------------------
# 4. 明确被拒（4xx）→ 报错且不重试；未配置 → 连请求都没发
# --------------------------------------------------------------------------
def test_rejected_submission_raises_once_and_stops():
    p = _Stub("rejected")
    try:
        _run(p)
    except ProviderError as exc:
        assert "HTTP 400" in str(exc)
        assert not isinstance(exc, SubmitStateUnknown)
    else:
        raise AssertionError("4xx 被拒却当成成功")
    assert p.submits == 1, "明确被拒不该自动重提"


def test_not_configured_sends_nothing():
    p = _Stub("ok")

    def _probe() -> ProviderCapability:
        return ProviderCapability(provider="omniailab", state="not_configured",
                                  provider_kind="native-platform", missing=["api_key"])

    p.probe = _probe  # type: ignore[method-assign]
    try:
        _run(p)
    except NotConfigured:
        pass
    else:
        raise AssertionError("未配置却继续执行")
    assert p.submits == 0 and p.polls == 0


# --------------------------------------------------------------------------
# 5. 正常路径：提交一次、轮询多次、取回一次
# --------------------------------------------------------------------------
def test_happy_path_submits_once():
    p = _Stub("ok")
    job = _run(p)
    assert p.submits == 1
    assert p.polls >= 2
    assert p.fetches == 1
    assert job.status == "succeeded" and job.outputs
    assert Path(job.outputs[0]).suffix == ".png"


# --------------------------------------------------------------------------
# 6. 幂等键：同参数同键，改参数换键
# --------------------------------------------------------------------------
def test_idempotency_key_is_stable_for_the_same_work():
    p = _Stub("ok")
    a = p.idempotency_key("image_generation", {"prompt": "客厅", "units": 1})
    b = p.idempotency_key("image_generation", {"prompt": "客厅", "units": 1})
    c = p.idempotency_key("image_generation", {"prompt": "卧室", "units": 1})
    assert a == b and a != c
    # 运行期真实使用同一个键
    job = _run(p, idempotency_key=a)
    assert job.idempotency_key == a


# --------------------------------------------------------------------------
# 7. 概念视觉层：未知状态不得记成 failed（否则下次运行会重新付费）
# --------------------------------------------------------------------------
class _Reg:
    def __init__(self, provider: _Stub) -> None:
        self.provider = provider
        self.linked: List[str] = []

    def capabilities(self):
        return [self.provider.probe()]

    def get(self, pid):
        return self.provider

    def generate(self, scope, params, target_dir, prefer=""):
        return ProviderJob(job_id="srv-1", provider="omniailab", operation=scope,
                           status="unknown", submitted_unknown=True,
                           idempotency_key=params.get("idempotency_key", ""),
                           recovery="按幂等键核实")

    def link_asset(self, *a, **k):
        return []

    def defer_creative_task(self, *a, **k):
        return {}


class _patched:
    def __init__(self, target, name, value):
        self.target, self.name, self.value, self.orig = target, name, value, None

    def __enter__(self):
        self.orig = getattr(self.target, self.name)
        setattr(self.target, self.name, self.value)
        return self

    def __exit__(self, *exc):
        setattr(self.target, self.name, self.orig)
        return False


def test_visual_ledger_keeps_unknown_as_submitted_and_does_not_retry():
    import omniarchitect.providers as providers
    from omniarchitect import concept as C
    from omniarchitect.concept import visual as vis
    from omniarchitect.demo import build_demo_project

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        p = build_demo_project(tmp / "proj")
        ctx = C.build_context(p, require_gate=False)
        concept = C.generate_concepts(ctx, limit=2)["concepts"][0]
        jobs = vis.build_jobs(concept, ctx, p)
        out = tmp / "out"
        stub = _Stub("ok")
        reg = _Reg(stub)
        with _patched(providers, "discover", lambda *a, **k: reg):
            first = vis.submit(jobs, p, out, submit=True, authorize=True, max_cost=100)
            second = vis.submit(jobs, p, out, submit=True, authorize=True, max_cost=100)

        assert first.unknown == len(jobs)
        assert first.failed == 0, "结果未知被记成失败，下次就会重付"
        assert all(j["status"] == "submitted_unknown" for j in first.jobs)
        # 第二次运行：台账里是 submitted，不许再调 provider
        assert second.submitted == 0
        assert second.unknown == len(jobs)

        ledger = vis.load_ledger(out / vis.LEDGER_NAME)
        assert all(e["status"] == "submitted" for e in ledger["entries"].values())


# --------------------------------------------------------------------------
# 8. 生命周期：submitted → succeeded → asset_validated → project_linked
# --------------------------------------------------------------------------
class _ChainProvider(_Stub):
    """能按剧本走完/走残一条任务的生命周期。"""

    def __init__(self, script: str = "ok") -> None:
        super().__init__("ok")
        self.script = script
        self.polls = 0
        self.fetches = 0
        self.png = ""

    def generate(self, scope, params, target_dir):
        self.submits += 1
        out = Path(target_dir) / "chain.png"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 2048)
        self.png = str(out)
        if self.script == "unknown":
            return ProviderJob(job_id="srv-9", provider="omniailab",
                               operation=scope, status="unknown",
                               submitted_unknown=False, poll_exhausted=True,
                               idempotency_key=params.get("idempotency_key", ""),
                               recovery="任务已受理，稍后核实")
        return ProviderJob(job_id="srv-9", provider="omniailab", operation=scope,
                           status="succeeded", outputs=[self.png],
                           idempotency_key=params.get("idempotency_key", ""))

    def poll(self, job):
        self.polls += 1
        if self.script == "running_then_ok" and self.polls == 1:
            job.status = "running"
            return job
        job.status = "succeeded"
        job.outputs = [self.png]
        return job

    def fetch(self, job, target_dir):
        self.fetches += 1
        return [self.png]


class _ChainRegistry:
    def __init__(self, provider: _ChainProvider) -> None:
        self.provider = provider
        self.links: List[Any] = []

    def capabilities(self):
        return [self.provider.probe()]

    def get(self, pid):
        return self.provider

    def generate(self, scope, params, target_dir, prefer=""):
        return self.provider.generate(scope, params, target_dir)

    def link_asset(self, job, assets, project_id, revision, stage, scope):
        self.links.append((job.job_id, list(assets)))
        return []

    def defer_creative_task(self, *a, **k):
        return {}


def _fresh_project(tmp: Path):
    from omniarchitect import concept as C
    from omniarchitect.demo import build_demo_project

    p = build_demo_project(tmp / "proj")
    ctx = C.build_context(p, require_gate=False)
    concept = C.generate_concepts(ctx, limit=2)["concepts"][0]
    from omniarchitect.concept import visual as vis

    return p, vis.build_jobs(concept, ctx, p)[:1]


def test_lifecycle_reaches_project_linked():
    from omniarchitect.concept import visual as vis

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        p, jobs = _fresh_project(tmp)
        out = tmp / "out"
        prov = _ChainProvider("ok")
        reg = _ChainRegistry(prov)
        with _patched(providers_mod(), "discover", lambda *a, **k: reg):
            res = vis.submit(jobs, p, out, submit=True, authorize=True, max_cost=10)
        assert res.generated == 1
        entry = list(vis.load_ledger(out / vis.LEDGER_NAME)["entries"].values())[0]
        states = [h["state"] for h in entry["history"]]
        assert states[0] == "submitted"
        for s in ("succeeded", "asset_validated", "project_linked"):
            assert s in states, states
        assert entry["artifacts"], "没有登记成项目资产"
        ids = {a.id for a in p.artifacts}
        assert entry["artifacts"][0] in ids, "资产没写进项目"
        assert reg.links, "没有 provider 资产关联"


def test_resume_recovers_unknown_without_another_submit():
    from omniarchitect.concept import visual as vis

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        p, jobs = _fresh_project(tmp)
        out = tmp / "out"
        prov = _ChainProvider("unknown")
        with _patched(providers_mod(), "discover", lambda *a, **k: _ChainRegistry(prov)):
            first = vis.submit(jobs, p, out, submit=True, authorize=True, max_cost=10)
        assert first.unknown == 1 and prov.submits == 1
        entry = list(vis.load_ledger(out / vis.LEDGER_NAME)["entries"].values())[0]
        assert entry["state"] == "submitted_unknown"

        # 第一轮核实：平台上还在跑
        prov.script = "running_then_ok"
        prov.polls = 0
        with _patched(providers_mod(), "discover", lambda *a, **k: _ChainRegistry(prov)):
            r1 = vis.resume_pending(p, out)
        assert r1["running"] == 1 and prov.submits == 1, "恢复路径不能重新提交"
        entry = list(vis.load_ledger(out / vis.LEDGER_NAME)["entries"].values())[0]
        assert entry["state"] == "running"

        # 第二轮核实：完成 → 取回 → 校核 → 登记
        prov.polls = 5
        with _patched(providers_mod(), "discover", lambda *a, **k: _ChainRegistry(prov)):
            r2 = vis.resume_pending(p, out)
        assert r2["resumed"] == 1, r2
        assert prov.submits == 1, "整个恢复过程只允许一次提交"
        entry = list(vis.load_ledger(out / vis.LEDGER_NAME)["entries"].values())[0]
        assert entry["state"] == "project_linked"
        assert entry["artifacts"]


def test_resume_without_platform_does_not_submit():
    from omniarchitect.concept import visual as vis

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        p, jobs = _fresh_project(tmp)
        out = tmp / "out"
        prov = _ChainProvider("unknown")
        with _patched(providers_mod(), "discover", lambda *a, **k: _ChainRegistry(prov)):
            vis.submit(jobs, p, out, submit=True, authorize=True, max_cost=10)

        class _Down(_ChainRegistry):
            def capabilities(self):
                from omniarchitect.providers.base import ProviderCapability

                return [ProviderCapability(provider="omniailab",
                                           state="not_configured",
                                           provider_kind="native-platform",
                                           missing=["api_key"])]

        before = prov.submits
        with _patched(providers_mod(), "discover", lambda *a, **k: _Down(prov)):
            r = vis.resume_pending(p, out)
        assert prov.submits == before, "平台不可用时恢复路径居然提交了"
        assert r["resumed"] == 0 and "不可用" in r["note"]


def providers_mod():
    import omniarchitect.providers as providers

    return providers
