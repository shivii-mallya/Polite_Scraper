import os
import time
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "FlyRankInternship-A9/1.0 (+https://github.com/shivii-mallya/Polite_Scraper.git)"
}
CACHE_DIR = "cache"

def fetch_page(url: str, cache_filename: str) -> str:
    """Fetch HTML from cache if available; otherwise fetch live and save to cache."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    cache_path = os.path.join(CACHE_DIR, cache_filename)

    if os.path.exists(cache_path):
        with open(cache_path, "r", encoding="utf-8") as f:
            content = f.read()
        print(f"CACHE HIT | {cache_filename} | Size: {len(content)} bytes")
        return content

    # Polite delay before network request
    time.sleep(0.5)
    response = requests.get(url, headers=HEADERS, timeout=5)
    
    if response.status_code != 200:
        raise RuntimeError(f"Fetch failed with status code: {response.status_code}")

    content = response.text
    with open(cache_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"FETCH | {cache_filename} | Status: {response.status_code} | Size: {len(content)} bytes")
    return content

def extract_book_urls(html: str, current_page_url: str) -> list[str]:
    """Extract all book links from a single catalogue page and convert to absolute URLs."""
    soup = BeautifulSoup(html, "html.parser")
    book_urls = []
    
    # Target book links inside <h3> elements
    for h3 in soup.find_all("h3"):
        a_tag = h3.find("a")
        if a_tag and "href" in a_tag.attrs:
            relative_url = a_tag["href"]
            # Convert relative URL to absolute URL
            absolute_url = urljoin(current_page_url, relative_url)
            book_urls.append(absolute_url)
            
    return book_urls

def get_next_page_url(html: str, current_page_url: str) -> str | None:
    """Find the 'next' catalogue page link if it exists."""
    soup = BeautifulSoup(html, "html.parser")
    next_li = soup.find("li", class_="next")
    if next_li:
        a_tag = next_li.find("a")
        if a_tag and "href" in a_tag.attrs:
            return urljoin(current_page_url, a_tag["href"])
    return None

def discover_catalogue_books(max_pages: int = 3) -> tuple[int, list[str]]:
    """Crawl up to max_pages catalogue pages and gather unique book URLs."""
    current_url = "https://books.toscrape.com/catalogue/page-1.html"
    discovered_urls = []
    pages_visited = 0

    while current_url and pages_visited < max_pages:
        pages_visited += 1
        cache_filename = f"catalogue-page-{pages_visited}.html"
        
        # Fetch or load from cache
        html = fetch_page(current_url, cache_filename)
        
        # Extract book links from current page[cite: 1]
        page_book_urls = extract_book_urls(html, current_url)
        discovered_urls.extend(page_book_urls)
        
        # Find next page link[cite: 1]
        current_url = get_next_page_url(html, current_url)

    # Remove duplicates while preserving order[cite: 1]
    unique_urls = list(dict.fromkeys(discovered_urls))
    
    return pages_visited, unique_urls

if __name__ == "__main__":
    pages_count, book_urls = discover_catalogue_books(max_pages=3)
    print(f"\ncatalogue_pages={pages_count}, discovered={len(book_urls)}, unique_urls={len(book_urls)}")