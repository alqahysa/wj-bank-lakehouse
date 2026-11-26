"""Live card-transaction producer: sends one transaction to Azure Event Hub every N seconds.

Plays the role of the card switch / POS network. Reads EVENTHUB_CONNECTION_STRING and
EVENTHUB_NAME from a .env file in this folder.

    python 05_stream_transactions.py              # one transaction every 2 seconds, until Ctrl+C
    python 05_stream_transactions.py --max 20     # stop after 20 transactions
"""
import argparse
import json
import os
import random
import time
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
from azure.eventhub import EventData, EventHubProducerClient
from dotenv import load_dotenv

from common import DATA_DIR, build_transaction, new_txn_id

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
EVENTHUB_CONNECTION_STRING = os.getenv("EVENTHUB_CONNECTION_STRING")
EVENTHUB_NAME = os.getenv("EVENTHUB_NAME")
RIYADH = ZoneInfo("Asia/Riyadh")

customers = pd.read_csv(os.path.join(DATA_DIR, "customers.csv"), dtype=str).to_dict("records")
cards = pd.read_csv(os.path.join(DATA_DIR, "cards.csv"), dtype=str)
CARDS_BY_CUSTOMER = {cid: g.to_dict("records") for cid, g in cards.groupby("customer_id")}


def generate_live_transaction():
    ts = datetime.now(RIYADH).replace(tzinfo=None)          # Riyadh local time, no offset
    customer = random.choice(customers)
    card = random.choice(CARDS_BY_CUSTOMER[customer["customer_id"]])
    txn = build_transaction(new_txn_id(ts), ts, customer, card)
    txn["instalments"] = json.loads(txn["instalments"])     # send a real JSON array in the event
    return txn


def stream_to_eventhub(interval_seconds=2.0, max_txns=None):
    if not EVENTHUB_CONNECTION_STRING or not EVENTHUB_NAME:
        raise SystemExit("Set EVENTHUB_CONNECTION_STRING and EVENTHUB_NAME in 00_synthetic_data/.env")
    producer = EventHubProducerClient.from_connection_string(
        conn_str=EVENTHUB_CONNECTION_STRING, eventhub_name=EVENTHUB_NAME)
    print(f"Streaming to Event Hub '{EVENTHUB_NAME}' every {interval_seconds}s. Ctrl+C to stop.")
    sent = 0
    try:
        while True:
            txn = generate_live_transaction()
            batch = producer.create_batch()
            batch.add(EventData(json.dumps(txn, ensure_ascii=False)))
            producer.send_batch(batch)
            sent += 1
            print(f"[{sent}] {txn['txn_id']} | {txn['channel']:<9} | {txn['merchant_name']:<22} "
                  f"| SAR {txn['amount_sar']:>9,.2f} | {txn['status']}{' | BNPL' if txn['is_bnpl'] else ''}")
            if max_txns and sent >= max_txns:
                break
            time.sleep(interval_seconds)
    except KeyboardInterrupt:
        print("\nStopped")
    finally:
        producer.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--interval", type=float, default=2.0, help="seconds between transactions")
    parser.add_argument("--max", type=int, default=None, help="stop after this many transactions")
    args = parser.parse_args()
    stream_to_eventhub(args.interval, args.max)