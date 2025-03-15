#!/bin/bash
# Run a specific agent query through the container

if [ $# -lt 2 ]; then
  echo "Usage: $0 <agent_type> <query> [--execute]"
  echo "Example: $0 vm_manager 'List all VMs'"
  echo "Example: $0 storage_manager 'Show disk usage' --execute"
  exit 1
fi

AGENT="$1"
QUERY="$2"
EXECUTE="false"

# Check if --execute flag is provided
if [ "$3" = "--execute" ]; then
  EXECUTE="true"
fi

# Export variables for docker-compose
export AGENT="$AGENT"
export QUERY="$QUERY" 
export EXECUTE="$EXECUTE"

# Run the command
docker-compose run --rm -e AGENT -e QUERY -e EXECUTE proxmox-ai
