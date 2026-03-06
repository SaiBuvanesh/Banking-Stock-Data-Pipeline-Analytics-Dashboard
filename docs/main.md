# main.py — Pipeline Orchestrator

The entry point. No logic lives here — it just imports and calls the four pipeline stages in order. Think of it as the conductor: each module knows its job, `main.py` tells them when to go.

---

## Execution Flow

```
main.py
  │
  ├── [1/4] db.py          → Create tables (if not exist), load bank dimension
  ├── [2/4] extract.py     → Yahoo Finance API → Bronze Layer (raw_stock_data)
  ├── [3/4] transform.py   → Bronze → Silver (clean), Silver → Gold (indicators)
  └── [4/4] s3_export.py   → SQLite tables → Parquet files → AWS S3
```

---

## Stage Breakdown

### Stage 1 — Initialize Data Warehouse
```python
initialize_database()
load_stocks_dim(BANK_SYMBOLS)
```
Creates the 4 SQL tables if they don't exist yet. Completely safe to run on an already-initialized database — `IF NOT EXISTS` guarantees nothing gets overwritten. Then populates the `stocks` dimension table with bank names from `config.py`.

### Stage 2 — Extract to Bronze
```python
run_extraction()
```
Loops through all 12 banks, checks the last stored date for each one, fetches only missing data from Yahoo Finance, and writes raw OHLCV records into `raw_stock_data`.

### Stage 3 — Transform to Silver & Gold
```python
run_transformations()
```
Two passes per bank:
- Clean and de-duplicate Bronze data → write to `processed_stock_prices`
- Compute 5 financial indicators from Silver data → write to `stock_analytics`

### Stage 4 — Export to S3
```python
run_s3_exports()
```
Reads all 4 tables from SQLite, converts to Parquet via PyArrow, uploads to AWS S3 under structured folder paths.

---

## How to Run

### Full Pipeline
```bash
python main.py
```

### Individual Stages (for debugging)
```bash
python extract.py    # Bronze only
python transform.py  # Silver + Gold only
python s3_export.py  # S3 upload only
```

### Daily Refresh (Windows)
Double-click `run_pipeline.bat` — no terminal needed.

---

## Why This Structure?

Each stage is a separate Python module with a single `run_*()` function. `main.py` just calls them in order.

The benefit: if the S3 upload fails one day, you can run `python s3_export.py` in isolation without re-fetching and re-processing all 12 banks. If a new bank's API data is bad, only `extract.py` is involved. Each module is independently testable and replaceable.
