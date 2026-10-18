---
name: omniailab-licences-index
description: LICENSES 目录索引 —— 第三方许可证原文与署名的归档位置；与 THIRD_PARTY_NOTICES.md 配套，二者构成本仓唯一的第三方声明落点。
scope: 许可证原文归档（唯一处）
version: 1.6.0
author: OmniAiLab
developer: Mochiball
agent_created: true
开源仓库: https://github.com/tomatoparkdao/omniailab-ai-architect
操作手册: https://zcn03zgas1zl.feishu.cn/wiki/K1IWwPuBDiQXufkS76Yc3EMPnTd
---

# LICENSES/ — 许可证原文归档

本目录存放需要履行的第三方许可证原文与版权声明。

## 现状

**本仓不打包、不分发任何第三方源码或二进制，也不含任何第三方作品内容，
因此当前不需要在本目录留存任何许可证原文。**

| 文件 | 性质 |
|---|---|
| `README.md` | 本目录索引（本仓自有文档） |

与本仓配合使用的第三方项目均为**可选**依赖或**用户自备**的宿主软件，
逐项登记在仓库根目录的 `THIRD_PARTY_NOTICES.md` 中，包含：

- 项目名
- 许可证标识（SPDX）
- 版权持有方
- 官方来源链接
- 在本系统中的用途，以及缺失时的自有降级路径

### 关于设计风格系统

`knowledge/styles/` 的 47 条风格记录**全部为本项目独立原创撰写**，
不含任何第三方的提示词文本、案例描述、品牌名、宣传语或外部链接，
因此本目录无需为其保留任何许可证留档。详见 `THIRD_PARTY_NOTICES.md`
的「设计风格系统的内容来源（全部自有）」一节。

## 何时需要在本目录放文件

出现下列任一情况时，把对应项目的许可证全文放入本目录，
文件名使用 `<项目名>-<SPDX标识>.txt`（例如 `ezdxf-MIT.txt`）：

1. 本仓开始打包、镜像或分发某个第三方项目的代码或二进制；
2. 某个项目的许可证要求在特定位置附全文，而该位置不在其官方发布包内；
3. 引入了许可证要求"随附声明"的素材（字体、纹理、模型、数据）。

放置后必须在 `THIRD_PARTY_NOTICES.md` 中增加指向该文件的说明，
并运行 `python -m omniarchitect policy` 确认登记一致。

## 不得做的事

- **不得删除**任何法律要求的署名、版权声明与许可证文本；
- **不得**通过删去原作者信息、把第三方代码或文档宣称为 OmniAiLab 原创；
- **不得**把本目录或 `THIRD_PARTY_NOTICES.md` 的内容复制进普通设计成果、
  汇报 PPT / PDF、README、SKILL.md、提示词与用户界面。

---
> © OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
