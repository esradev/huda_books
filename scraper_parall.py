import requests
from bs4 import BeautifulSoup
import os
import json
import time
from concurrent.futures import ThreadPoolExecutor

# ---------------------------
# CONFIG
# ---------------------------

BASE_URL = "https://lib.eshia.ir"
BOOK_ID = "10028"
OUTPUT_DIR = f"books/{BOOK_ID}"
DELAY = 0.5  # seconds between requests
MAX_PAGES_SAFETY = 1000
MAX_THREADS = 5  # parallel volumes

# ---------------------------
# HELPER FUNCTIONS
# ---------------------------

def fetch_page(volume, page_number):
    url = f"{BASE_URL}/{BOOK_ID}/{volume}/{page_number}"
    try:
        resp = requests.get(url, timeout=20)
        resp.encoding = "utf-8"
    except Exception as e:
        print(f"[Vol {volume}] Request error:", e)
        return None, None

    if resp.status_code != 200:
        return None, None

    soup = BeautifulSoup(resp.text, "html.parser")
    content_td = soup.select_one("td.book-page-show")
    if not content_td:
        return None, resp.url

    sticky = content_td.select_one(".sticky-menue")
    if sticky:
        sticky.decompose()

    html_content = content_td.decode_contents()
    return html_content, resp.url

def save_page(volume_dir, page_number, data):
    os.makedirs(volume_dir, exist_ok=True)
    filename = os.path.join(volume_dir, f"page_{page_number}.json")
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def combine_volume_pages(volume_dir, volume_number):
    pages = []
    for file_name in sorted(os.listdir(volume_dir)):
        if file_name.startswith("page_") and file_name.endswith(".json"):
            with open(os.path.join(volume_dir, file_name), "r", encoding="utf-8") as f:
                pages.append(json.load(f))
    combined_file = os.path.join(volume_dir, f"volume_{volume_number}_combined.json")
    with open(combined_file, "w", encoding="utf-8") as f:
        json.dump({
            "bookId": BOOK_ID,
            "volumeNumber": volume_number,
            "pages": pages
        }, f, ensure_ascii=False, indent=2)
    print(f"[Vol {volume_number}] Combined volume saved as {combined_file}")

# ---------------------------
# SCRAPE ONE VOLUME
# ---------------------------

def scrape_volume(volume):
    print(f"[Vol {volume}] Starting...")
    volume_dir = os.path.join(OUTPUT_DIR, f"vol_{volume}")
    os.makedirs(volume_dir, exist_ok=True)

    page = 1
    last_url = None

    while True:
        if page > MAX_PAGES_SAFETY:
            print(f"[Vol {volume}] Safety stop triggered.")
            break

        # Skip already downloaded pages (resume)
        page_file = os.path.join(volume_dir, f"page_{page}.json")
        if os.path.exists(page_file):
            page += 1
            continue

        html, final_url = fetch_page(volume, page)
        if html is None:
            print(f"[Vol {volume}] No content found. Stop.")
            break

        if final_url == last_url:
            print(f"[Vol {volume}] Reached last page.")
            break

        last_url = final_url

        page_data = {
            "version": "1.0",
            "bookId": BOOK_ID,
            "volumeNumber": int(volume),
            "pageNumber": page,
            "encoding": "utf-8",
            "source": "lib.eshia.ir",
            "html": html
        }
        save_page(volume_dir, page, page_data)
        print(f"[Vol {volume}] Saved page {page}")

        page += 1
        time.sleep(DELAY)

    # Combine all pages after scraping this volume
    combine_volume_pages(volume_dir, volume)
    print(f"[Vol {volume}] Done scraping volume.")

# ---------------------------
# DETECT AVAILABLE VOLUMES
# ---------------------------

def detect_volumes():
    volumes = []
    volume = 1
    while True:
        test_url = f"{BASE_URL}/{BOOK_ID}/{volume}/1"
        try:
            resp = requests.get(test_url, timeout=10, allow_redirects=True)
            final_url = resp.url
        except:
            break

        if final_url.endswith("/1") and volume != 1:
            break

        volumes.append(volume)
        volume += 1
        time.sleep(0.2)
    return volumes

# ---------------------------
# MAIN SCRAPER
# ---------------------------

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    volumes = detect_volumes()
    print("Detected volumes:", volumes)

    # Parallel scrape volumes
    from functools import partial
    with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
        executor.map(scrape_volume, volumes)

    print("All volumes done!")

if __name__ == "__main__":
    main()
