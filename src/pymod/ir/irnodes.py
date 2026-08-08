"""The intermediate representation (IR).

The IR is the *sole* thing that reaches the code generators.  A generator never
sees raw Python ``ast`` nodes; it sees these normalized, checked, target-agnostic
objects.  Keeping the IR this way is what lets the Checker run once, before any
codegen, and lets each target apply its own capability matrix on top.

The IR deliberately does **not** try to mirror Python syntax 1:1.  A handler
body is reduced to a flat sequence of checked :class:`EventAction` objects, so a
generator never has to understand ``if``/``for``/expression trees again.  If the
DSL front end cannot reduce some construct to that form, the front end rejects
it (stage 2) instead of passing it through.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ._value import Value

# Re-export so callers get the value union from one place.
__all__ = [
    "Value",
    "SourceLoc",
    "ModInfo",
    "Registration",
    "Guard",
    "EventAction",
    "EventHandler",
    "ModSpec",
    "TARGETS",
]

#: target identifiers the CLI and capability layer understand.  Order also
#: expresses generation priority (datapack is the safest/first).
TARGETS = ("datapack", "kubejs", "fabric")


@dataclass(frozen=True)
class SourceLoc:
    file: str
    line: int
    col: int = 0
    context: str = ""


@dataclass(frozen=True)
class ModInfo:
    """The mod's header block."""

    id: str
    name: str
    version: str
    description: str = ""
    loc: SourceLoc = field(default_factory=lambda: SourceLoc("", 0))


@dataclass(frozen=True)
class Registration:
    """One declarative registration: an item, block, tag, ..."""

    kind: str
    name: str  # path inside the mod namespace, e.g. "ruby"
    props: tuple[tuple[str, Value], ...] = ()
    loc: SourceLoc = field(default_factory=lambda: SourceLoc("", 0))

    @property
    def id(self) -> str:
        return self.name  # namespaced id is <modid>:<name>, resolved by builder


@dataclass(frozen=True)
class Guard:
    """One conjunctive condition attached to an action.

    ``lhs`` is either a handler parameter (``lhs_kind="param"``) or a literal
    value.  ``op`` is one of ``== != < <= > >= in not-in``.  Guards are the only
    control flow the IR carries; everything more complex is rejected earlier.
    """

    lhs_kind: str  # "param" | "lit"
    lhs: Value
    op: str
    rhs: Value
    loc: SourceLoc = field(default_factory=lambda: SourceLoc("", 0))


@dataclass(frozen=True)
class EventAction:
    """One reduced, checked action inside a handler body.

    ``guards`` is the accumulated AND of every enclosing ``if`` condition, so a
    generator does not have to understand the source's control flow.
    """

    op: str  # e.g. "send_message", "give_item"
    args: tuple[Value, ...]
    guards: tuple[Guard, ...] = ()
    loc: SourceLoc = field(default_factory=lambda: SourceLoc("", 0))


@dataclass(frozen=True)
class EventHandler:
    kind: str  # e.g. "player.use_item"
    handler_name: str
    params: tuple[str, ...] = ()
    body: tuple[EventAction, ...] = ()
    loc: SourceLoc = field(default_factory=lambda: SourceLoc("", 0))


@dataclass(frozen=True)
class ModSpec:
    info: ModInfo
    registrations: tuple[Registration, ...] = ()
    events: tuple[EventHandler, ...] = ()
    src: str = ""

    def all_ids(self) -> tuple[str, ...]:
        out: list[str] = []
        for r in self.registrations:
            out.append(f"{self.info.id}:{r.name}")
        out.append(f"{self.info.id}:{self.info.id}")  # pack id
        return tuple(out)