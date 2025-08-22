# Use official Python image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy script
COPY csv_watcher.py /app/csv_watcher.py

# Install required packages
RUN pip install --no-cache-dir boto3 pandas influxdb-client

# Default command
CMD ["python", "/app/csv_watcher.py"]