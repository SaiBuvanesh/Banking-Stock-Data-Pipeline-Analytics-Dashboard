# Banking Sector Stock Intelligence - Data Dictionary

This document details the structure, contents, and transformation layers of the datasets processed by the data engineering pipeline. 
The pipeline follows a cloud-native Medallion Architecture, saving data in highly optimized Parquet format to an AWS S3 Data Lake.

## 1. Dimension Tables 

These tables provide descriptive attributes and context for facts in the data model.

### `stocks` (Dimensions Directory)
Provides dimensional data mapping the raw ticker symbol to easily identifiable real-world bank names and properties.

| Column Name | Data Type | Description |
|---|---|---|
| `stock_symbol` | String (Primary Key) | The exact Yahoo Finance ticker symbol (e.g., `SBIN.NS`). |
| `company_name` | String | Full human-readable name of the bank (e.g., `State Bank of India`). |
| `sector` | String | Market sector assignment (defaults to `Banking`). |
| `country` | String | Origin country of the bank's main stock exchange (e.g., `India`, `Jordan`). |

---

## 2. Fact Tables (Medallion Layers)

These tables contain the time-series financial metrics, built incrementally block-by-block.

### `raw_stock_data` (Bronze Layer)
The original, unmodified data fetched directly from the Yahoo Finance API. Contains potentially missing or unstandardized fields.

| Column Name | Data Type | Description |
|---|---|---|
| `date` | String | Trading date (Format: `YYYY-MM-DD`). |
| `stock_symbol` | String | Yahoo Finance ticker symbol. Links to the `stocks` table. |
| `open_price` | Float | The initial stock price recorded when the market opened. |
| `high_price` | Float | The highest stock price reached that trading day. |
| `low_price` | Float | The lowest stock price reached that trading day. |
| `close_price` | Float | The final stock price when the market closed. |
| `adjusted_close`| Float | The closing price automatically adjusted for splits and dividend distributions. |
| `volume` | Integer | Total number of shares traded during the day. |
| `data_ingestion_timestamp` | String | The exact system time the pipeline pulled this specific row into the Bronze database. |

### `processed_stock_prices` (Silver Layer)
Data cleaned using Forward/Backward-filling techniques. Missing prices and unrecorded `volume` entries are computationally patched to prevent data gaps during charting.

| Column Name | Data Type | Description |
|---|---|---|
| `date` | String | Trading date (Format: `YYYY-MM-DD`). |
| `stock_symbol` | String | Yahoo Finance ticker symbol. Links to `stocks`. |
| `open_price` | Float | Cleaned Opening Price. |
| `high_price` | Float | Cleaned High Price. |
| `low_price` | Float | Cleaned Low Price. |
| `close_price` | Float | Cleaned Closing Price. |
| `volume` | Integer | Cleaned Trading Volume (Missing defaults to 0). |

### `stock_analytics` (Gold Layer)
Contains entirely computed/enriched financial trading indicators derived strictly from the Silver Layer. Critical for deep business intelligence dashboards.

| Column Name | Data Type | Description |
|---|---|---|
| `date` | String | Trading date (Format: `YYYY-MM-DD`). |
| `stock_symbol` | String | Yahoo Finance ticker symbol. Links to `stocks`. |
| `daily_return` | Float | Percentage change in daily close price compared to the previous trading session. |
| `ma50` | Float | 50-Day Moving Average. Smooths out short-term fluctuations to highlight midterm trends. |
| `ma200` | Float | 200-Day Moving Average. Major long-term trend indicator. |
| `volatility` | Float | 20-Day annualized historically rolling standard deviation (How drastically the stock price swings). |
| `rsi` | Float | Relative Strength Index. A momentum oscillator measuring the speed and change of price movements (0 to 100). |
| `macd` | Float | Moving Average Convergence Divergence. Relationship between the 12-day and 26-day EMA (Momentum trend-following). |

## Power BI Integration & Modeling Instructions

1. **Star Schema Setup**: 
   - Connect the `stocks` dimension table to `raw_stock_data`, `processed_stock_prices`, and `stock_analytics` in a **1-to-Many** relationship based exclusively on the `stock_symbol` column.
2. **Filtering Context**: 
   - When building dashboard visuals, always use `company_name` directly from the `stocks` dimension table as your primary slicer/filter. Doing this will successfully dynamically filter the Silver prices and Gold analytics metrics simultaneously.
