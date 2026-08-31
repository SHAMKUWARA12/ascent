"""
ASCENT — CCMT Cutoff Score Scraper
Scrapes Opening/Closing GATE scores for all target NITs
across 2021-2025 from ccmt.admissions.nic.in (OR-CR page).

Output: One JSON file per year in data/raw/parsed/
        ccmt_2021_final.json ... ccmt_2025_final.json
"""

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time
import os
import json


# ── Configuration ──────────────────────────────────────────

RESULTS_DIR = "../data/raw/parsed"

TARGET_NITS = [
    "Agartala", "Andhra Pradesh", "Arunachal Pradesh", "Calicut",
    "Delhi", "Durgapur", "Goa", "Hamirpur", "Jalandhar", "Jamshedpur",
    "Jaipur", "Karnataka, Surathkal", "Kurukshetra", "Manipur",
    "Meghalaya", "Mizoram", "Nagaland", "Nagpur", "Patna", "Puducherry",
    "Raipur", "Rourkela", "Silchar", "Sikkim", "Srinagar", "Surat",
    "Tiruchirappalli", "Uttarakhand", "Warangal", "Allahabad", "Bhopal"
]

YEAR_URLS = {
    2021: "https://admissions.nic.in/admiss/admissions/orcrjacd/105012121",
    2022: "https://admissions.nic.in/admiss/admissions/orcrjacd/105012221",
    2023: "https://admissions.nic.in/admiss/admissions/orcrjacd/105012321",
    2024: "https://admissions.nic.in/admiss/admissions/orcrjacd/105012421",
    2025: "https://admissions.nic.in/admiss/admissions/orcrjacd/105012521",
}


# ── Driver setup ────────────────────────────────────────────

def get_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    )
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)


def load_url_with_retry(driver, url, max_retries=5, wait_after_load=15):
    """Navigate to a URL with retries on transient network failures."""
    for attempt in range(1, max_retries + 1):
        try:
            print(f"  Loading (attempt {attempt}/{max_retries}): {url}")
            driver.get(url)
            time.sleep(wait_after_load)
            return True
        except Exception as e:
            wait = attempt * 8
            print(f"  Load failed: {str(e)[:100]}")
            print(f"  Retrying in {wait}s...")
            time.sleep(wait)
    print(f"  ❌ Failed to load after {max_retries} attempts")
    return False


# ── Filtering ───────────────────────────────────────────────

def is_target_nit(institute_name: str) -> bool:
    name_lower = institute_name.lower()
    return any(nit.lower() in name_lower for nit in TARGET_NITS)


# ── Table scraping ──────────────────────────────────────────

def scrape_current_table(driver) -> list:
    """Extract all data rows from the currently visible table."""
    soup = BeautifulSoup(driver.page_source, "html.parser")
    tables = soup.find_all("table")
    if not tables:
        return []

    main_table = max(tables, key=lambda t: len(t.find_all("tr")))
    rows = main_table.find_all("tr")
    if len(rows) < 2:
        return []

    header_cells = [
        c.get_text(strip=True).lower()
        for c in rows[0].find_all(["td", "th"])
    ]

    records = []
    for row in rows[1:]:
        cells = row.find_all(["td", "th"])
        values = [c.get_text(strip=True) for c in cells]
        if len(values) != len(header_cells):
            continue
        records.append(dict(zip(header_cells, values)))

    return records


def click_next_page(driver) -> bool:
    """Click 'Next' pagination link. Returns False if disabled/absent."""
    try:
        next_links = driver.find_elements(By.LINK_TEXT, "Next")
        if not next_links:
            next_links = driver.find_elements(
                By.XPATH, "//*[contains(text(), 'Next')]"
            )

        for link in next_links:
            if not link.is_displayed():
                continue
            classes = (link.get_attribute("class") or "").lower()
            try:
                parent = link.find_element(By.XPATH, "..")
                parent_classes = (parent.get_attribute("class") or "").lower()
            except Exception:
                parent_classes = ""

            if "disabled" in classes or "disabled" in parent_classes:
                return False

            link.click()
            return True

        return False
    except Exception as e:
        print(f"    Pagination error: {e}")
        return False


# ── Persistence ─────────────────────────────────────────────

def save_records(records: list, filename: str):
    os.makedirs(RESULTS_DIR, exist_ok=True)
    filepath = os.path.join(RESULTS_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)
    print(f"  Saved {len(records)} records to {filepath}")


# ── Per-year scrape ─────────────────────────────────────────

def scrape_year(url: str, year: int, max_pages: int = 600,
                 wait_between_pages: float = 2.0) -> list:
    driver = get_driver()
    all_records = []

    try:
        print(f"\n{'='*60}")
        print(f"YEAR {year}")
        print(f"{'='*60}")

        loaded = load_url_with_retry(driver, url, max_retries=5, wait_after_load=15)
        if not loaded:
            return []

        page_num = 1
        empty_first_page_retries = 0

        while page_num <= max_pages:
            records = scrape_current_table(driver)

            # Retry with longer wait if page 1 loads empty
            if page_num == 1 and len(records) == 0 and empty_first_page_retries < 3:
                empty_first_page_retries += 1
                print(f"  ⚠️ Page 1 empty, waiting longer "
                      f"({empty_first_page_retries}/3)...")
                time.sleep(15)
                continue

            kept = [r for r in records if is_target_nit(r.get("institute", ""))]
            for r in kept:
                r["year"] = year
            all_records.extend(kept)

            if page_num % 20 == 0 or page_num == 1:
                print(f"  [{year}] Page {page_num}: {len(records)} scanned, "
                      f"{len(all_records)} total matched so far")

            if page_num % 50 == 0:
                save_records(all_records, f"ccmt_{year}_partial.json")

            has_next = click_next_page(driver)
            if not has_next:
                print(f"  [{year}] Reached last page at {page_num}")
                break

            time.sleep(wait_between_pages)
            page_num += 1

        print(f"✅ {year} complete. Total matched records: {len(all_records)}")
        return all_records

    except Exception as e:
        print(f"❌ Error scraping {year}: {str(e)[:200]}")
        return all_records

    finally:
        driver.quit()


# ── Full pipeline ───────────────────────────────────────────

def scrape_all_years():
    """
    Scrape all 5 years fresh. Skips a year only if its final
    file already exists AND has records (resume-safe on reruns).
    """
    for year, url in YEAR_URLS.items():
        final_filename = f"ccmt_{year}_final.json"
        final_path = os.path.join(RESULTS_DIR, final_filename)

        if os.path.exists(final_path):
            with open(final_path, "r", encoding="utf-8") as f:
                existing = json.load(f)
            if len(existing) > 0:
                print(f"\n⏭️  Skipping {year} — already completed "
                      f"({len(existing)} records)")
                continue

        records = scrape_year(url, year)
        save_records(records, final_filename)

        # Clean up partial file once final is saved
        partial_path = os.path.join(RESULTS_DIR, f"ccmt_{year}_partial.json")
        if os.path.exists(partial_path):
            os.remove(partial_path)

        print("  Pausing 10s before next year...")
        time.sleep(10)

    print("\n" + "=" * 60)
    print("ALL YEARS COMPLETE")
    print("=" * 60)

    total = 0
    for year in YEAR_URLS:
        path = os.path.join(RESULTS_DIR, f"ccmt_{year}_final.json")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                print(f"  {year}: {len(data)} records")
                total += len(data)
    print(f"\nGrand total: {total} records across all years")


if __name__ == "__main__":
    scrape_all_years()