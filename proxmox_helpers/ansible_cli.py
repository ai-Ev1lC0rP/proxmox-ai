#!/usr/bin/env python3
"""
Command Line Interface for Ansible Integration with Proxmox AI

This module provides a command-line interface to interact with the Ansible
integration features for Proxmox configuration management.
"""

import os
import sys
import json
import argparse
from typing import Dict, Any, List, Optional
import logging

from ansible_manager import AnsibleManager

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Proxmox AI Ansible Integration",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    # Create subparsers for different commands
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # List playbooks command
    list_parser = subparsers.add_parser("list", help="List available Ansible playbooks")
    
    # Run playbook command
    run_parser = subparsers.add_parser("run", help="Run an Ansible playbook")
    run_parser.add_argument("--playbook", required=True, help="Name of the playbook to run")
    run_parser.add_argument("--vars", help="JSON string of variables to pass to the playbook")
    run_parser.add_argument("--limit", help="Limit execution to specific hosts")
    run_parser.add_argument("--tags", help="Comma-separated list of tags to execute")
    run_parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    
    # VM management command
    vm_parser = subparsers.add_parser("vm", help="Manage VMs using Ansible")
    vm_parser.add_argument("--operation", required=True, 
                         choices=["create", "start", "stop", "restart", "delete"],
                         help="Operation to perform")
    vm_parser.add_argument("--vm-id", help="ID of the VM to manage")
    vm_parser.add_argument("--vm-name", help="Name of the VM")
    vm_parser.add_argument("--node", help="Proxmox node where the VM is located")
    vm_parser.add_argument("--memory", type=int, help="Memory in MB (for VM creation)")
    vm_parser.add_argument("--cores", type=int, help="Number of CPU cores (for VM creation)")
    vm_parser.add_argument("--disk-size", help="Disk size (for VM creation)")
    vm_parser.add_argument("--storage", help="Storage location (for VM creation)")
    vm_parser.add_argument("--template", help="Template to clone (for VM creation)")
    vm_parser.add_argument("--iso", help="ISO image to use (for VM creation)")
    
    # Container management command
    ct_parser = subparsers.add_parser("ct", help="Manage containers using Ansible")
    ct_parser.add_argument("--operation", required=True, 
                         choices=["create", "start", "stop", "restart", "delete"],
                         help="Operation to perform")
    ct_parser.add_argument("--ct-id", help="ID of the container to manage")
    ct_parser.add_argument("--hostname", help="Hostname of the container")
    ct_parser.add_argument("--node", help="Proxmox node where the container is located")
    ct_parser.add_argument("--memory", type=int, help="Memory in MB (for container creation)")
    ct_parser.add_argument("--cores", type=int, help="Number of CPU cores (for container creation)")
    ct_parser.add_argument("--disk", help="Disk size (for container creation)")
    ct_parser.add_argument("--storage", help="Storage location (for container creation)")
    ct_parser.add_argument("--ostemplate", help="OS template (for container creation)")
    
    # Cluster management command
    cluster_parser = subparsers.add_parser("cluster", help="Manage Proxmox cluster using Ansible")
    cluster_parser.add_argument("--operation", required=True, 
                              choices=["status", "create_cluster", "join_cluster", "leave_cluster", "enable_ha"],
                              help="Operation to perform")
    cluster_parser.add_argument("--target-node", help="Target node for operations")
    cluster_parser.add_argument("--source-node", help="Source node for cluster join")
    cluster_parser.add_argument("--cluster-name", help="Name for new cluster")
    
    # Backup management command
    backup_parser = subparsers.add_parser("backup", help="Manage Proxmox backups using Ansible")
    backup_parser.add_argument("--operation", required=True, 
                              choices=["list", "create", "restore", "delete", "schedule"],
                              help="Operation to perform")
    backup_parser.add_argument("--vm-id", help="ID of the VM to backup/restore")
    backup_parser.add_argument("--backup-id", help="ID of the backup for restore/delete operations")
    backup_parser.add_argument("--storage", help="Storage location for backups")
    backup_parser.add_argument("--node", help="Proxmox node for backup operations")
    backup_parser.add_argument("--mode", choices=["snapshot", "suspend", "stop"], 
                             help="Backup mode (snapshot, suspend, stop)")
    backup_parser.add_argument("--compress", choices=["0", "gzip", "lzo", "zstd"], 
                             help="Compression method")
    backup_parser.add_argument("--schedule-hour", help="Hour for scheduled backups (0-23)")
    backup_parser.add_argument("--schedule-minute", help="Minute for scheduled backups (0-59)")
    backup_parser.add_argument("--schedule-day", help="Day of month for scheduled backups (1-31, * for all)")
    backup_parser.add_argument("--schedule-month", help="Month for scheduled backups (1-12, * for all)")
    backup_parser.add_argument("--schedule-weekday", help="Day of week for scheduled backups (0-6, * for all)")
    
    return parser.parse_args()

def handle_list_command() -> None:
    """Handle the list command to show available playbooks."""
    ansible_mgr = AnsibleManager()
    playbooks = ansible_mgr.list_playbooks()
    
    if not playbooks:
        print("No Ansible playbooks found.")
        return
        
    print("\nAvailable Ansible Playbooks:")
    print("===========================")
    for i, playbook in enumerate(playbooks, 1):
        print(f"{i}. {playbook}")
    print()

