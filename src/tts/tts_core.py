"""
Manages TTS Queue and background playback loop.
Avoids slash-commands, focuses on audio.
"""

# built-in
from collections import deque
from typing import Dict, Deque, Optional
import asyncio
import os
import platform

# PyPI
import discord

# my modules
from src.tts import driver as ttsd
from src.tts.returncodes import TTSReturnCode as TRC
from .voices import TTSVibesVoice as TVV
from ..errors import *
from ..utils.logging_utils import timestamp_print as tsprint
from ..vc.vc_state import VCState

class TTSManager():
    """
    Holds the TTS queue and its contents, allows you to queue into the TTS queue
    """

    def __init__(self):
        # maps guild_id -> voice_name -> deque of filenames to play
        self.tts_queue_dict: Dict[int, Dict[str, Deque[str]]] = dict()

    def init_guild(self, guild_id: int):
        """
        Verifies/initializes guild in "tts queue" dict with all voices

        ## Args:
        - `guild_id` (int): the guild ID to verify/initialize
        """
        if guild_id not in self.tts_queue_dict:
            self.tts_queue_dict[guild_id] = {voice: deque() for voice in ttsd.TTS_VOICES}

    def download_and_queue(self, input: str, voice: TVV, guild_id: TRC) -> int:
        """
        Wraps tts_driver.download_and_queue_tts_vibes
        
        :param input: the text to speak
        :type input: str
        :param voice: the voice to use
        :type voice: TVV
        :param guild_id: the guild ID to queue the TTS in
        :type guild_id: int
        :return: the return code from the function
        :rtype: TRC
        """
        queue_deque = self.tts_queue_dict[guild_id][voice.name]

        return ttsd.download_and_queue_tts_vibes(input, voice, queue_deque)
    
class TTSBackgroundTask():
    """
    Playback loop. Instantiate then call `start` to start the loop.
    """

    def __init__(self):
        self.running = False
        self._task: Optional[asyncio.Task] = None

        match platform.system():
            case "Windows":
                self.ffmpeg_path = os.path.join("depend", "ffmpeg.exe")
            case "Darwin":
                self.ffmpeg_path = "/opt/homebrew/bin/ffmpeg"
            case _:
                self.ffmpeg_path = ""
                raise OSNotSupportedError()

    def start(self, bot: discord.Bot, vc_state, tts_manager: TTSManager):
        """
        Starts the playback loop task if it's not already running.
        
        :param bot: The Discord bot instance we're using
        :type bot: discord.Bot
        :param vc_state: The voice chat state
        :param tts_manager: The TTS manager to use
        :type tts_manager: TTSManager
        """
        tsprint("Starting TTS background task...")

        if self.running: # don't start if already started
            tsprint("TTS background task already running.")
            return
        
        tsprint("Success.")

        self.running = True
        self._task = bot.loop.create_task(self._playback_loop(bot, vc_state, tts_manager))

    def stop(self):
        """
        Stops the playback loop task if it's running.
        """
        tsprint("Stopping TTS background task...")

        if not self.running:
            tsprint("TTS background task not running.")
            return
        
        self._task.cancel()
        self.running = False
        
    async def _playback_loop(self, bot: discord.Bot, voice_state: VCState, tts_manager: TTSManager):
        """
        Processes TTS queue - runs in Pycord event loop
        """

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
            for guild_id, vc in voice_state.vc_dict.items():
                if vc is None or not vc.is_connected():
                    continue

                for voice, queue in tts_manager.tts_queue_dict[guild_id].items():
                    if queue and not vc.is_playing():
                        tts_filename = queue.popleft()
                        tsprint(f"Playing queued TTS {tts_filename} in guild {guild_id}")

                        try:
                            tts_audio_source = discord.FFmpegOpusAudio(
                                executable=self.ffmpeg_path,
                                source=tts_filename
                            )
                            vc.play(tts_audio_source, after=make_after_callback(tts_filename, guild_id))
                        except Exception as e:
                            tsprint(f"Could not play audio for guild {guild_id}: {e}")
            await asyncio.sleep(0.1)