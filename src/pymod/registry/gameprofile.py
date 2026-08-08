"""Game-version profiles: the single source of truth for version-sensitive facts.

Generators and the Fabric project template read version facts exclusively from
here (or from an override supplied on the CLI).  Nothing in codegen hardcodes a
Minecraft version number.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class GameProfile:
    game_version: str
    release: str = ""
    userspace_name: str = ""
    data_channel: str = "stable"
    java_version: str = "21"
    fabric: dict[str, Any] = None  # loader/fabric-api/mappings/loom/gradle
    minecraft_internal: dict[str, Any] = None  # pack_version/world/protocol
    pack: dict[str, Any] = None  # data_format / resource_format / provenance

    def pack_format(self) -> str:
        """Data-pack format number; raises a clear error if it is unverified."""
        fmt = (self.pack or {}).get("data_format", "TBD-Verify")
        if isinstance(fmt, str) and fmt.startswith("TBD"):
            raise LookupError(
                "data pack format for this game version is not verified yet; "
                "see src/pymod/gameprofiles.json"
            )
        return str(fmt)

    def resource_pack_format(self) -> str:
        fmt = (self.pack or {}).get("resource_format", "TBD-Verify")
        if isinstance(fmt, str) and fmt.startswith("TBD"):
            raise LookupError(
                "resource pack format for this game version is not verified yet"
            )
        return str(fmt)


def load_profiles(path: Path | None = None) -> dict[str, dict]:
    if path is not None:
        return json.loads(path.read_text(encoding="utf-8"))
    text = resources.files("pymod").joinpath("gameprofiles.json").read_text(encoding="utf-8")
    return json.loads(text)


def profile_for(game_version: str, path: Path | None = None) -> GameProfile:
    data = load_profiles(path)
    raw = data.get("profiles", {}).get(game_version)
    if not raw:
        known = ", ".join(sorted(data.get("profiles", {})))
        raise KeyError(
            f"no game profile for Minecraft {game_version!r} (known: {known})"
        )
    prof = dict(raw)
    prof.pop("game_version", None)  # this function supplies it
    return GameProfile(game_version=game_version, **prof)


def default_game_version(path: Path | None = None) -> str:
    return load_profiles(path).get("default", "26.2")