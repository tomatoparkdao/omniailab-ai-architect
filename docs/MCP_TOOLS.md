# MCP 与工具执行系统

## 1. 统一工具注册表

```bash
python -m omniailab_ai_architect tools
python -m omniailab_ai_architect tools --json
python -m omniailab_ai_architect tools --plan "dxf:draw_plan"
```

注册表回答三个问题：

1. **这台机器上能跑什么？** —— 逐个探测，不假设存在。
2. **可以跑吗？** —— L1–L4 权限分级把关。
3. **真的跑成了吗？** —— 用**独立解析器**重新打开产物；工具从不自证。

## 2. 已适配的工具

| id | 类型 | 能力 | 缺失时的降级 |
| --- | --- | --- | --- |
| `dxf` | python | 绘制平面图、写出 DXF（R12 / R2010）、独立复核 | 内置 R12 写出器，始终可用 |
| `mesh` | python | 由空间模型构建三角网格、导出 OBJ/MTL | 纯 Python，始终可用 |
| `blender` | 宿主程序 | 生成场景脚本、执行 Blender 批处理 | `build_scene.py`（有 Blender 的机器可直接跑） |
| `freecad` | 宿主程序 | 生成参数化建模脚本、执行 FreeCAD | `build_freecad.py` |
| `ifc` | python | IFC 投影数据、写出 IFC | `ifc_projection.json` + `build_ifc.py` |
| `render` | provider | 编排机位任务包、本地示意图、调用图片 provider | 任务包 JSON |

`--plan` 打印某次调用的风险、门禁、允许的最强表述与限制。

## 3. 权限分级

| 级别 | 含义 | 确认 | 示例 |
| --- | --- | --- | --- |
| L1 | 只读 | 否 | `dxf:audit`、`dxf:read_back` |
| L2 | 本地写入 | 否 | `dxf:draw_plan`、`mesh:build`、`ifc:emit_projection` |
| L3 | 联网 | **是** | `render:render_ai`（调用外部模型 provider） |
| L4 | 执行 / 发送 | **是，且必须先 dry-run** | `blender:run_blender`、`freecad:run_freecad` |

未获授权时抛出 `PermissionRequired`，**不静默执行**：

```python
from omniailab_ai_architect.tools import registry
reg = registry()
reg.guard("blender", "run_blender")            # -> PermissionRequired
reg.guard("blender", "run_blender", approved=True)   # 仍需工具真实可用
```

## 4. 产物验证

写出即验证，且**用不同实现**：

| 扩展名 | 验证方式 |
| --- | --- |
| `.dxf` | 内置 R12 解析器（实体/图层统计）+ `ezdxf.recover` 交叉复核 |
| `.obj` | 重新解析顶点/面/材质，回读包围盒与尺寸 |
| `.pptx` | 解开 OOXML 容器：`[Content_Types].xml`、slide part 数量、每张 slide 的 XML 合法性 |
| `.json` | JSON 解析 + 顶层结构 |
| `.png` | PNG 魔数 + 尺寸 |

```python
reg.verify("out/03-plan/S3-schematic-A.dxf")
# {'ok': True, 'dialect': 'R2010+', 'stats': {...}, 'honest_label': '可编辑 2D CAD 图纸（DXF）'}
```

## 5. 能力真实性规则

`python -m omniailab_ai_architect honesty` 打印完整清单。核心五条：

| 不得声称 | 为什么 | 应当表述为 |
| --- | --- | --- |
| DXF 改名为 DWG 即为 DWG | DWG 是封闭二进制格式，改名不改内容 | 只能声明输出了 DXF；DWG 需具备许可的后端另存 |
| 三角网格是参数化 BIM | 网格无构件语义、属性与参数关系 | 输出为三维网格模型（非参数化 BIM） |
| AI 效果图可作施工尺寸依据 | 生成图不保证尺寸与比例 | 施工图须由经校核的几何模型生成 |
| 未装 IfcOpenShell 也输出了合规 IFC | 没有写出能力时不存在 IFC 文件 | IFC 投影数据 + 可在有环境的机器上运行的脚本 |
| 系统已通过结构/消防/无障碍校核 | 不在系统能力范围内 | 只做规则初筛；须持证专业人员复核签署 |

各扩展名允许的最强表述由 `ARTIFACT_KIND_CEILING` 定义，并在每条产物的验收记录里回填。

## 6. 扩展新工具

1. 在 `adapters/` 写适配器（实现 `preflight()` 与操作），或在 `mcp.json` 声明 MCP 服务器；
2. 在 `tools/registry.py: BUILTIN_OPERATIONS` 声明操作及其风险等级（**静态声明，不允许运行时提权**）；
3. 在 `BUILTIN_LIMITS` 写清"产物不得被称为什么"；
4. 若产生新扩展名，在 `VERIFIERS` 注册独立校验器；
5. 补一条测试：工具缺失时必须降级且如实标注。

## 7. MCP 声明

MCP 服务器**只被读取，不被猜测**。配置放项目根目录 `mcp.json`：

```json
{ "mcpServers": { "blender": { "command": "uvx", "args": ["blender-mcp"] } } }
```

- 命令在本机可解析 → `available`；
- 已声明但命令不可解析 → `not_configured`（服务器不会启动）；
- 只给了 `url` → `not_configured`（**不做连通性探测，不猜测鉴权**）。

示例见 `compatibility/mcp.servers.example.json.md`。
