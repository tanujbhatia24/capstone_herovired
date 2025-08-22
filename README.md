# DevOps Dashboard for AWS Resource and Cost Monitoring

## Problem Statement

DevOps teams often struggle to monitor **resource usage and manage
costs** effectively across cloud environments. Without clear visibility
into cost drivers and resource consumption, optimizing infrastructure
becomes challenging, leading to unnecessary spend and inefficiencies.

This project focuses on **AWS cost monitoring** --- building a
centralized dashboard that ingests AWS billing data, stores it in a
time-series database, and visualizes it in Grafana. The dashboard
enables DevOps teams to track **per-region costs, per-service spend, and
overall trends**, with the ability to drill down and compare different
billing metrics.

------------------------------------------------------------------------

## Project Goals

1.  **Aggregate AWS cost and usage data** into a central dashboard.
2.  Provide **real-time and historical visualizations** of spend by
    region, service, and globally.
3.  Enable **filters and drill-downs** (e.g., by service, region, date
    range).
4.  Support **alerting** on anomalies (via Grafana alerts).

------------------------------------------------------------------------

## Tools & Technologies Used

-   **Python** → Lambda + csv-watcher ingestion script.
-   **AWS Cost Explorer API** → Cost and usage data collection.
-   **AWS Lambda** → Fetches daily cost data and writes CSVs to S3.
-   **Amazon S3** → Stores daily billing CSVs.
-   **csv-watcher (Python service)** → Watches S3, ingests CSVs into
    InfluxDB.
-   **InfluxDB 2.6** → Stores cost data in time-series format.
-   **Grafana** → Dashboard for visualization & alerting.
-   **Containerization**: Pods deployed in **Minikube** on an **EC2
    host**, using `containerd`.

------------------------------------------------------------------------

## Data Flow

1.  **Lambda Function** (Python):
    -   Runs daily.
    -   Calls AWS Cost Explorer API.
    -   Groups costs by **Service** and **Region**.
    -   Saves results as a daily CSV into S3 (e.g.,
        `costs/2025-08-21.csv`).
2.  **csv-watcher** (Python service in Kubernetes pod):
    -   Watches the S3 bucket.
    -   Reads new CSVs.
    -   Writes records to **InfluxDB** with:
        -   Tags: `service`, `region`
        -   Fields: `amortized_cost`, `blended_cost`, `unblended_cost`,
            `usage_quantity`
        -   Timestamp: `date` column from CSV
3.  **InfluxDB**:
    -   Stores cost data in bucket `cost_data`.
    -   Retains 180 days of history (configurable).
4.  **Grafana Dashboard**:
    -   Queries InfluxDB using Flux.
    -   Visualizes costs by region, service, and total trends.

------------------------------------------------------------------------

## Dashboard Panels

The Grafana dashboard is designed to provide **clear visibility into AWS
cost distribution, total spend, and usage trends**. Each panel addresses
a specific monitoring requirement:

### 1. **AWS COST PER REGION (\$)**

-   **Purpose:** Highlights the total **amortized cost per AWS region**
    in the selected time range.
-   **Why it matters:** Quickly identifies which regions drive the
    highest portion of the AWS bill, enabling teams to focus on
    optimizing workloads in high-cost regions.

### 2. **AWS TOTAL COST (\$)**

-   **Purpose:** Displays the **global total amortized cost** across all
    AWS services and regions.
-   **Why it matters:** Provides a single-glance view of the overall AWS
    spend for the organization in the chosen time window.

### 3. **AWS Top 5 Services & Regions Combined**

-   **Purpose:** Lists the **top 5 service--region pairs** ranked by
    total amortized cost.
-   **Why it matters:** Helps pinpoint the most expensive service
    deployments in specific regions (e.g., *Amazon EC2 in us-east-1*).

### 4. **AWS Daily Total Spend (All Services, All Regions) (\$)**

-   **Purpose:** Shows the **day-by-day trend of total amortized costs**
    across AWS.
-   **Why it matters:** Helps teams spot anomalies (e.g., sudden cost
    spikes), monitor long-term trends, and correlate cost changes with
    deployments or scaling events.

### 5. **Top 5 Regions by Cost (\$)**

-   **Purpose:** Shows the five AWS regions with the highest amortized
    cost.
-   **Why it matters:** Quickly identifies where the majority of
    spending occurs geographically.

### 6. **Top 5 Services by Cost (\$)**

-   **Purpose:** Highlights the five AWS services contributing most to
    overall costs.
-   **Why it matters:** Helps teams focus on the services driving the
    largest portion of spend.

### 7. **AWS Daily Total Cost Comparison (Amortized vs Blended vs Unblended) (\$)**

-   **Purpose:** Compares daily totals across different AWS billing
    models.
-   **Why it matters:** Provides financial insight for reconciling AWS
    invoices and understanding billing differences.

### 8. **Usage Quantity by Service **

