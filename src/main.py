import json
import os
import re
import time
from collections import Counter
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

RATING_MAP = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5}

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

def fetch_page(url: str, cache_filename: str) -> str | None:
    """Fetch HTML with caching, user-agent, timeout, and polite single-retry on 5xx."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    cache_path = os.path.join(CACHE_DIR, cache_filename)

    if os.path.exists(cache_path):
        with open(cache_path, "r", encoding="utf-8") as f:
            return f.read()

    time.sleep(0.5)
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=5)
        
        # Polite retry once on 5xx server errors
        if response.status_code >= 500:
            time.sleep(1.0)
            response = requests.get(url, headers=HEADERS, timeout=5)

        if response.status_code != 200:
            return None

        content = response.text
        with open(cache_path, "w", encoding="utf-8") as f:
            f.write(content)
        return content

    except requests.RequestException:
        return None

def extract_book_urls(html: str, current_page_url: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    book_urls = []
    for h3 in soup.find_all("h3"):
        a_tag = h3.find("a")
        if a_tag and "href" in a_tag.attrs:
            book_urls.append(urljoin(current_page_url, a_tag["href"]))
    return book_urls

def get_next_page_url(html: str, current_page_url: str) -> str | None:
    soup = BeautifulSoup(html, "html.parser")
    next_li = soup.find("li", class_="next")
    if next_li and next_li.find("a"):
        return urljoin(current_page_url, next_li.find("a")["href"])
    return None

def discover_catalogue_books(max_pages: int = 3) -> tuple[int, list[str]]:
    current_url = "https://books.toscrape.com/catalogue/page-1.html"
    discovered_urls = []
    pages_visited = 0

    while current_url and pages_visited < max_pages:
        pages_visited += 1
        cache_filename = f"catalogue-page-{pages_visited}.html"
        html = fetch_page(current_url, cache_filename)
        if html:
            discovered_urls.extend(extract_book_urls(html, current_url))
            current_url = get_next_page_url(html, current_url)
        else:
            break

    return pages_visited, list(dict.fromkeys(discovered_urls))

def parse_book_detail(html: str, product_url: str, source_page: str) -> dict:
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
    price_match = re.search(r"[\d.]+", raw_record["price_text"])
    price_gbp = float(price_match.group(0)) if price_match else 0.0

    avail_text = raw_record["availability_text"]
    in_stock = "In stock" in avail_text
    stock_match = re.search(r"\d+", avail_text)
    stock_count = int(stock_match.group(0)) if stock_match else 0

    rating_word = (raw_record.get("rating_text") or "").lower()
    rating = RATING_MAP.get(rating_word, 1)

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

def run_pipeline() -> tuple[list[BookModel], list[dict], dict]:
    start_time = time.time()
    pages_count, book_urls = discover_catalogue_books(max_pages=3)
    validated_books = []
    errors = []

    for index, url in enumerate(book_urls, start=1):
        slug = url.split("/")[-2]
        cache_filename = f"detail-{slug}.html"
        cat_page_num = ((index - 1) // 20) + 1
        source_page = f"https://books.toscrape.com/catalogue/page-{cat_page_num}.html"

        html = fetch_page(url, cache_filename)
        if not html:
            errors.append({"url": url, "reason": "Failed to fetch page or non-200 HTTP response"})
            continue

        try:
            raw_record = parse_book_detail(html, url, source_page)
            validated_record = clean_and_validate_record(raw_record)
            validated_books.append(validated_record)
        except Exception as e:
            errors.append({"url": url, "reason": f"Validation/Parsing error: {str(e)}"})

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Save output/books.json
    books_path = os.path.join(OUTPUT_DIR, "books.json")
    json_data = [book.model_dump(mode="json") for book in validated_books]
    with open(books_path, "w", encoding="utf-8") as f:
        json.dump(json_data, f, indent=2)

    # Save output/errors.json
    errors_path = os.path.join(OUTPUT_DIR, "errors.json")
    with open(errors_path, "w", encoding="utf-8") as f:
        json.dump(errors, f, indent=2)

    # Compute & Save output/run-report.json
    duration = round(time.time() - start_time, 2)
    avg_price = round(sum(b.price_gbp for b in validated_books) / len(validated_books), 2) if validated_books else 0.0
    in_stock_ratio = round((sum(1 for b in validated_books if b.in_stock) / len(validated_books)) * 100, 2) if validated_books else 0.0
    rating_dist = dict(Counter(b.rating for b in validated_books))

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "execution_time_seconds": duration,
        "catalogue_pages_visited": pages_count,
        "total_records_extracted": len(validated_books),
        "failed_records_count": len(errors),
        "metrics": {
            "avg_price_gbp": avg_price,
            "in_stock_ratio_pct": in_stock_ratio,
            "rating_distribution": rating_dist
        }
    }
    
    report_path = os.path.join(OUTPUT_DIR, "run-report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    return validated_books, errors, report

if __name__ == "__main__":
    books, errors, report = run_pipeline()
    print("Pipeline executed successfully!")
    print(json.dumps(report, indent=2))