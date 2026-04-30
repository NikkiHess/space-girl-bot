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
import aiohttp, asyncio

# PyPI modules
import emoji

# my modules
from src.utils.logging_utils import timestamp_print as tsprint
from src.tts.voices import TikTokVoice as TTV
from src.tts.returncodes import TTSReturnCode as TRC

DOWNLOADS_DIR = os.path.join(os.getcwd(), "downloads")
os.makedirs(DOWNLOADS_DIR, exist_ok=True)

CHUNK_SIZE = 300 # TikTok voices limit us here. TODO: dynamic length for different services?
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

    # TODO: handle Discord emojis, how do we/can we make it so that they can come through the bot's messages?
    # TODO: add this to database, make way to add global pronunciation via bot (NIKKI ONLY)
    # TODO: handle "wa" -> "wah", but not when it would be washington (after a comma)
    # TODO: add filtering for "hahaha" -> "ha ha ha", applies to any number of ha's
    
    # TikTok voices pronounce the same words wrongly
    if voice in TIKTOK_VOICES:
        LEGACY_PRONUNCIATION_DICTIONARY = {
            "lol": {
                "pronunciation": "lawl",
                "case_sensitive": False
            },
            "minecraft": {
                "pronunciation": "mine craft",
                "case_sensitive": False
            },
            "lmao": {
                "pronunciation": "LMAO",
                "case_sensitive": False
            },
            "labubu": {
                "pronunciation": "luh booboo",
                "case_sensitive": False
            },
            "bros": {
                "pronunciation": "bro's",
                "case_sensitive": False
            },
            "pls": {
                "pronunciation": "please",
                "case_sensitive": False
            },
            "brb": {
                "pronunciation": "b r b",
                "case_sensitive": False
            },
            r">:\)": {
                "pronunciation": "evil face",
                "case_sensitive": False
            },
            r":\)": {
                "pronunciation": "smiley face",
                "case_sensitive": False
            },
            r">:\(": {
                "pronunciation": "angry face",
                "case_sensitive": False
            },
            r":\(": {
                "pronunciation": "sad face",
                "case_sensitive": False
            },
            ":o": {
                "pronunciation": "shocked face",
                "case_sensitive": False
            },
            "D:": {
                "pronunciation": "shocked face",
                "case_sensitive": True
            },
            ":D": {
                "pronunciation": "big smile face",
                "case_sensitive": True
            },
            "uwu": {
                "pronunciation": "ooh woo",
                "case_sensitive": False
            },
            ">:3": {
                "pronunciation": "evil cat face",
                "case_sensitive": False
            },
            ":3": {
                "pronunciation": "cat face",
                "case_sensitive": False
            },
            "<3": {
                "pronunciation": "heart",
                "case_sensitive": False
            },
            "regex": {
                "pronunciation": "regh ex",
                "case_sensitive": False
            },
            "params": {
                "pronunciation": "puh rams",
                "case_sensitive": False
            },
            "unironically": {
                "pronunciation": "un ironically",
                "case_sensitive": False
            },
            "ngl": {
                "pronunciation": "not gonna lie",
                "case_sensitive": False
            },
            "wtf": {
                "pronunciation": "what the fuck",
                "case_sensitive": False
            },
            "ykwim": {
                "pronunciation": "you know what I mean",
                "case_sensitive": False
            },
            "rq": {
                "pronunciation": "real quick",
                "case_sensitive": False
            },
            "github": {
                "pronunciation": "git hub",
                "case_sensitive": False
            },
            "fr": {
                "pronunciation": "for real",
                "case_sensitive": False
            },
            "wdym": {
                "pronunciation": "what do you mean",
                "case_sensitive": False
            },
            "cuz": {
                "pronunciation": "cuhs", # TODO: this kinda sucks, find a better one
                "case_sensitive": False
            },
            "oop": {
                "pronunciation": "oohp",
                "case_sensitive": False
            },
            "tbh": {
                "pronunciation": "to be honest",
                "case_sensitive": False
            },
            "nvm": {
                "pronunciation": "never mind",
                "case_sensitive": False
            }
            # TODO: handle certain context-sensitive stuff, like NO after some words causes it to say nitrogen monoxide
        }
            
        # for each pronunciation, apply to the text
        # making sure to account for whether it's case sensitive
        for trigger, data in LEGACY_PRONUNCIATION_DICTIONARY.items():
            flags = re.IGNORECASE if not data["case_sensitive"] else 0

            # BUG: phrases that include non-alphanumeric characters are excluded by this... how do I fix that?
            text = re.sub(r"\b" + trigger + r"\b", data["pronunciation"], text, flags=flags)

        # if the whole input is "no", add a period so voice doesn't say "number"
        if text.lower() == "no":
            text = "no."
        
    return text

def smart_split(input_text: str, max_chunk_length: int = CHUNK_SIZE):
    """
    splits an input text by length, constrained by whitespace

    :param str input_text: the text to split
    :param int max_chunk_length: the max length of the split, defaults to the program's max length
    :return TRC: the return code, to indicate whether valid or not and in what way
    """
    split_text = []

    # split by length constrained by whitespace
    while len(input_text) > 0:
        chunk = input_text[:max_chunk_length]
        
        # if the chunk is maximum length, find the last whitespace character and cut it off there instead
        if len(chunk) == max_chunk_length:
            whitespace_matches = re.finditer(r"\s", chunk)
            whitespace_matches = list(whitespace_matches)
            last_match = {
                "char": whitespace_matches[-1].group(0),
                "index": whitespace_matches[-1].start()
            }

            # if we found whitespace, remove trim the max length chunk and remove it from the string
            if last_match:
                chunk = input_text[:last_match["index"]]
                input_text = input_text.replace(chunk + last_match["char"], "", 1)
            # if no whitespace, just remove the chunk
            else: input_text = input_text.removeprefix(chunk)
        # if the chunk isn't maximum length, we can just clear the input text and split by the maximum length no problem
        else: input_text = ""

        # finally, append the split text
        split_text.append(chunk)

    return split_text

async def download_and_queue_tiktok(input_text: str, voice: TTV, tts_queue_deque: deque) -> TRC:
    """
    downloads a TikTok voice line and adds it to the TTS queue

    :param input_text: the text to speak
    :type input_text: str
    :param voice: the TikTok voice to use
    :type voice: TVV
    :param tts_queue_deque: the tts deque (from dict) to add to
    :type tts_queue_deque: deque
    :return: the return code, to indicate whether valid or not and in what way
    :rtype: TRC
    """
    tsprint(f"Getting {voice.name} TTS...")
    # make any necessary pronunciation changes/emoji pronunciations prior to checking repeat chars

    adjusted_input = adjust_pronunciation(input_text, voice.name)

    # use chunking, if necessary
    split_text = smart_split(adjusted_input)

    async with aiohttp.ClientSession():
        # for loop will send separate requests for each chunk
        for index, split_item in enumerate(split_text):
            # strip illegal chars from input to put into filename
            filename = re.sub(r'[\\/*?:"<>,|]', "", split_item)
            filename = f"{filename[:100].rstrip()} part {index}"
            filename_ext = f"{filename}.mp3"

            # make sure filename is not too long (factoring in .mp3)
            filepath = os.path.join("downloads", filename_ext)

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
                "text": split_item
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

            tts_queue_deque.append(f"{filename}.mp3")

            tsprint(f"Queued TTS \"{split_item}\"")

            await asyncio.sleep(0.1)

    return TRC.OKAY

# TODO: add gTTS support (it's free)