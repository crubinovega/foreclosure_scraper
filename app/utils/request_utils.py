import requests
import time

def safe_get(url, retries=3, delay=2):
    for i in range(retries):
        try:
            return requests.get(url, timeout=10)
        except:
            time.sleep(delay)
    return None
