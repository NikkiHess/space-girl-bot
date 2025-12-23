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

DOWNLOADS_DIR = os.path.join(os.getcwd(), "downloads")
os.makedirs(DOWNLOADS_DIR, exist_ok=True)

MAX_LEN = 300
TTSVIBES_VOICES = [voice.replace("_", " ") for voice in TVV._member_names_]

TTS_VOICES = TTSVIBES_VOICES + [] # you can add more :3

EMOJI_DICT = Path(f"{os.getcwd()}/emoji.json") # read in emoji.json
EMOJI_DICT = EMOJI_DICT.read_text() # read text from emoji.json
EMOJI_DICT: dict = json.loads(EMOJI_DICT) # load into a dict

def adjust_pronunciation(text: str, voice: str) -> str:
    """
    Makes various adjustments to input text to make tts sound and function better

    :param text: the text to adjust
    :type text: str
    :param voice: the voice to adjust pronunciation for
    :type voice: str
    :return: the adjusted input
    :rtype: str
    """

    # normalize variation selectors first
    text = re.sub(r"[\uFE0F\uFE0E]", "", text)

    # used to contain emoji names to replace
    # important for pluralization
    names = set()

    # callback to replace emoji with their names, more reliable than regex on MANY levels
    def replace_match(unicode_emoji: str, _: dict) -> str:
        name = EMOJI_DICT.get(unicode_emoji) # match emoji to name
        if not name or not name.strip():
            return ""
        
        # add the name (if not there already) to check for plurality later
        names.add(name)

        # whitespace to ensure we don't have stuff like "man emojiwoman emoji"
        return f" :{name}: "

    # replaces each emoji with its name surrounded by colons and whitespace
    text = emoji.replace_emoji(text, replace=replace_match)

    
    for name in names:
        # sub with name + emojis if there's a plural group
        pattern = rf"(?:(?::{re.escape(name)}:)\s*){{2,}}"
        text = re.sub(pattern, f"{name} emojis ", text)

        # sub with name + emoji if singular
        text = text.replace(f":{name}:", f"{name} emoji ")

    # max 1 space between words, and no whitespace on ends
    text = re.sub(r"\s+", " ", text).strip()

    # TODO: handle Discord emojis
    # TODO: add this to database, make way to add global pronunciation via bot (NIKKI ONLY)
    # TODO: handle "wa" -> "wah", but not when it would be washington (after a comma)
    # TODO: add filtering for "hahaha" -> "ha ha ha", applies to any number of ha's
    
    # TTS vibes pronounces the same words wrongly across voices
    if voice in TTSVIBES_VOICES:
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
            
        # for each translation, apply to the text
        # making sure to account for whether it's case sensitive
        for trigger, data in LEGACY_PRONUNCIATION_DICTIONARY.items():
            flags = re.IGNORECASE if not data["case_sensitive"] else 0
            text = re.sub(trigger, data["translation"], text, flags=flags)

        # if the whole input is "no", add a period so voice doesn't say "number"
        if text.lower() == "no":
            text = "no."
        
    return text

def download_and_queue_tts_vibes(input: str, voice: TVV, tts_queue_dict: dict) -> bool:
    """
    downloads a voice line from the TTS Vibes API and adds it to the TTS queue

    :param input: the text to speak (max 300 chars)
    :type input: str
    :param voice: the TTS Vibes voice to use
    :type voice: TVV
    :param tts_queue_dict: the tts queue (from dict) to add to
    :type tts_queue_dict: dict
    :return: whether the input got trimmed/was too long
    :rtype: bool
    """

    tsprint(f"Getting {voice.name} TTS...")

    was_too_long = False

    # trim input if too long
    if len(input) > MAX_LEN:
        input = input[:MAX_LEN-1]
        was_too_long = True
        
    # strip illegal chars from input to put into filename
    filename = re.sub(r'[\\/*?:"<>,|]', "", input)
    filepath = os.path.join("downloads", f"{filename}.mp3")

    input = adjust_pronunciation(input, voice.name)

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
    if response["type"] == "error":
        tsprint(f"Could not get TTS from TTS Vibes. {response["error"]["message"]}")
        return

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

    tts_queue_dict.append(filepath)

    return was_too_long