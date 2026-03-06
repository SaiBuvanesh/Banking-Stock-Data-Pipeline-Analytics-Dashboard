# extract.py — Data Extraction (Bronze Layer)

Pulls stock price data from Yahoo Finance and stores it raw in the Bronze layer. The key design here is **incremental loading** — on every run, it only fetches data that doesn't already exist in the database.

---

## How It Works

### Step 1 — Check the Last Stored Date
```python
query = f"SELECT MAX(date) FROM raw_stock_data WHERE stock_symbol = '{symbol}';"
```
Before making any API call, the script checks what's already in the database. `MAX(date)` returns the most recent date stored for that bank.

- **First run ever:** Returns `None` → falls back to `DEFAULT_START_DATE = "2020-01-01"` → downloads 5 years of data.
- **Every run after that:** Returns yesterday's date → downloads only 1 new day.

This is called **incremental ingestion** — a fundamental data engineering pattern that avoids re-downloading data you already have.

---

### Step 2 — Call Yahoo Finance API
```python
ticker = yf.Ticker(symbol)
df = ticker.history(start=start_date)
```
`yf.Ticker(symbol)` wraps the Yahoo Finance API for a specific stock. `.history(start=start_date)` fetches OHLCV data from the given date to today and returns a Pandas DataFrame.

The entire thing is wrapped in `try/except` — if one bank's API call fails (invalid symbol, network timeout, rate limit), the error is logged and the loop continues with the next bank. One failure doesn't kill the whole run.

---

### Step 3 — Normalize the Data
```python
df.reset_index(inplace=True)
df['Date'] = pd.to_datetime(df['Date']).dt.strftime('%Y-%m-%d')
df['stock_symbol'] = symbol
df['data_ingestion_timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
```
Yahoo Finance returns `Date` as the DataFrame index. `reset_index()` converts it to a regular column. Then:
- Date gets standardized to `YYYY-MM-DD` (ISO 8601) for consistent SQL storage
- `stock_symbol` is added to tag each row with its source
- `data_ingestion_timestamp` records when this batch was pulled (audit trail)

Column names are renamed from `Open/Close/High` → `open_price/close_price/high_price` to match the SQL schema.

---

### Step 4 — Upsert to Bronze Layer
```python
df.to_sql(temp_table, con=conn, if_exists='replace', index=False)

INSERT INTO raw_stock_data ...
SELECT ... FROM {temp_table}
ON CONFLICT(date, stock_symbol) DO UPDATE SET ...
```
A two-step pattern:

1. Dump the DataFrame into a **temporary SQLite table** using `pandas.to_sql()` — the fastest way to bulk load data.
2. Use `INSERT ... ON CONFLICT DO UPDATE` to move data from the temp table into the real `raw_stock_data` table.

`ON CONFLICT DO UPDATE` handles both cases safely:
- Row doesn't exist → **inserted**
- Row exists (e.g., pipeline ran twice today) → **updated** with latest values

The temp table is dropped immediately after. This entire pattern is called an **upsert** — and it makes the pipeline fully idempotent (safe to run multiple times with the same result).

---

## Technical Concepts Used

| Concept | Where |
|---|---|
| Incremental ingestion | `MAX(date)` check before API call |
| Idempotency | `ON CONFLICT DO UPDATE` |
| Bulk loading | `pandas.to_sql()` to temp table |
| Error isolation | `try/except` per symbol |
| Audit trail | `data_ingestion_timestamp` column |
