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
from typing import Dict, Deque, Optional
from itertools import islice

# PyPI modules
import discord # pycord

# my modules
from nikki_util import timestamp_print as tsprint
import tts_driver as ttsd
from errors import *
import db_driver as dbd # NOT DEAD BY DAYLIGHT
from views import *

VC_DICT: Dict[int, Optional[discord.VoiceClient]] = dict()
TTS_QUEUE_DICT: Dict[int, Dict[str, Deque[str]]] = dict()
LAST_TRIGGERED_CHANNEL_DICT: Dict[int, int] = dict()

OS_NAME = platform.system() # for platform-dependent Opus loading
INVITE_LINK = "https://discord.com/oauth2/authorize?client_id=1424873603790540982&scope=bot&permissions=2184268800"

# get intents
intents = discord.Intents.default()
intents.voice_states = True
intents.members = True
intents.guilds = True

bot = discord.Bot(intents=intents)

voices = ["Marcus"]

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

    tsprint("Initializing database...")
    dbd.init_db()

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
    When the bot's voice state updates:
        - if it left a VC, clear its VC state.
        - if the VC is empty except for bots, leave.

    ## Args:
    - `member` (discord.Member): the member whose voice state updates
    - `before` (discord.member.VoiceState): the VoiceState before the update
    - `after` (discord.member.VoiceState): the VoiceState after the update
    """
    global VC_DICT
    guild_id = member.guild.id

    # check if the bot left the VC
    if member.id == bot.user.id:
        if after.channel is None:
            VC_DICT[guild_id] = None
            tsprint(f"Bot left VC in {guild_id}.")
        return # no need to check for emptiness if bot left
    
    # check if the bot is in a VC in this guild, just to make sure
    vc = VC_DICT.get(guild_id)
    if vc is None or not vc.is_connected():
        return
    
    # if VC empty except for bots, leave
    non_bot_members = [member for member in vc.channel.members if not member.bot]
    if not non_bot_members:
        await leave_vc(guild_id)
        

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

# TODO: make a command where you can select a voice so you don't have to type a voice every time
@bot.command(description="Does TTS.", dm_permission=False)
@discord.option(
    "voice",
    description="Which voice to use",
    choices=voices
)
@discord.option(
    "input", 
    type=str, 
    description="The input to read (MAX 300 CHARS)"
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
        
    tsprint(f"Queued TTS \"{input}\" in guild {ctx.guild_id}")
    
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
    global VC_DICT, LAST_TRIGGERED_CHANNEL_DICT

    LAST_TRIGGERED_CHANNEL_DICT[ctx.guild_id] = ctx.channel_id

    voice_state = ctx.author.voice

    # not in a vc
    if vc is None and voice_state is None:
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

async def leave_vc(guild_id: int, ctx: Optional[discord.ApplicationContext] = None):
    """
    Leaves a VC in a guild safely, optionally sending a message if ctx is given.
    """
    vc = VC_DICT.get(guild_id)
    if not vc or not vc.is_connected():
        if ctx:
            await ctx.respond("❌ I am not currently in a VC.")
        return

    if ctx:
        await ctx.respond("👋🏻 Left voice!")

    # reset triggered channel
    LAST_TRIGGERED_CHANNEL_DICT[guild_id] = None

    await vc.disconnect()
    VC_DICT[guild_id] = None

@bot.command(description="Leaves whatever voice chat it's currently in.")
async def leave(ctx: discord.ApplicationContext):
    """
    Command wrapper to leave VC from current guild.
    """
    await leave_vc(ctx.guild_id, ctx)

pronunciation = bot.create_group("pronunciation", "Modify pronunciations on a per-server basis")

@pronunciation.command(description="Add a pronunciation to this server")
@discord.option(
    "voice",
    description="Which voice to use",
    choices=voices
)
@discord.option("text", description="The text to translate")
@discord.option("pronunciation", description="What to translate to")
async def add(ctx: discord.ApplicationContext, voice: str, text: str, pronunciation: str):
    """
    Adds a pronunciation to the Discord server within the database
    """
    await ctx.respond("🔄 Processing...")

    existing_pronunciation = dbd.get_pronunciation(ctx.guild_id, voice, text)
    if existing_pronunciation:
        embed = discord.Embed(
            title = "Pronunciation Override Confirmation",
            description = f"",
            color = discord.Color.yellow()
        )
        embed.add_field(name = "Text", value = text, inline = False)
        embed.add_field(name = "Old Pronunciation", value = existing_pronunciation, inline = False)
        embed.add_field(name = "New Pronunciation", value = pronunciation, inline = False)

        view = ConfirmView()
        await ctx.edit(
            embed=embed, 
            view=view
        )
        await view.wait()

        if view.value is False:
            await ctx.edit(content="❌ Operation cancelled.", embed=None, view=None)
            return
    else:
        tsprint(f"Adding pronunciation \"{text}\" -> \"{pronunciation}\" to guild {ctx.guild_id}")
    
    dbd.add_pronunciation(ctx.guild_id, voice, text, pronunciation)

    embed = discord.Embed(
        title = "Pronunciation Successfully Added!",
        description = f"Your pronunciation has been added to **{ctx.guild.name}**!",
        color = discord.Color.brand_green()
    )
    embed.add_field(name = "Text", value = text, inline = False)
    embed.add_field(name = "Pronunciation", value = pronunciation, inline = False)

    await ctx.edit(content=None, embed=embed, view=None)
    
# name="list" doesn't match function name here because otherwise we have naming conflicts
@discord.option(
    "voice",
    description="Which voice to check pronunciations for",
    choices=voices
)
@pronunciation.command(name="list", description="List all pronunciations for a voice in this server")
async def list_pronunciations(ctx: discord.ApplicationContext, voice: str):
    """
    Lists all pronunciations for a specified voice within the Discord server
    """
    pronunciations = dbd.list_pronunciations(ctx.guild_id, voice)
    
    per_page = 10
    current_page = 1
    # 10 per page, add 1 to page number cuz floor divide
    num_pages = (len(pronunciations) // per_page) + 1

    def build_embed(current_page: int, num_pages: int):
        """
        builds the embed based on page information
        """
        embed = discord.Embed(
            title=f"Pronunciation Dictionary for **{voice}** in **{ctx.guild.name}**",
            color=0xED99A0  # cute pink color
        )

        # slice items for the current page
        start_idx = (current_page - 1) * per_page
        end_idx = current_page * per_page
        slice_items = list(islice(pronunciations.items(), start_idx, end_idx))

        # join keys and values for this page
        keys_text = "\n".join(k for k, _ in slice_items)
        vals_text = "\n".join(v for _, v in slice_items)

        # list all pronunciations
        embed.add_field(name="Text", value=keys_text or "—")
        embed.add_field(name="Pronunciation", value=vals_text or "—")

        # pycord doesn't like empty strings for names, so just use 0-width character
        embed.add_field(name="\u200b", value=f"({current_page} / {num_pages})", inline=False)

        return embed

    if len(pronunciations) > 0:
        embed = build_embed(current_page, num_pages)

        page_nav_view = PageNavView(num_pages, build_embed)
        await ctx.respond(embed=embed, view=page_nav_view)
    else:
        await ctx.respond("❌ No pronunciations found for this guild!")


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
                tsprint(f"Deleted \"{tts_filename}\"")
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