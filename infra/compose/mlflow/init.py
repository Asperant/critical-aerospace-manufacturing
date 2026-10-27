"""WP-PLAT-003 — idempotent MLflow prerequisites, run by the one-shot mlflow-init job.

Creates the `mlflow` database on the platform PostgreSQL and the artifact bucket on
SeaweedFS when they are missing. Only this job holds the S3 admin identity (bucket
creation); the MLflow server itself uses the bucket-scoped `cap-mlflow` identity.
"""

from __future__ import annotations

import os

import boto3
import psycopg2
from botocore.exceptions import ClientError
from psycopg2 import sql

DATABASE = "mlflow"


def ensure_database() -> None:
    connection = psycopg2.connect(
        host="postgres",
        port=5432,
        user="cap",
        password=os.environ["CAP_POSTGRES_PASSWORD"],
        dbname="cap",
        connect_timeout=10,
    )
    connection.autocommit = True  # CREATE DATABASE cannot run in a transaction
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (DATABASE,))
            if cursor.fetchone() is not None:
                print(f"database {DATABASE} exists")
                return
            cursor.execute(
                sql.SQL("CREATE DATABASE {}").format(sql.Identifier(DATABASE))
            )
            print(f"database {DATABASE} created")
    finally:
        connection.close()


def ensure_bucket() -> None:
    bucket = os.environ["CAP_MLFLOW_BUCKET"]
    s3 = boto3.client(
        "s3",
        endpoint_url=os.environ["MLFLOW_S3_ENDPOINT_URL"],
        aws_access_key_id=os.environ["CAP_S3_ADMIN_ACCESS_KEY"],
        aws_secret_access_key=os.environ["CAP_S3_ADMIN_SECRET_KEY"],
        region_name="us-east-1",
    )
    try:
        s3.head_bucket(Bucket=bucket)
        print(f"bucket {bucket} exists")
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") not in {
            "404",
            "NoSuchBucket",
            "NotFound",
        }:
            raise
        s3.create_bucket(Bucket=bucket)
        print(f"bucket {bucket} created")


if __name__ == "__main__":
    ensure_database()
    ensure_bucket()
