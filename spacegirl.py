"""
the main module for space girl bot

Author:
Nikki Hess (nkhess@umich.edu)
"""

# built-in modules
import os
import json

# PyPI modules
import discord # pycord

# my modules
from nikki_util import timestamp_print as tsprint
import tts_driver as ttsd

# initialize in main
CHROMEDRIVER = None

# get intents
intents = discord.Intents.default()
intents.voice_states = True
intents.members = True
intents.guilds = True

bot = discord.Bot(intents=intents)

# BOT EVENTS

@bot.event
async def on_ready():
    """
    Simply declares that the bot is ready and clears its vc state
    """

    tsprint(f"{bot.user} is now ready!")
    bot.vc = None

@bot.event
async def on_voice_state_update(member: discord.Member,
                                before: discord.member.VoiceState,
                                after: discord.member.VoiceState):
    """
    When the bot's voice state updates, if it left a VC, clear its VC state

    ## Args:
    - `member` (discord.Member): the member whose voice state updates
    - `before` (discord.member.VoiceState): the VoiceState before the update
    - `after` (discord.member.VoiceState): the VoiceState after the update
    """

    if member.id == bot.user.id:
        if after.channel is None:
            bot.vc = None
            tsprint("Bot left VC.")

# SLASH COMMANDS

@bot.command(description="Does TTS.")
async def tts(ctx):
    """
    Does TTS, currently only Marcus.
    """
    ttsd.get_marcus_tts(CHROMEDRIVER, "This is a test of the TTS system.")
    # bot.vc.play()

@bot.command(description="Joins the voice chat you're currently in.")
async def join(ctx):
    """
    Forces the bot to join VC.
    """

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
    """
    Forces the bot to leave vc.
    """
    
    voice_state = ctx.voice_client

    if voice_state is None:
        await ctx.respond("I am not currently in a vc.")
        return
    
    await voice_state.disconnect()
    await ctx.respond("Left voice!")

if __name__ == "__main__":
    # load in our token
    config_path = os.path.join("config", "discord.json")
    with open(config_path, "r") as f:
        config = json.load(f)

    # run the bot with that token
    token = config.get("token")
    bot.run(token)

    # initiate our chromedriver instance
    CHROMEDRIVER = ttsd.open_driver()