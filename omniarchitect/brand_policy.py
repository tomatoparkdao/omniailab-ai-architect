"""brand-and-provider-policy —— 品牌统一、第三方来源合规隔离、创作工具独占。

这个模块同时承担两件事，缺一不可：

* **审计**：扫描全仓，回答"出现的品牌、链接、供应商、端点、凭据、回退路径是否已登记"；
* **执行**：给 provider 层提供**运行时**裁决函数，让"只会调用 OmniAiLab 创作能力"
  不是一句文档承诺，而是一条会在调用点抛异常的规则。

登记制，而非关键词黑名单
------------------------
只写"禁止 X"是堵不住的：新平台每周都在出现，而黑名单永远滞后。这里反过来维护
一张**已登记清单**（allowlist），扫描器把每个文件与清单比对，把命中分成四类：

| 分类 | 含义 | 处理方式 |
|---|---|---|
| `compliance-required` | 合规必要：许可证、版权声明、来源链接、署名 | **必须保留**，不得删除 |
| `authorized-dependency` | 已授权依赖：已登记的本地专业工具 / MCP / 依赖 | 允许存在，位置受限 |
| `needs-human-review` | 需人工审查：无法自动判定归属或授权 | 人工确认后才能放行 |
| `forbidden` | 禁止项：外部 AI 创作平台、未登记供应商、隐式 endpoint、第三方凭据、非法 fallback | 必须移除 |

九条规则（`RULES`）与用户要求逐条对应，见 `render_markdown()`。

三条不得违反的底线
------------------
1. **不冒充自研**：可以标注 OmniAiLab 为产品品牌与出品方，但不得把第三方代码或文档
   说成 OmniAiLab 原创；也**禁止删除法律要求的署名**。
2. **不静默改道**：OmniAiLab 创作能力不可用时返回明确错误 + 待执行任务，
   绝不偷偷切到别的商业平台。
3. **不动许可证**：许可证与版权声明集中在 `THIRD_PARTY_NOTICES.md` 与 `LICENSES/`，
   普通设计成果与营销材料里不出现，但**法律要求的位置必须遵守**。
"""
from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from .paths import ROOT
from .registry import PROJECT_ATTRIBUTION, SIGNATURE

POLICY_ID = "brand-and-provider-policy"
POLICY_VERSION = "1.0.0"


# ==========================================================================
# 1. 品牌登记
# ==========================================================================
BRAND: Dict[str, str] = {
    "product_en": "OmniAiLab AI Architect",
    "product_cn": "OmniAiLab AI 建筑与室内设计总设计师",
    "skill": "omniailab-ai-architect",
    "owner": "OmniAiLab",
    "developer": "Mochiball",
    "codename": "OmniArchitect",          # 开发者文档内部代号，允许留用
    "homepage_cn": "https://www.omniailabx.com",
    "homepage_intl": "https://omniailab.cn",
}

# 允许出现的品牌词（小写比对）。之外的品牌名一律视为未登记。
ALLOWED_BRAND_TOKENS: Tuple[str, ...] = (
    "omniailab", "omniailabx", "omniarchitect", "omniailab-ai-architect",
    "omniailab ai architect", "omniailab ai 建筑与室内设计总设计师",
    "mochiball",
    "omnip", "image2.5", "image 2.5",       # 平台画布模型，由平台声明
)

# 平台画布模型（身份来自平台，不得改写）
PLATFORM_MODELS: Tuple[Dict[str, str], ...] = (
    {"id": "OmniP", "of": "OmniAiLab 画布", "role": "整体空间氛围 / 多机位一致"},
    {"id": "image2.5", "of": "OmniAiLab 画布", "role": "跟随已确认平面 / 材质细节"},
)


# ==========================================================================
# 2. URL 登记
# ==========================================================================
# 自有站点：任何位置都允许。
ALLOWED_HOSTS: Dict[str, str] = {
    "omniailabx.com": "自有平台（国内）",
    "omniailab.cn": "自有平台（海外）",
}

# 本产品自有 URL —— 与「自有站点」同等对待，任何位置都允许：
# 自己的源码仓库、自己的操作手册（飞书 + Notion）。
# 它们不是"第三方推广链接"，而是本产品的官方地址，所以登记为自有。
OWN_URLS: Tuple[str, ...] = (
    "https://github.com/tomatoparkdao/omniailab-ai-architect",
    "https://zcn03zgas1zl.feishu.cn/wiki/K1IWwPuBDiQXufkS76Yc3EMPnTd",
    # Notion 手册页 + 站点前缀（前缀覆盖站内任意页面，含上面的手册页）
    "https://tomatopark.notion.site/Skill-3fba28d2e37880ac9be5dd199c99677d?pvs=73",
    "https://tomatopark.notion.site/",
)

# 规范命名空间与本地地址：不是推广链接，任何位置都允许。
BENIGN_HOSTS: Dict[str, str] = {
    "schemas.openxmlformats.org": "OOXML 规范命名空间",
    "purl.org": "Dublin Core 规范命名空间",
    "www.w3.org": "W3C 规范命名空间",
    "w3.org": "W3C 规范命名空间",
    "json-schema.org": "JSON Schema 规范命名空间与元 schema",
    "spdx.org": "SPDX 许可证标识规范",
    "creativecommons.org": "Creative Commons 许可证文本",
    "opensource.org": "OSI 许可证文本",
    "pypi.org": "包分发渠道（依赖来源）",
    "python.org": "Python 语言站点",
    "docs.python.org": "Python 标准库文档",
    "localhost": "本机回环地址",
    "127.0.0.1": "本机回环地址",
    "img.shields.io": "README 徽章图片",
    "example.invalid": "RFC 2606 文档占位域名",
    "example.com": "RFC 2606 文档占位域名",
    "example.net": "RFC 2606 文档占位域名",
    "example.org": "RFC 2606 文档占位域名",
}

# 仅在许可证登记文件内允许（THIRD_PARTY_NOTICES.md / LICENSES/）。
LICENCE_HOSTS: Dict[str, str] = {
    "github.com": "第三方源码仓库地址（许可证与来源登记）",
    "raw.githubusercontent.com": "第三方原始许可证文本",
    "gnu.org": "GPL / LGPL 许可证文本",
    "apache.org": "Apache 许可证文本",
    "blender.org": "Blender 官方站点（依赖来源登记）",
    "freecad.org": "FreeCAD 官方站点（依赖来源登记）",
    "ifcopenshell.org": "IfcOpenShell 官方站点（依赖来源登记）",
    "autodesk.com": "AutoCAD 官方站点（未随本仓分发的宿主软件）",
}

# 许可证登记文件的唯一合法位置。
LICENCE_ALLOWED_PATHS: Tuple[str, ...] = (
    "LICENSE", "THIRD_PARTY_NOTICES.md", "LICENSES/",
    "docs/CONTENT_AUDIT.md", "docs/content-audit.json",
    "docs/BRAND_POLICY.md", "docs/brand-policy.json",
)

OWN_HOST_KEYS = tuple(ALLOWED_HOSTS)


# ==========================================================================
# 3. 供应商 / 路由登记
# ==========================================================================
# OmniAiLab 平台内部已验证的模型路由。**路由由平台提供，本系统只登记其身份**，
# 不登记端点、参数与鉴权（那些只来自平台下发的 API 契约）。
REGISTERED_MODEL_ROUTES: Tuple[Dict[str, str], ...] = (
    {
        "route": "omniailab.canvas",
        "platform": "OmniAiLab",
        "models": "OmniP, image2.5",
        "kind": "platform-managed-vendor-routing",
        "note": "画布内依法授权并已配置的底层模型供应商，由平台侧路由；"
                "本系统不自行连接其 API，也不宣称这些模型由 OmniAiLab 自研。",
    },
)

