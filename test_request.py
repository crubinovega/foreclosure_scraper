from app.scrapers.hillsborough.scraper import get_recent_cash_buyers

print("🔎 Running investor preview...\n")

# Fetch investors from last 180 days
investors = get_recent_cash_buyers(
    max_pages=15,
    days_back=180
)

print("\n🎉 Previewing first 10 investors:\n")

for i, inv in enumerate(investors[:10], 1):
    print(f"---- Investor #{i} ----")
    print(f"Name: {inv.get('buyer_name')}")
    print(f"Mailing Address: {inv.get('mailing_address')}")
    print(f"Portfolio Count: {inv.get('portfolio_count')}")
    print("\nProperties:")

    # Loop through each property in the properties list
    for prop in inv.get('properties', []):
        print(f"  • Site Address: {prop.get('site_address')}")
        print(f"    Sale Price: ${prop.get('sale_price'):,}" if prop.get('sale_price') else "    Sale Price: N/A")
        print(f"    Sale Date: {prop.get('sale_date')}")
        print(f"    Type: {prop.get('type')}")
        print(f"    Year Built: {prop.get('year_built')}")
        print(f"    Folio: {prop.get('folio')}")
        print(f"    PIN: {prop.get('pin')}")
        print()

    print("-------------------------\n")

print(f"🎯 Total Investors Found: {len(investors)}")