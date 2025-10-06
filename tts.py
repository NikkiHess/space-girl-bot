from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import os
import time

TTS_VIBES_URL = "https://ttsvibes.com/storyteller"

CUSTOM_CHROME = os.path.join(os.getcwd(), "selenium", "chrome", "chrome.exe")
CHROMEDRIVER_PATH = os.path.join(os.path.dirname(__file__), "selenium", "chromedriver.exe")

DOWNLOADS_DIR = os.path.join(os.getcwd(), "downloads")
os.makedirs(DOWNLOADS_DIR, exist_ok=True)

def open_driver():
    """
    Opens a headless Chrome instance with which to do TTS

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

    # step 1: await text input readiness, then input the text
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "text"))
    )

    text_input = driver.find_element(by=By.ID, value="text")

    driver.execute_script("arguments[0].value = arguments[1]; arguments[0].dispatchEvent(new Event('input', {bubbles: true}));", text_input, input)
    
    # step 2: click the generate button
    generate_button = driver.find_element(
        by=By.XPATH, 
        value="//button[contains(@class, 'text-primary-foreground')]//*[contains(., 'Generate')]/.."
    )
    generate_button.click()

    # step 3: wait for download + step 4: download
    download_button = WebDriverWait(driver, 5).until(
        EC.element_to_be_clickable(
            (By.XPATH, "//button[contains(@class, 'bg-secondary') and contains(@class, 'text-secondary-foreground')]//*[contains(., 'Download')]/..")
        )
    )
    download_button.click()

    download_wait(DOWNLOADS_DIR, 10, 1)
    
    # TODO: generate, download, and return

if __name__ == "__main__":
    driver = open_driver()

    open_tts_vibes(driver)
    get_tts_vibes_tts(driver, "testing")

    driver.quit()