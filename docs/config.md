# config.py — Settings & Configuration

All project-wide settings live here. Ticker symbols, AWS credentials, file paths — one place, no hunting through multiple files.

---

## What It Does

When any script starts, it imports from `config.py`. That means if you want to add a new bank, change your S3 bucket, or shift the historical start date — you do it here and the rest of the pipeline picks it up automatically. Zero changes needed elsewhere.

---

## How It Works

### Loading `.env` Secrets
```python
from dotenv import load_dotenv
load_dotenv()
```
`load_dotenv()` reads the `.env` file and pushes everything inside it into Python's `os.environ`. AWS keys, bucket names, region — all loaded securely without touching the code. This is standard practice so credentials never end up in a Git commit.

### Building File Paths
```python
BASE_DIR = Path(__file__).resolve().parent
DB_PATH  = os.path.join(BASE_DIR, "bank_stocks.db")
```
`__file__` is the path of the current script. `.resolve().parent` gives you the folder it lives in. All paths are built from here — so the pipeline works from any terminal location without path-related bugs.

### AWS Config
```python
AWS_ACCESS_KEY_ID     = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION            = os.getenv("AWS_REGION", "us-east-1")
AWS_S3_BUCKET_NAME    = os.getenv("AWS_S3_BUCKET_NAME")
```
`os.getenv()` returns `None` if a key isn't set — no crashes. The region has `"us-east-1"` as a fallback default so you don't have to set it if you're on the standard AWS region.

### Local Parquet Output
```python
PARQUET_OUTPUT_DIR = os.path.join(BASE_DIR, "datalake_export")
os.makedirs(PARQUET_OUTPUT_DIR, exist_ok=True)
```
Creates a local folder for Parquet files before they get uploaded to S3. `exist_ok=True` means this never throws an error even if the folder already exists.

### Bank Symbol Mapping
```python
BANK_SYMBOLS = {
    "State Bank of India (SBI)": "SBIN.NS",
    "HDFC Bank":                 "HDFCBANK.NS",
    ...
}
```
A dictionary of `{ "Full Name": "Yahoo Finance Ticker" }`. The `.NS` suffix means the stock is listed on India's NSE. To add a new bank — just add a line here and run `main.py`. The pipeline handles the rest.

### Historical Start Date
```python
DEFAULT_START_DATE = "2020-01-01"
DEFAULT_END_DATE   = None
```
The very first run pulls data from `2020-01-01` to today. `None` for the end date means yfinance goes up to the current day automatically. Every subsequent run ignores this and starts from the last stored date instead (incremental logic in `extract.py`).
