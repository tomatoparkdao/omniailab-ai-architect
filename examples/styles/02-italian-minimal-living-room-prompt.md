---
name: omniailab-style-prompt-interior-render
description: 提示词任务包 —— 室内效果图（`interior-render`）：中英双语分层结构、几何保持规则与产出后校核清单；风格 意式极简（Italian Minimal），一致性指纹 sp-22db636aa74d。
version: 1.17.0
author: OmniAiLab
developer: Mochiball
agent_created: true
开源仓库: https://github.com/tomatoparkdao/omniailab-ai-architect
操作手册: https://zcn03zgas1zl.feishu.cn/wiki/K1IWwPuBDiQXufkS76Yc3EMPnTd
---

# 提示词任务包 —— 室内效果图

- 目标类型：`interior-render`（interior rendering）
- 建议阶段：S4
- 风格：意式极简（Italian Minimal）
- 一致性指纹：`sp-22db636aa74d`
- 模型修订：r3
- 风格已锁定（门禁确认），提示词以锁定结果为准。

**画面重点**：室内空间完整视野：界面、家具、材质、光线与透视关系
**机位倾向**：等效 24–28mm，视高 1400–1600mm，两点透视

## 正向提示词（中文）

```text
【风格】意式极简（Italian Minimal）。开敞连续的起居空间，一面整幅石材背景墙作为视觉锚点，天花为窄边暗槽平顶
【空间（取自已确认模型，不得改动）】空间：客厅；开间 × 进深：4200 × 6000 mm；净高：2800 mm；朝向与采光：南向，主采光面 3.6m 落地窗；门窗与洞口：阳台推拉门 2400×2400，南墙偏东
【材质】暖灰米色哑光岩板地面与背景墙对纹拼接，暖色胡桃木饰面通高墙板，台面加厚并做 45° 斜切，拉丝香槟金属细线收口
【光线】洗墙射灯自上而下强调石材纹理，台面下暗藏线性灯带，光色偏暖、暗部保留层次
【家具】低矮方正的大型软体沙发，皮革与织物混搭，柜体齐平配细长金属拉手
【机位】一点透视，镜头略低于人眼，28–40mm
【氛围】温暖、克制而有质感层级，材料本身构成视觉重心
【客户功能需求】三人布艺沙发，坐深 900；电视背景墙只做整幅石材
【关键词】意式极简，整幅岩板，木饰面，斜切台面，少缝，暖色石材
【画面目标】室内空间完整视野：界面、家具、材质、光线与透视关系
```

## Positive prompt (English)

```text
[style] Italian Minimal. An open continuous living volume with a single full-slab stone feature wall as the visual anchor, flat ceiling with narrow recessed shadow gap
[space, taken from the approved model — do not alter] space: 客厅; width × depth: 4200 × 6000 mm; clear ceiling height: 2800 mm; orientation and daylight: 南向，主采光面 3.6m 落地窗; openings: 阳台推拉门 2400×2400，南墙偏东
[materials] Warm greige matte sintered stone floor and book-matched feature wall, warm walnut full-height veneer panelling, thickened countertop with 45° mitred edge, brushed champagne metal reveals
[light] Wall-washing spotlights grazing the stone texture from above, hidden linear LED under the counter, warm tone with retained shadow detail
[furniture] Large low square sofa mixing leather and fabric, flush cabinetry with slim metal pulls
[camera] 一点透视，镜头略低于人眼，28–40mm
[atmosphere] Warm, restrained, layered in material rather than object
[client requirements] 三人布艺沙发，坐深 900; 电视背景墙只做整幅石材
[keywords] italian minimal, full slab stone, wood veneer, mitred edge, few seams, warm stone
[shot purpose] a full interior view: surfaces, furniture, materials, light and perspective
```

## 负向约束（中文）

- 不要高饱和与荧光色
- 不要仿石纹贴纸、塑料饰面与廉价复合板
- 不要露明管线与未经处理的水泥裸面
- 不要古典雕饰与繁复线脚
- 不要可见阳角压条与彩色收边条
- 改变墙体或门窗位置
- 改变房间比例与层高
- 添加不存在的结构构件
- 乱码文字与错字招牌
- 失真的人体比例
- 过度 HDR 与塑料感
- 与锁定风格冲突的材质
- 品牌 logo 与商标
- 水印与画面外文字

## Negative constraints (English)

- no saturated or fluorescent colours
- no faux-stone laminates, plastic finishes or cheap composite panels
- no exposed services or raw untreated concrete
- no classical ornament or applied mouldings
- no visible corner trims or coloured edge strips
- altered wall or window positions
- altered room proportions or ceiling height
- structural elements that do not exist
- garbled text or signage
- distorted human proportions
- over-processed HDR and plastic sheen
- materials conflicting with the locked style
- brand logos and trademarks
- watermarks or out-of-frame text

## 几何保持（必须遵守）

- 所有墙体、门窗洞口、梁柱的位置与尺寸保持与已确认模型一致。
- 房间的开间、进深与净高不得被调整以适配构图。
- 家具与固定件只能布置在模型允许的位置，不得穿过墙体或洞口。
- 保持大体量材质块的体量与位置不变，不改动背景墙所在墙面
- 保持石材整幅排版的对纹关系与缝位分布
- 保持天花暗槽位置与灯位网格，不新增叠级

## 产出后必须做的校核（不能跳过）

- [ ] 把生成结果与**已确认的统一空间模型**逐项比对：开间进深、墙体与门窗位置、层高。
- [ ] 把生成结果与**参考图**（已确认平面的确定性栅格化）比对空间关系是否成立。
- [ ] 多机位或多张产出之间比对：材质、色温、家具形态是否一致；不一致则以模型为准重出。
- [ ] 涉及结构、消防、无障碍、机电负荷与法规符合性的内容，必须由持证专业人员在项目所在地复核签署。
- [ ] 生成图像为非权威成果，**不得作为施工尺寸依据**。

---

> 提示词**不承载几何**。纯提示词无法保证精确的几何一致性——必须结合已确认模型、参考图与生成结果逐项校核。生成图像为非权威成果，不得作为施工尺寸依据。

---
> © OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
