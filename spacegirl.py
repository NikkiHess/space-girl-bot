"""
the main module for space girl bot
"""

# built-in modules
import os
import json
import asyncio
import platform

# PyPI modules
import discord # pycord

# my modules
from nikki_util import timestamp_print as tsprint
import tts_driver as ttsd
from errors import *

VC = None # the voice client, initialized in main
OS_NAME = platform.system() # for platform-dependent Opus loading

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
    Declares bot ready, clears VC state, loads Opus (platform dependent), and runs TTS Queue handler
    """
    global VC

    VC = None

    # if that didn't work, try loading from /depend
    if not discord.opus.is_loaded():
        tsprint("Opus not loaded, searching on the system...")

        try:
            match OS_NAME:
                case "Windows":
                    opus_path = os.path.join("depend", "libopus.dll")
                case "Darwin":
                    opus_path = "/opt/homebrew/opt/opus/lib/libopus.dylib"
                case _:
                    raise OSNotSupportedError()
                
            discord.opus.load_opus(opus_path)
        except OSError:
            tsprint("Opus not found.")
            match OS_NAME:
                case "Windows":
                    tsprint("Please install Opus to /depend/libopus.dll")
                case "Darwin":
                    tsprint("Please install Opus using \"brew install opus\"")

            raise OpusNotFoundError()
    
    tsprint("Loaded Opus successfully.")

    bot.loop.create_task(process_tts_queue())

    tsprint(f"{bot.user} is now ready!")

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
        
        was_too_long = ttsd.download_and_queue_marcus_tts(input)
        await ctx.followup.send(
            content=f"Queued TTS: {input}\n" + ("Input was trimmed because it was over 300 chars." if was_too_long else "")
        )

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
    Processes TTS queue - runs in Pycord event loop
    """
    global VC

    ffmpeg_path = None
    match OS_NAME:
        case "Windows":
            ffmpeg_path = os.path.join("depend", "libopus.dll")
        case "Darwin":
            ffmpeg_path = "/opt/homebrew/bin/ffmpeg"
        case _:
            raise OSNotSupportedError()
    
    def make_after_callback(tts_filename):
        def after_play(_):  # The `_` is the exception Pycord passes
            tsprint(f"Audio done playing: {tts_filename}")
            try:
                os.remove(tts_filename)
                tsprint(f"Deleted {tts_filename}")
            except FileNotFoundError:
                tsprint(f"File {tts_filename} already deleted")
        return after_play

    while(True):
        if VC is None or not VC.is_connected():
            await asyncio.sleep(0.1)
            continue

        # if there's something in the queue and we're not playing something else, play our first TTS queue item
        if len(ttsd.TTS_QUEUE) > 0 and not VC.is_playing():
            tts_filename = ttsd.TTS_QUEUE.popleft()

            tsprint(f"Playing queued TTS {tts_filename}")

            tts_audio_source = discord.FFmpegOpusAudio(
                executable=ffmpeg_path,
                source=tts_filename
            )

            VC.play(tts_audio_source, after=make_after_callback(tts_filename))
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