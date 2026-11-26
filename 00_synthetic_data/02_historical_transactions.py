"""Generate 6 months of historical card transactions -> data/historical_transactions.csv.

Every transaction references a real customer, one of that customer's cards and a real MCC,
so the data joins cleanly downstream.
"""
import os
import random
from datetime import date, timedelta

import pandas as pd

from common import DATA_DIR, build_transaction, day_weight, new_txn_id, random_timestamp_on


def generate_historical_transactions(num_txns=20000, days_back=180, seed=7):
    rng = random.Random(seed)
    customers = pd.read_csv(os.path.join(DATA_DIR, "customers.csv"), dtype=str).to_dict("records")
    cards = pd.read_csv(os.path.join(DATA_DIR, "cards.csv"), dtype=str)
    cards_by_customer = {cid: g.to_dict("records") for cid, g in cards.groupby("customer_id")}

    # a few heavy users, many light ones -> realistic segments in customer 360
    activity = [rng.paretovariate(1.6) for _ in customers]

    end = date.today() - timedelta(days=1)
    days = [end - timedelta(days=i) for i in range(days_back)]
    weights = [day_weight(d) for d in days]

    rows, seen = [], set()
    print(f"Generating {num_txns} transactions from {days[-1]} to {end}")
    while len(rows) < num_txns:
        day = rng.choices(days, weights=weights)[0]
        ts = random_timestamp_on(day, rng)
        customer = rng.choices(customers, weights=activity)[0]
        own_cards = cards_by_customer[customer["customer_id"]]
        debit = [c for c in own_cards if c["card_type"] == "MADA_DEBIT"]
        other = [c for c in own_cards if c["card_type"] != "MADA_DEBIT"]
        card = rng.choice(other) if other and rng.random() < 0.35 else debit[0]
        txn_id = new_txn_id(ts, rng)
        if txn_id in seen:
            continue
        seen.add(txn_id)
        rows.append(build_transaction(txn_id, ts, customer, card, rng))

    df = pd.DataFrame(rows).sort_values("txn_timestamp")
    df.to_csv(os.path.join(DATA_DIR, "historical_transactions.csv"), index=False)
    print(f"historical_transactions: {len(df)} rows | declined: {(df.status == 'DECLINED').sum()} "
          f"| BNPL: {df.is_bnpl.sum()}")


if __name__ == "__main__":
    generate_historical_transactions()