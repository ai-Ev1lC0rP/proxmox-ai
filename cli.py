#!/usr/bin/env python3
"""
Proxmox AI CLI Interface

This module provides a command-line interface for interacting with the Proxmox AI system.
It allows users to issue natural language commands or use standard command patterns.
"""
import os
import sys
import argparse
import logging
from typing import Optional, List, Dict, Any, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import proxmox client components
from proxmox_client import ProxmoxClient
from proxmox_helpers.command_handler import ProxmoxCommandHandler
from database.manager import DatabaseManager

class ProxmoxAICLI:
    """CLI interface for Proxmox AI"""
    
    def __init__(self, db_url: Optional[str] = None):
        """
        Initialize the CLI interface
        
        Args:
            db_url: Database connection URL
        """
        # Get database URL from environment or use default
        self.db_url = db_url or os.environ.get(
            "PROXMOX_DB_URL", 
            "postgresql://postgres:postgres@localhost:5432/proxmox_ai"
        )
        
        # Initialize database manager
        logger.info(f"Connecting to database at {self.db_url}")
        self.db_manager = DatabaseManager(self.db_url)
        
        # Initialize Proxmox client
        logger.info("Initializing Proxmox client")
        self.proxmox_client = self._setup_proxmox_client()
        
        # Initialize command handler
        logger.info("Initializing command handler")
        self.command_handler = ProxmoxCommandHandler(
            self.proxmox_client, 
            self.db_manager
        )
    
    def _setup_proxmox_client(self) -> ProxmoxClient:
        """
        Set up the Proxmox client from environment variables
        
        Returns:
            ProxmoxClient: Configured Proxmox client
        """
        # Get Proxmox connection details from environment
        host = os.environ.get("PROXMOX_HOST")
        port = int(os.environ.get("PROXMOX_PORT", "8006"))
        user = os.environ.get("PROXMOX_USER")
        token_name = os.environ.get("PROXMOX_TOKEN_ID")
        token_value = os.environ.get("PROXMOX_SECRET")
        verify_ssl = os.environ.get("PROXMOX_VERIFY_SSL", "false").lower() == "true"
        
        # Check if required environment variables are set
        if not all([host, user or token_name, token_value]):
            logger.warning(
                "Proxmox connection details not fully provided. "
                "Set PROXMOX_HOST, PROXMOX_TOKEN_ID, and PROXMOX_SECRET environment variables."
            )
            return None
        
        # Create and return the client
        return ProxmoxClient(
            host=host,
            port=port,
            user=user,
            token_name=token_name,
            token_value=token_value,
            verify_ssl=verify_ssl
        )
    
    def process_command(self, command: str) -> Dict[str, Any]:
        """
        Process a user command
        
        Args:
            command: User command text
            
        Returns:
            Dict: Command result
        """
        if not command:
            return {"error": "Empty command"}
        
        try:
            # Log the command
            self.db_manager.log_command(command)
            
            # Process the command
            result = self.command_handler.handle_command(command)
            
            return result
        except Exception as e:
            logger.error(f"Error processing command: {str(e)}")
            return {"error": str(e)}
    
    def interactive_mode(self) -> None:
        """Run the CLI in interactive mode"""
        print("=== Proxmox AI CLI ===")
        print("Type 'exit' or 'quit' to exit")
        print("Type 'help' to see available commands")
        
        while True:
            try:
                # Get user input
                command = input("\nproxmox-ai> ")
                
                # Check for exit command
                if command.lower() in ['exit', 'quit']:
                    print("Goodbye!")
                    break
                
                # Check for help command
                if command.lower() == 'help':
                    self._print_help()
                    continue
                
                # Process the command
                result = self.process_command(command)
                
                # Display the result
                if isinstance(result, dict) and "error" in result:
                    print(f"Error: {result['error']}")
                else:
                    self._display_result(result)
                    
            except KeyboardInterrupt:
                print("\nOperation cancelled. Type 'exit' to quit.")
                continue
            except EOFError:
                print("\nGoodbye!")
                break
            except Exception as e:
                print(f"Error: {str(e)}")
    
    def _display_result(self, result: Any) -> None:
        """
        Display the command result in a user-friendly format
        
        Args:
            result: Command result to display
        """
        if result is None:
            print("Command completed with no result.")
            return
        
        if isinstance(result, str):
            print(result)
        elif isinstance(result, list):
            if not result:
                print("No results found.")
                return
            
            if isinstance(result[0], dict):
                # Print tabular data for list of dictionaries
                keys = result[0].keys()
                
                # Print header
                header = " | ".join(str(k).upper() for k in keys)
                print(header)
                print("-" * len(header))
                
                # Print rows
                for item in result:
                    print(" | ".join(str(item.get(k, "")) for k in keys))
            else:
                # Print simple list
                for item in result:
                    print(f"- {item}")
        elif isinstance(result, dict):
            for key, value in result.items():
                print(f"{key}: {value}")
        else:
            print(result)
    
    def _print_help(self) -> None:
        """Print help information"""
        commands = [
            ("list nodes", "List all Proxmox nodes"),
            ("list vms [on <node>]", "List all virtual machines"),
            ("list containers [on <node>]", "List all containers"),
            ("list storage [on <node>]", "List all storage resources"),
            ("start vm <vmid> [on <node>]", "Start a virtual machine"),
            ("stop vm <vmid> [on <node>]", "Stop a virtual machine"),
            ("start container <ctid> [on <node>]", "Start a container"),
            ("stop container <ctid> [on <node>]", "Stop a container"),
            ("create vm from template <template>", "Create a VM from a template"),
            ("create container <type>", "Create a container"),
            ("help", "Show this help message"),
            ("exit, quit", "Exit the program"),
            ("", ""),
            ("Natural language commands:", ""),
            ("You can also use natural language commands like:", ""),
            ("  - \"Show me all running containers\"", ""),
            ("  - \"Start the VM with ID 100\"", ""),
            ("  - \"What is the status of node pve01?\"", "")
        ]
        
        # Calculate the width for the first column
        max_width = max(len(cmd[0]) for cmd in commands)
        
        # Print each command with description
        for cmd, desc in commands:
            if not desc:
                print(f"\n{cmd}")
            else:
                print(f"{cmd.ljust(max_width + 2)} {desc}")

def main():
    """Main entry point for CLI"""
    parser = argparse.ArgumentParser(description="Proxmox AI CLI")
    parser.add_argument("--db-url", help="PostgreSQL connection URL")
    parser.add_argument("-c", "--command", help="Run a single command and exit")
    
    args = parser.parse_args()
    
    # Create CLI instance
    cli = ProxmoxAICLI(db_url=args.db_url)
    
    # Run single command or interactive mode
    if args.command:
        result = cli.process_command(args.command)
        cli._display_result(result)
    else:
        cli.interactive_mode()

if __name__ == "__main__":
    main()
