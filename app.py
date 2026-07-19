"""
app.py

Live dashboard for the metals price tracker. Reads directly from
metal_prices.db (and the views defined in views.sql). Deployed on
Streamlit Community Cloud, this redeploys automatically whenever the
GitHub Actions job commits a new day's data — no manual refresh needed.

Requires: streamlit, pandas, plotly
    pip install streamlit pandas plotly
Run locally with: streamlit run app.py
"""

import sqlite3
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

DB_PATH = Path(__file__).parent / "metal_prices.db"

st.set_page_config(page_title="Metals Price Tracker", layout="wide")


@st.cache_resource
def get_connection():
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def load(query: str) -> pd.DataFrame:
    return pd.read_sql(query, get_connection())


st.title("📈 Live Metals Price Tracker")
st.caption("Auto-updated daily via GitHub Actions — copper, platinum, palladium & gold")

# ---- Top row: latest price + day-over-day change cards ----
latest = load("SELECT * FROM latest_prices")
changes = load("""
    SELECT metal_name, pct_change
    FROM daily_pct_change
    WHERE price_date = (SELECT MAX(price_date) FROM metal_prices)
""")
merged = latest.merge(changes, on="metal_name", how="left")

cols = st.columns(len(merged))
for col, (_, row) in zip(cols, merged.iterrows()):
    delta = f"{row['pct_change']:+.2f}%" if pd.notna(row["pct_change"]) else "—"
    col.metric(label=row["metal_name"], value=f"${row['close_price']:,.2f}", delta=delta)

st.caption(f"Last updated: {latest['price_date'].max() if not latest.empty else 'no data yet'}")

st.divider()

# ---- Rolling average trend chart / performance comparison / correlation & risk ----
all_prices = load("SELECT metal_name, price_date, close_price FROM metal_prices ORDER BY price_date")

tab1, tab2, tab3 = st.tabs(["📈 Price Trend", "⚖️ Performance Comparison", "🔗 Correlation & Risk"])

with tab1:
    st.subheader("Price Trend & Rolling Averages")
    rolling = load("SELECT * FROM rolling_averages ORDER BY price_date")

    if not rolling.empty:
        metal_choice = st.selectbox("Select metal", rolling["metal_name"].unique())
        subset = rolling[rolling["metal_name"] == metal_choice]

        fig = px.line(
            subset,
            x="price_date",
            y=["close_price", "rolling_7d_avg", "rolling_30d_avg"],
            labels={"value": "Price (USD)", "price_date": "Date", "variable": "Series"},
            title=f"{metal_choice} — Daily Close vs. Rolling Averages",
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No price history yet — check back after the pipeline has run a few times.")

with tab2:
    st.subheader("Normalized Performance Comparison (Indexed to 100)")
    st.caption("Lets you compare metals on the same scale regardless of their raw price — a $5 copper move and a $20 gold move aren't directly comparable in dollar terms, but are here.")

    if not all_prices.empty:
        wide = all_prices.pivot(index="price_date", columns="metal_name", values="close_price")
        normalized = (wide / wide.iloc[0] * 100).reset_index()
        normalized_long = normalized.melt(id_vars="price_date", var_name="metal_name", value_name="indexed_price")

        fig2 = px.line(
            normalized_long,
            x="price_date",
            y="indexed_price",
            color="metal_name",
            labels={"indexed_price": "Indexed Price (start = 100)", "price_date": "Date"},
            title="Relative Performance Since Tracking Began",
        )
        fig2.add_hline(y=100, line_dash="dot", line_color="gray")
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("Not enough data yet for a performance comparison.")

with tab3:
    st.subheader("Correlation Between Metals")
    st.caption("Do these metals move together? Values close to 1.0 mean they tend to rise and fall in tandem.")

    if not all_prices.empty and all_prices["metal_name"].nunique() > 1:
        wide = all_prices.pivot(index="price_date", columns="metal_name", values="close_price")
        corr = wide.corr().round(2)

        fig3 = px.imshow(
            corr,
            text_auto=True,
            color_continuous_scale="RdBu_r",
            zmin=-1,
            zmax=1,
            title="Price Correlation Matrix",
        )
        st.plotly_chart(fig3, use_container_width=True)

        st.subheader("Rolling 30-Day Volatility")
        st.caption("Standard deviation of daily % price changes — higher means the metal has been swinging more sharply recently.")

        pct_change = wide.pct_change()
        rolling_vol = (pct_change.rolling(30).std() * 100).reset_index()
        vol_long = rolling_vol.melt(id_vars="price_date", var_name="metal_name", value_name="volatility_pct").dropna()

        if not vol_long.empty:
            fig4 = px.line(
                vol_long,
                x="price_date",
                y="volatility_pct",
                color="metal_name",
                labels={"volatility_pct": "30-Day Rolling Volatility (%)", "price_date": "Date"},
            )
            st.plotly_chart(fig4, use_container_width=True)
        else:
            st.info("Need at least 30 days of history for the rolling volatility chart.")
    else:
        st.info("Need at least two metals with overlapping history to compute correlation.")

st.divider()

# ---- Weekly volatility ranking ----
st.subheader("This Week's Volatility Ranking")
volatility = load("SELECT * FROM weekly_volatility ORDER BY volatility_rank")
st.dataframe(volatility, use_container_width=True, hide_index=True)

st.divider()
st.caption(
    "Data source: Yahoo Finance futures tickers (HG=F, PL=F, PA=F, GC=F) via yfinance. "
    "Pipeline: GitHub Actions (daily) → SQLite → Streamlit."
)