"""
the module that handles tts interactions (right now just TTSVibes)

Author:
Nikki Hess (nkhess@umich.edu)
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
from voices import TikTokVoice

DOWNLOADS_DIR = os.path.join(os.getcwd(), "downloads")
os.makedirs(DOWNLOADS_DIR, exist_ok=True)

MAX_LEN = 255 - len("downloads") - len(".mp3")

TTS_QUEUE = deque()

def download_and_queue_marcus_tts(input: str) -> dict:
    """
    downloads Marcus TTS from the TTS Vibes API and adds it to the TTS queue

    ## Args:
    - `input` (str): the text to speak (max 300 chars)
    """
    global TTS_QUEUE

    tsprint("Getting Marcus TTS...")

    # trim input if too long
    if len(input) > MAX_LEN:
        input = input[:MAX_LEN-1]
        
    # strip illegal chars from input to put into filename
    filename = re.sub(r'[\\/*?:"<>,|]', "", input)
    filepath = os.path.join("downloads", f"{filename}.mp3")

    # if the file already exists, skip the download and just play it
    file_exists = False
    if os.path.exists(filepath):
        file_exists = True
        tsprint("File already exists, skipping download.")

    if not file_exists:
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

    TTS_QUEUE.append(filepath)
    tsprint(f"Added \"{input}\" to queue.")

if __name__ == "__main__":
    download_and_queue_marcus_tts("robert help")
    download_and_queue_marcus_tts("i am mildly irritated")