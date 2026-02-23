"""
the module that handles tts interactions (right now just TTSVibes)
"""

# built-in modules
import os
import re
from collections import deque
import requests
import base64
import json
from pathlib import Path

# PyPI modules
import emoji

# my modules
from src.utils.logging_utils import timestamp_print as tsprint
from src.tts.voices import TTSVibesVoice as TVV
from src.tts.returncodes import TTSReturnCode as TRC
from src.db import driver as dbd

DOWNLOADS_DIR = os.path.join(os.getcwd(), "downloads")
os.makedirs(DOWNLOADS_DIR, exist_ok=True)

MAX_LEN = 300 # TTSVibes limits us here. TODO: dynamic length for different services?
TTSVIBES_MAX_REPEAT = 4
# exclude members that start with _ because they are hidden
TTSVIBES_VOICES = [voice.replace("_", " ") for voice in TVV._member_names_ if not voice.startswith("_")]
TTS_VOICES = TTSVIBES_VOICES + [] # you can add more :3

EMOJI_DICT = Path(f"{os.getcwd()}/emoji.json") # read in emoji.json
EMOJI_DICT = EMOJI_DICT.read_text(encoding="utf-8") # read text from emoji.json
EMOJI_DICT: dict = json.loads(EMOJI_DICT) # load into a dict

LEGACY_PRONUNCIATION_DICTIONARY = {
    "lol": {
        "translation": "lawl",
        "case_sensitive": False
    },
    "uwu": {
        "translation": "ooh woo",
        "case_sensitive": False
    },
    ":3": {
        "translation": "colon three",
        "case_sensitive": False
    },
    "minecraft": {
        "translation": "mine craft",
        "case_sensitive": False
    },
    "lmao": {
        "translation": "LMAO",
        "case_sensitive": False
    },
    "labubu": {
        "translation": "luh booboo",
        "case_sensitive": False
    },
    "bros": {
        "translation": "bro's",
        "case_sensitive": False
    },
    "pls": {
        "translation": "please",
        "case_sensitive": False
    },
    "brb": {
        "translation": "b r b",
        "case_sensitive": False
    },
    r">:\(": {
        "translation": "angry face",
        "case_sensitive": False
    },
    r":\)": {
        "translation": "smiley face",
        "case_sensitive": False
    },
    r":\(": {
        "translation": "sad face",
        "case_sensitive": False
    },
    r":o": {
        "translation": "shocked face",
        "case_sensitive": False
    },
    r"D:": {
        "translation": "big shocked face",
        "case_sensitive": True
    },
    r":D": {
        "translation": "big smile face",
        "case_sensitive": True
    },
    r"<3": {
        "translation": "heart",
        "case_sensitive": False
    },
    "regex": {
        "translation": "regh ex",
        "case_sensitive": False
    }
}

def adjust_pronunciation(text: str, voice: str, guild_id: int) -> str:
    """
    Makes various adjustments to input text to make tts sound and function better

    :param str text: the text to adjust
    :param str voice: the name of the voice to adjust pronunciation for
    :param int guild_id: the Discord ID for the guild we're executing in
    
    :return str: the adjusted input
    """

    # ----- HANDLE UNICODE EMOJI -----
    # remove variation selectors first
    text = re.sub(r"[\uFE0F\uFE0E]", "", text)

    # callback to replace emoji with their names, more reliable than regex on MANY levels
    def replace_match(unicode_emoji: str, _: dict) -> str:
        name = EMOJI_DICT.get(unicode_emoji) # match emoji to name
        if not name or not name.strip():
            return ""
        
        # whitespace to ensure we don't end up with strings like "footballred heart"
        return f" {name} "

    # replaces each emoji with its name surrounded by colons and whitespace
    text = emoji.replace_emoji(text, replace=replace_match)
    # --------------------------------

    # ----- HANDLE DISCORD EMOJI -----
    # discord_emoji = re.findall(r"")

    # --------------------------------

    # max 1 space between words, and no whitespace on ends
    text = re.sub(r"\s+", " ", text).strip()

    # TODO: handle Discord emojis
    # TODO: add this to database, make way to add global pronunciation via bot (NIKKI ONLY)
    # TODO: handle "wa" -> "wah", but not when it would be washington (after a comma)
    # TODO: add filtering for "hahaha" -> "ha ha ha", applies to any number of ha's
    
    # - HANDLE CUSTOM PRONUNCIATIONS -
    voice_pronunciation_dict = dbd.list_pronunciations(guild_id, voice) | dbd.list_pronunciations(guild_id, "All Voices")
    global_pronunciation_dict = dbd.list_pronunciations(-1, voice) | dbd.list_pronunciations(-1, "All Voices")

    for original, pronunciation in voice_pronunciation_dict.items():
        text = text.replace(original, pronunciation)

    for original, pronunciation in global_pronunciation_dict.items():
        text = text.replace(original, pronunciation)
    # --------------------------------


    # TTS vibes pronounces the same words wrongly across voices
    if voice in TTSVIBES_VOICES:
        # for each translation, apply to the text
        # making sure to account for whether it's case sensitive
        for trigger, data in LEGACY_PRONUNCIATION_DICTIONARY.items():
            flags = re.IGNORECASE if not data["case_sensitive"] else 0
            text = re.sub(trigger, data["translation"], text, flags=flags)

        # if the whole input is "no", add a period so voice doesn't say "number"
        if text.lower() == "no":
            text = "no."
        
    return text

