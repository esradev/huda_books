import requests
from bs4 import BeautifulSoup
import time
import json
import os

# ---------------------------
# CONFIG
# ---------------------------

BASE_URL = "https://lib.eshia.ir"
BOOK_ID = "12016"
VOLUME = "1"

OUTPUT_FILE = f"book_{BOOK_ID}_vol_{VOLUME}.json"

DELAY = 1   # seconds between requests
MAX_PAGES_SAFETY = 1000  # safety stop


# ---------------------------
# FETCH ONE PAGE
# ---------------------------

def fetch_page(page_number):
    url = f"{BASE_URL}/{BOOK_ID}/{VOLUME}/{page_number}"

    try:
        resp = requests.get(url, timeout=20)
    except Exception as e:
        print("Request error:", e)
        return None, None

    resp.encoding = "utf-8"

    if resp.status_code != 200:
        return None, None

    soup = BeautifulSoup(resp.text, "html.parser")

    content_td = soup.select_one("td.book-page-show")

    if not content_td:
        return None, resp.url

    # Remove sticky menu
    sticky = content_td.select_one(".sticky-menue")
    if sticky:
        sticky.decompose()

    # Keep HTML structure
    html_content = content_td.decode_contents()

    return html_content, resp.url


# ---------------------------
# MAIN SCRAPER LOOP
# ---------------------------

def scrape_book():

    book_json = {
        "version": "1.0",
        "bookId": BOOK_ID,
        "volumeNumber": int(VOLUME),
        "encoding": "utf-8",
        "source": "lib.eshia.ir",
        "pages": []
    }

    page = 1
    last_url = None

    while True:

        if page > MAX_PAGES_SAFETY:
            print("Safety stop triggered.")
            break

        print(f"Scraping page {page}")

        html, final_url = fetch_page(page)

        if html is None:
            print("No content found. Stop.")
            break

        # Detect last page via redirect loop
        if final_url == last_url:
            print("Reached last page.")
            break

        last_url = final_url

        book_json["pages"].append({
            "number": page,
            "html": html
        })

        page += 1
        time.sleep(DELAY)

    return book_json


# ---------------------------
# SAVE JSON
# ---------------------------

def save_json(data):
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ---------------------------
# RUN
# ---------------------------

if __name__ == "__main__":

    result = scrape_book()
    save_json(result)

    print("Done.")
    print("Saved to:", OUTPUT_FILE)
