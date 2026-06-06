FROM python:3.11-slim

# Avoid .pyc files and buffer flushing so logs appear immediately.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies first for better layer caching.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application code.
COPY tracker ./tracker

# Snapshots and the cached instagrapi session live here; mount it as a volume
# so state survives container restarts.
VOLUME ["/app/data"]

# Loop interval can be overridden, e.g.:
#   docker run -e INTERVAL=24h ...
ENV INTERVAL=12h

# Run continuously, checking every $INTERVAL. Config comes from env vars
# (INSTAGRAM_SESSIONID / WEBHOOK_URL / TARGET_USERNAME / NOTIFIER_TYPE).
CMD ["sh", "-c", "python -m tracker run --loop --interval \"$INTERVAL\""]
