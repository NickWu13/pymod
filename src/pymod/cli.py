"""The ``pymod`` command-line interface.

Pipeline discipline: both commands parse source -> build IR -> (for generate)
check against the target -> run the target generator.  The checker always runs
before codegen, so bad IR for a target never reaches a generator.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .errors import PyModError
from .ir import TARGETS
from .ir.builder import build as build_ir
from .dsl.parser import parse_source
from .check import run as run_check
from .registry.gameprofile import default_game_version
from .target import get_generator


def _load_spec(path: Path) -> "object":
    source = path.read_text(encoding="utf-8")
    program = parse_source(source, filename=str(path))
    return build_ir(program, src_path=str(path))


def _err(msg: str) -> int:
    print(f"error: {msg}", file=sys.stderr)
    return 1


def cmd_check(args: argparse.Namespace) -> int:
    try:
        spec = _load_spec(Path(args.file))
    except PyModError as e:
        return _err(str(e))

    if args.target:
        report = run_check(spec, args.target)
        print(report.render())
        return 0 if report.is_clean() else 1

    # no target: core check already succeeded during build
    n_reg = len(spec.registrations)
    n_ev = len(spec.events)
    print(f"OK: {Path(args.file).name} is valid pymod DSL "
          f"({n_reg} registration(s), {n_ev} event handler(s)).")
    print("Run with --target <datapack|kubejs|fabric> to check target support.")
    return 0


def cmd_generate(args: argparse.Namespace) -> int:
    if args.target not in TARGETS:
        return _err(f"unknown target {args.target!r}; allowed: {', '.join(TARGETS)}")

    file = Path(args.file)
    out = Path(args.out)
    try:
        spec = _load_spec(file)
        report = run_check(spec, args.target)
        if not report.is_clean():
            print(report.render())
            return 1
        gen = get_generator(
            args.target,
            spec,
            out,
            game_version=args.game,
            pack_format=args.pack_format,
        )
        written = gen.generate()
    except PyModError as e:
        return _err(str(e))
    except LookupError as e:
        return _err(str(e))

    print(f"generated target {args.target!r} -> {out}")
    for p in written:
        print(f"  wrote {p}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pymod",
        description="Compile a restricted Python DSL into Minecraft "
        "Data Packs, KubeJS scripts, and compilable Fabric Java mods.",
    )
    parser.add_argument("--version", action="version", version=f"pymod {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p_check = sub.add_parser("check", help="validate a DSL file")
    p_check.add_argument("file", help="path to the .py DSL mod file")
    p_check.add_argument(
        "-t",
        "--target",
        choices=TARGETS,
        default=None,
        help="also check that the target supports this mod",
    )
    p_check.set_defaults(func=cmd_check)

    p_gen = sub.add_parser("generate", help="emit a target artifact")
    p_gen.add_argument("file", help="path to the .py DSL mod file")
    p_gen.add_argument("-t", "--target", required=True, choices=TARGETS, help="output target")
    p_gen.add_argument("-o", "--out", required=True, help="output directory")
    p_gen.add_argument(
        "--game", default=None, help="Minecraft version profile (default: the project default)"
    )
    p_gen.add_argument(
        "--pack-format",
        type=int,
        default=None,
        help="override the data-pack pack_format number (the 26.2 value is "
        "pending verification; supply it explicitly to generate)",
    )
    p_gen.set_defaults(func=cmd_generate)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    game = getattr(args, "game", None) or default_game_version()
    setattr(args, "game", game)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())