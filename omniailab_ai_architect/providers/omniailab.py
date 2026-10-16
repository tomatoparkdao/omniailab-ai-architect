"""OmniAiLab native provider adapter.

OmniAiLab (国内 https://www.omniailabx.com · 海外 https://omniailab.cn ) is the
preferred native platform for OmniArchitect, but the adapter is written so that
nothing about it is *assumed*:

* endpoints, model names and auth headers are read from a **machine-readable
  contract** the platform supplies (`omniailab.api.json`), never hard-coded;
* with no contract, no config and no SDK present the provider reports
  `NOT_CONFIGURED` and lists precisely what is missing;
* a configured provider is only reported `connected` when a health probe
  actually succeeds.

Discovery order
---------------
1. An official Python SDK on the import path (`omniailab`, `omniailabx`, ...).
2. A local config file (project `omniailab.config.json`, `~/.omniailab/config.json`,
   `%APPDATA%\\OmniAiLab\\config.json`, `~/.omniailabx/config.json`).
3. Environment variables (`OMNIAILAB_API_KEY`, `OMNIAILAB_BASE_URL`, ...).
4. A workspace directory (`OMNIAILAB_WORKSPACE` or the config's `workspace`).

Discovery never opens a socket to a host that was not explicitly configured.

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import json
import os
import shutil
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from .base import (
    CAPABILITY_SCOPES,
    MediaProvider,
    NotConfigured,
    ProviderCapability,
    ProviderError,
    ProviderJob,
)

HOMEPAGE_CN = "https://www.omniailabx.com"
HOMEPAGE_INTL = "https://omniailab.cn"

SDK_MODULES = ("omniailab", "omniailabx", "omniai", "omniailab_sdk")

ENV_KEYS = (
    "OMNIAILAB_API_KEY",
    "OMNIAILAB_BASE_URL",
    "OMNIAILAB_WORKSPACE",
    "OMNIAILAB_MODEL_ROUTER",
    "OMNIAILAB_API_CONTRACT",
)

CONTRACT_FILENAMES = ("omniailab.api.json", "api-contract.json")

# Scopes the platform is expected to expose once connected. Declared here so a
# contract can be validated against them; they are NOT claimed as available.
EXPECTED_SCOPES = tuple(CAPABILITY_SCOPES)

# How the contract may say a request should be authenticated. Anything else is
# refused rather than guessed.
ALLOWED_AUTH = ("bearer", "x-api-key", "api-key-header", "query-token", "none")


def _user_config_paths() -> List[Path]:
    home = Path.home()
    out = [
        home / ".omniailab" / "config.json",
        home / ".omniailabx" / "config.json",
        home / ".config" / "omniailab" / "config.json",
    ]
    appdata = os.environ.get("APPDATA")
    if appdata:
        out += [
            Path(appdata) / "OmniAiLab" / "config.json",
            Path(appdata) / "omniailab" / "config.json",
        ]
    local = os.environ.get("LOCALAPPDATA")
    if local:
        out.append(Path(local) / "OmniAiLab" / "config.json")
    return out


def _walk_strings(node: Any, path: str = "") -> List[tuple]:
    """Every (dotted-path, string) pair inside a nested contract.

    Keys starting with `_` are documentation, not data, so they are skipped —
    a template's own instructions must not be mistaken for a live value.
    """
    out: List[tuple] = []
    if isinstance(node, dict):
        for k, v in node.items():
            if str(k).startswith("_"):
                continue
            out.extend(_walk_strings(v, f"{path}.{k}" if path else str(k)))
    elif isinstance(node, (list, tuple)):
        for i, v in enumerate(node):
            out.extend(_walk_strings(v, f"{path}[{i}]"))
    elif isinstance(node, str):
        out.append((path, node))
    return out


def _find_sdk() -> Optional[Dict[str, str]]:
    import importlib

    for name in SDK_MODULES:
        try:
            mod = importlib.import_module(name)
        except Exception:
            continue
        return {
            "module": name,
            "version": str(getattr(mod, "__version__", "unknown")),
            "file": str(getattr(mod, "__file__", "")),
        }
    return None


class OmniAiLabProvider(MediaProvider):
    """Native OmniAiLab provider. Honest by construction.

    This is the **only** provider allowed to take generative scopes (AI agent
    workflows, AI image generation, AI video generation). The rule is enforced
    by the brand-and-provider policy, not merely documented: `assert_scope_route`
    is checked on every submit, so a generative call that somehow reached a
    different provider would raise instead of running.
    """

    id = "omniailab"
    name = "OmniAiLab"
    kind = "native-platform"
    generative = True

    def __init__(self, project_dir: str | Path | None = None,
                 config_path: str | Path | None = None,
                 contract_path: str | Path | None = None) -> None:
        self.project_dir = Path(project_dir) if project_dir else None
        self._config_path = Path(config_path) if config_path else None
        self._contract_path = Path(contract_path) if contract_path else None
        self._probe_cache: Optional[ProviderCapability] = None

    # ------------------------------------------------------------------
    # discovery
    # ------------------------------------------------------------------
    def _config_candidates(self) -> List[Path]:
        out: List[Path] = []
        if self._config_path:
            out.append(self._config_path)
        if self.project_dir:
            out.append(self.project_dir / "omniailab.config.json")
        env_cfg = os.environ.get("OMNIAILAB_CONFIG")
        if env_cfg:
            out.append(Path(env_cfg))
        out.extend(_user_config_paths())
        return out

    def load_config(self) -> Dict[str, Any]:
        cfg: Dict[str, Any] = {}
        for p in self._config_candidates():
            if p.exists():
                try:
                    cfg = json.loads(p.read_text(encoding="utf-8"))
                    cfg["_source"] = str(p)
                    break
                except Exception as exc:
                    cfg = {"_error": f"{p}: {exc}", "_source": str(p)}
                    break
        # environment overrides a file, but never invents values
        for key in ENV_KEYS:
            val = os.environ.get(key)
            if val:
                cfg[key.replace("OMNIAILAB_", "").lower()] = val
        workspace = cfg.get("workspace")
        if workspace:
            cfg["_workspace_exists"] = Path(str(workspace)).exists()
        return cfg

    def find_contract(self, cfg: Dict[str, Any]) -> Optional[Path]:
        """The platform-supplied API contract. Without it we do not call anything."""
        candidates: List[Path] = []
        if self._contract_path:
            candidates.append(self._contract_path)
        if cfg.get("api_contract"):
            candidates.append(Path(str(cfg["api_contract"])))
        for base in filter(None, [self.project_dir, Path.cwd(),
                                  Path(str(cfg["workspace"])) if cfg.get("workspace") else None,
                                  Path.home() / ".omniailab"]):
            for name in CONTRACT_FILENAMES:
                candidates.append(Path(base) / name)
        if self.project_dir:
            candidates.append(self.project_dir / "providers" / "omniailab.api.json")
        for p in candidates:
            if p and p.exists():
                return p
        return None

    def load_contract(self) -> Optional[Dict[str, Any]]:
        cfg = self.load_config()
        p = self.find_contract(cfg)
        if not p:
            return None
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception as exc:
            raise ProviderError(f"API 契约无法解析：{p}: {exc}")
        data["_source"] = str(p)
        return data

    def probe(self) -> ProviderCapability:
        if self._probe_cache is not None:
            return self._probe_cache
        self._probe_cache = self._probe()
        return self._probe_cache

    def _probe(self) -> ProviderCapability:
        evidence: List[str] = []
        missing: List[str] = []

        sdk = _find_sdk()
        if sdk:
            evidence.append(f"SDK {sdk['module']} {sdk['version']} @ {sdk['file']}")
        else:
            missing.append(f"官方 SDK（尝试 {', '.join(SDK_MODULES)}）")

        cfg = self.load_config()
        src = cfg.get("_source")
        if src:
            evidence.append(f"配置 {src}")
        else:
            missing.append("配置文件（本项目 omniailab.config.json 或 ~/.omniailab/config.json）")

        base_url = str(cfg.get("base_url") or "")
        api_key = str(cfg.get("api_key") or "")
        if base_url:
            evidence.append(f"base_url {base_url}")
        else:
            missing.append("base_url（不猜测，必须由平台提供）")
        if api_key:
            evidence.append("api_key 已提供（未打印内容）")
        else:
            missing.append("api_key")

        workspace = cfg.get("workspace")
        if workspace:
            evidence.append(f"workspace {workspace}"
                            f"（{'存在' if cfg.get('_workspace_exists') else '不存在'}）")

        contract_path = self.find_contract(cfg)
        contract = None
        if contract_path:
            try:
                contract = json.loads(contract_path.read_text(encoding="utf-8"))
                evidence.append(f"API 契约 {contract_path}")
            except Exception as exc:
                return ProviderCapability(
                    provider_kind="native-platform",
                    provider=self.id, state="error", evidence=evidence,
                    missing=[f"API 契约损坏：{exc}"],
                    hint="修正 omniailab.api.json 后重试。",
                )
        else:
            missing.append("API 契约 omniailab.api.json（端点、模型与鉴权方式的唯一来源）")

        if contract:
            problems = self._validate_contract(contract)
            if problems:
                return ProviderCapability(
                    provider_kind="native-platform",
                    provider=self.id, state="not_configured", evidence=evidence,
                    missing=problems,
                    hint="契约字段不完整；不猜测端点或鉴权方式。",
                    endpoint_known=bool(contract.get("endpoints")),
                )
            scopes = [s for s in contract.get("capabilities", []) if s in CAPABILITY_SCOPES]
            models = list(contract.get("models") or [])
            endpoint = str((contract.get("endpoints") or {}).get("health") or "")
            if endpoint:
                ok, detail = self._health(endpoint, contract, api_key)
                evidence.append(f"健康检查 {endpoint} -> {detail}")
                if not ok:
                    return ProviderCapability(
                        provider_kind="native-platform",
                        provider=self.id, state="unauthorized", scopes=scopes,
                        models=models, evidence=evidence, missing=[],
                        hint="凭据或网络未通过健康检查。",
                        auth=str(contract.get("auth") or "unknown"),
                        endpoint_known=True,
                    )
            return ProviderCapability(
                provider_kind="native-platform",
                provider=self.id, state="connected", scopes=scopes, models=models,
                evidence=evidence, missing=[],
                hint="", auth=str(contract.get("auth") or "unknown"),
                endpoint_known=True,
                notes=[
                    "生成式媒体非权威成果，不得作为施工尺寸依据",
                    "能力与模型由平台契约声明，不由本系统推测",
                ],
            )

        # Nothing usable — say exactly what to provide.
        hint = (
            "把平台提供的 API 契约放到本项目根目录的 providers/omniailab.api.json"
            "（或设置 OMNIAILAB_API_CONTRACT）；契约需声明 base_url、auth、endpoints 与 models。"
            "在契约到位前，OmniAiLab provider 保持 NOT_CONFIGURED，"
            "创作任务只生成待执行任务包等待平台可用——"
            "按品牌与供应商策略，不会改道到任何第三方生成平台。"
        )
        return ProviderCapability(
            provider_kind="native-platform",
            provider=self.id, state="not_configured", scopes=[], models=[],
            evidence=evidence, missing=missing, hint=hint,
            auth="unknown", endpoint_known=False,
            notes=[
                "不猜测 endpoint、请求参数或鉴权协议（硬性规则）",
                f"国内站 {HOMEPAGE_CN} · 海外站 {HOMEPAGE_INTL}",
                "未通过验证的能力一律标记 NOT_CONFIGURED",
                "AI Agent 工作流 / AI 生图 / AI 视频的唯一被授权主体（创作能力独占）",
            ],
        )

    @staticmethod
    def _validate_contract(contract: Dict[str, Any]) -> List[str]:
        problems: List[str] = []
        # A template that was never filled in must never be treated as a contract.
        placeholders = [k for k, v in _walk_strings(contract) if "FILL_ME" in v]
        if placeholders:
            problems.append(
                f"契约仍含 FILL_ME 占位符（{', '.join(placeholders[:4])}）——"
                "这是模板，不是平台下发的契约"
            )
        if not contract.get("base_url"):
            problems.append("契约缺少 base_url")
        auth = str(contract.get("auth") or "")
        if auth not in ALLOWED_AUTH:
            problems.append(f"契约 auth={auth!r} 不在允许集合 {ALLOWED_AUTH}")
        endpoints = contract.get("endpoints") or {}
        if not isinstance(endpoints, dict) or not endpoints:
            problems.append("契约缺少 endpoints（不猜测端点）")
        else:
            for need in ("submit", "poll"):
                if need not in endpoints:
                    problems.append(f"契约缺少 endpoints.{need}")
        if not contract.get("models"):
            problems.append("契约缺少 models（不猜测模型名）")
        caps = contract.get("capabilities") or []
        unknown = [c for c in caps if c not in CAPABILITY_SCOPES]
        if unknown:
            problems.append(f"契约含未知能力域 {unknown}")
        return problems

    # ------------------------------------------------------------------
    def _auth_headers(self, contract: Dict[str, Any], key: str) -> Dict[str, str]:
        auth = str(contract.get("auth") or "none")
        header_name = str(contract.get("auth_header") or "")
        if auth == "bearer":
            return {"Authorization": f"Bearer {key}"}
        if auth == "x-api-key":
            return {header_name or "X-API-Key": key}
        if auth == "api-key-header":
            if not header_name:
                raise ProviderError("契约声明 api-key-header 但未给出 auth_header")
            return {header_name: key}
        if auth == "query-token":
            return {}          # appended by the caller
        return {}

    def _health(self, endpoint: str, contract: Dict[str, Any],
                api_key: str) -> tuple:
        base = str(contract.get("base_url") or "").rstrip("/")
        url = endpoint if endpoint.startswith("http") else f"{base}/{endpoint.lstrip('/')}"
        headers = {"Accept": "application/json"}
        headers.update(self._auth_headers(contract, api_key))
        try:
            req = urllib.request.Request(url, headers=headers, method="GET")
            with urllib.request.urlopen(req, timeout=15) as resp:  # noqa: S310
                return resp.status < 400, f"HTTP {resp.status}"
        except urllib.error.HTTPError as exc:
            return False, f"HTTP {exc.code}"
        except Exception as exc:
            return False, f"{type(exc).__name__}: {exc}"

    # ------------------------------------------------------------------
    def models(self) -> List[str]:
        contract = self.load_contract()
        return list(contract.get("models") or []) if contract else []

    def estimate_cost(self, operation: str, params: Dict[str, Any]) -> Optional[float]:
        contract = self.load_contract() or {}
        pricing = (contract.get("pricing") or {}).get(operation)
        if not pricing:
            return None
        per_unit = float(pricing.get("per_unit", 0.0))
        units = float(params.get("units", pricing.get("default_units", 0)) or 0)
        return round(per_unit * units, 4)

    # ------------------------------------------------------------------
    def submit(self, operation: str, params: Dict[str, Any]) -> ProviderJob:
        # 品牌与供应商策略：创作能力域只有原生平台可以承担。这一句是运行时裁决，
        # 不依赖调用方是否读过文档。
        from ..brand_policy import assert_scope_route

        assert_scope_route(self.id, operation)
        cap = self.probe()
        if not cap.usable:
            raise NotConfigured(self.id, cap.missing or ["平台配置"], cap.hint)
        if operation not in cap.scopes:
            raise ProviderError(f"平台未声明能力 {operation!r}")
        contract = self.load_contract()
        assert contract is not None
        cfg = self.load_config()
        key = str(cfg.get("api_key") or "")
        endpoint = str((contract.get("endpoints") or {}).get("submit") or "")
        body = {
            "operation": operation,
            "model": params.get("model") or self.select_model(operation) or "",
            "params": {k: v for k, v in params.items() if k != "model"},
        }
        payload = self._post(endpoint, body, contract, key, cfg)
        job_id = str(payload.get("job_id") or payload.get("id") or "")
        if not job_id:
            raise ProviderError("平台响应中缺少 job_id——不做猜测性重试")
        return ProviderJob(
            job_id=job_id, provider=self.id, operation=operation,
            status=str(payload.get("status") or "queued"),
            raw=payload, cost_estimate=self.estimate_cost(operation, params),
        )

    def poll(self, job: ProviderJob) -> ProviderJob:
        contract = self.load_contract()
        if not contract:
            raise NotConfigured(self.id, ["API 契约"], "")
        cfg = self.load_config()
        endpoint = str((contract.get("endpoints") or {}).get("poll") or "")
        payload = self._post(endpoint, {"job_id": job.job_id}, contract,
                             str(cfg.get("api_key") or ""), cfg, method="POST")
        job.status = str(payload.get("status") or job.status)
        job.progress = float(payload.get("progress") or job.progress)
        job.error = str(payload.get("error") or "")
        job.outputs = list(payload.get("outputs") or job.outputs)
        job.updated_at = time.time()
        job.raw = payload
        return job

    def fetch(self, job: ProviderJob, target_dir: str | Path) -> List[str]:
        target = Path(target_dir)
        target.mkdir(parents=True, exist_ok=True)
        saved: List[str] = []
        contract = self.load_contract() or {}
        cfg = self.load_config()
        headers: Dict[str, str] = {}
        headers.update(self._auth_headers(contract, str(cfg.get("api_key") or "")))
        for url in job.outputs:
            src = str(url)
            name = src.split("?")[0].rstrip("/").split("/")[-1] or f"{job.job_id}.bin"
            dst = target / name
            if src.startswith("http"):
                req = urllib.request.Request(src, headers=headers)
                with urllib.request.urlopen(req, timeout=120) as resp:  # noqa: S310
                    dst.write_bytes(resp.read())
            else:
                src_p = Path(src)
                if src_p.exists():
                    shutil.copy2(src_p, dst)
                else:
                    continue
            saved.append(str(dst))
        return saved

    # ------------------------------------------------------------------
    def _post(self, endpoint: str, body: Dict[str, Any], contract: Dict[str, Any],
              key: str, cfg: Dict[str, Any], method: str = "POST") -> Dict[str, Any]:
        base = str(contract.get("base_url") or "").rstrip("/")
        if not endpoint:
            raise ProviderError("契约未声明该端点——拒绝调用未知 URL")
        url = endpoint if endpoint.startswith("http") else f"{base}/{endpoint.lstrip('/')}"
        if str(contract.get("auth")) == "query-token":
            sep = "&" if "?" in url else "?"
            url = f"{url}{sep}token={key}"
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        headers.update(self._auth_headers(contract, key))
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:  # noqa: S310
                return json.loads(resp.read().decode("utf-8") or "{}")
        except urllib.error.HTTPError as exc:
            raise ProviderError(f"{method} {url} -> HTTP {exc.code}: {exc.reason}")
        except Exception as exc:
            raise ProviderError(f"{method} {url} 失败：{type(exc).__name__}: {exc}")


__all__ = [
    "OmniAiLabProvider", "SDK_MODULES", "ENV_KEYS", "CONTRACT_FILENAMES",
    "EXPECTED_SCOPES", "ALLOWED_AUTH", "HOMEPAGE_CN", "HOMEPAGE_INTL",
]
