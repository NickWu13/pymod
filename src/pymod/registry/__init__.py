"""Registry of game-version profiles and vanilla names."""
from . import gameprofile
from .gameprofile import GameProfile, profile_for, default_game_version, load_profiles

# re-export vanilla registry lazily to avoid importing it eagerly
from . import vanilla  # noqa: F401

__all__ = ["gameprofile", "GameProfile", "profile_for", "default_game_version", "load_profiles"]