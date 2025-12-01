"""
the main module for space girl bot
"""

# built-in modules
import os
import json
import platform
import aiohttp
from itertools import islice
import importlib

# Pycord
import discord # pycord

# my modules
from .utils.logging_utils import timestamp_print as tsprint
from .errors import *
from .tts import driver as ttsd
from .db import driver as dbd # NOT DEAD BY DAYLIGHT
from .views.views import *
from .tts.voices import TTSVibesVoice as TVV

INVITE_LINK = "https://discord.com/oauth2/authorize?client_id=1424873603790540982&scope=bot&permissions=2184268800"

# get intents
intents = discord.Intents.default()
intents.voice_states = True
intents.members = True
intents.guilds = True

bot = discord.Bot(intents=intents)

# load cogs
for filename in os.listdir(os.path.join(os.path.dirname(__file__), "cogs")):
    if filename.endswith(".py") and filename != "__init__.py":
        mod = f".cogs.{filename[:-3]}"
        importlib.import_module(mod, package="src")
        bot.load_extension(mod, package="src")

# BUG: If you try to make TTS that is too long the bot gets confused and thinks it can play it when TTS Vibes says no.

# BOT EVENTS
@bot.event
async def on_ready():
    tsprint("Initializing database...")
    dbd.init_db()

    # if that didn't work, try loading from /depend
    if not discord.opus.is_loaded():
        tsprint("Opus not loaded, searching on the system...")

        os_name = platform.system()
        try:
            match os_name:
                case "Windows":
                    opus_path = os.path.join("depend", "libopus.dll")
                case "Darwin":
                    opus_path = "/opt/homebrew/opt/opus/lib/libopus.dylib"
                case _:
                    raise OSNotSupportedError()
                
            discord.opus.load_opus(opus_path)
        except OSError:
            tsprint("Opus not found.")
            match os_name:
                case "Windows":
                    tsprint("Please install Opus to /depend/libopus.dll")
                case "Darwin":
                    tsprint("Please install Opus using \"brew install opus\"")

            raise OpusNotFoundError()
    
    tsprint("Loaded Opus successfully.")

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

pronunciation = bot.create_group("pronunciation", "Modify pronunciations on a per-server basis")

@pronunciation.command(description="Add a pronunciation to this server")
@discord.option(
    "voice",
    description="Which voice to edit",
    choices=ttsd.TTS_VOICES
)
@discord.option("text", description="The text to update pronounciation for")
@discord.option("pronunciation", description="How to pronounce the text")
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
        embed.add_field(name = "Text", value = text)
        embed.add_field(name = "Old Pronunciation", value = existing_pronunciation)
        embed.add_field(name = "New Pronunciation", value = pronunciation)

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
    embed.add_field(name = "Text", value = text)
    embed.add_field(name = "Pronunciation", value = pronunciation)

    await ctx.edit(content=None, embed=embed, view=None)

@pronunciation.command(name="delete", description="Remove a pronunciation from this server")
@discord.option(
    "voice",
    description="Which voice to edit",
    choices=ttsd.TTS_VOICES
)
@discord.option("text", description="The text to remove the pronunciation for")
async def remove_pronunciation(ctx: discord.ApplicationContext, voice: str, text: str):
    """
    Removes a pronunciation from the Discord server within the database
    """
    await ctx.respond("🔄 Processing...")

    existing_pronunciation = dbd.get_pronunciation(ctx.guild_id, voice, text)
    if existing_pronunciation:
        tsprint(f"Removed pronunciation \"{text}\" -> \"{existing_pronunciation}\" from guild {ctx.guild_id}")
        dbd.remove_pronunciation(ctx.guild_id, voice, text)
    
        embed = discord.Embed(
            title = "Pronunciation Successfully Removed!",
            description = f"Your pronunciation has been removed from **{ctx.guild.name}**!",
            color = discord.Color.brand_red()
        )
        embed.add_field(name = "Text", value = text)

        await ctx.edit(content=None, embed=embed, view=None)
    else:
        tsprint(f"Pronunciation for \"{text}\" not found in guild {ctx.guild_id}")
        await ctx.edit(content=f"❌ Pronunciation for \"{text}\" not found in **{ctx.guild.name}**")
    
@pronunciation.command(name="list", description="List all pronunciations for a voice in this server")
# name="list" doesn't match function name here because otherwise we have naming conflicts (with built-in list function)
@discord.option(
    "voice",
    description="Which voice to check pronunciations for",
    choices=ttsd.TTS_VOICES
)
async def list_pronunciations(ctx: discord.ApplicationContext, voice: str):
    """
    Lists all pronunciations for a specified voice within the Discord server
    """
    pronunciations = dbd.list_pronunciations(ctx.guild_id, voice)
    
    # TODO: fix this, shows up weirdly on mobile

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
        await ctx.respond(f"❌ No pronunciations found for **{voice}** in **{ctx.guild.name}**!")

settings = bot.create_group("settings", "Modify your settings (global)")

@settings.command(name="voice", description="Get or set your default voice")
@discord.option(
    "voice",
    description="The voice to set your default to",
    choices=["None"] + ttsd.TTS_VOICES,
    default=None
)
async def settings_voice(ctx: discord.ApplicationContext, voice: str | None = None):
    author_id = ctx.author.id

    # no voice specified = get settings value
    if not voice:
        voice_name = dbd.get_user_voice(author_id)

        if voice_name:
            await ctx.respond(f"🗣️ Your current voice is **{voice_name}**!")
        else:
            await ctx.respond(f"❌ You don't currently have a default voice set.")
            
        return
    
    # if the None option is selected, convert to TYPE None
    if voice == "None":
        voice = None
    # voice is guaranteed to be specified at this point
    # set settings value
    dbd.set_user_voice(author_id, voice)

    if voice:
        await ctx.respond(f"✅ Your default voice has been set to **{voice}**! You can now use /tts without specifying a voice.")
    else:
        await ctx.respond(f"✅ Your default voice has been cleared. You must now specify a voice when using /tts.")

if __name__ == "__main__":
    # load in our token
    config_path = os.path.join("config", "discord.json")
    with open(config_path, "r") as f:
        config = json.load(f)

    # run the bot with that token
    token = config.get("token")
    bot.run(token)