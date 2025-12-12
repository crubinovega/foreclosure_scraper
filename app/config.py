import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("API_KEY", "changeme")
BASE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (ForeclosureScraperBot)"
}
