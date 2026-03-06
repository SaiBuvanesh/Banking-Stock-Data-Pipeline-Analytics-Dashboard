# System Architecture

## Overview

This pipeline follows a **Medallion Architecture** — a layered data engineering pattern where data moves through Bronze → Silver → Gold stages, with each layer adding progressively more structure, quality, and analytical value.

---

## Full Pipeline Flow

```
┌─────────────────────────────────────────────────────────┐
│                   Yahoo Finance API                      │
│              (yfinance Python library)                   │
└──────────────────────────┬──────────────────────────────┘
                           │  OHLCV data per ticker
                           ▼
┌─────────────────────────────────────────────────────────┐
│                   extract.py                            │
│  • Checks last ingested date (MAX(date) per symbol)     │
│  • Fetches only missing data (incremental loading)      │
│  • Normalises column names and date formats             │
│  • Upserts via temp table → ON CONFLICT DO UPDATE       │
└──────────────────────────┬──────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│              SQLite — Bronze Layer                      │
│              Table: raw_stock_data                      │
│  • Unmodified API response                              │
│  • Includes data_ingestion_timestamp (audit trail)      │
│  • Primary Key: (date, stock_symbol)                    │
└──────────────────────────┬──────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│              transform.py — Silver Pass                 │
│  • Drops duplicates                                     │
│  • Forward fill + backward fill on missing prices       │
│  • Volume NaN → 0                                       │
│  • Sort chronologically                                 │
└──────────────────────────┬──────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│              SQLite — Silver Layer                      │
│         Table: processed_stock_prices                   │
│  • Clean OHLCV only                                     │
│  • No nulls, no duplicates, sorted by date              │
└──────────────────────────┬──────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│              transform.py — Gold Pass                   │
│  • Daily Return     → pct_change()                      │
│  • MA50 / MA200     → rolling(50/200).mean()            │
│  • Volatility       → rolling(20).std() × √252          │
│  • RSI              → 14-day avg gain/loss ratio        │
│  • MACD             → EMA(12) − EMA(26)                 │
│  • Drops rows with NaN MA200 (< 200 days of data)       │
└──────────────────────────┬──────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│               SQLite — Gold Layer                       │
│               Table: stock_analytics                    │
│  • Fully enriched, analytics-ready dataset              │
│  • Powers all Power BI chart visuals                    │
└──────────────────────────┬──────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│                   s3_export.py                          │
│  • Reads each table from SQLite via pandas              │
│  • Serialises to Parquet (PyArrow engine, ~5× smaller)  │
│  • Uploads to S3 via boto3 with structured key paths    │
└──────────────────────────┬──────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│               AWS S3 — Data Lake                        │
│   bucket/data-lake/                                     │
│   ├── dimensions/stocks/data.parquet                    │
│   ├── bronze_layer/raw_stock_data/data.parquet          │
│   ├── silver_layer/processed_stock_prices/data.parquet  │
│   └── gold_layer/stock_analytics/data.parquet           │
└──────────────────────────┬──────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│               Power BI Dashboard                        │
│  • Python script source (s3fs + pandas.read_parquet)    │
│  • Star Schema: stocks → analytics / prices             │
│  • Visuals: Price trends, RSI, MACD, Volatility         │
└─────────────────────────────────────────────────────────┘
```

---

## Database Design (Star Schema)

```
             ┌─────────────────┐
             │     stocks      │  ← Dimension Table
             │─────────────────│
             │ stock_symbol PK │
             │ company_name    │
             │ sector          │
             │ country         │
             └────────┬────────┘
                      │ 1
          ┌───────────┼───────────┐
          │ *         │ *         │ *
┌─────────┴──────┐  ┌─┴──────────────┐  ┌──────────────────┐
│ raw_stock_data │  │processed_stock │  │ stock_analytics  │
│────────────────│  │_prices         │  │──────────────────│
│ date           │  │────────────────│  │ date             │
│ stock_symbol FK│  │ date           │  │ stock_symbol FK  │
│ open_price     │  │ stock_symbol FK│  │ daily_return     │
│ high_price     │  │ open_price     │  │ ma50             │
│ low_price      │  │ close_price    │  │ ma200            │
│ close_price    │  │ high_price     │  │ volatility       │
│ adjusted_close │  │ low_price      │  │ rsi              │
│ volume         │  │ volume         │  │ macd             │
│ ingested_at    │  └────────────────┘  └──────────────────┘
└────────────────┘
   Bronze Layer       Silver Layer           Gold Layer
```

---

## Key Engineering Decisions

### 1. Incremental Loading over Full Refresh
On every run, `extract.py` checks `MAX(date)` per symbol before calling the API. This means only 1 new day of data is fetched after the initial load — not 5 years every time. At scale this saves thousands of API calls per day.

### 2. Upsert Pattern (Temp Table → INSERT ON CONFLICT)
A direct `INSERT` would fail on duplicate `(date, symbol)` pairs. A direct `UPDATE` would require the row to already exist. The **two-step temp table + ON CONFLICT DO UPDATE** handles both cases: new rows are inserted, existing rows are updated. This makes every pipeline run fully idempotent — safe to run multiple times.

### 3. Parquet over CSV for the Data Lake
Parquet is a columnar binary format. For a dataset like this (high row count, low column count per query), Parquet reads 5–10× faster and compresses 5× smaller than CSV. Power BI and AWS Athena both read it natively.

### 4. SQLite as an Intermediate Store
SQLite provides a free, zero-configuration relational database that sits between raw API data and the cloud upload. It enables SQL querying, primary key constraints, foreign key integrity, and fast `pandas.read_sql_query()` reads. In production, this would be replaced by PostgreSQL on AWS RDS.

### 5. Modular Pipeline Structure
Each stage is a standalone Python file with a single public `run_*()` function. This means:
- Each stage can be run and tested independently
- Failures in one stage don't break others
- Swapping out S3 for Azure Blob requires only changing `s3_export.py`

---

## Data Flow Summary

```
API Response → Bronze (raw) → Silver (clean) → Gold (enriched) → S3 Parquet → Power BI
```
