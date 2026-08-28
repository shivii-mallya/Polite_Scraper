import json
import os
import time
from datetime import datetime, timezone
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "FlyRankInternship-A9/1.0 (+https://github.com/shivii-mallya/Polite_Scraper)"
}
CACHE_DIR = "cache"

def fetch_page(url: str, cache_filename: str) -> str:
    """Fetch HTML from cache if available; otherwise fetch live and save to cache."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    cache_path = os.path.join(CACHE_DIR, cache_filename)

    if os.path.exists(cache_path):
        with open(cache_path, "r", encoding="utf-8") as f:
            return f.read()

    time.sleep(0.5)
    response = requests.get(url, headers=HEADERS, timeout=5)
    
    if response.status_code != 200:
        raise RuntimeError(f"Fetch failed with status code: {response.status_code}")

    content = response.text
    with open(cache_path, "w", encoding="utf-8") as f:
        f.write(content)

    return content

def extract_book_urls(html: str, current_page_url: str) -> list[str]:
    """Extract all book links from a single catalogue page."""
    soup = BeautifulSoup(html, "html.parser")
    book_urls = []
    
    for h3 in soup.find_all("h3"):
        a_tag = h3.find("a")
        if a_tag and "href" in a_tag.attrs:
            absolute_url = urljoin(current_page_url, a_tag["href"])
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
        html = fetch_page(current_url, cache_filename)
        page_book_urls = extract_book_urls(html, current_url)
        discovered_urls.extend(page_book_urls)
        current_url = get_next_page_url(html, current_url)

    unique_urls = list(dict.fromkeys(discovered_urls))
    return pages_visited, unique_urls

def parse_book_detail(html: str, product_url: str, source_page: str) -> dict:
    """Extract all 8 required raw fields from a book detail HTML page."""
    soup = BeautifulSoup(html, "html.parser")
    product_main = soup.find("div", class_="product_main")

    title = product_main.find("h1").text.strip()
    price_text = product_main.find("p", class_="price_color").text.strip()
    availability_text = product_main.find("p", class_="instock availability").text.strip()

    rating_tag = product_main.find("p", class_="star-rating")
    rating_text = rating_tag["class"][1] if rating_tag and len(rating_tag["class"]) > 1 else None

    desc_tag = soup.find("div", id="product_description")
    description = desc_tag.find_next_sibling("p").text.strip() if desc_tag else None

    return {
        "title": title,
        "product_url": product_url,
        "price_text": price_text,
        "availability_text": availability_text,
        "rating_text": rating_text,
        "description": description,
        "source_page": source_page,
        "fetched_at": datetime.now(timezone.utc).isoformat()
    }

def extract_all_raw_records() -> list[dict]:
    """Iterate across all 60 book URLs, fetch and parse detail records."""
    pages_count, book_urls = discover_catalogue_books(max_pages=3)
    raw_records = []

    for index, url in enumerate(book_urls, start=1):
        slug = url.split("/")[-2]
        cache_filename = f"detail-{slug}.html"

        cat_page_num = ((index - 1) // 20) + 1
        source_page = f"https://books.toscrape.com/catalogue/page-{cat_page_num}.html"

        html = fetch_page(url, cache_filename)
        record = parse_book_detail(html, url, source_page)
        raw_records.append(record)

    return raw_records

if __name__ == "__main__":
    records = extract_all_raw_records()
    print(f"detail_pages={len(records)}\n")
    print("Sample Raw Record:")
    print(json.dumps(records[0], indent=2))