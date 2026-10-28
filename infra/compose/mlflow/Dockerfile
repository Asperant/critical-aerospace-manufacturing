# WP-PLAT-003 — MLflow tracking server for the platform runtime.
# 02: metadata in PostgreSQL, artifacts in SeaweedFS (S3). The upstream image ships
# neither driver, so this adds exactly those two pinned wheels and nothing else,
# and drops root.
FROM ghcr.io/mlflow/mlflow:v3.16.1

RUN pip install --no-cache-dir --only-binary=:all: \
        psycopg2-binary==2.9.13 \
        boto3==1.43.108 \
    && useradd --system --uid 10001 --no-create-home --shell /usr/sbin/nologin mlflow \
    && install -d -m 0755 /opt/cap

# Readable whatever the build host's umask is (--chmod alone would also apply
# 0444 to a directory it creates, which the non-root user could not enter).
COPY --chmod=0444 init.py /opt/cap/mlflow_init.py

USER 10001
