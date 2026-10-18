"""参考图必须真的进请求 —— 不是路径存在就算通。

这一组用**假契约**把请求体截下来看：参考图有没有落在契约声明的字段里、
字节是否一致、格式是否被接受、本地路径有没有被误发出去。

平台真实契约不在本机，所以这是 Mock 验证；但验证的是"映射正确"这件事，
不是"看起来像提交了"。

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import base64
import hashlib
import json
import tempfile
from pathlib import Path
from typing import Any, Dict, List

from omniarchitect.providers.base import ProviderCapability, ProviderError
from omniarchitect.providers.omniailab import OmniAiLabProvider

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 4096
SVG = b'<?xml version="1.0"?><svg xmlns="http://www.w3.org/2000/svg"><rect/></svg>'


def _contract(mode: str = "base64", **refs: Any) -> Dict[str, Any]:
    spec = {"mode": mode, "field": "reference_images",
            "accepted_formats": ["png"], "max_bytes": 5_000_000}
    spec.update(refs)
    return {
        "schema": "omniailab.api/1",
        "base_url": "https://api.example.invalid",
        "auth": "bearer",
        "endpoints": {"submit": "/jobs", "poll": "/jobs/status", "upload": "/assets"},
        "models": ["stub-model"],
        "capabilities": ["reference_image_generation"],
        "references": spec,
        "pricing": {"reference_image_generation": {"per_unit": 1.0, "default_units": 1}},
    }


def _provider(contract: Dict[str, Any], captured: Dict[str, Any]) -> OmniAiLabProvider:
    prov = OmniAiLabProvider()
    prov.probe = lambda: ProviderCapability(          # type: ignore[method-assign]
        provider="omniailab", state="connected", provider_kind="native-platform",
        scopes=["reference_image_generation"], models=["stub-model"])
    prov.load_contract = lambda: contract              # type: ignore[method-assign]
    prov.load_config = lambda root=None: {"api_key": "k"}  # type: ignore[method-assign]

    def _post(endpoint, body, c, k, cfg, method="POST", extra_headers=None):
        captured["endpoint"] = endpoint
        captured["body"] = body
        captured["headers"] = extra_headers or {}
        return {"job_id": "job-1", "status": "queued"}

    def _post_multipart(endpoint, fields, files, c, k, cfg, method="POST",
                        extra_headers=None, json_fields=None):
        captured["endpoint"] = endpoint
        captured["fields"] = fields
        captured["files"] = [(n, len(raw), mime) for n, raw, mime in files]
        captured["json_fields"] = json_fields or {}
        return {"job_id": "job-2", "status": "queued"}

    prov._post = _post                                # type: ignore[method-assign]
    prov._post_multipart = _post_multipart            # type: ignore[method-assign]
    return prov


def _params(refs: List[str]) -> Dict[str, Any]:
    return {"prompt": "x", "negative_prompt": "y", "units": 1,
            "references": refs, "revision": 3, "stage": "S3",
            "target": "plan-color", "workflow": "drawing",
            "plan_confirmed": True, "scope": "reference_image_generation"}


# --------------------------------------------------------------------------
def test_base64_mode_puts_the_real_bytes_into_the_declared_field():
    with tempfile.TemporaryDirectory() as td:
        ref = Path(td) / "reference-plan-A.png"
        ref.write_bytes(PNG)
        captured: Dict[str, Any] = {}
        prov = _provider(_contract(), captured)
        prov.submit("reference_image_generation", _params([str(ref)]))

        body = captured["body"]
        assert body["reference_images"], "参考图没进请求"
        item = body["reference_images"][0]
        assert base64.b64decode(item["data"]) == PNG, "发出去的不是同一份字节"
        assert item["mime"] == "image/png"

        meta = body["params"]["reference_meta"][0]
        assert meta["sha256"] == hashlib.sha256(PNG).hexdigest()
        assert meta["bytes"] == len(PNG)
        # 本地路径不得发出去
        blob = json.dumps(body, ensure_ascii=False)
        assert str(ref) not in blob, "本地路径被发给了平台"
        # 阶段/目标/修订号必须随请求
        assert body["params"]["stage"] == "S3"
        assert body["params"]["target"] == "plan-color"
        assert body["params"]["revision"] == 3
        assert body["params"]["plan_confirmed"] is True


def test_unknown_transport_mode_is_refused_not_guessed():
    with tempfile.TemporaryDirectory() as td:
        ref = Path(td) / "p.png"
        ref.write_bytes(PNG)
        contract = _contract()
        contract["references"] = {"field": "reference_images",
                                 "accepted_formats": ["png"]}      # 没写 mode
        captured: Dict[str, Any] = {}
        try:
            _provider(contract, captured).submit(
                "reference_image_generation", _params([str(ref)]))
        except ProviderError as exc:
            assert "references.mode" in str(exc)
        else:
            raise AssertionError("没有传输方式却提交了")
        assert "body" not in captured, "被拒的请求不该发出去"


def test_svg_is_not_assumed_supported():
    with tempfile.TemporaryDirectory() as td:
        ref = Path(td) / "plan.svg"
        ref.write_text(SVG.decode("utf-8"), encoding="utf-8")
        captured: Dict[str, Any] = {}
        try:
            _provider(_contract(), captured).submit(
                "reference_image_generation", _params([str(ref)]))
        except ProviderError as exc:
            assert "契约只接受" in str(exc)
        else:
            raise AssertionError("契约只接受 png，却把 svg 提交了")


def test_missing_accepted_formats_is_refused():
    with tempfile.TemporaryDirectory() as td:
        ref = Path(td) / "p.png"
        ref.write_bytes(PNG)
        contract = _contract()
        contract["references"] = {"mode": "base64", "field": "reference_images"}
        try:
            _provider(contract, {}).submit("reference_image_generation",
                                           _params([str(ref)]))
        except ProviderError as exc:
            assert "accepted_formats" in str(exc)
        else:
            raise AssertionError("未声明可接收格式时不该猜")


def test_truncated_png_is_caught_before_upload():
    with tempfile.TemporaryDirectory() as td:
        bad = Path(td) / "broken.png"
        bad.write_bytes(b"not a png at all" * 100)
        try:
            _provider(_contract(), {}).submit("reference_image_generation",
                                              _params([str(bad)]))
        except ProviderError as exc:
            assert "不是 PNG" in str(exc)
        else:
            raise AssertionError("坏文件被当成参考图提交了")


def test_multipart_mode_sends_files_as_bodies():
    with tempfile.TemporaryDirectory() as td:
        ref = Path(td) / "p.png"
        ref.write_bytes(PNG)
        captured: Dict[str, Any] = {}
        prov = _provider(_contract(mode="multipart"), captured)
        prov.submit("reference_image_generation", _params([str(ref)]))
        assert captured["files"], "multipart 没有带文件"
        name, size, mime = captured["files"][0]
        assert name == "p.png" and size == len(PNG) and mime == "image/png"
        assert "params" in captured["json_fields"]


def test_visual_params_carry_stage_target_scope_and_references():
    """drawing-visuals 的任务经 _params 后，阶段/目标/能力域/参考图都在。"""
    from omniarchitect.concept.visual import _params as build_params
    from omniarchitect.demo import build_demo_project

    with tempfile.TemporaryDirectory() as td:
        p = build_demo_project(Path(td) / "proj")
        job = {
            "job_id": "C-B-plan-color", "target": "plan-color",
            "scope": "reference_image_generation", "family": "drawing",
            "stage": "S3", "workflow": "drawing",
            "references": ["/tmp/reference-plan-A.png"],
            "style_ids": ["italian-minimal"], "consistency_key": "sp-x",
            "label": "平面图上色", "text_overlay": [],
            "prompt": {"positive": {"zh": "p"}, "negative": {"zh": "n"},
                       "gate": {"plan_confirmed": True}},
        }
        params = build_params(job, p)
        assert params["stage"] == "S3" and params["workflow"] == "drawing"
        assert params["target"] == "plan-color"
        assert params["scope"] == "reference_image_generation"
        assert params["references"] == ["/tmp/reference-plan-A.png"]
        assert params["plan_confirmed"] is True
        assert params["revision"] == p.revision
        assert params["units"] == 1
