"""
Database setup script for Proxmox AI

This script initializes the PostgreSQL database with the pgvector extension
and creates the necessary schema for the Proxmox AI application.
"""
import os
import sys
import logging
import argparse
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.schema import Base
from database.manager import DatabaseManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def setup_database(db_url: str, drop_existing: bool = False) -> None:
    """
    Set up the database schema
    
    Args:
        db_url: PostgreSQL connection URL
        drop_existing: Whether to drop existing tables
    """
    logger.info(f"Connecting to database at {db_url}")
    engine = create_engine(db_url)
    
    try:
        # Check if we can connect to the database
        with engine.connect() as conn:
            logger.info("Successfully connected to the database")
        
        # Create pgvector extension if it doesn't exist
        with engine.connect() as conn:
            logger.info("Creating pgvector extension if it doesn't exist")
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            conn.commit()
        
        # Drop all tables if requested
        if drop_existing:
            logger.warning("Dropping all existing tables")
            Base.metadata.drop_all(engine)
        
        # Create tables
        logger.info("Creating database tables")
        Base.metadata.create_all(engine)
        
        logger.info("Database setup completed successfully")
    except SQLAlchemyError as e:
        logger.error(f"Error setting up database: {e}")
        raise

def index_proxmox_scripts(db_url: str, proxmox_scripts_path: str = None) -> None:
    """
    Index ProxmoxVE helper scripts
    
    Args:
        db_url: PostgreSQL connection URL
        proxmox_scripts_path: Path to the ProxmoxVE scripts directory
    """
    # Import here to avoid circular imports
    from proxmox_helpers.script_manager import ProxmoxScriptManager
    
    logger.info("Initializing database manager")
    db_manager = DatabaseManager(db_url)
    
    logger.info("Initializing script manager")
    script_manager = ProxmoxScriptManager(proxmox_scripts_path, db_manager)
    
    logger.info("Indexing ProxmoxVE scripts")
    script_manager.index_all_scripts()
    
    logger.info("Script indexing completed successfully")

def main():
    """Main function to run database setup"""
    parser = argparse.ArgumentParser(description="Setup the Proxmox AI database")
    parser.add_argument("--db-url", help="PostgreSQL connection URL", 
                      default=os.environ.get("PROXMOX_DB_URL"))
    parser.add_argument("--drop-existing", action="store_true", 
                      help="Drop existing tables before creating")
    parser.add_argument("--scripts-path", help="Path to ProxmoxVE scripts directory",
                      default=None)
    parser.add_argument("--index-scripts", action="store_true", 
                      help="Index ProxmoxVE scripts after setup")
    
    args = parser.parse_args()
    
    # If db_url is not provided, try environment variable or default
    if not args.db_url:
        args.db_url = os.environ.get(
            "PROXMOX_DB_URL", 
            "postgresql://postgres:postgres@localhost:5432/proxmox_ai"
        )
    
    # Run database setup
    setup_database(args.db_url, args.drop_existing)
    
    # Index ProxmoxVE scripts if requested
    if args.index_scripts:
        index_proxmox_scripts(args.db_url, args.scripts_path)

if __name__ == "__main__":
    main()
