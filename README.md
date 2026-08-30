# Production-Grade Books Scraper (`Polite_Scraper`)

An automated, resilient ETL scraping pipeline built with Python, `BeautifulSoup4`, `requests`, and `Pydantic`.

---

## Target Classification & Architecture

* **Stage 0 Target Classification**: Static / Server-Side Rendered HTML (`books.toscrape.com`).
* **Robots.txt Result**: Requesting `https://books.toscrape.com/robots.txt` returned a 404 (no robots file found). Permission is explicitly granted on the homepage sandbox note. *"I will not reuse this code on another site without checking its rules and terms first."*
* **Why No Browser Was Needed**: All book data and pagination links are embedded directly in the static HTML returned by the server upon GET request. Using a headless browser (e.g., Selenium/Playwright) would add unnecessary memory overhead, execution cost, and complexity without providing any functional benefit.

---

## Lane & Installation

* **Lane**: Python ETL (Static HTML Scraping & Pydantic Validation)

### Installation
Clone the repository and install requirements:

```bash
git clone [https://github.com/shivii-mallya/Polite_Scraper.git](https://github.com/shivii-mallya/Polite_Scraper.git)
cd Polite_Scraper
python -m pip install -r requirements.txt