"""
the main module for space girl bot
"""

# built-in modules
import os
import json
import asyncio
import platform
import aiohttp
from collections import deque

# PyPI modules
import discord # pycord
from discord.commands import SlashCommandGroup

# my modules
from nikki_util import timestamp_print as tsprint
import tts_driver as ttsd
from errors import *
from db_driver import *

VC_DICT = dict()
TTS_QUEUE_DICT = dict()
OS_NAME = platform.system() # for platform-dependent Opus loading
INVITE_LINK = "https://discord.com/oauth2/authorize?client_id=1424873603790540982&scope=bot&permissions=2184268800"

# get intents
intents = discord.Intents.default()
intents.voice_states = True
intents.members = True
intents.guilds = True

bot = discord.Bot(intents=intents)

# BUG: If you try to make TTS that is too long the bot gets confused and thinks it can play it when TTS Vibes says no.
# TODO: Server dictionary function
# TODO: bring cache back, copy old code?


# BOT EVENTS
@bot.event
async def on_ready():
    """
    Declares bot ready, clears VC state, loads Opus (platform dependent), and runs TTS Queue handler
    """
    global VC_DICT

    tsprint("Initializing guild VC list...")
    for guild in bot.guilds:
        VC_DICT[guild.id] = None
        TTS_QUEUE_DICT[guild.id] = dict()

        for voice in ttsd.TTS_VOICES:
            TTS_QUEUE_DICT[guild.id][voice] = deque()

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
    global VC_DICT

    if member.id == bot.user.id:
        if after.channel is None:
            VC_DICT[member.guild.id] = None
            tsprint("Bot left VC.")

@bot.event
async def on_command_error(ctx: discord.ApplicationContext, error):
    """
    Handle uncaught exceptions in the bot
    """

    if isinstance(error, aiohttp.ClientConnectorDNSError):
        await ctx.respond("⚠️ Network error: unable to reach Discord. Try again later.")
    else:
        # fallback logging
        print(f"⚠️ Something went wrong!\n{error}")


# SLASH COMMANDS

@bot.command(description="DMs you the link to invite me to your server", dm_permission=True)
async def invite(ctx: discord.ApplicationContext):
    """
    Sends the relevant invite link to the user who asked
    """
    embed = discord.Embed(
        title="✨ Invite Space Girl Bot!",
        description=f"Click the button below to add me to your server!",
        color=0xED99A0  # cute pink color
    )
    embed.add_field(name="Invite Link", value=f"[Click here!]({INVITE_LINK})", inline=False)

    try:
        # only send this message in guilds
        if ctx.guild:
            await ctx.respond("📬 I’ve sent you my invite link via DM!")
            await ctx.author.send(embed=embed)
        else:
            await ctx.respond(embed=embed)
    except discord.Forbidden:
        await ctx.respond("⚠️ I couldn’t DM you! Please check your privacy settings.")

@bot.command(description="Does TTS.", dm_permission=False)
@discord.option(
    "voice",
    description="Which voice to use",
    choices=["Marcus"]
)
@discord.option(
    "input", 
    type=str, 
    description="The input to read"
)
async def tts(ctx: discord.ApplicationContext, voice: str, input: str):
    """
    Does TTS, currently only Marcus.
    """
    global VC_DICT, TTS_QUEUE_DICT

    # make sure dicts have entries for this guild
    if ctx.guild_id not in VC_DICT:
        tsprint(f"Adding guild to the TTS queue system...")
        VC_DICT[ctx.guild_id] = None
    if ctx.guild_id not in TTS_QUEUE_DICT:
        tsprint(f"Adding voices to the TTS queue system in {ctx.guild_id}...")
        TTS_QUEUE_DICT[ctx.guild_id] = {voice: deque() for voice in ttsd.TTS_VOICES}

    await ctx.defer()

    voice_state = ctx.author.voice
    if voice_state is None:
        await ctx.respond("❌ You are not in a VC.")
        return

    if VC_DICT[ctx.guild_id] is None:
        VC_DICT[ctx.guild_id] = await voice_state.channel.connect(reconnect=False)
    
    # pick the right tts based on chosen voice
    match voice.lower():
        case "marcus":
            was_too_long = ttsd.download_and_queue_marcus_tts(input, TTS_QUEUE_DICT[ctx.guild_id]["marcus"])
        case _:
            await ctx.followup.send("❌ Unknown voice selected.")
            return
    
    await ctx.followup.send(
        content=f"🎤 Queued TTS: {input}\n" + 
                ("Input was trimmed because it was over 300 chars." if was_too_long else "")
    )

