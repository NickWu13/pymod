"""Target-agonistic intermediate representation (IR) and capability matrix."""

from ._value import Value, value_to_str
from .irnodes import (
    ModSpec,
    ModInfo,
    Registration,
    EventHandler,
    EventAction,
    Guard,
    TARGETS,
)
from .capability import (
    ACTION_SPECS,
    EVENT_SPECS,
    REGISTRATION_KINDS,
    REGISTRATION_PROPS,
    TargetCapability,
    capability_for,
)

__all__ = [
    "Value",
    "value_to_str",
    "ModSpec",
    "ModInfo",
    "Registration",
    "EventHandler",
    "EventAction",
    "Guard",
    "TARGETS",
    "ACTION_SPECS",
    "EVENT_SPECS",
    "REGISTRATION_KINDS",
    "REGISTRATION_PROPS",
    "TargetCapability",
    "capability_for",
]