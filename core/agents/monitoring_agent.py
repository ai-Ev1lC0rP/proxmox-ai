"""
Monitoring agent for Proxmox VE environments.
Provides comprehensive monitoring and analytics of Proxmox nodes, VMs, and containers.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime, timedelta
import time

from core.client import ProxmoxClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("monitoring_agent")


class ProxmoxMonitoringAgent:
    """
    Agent for monitoring Proxmox VE environments.
    Tracks performance metrics, resource utilization, and system health.
    """
    
    def __init__(self, proxmox_client: ProxmoxClient):
        """
        Initialize the Monitoring agent.
        
        Args:
            proxmox_client: Initialized ProxmoxClient instance
        """
        self.proxmox_client = proxmox_client
        
    def get_cluster_status(self) -> Dict[str, Any]:
        """
        Get overall cluster status and health metrics.
        
        Returns:
            Dictionary with cluster status information
        """
        try:
            # Get cluster resources
            resources = self.proxmox_client.proxmox.cluster.resources.get()
            
            # Get cluster status
            status = self.proxmox_client.proxmox.cluster.status.get()
            
            # Get cluster nodes
            nodes = self.proxmox_client.get_node_status()
            
            # Process and categorize resources
            vms = [r for r in resources if r.get('type') == 'qemu']
            containers = [r for r in resources if r.get('type') == 'lxc']
            storages = [r for r in resources if r.get('type') == 'storage']
            
            # Calculate summary metrics
            total_vms = len(vms)
            total_containers = len(containers)
            total_nodes = len(nodes)
            
            # Calculate resource utilization
            cpu_usage = sum(float(r.get('cpu', 0)) for r in resources if 'cpu' in r)
            memory_usage = sum(float(r.get('mem', 0)) for r in resources if 'mem' in r)
            memory_total = sum(float(r.get('maxmem', 0)) for r in resources if 'maxmem' in r)
            
            # Storage usage
            storage_usage = sum(float(r.get('disk', 0)) for r in storages if 'disk' in r)
            storage_total = sum(float(r.get('maxdisk', 0)) for r in storages if 'maxdisk' in r)
            
            # Format as percentages if total available
            cpu_percent = None  # Not easily accessible as a cluster total
            memory_percent = (memory_usage / memory_total * 100) if memory_total > 0 else None
            storage_percent = (storage_usage / storage_total * 100) if storage_total > 0 else None
            
            # Return compiled cluster status
            return {
                "cluster_name": status[0]['name'] if status and len(status) > 0 else "Unknown",
                "nodes": {
                    "total": total_nodes,
                    "online": sum(1 for n in nodes if n['status'] == 'online'),
                    "detailed": [{"name": n['node'], "status": n['status']} for n in nodes]
                },
                "vms": {
                    "total": total_vms,
                    "running": sum(1 for vm in vms if vm.get('status') == 'running'),
                    "stopped": sum(1 for vm in vms if vm.get('status') == 'stopped')
                },
                "containers": {
                    "total": total_containers,
                    "running": sum(1 for ct in containers if ct.get('status') == 'running'),
                    "stopped": sum(1 for ct in containers if ct.get('status') == 'stopped')
                },
                "resources": {
                    "cpu": {
                        "usage_percent": cpu_percent,
                        "usage": cpu_usage
                    },
                    "memory": {
                        "usage_bytes": memory_usage,
                        "total_bytes": memory_total,
                        "usage_percent": memory_percent
                    },
                    "storage": {
                        "usage_bytes": storage_usage,
                        "total_bytes": storage_total,
                        "usage_percent": storage_percent
                    }
                },
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting cluster status: {str(e)}")
            return {"error": str(e), "timestamp": datetime.now().isoformat()}
    
    def get_node_metrics(self, node: str) -> Dict[str, Any]:
        """
        Get detailed metrics for a specific node.
        
        Args:
            node: Node name
            
        Returns:
            Dictionary with node metrics
        """
        try:
            # Get node status
            status = self.proxmox_client.proxmox.nodes(node).status.get()
            
            # Get node RRD data (more detailed metrics)
            rrd_data = self.proxmox_client.proxmox.nodes(node).rrddata.get()
            
            # Get network interfaces
            network = self.proxmox_client.proxmox.nodes(node).network.get()
            
            # Get storage status
            storage = self.proxmox_client.proxmox.nodes(node).storage.get()
            
            # Calculate node health
            load_avg = status.get('loadavg', [0, 0, 0])
            memory_usage = status.get('memory', {}).get('used', 0)
            memory_total = status.get('memory', {}).get('total', 1)  # Default to 1 to avoid div by zero
            memory_percent = (memory_usage / memory_total) * 100
            
            # Node health status based on metrics
            health_status = "healthy"
            if load_avg[0] > status.get('cpuinfo', {}).get('cpus', 1) * 1.5:
                health_status = "warning"  # High load
            if memory_percent > 90:
                health_status = "warning"  # High memory usage
                
            # Disk health
            disk_health = "healthy"
            for s in storage:
                if s.get('active') == 0:
                    disk_health = "warning"  # Inactive storage
                if s.get('avail') and s.get('total') and (s.get('avail') / s.get('total')) < 0.1:
                    disk_health = "critical"  # Less than 10% space available
            
            # Format network interfaces
            network_info = []
            for iface in network:
                if 'name' in iface:
                    network_info.append({
                        "name": iface.get('name'),
                        "type": iface.get('type'),
                        "active": iface.get('active', False),
                        "address": iface.get('address', None),
                        "netmask": iface.get('netmask', None)
                    })
            
            # Return compiled node metrics
            return {
                "node": node,
                "uptime": status.get('uptime'),
                "health": {
                    "status": health_status,
                    "disk_health": disk_health
                },
                "cpu": {
                    "cores": status.get('cpuinfo', {}).get('cpus', 0),
                    "load_avg": load_avg,
                    "utilization_percent": next((item['value'] for item in rrd_data if item.get('metric') == 'cpu'), None)
                },
                "memory": {
                    "total_bytes": memory_total,
                    "used_bytes": memory_usage,
                    "used_percent": memory_percent
                },
                "network": {
                    "interfaces": network_info,
                    "traffic": {
                        "in_bytes": next((item['value'] for item in rrd_data if item.get('metric') == 'netin'), None),
                        "out_bytes": next((item['value'] for item in rrd_data if item.get('metric') == 'netout'), None)
                    }
                },
                "storage": [
                    {
                        "storage": s.get('storage'),
                        "type": s.get('type'),
                        "active": s.get('active') == 1,
                        "used_bytes": s.get('used'),
                        "total_bytes": s.get('total'),
                        "used_percent": (s.get('used', 0) / s.get('total', 1)) * 100 if s.get('total') else None
                    }
                    for s in storage
                ],
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting node metrics for {node}: {str(e)}")
            return {"node": node, "error": str(e), "timestamp": datetime.now().isoformat()}
    
    def get_vm_performance(self, node: str, vmid: int) -> Dict[str, Any]:
        """
        Get detailed performance metrics for a specific VM.
        
        Args:
            node: Node name
            vmid: VM ID
            
        Returns:
            Dictionary with VM performance metrics
        """
        try:
            # Get VM status
            status = self.proxmox_client.proxmox.nodes(node).qemu(vmid).status.current.get()
            
            # Get VM RRD data (historical performance)
            rrd_data = self.proxmox_client.proxmox.nodes(node).qemu(vmid).rrddata.get()
            
            # Get VM config
            config = self.proxmox_client.get_vm_config(node, vmid)
            
            # Format running status
            running = status.get('status') == 'running'
            
            # Process RRD data for different metrics
            cpu_usage = next((item['value'] for item in rrd_data if item.get('metric') == 'cpu'), None)
            memory_usage = next((item['value'] for item in rrd_data if item.get('metric') == 'mem'), None)
            disk_read = next((item['value'] for item in rrd_data if item.get('metric') == 'diskread'), None)
            disk_write = next((item['value'] for item in rrd_data if item.get('metric') == 'diskwrite'), None)
            net_in = next((item['value'] for item in rrd_data if item.get('metric') == 'netin'), None)
            net_out = next((item['value'] for item in rrd_data if item.get('metric') == 'netout'), None)
            
            # Calculate performance health
            health_status = "healthy"
            if cpu_usage and cpu_usage > 90:
                health_status = "warning"  # High CPU usage
            if memory_usage and memory_usage > 90:
                health_status = "warning"  # High memory usage
            
            # Return compiled VM performance data
            return {
                "vm": {
                    "id": vmid,
                    "name": config.get('name', f"vm-{vmid}"),
                    "status": status.get('status'),
                    "running": running,
                    "ha_state": status.get('ha', {}).get('managed', 'unmanaged'),
                    "uptime": status.get('uptime') if running else 0
                },
                "performance": {
                    "health": health_status,
                    "cpu": {
                        "cores": config.get('cores', 1),
                        "usage_percent": cpu_usage
                    },
                    "memory": {
                        "allocated_bytes": status.get('maxmem'),
                        "used_bytes": status.get('mem'),
                        "used_percent": memory_usage
                    },
                    "disk": {
                        "read_bytes": disk_read,
                        "write_bytes": disk_write
                    },
                    "network": {
                        "in_bytes": net_in,
                        "out_bytes": net_out
                    }
                },
                "snapshots": len(self.proxmox_client.proxmox.nodes(node).qemu(vmid).snapshot.get()),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting VM performance for VM {vmid} on node {node}: {str(e)}")
            return {"vmid": vmid, "node": node, "error": str(e), "timestamp": datetime.now().isoformat()}
    
    def get_container_performance(self, node: str, vmid: int) -> Dict[str, Any]:
        """
        Get detailed performance metrics for a specific container.
        
        Args:
            node: Node name
            vmid: Container ID
            
        Returns:
            Dictionary with container performance metrics
        """
        try:
            # Get container status
            status = self.proxmox_client.proxmox.nodes(node).lxc(vmid).status.current.get()
            
            # Get container RRD data (historical performance)
            rrd_data = self.proxmox_client.proxmox.nodes(node).lxc(vmid).rrddata.get()
            
            # Get container config
            config = self.proxmox_client.get_container_config(node, vmid)
            
            # Format running status
            running = status.get('status') == 'running'
            
            # Process RRD data for different metrics
            cpu_usage = next((item['value'] for item in rrd_data if item.get('metric') == 'cpu'), None)
            memory_usage = next((item['value'] for item in rrd_data if item.get('metric') == 'mem'), None)
            disk_read = next((item['value'] for item in rrd_data if item.get('metric') == 'diskread'), None)
            disk_write = next((item['value'] for item in rrd_data if item.get('metric') == 'diskwrite'), None)
            net_in = next((item['value'] for item in rrd_data if item.get('metric') == 'netin'), None)
            net_out = next((item['value'] for item in rrd_data if item.get('metric') == 'netout'), None)
            
            # Calculate performance health
            health_status = "healthy"
            if cpu_usage and cpu_usage > 90:
                health_status = "warning"  # High CPU usage
            if memory_usage and memory_usage > 90:
                health_status = "warning"  # High memory usage
            
            # Return compiled container performance data
            return {
                "container": {
                    "id": vmid,
                    "name": config.get('hostname', f"ct-{vmid}"),
                    "status": status.get('status'),
                    "running": running,
                    "uptime": status.get('uptime') if running else 0
                },
                "performance": {
                    "health": health_status,
                    "cpu": {
                        "cores": config.get('cores', 1),
                        "usage_percent": cpu_usage
                    },
                    "memory": {
                        "allocated_bytes": status.get('maxmem'),
                        "used_bytes": status.get('mem'),
                        "used_percent": memory_usage
                    },
                    "disk": {
                        "read_bytes": disk_read,
                        "write_bytes": disk_write
                    },
                    "network": {
                        "in_bytes": net_in,
                        "out_bytes": net_out
                    }
                },
                "snapshots": len(self.proxmox_client.proxmox.nodes(node).lxc(vmid).snapshot.get()),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting container performance for CT {vmid} on node {node}: {str(e)}")
            return {"vmid": vmid, "node": node, "error": str(e), "timestamp": datetime.now().isoformat()}
    
    def monitor_tasks(self, node: str = None, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Monitor recent tasks across the cluster or on a specific node.
        
        Args:
            node: Optional node name for node-specific tasks
            limit: Maximum number of tasks to return
            
        Returns:
            List of task information dictionaries
        """
        try:
            tasks = []
            
            # If node is specified, get tasks for that node
            if node:
                tasks = self.proxmox_client.proxmox.nodes(node).tasks.get(limit=limit)
            else:
                # Get tasks from all nodes
                for node_data in self.proxmox_client.get_node_status():
                    node_name = node_data['node']
                    node_tasks = self.proxmox_client.proxmox.nodes(node_name).tasks.get(limit=limit)
                    tasks.extend(node_tasks)
                
                # Sort by start time (descending) and limit
                tasks.sort(key=lambda t: t.get('starttime', 0), reverse=True)
                tasks = tasks[:limit]
            
            # Enhance task data with additional information
            enhanced_tasks = []
            for task in tasks:
                enhanced_task = {
                    **task,
                    "node": task.get('node'),
                    "id": task.get('upid'),
                    "type": task.get('type'),
                    "status": task.get('status'),
                    "user": task.get('user'),
                    "start_time": datetime.fromtimestamp(task.get('starttime')).isoformat() if task.get('starttime') else None,
                    "end_time": datetime.fromtimestamp(task.get('endtime')).isoformat() if task.get('endtime') else None,
                    "duration_seconds": task.get('endtime', 0) - task.get('starttime', 0) if task.get('endtime') else None
                }
                enhanced_tasks.append(enhanced_task)
            
            return enhanced_tasks
            
        except Exception as e:
            logger.error(f"Error monitoring tasks: {str(e)}")
            return []
