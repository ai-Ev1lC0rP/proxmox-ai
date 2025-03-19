import os
import json
from typing import Dict, List, Any, Optional, Union, Tuple
from proxmoxer import ProxmoxAPI
import re
import time

class ProxmoxClient:
    """A client for interacting with Proxmox API"""
    
    def __init__(self, host: str, token_id: str = None, token_secret: str = None,
                 username: str = None, password: str = None, 
                 verify_ssl: bool = False, port: int = 8006):
        """
        Initialize the Proxmox client
        
        Args:
            host: Proxmox host address
            token_id: Token ID for authentication
            token_secret: Token secret for authentication
            username: Username for authentication (alternative to token auth)
            password: Password for authentication (alternative to token auth)
            verify_ssl: Whether to verify SSL certificates
            port: Port number (default: 8006)
        """
        # Clean up host to ensure we don't have protocol or port included
        host = self._clean_host(host)
        
        self.host = host
        self.port = port
        self.token_id = token_id
        self.token_secret = token_secret
        self.username = username
        self.password = password
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
            # Token-based authentication
            if self.token_id and self.token_secret:
                return ProxmoxAPI(
                    host=self.host,
                    port=self.port,
                    user=self.token_id,
                    token_name=self.token_id.split('!')[1] if '!' in self.token_id else None,
                    token_value=self.token_secret,
                    verify_ssl=self.verify_ssl
                )
            # Username/password authentication
            elif self.username and self.password:
                return ProxmoxAPI(
                    host=self.host,
                    port=self.port,
                    user=self.username,
                    password=self.password,
                    verify_ssl=self.verify_ssl
                )
            else:
                raise ValueError("Either token authentication or username/password authentication must be provided")
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
    
    def shutdown_vm(self, node: str, vmid: int, timeout: int = 60) -> Dict:
        """Gracefully shutdown a VM"""
        try:
            return self.proxmox.nodes(node).qemu(vmid).status.shutdown.post(timeout=timeout)
        except Exception as e:
            print(f"Failed to shutdown VM: {e}")
            return {"error": str(e)}
    
    def reset_vm(self, node: str, vmid: int) -> Dict:
        """Reset a VM"""
        try:
            return self.proxmox.nodes(node).qemu(vmid).status.reset.post()
        except Exception as e:
            print(f"Failed to reset VM: {e}")
            return {"error": str(e)}
    
    def suspend_vm(self, node: str, vmid: int) -> Dict:
        """Suspend a VM"""
        try:
            return self.proxmox.nodes(node).qemu(vmid).status.suspend.post()
        except Exception as e:
            print(f"Failed to suspend VM: {e}")
            return {"error": str(e)}
    
    def resume_vm(self, node: str, vmid: int) -> Dict:
        """Resume a suspended VM"""
        try:
            return self.proxmox.nodes(node).qemu(vmid).status.resume.post()
        except Exception as e:
            print(f"Failed to resume VM: {e}")
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
    
    def shutdown_container(self, node: str, vmid: int, timeout: int = 60) -> Dict:
        """Gracefully shutdown a container"""
        try:
            return self.proxmox.nodes(node).lxc(vmid).status.shutdown.post(timeout=timeout)
        except Exception as e:
            print(f"Failed to shutdown container: {e}")
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
    
    def list_vm_snapshots(self, node: str, vmid: int) -> List[Dict]:
        """List all snapshots for a VM"""
        try:
            return self.proxmox.nodes(node).qemu(vmid).snapshot.get()
        except Exception as e:
            print(f"Failed to list VM snapshots: {e}")
            return []
    
    def list_container_snapshots(self, node: str, vmid: int) -> List[Dict]:
        """List all snapshots for a container"""
        try:
            return self.proxmox.nodes(node).lxc(vmid).snapshot.get()
        except Exception as e:
            print(f"Failed to list container snapshots: {e}")
            return []
    
    def rollback_vm_snapshot(self, node: str, vmid: int, snapshot: str) -> Dict:
        """Rollback a VM to a snapshot"""
        try:
            return self.proxmox.nodes(node).qemu(vmid).snapshot(snapshot).rollback.post()
        except Exception as e:
            print(f"Failed to rollback VM snapshot: {e}")
            return {"error": str(e)}
    
    def rollback_container_snapshot(self, node: str, vmid: int, snapshot: str) -> Dict:
        """Rollback a container to a snapshot"""
        try:
            return self.proxmox.nodes(node).lxc(vmid).snapshot(snapshot).rollback.post()
        except Exception as e:
            print(f"Failed to rollback container snapshot: {e}")
            return {"error": str(e)}
    
    def delete_vm_snapshot(self, node: str, vmid: int, snapshot: str) -> Dict:
        """Delete a VM snapshot"""
        try:
            return self.proxmox.nodes(node).qemu(vmid).snapshot(snapshot).delete()
        except Exception as e:
            print(f"Failed to delete VM snapshot: {e}")
            return {"error": str(e)}
    
    def delete_container_snapshot(self, node: str, vmid: int, snapshot: str) -> Dict:
        """Delete a container snapshot"""
        try:
            return self.proxmox.nodes(node).lxc(vmid).snapshot(snapshot).delete()
        except Exception as e:
            print(f"Failed to delete container snapshot: {e}")
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
    
    def clone_vm(self, node: str, vmid: int, newid: int, name: str, target_node: str = None, 
                full: bool = False, storage: str = None) -> Dict:
        """
        Clone a VM
        
        Args:
            node: Source node
            vmid: Source VM ID
            newid: New VM ID
            name: Name for the new VM
            target_node: Target node (default: same as source)
            full: Create a full clone (default: False)
            storage: Target storage for full clone (default: same as source)
            
        Returns:
            Task information
        """
        try:
            params = {
                "newid": newid,
                "name": name,
                "full": 1 if full else 0
            }
            
            if target_node:
                params["target"] = target_node
                
            if storage and full:
                params["storage"] = storage
                
            return self.proxmox.nodes(node).qemu(vmid).clone.post(**params)
        except Exception as e:
            print(f"Failed to clone VM: {e}")
            return {"error": str(e)}
    
    def create_vm(self, node: str, vmid: int, name: str, memory: int = 512, cores: int = 1, 
                 storage: str = None, iso: str = None, net0: str = None) -> Dict:
        """
        Create a new VM
        
        Args:
            node: Node to create VM on
            vmid: VM ID
            name: VM name
            memory: Memory in MB (default: 512)
            cores: Number of CPU cores (default: 1)
            storage: Storage name
            iso: ISO image to use
            net0: Network interface configuration
            
        Returns:
            Task information
        """
        try:
            params = {
                "vmid": vmid,
                "name": name,
                "memory": memory,
                "cores": cores
            }
            
            if storage:
                params["storage"] = storage
                
            if iso:
                params["iso"] = iso
                
            if net0:
                params["net0"] = net0
                
            return self.proxmox.nodes(node).qemu.post(**params)
        except Exception as e:
            print(f"Failed to create VM: {e}")
            return {"error": str(e)}
    
    def create_container(self, node: str, vmid: int, ostemplate: str, storage: str, 
                       memory: int = 512, swap: int = 512, cores: int = 1, password: str = None,
                       hostname: str = None, net0: str = None, rootfs: str = None) -> Dict:
        """
        Create a new container
        
        Args:
            node: Node to create container on
            vmid: Container ID
            ostemplate: OS template to use
            storage: Storage for container
            memory: Memory in MB (default: 512)
            swap: Swap in MB (default: 512)
            cores: Number of CPU cores (default: 1)
            password: Root password
            hostname: Container hostname
            net0: Network interface configuration
            rootfs: Root filesystem configuration
            
        Returns:
            Task information
        """
        try:
            params = {
                "vmid": vmid,
                "ostemplate": ostemplate,
                "storage": storage,
                "memory": memory,
                "swap": swap,
                "cores": cores
            }
            
            if password:
                params["password"] = password
                
            if hostname:
                params["hostname"] = hostname
                
            if net0:
                params["net0"] = net0
                
            if rootfs:
                params["rootfs"] = rootfs
                
            return self.proxmox.nodes(node).lxc.post(**params)
        except Exception as e:
            print(f"Failed to create container: {e}")
            return {"error": str(e)}
    
    def delete_vm(self, node: str, vmid: int, purge: bool = True) -> Dict:
        """
        Delete a VM
        
        Args:
            node: Node name
            vmid: VM ID
            purge: Remove from all related configurations (default: True)
            
        Returns:
            Task information
        """
        try:
            params = {}
            if purge:
                params["purge"] = 1
                
            return self.proxmox.nodes(node).qemu(vmid).delete(**params)
        except Exception as e:
            print(f"Failed to delete VM: {e}")
            return {"error": str(e)}
    
    def delete_container(self, node: str, vmid: int, purge: bool = True) -> Dict:
        """
        Delete a container
        
        Args:
            node: Node name
            vmid: Container ID
            purge: Remove from all related configurations (default: True)
            
        Returns:
            Task information
        """
        try:
            params = {}
            if purge:
                params["purge"] = 1
                
            return self.proxmox.nodes(node).lxc(vmid).delete(**params)
        except Exception as e:
            print(f"Failed to delete container: {e}")
            return {"error": str(e)}

    def get_vm_status(self, node: str, vmid: int) -> Dict:
        """Get status information for a VM"""
        try:
            return self.proxmox.nodes(node).qemu(vmid).status.current.get()
        except Exception as e:
            print(f"Failed to get VM status: {e}")
            return {}
    
    def get_container_status(self, node: str, vmid: int) -> Dict:
        """Get status information for a container"""
        try:
            return self.proxmox.nodes(node).lxc(vmid).status.current.get()
        except Exception as e:
            print(f"Failed to get container status: {e}")
            return {}
    
    def get_storages(self) -> List[Dict]:
        """Get all storage definitions in the cluster"""
        try:
            return self.proxmox.storage.get()
        except Exception as e:
            print(f"Failed to get storages: {e}")
            return []
    
    def get_pools(self) -> List[Dict]:
        """Get all pools in the cluster"""
        try:
            return self.proxmox.pools.get()
        except Exception as e:
            print(f"Failed to get pools: {e}")
            return []
    
    def create_pool(self, poolid: str, comment: str = None) -> Dict:
        """Create a new pool"""
        try:
            params = {"poolid": poolid}
            if comment:
                params["comment"] = comment
                
            return self.proxmox.pools.post(**params)
        except Exception as e:
            print(f"Failed to create pool: {e}")
            return {"error": str(e)}
    
    def get_pool(self, poolid: str) -> Dict:
        """Get pool information and members"""
        try:
            return self.proxmox.pools(poolid).get()
        except Exception as e:
            print(f"Failed to get pool: {e}")
            return {}
    
    def get_next_vmid(self) -> int:
        """Get the next available VMID"""
        try:
            return int(self.proxmox.cluster.nextid.get())
        except Exception as e:
            print(f"Failed to get next VMID: {e}")
            return 0
    
    def wait_for_task(self, node: str, upid: str, timeout: int = 300, interval: int = 1) -> Tuple[bool, Dict]:
        """
        Wait for a task to complete
        
        Args:
            node: Node name
            upid: Task UPID
            timeout: Timeout in seconds (default: 300)
            interval: Check interval in seconds (default: 1)
            
        Returns:
            Tuple of (success, task_details)
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                status = self.proxmox.nodes(node).tasks(upid).status.get()
                if status.get("status") == "stopped":
                    exitstatus = status.get("exitstatus", "")
                    if exitstatus == "OK":
                        return True, status
                    else:
                        return False, status
            except Exception as e:
                print(f"Error checking task status: {e}")
                return False, {"error": str(e)}
                
            time.sleep(interval)
            
        return False, {"error": "Timeout waiting for task to complete"}
    
    def update_vm_config(self, node: str, vmid: int, **params) -> Dict:
        """
        Update VM configuration
        
        Args:
            node: Node name
            vmid: VM ID
            **params: Configuration parameters to update
            
        Returns:
            Task information
        """
        try:
            return self.proxmox.nodes(node).qemu(vmid).config.put(**params)
        except Exception as e:
            print(f"Failed to update VM config: {e}")
            return {"error": str(e)}
    
    def update_container_config(self, node: str, vmid: int, **params) -> Dict:
        """
        Update container configuration
        
        Args:
            node: Node name
            vmid: Container ID
            **params: Configuration parameters to update
            
        Returns:
            Task information
        """
        try:
            return self.proxmox.nodes(node).lxc(vmid).config.put(**params)
        except Exception as e:
            print(f"Failed to update container config: {e}")
            return {"error": str(e)}
    
    def get_system_info(self, node: str) -> Dict:
        """Get system information for a node"""
        try:
            return self.proxmox.nodes(node).system.get()
        except Exception as e:
            print(f"Failed to get system info: {e}")
            return {}
    
    def get_node_network(self, node: str) -> List[Dict]:
        """Get network configuration for a node"""
        try:
            return self.proxmox.nodes(node).network.get()
        except Exception as e:
            print(f"Failed to get network configuration: {e}")
            return []

    def get_vm_rrd_data(self, node: str, vmid: int, timeframe: str = "hour") -> Dict:
        """
        Get VM performance statistics
        
        Args:
            node: Node name
            vmid: VM ID
            timeframe: Timeframe (hour, day, week, month, year)
            
        Returns:
            Performance data
        """
        try:
            return self.proxmox.nodes(node).qemu(vmid).rrddata.get(timeframe=timeframe)
        except Exception as e:
            print(f"Failed to get VM RRD data: {e}")
            return {}
    
    def get_container_rrd_data(self, node: str, vmid: int, timeframe: str = "hour") -> Dict:
        """
        Get container performance statistics
        
        Args:
            node: Node name
            vmid: Container ID
            timeframe: Timeframe (hour, day, week, month, year)
            
        Returns:
            Performance data
        """
        try:
            return self.proxmox.nodes(node).lxc(vmid).rrddata.get(timeframe=timeframe)
        except Exception as e:
            print(f"Failed to get container RRD data: {e}")
            return {}
    
    def get_node_rrd_data(self, node: str, timeframe: str = "hour") -> Dict:
        """
        Get node performance statistics
        
        Args:
            node: Node name
            timeframe: Timeframe (hour, day, week, month, year)
            
        Returns:
            Performance data
        """
        try:
            return self.proxmox.nodes(node).rrddata.get(timeframe=timeframe)
        except Exception as e:
            print(f"Failed to get node RRD data: {e}")
            return {}
    
    def get_backup_schedule(self) -> List[Dict]:
        """Get the backup schedules"""
        try:
            return self.proxmox.cluster.backup.get()
        except Exception as e:
            print(f"Failed to get backup schedule: {e}")
            return []
    
    def create_backup_schedule(self, id: str, schedule: str, storage: str, mode: str = "snapshot",
                             compress: str = "zstd", node: str = None, vmid: str = None) -> Dict:
        """
        Create a backup schedule
        
        Args:
            id: Backup job ID
            schedule: Backup schedule (cron format)
            storage: Storage for backup
            mode: Backup mode (default: snapshot)
            compress: Compression algorithm (default: zstd)
            node: Limit to specified node
            vmid: Limit to specified VMs
            
        Returns:
            Job information
        """
        try:
            params = {
                "id": id,
                "schedule": schedule,
                "storage": storage,
                "mode": mode,
                "compress": compress
            }
            
            if node:
                params["node"] = node
                
            if vmid:
                params["vmid"] = vmid
                
            return self.proxmox.cluster.backup.post(**params)
        except Exception as e:
            print(f"Failed to create backup schedule: {e}")
            return {"error": str(e)}
    
    def restore_backup(self, node: str, vmid: int, archive: str, storage: str = None) -> Dict:
        """
        Restore from backup
        
        Args:
            node: Node name
            vmid: Target VM ID
            archive: Backup archive to restore from
            storage: Target storage for disks (default: origin)
            
        Returns:
            Task information
        """
        try:
            params = {
                "archive": archive,
            }
            
            if storage:
                params["storage"] = storage
                
            return self.proxmox.nodes(node).qemu(vmid).restore.post(**params)
        except Exception as e:
            print(f"Failed to restore backup: {e}")
            return {"error": str(e)}
    
    def get_users(self) -> List[Dict]:
        """Get all users"""
        try:
            return self.proxmox.access.users.get()
        except Exception as e:
            print(f"Failed to get users: {e}")
            return []
    
    def create_user(self, userid: str, password: str = None, email: str = None, 
                   expire: int = None, groups: List[str] = None) -> Dict:
        """
        Create a new user
        
        Args:
            userid: User ID
            password: Password
            email: Email
            expire: Expiration timestamp
            groups: List of groups
            
        Returns:
            User information
        """
        try:
            params = {"userid": userid}
            
            if password:
                params["password"] = password
                
            if email:
                params["email"] = email
                
            if expire:
                params["expire"] = expire
                
            if groups:
                params["groups"] = ",".join(groups)
                
            return self.proxmox.access.users.post(**params)
        except Exception as e:
            print(f"Failed to create user: {e}")
            return {"error": str(e)}
    
    def get_groups(self) -> List[Dict]:
        """Get all groups"""
        try:
            return self.proxmox.access.groups.get()
        except Exception as e:
            print(f"Failed to get groups: {e}")
            return []
    
    def get_acl(self) -> List[Dict]:
        """Get all permissions (ACLs)"""
        try:
            return self.proxmox.access.acl.get()
        except Exception as e:
            print(f"Failed to get ACLs: {e}")
            return []
    
    def get_qemu_agent_info(self, node: str, vmid: int, command: str = "info") -> Dict:
        """
        Get VM guest information via QEMU Guest Agent
        
        Args:
            node: Node name
            vmid: VM ID
            command: QEMU agent command (default: info)
            
        Returns:
            Guest agent information
        """
        try:
            return self.proxmox.nodes(node).qemu(vmid).agent.get(command=command)
        except Exception as e:
            print(f"Failed to get QEMU agent info: {e}")
            return {"error": str(e)}
    
    def get_vm_firewall_rules(self, node: str, vmid: int) -> List[Dict]:
        """Get firewall rules for a VM"""
        try:
            return self.proxmox.nodes(node).qemu(vmid).firewall.rules.get()
        except Exception as e:
            print(f"Failed to get VM firewall rules: {e}")
            return []
    
    def get_container_firewall_rules(self, node: str, vmid: int) -> List[Dict]:
        """Get firewall rules for a container"""
        try:
            return self.proxmox.nodes(node).lxc(vmid).firewall.rules.get()
        except Exception as e:
            print(f"Failed to get container firewall rules: {e}")
            return []
    
    def add_vm_firewall_rule(self, node: str, vmid: int, rule: Dict) -> Dict:
        """
        Add firewall rule to a VM
        
        Args:
            node: Node name
            vmid: VM ID
            rule: Firewall rule definition
            
        Returns:
            Task information
        """
        try:
            return self.proxmox.nodes(node).qemu(vmid).firewall.rules.post(**rule)
        except Exception as e:
            print(f"Failed to add VM firewall rule: {e}")
            return {"error": str(e)}
    
    def add_container_firewall_rule(self, node: str, vmid: int, rule: Dict) -> Dict:
        """
        Add firewall rule to a container
        
        Args:
            node: Node name
            vmid: Container ID
            rule: Firewall rule definition
            
        Returns:
            Task information
        """
        try:
            return self.proxmox.nodes(node).lxc(vmid).firewall.rules.post(**rule)
        except Exception as e:
            print(f"Failed to add container firewall rule: {e}")
            return {"error": str(e)}
