"""
the main module for space girl bot

Author:
Nikki Hess (nkhess@umich.edu)
"""

# built-in modules
import os
import json
import asyncio

# PyPI modules
import discord # pycord

# my modules
from nikki_util import timestamp_print as tsprint
import tts_driver as ttsd

# initialize in main
CHROMEDRIVER = None
VC = None

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
    Declares bot ready, clears VC state, opens driver, loads Opus, and runs TTS Queue handler
    """
    global CHROMEDRIVER, VC

    tsprint(f"{bot.user} is now ready!")
    VC = None
    
    # initiate our chromedriver instance
    CHROMEDRIVER = ttsd.open_driver()

    # load opus
    opus_path = os.path.join("depend", "libopus.dll")
    discord.opus.load_opus(opus_path)

    if not discord.opus.is_loaded():
        tsprint("Failed to load Opus. This is a problem.")
    else:
        tsprint("Loaded opus successfully.")

    bot.loop.create_task(process_tts_queue())

@bot.event
async def on_disconnect():
    for client in bot.voice_clients:
        await client.disconnect()

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
    global VC

    if member.id == bot.user.id:
        if after.channel is None:
            VC = None
            tsprint("Bot left VC.")

# SLASH COMMANDS

@bot.command(description="Does TTS.")
@discord.option("input", type=str)
async def tts(ctx, input: str):
    """
    Does TTS, currently only Marcus.
    """
    global VC

    await ctx.defer()

    voice_state = ctx.author.voice
    if voice_state is None:
        await ctx.edit("You are not in a VC.")
    else:
        if VC is None:
            VC = await voice_state.channel.connect(reconnect=False)
        
        ttsd.download_and_queue_marcus_tts(CHROMEDRIVER, input)
        await ctx.followup.send(content=f"Queued TTS: {input}")

@bot.command(description="Joins the voice chat you're currently in.")
async def join(ctx):
    """
    Forces the bot to join VC.
    """
    global VC

    voice_state = ctx.author.voice

    # not in a vc
    if voice_state is None:
        await ctx.respond("You are not in a VC.")
        return
    
    if VC is not None:
        await ctx.respond("Already connected in this guild.")
        return
    
    await ctx.defer(invisible=False)
    await ctx.edit(content="Connecting...")
    
    voice_channel = voice_state.channel
    VC = await voice_channel.connect(reconnect=False)

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

async def process_tts_queue():
    """
    Processes TTS queue, deleting files as it goes - runs in Pycord event loop
    """
    global VC

    while(True):
        if VC is None or not VC.is_connected():
            await asyncio.sleep(0.1)
            continue

        if len(ttsd.TTS_QUEUE) > 0:
            tts_filename = ttsd.TTS_QUEUE.popleft()
            tts_full_path = os.path.join("downloads", tts_filename)
            tts_audio_source = discord.FFmpegOpusAudio(
                executable="depend/ffmpeg.exe",
                source=tts_full_path
            )

            def after_play(err):
                if err:
                    tsprint(f"Error during playback: {err}")
                if os.path.exists(tts_full_path):
                    os.remove(tts_full_path)
                    tsprint(f"Removed TTS file {tts_filename}")

            VC.play(tts_audio_source, after=after_play)
        else:      
            await asyncio.sleep(0.1)

if __name__ == "__main__":
    # load in our token
    config_path = os.path.join("config", "discord.json")
    with open(config_path, "r") as f:
        config = json.load(f)

    # run the bot with that token
    token = config.get("token")
    bot.run(token)