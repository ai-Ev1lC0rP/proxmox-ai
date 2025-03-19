#!/bin/bash

if [ "$1" = "interactive" ]; then
  python proxmox_ai.py
elif [ "$1" = "server" ]; then
  python proxmox_ai.py --server
elif [ -n "$AGENT" ] && [ -n "$QUERY" ]; then
  ARGS="--agent $AGENT --query \"$QUERY\""
  if [ "$EXECUTE" = "true" ]; then
    ARGS="$ARGS --execute"
  fi
  if [ "$NO_STREAM" = "true" ]; then
    ARGS="$ARGS --no-stream"
  fi
  python proxmox_ai.py $ARGS
else
  python proxmox_ai.py --server
fi
