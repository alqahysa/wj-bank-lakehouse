"""Shared constants and helpers for the WJ Bank synthetic data generators.

WJ Bank is fictional. Every name, ID, IBAN and phone number produced here is random.
All timestamps are Riyadh local time (Asia/Riyadh, UTC+3) without an offset.
"""
import json
import os
import random
from datetime import datetime, timedelta

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "data")

# ---------------------------------------------------------------------------
# Branches: 5 cities, one branch each
# ---------------------------------------------------------------------------
BRANCHES = [
    # branch_id,     name,                       city,      region,             opening_date, phone
    ("BR-RUH-001", "WJ Olaya Branch",      "Riyadh",  "Riyadh Region",    "2012-03-11", "+966-11-410-2200"),
    ("BR-JED-001", "WJ Tahlia Branch",     "Jeddah",  "Makkah Region",    "2013-09-22", "+966-12-661-4300"),
    ("BR-DMM-001", "WJ Corniche Branch",   "Dammam",  "Eastern Province", "2015-01-18", "+966-13-834-5100"),
    ("BR-MKK-001", "WJ Aziziyah Branch",   "Makkah",  "Makkah Region",    "2017-06-04", "+966-12-556-7800"),
    ("BR-MED-001", "WJ Quba Branch",       "Madinah", "Madinah Region",   "2019-11-10", "+966-14-822-9400"),
]
CITY_WEIGHTS = {"Riyadh": 0.38, "Jeddah": 0.27, "Dammam": 0.15, "Makkah": 0.11, "Madinah": 0.09}
BRANCH_BY_CITY = {b[2]: b[0] for b in BRANCHES}

# ---------------------------------------------------------------------------
# Merchant categories (real ISO 18245 MCC codes, fictional merchant names)
# ---------------------------------------------------------------------------
MERCHANT_CATEGORIES = [
    # mcc,  category_name,          min_sar, max_sar, weight, bnpl_eligible, merchants
    ("5411", "Groceries",              15,    900,   0.24, False, ["Nakheel Hypermarket", "Bayt Al-Khair Market", "Dana Fresh"]),
    ("5812", "Restaurants & Cafes",    12,    450,   0.20, False, ["Qahwa House", "Mandi Palace", "Shawarma Corner"]),
    ("5541", "Fuel",                   30,    250,   0.12, False, ["Sahra Fuel Station", "Wadi Petrol"]),
    ("5651", "Fashion",                60,   2500,   0.08, True,  ["Abaya Lane", "Rimal Fashion", "Thobe Tailors"]),
    ("5732", "Electronics",           150,   9000,   0.06, True,  ["Najm Electronics", "Smart Hub"]),
    ("4511", "Travel & Airlines",     300,   7000,   0.04, True,  ["Sky Wings Travel", "Umrah Journeys"]),
    ("5912", "Pharmacy & Health",      10,    600,   0.07, False, ["Shifa Pharmacy", "Al-Afiya Clinic"]),
    ("4814", "Telecom & Utilities",    50,    800,   0.07, False, ["Ittisal Telecom", "Noor Utilities"]),
    ("9399", "Government Services",    20,   2000,   0.05, False, ["Government e-Services"]),
    ("7832", "Entertainment",          40,    700,   0.07, False, ["Boulevard Cinemas", "Fun Zone"]),
]
ATM_MCC = ("6011", "ATM Cash Withdrawal", 100, 5000)

CHANNELS = {"POS": 0.52, "APPLE_PAY": 0.22, "ECOM": 0.18, "ATM": 0.08}
DECLINE_REASONS = ["INSUFFICIENT_FUNDS", "INCORRECT_PIN", "LIMIT_EXCEEDED", "SUSPECTED_FRAUD", "EXPIRED_CARD"]
DECLINE_RATE = 0.04
BNPL_RATE = 0.35          # share of eligible purchases split into 4 instalments
BNPL_MIN_SAR = 300

