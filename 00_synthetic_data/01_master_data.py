"""Generate master data: branches, merchant categories, customers and cards.

Writes data/branches.csv, data/merchant_categories.csv, data/customers.csv, data/cards.csv.
"""
import os
import random
from datetime import date, timedelta

import pandas as pd

from common import (ATM_MCC, BRANCHES, BRANCH_BY_CITY, CITY_WEIGHTS, DATA_DIR,
                    MERCHANT_CATEGORIES)

MALE_FIRST = ["Abdullah", "Mohammed", "Fahad", "Khalid", "Saud", "Faisal", "Turki", "Nasser",
              "Omar", "Yousef", "Abdulaziz", "Sultan", "Majed", "Bandar", "Hamad", "Rayan"]
FEMALE_FIRST = ["Noura", "Sara", "Reem", "Lama", "Hessa", "Maha", "Abeer", "Dana",
                "Lulwa", "Shahad", "Jawaher", "Amal", "Haya", "Mashael", "Ghada", "Rawan"]
FAMILY = ["Al-Qahtani", "Al-Otaibi", "Al-Ghamdi", "Al-Zahrani", "Al-Harbi", "Al-Shehri",
          "Al-Dosari", "Al-Mutairi", "Al-Anazi", "Al-Shammari", "Al-Subaie", "Al-Malki",
          "Al-Juhani", "Al-Rashidi", "Al-Omari", "Al-Tamimi", "Al-Yami", "Al-Balawi"]
EXPAT_FIRST = ["Ahmed", "Imran", "Rahul", "Jose", "Mahmoud", "Ali", "Priya", "Fatima", "Hassan", "Maria"]
EXPAT_FAMILY = ["Khan", "Hussain", "Sharma", "Santos", "Ibrahim", "Mostafa", "Nair", "Rahman", "Cruz", "Haddad"]


def iban_check_digits(bank_code, account):
    """ISO 13616 mod-97 check digits for a Saudi IBAN (SA + 2 check + 2 bank + 18 account)."""
    bban = bank_code + account
    rearranged = bban + "SA00"
    numeric = "".join(str(int(ch, 36)) for ch in rearranged)
    return f"{98 - int(numeric) % 97:02d}"


def make_iban(rng):
    bank_code = "77"                      # fictional bank code
    account = "".join(str(rng.randint(0, 9)) for _ in range(18))
    return f"SA{iban_check_digits(bank_code, account)}{bank_code}{account}"


def generate_customers(rng, n=2000):
    rows = []
    for i in range(n):
        is_citizen = rng.random() < 0.7
        if is_citizen:
            first = rng.choice(MALE_FIRST + FEMALE_FIRST)
            last = rng.choice(FAMILY)
            national_id = "1" + "".join(str(rng.randint(0, 9)) for _ in range(9))
        else:
            first = rng.choice(EXPAT_FIRST)
            last = rng.choice(EXPAT_FAMILY)
            national_id = "2" + "".join(str(rng.randint(0, 9)) for _ in range(9))   # Iqama
        city = rng.choices(list(CITY_WEIGHTS), weights=list(CITY_WEIGHTS.values()))[0]
        email_name = f"{first}.{last.replace('Al-', '')}".lower()
        rows.append({
            "customer_id": f"CUST-{100000 + i}",
            "full_name": f"{first} {last}",
            "national_id": national_id,
            "customer_type": "CITIZEN" if is_citizen else "RESIDENT",
            "iban": make_iban(rng),
            "phone": "+9665" + "".join(str(rng.randint(0, 9)) for _ in range(8)),
            "email": f"{email_name}{rng.randint(1, 999)}@example.com",
            "city": city,
            "home_branch_id": BRANCH_BY_CITY[city],
            "join_date": (date(2015, 1, 1) + timedelta(days=rng.randint(0, 3800))).isoformat(),
        })
    return pd.DataFrame(rows)


def generate_cards(rng, customers):
    rows = []
    n = 0
    for c in customers.itertuples():
        join = date.fromisoformat(c.join_date)
        # every customer has a mada debit card
        specs = [("MADA_DEBIT", "mada", None)]
        r = rng.random()
        if r < 0.30:
            specs.append(("CREDIT_CLASSIC", "Visa", rng.choice([5000, 8000, 10000, 15000])))
        elif r < 0.42:
            specs.append(("CREDIT_PLATINUM", "Mastercard", rng.choice([30000, 50000, 75000])))
        if rng.random() < 0.08:
            specs.append(("PREPAID", "mada", None))
        for card_type, scheme, limit in specs:
            issue = join + timedelta(days=rng.randint(0, 365))
            rows.append({
                "card_id": f"CARD-{500000 + n}",
                "customer_id": c.customer_id,
                "card_type": card_type,
                "card_scheme": scheme,
                "last4": f"{rng.randint(0, 9999):04d}",
                "credit_limit_sar": limit,
                "issue_date": issue.isoformat(),
                "expiry_date": (issue + timedelta(days=5 * 365)).isoformat(),
                "card_status": "ACTIVE",
            })
            n += 1
    return pd.DataFrame(rows)


def generate_master_data(seed=42):
    rng = random.Random(seed)
    os.makedirs(DATA_DIR, exist_ok=True)

    branches = pd.DataFrame(BRANCHES, columns=["branch_id", "name", "city", "region", "opening_date", "phone"])
    categories = pd.DataFrame(
        [(m[0], m[1], m[2], m[3], int(m[5])) for m in MERCHANT_CATEGORIES]
        + [(ATM_MCC[0], ATM_MCC[1], ATM_MCC[2], ATM_MCC[3], 0)],
        columns=["mcc_code", "category_name", "typical_min_sar", "typical_max_sar", "bnpl_eligible"],
    )
    customers = generate_customers(rng)
    cards = generate_cards(rng, customers)

    branches.to_csv(os.path.join(DATA_DIR, "branches.csv"), index=False)
    categories.to_csv(os.path.join(DATA_DIR, "merchant_categories.csv"), index=False)
    customers.to_csv(os.path.join(DATA_DIR, "customers.csv"), index=False)
    cards.to_csv(os.path.join(DATA_DIR, "cards.csv"), index=False)
    print(f"branches: {len(branches)} | merchant_categories: {len(categories)} | "
          f"customers: {len(customers)} | cards: {len(cards)}")


if __name__ == "__main__":
    generate_master_data()