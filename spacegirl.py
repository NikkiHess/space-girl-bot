from bs4 import BeautifulSoup
import requests

url = "https://ttsvibes.com/storyteller"
response = requests.get(url)
soup = BeautifulSoup(response.text, "html.parser")

# step 1, type into text input
text_input = soup.find("input", {"name": "text"})
text_input.text

# step 2, press generate
generate_button = soup.find("Generate").parent

# step 3, press download
download_button = soup.find("Download").parent