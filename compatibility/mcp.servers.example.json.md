---
name: omniailab-compatibility-mcp-servers-example-json
description: MCP 服务器声明示例 —— 本文件是示例，不会被自动加载。真实配置请放到项目根目录的 mcp.json。
version: 1.21.2
author: OmniAiLab
developer: Mochiball
agent_created: true
开源仓库: https://github.com/tomatoparkdao/omniailab-ai-architect
操作手册: https://zcn03zgas1zl.feishu.cn/wiki/K1IWwPuBDiQXufkS76Yc3EMPnTd
---

# MCP 服务器声明示例

本文件是**示例**，不会被自动加载。真实配置请放到项目根目录的 `mcp.json`。

工具注册表只读取**已声明**的服务器：没有声明就报告"未注册"，
声明了但命令在本机不可解析就报告 `not_configured`。
**不会**猜测 endpoint、请求参数或鉴权方式。

```json
{
  "mcpServers": {
    "blender": {
      "command": "uvx",
      "args": ["blender-mcp"],
      "env": { "BLENDER_HOST": "127.0.0.1", "BLENDER_PORT": "9876" }
    },
    "freecad": {
      "command": "uvx",
      "args": ["freecad-mcp"]
    },
    "autocad": {
      "command": "npx",
      "args": ["-y", "autocad-mcp"]
    },
    "ifcopenshell": {
      "command": "python",
      "args": ["-m", "ifcopenshell_mcp"]
    },
    "remote-example": {
      "url": "https://example.invalid/mcp"
    }
  }
}
```

查看当前解析结果：

```bash
python -m omniarchitect tools
python -m omniarchitect tools --json
```

## 权限分级

| 级别 | 含义 | 是否需要确认 |
|---|---|---|
| L1 | 只读：解析图纸、查询状态 | 否 |
| L2 | 本地写入：在项目目录内创建/修改文件 | 否 |
| L3 | 联网：调用外部服务或模型 provider | **是** |
| L4 | 执行/发送：运行第三方代码、驱动宿主软件、对外发布 | **是，且必须先 dry-run** |

查看某个具体调用的门槛（不执行）：

```bash
python -m omniarchitect tools --plan "dxf:draw_plan"
python -m omniarchitect tools --plan "blender:run_blender"
```

## 安全约定

1. 远端 MCP 的连通性不做自动探测；未经验证一律 `not_configured`。
2. 任何 L3/L4 调用在未获显式授权时抛出 `PermissionRequired`，不静默执行。
3. 修改原始文件前必须留事务/撤销备份，并限制可访问路径。
4. 不把任意 CAD/Blender 脚本执行权限开放给互联网用户。

---
> © OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
