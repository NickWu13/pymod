"""The checker: target-capability validation on top of IR.

The DSL parser and IR builder have already validated that a program is
*germane* (known ops, known events, correct types).  The checker adds the
per-target gate: which of those known things the *selected output target* can
actually express.  It collects everything wrong at once into a :class:`Report`
so ``pymod check`` can list all problems rather than dying on the first.

Command-ordering guarantee: ``check`` always runs before codegen; a generator
never sees an IR the checker has not approved for its target.
"""
from __future__ import annotations

from ..ir.capability import capability_for, TargetCapability
from ..ir.irnodes import ModSpec
from ..report.report import Issue, Report


def run(spec: ModSpec, target: str) -> Report:
    """Validate ``spec`` against ``target`` and return a :class:`Report`."""
    cap = capability_for(target)
    issues: list[Issue] = []

    for reg in spec.registrations:
        if not cap.can_register(reg.kind):
            issues.append(
                Issue(
                    code="target-unsupported-registration",
                    message=(
                        f"target {target!r} does not support registering {reg.kind} "
                        f"{reg.name!r}."
                    ),
                    loc=reg.loc,
                )
            )

    for ev in spec.events:
        if not cap.can_emit_event(ev.kind):
            issues.append(
                Issue(
                    code="target-unsupported-event",
                    message=(
                        f"target {target!r} does not support the {ev.kind!r} event "
                        f"(handler {ev.handler_name!r})."
                    ),
                    loc=ev.loc,
                )
            )
        for action in ev.body:
            if not cap.can_emit_action(action.op):
                issues.append(
                    Issue(
                        code="target-unsupported-action",
                        message=(
                            f"target {target!r} does not support the ctx.{action.op}(...) "
                            f"action (in handler {ev.handler_name!r} for {ev.kind!r})."
                        ),
                        loc=action.loc,
                    )
                )

    report = Report(issues, target=target)
    _attach_notes(report, cap)
    return report


def _attach_notes(report: Report, cap: TargetCapability) -> None:
    if not report.is_clean():
        return
    # notes may be a plain string (string-literal concatenation) or a tuple
    notes = [cap.notes] if isinstance(cap.notes, str) else cap.notes
    for note in notes:
        report.add(Issue(code="capability-note", message=note, severity="info"))