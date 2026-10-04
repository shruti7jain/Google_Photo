FROM python:3.11-slim

WORKDIR /app

# Install essential system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements
COPY discovery-engine/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY discovery-engine /app/discovery-engine
COPY Docs /app/Docs

WORKDIR /app/discovery-engine

ENV PORT=8000
EXPOSE 8000

CMD ["sh", "-c", "uvicorn dashboard.api:app --host 0.0.0.0 --port ${PORT:-8000}"]
