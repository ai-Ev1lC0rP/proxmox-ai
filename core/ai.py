import os
import json
import asyncio
import argparse
import sys
from typing import Dict, List, Any, Optional, Callable, Union

from app import setup_ollama
from proxmox_client import ProxmoxClient
from proxmox_agents import ProxmoxAgentManager, ProxmoxAPIExecutor


class ProxmoxAI:
    """Main application for Proxmox AI management"""
    
    def __init__(self, host: str = None, token_id: str = None, token_secret: str = None):
        """
        Initialize the Proxmox AI application
        
        Args:
            host: Proxmox host (optional, will use environment variables if not provided)
            token_id: API token ID (optional, will use environment variables if not provided)
            token_secret: API token secret (optional, will use environment variables if not provided)
        """
        # Load configuration from environment variables if not provided
        self.host = host or os.environ.get('PROXMOX_HOST')
        self.token_id = token_id or os.environ.get('PROXMOX_TOKEN_ID')
        self.token_secret = token_secret or os.environ.get('PROXMOX_SECRET')
        self.port = int(os.environ.get('PROXMOX_PORT', '8006'))
        self.verify_ssl = os.environ.get('PROXMOX_VERIFY_SSL', 'false').lower() == 'true'
        
        # Initialize LLM model
        self.temperature = float(os.environ.get('LLM_TEMPERATURE', '0.7'))
        self.top_p = float(os.environ.get('LLM_TOP_P', '0.9'))
        self.max_tokens = int(os.environ.get('LLM_MAX_TOKENS', '2048'))
        
        # Initialize components
        self.model = None
        try:
            self.model = setup_ollama(
                temperature=self.temperature,
                top_p=self.top_p,
                max_tokens=self.max_tokens
            )
        except Exception as e:
            print(f"Warning: Failed to initialize LLM model: {e}")
            print("Running in limited functionality mode without LLM capabilities")
        
        self.proxmox_client = None
        if all([self.host, self.token_id, self.token_secret]):
            try:
                self.proxmox_client = ProxmoxClient(
                    host=self.host,
                    token_id=self.token_id,
                    token_secret=self.token_secret,
                    verify_ssl=self.verify_ssl,
                    port=self.port
                )
                print(f"Successfully connected to Proxmox host: {self.host}")
            except Exception as e:
                print(f"Warning: Failed to connect to Proxmox host: {e}")
        
        self.agent_manager = None
        if self.model:
            self.agent_manager = ProxmoxAgentManager(
                model=self.model,
                proxmox_client=self.proxmox_client
            )
        
        self.api_executor = None
        if self.proxmox_client:
            self.api_executor = ProxmoxAPIExecutor(self.proxmox_client)
    
    def load_hosts(self, hosts_file: str = '.hosts') -> List[Dict[str, str]]:
        """
        Load host configurations from .hosts file
        
        Args:
            hosts_file: Path to hosts file
            
        Returns:
            List of host configurations
        """
        hosts = []
        
        try:
            with open(hosts_file, 'r') as f:
                content = f.read()
                
            # Parse the custom format - each host entry is separated by blank lines
            host_entries = content.split('\n\n')
            
            for entry in host_entries:
                if not entry.strip():
                    continue
                
                host_config = {}
                lines = entry.strip().split('\n')
                
                for line in lines:
                    if not line.strip() or ':' not in line:
                        continue
                    
                    # Split on first colon
                    key, value = line.split(':', 1)
                    key = key.strip().replace('Name', 'name')  # Normalize 'Name' to 'name'
                    value = value.strip().rstrip(',')  # Remove trailing comma if present
                    
                    host_config[key] = value
                
                if host_config:
                    hosts.append(host_config)
        
        except Exception as e:
            print(f"Error loading hosts file: {e}")
        
        return hosts
    
    def connect_to_host(self, host_name: str) -> bool:
        """
        Connect to a specific Proxmox host by name
        
        Args:
            host_name: Name of the host to connect to
            
        Returns:
            True if connection successful, False otherwise
        """
        hosts = self.load_hosts()
        
        # Find the host by name
        host_config = None
        for host in hosts:
            if host.get('name', '').lower() == host_name.lower():
                host_config = host
                break
        
        if not host_config:
            print(f"Host '{host_name}' not found in hosts configuration")
            return False
        
        # Extract connection details
        try:
            self.host = host_config.get('PROXMOX_HOST')
            self.token_id = host_config.get('PROXMOX_TOKEN_ID')
            self.token_secret = host_config.get('PROXMOX_SECRET')
            
            if not all([self.host, self.token_id, self.token_secret]):
                print(f"Missing required connection details for host '{host_name}'")
                return False
            
            # Create new client and update components
            self.proxmox_client = ProxmoxClient(
                host=self.host,
                token_id=self.token_id,
                token_secret=self.token_secret,
                verify_ssl=self.verify_ssl,
                port=self.port
            )
            
            # Test connection
            nodes = self.proxmox_client.get_node_status()
            if not nodes:
                print(f"Failed to connect to host '{host_name}'")
                return False
            
            # Update API executor and agent manager
            self.api_executor = ProxmoxAPIExecutor(self.proxmox_client)
            if self.agent_manager:
                self.agent_manager.proxmox_client = self.proxmox_client
            
            print(f"Successfully connected to host '{host_name}'")
            return True
            
        except Exception as e:
            print(f"Error connecting to host '{host_name}': {e}")
            return False
    
    def list_available_hosts(self) -> List[str]:
        """
        List all available Proxmox hosts
        
        Returns:
            List of host names
        """
        hosts = self.load_hosts()
        return [host.get('name', 'Unknown') for host in hosts]
    
    def list_available_agents(self) -> List[str]:
        """
        List all available AI agents
        
        Returns:
            List of agent types
        """
        if not self.agent_manager:
            return ["No agents available - LLM connection failed"]
        return list(self.agent_manager.agents.keys())
    
    def token_callback(self, token: str):
        """Callback for streaming tokens"""
        print(token, end="", flush=True)
    
    async def process_query(self, 
                           agent_type: str, 
                           query: str, 
                           execute: bool = False,
                           streaming: bool = True) -> Dict[str, Any]:
        """
        Process a query using an agent and optionally execute the resulting action
        
        Args:
            agent_type: Type of agent to use
            query: User query
            execute: Whether to execute the action
            streaming: Whether to stream the response
            
        Returns:
            Dict containing the action details and result
        """
        # Check if we have agent manager
        if not self.agent_manager:
            return {"error": "LLM model not available. Cannot process query without AI capabilities."}
            
        # Validate agent type
        if agent_type not in self.agent_manager.agents:
            return {"error": f"Unknown agent type: {agent_type}"}
        
        # Process the query
        callback = self.token_callback if streaming else None
        
        try:
            result = await self.agent_manager.execute_action(
                agent_type=agent_type,
                query=query,
                execute=execute and self.api_executor is not None,
                streaming=streaming,
                callback=callback
            )
            
            # If execution is requested but we don't have a valid client or executor
            if execute and (not self.proxmox_client or not self.api_executor):
                result["warning"] = "Action execution skipped: No Proxmox connection"
            
            return result
        except Exception as e:
            return {"error": f"Error processing query: {str(e)}"}
    
    def safe_input(self, prompt: str, default: str = "") -> str:
        """Safe input function that handles EOF and other input errors

        Args:
            prompt: Input prompt
            default: Default value if input fails

        Returns:
            User input or default value
        """
        try:
            if not sys.stdin.isatty():
                # We're not in an interactive terminal, return default
                print(f"{prompt} (using default: {default})")
                return default
                
            return input(prompt)
        except (EOFError, KeyboardInterrupt):
            print(f"\nInput error, using default: {default}")
            return default
    
    async def interactive_mode(self):
        """Run in interactive command-line mode"""
        print("Proxmox AI - Interactive Mode")
        print("-" * 40)
        
        # Check if we're running in a terminal
        is_interactive = sys.stdin.isatty()
        
        if not self.proxmox_client:
            print("Warning: No Proxmox connection configured. Some features will be limited.")
            hosts = self.list_available_hosts()
            
            if hosts:
                print("Available hosts:")
                for i, host in enumerate(hosts):
                    print(f"  {i+1}. {host}")
                
                if is_interactive:
                    choice = self.safe_input("Select host number to connect (or press Enter to continue without connection): ")
                    if choice.strip():
                        try:
                            host_idx = int(choice) - 1
                            if 0 <= host_idx < len(hosts):
                                self.connect_to_host(hosts[host_idx])
                            else:
                                print("Invalid selection")
                        except ValueError:
                            print("Invalid input")
                else:
                    print("Non-interactive mode detected, skipping host selection")
        
        # Check if we have agent manager
        if not self.agent_manager:
            print("Error: LLM model not available. Cannot run in interactive mode without AI capabilities.")
            return
            
        print("\nAvailable agents:")
        agents = self.list_available_agents()
        for i, agent in enumerate(agents):
            print(f"  {i+1}. {agent}")
        
        agent_idx = 0
        if is_interactive:
            try:
                choice = self.safe_input("Select agent number (default: 1): ", "1")
                if choice.strip():
                    agent_idx = int(choice) - 1
                    if not (0 <= agent_idx < len(agents)):
                        print("Invalid selection, using default")
                        agent_idx = 0
            except ValueError:
                print("Invalid input, using default")
        else:
            print("Non-interactive mode detected, using default agent")
            
        if not agents:
            print("No agents available. Exiting.")
            return
            
        agent_type = agents[agent_idx]
        print(f"\nUsing agent: {agent_type}")
        
        execute_actions = False
        if self.proxmox_client and is_interactive:
            choice = self.safe_input("Execute actions automatically? (y/N): ", "n")
            execute_actions = choice.lower() == 'y'
        
        # For non-interactive mode, exit after setup
        if not is_interactive:
            print("\nNon-interactive mode detected. Setup complete. Exit interactive mode.")
            return
            
        print("\nEnter your queries (type 'exit' to quit):")
        while True:
            query = self.safe_input("\n> ")
            if query.lower() in ('exit', 'quit'):
                break
            
            if not query.strip():
                continue
            
            print()
            await self.process_query(
                agent_type=agent_type,
                query=query,
                execute=execute_actions,
                streaming=True
            )


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Proxmox AI - AI-driven Proxmox management")
    parser.add_argument('--host', help='Proxmox host')
    parser.add_argument('--token-id', help='API token ID')
    parser.add_argument('--token-secret', help='API token secret')
    parser.add_argument('--connect', help='Connect to a specific host from .hosts file')
    parser.add_argument('--agent', help='Agent type to use')
    parser.add_argument('--query', help='Query to process')
    parser.add_argument('--execute', action='store_true', help='Execute the action')
    parser.add_argument('--no-stream', action='store_true', help='Disable streaming output')
    parser.add_argument('--list-hosts', action='store_true', help='List available hosts')
    parser.add_argument('--list-agents', action='store_true', help='List available agents')
    parser.add_argument('--server', action='store_true', help='Run in server mode (non-interactive)')
    
    args = parser.parse_args()
    
    # Initialize the application
    app = ProxmoxAI(
        host=args.host,
        token_id=args.token_id,
        token_secret=args.token_secret
    )
    
    # Handle commands
    if args.list_hosts:
        hosts = app.list_available_hosts()
        print("Available hosts:")
        for host in hosts:
            print(f"  - {host}")
        return
    
    if args.list_agents:
        agents = app.list_available_agents()
        print("Available agents:")
        for agent in agents:
            print(f"  - {agent}")
        return
    
    if args.connect:
        app.connect_to_host(args.connect)
    
    if args.query and args.agent:
        result = await app.process_query(
            agent_type=args.agent,
            query=args.query,
            execute=args.execute,
            streaming=not args.no_stream
        )
        
        if not args.no_stream:
            print("\n\nAction details:")
        
        print(json.dumps(result, indent=2))
    elif args.server:
        # Server mode - keep running instead of exiting
        print("Initialized Proxmox AI in server mode")
        # Simple server loop to keep the container running
        try:
            print("Server is running. Press Ctrl+C to exit.")
            # Keep the application running
            while True:
                await asyncio.sleep(60)  # Sleep for 60 seconds between checks
        except KeyboardInterrupt:
            print("Server shutting down...")
    else:
        # Enter interactive mode if no query specified
        await app.interactive_mode()


if __name__ == "__main__":
    # Load environment variables from .env file
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except Exception as e:
        print(f"Warning: Could not load .env file: {e}")
    
    asyncio.run(main())
