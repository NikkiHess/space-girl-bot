"""
Handles Discord VC behavior, including joining and leaving VC, queueing TTS (through TTSManager),
and running the background playback loop (through TTSBackgroundTask). This is the glue that holds together all
the components of text-to-speech and voice chat.
"""

# built-in
from typing import Optional

# Pycord
import discord
from discord.ext import commands

# my modules
from src.db import driver as dbd
from src.tts import driver as ttsd
from src.tts.voices import TTSVibesVoice as TVV
from src.utils.logging_utils import timestamp_print as tsprint
from src.utils.discord_utils import get_random_app_emoji
from src.errors import *
from src.vc.vc_state import VCState
from src.tts.tts_core import TTSManager, TTSBackgroundTask
from src.tts import driver as ttsd

# required for cogs API
def setup(bot: discord.Bot):
    bot.add_cog(VCCog(bot))

class VCCog(commands.Cog):
    """
    Manages all voice-related commands and the TTS background loop
    """

    def __init__(self, bot):
        self.bot = bot
        self.vc_state = VCState()
        self.tts_manager = TTSManager()
        self.bg_task = TTSBackgroundTask()

    # HELPERS
    async def try_leave_vc(self, guild_id: int, ctx: Optional[discord.ApplicationContext] = None):
        """
        Attempts to leave a VC in a guild, optionally sending a message if ctx is given.
        """
        tsprint("Bot attempting to leave VC...")
        
        vc = self.vc_state.vc_dict.get(guild_id)
        if not vc or not vc.is_connected():
            tsprint("Bot was not in a VC")
            if ctx:
                await ctx.respond("❌ I am not currently in a VC.")
            return

        if ctx:
            await ctx.respond("👋🏻 Left voice!")

        # reset triggered channel
        self.vc_state.set_last_triggered(guild_id, None)
        await vc.disconnect()
        self.vc_state.set_vc_state(guild_id, None)
        tsprint("Bot left VC successfully")

    # COMMANDS
    @discord.slash_command(
        name="tts",
        description="Does TTS.",
        dm_permission=False
    )
    @discord.option(
        "input", 
        type=str, 
        description="The input to read (MAX 300 CHARS)"
    )
    @discord.option( # OPTIONAL ARGUMENTS NEED TO BE AFTER NON-OPTIONAL
        "voice",
        description="Which voice to use (optional)",
        choices=ttsd.TTS_VOICES,
        default=None # make argument optional
    )
    async def cmd_tts(self, ctx: discord.ApplicationContext, input: str, voice: str):
        """
        Does TTS, currently only through TTS Vibes (soon to include Moonbase Alpha, REPO)
        """
        # make sure vc and tts queue dicts have entries for this guild
        self.vc_state.init_guild(ctx.guild_id)
        self.tts_manager.init_guild(ctx.guild_id)

        # silently acknowledge the command
        await ctx.defer()

        # if the user isn't in a VC, it doesn't make sense to do TTS
        # TODO: evaluate this, server setting?
        author_vc = ctx.author.voice
        if author_vc is None:
            await ctx.respond("❌ You are not in a VC.")
            return

        if not self.vc_state.is_connected_in_channel(ctx.guild_id, author_vc.channel):
            await self.try_leave_vc(ctx.guild_id)
            vc = await author_vc.channel.connect(reconnect=False)
            self.vc_state.set_vc_state(ctx.guild_id, vc)
        
        # if no voice is specified, need to check if user has a default set and use it
        if voice is None:
            db_user_voice = dbd.get_user_voice(ctx.author.id)
            if db_user_voice:
                voice = db_user_voice
            else:
                await ctx.respond("❌ You need to specify a voice or set a default with /settings voice")
                return

        # download and queue the voice line
        was_too_long = False # define this early so there's no chance it's undefined
        if voice in ttsd.TTS_VOICES:
            voice_internal = voice.replace(" ", "_") # internal voice names are goofy, translate them pls

            # is this as TTSVibes voice?
            if voice_internal in TVV._member_names_:
                # self.tts_manager.init_guild(ctx.guild_id)
                was_too_long = self.tts_manager.download_and_queue(input, TVV[voice_internal], ctx.guild_id)
            
        tsprint(f"Queued TTS \"{input}\" in guild {ctx.guild_id}")
        
        # handle message intro with voice emoji and name
        app_emoji = await get_random_app_emoji(self.bot, voice)
        message_intro = f"🎤 {voice}"
        if app_emoji:
            message_intro = f"{app_emoji} {voice}"

        await ctx.followup.send(
            content=f"{message_intro}: {input}\n" + 
                    ("Input was trimmed because it was over 300 chars." if was_too_long else "")
        )

    @discord.slash_command(name="join", description="Joins the voice chat you're currently in.")
    @discord.option(
        "vc",
        description="[Optional] The VC (#channel-name) to join",
        channel_types=[discord.ChannelType.voice],
        default=None
    )
    async def cmd_join(self, ctx: discord.ApplicationContext, vc: discord.VoiceChannel = None):
        """
        Forces the bot to join VC.
        """
        self.vc_state.init_guild(ctx.guild_id)
        self.vc_state.set_last_triggered(ctx.guild_id, ctx.channel_id)

        author_vc = ctx.author.voice
        # not in a vc
        if vc is None and author_vc is None:
            await ctx.respond("❌ You are not in a VC.")
            return
        
        if self.vc_state(ctx.guild_id):
            await ctx.respond("❌ Already connected in this guild.")
            return
        
        await ctx.defer(invisible=False)
        await ctx.respond(content="🛜 Connecting...")
        
        voice_channel = vc or author_vc.channel # shorthand for separate ifs
        vc_client = await voice_channel.connect(reconnect=False)
        self.vc_state.set_vc_state(ctx.guild_id, vc_client)

        await ctx.edit(content=f"✅ Successfully joined **{voice_channel.name}**! Use /tts to speak.")

    @discord.command(description="Leaves whatever voice chat it's currently in.")
    async def cmd_leave(self, ctx: discord.ApplicationContext):
        """
        Command wrapper to leave VC from current guild.
        """
        await self.try_leave_vc(ctx.guild_id, ctx)

    # EVENTS
    @discord.Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState
    ):
        """
        When the bot's voice state updates:
            - if it left a VC, clear its VC state.
            - if the VC is empty except for bots, leave.

        ## Args:
        - `member` (discord.Member): the member whose voice state updates
        - `before` (discord.member.VoiceState): the VoiceState before the update
        - `after` (discord.member.VoiceState): the VoiceState after the update
        """
        guild_id = member.guild.id

        # check if the bot left the VC
        if member.id == self.bot.user.id:
            if after.channel is None:
                self.vc_state.set_vc_state(guild_id, None)
                tsprint(f"Bot left VC {before.channel.name} in {guild_id}.")
            return # no need to check for emptiness if bot left
        
        # check if the bot is in a VC in this guild, just to make sure
        vc = self.vc_state.get_vc_state(guild_id)
        if vc is None or not vc.is_connected():
            return
        
        # BUG: why doesn't this work properly? is it because we rely on self.vc_dict? is there a better way?
        # if VC empty except for bots, leave
        non_bot_members = [m for m in vc.channel.members if not m.bot]
        if not non_bot_members:
            tsprint(f"Nobody in VC {vc.channel.name} except bots. Leaving.")
            await self.try_leave_vc(guild_id)

    @discord.Cog.listener()
    async def on_ready(self):
        tsprint("Initializing guild VC list...")

        for guild in self.bot.guilds:
            self.vc_state.init_guild(guild.id)
            self.tts_manager.init_guild(guild.id)
        
        tsprint("Creating TTS queue task in event loop...")
        self.bg_task.start(self.bot, self.vc_state, self.tts_manager)

        tsprint("VC Cog is now ready!")