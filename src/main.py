import os
import requests

# 1. Setup paths and polite headers
BASE_URL = "https://books.toscrape.com/catalogue/page-1.html"
# Replace 'your-username' and 'your-repo' with your actual GitHub info
HEADERS = {
    "User-Agent": "FlyRankInternship-A9/1.0 (+https://github.com/shivii-mallya/Polite_Scraper.git)"
}
CACHE_DIR = "cache"

def fetch_page(url: str, cache_filename: str) -> str:
    """Fetch HTML from cache if it exists; otherwise fetch from network and cache it."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    cache_path = os.path.join(CACHE_DIR, cache_filename)

    # Check cache first
    if os.path.exists(cache_path):
        with open(cache_path, "r", encoding="utf-8") as f:
            content = f.read()
        print(f"CACHE HIT | Size: {len(content)} bytes")
        return content

    # If not cached, make network request
    response = requests.get(url, headers=HEADERS, timeout=5)
    
    # Check status code
    if response.status_code != 200:
        raise RuntimeError(f"Fetch failed with status code: {response.status_code}")

    content = response.text
    
    # Save to cache
    with open(cache_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"FETCH | Status: {response.status_code} | Size: {len(content)} bytes")
    return content

if __name__ == "__main__":
    fetch_page(BASE_URL, "catalogue-page-1.html")