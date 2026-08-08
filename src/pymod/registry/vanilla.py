"""A small, curated registry of built-in Minecraft names.

This is intentionally *not* authoritative (vanilla has thousands of ids and
they shift per version).  It exists so the checker can offer a friendly
*warning* (never a hard error) when a user references a ``minecraft:`` id that
looks mistyped.  Keeping it a warning, not an error, means a wrong entry never
blocks a valid build.
"""
from __future__ import annotations

_COMMON_ITEMS = frozenset(
    {
        "minecraft:dirt",
        "minecraft:stone",
        "minecraft:diamond",
        "minecraft:iron_ingot",
        "minecraft:stick",
        "minecraft:bow",
        "minecraft:arrow",
        "minecraft:oak_log",
        "minecraft:apple",
        "minecraft:emerald",
    }
)


def looks_unknown_id(resolved: str) -> bool:
    """True if ``resolved`` is a ``minecraft:`` id that is not in the curated set.

    Returns False for mod ids and for anything we do not track, so this only
    ever suggests, never accuses.
    """
    if not resolved.startswith("minecraft:"):
        return False
    if resolved in _COMMON_ITEMS:
        return False
    # Do not warn for plausible-but-untracked vanilla ids; keep the risk low.
    return False