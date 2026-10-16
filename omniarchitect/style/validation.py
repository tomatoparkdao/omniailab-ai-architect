"""Style-data validation with no third-party dependency.

The project keeps a hard rule of zero required dependencies: the whole engine
must run on a bare CPython. `jsonschema` is not installed everywhere, so this
module implements the small subset of JSON Schema the style schema actually
uses — `type`, `required`, `properties`, `additionalProperties`, `items`,
`minItems`, `maxItems`, `enum`, `pattern`, `minLength`, `maxLength`, `$ref`
and `$defs`.

Validation failures are reported as a list of JSON-pointer paths so the message
tells you exactly which key is wrong, not merely that something is.

© OmniAiLab ｜ 开发者：Mochiball ｜ OmniAiLab AI建筑与室内设计总设计师（omniailabx.com）— 未经授权禁止复制、传播或二次分发。
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from .resources import STYLE_SCHEMA


class StyleValidationError(Exception):
    """A style record failed validation. Carries every problem found."""

    def __init__(self, subject: str, problems: Sequence[str]):
        self.subject = subject
        self.problems = list(problems)
        head = f"{subject} 校验未通过（{len(self.problems)} 项）"
        super().__init__(head + "\n" + "\n".join(f"  - {p}" for p in self.problems))


def load_schema(path: Optional[Path] = None) -> Dict[str, Any]:
    p = path or STYLE_SCHEMA
    return json.loads(p.read_text(encoding="utf-8"))


_TYPE_MAP = {
    "object": dict,
    "array": list,
    "string": str,
    "integer": int,
    "number": (int, float),
    "boolean": bool,
    "null": type(None),
}


def _type_ok(value: Any, wanted: str) -> bool:
    if wanted == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if wanted == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if wanted == "boolean":
        return isinstance(value, bool)
    if wanted == "string":
        return isinstance(value, str)
    if wanted == "object":
        return isinstance(value, dict)
    if wanted == "array":
        return isinstance(value, list)
    return True


def _resolve(ref: str, root: Dict[str, Any]) -> Dict[str, Any]:
    """Resolve a local `#/$defs/Name` reference."""
    if not ref.startswith("#/"):
        return {}
    node: Any = root
    for part in ref[2:].split("/"):
        if not isinstance(node, dict) or part not in node:
            return {}
        node = node[part]
    return node if isinstance(node, dict) else {}


def _validate(value: Any, schema: Dict[str, Any], root: Dict[str, Any],
              path: str, out: List[str]) -> None:
    if "$ref" in schema:
        schema = {**_resolve(schema["$ref"], root), **{k: v for k, v in schema.items() if k != "$ref"}}

    if "type" in schema:
        want = schema["type"]
        wants = want if isinstance(want, list) else [want]
        if not any(_type_ok(value, w) for w in wants):
            out.append(f"{path}: 类型应为 {'/'.join(wants)}，实际 {type(value).__name__}")
            return

    if "enum" in schema and value not in schema["enum"]:
        out.append(f"{path}: 取值 {value!r} 不在允许集合 {schema['enum']}")

    if isinstance(value, str):
        if "minLength" in schema and len(value) < schema["minLength"]:
            out.append(f"{path}: 长度 {len(value)} < 最小 {schema['minLength']}")
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            out.append(f"{path}: 长度 {len(value)} > 最大 {schema['maxLength']}")
        if "pattern" in schema and not re.search(schema["pattern"], value):
            out.append(f"{path}: {value!r} 不匹配模式 {schema['pattern']}")

    if isinstance(value, dict):
        for key in schema.get("required", []):
            if key not in value:
                out.append(f"{path}.{key}: 缺少必需字段")
        props = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            for key in value:
                if key not in props:
                    out.append(f"{path}.{key}: 不在 Schema 允许的字段内（additionalProperties=false）")
        for key, sub in props.items():
            if key in value:
                _validate(value[key], sub, root, f"{path}.{key}", out)

    if isinstance(value, list):
        if "minItems" in schema and len(value) < schema["minItems"]:
            out.append(f"{path}: 条目数 {len(value)} < 最小 {schema['minItems']}")
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            out.append(f"{path}: 条目数 {len(value)} > 最大 {schema['maxItems']}")
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for i, item in enumerate(value):
                _validate(item, item_schema, root, f"{path}[{i}]", out)


def validate_style(style: Dict[str, Any], *, subject: str = "style",
                   schema: Optional[Dict[str, Any]] = None,
                   filename: Optional[str] = None) -> List[str]:
    """Return every problem found (empty list = valid). Does not raise."""
    sch = schema or load_schema()
    out: List[str] = []
    _validate(style, sch, sch, "$", out)
    if filename is not None and style.get("style_id") != filename:
        out.append(f"$.style_id: {style.get('style_id')!r} 与文件名 {filename!r} 不一致")
    return out


def assert_valid_style(style: Dict[str, Any], *, subject: str = "style") -> None:
    problems = validate_style(style, subject=subject)
    if problems:
        raise StyleValidationError(subject, problems)


def check_style_file(path: Path) -> List[str]:
    """Validate one style file on disk, including id/filename agreement."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:                                   # noqa: BLE001
        return [f"{path.name}: JSON 解析失败 —— {type(exc).__name__}: {exc}"]
    return validate_style(data, subject=path.name, filename=path.stem)


def check_style_dir(style_dir: Optional[Path] = None) -> Dict[str, List[str]]:
    """Validate every style file. Returns {filename: [problems]} for bad ones."""
    from .resources import style_files

    bad: Dict[str, List[str]] = {}
    for p in style_files(style_dir):
        problems = check_style_file(p)
        if problems:
            bad[p.name] = problems
    return bad