def handle_run_command(args: argparse.Namespace) -> None:
    """Handle the run command to execute a specific playbook."""
    ansible_mgr = AnsibleManager()
    
    # Check if playbook exists
    playbooks = ansible_mgr.list_playbooks()
    if args.playbook not in playbooks:
        print(f"Error: Playbook '{args.playbook}' not found.")
        print("Available playbooks:", ", ".join(playbooks))
        sys.exit(1)
    
    # Parse extra vars if provided
    extra_vars = None
    if args.vars:
        try:
            extra_vars = json.loads(args.vars)
        except json.JSONDecodeError:
            print("Error: --vars must be a valid JSON string")
            sys.exit(1)
    
    # Parse tags if provided
    tags = None
    if args.tags:
        tags = [tag.strip() for tag in args.tags.split(",")]
    
    # Run the playbook
    print(f"Running playbook: {args.playbook}")
    success, output = ansible_mgr.run_playbook(
        playbook_name=args.playbook,
        extra_vars=extra_vars,
        limit_hosts=args.limit,
        tags=tags,
        verbose=args.verbose
    )
    
    if success:
        print("Playbook executed successfully.")
    else:
        print("Playbook execution failed.")
    
    print("\nOutput:")
    print("=======")
    print(output)

def handle_vm_command(args: argparse.Namespace) -> None:
    """Handle the VM management command."""
    ansible_mgr = AnsibleManager()
    
    # Collect all additional parameters
    kwargs = {}
    for arg in ["memory", "cores", "disk_size", "storage", "template", "iso"]:
        value = getattr(args, arg.replace("-", "_"), None)
        if value is not None:
            kwargs[arg] = value
    
    print(f"Performing '{args.operation}' operation on VM")
    success, output = ansible_mgr.run_vm_management(
        operation=args.operation,
        vm_id=args.vm_id,
        vm_name=args.vm_name,
        node=args.node,
        **kwargs
    )
    
    if success:
        print(f"VM {args.operation} operation completed successfully.")
    else:
        print(f"VM {args.operation} operation failed.")
    
    print("\nOutput:")
    print("=======")
    print(output)

def handle_ct_command(args: argparse.Namespace) -> None:
    """Handle the container management command."""
    ansible_mgr = AnsibleManager()
    
    # Collect all additional parameters
    kwargs = {}
    for arg in ["memory", "cores", "disk", "storage", "ostemplate"]:
        value = getattr(args, arg.replace("-", "_"), None)
        if value is not None:
            kwargs[arg] = value
    
    print(f"Performing '{args.operation}' operation on container")
    success, output = ansible_mgr.run_container_management(
        operation=args.operation,
        ct_id=args.ct_id,
        ct_hostname=args.hostname,
        node=args.node,
        **kwargs
    )
    
    if success:
        print(f"Container {args.operation} operation completed successfully.")
    else:
        print(f"Container {args.operation} operation failed.")
    
    print("\nOutput:")
    print("=======")
    print(output)

def handle_cluster_command(args: argparse.Namespace) -> None:
    """Handle the cluster management command."""
    ansible_mgr = AnsibleManager()
    
    print(f"Performing '{args.operation}' operation on Proxmox cluster")
    success, output = ansible_mgr.run_cluster_management(
        operation=args.operation,
        target_node=args.target_node,
        source_node=args.source_node,
        cluster_name=args.cluster_name
    )
    
    if success:
        print(f"Cluster {args.operation} operation completed successfully.")
    else:
        print(f"Cluster {args.operation} operation failed.")
    
    print("\nOutput:")
    print("=======")
    print(output)

def handle_backup_command(args: argparse.Namespace) -> None:
    """Handle the backup management command."""
    ansible_mgr = AnsibleManager()
    
    # Collect schedule parameters if provided
    kwargs = {}
    schedule_params = ["schedule_hour", "schedule_minute", "schedule_day", 
                      "schedule_month", "schedule_weekday"]
    
    for param in schedule_params:
        value = getattr(args, param, None)
        if value is not None:
            kwargs[param] = value
    
    # Add mode and compress if provided
    if args.mode:
        kwargs["mode"] = args.mode
    
    if args.compress:
        kwargs["compress"] = args.compress
    
    print(f"Performing '{args.operation}' backup operation")
    success, output = ansible_mgr.run_backup_management(
        operation=args.operation,
        vm_id=args.vm_id,
        backup_id=args.backup_id,
        storage=args.storage,
        node=args.node,
        **kwargs
    )
    
    if success:
        print(f"Backup {args.operation} operation completed successfully.")
    else:
        print(f"Backup {args.operation} operation failed.")
    
    print("\nOutput:")
    print("=======")
    print(output)

def main() -> None:
    """Main entry point for the CLI."""
    args = parse_args()
    
    if args.command == "list":
        handle_list_command()
    elif args.command == "run":
        handle_run_command(args)
    elif args.command == "vm":
        handle_vm_command(args)
    elif args.command == "ct":
        handle_ct_command(args)
    elif args.command == "cluster":
        handle_cluster_command(args)
    elif args.command == "backup":
        handle_backup_command(args)
    else:
        print("Please specify a command. Use --help for more information.")
        sys.exit(1)

if __name__ == "__main__":
    main()
