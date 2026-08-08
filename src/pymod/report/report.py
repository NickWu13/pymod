"""Issue/Report primitives shared by the checker and the CLI.

:class:`Issue` lives in :mod:`pymod.errors` (single definition used by both the
exception path and the collected-diagnostics path); this module adds the
:class:`Report` container and its human-readable rendering.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..errors import Issue  # re-export the one true Issue type

__all__ = ["Issue", "Report"]


@dataclass
class Report:
    issues: list[Issue] = field(default_factory=list)
    target: str | None = None

    @property
    def errors(self) -> list[Issue]:
        return [i for i in self.issues if i.severity == "error"]

    @property
    def warnings(self) -> list[Issue]:
        return [i for i in self.issues if i.severity == "warning"]

    def is_clean(self) -> bool:
        return not self.errors

    def add(self, issue: Issue) -> None:
        self.issues.append(issue)

    def add_error(self, code: str, message: str, loc: "SourceLoc | None" = None, suggestion: str | None = None) -> None:
        self.issues.append(Issue(code=code, message=message, loc=loc, severity="error", suggestion=suggestion))

    def render(self) -> str:
        """Render the report the way the CLI prints it (readable, greppable)."""
        lines: list[str] = []
        for issue in self.issues:
            head = issue.code
            loc = f"  @ {issue.loc}" if issue.loc else ""
            lines.append(f"[{issue.severity}] {head}: {issue.message}{loc}")
            if issue.suggestion:
                lines.append(f"       hint: {issue.suggestion}")
        if not lines:
            target = f" for target {self.target!r}" if self.target else ""
            lines.append(f"OK{target}: no problems found.")
        return "\n".join(lines)

    def __bool__(self) -> bool:
        return bool(self.issues)