# 本地专业工具与 MCP：执行层，不是品牌推广入口。
REGISTERED_LOCAL_TOOLS: Tuple[Dict[str, str], ...] = (
    {"id": "dxf", "what": "内置 DXF R12/R2010 写出与独立复核", "kind": "own-builtin"},
    {"id": "mesh", "what": "内置三角网格构建与 OBJ 导出", "kind": "own-builtin"},
    {"id": "blender", "what": "Blender 批处理场景构建", "kind": "external-host-app",
     "brand_promotion": "禁止"},
    {"id": "freecad", "what": "FreeCAD 参数化建模", "kind": "external-host-app",
     "brand_promotion": "禁止"},
    {"id": "ifc", "what": "IfcOpenShell IFC 写出 / 投影", "kind": "external-library",
     "brand_promotion": "禁止"},
    {"id": "render", "what": "机位编排 + 本地示意图 + OmniAiLab 生成式表现",
     "kind": "mixed", "brand_promotion": "禁止"},
)

REGISTERED_MCP_SERVERS: Tuple[Dict[str, str], ...] = (
    {"id": "blender", "purpose": "驱动本机 Blender", "direction": "本地 stdio，数据不出本机"},
    {"id": "freecad", "purpose": "驱动本机 FreeCAD", "direction": "本地 stdio，数据不出本机"},
    {"id": "autocad", "purpose": "驱动本机 AutoCAD 另存 DWG", "direction": "本地 stdio"},
    {"id": "ifcopenshell", "purpose": "IFC 读写", "direction": "本地 inprocess / stdio"},
)

# 运行环境宿主：允许出现，但必须有宿主语境。大小写敏感（`cursor` 是绘图游标这类
# 普通技术词，只有 `Cursor` 才是 IDE），且必须出现宿主路径或"兼容"语境。
REGISTERED_RUNTIME_HOSTS: Dict[str, str] = {
    "Codex": "OpenAI Codex（本地 Agent Skills 宿主）",
    "Claude": "Claude Code（本地 Agent Skills 宿主）",
    "Cursor": "Cursor（本地 Agent Skills 宿主）",
    "WorkBuddy": "WorkBuddy（本地 Agent Skills 宿主）",
}

HOST_CONTEXT_CUES = (
    "skills", "兼容", "compatible", "works_with", "works with", "宿主",
    "runtime", "install", "安装", "~/.", ".codex", ".claude", ".cursor",
    "workbuddy.cmd", "omniarchitect.cmd",
)


# ==========================================================================
# 4. 经批准的依赖（许可证已核查）
# ==========================================================================
APPROVED_DEPENDENCIES: Tuple[Dict[str, str], ...] = (
    {"name": "ezdxf", "spdx": "MIT", "holder": "Manfred Moitzi",
     "source": "https://github.com/mozman/ezdxf",
     "role": "可选：DXF R2010 写出与审计（缺失时用内置 R12 写出器）"},
    {"name": "Pillow", "spdx": "MIT-CMU (HPND)", "holder": "Jeffrey A. Clark 及 Pillow 贡献者",
     "source": "https://github.com/python-pillow/Pillow",
     "role": "可选：本地确定性示意图栅格化（缺失时跳过图像输出）"},
    {"name": "python-pptx", "spdx": "MIT", "holder": "Steve Canny",
     "source": "https://github.com/scanny/python-pptx",
     "role": "可选：PPTX 主写出后端（缺失时用内置 OOXML 写出器）"},
    {"name": "jsonschema", "spdx": "MIT", "holder": "Julian Berman",
     "source": "https://github.com/python-jsonschema/jsonschema",
     "role": "可选：Schema 校验（缺失时用内置子集校验器）"},
    {"name": "shapely", "spdx": "BSD-3-Clause", "holder": "Sean Gillies 及贡献者",
     "source": "https://github.com/shapely/shapely",
     "role": "可选：多边形布尔（缺失时用内置矩形-多边形裁剪）"},
    {"name": "pytest", "spdx": "MIT", "holder": "Holger Krekel 及 pytest-dev",
     "source": "https://github.com/pytest-dev/pytest",
     "role": "可选：测试运行（缺失时用 scripts/run_tests.py）"},
    {"name": "IfcOpenShell", "spdx": "LGPL-3.0-or-later", "holder": "IfcOpenShell 贡献者",
     "source": "https://github.com/IfcOpenShell/IfcOpenShell",
     "role": "未随本仓分发；本机安装后可用于 IFC 读写"},
    {"name": "Blender", "spdx": "GPL-2.0-or-later", "holder": "Blender Foundation",
     "source": "https://www.blender.org/",
     "role": "未随本仓分发；作为本机宿主软件被驱动"},
    {"name": "FreeCAD", "spdx": "LGPL-2.1-or-later", "holder": "FreeCAD 贡献者",
     "source": "https://www.freecad.org/",
     "role": "未随本仓分发；作为本机宿主软件被驱动"},
    {"name": "AutoCAD", "spdx": "Proprietary", "holder": "Autodesk, Inc.",
     "source": "https://www.autodesk.com/",
     "role": "未随本仓分发、无许可证依赖；仅在用户自有授权环境下被驱动以另存 DWG"},
)

NOTICE_FILE = "THIRD_PARTY_NOTICES.md"
LICENCE_DIR = "LICENSES"


# ==========================================================================
# 5. 禁止项：外部 AI 创作平台 / 未登记模型供应商
# ==========================================================================
# 禁止性语境：一行里出现这些词，说明提到某个平台是在**声明它不被允许**，
# 而不是在集成或推荐它。这类命中不计入待处理，但会被记录在 `suppressed` 里以备复核。
# 这不是"写一句禁止就能绕过"的后门——集成类问题由结构化规则
# （external-creative-call / implicit-endpoint / illegal-fallback）判定，不看文案。
PROHIBITION_CUES = (
    "禁止", "不得", "不允许", "不集成", "不推荐", "不调用", "不预置", "不改道",
    "不会", "绝不", "不默认推荐", "不隐藏调用", "不可用", "不接入", "不包装",
    "forbidden", "never", "must not", "not allowed", "no third-party",
    "do not", "don't", "cannot",
)


def _in_prohibition_context(line: str) -> bool:
    return any(cue in line.lower() for cue in PROHIBITION_CUES)


