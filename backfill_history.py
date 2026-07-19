"""
backfill_history.py

One-time script to populate metal_prices.db with historical data,
so you don't have to wait days for the daily job to accumulate rows.

Run this ONCE, then let fetch_prices.py handle daily updates going forward.

Requires: yfinance, pandas
    pip install yfinance pandas
"""

import sqlite3
from pathlib import Path

import pandas as pd
import yfinance as yf

DB_PATH = Path(__file__).parent / "metal_prices.db"

TICKERS = {
    "HG=F": "Copper",
    "PL=F": "Platinum",
    "PA=F": "Palladium",
    "GC=F": "Gold",
}

# How far back to backfill. yfinance accepts: 1mo, 3mo, 6mo, 1y, 2y, 5y, max
BACKFILL_PERIOD = "6mo"


def init_db(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS metal_prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            metal_name TEXT NOT NULL,
            price_date DATE NOT NULL,
            close_price REAL NOT NULL,
            fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(ticker, price_date)
        )
        """
    )
    conn.commit()


def fetch_history(ticker: str, name: str) -> pd.DataFrame:
    hist = yf.Ticker(ticker).history(period=BACKFILL_PERIOD, interval="1d")
    if hist.empty:
        print(f"WARNING: no historical data returned for {ticker} ({name})")
        return pd.DataFrame()

    df = hist.reset_index()[["Date", "Close"]].copy()
    df["ticker"] = ticker
    df["metal_name"] = name
    df["price_date"] = df["Date"].dt.date.astype(str)
    df["close_price"] = df["Close"].round(4)
    return df[["ticker", "metal_name", "price_date", "close_price"]]


def save_to_db(df: pd.DataFrame, conn: sqlite3.Connection) -> int:
    inserted = 0
    for _, row in df.iterrows():
        try:
            conn.execute(
                """
                INSERT INTO metal_prices (ticker, metal_name, price_date, close_price)
                VALUES (?, ?, ?, ?)
                """,
                (row["ticker"], row["metal_name"], row["price_date"], row["close_price"]),
            )
            inserted += 1
        except sqlite3.IntegrityError:
            pass  # already have this ticker/date, skip
    conn.commit()
    return inserted


def main():
    conn = sqlite3.connect(DB_PATH)
    init_db(conn)

    total_inserted = 0
    for ticker, name in TICKERS.items():
        df = fetch_history(ticker, name)
        if df.empty:
            continue
        inserted = save_to_db(df, conn)
        total_inserted += inserted
        print(f"{name} ({ticker}): {len(df)} rows fetched, {inserted} new rows inserted")

    print(f"\nBackfill complete. Total new rows: {total_inserted}")

    # quick sanity check
    summary = pd.read_sql(
        "SELECT metal_name, COUNT(*) AS rows, MIN(price_date) AS earliest, MAX(price_date) AS latest "
        "FROM metal_prices GROUP BY metal_name",
        conn,
    )
    print("\nCurrent DB contents:")
    print(summary.to_string(index=False))

    conn.close()


if __name__ == "__main__":
    main()
