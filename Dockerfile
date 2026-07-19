# Multi-service Dockerfile for Clew Personal AI Assistant
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt || true
RUN pip install --no-cache-dir \
    streamlit \
    fastapi \
    uvicorn \
    livekit-agents \
    livekit-plugins-openai \
    livekit-plugins-silero \
    python-dotenv \
    psycopg2-binary

# Copy application source code
COPY . /app

# Create data directory for SQLite WAL storage
RUN mkdir -p /data

EXPOSE 8501 8000

# Default command launches Desktop Command Center
CMD ["streamlit", "run", "ui/app.py", "--server.port=8501", "--server.address=0.0.0.0"]
