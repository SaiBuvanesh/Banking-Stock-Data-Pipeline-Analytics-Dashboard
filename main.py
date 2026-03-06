from db import initialize_database, load_stocks_dim
from extract import run_extraction
from transform import run_transformations
from s3_export import run_s3_exports
from config import BANK_SYMBOLS

def main():
    print("="*50)
    print("Banking Sector Stock Intelligence Platform Pipeline")
    print("="*50)
    
    # Step 1: Initialize Database & Dimensions
    print("\n[Step 1/4] Initializing Data Warehouse Schemas (Medallion DB)...")
    initialize_database()
    load_stocks_dim(BANK_SYMBOLS)
    
    # Step 2: Extract from API to Bronze Layer
    print("\n[Step 2/4] Extracting Raw Data from Yahoo Finance API...")
    run_extraction()
    
    # Step 3: Transform (Clean to Silver -> Analyze to Gold)
    print("\n[Step 3/4] Processing Data into Silver and Analytics Gold Layers...")
    run_transformations()
    
    # Step 4: Export to AWS S3 Data Lake (Parquet)
    print("\n[Step 4/4] Generating Parquet Files and Syncing to AWS S3 Data Lake...")
    run_s3_exports()
    
    print("\n" + "="*50)
    print("Pipeline Execution Completed Successfully.")
    print("Cloud Data Lake / Parquet Files are ready for Power BI consumption.")
    print("="*50)

if __name__ == "__main__":
    main()
