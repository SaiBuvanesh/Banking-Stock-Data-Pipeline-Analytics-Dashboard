# Banking Sector Stock Intelligence Pipeline

> An end-to-end data engineering pipeline that pulls live market data from Yahoo Finance, processes it through a Medallion Architecture (Bronze → Silver → Gold), and pushes it to AWS S3 as Parquet for Power BI dashboarding.

---

## What This Project Does

Banks generate massive amounts of trading data every day. This pipeline automates the entire journey from raw API data to a business-intelligence-ready cloud Data Lake — no manual downloads, no broken Excel files.

Every day you run it, it:
- Pulls only the **missing** market data (incremental loading — not the full history again)
- Cleans and structures the raw prices
- Calculates technical indicators (RSI, MACD, Moving Averages, Volatility)
- Uploads everything to **AWS S3** as compressed Parquet files
- Power BI reads directly from S3 for the dashboard

---

## Tech Stack

| Layer | Tool |
|---|---|
| Data Source | Yahoo Finance API via `yfinance` |
| Data Processing | Python, Pandas, NumPy |
| Local Storage | SQLite (`bank_stocks.db`) |
| Cloud Storage | AWS S3 (Parquet via `boto3` + `pyarrow`) |
| Dashboard | Power BI (Python S3 connector) |

---

## Architecture

```
Yahoo Finance API
       │
       ▼
  extract.py ──► raw_stock_data        (Bronze Layer — SQLite)
       │
       ▼
 transform.py ──► processed_stock_prices (Silver Layer — SQLite)
       │
       ▼
 transform.py ──► stock_analytics       (Gold Layer   — SQLite)
       │
       ▼
  s3_export.py ──► AWS S3 Parquet Files
       │
       ▼
   Power BI Dashboard
```

Full architecture breakdown → [`ARCHITECTURE.md`](ARCHITECTURE.md)

---

## Banks Tracked

| Bank | NSE Ticker |
|---|---|
| State Bank of India | `SBIN.NS` |
| HDFC Bank | `HDFCBANK.NS` |
| ICICI Bank | `ICICIBANK.NS` |
| Axis Bank | `AXISBANK.NS` |
| Kotak Mahindra Bank | `KOTAKBANK.NS` |
| IndusInd Bank | `INDUSINDBK.NS` |
| Bank of Baroda | `BANKBARODA.NS` |
| Punjab National Bank | `PNB.NS` |
| IDFC First Bank | `IDFCFIRSTB.NS` |
| Federal Bank | `FEDERALBNK.NS` |
| AU Small Finance Bank | `AUBANK.NS` |
| Bandhan Bank | `BANDHANBNK.NS` |

---

## Setup

### 1. Clone and install dependencies
```bash
git clone https://github.com/yourusername/bankstock-pipeline.git
cd bankstock-pipeline

python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
```

### 2. Configure AWS credentials
Create a `.env` file in the root:
```env
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
AWS_REGION=ap-south-1
AWS_S3_BUCKET_NAME=your-bucket-name
```

### 3. Run the pipeline
```bash
python main.py
```

Or just double-click `run_pipeline.bat` on Windows.

---

## Project Structure

```
bankstock-pipeline/
├── config.py          # All settings — stocks, paths, AWS config
├── db.py              # Database schema — Medallion Architecture tables
├── extract.py         # Yahoo Finance → Bronze Layer (raw data)
├── transform.py       # Bronze → Silver (clean) → Gold (indicators)
├── s3_export.py       # SQLite → Parquet → AWS S3
├── main.py            # Pipeline orchestrator
├── run_pipeline.bat   # One-click daily refresh (Windows)
├── requirements.txt
├── docs/              # Technical documentation per file
│   ├── config.md
│   ├── db.md
│   ├── extract.md
│   ├── transform.md
│   ├── s3_export.md
│   └── main.md
├── DATA.md            # Full data dictionary (all columns explained)
├── ARCHITECTURE.md    # System design deep-dive
└── .gitignore
```

---

## Technical Indicators Computed

| Indicator | Window | What It Tells You |
|---|---|---|
| Daily Return | 1-day | % price change from previous close |
| MA50 | 50-day rolling | Medium-term trend direction |
| MA200 | 200-day rolling | Long-term trend direction |
| Volatility | 20-day annualized | How risky / erratic the stock is |
| RSI | 14-day | Overbought (>70) or oversold (<30) |
| MACD | 12/26-day EMA diff | Momentum and trend strength |

---

## Data Dictionary

Full schema of every table and column → [`DATA.md`](DATA.md)
