"""Source locations and the exception hierarchy used across the pymod pipeline.

Every error that can be attributed to user source carries a :class:`SourceLoc`
so the CLI can print ``file:line:col`` and the offending line.  Nothing in the
codegen path ever raises a bare ``Exception`` -- it raises :class:`PyModError`
(or a subclass) so the CLI can render it uniformly.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SourceLoc:
    """A position inside a user-authored ``.py`` DSL file."""

    file: str
    line: int
    col: int = 0
    context: str = ""  # the source line, captured for error display

    def __str__(self) -> str:
        return f"{self.file}:{self.line}:{self.col}"


@dataclass(frozen=True)
class Issue:
    """A single diagnostic produced by the checker.

    ``code`` is a stable machine-readable id (e.g. ``"unknown-op"``) used by
    tests and by tooling; ``message`` is human readable and may span lines.
    """

    code: str
    message: str
    loc: SourceLoc | None = None
    severity: str = "error"  # "error" | "warning" | "info"
    suggestion: str | None = None
    details: tuple[str, ...] = field(default_factory=tuple)


class PyModError(Exception):
    """Base class for all pymod-internal errors."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        loc: SourceLoc | None = None,
        suggestion: str | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.loc = loc
        self.suggestion = suggestion

    def as_issue(self) -> Issue:
        return Issue(
            code=self.code,
            message=self.message,
            loc=self.loc,
            severity="error",
            suggestion=self.suggestion,
        )

    def __str__(self) -> str:
        prefix = f"{self.loc}: " if self.loc else ""
        text = f"{prefix}[{self.code}] {self.message}"
        if self.suggestion:
            text += f"\n  hint: {self.suggestion}"
        return text


class ParseError(PyModError):
    """Raised by the DSL front end when source is syntactically rejected."""


class IRError(PyModError):
    """Raised while lowering validated Python AST into IR."""


class CheckError(PyModError):
    """Raised when lowering to a target finds an unsupported capability."""


class TargetError(PyModError):
    """Raised by a code generator when it cannot emit a target artifact."""
