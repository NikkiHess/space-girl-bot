"""
Lightweight voice-state manager to keep track of guild VC's and the last channel TTS was triggered from.
No major Discord API calls.
"""

# built-in
from typing import Dict, Optional

# pycord
import discord

# my modules
from ..utils.logging_utils import timestamp_print as tsprint

class VCState():
    "Manages the bot's voice channel state"

    def __init__(self):
        # maps guild_id -> VoiceClient | None
        self.vc_dict: Dict[int, Optional[discord.VoiceClient]] = dict()

        # maps guild_id -> last channel id that triggered the bot
        self.last_triggered_channel_dict: Dict[int, Optional[int]] = dict()

    def init_guild(self, guild_id: int):
        """
        Verifies/initializes guild in vc dict and "last triggered channel" dict

        ## Args:
        - `guild_id` (int): the guild ID to verify/initialize
        """
        if guild_id not in self.vc_dict:
            tsprint(f"Initializing guild {guild_id} in VC dict...")
            self.vc_dict[guild_id] = None

        if guild_id not in self.last_triggered_channel_dict:
            tsprint(f"Initializing guild {guild_id} in last triggered dict...")
            self.last_triggered_channel_dict[guild_id] = None

    def set_vc_state(self, guild_id: int, vc: Optional[discord.VoiceClient]):
        """
        Sets the voice channel state in the specified guild

        ## Args:
        - `guild_id` (int): the guild ID to set the voice channel state in
        - `vc` (Optional[discord.VoiceClient]): the voice channel to set to
        """
        self.vc_dict[guild_id] = vc

    def get_vc_state(self, guild_id: int) -> Optional[discord.VoiceClient]:
        """
        Gets the voice channel state in the specified guild

        ## Args:
        - `guild_id` (int): the guild ID to get the voice channel state from

        ## Returns:
        - `vc` (Optional[discord.VoiceClient]): the voice channel obtained
        """
        return self.vc_dict.get(guild_id)
    
    def set_last_triggered(self, guild_id: int, text_channel_id: Optional[int]):
        """
        Sets the last triggered text channel state in the specified guild

        ## Args:
        - `guild_id` (int): the guild ID to set the last triggered text channel state in
        - `text_channel_id` (Optional[int]): the text channel to set the last triggered state to
        """
        self.last_triggered_channel_dict[guild_id] = text_channel_id
    
    def get_last_triggered(self, guild_id: int) -> Optional[int]:
        """
        Gets the last triggered text channel state in the specified guild

        ## Args:
        - `guild_id` (int): the guild ID to get the last triggered text channel state from

        ## Returns:
        - `text_channel_id` (Optional[int]): the text channel obtained
        """
        return self.last_triggered_channel_dict.get(guild_id)
    
    def is_connected(self, guild_id: int) -> bool:
        """
        Checks whether the bot is connected in a specific guild

        ## Args:
        - `guild_id` (int): the guild ID to check voice state in

        ## Returns:
        - True if in a voice channel, False otherwise
        """
        vc = self.get_vc_state(guild_id)
        return vc and vc.is_connected()

    def is_connected_in_channel(self, guild_id: int, channel: discord.VoiceChannel) -> bool:
        """
        Checks whether the bot is in a specific voice channel

        ## Args:
        - `guild_id` (int): the guild ID to check voice state in
        - `channel` (discord.VoiceChannel): the voice channel to check connection status to

        ## Returns:
        - True if in the specified voice channel, False otherwise
        """
        vc = self.get_vc_state(guild_id)
        return vc and vc.is_connected() and vc.channel == channel