#!/bin/bash

# Set environment variables for local development
export OLLAMA_BASE_URL=http://localhost:11434/v1
export OLLAMA_MODEL=llama3.2:latest
export PROXMOX_DB_URL=postgresql://postgres:postgres@localhost:5432/proxmox_ai

# Print configuration
echo "Starting Proxmox AI Streamlit UI with:"
echo "OLLAMA_BASE_URL: $OLLAMA_BASE_URL"
echo "OLLAMA_MODEL: $OLLAMA_MODEL"
echo "PROXMOX_DB_URL: $PROXMOX_DB_URL"

# Run the Streamlit UI
streamlit run streamlit_ui.py --server.port=9999
