"""The capability matrix: the single authority on what the DSL may express.

This module is the *whitelist* for both the Checker (did the user use a known
op/event with the right arguments?) and for each code target (does this target
support the op/event/registration at all?).  A target that cannot express
something must say so loudly in its :class:`TargetCapability` rather than
silently emitting nothing.

The datapack target is the weakest (events are simulated through
advancements+mcfunctions) and fabric the strongest; the IR stays a superset and
each target's matrix decides the cut.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ActionSpec:
    """Static description of one action op, used by the checker."""

    op: str
    arg_names: tuple[str, ...]
    #: expected type for each positional arg: "str" | "int" | "float" | "bool" | "id"
    arg_types: tuple[str, ...]
    description: str
    required: int = 0  # how many leading args are mandatory


@dataclass(frozen=True)
class EventSpec:
    """Static description of one event kind."""

    kind: str
    params: tuple[str, ...]
    description: str


@dataclass(frozen=True)
class TargetCapability:
    target: str
    registrations: frozenset[str] = frozenset()
    events: frozenset[str] = frozenset()
    actions: frozenset[str] = frozenset()
    notes: tuple[str, ...] = field(default_factory=tuple)

    def can_register(self, kind: str) -> bool:
        return kind in self.registrations

    def can_emit_event(self, kind: str) -> bool:
        return kind in self.events

    def can_emit_action(self, op: str) -> bool:
        return op in self.actions


# --------------------------------------------------------------------------
# The DSL vocabulary (target-independent).
# --------------------------------------------------------------------------

ACTION_SPECS: dict[str, ActionSpec] = {
    "send_message": ActionSpec(
        "send_message",
        ("message",),
        ("str",),
        "Show a chat message to the event source (player).",
        required=1,
    ),
    "give_item": ActionSpec(
        "give_item",
        ("item", "count"),
        ("id", "int"),
        "Give the player an item (optionally with a count).",
        required=1,
    ),
    "set_block": ActionSpec(
        "set_block",
        ("x", "y", "z", "block"),
        ("int", "int", "int", "id"),
        "Place a block at a world offset from the event position.",
        required=4,
    ),
    "teleport": ActionSpec(
        "teleport",
        ("target", "x", "y", "z"),
        ("str", "float", "float", "float"),
        "Teleport an entity to world coordinates.",
        required=4,
    ),
    "spawn_particle": ActionSpec(
        "spawn_particle",
        ("effect", "x", "y", "z", "count"),
        ("id", "float", "float", "float", "int"),
        "Spawn a particle effect at a position.",
        required=4,
    ),
    "play_sound": ActionSpec(
        "play_sound",
        ("sound", "x", "y", "z", "volume", "pitch"),
        ("id", "float", "float", "float", "float", "float"),
        "Play a sound event for the player.",
        required=4,
    ),
    "grant_advancement": ActionSpec(
        "grant_advancement",
        ("advancement",),
        ("id",),
        "Grant a player an advancement.",
        required=1,
    ),
}

EVENT_SPECS: dict[str, EventSpec] = {
    "player.use_item": EventSpec(
        "player.use_item", ("player", "item"), "Fired when a player uses an item."
    ),
    "player.right_click_block": EventSpec(
        "player.right_click_block",
        ("player", "block", "pos"),
        "Fired when a player right-clicks a block.",
    ),
    "entity.killed": EventSpec(
        "entity.killed", ("entity", "killer"), "Fired when an entity is killed."
    ),
    "block.broken": EventSpec(
        "block.broken", ("player", "block", "pos"), "Fired when a player breaks a block."
    ),
    "advancement.granted": EventSpec(
        "advancement.granted",
        ("player", "advancement"),
        "Fired when a player is granted an advancement.",
    ),
}

REGISTRATION_KINDS: frozenset[str] = frozenset({"item", "block", "tag"})

#: allowed kwargs per registration kind; value is the expected type tag used by
#: the checker ("int" | "float" | "bool" | "str" | "id" | "id-list").
REGISTRATION_PROPS: dict[str, dict[str, str]] = {
    "item": {"max_stack": "int", "has_glint": "bool"},
    "block": {"hardness": "float", "transparent": "bool"},
    "tag": {"values": "id-list"},
}


# --------------------------------------------------------------------------
# Per-target support.
# --------------------------------------------------------------------------

CAPABILITIES: dict[str, TargetCapability] = {
    "datapack": TargetCapability(
        target="datapack",
        registrations=frozenset({"item", "block", "tag"}),
        # datapack has no first-class events; these are simulated via
        # advancement triggers + mcfunctions.  Only a narrow slice is honest in
        # MVP -- see notes.
        events=frozenset({"player.use_item", "player.right_click_block"}),
        actions=frozenset(
            {
                "send_message",
                "give_item",
                "set_block",
                "teleport",
                "spawn_particle",
                "play_sound",
                "grant_advancement",
            }
        ),
        notes=(
            "player.use_item / player.right_click_block are simulated by the "
            "item_used_on_block advancement trigger driving a reward function. "
            "Rewards fire once per player. item/block registrations are metadata "
            "only (a datapack cannot add new game content without a resource pack)."
        ),
    ),
    "kubejs": TargetCapability(
        target="kubejs",
        registrations=frozenset({"item", "block", "tag"}),
        # MVP: only player-scoped callbacks where event.player is guaranteed
        # and the emitted action maps onto a real KubeJS call.
        events=frozenset({"player.use_item", "player.right_click_block", "block.broken"}),
        actions=frozenset({"send_message", "give_item", "set_block"}),
        notes=(
            "player.use_item -> ItemEvents.rightClicked; "
            "player.right_click_block -> BlockEvents.rightClicked; "
            "block.broken -> BlockEvents.broken.",
            "teleport / spawn_particle / play_sound / grant_advancement and "
            "entity.killed are deferred in the KubeJS MVP (no guaranteed "
            "player context / non-trivial command emission).",
        ),
    ),
    "fabric": TargetCapability(
        target="fabric",
        registrations=frozenset({"item", "block", "tag"}),
        # Stage 5 is being validated against real 26.2 deps. Only what the
        # generated Java is *verified* to compile is marked supported; events
        # and actions are deferred with explicit errors until the build loop
        # proves each mapping.
        events=frozenset(),
        actions=frozenset(),
        notes=(
            "Fabric registrations compile against real 26.2 deps (loader "
            "0.19.3, fabric-api 0.156.0+26.2, official mappings). Events/actions "
            "are not yet verified in the build loop and are rejected explicitly.",
        ),
    ),
}


def capability_for(target: str) -> TargetCapability:
    cap = CAPABILITIES.get(target)
    if cap is None:
        raise KeyError(f"unknown target {target!r} (known: {', '.join(CAPABILITIES)})")
    return cap