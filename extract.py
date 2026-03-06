import yfinance as yf
import pandas as pd
from datetime import datetime
from db import get_connection
from config import BANK_SYMBOLS, DEFAULT_START_DATE

def get_latest_date(symbol: str) -> str:
    """Fetch the latest date available for a given stock symbol in the Raw Layer."""
    conn = get_connection()
    query = f"SELECT MAX(date) FROM raw_stock_data WHERE stock_symbol = '{symbol}';"
    cursor = conn.cursor()
    cursor.execute(query)
    result = cursor.fetchone()[0]
    conn.close()
    return result

def extract_stock_data(symbol: str, name: str) -> pd.DataFrame:
    """Extract stock data incrementally from Yahoo Finance API."""
    latest_date = get_latest_date(symbol)
    start_date = latest_date if latest_date else DEFAULT_START_DATE
    
    print(f"[{symbol}] Fetching data from Yahoo Finance API (start_date: {start_date})...")
    
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(start=start_date)
        
        if df.empty:
            print(f"[{symbol}] No new data found.")
            return pd.DataFrame()
            
        # Reset index to make Date a column
        df.reset_index(inplace=True)
        
        # Format Date to YYYY-MM-DD
        df['Date'] = pd.to_datetime(df['Date']).dt.strftime('%Y-%m-%d')
        
        # Add stock symbol column
        df['stock_symbol'] = symbol
        
        # Add ingestion timestamp
        df['data_ingestion_timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Rename columns to match the target schema
        df.rename(columns={
            'Date': 'date',
            'Open': 'open_price',
            'High': 'high_price',
            'Low': 'low_price',
            'Close': 'close_price',
            'Adj Close': 'adjusted_close',
            'Volume': 'volume'
        }, inplace=True)
        
        # Drop unwanted columns like Dividends, Stock Splits
        cols_to_keep = ['date', 'stock_symbol', 'open_price', 'high_price', 'low_price', 
                        'close_price', 'adjusted_close', 'volume', 'data_ingestion_timestamp']
        
        # Sometimes 'Adj Close' doesn't exist in yfinance history(), if not, map close to it
        if 'adjusted_close' not in df.columns:
            df['adjusted_close'] = df['close_price']
            
        df = df[[col for col in cols_to_keep if col in df.columns]]
        
        return df

    except Exception as e:
        print(f"Error fetching data for {symbol}: {e}")
        return pd.DataFrame()

def load_raw_data(df: pd.DataFrame, symbol: str):
    """Loads df into raw_stock_data handling duplicates via temporary table."""
    if df.empty:
        return
        
    conn = get_connection()
    temp_table = f"temp_{symbol.replace('.','_')}"
    
    # Dump to temp table
    df.to_sql(temp_table, con=conn, if_exists='replace', index=False)
    
    # Upsert (Insert if not exists)
    insert_query = f"""
    INSERT INTO raw_stock_data 
    (date, stock_symbol, open_price, high_price, low_price, close_price, adjusted_close, volume, data_ingestion_timestamp)
    SELECT date, stock_symbol, open_price, high_price, low_price, close_price, adjusted_close, volume, data_ingestion_timestamp
    FROM {temp_table}
    WHERE true
    ON CONFLICT(date, stock_symbol) DO UPDATE SET
        open_price=excluded.open_price,
        high_price=excluded.high_price,
        low_price=excluded.low_price,
        close_price=excluded.close_price,
        adjusted_close=excluded.adjusted_close,
        volume=excluded.volume,
        data_ingestion_timestamp=excluded.data_ingestion_timestamp;
    """
    
    cursor = conn.cursor()
    cursor.execute(insert_query)
    
    # Clean up temp
    cursor.execute(f"DROP TABLE {temp_table};")
    conn.commit()
    conn.close()

def run_extraction():
    """Main function to trigger extraction for all defined banks."""
    print("Starting Raw Data Extraction (Bronze Layer)...")
    for name, symbol in BANK_SYMBOLS.items():
        df = extract_stock_data(symbol, name)
        if not df.empty:
            load_raw_data(df, symbol)
            print(f"[{symbol}] Ingested {len(df)} records into Bronze Layer.")
    print("Extraction successful.")

if __name__ == "__main__":
    run_extraction()
