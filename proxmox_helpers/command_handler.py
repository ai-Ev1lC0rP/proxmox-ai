"""
Command handler for Proxmox AI

This module handles natural language commands for Proxmox operations,
parsing them into executable actions using the proxmox client.
"""
from typing import Dict, List, Any, Optional, Tuple, Union
import re
import logging
import json
from datetime import datetime

from proxmox_client import ProxmoxClient
from database.manager import DatabaseManager
from .script_manager import ProxmoxScriptManager
from .ansible_manager import AnsibleManager

logger = logging.getLogger(__name__)

class ProxmoxCommandHandler:
    """
    Handler for natural language Proxmox commands
    
    This class interprets common commands for Proxmox operations and
    executes them using the Proxmox client.
    """
    
    def __init__(self, proxmox_client: ProxmoxClient, db_manager: DatabaseManager = None):
        """
        Initialize the command handler
        
        Args:
            proxmox_client: Initialized Proxmox client
            db_manager: Database manager for storing command history and embeddings
        """
        self.proxmox = proxmox_client
        self.db_manager = db_manager or DatabaseManager()
        self.script_manager = ProxmoxScriptManager()
        self.ansible_manager = AnsibleManager()
        
        # Define command patterns for regular expression matching
        self.command_patterns = [
            # Node commands
            (r"list (?:all )?(?:hosts|nodes)", self.list_nodes),
            (r"show (?:node|host) status", self.list_nodes),
            (r"get (?:node|host) (?:status|info)(?: for| of)? ([a-zA-Z0-9\-_]+)", self.get_node_status),
            
            # VM commands
            (r"list (?:all )?(?:vms|virtual machines)", self.list_vms),
            (r"list (?:running|active) (?:vms|virtual machines)", lambda: self.list_vms(status="running")),
            (r"list (?:stopped|inactive) (?:vms|virtual machines)", lambda: self.list_vms(status="stopped")),
            (r"get (?:vm|virtual machine) (?:status|info)(?: for| of)? (\d+)", self.get_vm_status),
            (r"start (?:vm|virtual machine) (\d+)(?: on node ([a-zA-Z0-9\-_]+))?", self.start_vm),
            (r"stop (?:vm|virtual machine) (\d+)(?: on node ([a-zA-Z0-9\-_]+))?", self.stop_vm),
            (r"restart (?:vm|virtual machine) (\d+)(?: on node ([a-zA-Z0-9\-_]+))?", self.restart_vm),
            
            # Container commands
            (r"list (?:all )?(?:containers|cts|lxcs)", self.list_containers),
            (r"list (?:running|active) (?:containers|cts|lxcs)", lambda: self.list_containers(status="running")),
            (r"list (?:stopped|inactive) (?:containers|cts|lxcs)", lambda: self.list_containers(status="stopped")),
            (r"get (?:container|ct|lxc) (?:status|info)(?: for| of)? (\d+)", self.get_container_status),
            (r"start (?:container|ct|lxc) (\d+)(?: on node ([a-zA-Z0-9\-_]+))?", self.start_container),
            (r"stop (?:container|ct|lxc) (\d+)(?: on node ([a-zA-Z0-9\-_]+))?", self.stop_container),
            (r"restart (?:container|ct|lxc) (\d+)(?: on node ([a-zA-Z0-9\-_]+))?", self.restart_container),
            
            # Storage commands
            (r"list (?:all )?storage", self.list_storage),
            (r"show storage(?: on| for) node ([a-zA-Z0-9\-_]+)", self.list_node_storage),
            
            # Resource usage commands
            (r"show (?:resource |system )?usage(?: for| of)? node ([a-zA-Z0-9\-_]+)", self.get_resource_usage),
            (r"show (?:cluster|datacenter) usage", self.get_cluster_usage),
            
            # Task commands
            (r"list (?:recent )?tasks", lambda: self.list_tasks(limit=10)),
            (r"list (?:recent )?tasks(?: for| on) node ([a-zA-Z0-9\-_]+)", self.list_node_tasks),
            
            # Snapshot commands
            (r"list snapshots for (?:vm|virtual machine) (\d+)(?: on node ([a-zA-Z0-9\-_]+))?", self.list_vm_snapshots),
            (r"list snapshots for (?:container|ct|lxc) (\d+)(?: on node ([a-zA-Z0-9\-_]+))?", self.list_container_snapshots),
            
            # Combined resource commands
            (r"list (?:all )?resources", self.list_all_resources),
            (r"summarize (?:datacenter|cluster|environment)", self.summarize_environment),
            
            # Ansible integration commands
            (r"list ansible playbooks", self.list_ansible_playbooks),
            (r"run ansible playbook ([a-zA-Z0-9\-_]+)(?: with vars (.+))?(?: on hosts (.+))?(?: with tags (.+))?", self.run_ansible_playbook),
            (r"manage vm with ansible ([a-zA-Z0-9\-_]+) (?:vm|vmid) (\d+)(?: on node ([a-zA-Z0-9\-_]+))?", self.manage_vm_with_ansible),
            (r"manage container with ansible ([a-zA-Z0-9\-_]+) (?:ct|ctid) (\d+)(?: on node ([a-zA-Z0-9\-_]+))?", self.manage_container_with_ansible),
            (r"manage cluster with ansible ([a-zA-Z0-9\-_]+)(?: on node ([a-zA-Z0-9\-_]+))?(?: from node ([a-zA-Z0-9\-_]+))?(?: with name ([a-zA-Z0-9\-_]+))?", self.manage_cluster_with_ansible),
        ]
    
    def process_command(self, command: str) -> Dict[str, Any]:
        """
        Process a natural language command
        
        Args:
            command: The natural language command to process
            
        Returns:
            Dictionary with command result
        """
        logger.info(f"Processing command: {command}")
        
        # Save command in history if db_manager is available
        command_log = None
        if self.db_manager:
            command_log = self.db_manager.store_command_log(command=command)
        
        # Try to match the command with our patterns
        for pattern, handler in self.command_patterns:
            match = re.match(pattern, command, re.IGNORECASE)
            if match:
                try:
                    # Extract arguments from the regex match and call the handler
                    args = match.groups()
                    result = handler(*args) if args else handler()
                    
                    # Update command log with the result
                    if command_log and self.db_manager:
                        success = True
                        if isinstance(result, dict) and result.get("error"):
                            success = False
                            self.db_manager.store_command_log(
                                command=command,
                                output=json.dumps(result, indent=2),
                                success=success,
                                error_message=result.get("error")
                            )
                        else:
                            self.db_manager.store_command_log(
                                command=command,
                                output=json.dumps(result, indent=2),
                                success=success
                            )
                    
                    return {
                        "success": True,
                        "command": command,
                        "result": result,
                        "timestamp": datetime.now().isoformat()
                    }
                except Exception as e:
                    logger.error(f"Error processing command '{command}': {e}")
                    
                    # Update command log with the error
                    if command_log and self.db_manager:
                        self.db_manager.store_command_log(
                            command=command,
                            success=False,
                            error_message=str(e)
                        )
                    
                    return {
                        "success": False,
                        "command": command,
                        "error": str(e),
                        "timestamp": datetime.now().isoformat()
                    }
        
        # If no pattern matched, query similar commands from history
        similar_commands = []
        if self.db_manager:
            try:
                similar_logs = self.db_manager.search_similar_commands(command, limit=3)
                similar_commands = [log.command for log in similar_logs if log.success]
            except Exception as e:
                logger.error(f"Error finding similar commands: {e}")
        
        # Update command log with the error
        if command_log and self.db_manager:
            self.db_manager.store_command_log(
                command=command,
                success=False,
                error_message="Command not recognized"
            )
        
        return {
            "success": False,
            "command": command,
            "error": "Command not recognized",
            "similar_commands": similar_commands,
            "timestamp": datetime.now().isoformat()
        }
    
    # Node commands
    def list_nodes(self) -> List[Dict[str, Any]]:
        """
        List all Proxmox nodes
        
        Returns:
            List of node information dictionaries
        """
        nodes = self.proxmox.get_node_status()
        
        # Update database if available
        if self.db_manager:
            self.db_manager.update_proxmox_data('nodes', nodes)
        
        return nodes
    
    def get_node_status(self, node_name: str) -> Dict[str, Any]:
        """
        Get status for a specific node
        
        Args:
            node_name: Name of the node
            
        Returns:
            Node status information
        """
        nodes = self.proxmox.get_node_status()
        for node in nodes:
            if node['node'] == node_name:
                # Get detailed status
                node_status = self.proxmox.get_resource_usage(node_name)
                return {**node, **node_status}
        
        return {"error": f"Node {node_name} not found"}
    
    # VM commands
    def list_vms(self, node: str = None, status: str = None) -> List[Dict[str, Any]]:
        """
        List virtual machines
        
        Args:
            node: Optional node name to filter VMs
            status: Optional status filter ('running' or 'stopped')
            
        Returns:
            List of VM information dictionaries
        """
        vms = self.proxmox.get_vms(node)
        
        # Filter by status if specified
        if status:
            status = status.lower()
            vms = [vm for vm in vms if vm.get('status', '').lower() == status]
        
        # Update database if available
        if self.db_manager:
            self.db_manager.update_proxmox_data('vms', vms)
        
        return vms
    
    def get_vm_status(self, vmid: str) -> Dict[str, Any]:
        """
        Get status for a specific VM
        
        Args:
            vmid: VM ID
            
        Returns:
            VM status information
        """
        # Convert vmid to int
        vmid = int(vmid)
        
        # Find the VM in any node
        vms = self.proxmox.get_vms()
        for vm in vms:
            if vm.get('vmid') == vmid:
                node = vm.get('node')
                
                # Get detailed configuration
                config = self.proxmox.get_vm_config(node, vmid)
                return {**vm, "config": config}
        
        return {"error": f"VM {vmid} not found"}
    
    def start_vm(self, vmid: str, node: str = None) -> Dict[str, Any]:
        """
        Start a VM
        
        Args:
            vmid: VM ID
            node: Optional node name
            
        Returns:
            Operation result
        """
        # Convert vmid to int
        vmid = int(vmid)
        
        # If node is not specified, find the VM and get its node
        if not node:
            vms = self.proxmox.get_vms()
            for vm in vms:
                if vm.get('vmid') == vmid:
                    node = vm.get('node')
                    break
            
            if not node:
                return {"error": f"VM {vmid} not found"}
        
        return self.proxmox.start_vm(node, vmid)
    
    def stop_vm(self, vmid: str, node: str = None) -> Dict[str, Any]:
        """
        Stop a VM
        
        Args:
            vmid: VM ID
            node: Optional node name
            
        Returns:
            Operation result
        """
        # Convert vmid to int
        vmid = int(vmid)
        
        # If node is not specified, find the VM and get its node
        if not node:
            vms = self.proxmox.get_vms()
            for vm in vms:
                if vm.get('vmid') == vmid:
                    node = vm.get('node')
                    break
            
            if not node:
                return {"error": f"VM {vmid} not found"}
        
        return self.proxmox.stop_vm(node, vmid)
    
    def restart_vm(self, vmid: str, node: str = None) -> Dict[str, Any]:
        """
        Restart a VM
        
        Args:
            vmid: VM ID
            node: Optional node name
            
        Returns:
            Operation result
        """
        # Convert vmid to int
        vmid = int(vmid)
        
        # If node is not specified, find the VM and get its node
        if not node:
            vms = self.proxmox.get_vms()
            for vm in vms:
                if vm.get('vmid') == vmid:
                    node = vm.get('node')
                    break
            
            if not node:
                return {"error": f"VM {vmid} not found"}
        
        # First stop, then start
        stop_result = self.proxmox.stop_vm(node, vmid)
        
        # If there was an error, return it
        if "error" in stop_result:
            return stop_result
        
        # Wait a moment before starting (in a real implementation, this should be async)
        import time
        time.sleep(2)
        
        # Start the VM
        return self.proxmox.start_vm(node, vmid)
    
    # Container commands
    def list_containers(self, node: str = None, status: str = None) -> List[Dict[str, Any]]:
        """
        List containers
        
        Args:
            node: Optional node name to filter containers
            status: Optional status filter ('running' or 'stopped')
            
        Returns:
            List of container information dictionaries
        """
        containers = self.proxmox.get_containers(node)
        
        # Filter by status if specified
        if status:
            status = status.lower()
            containers = [ct for ct in containers if ct.get('status', '').lower() == status]
        
        # Update database if available
        if self.db_manager:
            self.db_manager.update_proxmox_data('containers', containers)
        
        return containers
    
    def get_container_status(self, vmid: str) -> Dict[str, Any]:
        """
        Get status for a specific container
        
        Args:
            vmid: Container ID
            
        Returns:
            Container status information
        """
        # Convert vmid to int
        vmid = int(vmid)
        
        # Find the container in any node
        containers = self.proxmox.get_containers()
        for ct in containers:
            if ct.get('vmid') == vmid:
                node = ct.get('node')
                
                # Get detailed configuration
                config = self.proxmox.get_container_config(node, vmid)
                return {**ct, "config": config}
        
        return {"error": f"Container {vmid} not found"}
    
    def start_container(self, vmid: str, node: str = None) -> Dict[str, Any]:
        """
        Start a container
        
        Args:
            vmid: Container ID
            node: Optional node name
            
        Returns:
            Operation result
        """
        # Convert vmid to int
        vmid = int(vmid)
        
        # If node is not specified, find the container and get its node
        if not node:
            containers = self.proxmox.get_containers()
            for ct in containers:
                if ct.get('vmid') == vmid:
                    node = ct.get('node')
                    break
            
            if not node:
                return {"error": f"Container {vmid} not found"}
        
        return self.proxmox.start_container(node, vmid)
    
    def stop_container(self, vmid: str, node: str = None) -> Dict[str, Any]:
        """
        Stop a container
        
        Args:
            vmid: Container ID
            node: Optional node name
            
        Returns:
            Operation result
        """
        # Convert vmid to int
        vmid = int(vmid)
        
        # If node is not specified, find the container and get its node
        if not node:
            containers = self.proxmox.get_containers()
            for ct in containers:
                if ct.get('vmid') == vmid:
                    node = ct.get('node')
                    break
            
            if not node:
                return {"error": f"Container {vmid} not found"}
        
        return self.proxmox.stop_container(node, vmid)
    
    def restart_container(self, vmid: str, node: str = None) -> Dict[str, Any]:
        """
        Restart a container
        
        Args:
            vmid: Container ID
            node: Optional node name
            
        Returns:
            Operation result
        """
        # Convert vmid to int
        vmid = int(vmid)
        
        # If node is not specified, find the container and get its node
        if not node:
            containers = self.proxmox.get_containers()
            for ct in containers:
                if ct.get('vmid') == vmid:
                    node = ct.get('node')
                    break
            
            if not node:
                return {"error": f"Container {vmid} not found"}
        
        # First stop, then start
        stop_result = self.proxmox.stop_container(node, vmid)
        
        # If there was an error, return it
        if "error" in stop_result:
            return stop_result
        
        # Wait a moment before starting (in a real implementation, this should be async)
        import time
        time.sleep(2)
        
        # Start the container
        return self.proxmox.start_container(node, vmid)
    
    # Storage commands
    def list_storage(self) -> List[Dict[str, Any]]:
        """
        List all storage resources
        
        Returns:
            List of storage information dictionaries
        """
        storage = self.proxmox.get_storage()
        
        # Update database if available
        if self.db_manager:
            self.db_manager.update_proxmox_data('storage', storage)
        
        return storage
    
    def list_node_storage(self, node: str) -> List[Dict[str, Any]]:
        """
        List storage resources for a specific node
        
        Args:
            node: Node name
            
        Returns:
            List of storage information dictionaries
        """
        storage = self.proxmox.get_storage(node)
        
        # Update database if available
        if self.db_manager:
            self.db_manager.update_proxmox_data('storage', storage)
        
        return storage
    
    # Resource usage commands
    def get_resource_usage(self, node: str) -> Dict[str, Any]:
        """
        Get resource usage for a specific node
        
        Args:
            node: Node name
            
        Returns:
            Resource usage information
        """
        return self.proxmox.get_resource_usage(node)
    
    def get_cluster_usage(self) -> Dict[str, Any]:
        """
        Get cluster-wide resource usage
        
        Returns:
            Dictionary with cluster resource usage
        """
        # Get all nodes
        nodes = self.proxmox.get_node_status()
        
        # Get resource usage for each node
        total_cpu = 0
        total_memory = 0
        total_memory_used = 0
        total_disk = 0
        total_disk_used = 0
        node_count = 0
        
        for node in nodes:
            node_name = node['node']
            try:
                usage = self.proxmox.get_resource_usage(node_name)
                
                # Some nodes might not have all metrics
                if usage:
                    total_cpu += usage.get('cpu', 0)
                    total_memory += usage.get('maxmem', 0)
                    total_memory_used += usage.get('mem', 0)
                    total_disk += usage.get('maxdisk', 0)
                    total_disk_used += usage.get('disk', 0)
                    node_count += 1
            except Exception as e:
                logger.error(f"Error getting resource usage for node {node_name}: {e}")
        
        # Calculate averages
        avg_cpu = total_cpu / node_count if node_count > 0 else 0
        
        return {
            "cluster": {
                "nodes": node_count,
                "cpu_usage": avg_cpu,
                "memory_total": total_memory,
                "memory_used": total_memory_used,
                "memory_usage": (total_memory_used / total_memory) if total_memory > 0 else 0,
                "disk_total": total_disk,
                "disk_used": total_disk_used,
                "disk_usage": (total_disk_used / total_disk) if total_disk > 0 else 0
            },
            "nodes": nodes
        }
    
    # Task commands
    def list_tasks(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        List recent tasks
        
        Args:
            limit: Maximum number of tasks to return
            
        Returns:
            List of task information dictionaries
        """
        try:
            tasks = []
            nodes = self.proxmox.get_node_status()
            
            for node in nodes:
                node_name = node['node']
                node_tasks = self.proxmox.get_tasks(node_name, limit)
                tasks.extend(node_tasks)
            
            # Sort by start time (newest first) and limit
            tasks = sorted(tasks, key=lambda t: t.get('starttime', 0), reverse=True)[:limit]
            return tasks
        except Exception as e:
            logger.error(f"Error listing tasks: {e}")
            return []
    
    def list_node_tasks(self, node: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        List recent tasks for a specific node
        
        Args:
            node: Node name
            limit: Maximum number of tasks to return
            
        Returns:
            List of task information dictionaries
        """
        try:
            return self.proxmox.get_tasks(node, limit)
        except Exception as e:
            logger.error(f"Error listing tasks for node {node}: {e}")
            return []
    
    # Snapshot commands
    def list_vm_snapshots(self, vmid: str, node: str = None) -> List[Dict[str, Any]]:
        """
        List snapshots for a VM
        
        Args:
            vmid: VM ID
            node: Optional node name
            
        Returns:
            List of snapshot information dictionaries
        """
        # Convert vmid to int
        vmid = int(vmid)
        
        # If node is not specified, find the VM and get its node
        if not node:
            vms = self.proxmox.get_vms()
            for vm in vms:
                if vm.get('vmid') == vmid:
                    node = vm.get('node')
                    break
            
            if not node:
                return {"error": f"VM {vmid} not found"}
        
        try:
            return self.proxmox.proxmox.nodes(node).qemu(vmid).snapshot.get()
        except Exception as e:
            logger.error(f"Error listing snapshots for VM {vmid}: {e}")
            return []
    
    def list_container_snapshots(self, vmid: str, node: str = None) -> List[Dict[str, Any]]:
        """
        List snapshots for a container
        
        Args:
            vmid: Container ID
            node: Optional node name
            
        Returns:
            List of snapshot information dictionaries
        """
        # Convert vmid to int
        vmid = int(vmid)
        
        # If node is not specified, find the container and get its node
        if not node:
            containers = self.proxmox.get_containers()
            for ct in containers:
                if ct.get('vmid') == vmid:
                    node = ct.get('node')
                    break
            
            if not node:
                return {"error": f"Container {vmid} not found"}
        
        try:
            return self.proxmox.proxmox.nodes(node).lxc(vmid).snapshot.get()
        except Exception as e:
            logger.error(f"Error listing snapshots for container {vmid}: {e}")
            return []
    
    # Combined resource commands
    def list_all_resources(self) -> Dict[str, Any]:
        """
        List all Proxmox resources
        
        Returns:
            Dictionary with all resource information
        """
        nodes = self.list_nodes()
        vms = self.list_vms()
        containers = self.list_containers()
        storage = self.list_storage()
        
        return {
            "nodes": nodes,
            "vms": vms,
            "containers": containers,
            "storage": storage
        }
    
    def summarize_environment(self) -> Dict[str, Any]:
        """
        Get a summary of the Proxmox environment
        
        Returns:
            Dictionary with environment summary
        """
        # Get cluster status
        cluster_status = self.proxmox.get_cluster_status()
        
        # Get all nodes
        nodes = self.list_nodes()
        
        # Get all VMs and containers
        vms = self.list_vms()
        containers = self.list_containers()
        
        # Count running and stopped VMs
        running_vms = sum(1 for vm in vms if vm.get('status') == 'running')
        stopped_vms = len(vms) - running_vms
        
        # Count running and stopped containers
        running_containers = sum(1 for ct in containers if ct.get('status') == 'running')
        stopped_containers = len(containers) - running_containers
        
        # Get storage summary
        storage = self.list_storage()
        total_storage = sum(s.get('total', 0) for s in storage)
        used_storage = sum(s.get('used', 0) for s in storage)
        
        # Calculate usage percentages
        storage_usage_percent = (used_storage / total_storage * 100) if total_storage > 0 else 0
        
        return {
            "cluster": {
                "name": cluster_status[0].get('name', 'Proxmox Cluster') if cluster_status else 'Proxmox Cluster',
                "nodes": len(nodes),
                "quorate": cluster_status[0].get('quorate', 1) if cluster_status else 1,
            },
            "resources": {
                "vms_total": len(vms),
                "vms_running": running_vms,
                "vms_stopped": stopped_vms,
                "containers_total": len(containers),
                "containers_running": running_containers,
                "containers_stopped": stopped_containers,
                "storage_total_gb": round(total_storage / (1024 ** 3), 2),
                "storage_used_gb": round(used_storage / (1024 ** 3), 2),
                "storage_usage_percent": round(storage_usage_percent, 2)
            }
        }
    
    # Ansible integration methods
    def list_ansible_playbooks(self) -> List[str]:
        """
        List all available Ansible playbooks.
        
        Returns:
            List of playbook names
        """
        return self.ansible_manager.list_playbooks()
    
    def run_ansible_playbook(self, 
                          playbook_name: str, 
                          extra_vars: Dict[str, Any] = None,
                          limit_hosts: str = None,
                          tags: List[str] = None,
                          verbose: bool = False) -> Dict[str, Any]:
        """
        Run an Ansible playbook with specified parameters.
        
        Args:
            playbook_name: Name of the playbook to run
            extra_vars: Dictionary of variables to pass to the playbook
            limit_hosts: Limit execution to specific hosts
            tags: List of tags to execute
            verbose: Enable verbose output
            
        Returns:
            Dict with results and status message
        """
        success, output = self.ansible_manager.run_playbook(
            playbook_name=playbook_name,
            extra_vars=extra_vars,
            limit_hosts=limit_hosts,
            tags=tags,
            verbose=verbose
        )
        
        result = {
            "success": success,
            "playbook": playbook_name,
            "output": output,
            "timestamp": datetime.now().isoformat()
        }
        
        # Store result in database
        self.db_manager.add_command_history(
            command=f"ansible_playbook:{playbook_name}",
            parameters=json.dumps({"extra_vars": extra_vars, "limit_hosts": limit_hosts, "tags": tags}),
            result=json.dumps(result),
            success=success
        )
        
        return result
    
    def manage_vm_with_ansible(self,
                             operation: str,
                             vm_id: Union[int, str] = None,
                             vm_name: str = None,
                             node: str = None,
                             **kwargs) -> Dict[str, Any]:
        """
        Manage VMs using Ansible playbooks.
        
        Args:
            operation: One of 'create', 'start', 'stop', 'restart', 'delete'
            vm_id: ID of the VM to manage
            vm_name: Name of the VM 
            node: Proxmox node where the VM is located
            **kwargs: Additional parameters for VM creation
            
        Returns:
            Dict with results and status message
        """
        success, output = self.ansible_manager.run_vm_management(
            operation=operation,
            vm_id=vm_id,
            vm_name=vm_name,
            node=node,
            **kwargs
        )
        
        result = {
            "success": success,
            "operation": operation,
            "vm_id": vm_id,
            "vm_name": vm_name,
            "output": output,
            "timestamp": datetime.now().isoformat()
        }
        
        # Store result in database
        self.db_manager.add_command_history(
            command=f"ansible_vm:{operation}",
            parameters=json.dumps({"vm_id": vm_id, "vm_name": vm_name, "node": node, **kwargs}),
            result=json.dumps(result),
            success=success
        )
        
        return result
    
    def manage_container_with_ansible(self,
                                   operation: str,
                                   ct_id: Union[int, str] = None,
                                   ct_hostname: str = None,
                                   node: str = None,
                                   **kwargs) -> Dict[str, Any]:
        """
        Manage containers using Ansible playbooks.
        
        Args:
            operation: One of 'create', 'start', 'stop', 'restart', 'delete'
            ct_id: ID of the container to manage
            ct_hostname: Hostname of the container
            node: Proxmox node where the container is located
            **kwargs: Additional parameters for container creation
            
        Returns:
            Dict with results and status message
        """
        success, output = self.ansible_manager.run_container_management(
            operation=operation,
            ct_id=ct_id,
            ct_hostname=ct_hostname,
            node=node,
            **kwargs
        )
        
        result = {
            "success": success,
            "operation": operation,
            "ct_id": ct_id,
            "ct_hostname": ct_hostname,
            "output": output,
            "timestamp": datetime.now().isoformat()
        }
        
        # Store result in database
        self.db_manager.add_command_history(
            command=f"ansible_container:{operation}",
            parameters=json.dumps({"ct_id": ct_id, "ct_hostname": ct_hostname, "node": node, **kwargs}),
            result=json.dumps(result),
            success=success
        )
        
        return result
    
    def manage_cluster_with_ansible(self,
                                 operation: str,
                                 target_node: str = None,
                                 source_node: str = None,
                                 cluster_name: str = None,
                                 **kwargs) -> Dict[str, Any]:
        """
        Manage Proxmox cluster using Ansible playbooks.
        
        Args:
            operation: One of 'status', 'create_cluster', 'join_cluster', 'leave_cluster', 'enable_ha'
            target_node: Target node for operations
            source_node: Source node for cluster join
            cluster_name: Name for new cluster
            **kwargs: Additional parameters
            
        Returns:
            Dict with results and status message
        """
        success, output = self.ansible_manager.run_cluster_management(
            operation=operation,
            target_node=target_node,
            source_node=source_node,
            cluster_name=cluster_name,
            **kwargs
        )
        
        result = {
            "success": success,
            "operation": operation,
            "target_node": target_node,
            "output": output,
            "timestamp": datetime.now().isoformat()
        }
        
        # Store result in database
        self.db_manager.add_command_history(
            command=f"ansible_cluster:{operation}",
            parameters=json.dumps({"target_node": target_node, "source_node": source_node, "cluster_name": cluster_name, **kwargs}),
            result=json.dumps(result),
            success=success
        )
        
        return result