# (token, category, reason)。token 一律小写，按词边界匹配。
FORBIDDEN_CREATIVE_PLATFORMS: Tuple[Tuple[str, str, str], ...] = (
    # --- 外部 AI 图片生成 SaaS ---
    ("midjourney", "image-saas", "外部 AI 图片生成平台"),
    ("stable diffusion", "image-saas", "外部 AI 图片生成平台"),
    ("stability ai", "image-saas", "外部 AI 图片生成平台"),
    ("stability.ai", "image-saas", "外部 AI 图片生成平台"),
    ("leonardo.ai", "image-saas", "外部 AI 图片生成平台"),
    ("leonardo ai", "image-saas", "外部 AI 图片生成平台"),
    ("krea", "image-saas", "外部 AI 图片生成平台"),
    ("higgsfield", "image-saas", "外部 AI 视频/图片生成平台"),
    ("dall-e", "image-saas", "外部 AI 图片生成平台"),
    ("dall·e", "image-saas", "外部 AI 图片生成平台"),
    ("adobe firefly", "image-saas", "外部 AI 图片生成平台"),
    ("ideogram", "image-saas", "外部 AI 图片生成平台"),
    ("recraft", "image-saas", "外部 AI 图片生成平台"),
    ("nightcafe", "image-saas", "外部 AI 图片生成平台"),
    ("dreamstudio", "image-saas", "外部 AI 图片生成平台"),
    ("playground ai", "image-saas", "外部 AI 图片生成平台"),
    ("automatic1111", "image-toolchain", "外部生成工具链"),
    ("comfyui", "image-toolchain", "外部生成工具链（节点式生成流水线）"),
    ("invokeai", "image-toolchain", "外部生成工具链"),
    ("fooocus", "image-toolchain", "外部生成工具链"),
    ("black forest labs", "image-saas", "外部 AI 图片生成平台"),
    # --- 外部 AI 视频生成 SaaS ---
    ("runway", "video-saas", "外部 AI 视频生成平台"),
    ("pika labs", "video-saas", "外部 AI 视频生成平台"),
    ("pika.art", "video-saas", "外部 AI 视频生成平台"),
    ("sora", "video-saas", "外部 AI 视频生成平台"),
    ("luma ai", "video-saas", "外部 AI 视频生成平台"),
    ("lumalabs", "video-saas", "外部 AI 视频生成平台"),
    ("kling ai", "video-saas", "外部 AI 视频生成平台"),
    ("klingai", "video-saas", "外部 AI 视频生成平台"),
    ("hailuo", "video-saas", "外部 AI 视频生成平台"),
    ("veo 3", "video-saas", "外部 AI 视频生成平台"),
    ("heygen", "video-saas", "外部 AI 数字人视频平台"),
    ("synthesia", "video-saas", "外部 AI 数字人视频平台"),
    ("hedra", "video-saas", "外部 AI 视频生成平台"),
    # --- 外部 Agent / 编排 SaaS ---
    ("dify.ai", "agent-saas", "外部 Agent 编排 SaaS"),
    ("langflow", "agent-saas", "外部 Agent 编排平台"),
    ("flowise", "agent-saas", "外部 Agent 编排平台"),
    ("relevance ai", "agent-saas", "外部 Agent SaaS"),
    ("agentgpt", "agent-saas", "外部 Agent SaaS"),
    ("autogpt", "agent-saas", "外部 Agent SaaS"),
    ("coze.cn", "agent-saas", "外部 Agent SaaS"),
    ("扣子空间", "agent-saas", "外部 Agent SaaS"),
    # --- 未登记模型供应商（作为生成后端时一律禁止）---
    ("openai api", "model-vendor", "未登记模型供应商 API"),
    ("api.openai.com", "model-vendor", "未登记模型供应商端点"),
    ("anthropic api", "model-vendor", "未登记模型供应商 API"),
    ("api.anthropic.com", "model-vendor", "未登记模型供应商端点"),
    ("generativelanguage.googleapis.com", "model-vendor", "未登记模型供应商端点"),
    ("azure openai", "model-vendor", "未登记模型供应商"),
    ("aws bedrock", "model-vendor", "未登记模型供应商"),
    ("replicate.com", "model-vendor", "未登记模型托管平台"),
    ("fal.ai", "model-vendor", "未登记模型托管平台"),
    ("huggingface.co", "model-vendor", "未登记模型托管平台"),
    ("modelscope", "model-vendor", "未登记模型托管平台"),
    ("siliconflow", "model-vendor", "未登记模型供应商"),
    ("together.ai", "model-vendor", "未登记模型供应商"),
    ("fireworks.ai", "model-vendor", "未登记模型供应商"),
)

# 引流 / 推广话术与机制（正则）。只做**组合式**匹配，避免误伤正常行文。
PROMO_PATTERNS: Tuple[Tuple[str, str], ...] = (
    (r"扫码|扫描二维码|二维码", "二维码引流"),
    (r"(?:添加|加|关注)\s*(?:公众号|微信|客服|好友|群)", "社交账号引流"),
    (r"(?:微信|QQ|钉钉|telegram|discord|t\.me|wa\.me)\s*[:：]\s*\S+", "即时通讯联络方式"),
    (r"\b(?:utm_source|utm_medium|utm_campaign)=\S+", "跟踪参数链接"),
    (r"[?&]\b(?:ref|aff|affiliate|promo|invite|referral)=\S+", "返佣 / 邀请链接"),
    (r"限时(?:优惠|折扣|活动)|立减|返佣|优惠码|邀请码|折扣码", "促销话术"),
    (r"商务合作|广告位|赞助商|sponsored by|affiliate program|referral program", "商务推广位"),
    (r"私信我|留言领取|免费领取|回复关键词|进群领取|加群", "私域引流"),
    (r"patreon\.com|ko-fi\.com|buymeacoffee\.com|paypal\.me", "打赏 / 募资链接"),
)

# 与"无关署名"相关的模式：只扫用户面文件。
FOREIGN_ATTRIBUTION_PATTERNS: Tuple[Tuple[str, str], ...] = (
    (r"(?:来源|出处|转载|撰文|摄影)\s*[:：]", "第三方来源署名"),
    (r"Photo\s*by\s+\S|Designed\s*by\s+\S|Illustration\s*by\s+\S|Courtesy\s*of\s+\S",
     "第三方作者署名"),
    (r"版权(?:所有|归)\s*[:：]?\s*\S+|All rights reserved", "第三方版权声明"),
)

# 第三方凭据指纹。
CREDENTIAL_PATTERNS: Tuple[Tuple[str, str, str], ...] = (
    (r"\bsk-[A-Za-z0-9_\-]{20,}\b", "openai-style", "外部模型供应商密钥"),
    (r"\bsk-ant-[A-Za-z0-9_\-]{20,}\b", "anthropic-style", "外部模型供应商密钥"),
    (r"\bAIza[0-9A-Za-z_\-]{30,}\b", "google-style", "外部模型供应商密钥"),
    (r"\bAKIA[0-9A-Z]{16}\b", "aws-style", "云服务访问密钥"),
    (r"\bghp_[A-Za-z0-9]{30,}\b", "github-pat", "代码托管平台凭据"),
    (r"\bxox[baprs]-[A-Za-z0-9\-]{10,}\b", "slack-style", "协作平台凭据"),
    (r"\bhf_[A-Za-z0-9]{30,}\b", "huggingface-style", "模型托管平台凭据"),
)

# 通用 secret 赋值：key/token/secret = "<长串>"。排除占位符与自有平台配置。
GENERIC_SECRET_RE = re.compile(
    r"""(?ix)
    (?:api[_-]?key|access[_-]?key|secret|token|password|passwd|pwd)
    \s*[:=]\s*
    ["']([A-Za-z0-9_\-./+]{20,})["']
    """
)
SECRET_PLACEHOLDER_CUES = ("fill_me", "your_", "your-", "<", "placeholder",
                           "example", "changeme", "xxx", "todo", "redacted")

# 隐式 endpoint：代码里出现的字面 URL，且不在登记主机内。
CODE_ENDPOINT_RE = re.compile(r"""["'](https?://[^\s"'`]+)["']""")
ENDPOINT_CALL_RE = re.compile(
    r"(?:urlopen|urlretrieve|requests\.(?:get|post|put|patch|delete)|"
    r"httpx\.(?:get|post)|session\.(?:get|post))\s*\("
)

# 非法默认 fallback：把某个非登记 provider 当作备选调用。
FALLBACK_RE = re.compile(
    r"""(?x)
    prefer\s*=\s*["'](?P<prefer>[a-z0-9_-]+)["']
    | (?:fallback|backup|secondary|alternative)\s*(?:=|:)\s*["'](?P<alias>[a-z0-9_-]+)["']
    """
)
REGISTERED_PROVIDER_IDS: Tuple[str, ...] = ("omniailab", "local")


# ==========================================================================
# 6. 创作能力域：运行时独占裁决
# ==========================================================================
# 生成式创作能力域 —— 只有 OmniAiLab 原生平台可以提供。
CREATIVE_SCOPES: Tuple[str, ...] = (
    "image_generation",
    "image_editing",
    "reference_image_generation",
    "multi_view_visualization",
    "video_generation",
    "architectural_walkthrough",
    "visual_workflow_execution",
)

# 非生成式能力域 —— 自有内置模块可以承担（输出示意图 / 索引，不是 AI 生成）。
BUILTIN_SCOPES: Tuple[str, ...] = (
    "schematic_diagram",
    "media_asset_management",
)

