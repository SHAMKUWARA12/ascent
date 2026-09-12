"""
ASCENT — NIRF 2025 Engineering Rankings Scraper

Scrapes real NIRF 2025 engineering rankings from
nirfindia.org (official Government of India source)
and updates the nirf_rank field in the nits MongoDB
collection, replacing the approximate/hardcoded values
in generate_seed_nits.py.

Source: https://www.nirfindia.org/Rankings/2025/
Pages scraped:
  EngineeringRanking.html      (ranks 1-100, exact)
  EngineeringRanking150.html   (band 101-150, no exact rank)
  EngineeringRanking200.html   (band 151-200, no exact rank)
  EngineeringRanking300.html   (band 201-300, no exact rank)

Legal: public government website, read-only,
       no login required, no ToS violation.
"""

import asyncio
import time
import re
import requests
from bs4 import BeautifulSoup
from motor.motor_asyncio import AsyncIOMotorClient

MONGODB_URL   = "mongodb://localhost:27017"
DATABASE_NAME = "ascent_db"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0 Safari/537.36"
    )
}

NIRF_PAGES = [
    {
        "url": "https://www.nirfindia.org/Rankings/2025/EngineeringRanking.html",
        "band": "1-100",
        "has_exact_rank": True
    },
    {
        "url": "https://www.nirfindia.org/Rankings/2025/EngineeringRanking150.html",
        "band": "101-150",
        "has_exact_rank": False
    },
    {
        "url": "https://www.nirfindia.org/Rankings/2025/EngineeringRanking200.html",
        "band": "151-200",
        "has_exact_rank": False
    },
    {
        "url": "https://www.nirfindia.org/Rankings/2025/EngineeringRanking300.html",
        "band": "201-300",
        "has_exact_rank": False
    },
]

# Map NIRF name substrings → our NIT code
# More specific patterns listed first to avoid false matches
NIT_NAME_MAP = {
    "National Institute of Technology Tiruchirappalli":    "NITT",
    "National Institute of Technology Rourkela":           "NITRK",
    "National Institute of Technology Karnataka":          "NITK",
    "National Institute of Technology Calicut":            "NITC",
    "National Institute of Technology Warangal":           "NITW",
    "National Institute of Technology Durgapur":           "NITDGP",
    "National Institute of Technology Silchar":            "NITSLR",
    "National Institute of Technology Patna":              "NITP",
    "Dr. B R Ambedkar National Institute of Technology":   "NITJ",
    "National Institute of Technology, Jamshedpur":        "NITJSR",
    "National Institute of Technology Jamshedpur":         "NITJSR",
    "Malaviya National Institute of Technology":           "MNIT",
    "Visvesvaraya National Institute of Technology":       "VNIT",
    "Motilal Nehru National Institute of Technology":      "MNNIT",
    "Maulana Azad National Institute of Technology":       "MANIT",
    "National Institute of Technology Delhi":              "NITD",
    "Sardar Vallabhbhai National Institute of Technology": "SVNIT",
    "National Institute of Technology Srinagar":           "NITSR",
    "National Institute of Technology Kurukshetra":        "NITKKR",
    "National Institute of Technology, Raipur":            "NITRR",
    "National Institute of Technology Raipur":             "NITRR",
    "National Institute of Technology Hamirpur":           "NITH",
    "National Institute of Technology Puducherry":         "NITPY",
    "National Institute of Technology Meghalaya":          "NITM",
    "National Institute of Technology Agartala":           "NITA",
    "National Institute of Technology Arunachal Pradesh":  "NITAR",
    "National Institute of Technology Goa":                "NITGOA",
    "National Institute of Technology Mizoram":            "NITMZ",
    "National Institute of Technology Nagaland":           "NITNGL",
    "National Institute of Technology Manipur":            "NITMN",
    "National Institute of Technology Sikkim":             "NITSKM",
    "National Institute of Technology Uttarakhand":        "NITUK",
    "National Institute of Technology Andhra Pradesh":     "NITAP",
}


def match_nit_code(name: str):
    """Match a NIRF institution name to our NIT code."""
    for nirf_name, code in NIT_NAME_MAP.items():
        if nirf_name.lower() in name.lower():
            return code
    return None


def fetch_page(url: str):
    """Fetch a page with retry logic."""
    for attempt in range(1, 4):
        try:
            time.sleep(1)
            res = requests.get(url, headers=HEADERS, timeout=15)
            res.raise_for_status()
            return res.text
        except Exception as e:
            print(f"  Attempt {attempt}/3 failed: {e}")
            time.sleep(attempt * 3)
    print(f"  ❌ Could not fetch {url} after 3 attempts")
    return None


def scrape_exact_rank_page(html: str, band: str) -> list:
    """
    Parse the top-100 page which has a full table with
    Institute ID, Name, City, State, Score, Rank columns.
    """
    soup = BeautifulSoup(html, "html.parser")
    results = []

    table = soup.find("table")
    if not table:
        print(f"  ❌ No <table> found on exact rank page")
        return results

    rows = table.find_all("tr")
    for row in rows[1:]:  # skip header
        cells = row.find_all(["td", "th"])
        if len(cells) < 6:
            continue

        # Name is in second cell; clean up injected javascript text
        name_raw = cells[1].get_text(separator=" ", strip=True)
        name = re.sub(r"\s+More Details.*", "", name_raw).strip()
        name = re.sub(r"\s+(TLR|RPC|GO|OI|PERCEPTION).*", "", name).strip()

        # Rank is in last cell
        rank_raw = cells[-1].get_text(strip=True)
        try:
            rank = int(rank_raw)
        except ValueError:
            continue

        code = match_nit_code(name)
        if code:
            results.append({
                "nit_code": code,
                "nirf_name": name,
                "nirf_rank": rank,
                "rank_band": band,
                "is_exact": True,
                "source": "NIRF 2025 Engineering"
            })
            print(f"    ✅ {name[:52]:52s} → {code} (Rank {rank})")

    return results


