# 📈 Live Metals Price Tracker

An automated, self-updating data pipeline tracking daily copper, platinum, palladium, and gold prices — built to demonstrate end-to-end ownership of a live data product, not just a one-time analysis of a static file.

🔗 **Live Dashboard:** [metals-price-tracker.streamlit.app](https://metals-price-tracker.streamlit.app/)

![Daily Metal Price Fetch](https://github.com/aryankharvar/metals-price-tracker/actions/workflows/daily_fetch.yml/badge.svg)

---

## 📊 Overview

Unlike a typical portfolio project built from a downloaded CSV, this pipeline pulls **real market data every day on its own**, stores a growing historical record, and serves a dashboard that refreshes automatically — no manual export, no manual re-upload, no manual refresh click.

```
GitHub Actions (daily cron)
        │  pulls latest prices via yfinance
        ▼
   fetch_prices.py
        │  writes to SQLite, dedups on (ticker, date)
        ▼
   metal_prices.db  ──── committed back to the repo daily
        │
        ▼
   SQL views (window functions, CTEs)
        │
        ▼
   Streamlit dashboard  ──── auto-redeploys on every new commit
```

## 🛠️ Tech Stack

- **Data source:** Yahoo Finance futures tickers (`HG=F` Copper, `PL=F` Platinum, `PA=F` Palladium, `GC=F` Gold) via `yfinance`
- **Language:** Python (Pandas)
- **Database:** SQLite, with `UNIQUE(ticker, price_date)` constraint to make re-runs safe
- **SQL:** Window functions (`RANK() OVER PARTITION BY`, `LAG()`), CTEs, and views for reusable analysis logic
- **Automation:** GitHub Actions (scheduled cron, weekdays after market close)
- **Dashboard:** Streamlit (Community Cloud), Plotly for charts

## 📁 Repository Structure

```
metals-price-tracker/
├── .github/workflows/
│   └── daily_fetch.yml        # scheduled daily automation
├── fetch_prices.py             # daily incremental pull + view creation
├── backfill_history.py         # one-time historical backfill
├── views.sql                   # reusable SQL views (window functions, CTEs)
├── app.py                      # Streamlit dashboard
├── metal_prices.db             # SQLite DB, updated daily by the pipeline
├── requirements.txt
└── README.md
```

## 🧩 What the SQL Layer Does

All analysis is defined as views on top of the raw `metal_prices` table, so the logic runs once and stays reusable rather than being copy-pasted across scripts:

| View | Technique | Purpose |
|---|---|---|
| `latest_prices` | Correlated subquery | Most recent price per metal |
| `daily_pct_change` | `LAG() OVER (PARTITION BY ...)` | Day-over-day % change |
| `rolling_averages` | Window frame (`ROWS BETWEEN ... PRECEDING`) | 7-day and 30-day rolling averages |
| `weekly_volatility` | CTE + `RANK() OVER (...)` | Ranks metals by this week's price range |

## 📈 Dashboard Features

- **Live price cards** with day-over-day % change
- **Price Trend tab** — daily close vs. 7-day and 30-day rolling averages, per metal
- **Performance Comparison tab** — all four metals indexed to 100 at the start of tracking, so relative moves are comparable regardless of raw price scale
- **Correlation & Risk tab** — correlation heatmap between metals, plus rolling 30-day volatility

## 🚀 How It Stays "Live"

1. A GitHub Actions workflow runs on a weekday cron schedule, executes `fetch_prices.py`, and commits the updated `metal_prices.db` back to this repo
2. Streamlit Community Cloud watches this repo and automatically redeploys the app whenever it detects a new commit
3. The dashboard's SQL views recompute directly against the latest data on every page load — there's no separate caching or ETL step between "new data lands" and "dashboard reflects it"

## 🔍 Sample Insight

The correlation heatmap shows gold, platinum, and palladium moving closely together (correlation typically 0.9+), while copper — more tied to industrial demand than to store-of-value demand — tends to diverge from the precious-metals cluster during risk-off periods.

## 🏗️ How to Reproduce

```bash
git clone https://github.com/aryankharvar/metals-price-tracker.git
cd metals-price-tracker
pip install -r requirements.txt

# one-time historical backfill
python backfill_history.py

# manual daily pull (GitHub Actions runs this automatically going forward)
python fetch_prices.py

# run the dashboard locally
streamlit run app.py
```

## 📌 Future Improvements

- Extend the schema to store Open/High/Low (not just Close) to enable candlestick charts
- Add nickel and cobalt once a reliable free data source is identified (currently limited by LME data typically being paywalled)
- Add a simple anomaly flag for days with unusually large price moves


# 👨‍💻 Author

**Aryan Kharvar**

**M.Sc. Computational Sciences**

Data Analytics | Business Intelligence | Power BI | SQL | Python

💼 LinkedIn: [Aryan Kharvar](https://www.linkedin.com/in/aryankharvar)
