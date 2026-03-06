import boto3
import os
import pandas as pd
from botocore.exceptions import NoCredentialsError, ClientError
from config import (
    AWS_ACCESS_KEY_ID, 
    AWS_SECRET_ACCESS_KEY, 
    AWS_REGION, 
    AWS_S3_BUCKET_NAME,
    PARQUET_OUTPUT_DIR
)
from db import get_connection

def get_s3_client():
    """Initializes and returns the boto3 S3 client."""
    if not all([AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_S3_BUCKET_NAME]):
        print("Warning: AWS Credentials or Bucket Name not fully set in .env. Skipping S3 upload.")
        return None
        
    return boto3.client(
        's3',
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_REGION
    )

def export_table_to_parquet_and_upload(table_name: str, s3_folder: str = "curated_data"):
    """
    Reads a table from the SQLite local DB, converts it to Parquet,
    and uploads it directly to the designated S3 Data Lake bucket.
    """
    print(f"\n[S3 Export] Processing table: '{table_name}'...")
    
    # 1. Read Data from SQLite Database
    conn = get_connection()
    try:
        df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
    except Exception as e:
        print(f"Error reading {table_name}: {e}")
        conn.close()
        return
    finally:
        conn.close()
        
    if df.empty:
        print(f"Table {table_name} is empty. Skipping export.")
        return
        
    # 2. Save directly to local fast-read Parquet
    local_parquet_path = os.path.join(PARQUET_OUTPUT_DIR, f"{table_name}.parquet")
    
    # Convert dates or other standard formats specific to Pandas->Parquet serialization 
    # Use PyArrow engine natively
    print(f"Saving '{table_name}' to local Parquet file: {local_parquet_path}")
    df.to_parquet(local_parquet_path, engine='pyarrow', index=False)
    
    # 3. Upload to AWS S3 Data Lake
    s3_client = get_s3_client()
    if not s3_client:
        print("Local Parquet generated, but S3 Upload skipped due to missing credentials.")
        return
        
    # Example key (path in S3): data-lake/curated_data/stock_analytics/data.parquet
    s3_key = f"data-lake/{s3_folder}/{table_name}/data.parquet"
    
    print(f"Uploading {local_parquet_path} to S3 bucket '{AWS_S3_BUCKET_NAME}' at key '{s3_key}'...")
    try:
        s3_client.upload_file(local_parquet_path, AWS_S3_BUCKET_NAME, s3_key)
        print("Upload Successful.")
    except FileNotFoundError:
        print("The file was not found")
    except NoCredentialsError:
        print("Credentials not available")
    except ClientError as e:
        print(f"AWS Client Error: {e}")
    except Exception as e:
        print(f"Failed to upload to S3 (Check bucket name?): {e}")

def run_s3_exports():
    """Exports dimensions and Gold/Silver layers to Parquet Data Lake on AWS S3."""
    print("\nStarting AWS S3 Data Lake Export Process...")
    
    # Dimension Table
    export_table_to_parquet_and_upload("stocks", "dimensions")
    
    # Bronze Layer Table
    export_table_to_parquet_and_upload("raw_stock_data", "bronze_layer")
    
    # Silver Layer Table
    export_table_to_parquet_and_upload("processed_stock_prices", "silver_layer")
    
    # Gold Analytics Table
    export_table_to_parquet_and_upload("stock_analytics", "gold_layer")
    
    print("S3 Data Lake Export Process completed.")

if __name__ == "__main__":
    run_s3_exports()
