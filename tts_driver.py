"""
the module that handles tts interactions (right now just TTSVibes)

author:
Nikki Hess (nkhess@umich.edu)
"""

# built-in modules
import os
import time
import re
import platform

# PyPI modules
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException

# my modules
from nikki_util import timestamp_print as tsprint

TTS_VIBES_URL = "https://ttsvibes.com/storyteller"

CUSTOM_CHROME = os.path.join(os.getcwd(), "depend", "selenium", "chrome", "chrome.exe")
CHROMEDRIVER_PATH = os.path.join(os.path.dirname(__file__), "depend", "selenium", "chromedriver.exe")

DOWNLOADS_DIR = os.path.join(os.getcwd(), "downloads")
os.makedirs(DOWNLOADS_DIR, exist_ok=True)

CHAR_LIMIT = 200
MAX_CHAR_REPEAT = 4

def download_wait(directory, timeout, nfiles=None):
    """
    Wait for downloads to finish with a specified timeout.

    Args
    ----
    directory : str
        The path to the folder where the files will be downloaded.
    timeout : int
        How many seconds to wait until timing out.
    nfiles : int, defaults to None
        If provided, also wait for the expected number of files.

    """
    seconds = 0
    dl_wait = True
    while dl_wait and seconds < timeout:
        time.sleep(1)
        dl_wait = False
        files = os.listdir(directory)
        if nfiles and len(files) != nfiles:
            dl_wait = True

        for fname in files:
            if fname.endswith('.crdownload'):
                dl_wait = True

        seconds += 1
    return seconds

def safe_click(driver: webdriver.Chrome, xpath: str, timeout: int=10, retries: int=3):
    """
    tries to click an element even if it goes stale
    
    Args:
        driver (webdriver.Chrome): the webdriver (selenium instance)
        xpath (str): the xpath to follow to get to the element
        timeout (int): the wait time before we give up
        retries (int): the max number of retries
    """
    for _ in range(retries):
        try:
            elem = WebDriverWait(driver, timeout).until(
                EC.element_to_be_clickable((By.XPATH, xpath))
            )
            elem.click()
            return True
        except StaleElementReferenceException:
            time.sleep(0.2)  # let the dom settle
    raise StaleElementReferenceException(f"element stayed stale after {retries} tries")

class CharLimitError(Exception):
    """
    a simple exception to remind users of the char limit.

    Args:
        num_chars (int): the number of characters we have
    """
    
    def __init__(self, num_chars: int):
        self.message = f"The character limit is {CHAR_LIMIT}! You have {num_chars} characters."
        super().__init__(self.message)
        
class CharRepeatError(Exception):
    """
    a simple exception to remind users of the char limit.

    Args:
        num_chars (int): the number of characters repeated
    """
    
    def __init__(self, num_char_repeat: int):
        self.message = f"The character repeat limit is {MAX_CHAR_REPEAT}! You have {num_char_repeat} characters."
        super().__init__(self.message)

def open_driver():
    """
    opens a headless Chrome instance with which to do TTS

    Returns:
        driver (webdriver.Chrome): the created headless chrome instance
    """

    # options for our chromedriver
    options = Options()
    options.binary_location = CUSTOM_CHROME # use a custom chrome binary to match our driver
    # options.add_argument("--headless") # do not the gui
    options.add_argument("--disable-gpu") # do not the gpu
    options.add_argument('--no-sandbox') # do not the sandbox

    prefs = {"download.default_directory": DOWNLOADS_DIR}
    options.add_experimental_option("prefs", prefs) # download to this directory

    # get the chromedriver service
    service = Service(CHROMEDRIVER_PATH)

    # get the TTS vibes site
    driver = webdriver.Chrome(service=service, options=options)

    return driver

def open_tts_vibes(driver: webdriver.Chrome):
    """
    opens the TTS Vibes website in the given driver.

    Args:
        driver (webdriver.Chrome): the webdriver to use
    """

    driver.get(TTS_VIBES_URL)

def get_marcus_tts(driver: webdriver.Chrome, input: str):
    """
    does TTS through the TTS Vibes website

    Args:
        driver (webdriver.Chrome): the webdriver to use
        input (str): the text to speak (max 300 chars)

    Returns:
        the downloaded file
    """
    if len(input) > CHAR_LIMIT:
        raise CharLimitError(len(input))
    
    matches = [m.group(0) for m in re.finditer(r"(.)\1{4,}", input)]

    if len(matches) > 0:
        raise CharRepeatError(len(matches[0]))

    # step 1: await text input readiness, then input the text
    tsprint("Awaiting text input availibility...")

    text_input = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "text"))
    )

    tsprint("Inputting text...")
    # to make sure this goes fast, edit directly via JavaScript
    driver.execute_script("arguments[0].value = arguments[1]; arguments[0].dispatchEvent(new Event('input', {bubbles: true}));", text_input, input)
    
    # step 2: click the generate button
    generate_button_xpath = "//button[contains(@class, 'text-primary-foreground')]//*[contains(., 'Generate')]/.."
    
    tsprint("Inputting text...")
    safe_click(driver, generate_button_xpath)

    # step 3: wait for download button availability + step 4: download
    download_button_xpath = "//button[contains(@class, 'bg-secondary') and contains(@class, 'text-secondary-foreground')]//*[contains(., 'Download')]/.."

    tsprint("Awaiting download button availability...")
    safe_click(driver, download_button_xpath)

    tsprint("Downloading TTS file...")
    download_wait(DOWNLOADS_DIR, 10, 1)

    tsprint("Downloaded. Returning...")

if __name__ == "__main__":
    driver = open_driver()

    open_tts_vibes(driver)
    try:
        get_marcus_tts(driver, "I love Neovim")
    except (CharLimitError, CharRepeatError) as e:
        print(e)

    driver.quit()