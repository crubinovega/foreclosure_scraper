import pandas as pd
import re


# ---------------------------------------
# Extract street portion only
# (house number + street name)
# ---------------------------------------
def extract_street(addr):
    if not isinstance(addr, str):
        return ""

    addr = addr.upper().replace(",", " ")
    tokens = addr.split()

    # Stop words (cities + states)
    STOP = {
        "TAMPA", "ODESSA", "LUTZ", "RIVERVIEW", "PLANT", "CITY", "FL", "GA", "TX", "NC", "SC", "AL", "LA", "MS", "TN"
    }

    street_tokens = []
    for tok in tokens:
        if tok in STOP:
            break
        street_tokens.append(tok)

    return " ".join(street_tokens).strip()


# ---------------------------------------
# Detect if buyer looks like a company
# ---------------------------------------
def is_entity(name):
    if not isinstance(name, str):
        return False
    name = name.upper()
    keywords = ["LLC", "INC", "TRUST", "HOLDINGS", "CAPITAL", "PROPERTIES", "MGMT", "LP", "CORP"]
    return any(k in name for k in keywords)


# ---------------------------------------
# Detect owner-occupied
# ---------------------------------------
def is_owner_occupied(site_addr, mailing_addr, owner1, owner2):
    site_st = extract_street(site_addr)
    mail_st = extract_street(mailing_addr)

    # If street matches AND name is NOT an entity → owner occupied
    if site_st and mail_st and site_st == mail_st:
        if not is_entity(owner1) and not is_entity(owner2):
            return True

    return False


# ---------------------------------------
# MAIN PROCESSOR
# ---------------------------------------
def process_sales_csv(path):
    df = pd.read_csv(path)

    # Extract streets
    df["SiteStreet"] = df["SiteAddress"].apply(extract_street)
    df["MailStreet"] = df["MailingAddress1"].apply(extract_street)

    # Owner-occupied flag
    df["OwnerOccupied"] = df.apply(
        lambda x: is_owner_occupied(
            x["SiteAddress"],
            x["MailingAddress1"],
            x["Owner1"],
            x["Owner2"]
        ),
        axis=1
    )

    # Portfolio size via mailing address
    df["PortfolioCount"] = df.groupby("MailingAddress1")["MailingAddress1"].transform("size")

    # Investor if:
    # - Not owner-occupied
    # - PortfolioCount >= 2
    df_investors = df[
        (df["OwnerOccupied"] == False) &
        (df["PortfolioCount"] >= 2)
        ].copy()

    # Optional: classify investor type
    df_investors["InvestorType"] = df_investors["PortfolioCount"].apply(
        lambda n:
        "Institutional (25+)" if n >= 25 else
        "Large (10-24)" if n >= 10 else
        "Mid-size (4-9)" if n >= 4 else
        "Small (2-3)"
    )

    return df_investors


# ---------------------------------------
# Run it
# ---------------------------------------
if __name__ == "__main__":
    investors = process_sales_csv("data/hillsborough_sales.csv")
    print(investors.head(20))
    investors.to_csv("investors_output.csv", index=False)
