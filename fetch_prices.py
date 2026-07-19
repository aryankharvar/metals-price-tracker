"""
fetch_prices.py

Pulls the latest daily closing price for a set of metals futures tickers
and appends them to a local SQLite database. Designed to be run once a
day by a GitHub Actions cron job, but works fine run manually too.

Requires: yfinance, pandas, sqlalchemy
    pip install yfinance pandas sqlalchemy
"""

import datetime as dt
import sqlite3
from pathlib import Path

import pandas as pd
import yfinance as yf

DB_PATH = Path(__file__).parent / "metal_prices.db"

# Ticker -> friendly name. Add/remove tickers here as needed.
TICKERS = {
    "HG=F": "Copper",
    "PL=F": "Platinum",
    "PA=F": "Palladium",
    "GC=F": "Gold",
}


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


def fetch_latest_prices() -> pd.DataFrame:
    """Fetch the most recent daily close for each ticker."""
    rows = []
    for ticker, name in TICKERS.items():
        # period="5d" as a small buffer in case today's session hasn't closed yet
        # (weekends, holidays) — we just take the most recent available row.
        hist = yf.Ticker(ticker).history(period="5d", interval="1d")
        if hist.empty:
            print(f"WARNING: no data returned for {ticker} ({name})")
            continue

        last_row = hist.tail(1)
        price_date = last_row.index[0].date()
        close_price = float(last_row["Close"].iloc[0])

        rows.append(
            {
                "ticker": ticker,
                "metal_name": name,
                "price_date": price_date.isoformat(),
                "close_price": round(close_price, 4),
            }
        )
    return pd.DataFrame(rows)


def save_to_db(df: pd.DataFrame, conn: sqlite3.Connection) -> int:
    """Insert rows, skipping any (ticker, price_date) already stored. Returns rows inserted."""
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
            # Row for this ticker/date already exists — expected on re-runs, not an error.
            pass
    conn.commit()
    return inserted


def main():
    conn = sqlite3.connect(DB_PATH)
    init_db(conn)

    df = fetch_latest_prices()
    print(df.head())
    if df.empty:
        print("No price data fetched — exiting without writing to DB.")
        return

    inserted = save_to_db(df, conn)
    print(f"[{dt.datetime.now().isoformat()}] Fetched {len(df)} rows, inserted {inserted} new rows.")
    print(df.to_string(index=False))

    conn.close()


if __name__ == "__main__":
    main()
