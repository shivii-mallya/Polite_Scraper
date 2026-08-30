import json
import os
import re
import time
from datetime import datetime, timezone
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
from pydantic import BaseModel, HttpUrl, Field

HEADERS = {
    "User-Agent": "FlyRankInternship-A9/1.0 (+https://github.com/shivii-mallya/Polite_Scraper)"
}
CACHE_DIR = "cache"
OUTPUT_DIR = "output"

# Mapping star rating words to integers
RATING_MAP = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5
}

# Pydantic Schema for Standardized Book Record
class BookModel(BaseModel):
    title: str
    product_url: HttpUrl
    price_gbp: float = Field(..., ge=0.0)
    in_stock: bool
    stock_count: int = Field(..., ge=0)
    rating: int = Field(..., ge=1, le=5)
    description: str | None = None
    source_page: HttpUrl
    fetched_at: str

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
    """Extract raw fields from book detail HTML page."""
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

def clean_and_validate_record(raw_record: dict) -> BookModel:
    """Transform raw extracted text into clean, typed Pydantic models."""
    # 1. Clean Price
    price_match = re.search(r"[\d.]+", raw_record["price_text"])
    price_gbp = float(price_match.group(0)) if price_match else 0.0

    # 2. Clean Availability & Stock Count
    avail_text = raw_record["availability_text"]
    in_stock = "In stock" in avail_text
    stock_match = re.search(r"\d+", avail_text)
    stock_count = int(stock_match.group(0)) if stock_match else 0

    # 3. Clean Rating
    rating_word = (raw_record.get("rating_text") or "").lower()
    rating = RATING_MAP.get(rating_word, 1)

    # 4. Instantiate and validate with Pydantic
    return BookModel(
        title=raw_record["title"],
        product_url=raw_record["product_url"],
        price_gbp=price_gbp,
        in_stock=in_stock,
        stock_count=stock_count,
        rating=rating,
        description=raw_record["description"],
        source_page=raw_record["source_page"],
        fetched_at=raw_record["fetched_at"]
    )

def run_pipeline() -> list[BookModel]:
    """Execute stages 1-4: crawl catalogue, fetch details, clean & export JSON."""
    _, book_urls = discover_catalogue_books(max_pages=3)
    validated_books = []

    for index, url in enumerate(book_urls, start=1):
        slug = url.split("/")[-2]
        cache_filename = f"detail-{slug}.html"

        cat_page_num = ((index - 1) // 20) + 1
        source_page = f"https://books.toscrape.com/catalogue/page-{cat_page_num}.html"

        html = fetch_page(url, cache_filename)
        raw_record = parse_book_detail(html, url, source_page)
        clean_record = clean_and_validate_record(raw_record)
        validated_books.append(clean_record)

    # Save to output/books.json
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_path = os.path.join(OUTPUT_DIR, "books.json")
    
    # Dump Pydantic models as JSON
    json_data = [book.model_dump(mode="json") for book in validated_books]
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(json_data, f, indent=2)

    return validated_books

if __name__ == "__main__":
    books = run_pipeline()
    print(f"validated_records={len(books)}")
    print(f"saved_to=output/books.json\n")
    print("First Validated Record:")
    print(books[0].model_dump_json(indent=2))
    