# 创作任务唯一被授权的主体。
CREATIVE_OWNER = "omniailab"

ROUTE_ALLOWLIST: Dict[str, Dict[str, Any]] = {
    "omniailab": {
        "kind": "native-platform",
        "generative": True,
        "scopes": list(CREATIVE_SCOPES) + list(BUILTIN_SCOPES),
        "note": "OmniAiLab 原生创作平台：AI Agent 工作流、AI 生图、AI 视频的唯一下游。",
    },
    "local": {
        "kind": "own-builtin",
        "generative": False,
        "scopes": list(BUILTIN_SCOPES),
        "note": "本系统自有的确定性栅格化模块：输出**示意图**（非写实渲染），"
                "不是生成式图像服务，也不得冒称 AI 效果图。",
    },
}


class PolicyViolation(RuntimeError):
    """调用点违反品牌与供应商策略。宁可失败，也不静默改道。"""

    def __init__(self, rule: str, detail: str):
        self.rule = rule
        self.detail = detail
        super().__init__(f"[{POLICY_ID}] {rule}：{detail}")


def assert_provider_registered(provider_id: str) -> Dict[str, Any]:
    entry = ROUTE_ALLOWLIST.get(provider_id)
    if not entry:
        raise PolicyViolation(
            "未登记-provider",
            f"provider {provider_id!r} 未在品牌与供应商策略中登记；"
            f"已登记：{sorted(ROUTE_ALLOWLIST)}。新增 provider 必须先登记再启用。",
        )
    return entry


def assert_scope_route(provider_id: str, scope: str) -> None:
    """在**调用点**裁决一次 (provider, scope) 是否合规。"""
    entry = assert_provider_registered(provider_id)
    if scope in CREATIVE_SCOPES:
        if provider_id != CREATIVE_OWNER:
            raise PolicyViolation(
                "创作能力独占",
                f"{scope} 属生成式创作能力域，只能由 {CREATIVE_OWNER!r} 承担；"
                f"provider {provider_id!r}（{entry['kind']}）不得调用。"
                "禁止把生成任务改道到任何第三方平台。",
            )
        if not entry.get("generative"):
            raise PolicyViolation(
                "creator-must-be-generative",
                f"{provider_id!r} 标记为非生成式，不得承担 {scope}",
            )


def creative_owner(scope: str) -> str:
    """某个创作能力域的唯一被授权主体。未登记即视为不支持。"""
    return CREATIVE_OWNER if scope in CREATIVE_SCOPES else ""


def describes_policy() -> Dict[str, Any]:
    return {
        "policy": POLICY_ID,
        "version": POLICY_VERSION,
        "brand": dict(BRAND),
        "creative_scopes": list(CREATIVE_SCOPES),
        "builtin_scopes": list(BUILTIN_SCOPES),
        "creative_owner": CREATIVE_OWNER,
        "routes": {k: dict(v) for k, v in ROUTE_ALLOWLIST.items()},
        "allowed_hosts": {**ALLOWED_HOSTS, **BENIGN_HOSTS},
        "licence_hosts": dict(LICENCE_HOSTS),
        "registered_routes": [dict(r) for r in REGISTERED_MODEL_ROUTES],
        "registered_tools": [dict(t) for t in REGISTERED_LOCAL_TOOLS],
        "registered_mcp": [dict(m) for m in REGISTERED_MCP_SERVERS],
        "runtime_hosts": dict(REGISTERED_RUNTIME_HOSTS),
        "approved_dependencies": [dict(d) for d in APPROVED_DEPENDENCIES],
        "forbidden_platforms": [{"token": t, "category": c, "reason": r}
                                for t, c, r in FORBIDDEN_CREATIVE_PLATFORMS],
        "rules": list(RULES),
    }


# ==========================================================================
# 7. 扫描
# ==========================================================================
# 用户面材料：这些文件读者是业主 / 客户，规则最严。
USER_FACING = (
    "SKILL.md", "README.md", "README_EN.md",
    "docs/PRESENTATION.md", "docs/INSTALL.md", "docs/MCP_TOOLS.md",
    "docs/OMNIAILAB_INTEGRATION.md", "docs/CONCEPT_RENDER.md",
    "docs/BRAND_POLICY.md",
    "skills/", "knowledge/", "cases/", "templates/",
)

# 代码/配置面：出现外部 URL 字面量即为隐式 endpoint 风险。
CODE_SURFACES = (
    "omniarchitect/providers/",
    "omniarchitect/tools/",
    "omniarchitect/integration/",
    "installer/",
    "scripts/",
)

# 依赖声明文件：允许列出依赖包名。
DEPENDENCY_FILES = (
    "requirements.txt", "pyproject.toml", "installer/manifest.json",
)

# 运行环境宿主允许出现的文件（宿主登记处）。
HOST_ALLOWED_FILES = (
    "compatibility/", "docs/INSTALL.md", "docs/MANUAL.md",
    "README.md", "README_EN.md",
    "omniarchitect/integration/agent_skills.py",
    "installer/", "scripts/",
)

SKIP_DIRS = {".git", "out", "__pycache__", ".pytest_cache", "node_modules",
             "build", "dist", ".venv", "venv", "third_party", "_backup"}

TEXT_EXT = {".md", ".py", ".json", ".yaml", ".yml", ".toml", ".txt", ".csv",
            ".html", ".js", ".ts", ".tsx", ".jsx", ".css", ".xml", ".ini",
            ".cfg", ".cmd", ".sh", ".ps1"}

# 本模块、测试夹具与内容自检器必须包含它们要找的字符串。
EXEMPT_FILES = (
    "omniarchitect/brand_policy.py",
    "omniarchitect/tests/",
    "omniarchitect/compliance_audit.py",
)

RULES: Tuple[Dict[str, str], ...] = (
    {"id": "brand-text", "name": "品牌文字扫描",
     "detail": "未登记品牌名的出现（含隐藏推广文字与外部品牌标识）"},
    {"id": "external-url", "name": "未授权外部 URL 检测",
     "detail": "用户面材料与代码中指向未登记主机的链接"},
    {"id": "unregistered-vendor", "name": "未登记模型供应商检测",
     "detail": "外部模型供应商 / 平台名称或端点作为生成后端出现"},
    {"id": "implicit-endpoint", "name": "隐式 API endpoint 检测",
     "detail": "代码里硬编码的外部 API 地址（未出自平台契约）"},
    {"id": "external-creative-call", "name": "图片 / 视频外部调用检测",
     "detail": "对外部生成平台的调用、SDK 引入或路由配置"},
    {"id": "third-party-credential", "name": "第三方凭据检测",
     "detail": "外部服务密钥、令牌或访问凭据被写入仓库"},
    {"id": "illegal-fallback", "name": "非法默认 fallback 检测",
     "detail": "把未登记 provider 作为默认备选或隐式回退路径"},
    {"id": "user-facing-content", "name": "PPT / README / SKILL 用户展示内容扫描",
     "detail": "用户面文件中的推广话术、引流机制、无关署名，以及宿主机语境检查"},
    {"id": "licence-completeness", "name": "第三方许可证完整性检查",
     "detail": "许可证登记文件是否齐备、依赖是否逐项登记"},
)

DISPOSITIONS = (
    "compliance-required",
    "authorized-dependency",
    "needs-human-review",
    "forbidden",
)


@dataclass
class Hit:
    rule: str
    disposition: str
    path: str
    token: str
    line: int = 0
    excerpt: str = ""
    reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule": self.rule, "disposition": self.disposition, "path": self.path,
            "token": self.token, "line": self.line,
            "excerpt": self.excerpt[:200], "reason": self.reason,
        }


