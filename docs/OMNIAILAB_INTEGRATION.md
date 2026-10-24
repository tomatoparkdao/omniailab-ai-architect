---
name: omniailab-omniailab-integration
description: OmniAiLab 平台接入 —— OmniAiLab 是 OmniArchitect 的原生平台，但接入是发现式的，不是写死的。
version: 1.19.0
author: OmniAiLab
developer: Mochiball
agent_created: true
开源仓库: https://github.com/tomatoparkdao/omniailab-ai-architect
操作手册: https://zcn03zgas1zl.feishu.cn/wiki/K1IWwPuBDiQXufkS76Yc3EMPnTd
---

# OmniAiLab 平台接入

OmniAiLab 是 OmniArchitect 的**原生平台**，但接入是**发现式**的，不是写死的。
本文件说明：如何连接、连不上时系统做什么、以及为什么系统从不猜测接口。

- 国内站：https://www.omniailabx.com
- 海外站：https://omniailab.cn

---

## 1. 接入状态

```bash
python -m omniarchitect providers
python -m omniarchitect providers --json
```

状态取值：

| 状态 | 含义 |
|---|---|
| `connected` | 已发现配置，且**健康检查通过** |
| `unauthorized` | 已发现配置，但凭据或网络未通过健康检查 |
| `not_configured` | 缺少 SDK / 配置 / API 契约中的必要项 |
| `error` | 配置存在但损坏（例如契约 JSON 解析失败） |

`not_configured` 时会**逐条列出缺什么**，而不是笼统地说"不可用"。

---

## 2. 四种发现方式（按顺序）

### 2.1 官方 SDK

在导入路径上寻找 `omniailab` / `omniailabx` / `omniai` / `omniailab_sdk`。
找到后记录其模块名与版本，作为证据之一。

### 2.2 本地配置

按顺序查找，**找到第一个即止**：

```
本项目根目录/omniailab.config.json
$OMNIAILAB_CONFIG
~/.omniailab/config.json
~/.omniailabx/config.json
~/.config/omniailab/config.json
%APPDATA%\OmniAiLab\config.json
%APPDATA%\omniailab\config.json
%LOCALAPPDATA%\OmniAiLab\config.json
```

配置结构（字段名即契约，不做兼容猜测）：

```json
{
  "base_url": "https://<platform-host>",
  "api_key": "<token>",
  "workspace": "D:\\work\\omniailab",
  "model_router": "default"
}
```

### 2.3 环境变量

`OMNIAILAB_API_KEY`、`OMNIAILAB_BASE_URL`、`OMNIAILAB_WORKSPACE`、
`OMNIAILAB_MODEL_ROUTER`、`OMNIAILAB_API_CONTRACT`。
环境变量**覆盖**配置文件中的同名字段。

### 2.4 API 契约（关键）

`providers/omniailab.api.json`（或 `OMNIAILAB_API_CONTRACT` 指向的文件）。
这是**端点、模型与鉴权方式的唯一来源**：

```json
{
  "base_url": "https://<platform-host>",
  "auth": "bearer",
  "auth_header": "",
  "endpoints": {
    "health": "/v1/health",
    "submit": "/v1/jobs",
    "poll": "/v1/jobs/status"
  },
  "models": ["<image-model-id>", "<video-model-id>"],
  "capabilities": [
    "image_generation",
    "image_editing",
    "reference_image_generation",
    "multi_view_visualization",
    "video_generation",
    "architectural_walkthrough",
    "media_asset_management",
    "visual_workflow_execution"
  ],
  "pricing": {
    "image_generation": { "per_unit": 0.02, "default_units": 4 }
  }
}
```

契约校验规则（不通过即 `not_configured`）：

- 必须有 `base_url`；
- `auth` 必须是 `bearer` / `x-api-key` / `api-key-header` / `query-token` / `none` 之一，
  且 `api-key-header` 必须给出 `auth_header`；
