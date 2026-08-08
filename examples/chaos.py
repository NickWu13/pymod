# Chaos Cube example mod.
#
# This file is *parsed* (not executed) by pymod. Only the DSL subset below is
# allowed; anything else is a hard error with a line number. See docs/dsl.md.

from pymod import mod

mod(
    id="chaoscube",
    name="Chaos Cube",
    version="1.0.0",
    description="Example mod for the pymod DSL.",
)

# -------- registrations --------
register("tag", "blocks/magic", values=["minecraft:stone", "minecraft:dirt"])
register("item", "ruby", max_stack=64)
register("block", "ruby_ore", hardness=3.0)


# -------- events --------
@mod.on("player.use_item")
def on_stick(ctx):
    count = 1
    if ctx.item == "minecraft:stick":
        ctx.send_message("You used a stick!")
        ctx.give_item("minecraft:diamond", count)
    ctx.play_sound("minecraft:block.note_block.pling", 0, 0, 0, 0.5, 1.0)