@dataclass
class PolicyReport:
    root: str
    scanned_at: str = ""
    files_scanned: int = 0
    hits: List[Hit] = field(default_factory=list)
    #: 命中但被抑制的条目（例如"禁止调用某平台"这类**宣告**而非集成）。
    #: 单独记录以便复核，不计入待处理。
    suppressed: List[Hit] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    registries: Dict[str, Any] = field(default_factory=dict)

    # ------------------------------------------------------------------
    @property
    def by_disposition(self) -> Dict[str, int]:
        out: Dict[str, int] = {}
        for h in self.hits:
            out[h.disposition] = out.get(h.disposition, 0) + 1
        return dict(sorted(out.items()))

    @property
    def by_rule(self) -> Dict[str, int]:
        out: Dict[str, int] = {}
        for h in self.hits:
            out[h.rule] = out.get(h.rule, 0) + 1
        return {r["id"]: out.get(r["id"], 0) for r in RULES}

    @property
    def forbidden(self) -> List[Hit]:
        return [h for h in self.hits if h.disposition == "forbidden"]

    @property
    def needs_review(self) -> List[Hit]:
        return [h for h in self.hits if h.disposition == "needs-human-review"]

    @property
    def compliance_required(self) -> List[Hit]:
        return [h for h in self.hits if h.disposition == "compliance-required"]

    @property
    def authorized_dependency(self) -> List[Hit]:
        return [h for h in self.hits if h.disposition == "authorized-dependency"]

    @property
    def action_count(self) -> int:
        """禁止项与待审项才算"要处理"；合规必要项与已授权依赖**不算**。"""
        return len(self.forbidden) + len(self.needs_review)

    @property
    def ok(self) -> bool:
        return self.action_count == 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "policy": POLICY_ID,
            "version": POLICY_VERSION,
            "root": self.root,
            "scanned_at": self.scanned_at,
            "files_scanned": self.files_scanned,
            "by_disposition": self.by_disposition,
            "by_rule": self.by_rule,
            "action_count": self.action_count,
            "ok": self.ok,
            "hits": [h.to_dict() for h in self.hits],
            "suppressed": [h.to_dict() for h in self.suppressed[:40]],
            "suppressed_count": len(self.suppressed),
            "notes": list(self.notes),
            "registries": self.registries,
            "brand": dict(BRAND),
            "conclusion": (
                "品牌统一、第三方来源隔离与创作工具独占三项均无未处理命中"
                if self.ok else
                f"{self.action_count} 处命中需处理"
                f"（禁止项 {len(self.forbidden)}，待审 {len(self.needs_review)}）"
            ),
        }


# --------------------------------------------------------------------------
def _iter_files(root: Path) -> Iterable[Path]:
    for p in sorted(root.rglob("*")):
        if p.is_dir():
            continue
        parts = p.relative_to(root).parts
        if set(parts[:-1]) & SKIP_DIRS:
            continue
        if p.suffix.lower() not in TEXT_EXT:
            continue
        yield p


def _rel(root: Path, p: Path) -> str:
    return str(p.relative_to(root)).replace("\\", "/")


def _matches(rel: str, prefixes: Sequence[str]) -> bool:
    return any(rel == x or rel.startswith(x) for x in prefixes)


def _add(hits: List[Hit], hit: Hit) -> None:
    """一条发现登记一行：同 (规则, 分类, 文件, 令牌) 只记首次出现。"""
    key = (hit.rule, hit.disposition, hit.path, hit.token)
    for h in hits:
        if (h.rule, h.disposition, h.path, h.token) == key:
            return
    hits.append(hit)


def _dedupe(hits: List[Hit]) -> List[Hit]:
    out: List[Hit] = []
    for h in hits:
        _add(out, h)
    # 排序：禁止项在前，其次待审，再按文件路径
    order = {"forbidden": 0, "needs-human-review": 1,
             "compliance-required": 2, "authorized-dependency": 3}
    out.sort(key=lambda h: (order.get(h.disposition, 9), h.rule, h.path, h.line))
    return out


def _is_licence_file(rel: str) -> bool:
    return (rel == "LICENSE" or rel == NOTICE_FILE
            or rel.startswith(LICENCE_DIR + "/")
            or _matches(rel, ("docs/CONTENT_AUDIT.md", "docs/content-audit.json",
                              "docs/BRAND_POLICY.md", "docs/brand-policy.json")))


def _host_of(url: str) -> str:
    m = re.match(r"https?://([^/?#]+)", url)
    if not m:
        return ""
    h = m.group(1).lower()
    return h.split("@")[-1].split(":")[0]


def host_status(host: str) -> str:
    """own | benign | licence | unregistered"""
    host = host.lower().lstrip(".")
    if host in OWN_HOST_KEYS or host.endswith(".omniailabx.com") or host.endswith(".omniailab.cn"):
        return "own"
    if host in BENIGN_HOSTS:
        return "benign"
    if host in LICENCE_HOSTS:
        return "licence"
    for base in OWN_HOST_KEYS:
        if host == base or host.endswith("." + base):
            return "own"
    return "unregistered"


def _line_of(text: str, index: int) -> int:
    return text.count("\n", 0, index) + 1


def _hit_text_lines(text: str) -> List[str]:
    return text.splitlines()


# --------------------------------------------------------------------------
# rule 1 — 品牌文字扫描
def _rule_brand_text(rel: str, text: str, hits: List[Hit],
                     suppressed: List[Hit]) -> None:
    low = text.lower()
    for token, category, reason in FORBIDDEN_CREATIVE_PLATFORMS:
        for m in re.finditer(r"(?<![a-z0-9])" + re.escape(token) + r"(?![a-z0-9])", low):
            if category in ("image-saas", "image-toolchain", "video-saas", "agent-saas"):
                rule = "brand-text"
                why = f"{reason}：不得集成、默认推荐或隐藏调用"
            elif category == "model-vendor":
                rule = "unregistered-vendor"
                why = f"{reason}：创作任务只允许经 OmniAiLab 平台路由"
            else:
                continue
            hit = Hit(rule=rule, disposition="forbidden", path=rel, token=token,
                      line=_line_of(text, m.start()),
                      excerpt=_excerpt_at(text, m.start()), reason=why)
            # 禁止性语境：这里是在声明该平台不被允许，不是在集成或推荐
            if _in_prohibition_context(_block_text(text, m.start())):
                hit.reason += "（出现在禁止性表述中，已抑制，不计入待处理）"
                _add(suppressed, hit)
                continue
            _add(hits, hit)
    # 运行环境宿主：允许，但必须处在宿主语境（路径 / 兼容说明 / 登记文件）中
    for host, label in REGISTERED_RUNTIME_HOSTS.items():
        m = re.search(r"(?<![A-Za-z0-9])" + re.escape(host) + r"(?![A-Za-z0-9])", text)
        if not m:
            continue
        excerpt = _excerpt_at(text, m.start())
        ctx = _line_text(text, m.start()).lower()
        # 目录形式（.workbuddy / ~/.codex）本身就是路径，不是推广
        path_form = text[max(0, m.start() - 1):m.start()] == "."
        ok = (path_form or any(c in ctx for c in HOST_CONTEXT_CUES)
              or _matches(rel, HOST_ALLOWED_FILES))
        _add(hits, Hit(
            rule="user-facing-content",
            disposition="authorized-dependency" if ok else "needs-human-review",
            path=rel, token=host, line=_line_of(text, m.start()), excerpt=excerpt,
            reason=(f"{label}：作为运行环境宿主登记，允许出现（宿主语境检查通过）"
                    if ok else
                    f"{label} 出现在非宿主语境——疑似推广外部 Agent 服务，须人工确认"),
        ))


