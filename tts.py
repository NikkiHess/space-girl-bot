from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

import os

TTS_VIBES_URL = "https://ttsvibes.com/storyteller"

CUSTOM_CHROME = os.path.join(os.getcwd(), "selenium", "chrome", "chrome.exe")
CHROMEDRIVER_PATH = os.path.join(os.path.dirname(__file__), "selenium", "chromedriver.exe")

def open_driver():
    """
    Opens a headless Chrome instance with which to do TTS

    Returns:
        driver (webdriver.Chrome): the created headless chrome instance
    """

    # options for our chromedriver
    options = Options()
    options.binary_location = CUSTOM_CHROME # use a custom chrome binary to match our driver
    options.add_argument("--headless") # do not the gui
    options.add_argument("--disable-gpu") # do not the gpu
    options.add_argument('--no-sandbox') # do not the sandbox

    # get the chromedriver service
    service = Service(CHROMEDRIVER_PATH)

    # get the TTS vibes site
    driver = webdriver.Chrome(service=service, options=options)

    return driver

def open_tts_vibes(driver: webdriver.Chrome):
    """
    Opens the TTS Vibes website in the given driver.

    Args: 
        driver (webdriver.Chrome): the webdriver to use
    """

    driver.get(TTS_VIBES_URL)

def get_tts_vibes_tts(driver: webdriver.Chrome, input: str):
    """
    Does TTS through the TTS Vibes website

    Args: 
        driver (webdriver.Chrome): the webdriver to use
        input (str): the text to speak

    Returns:
        the downloaded file
    """

    # input the text and make sure it inputted properly
    text_input = driver.find_element(by=By.ID, value="text")
    text_display = driver.find_element(by=By.NAME, value="text")

    text_input.send_keys(input)

    if text_display.get_property("value") != input:
        print("Something went wrong with our input. Try again.")
        return
    
    # TODO: generate, download, and return

if __name__ == "__main__":
    driver = open_driver()

    open_tts_vibes(driver)
    get_tts_vibes_tts(driver)

    driver.quit()