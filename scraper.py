import requests
from bs4 import BeautifulSoup
import time
import json
import os

# ---------------------------
# CONFIG
# ---------------------------

BASE_URL = "https://lib.eshia.ir"
BOOK_ID = "27897"

OUTPUT_ROOT = "books"

DELAY = 0.6
MAX_PAGES_SAFETY = 2000
REQUEST_RETRIES = 3


# ---------------------------
# CREATE BOOK FOLDER
# ---------------------------

BOOK_FOLDER = os.path.join(OUTPUT_ROOT, BOOK_ID)
os.makedirs(BOOK_FOLDER, exist_ok=True)


# ---------------------------
# SAFE REQUEST
# ---------------------------

def safe_get(url):
    for i in range(REQUEST_RETRIES):
        try:
            r = requests.get(url, timeout=20)
            r.encoding = "utf-8"
            return r
        except Exception:
            print("Retry request:", url)
            time.sleep(2)
    return None


# ---------------------------
# DETECT LAST VOLUME
# ---------------------------

def volume_exists(volume):

    url = f"{BASE_URL}/{BOOK_ID}/{volume}/0"

    resp = safe_get(url)
    if not resp:
        return False

    # if redirected to another volume → doesn't exist
    final_url = resp.url

    expected = f"/{BOOK_ID}/{volume}/"

    if expected not in final_url:
        return False

    return True


# ---------------------------
# FETCH PAGE CONTENT
# ---------------------------

def fetch_page(volume, page_number):

    url = f"{BASE_URL}/{BOOK_ID}/{volume}/{page_number}"

    resp = safe_get(url)
    if not resp or resp.status_code != 200:
        return None, None

    soup = BeautifulSoup(resp.text, "html.parser")

    content_td = soup.select_one("td.book-page-show")

    if not content_td:
        return None, resp.url

    # Remove sticky menu
    sticky = content_td.select_one(".sticky-menue")
    if sticky:
        sticky.decompose()

    html_content = content_td.decode_contents()

    return html_content, resp.url


# ---------------------------
# SCRAPE ONE VOLUME
# ---------------------------

def scrape_volume(volume):

    output_file = os.path.join(BOOK_FOLDER, f"vol_{volume}.json")

    if os.path.exists(output_file):
        print("Volume exists, skipping:", volume)
        return

    print("\n====================")
    print("Scraping volume:", volume)
    print("====================")

    data = {
        "version": "1.0",
        "bookId": BOOK_ID,
        "volumeNumber": int(volume),
        "encoding": "utf-8",
        "source": "lib.eshia.ir",
        "pages": []
    }

    page = 1
    last_url = None

    while True:

        if page > MAX_PAGES_SAFETY:
            print("Safety stop pages.")
            break

        print(f"Page {page}")

        html, final_url = fetch_page(volume, page)

        if html is None:
            print("No content -> stop pages")
            break

        if final_url == last_url:
            print("Last page reached")
            break

        last_url = final_url

        data["pages"].append({
            "number": page,
            "html": html
        })

        page += 1
        time.sleep(DELAY)

    # Save volume
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)

    print("Saved:", output_file)


# ---------------------------
# MAIN LOOP ALL VOLUMES
# ---------------------------

def scrape_all_volumes():

    volume = 1

    while True:

        print("\nChecking volume:", volume)

        if not volume_exists(volume):
            print("No more volumes.")
            break

        scrape_volume(volume)

        volume += 1


# ---------------------------
# RUN
# ---------------------------

if __name__ == "__main__":

    scrape_all_volumes()

    print("\nDone.")
