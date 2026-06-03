# TODO: implement this (based on the "to watch" channel in Afzuigkapje)
# IDEAS: 
# - command to input media you want to watch
# - get icon/data for media from some source (IMDb? do they have a public API?)
# - also link to whatever the data source is if possible, if not fall back on IMDb
# - maybe allow for changing this link to your preferred service (IMDb, Letterboxd, etc)
# - somehow get show # of seasons/movie length, then have a progress bar tracking how far in the guild is
# - also "up next" 
# - list of streaming services the media is on (if applicable and turned on)
# - statuses: not started/to rewatch/in progress/actively rewatching
# - command to search by name, status, type (movie/show), etc.
# - support for YouTube as well, since not everything is on streaming
# - all of this in nice embeds ideally, utilizing the existing database. embed color probably based on status (or grab the most common color from the show icon)

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