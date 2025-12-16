"""
Handles all the per-user, per-guild, and global settings bot functionality.
This currently includes the settings command and the pronunciation command.
"""

# built-in
from itertools import islice

# PyPI
import discord
from discord.ext import commands

# my modules
from src.tts import driver as ttsd
from src.db import driver as dbd # NOT DEAD BY DAYLIGHT
from src.utils.logging_utils import timestamp_print as tsprint
from src.views.views import ConfirmView, PageNavView

# required for cogs API
def setup(bot: discord.Bot):
    bot.add_cog(SettingsCog(bot))

class SettingsCog(commands.Cog):
    pronunciation = discord.SlashCommandGroup("pronunciation", "Modify pronunciations on a per-server basis")
    settings = discord.SlashCommandGroup("settings", "Modify your settings (global)")

    def __init__(self, bot: discord.Bot):
        self.bot = bot

    @pronunciation.command(name="add", description="Add a pronunciation to this server")
    @discord.option(
        "voice",
        description="Which voice to edit",
        choices=ttsd.TTS_VOICES
    )
    @discord.option("text", description="The text to update pronounciation for")
    @discord.option("pronunciation", description="How to pronounce the text")
    async def add_pronunciation(self, ctx: discord.ApplicationContext, voice: str, text: str, pronunciation: str):
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
    async def remove_pronunciation(self, ctx: discord.ApplicationContext, voice: str, text: str):
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
    async def list_pronunciations(self, ctx: discord.ApplicationContext, voice: str):
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

    @settings.command(name="voice", description="Get or set your default voice")
    @discord.option(
        "voice",
        description="The voice to set your default to",
        choices=["None"] + ttsd.TTS_VOICES,
        default=None
    )
    async def settings_voice(self, ctx: discord.ApplicationContext, voice: str | None = None):
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

    @discord.Cog.listener()
    async def on_ready(self):
        tsprint("Settings Cog is now ready!")