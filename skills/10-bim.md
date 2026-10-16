---
name: omniarchitect-10-bim
version: 0.1.0
capability: bim-modeling
stages: [S5, S7]
---
# BIM Modeling

## Responsibility
Build and validate structured IFC objects with consistent spatial IDs.

## Inputs
Project brief, canonical model, source files, explicit constraints and design revision.

## Outputs
Structured findings, changes to canonical model (if applicable), artifacts and QA notes.

## Procedure
1. Confirm applicable input quality and assumptions.
2. Formulate a task plan and check project constraints.
3. Execute available tool adapters; avoid unverified claims.
4. Validate dimensional and semantic consistency.
5. Update revisions and list downstream artifacts to regenerate.

## Gate
If professional sign-off, statutory compliance or site measurement is needed, explicitly stop at draft/review stage.

## 阶段归属（v1.0 八阶段体系）

- 专业能力：`bim-modeling`（BIM 建模）
- 参与阶段：S5,S7
- 说明：专业能力是设计事务所的岗位能力，可跨阶段调用；项目推进按 `docs/WORKFLOW.md` 的八个业务阶段进行。
