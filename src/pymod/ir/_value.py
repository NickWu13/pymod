"""Scalar values allowed in IR arguments and registration props.

The DSL evaluates everything down to one of these Python primitives before it
enters the IR.  No arbitrary objects, no expressions, no AST nodes survive.
"""
from __future__ import annotations

from typing import Union

Value = Union[str, int, float, bool, None]


def value_to_str(v: Value) -> str:
    """Render an IR value the way Minecraft ID/JSON contexts expect."""
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v)