# TODO: make it so TTS that is too long just sends multiple API requests.
def download_and_queue_tts_vibes(input: str, voice: TVV, tts_queue_deque: deque, guild_id: int) -> bool:
    """
    downloads a voice line from the TTS Vibes API and adds it to the TTS queue

    :param str input: the text to speak
    :param TVV voice: the TTS Vibes voice to use
    :param deque tts_queue_deque: the tts deque (from dict) to add to

    :return TRC: the return code, to indicate whether valid or not and in what way
    """

    tsprint(f"Getting {voice.name} TTS...")

    # strip illegal chars from input to put into filename
    filename = re.sub(r'[\\/*?:"<>,|]', "", input)

    # make sure filename is not too long (factoring in .mp3)
    if len(filename) > 251:
        return TRC.TOO_LONG
    filepath = os.path.join("downloads", f"{filename}.mp3")

    # make any necessary pronunciation changes/emoji translations prior to checking repeat chars
    input = adjust_pronunciation(input, voice.name, guild_id)

    # make sure final input length is not too long
    if len(input) > MAX_LEN:
        return TRC.TOO_LONG
    
    # if we have even a single instance of too many repeat chars, shut it down
    if re.search("((\\S)\\2{" + str(TTSVIBES_MAX_REPEAT) + ",})", input):
        return TRC.TOO_MANY_REPEAT_CHARS

    # request from the TTS Vibes API (subject to change)
    url = "https://ttsvibes.com/?/generate"
    headers = {
        "x-sveltekit-action": "true",
        "content-type": "application/x-www-form-urlencoded",
        "origin": "https://ttsvibes.com",
        "referer": "https://ttsvibes.com/storyteller",
        "user-agent": "Mozilla/5.0"
    }
    data = {
        "selectedVoiceValue": voice.value,
        "text": input
    }

    response = requests.post(url, headers=headers, data=data)

    response = response.json() # get response json

    # sometimes even with my filters TTSVibes just doesn't like stuff
    # tts vibes just doesn't like spammy stuff I guess...
    if response["type"] == "error":
        error_msg = response["error"]["message"]
        tsprint(f"Could not get TTS from TTS Vibes. {error_msg}")

        if "supported for this language" in error_msg:
            return TRC.LANGUAGE_UNSUPPORTED
        
        return TRC.GENERIC_TTSVIBES_ERROR

    response = response["data"] # get data (actual response payload)

    # parse data json string
    parsed_data = json.loads(response)

    # in the json data, the base64 string is 3rd within a list
    base64_string = parsed_data[2]

    # decode to bytes
    decoded_audio_bytes = base64.b64decode(base64_string)

    with open(filepath, "wb") as file:
        file.write(decoded_audio_bytes)

        tsprint(f"Saved TTS to \"{filepath}\"")

    tts_queue_deque.append(filepath)

    return TRC.OKAY