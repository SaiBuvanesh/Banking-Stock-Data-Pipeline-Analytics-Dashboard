import sqlite3
import pandas as pd
from typing import List
import os
from config import DB_PATH

def get_connection():
    """Returns a SQLite connection object."""
    return sqlite3.connect(DB_PATH)

def initialize_database():
    """Initializes the database schema for Medallion Architecture."""
    conn = get_connection()
    cursor = conn.cursor()

    # Enable foreign keys for SQLite
    cursor.execute("PRAGMA foreign_keys = ON;")

    # Table 1: stocks (Dimension table mapping stock symbols to bank details)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS stocks (
        stock_symbol TEXT PRIMARY KEY,
        company_name TEXT NOT NULL,
        sector TEXT DEFAULT 'Banking',
        country TEXT
    );
    """)

    # Table 2: raw_stock_data (Bronze Layer)
    # Stores unmodified data directly from the API
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS raw_stock_data (
        date TEXT,
        stock_symbol TEXT,
        open_price REAL,
        high_price REAL,
        low_price REAL,
        close_price REAL,
        adjusted_close REAL,
        volume INTEGER,
        data_ingestion_timestamp TEXT,
        PRIMARY KEY (date, stock_symbol),
        FOREIGN KEY (stock_symbol) REFERENCES stocks(stock_symbol)
    );
    """)

    # Table 3: processed_stock_prices (Silver Layer)
    # Stores cleaned and standardized stock prices
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS processed_stock_prices (
        date TEXT,
        stock_symbol TEXT,
        open_price REAL,
        high_price REAL,
        low_price REAL,
        close_price REAL,
        volume INTEGER,
        PRIMARY KEY (date, stock_symbol),
        FOREIGN KEY (stock_symbol) REFERENCES stocks(stock_symbol)
    );
    """)

    # Table 4: stock_analytics (Gold Layer)
    # Contains enriched datasets with technical indicators
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS stock_analytics (
        date TEXT,
        stock_symbol TEXT,
        daily_return REAL,
        ma50 REAL,
        ma200 REAL,
        volatility REAL,
        rsi REAL,
        macd REAL,
        PRIMARY KEY (date, stock_symbol),
        FOREIGN KEY (stock_symbol) REFERENCES stocks(stock_symbol)
    );
    """)

    conn.commit()
    conn.close()
    print("Database initialized with Bronze, Silver, and Gold layer schemas.")

def load_stocks_dim(banks_dict: dict):
    """Populates the stocks dimension table."""
    conn = get_connection()
    cursor = conn.cursor()
    for name, symbol in banks_dict.items():
        cursor.execute("""
            INSERT INTO stocks (stock_symbol, company_name, sector, country)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(stock_symbol) DO NOTHING;
        """, (symbol, name, 'Banking', 'India' if not 'Arab' in name else 'Jordan'))
    conn.commit()
    conn.close()

if __name__ == "__main__":
    from config import BANK_SYMBOLS
    initialize_database()
    load_stocks_dim(BANK_SYMBOLS)
