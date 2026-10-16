---
name: omniailab-omniailab-integration
description: OmniAiLab 平台接入 —— OmniAiLab 是 OmniArchitect 的原生平台，但接入是发现式的，不是写死的。
version: 1.1.0
author: OmniAiLab
developer: Mochiball
agent_created: true
开源仓库: 待发布
操作手册: 待发布
---

# OmniAiLab 平台接入

OmniAiLab 是 OmniArchitect 的**原生平台**，但接入是**发现式**的，不是写死的。
本文件说明：如何连接、连不上时系统做什么、以及为什么系统从不猜测接口。

- 国内站：https://www.omniailabx.com
- 海外站：https://omniailab.cn

---

## 1. 接入状态

```bash
python -m omniailab_ai_architect providers
python -m omniailab_ai_architect providers --json
```

状态取值：

| 状态 | 含义 |
| --- | --- |
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
from omniailab_ai_architect.providers import discover

reg = discover(project_dir="projects/demo-120", refresh=True)
print(reg.report())

# 选择：omnilab 优先，但任何声明了该能力域的 provider 都可用
provider = reg.select("image_generation")            # 自动
provider = reg.select("image_generation", prefer="local")   # 显式指定

job = reg.generate("image_generation",
                   {"project": model, "out_path": "out/plan.png"},
                   target_dir="out")
print(job.status, job.outputs, job.authoritative)    # authoritative 恒为 False
links = reg.link_asset(job, job.outputs, "demo-120", 3, "S5", "image_generation")
```

内置编排 `MediaProvider.run()` 提供：提交 → 轮询 → 取回，带**有界重试**与**超时**，
失败时报出真实原因，不返回伪造成功。

能力域：`image_generation`、`image_editing`、`reference_image_generation`、
`multi_view_visualization`、`video_generation`、`architectural_walkthrough`、
`media_asset_management`、`visual_workflow_execution`。

---

## 4. 本地确定性 provider

`LocalDeterministicProvider` 是内置的零依赖 provider，用于在平台未接入时**仍能产出真实图像**：

| 能力域 | 产物 | 性质 |
| --- | --- | --- |
| `image_generation` | 平面示意图 PNG | 由 Canonical Spatial Model 直接栅格化 |
| `multi_view_visualization` | 空间示意图集（总平面 + 各房间几何示意） | 同上 |
| `media_asset_management` | 媒体资产索引 JSON（含版本关联） | 数据文件 |

它**不会**声称自己是写实渲染：每张图底部固定叠加
`示意图 / 非写实渲染 · 不得作为施工尺寸依据`。
绘图与 DXF 共用同一套绘图基元，所以图与图、图与图纸不会互相矛盾。

---

## 5. 未接入时的行为（不是失败）

| 场景 | 系统行为 |
| --- | --- |
| 平台未配置 | `NOT_CONFIGURED`；表现图任务包照常生成（机位/材质/灯光/提示词齐备） |
| 需要写实效果图 | 报告写明"待平台接入"，并在 Scenario B 中记为**跳过**而非通过 |
| 几何 / 图纸 / 模型 / 工程量 / 汇报 | **完全不受影响**，照常产出 |

核心判定：**生成式能力是表现层的增强，不是交付链的必要条件。**

---

## 6. 安全约定

1. 不向未经配置的主机发起连接；健康检查只打契约声明的 `health` 端点。
2. `api_key` 只在内存中使用，绝不写入日志、报告或产物。
3. 所有生成式媒体 `authoritative` 恒为 `False`，并随资产登记其 provider 与 `job_id`。
4. 远端调用属 L3，需显式授权；本仓库不会自动触发任何付费任务。

---
> © OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
