"""
ASCENT — CCMT 2026 Seat Matrix Scraper

Fetches TOTAL intake seats per programme per category
for all NITs from the official CCMT 2026 Seat Matrix.

URL: https://admissions.nic.in/CCMT/Applicant/Report/
     SeatMatrixForm_CC.aspx?agencyid=105&boardid=105012621

Technical approach:
The page uses jQuery "Chosen" plugin which hides the real
<select> elements and renders a custom UI on top. Selenium
must set values on the hidden native <select> elements
using JavaScript (driver.execute_script), then trigger
the ASP.NET PostBack manually to refresh dependent dropdowns.

We scrape once per CSE/DA-relevant department code to keep
the result set manageable. Departments targeted:
  CT = Computer Science & Engineering
  IT = Information Technology
  MC = Mathematical & Computational Sciences
  CG = Computer Science & Technology
  CX = Computer Engineering
  C2 = Centre for Artificial Intelligence
  DP = Mathematics and Computing

Legal: public government page, no login required.
"""

import asyncio
import sys
import os
import time
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from motor.motor_asyncio import AsyncIOMotorClient
from app.process_cutoffs import (
    normalise_institute_code,
    classify_programme,
)

MONGODB_URL     = "mongodb://localhost:27017"
DATABASE_NAME   = "ascent_db"
SEAT_MATRIX_URL = (
    "https://admissions.nic.in/CCMT/Applicant/Report/"
    "SeatMatrixForm_CC.aspx?agencyid=105&boardid=105012621"
)

# Department codes to scrape — only CSE/DA relevant depts
# This filters at source, reducing table size significantly
CSE_DA_DEPT_CODES = [
    "CT",   # Computer Science & Engineering (main)
    "IT",   # Information Technology
    "MC",   # Mathematical & Computational Sciences
    "CG",   # Computer Science & Technology
    "CX",   # Computer Engineering
    "C2",   # Centre for Artificial Intelligence
    "DP",   # Mathematics and Computing
    "MD",   # Mathematics, CS & Engineering (covers some DA)
    "A2",   # Mathematics, Bioinformatics & CS
    "CA",   # Computer Applications
]


# ── Driver ────────────────────────────────────────────────

def get_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0 Safari/537.36"
    )
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)


# ── Set a hidden <select> value via JavaScript ────────────

def js_set_select(driver, element_id: str, value: str):
    """
    Set a hidden native <select> value via JavaScript and
    trigger the ASP.NET onchange PostBack so the server
    refreshes dependent dropdowns.
    """
    driver.execute_script(
        f"""
        var sel = document.getElementById('{element_id}');
        sel.value = '{value}';
        var event = new Event('change', {{ bubbles: true }});
        sel.dispatchEvent(event);
        if (sel.onchange) {{ sel.onchange(); }}
        """,
    )
    time.sleep(3)  # wait for PostBack to complete


# ── Wait for table to appear ──────────────────────────────

def wait_for_table(driver, timeout: int = 60) -> bool:
    try:
        WebDriverWait(driver, timeout).until(
            lambda d: any(
                "OPEN" in t.text or "Total" in t.text
                for t in d.find_elements(By.TAG_NAME, "table")
            )
        )
        return True
    except Exception:
        return False


# ── Scrape one department at a time ──────────────────────

def scrape_department(driver, dept_code: str) -> list:
    """
    Set Department = dept_code, leave everything else as All,
    wait for table, scrape all rows. Returns list of raw dicts.
    """
    print(f"\n  Setting Department = {dept_code}...")

    # Reset to All first to trigger PostBack
    js_set_select(
        driver,
        "ctl00_ContentPlaceHolder1_ddlDepartment",
        "All"
    )

    # Now set the target department
    js_set_select(
        driver,
        "ctl00_ContentPlaceHolder1_ddlDepartment",
        dept_code
    )
    time.sleep(2)

    # Reset Programme and Group to All
    js_set_select(
        driver,
        "ctl00_ContentPlaceHolder1_ddlProgram",
        "All"
    )
    js_set_select(
        driver,
        "ctl00_ContentPlaceHolder1_ddlGroupList",
        "All"
    )

    found = wait_for_table(driver, timeout=45)
    if not found:
        print(f"    ⚠️ No table for dept {dept_code} — skipping")
        return []

    time.sleep(2)
    html = driver.page_source
    rows = parse_table(html)
    print(f"    Found {len(rows)} rows")
    return rows