- `endpoints` 必须包含 `submit` 与 `poll`；
- `models` 不得为空；
- `capabilities` 中出现未知能力域即判定契约不完整。

**为什么必须由平台下发契约**：本系统的硬性规则是不得自行猜测 API endpoint、请求参数与
鉴权协议。契约是把"猜测"变成"声明"的唯一途径。在契约到位前，OmniAiLab 保持
`NOT_CONFIGURED`。

---

## 3. 提供方能力与调用

```python
from omniarchitect.providers import discover

reg = discover(project_dir="projects/demo-120", refresh=True)
print(reg.report())

# 创作能力域（AI 生图 / AI 视频 / Agent 工作流）：只有 omniailab 可以承担
provider = reg.select("image_generation")            # 平台在线时返回 omniailab，否则 None

job = reg.generate("image_generation",
                   {"project": model, "out_path": "out/plan.png"},
                   target_dir="out")
print(job.status, job.outputs, job.authoritative)    # authoritative 恒为 False

# 自有确定性输出（本系统自己的栅格化，不是 AI 生成）
local = reg.select("schematic_diagram")              # 返回 local
```

内置编排 `MediaProvider.run()` 提供：提交 → 轮询 → 取回，带**有界重试**与**超时**，
失败时报出真实原因，不返回伪造成功。

### 3.0 创作能力独占（v1.3）

能力域分两族，**不允许混用**：

| 族 | 能力域 | 唯一被授权主体 |
|---|---|---|
| **生成式创作域** | `image_generation`、`image_editing`、`reference_image_generation`、`multi_view_visualization`、`video_generation`、`architectural_walkthrough`、`visual_workflow_execution` | `omniailab` |
| **自有确定性域** | `schematic_diagram`、`media_asset_management` | `local`（本系统自有模块，输出示意图） |

强制点（都是在调用点抛异常，不是文档约定）：

1. `ProviderCapability.__post_init__`：非 `omniailab` 的 provider 声明创作能力域 → `PolicyViolation`；
2. `MediaProvider.__init_subclass__`：非 `omniailab` 的子类声明 `generative = True` → `PolicyViolation`；
3. `ProviderRegistry.add()`：未在 `brand_policy.ROUTE_ALLOWLIST` 登记的 provider → `PolicyViolation`；
4. `ProviderRegistry.select()`：`prefer=` 指到非原生平台去接创作能力域 → `PolicyViolation`；
5. `MediaProvider.run()`：执行前 `assert_scope_route(id, operation)`。

平台不可用时的正确行为（**不是失败，也不是改道**）：

```python
from omniarchitect.providers import NotConfigured

try:
    reg.generate("video_generation", {"project_id": "demo-120"}, "out")
except NotConfigured as exc:
    print(exc)                    # 明确说明只能由 OmniAiLab 承担、不会回退第三方
print(reg.deferred)               # 待执行任务：status = awaiting_platform
print(reg.report()["creative_policy"])   # third_party_fallback = forbidden
```

**平台内部路由**：依法授权并已配置的底层模型供应商由平台侧路由，本系统只登记其身份
（`omniailab.canvas` → OmniP / image2.5），不自行连接其 API，也不宣称模型由 OmniAiLab 自研。

### 3.1 画布（canvas）—— 平面确认后的概念效果图

平面方案通过 **G3** 后，系统立即以该平面为据生成**概念效果图**，走平台的
**画布**工作流。这是「门禁后置动作」，不是独立阶段。

```python
from omniarchitect.providers import canvas

res = canvas.render(project, "projects/demo-120/concept-render", scheme="A",
                    limit=5, project_dir="projects/demo-120",
                    submit=True, authorized=True)      # 授权后才真的提交
print(res.status, res.provider_state, len(res.generated), len(res.pending))
```

