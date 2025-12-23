"""
the main module for space girl bot
"""

# built-in modules
import os
import json
import platform
import aiohttp
import importlib

# Pycord
import discord # pycord

# my modules
from src.utils.logging_utils import timestamp_print as tsprint
from src.errors import *
from src.db import driver as dbd # NOT DEAD BY DAYLIGHT
from src.views.views import *

# get intents
intents = discord.Intents.default()
intents.voice_states = True
intents.members = True
intents.guilds = True

tsprint("Starting Space Girl...")

bot = discord.Bot(intents=intents)

tsprint("Loading cogs...")
for filename in os.listdir(os.path.join(os.path.dirname(__file__), "cogs")):
    if filename.endswith(".py") and filename != "__init__.py":
        mod = f".cogs.{filename[:-3]}"
        importlib.import_module(mod, package="src")
        bot.load_extension(mod, package="src")

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

if __name__ == "__main__":
    # load in our token
    config_path = os.path.join("config", "discord.json")
    with open(config_path, "r") as f:
        config = json.load(f)

    # run the bot with that token
    token = config.get("token")
    bot.run(token)