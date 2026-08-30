# Production-Grade Books Scraper (`Polite_Scraper`)

An automated, resilient web scraper built with Python, `BeautifulSoup`, `requests`, and `Pydantic`. The pipeline crawls catalogue pages from [Books to Scrape](https://books.toscrape.com), extracts product details, enforces data quality via strict schema validation, and exports clean JSON outputs alongside dataset summary metrics.

---

## Key Features & Architecture

1. **HTTP Politeness**:
   * Custom `User-Agent` string (`FlyRankInternship-A9/1.0 (+https://github.com/shivii-mallya/Polite_Scraper)`).
   * Built-in 0.5-second rate limiting between live network requests to prevent server throttling.
2. **Local File Caching**:
   * HTML pages are saved locally in the `cache/` directory on initial fetch.
   * Subsequent runs execute instantly offline without making redundant HTTP calls.
3. **Pagination & Link Discovery**:
   * Dynamically tracks "Next" pagination buttons across catalogue pages instead of hardcoding target URLs.
4. **Data Normalization & Validation**:
   * Converts raw HTML strings into clean numeric types using Regular Expressions.
   * Validates data structure using Pydantic v2 schemas (`BookModel`).
5. **Data Provenance**:
   * Tracks origin URLs (`source_page`), canonical URLs (`product_url`), and precise UTC timestamp execution metadata (`fetched_at`).

---

## Data Schema (`BookModel`)

| Field Name | Type | Description |
| :--- | :--- | :--- |
| `title` | `str` | Book title string |
| `product_url` | `HttpUrl` | Canonical URL to the detail page |
| `price_gbp` | `float` | Price in GBP (`>= 0.0`) |
| `in_stock` | `bool` | Stock availability flag |
| `stock_count` | `int` | Quantity of stock remaining (`>= 0`) |
| `rating` | `int` | Star rating integer (`1` to `5`) |
| `description` | `str \| None` | Text description or `None` |
| `source_page` | `HttpUrl` | Catalogue page where link was discovered |
| `fetched_at` | `str` | ISO 8601 UTC timestamp of fetch execution |

---

## Repository Structure

---

## Setup & Running the Pipeline

### 1. Prerequisites
* Python 3.10+
* Virtual environment (recommended)

### 2. Installation
Clone the repository and install required packages:

```bash
git clone [https://github.com/shivii-mallya/Polite_Scraper.git](https://github.com/shivii-mallya/Polite_Scraper.git)
cd Polite_Scraper
python -m pip install beautifulsoup4 requests pydantic

---