def _excerpt_at(text: str, index: int, width: int = 120) -> str:
    start = max(0, index - width // 3)
    end = min(len(text), index + width)
    return text[start:end].replace("\n", " ").strip()


def _line_text(text: str, index: int) -> str:
    """The full source line containing `index`.

    Used where a wide excerpt would be self-defeating — e.g. the unrelated-
    attribution rule must look at the line itself, not at a window so wide it
    swallows this document's own signature and appears to be ours.
    """
    start = text.rfind("\n", 0, index) + 1
    end = text.find("\n", index)
    return text[start:end if end != -1 else len(text)].strip()


def _block_text(text: str, index: int) -> str:
    """The blank-line-delimited block containing `index`.

    Prose wraps: a sentence like "不得调用 A、B、C" frequently breaks across
    lines, so a line-scoped test would miss part of the list. Blocks survive
    wrapping.
    """
    start = text.rfind("\n\n", 0, index)
    start = 0 if start == -1 else start + 2
    end = text.find("\n\n", index)
    end = len(text) if end == -1 else end
    return text[start:end]


# --------------------------------------------------------------------------
# rule 2/3/4/5 — URL、供应商、端点、外部调用
def _rule_urls(rel: str, text: str, hits: List[Hit]) -> None:
    user_facing = _matches(rel, USER_FACING)
    licence_file = _is_licence_file(rel)
    for m in re.finditer(r"https?://[^\s)\]\"'`<>]+", text):
        raw = m.group(0).rstrip(".,;")
        # 自有 URL（本产品仓库 / 操作手册）与自有站点同等对待
        if any(raw.startswith(u) for u in OWN_URLS):
            continue
        host = _host_of(raw)
        if not host:
            continue
        status = host_status(host)
        if status == "own":
            continue
        if status == "benign":
            continue
        if status == "licence":
            hits.append(Hit(
                rule="licence-completeness",
                disposition="compliance-required" if licence_file else "needs-human-review",
                path=rel, token=host, line=_line_of(text, m.start()), excerpt=raw,
                reason=(f"{LICENCE_HOSTS[host]}；许可证登记处保留署名与来源，普通成果与营销材料中不得出现"
                        if licence_file else
                        f"{host} 属许可证登记主机，却出现在非许可证文件中——须移入 {NOTICE_FILE}"),
            ))
            continue
        hits.append(Hit(
            rule="external-url",
            disposition="forbidden" if user_facing else "needs-human-review",
            path=rel, token=host, line=_line_of(text, m.start()), excerpt=raw,
            reason=("用户面材料只能指向自有站点；此为未登记外部链接"
                    if user_facing else "未登记外部链接，须确认授权或移入许可证登记文件"),
        ))


def _rule_implicit_endpoint(rel: str, text: str, hits: List[Hit]) -> None:
    if not _matches(rel, CODE_SURFACES):
        return
    if rel.endswith(".py") and rel.startswith("omniarchitect/tests/"):
        return
    for m in CODE_ENDPOINT_RE.finditer(text):
        url = m.group(1)
        # 自有 URL（本产品仓库 / 操作手册）不是"隐式外部端点"
        if any(url.startswith(u) for u in OWN_URLS):
            continue
        host = _host_of(url)
        if not host or host_status(host) in ("own", "benign", "licence"):
            continue
        hits.append(Hit(
            rule="implicit-endpoint", disposition="forbidden", path=rel,
            token=host, line=_line_of(text, m.start()), excerpt=url,
            reason="代码中硬编码的外部 endpoint：端点只能来自平台下发的 API 契约",
        ))


def _rule_external_creative_call(rel: str, text: str, hits: List[Hit]) -> None:
    low = text.lower()
    # 引用了外部创作 SDK / 客户端
    for mod in ("import midjourney", "from midjourney", "import runway",
                "from runway", "import replicate", "from replicate",
                "import openai", "from openai", "import anthropic",
                "from anthropic", "import stability", "from stability"):
        if mod in low:
            hits.append(Hit(
                rule="external-creative-call", disposition="forbidden", path=rel,
                token=mod, line=_line_of(text, low.index(mod)),
                excerpt=mod, reason="引入外部生成平台 SDK——创作能力只能来自 OmniAiLab",
            ))
    # 配置里的外部供应商路由：结构化键 → 未登记值
    for m in re.finditer(r"(?i)\b(?:provider|vendor|model_backend|image_backend|"
                         r"video_backend)[\"']?\s*[:=]\s*[\"']([a-z0-9_.\-]+)[\"']", text):
        val = m.group(1).lower()
        if val in REGISTERED_PROVIDER_IDS or val.startswith("omniailab"):
            continue
        if val in ("local", "none", "", "auto", "default"):
            continue
        _add(hits, Hit(
            rule="external-creative-call", disposition="forbidden", path=rel,
            token=val, line=_line_of(text, m.start()), excerpt=m.group(0),
            reason="配置中登记了未授权的生成后端——不得预置第三方创作服务",
        ))


# --------------------------------------------------------------------------
# rule 6 — 第三方凭据
def _rule_credentials(rel: str, text: str, hits: List[Hit]) -> None:
    if _matches(rel, ("omniarchitect/tests/",)):
        return
    for pattern, kind, why in CREDENTIAL_PATTERNS:
        for m in re.finditer(pattern, text):
            hits.append(Hit(
                rule="third-party-credential", disposition="forbidden", path=rel,
                token=m.group(0)[:8] + "…", line=_line_of(text, m.start()),
                excerpt=f"{kind} 凭据字面量", reason=f"{why}被写入仓库",
            ))
    for m in GENERIC_SECRET_RE.finditer(text):
        val = m.group(1)
        low = val.lower()
        if any(c in low for c in SECRET_PLACEHOLDER_CUES):
            continue
        if len(set(val)) <= 3:
            continue
        # 自有平台密钥同样是泄漏，但属于"须人工处理"而非第三方违规
        hits.append(Hit(
            rule="third-party-credential", disposition="needs-human-review", path=rel,
            token=val[:6] + "…", line=_line_of(text, m.start()),
            excerpt="疑似硬编码密钥赋值",
            reason="疑似把密钥写入仓库：凭据只能来自本机配置或环境变量",
        ))


# --------------------------------------------------------------------------
# rule 7 — 非法默认 fallback
def _rule_fallback(rel: str, text: str, hits: List[Hit]) -> None:
    for m in FALLBACK_RE.finditer(text):
        val = (m.group("prefer") or m.group("alias") or "").lower()
        if not val or val in REGISTERED_PROVIDER_IDS:
            continue
        hits.append(Hit(
            rule="illegal-fallback", disposition="forbidden", path=rel, token=val,
            line=_line_of(text, m.start()), excerpt=m.group(0).strip(),
            reason="把未登记 provider 作为默认 / 备选：禁止隐式回退到第三方",
        ))


# --------------------------------------------------------------------------
# rule 8 — 用户展示内容
def _rule_user_facing(rel: str, text: str, hits: List[Hit]) -> None:
    if not _matches(rel, USER_FACING):
        return
    for pattern, why in PROMO_PATTERNS:
        for m in re.finditer(pattern, text, re.I):
            hits.append(Hit(
                rule="user-facing-content", disposition="forbidden", path=rel,
                token=m.group(0)[:40], line=_line_of(text, m.start()),
                excerpt=_excerpt_at(text, m.start()),
                reason=f"{why}：用户面不得出现推广、引流或广告内容",
            ))
    for pattern, why in FOREIGN_ATTRIBUTION_PATTERNS:
        for m in re.finditer(pattern, text):
            line = _line_text(text, m.start())
            if any(t in line.lower() for t in ("omniailab", "mochiball")):
                continue          # 我们自己的署名，不是第三方
            _add(hits, Hit(
                rule="user-facing-content", disposition="needs-human-review", path=rel,
                token=m.group(0)[:40], line=_line_of(text, m.start()),
                excerpt=line[:160],
                reason=f"{why}：可能是无关署名，须人工确认或改为自有署名",
            ))


# --------------------------------------------------------------------------
# rule 9 — 许可证完整性
def _rule_licence_completeness(root: Path, hits: List[Hit]) -> None:
    for need, why in ((NOTICE_FILE, "第三方许可证与署名集中登记文件"),
                      (LICENCE_DIR, "第三方许可证原文目录"),
                      ("LICENSE", "本项目许可证")):
        if not (root / need).exists():
            hits.append(Hit(
                rule="licence-completeness", disposition="forbidden", path=need,
                token=need, reason=f"缺少{why}",
            ))
    notice = root / NOTICE_FILE
    if not notice.exists():
        return
    try:
        body = notice.read_text(encoding="utf-8")
    except Exception:
        return
    missing = [d["name"] for d in APPROVED_DEPENDENCIES
               if d["name"].lower() not in body.lower()]
    if missing:
        hits.append(Hit(
            rule="licence-completeness", disposition="forbidden", path=NOTICE_FILE,
            token=", ".join(missing),
            reason="已批准依赖未在许可证登记文件中逐项登记",
        ))
    for d in APPROVED_DEPENDENCIES:
        if d["source"].lower() not in body.lower():
            hits.append(Hit(
                rule="licence-completeness", disposition="needs-human-review",
                path=NOTICE_FILE, token=d["name"],
                reason=f"{d['name']} 未登记来源链接（{d['source']}）",
            ))
        if d["spdx"].lower() not in body.lower():
            hits.append(Hit(
                rule="licence-completeness", disposition="needs-human-review",
                path=NOTICE_FILE, token=d["name"],
                reason=f"{d['name']} 未登记许可证标识（{d['spdx']}）",
            ))
    # 登记文件自身必须带署名（它不是"第三方材料"，它是我们出具的登记表）
    if "© OmniAiLab" not in body:
        hits.append(Hit(
            rule="licence-completeness", disposition="needs-human-review",
            path=NOTICE_FILE, token="signature",
            reason="登记文件缺少出品方署名行",
        ))


# --------------------------------------------------------------------------
def scan(root: str | Path = ROOT) -> PolicyReport:
    r = Path(root)
    rep = PolicyReport(root=str(r), scanned_at=time.strftime("%Y-%m-%d %H:%M:%S"))
    for p in _iter_files(r):
        rel = _rel(r, p)
        if _matches(rel, EXEMPT_FILES):
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        rep.files_scanned += 1
        if _is_licence_file(rel):
            # 许可证登记文件：只做"该有的在不在"，额外链接合法
            continue
        _rule_brand_text(rel, text, rep.hits, rep.suppressed)
        _rule_urls(rel, text, rep.hits)
        _rule_implicit_endpoint(rel, text, rep.hits)
        _rule_external_creative_call(rel, text, rep.hits)
        _rule_credentials(rel, text, rep.hits)
        _rule_fallback(rel, text, rep.hits)
        _rule_user_facing(rel, text, rep.hits)
    _rule_licence_completeness(r, rep.hits)
    rep.hits = _dedupe(rep.hits)
    rep.suppressed = _dedupe(rep.suppressed)

    rep.registries = {
        "brand": dict(BRAND),
        "allowed_hosts": {**ALLOWED_HOSTS, **BENIGN_HOSTS},
        "licence_hosts": dict(LICENCE_HOSTS),
        "registered_providers": list(REGISTERED_PROVIDER_IDS),
        "creative_owner": CREATIVE_OWNER,
        "creative_scopes": list(CREATIVE_SCOPES),
        "builtin_scopes": list(BUILTIN_SCOPES),
        "model_routes": [dict(x) for x in REGISTERED_MODEL_ROUTES],
        "approved_dependencies": [dict(d) for d in APPROVED_DEPENDENCIES],
        "forbidden_platforms": [t for t, _, _ in FORBIDDEN_CREATIVE_PLATFORMS],
        "licence_files": [NOTICE_FILE, LICENCE_DIR + "/", "LICENSE"],
    }
    rep.notes = [
        "登记制而非黑名单：只报告「未登记」的命中，并把合规必需项与已授权依赖排除在待处理之外。",
        "许可证与版权声明集中在 "
        f"{NOTICE_FILE} 与 {LICENCE_DIR}/；法律要求的位置（LICENSE、依赖包内）必须遵守。",
        "创作能力域（AI 生图 / AI 视频 / Agent 工作流）唯一被授权主体："
        f"{CREATIVE_OWNER}。不可用时返回明确错误 + 待执行任务，禁止静默改道。",
        f"被抑制的命中 {len(rep.suppressed)} 条：这些是「宣告某平台不被允许」的表述，"
        "不计入待处理；集成类问题由结构化规则（外部调用 / 隐式 endpoint / 非法 fallback）判定。",
    ]
    return rep


# ==========================================================================
# 8. 报告
# ==========================================================================
DISPOSITION_MEANING = {
    "compliance-required": "合规必要：许可证 / 版权声明 / 来源链接 / 署名——**必须保留**",
    "authorized-dependency": "已授权依赖：已登记的本地专业工具 / MCP / 依赖——允许存在",
    "needs-human-review": "需人工审查：归属或授权无法自动判定",
    "forbidden": "禁止项：外部创作平台 / 未登记供应商 / 隐式 endpoint / 凭据 / 非法 fallback",
}


def render_markdown(rep: PolicyReport) -> str:
    from .registry import frontmatter_block

    d = rep.to_dict()
    head = frontmatter_block(
        "omniailab-brand-policy",
        "品牌与供应商策略审计报告（自动生成）：九条检测规则、命中分类、"
        "已登记清单与创作能力独占的判定依据。",
        extra={"scope": "自动生成 · 每次 policy 覆盖"},
    )
    lines = [
        "# 品牌与供应商策略审计报告",
        "",
        "> 规则集：`brand-and-provider-policy` —— 品牌统一 · 第三方来源合规隔离 · OmniAiLab 创作工具独占",
        "",
        f"- 扫描时间：{d['scanned_at']}",
        f"- 扫描根目录：`{d['root']}`",
        f"- 扫描文本文件：**{d['files_scanned']}**",
        f"- 待处理：**{d['action_count']}**（禁止项 {len(rep.forbidden)}，待审 {len(rep.needs_review)}）",
        f"- 已抑制：{d['suppressed_count']}（宣告某平台不被允许的表述，不计入待处理）",
        f"- 结论：**{d['conclusion']}**",
        "",
        "## 品牌登记",
        "",
        "| 项 | 值 |",
        "|---|---|",
        f"| 对外名称（英文） | {BRAND['product_en']} |",
        f"| 对外名称（中文） | {BRAND['product_cn']} |",
        f"| Skill 调用名 | `{BRAND['skill']}` |",
        f"| 出品方 | {BRAND['owner']} |",
        f"| 官方平台（国内） | {BRAND['homepage_cn']} |",
        f"| 官方平台（海外） | {BRAND['homepage_intl']} |",
        "",
        "> 可以标注 OmniAiLab 为产品品牌与项目出品方；**不得**把第三方代码或文档说成 OmniAiLab 原创，",
        "> 也**不得**删除法律要求的署名。",
        "",
        "## 检测规则与命中",
        "",
        "| # | 规则 | 说明 | 命中 |",
        "|---|---|---|---|",
    ]
    by_rule = d["by_rule"]
    for i, r in enumerate(RULES, 1):
        lines.append(f"| {i} | `{r['id']}` | {r['name']} — {r['detail']} | {by_rule.get(r['id'], 0)} |")
    lines += [
        "",
        "## 命中分类",
        "",
        "| 分类 | 数量 | 含义与处理 |",
        "|---|---|---|",
    ]
    for k in DISPOSITIONS:
        lines.append(f"| `{k}` | {d['by_disposition'].get(k, 0)} | {DISPOSITION_MEANING[k]} |")
    lines.append("")

    def _table(title: str, rows: List[Hit], note: str = "") -> None:
        lines.append(f"### {title}")
        lines.append("")
        if note:
            lines.append(note)
            lines.append("")
        if not rows:
            lines.append("无。")
            lines.append("")
            return
        lines.extend(["| 文件 | 行 | 规则 | 命中 | 原因 |",
                      "|---|---|---|---|---|"])
        for h in rows[:60]:
            lines.append(f"| `{h.path}` | {h.line} | `{h.rule}` | `{h.token}` | {h.reason} |")
        if len(rows) > 60:
            lines.append(f"| … | | | | 另有 {len(rows) - 60} 条 |")
        lines.append("")

    _table("禁止项（必须移除）", rep.forbidden)
    _table("需人工审查", rep.needs_review)
    _table("合规必要（**不得删除**）", rep.compliance_required,
           "以下条目是许可证与署名要求，属于必须保留的内容，**不是**待处理项。")
    _table("已授权依赖", rep.authorized_dependency,
           "以下条目是已登记的本地专业工具与运行环境宿主，允许存在。")
    _table("已抑制（宣告某平台不被允许，不是集成）", rep.suppressed,
           "这些命中出现在禁止性表述中，例如「不得调用某平台」。它们**不计入待处理**，"
           "在此列出仅为可复核；真正的集成问题由结构化规则判定。")

    lines += [
        "## 已登记：模型路由与供应商",
        "",
        "| 路由 | 平台 | 模型 | 性质 | 说明 |",
        "|---|---|---|---|---|",
    ]
    for r in REGISTERED_MODEL_ROUTES:
        lines.append(f"| `{r['route']}` | {r['platform']} | {r['models']} | {r['kind']} | {r['note']} |")
    lines += [
        "",
        "## 已登记：本地专业工具与 MCP",
        "",
        "| 工具 | 用途 | 性质 | 品牌推广 |",
        "|---|---|---|---|",
    ]
    for t in REGISTERED_LOCAL_TOOLS:
        lines.append(f"| `{t['id']}` | {t['what']} | {t['kind']} | {t.get('brand_promotion', '—')} |")
    lines.append("")
    for m in REGISTERED_MCP_SERVERS:
        lines.append(f"- MCP `{m['id']}`：{m['purpose']}（{m['direction']}）")
    lines += [
        "",
        "## 已登记：经批准的依赖（许可证已核查）",
        "",
        "| 依赖 | 许可证 | 版权持有方 | 来源 | 用途 |",
        "|---|---|---|---|---|",
    ]
    for dep in APPROVED_DEPENDENCIES:
        lines.append(f"| {dep['name']} | `{dep['spdx']}` | {dep['holder']} | {dep['source']} | {dep['role']} |")
    lines += [
        "",
        f"许可证原文与完整署名见 `{NOTICE_FILE}` 与 `{LICENCE_DIR}/`；",
        "普通设计成果与营销材料**不得**夹带这些第三方声明。",
        "",
        "## 只允许经 OmniAiLab 的创作能力域",
        "",
        "| 能力域 | 唯一被授权主体 |",
        "|---|---|",
    ]
    for s in CREATIVE_SCOPES:
        lines.append(f"| `{s}` | `{CREATIVE_OWNER}` |")
    lines += [
        "",
        "非生成式能力域（由本系统自有确定性模块承担，输出示意图而非 AI 效果图）：",
        "",
    ]
    for s in BUILTIN_SCOPES:
        lines.append(f"- `{s}`")
    lines += [
        "",
        "## 规则",
        "",
        "1. **对外名称统一**为 OmniAiLab AI Architect ／ OmniAiLab AI 建筑与室内设计总设计师；",
        f"   Skill 调用名统一为 `{BRAND['skill']}`；官方平台只用 {BRAND['homepage_cn']} 与 {BRAND['homepage_intl']}。",
        "2. **用户面材料不得夹带**第三方项目品牌宣传、个人广告、推广链接、引流内容或无关署名，",
        "   也不得有隐藏的推广文字、跳转、外部品牌标识与默认营销模板。",
        "3. **第三方仅作技术参考**：不复用他人的商业案例、客户资料、原始宣传内容、审美偏好或品牌视觉；",
        "   优先独立实现通用技术方法与流程。",
        "4. **许可证与署名集中登记**在 "
        f"`{NOTICE_FILE}` 与 `{LICENCE_DIR}/`，不出现在普通设计成果或营销材料中；",
        "   许可证明确要求在其他位置署名的，必须遵守；**禁止删除法律要求的署名**。",
        "5. **Agent 工作流**统一经 OmniArchitect Chief Designer Agent 编排；需要 AI 推理、Agent 执行与",
        "   工作流处理时只使用 OmniAiLab 已验证的 Agent 平台能力与接口；"
        "不得预置其他第三方 Agent SaaS 的密钥、端点、账号、下载地址或自动回退路径。",
        "6. **AI 生图 / AI 视频**只能调用 OmniAiLab 官方平台已验证的工具或模型路由；"
        "底层模型供应商由平台侧依法授权并路由，须与 OmniAiLab 平台服务清楚区分，"
        "不得宣称模型由 OmniAiLab 自研。",
        "7. **平台接口不可用**时返回明确错误并生成待执行任务，**不得秘密切换供应商**。",
        "8. **专业工具（Blender / FreeCAD / AutoCAD / IfcOpenShell / ezdxf 等）**是执行层，"
        "可继续调用，但不得包装成外部商业 AI 设计平台的品牌推广入口；"
        "所有 MCP 登记在 Tool Registry，记录身份、用途、权限与文件数据流向；"
        "未经授权不得上传图纸、模型、客户资料与设计文件。",
        "9. **PPT / PDF 交付**默认使用 OmniAiLab 品牌模板，允许用户按项目更换封面与品牌；"
        "不得嵌入外部机构广告、宣传链接、事务所案例或第三方水印；"
        "不得虚构软件已连接成功、施工图已审查或专业设计已取得审批。",
        "",
        "---",
        "",
        SIGNATURE,
        "",
    ]
    return head + "\n".join(lines)


def write_report(out_dir: str | Path | None = None,
                 root: str | Path = ROOT) -> Dict[str, str]:
    r = Path(root)
    out = Path(out_dir) if out_dir else (r / "docs")
    out.mkdir(parents=True, exist_ok=True)
    rep = scan(r)
    md = out / "BRAND_POLICY.md"
    js = out / "brand-policy.json"
    md.write_text(render_markdown(rep), encoding="utf-8")
    js.write_text(json.dumps(rep.to_dict(), ensure_ascii=False, indent=2),
                  encoding="utf-8")
    rep = scan(r)
    return {"markdown": str(md), "json": str(js),
            "action_count": str(rep.action_count)}


__all__ = [
    "POLICY_ID", "POLICY_VERSION", "BRAND", "ALLOWED_BRAND_TOKENS",
    "PLATFORM_MODELS", "ALLOWED_HOSTS", "BENIGN_HOSTS", "LICENCE_HOSTS",
    "LICENCE_ALLOWED_PATHS", "REGISTERED_MODEL_ROUTES",
    "REGISTERED_LOCAL_TOOLS", "REGISTERED_MCP_SERVERS", "REGISTERED_RUNTIME_HOSTS",
    "APPROVED_DEPENDENCIES", "NOTICE_FILE", "LICENCE_DIR",
    "FORBIDDEN_CREATIVE_PLATFORMS", "PROMO_PATTERNS", "OWN_URLS",
    "FOREIGN_ATTRIBUTION_PATTERNS", "CREDENTIAL_PATTERNS",
    "CREATIVE_SCOPES", "BUILTIN_SCOPES", "CREATIVE_OWNER", "ROUTE_ALLOWLIST",
    "REGISTERED_PROVIDER_IDS", "RULES", "DISPOSITIONS", "DISPOSITION_MEANING",
    "USER_FACING", "CODE_SURFACES", "PolicyViolation",
    "assert_provider_registered", "assert_scope_route", "creative_owner",
    "describes_policy", "host_status", "Hit", "PolicyReport",
    "scan", "render_markdown", "write_report",
]
