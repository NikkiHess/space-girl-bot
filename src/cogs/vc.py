"""
Contains the VC Cog for the Discord API
"""

# built-in
from collections import deque
from typing import Optional, Dict, Deque
import asyncio
import platform
import os

# Pycord
import discord
from discord.ext import commands

# my modules
from ..db import driver as dbd
from ..tts import driver as ttsd
from ..tts.voices import TTSVibesVoice as TVV
from ..utils.logging_utils import timestamp_print as tsprint
from ..utils.discord_utils import get_random_app_emoji
from ..errors import *

# required for cogs API
def setup(bot):
    bot.add_cog(VCCog(bot))

class VCCog(commands.Cog):
    """
    Handles:
    1.) Commands: tts, join, leave
    """

    def __init__(self, bot):
        self.bot = bot
        self.vc_dict: Dict[int, Optional[discord.VoiceClient]] = dict()
        self.tts_queue_dict: Dict[int, Dict[str, Deque[str]]] = dict()
        self.last_triggered_channel_dict: Dict[int, int] = dict()

    # HELPERS
    async def try_leave_vc(self, guild_id: int, ctx: Optional[discord.ApplicationContext] = None):
        """
        Attempts to leave a VC in a guild, optionally sending a message if ctx is given.
        """
        tsprint("Bot attempting to leave VC...")
        
        vc = self.vc_dict.get(guild_id)
        if not vc or not vc.is_connected():
            tsprint("Bot was not in a VC")
            if ctx:
                await ctx.respond("❌ I am not currently in a VC.")
            return

        if ctx:
            await ctx.respond("👋🏻 Left voice!")

        # reset triggered channel
        self.last_triggered_channel_dict[guild_id] = None

        await vc.disconnect()
        self.vc_dict[guild_id] = None

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
        Does TTS, currently only Marcus.
        """
        # make sure VC and TTS_QUEUE dicts have entries for this guild
        if ctx.guild_id not in self.vc_dict:
            tsprint(f"Adding guild to the TTS queue system...")
            self.vc_dict[ctx.guild_id] = None
        if ctx.guild_id not in self.tts_queue_dict:
            tsprint(f"Adding voices to the TTS queue system in {ctx.guild_id}...")
            self.tts_queue_dict[ctx.guild_id] = {voice: deque() for voice in ttsd.TTS_VOICES}

        # silently acknowledge the command
        await ctx.defer()

        # if the user isn't in a VC, it doesn't make sense to do TTS
        # TODO: evaluate this, server setting?
        voice_state = ctx.author.voice
        if voice_state is None:
            await ctx.respond("❌ You are not in a VC.")
            return

        current_vc = self.vc_dict.get(ctx.guild_id)
        # if the bot is not in the current VC, connect it
        if current_vc is None or current_vc.channel != voice_state.channel:
            await self.try_leave_vc(ctx.guild_id)
            self.vc_dict[ctx.guild_id] = await voice_state.channel.connect(reconnect=False)
        
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
            voice_internal = voice.replace(" ", "_") # internal voice names are goofy, TODO: is there a better way to do this?

            # is this as TTSVibes voice?
            if voice_internal in TVV._member_names_:
                was_too_long = ttsd.download_and_queue_tts_vibes(
                    input,
                    TVV[voice_internal], 
                    self.tts_queue_dict[ctx.guild_id][voice]
                )
            
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
        self.last_triggered_channel_dict[ctx.guild_id] = ctx.channel_id

        voice_state = ctx.author.voice

        # not in a vc
        if vc is None and voice_state is None:
            await ctx.respond("❌ You are not in a VC.")
            return
        
        if self.vc_dict[ctx.guild_id] is not None:
            await ctx.respond("❌ Already connected in this guild.")
            return
        
        await ctx.defer(invisible=False)
        await ctx.respond(content="🛜 Connecting...")
        
        if vc is None:
            voice_channel = voice_state.channel
        else:
            voice_channel = vc
        
        self.vc_dict[ctx.guild_id] = await voice_channel.connect(reconnect=False)

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
                self.vc_dict[guild_id] = None
                tsprint(f"Bot left VC {before.channel.name} in {guild_id}.")
            return # no need to check for emptiness if bot left
        
        # check if the bot is in a VC in this guild, just to make sure
        vc = self.vc_dict.get(guild_id)
        if vc is None or not vc.is_connected():
            return
        
        # BUG: why doesn't this work properly? is it because we rely on self.vc_dict? is there a better way?
        # if VC empty except for bots, leave
        non_bot_members = [m for m in vc.channel.members if not m.bot]
        if not non_bot_members:
            await self.try_leave_vc(guild_id)

    @discord.Cog.listener()
    async def on_ready(self):
        tsprint("Initializing guild VC list...")

        for guild in self.bot.guilds:
            self.vc_dict[guild.id] = None
            self.tts_queue_dict[guild.id] = dict()

            for voice in ttsd.TTS_VOICES:
                self.tts_queue_dict[guild.id][voice] = deque()
        
        tsprint("Creating TTS queue task in event loop...")
        self.bot.loop.create_task(self.process_tts_queue())

        tsprint("VC Cog is now ready!")

    async def process_tts_queue(self):
        """
        Processes TTS queue - runs in Pycord event loop
        """
        ffmpeg_path = None
        
        match platform.system():
            case "Windows":
                ffmpeg_path = os.path.join("depend", "ffmpeg.exe")
            case "Darwin":
                ffmpeg_path = "/opt/homebrew/bin/ffmpeg"
            case _:
                raise OSNotSupportedError()
        
        def make_after_callback(tts_filename, guild_id):
            def after_play(_):  # The `_` is the exception Pycord passes
                tsprint(f"Audio done playing in {guild_id}: {tts_filename}")
                try:
                    os.remove(tts_filename)
                    tsprint(f"Deleted \"{tts_filename}\"")
                except FileNotFoundError:
                    tsprint(f"File {tts_filename} already deleted")
            return after_play

        while True:
            for guild_id, vc in self.vc_dict.items():
                if vc is None or not vc.is_connected():
                    continue

                for voice, queue in self.tts_queue_dict[guild_id].items():
                    if queue and not vc.is_playing():
                        tts_filename = queue.popleft()
                        tsprint(f"Playing queued TTS {tts_filename} in guild {guild_id}")

                        try:
                            tts_audio_source = discord.FFmpegOpusAudio(
                                executable=ffmpeg_path,
                                source=tts_filename
                            )
                            vc.play(tts_audio_source, after=make_after_callback(tts_filename, guild_id))
                        except Exception as e:
                            tsprint(f"Could not play audio for guild {guild_id}: {e}")
            await asyncio.sleep(0.1)