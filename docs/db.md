# db.py — Database Schema & Setup

Sets up the local SQLite database and defines all four tables. This runs first in the pipeline and is completely safe to re-run — nothing gets overwritten or broken.

---

## Medallion Architecture

Three layers, each a separate SQL table:

```
stocks (Dimension)
    ├── raw_stock_data         ← Bronze: unmodified API data
    ├── processed_stock_prices ← Silver: cleaned & structured
    └── stock_analytics        ← Gold:   computed indicators
```

Data flows down. Each layer is progressively cleaner and more analytically useful.

---

## Tables

### `stocks` — Dimension Table
```sql
CREATE TABLE IF NOT EXISTS stocks (
    stock_symbol TEXT PRIMARY KEY,
    company_name TEXT NOT NULL,
    sector       TEXT DEFAULT 'Banking',
    country      TEXT
);
```
The reference table. Maps a ticker symbol (`SBIN.NS`) to its real bank name, sector, and country. Every fact table links back here via a foreign key. This is the **center of the Star Schema**.

`CREATE TABLE IF NOT EXISTS` makes this safe to run multiple times — no duplicate table errors.

### `raw_stock_data` — Bronze Layer
```sql
PRIMARY KEY (date, stock_symbol)
FOREIGN KEY (stock_symbol) REFERENCES stocks(stock_symbol)
```
Stores whatever the API returns, untouched. The **composite primary key** on `(date, symbol)` prevents the same day from being inserted twice for the same bank. The `data_ingestion_timestamp` column records exactly when each row entered the system — a basic audit trail.

### `processed_stock_prices` — Silver Layer
Same key pattern, fewer columns. `adjusted_close` and `data_ingestion_timestamp` are dropped here — they're not needed after cleaning. Only clean OHLCV (Open, High, Low, Close, Volume) data lives here.

### `stock_analytics` — Gold Layer
Only computed columns. Nothing here exists in the raw API data — `daily_return`, `ma50`, `ma200`, `volatility`, `rsi`, `macd` are all calculated by `transform.py`. This is the table Power BI reads from directly.

---

## Key Functions

### `get_connection()`
```python
def get_connection():
    return sqlite3.connect(DB_PATH)
```
Opens a fresh SQLite connection each time it's called. Every function in the pipeline calls this at the start and closes the connection when done. Prevents connection leaks during long runs.

### `initialize_database()`
Runs all four `CREATE TABLE IF NOT EXISTS` statements plus:
```python
cursor.execute("PRAGMA foreign_keys = ON;")
```
SQLite ignores foreign key constraints by default (for legacy reasons). This PRAGMA enables them — so inserting a stock record that doesn't exist in `stocks` gets rejected instead of silently creating orphan rows.

### `load_stocks_dim()`
```python
INSERT INTO stocks VALUES (?, ?, ?, ?)
ON CONFLICT(stock_symbol) DO NOTHING;
```
Parameterized query (not an f-string) — safe from SQL injection. `ON CONFLICT DO NOTHING` means running this multiple times never duplicates or overwrites existing records.

---

## Why SQLite?

- **Zero setup** — just a file on disk, no database server
- **Portable** — copy `bank_stocks.db` anywhere and it works
- **Fast enough** — this is a daily batch job, not a real-time system

In production, swapping to PostgreSQL just means changing the connection string in `config.py`.
