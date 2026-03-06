# transform.py — Silver & Gold Layer Transformations

Takes the raw Bronze data and runs it through two passes — first cleaning it up (Silver), then computing financial indicators (Gold). This is where the actual data engineering and financial math happen.

---

## Pass 1 — Silver Layer (Cleaning)

### Remove Duplicates
```python
df.drop_duplicates(subset=['date', 'stock_symbol'], keep='last', inplace=True)
```
Even with the Bronze upsert, edge cases can produce duplicates. `keep='last'` keeps the most recently ingested version.

### Fix Missing Prices
```python
df[price_cols] = df[price_cols].ffill().bfill()
df['volume']   = df['volume'].fillna(0)
```
Financial data has gaps — public holidays, exchange closures, API hiccups. Rather than dropping those rows (which breaks time-series charts), we fill them:

- **`ffill()` (Forward Fill):** Carry the last known price forward into the missing day
- **`bfill()` (Backward Fill):** If the very first row is missing, pull from the next available
- **Volume gaps → 0:** No trading happened, so volume should be zero, not carried forward

### Sort and Write
Data is sorted chronologically before the upsert to `processed_stock_prices`. All Gold calculations depend on correct date ordering.

---

## Pass 2 — Gold Layer (Indicators)

### Minimum Data Check
```python
if df.empty or len(df) < 200:
    return
```
The 200-day moving average needs at least 200 rows to produce a valid result. Banks with less data are skipped cleanly.

---

### Daily Return
```python
df['daily_return'] = df['close_price'].pct_change()
```
Percentage change between each day's closing price and the previous day's:

```
daily_return = (today_close - yesterday_close) / yesterday_close
```

Tells you how much the stock moved in one trading session. A value of `0.023` means +2.3%.

---

### Moving Averages (MA50 & MA200)
```python
df['ma50']  = df['close_price'].rolling(window=50).mean()
df['ma200'] = df['close_price'].rolling(window=200).mean()
```
A rolling mean averages the last N closing prices at each point in time, smoothing out short-term noise to reveal the actual trend direction.

- **MA50** — medium-term trend (~2 months)
- **MA200** — long-term trend (~10 months)

When MA50 crosses **above** MA200 → **Golden Cross** (bullish). When MA50 crosses **below** → **Death Cross** (bearish).

---

### Annualized Volatility
```python
df['volatility'] = df['daily_return'].rolling(window=20).std() * np.sqrt(252)
```
Standard deviation of daily returns over the last 20 trading days, multiplied by √252 (the number of trading days in a year) to annualize it.

Higher = more erratic and riskier. Lower = more stable and predictable.

---

### RSI (Relative Strength Index)
```python
gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
rs   = gain / loss
df['rsi'] = 100 - (100 / (1 + rs))
```
A momentum oscillator ranging from 0 to 100. Separates each day's price move into gains and losses, averages them over 14 days, then converts to a 0–100 scale.

- **> 70** → overbought, price may pull back
- **< 30** → oversold, potential bounce

---

### MACD (Moving Average Convergence Divergence)
```python
ema12 = df['close_price'].ewm(span=12, adjust=False).mean()
ema26 = df['close_price'].ewm(span=26, adjust=False).mean()
df['macd'] = ema12 - ema26
```
Uses **Exponential Moving Averages (EMA)** — like a regular moving average but with heavier weighting on recent prices. `MACD = EMA(12) − EMA(26)`.

- **Positive MACD** → short-term momentum stronger than long-term (bullish)
- **Negative MACD** → short-term momentum weaker (bearish)

---

### Final Write to Gold
```python
gold_df = gold_df.dropna(subset=['ma200']).copy()
```
The first 199 rows for every bank will have `NaN` for `ma200` (not enough historical data yet). Those get dropped before writing so Power BI only receives complete, valid rows.

Same upsert pattern as the Bronze and Silver writes.
