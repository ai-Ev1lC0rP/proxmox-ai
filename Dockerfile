FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies with explicit versions to avoid conflicts
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir torch==2.0.1 && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir \
    sentence-transformers==2.2.2 \
    pgvector==0.2.0 \
    pytest==7.3.1 \
    transformers==4.30.2 \
    sqlalchemy==2.0.19

# Copy application code
COPY . .

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# Expose port for future web interface
EXPOSE 8000

# Create entrypoint script
RUN echo '#!/bin/bash\n\
if [ "$1" = "interactive" ]; then\n\
  python proxmox_ai.py\n\
elif [ "$1" = "server" ]; then\n\
  python proxmox_ai.py --server\n\
elif [ -n "$AGENT" ] && [ -n "$QUERY" ]; then\n\
  ARGS="--agent $AGENT --query \"$QUERY\""\n\
  if [ "$EXECUTE" = "true" ]; then\n\
    ARGS="$ARGS --execute"\n\
  fi\n\
  if [ "$NO_STREAM" = "true" ]; then\n\
    ARGS="$ARGS --no-stream"\n\
  fi\n\
  python proxmox_ai.py $ARGS\n\
else\n\
  python proxmox_ai.py --server\n\
fi' > /app/entrypoint.sh && chmod +x /app/entrypoint.sh

# Set the entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]

# Default command (will be passed to entrypoint)
CMD ["server"]
