import boto3
import pandas as pd
import time
from influxdb_client import InfluxDBClient, Point, WritePrecision, WriteOptions
import json
import io
import os
from datetime import datetime, timedelta
from botocore.exceptions import ClientError
import logging

# -----------------------------
# Logging setup
# -----------------------------
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("csv-watcher")

# -----------------------------
# Environment variables / config
# -----------------------------
BUCKET = os.getenv("S3_BUCKET", "tanuj-aws-cost-history-metrics")
PREFIX = os.getenv("S3_PREFIX", "costs/")
PROCESSED_FILE_KEY = os.getenv("PROCESSED_FILE_KEY", "process_keys/processed_files.json")
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", 3600))  # seconds
RETENTION_DAYS = int(os.getenv("RETENTION_DAYS", 180))

INFLUX_URL = os.getenv("INFLUX_URL", "http://influxdb.monitoring.svc.cluster.local:8086")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN", "admin123admin")
INFLUX_ORG = os.getenv("INFLUX_ORG", "my_org")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "cost_data")

# -----------------------------
# S3 client
# -----------------------------
s3 = boto3.client(
    's3',
    aws_access_key_id=os.environ['AWS_ACCESS_KEY_ID'],
    aws_secret_access_key=os.environ['AWS_SECRET_ACCESS_KEY']
)

# -----------------------------
# InfluxDB client
# -----------------------------
client = InfluxDBClient(
    url=INFLUX_URL,
    token=INFLUX_TOKEN,
    org=INFLUX_ORG
)
write_api = client.write_api(
    write_options=WriteOptions(batch_size=1000, flush_interval=10000, jitter_interval=2000, retry_interval=5000, write_type='blocking')
)
delete_api = client.delete_api()

# -----------------------------
# Helper functions
# -----------------------------
def load_processed_files():
    try:
        obj = s3.get_object(Bucket=BUCKET, Key=PROCESSED_FILE_KEY)
        data = obj['Body'].read()
        return set(json.loads(data))
    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchKey':
            return set()
        else:
            raise

def save_processed_files(processed):
    s3.put_object(Bucket=BUCKET, Key=PROCESSED_FILE_KEY, Body=json.dumps(list(processed)))

def delete_old_entries():
    now = datetime.utcnow()
    cutoff = now - timedelta(days=RETENTION_DAYS)
    logger.info(f"Deleting entries older than {RETENTION_DAYS} days (before {cutoff.isoformat()} UTC)")
    try:
        delete_api.delete(
            start="1970-01-01T00:00:00Z",
            stop=cutoff.isoformat() + "Z",
            predicate='_measurement="cost"',
            bucket=INFLUX_BUCKET,
            org=INFLUX_ORG
        )
        logger.info("Old entries deleted successfully.")
    except Exception as e:
        logger.error(f"Failed to delete old entries: {e}")

# -----------------------------
# Main loop
# -----------------------------
processed_files = load_processed_files()

while True:
    try:
        # 1️⃣ Clean up old data
        delete_old_entries()

        # 2️⃣ List new CSV files
        resp = s3.list_objects_v2(Bucket=BUCKET, Prefix=PREFIX)
        for obj in resp.get('Contents', []):
            key = obj['Key']
            if key in processed_files or key == PROCESSED_FILE_KEY:
                continue

            logger.info(f"Processing {key}")
            csv_obj = s3.get_object(Bucket=BUCKET, Key=key)
            df = pd.read_csv(io.BytesIO(csv_obj['Body'].read()))

            if df.empty:
                logger.warning(f"{key} is empty, skipping...")
                processed_files.add(key)
                save_processed_files(processed_files)
                continue

            for _, row in df.iterrows():
                point = Point("cost") \
                    .time(pd.to_datetime(row['date']), WritePrecision.NS) \
                    .tag("service", str(row['service'])) \
                    .tag("region", str(row['region'])) \
                    .field("amortized_cost", float(row['amortized_cost'])) \
                    .field("blended_cost", float(row['blended_cost'])) \
                    .field("unblended_cost", float(row['unblended_cost'])) \
                    .field("usage_quantity", float(row['usage_quantity']))
                write_api.write(bucket=INFLUX_BUCKET, record=point)

            processed_files.add(key)
            save_processed_files(processed_files)

        logger.info(f"Sleeping for {POLL_INTERVAL} seconds...")
        time.sleep(POLL_INTERVAL)

    except Exception as e:
        logger.error(f"Error encountered: {e}, retrying in 60 seconds...")
        time.sleep(60)