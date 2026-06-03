# PyPI
import discord
from discord.ext import commands

# my modules
from src.utils.logging_utils import timestamp_print as tsprint

# required for cogs API
def setup(bot: discord.Bot):
    bot.add_cog(MediaTrackerCog(bot))

class MediaTrackerCog(commands.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot

    @discord.Cog.listener()
    async def on_ready(self):
        tsprint("Settings Cog is now ready!")