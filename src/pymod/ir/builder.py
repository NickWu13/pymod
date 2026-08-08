"""Lower a validated :class:`Program` into the :class:`ModSpec` IR.

This is the semantic gate.  The parser has already rejected foreign syntax;
here we validate meaning: known event kinds, known action ops, argument counts
and types, registration props, duplicate ids, and ctx parameter references.
Anything that does not satisfy the capability vocabulary is an :class:`IRError`
with a precise location -- it never reaches a generator.
"""
from __future__ import annotations

from ..errors import IRError, SourceLoc
from ._value import Value
from .capability import ACTION_SPECS, EVENT_SPECS, REGISTRATION_KINDS, REGISTRATION_PROPS
from .irnodes import EventAction, EventHandler, Guard, ModInfo, ModSpec, Registration
from ..dsl.parser import ActionCallNode, HandlerNode, Program, RegNode

_NUMERIC = ("int", "float")


def build(program: Program, src_path: str = "") -> ModSpec:
    header = program.header
    if header is None:
        raise IRError("missing-header", "no mod(...) header in program")

    # ---- registrations ----------------------------------------------------
    seen: set[str] = set()
    regs: list[Registration] = []
    for node in program.registrations:
        _validate_registration(node, seen)
        regs.append(_lower_registration(node, header.id))

    # ---- handlers ---------------------------------------------------------
    handlers: list[EventHandler] = []
    for node in program.handlers:
        handlers.append(_lower_handler(node, header.id, regs))

    return ModSpec(
        info=ModInfo(
            id=header.id,
            name=header.name,
            version=header.version,
            description=header.description,
            loc=header.loc,
        ),
        registrations=tuple(regs),
        events=tuple(handlers),
        src=src_path,
    )


# ---------------------------------------------------------------------------
# registrations
# ---------------------------------------------------------------------------


def _validate_registration(node: RegNode, seen: set[str]) -> None:
    if node.kind not in REGISTRATION_KINDS:
        raise IRError(
            "unknown-register-kind",
            f"register kind {node.kind!r} is not supported; allowed: "
            + ", ".join(sorted(REGISTRATION_KINDS)),
            loc=node.loc,
        )
    key = f"{node.kind}:{node.name}"
    if key in seen:
        raise IRError(
            "duplicate-registration",
            f"{node.kind} {node.name!r} is registered more than once",
            loc=node.loc,
        )
    seen.add(key)

    schema = REGISTRATION_PROPS[node.kind]
    for prop, value in node.props:
        if prop not in schema:
            raise IRError(
                "unknown-prop",
                f"{node.kind} registration does not accept prop {prop!r}; allowed: "
                + ", ".join(sorted(schema)),
                loc=node.loc,
            )
        _check_type(prop, value, schema[prop], node.loc)


def _lower_registration(node: RegNode, modid: str) -> Registration:
    props: list[tuple[str, Value]] = []
    registered = _registry_names_from(node)
    for prop, value in node.props:
        t = REGISTRATION_PROPS[node.kind][prop]
        props.append((prop, _coerce(value, t, modid, registered, node.loc)))
    return Registration(kind=node.kind, name=node.name, props=tuple(props), loc=node.loc)


def _registry_names_from(node: RegNode) -> frozenset[str]:
    # names registered in the same file that an id prop may reference
    return frozenset()


# ---------------------------------------------------------------------------
# handlers
# ---------------------------------------------------------------------------


def _lower_handler(node: HandlerNode, modid: str, regs: list[Registration]) -> EventHandler:
    if node.kind not in EVENT_SPECS:
        raise IRError(
            "unknown-event",
            f"event kind {node.kind!r} is not supported; allowed: "
            + ", ".join(sorted(EVENT_SPECS)),
            loc=node.loc,
        )
    params = EVENT_SPECS[node.kind].params
    registered = frozenset(r.name for r in regs)

    body: list[EventAction] = []
    for action_node in node.body:
        body.append(_lower_action(action_node, params, modid, registered))

    return EventHandler(
        kind=node.kind,
        handler_name=node.handler_name,
        params=params,
        body=tuple(body),
        loc=node.loc,
    )


