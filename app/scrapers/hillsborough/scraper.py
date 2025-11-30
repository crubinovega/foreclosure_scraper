import requests
import time
import re
from datetime import datetime, timedelta

BASE_URL = "https://gis.hcpafl.org/CommonServices/property"


# ----------------------------------------------------------
# ADDRESS NORMALIZATION (PRESERVE SPACES, REMOVE PUNCT)
# ----------------------------------------------------------
def normalize_address(addr):
    if not addr:
        return ""
    addr = addr.upper()
    addr = re.sub(r"[,.]", "", addr)       # remove punctuation
    addr = re.sub(r"\s+", " ", addr)       # collapse spaces
    return addr.strip()


# ----------------------------------------------------------
# Extract street number + street name only
# ----------------------------------------------------------
def extract_street_only(addr):
    if not addr:
        return ""

    addr = addr.upper()

    # Split by comma if present
    if "," in addr:
        return addr.split(",")[0].strip()

    tokens = addr.split()

    STOP_WORDS = {
        "TAMPA", "ODESSA", "LUTZ", "APOLLO", "BEACH",
        "PLANT", "RIVERVIEW", "FL", "GA", "TX", "NC",
        "SC", "AL", "LA", "MS", "TN"
    }

    street_tokens = []
    for tok in tokens:
        if tok in STOP_WORDS:
            break
        street_tokens.append(tok)

    return " ".join(street_tokens).strip()


# ----------------------------------------------------------
# OWNER-OCCUPIED DETECTION
# ----------------------------------------------------------
def is_owner_occupied(site_address, mailing_raw, buyer_name):

    site_street = normalize_address(extract_street_only(site_address))
    mail_street = normalize_address(extract_street_only(mailing_raw))

    # If streets don't match → not owner occupied
    if site_street != mail_street:
        return False

    # If buyer is an entity, it's investment even if addresses match
    ENTITIES = ["LLC", "INC", "HOLDINGS", "CAPITAL", "PROPERTIES", "MGMT", "LP", "CORP"]
    buyer_upper = (buyer_name or "").upper()

    if any(word in buyer_upper for word in ENTITIES):
        return False

    return True  # Same street, and not business → owner occupied


# ----------------------------------------------------------
# Fetch single page of sales
# ----------------------------------------------------------
def fetch_sales(page=1, pagesize=1000):
    url = f"{BASE_URL}/search/SalesSearchMod"
    params = {
        "prop": "0403,0400,0500,0501,0200,0408,0508,0111,0102,0100,0106",
        "stype": "q",
        "pagesize": pagesize,
        "page": page,
    }
    resp = requests.get(url, params=params)
    resp.raise_for_status()
    return resp.json()


# ----------------------------------------------------------
# Fetch full property details
# ----------------------------------------------------------
def fetch_property_details(pin):
    url = f"{BASE_URL}/search/ParcelData?pin={pin}"
    resp = requests.get(url)
    resp.raise_for_status()
    return resp.json()


# ----------------------------------------------------------
# Detect cash buyers
# ----------------------------------------------------------
def detect_cash_purchase(details):
    sales = details.get("salesHistory", [])
    if not sales:
        return False

    deed = (sales[0].get("deedType") or "").strip().upper()

    investor_deed_types = ["TR", "TD", "QC", "SWD", "WD"]

    if deed in investor_deed_types:
        return True

    # If NO mortgage data anywhere, assume cash
    if "mortgage" not in str(details).lower():
        return True

    return False


# ----------------------------------------------------------
# MAIN INVESTOR SCRAPER
# ----------------------------------------------------------
def get_recent_cash_buyers(max_pages=None, days_back=180):

    portfolio_map = {}
    properties_by_mailing = {}

    print(f"🔍 Building portfolio index for last {days_back} days...")

    # ----------------------------------------------------------
    # FIRST PASS — Build investor portfolios
    # ----------------------------------------------------------
    page = 1
    while max_pages is None or page <= max_pages:
        print(f"📄 Fetching sales page {page}...")
        try:
            sales = fetch_sales(page)
        except:
            break

        if not sales:
            print(f"⚠️ No more sales at page {page}.")
            break

        for s in sales:

            sale_date = s.get("saleDate")
            if not sale_date:
                continue

            # Convert date
            try:
                sale_dt = datetime.strptime(sale_date, "%Y-%m-%d")
            except:
                continue

            if sale_dt < datetime.now() - timedelta(days_back):
                continue

            pin = s.get("pin")
            if not pin:
                continue

            try:
                details = fetch_property_details(pin)
            except Exception as e:
                print("⚠️ Error fetching details:", e)
                continue

            # Mailing address
            mailing = details.get("mailingAddress") or {}
            mail_raw = f"{mailing.get('addr1','')} {mailing.get('city','')} {mailing.get('state','')} {mailing.get('zip','')}"
            mail_norm = normalize_address(mail_raw)

            # Extract property info
            bldg = (details.get("buildings") or [{}])[0]
            prop_type = bldg.get("type", {}).get("description", "")
            year_built = bldg.get("yearBuilt")

            site_addr = (
                details.get("siteAddress")
                or s.get("address")
                or s.get("siteAddress")
                or ""
            )

            prop_record = {
                "pin": pin,
                "folio": s.get("displayFolio"),
                "site_address": site_addr,
                "sale_price": s.get("salePrice"),
                "sale_date": s.get("saleDate"),
                "type": prop_type,
                "year_built": year_built,
            }

            # Add to portfolio map
            portfolio_map[mail_norm] = portfolio_map.get(mail_norm, 0) + 1

            # Store all properties for this mailing address
            if mail_norm not in properties_by_mailing:
                properties_by_mailing[mail_norm] = []

            properties_by_mailing[mail_norm].append(prop_record)

        page += 1
        time.sleep(0.25)  # reduce risk of rate limiting

    print(f"📦 Portfolio map built. Unique owners: {len(portfolio_map)}")

    # ----------------------------------------------------------
    # SECOND PASS — Apply investor filters
    # ----------------------------------------------------------
    investors = []

    print("🔍 Applying investor filters...")

    for mail_norm, props in properties_by_mailing.items():

        if mail_norm not in portfolio_map:
            continue

        portfolio_count = portfolio_map[mail_norm]
        if portfolio_count < 2:
            continue  # skip one-off buyers

        # Extract fields from first property (just to get owner + mailing)
        sample_pin = props[0]["pin"]

        try:
            details = fetch_property_details(sample_pin)
        except:
            continue

        buyer_name = details.get("owner", "").strip()

        mailing = details.get("mailingAddress") or {}
        mail_raw = f"{mailing.get('addr1','')} {mailing.get('city','')} {mailing.get('state','')} {mailing.get('zip','')}"

        site_first = props[0].get("site_address", "")

        # Filter out owner-occupied
        if is_owner_occupied(site_first, mail_raw, buyer_name):
            continue

        # Cash buyer check
        if not detect_cash_purchase(details):
            continue

        # Build final investor profile
        investors.append({
            "buyer_name": buyer_name,
            "mailing_address": mail_raw.strip(),
            "portfolio_count": portfolio_count,
            "properties": props  # This is a LIST of all properties
        })


    print(f"🎉 FINAL INVESTOR COUNT: {len(investors)}")
    return investors