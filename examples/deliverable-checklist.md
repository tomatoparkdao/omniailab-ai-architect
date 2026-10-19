---
name: omniailab-examples-deliverable-checklist
description: 交付清单 —— 逐阶段产物清单与收尾自查：该拿的东西拿齐了吗。
version: 1.9.0
author: OmniAiLab
developer: Mochiball
agent_created: true
开源仓库: https://github.com/tomatoparkdao/omniailab-ai-architect
操作手册: https://zcn03zgas1zl.feishu.cn/wiki/K1IWwPuBDiQXufkS76Yc3EMPnTd
---

# 交付清单（收尾自查）

全流程跑完，你应该拿到下面这些。**缺哪一项就问它，不要自己以为"应该有"。**

## 一、逐阶段产物

| 阶段 | 应拿到 | 形态 |
|---|---|---|
| S1 任务书 | 设计任务书、原始条件报告 | `.md` / `.json` |
| S2 概念 | 概念方案、风格意向板 | `.md` / 图片 |
| S3 平面 | 两至三套平面方案 + 对比分析 | `.dxf` / `.json` / `.md` |
| S3 门禁后 | 概念效果图 + 画布任务包 + 汇报 | `.png` 任务包 / `canvas-jobs.json` / `.pptx` |
| S4 初步设计 | 初步设计图纸、材料与灯光方案 | `.dxf` / `.md` |
| S5 表现 | 3D 模型、空间示意图、漫游机位 | `.obj` / `.png` / `.json` |
| S6 定稿 | 确认版方案、深化依据 | `.md` / `.json` |
| S7 施工图深化 | 施工深度 DXF、IFC 投影数据 | `.dxf` / `.json` |
| S8 交付 | 物料表、工程量清单、交付包索引 | `.json` / `.md` |

## 二、五件"必须存在"的东西

1. **修订号**：每份产物文件名都带 `-r<修订号>`；改过几何的修订号必须递增。
2. **变更影响记录**：走过 `change` 就必须有影响面报告与门禁重开清单。
3. **免责与边界页**：每份汇报 PPTX 必须含一页写明结构 / 消防 / 无障碍 / 机电 / 法规的边界。
4. **未闭环项清单**：交付包里必须列出还没确认、还缺资料、还待复核的事项。
5. **署名**：每份 Markdown 的开头 front-matter 与结尾署名行齐全。

## 三、四条不许出现的说法

| 不许出现 | 因为 |
|---|---|
| "已通过施工图审查" | 审查不在本系统结论范围内，须持证专业人员复核签署 |
| "DWG 已导出" | 本系统只写 DXF；DXF ≠ DWG |
| "参数化 BIM 模型已完成" | 无 IfcOpenShell 时只有网格 + IFC 投影数据，网格 ≠ 参数化 BIM |
| "效果图尺寸按此为准" | 生成式图像永远 `authoritative = false`，不得作为尺寸依据 |

## 四、两条命令自查

```bash
python -m omniarchitect status --project <项目目录>     # 阶段状态与未闭环项
python -m omniarchitect audit                           # 署名 / 隐私 / 外链 / 许可，必须 0
```

---
> © OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
