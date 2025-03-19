#!/usr/bin/env python3
"""
Proxmox AI - Main Entry Point
Manages Proxmox VE environments with natural language processing.
"""

import os
import argparse
import uvicorn
from dotenv import load_dotenv
import threading
import time

# Load environment variables
load_dotenv()

def start_api(host="0.0.0.0", port=5000, reload=False):
    """Start the FastAPI server for the API"""
    print(f"Starting Proxmox AI API on {host}:{port}")
    uvicorn.run("api.routes:app", host=host, port=port, reload=reload)
    
def start_streamlit(port=8501):
    """Start the Streamlit UI"""
    import streamlit.web.bootstrap as bootstrap
    import sys
    
    print(f"Starting Proxmox AI Streamlit UI on port {port}")
    sys.argv = ["streamlit", "run", "ui/streamlit_ui.py", "--server.port", str(port)]
    bootstrap.run()
    
def start_chainlit(port=8000):
    """Start the Chainlit UI"""
    import chainlit as cl
    import importlib.util
    import sys
    
    print(f"Starting Proxmox AI Chainlit UI on port {port}")
    # We need to import the UI module dynamically
    spec = importlib.util.spec_from_file_location("chainlit_ui", "ui/chainlit_ui.py")
    chainlit_ui = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(chainlit_ui)
    
    # Chainlit uses its own CLI, so we need to modify sys.argv
    sys.argv = ["chainlit", "run", "ui/chainlit_ui.py", "--port", str(port)]
    cl.main()

def init_database(recreate=False):
    """Initialize the database"""
    from db.models import init_db
    from db.vector_store import VectorStore
    
    print("Initializing database...")
    try:
        # Initialize database
        init_db()
        
        if recreate:
            print("Recreating database tables...")
            from sqlalchemy import MetaData
            from db.models import engine
            
            # Drop all tables
            metadata = MetaData()
            metadata.reflect(bind=engine)
            metadata.drop_all(bind=engine)
            
            # Recreate tables
            init_db()
        
        print("Database initialization complete!")
        return True
    except Exception as e:
        print(f"Database initialization failed: {e}")
        return False

def start_all(api_host="0.0.0.0", api_port=5000, ui_port=8501, ui_type="streamlit"):
    """Start both the API and UI services"""
    # First initialize the database
    init_database()
    
    # Start API in a separate thread
    api_thread = threading.Thread(
        target=start_api,
        args=(api_host, api_port, False),
        daemon=True
    )
    api_thread.start()
    
    # Give the API time to start
    time.sleep(2)
    
    # Start the selected UI
    print(f"Starting UI using {ui_type}...")
    if ui_type == "streamlit":
        start_streamlit(port=ui_port)
    elif ui_type == "chainlit":
        start_chainlit(port=ui_port)
    else:
        print(f"Unknown UI type: {ui_type}")
        return

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Proxmox AI - Manage Proxmox VE with natural language")
    
    # Create subparsers for different commands
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # API command
    api_parser = subparsers.add_parser("api", help="Start the API server")
    api_parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to bind to")
    api_parser.add_argument("--port", type=int, default=5000, help="Port to bind to")
    api_parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    
    # Streamlit UI command
    streamlit_parser = subparsers.add_parser("streamlit", help="Start the Streamlit UI")
    streamlit_parser.add_argument("--port", type=int, default=8501, help="Port to bind to")
    
    # Chainlit UI command
    chainlit_parser = subparsers.add_parser("chainlit", help="Start the Chainlit UI")
    chainlit_parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    
    # Database init command
    db_parser = subparsers.add_parser("init-db", help="Initialize the database")
    db_parser.add_argument("--recreate", action="store_true", help="Drop and recreate all tables")
    
    # Start all command
    all_parser = subparsers.add_parser("start-all", help="Start both API and UI")
    all_parser.add_argument("--api-host", type=str, default="0.0.0.0", help="API host to bind to")
    all_parser.add_argument("--api-port", type=int, default=5000, help="API port to bind to")
    all_parser.add_argument("--ui-port", type=int, default=8501, help="UI port to bind to")
    all_parser.add_argument("--ui-type", type=str, default="streamlit", choices=["streamlit", "chainlit"], help="UI type to use")
    
    # Parse arguments
    args = parser.parse_args()
    
    # Execute the appropriate command
    if args.command == "api":
        start_api(host=args.host, port=args.port, reload=args.reload)
    elif args.command == "streamlit":
        start_streamlit(port=args.port)
    elif args.command == "chainlit":
        start_chainlit(port=args.port)
    elif args.command == "init-db":
        init_database(recreate=args.recreate)
    elif args.command == "start-all":
        start_all(api_host=args.api_host, api_port=args.api_port, ui_port=args.ui_port, ui_type=args.ui_type)
    else:
        parser.print_help()
