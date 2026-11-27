"""Load the CSVs in data/ into Azure SQL without a SQL client.

Reads SQL_SERVER, SQL_USER and SQL_PASSWORD from .env. Run after sql/01_create_tables.sql.
Inserts in batches of 1,000 rows; the full load takes a few minutes over the internet.
"""
import os

import pandas as pd
import pymssql
from dotenv import load_dotenv

from common import DATA_DIR

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

# load order respects the logical relationships (dims first)
FILES = [
    ("branches", "branches.csv"),
    ("merchant_categories", "merchant_categories.csv"),
    ("customers", "customers.csv"),
    ("cards", "cards.csv"),
    ("historical_transactions", "historical_transactions.csv"),
    ("complaints", "complaints.csv"),
]
BATCH = 1000


def main():
    conn = pymssql.connect(
        server=os.environ["SQL_SERVER"],
        user=os.environ["SQL_USER"],
        password=os.environ["SQL_PASSWORD"],
        database=os.environ.get("SQL_DATABASE", "bank_ops"),
        charset="UTF-8",
    )
    cur = conn.cursor()
    for table, file in FILES:
        df = pd.read_csv(os.path.join(DATA_DIR, file), dtype=str, keep_default_na=False)
        rows = [tuple(v if v != "" else None for v in r) for r in df.itertuples(index=False)]
        cols = ", ".join(df.columns)
        marks = ", ".join(["%s"] * len(df.columns))
        sql = f"INSERT INTO dbo.{table} ({cols}) VALUES ({marks})"
        for i in range(0, len(rows), BATCH):
            cur.executemany(sql, rows[i:i + BATCH])
            conn.commit()
        print(f"{table}: {len(rows)} rows")
    conn.close()


if __name__ == "__main__":
    main()