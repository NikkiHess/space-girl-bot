"""
the main module for space girl bot

author:
Nikki Hess (nkhess@umich.edu)
"""

# built-in modules
import os
import json

# PyPI modules
import discord # pycord

# my modules
from nikki_util import timestamp_print as tsprint
import tts

# load in our token
CONFIG_PATH = os.path.join("config", "discord.json")
with open(CONFIG_PATH, "r") as f:
    config = json.load(f)

TOKEN = config.get("token")

# get intents
intents = discord.Intents.default()
intents.voice_states = True
intents.members = True

bot = discord.Bot(intents=intents)

@bot.event
async def on_ready():
    tsprint(f"{bot.user} is now ready!")

@bot.event
async def on_voice_state_update(member, before, after):
    if member.id == bot.user.id:
        if after.channel is None:
            bot.vc = None
            print("Bot left VC.")

# SLASH COMMANDS

@bot.command(description="Does TTS.")
async def tts(ctx):
    await ctx.respond("Testing!")

@bot.command(description="Joins the voice chat you're currently in.")
async def join(ctx):
    voice_state = ctx.author.voice

    # not in a vc
    if voice_state is None:
        await ctx.respond("You are not currently in a vc.")
        return
    
    if bot.vc is not None:
        await ctx.respond("Already connected in this guild.")
        return
    
    await ctx.defer(invisible=False)
    await ctx.edit(content="Connecting...")
    
    voice_channel = voice_state.channel
    bot.vc = await voice_channel.connect(reconnect=False)

    await ctx.edit(content=f"Successfully joined {voice_channel.name}! Use /tts to speak.")

@bot.command(description="Leaves whatever voice chat it's currently in.")
async def leave(ctx):
    voice_state = ctx.voice_client

    if voice_state is None:
        await ctx.respond("I am not currently in a vc.")
        return
    
    await voice_state.disconnect()
    await ctx.respond("Left voice!")

bot.run(TOKEN)