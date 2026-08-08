"""The DSL front end.

Reads user ``.py`` source, parses it with CPython's ``ast``, then *rejects*
anything outside the documented DSL subset.  What survives is a small,
target-agnostic ``Program`` whose nodes still carry :class:`SourceLoc` so later
stages can point at the exact offending line.

The whitelist is deliberately narrow.  If a construct is not listed here it is
a hard :class:`ParseError`, not silently dropped.  See ``docs/dsl.md`` for the
user-facing grammar.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass, field
from typing import Iterable

from ..errors import ParseError, SourceLoc

# ---------------------------------------------------------------------------
# Raw (pre-IR) node shapes produced by this module.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class HeaderNode:
    id: str
    name: str
    version: str
    description: str
    loc: SourceLoc


@dataclass(frozen=True)
class RegNode:
    kind: str
    name: str
    props: tuple[tuple[str, object], ...]  # prop name -> evaluated python value
    loc: SourceLoc


@dataclass(frozen=True)
class ActionCallNode:
    op: str
    args: tuple[object, ...]  # evaluated python values
    guards: tuple[tuple, ...]  # raw guard tuples (lhs_kind, lhs, op, rhs)
    loc: SourceLoc


@dataclass(frozen=True)
class HandlerNode:
    kind: str
    handler_name: str
    params: tuple[str, ...]
    body: tuple[ActionCallNode, ...]
    loc: SourceLoc


@dataclass(frozen=True)
class Program:
    header: HeaderNode | None
    registrations: tuple[RegNode, ...] = ()
    handlers: tuple[HandlerNode, ...] = ()
    src: str = ""


# ---------------------------------------------------------------------------
# primitive helpers
# ---------------------------------------------------------------------------


def _loc_of(node: ast.AST, fallback: SourceLoc) -> SourceLoc:
    lineno = getattr(node, "lineno", None)
    if lineno is not None:
        return SourceLoc(fallback.file, lineno, node.col_offset)
    return fallback


def _src_line(src: str, lineno: int) -> str:
    try:
        return src.splitlines()[lineno - 1].strip()
    except Exception:
        return ""


def _line_loc(src: str, node: ast.AST, fallback_file: str) -> SourceLoc:
    return SourceLoc(fallback_file, node.lineno, node.col_offset, _src_line(src, node.lineno))


# ---------------------------------------------------------------------------
# Literal evaluation
# ---------------------------------------------------------------------------

_LITERAL_TYPES = (str, int, float, bool, type(None))


def _eval_literal(node: ast.AST, loc: SourceLoc) -> object:
    """Evaluate a node that must be a scalar literal (or a list of them)."""
    if isinstance(node, ast.Constant):
        if isinstance(node.value, _LITERAL_TYPES):
            return node.value
        raise ParseError(
            "unsupported-literal",
            f"literal {node.value!r} is not allowed (strings, numbers, booleans, None only)",
            loc=loc,
        )
    if isinstance(node, ast.List):
        return [_eval_literal(e, _loc_of(e, loc)) for e in node.elts]
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
        v = _eval_literal(node.operand, _loc_of(node.operand, loc))
        if isinstance(v, (int, float)):
            return -v if isinstance(node.op, ast.USub) else v
    raise ParseError(
        "unsupported-expression",
        f"expression is not a literal (got {node.__class__.__name__}); "
        "MVP supports string/number/bool literals and lists of them",
        loc=loc,
    )


def _eval_literal_or_name(node: ast.AST, loc: SourceLoc, locals_: dict[str, object]) -> object:
    """Evaluate a literal, or resolve a previously assigned local variable."""
    if isinstance(node, ast.Name):
        if node.id in locals_:
            return locals_[node.id]
        raise ParseError(
            "unknown-name",
            f"name {node.id!r} is not defined in this handler; "
            "use ctx.<param> for event parameters or assign a literal first",
            loc=loc,
        )
    return _eval_literal(node, loc)


# ---------------------------------------------------------------------------
# Guards: conditions reduce to conjuncts of simple comparisons.
# ---------------------------------------------------------------------------

_NEGATIONS = {"==": "!=", "!=": "==", "<": ">=", "<=": ">", ">": "<=", ">=": "<"}


def _cmp_op(op: ast.cmpop) -> str:
    for cls, name in (
        (ast.Eq, "=="),
        (ast.NotEq, "!="),
        (ast.Lt, "<"),
        (ast.LtE, "<="),
        (ast.Gt, ">"),
        (ast.GtE, ">="),
    ):
        if isinstance(op, cls):
            return name
    raise ParseError(
        "unsupported-condition",
        f"comparison operator {op.__class__.__name__} is not supported (== != < <= > >= only)",
    )


def _guard_from_compare(node: ast.Compare, loc: SourceLoc) -> tuple:
    if len(node.ops) != 1:
        raise ParseError(
            "unsupported-condition", "chained comparisons (a < b < c) are not supported in MVP", loc=loc
        )
    op = _cmp_op(node.ops[0])
    left, right = node.left, node.comparators[0]
    if isinstance(left, ast.Attribute) and isinstance(left.value, ast.Name) and left.value.id == "ctx":
        lhs_kind, lhs = "param", left.attr
    else:
        lhs_kind, lhs = "lit", _eval_literal(left, _loc_of(left, loc))
    rhs = _eval_literal(right, _loc_of(right, loc))
    return (lhs_kind, lhs, op, rhs)


def _build_guards(node: ast.AST, loc: SourceLoc) -> list[tuple]:
    """Reduce a condition to a list of conjunctive guard tuples.

    Supports ``param OP lit``, ``lit OP lit``, and ``and`` combinations thereof.
    ``or`` / ``not`` / parentheses are rejected in MVP (documented limitation).
    """
    if isinstance(node, ast.Compare):
        return [_guard_from_compare(node, loc)]
    if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.And):
        out: list[tuple] = []
        for v in node.values:
            out.extend(_build_guards(v, loc))
        return out
    if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.Or):
        raise ParseError(
            "unsupported-condition", "'or' in conditions is not supported in MVP", loc=loc
        )
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        raise ParseError(
            "unsupported-condition",
            "'not' in conditions is not supported in MVP (write the negated comparison)",
            loc=loc,
        )
    raise ParseError(
        "unsupported-condition",
        "unsupported condition expression; use simple comparisons with 'and'",
        loc=loc,
    )


def _negate_guard(g: tuple, loc: SourceLoc) -> tuple:
    lhs_kind, lhs, op, rhs = g
    if op in _NEGATIONS:
        return (lhs_kind, lhs, _NEGATIONS[op], rhs)
    raise ParseError(
        "unsupported-condition",
        f"cannot build an 'else' branch for operator {op!r}; use a plain comparison",
        loc=loc,
    )


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

_MOD_KWARGS = ("id", "name", "version", "description")


def parse_source(source: str, filename: str = "<string>") -> Program:
    """Parse and whitelist user DSL source into a :class:`Program`."""
    try:
        tree = ast.parse(source, filename=filename)
    except SyntaxError as e:
        loc = SourceLoc(filename, e.lineno or 0, e.offset or 0, _src_line(source, e.lineno or 0))
        raise ParseError("syntax-error", f"invalid Python syntax: {e.msg}", loc=loc) from e

    header: HeaderNode | None = None
    regs: list[RegNode] = []
    handlers: list[HandlerNode] = []

    for node in tree.body:
        loc = _line_loc(source, node, filename)

        if isinstance(node, ast.ImportFrom) and node.module == "pymod":
            _check_import(node, loc)
            continue
        if isinstance(node, ast.Import):
            raise ParseError("unsupported-import", "only 'from pymod import mod' is allowed", loc=loc)

        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            call = node.value
            name = _call_name(call, loc)
            if name == "mod":
                header = _parse_header(call, loc)
                continue
            if name == "register":
                regs.append(_parse_register(call, loc))
                continue
            raise ParseError(
                "unsupported-call",
                f"unknown top-level call {name!r}; use mod(...), register(...), or @mod.on(...)",
                loc=loc,
            )

        if isinstance(node, ast.FunctionDef):
            handlers.append(_parse_handler(node, source, loc))
            continue

        raise ParseError(
            "unsupported-statement",
            f"top-level {node.__class__.__name__} is not part of the DSL; "
            "only mod(...), register(...), @mod.on(...) and the pymod import are allowed",
            loc=loc,
        )

    if header is None:
        raise ParseError("missing-header", "the file must start with a mod(...) header", loc=None)

    return Program(header=header, registrations=tuple(regs), handlers=tuple(handlers), src=source)


def _check_import(node: ast.ImportFrom, loc: SourceLoc) -> None:
    if node.names and node.names[0].name == "*":
        return
    if tuple(a.asname or a.name for a in node.names) != ("mod",):
        raise ParseError("unsupported-import", "only 'from pymod import mod' is allowed", loc=loc)


def _call_name(call: ast.Call, loc: SourceLoc) -> str:
    if isinstance(call.func, ast.Name):
        return call.func.id
    if (
        isinstance(call.func, ast.Attribute)
        and isinstance(call.func.value, ast.Name)
        and call.func.value.id == "mod"
    ):
        return f"mod.{call.func.attr}"
    raise ParseError("unsupported-call", "malformed call; use mod(...) or register(...)", loc=loc)


def _parse_header(call: ast.Call, loc: SourceLoc) -> HeaderNode:
    if call.args:
        raise ParseError("header-args", "mod(...) takes keyword arguments only", loc=loc)
    kwargs: dict[str, object] = {}
    for kw in call.keywords:
        if kw.arg not in _MOD_KWARGS:
            raise ParseError(
                "unknown-header-key",
                f"unknown mod(...) option {kw.arg!r}; allowed: {', '.join(_MOD_KWARGS)}",
                loc=_loc_of(kw.value, loc),
            )
        kwargs[kw.arg] = _eval_literal(kw.value, _loc_of(kw.value, loc))
    for req in ("id", "name", "version"):
        if req not in kwargs:
            raise ParseError("missing-header-key", f"mod(...) requires {req!r}", loc=loc)
    modid = kwargs["id"]
    if not isinstance(modid, str) or not _valid_id(modid):
        raise ParseError(
            "bad-modid",
            f"mod id {modid!r} must be a lowercase [a-z0-9_.-] string starting with a letter",
            loc=loc,
        )
    return HeaderNode(
        id=modid,
        name=str(kwargs["name"]),
        version=str(kwargs["version"]),
        description=str(kwargs.get("description", "")),
        loc=loc,
    )


def _parse_register(call: ast.Call, loc: SourceLoc) -> RegNode:
    if len(call.args) < 2:
        raise ParseError(
            "register-args", "register(kind, name, **props) needs at least kind and name", loc=loc
        )
    kind = _eval_literal(call.args[0], _loc_of(call.args[0], loc))
    name = _eval_literal(call.args[1], _loc_of(call.args[1], loc))
    if not isinstance(kind, str):
        raise ParseError("register-kind", "register kind must be a string", loc=loc)
    if not isinstance(name, str):
        raise ParseError("register-name", "registration name must be a string", loc=loc)
    if kind == "tag":
        # tags carry a category prefix like "blocks/magic" or "items/foo"
        if "/" in name and not _valid_tag_name(name):
            raise ParseError(
                "register-name",
                f"tag name {name!r} must be <category>/<name> with lowercase [a-z0-9_.-] segments "
                "(categories: items, blocks, functions, entity_types)",
                loc=loc,
            )
        if "/" not in name and not _valid_id(name):
            raise ParseError(
                "register-name",
                f"tag name {name!r} must be a lowercase [a-z0-9_.-] string",
                loc=loc,
            )
    elif not _valid_id(name):
        raise ParseError(
            "register-name",
            f"registration name {name!r} must be a lowercase [a-z0-9_.-] string",
            loc=loc,
        )
    props: list[tuple[str, object]] = []
    for kw in call.keywords:
        if kw.arg is None:
            raise ParseError("register-props", "**kwargs are not allowed in register(...)", loc=loc)
        props.append((kw.arg, _eval_literal(kw.value, _loc_of(kw.value, loc))))
    return RegNode(kind=kind, name=name, props=tuple(props), loc=loc)


def _parse_handler(node: ast.FunctionDef, source: str, loc: SourceLoc) -> HandlerNode:
    kind = _decorator_kind(node, loc)

    if node.returns is not None:
        raise ParseError("handler-signature", "handler must not declare a return annotation", loc=loc)
    args = node.args
    if (
        args.vararg
        or args.kwarg
        or args.kwonlyargs
        or args.defaults
        or args.kw_defaults
        or args.posonlyargs
    ):
        raise ParseError(
            "handler-signature", "handler signature must be exactly def name(ctx):", loc=loc
        )
    if len(args.args) != 1 or args.args[0].arg != "ctx":
        raise ParseError("handler-signature", "handler signature must be exactly def name(ctx):", loc=loc)

    body_stmts = node.body
    if body_stmts and isinstance(body_stmts[0], ast.Expr) and isinstance(body_stmts[0].value, ast.Constant):
        body_stmts = body_stmts[1:]  # tolerate a leading docstring

    actions = _walk_body(body_stmts, loc, source, filename=loc.file)

    return HandlerNode(
        kind=kind,
        handler_name=node.name,
        params=("ctx",),
        body=tuple(actions),
        loc=loc,
    )


def _decorator_kind(node: ast.FunctionDef, loc: SourceLoc) -> str:
    if len(node.decorator_list) != 1:
        raise ParseError(
            "handler-decorator",
            "event handlers need exactly one @mod.on('event.kind') decorator",
            loc=loc,
        )
    dec = node.decorator_list[0]
    if not (
        isinstance(dec, ast.Call)
        and isinstance(dec.func, ast.Attribute)
        and isinstance(dec.func.value, ast.Name)
        and dec.func.value.id == "mod"
        and dec.func.attr == "on"
        and len(dec.args) == 1
        and not dec.keywords
    ):
        raise ParseError(
            "handler-decorator",
            "decorator must be exactly @mod.on('event.kind') with one string argument",
            loc=_loc_of(dec, loc),
        )
    kind = _eval_literal(dec.args[0], _loc_of(dec.args[0], loc))
    if not isinstance(kind, str) or "." not in kind:
        raise ParseError(
            "handler-decorator",
            f"event kind {kind!r} must look like 'category.name' (e.g. 'player.use_item')",
            loc=_loc_of(dec.args[0], loc),
        )
    return kind


def _walk_body(stmts: list[ast.stmt], base_loc: SourceLoc, source: str, filename: str) -> list[ActionCallNode]:
    """Lower handler statements to action calls, resolving local vars and if/else."""
    locals_: dict[str, object] = {}
    out: list[ActionCallNode] = []
    for stmt in stmts:
        loc = _line_loc(source, stmt, filename)
        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
            out.append(_lower_call(stmt.value, loc, locals_, ()))
            continue
        if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name):
            locals_[stmt.targets[0].id] = _eval_literal(stmt.value, _loc_of(stmt.value, loc))
            continue
        if isinstance(stmt, ast.If):
            out.extend(_lower_if(stmt, source, filename, loc, locals_))
            continue
        raise ParseError(
            "unsupported-statement",
            f"{stmt.__class__.__name__} inside a handler is not supported in MVP; "
            "use ctx.<action>(...), if/else with simple comparisons, or literal assignment",
            loc=loc,
        )
    return out


def _lower_if(stmt: ast.If, source: str, filename: str, loc: SourceLoc, locals_: dict) -> list[ActionCallNode]:
    guards = _build_guards(stmt.test, loc)
    out: list[ActionCallNode] = []
    out.extend(_walk_guarded(stmt.body, source, filename, loc, locals_, tuple(guards)))
    if stmt.orelse:
        if len(guards) != 1:
            raise ParseError(
                "unsupported-condition",
                "'else' with a compound 'and' condition is not supported in MVP",
                loc=loc,
            )
        neg = _negate_guard(guards[0], loc)
        out.extend(_walk_guarded(stmt.orelse, source, filename, loc, locals_, (neg,)))
    return out


def _walk_guarded(
    stmts: list[ast.stmt],
    source: str,
    filename: str,
    base_loc: SourceLoc,
    locals_: dict[str, object],
    guards: tuple,
) -> list[ActionCallNode]:
    sub = locals_.copy()  # scope: assignments inside a branch do not leak out
    out: list[ActionCallNode] = []
    for stmt in stmts:
        loc = _line_loc(source, stmt, filename)
        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
            out.append(_lower_call(stmt.value, loc, sub, guards))
            continue
        if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name):
            sub[stmt.targets[0].id] = _eval_literal(stmt.value, _loc_of(stmt.value, loc))
            continue
        raise ParseError(
            "unsupported-statement",
            f"nested {stmt.__class__.__name__} is not supported in MVP; "
            "only action calls and literal assignment are allowed inside branches",
            loc=loc,
        )
    return out


def _lower_call(call: ast.Call, loc: SourceLoc, locals_: dict, guards: tuple) -> ActionCallNode:
    func = call.func
    if not (
        isinstance(func, ast.Attribute)
        and isinstance(func.value, ast.Name)
        and func.value.id == "ctx"
    ):
        raise ParseError(
            "unsupported-call",
            "only ctx.<action>(...) calls are allowed inside handlers",
            loc=loc,
        )
    if call.keywords:
        raise ParseError(
            "unsupported-call",
            "keyword arguments on ctx actions are not supported in MVP; pass positional literals",
            loc=loc,
        )
    args = tuple(_eval_literal_or_name(a, _loc_of(a, loc), locals_) for a in call.args)
    return ActionCallNode(op=func.attr, args=args, guards=guards, loc=loc)


def _valid_id(s: str) -> bool:
    return bool(s) and s[0].isalpha() and all(
        c.isascii() and (c.islower() or c.isdigit() or c in "_.-") for c in s
    )


def _valid_tag_name(s: str) -> bool:
    cat, _, base = s.rpartition("/")
    return bool(cat) and bool(base) and _valid_id(cat) and _valid_id(base)


def _loc(source: str, node: ast.AST, filename: str) -> SourceLoc:
    return _line_loc(source, node, filename)