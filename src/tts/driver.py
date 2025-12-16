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

# PyPI modules
import emoji

# my modules
from ..utils.logging_utils import timestamp_print as tsprint
from ..tts.voices import TTSVibesVoice as TVV

DOWNLOADS_DIR = os.path.join(os.getcwd(), "downloads")
os.makedirs(DOWNLOADS_DIR, exist_ok=True)

MAX_LEN = 300
TTSVIBES_VOICES = [voice.replace("_", " ") for voice in TVV._member_names_]

TTS_VOICES = TTSVIBES_VOICES + [] # you can add more :3

def handle_emojis(text: str) -> str:
    """
    Transform emojis into "more speakable" text
    
    :param text: The text (theoretically) containing emojis
    :type text: str
    :return: the "more speakable" string
    :rtype: str
    """
    # convert Unicode emojis to text
    text = emoji.demojize(text, delimiters=("", " emoji"))
    text = re.sub(
        r"face_with_([a-z0-9_]+)",
        lambda match: match.group(1).replace("_", " "),
        text,
        flags=re.IGNORECASE
    )

    return text

print(handle_emojis("😍"))

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

    text = handle_emojis(text)

    # TODO: handle Discord emojis
    # TODO: add this to database, make way to add global pronunciation via bot (NIKKI ONLY)
    # TODO: handle "wa" -> "wah", but not when it would be washington (after a comma)
    # TODO: add filtering for "hahaha" -> "ha ha ha", applies to any number of ha's
    
    # TTS vibes pronounces the same words wrongly across voices
    if voice in TTSVIBES_VOICES:
        LEGACY_PRONUNCIATION_DICTIONARY = {
            "lol": "lawl",
            "uwu": "ooh woo",
            ":3": "colon three",
            "minecraft": "mine craft",
            "lmao": "LMAO",
            "labubu": "luh booboo",
            "bros": "bro's",
            "pls": "please",
            "brb": "b r b",
            r">:\(": "angry face",
            r":\)": "smiley face",
            r":\(": "sad face",
            r":o": "shocked face",
            r"D:": "big shocked face",
            r":D": "big smile face",
            r"<3": "heart",
            "regex": "regh ex"
        }
            
        for trigger, replacement in LEGACY_PRONUNCIATION_DICTIONARY.items():
            text = re.sub(trigger, replacement, text, flags=re.IGNORECASE)


        # if the whole input is no, add a period so voice doesn't say number
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