# ── Parse the seat matrix table ───────────────────────────

def parse_table(html: str) -> list:
    """
    Parse the Seat Matrix HTML table.

    Columns: Institute | Department | Programme | Group |
    OPEN | OPEN-PwD | EWS | EWS-PwD | SC | SC-PwD |
    ST | ST-PwD | OBC | OBC-PwD | Total
    """
    soup = BeautifulSoup(html, "html.parser")
    records = []

    # Find table with OPEN and Total headers
    target_table = None
    for table in soup.find_all("table"):
        header = table.find("tr")
        if not header:
            continue
        text = header.get_text()
        if "OPEN" in text and "Total" in text:
            target_table = table
            break

    if not target_table:
        return []

    rows = target_table.find_all("tr")
    if len(rows) < 2:
        return []

    # Build column index map from header
    header_cells = [
        th.get_text(strip=True)
        for th in rows[0].find_all(["th", "td"])
    ]
    col = {name: i for i, name in enumerate(header_cells)}

    def safe_int(s: str) -> int:
        try:
            return int(re.search(r"\d+", s).group())
        except (AttributeError, ValueError, TypeError):
            return 0

    def cell(cells, name, default=""):
        idx = col.get(name)
        if idx is None or idx >= len(cells):
            return default
        return cells[idx].get_text(strip=True)

    for row in rows[1:]:
        cells = row.find_all(["td", "th"])
        if len(cells) < 10:
            continue

        institute = cell(cells, "Institute")
        programme = cell(cells, "Programme")

        if not institute or institute == "Institute":
            continue

        records.append({
            "institute_name": institute,
            "department":     cell(cells, "Department"),
            "programme":      programme,
            "group":          cell(cells, "Group"),
            "seats_UR":       safe_int(cell(cells, "OPEN",  "0")),
            "seats_EWS":      safe_int(cell(cells, "EWS",   "0")),
            "seats_SC":       safe_int(cell(cells, "SC",    "0")),
            "seats_ST":       safe_int(cell(cells, "ST",    "0")),
            "seats_OBC":      safe_int(cell(cells, "OBC",   "0")),
            "seats_total":    safe_int(cell(cells, "Total", "0")),
            "data_type":      "CCMT 2026 Total Intake",
        })

    return records


# ── Full fetch: initialise page then loop departments ─────

def fetch_all_departments() -> list:
    driver = get_driver()
    all_records = []

    try:
        print(f"Opening Seat Matrix page...")
        driver.get(SEAT_MATRIX_URL)
        time.sleep(8)

        # Step 1: Set Type = NIT
        print("Setting Type of Institute = NIT...")
        js_set_select(
            driver,
            "ctl00_ContentPlaceHolder1_ddlInstType",
            "NIT"
        )
        time.sleep(3)

        # Step 2: Set Institute = All
        print("Setting Institute = All...")
        js_set_select(
            driver,
            "ctl00_ContentPlaceHolder1_ddlInstitutes",
            "All"
        )
        time.sleep(3)

        # Step 3: Loop through each CSE/DA department
        for dept_code in CSE_DA_DEPT_CODES:
            rows = scrape_department(driver, dept_code)
            all_records.extend(rows)

        print(f"\nTotal raw rows scraped: {len(all_records)}")

    finally:
        driver.quit()

    return all_records


# ── Enrich: add nit_code and branch_code ─────────────────

def enrich_records(records: list) -> list:
    enriched = []
    for r in records:
        nit_code    = normalise_institute_code(r["institute_name"])
        branch_code = classify_programme(r["programme"])

        if nit_code == "UNKNOWN" or branch_code is None:
            continue

        enriched.append({**r, "nit_code": nit_code,
                              "branch_code": branch_code})

    print(f"Enriched: {len(enriched)} CSE/DA NIT records "
          f"(from {len(records)} total raw rows)")
    return enriched


