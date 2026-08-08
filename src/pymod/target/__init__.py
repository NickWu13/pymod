"""Code-target registry and factory."""
from __future__ import annotations

from pathlib import Path

from . import base
from .base import CodeTarget
from .datapack import DataPackTarget

__all__ = ["base", "CodeTarget", "get_generator"]


def get_generator(
    target: str,
    spec,
    out_dir: Path,
    game_version: str,
    pack_format: int | None = None,
) -> CodeTarget:
    """Return a configured :class:`CodeTarget` for ``target``.

    kubejs/fabric are imported lazily so an unimplemented or broken target fails
    at generation time with a clear message rather than at import time.
    """
    if target == "datapack":
        return DataPackTarget(spec, out_dir, game_version=game_version, pack_format=pack_format)
    if target == "kubejs":
        from .kubejs import KubeJSTarget

        return KubeJSTarget(spec, out_dir, game_version=game_version)
    if target == "fabric":
        from .fabric import FabricTarget

        return FabricTarget(spec, out_dir, game_version=game_version)
    raise ValueError(f"unknown target {target!r}")