def _lower_action(
    action_node: ActionCallNode, params: tuple[str, ...], modid: str, registered: frozenset[str]
) -> EventAction:
    spec = ACTION_SPECS.get(action_node.op)
    if spec is None:
        raise IRError(
            "unknown-action",
            f"unknown action ctx.{action_node.op}(...); allowed: "
            + ", ".join(sorted(ACTION_SPECS)),
            loc=action_node.loc,
        )

    nargs = len(action_node.args)
    if nargs < spec.required or nargs > len(spec.arg_names):
        if spec.required == len(spec.arg_names):
            expected = f"exactly {len(spec.arg_names)} arguments"
        else:
            expected = f"{spec.required}..{len(spec.arg_names)} arguments"
        raise IRError(
            "bad-action-args",
            f"ctx.{action_node.op}(...) expects {expected}, got {nargs}",
            loc=action_node.loc,
        )

    args: list[Value] = []
    for i, (value, type_tag) in enumerate(zip(action_node.args, spec.arg_types)):
        args.append(_coerce(value, type_tag, modid, registered, action_node.loc, arg_name=spec.arg_names[i]))

    guards = tuple(_lower_guard(g, params, action_node.loc) for g in action_node.guards)

    return EventAction(op=action_node.op, args=tuple(args), guards=guards, loc=action_node.loc)


def _lower_guard(raw: tuple, params: tuple[str, ...], loc: SourceLoc) -> Guard:
    lhs_kind, lhs, op, rhs = raw
    if lhs_kind == "param":
        if lhs not in params:
            raise IRError(
                "unknown-param",
                f"ctx.{lhs} is not a parameter of this event; available: "
                + ", ".join(params),
                loc=loc,
            )
        if not isinstance(rhs, (str, int, float, bool)):
            raise IRError(
                "bad-condition",
                "condition compares a ctx parameter to a literal; "
                "literal-to-literal conditions are not useful",
                loc=loc,
            )
    return Guard(lhs_kind=lhs_kind, lhs=lhs, op=op, rhs=rhs, loc=loc)


# ---------------------------------------------------------------------------
# value coercion / type checking
# ---------------------------------------------------------------------------


def _coerce(
    value: object,
    type_tag: str,
    modid: str,
    registered: frozenset[str],
    loc: SourceLoc,
    arg_name: str | None = None,
) -> Value:
    what = f"argument {arg_name!r}" if arg_name else "value"
    if type_tag == "id":
        if not isinstance(value, str):
            raise IRError("bad-type", f"{what} must be an item/block id string", loc=loc)
        return _resolve_id(value, modid, registered)
    if type_tag == "id-list":
        if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
            raise IRError("bad-type", f"{what} must be a list of id strings", loc=loc)
        return tuple(_resolve_id(v, modid, registered) for v in value)
    if type_tag == "str":
        if not isinstance(value, str):
            raise IRError("bad-type", f"{what} must be a string", loc=loc)
        return value
    if type_tag == "int":
        if isinstance(value, bool) or not isinstance(value, int):
            raise IRError("bad-type", f"{what} must be an integer", loc=loc)
        return value
    if type_tag == "float":
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise IRError("bad-type", f"{what} must be a number", loc=loc)
        return value
    if type_tag == "bool":
        if not isinstance(value, bool):
            raise IRError("bad-type", f"{what} must be true or false", loc=loc)
        return value
    raise IRError("internal", f"unknown type tag {type_tag!r}", loc=loc)


def _resolve_id(value: str, modid: str, registered: frozenset[str]) -> str:
    if ":" in value:
        return value
    if value in registered:
        return f"{modid}:{value}"
    return f"minecraft:{value}"


def _check_type(prop: str, value: object, type_tag: str, loc: SourceLoc) -> None:
    _coerce(value, type_tag, "x", frozenset(), loc, arg_name=prop)