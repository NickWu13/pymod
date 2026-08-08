"""Base code-target contract.

Every generator is a :class:`CodeTarget` that renders an approved
:class:`ModSpec` into files under its output directory.  Targets must be
*self-describing*: a generator should assert the capability matrix supports
what it is about to emit and raise :class:`~pymod.errors.TargetError` otherwise
(though the checker normally catches this earlier with a nicer report).
"""
from __future__ import annotations

import abc
from pathlib import Path

from ..ir.irnodes import ModSpec


class CodeTarget(abc.ABC):
    name: str  # stable id, e.g. "datapack"

    def __init__(self, spec: ModSpec, out_dir: Path) -> None:
        self.spec = spec
        self.out_dir = out_dir

    @abc.abstractmethod
    def generate(self) -> list[Path]:
        """Emit the target artifacts under :attr:`out_dir`.

        Returns the list of written file paths (for reporting and tests).
        """

    def write(self, rel: str, content: str) -> Path:
        path = self.out_dir / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        # newline="" keeps LF line endings byte-for-byte stable across platforms
        # and a single trailing LF makes every emitted file POSIX-clean, so
        # golden-file comparisons are deterministic.
        if not content.endswith("\n"):
            content += "\n"
        path.write_text(content, encoding="utf-8", newline="")
        return path