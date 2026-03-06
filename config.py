import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Project Roots
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = os.path.join(BASE_DIR, "bank_stocks.db")
DATABASE_URI = f"sqlite:///{DB_PATH}"

# AWS S3 Data Lake Configuration
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
AWS_S3_BUCKET_NAME = os.getenv("AWS_S3_BUCKET_NAME")

# Local fallback directory for Parquet files before upload
PARQUET_OUTPUT_DIR = os.path.join(BASE_DIR, "datalake_export")
os.makedirs(PARQUET_OUTPUT_DIR, exist_ok=True)


# List of banking stocks to track
# Uses Yahoo Finance ticker symbols
BANK_SYMBOLS = {
    "State Bank of India (SBI)": "SBIN.NS",
    "HDFC Bank": "HDFCBANK.NS",
    "ICICI Bank": "ICICIBANK.NS",
    "Axis Bank": "AXISBANK.NS",
    "Kotak Mahindra Bank": "KOTAKBANK.NS",
    "IndusInd Bank": "INDUSINDBK.NS",
    "Bank of Baroda": "BANKBARODA.NS",
    "Punjab National Bank": "PNB.NS",
    "IDFC First Bank": "IDFCFIRSTB.NS",
    "Federal Bank": "FEDERALBNK.NS",
    "AU Small Finance Bank": "AUBANK.NS",
    "Bandhan Bank": "BANDHANBNK.NS"
}

# Settings for Historical Data Download
DEFAULT_START_DATE = "2020-01-01"
# If end_date is None, yfinance fetches up to the current day
DEFAULT_END_DATE = None
