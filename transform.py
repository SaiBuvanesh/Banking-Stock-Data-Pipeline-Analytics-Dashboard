import pandas as pd
import numpy as np
from db import get_connection
from config import BANK_SYMBOLS

def clean_data_silver_layer(symbol: str):
    """Clean raw data and move to processed_stock_prices (Silver Layer)."""
    conn = get_connection()
    
    # Read from Bronze Layer
    query = f"SELECT * FROM raw_stock_data WHERE stock_symbol = '{symbol}';"
    df = pd.read_sql_query(query, conn)
    
    if df.empty:
        conn.close()
        return df
        
    # Cleaning transformations
    # 1. Drop duplicates
    df.drop_duplicates(subset=['date', 'stock_symbol'], keep='last', inplace=True)
    
    # 2. Handle Missing values: Forward fill, then backward fill for prices
    price_cols = ['open_price', 'high_price', 'low_price', 'close_price', 'adjusted_close']
    df[price_cols] = df[price_cols].ffill().bfill()
    df['volume'] = df['volume'].fillna(0)
    
    # Sort by date
    df['date'] = pd.to_datetime(df['date'])
    df.sort_values(by='date', inplace=True)
    df['date'] = df['date'].dt.strftime('%Y-%m-%d')
    
    # Select columns for Silver
    silver_df = df[['date', 'stock_symbol', 'open_price', 'high_price', 'low_price', 'close_price', 'volume']]
    
    # Upsert into Silver Layer using a temp table
    temp_table = f"temp_silver_{symbol.replace('.', '_')}"
    silver_df.to_sql(temp_table, con=conn, if_exists='replace', index=False)
    
    upsert_query = f"""
    INSERT INTO processed_stock_prices 
    (date, stock_symbol, open_price, high_price, low_price, close_price, volume)
    SELECT date, stock_symbol, open_price, high_price, low_price, close_price, volume FROM {temp_table}
    WHERE true
    ON CONFLICT(date, stock_symbol) DO UPDATE SET
        open_price=excluded.open_price,
        high_price=excluded.high_price,
        low_price=excluded.low_price,
        close_price=excluded.close_price,
        volume=excluded.volume;
    """
    
    cursor = conn.cursor()
    cursor.execute(upsert_query)
    cursor.execute(f"DROP TABLE {temp_table};")
    conn.commit()
    conn.close()
    
    return silver_df

def compute_indicators_gold_layer(symbol: str):
    """Compute financial indicators and push to stock_analytics (Gold Layer)."""
    conn = get_connection()
    
    # Read from Silver Layer
    query = f"SELECT * FROM processed_stock_prices WHERE stock_symbol = '{symbol}' ORDER BY date ASC;"
    df = pd.read_sql_query(query, conn)
    
    if df.empty or len(df) < 200:
        # Not enough data for MA200
        conn.close()
        return
        
    df['date'] = pd.to_datetime(df['date'])
    df.set_index('date', inplace=True)
    
    # 1. Daily Return
    df['daily_return'] = df['close_price'].pct_change()
    
    # 2. Moving Averages
    df['ma50'] = df['close_price'].rolling(window=50).mean()
    df['ma200'] = df['close_price'].rolling(window=200).mean()
    
    # 3. Volatility (Annualized standard deviation of daily returns, 20-day rolling window)
    df['volatility'] = df['daily_return'].rolling(window=20).std() * np.sqrt(252)
    
    # 4. RSI (Relative Strength Index 14-day)
    delta = df['close_price'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # 5. MACD Indicator
    # MACD Line = 12-Day EMA - 26-Day EMA
    ema12 = df['close_price'].ewm(span=12, adjust=False).mean()
    ema26 = df['close_price'].ewm(span=26, adjust=False).mean()
    df['macd'] = ema12 - ema26
    
    # Drop rows with NaN if preferred, or keep them
    df.reset_index(inplace=True)
    df['date'] = df['date'].dt.strftime('%Y-%m-%d')
    
    gold_df = df[['date', 'stock_symbol', 'daily_return', 'ma50', 'ma200', 'volatility', 'rsi', 'macd']]
    gold_df = gold_df.dropna(subset=['ma200']).copy() # Only keep rows where MA200 is available for clean charts
    
    # Upsert to Gold Layer
    temp_table = f"temp_gold_{symbol.replace('.', '_')}"
    gold_df.to_sql(temp_table, con=conn, if_exists='replace', index=False)
    
    upsert_query = f"""
    INSERT INTO stock_analytics 
    (date, stock_symbol, daily_return, ma50, ma200, volatility, rsi, macd)
    SELECT date, stock_symbol, daily_return, ma50, ma200, volatility, rsi, macd FROM {temp_table}
    WHERE true
    ON CONFLICT(date, stock_symbol) DO UPDATE SET
        daily_return=excluded.daily_return,
        ma50=excluded.ma50,
        ma200=excluded.ma200,
        volatility=excluded.volatility,
        rsi=excluded.rsi,
        macd=excluded.macd;
    """
    
    cursor = conn.cursor()
    cursor.execute(upsert_query)
    cursor.execute(f"DROP TABLE {temp_table};")
    conn.commit()
    conn.close()

def run_transformations():
    print("Starting Transformations to Silver & Gold Layers...")
    for name, symbol in BANK_SYMBOLS.items():
        print(f"[{symbol}] Processing Silver Layer (Cleaning)...")
        clean_data_silver_layer(symbol)
        
        print(f"[{symbol}] Processing Gold Layer (Analytics)...")
        compute_indicators_gold_layer(symbol)
    print("Transformations completed.")

if __name__ == "__main__":
    run_transformations()
