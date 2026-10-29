FROM python:3.13.7-slim

WORKDIR /app
ENV PYTHONPATH=/app/services/manufacturing-core/src
COPY packages/contracts /app/packages/contracts
COPY packages/event-consumer /app/packages/event-consumer
COPY services/manufacturing-core /app/services/manufacturing-core
COPY services/operational-twin /app/services/operational-twin
COPY services/operations-bff /app/services/operations-bff
COPY tools/demo-runtime /app/tools/demo-runtime

RUN pip install --no-cache-dir \
    /app/packages/contracts \
    /app/packages/event-consumer \
    /app/services/manufacturing-core \
    /app/services/operational-twin \
    /app/services/operations-bff \
    /app/tools/demo-runtime

ENV PYTHONUNBUFFERED=1
