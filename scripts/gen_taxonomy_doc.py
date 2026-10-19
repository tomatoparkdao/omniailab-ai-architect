"""生成 `docs/PROJECT_TAXONOMY.md`：分类索引的唯一书面版本。

索引不手抄：这里从 `omniarchitect/taxonomy.py` 读出全部类型、子类数与能力边界，
写成一张可以对照的表。改了 taxonomy 就跑一次，文档不会漂。

用法：``python scripts/gen_taxonomy_doc.py``（``--check`` 只比对不写盘）

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from omniarchitect import taxonomy as tx  # noqa: E402
from omniarchitect.paths import MANUAL_CN_URL, REPO_URL, project_version  # noqa: E402
from omniarchitect.registry import SIGNATURE  # noqa: E402

OUT = ROOT / "docs" / "PROJECT_TAXONOMY.md"

HEAD = """---
name: omniailab-PROJECT_TAXONOMY
description: PROJECT_TAXONOMY —— OmniAiLab AI 建筑与室内设计总设计师的说明文档。
version: {version}
author: OmniAiLab
developer: Mochiball
agent_created: true
开源仓库: {repo}
操作手册: {manual}
---

# 项目分类与专业路由

这份文档回答一个问题：**同一个"总设计师"，面对不同类型的项目，凭什么给出不同的答案。**

分类是唯一数据源 `omniarchitect/taxonomy.py` 的书面版；`python -m omniarchitect taxonomy`
打印的是同一份数据的终端版。本文件由 `scripts/gen_taxonomy_doc.py` 生成，不要手改。

---

## 一、三条分类学规矩

1. **民用建筑 = 居住建筑 + 公共建筑。** 学校、医院、酒店是公共建筑下面的功能类型，
   不与民用建筑并列。工业建筑与农业建筑是生产建筑，单独成支。
2. **用途与性质是两个维度。** "酒店"是用途，"新建 / 改扩建 / 既有室内精装 / 功能转换 /
   历史保护"是性质。同一个酒店可以是新建，也可以只是室内改造。
3. **用途可多选，委托范围不能推断。** "商业办公酒店综合体"就是三个标签；
   但客户说"酒店室内设计"，建筑专业就不在范围内——名称不是委托书。

---

## 二、A 建筑（15 类）

| 编码 | 类型 | 所属 | 子类 | 能力边界 |
|---|---|---|---|---|
"""

HEAD_B = """
室内与景观同理：`B` 开头是室内，`C` 开头是景观。三段的编码首位即专业。

---

## 三、能力边界怎么读

| 级别 | 含义 | 本系统实际能做什么 |
|---|---|---|
| `full` | 方案级完整执行 | 概念、平面、面积与指标可核对（仍不含结构/机电/法规结论） |
| `partial` | 部分执行 | 空间组织与面积可核对；结构、机电、法规不在结论内 |
| `concept_only` | 概念与任务梳理 | 可出方向、图解与设计任务清单；不出合规平面 |
| `specialist` | 必须专项前提 | 只做条件梳理与协同；工艺、感控、结构、消防由专项单位与持证人员完成 |

**分类覆盖全面 ≠ 每个类型都能出成品。** 新增一个"医院"分类，不等于能自动完成符合规范的
医院设计；它意味着系统知道该问医疗工艺、该按洁污分流推、该在 S3 列出医疗专项任务，
并且会把"须专项复核"写在成果里。

---

## 四、S1 → S2 → S3 怎么用这份分类

| 阶段 | 用分类做什么 | 产物 |
|---|---|---|
| S1 | 识别用途（可多选）、性质、委托范围；按类型追加 2–3 条行业专项问题（每轮仍最多 3 问） | `meta.intake.taxonomy` |
| S2 | 按类型选设计方法与概念方向：从"院中取院"到"医技居中·门诊环绕" | 概念方案 + `taxonomy` 块 + 缺口说明 |
| S3 | 按专业列任务清单（通用任务 + 本类型专属任务），并写明能力边界 | `scheme-comparison.md` 开头的分类与任务板 |

指令对照：

```bash
python -m omniarchitect taxonomy                      # 全部 36 类
python -m omniarchitect taxonomy --show A4            # 医院：要点/方向/S3 任务
python -m omniarchitect taxonomy --detect "既有酒店室内精装修"
```

