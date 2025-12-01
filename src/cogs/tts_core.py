"""
Manages TTS Queue and background playback loop.
Avoids slash-commands, focuses on audio.
"""

from collections import deque
from typing import Dict, Deque, Optional
import asyncio
import os
import platform
import discord

from ..tts import driver as ttsd
from ..tts.voices import TTSVibesVoice as TVV
from ..errors import *
from ..utils.logging_utils import timestamp_print as tsprint

class TTSManager:
    def __init__(self):
        # maps guild_id -> voice_name -> deque of filenames to play
        self.tts_queue_dict = Dict[int, Dict[str, Deque[str]]] = dict()

    def init_guild(self, guild_id: int):
        """
        Verifies/initializes guild in "tts queue" dict with all voices

        ## Args:
        - `guild_id` (int): the guild ID to verify/initialize
        """
        if guild_id not in self.tts_queue_dict:
            self.tts_queue_dict[guild_id] = {voice: deque() for voice in ttsd.TTS_VOICES}

    def download_and_queue(self, guild_id: int, voice_name: str, filename: str):