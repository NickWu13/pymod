# KubeJS-friendly example: only uses the events/actions the KubeJS MVP can emit.

from pymod import mod

mod(id="kjdemo", name="KubeJS Demo", version="1.0.0")

register("tag", "items/rare", values=["minecraft:diamond", "minecraft:emerald"])


@mod.on("player.use_item")
def on_use(ctx):
    if ctx.item == "minecraft:stick":
        ctx.send_message("sticky!")
        ctx.give_item("minecraft:diamond", 2)


@mod.on("block.broken")
def on_break(ctx):
    ctx.set_block(0, -1, 0, "minecraft:bedrock")