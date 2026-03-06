# s3_export.py — AWS S3 Data Lake Upload

Reads every processed table from the local SQLite database, converts each one to Parquet format, and uploads to an AWS S3 bucket. This is what makes the pipeline cloud-native.

---

## Why Parquet?

| | CSV | Parquet |
|---|---|---|
| Size | Large (plain text) | ~5× smaller (columnar binary) |
| Speed | Slow full scan | Fast column-projection reads |
| Types | Everything is a string | Preserves int, float, date natively |
| Tool support | Basic | Power BI, Athena, Spark, Databricks |

Parquet is the standard format for Data Lakes. Every major analytics tool reads it natively.

---

## Step-by-Step

### Initialize S3 Client
```python
return boto3.client(
    's3',
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION
)
```
`boto3` is the official AWS SDK for Python. The credential check runs first — if any of the three required values is missing from `.env`, the function returns `None` and the pipeline continues without crashing, generating only local Parquet files. Graceful degradation.

### Read Table from SQLite
```python
df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
```
`pandas.read_sql_query()` pulls the entire table into memory as a DataFrame. From this point the data is no longer tied to SQLite — it's just a Pandas DataFrame that can be written to any format.

### Write Local Parquet
```python
df.to_parquet(local_parquet_path, engine='pyarrow', index=False)
```
**PyArrow** is the columnar memory format library originally built by Apache (used in Spark and dozens of other tools). `index=False` prevents Pandas from writing its internal integer row index as a separate column. The file saves locally to `datalake_export/<table>.parquet` — this acts as a local backup even if the S3 upload fails.

### Upload to S3
```python
s3_key = f"data-lake/{s3_folder}/{table_name}/data.parquet"
s3_client.upload_file(local_parquet_path, AWS_S3_BUCKET_NAME, s3_key)
```
The `s3_key` defines where the file lands inside the bucket. The folder structure mirrors the Medallion layers:

```
bank-stock-data-lake-sai/
└── data-lake/
    ├── dimensions/stocks/data.parquet
    ├── bronze_layer/raw_stock_data/data.parquet
    ├── silver_layer/processed_stock_prices/data.parquet
    └── gold_layer/stock_analytics/data.parquet
```

### Error Handling
Four separate exception types are caught:
- `FileNotFoundError` — local Parquet failed to write
- `NoCredentialsError` — boto3 can't find valid AWS credentials
- `ClientError` — AWS rejecting the request (wrong bucket, IAM permissions, etc.)
- `Exception` — anything else unexpected

None of them stop the pipeline. Each error is logged, and the next table continues.

---

## Connecting Power BI to S3

Power BI uses a Python script data source with `s3fs`:

```python
import pandas as pd, s3fs

aws_params = {
    "key":    "YOUR_KEY",
    "secret": "YOUR_SECRET",
    "client_kwargs": {"region_name": "ap-south-1"}
}

stock_analytics = pd.read_parquet(
    "s3://bank-stock-data-lake-sai/data-lake/gold_layer/stock_analytics/data.parquet",
    storage_options=aws_params
)
```

`s3fs` makes S3 paths behave like local file paths. Pandas reads the Parquet file directly from S3 as if it were on disk.
