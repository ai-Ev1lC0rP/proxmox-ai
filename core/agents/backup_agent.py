"""
Backup and restore agent for Proxmox VE environments.
Provides enhanced backup management functionalities based on reference implementations.
"""

import os
import time
import logging
from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime

from core.client import ProxmoxClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("backup_agent")


class ProxmoxBackupAgent:
    """
    Agent for managing backups and restores in Proxmox VE environments.
    Implements functionality based on the ProxmoxVE reference scripts.
    """
    
    def __init__(self, proxmox_client: ProxmoxClient):
        """
        Initialize the Backup agent.
        
        Args:
            proxmox_client: Initialized ProxmoxClient instance
        """
        self.proxmox_client = proxmox_client
    
    def list_storages_with_backup_capability(self, node: str) -> List[Dict[str, Any]]:
        """
        List storage locations that support backups.
        
        Args:
            node: Node name
            
        Returns:
            List of backup-capable storage information dictionaries
        """
        all_storages = self.proxmox_client.get_storage(node=node)
        
        # Filter for storages that support backups
        backup_storages = []
        for storage in all_storages:
            content = storage.get("content", "").split(",")
            if "backup" in content or "vztmpl" in content or "rootdir" in content:
                backup_storages.append(storage)
        
        return backup_storages
    
    def list_backups(self, node: str, storage: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List available backups on a node or specific storage.
        
        Args:
            node: Node name
            storage: Optional storage name to filter by
            
        Returns:
            List of backup information dictionaries
        """
        # Get all storages if none specified
        if storage is None:
            storages = [s.get("storage") for s in self.list_storages_with_backup_capability(node)]
        else:
            storages = [storage]
        
        backups = []
        
        # Loop through each storage to get backups
        for storage_name in storages:
            if not storage_name:
                continue
                
            try:
                # Get the content of the storage
                storage_backups = self.proxmox_client.proxmox.nodes(node).storage(storage_name).content.get()
                
                # Filter for backup files
                for backup in storage_backups:
                    if backup.get("content") == "backup":
                        # Parse additional information from the volid
                        volid = backup.get("volid", "")
                        
                        # Extract VMID and timestamp if possible
                        vmid = None
                        timestamp = None
                        filename = backup.get("volid", "").split("/")[-1]
                        
                        if "vzdump-" in filename:
                            # Parse typical Proxmox backup filename format
                            # Example: vzdump-qemu-123-2023_01_01-00_00_00.vma.zst
                            parts = filename.split("-")
                            
                            if len(parts) >= 3:
                                try:
                                    vmid = int(parts[2].split("-")[0])
                                except ValueError:
                                    vmid = None
                                    
                            if len(parts) >= 4:
                                # Try to parse the timestamp
                                date_part = parts[3].split(".")[0]
                                try:
                                    date_time = datetime.strptime(date_part, "%Y_%m_%d-%H_%M_%S")
                                    timestamp = date_time.isoformat()
                                except ValueError:
                                    timestamp = None
                        
                        # Add parsed information to the backup data
                        backup_info = {
                            **backup,
                            "node": node,
                            "storage": storage_name,
                            "parsed_vmid": vmid,
                            "timestamp": timestamp
                        }
                        
                        backups.append(backup_info)
            except Exception as e:
                logger.error(f"Error listing backups on {storage_name}: {str(e)}")
        
        # Sort backups by timestamp (newest first) if available
        backups.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        
        return backups
    
    def create_backup(self, 
                     node: str, 
                     vmid: int, 
                     storage: str = "local", 
                     mode: str = "snapshot", 
                     compress: bool = True,
                     mail: Optional[str] = None,
                     remove: int = 0) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Create a backup of a VM or container.
        
        Args:
            node: Node name
            vmid: VM or container ID
            storage: Storage name (default: local)
            mode: Backup mode ('snapshot', 'suspend', or 'stop')
            compress: Whether to compress the backup
            mail: Email to send notification to
            remove: Number of backups to keep (0 = keep all)
            
        Returns:
            Tuple of (success: bool, message: str, data: dict)
        """
        try:
            # Create backup parameters
            backup_params = {
                "vmid": vmid,
                "mode": mode,
                "compress": compress,
                "storage": storage,
                "remove": remove
            }
            
            if mail:
                backup_params["mailto"] = mail
            
            # Request backup creation
            result = self.proxmox_client.proxmox.nodes(node).vzdump.post(**backup_params)
            
            # Get the task ID from the result
            task_id = result.get("data")
            
            if not task_id:
                return False, "Failed to start backup task", {}
            
            logger.info(f"Started backup task {task_id} for VM/CT {vmid}")
            
            # Wait for task to start and get initial status
            time.sleep(2)
            task_status = self.proxmox_client.get_task_status(node=node, upid=task_id)
            
            return True, f"Backup task started: {task_id}", {
                "task_id": task_id,
                "vmid": vmid,
                "storage": storage,
                "initial_status": task_status
            }
            
        except Exception as e:
            logger.error(f"Error creating backup for VM/CT {vmid}: {str(e)}")
            return False, f"Error creating backup: {str(e)}", {}
    
    def restore_backup(self, 
                      node: str, 
                      backup_id: str,
                      target_vmid: Optional[int] = None,
                      target_storage: Optional[str] = None,
                      restore_type: str = "fast") -> Tuple[bool, str, Dict[str, Any]]:
        """
        Restore a backup to a VM or container.
        
        Args:
            node: Node name
            backup_id: Backup volid to restore
            target_vmid: Optional target VM/CT ID (default: original ID)
            target_storage: Optional target storage (default: original storage)
            restore_type: Restore type ('fast' or 'full')
            
        Returns:
            Tuple of (success: bool, message: str, data: dict)
        """
        try:
            # Parse the backup ID to get storage and path
            if ":" not in backup_id:
                return False, "Invalid backup ID format. Expected storage:path/to/backup", {}
            
            storage, path = backup_id.split(":", 1)
            
            # Set up restore parameters
            restore_params = {
                "storage": target_storage or storage,
                "archive": backup_id,
                "restore": 1
            }
            
            # If target VMID is specified, use it
            if target_vmid is not None:
                restore_params["vmid"] = target_vmid
            
            # Add restore type option
            if restore_type.lower() == "full":
                restore_params["full"] = 1
            
            # Request restore operation
            result = self.proxmox_client.proxmox.nodes(node).vzdump.extractconfig.post(**restore_params)
            
            # Get the task ID from the result
            task_id = result.get("data")
            
            if not task_id:
                return False, "Failed to start restore task", {}
            
            logger.info(f"Started restore task {task_id} for backup {backup_id}")
            
            # Wait for task to start and get initial status
            time.sleep(2)
            task_status = self.proxmox_client.get_task_status(node=node, upid=task_id)
            
            return True, f"Restore task started: {task_id}", {
                "task_id": task_id,
                "backup_id": backup_id,
                "target_vmid": target_vmid,
                "initial_status": task_status
            }
            
        except Exception as e:
            logger.error(f"Error restoring backup {backup_id}: {str(e)}")
            return False, f"Error restoring backup: {str(e)}", {}
    
    def monitor_backup_task(self, node: str, task_id: str) -> Dict[str, Any]:
        """
        Monitor a backup or restore task.
        
        Args:
            node: Node name
            task_id: Task ID (UPID)
            
        Returns:
            Task status information
        """
        try:
            # Get the task status
            task_status = self.proxmox_client.get_task_status(node=node, upid=task_id)
            
            # If there's a log file, get the most recent entries
            log_entries = []
            if task_status.get("pid"):
                log_params = {"limit": 10}  # Get last 10 log entries
                log_result = self.proxmox_client.proxmox.nodes(node).tasks(task_id).log.get(**log_params)
                log_entries = [entry.get("t", "") for entry in log_result]
            
            # Calculate progress percentage if available
            progress = 0
            if "status" in task_status:
                status_data = task_status["status"]
                if isinstance(status_data, str) and "%" in status_data:
                    try:
                        progress = float(status_data.split("%")[0])
                    except ValueError:
                        progress = 0
            
            # Add additional information to the status
            enhanced_status = {
                **task_status,
                "log_entries": log_entries,
                "progress": progress,
                "is_running": task_status.get("status") == "running",
                "is_complete": task_status.get("status") == "stopped" and task_status.get("exitstatus") == "OK",
                "is_failed": task_status.get("status") == "stopped" and task_status.get("exitstatus") != "OK"
            }
            
            return enhanced_status
            
        except Exception as e:
            logger.error(f"Error monitoring task {task_id}: {str(e)}")
            return {
                "error": str(e),
                "is_running": False,
                "is_complete": False,
                "is_failed": True
            }
    
    def create_scheduled_backup(self, 
                              node: str,
                              storage: str, 
                              vmid: Optional[int] = None,
                              schedule: str = "0 0 * * *",  # Default: daily at midnight
                              compress: bool = True,
                              mode: str = "snapshot",
                              max_backups: int = 5) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Create a scheduled backup job.
        
        Args:
            node: Node name
            storage: Storage name
            vmid: Optional VM/CT ID (if None, all VMs/CTs will be backed up)
            schedule: Cron schedule expression
            compress: Whether to compress backups
            mode: Backup mode ('snapshot', 'suspend', or 'stop')
            max_backups: Maximum number of backups to keep
            
        Returns:
            Tuple of (success: bool, message: str, data: dict)
        """
        try:
            # Set up the scheduled backup job
            job_params = {
                "enabled": 1,
                "storage": storage,
                "mode": mode,
                "compress": compress,
                "remove": max_backups,
                "schedule": schedule,
                "all": 0 if vmid else 1  # If vmid is None, backup all
            }
            
            # If specific VMID is provided, add it
            if vmid is not None:
                job_params["vmid"] = str(vmid)
            
            # Add the scheduled backup job to the node's vzdump configuration
            result = self.proxmox_client.proxmox.nodes(node).vzdump.post(**job_params)
            
            # Get the job ID if available
            job_id = "vzdump"  # Default ID as Proxmox doesn't always return a specific ID
            
            return True, f"Scheduled backup job created for {'VM/CT ' + str(vmid) if vmid else 'all VMs/CTs'}", {
                "job_id": job_id,
                "node": node,
                "storage": storage,
                "schedule": schedule,
                "vmid": vmid,
                "max_backups": max_backups
            }
            
        except Exception as e:
            logger.error(f"Error creating scheduled backup job: {str(e)}")
            return False, f"Error creating scheduled backup job: {str(e)}", {}
    
    def get_backup_schedule(self, node: str) -> List[Dict[str, Any]]:
        """
        Get all scheduled backup jobs for a node.
        
        Args:
            node: Node name
            
        Returns:
            List of scheduled backup job information dictionaries
        """
        try:
            # Get the node's vzdump configuration
            vzdump_config = self.proxmox_client.proxmox.nodes(node).vzdump.extractconfig.get()
            
            # Parse the configuration to find scheduled jobs
            scheduled_jobs = []
            
            # Process the configuration if it exists
            if vzdump_config and "data" in vzdump_config:
                config_data = vzdump_config["data"]
                
                # Look for lines with schedule settings
                for line in config_data.split("\n"):
                    if "schedule" in line:
                        # Parse the job configuration
                        job_config = {}
                        
                        # Split by space to get key=value pairs
                        parts = line.strip().split()
                        for part in parts:
                            if "=" in part:
                                key, value = part.split("=", 1)
                                job_config[key] = value
                        
                        # Add parsed job to the list
                        if job_config:
                            job_config["node"] = node
                            scheduled_jobs.append(job_config)
            
            return scheduled_jobs
            
        except Exception as e:
            logger.error(f"Error getting backup schedule for node {node}: {str(e)}")
            return []
