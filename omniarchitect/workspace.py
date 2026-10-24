"""运行工作区 —— 设计成果住在哪里，技能包里只留能力。

为什么单独一个模块
------------------
技能目录的定位是**能力定义**：`SKILL.md`、知识库、风格库、代码、Schema、适配器。
房子不会盖在工具箱里。所以所有"跑一次就生成一堆"的东西 —— CAD、模型、效果图、
PPT、视频、测试截图、交付清单 —— 一律写到技能目录**之外**的运行工作区。

五个分区（名字固定，不要另起一套）：

| 分区 | 内容 | 可再生 |
|---|---|---|
| `projects` | 真实客户项目（`project.json` + 版本记录） | 否，必须备份 |
| `outputs` | CAD / 模型 / 效果图 / PPT / HTML / 工程量 / 交付文件 | 由项目重算 |
| `tests` | 测试与演示跑出来的项目、截图、报告 | 是 |
| `cache` | 可随时清空的中间件（栅格化、下载、场景缓存） | 是 |
| `archive` | 历史运行资料、需要留档的旧验收产物 | 否 |

路径优先级
----------
1. 显式参数（调用方指定，比如 `--out`）—— 原样尊重，不重定向。
2. 分区环境变量：`OMNIAILAB_OUTPUT_DIR` / `OMNIAILAB_PROJECTS_DIR` /
   `OMNIAILAB_TESTS_DIR` / `OMNIAILAB_CACHE_DIR` / `OMNIAILAB_ARCHIVE_DIR`。
3. 工作区根：`OMNIAILAB_WORKSPACE`。
4. 平台默认（见 `default_root()`）：Windows 优先 `E:\\OmniAiLab-Workspace\\Architect`，
   其余用用户数据目录。**默认值绝不落在技能目录里**。

旧变量 `OMNI_TEST_OUTPUT` 仍然有效（等价于 `OMNIAILAB_TESTS_DIR`），只是标记为兼容。

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import contextlib
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

#: 技能仓库根（包目录的上一级）。这里自己算一次，避免 `paths` 与本模块循环导入。
SKILL_ROOT = Path(__file__).resolve().parent.parent

WORKSPACE_ENV = "OMNIAILAB_WORKSPACE"
LEGACY_TEST_ENV = "OMNI_TEST_OUTPUT"

#: 五个分区，顺序即文档顺序。
KINDS = ("projects", "outputs", "tests", "cache", "archive")

ENV_BY_KIND = {
    "projects": "OMNIAILAB_PROJECTS_DIR",
    "outputs": "OMNIAILAB_OUTPUT_DIR",
    "tests": "OMNIAILAB_TESTS_DIR",
    "cache": "OMNIAILAB_CACHE_DIR",
    "archive": "OMNIAILAB_ARCHIVE_DIR",
}

_DESCRIPTIONS = {
    "projects": "真实客户项目（project.json 与版本记录），不可再生",
    "outputs": "CAD / 模型 / 效果图 / PPT / 工程量 / 交付文件",
    "tests": "测试与演示产物，可随时删除",
    "cache": "中间缓存，可随时清空",
    "archive": "历史运行资料与旧验收产物留档",
}


# --------------------------------------------------------------------------
def default_root() -> Path:
    """平台默认工作区根。

    Windows 用 `E:\\OmniAiLab-Workspace\\Architect`（用户指定的布局）；E: 不在时退回
    用户目录下的同名结构 —— **不假设盘符存在**，否则在别人的机器上会直接写失败。
    macOS / Linux 走各自的数据目录，不往家目录根上撒文件。
    """
    if os.name == "nt":
        e_drive = Path("E:/")
        if e_drive.exists():
            return e_drive / "OmniAiLab-Workspace" / "Architect"
        return Path.home() / "OmniAiLab-Workspace" / "Architect"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "OmniAiLab" / "Architect"
    xdg = os.environ.get("XDG_DATA_HOME")
    base = Path(xdg) if xdg else (Path.home() / ".local" / "share")
    return base / "omniailab" / "architect"


def root() -> Path:
    """工作区根目录（不创建）。"""
    override = os.environ.get(WORKSPACE_ENV)
    if override and override.strip():
        return Path(os.path.expanduser(override.strip()))
    return default_root()


def path(kind: str = "outputs") -> Path:
    """某个分区的路径（不创建目录）。"""
    kind = _check_kind(kind)
    if kind == "tests":
        legacy = os.environ.get(LEGACY_TEST_ENV)
        if legacy and legacy.strip():
            return Path(os.path.expanduser(legacy.strip()))
    override = os.environ.get(ENV_BY_KIND[kind])
    if override and override.strip():
        return Path(os.path.expanduser(override.strip()))
    return root() / kind


def ensure(kind: str = "outputs", *parts: str) -> Path:
    """创建并返回分区目录（可再拼子路径）。"""
    p = path(kind).joinpath(*[str(x) for x in parts if str(x)])
    p.mkdir(parents=True, exist_ok=True)
    return p


def projects_dir() -> Path:
    return ensure("projects")


def outputs_dir() -> Path:
    return ensure("outputs")


def tests_dir() -> Path:
    return ensure("tests")


def cache_dir() -> Path:
    return ensure("cache")


def archive_dir() -> Path:
    return ensure("archive")


# --------------------------------------------------------------------------
def is_inside_skill(p: str | Path) -> bool:
    """这个路径是否落在技能仓库里。"""
    try:
        Path(p).resolve().relative_to(SKILL_ROOT.resolve())
        return True
    except ValueError:
        return False
    except OSError:            # Windows 上的非法字符等
        return False


def require_outside_skill(p: str | Path) -> Path:
    """运行产物不许放技能目录。放进去就直接拒绝，不做"悄悄搬家"。"""
    target = Path(p)
    if is_inside_skill(target):
        raise ValueError(
            f"运行产物不能写进技能目录：{target}\n"
            f"技能目录只放能力（代码 / 知识 / Schema），产物请写到工作区：{root()}"
        )
    return target


def resolve_project(value: str | Path) -> Path:
    """把用户给的 `--project` 解析成项目目录。

    依次尝试：原样路径 → 相对当前目录 → 工作区 `projects/<名字>` →
    工作区里同名项目（`projects/*/<名字>`）。都找不到时，报错要把**找过哪里**说清楚，
    而不是只丢一句 not found。
    """
    raw = Path(os.path.expanduser(str(value)))
    tried: List[str] = []
    candidates: List[Path] = [raw]
    if not raw.is_absolute():
        candidates.append(Path.cwd() / raw)
    candidates.append(path("projects") / raw)
    if raw.name:
        candidates.append(path("projects") / raw.name)
        candidates.extend(sorted(path("projects").glob(f"*/{raw.name}")))
    for c in candidates:
        tried.append(str(c))
        if c.exists():
            return c
    raise FileNotFoundError(
        "项目不存在：" + str(value) + "\n找过：" + "、".join(dict.fromkeys(tried))
        + "\n新项目请先建在工作区：" + str(path("projects"))
    )


# --------------------------------------------------------------------------
def stamp(fmt: str = "%Y%m%d-%H%M%S") -> str:
    return time.strftime(fmt)


@contextlib.contextmanager
def scratch(prefix: str = "scratch-") -> Iterator[Path]:
    """`cache/` 下的临时目录，退出即删 —— 测试与一次性转换用它。"""
    d = ensure("cache") / f"{prefix}{stamp()}-{os.getpid()}"
    d.mkdir(parents=True, exist_ok=True)
    try:
        yield d
    finally:
        shutil.rmtree(d, ignore_errors=True)


@contextlib.contextmanager
def tempdir(prefix: str = "omniailab-") -> Iterator[Path]:
    """系统临时目录，连 `cache/` 都不留的东西（比如只读一次就想扔的中间件）。"""
    with tempfile.TemporaryDirectory(prefix=prefix) as td:
        yield Path(td)


# --------------------------------------------------------------------------
def describe() -> Dict[str, Any]:
    """给 CLI / 文档 / 测试用的一份自述。"""
    kinds: Dict[str, Any] = {}
    for k in KINDS:
        p = path(k)
        kinds[k] = {
            "path": str(p),
            "env": ENV_BY_KIND[k],
            "description": _DESCRIPTIONS[k],
            "exists": p.exists(),
            "inside_skill": is_inside_skill(p),
        }
    return {
        "root": str(root()),
        "root_env": WORKSPACE_ENV,
        "default_root": str(default_root()),
        "overridden": bool(os.environ.get(WORKSPACE_ENV, "").strip()),
        "legacy_test_env": LEGACY_TEST_ENV if os.environ.get(LEGACY_TEST_ENV) else None,
        "skill_root": str(SKILL_ROOT),
        "inside_skill": is_inside_skill(root()),
        "kinds": kinds,
        "note": "技能目录只放能力；客户项目、图纸、模型、汇报、缓存全部在工作区。",
    }


def _check_kind(kind: str) -> str:
    k = (kind or "outputs").strip().strip("/\\")
    if k not in KINDS:
        raise ValueError(f"未知工作区分区 {kind!r}，可选：{'/'.join(KINDS)}")
    return k


__all__ = [
    "SKILL_ROOT", "WORKSPACE_ENV", "LEGACY_TEST_ENV", "KINDS", "ENV_BY_KIND",
    "default_root", "root", "path", "ensure", "projects_dir", "outputs_dir",
    "tests_dir", "cache_dir", "archive_dir", "is_inside_skill",
    "require_outside_skill", "resolve_project", "stamp", "scratch", "tempdir",
    "describe",
]
