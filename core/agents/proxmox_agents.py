import os
import json
import asyncio
from typing import Dict, List, Any, Optional, Callable, Union, Tuple

from proxmox_client import ProxmoxClient
from app import OpenAIChatCompletionsModel, Agent, Runner, Result


class ProxmoxAgentManager:
    """Manager for all Proxmox AI agents"""
    
    def __init__(self, 
                 model: OpenAIChatCompletionsModel,
                 proxmox_client: ProxmoxClient = None):
        """
        Initialize the Proxmox Agent Manager
        
        Args:
            model: LLM model to use for agents
            proxmox_client: Optional ProxmoxClient instance
        """
        self.model = model
        self.proxmox_client = proxmox_client
        self.agents = {}
        self._initialize_agents()
        
    def _initialize_agents(self):
        """Initialize all Proxmox agents"""
        # VM Management Agent
        self.agents["vm_manager"] = Agent(
            name="Proxmox VM Manager",
            instructions="""You are a Proxmox VM Management expert. 
            You can create, modify, delete, start, stop, and manage virtual machines in Proxmox VE.
            Always provide clear, concise responses focused on VM management.
            
            When creating or modifying VMs, ensure to validate parameters like:
            - vmid (unique identifier)
            - cores (number of CPU cores)
            - memory (RAM in MB)
            - disk size and format
            - network configuration
            
            Follow Proxmox best practices:
            - Set CPU type to 'host' for best performance
            - Disable memory ballooning
            - Use virtio for network interfaces where compatible
            - Use SCSI for disk interfaces where possible
            """,
            model=self.model
        )
        
        # Container Management Agent
        self.agents["container_manager"] = Agent(
            name="Proxmox Container Manager",
            instructions="""You are a Proxmox Container Management expert.
            You can create, modify, delete, start, stop, and manage Linux containers in Proxmox VE.
            Always provide clear, concise responses focused on container management.
            
            When creating or modifying containers, ensure to validate parameters like:
            - vmid (unique identifier)
            - cores (number of CPU cores)
            - memory (RAM in MB)
            - rootfs storage configuration
            - network configuration
            
            Follow Proxmox container best practices:
            - Use unprivileged containers when possible for security
            - Consider resource limits to prevent container resource starvation
            - Configure appropriate startup/shutdown order
            """,
            model=self.model
        )
        
        # Storage Management Agent
        self.agents["storage_manager"] = Agent(
            name="Proxmox Storage Manager",
            instructions="""You are a Proxmox Storage Management expert.
            You can analyze, optimize, and manage storage solutions in Proxmox VE.
            Always provide clear, concise responses focused on storage management.
            
            Consider the following aspects of storage:
            - Storage types (ZFS, LVM-thin, Directory, etc.)
            - Performance characteristics
            - Redundancy and backup strategies
            - Space utilization
            
            Follow Proxmox storage best practices:
            - ZFS offers great features for data integrity and snapshots
            - Consider using SSDs for ZIL (ZFS Intent Log) to speed up synchronous writes
            - Monitor both space usage and inode usage with tools like 'df -h' and 'df -i'
            - For VM storage, prefer mirrors over RAIDZ for performance
            """,
            model=self.model
        )
        
        # Cluster Management Agent
        self.agents["cluster_manager"] = Agent(
            name="Proxmox Cluster Manager",
            instructions="""You are a Proxmox Cluster Management expert.
            You can analyze, optimize, and manage Proxmox VE clusters.
            Always provide clear, concise responses focused on cluster management.
            
            Consider the following aspects of clusters:
            - Node configuration and resources
            - HA (High Availability) setup
            - Replication and live migration
            - Network redundancy
            
            Follow Proxmox cluster best practices:
            - Configure at least 3 nodes for a proper quorum
            - Set up redundant network connections
            - Monitor cluster health regularly
            - Plan for appropriate resource distribution
            """,
            model=self.model
        )
        
        # Proxmox API Assistant Agent
        self.agents["api_assistant"] = Agent(
            name="Proxmox API Assistant",
            instructions="""You are a Proxmox API expert.
            You can help users construct and understand Proxmox API calls.
            Always provide clear, structured responses that include:
            - The correct API endpoint
            - Required parameters
            - Optional parameters
            - Expected responses or status codes
            
            Format API endpoint examples as:
            - HTTP method (GET, POST, PUT, DELETE)
            - URL path (/nodes/{node}/qemu/{vmid}/status/start)
            - Request parameters or body as needed
            
            Follow Proxmox API best practices:
            - Use token-based authentication for security
            - Handle errors appropriately
            - Validate inputs before sending
            - Use appropriate Content-Type headers
            """,
            model=self.model
        )
        
        # Performance Analysis Agent
        self.agents["performance_analyst"] = Agent(
            name="Proxmox Performance Analyst",
            instructions="""You are a Proxmox Performance Analysis expert.
            You can analyze and optimize the performance of Proxmox VE environments.
            Always provide clear, data-driven responses focused on performance optimization.
            
            Consider the following performance aspects:
            - CPU utilization and scheduling
            - Memory usage and swapping
            - Disk I/O and storage throughput
            - Network bandwidth and latency
            
            Follow Proxmox performance best practices:
            - Monitor host CPU usage to avoid oversubscription
            - Ensure adequate memory for VMs and containers
            - Use SSDs for high-performance workloads
            - Separate networks for management, storage, and VM traffic
            - Tune VM parameters based on guest OS requirements
            """,
            model=self.model
        )
    
    def get_agent(self, agent_type: str) -> Optional[Agent]:
        """
        Get an agent by type
        
        Args:
            agent_type: Type of agent to retrieve
            
        Returns:
            Agent instance or None if not found
        """
        return self.agents.get(agent_type)
    
    async def process_request(self, 
                             agent_type: str, 
                             query: str, 
                             streaming: bool = True,
                             callback: Optional[Callable] = None,
                             **kwargs) -> str:
        """
        Process a request using the specified agent type
        
        Args:
            agent_type: Type of agent to use
            query: User query to process
            streaming: Whether to stream the response
            callback: Optional callback for streaming responses
            kwargs: Additional parameters to pass to the agent
            
        Returns:
            Agent response
        """
        agent = self.get_agent(agent_type)
        if not agent:
            return f"Error: Agent type '{agent_type}' not found"
        
        try:
            if streaming:
                return await Runner.run_async(agent, query, streaming=True, callback=callback, **kwargs)
            else:
                return Runner.run_sync(agent, query, **kwargs)
        except Exception as e:
            return f"Error processing request: {str(e)}"
    
    def _extract_action_from_response(self, response: str) -> Tuple[str, Dict[str, Any]]:
        """
        Extract API action from agent response
        
        Args:
            response: Agent response text
            
        Returns:
            Tuple of (action_type, parameters)
        """
        try:
            # Try to find a JSON block in the response
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                action_data = json.loads(json_str)
                
                # Extract the action type and parameters
                action_type = action_data.get('response_type', 'UNKNOWN')
                url = action_data.get('url', '')
                details = action_data.get('details', {})
                
                return action_type, {'url': url, 'details': details}
            
            return 'UNKNOWN', {}
        except Exception as e:
            print(f"Error extracting action: {e}")
            return 'ERROR', {'error': str(e)}
    
    async def execute_action(self, 
                           agent_type: str, 
                           query: str, 
                           execute: bool = False,
                           streaming: bool = False,
                           callback: Optional[Callable] = None) -> Dict[str, Any]:
        """
        Process a request and execute the resulting action if requested
        
        Args:
            agent_type: Type of agent to use
            query: User query to process
            execute: Whether to execute the action or just return it
            streaming: Whether to stream the response
            callback: Optional callback for streaming responses
            
        Returns:
            Dict containing the action details and result if executed
        """
        if not self.proxmox_client and execute:
            return {"error": "Cannot execute action: Proxmox client not initialized"}
        
        # Get agent response
        response = await self.process_request(agent_type, query, streaming, callback)
        
        # Extract action
        action_type, params = self._extract_action_from_response(response)
        
        result = {
            "action_type": action_type,
            "parameters": params,
            "raw_response": response,
            "executed": False,
            "result": None
        }
        
        # Execute the action if requested and we have a valid Proxmox client
        if execute and self.proxmox_client and action_type != 'UNKNOWN' and action_type != 'ERROR':
            try:
                # This is where we would execute the actual Proxmox API call
                # For safety, we're just logging what would be executed
                # In a production system, this would make the actual API call
                
                result["executed"] = True
                result["result"] = "Action execution simulated for safety. Implementation needed for actual execution."
                
                # Example of how execution might work:
                # if action_type == 'GET':
                #     result["result"] = self._execute_get(params)
                # elif action_type == 'POST':
                #     result["result"] = self._execute_post(params)
                # elif action_type == 'PUT':
                #     result["result"] = self._execute_put(params)
                # elif action_type == 'DELETE':
                #     result["result"] = self._execute_delete(params)
                
            except Exception as e:
                result["error"] = str(e)
        
        return result