@bot.command(description="Joins the voice chat you're currently in.")
@discord.option(
    "vc",
    description="[Optional] The VC (#channel-name) to join",
    channel_types=[discord.ChannelType.voice],
    default=None
)
async def join(ctx: discord.ApplicationContext, vc: discord.VoiceChannel = None):
    """
    Forces the bot to join VC.
    """
    global VC_DICT

    voice_state = ctx.author.voice

    # not in a vc
    if voice_state is None:
        await ctx.respond("❌ You are not in a VC.")
        return
    
    if VC_DICT[ctx.guild_id] is not None:
        await ctx.respond("❌ Already connected in this guild.")
        return
    
    await ctx.defer(invisible=False)
    await ctx.respond(content="🛜 Connecting...")
    
    if vc is None:
        voice_channel = voice_state.channel
    else:
        voice_channel = vc
    
    VC_DICT[ctx.guild_id] = await voice_channel.connect(reconnect=False)

    await ctx.edit(content=f"✅ Successfully joined {voice_channel.name}! Use /tts to speak.")

@bot.command(description="Leaves whatever voice chat it's currently in.")
async def leave(ctx):
    """
    Forces the bot to leave vc.
    """
    
    voice_state = ctx.voice_client

    if voice_state is None:
        await ctx.respond("❌ I am not currently in a vc.")
        return
    
    await voice_state.disconnect()
    await ctx.respond("👋🏻 Left voice!")

@bot.command(description="A command for testing stuff")
async def pronunciation(ctx: discord.ApplicationContext, add):
    pass 


# EVENT LOOP

async def process_tts_queue():
    """
    Processes TTS queue - runs in Pycord event loop
    """
    global VC_DICT, TTS_QUEUE_DICT

    ffmpeg_path = None
    match OS_NAME:
        case "Windows":
            ffmpeg_path = os.path.join("depend", "ffmpeg.exe")
        case "Darwin":
            ffmpeg_path = "/opt/homebrew/bin/ffmpeg"
        case _:
            raise OSNotSupportedError()
    
    def make_after_callback(tts_filename, guild_id):
        def after_play(_):  # The `_` is the exception Pycord passes
            tsprint(f"Audio done playing in {guild_id}: {tts_filename}")
            try:
                os.remove(tts_filename)
                tsprint(f"Deleted {tts_filename}")
            except FileNotFoundError:
                tsprint(f"File {tts_filename} already deleted")
        return after_play

    while True:
        for guild_id, vc in VC_DICT.items():
            if vc is None or not vc.is_connected():
                continue

            for voice, queue in TTS_QUEUE_DICT[guild_id].items():
                if queue and not vc.is_playing():
                    tts_filename = queue.popleft()
                    tsprint(f"Playing queued TTS {tts_filename} in guild {guild_id}")

                    try:
                        tts_audio_source = discord.FFmpegOpusAudio(
                            executable=ffmpeg_path,
                            source=tts_filename
                        )
                        vc.play(tts_audio_source, after=make_after_callback(tts_filename, guild_id))
                    except Exception as e:
                        tsprint(f"Could not play audio for guild {guild_id}: {e}")
        await asyncio.sleep(0.1)

if __name__ == "__main__":
    # load in our token
    config_path = os.path.join("config", "discord.json")
    with open(config_path, "r") as f:
        config = json.load(f)

    # run the bot with that token
    token = config.get("token")
    bot.run(token)