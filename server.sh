#!/bin/bash
# Server management script for Proxmox AI

# Default action
ACTION="status"

if [ $# -ge 1 ]; then
  ACTION="$1"
fi

case "$ACTION" in
  start)
    echo "Starting Proxmox AI server..."
    docker-compose up -d
    ;;
  stop)
    echo "Stopping Proxmox AI server..."
    docker-compose stop
    ;;
  restart)
    echo "Restarting Proxmox AI server..."
    docker-compose restart
    ;;
  logs)
    echo "Showing Proxmox AI server logs..."
    docker-compose logs -f
    ;;
  status)
    echo "Proxmox AI server status:"
    docker-compose ps
    ;;
  *)
    echo "Usage: $0 [start|stop|restart|logs|status]"
    exit 1
    ;;
esac
