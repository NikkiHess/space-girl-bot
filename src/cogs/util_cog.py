"""
Handles all utility functionality for the bot.
Currently this is literally only the invite command.
"""

# PyPi
import discord

# my modules
from ..utils.logging_utils import timestamp_print as tsprint

# required for cogs API
def setup(bot: discord.Bot):
    bot.add_cog(UtilCog())

class UtilCog(discord.Cog):
    def __init__(self):
        self.invite_link = "https://discord.com/oauth2/authorize?client_id=1424873603790540982&scope=bot&permissions=2184268800"

    @discord.command(name="invite", description="DMs you the link to invite me to your server", dm_permission=True)
    async def cmd_invite(self, ctx: discord.ApplicationContext):
        """
        Sends the relevant invite link to the user who asked
        """
        embed = discord.Embed(
            title="✨ Invite Space Girl Bot!",
            description=f"Click the button below to add me to your server!",
            color=0xED99A0  # cute pink color
        )
        embed.add_field(name="Invite Link", value=f"[Click here!]({self.invite_link})", inline=False)

        try:
            # only send this message in guilds
            if ctx.guild:
                await ctx.respond("📬 I've sent you my invite link via DM!")
                await ctx.author.send(embed=embed)
            else:
                await ctx.respond(embed=embed)
        except discord.Forbidden:
            await ctx.respond("⚠️ I couldn't DM you! Please check your privacy settings.")

    @discord.Cog.listener()
    async def on_ready(self):
        tsprint("Util Cog is now ready!")