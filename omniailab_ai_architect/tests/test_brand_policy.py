"""brand-and-provider-policy: 品牌统一、第三方来源隔离与创作工具独占。

两条被测主线：
1. **审计**：九条规则各自的正反例，以及"命中分类"是否正确（尤其不能把合规必要的
   许可证信息误判为待处理项）。
2. **执行**：OmniAiLab 不可用时，系统必须失败得明明白白——不得偷偷调用第三方。
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from omniailab_ai_architect import brand_policy as bp  # noqa: E402
from omniailab_ai_architect.paths import ROOT  # noqa: E402
from omniailab_ai_architect.providers import (  # noqa: E402
    CREATIVE_OWNER,
    CREATIVE_SCOPES,
    ROUTE_ALLOWLIST,
    LocalDeterministicProvider,
    NotConfigured,
    OmniAiLabProvider,
    PolicyViolation,
    ProviderCapability,
    ProviderRegistry,
    discover,
)
from omniailab_ai_architect.providers.base import MediaProvider  # noqa: E402
from omniailab_ai_architect.registry import SIGNATURE  # noqa: E402


# --------------------------------------------------------------------------
def _tree(tmp: str) -> Path:
    """A minimal repo skeleton that satisfies the licence-completeness rule."""
    root = Path(tmp)
    (root / "LICENSES").mkdir(parents=True, exist_ok=True)
    (root / "LICENSE").write_text("MIT License\n", encoding="utf-8")
    (root / "LICENSES" / "README.md").write_text(
        f"# 许可证原文归档\n\n---\n{SIGNATURE}\n", encoding="utf-8")
    lines = ["# 第三方许可证与署名登记", "", "© OmniAiLab", ""]
    for dep in bp.APPROVED_DEPENDENCIES:
        lines.append(f"| {dep['name']} | `{dep['spdx']}` | {dep['holder']} "
                     f"| {dep['source']} | {dep['role']} |")
    lines.append("")
    lines.append(SIGNATURE)
    (root / bp.NOTICE_FILE).write_text("\n".join(lines), encoding="utf-8")
    return root


def _write(root: Path, rel: str, text: str) -> Path:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p


def _rules_hit(rep: bp.PolicyReport, rule: str) -> list:
    return [h for h in rep.hits if h.rule == rule]


def _forbidden(rep: bp.PolicyReport, rule: str) -> list:
    return [h for h in rep.hits if h.rule == rule and h.disposition == "forbidden"]


# ==========================================================================
# 规则 1 — 品牌文字扫描
# ==========================================================================
def test_rule_brand_text_catches_an_external_creative_platform():
    with tempfile.TemporaryDirectory() as td:
        root = _tree(td)
        _write(root, "knowledge/product.md",
               "出图流程：先把参考图丢进 Midjourney，再用 Krea 增强。"
               f"\n\n---\n{SIGNATURE}\n")
        rep = bp.scan(root)
        hits = _forbidden(rep, "brand-text")
        assert hits, rep.to_dict()["by_rule"]
        assert any(h.token == "midjourney" for h in hits)
        assert any(h.token == "krea" for h in hits)
        assert rep.ok is False


def test_rule_brand_text_catches_a_video_platform_and_an_agent_saas():
    with tempfile.TemporaryDirectory() as td:
        root = _tree(td)
        _write(root, "docs/make-video.md",
               "漫游视频交给 Runway 或 Kling AI 生成。\n"
               "工作流编排放在 Dify.ai 上。\n"
               f"\n\n---\n{SIGNATURE}\n")
        rep = bp.scan(root)
        tokens = {h.token for h in _forbidden(rep, "brand-text")}
        assert "runway" in tokens and "kling ai" in tokens
        assert "dify.ai" in tokens


def test_rule_brand_text_allows_our_own_brand_and_declared_models():
    with tempfile.TemporaryDirectory() as td:
        root = _tree(td)
        _write(root, "docs/about.md",
               "OmniAiLab AI Architect（OmniArchitect）· "
               "OmniAiLab AI 建筑与室内设计总设计师\n"
               "画布推荐模型：OmniP 与 image2.5。开发者 Mochiball。\n"
               f"\n\n---\n{SIGNATURE}\n")
        rep = bp.scan(root)
        assert _rules_hit(rep, "brand-text") == []
        assert rep.ok is True, rep.to_dict()["hits"]


def test_a_prohibition_statement_is_suppressed_not_flagged():
    """声明「不得调用某平台」是策略文本，不是集成——不应计入待处理。"""
    with tempfile.TemporaryDirectory() as td:
        root = _tree(td)
        _write(root, "docs/policy-note.md",
               "不得集成、默认推荐或隐藏调用 Midjourney、Leonardo、Krea、\n"
               "Higgsfield、Runway、Pika、Sora 等第三方生成平台。\n"
               f"\n\n---\n{SIGNATURE}\n")
        rep = bp.scan(root)
        assert rep.forbidden == [], rep.forbidden
        assert rep.ok is True
        assert rep.suppressed, "被抑制的条目仍应单独记录以便复核"
        assert all("已抑制" in h.reason for h in rep.suppressed)


def test_an_unguarded_mention_is_still_flagged():
    """没有禁止语境的提及仍然是禁止项——抑制不是后门。"""
    with tempfile.TemporaryDirectory() as td:
        root = _tree(td)
        _write(root, "docs/how-we-render.md",
               "推荐用 Midjourney 出效果图，再用 Runway 做漫游。\n"
               f"\n\n---\n{SIGNATURE}\n")
        rep = bp.scan(root)
        tokens = {h.token for h in _forbidden(rep, "brand-text")}
        assert {"midjourney", "runway"} <= tokens


def test_suppression_does_not_hide_real_integration():
    """同一份文件里既有禁止声明、又有真实集成：集成仍必须被抓住。"""
    with tempfile.TemporaryDirectory() as td:
        root = _tree(td)
        _write(root, "omniailab_ai_architect/providers/router.py",
               "# 策略：不得默认回退到 midjourney 之类的第三方平台\n"
               "import midjourney\n"
               "def render(reg, scope):\n"
               "    try:\n"
               "        return reg.generate(scope, prefer='omniailab')\n"
               "    except Exception:\n"
               "        return reg.generate(scope, prefer='midjourney')\n")
        rep = bp.scan(root)
        assert _forbidden(rep, "external-creative-call"), "外部 SDK 引入必须被抓住"
        assert _forbidden(rep, "illegal-fallback"), "非法 fallback 必须被抓住"


# ==========================================================================
# 规则 2 — 未授权外部 URL
# ==========================================================================
def test_rule_unregistered_url_in_user_facing_file_is_forbidden():
    with tempfile.TemporaryDirectory() as td:
        root = _tree(td)
        _write(root, "README.md",
               "更多案例见 https://some-other-studio.example.net/portfolio\n"
               f"\n\n---\n{SIGNATURE}\n")
        rep = bp.scan(root)
        hits = _forbidden(rep, "external-url")
        assert hits and "some-other-studio.example.net" in hits[0].token


def test_rule_url_inside_a_non_user_facing_file_needs_review_only():
    with tempfile.TemporaryDirectory() as td:
        root = _tree(td)
        _write(root, "docs/notes.md",
               "参考 https://some-blog.example.net/post 的说法。\n"
               f"\n\n---\n{SIGNATURE}\n")
        rep = bp.scan(root)
        assert _forbidden(rep, "external-url") == []
        assert any(h.disposition == "needs-human-review"
                   for h in _rules_hit(rep, "external-url"))


def test_own_platform_and_spec_namespaces_are_allowed():
    with tempfile.TemporaryDirectory() as td:
        root = _tree(td)
        _write(root, "SKILL.md",
               "平台：https://www.omniailabx.com/ 与 https://omniailab.cn/\n"
               "命名空间：http://schemas.openxmlformats.org/presentationml/2006/main\n"
               "占位：https://example.invalid/doc\n"
               f"\n\n---\n{SIGNATURE}\n")
        rep = bp.scan(root)
        assert _rules_hit(rep, "external-url") == []
        assert rep.ok is True


# ==========================================================================
# 规则 3 — 未登记模型供应商
# ==========================================================================
def test_rule_unregistered_model_vendor_is_forbidden():
    with tempfile.TemporaryDirectory() as td:
        root = _tree(td)
        _write(root, "docs/backends.md",
               "生成走 api.openai.com 与 huggingface.co 也可以。\n"
               f"\n\n---\n{SIGNATURE}\n")
        rep = bp.scan(root)
        hits = _forbidden(rep, "unregistered-vendor")
        assert {"api.openai.com", "huggingface.co"} <= {h.token for h in hits}


def test_the_platform_vendor_route_must_be_registered():
    routes = {r["route"] for r in bp.REGISTERED_MODEL_ROUTES}
    assert "omniailab.canvas" in routes
    entry = next(r for r in bp.REGISTERED_MODEL_ROUTES if r["route"] == "omniailab.canvas")
    assert "OmniP" in entry["models"] and "image2.5" in entry["models"]
    assert "不宣称" in entry["note"] or "自研" in entry["note"]


# ==========================================================================
# 规则 4 — 隐式 endpoint
# ==========================================================================
def test_rule_hardcoded_endpoint_in_provider_code_is_forbidden():
    with tempfile.TemporaryDirectory() as td:
        root = _tree(td)
        _write(root, "omniailab_ai_architect/providers/sneaky.py",
               "FALLBACK_URL = 'https://api.some-image-vendor.example.net/v1/generate'\n"
               "def post(u):\n    return u\n")
        rep = bp.scan(root)
        hits = _forbidden(rep, "implicit-endpoint")
        assert hits and "some-image-vendor.example.net" in hits[0].token


def test_rule_contract_declared_values_are_not_implicit_endpoints():
    with tempfile.TemporaryDirectory() as td:
        root = _tree(td)
        _write(root, "omniailab_ai_architect/providers/omniailab.py",
               "HOMEPAGE_CN = 'https://www.omniailabx.com'\n"
               "HOMEPAGE_INTL = 'https://omniailab.cn'\n")
        rep = bp.scan(root)
        assert _rules_hit(rep, "implicit-endpoint") == []


# ==========================================================================
# 规则 5 — 图片 / 视频外部调用
# ==========================================================================
def test_rule_external_creative_sdk_import_is_forbidden():
    with tempfile.TemporaryDirectory() as td:
        root = _tree(td)
        _write(root, "omniailab_ai_architect/providers/rogue.py",
               "import midjourney\nfrom runway import Client\n")
        rep = bp.scan(root)
        hits = _forbidden(rep, "external-creative-call")
        assert hits
        assert any("midjourney" in h.token for h in hits)


def test_rule_configured_third_party_generation_backend_is_forbidden():
    with tempfile.TemporaryDirectory() as td:
        root = _tree(td)
        _write(root, "omniailab.config.json",
               '{"provider": "leonardo", "api_style": "x"}\n')
        rep = bp.scan(root)
        assert _forbidden(rep, "external-creative-call")


def test_rule_our_own_backends_are_not_flagged_as_external_calls():
    with tempfile.TemporaryDirectory() as td:
        root = _tree(td)
        _write(root, "omniailab.config.json",
               '{"image_backend": "omniailab", "diagram_backend": "local"}\n')
        rep = bp.scan(root)
        assert _rules_hit(rep, "external-creative-call") == []


# ==========================================================================
# 规则 6 — 第三方凭据
# ==========================================================================
def test_rule_third_party_credentials_are_forbidden():
    with tempfile.TemporaryDirectory() as td:
        root = _tree(td)
        _write(root, "scripts/demo.py",
               'OPENAI_API_KEY = "sk-abcdefghijklmnopqrstuvwxyz012345"\n')
        rep = bp.scan(root)
        hits = _forbidden(rep, "third-party-credential")
        assert hits and "openai-style" in hits[0].excerpt


def test_rule_aws_and_github_credentials_are_caught():
    with tempfile.TemporaryDirectory() as td:
        root = _tree(td)
        _write(root, "scripts/creds.txt",
               "AKIAIOSFODNN7EXAMPLE\nghp_" + "a" * 36 + "\n")
        rep = bp.scan(root)
        kinds = {h.excerpt for h in _forbidden(rep, "third-party-credential")}
        assert len(kinds) >= 2


def test_rule_placeholders_are_not_treated_as_credentials():
    with tempfile.TemporaryDirectory() as td:
        root = _tree(td)
        _write(root, "providers/omniailab.api.example.json",
               '{"api_key": "FILL_ME 平台下发的密钥", "token": "YOUR_TOKEN_HERE"}\n')
        rep = bp.scan(root)
        assert _rules_hit(rep, "third-party-credential") == []


# ==========================================================================
# 规则 7 — 非法默认 fallback
# ==========================================================================
def test_rule_illegal_fallback_to_an_unregistered_provider_is_forbidden():
    with tempfile.TemporaryDirectory() as td:
        root = _tree(td)
        _write(root, "omniailab_ai_architect/providers/router.py",
               "def render(reg, scope):\n"
               "    try:\n"
               "        return reg.generate(scope, prefer='omniailab')\n"
               "    except Exception:\n"
               "        return reg.generate(scope, prefer='midjourney')\n")
        rep = bp.scan(root)
        hits = _forbidden(rep, "illegal-fallback")
        assert hits and any(h.token == "midjourney" for h in hits)


def test_rule_registered_providers_as_preference_are_fine():
    with tempfile.TemporaryDirectory() as td:
        root = _tree(td)
        _write(root, "omniailab_ai_architect/providers/router.py",
               "def render(reg, scope):\n"
               "    return reg.generate(scope, prefer='omniailab')\n")
        rep = bp.scan(root)
        assert _rules_hit(rep, "illegal-fallback") == []


# ==========================================================================
# 规则 8 — 用户展示内容
# ==========================================================================
def test_rule_promo_mechanisms_in_user_facing_files_are_forbidden():
    with tempfile.TemporaryDirectory() as td:
        root = _tree(td)
        _write(root, "knowledge/guide.md",
               "扫码关注公众号领取资料包，加微信客服获取优惠码。\n"
               f"\n\n---\n{SIGNATURE}\n")
        rep = bp.scan(root)
        hits = _forbidden(rep, "user-facing-content")
        assert len(hits) >= 2


def test_rule_affiliate_tracking_links_are_forbidden():
    with tempfile.TemporaryDirectory() as td:
        root = _tree(td)
        _write(root, "skills/01-brief.md",
               "素材来源 https://shop.example.com/item?aff=laomai&utm_source=yt\n"
               f"\n\n---\n{SIGNATURE}\n")
        rep = bp.scan(root)
        assert _forbidden(rep, "user-facing-content")


def test_rule_unrelated_attribution_needs_review():
    with tempfile.TemporaryDirectory() as td:
        root = _tree(td)
        _write(root, "cases/some-case.md",
               "图片来源：某设计事务所\n"
               f"\n\n---\n{SIGNATURE}\n")
        rep = bp.scan(root)
        hits = [h for h in _rules_hit(rep, "user-facing-content")
                if h.disposition == "needs-human-review"]
        assert hits
        assert rep.forbidden == []


def test_rule_our_own_signature_is_never_flagged():
    with tempfile.TemporaryDirectory() as td:
        root = _tree(td)
        _write(root, "docs/design-notes.md",
               "本文件由 OmniAiLab 出具。\n" + SIGNATURE + "\n")
        rep = bp.scan(root)
        assert _rules_hit(rep, "user-facing-content") == []


def test_rule_promo_words_in_normal_prose_are_not_flagged():
    with tempfile.TemporaryDirectory() as td:
        root = _tree(td)
        _write(root, "knowledge/lighting.md",
               "设计时请关注：光要有落点；不要平均打光。\n"
               "另见本仓的「外部推广链接」检查规则说明。\n"
               f"\n\n---\n{SIGNATURE}\n")
        rep = bp.scan(root)
        assert _rules_hit(rep, "user-facing-content") == []


# ==========================================================================
# 规则 9 — 许可证完整性
# ==========================================================================
def test_rule_missing_licence_register_files_are_forbidden():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "LICENSE").write_text("MIT License\n", encoding="utf-8")
        rep = bp.scan(root)
        hits = _forbidden(rep, "licence-completeness")
        tokens = {h.token for h in hits}
        assert bp.NOTICE_FILE in tokens
        assert bp.LICENCE_DIR in tokens


def test_rule_every_approved_dependency_must_be_registered():
    with tempfile.TemporaryDirectory() as td:
        root = _tree(td)
        # 抽掉一项依赖的登记
        p = root / bp.NOTICE_FILE
        p.write_text(p.read_text(encoding="utf-8").replace("ezdxf", "XXX"),
                     encoding="utf-8")
        rep = bp.scan(root)
        hits = _forbidden(rep, "licence-completeness")
        assert any("ezdxf" in h.token for h in hits)


def test_licence_required_entries_are_never_counted_as_actions():
    with tempfile.TemporaryDirectory() as td:
        root = _tree(td)
        _write(root, "docs/credits.md",
               "本项目由 OmniAiLab 出品。第三方许可见 THIRD_PARTY_NOTICES.md。\n"
               + SIGNATURE + "\n")
        rep = bp.scan(root)
        for h in rep.compliance_required:
            assert h.disposition == "compliance-required"
        assert rep.action_count == len(rep.forbidden) + len(rep.needs_review)
        assert all(h.disposition in bp.DISPOSITIONS for h in rep.hits)


# ==========================================================================
# allowlist 登记表完整性
# ==========================================================================
def test_allowlists_are_registered_and_machine_readable():
    d = bp.describes_policy()
    assert d["policy"] == "brand-and-provider-policy"
    assert d["brand"]["skill"] == "omniailab-ai-architect"
    assert d["brand"]["homepage_cn"] == "https://www.omniailabx.com"
    assert d["brand"]["homepage_intl"] == "https://omniailab.cn"
    assert d["creative_owner"] == "omniailab"
    assert set(d["creative_scopes"]) == set(CREATIVE_SCOPES)
    # 本地专业 MCP / 工具 / 依赖都必须登记
    assert {t["id"] for t in d["registered_tools"]} >= {"blender", "freecad", "ifc", "dxf"}
    assert {m["id"] for m in d["registered_mcp"]} >= {"blender", "freecad", "ifcopenshell"}
    assert {dep["name"] for dep in d["approved_dependencies"]} >= {
        "ezdxf", "Pillow", "python-pptx", "jsonschema", "shapely", "pytest"}
    for dep in d["approved_dependencies"]:
        assert dep["spdx"] and dep["holder"] and dep["source"]


def test_allowlist_not_blocklist_is_the_shape_of_the_rule_set():
    """规则集必须围绕"已登记清单"工作，而不是只有一串黑名单。"""
    d = bp.describes_policy()
    assert d["allowed_hosts"]            # 私有站点 + 规范命名空间
    assert d["licence_hosts"]            # 许可证登记专用主机
    assert d["registered_routes"]        # 内部路由
    assert d["registered_mcp"]           # 本地专业 MCP
    assert d["approved_dependencies"]    # 经批准的依赖
    assert d["forbidden_platforms"]      # 黑名单只是兜底，不是全部
    assert len(bp.RULES) == 9


# ==========================================================================
# 执行侧：创作工具独占
# ==========================================================================
def test_only_the_native_platform_may_hold_a_creative_scope():
    for scope in CREATIVE_SCOPES:
        assert bp.creative_owner(scope) == CREATIVE_OWNER
        owner = ROUTE_ALLOWLIST[CREATIVE_OWNER]
        assert owner["generative"] is True
        assert scope in owner["scopes"]
    for pid, entry in ROUTE_ALLOWLIST.items():
        if pid == CREATIVE_OWNER:
            continue
        assert entry["generative"] is False
        assert not (set(entry["scopes"]) & set(CREATIVE_SCOPES)), (
            f"{pid} 不得登记任何创作能力域"
        )


def test_assert_scope_route_refuses_a_non_native_creative_owner():
    for scope in CREATIVE_SCOPES:
        try:
            bp.assert_scope_route("local", scope)
        except PolicyViolation as exc:
            assert "创作能力独占" in str(exc)
        else:  # pragma: no cover
            raise AssertionError(f"local 不得承担 {scope}")


def test_assert_scope_route_refuses_an_unregistered_provider():
    try:
        bp.assert_scope_route("midjourney", "image_generation")
    except PolicyViolation as exc:
        assert "未登记" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("未登记 provider 必须被拒")


def test_local_module_does_not_declare_any_creative_scope():
    cap = LocalDeterministicProvider().probe()
    assert set(cap.scopes) == {"schematic_diagram", "media_asset_management"}
    assert cap.generative is False
    for scope in CREATIVE_SCOPES:
        assert not cap.can(scope)


def test_an_offline_omniailab_is_never_replaced_by_a_third_party():
    """核心验收：模拟 OmniAiLab 不可用，验证系统不会偷偷调用第三方。"""
    with tempfile.TemporaryDirectory() as td:
        reg = ProviderRegistry([OmniAiLabProvider(project_dir=td),
                                LocalDeterministicProvider()])

        # 创作能力域：无人可做，绝不退给本地模块
        assert reg.creative_backends() == []
        assert reg.image_backends() == []
        assert reg.video_backends() == []
        for scope in CREATIVE_SCOPES:
            assert reg.select(scope) is None, scope

        # 生成请求必须抛错 + 留下待执行任务
        try:
            reg.generate("image_generation",
                         {"project_id": "p", "view_id": "v1"}, Path(td))
        except NotConfigured as exc:
            msg = str(exc)
            assert CREATIVE_OWNER in msg
            assert "第三方" in msg or "不回退" in msg or "不会" in msg
        else:  # pragma: no cover
            raise AssertionError("不可用时必须抛错")

        assert reg.deferred, "必须生成待执行任务"
        task = reg.deferred[0]
        assert task["status"] == "awaiting_platform"
        assert task["owner_required"] == CREATIVE_OWNER
        assert "第三方" in task["note"]

        # 报告里必须写清楚：第三方回退是被禁止的
        rep = reg.report()
        assert rep["creative_policy"]["third_party_fallback"] == "forbidden"
        assert rep["deferred_tasks"] == 1


def test_no_provider_registry_anywhere_can_be_asked_to_fall_back():
    """每一个已登记的 provider id 都要有明确裁决；没有第三个可选项。"""
    assert set(ROUTE_ALLOWLIST) == {"omniailab", "local"}
    with tempfile.TemporaryDirectory() as td:
        reg = discover(td, refresh=True)
        assert {p.id for p in reg.providers} == {"omniailab", "local"}


def test_a_capability_declaration_cannot_smuggle_a_creative_scope():
    for pid in ("midjourney", "runway", "some-vendor"):
        try:
            ProviderCapability(provider=pid, state="connected",
                               scopes=["video_generation"])
        except PolicyViolation:
            pass
        else:  # pragma: no cover
            raise AssertionError(f"{pid} 不得声明创作能力域")


def test_a_provider_subclass_cannot_declare_itself_generative():
    try:
        class Rogue(MediaProvider):
            id = "not-omniailab"
            generative = True
    except PolicyViolation as exc:
        assert "创作能力独占" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("只有原生平台可以声明为生成式主体")


def test_media_provider_run_refuses_a_creative_scope_for_a_foreign_id():
    class Vendor(MediaProvider):
        id = "local"          # 在册，但只是自有模块

        def probe(self):
            return ProviderCapability(provider="local", state="connected",
                                      provider_kind="own-builtin",
                                      scopes=["schematic_diagram"])

    try:
        Vendor().run("image_generation", {}, ".")
    except PolicyViolation as exc:
        assert "创作能力独占" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("自有模块不得执行创作能力域")


# ==========================================================================
# 报告
# ==========================================================================
def test_report_is_renderable_and_machine_readable():
    with tempfile.TemporaryDirectory() as td:
        root = _tree(td)
        rep = bp.scan(root)
        md = bp.render_markdown(rep)
        assert "# 品牌与供应商策略审计报告" in md
        assert "brand-and-provider-policy" in md
        assert "品牌登记" in md
        assert "命中分类" in md
        assert "已登记：经批准的依赖" in md
        assert "唯一被授权主体" in md
        assert SIGNATURE in md
        out = bp.write_report(td, root=root)
        for key in ("markdown", "json"):
            assert Path(out[key]).exists()
        data = json.loads(Path(out["json"]).read_text(encoding="utf-8"))
        assert data["policy"] == "brand-and-provider-policy"
        assert "forbidden" in bp.DISPOSITIONS
        assert "compliance-required" in bp.DISPOSITIONS


def test_nine_rules_are_all_reported_even_with_zero_hits():
    with tempfile.TemporaryDirectory() as td:
        root = _tree(td)
        rep = bp.scan(root)
        by_rule = rep.to_dict()["by_rule"]
        assert set(by_rule) == {r["id"] for r in bp.RULES}
        assert len(by_rule) == 9


def test_the_real_repository_passes_its_own_policy():
    rep = bp.scan(ROOT)
    assert rep.files_scanned > 100
    assert rep.action_count == 0, [
        (h.path, h.rule, h.disposition, h.token) for h in rep.forbidden + rep.needs_review
    ]
    assert rep.to_dict()["conclusion"]


def test_licence_files_are_present_and_carry_attribution():
    assert (ROOT / bp.NOTICE_FILE).exists()
    assert (ROOT / bp.LICENCE_DIR / "README.md").exists()
    body = (ROOT / bp.NOTICE_FILE).read_text(encoding="utf-8")
    for dep in bp.APPROVED_DEPENDENCIES:
        assert dep["name"] in body
        assert dep["spdx"] in body
    # 登记文件必须仍带出品方署名——不得通过删署名来"洗白"
    assert "© OmniAiLab" in body