---

## 五、设计方法的落点

每一类都写了三样东西，它们决定 S2 的推敲内容：

1. **专业要点（focus）**：这一类项目绕不开的判断，例如医院的洁污分流、学校的分龄组织、
   厂房的工艺流线；
2. **概念方向（directions）**：2–3 条**组织逻辑不同**的方向模板（parti 不同），
   不是风格差异；
3. **S3 专属任务**：在专业通用任务之外，这一类必须多做的事，例如"科室面积与床位配置表"
   "客房模数与走廊效率""汇水分区与竖向"。

已有成套策略库的类型（住宅、办公、私家庭院等）**继续用原策略**，分类只补充专业要点与
S3 任务；其余类型用方向模板推敲，并在成果里标 `source="method"` 与缺口说明。

---

## 六、与外部注册建筑师技能的关系

需要规范条文、防火疏散、构造做法等注册建筑师层面的知识时，按 `SKILL.md` §4
「需要建筑师专业知识」一行的规则按需读取外部技能（在线，不下载、不复制）。
分类负责"这是什么项目、要问什么、要做什么"；外部技能负责"这一条规范怎么规定"。
两者都不替代项目所在地现行规定与注册人员签署。

---

## 七、兼容性

- `taxonomy` 只写 `project.meta.intake.taxonomy`，**不新增必填字段**，旧项目照常打开；
- 旧 `profile_id`（residential / office / hospitality / retail / exhibition / architecture）
  全部保留，分类是叠加层，不是替换；
- 未识别出类型时 `codes` 为空，问诊按最宽口径提问，S2/S3 不套任何专项方法。
"""


def _row(code: str, name: str, disc: str, sub: str, cap: str) -> str:
    label = tx.CAPABILITY_LABELS.get(cap, cap).split("：")[0]
    short = {"architecture": "建筑", "interior": "室内", "landscape": "景观"}.get(disc, disc)
    fam = ""
    spec = tx.resolve(code)
    if spec:
        fam = tx.FAMILY_LABELS.get(spec.family, "").replace("民用建筑 · ", "")
    return f"| {code} | {name} | {fam or short} | {sub} | {label} |"


def build() -> str:
    head = HEAD.format(version=project_version(), repo=REPO_URL, manual=MANUAL_CN_URL)
    parts = [head.rstrip() + "\n"]
    # 三张表：A / B / C 各自成段，避免一张 36 行的表读不动
    for prefix, title in (("A", "建筑"), ("B", "室内"), ("C", "景观")):
        rows = [(t.code, t.name, t.discipline, str(len(t.subtypes)),
                 t.capability) for t in sorted(
                     (x for x in tx.TYPES.values() if x.code.startswith(prefix)),
                     key=lambda x: int(x.code[1:]))]
        if prefix != "A":
            parts.append(f"\n### {'二' if prefix == 'B' else '三'}、"
                         f"{prefix} {title}（{len(rows)} 类）\n")
            parts.append("| 编码 | 类型 | 所属 | 子类 | 能力边界 |")
            parts.append("|---|---|---|---|---|")
        for code, name, disc, sub, cap in rows:
            parts.append(_row(code, name, disc, sub, cap))
        parts.append("")
    parts.append(HEAD_B.strip())
    total = len(tx.TYPES)
    sub_total = sum(len(t.subtypes) for t in tx.TYPES.values())
    parts.append(f"\n---\n\n> 分类规模：{total} 类 / {sub_total} 个子类。"
                 f"改动请改 `omniarchitect/taxonomy.py` 后重跑本生成器。")
    parts.append(f"\n---\n{SIGNATURE}")
    return "\n".join(parts).rstrip() + "\n"


def main() -> int:
    text = build()
    check = "--check" in sys.argv
    current = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
    if check:
        if current != text:
            print("docs/PROJECT_TAXONOMY.md 与 taxonomy 不一致，请重跑生成器")
            return 1
        print("一致")
        return 0
    OUT.write_text(text, encoding="utf-8")
    print(f"写入 {OUT.relative_to(ROOT)}：{len(text.splitlines())} 行")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
