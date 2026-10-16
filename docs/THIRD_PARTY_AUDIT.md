# 第三方内容审计报告

- 扫描时间：2026-10-16 16:22:41
- 扫描根目录：`E:\SKILL\建筑室内设计skill\omniailab-ai-architect`
- 扫描文本文件：**189**
- 结论：**无第三方商业内容需要处理**

## 处置分布

| 处置 | 文件数 | 含义 |
| --- | --- | --- |
| `attribution-required-keep` | 11 | 许可要求的署名，必须保留 |
| `original` | 107 | 本项目原创内容，无需处理 |
| `test-fixture` | 14 | 测试夹具，含样本数据；内容规则不适用 |
| `vendored-preserve` | 57 | 上游副本原样保留（含其 LICENSE），禁止修改 |

## 需要处理的文件

无。

## 必须保留的第三方署名

- 项目：**arch-skills** — https://github.com/gujun1502/arch-skills
- 作者：**Gu Jun**
- 许可：MIT (code) · CC BY 4.0 (documentation)
- 本地副本：`third_party/arch-skills`（原样保留，不修改）
- 允许出现署名信息的文件：`THIRD_PARTY_NOTICES.md`, `docs/THIRD_PARTY_AUDIT.md`, `docs/ARCH_SKILLS_INTEGRATION.md`, `AGENTS.md`, `LICENSES/`, `compliance/`, `third_party/`, `omniailab_ai_architect/`, `docs/third-party-audit.json`

## 处置规则

1. **用户面文件（SKILL.md / README / skills / knowledge / cases / templates / presentation）**
   不得出现第三方品牌名、商业推广站点或跳转链接。
2. **署名义务不可删**：许可证要求的作者、来源与许可标识集中在本文件与 `THIRD_PARTY_NOTICES.md`。
3. **要去掉某份第三方文档的再分发依赖**，只能从通用设计原理与公开工程惯例出发独立原创，
   不得复制或仅作同义改写。
4. **疑似个人或客户信息**一律先脱敏并确认授权，未经授权不得作为可再分发资产。
5. **上游仓库**（`third_party/arch-skills/`）保持原样，其自带 LICENSE 不得删除。
