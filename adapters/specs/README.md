---
name: omniailab-adapters-specs-index
description: 外部工具适配规范索引 —— 每个适配器声明能力、权限与降级路径
version: 1.14.0
author: OmniAiLab
developer: Mochiball
agent_created: true
开源仓库: https://github.com/tomatoparkdao/omniailab-ai-architect
操作手册: https://zcn03zgas1zl.feishu.cn/wiki/K1IWwPuBDiQXufkS76Yc3EMPnTd
---

# 工具适配规范（MCP / 外部软件）

本目录是**人读**的适配规范；**机器读**的声明在 `omniarchitect/tools/registry.py`
（`BUILTIN_OPERATIONS` / `BUILTIN_LIMITS`）。两者必须一致，改动要一起改。

| 规范 | 对应工具 id | 风险示例 | 缺失时 |
|---|---|---|---|
| [`blender.md`](blender.md) | `blender` | `run_blender` **L4** | 输出 `build_scene.py`（有 Blender 的机器直接跑） |
| [`freecad.md`](freecad.md) | `freecad` | `run_freecad` **L4** | 输出 `build_freecad.py` |
| [`autocad.md`](autocad.md) | `autocad`（MCP） | 写回原图 **L4** | 使用内置 DXF 写出器；DWG 需许可后端 |
| [`ifc.md`](ifc.md) | `ifc` | `write_ifc` **L2** | 输出 IFC 投影 JSON + `build_ifc.py` |

## 统一契约

每个适配器都要回答同一组问题，缺一个都不合格：

1. **preflight**：这台机器上存在吗？版本？可执行文件路径？能做什么操作？
2. **降级路径**：不存在时输出什么？降级产物必须能在有环境的机器上直接使用。
3. **风险等级**：每个操作声明 L1–L4（静态声明，**不允许运行时提权**）。
4. **产物上限**：产物**不能**被称为什么（写进 `BUILTIN_LIMITS`）。
5. **写-读回**：写出的文件必须能被独立解析器重新打开并复核。

```bash
python -m omniarchitect tools
python -m omniarchitect tools --plan "blender:run_blender"
python -m omniarchitect honesty
```

## 安全

1. 第三方 MCP 独立部署、独立测试权限与运行环境；不把任意 CAD/Blender 脚本执行权开放给互联网用户。
2. `mcp.json` 里**声明过**的服务器才会被读取；命令不可解析即 `not_configured`（不会启动）。
3. 远端 MCP 不做连通性探测，也不猜鉴权方式。
4. 修改原始文件前必须留事务/撤销备份，并限制可访问路径。
5. 详细说明见 [`../../docs/MCP_TOOLS.md`](../../docs/MCP_TOOLS.md) 与
   [`../../compatibility/mcp.servers.example.json.md`](../../compatibility/mcp.servers.example.json.md)。

---
> © OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
