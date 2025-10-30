# Backend Dockerfile
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System deps (curl for healthchecks if desired)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY backend/requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt

# Copy app
COPY backend/ /app/

# Expose port
EXPOSE 5000

# Environment defaults (override in compose or env)
ENV ALLOWED_ORIGINS="*"

# Run with gunicorn
CMD ["gunicorn", "-b", "0.0.0.0:5000", "app:app", "--workers", "2", "--threads", "4", "--timeout", "60"]