def scrape_band_page(html: str, band: str) -> list:
    """
    Parse a band page (101-150, 151-200, 201-300).
    These pages only list names in alphabetical order
    with no exact rank — scrape all text content and
    match against our NIT name map.
    """
    soup = BeautifulSoup(html, "html.parser")
    results = []

    # Band pages may use a table OR just list items —
    # try both approaches

    # Approach 1: table rows
    table = soup.find("table")
    if table:
        rows = table.find_all("tr")
        for row in rows[1:]:
            cells = row.find_all(["td", "th"])
            if not cells:
                continue
            name = cells[0].get_text(strip=True)
            code = match_nit_code(name)
            if code:
                results.append({
                    "nit_code": code,
                    "nirf_name": name,
                    "nirf_rank": None,
                    "rank_band": band,
                    "is_exact": False,
                    "source": "NIRF 2025 Engineering"
                })
                print(f"    ✅ {name[:52]:52s} → {code} "
                      f"(Band {band} — no exact rank)")
        if results:
            return results

    # Approach 2: scan ALL text in the page for known NIT names
    # (handles cases where page uses <li>, <p>, or other tags)
    print(f"  No table found — scanning all text for NIT names...")
    all_text_elements = soup.find_all(
        ["td", "th", "li", "p", "div", "span", "a"],
        string=True
    )
    seen = set()
    for el in all_text_elements:
        name = el.get_text(strip=True)
        if len(name) < 10:
            continue
        code = match_nit_code(name)
        if code and code not in seen:
            seen.add(code)
            results.append({
                "nit_code": code,
                "nirf_name": name,
                "nirf_rank": None,
                "rank_band": band,
                "is_exact": False,
                "source": "NIRF 2025 Engineering"
            })
            print(f"    ✅ {name[:52]:52s} → {code} "
                  f"(Band {band} — no exact rank)")

    return results


def scrape_all_nirf() -> dict:
    """
    Scrape all NIRF pages and return {nit_code: rank_data} mapping.
    """
    all_results = {}

    for page in NIRF_PAGES:
        print(f"\nScraping band {page['band']} — {page['url']}")
        html = fetch_page(page["url"])
        if not html:
            continue

        if page["has_exact_rank"]:
            results = scrape_exact_rank_page(html, page["band"])
        else:
            results = scrape_band_page(html, page["band"])

        for r in results:
            code = r["nit_code"]
            # Never overwrite an exact rank with a band entry
            if code not in all_results or r["is_exact"]:
                all_results[code] = r

    return all_results


async def update_mongodb(nirf_data: dict):
    """
    Update nirf_rank fields in the nits collection.
    Only updates existing documents — never inserts or deletes.
    """
    client = AsyncIOMotorClient(MONGODB_URL)
    db = client[DATABASE_NAME]

    nits = await db["nits"].find(
        {}, {"_id": 0, "nit_code": 1, "name": 1}
    ).to_list(100)

    updated   = 0
    not_found = []

    for nit in nits:
        code = nit["nit_code"]
        if code in nirf_data:
            r = nirf_data[code]
            await db["nits"].update_one(
                {"nit_code": code},
                {"$set": {
                    # nirf_rank: exact integer if known, None if band-only
                    "nirf_rank":         r["nirf_rank"],
                    "nirf_rank_band":    r["rank_band"],
                    # nirf_rank_display: what to SHOW in the UI
                    # e.g. "13" for exact, "101-150" for band
                    "nirf_rank_display": (
                        str(r["nirf_rank"]) if r["is_exact"]
                        else r["rank_band"]
                    ),
                    "nirf_rank_exact":   r["is_exact"],
                    "nirf_source":       r["source"],
                }}
            )
            updated += 1
        else:
            not_found.append(code)

    print(f"\n✅ Updated {updated} NITs with real NIRF 2025 ranks")
    if not_found:
        print(
            f"⚠️  {len(not_found)} NITs not found in NIRF top-300 "
            f"(will keep current approximate rank): {not_found}"
        )

    client.close()
    return updated, not_found


async def run():
    print("=" * 60)
    print("ASCENT — NIRF 2025 Engineering Rankings Scraper")
    print("Source: nirfindia.org (official Government of India)")
    print("=" * 60)

    nirf_data = scrape_all_nirf()

    print(f"\n{'='*60}")
    print(f"Scraping complete. Found {len(nirf_data)} NITs total.")
    print(f"{'='*60}")

    print("\nUpdating MongoDB nits collection...")
    updated, not_found = await update_mongodb(nirf_data)

    print(f"\n{'='*60}")
    print("FINAL SUMMARY")
    print(f"{'='*60}")
    print(f"NITs updated with real NIRF 2025 rank: {updated}")
    print(f"NITs not in NIRF top-300 (kept approx): {len(not_found)}")
    if not_found:
        print(f"Unranked codes: {not_found}")
    print(f"\nnirf_rank_display field now shows:")
    print(f"  Exact rank  → numeric string e.g. '9', '13', '50'")
    print(f"  Band only   → range string  e.g. '101-150'")
    print(f"  Not in NIRF → kept as previous approximate value")


if __name__ == "__main__":
    asyncio.run(run())