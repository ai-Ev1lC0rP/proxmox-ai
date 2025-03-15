import os
import json
from typing import Dict, List, Any, Optional, Union
from proxmoxer import ProxmoxAPI
import re

class ProxmoxClient:
    """A client for interacting with Proxmox API"""
    
    def __init__(self, host: str, token_id: str, token_secret: str, 
                 verify_ssl: bool = False, port: int = 8006):
        """
        Initialize the Proxmox client
        
        Args:
            host: Proxmox host address
            token_id: Token ID for authentication
            token_secret: Token secret for authentication
            verify_ssl: Whether to verify SSL certificates
            port: Port number (default: 8006)
        """
        # Clean up host to ensure we don't have protocol or port included
        host = self._clean_host(host)
        
        self.host = host
        self.port = port
        self.token_id = token_id
        self.token_secret = token_secret
        self.verify_ssl = verify_ssl
        
        self.proxmox = self._connect()
        
    def _clean_host(self, host: str) -> str:
        """Remove protocol and port from host if present"""
        # Remove protocol (http:// or https://)
        host = re.sub(r'^https?://', '', host)
        # Remove port (e.g., :8006)
        host = re.sub(r':\d+$', '', host)
        return host
        
    def _connect(self) -> ProxmoxAPI:
        """Connect to Proxmox API"""
        try:
            return ProxmoxAPI(
                host=self.host,
                port=self.port,
                user=self.token_id,
                token_name=self.token_id.split('!')[1] if '!' in self.token_id else None,
                token_value=self.token_secret,
                verify_ssl=self.verify_ssl
            )
        except Exception as e:
            print(f"Failed to connect to Proxmox API: {e}")
            raise
    
    def get_node_status(self) -> Dict:
        """Get the status of all nodes"""
        try:
            return self.proxmox.nodes.get()
        except Exception as e:
            print(f"Failed to get node status: {e}")
            return {}
    
    def get_vms(self, node: str = None) -> List[Dict]:
        """Get all VMs on a specific node or all nodes"""
        try:
            if node:
                return self.proxmox.nodes(node).qemu.get()
            else:
                vms = []
                for node_data in self.proxmox.nodes.get():
                    node_name = node_data['node']
                    vms.extend(self.proxmox.nodes(node_name).qemu.get())
                return vms
        except Exception as e:
            print(f"Failed to get VMs: {e}")
            return []
    
    def get_containers(self, node: str = None) -> List[Dict]:
        """Get all containers on a specific node or all nodes"""
        try:
            if node:
                return self.proxmox.nodes(node).lxc.get()
            else:
                containers = []
                for node_data in self.proxmox.nodes.get():
                    node_name = node_data['node']
                    containers.extend(self.proxmox.nodes(node_name).lxc.get())
                return containers
        except Exception as e:
            print(f"Failed to get containers: {e}")
            return []
    
    def get_storage(self, node: str = None) -> List[Dict]:
        """Get storage information for a specific node or all nodes"""
        try:
            if node:
                return self.proxmox.nodes(node).storage.get()
            else:
                storage = []
                for node_data in self.proxmox.nodes.get():
                    node_name = node_data['node']
                    storage.extend(self.proxmox.nodes(node_name).storage.get())
                return storage
        except Exception as e:
            print(f"Failed to get storage info: {e}")
            return []
    
    def get_vm_config(self, node: str, vmid: int) -> Dict:
        """Get VM configuration"""
        try:
            return self.proxmox.nodes(node).qemu(vmid).config.get()
        except Exception as e:
            print(f"Failed to get VM config: {e}")
            return {}
    
    def get_container_config(self, node: str, vmid: int) -> Dict:
        """Get container configuration"""
        try:
            return self.proxmox.nodes(node).lxc(vmid).config.get()
        except Exception as e:
            print(f"Failed to get container config: {e}")
            return {}
    
    def start_vm(self, node: str, vmid: int) -> Dict:
        """Start a VM"""
        try:
            return self.proxmox.nodes(node).qemu(vmid).status.start.post()
        except Exception as e:
            print(f"Failed to start VM: {e}")
            return {"error": str(e)}
    
    def stop_vm(self, node: str, vmid: int) -> Dict:
        """Stop a VM"""
        try:
            return self.proxmox.nodes(node).qemu(vmid).status.stop.post()
        except Exception as e:
            print(f"Failed to stop VM: {e}")
            return {"error": str(e)}
    
    def start_container(self, node: str, vmid: int) -> Dict:
        """Start a container"""
        try:
            return self.proxmox.nodes(node).lxc(vmid).status.start.post()
        except Exception as e:
            print(f"Failed to start container: {e}")
            return {"error": str(e)}
    
    def stop_container(self, node: str, vmid: int) -> Dict:
        """Stop a container"""
        try:
            return self.proxmox.nodes(node).lxc(vmid).status.stop.post()
        except Exception as e:
            print(f"Failed to stop container: {e}")
            return {"error": str(e)}
    
    def get_resource_usage(self, node: str) -> Dict:
        """Get resource usage for a node"""
        try:
            return self.proxmox.nodes(node).status.get()
        except Exception as e:
            print(f"Failed to get resource usage: {e}")
            return {}
    
    def create_vm_snapshot(self, node: str, vmid: int, name: str, description: str = None) -> Dict:
        """Create a VM snapshot"""
        try:
            data = {
                "snapname": name,
            }
            if description:
                data["description"] = description
                
            return self.proxmox.nodes(node).qemu(vmid).snapshot.post(**data)
        except Exception as e:
            print(f"Failed to create VM snapshot: {e}")
            return {"error": str(e)}
    
    def create_container_snapshot(self, node: str, vmid: int, name: str, description: str = None) -> Dict:
        """Create a container snapshot"""
        try:
            data = {
                "snapname": name,
            }
            if description:
                data["description"] = description
                
            return self.proxmox.nodes(node).lxc(vmid).snapshot.post(**data)
        except Exception as e:
            print(f"Failed to create container snapshot: {e}")
            return {"error": str(e)}
            
    def get_cluster_status(self) -> Dict:
        """Get cluster status"""
        try:
            return self.proxmox.cluster.status.get()
        except Exception as e:
            print(f"Failed to get cluster status: {e}")
            return {}
    
    def get_tasks(self, node: str = None, limit: int = 10) -> List[Dict]:
        """Get recent tasks"""
        try:
            if node:
                return self.proxmox.nodes(node).tasks.get(limit=limit)
            else:
                tasks = []
                for node_data in self.proxmox.nodes.get():
                    node_name = node_data['node']
                    tasks.extend(self.proxmox.nodes(node_name).tasks.get(limit=limit))
                return tasks[:limit]  # Limit the combined results
        except Exception as e:
            print(f"Failed to get tasks: {e}")
            return []
