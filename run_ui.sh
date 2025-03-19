#!/bin/bash

# Wait for dependencies to initialize
echo "Waiting for services to initialize..."
sleep 5

# Set environment variables if not already set
export OLLAMA_BASE_URL=${OLLAMA_BASE_URL:-"http://host.docker.internal:11434/v1"}
export OLLAMA_MODEL=${OLLAMA_MODEL:-"llama3.2:latest"}

# Print debug information
echo "Starting Chainlit UI with:"
echo "OLLAMA_BASE_URL: $OLLAMA_BASE_URL"
echo "OLLAMA_MODEL: $OLLAMA_MODEL"

# Run the Chainlit UI
cd /app
chainlit run ui.py --host 0.0.0.0 --port 8000
