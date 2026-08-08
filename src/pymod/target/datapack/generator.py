"""Data Pack generator.

Emits a Minecraft data pack (pack.mcmeta + data/<modid>/...) from an IR that
the checker has already approved for this target.

MVP honesty rules (documented in ``docs/targets.md``):
  * ``tag`` registrations produce real tag JSON files.
  * ``item``/``block`` registrations are *metadata*: a data pack alone cannot
    add new game content, so they are recorded as a manifest note, not files.
  * ``player.use_item`` and ``player.right_click_block`` events are simulated
    with the ``item_used_on_block`` advancement trigger whose reward function
    runs the actions.  Reward functions fire once per player -- a documented
    limitation.
  * Any guard the advancement predicate cannot express (anything other than an
    ``item == ...`` equality) is a hard :class:`TargetError`, not a silent drop.
"""
from __future__ import annotations

import json
from pathlib import Path

from ...errors import TargetError
from ...ir._value import value_to_str
from ...ir.capability import capability_for
from ...ir.irnodes import Guard, ModSpec
from ...registry.gameprofile import GameProfile, profile_for
from ..base import CodeTarget

# advancement trigger per supported event kind
_TRIGGER = {
    "player.use_item": "minecraft:item_used_on_block",
    "player.right_click_block": "minecraft:item_used_on_block",
}

_META = {
    "released": "https://minecraft.wiki/w/Java_Edition_26.2",
    "version": "26.2",
}