# ── Aggregate: sum seats per NIT+branch ──────────────────

def aggregate_seats(records: list) -> dict:
    agg = {}
    for r in records:
        key = (r["nit_code"], r["branch_code"])
        if key not in agg:
            agg[key] = {
                "UR": 0, "OBC": 0, "SC": 0,
                "ST": 0, "EWS": 0, "total": 0
            }
        agg[key]["UR"]    += r.get("seats_UR",    0)
        agg[key]["OBC"]   += r.get("seats_OBC",   0)
        agg[key]["SC"]    += r.get("seats_SC",     0)
        agg[key]["ST"]    += r.get("seats_ST",     0)
        agg[key]["EWS"]   += r.get("seats_EWS",   0)
        agg[key]["total"] += r.get("seats_total",  0)
    return agg


# ── Save to MongoDB ───────────────────────────────────────

async def save_to_mongodb(records: list, agg: dict):
    client = AsyncIOMotorClient(MONGODB_URL)
    db = client[DATABASE_NAME]

    # Save raw records
    await db["seat_matrix"].delete_many({})
    if records:
        await db["seat_matrix"].insert_many(records)
        print(f"Saved {len(records)} records to seat_matrix collection")

    # Update nits.mtech_programs
    updated_nits  = 0
    updated_progs = 0

    for nit_code in sorted(set(k[0] for k in agg)):
        nit_doc = await db["nits"].find_one({"nit_code": nit_code})
        if not nit_doc:
            continue

        programs = nit_doc.get("mtech_programs", [])
        changed  = False

        for prog in programs:
            key = (nit_code, prog["short_name"])
            if key in agg:
                prog["seats"] = {
                    "UR":    agg[key]["UR"],
                    "OBC":   agg[key]["OBC"],
                    "SC":    agg[key]["SC"],
                    "ST":    agg[key]["ST"],
                    "EWS":   agg[key]["EWS"],
                    "total": agg[key]["total"],
                }
                prog["seats_data_type"] = "CCMT 2026 Total Intake"
                updated_progs += 1
                changed = True

        if changed:
            await db["nits"].update_one(
                {"nit_code": nit_code},
                {"$set": {"mtech_programs": programs}}
            )
            updated_nits += 1

    print(f"Updated {updated_progs} programmes across "
          f"{updated_nits} NITs")
    client.close()


# ── Main ──────────────────────────────────────────────────

async def run():
    print("=" * 60)
    print("ASCENT — CCMT 2026 Seat Matrix Scraper")
    print("Fetching TOTAL intake seats (not vacancy)")
    print("Filtering at source: CSE/DA departments only")
    print("=" * 60)

    records  = fetch_all_departments()

    if not records:
        print("\n❌ No records scraped.")
        print("Saving debug HTML snapshot...")
        os.makedirs("../data/raw", exist_ok=True)
        driver = get_driver()
        try:
            driver.get(SEAT_MATRIX_URL)
            time.sleep(8)
            with open("../data/raw/seat_matrix_debug.html",
                      "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            print("  Saved: data/raw/seat_matrix_debug.html")
        finally:
            driver.quit()
        return

    enriched = enrich_records(records)

    if not enriched:
        print("❌ No CSE/DA NIT records found after enrichment.")
        return

    agg = aggregate_seats(enriched)

    print("\nPer-NIT seat summary:")
    nit_summary = {}
    for (nit_code, branch_code), seats in agg.items():
        nit_summary.setdefault(nit_code, [])
        nit_summary[nit_code].append(
            f"{branch_code}(UR={seats['UR']},OBC={seats['OBC']},"
            f"SC={seats['SC']},ST={seats['ST']},"
            f"total={seats['total']})"
        )
    for code, branches in sorted(nit_summary.items()):
        print(f"  {code}: {branches}")

    await save_to_mongodb(enriched, agg)

    print(f"\n{'='*60}")
    print("COMPLETE — Real total intake seats now in MongoDB")
    print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(run())