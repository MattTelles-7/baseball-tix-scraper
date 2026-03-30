FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN groupadd --system app && useradd --system --gid app --home-dir /app app

COPY pyproject.toml README.md LICENSE /app/
COPY src /app/src

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir . && \
    mkdir -p /data && \
    chown -R app:app /app /data

USER app

HEALTHCHECK --interval=60s --timeout=10s --start-period=45s --retries=3 \
  CMD ["mlb-ticket-tracker", "healthcheck", "--json"]

ENTRYPOINT ["mlb-ticket-tracker"]
CMD ["run"]