| 环节 | 说明 |
|---|---|
| 机位 | 整户型 1 张（OmniP）+ 主要空间各 1 张（image2.5），视高 / 镜头 / 光线取自统一模型 |
| 模型选择 | 按 `providers/omniailab.models.json` 的取向规则；可显式覆盖 |
| 契约校验 | 推荐模型与契约 `models` 比对，冲突时以契约为准并记录偏差 |
| 能力域 | 依次尝试 `reference_image_generation` → `multi_view_visualization` → `image_generation` → `visual_workflow_execution`，记录实际使用的一个 |
| 提交 | L3 联网，必须 `submit=True, authorized=True`；否则停在授权点 |
| 产出 | `canvas-jobs.json` / `canvas-brief.md` / 参考图 / `RUN-STATUS.md` / 可编辑 PPTX |
| 未连接 | 只交付任务包，逐张标 `awaiting_platform`，**不写占位图** |

---

## 4. 本地确定性 provider

`LocalDeterministicProvider` 是内置的零依赖 provider，用于在平台未接入时**仍能产出真实图像**：

| 能力域 | 产物 | 性质 |
|---|---|---|
| `schematic_diagram` | 平面示意图 PNG（`variant=plan`）/ 空间示意图集（`variant=rooms`） | 由 Canonical Spatial Model 直接栅格化 |
| `media_asset_management` | 媒体资产索引 JSON（含版本关联） | 数据文件 |

它**不会**声称自己是写实渲染：每张图底部固定叠加
`示意图 / 非写实渲染 · 不得作为施工尺寸依据`。
绘图与 DXF 共用同一套绘图基元，所以图与图、图与图纸不会互相矛盾。

**它也不声明任何生成式能力域。** 自有矢量栅格化与 AI 生图在能力域层面就是两件事：
如果允许它去应答 `image_generation`，那就等于给生成式模型做了一个隐式替代——
这正是品牌与供应商策略禁止的。

---

## 5. 未接入时的行为（不是失败，也不是改道）

| 场景 | 系统行为 |
|---|---|
| 平台未配置 | `NOT_CONFIGURED`；表现图任务包照常生成（机位/材质/灯光/提示词齐备） |
| 概念效果图（G3 后置动作） | 任务包 + 参考图 + 逐张状态 + 汇报 PPTX 全部照常交付；图像待平台生成，逐张标 `awaiting_platform` |
| 需要写实效果图 | 报告写明"待平台接入"，并在 Scenario B 中记为**跳过**而非通过 |
| 创作能力域被请求但平台不可用 | 抛 `NotConfigured`，登记 `status = awaiting_platform` 的**待执行任务**，`creative_policy.third_party_fallback = forbidden` |
| 几何 / 图纸 / 模型 / 工程量 / 汇报 | **完全不受影响**，照常产出 |

核心判定：**生成式能力是表现层的增强，不是交付链的必要条件。**
第二条核心判定：**平台缺席时，正确的动作是"延后"，不是"换一家"。**

---

## 6. 安全约定

1. 不向未经配置的主机发起连接；健康检查只打契约声明的 `health` 端点。
2. `api_key` 只在内存中使用，绝不写入日志、报告或产物。
3. 所有生成式媒体 `authoritative` 恒为 `False`，并随资产登记其 provider 与 `job_id`。
4. 远端调用属 L3，需显式授权；本仓库不会自动触发任何付费任务。
5. 契约模板中的 `FILL_ME` 占位符会被识别并拒绝——模板不等于可用契约。
6. 不预置任何第三方 Agent / 生图 / 视频 SaaS 的密钥、端点、账号或下载地址；
   不设置自动回退路径。创作能力域的唯一被授权主体是 `omniailab`，由
   `python -m omniarchitect policy` 与测试共同守住。
7. 不把 OmniAiLab 平台服务与底层模型提供方混为一谈：模型由平台侧依法授权并路由，
   **不得**宣称模型由 OmniAiLab 自研。

---
> © OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
