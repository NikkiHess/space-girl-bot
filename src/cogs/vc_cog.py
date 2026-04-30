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
from src.tts.voices import TikTokVoice as TTV
from src.utils.logging_utils import timestamp_print as tsprint
from src.utils.discord_utils import get_random_app_emoji
from src.errors import *
from src.vc.vc_state import VCState
from src.tts.tts_core import TTSManager, TTSBackgroundTask
from src.tts import driver as ttsd
from src.tts.returncodes import TTSReturnCode as TRC

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
    @discord.Cog.listener()
    async def on_message(self, message: discord.Message):
        """
        Does TTS (soon to include Moonbase Alpha, REPO)
        """
        # gather data from the message about its context
        guild = message.guild
        author = message.author
        text_channel = message.channel
        content = message.content

        db_user_voice = dbd.get_user_voice(author.id)
        if db_user_voice:
            voice = db_user_voice
        else:
            await text_channel.send("❌ You need to set a voice with /settings user voice")
            return

        # make sure vc and tts queue dicts have entries for this guild
        self.vc_state.init_guild(guild.id)
        self.tts_manager.init_guild(guild.id)

        # if the user isn't in a VC, it doesn't make sense to do TTS
        author_vc = author.voice
        if author_vc is None:
            await text_channel.send("❌ You are not in a VC.")
            return

        if not self.vc_state.is_connected_in_channel(guild.id, author_vc.channel):
            await self.try_leave_vc(guild.id)
            vc = await author_vc.channel.connect(reconnect=False)
            self.vc_state.set_vc_state(guild.id, vc)

        # --------------------------------

        # ----- HANDLE PINGS -----
        # TODO: is there a better way to do this? this feels like it violates DRY
        # translate raw user mentions to nicknames
        raw_mentions = discord.utils.raw_mentions(content)
        for user_id in raw_mentions:
            content = content.replace(
                f"<@{user_id}>",
                "@" + guild.get_member(user_id).nick
            )
        
        # translate raw role mentions to role names
        raw_mentions = discord.utils.raw_role_mentions(content)
        for role_id in raw_mentions:
            content = content.replace(
                f"<@&{role_id}>",
                "@" + guild.get_role(role_id).name
            )
        
        # translate raw channel mentions to role names
        raw_mentions = discord.utils.raw_channel_mentions(content)
        for channel_id in raw_mentions:
            content = content.replace(
                f"<#{channel_id}>",
                "#" + guild.get_channel(channel_id).name.replace("-", " ")
            )
        # --------------------------------

        return_code = TRC.NONE
        # download and queue the voice line
        if voice in ttsd.TTS_VOICES:
            # TODO: can this be updated to use the list in ttsd instead?
            voice_internal = voice.replace(" ", "_") # internal voice names are goofy, translate them pls

            # is this a LazyPyro voice?
            if voice_internal in TTV._member_names_:
                return_code = await self.tts_manager.download_and_queue(content, TTV[voice_internal], guild.id)
        
        # error return codes? make error known
        if return_code == TRC.LANGUAGE_UNSUPPORTED:
            await text_channel.send(f"❌ Unsupported phonemes or characters in message.")
        if return_code == TRC.TEMP_UNAVAILABLE:
            await text_channel.send(f"❌ Lazypyro is temporarily unavailable.")
        if return_code == TRC.GENERIC_ERROR:
            await text_channel.send(f"❌ Generic error from lazypyro.")

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

    @discord.command(name="leave", description="Leaves whatever voice chat it's currently in.")
    async def cmd_leave(self, ctx: discord.ApplicationContext):
        """
        Command wrapper to leave VC from current guild.
        """
        await self.try_leave_vc(ctx.guild_id, ctx)

    # EVENTS

    # TODO: make it so when the bot leaves it clears the TTS queue and deletes all files for the server
    # in order to do this we may need separate folders for each server within /downloads
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
        non_bot_members = [member for member in vc.channel.members if not member.bot]
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