class ProxmoxAPIExecutor:
    """Executes Proxmox API calls based on agent output"""
    
    def __init__(self, proxmox_client: ProxmoxClient):
        """
        Initialize the Proxmox API Executor
        
        Args:
            proxmox_client: ProxmoxClient instance
        """
        self.client = proxmox_client
        
    def execute(self, action_type: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a Proxmox API call
        
        Args:
            action_type: Type of action (GET, POST, PUT, DELETE)
            params: Parameters for the action
            
        Returns:
            API response
        """
        url = params.get('url', '')
        details = params.get('details', {})
        
        # Parse the URL to determine the API endpoint
        # This is a simplified example - in production, you'd need more robust parsing
        path_parts = url.strip('/').split('/')
        
        # Execute the appropriate action based on the API endpoint
        try:
            if action_type == 'GET':
                return self._execute_get(path_parts, details)
            elif action_type == 'POST':
                return self._execute_post(path_parts, details)
            elif action_type == 'PUT':
                return self._execute_put(path_parts, details)
            elif action_type == 'DELETE':
                return self._execute_delete(path_parts, details)
            else:
                return {"error": f"Unsupported action type: {action_type}"}
        except Exception as e:
            return {"error": f"Error executing API call: {str(e)}"}
    
    def _execute_get(self, path_parts: List[str], details: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a GET request"""
        # This is a simplified implementation - would need to handle all endpoint types
        if len(path_parts) >= 3 and path_parts[0] == 'nodes':
            node = path_parts[1]
            
            # Get VM information
            if len(path_parts) >= 4 and path_parts[2] == 'qemu':
                vmid = path_parts[3] if len(path_parts) > 3 else None
                
                if vmid:
                    if len(path_parts) >= 5 and path_parts[4] == 'config':
                        return self.client.get_vm_config(node, int(vmid))
                    else:
                        # Get specific VM
                        found_vms = [vm for vm in self.client.get_vms(node) if str(vm.get('vmid')) == vmid]
                        return found_vms[0] if found_vms else {"error": f"VM {vmid} not found"}
                else:
                    # Get all VMs
                    return self.client.get_vms(node)
            
            # Get container information
            elif len(path_parts) >= 4 and path_parts[2] == 'lxc':
                vmid = path_parts[3] if len(path_parts) > 3 else None
                
                if vmid:
                    if len(path_parts) >= 5 and path_parts[4] == 'config':
                        return self.client.get_container_config(node, int(vmid))
                    else:
                        # Get specific container
                        found_containers = [c for c in self.client.get_containers(node) if str(c.get('vmid')) == vmid]
                        return found_containers[0] if found_containers else {"error": f"Container {vmid} not found"}
                else:
                    # Get all containers
                    return self.client.get_containers(node)
            
            # Get storage information
            elif len(path_parts) >= 3 and path_parts[2] == 'storage':
                return self.client.get_storage(node)
            
            # Get node status
            elif len(path_parts) == 2 or (len(path_parts) >= 3 and path_parts[2] == 'status'):
                return self.client.get_resource_usage(node)
            
        elif len(path_parts) >= 2 and path_parts[0] == 'cluster' and path_parts[1] == 'status':
            return self.client.get_cluster_status()
            
        return {"error": f"Unsupported GET endpoint: {'/'.join(path_parts)}"}
    
    def _execute_post(self, path_parts: List[str], details: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a POST request"""
        # VM operations
        if len(path_parts) >= 5 and path_parts[0] == 'nodes' and path_parts[2] == 'qemu':
            node = path_parts[1]
            vmid = path_parts[3]
            
            # VM status operations
            if path_parts[4] == 'status':
                if len(path_parts) >= 6:
                    if path_parts[5] == 'start':
                        return self.client.start_vm(node, int(vmid))
                    elif path_parts[5] == 'stop':
                        return self.client.stop_vm(node, int(vmid))
            
            # VM clone operation
            elif path_parts[4] == 'clone':
                # Implement VM clone functionality
                pass
            
            # VM snapshot operation
            elif path_parts[4] == 'snapshot':
                if 'snapname' in details:
                    return self.client.create_vm_snapshot(node, int(vmid), 
                                                        details['snapname'], 
                                                        details.get('description'))
        
        # Container operations
        elif len(path_parts) >= 5 and path_parts[0] == 'nodes' and path_parts[2] == 'lxc':
            node = path_parts[1]
            vmid = path_parts[3]
            
            # Container status operations
            if path_parts[4] == 'status':
                if len(path_parts) >= 6:
                    if path_parts[5] == 'start':
                        return self.client.start_container(node, int(vmid))
                    elif path_parts[5] == 'stop':
                        return self.client.stop_container(node, int(vmid))
            
            # Container snapshot operation
            elif path_parts[4] == 'snapshot':
                if 'snapname' in details:
                    return self.client.create_container_snapshot(node, int(vmid), 
                                                              details['snapname'], 
                                                              details.get('description'))
        
        # Create VM
        elif len(path_parts) >= 3 and path_parts[0] == 'nodes' and path_parts[2] == 'qemu' and len(path_parts) == 3:
            # Implement VM creation
            pass
        
        # Create container
        elif len(path_parts) >= 3 and path_parts[0] == 'nodes' and path_parts[2] == 'lxc' and len(path_parts) == 3:
            # Implement container creation
            pass
            
        return {"error": f"Unsupported POST endpoint: {'/'.join(path_parts)}"}
    
    def _execute_put(self, path_parts: List[str], details: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a PUT request"""
        # VM config update
        if (len(path_parts) >= 5 and path_parts[0] == 'nodes' and 
            path_parts[2] == 'qemu' and path_parts[4] == 'config'):
            # Implement VM config update
            pass
        
        # Container config update
        elif (len(path_parts) >= 5 and path_parts[0] == 'nodes' and 
              path_parts[2] == 'lxc' and path_parts[4] == 'config'):
            # Implement container config update
            pass
        
        # VM resize operation
        elif (len(path_parts) >= 5 and path_parts[0] == 'nodes' and 
              path_parts[2] == 'qemu' and path_parts[4] == 'resize'):
            # Implement VM resize
            pass
            
        return {"error": f"Unsupported PUT endpoint: {'/'.join(path_parts)}"}
    
    def _execute_delete(self, path_parts: List[str], details: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a DELETE request"""
        # VM deletion
        if len(path_parts) >= 4 and path_parts[0] == 'nodes' and path_parts[2] == 'qemu':
            # Implement VM deletion
            pass
        
        # Container deletion
        elif len(path_parts) >= 4 and path_parts[0] == 'nodes' and path_parts[2] == 'lxc':
            # Implement container deletion
            pass
            
        return {"error": f"Unsupported DELETE endpoint: {'/'.join(path_parts)}"}
