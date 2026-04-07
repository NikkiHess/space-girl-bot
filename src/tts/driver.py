"""
the module that handles tts interactions
"""

# built-in modules
import os
import re
from collections import deque
import requests
import json
from pathlib import Path

# PyPI modules
import emoji

# my modules
from src.utils.logging_utils import timestamp_print as tsprint
from src.tts.voices import TikTokVoice as TTV
from src.tts.returncodes import TTSReturnCode as TRC

DOWNLOADS_DIR = os.path.join(os.getcwd(), "downloads")
os.makedirs(DOWNLOADS_DIR, exist_ok=True)

MAX_LEN = 300 # TikTok voices limit us here. TODO: dynamic length for different services?
TIKTOK_MAX_REPEAT = 4
TIKTOK_VOICES = [voice.replace("_", " ") for voice in TTV._member_names_]
TTS_VOICES = TIKTOK_VOICES + [] # you can add more :3

EMOJI_DICT = Path(f"{os.getcwd()}/emoji.json") # read in emoji.json
EMOJI_DICT = EMOJI_DICT.read_text(encoding="utf-8") # read text from emoji.json
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

    # ----- HANDLE UNICODE EMOJI -----
    # remove emoji variation selectors first
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

    # max 1 space between words, and no whitespace on ends
    text = re.sub(r"\s+", " ", text).strip()

    # TODO: handle Discord emojis
    # TODO: add this to database, make way to add global pronunciation via bot (NIKKI ONLY)
    # TODO: handle "wa" -> "wah", but not when it would be washington (after a comma)
    # TODO: add filtering for "hahaha" -> "ha ha ha", applies to any number of ha's
    
    # TikTok voices pronounce the same words wrongly
    if voice in TIKTOK_VOICES:
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

def download_and_queue_tiktok(adjusted_input: str, voice: TTV, tts_queue_deque: deque) -> TRC:
    """
    downloads a TikTok voice line and adds it to the TTS queue

    :param input: the text to speak
    :type input: str
    :param voice: the TikTok voice to use
    :type voice: TVV
    :param tts_queue_deque: the tts deque (from dict) to add to
    :type tts_queue_deque: deque
    :return: the return code, to indicate whether valid or not and in what way
    :rtype: TRC
    """

    tsprint(f"Getting {voice.name} TTS...")

    # strip illegal chars from input to put into filename
    filename = re.sub(r'[\\/*?:"<>,|]', "", adjusted_input)
    filename = filename[:100] + "..."

    # make sure filename is not too long (factoring in .mp3)
    filepath = os.path.join("downloads", f"{filename}.mp3")

    # make any necessary pronunciation changes/emoji translations prior to checking repeat chars
    adjusted_input = adjust_pronunciation(adjusted_input, voice.name)

    # make sure final input length is not too long
    if len(adjusted_input) > MAX_LEN:
        return TRC.TOO_LONG

    # request from the lazypyro API
    url = f"https://lazypy.ro/tts/request_tts.php"
    headers = {
        "content-type": "application/x-www-form-urlencoded",
        "origin": "https://lazypy.ro",
        "referer": url,
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    data = {
        "service": "TikTok",
        "voice": voice.value,
        "text": adjusted_input
    }
    response = requests.post(url, headers=headers, data=data)

    response = response.json() # get response json

    if not response["success"]:
        error_msg = response["error_msg"]
        tsprint(f"Could not get TTS from lazypyro. {error_msg}")

        if "supported for this language" in error_msg:
            return TRC.LANGUAGE_UNSUPPORTED
        elif "generation is temporarily unavailable":
            return TRC.TEMP_UNAVAILABLE
        
        return TRC.GENERIC_ERROR

    audio_url = response["audio_url"]
    audio_response = requests.get(audio_url)
    decoded_audio_bytes = audio_response.content

    with open(filepath, "wb") as file:
        file.write(decoded_audio_bytes)

        tsprint(f"Saved TTS to \"{filepath}\"")

    tts_queue_deque.append(filepath)

    return TRC.OKAY