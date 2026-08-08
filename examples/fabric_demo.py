# Fabric target example: registrations only.
# Events/actions are rejected for the fabric target until each Java mapping is
# verified to compile against real 26.2 deps (see docs/targets.md).

from pymod import mod

mod(id="fdemo", name="Fabric Demo", version="1.0.0")

register("item", "ruby", max_stack=64)
register("block", "ruby_ore", hardness=3.0)
register("tag", "blocks/magic", values=["minecraft:stone", "minecraft:dirt"])