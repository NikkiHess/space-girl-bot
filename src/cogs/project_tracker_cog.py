# PyPI
import discord
from discord.ext import commands

# my modules
from src.embeds.project_tracker_embed import ProjectTrackerEmbed
from src.utils.logging_utils import timestamp_print as tsprint

# required for cogs API
def setup(bot: discord.Bot):
    bot.add_cog(ProjectTrackerCog(bot))

class ProjectTrackerCog(commands.Cog):
    project_tracker = discord.SlashCommandGroup("projecttracker", "Helps track your projects and their progress")

    def __init__(self, bot: discord.Bot):
        self.bot = bot

    @discord.Cog.listener()
    async def on_ready(self):
        tsprint("Project Tracker Cog is now ready!")

    @project_tracker.command(name="create", description="Create a project to begin tracking")
    @discord.option(
        "Title",
        parameter_name="title",
        description="The name/title of the project (optional)",
        value="Unnamed Project"
    )
    @discord.option(
        "Description",
        parameter_name="description",
        description="A short description of the project (optional)",
        value=None
    )
    @discord.option(
        "Project Start",
        parameter_name="project_start",
        description="The date the project was started (optional)",
        value=None
    )
    @discord.option(
        "Project End",
        parameter_name="project_end",
        description="The last time the project was updated or when it was finished (optional)",
        value=None
    )
    @discord.option(
        "Status",
        parameter_name="status",
        description="The current status of the project (optional)",
        value=None
    )
    async def cmd_project_tracker_create(
        self,
        ctx: discord.ApplicationContext,
        title: str | None = None,
        description: str | None = None,
        project_start: str | None = None,
        project_end: str | None = None,
        status: str | None = None,
    ):
        """
        Adds a pronunciation to the Discord server within the database

        :param discord.ApplicationContext ctx: the context in which to execute
        :param str name: the name of the project (optional)
        :param str description: a short description of the project (optional)
        :param str date_started: the date the project was started (optional)
        :param bool admin_global: whether this is an adjustment for the entire bot, bot admins only
        """
        # acknowledge the command internally
        await ctx.defer()
        
        await ctx.respond(embed=ProjectTrackerEmbed(title, description, project_start, project_end, status))