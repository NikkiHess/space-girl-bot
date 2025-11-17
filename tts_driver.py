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

# my modules
from nikki_util import timestamp_print as tsprint

DOWNLOADS_DIR = os.path.join(os.getcwd(), "downloads")
os.makedirs(DOWNLOADS_DIR, exist_ok=True)

MAX_LEN = 300
TTS_VOICES = ["marcus"]

def adjust_pronunciation(input: str, voice: str):
    """
    Makes various adjustments to input text to make tts sound and function better

    ## Args:
    - `input` (str): the text to adjust
    - `voice` (str): the voice to adjust pronunciation for

    ## Returns:
    - `input` (str): the adjusted input
    """

    # marcus-related voice stuff
    if voice == "Marcus":
        # TODO: add this to database, make way to add global pronunciation via bot
        LEGACY_PRONUNCIATION_DICTIONARY = {
            "lol": "lawl",
            "uwu": "ooh woo",
            ":3": "colon three",
            "minecraft": "mine craft",
            "lmao": "LMAO",
            "labubu": "luh booboo",
            "bros": "bro's"
        }
            
        for trigger, replacement in LEGACY_PRONUNCIATION_DICTIONARY.items():
            input = re.sub(trigger, replacement, input, flags=re.IGNORECASE)

        # if the whole input is no, add a period so marcus doesn't say number
        if input.lower() == "no":
            input = "no."

    return input

def download_and_queue_marcus_tts(input: str, tts_queue_dict: dict) -> bool:
    """
    downloads Marcus TTS from the TTS Vibes API and adds it to the TTS queue

    ## Args:
    - `input` (str): the text to speak (max 300 chars)
    - `tts_queue` (dict): the tts queue (from dict) to add to

    ## Returns:
    - `was_too_long` (bool): whether the input got trimmed/was too long
    """

    tsprint("Getting Marcus TTS...")

    was_too_long = False

    # trim input if too long
    if len(input) > MAX_LEN:
        input = input[:MAX_LEN-1]
        was_too_long = True
        
    # strip illegal chars from input to put into filename
    filename = re.sub(r'[\\/*?:"<>,|]', "", input)
    filepath = os.path.join("downloads", f"{filename}.mp3")

    input = adjust_pronunciation(input, "Marcus")

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
        "selectedVoiceValue": "tt-en_male_narration",
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

if __name__ == "__main__":
    download_and_queue_marcus_tts("lawl")
    download_and_queue_marcus_tts("hello robert")