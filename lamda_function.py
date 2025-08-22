import os
import csv
import io
from datetime import datetime, timedelta, timezone
import boto3
from botocore.exceptions import ClientError
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

S3_BUCKET = os.environ.get("S3_BUCKET", "tanuj-aws-cost-history-metrics")
S3_PREFIX = os.environ.get("S3_PREFIX", "costs")  # Store daily files under this prefix
REGION = os.environ.get("AWS_REGION", "ap-south-1")

ce = boto3.client("ce", region_name=REGION)
s3 = boto3.client("s3", region_name=REGION)

SERVICE_MAPPING = {
    "Amazon Elastic Compute Cloud - Compute": "Amazon EC2",
    "Amazon Simple Storage Service": "Amazon S3",
    "Amazon Elastic Block Store": "Amazon EBS",
    "Amazon RDS Service": "Amazon RDS",
    "Amazon DynamoDB": "Amazon DynamoDB",
    "Amazon CloudWatch": "Amazon CloudWatch",
}

def format_service_name(service):
    return SERVICE_MAPPING.get(service, service)

def normalize_aws_cost_record(raw_record):
    """Normalize raw AWS cost record to flat dict."""
    date_val = raw_record["date"]
    group_keys = raw_record.get("group_keys", [])
    raw_service = group_keys[0] if len(group_keys) > 0 else "Unknown"
    service = format_service_name(raw_service)
    region = group_keys[1] if len(group_keys) > 1 else "Unknown"
    usage_type = group_keys[2] if len(group_keys) > 2 else "Unknown"
    operation = group_keys[3] if len(group_keys) > 3 else "Unknown"

    metrics = raw_record.get("metrics", {})
    amortized_cost = float(metrics.get("AmortizedCost", {}).get("Amount", 0))
    blended_cost = float(metrics.get("BlendedCost", {}).get("Amount", 0))
    unblended_cost = float(metrics.get("UnblendedCost", {}).get("Amount", 0))
    usage_quantity = float(metrics.get("UsageQuantity", {}).get("Amount", 0))

    return {
        "date": date_val,
        "service": service,
        "region": region,
        "usage_type": usage_type,
        "operation": operation,
        "amortized_cost": round(amortized_cost, 5),
        "blended_cost": round(blended_cost, 5),
        "unblended_cost": round(unblended_cost, 5),
        "usage_quantity": round(usage_quantity, 5),
    }

def fetch_and_store_cost():
    """Fetch AWS cost data and store as day-wise CSV files in S3."""
    try:
        end_date = datetime.now(timezone.utc).date()
        start_date = end_date - timedelta(days=1)  # Yesterday's data
        str_date = start_date.strftime("%Y-%m-%d")

        metrics = ["AmortizedCost", "BlendedCost", "UnblendedCost", "UsageQuantity"]
        group_by = [
            {"Type": "DIMENSION", "Key": "SERVICE"},
            {"Type": "DIMENSION", "Key": "REGION"}
        ]

        logger.info(f"Fetching AWS costs for {str_date}")
        response = ce.get_cost_and_usage(
            TimePeriod={"Start": str_date, "End": (start_date + timedelta(days=1)).strftime("%Y-%m-%d")},
            Granularity="DAILY",
            Metrics=metrics,
            GroupBy=group_by
        )

        # Prepare CSV rows
        header = ["date", "service", "region", "amortized_cost", "blended_cost", "unblended_cost", "usage_quantity"]
        rows = [header]

        for result in response["ResultsByTime"]:
            date_val = result["TimePeriod"]["Start"]
            for group in result.get("Groups", []):
                raw_record = {"date": date_val, "group_keys": group["Keys"], "metrics": group["Metrics"]}
                normalized = normalize_aws_cost_record(raw_record)

                # Skip zero-cost rows
                if normalized["amortized_cost"] == 0.0 and normalized["usage_quantity"] == 0.0:
                    continue

                rows.append([
                    normalized["date"],
                    normalized["service"],
                    normalized["region"],
                    normalized["amortized_cost"],
                    normalized["blended_cost"],
                    normalized["unblended_cost"],
                    normalized["usage_quantity"]
                ])

        # Store CSV in S3 under day-wise path
        s3_key = f"{S3_PREFIX}/{str_date}.csv"
        out = io.StringIO()
        csv.writer(out).writerows(rows)
        s3.put_object(Bucket=S3_BUCKET, Key=s3_key, Body=out.getvalue().encode("utf-8"))

        logger.info(f"Stored AWS cost data to s3://{S3_BUCKET}/{s3_key}, {len(rows)-1} rows")
        return {"status": "ok", "date": str_date, "rows_written": len(rows)-1}

    except ClientError as e:
        logger.error(f"AWS ClientError: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Error fetching AWS cost data: {str(e)}")
        raise

def lambda_handler(event, context):
    return fetch_and_store_cost()
