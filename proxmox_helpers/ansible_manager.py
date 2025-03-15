"""
Ansible Integration Manager for Proxmox AI

This module provides functionality to manage and execute Ansible playbooks
for Proxmox configuration management directly from the Proxmox AI system.
"""

import os
import json
import subprocess
import logging
from typing import Dict, List, Any, Optional, Union, Tuple
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AnsibleManager:
    """
    Manages Ansible playbook execution and integration with Proxmox configuration.
    """
    
    def __init__(self, 
                 ansible_path: str = None, 
                 inventory_path: str = None,
                 playbooks_path: str = None):
        """
        Initialize the AnsibleManager with paths to ansible resources.
        
        Args:
            ansible_path: Base directory for Ansible files
            inventory_path: Path to the inventory directory
            playbooks_path: Path to the playbooks directory
        """
        # Set default paths relative to the project root
        project_root = Path(__file__).parent.parent.absolute()
        self.ansible_path = ansible_path or os.path.join(project_root, "ansible_integration")
        self.inventory_path = inventory_path or os.path.join(self.ansible_path, "inventory")
        self.playbooks_path = playbooks_path or os.path.join(self.ansible_path, "playbooks")
        
        # Verify paths exist
        self._verify_paths()
        
        # Available playbooks map (name -> file path)
        self.available_playbooks = self._scan_playbooks()
        
    def _verify_paths(self) -> None:
        """Verify that required directories exist."""
        for path in [self.ansible_path, self.inventory_path, self.playbooks_path]:
            if not os.path.exists(path):
                logger.warning(f"Path does not exist: {path}")
                os.makedirs(path, exist_ok=True)
                logger.info(f"Created directory: {path}")
    
    def _scan_playbooks(self) -> Dict[str, str]:
        """
        Scan and index available playbooks.
        
        Returns:
            Dict mapping playbook name to file path
        """
        playbooks = {}
        
        if os.path.exists(self.playbooks_path):
            for file in os.listdir(self.playbooks_path):
                if file.endswith(('.yml', '.yaml')):
                    name = file.replace('.yml', '').replace('.yaml', '')
                    path = os.path.join(self.playbooks_path, file)
                    playbooks[name] = path
        
        logger.info(f"Found {len(playbooks)} Ansible playbooks")
        return playbooks
    
    def list_playbooks(self) -> List[str]:
        """
        List all available playbooks.
        
        Returns:
            List of playbook names
        """
        return list(self.available_playbooks.keys())
    
    def run_playbook(self, 
                    playbook_name: str, 
                    extra_vars: Dict[str, Any] = None,
                    limit_hosts: str = None,
                    tags: List[str] = None,
                    verbose: bool = False) -> Tuple[bool, str]:
        """
        Run an Ansible playbook with specified parameters.
        
        Args:
            playbook_name: Name of the playbook to run
            extra_vars: Dictionary of variables to pass to the playbook
            limit_hosts: Limit execution to specific hosts
            tags: List of tags to execute
            verbose: Enable verbose output
            
        Returns:
            Tuple containing (success: bool, output: str)
        """
        # Validate playbook exists
        if playbook_name not in self.available_playbooks:
            playbooks_list = ", ".join(self.list_playbooks())
            return False, f"Playbook '{playbook_name}' not found. Available playbooks: {playbooks_list}"
        
        playbook_path = self.available_playbooks[playbook_name]
        
        # Build command
        cmd = ["ansible-playbook", playbook_path]
        
        # Add verbose flag if requested
        if verbose:
            cmd.append("-vvv")
            
        # Add limit if specified
        if limit_hosts:
            cmd.extend(["-l", limit_hosts])
            
        # Add tags if specified
        if tags:
            cmd.extend(["-t", ",".join(tags)])
            
        # Add extra vars if specified
        if extra_vars:
            extra_vars_json = json.dumps(extra_vars)
            cmd.extend(["--extra-vars", extra_vars_json])
            
        # Set environment variables for ansible execution
        env = os.environ.copy()
        env["ANSIBLE_CONFIG"] = os.path.join(self.ansible_path, "ansible.cfg")
        
        try:
            logger.info(f"Running Ansible playbook: {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                env=env,
                cwd=self.ansible_path,
                check=False,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                logger.info(f"Playbook '{playbook_name}' executed successfully")
                return True, result.stdout
            else:
                logger.error(f"Playbook '{playbook_name}' failed: {result.stderr}")
                return False, f"Error: {result.stderr}"
                
        except Exception as e:
            logger.exception(f"Failed to execute playbook '{playbook_name}'")
            return False, f"Exception: {str(e)}"
    
    def run_vm_management(self, 
                          operation: str, 
                          vm_id: Union[int, str] = None,
                          vm_name: str = None,
                          node: str = None,
                          **kwargs) -> Tuple[bool, str]:
        """
        Run VM management operations using the Ansible playbook.
        
        Args:
            operation: One of 'create', 'start', 'stop', 'restart', 'delete'
            vm_id: ID of the VM to manage
            vm_name: Name of the VM 
            node: Proxmox node where the VM is located
            **kwargs: Additional parameters for VM creation
            
        Returns:
            Tuple containing (success: bool, output: str)
        """
        # Map operations to playbook states
        op_map = {
            'create': 'present',
            'start': 'started',
            'stop': 'stopped',
            'restart': 'restarted',
            'delete': 'absent'
        }
        
        if operation not in op_map:
            return False, f"Invalid operation '{operation}'. Must be one of: {', '.join(op_map.keys())}"
        
        extra_vars = {
            'vm_state': op_map[operation],
            'vm_id': vm_id,
            'vm_name': vm_name,
        }
        
        if node:
            extra_vars['vm_node'] = node
            
        # Add any additional kwargs as variables
        extra_vars.update(kwargs)
        
        return self.run_playbook('proxmox_vm_manager', extra_vars=extra_vars)
    
    def run_container_management(self, 
                                operation: str, 
                                ct_id: Union[int, str] = None,
                                ct_hostname: str = None,
                                node: str = None,
                                **kwargs) -> Tuple[bool, str]:
        """
        Run container management operations using the Ansible playbook.
        
        Args:
            operation: One of 'create', 'start', 'stop', 'restart', 'delete'
            ct_id: ID of the container to manage
            ct_hostname: Hostname of the container
            node: Proxmox node where the container is located
            **kwargs: Additional parameters for container creation
            
        Returns:
            Tuple containing (success: bool, output: str)
        """
        # Map operations to playbook states
        op_map = {
            'create': 'present',
            'start': 'started',
            'stop': 'stopped',
            'restart': 'restarted',
            'delete': 'absent'
        }
        
        if operation not in op_map:
            return False, f"Invalid operation '{operation}'. Must be one of: {', '.join(op_map.keys())}"
        
        extra_vars = {
            'ct_state': op_map[operation],
            'ct_id': ct_id,
            'ct_hostname': ct_hostname,
        }
        
        if node:
            extra_vars['ct_node'] = node
            
        # Add any additional kwargs as variables
        extra_vars.update(kwargs)
        
        return self.run_playbook('proxmox_container_manager', extra_vars=extra_vars)
    
    def run_cluster_management(self, 
                              operation: str,
                              target_node: str = None,
                              source_node: str = None,
                              cluster_name: str = None,
                              **kwargs) -> Tuple[bool, str]:
        """
        Run Proxmox cluster management operations.
        
        Args:
            operation: One of 'status', 'create_cluster', 'join_cluster', 'leave_cluster', 'enable_ha'
            target_node: Target node for operations
            source_node: Source node for cluster join
            cluster_name: Name for new cluster
            **kwargs: Additional parameters
            
        Returns:
            Tuple containing (success: bool, output: str)
        """
        extra_vars = {'operation': operation}
        
        if target_node:
            extra_vars['target_node'] = target_node
            
        if source_node:
            extra_vars['source_node'] = source_node
            
        if cluster_name:
            extra_vars['cluster_name'] = cluster_name
            
        # Add any additional kwargs as variables
        extra_vars.update(kwargs)
        
        return self.run_playbook('proxmox_cluster_manager', extra_vars=extra_vars)
    
    def run_backup_management(self,
                             operation: str,
                             vm_id: Union[int, str] = None,
                             backup_id: str = None,
                             storage: str = None,
                             node: str = None,
                             **kwargs) -> Tuple[bool, str]:
        """
        Run Proxmox backup management operations.
        
        Args:
            operation: One of 'list', 'create', 'restore', 'delete', 'schedule'
            vm_id: ID of the VM to backup/restore
            backup_id: ID of the backup for restore/delete operations
            storage: Storage location for backups
            node: Proxmox node for backup operations
            **kwargs: Additional parameters including:
                      - mode: Backup mode (snapshot, suspend, etc)
                      - compress: Compression method
                      - schedule_hour, schedule_minute, etc: For scheduling
            
        Returns:
            Tuple containing (success: bool, output: str)
        """
        valid_operations = ['list', 'create', 'restore', 'delete', 'schedule']
        if operation not in valid_operations:
            return False, f"Invalid operation '{operation}'. Must be one of: {', '.join(valid_operations)}"
        
        extra_vars = {'operation': operation}
        
        if vm_id:
            extra_vars['vm_id'] = vm_id
            
        if backup_id:
            extra_vars['backup_id'] = backup_id
            
        if storage:
            extra_vars['storage'] = storage
            
        if node:
            extra_vars['node'] = node
            
        # Add any additional kwargs as variables
        extra_vars.update(kwargs)
        
        return self.run_playbook('proxmox_backup_manager', extra_vars=extra_vars)
