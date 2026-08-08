# Demonstrates a documented datapack limitation: one handler may carry only a
# single ctx.item condition. The if/else below produces both `==` and `!=`
# guards, so `pymod generate --target datapack` rejects it with a precise
# message. Split such logic into two handlers.

from pymod import mod

mod(id="ifelse", name="If Else Demo", version="1.0.0")


@mod.on("player.use_item")
def on_item(ctx):
    if ctx.item == "minecraft:stick":
        ctx.send_message("stick!")
    else:
        ctx.send_message("not a stick")