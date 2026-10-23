---
name: omniailab-style-integration
description: 风格系统在主流程中的位置 —— 它不再是独立工程，而是 omniailab-ai-architect 的内部专业模块：六个阶段介入点、内部调用方式，以及"为什么现在不会再漂移"。
version: 1.17.0
author: OmniAiLab
developer: Mochiball
agent_created: true
开源仓库: https://github.com/tomatoparkdao/omniailab-ai-architect
操作手册: https://zcn03zgas1zl.feishu.cn/wiki/K1IWwPuBDiQXufkS76Yc3EMPnTd
---

# 设计风格系统在主流程中的位置

> **风格系统不是第二个 Skill。** 它是 `omniailab-ai-architect` 内部的
> `omniarchitect/style/` 子包，与 `providers/`、`tools/`、`presentation/` 同级，
> 由主 Skill 直接发现和调用。没有独立安装、没有独立入口、没有独立仓库。

## 一、它原先为什么会分开，现在为什么合回来

风格系统原本是一个独立工程（Design Style Intelligence）。当时的理由是"风格库扩容节奏与主流程不同"。实际后果是**同一个规则有了两份实现**：

| 事项 | 分开时的状态 | 合并后 |
|---|---|---|
| 项目根与目录 | 自己推算 `parents[1]` | `omniarchitect.paths` |
| 平台探测与契约校验 | 自己读契约、自己判 `FILL_ME` | `omniarchitect.providers` |
| 署名与 front-matter | 自己的 `attribution.py` | `omniarchitect.registry` |
| 八阶段与门禁 | 导出一份快照再读 | `omniarchitect.stages`（同包，直接引用） |
| CLI 入口 | 自己的 `__main__` | 主 CLI 的 `style` 子命令 |

代价是真实发生过的：分开时手写的门禁措辞与阶段模型有 **4 处不一致**
（G2/G3/G5/G8）。那种漂移不报错，它一路飘到给业主的汇报里。

**合并后不再有第二份实现可以漂移** —— 比对变成同一进程内的对象引用，而不是两个文件之间的对照。

## 二、六个介入点

风格系统挂在六个阶段上。**S1 与 S6 不挂**：S1 是需求接单（还没有风格可选），
S6 是设计冻结（风格已锁定并随修订号追踪）。

| 阶段 | 风格系统做什么 | 产物 | 门禁 |
|---|---|---|---|
| **S2** 概念 | 三套方向不同的风格方案 → 业主指定 → **锁定** | `style-recommendation.md`、`style-lock-r*` | G2 |
| **S3** 平面 | 用锁定风格的空间原则逐条对照平面，冲突项给两条可选路径 | `style-space-check.md` | G3 |
| **S4** 初步设计 | 提取材料体系、色板、家具语汇、照明策略，并记录材料替换理由 | `style-material-spec.json` | G4 |
| **S5** 效果表现 | 编译中英双语结构化提示词；多机位共用一致性指纹；提交或延后 | `style-jobs.json`、`style-jobs-brief.md` | G5 |
| **S7** 施工深化 | 材料规格化；核对深化图是否偏离风格意图 | `style-construction-spec.md` | G7 |
| **S8** 交付汇报 | 生成风格对比数据供汇报使用 | `style-comparison.json` | G8 |

```bash
python -m omniarchitect style hooks              # 六条挂钩全文
python -m omniarchitect style hooks --stage S3    # 单看某一阶段
```

## 三、两条调用路径

### 路径 A：进程内（主流程内部使用）

```python
from omniarchitect.style import (
    recommend, RecommendRequest,     # S2 三套方案
    load_catalog,                    # 知识库检索
    compile_prompt, SpaceBrief,      # S4/S5 提示词
    submit, probe,                   # 唯一生成出口
    hook, gate_label,                # 阶段挂钩与门禁
)

req = RecommendRequest(space_type="住宅", area_m2=120, budget_tier="mid",
                       location="上海", preferences=["简洁", "温暖"])
options = recommend(req)             # 三个角色：稳妥 / 个性 / 混搭
```

### 路径 B：命令行（脚本、流水线、人工排查）

```bash
python -m omniarchitect style recommend --space-type 住宅 --area 120 --budget mid --out out
python -m omniarchitect style lock      --style modern-minimalism --out out --revision 1 --by 业主
python -m omniarchitect style space-check --style modern-minimalism --space 客厅 --ceiling 2300
python -m omniarchitect style materials --style modern-minimalism --out out
python -m omniarchitect style compile   --style modern-minimalism --target interior-render \
    --space 客厅 --width 4200 --depth 6000 --ceiling 2800 --locked --out out
python -m omniarchitect style intent    --style modern-minimalism --deviations "门套缝宽由 3mm 改为 10mm"
python -m omniarchitect style compare   --styles modern-minimalism,chinese-neo-classical
```

## 四、必须一致的地方 —— 由代码保证，不靠人工比对

| 约定 | 怎么保证 |
|---|---|
| 阶段编号与名称 | 直接读 `omniarchitect.stages.STAGES` |
| 门禁编号与名称 | 同上；`tests/test_style_frame.py` 逐字符比对 |
| 署名与 front-matter | `registry.frontmatter_block()` + `registry.SIGNATURE` 唯一来源 |
| 版本号 | `paths.project_version()` 读 `VERSION` |
| 创作出口 | `provider_bridge` 委托 `providers` 层，唯一主体 omniailab |
| 资产体积 | `scripts/check_assets.py`，两个仓库同一规则 |

**特别提醒**：`SpaceBrief` **不产生几何**，它只把主流程确认的几何
（开间、进深、净高、门窗洞口）如实带进提示词。若平面尚未确认（G3 未通过），
不要调用 `compile` —— 那等于凭空造几何。

## 五、生成式能力的唯一出口

风格系统不做自己的平台调用。所有创作任务都经 `style/provider_bridge.py`，
而它只做一件事：问 `omniarchitect.providers` 层能不能做。

```python
from omniarchitect.style import probe, submit
st = probe()                     # 状态来自 provider 层
if not st.usable:
    ...                          # submit() 会把任务标为 awaiting_platform
```

平台不可用时：任务保留、逐条标 `awaiting_platform`、**不改道任何第三方平台**、
不写占位图。缺失生成能力不影响几何、图纸、工程量与汇报。

---
> © OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
