#!/bin/bash
# Run the Docker container in interactive mode with TTY attached

# Stop any existing container
docker-compose stop proxmox-ai

# Run in interactive mode with TTY
docker-compose run --rm -it proxmox-ai interactive
