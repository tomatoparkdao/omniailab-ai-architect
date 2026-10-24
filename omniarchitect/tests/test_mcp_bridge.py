"""MCP 桥接的守卫测试。

守四件事：

1. 没配置就是 `not_configured`，并列出缺哪些操作——不能含糊成"部分可用"；
2. 握手是真的（JSON-RPC initialize + tools/list），服务器不响应就不算连上；
3. 工具名靠别名钉住，不猜；只实现一半契约记 `partial`；
4. 未授权的调用必须被拒，任务包要留下真正会发出去的 arguments。

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

from omniarchitect.tools import mcp_bridge as mb

# A minimal MCP server: initialize / tools/list / tools/call, nothing more.
# `WITH_SECTION=0` drops the section tool so a half-implemented contract can be
# exercised — that is the case that must report `partial`, not `available`.
STUB = r'''
import json, os, sys

TOOLS = [
    {"name": "create_plan", "description": "plan", "inputSchema": {"type": "object"}},
    {"name": "create_elevation", "description": "elev", "inputSchema": {"type": "object"}},
    {"name": "write_dxf", "description": "dxf", "inputSchema": {"type": "object"}},
]
if os.environ.get("WITH_SECTION", "1") != "0":
    TOOLS.append({"name": "create_section", "description": "sect",
                  "inputSchema": {"type": "object"}})

for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    try:
        msg = json.loads(line)
    except Exception:
        continue
    if "id" not in msg:
        continue
    method = msg.get("method")
    if method == "initialize":
        result = {"protocolVersion": "2024-11-05",
                  "capabilities": {"tools": {}},
                  "serverInfo": {"name": "stub", "version": "0"}}
    elif method == "tools/list":
        result = {"tools": TOOLS}
    elif method == "tools/call":
        result = {"content": [{"type": "text",
                               "text": "ran:" + msg["params"]["name"]}]}
    else:
        result = {}
    sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": msg["id"],
                                 "result": result}) + "\n")
    sys.stdout.flush()
'''


def _write_config(tmp: Path, servers: dict) -> Path:
    path = tmp / "mcp.json"
    path.write_text(json.dumps({"mcpServers": servers}, ensure_ascii=False),
                    encoding="utf-8")
    return path


def _stub_config(tmp: Path, extra: dict | None = None,
                 with_section: bool = True) -> Path:
    script = tmp / "stub_server.py"
    script.write_text(STUB, encoding="utf-8")
    spec = {"role": "cad", "command": sys.executable, "args": [str(script)],
            "env": {"WITH_SECTION": "1" if with_section else "0"},
            "toolAliases": {"draw_plan": "create_plan",
                            "draw_elevation": "create_elevation",
                            "draw_section": "create_section",
                            "export_dxf": "write_dxf"}}
    spec.update(extra or {})
    return _write_config(tmp, {"cad": spec})


# --------------------------------------------------------------------------
def test_no_config_means_not_configured_with_missing_ops() -> None:
    """没有 mcp.json 时，缺的是全部操作，不是一个含糊的"不可用"。"""
    with tempfile.TemporaryDirectory() as td:
        prof = mb.probe("cad", Path(td))
    assert prof.state == mb.NOT_CONFIGURED
    assert not prof.usable
    assert set(prof.missing) == set(mb.CONTRACTS["cad"]["operations"])
    assert "mcp.json" in " ".join(prof.notes)


def test_unresolvable_command_is_not_configured() -> None:
    """配了但命令跑不起来，等于没配——不能因为配置存在就当成可用。"""
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        _write_config(tmp, {"cad": {"role": "cad",
                                    "command": "definitely-not-a-real-binary-xyz"}})
        prof = mb.probe("cad", tmp)
    assert prof.state == mb.NOT_CONFIGURED
    assert prof.missing


def test_real_handshake_resolves_aliases() -> None:
    """握手成功 + 四个契约操作全部解析成功，才算 available。

    stub 暴露的是 create_plan 这类名字，契约里叫 draw_plan；
    靠 toolAliases 钉住，而不是猜。
    """
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        _stub_config(tmp)
        prof = mb.probe("cad", tmp)
    assert prof.state == mb.AVAILABLE, prof.to_dict()
    assert prof.resolved["draw_plan"] == "create_plan"
    assert prof.resolved["draw_elevation"] == "create_elevation"
    assert prof.resolved["draw_section"] == "create_section"
    assert prof.resolved["export_dxf"] == "write_dxf"
    assert not prof.missing


def test_half_contract_is_partial_not_available() -> None:
    """服务器缺 draw_section 时记 partial，并点名缺哪个。

    半套工具最容易被当成"能用"：平面能画、剖面画不出，
    如果报 available，后面就会拿一个空剖面去出图。
    """
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        _stub_config(tmp, with_section=False)
        prof = mb.probe("cad", tmp)
    assert prof.state == mb.PARTIAL, prof.to_dict()
    assert prof.missing == ["draw_section"]
    assert set(prof.resolved) == {"draw_plan", "draw_elevation", "export_dxf"}
    assert prof.usable                      # 部分可用仍可用，但缺口必须点名


def test_call_requires_approval_and_returns_content() -> None:
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        _stub_config(tmp)
        denied = mb.call("cad", "draw_plan", {"level": "L1"}, tmp)
        ok = mb.call("cad", "draw_plan", {"level": "L1"}, tmp, approved=True)
    assert denied.ok is False and denied.state == "needs_approval"
    assert ok.ok is True
    assert ok.tool == "create_plan"
    assert "ran:create_plan" in json.dumps(ok.content, ensure_ascii=False)


def test_job_package_preserves_the_exact_arguments() -> None:
    """连不上时不能把活丢掉：任务包里要留下本来会发出去的参数。"""
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        args = {"level": "L1", "walls": 12, "title": "一层平面"}
        prof = mb.probe("sketchup", tmp)
        pkg = mb.job_package("sketchup", "create_walls", args, prof,
                             tmp / "sketchup-job.json")
        written = json.loads((tmp / "sketchup-job.json").read_text(encoding="utf-8"))
    assert pkg["state"] == mb.NOT_CONFIGURED
    assert written["arguments"] == args
    assert written["expected_tool_aliases"]
    assert written["how_to_run"]


def test_role_inferred_from_server_name() -> None:
    """名字里带 sketchup 就归 sketchup，不用每台服务器都手写 role。"""
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        path = _write_config(tmp, {"sketchup-mcp": {"command": "x"}})
        servers = mb.load_servers(tmp, path)
    assert servers["sketchup-mcp"].role == "sketchup"