-   **Purpose:** Tracks daily usage quantities for each AWS service.
-   **Why it matters:** Links resource consumption to costs, helping
    correlate spikes in usage with spending.

------------------------------------------------------------------------

## Custom Docker Image

The `csv-watcher` pod is deployed using a **custom Docker image** built
specifically for this project:

    tanujbhatia24/csv-watcher:latest

This image contains the Python watcher service that ingests AWS billing
CSVs from S3 into InfluxDB.

------------------------------------------------------------------------

## Minikube Startup

To simplify local testing, the repository also includes a
**`startup.bat` script**:
- Automates Minikube startup on the EC2 host.
- Ensures all required pods (Grafana, InfluxDB, csv-watcher) are
launched automatically.

------------------------------------------------------------------------

## Deployment

### Prerequisites

-   AWS Account with Cost Explorer enabled.
-   IAM role/credentials with permissions for:
    -   `ce:GetCostAndUsage`
    -   `s3:PutObject`, `s3:GetObject`
-   Kubernetes cluster (Minikube on EC2 in this case).
-   Grafana and InfluxDB pods deployed.

### Steps

1.  **Deploy InfluxDB & Grafana** in Minikube.

2.  **Deploy csv-watcher pod** with proper environment variables:

    -   `INFLUX_URL`, `INFLUX_BUCKET`, `INFLUX_TOKEN`,
        `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`.

3.  **Update AWS Credentials in YAML**\
    Before deploying, update the **`csv-watcher.yaml`** file with your
    AWS credentials:

    ``` yaml
    env:
      - name: AWS_ACCESS_KEY_ID
        value: "<Your_Access_Key>"
      - name: AWS_SECRET_ACCESS_KEY
        value: "<Your_Secret_Access_Key>"
    ```

    *Recommendation:* For production, use **IAM roles** or
    **Kubernetes secrets** instead of hardcoding credentials.

4.  **Deploy Lambda** with IAM role to fetch AWS Cost Explorer data and
    store CSV in S3 daily.

5.  Import the **Grafana dashboard JSON** (provided in `dashboards/`).

------------------------------------------------------------------------

## Limitations

-   Data is daily granularity only (AWS Cost Explorer API limitation).
-   AWS Cost Explorer data may lag by up to **24--48 hours**.
-   Retention set to **180 days** (configurable).
-   Currently supports **AWS only** (not Azure/GCP).

------------------------------------------------------------------------

## Future Enhancements

-   Add support for **Azure** and **GCP billing data** for multi-cloud
    visibility.
-   Add **cost anomaly detection** with alerts via Slack/Teams.
-   Backfill and analyze **12 months of AWS historical data**.
-   Enable **multi-account cost aggregation** across AWS Organizations.

------------------------------------------------------------------------

## Kubernetes Pods & Services
<img width="960" height="540" alt="image" src="https://github.com/user-attachments/assets/302e8723-279e-42d9-a5d1-605f958ac9bb" /><br>

## Sample Dashboard
<img width="960" height="540" alt="image" src="https://github.com/user-attachments/assets/55200667-a71c-488d-8440-8bbc49d4fc31" /><br>
<img width="960" height="540" alt="image" src="https://github.com/user-attachments/assets/36f1d43f-7b24-401b-8f88-2fb1bac3ca00" /><br>

## Sample Alerting
<img width="960" height="540" alt="image" src="https://github.com/user-attachments/assets/c5ca29f2-c8bd-46eb-90aa-e3f163f44e77" /><br>
<img width="960" height="540" alt="image" src="https://github.com/user-attachments/assets/fa7d9142-7a58-4429-ba24-fb4cc019e2e3" /><br>

------------------------------------------------------------------------

## Conclusion

This project delivers a **centralized AWS cost monitoring dashboard**
that integrates data from AWS Cost Explorer into **Grafana via
InfluxDB**, providing DevOps teams with actionable insights into cloud
spending.

With panels for **per-region costs, global totals, top services, and
daily trends**, the dashboard makes it easy to:
- Identify cost hotspots (by service and region).
- Monitor overall spending trends.
- Correlate resource usage with costs.
- Support data-driven decisions for cost optimization.

By automating the entire pipeline --- **AWS Lambda → S3 → csv-watcher →
InfluxDB → Grafana** --- the solution ensures that cost data is
refreshed daily and stays up to date without manual intervention.

------------------------------------------------------------------------

## References

-   [AWS Cost Explorer API Documentation](https://docs.aws.amazon.com/aws-cost-management/latest/APIReference/Welcome.html)
-   [InfluxDB Flux Query Language](https://docs.influxdata.com/flux/)
-   [Grafana Documentation](https://grafana.com/docs/)

------------------------------------------------------------------------

*With this dashboard in place, DevOps teams can move from reactive
cost management to **proactive cost optimization**, ensuring better
visibility, control, and efficiency across AWS resources.*

---
