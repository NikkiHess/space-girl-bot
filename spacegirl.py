"""
the main module for space girl bot

author:
Nikki Hess (nkhess@umich.edu)
"""

# PyPI modules
import discord # pycord

# my modules
from nikki_util import timestamp_print as tsprint

CONFIG_PATH = os.path.join("config", "discord.json")
with open(CONFIG_PATH, "r") as f:
    config = json.load(f)

TOKEN = config.get("token")

bot = discord.Bot()

@bot.event
async def on_ready():
    tsprint(f"{bot.user} is now ready!")

@bot.slash_command()
async def