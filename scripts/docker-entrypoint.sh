#!/bin/bash
set -e

# Wait for PostgreSQL to be ready
wait_for_postgres() {
  echo "Waiting for PostgreSQL..."
  until PGPASSWORD=${POSTGRES_PASSWORD:-postgres} psql -h ${POSTGRES_HOST:-postgres} -U ${POSTGRES_USER:-postgres} -d ${POSTGRES_DB:-proxmox_ai} -c '\q' 2>/dev/null; do
    echo "PostgreSQL is unavailable - sleeping"
    sleep 2
  done
  echo "PostgreSQL is up and running!"
}

# Wait for Ollama to be ready
wait_for_ollama() {
  echo "Waiting for Ollama..."
  until curl -s --fail "${OLLAMA_BASE_URL:-http://ollama:11434/v1}/models" > /dev/null 2>&1; do
    echo "Ollama is unavailable - sleeping"
    sleep 2
  done
  echo "Ollama is up and running!"
}

# Initialize database if needed
init_database() {
  echo "Initializing database if needed..."
  python -c "from db.models import init_db; init_db()"
  echo "Database initialization completed!"
}

# Main function
main() {
  # Wait for required services
  if [[ "${SKIP_WAIT:-false}" != "true" ]]; then
    wait_for_postgres
    wait_for_ollama
  fi
  
  # Initialize database
  init_database
  
  # Execute the command
  exec "$@"
}

# Run main function with all arguments
main "$@"
