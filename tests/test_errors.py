"""Error-contract tests: unsupported DSL must fail with a precise code.

Two channels are exercised:
  * the parse/build front end raises :class:`PyModError` subclasses whose
    ``code`` we assert (so error *identity* is part of the contract), and
  * the per-target checker reports collected issues (codes on :class:`Issue`).
"""
from __future__ import annotations

import pytest

from helpers import EXAMPLES, parse_build
from pymod.check import run as run_check
from pymod.errors import PyModError
from pymod.ir.builder import build
from pymod.dsl.parser import parse_source

HEAD = 'from pymod import mod\nmod(id="demo", name="Demo", version="1.0.0")\n'


def raises_code(source: str, expected: str):
    with pytest.raises(PyModError) as ei:
        parse_build(source)
    assert ei.value.code == expected, f"expected {expected!r}, got {ei.value.code!r}"


def build_ok(source: str):
    return build(parse_source(source, filename="<t>"), src_path="<t>")


# ------------------------------------------------------------------ front end


def test_syntax_error():
    raises_code("mod(id='x', name='X', version='1',\n", "syntax-error")


def test_unsupported_import():
    raises_code("import os\n", "unsupported-import")


def test_missing_header():
    raises_code("register('item', 'x')\n", "missing-header")


def test_bad_modid_uppercase():
    raises_code(HEAD.replace('id="demo"', 'id="Demo"'), "bad-modid")


def test_unknown_header_key():
    raises_code(HEAD.replace('version="1.0.0"', 'version="1.0.0", color="red"'), "unknown-header-key")


def test_unknown_register_kind():
    raises_code(HEAD + "register('thing', 'x')\n", "unknown-register-kind")


def test_register_name_invalid():
    raises_code(HEAD + "register('item', 'Ruby')\n", "register-name")


def test_duplicate_registration():
    raises_code(HEAD + "register('item', 'x')\nregister('item', 'x')\n", "duplicate-registration")


def test_unknown_event_kind():
    raises_code(
        HEAD + "@mod.on('bogus.event')\ndef h(ctx):\n    ctx.send_message('hi')\n",
        "unknown-event",
    )


def test_unknown_action():
    raises_code(
        HEAD + "@mod.on('player.use_item')\ndef h(ctx):\n    ctx.bogus()\n",
        "unknown-action",
    )


def test_bad_action_arity():
    raises_code(
        HEAD + "@mod.on('player.use_item')\ndef h(ctx):\n    ctx.give_item()\n",
        "bad-action-args",
    )


def test_bad_action_arg_type():
    raises_code(
        HEAD + "@mod.on('player.use_item')\ndef h(ctx):\n    ctx.give_item('minecraft:stick', 'one')\n",
        "bad-type",
    )


def test_unknown_guard_param():
    raises_code(
        HEAD
        + "@mod.on('player.use_item')\ndef h(ctx):\n"
        + "    if ctx.killer == 'x':\n        ctx.send_message('hi')\n",
        "unknown-param",
    )


def test_unsupported_or_condition():
    raises_code(
        HEAD
        + "@mod.on('player.use_item')\ndef h(ctx):\n"
        + "    if ctx.item == 'a' or ctx.item == 'b':\n        ctx.send_message('hi')\n",
        "unsupported-condition",
    )


def test_unsupported_statement():
    raises_code(
        HEAD + "@mod.on('player.use_item')\ndef h(ctx):\n    for i in range(3):\n        ctx.send_message('hi')\n",
        "unsupported-statement",
    )


# ------------------------------------------------------------------ checker


def test_checker_datapack_rejects_event():
    src = HEAD + "@mod.on('entity.killed')\ndef h(ctx):\n    ctx.send_message('x')\n"
    report = run_check(build_ok(src), "datapack")
    assert any(i.code == "target-unsupported-event" for i in report.errors)


def test_checker_kubejs_rejects_action():
    chaos = (EXAMPLES / "chaos.py").read_text(encoding="utf-8")
    report = run_check(build_ok(chaos), "kubejs")  # chaos uses play_sound
    assert any(i.code == "target-unsupported-action" for i in report.errors)


def test_checker_fabric_defers_events_and_actions():
    chaos = (EXAMPLES / "chaos.py").read_text(encoding="utf-8")
    report = run_check(build_ok(chaos), "fabric")
    codes = {i.code for i in report.errors}
    assert "target-unsupported-event" in codes
    assert "target-unsupported-action" in codes


def test_checker_datapack_clean():
    chaos = (EXAMPLES / "chaos.py").read_text(encoding="utf-8")
    report = run_check(build_ok(chaos), "datapack")
    assert report.is_clean()