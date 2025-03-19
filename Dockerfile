FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Expose ports for API and UIs
EXPOSE 5000 8000 8501

# Create entrypoint that waits for services
ENTRYPOINT ["bash", "/app/scripts/docker-entrypoint.sh"]

# Default command (override in docker-compose)
CMD ["python", "main.py", "api", "--port", "5000"]
