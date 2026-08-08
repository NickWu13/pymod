"""Shared helpers for the pymod test suite (not collected by pytest)."""
from __future__ import annotations

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from pymod.dsl.parser import parse_source  # noqa: E402
from pymod.ir.builder import build  # noqa: E402

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


def parse_build(source: str, name: str = "<test>"):
    """Parse + build DSL source into an approved IR ModSpec."""
    return build(parse_source(source, filename=name), src_path=name)


def render(target: str, source: str, out_dir: Path) -> list:
    """Run the full checker+generator pipeline for ``target`` into out_dir.

    Returns the list of written file paths.  Raises on check errors.
    """
    from pymod.check import run as run_check
    from pymod.target import get_generator

    spec = parse_build(source)
    report = run_check(spec, target)
    assert report.is_clean(), report.render()
    gen = get_generator(target, spec, out_dir, game_version="26.2", pack_format=None)
    return gen.generate()


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")