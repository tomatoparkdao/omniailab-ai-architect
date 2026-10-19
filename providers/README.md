---
name: omniailab-providers-readme
description: OmniAiLab 平台连接说明：API 契约填写模板、凭据放置位置、三步接入流程，以及创作能力独占的硬规则。
version: 1.10.0
author: OmniAiLab
developer: Mochiball
agent_created: true
开源仓库: https://github.com/tomatoparkdao/omniailab-ai-architect
操作手册: https://zcn03zgas1zl.feishu.cn/wiki/K1IWwPuBDiQXufkS76Yc3EMPnTd
---

# OmniAiLab 平台连接

本目录存放**平台连接所需的本地文件**。它不属于 Python 包，只是本机/本项目的连接配置位置。

| 文件 | 用途 | 是否入库 |
|---|---|---|
| `omniailab.api.example.json` | API 契约填写模板（含 `FILL_ME` 占位符，**不可直接用**） | 入库 |
| `omniailab.api.json` | 真实 API 契约：`base_url` / `auth` / `endpoints` / `models` | 按需，不含密钥 |
| `omniailab.models.json` | 画布模型声明（推荐 OmniP / image2.5 与选择规则） | 见包内同名文件 |
| `../omniailab.config.json` | 本机凭据与工作区（`api_key`、`workspace`） | **不入库**（已 gitignore） |

## 三步接入

```bat
:: 1) 复制模板并填入平台下发的真实值
copy providers\omniailab.api.example.json providers\omniailab.api.json

:: 2) 写入凭据（不要写进契约文件）
::    omniailab.config.json -> { "api_key": "...", "workspace": "..." }
::    或设置环境变量 OMNIAILAB_API_KEY

:: 3) 验证
python -m omniarchitect providers
python -m omniarchitect concept-render --project <项目> --submit --authorize
```

## 硬规则

1. **不猜**。端点、参数名、鉴权头与模型名只能来自平台下发的契约；契约缺字段或仍含
   `FILL_ME` 占位符时，provider 一律 `NOT_CONFIGURED`，不发请求。
2. **不伪造**。平台未连接时只产出任务包（提示词 / 参考图 / 机位 / 模型建议 / 回填位置），
   逐条标注 `awaiting_platform`，绝不写占位图片。
3. **不越权**。向平台提交生成属 **L3 联网**操作，必须显式授权
   （`--submit --authorize`）；未授权时停在授权点。
4. **不当作尺寸依据**。画布产出的一切图像均为表现材料，`authoritative = false`。
5. **不改道（v1.3）**。生成式创作能力域（AI 生图 / AI 视频 / Agent 工作流）的唯一被授权
   主体是 OmniAiLab。不得集成、默认推荐或隐藏调用 Midjourney / Leonardo / Krea /
   Higgsfield / Runway / Pika / Sora 等第三方平台及其独立 API，也不得预置其密钥、端点、
   账号、下载地址或自动回退路径。平台不可用时**返回明确错误 + 生成待执行任务**，
   **不得秘密切换供应商**。
6. **自有模块不冒称生成式**。本地确定性栅格化只声明 `schematic_diagram`（输出示意图，
   非写实渲染），不得应答 `image_generation` 等生成式能力域。
7. **平台服务与模型提供方分开**。平台内部依法授权并已配置的底层模型供应商由平台侧路由；
   已登记路由 `omniailab.canvas`（OmniP / image2.5）。**不得**宣称这些模型由 OmniAiLab 自研。

自查：

```bash
python -m omniarchitect providers    # 创作独占状态 + 待执行任务
python -m omniarchitect policy       # 品牌与供应商策略（九条规则）
```

第三方许可证、版权声明与来源链接集中登记在仓库根目录 `THIRD_PARTY_NOTICES.md` 与
`LICENSES/`；本目录不放许可证信息。

## 契约与推荐模型的关系

`omniarchitect/providers/omniailab.models.json` 声明了画布上的推荐模型与取向规则。
平台连接成功后，本系统会把该声明与契约的 `models` 列表交叉校验：

- 推荐模型在契约中 → 按其取向使用，并把声明标记为 `verified_against_contract`；
- 推荐模型不在契约中 → **以契约为准**，改用契约中的模型，并在结果里记录偏差说明。

> © OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
