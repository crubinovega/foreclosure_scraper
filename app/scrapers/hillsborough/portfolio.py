import requests
from bs4 import BeautifulSoup

SEARCH_URL = "https://gis.hillsboroughcounty.org/PropertyAppraiser/ParcelSearch/Search"


def lookup_hillsborough_portfolio(buyer_name):
    payload = {
        "OwnerName": buyer_name,
        "Address": "",
        "SaleDateFrom": "",
        "SaleDateTo": ""
    }

    response = requests.post(SEARCH_URL, data=payload)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    rows = soup.find_all("tr")

    parcels = []

    for row in rows:
        cols = row.find_all("td")
        if len(cols) < 3:
            continue

        parcel_id = cols[0].text.strip()
        address = cols[1].text.strip()

        parcels.append({
            "ParcelID": parcel_id,
            "Address": address
        })

    return {
        "BuyerName": buyer_name,
        "PortfolioCount": len(parcels),
        "Properties": parcels
    }