# ---------------------------------------------------------------------------
# Saudi calendar shape: busy evenings, Friday-prayer dip, salary-day spike
# ---------------------------------------------------------------------------
HOUR_WEIGHTS = [0.3, 0.2, 0.1, 0.1, 0.1, 0.2, 0.5, 1.0, 1.6, 2.0, 2.2, 2.4,
                2.6, 2.4, 2.0, 2.0, 2.4, 3.0, 3.4, 3.8, 4.2, 4.4, 3.8, 2.4]


def hour_weights_for(day):
    """Hourly weights for a date; Friday (weekday 4) dips around Jumu'ah prayer."""
    weights = list(HOUR_WEIGHTS)
    if day.weekday() == 4:
        for h in (11, 12, 13):
            weights[h] *= 0.15
    return weights


def day_weight(day):
    """Salary is paid around the 27th, so spending spikes from the 27th to the 2nd."""
    w = 1.0
    if day.day >= 27 or day.day <= 2:
        w *= 1.6
    if day.weekday() == 5:      # Saturday
        w *= 1.15
    if day.weekday() == 4:      # Friday
        w *= 0.9
    return w


def random_timestamp_on(day, rng=random):
    hour = rng.choices(range(24), weights=hour_weights_for(day))[0]
    return datetime(day.year, day.month, day.day, hour, rng.randint(0, 59), rng.randint(0, 59),
                    rng.randint(0, 999999))


def fmt_ts(ts):
    return ts.strftime("%Y-%m-%dT%H:%M:%S.%f")


def build_instalments(ts, amount):
    """Split an amount into 4 monthly instalments (buy now, pay later)."""
    base = round(amount / 4, 2)
    amounts = [base, base, base, round(amount - 3 * base, 2)]
    return [
        {"instalment_no": i + 1,
         "due_date": (ts.date() + timedelta(days=30 * i)).isoformat(),
         "amount_sar": amounts[i]}
        for i in range(4)
    ]


def build_transaction(txn_id, ts, customer, card, rng=random):
    """Build one card transaction as a dict. Used by history and by the live producer."""
    channel = rng.choices(list(CHANNELS), weights=list(CHANNELS.values()))[0]
    if channel == "ATM":
        mcc, category, lo, hi = ATM_MCC
        merchant = f"WJ ATM {customer['city']}"
        bnpl_eligible = False
        amount = float(rng.choice(range(lo, hi + 1, 100)))
    else:
        # you can't buy fuel online
        options = [c for c in MERCHANT_CATEGORIES if not (channel == "ECOM" and c[0] == "5541")]
        cat = rng.choices(options, weights=[c[4] for c in options])[0]
        mcc, category, lo, hi, _, bnpl_eligible, merchants = cat
        merchant = rng.choice(merchants)
        # skewed amounts: most purchases are small
        amount = round(lo + (hi - lo) * (rng.random() ** 2.5), 2)

    if channel == "ECOM":
        merchant_city = "Online"
    elif rng.random() < 0.85:
        merchant_city = customer["city"]
    else:
        merchant_city = rng.choice(list(CITY_WEIGHTS))

    declined = rng.random() < DECLINE_RATE
    status = "DECLINED" if declined else "APPROVED"
    decline_reason = rng.choice(DECLINE_REASONS) if declined else None

    is_bnpl = (not declined and bnpl_eligible and amount >= BNPL_MIN_SAR
               and card["card_type"] != "PREPAID" and rng.random() < BNPL_RATE)
    instalments = build_instalments(ts, amount) if is_bnpl else []

    return {
        "txn_id": txn_id,
        "txn_timestamp": fmt_ts(ts),
        "card_id": card["card_id"],
        "customer_id": customer["customer_id"],
        "branch_id": customer["home_branch_id"],
        "channel": channel,
        "mcc_code": mcc,
        "merchant_name": merchant,
        "merchant_city": merchant_city,
        "amount_sar": amount,
        "currency": "SAR",
        "status": status,
        "decline_reason": decline_reason,
        "is_bnpl": int(is_bnpl),
        "instalments": json.dumps(instalments),
    }


def new_txn_id(ts, rng=random):
    return f"TXN-{ts.strftime('%Y%m%d')}-{rng.randint(10_000_000, 99_999_999)}"