# Dockerfile
# Multi-stage build setup for Python FastAPI backend.
# The React application is built separately and can be run in the docker-compose bundle.

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend application
COPY backend/ /app/

# Create uploads, logs, and chroma storage folders
RUN mkdir -p /app/uploads /app/chroma_db /app/logs

EXPOSE 8000

ENV PORT=8000
ENV HOST=0.0.0.0

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