class DataPackTarget(CodeTarget):
    name = "datapack"

    def __init__(self, spec: ModSpec, out_dir: Path, game_version: str = "26.2", pack_format: int | None = None) -> None:
        super().__init__(spec, out_dir)
        self.game_version = game_version
        self.pack_format_override = pack_format
        self.cap = capability_for(self.name)
        self.profile: GameProfile = profile_for(game_version)

    # ------------------------------------------------------------------
    def generate(self) -> list[Path]:
        written: list[Path] = []
        modid = self.spec.info.id

        written.append(self.write("pack.mcmeta", self._pack_mcmeta()))
        written.append(self.write(f"data/{modid}/mod_manifest.json", self._manifest()))

        for reg in self.spec.registrations:
            if reg.kind == "tag":
                written.append(self._emit_tag(reg))

        for handler in self.spec.events:
            if not self.cap.can_emit_event(handler.kind):
                raise TargetError(
                    "target-unsupported-event",
                    f"datapack cannot express event {handler.kind!r} (handler "
                    f"{handler.handler_name!r})",
                    loc=handler.loc,
                )
            fname = self._slug(handler.handler_name)
            written.append(self._emit_advancement(handler, fname))
            written.append(self._emit_function(handler, fname))

        return written

    # ------------------------------------------------------------------
    def _pack_mcmeta(self) -> str:
        if self.pack_format_override is not None:
            fmt = self.pack_format_override
        else:
            fmt = self.profile.pack_format()
        desc = self.spec.info.description or f"pymod data pack for {self.spec.info.name}"
        return json.dumps({"pack": {"pack_format": int(fmt), "description": desc}}, indent=2)

    def _manifest(self) -> str:
        info = {
            "pymod_version": "0.1.0",
            "mod": {
                "id": self.spec.info.id,
                "name": self.spec.info.name,
                "version": self.spec.info.version,
            },
            "game_version": self.game_version,
            "registrations": [
                {"kind": r.kind, "name": r.name, "props": dict(r.props)} for r in self.spec.registrations
            ],
            "note": (
                "item/block registrations are metadata only in a datapack; "
                "they do not define new game content."
            ),
        }
        return json.dumps(info, indent=2, ensure_ascii=False)

    def _emit_tag(self, reg) -> Path:
        modid = self.spec.info.id
        props = dict(reg.props)
        values = props.get("values", ())
        # tag name may carry a category prefix, e.g. "blocks/magic" or "items/foo"
        name = reg.name
        if "/" in name:
            category, _, base = name.rpartition("/")
        else:
            category, base = "items", name
        if category not in ("items", "blocks", "functions", "entity_types"):
            raise TargetError(
                "bad-tag-category",
                f"datapack tag {reg.name!r} uses unknown category {category!r}; "
                "use items/... or blocks/...",
                loc=reg.loc,
            )
        doc = {
            "replace": False,
            "values": list(values),
        }
        return self.write(f"data/{modid}/tags/{category}/{base}.json", json.dumps(doc, indent=2))

    # ------------------------------------------------------------------
    def _emit_advancement(self, handler, fname: str) -> Path:
        modid = self.spec.info.id
        trigger = _TRIGGER.get(handler.kind)
        if trigger is None:
            raise TargetError(
                "target-unsupported-event",
                f"datapack has no trigger for event {handler.kind!r}",
                loc=handler.loc,
            )

        seen: set[tuple] = set()
        guards: list[Guard] = []
        for g in self._all_guards(handler):
            key = (g.lhs_kind, g.lhs, g.op, g.rhs)
            if key not in seen:
                seen.add(key)
                guards.append(g)
        item_guards = [
            g for g in guards
            if g.lhs_kind == "param" and g.lhs == "item" and g.op in ("==", "!=")
        ]
        for g in guards:
            if g.lhs_kind == "param" and g.lhs == "item" and g.op not in ("==", "!="):
                raise TargetError(
                    "datapack-unsupported-guard",
                    f"datapack can only express 'ctx.item == / != <id>' conditions, "
                    f"not ctx.item {g.op} {g.rhs} (handler {handler.handler_name!r})",
                    loc=g.loc,
                )
        if any(g.lhs_kind == "param" and g.lhs != "item" for g in guards):
            g = next(g for g in guards if g.lhs_kind == "param" and g.lhs != "item")
            raise TargetError(
                "datapack-unsupported-guard",
                f"datapack can only express today the ctx.item condition, "
                f"not ctx.{g.lhs} {g.op} {g.rhs} (handler {handler.handler_name!r})",
                loc=g.loc,
            )
        if len(item_guards) > 1:
            raise TargetError(
                "datapack-unsupported-guard",
                "datapack MVP supports a single ctx.item condition per handler "
                "(use if/else-free handlers or split into multiple handlers)",
                loc=item_guards[1].loc,
            )

        conditions = {}
        if item_guards:
            g = item_guards[0]
            predicate = {"items": [g.rhs]}
            if g.op == "!=":
                predicate["negate"] = True
            conditions["item"] = predicate

        doc = {
            "criteria": {
                "triggered": {"trigger": trigger, "conditions": conditions},
            },
            "rewards": {"function": f"{modid}:{fname}"},
        }
        return self.write(
            f"data/{modid}/advancement/{fname}.json", json.dumps(doc, indent=2)
        )

    def _emit_function(self, handler, fname: str) -> Path:
        modid = self.spec.info.id
        lines = [f"# generated by pymod: {handler.kind} ({handler.handler_name})"]
        for action in handler.body:
            lines.extend(self._emit_action(action))
        body = "\n".join(lines) + "\n"
        return self.write(f"data/{modid}/function/{fname}.mcfunction", body)

    # ------------------------------------------------------------------
    def _emit_action(self, action) -> list[str]:
        op, args = action.op, action.args
        if op == "send_message":
            (msg,) = args
            return [f'tellraw @s {json.dumps({"text": msg}, ensure_ascii=False)}']
        if op == "give_item":
            item = args[0]
            count = args[1] if len(args) > 1 else 1
            return [f"give @s {item} {count}"]
        if op == "set_block":
            x, y, z, block = args
            return [f"setblock {x} {y} {z} {block}"]
        if op == "teleport":
            target, x, y, z = args
            return [f"tp {target} {x} {y} {z}"]
        if op == "spawn_particle":
            effect, x, y, z = args[:4]
            count = args[4] if len(args) > 4 else 1
            return [f"particle {effect} {x} {y} {z} 0 0 0 0 {count} normal"]
        if op == "play_sound":
            sound, x, y, z = args[:4]
            volume = args[4] if len(args) > 4 else 1.0
            pitch = args[5] if len(args) > 5 else 1.0
            return [f"playsound {sound} player @s {x} {y} {z} {value_to_str(volume)} {value_to_str(pitch)}"]
        if op == "grant_advancement":
            (adv,) = args
            return [f"advancement grant @s only {adv}"]
        raise TargetError(
            "target-unsupported-action",
            f"datapack has no command for ctx.{op}(...)",
            loc=action.loc,
        )

    @staticmethod
    def _all_guards(handler) -> list[Guard]:
        out: list[Guard] = []
        for a in handler.body:
            out.extend(a.guards)
        return out

    @staticmethod
    def _slug(name: str) -> str:
        return name.replace("-", "_")