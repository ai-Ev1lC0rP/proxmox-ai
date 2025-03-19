"""
VM to Container conversion agent for Proxmox AI.
Based on proxmox-vm-to-ct-main reference implementation.
"""

import os
import subprocess
import tempfile
import shutil
from typing import Dict, List, Any, Optional, Tuple, Union
import logging

from core.client import ProxmoxClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("vm_converter")


class VMConverterAgent:
    """
    Agent for converting Proxmox VMs to containers.
    Implements functionality based on the proxmox-vm-to-ct-main reference.
    """
    
    def __init__(self, proxmox_client: ProxmoxClient):
        """
        Initialize the VM Converter agent.
        
        Args:
            proxmox_client: Initialized ProxmoxClient instance
        """
        self.proxmox_client = proxmox_client
        self.temp_dir = None
    
    def check_prerequisites(self) -> Tuple[bool, str]:
        """
        Check if all required prerequisites are met for conversion.
        
        Returns:
            Tuple of (success: bool, message: str)
        """
        # Check if pct and qm commands are available
        try:
            subprocess.run(["which", "pct"], check=True, capture_output=True)
            subprocess.run(["which", "qm"], check=True, capture_output=True)
            return True, "All prerequisites met"
        except subprocess.CalledProcessError:
            return False, "Required commands (pct, qm) not found. Please ensure you are running on a Proxmox host."
    
    def list_convertible_vms(self, node: str) -> List[Dict[str, Any]]:
        """
        List VMs that can be converted to containers.
        Only running Linux VMs are considered convertible.
        
        Args:
            node: Node name
            
        Returns:
            List of convertible VM information dictionaries
        """
        # Get all VMs
        all_vms = self.proxmox_client.get_vms(node=node)
        
        # Filter for running Linux VMs
        convertible_vms = []
        for vm in all_vms:
            if vm.get("status") == "running":
                # Get VM config to check OS type
                vmid = vm.get("vmid")
                config = self.proxmox_client.get_vm_config(node=node, vmid=vmid)
                
                # Check if it's a Linux VM (either explicitly or by checking for typical Linux settings)
                is_linux = False
                if config.get("ostype", "").lower() in ["l24", "l26", "debian", "ubuntu", "centos", "fedora"]:
                    is_linux = True
                elif "ide2" in config and "virtio" in config:  # Common in Linux VMs
                    is_linux = True
                
                if is_linux:
                    convertible_vms.append({
                        "vmid": vmid,
                        "name": vm.get("name", f"VM {vmid}"),
                        "status": vm.get("status"),
                        "memory": vm.get("maxmem"),
                        "disk": vm.get("maxdisk")
                    })
        
        return convertible_vms
    
    def prepare_conversion(self, node: str, vmid: int) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Prepare a VM for conversion by taking a snapshot and mounting its disks.
        
        Args:
            node: Node name
            vmid: VM ID
            
        Returns:
            Tuple of (success: bool, message: str, data: dict)
        """
        try:
            # Check if VM exists and is running
            vm_info = self.proxmox_client.get_vm_status(node=node, vmid=vmid)
            if not vm_info:
                return False, f"VM {vmid} not found on node {node}", {}
            
            if vm_info.get("status") != "running":
                return False, f"VM {vmid} is not running. VM must be running for conversion.", {}
            
            # Create a snapshot for the conversion
            snapshot_name = f"convert-to-ct-{vmid}"
            self.proxmox_client.create_vm_snapshot(node=node, vmid=vmid, name=snapshot_name)
            
            logger.info(f"Created snapshot {snapshot_name} for VM {vmid}")
            
            # Create a temporary directory for the conversion
            self.temp_dir = tempfile.mkdtemp(prefix=f"vm2ct-{vmid}-")
            
            # Get VM configuration for reference
            vm_config = self.proxmox_client.get_vm_config(node=node, vmid=vmid)
            
            # Identify the main disk
            main_disk = None
            for key, value in vm_config.items():
                if key.startswith(("ide", "scsi", "sata", "virtio")) and "disk" in value:
                    main_disk = {"key": key, "value": value}
                    break
            
            if not main_disk:
                # Clean up snapshot if no disk found
                self.proxmox_client.delete_vm_snapshot(node=node, vmid=vmid, name=snapshot_name)
                return False, f"No disk found for VM {vmid}", {}
            
            # Store conversion information
            conversion_info = {
                "node": node,
                "vmid": vmid,
                "snapshot": snapshot_name,
                "temp_dir": self.temp_dir,
                "main_disk": main_disk,
                "vm_config": vm_config
            }
            
            return True, f"VM {vmid} prepared for conversion", conversion_info
            
        except Exception as e:
            # Clean up any created resources
            if hasattr(self, "temp_dir") and self.temp_dir:
                shutil.rmtree(self.temp_dir, ignore_errors=True)
            
            logger.error(f"Error preparing VM {vmid} for conversion: {str(e)}")
            return False, f"Error preparing conversion: {str(e)}", {}
    
    def convert_vm_to_ct(self, 
                        node: str, 
                        vmid: int, 
                        new_ctid: Optional[int] = None,
                        storage: str = "local",
                        keep_vm: bool = True) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Convert a VM to a container.
        
        Args:
            node: Node name
            vmid: VM ID to convert
            new_ctid: Container ID for the new container (if None, next available ID is used)
            storage: Storage for the new container
            keep_vm: Whether to keep the original VM after conversion
            
        Returns:
            Tuple of (success: bool, message: str, data: dict)
        """
        try:
            # Check prerequisites
            prereq_ok, prereq_msg = self.check_prerequisites()
            if not prereq_ok:
                return False, prereq_msg, {}
            
            # Prepare VM for conversion
            prep_ok, prep_msg, conversion_info = self.prepare_conversion(node=node, vmid=vmid)
            if not prep_ok:
                return False, prep_msg, {}
            
            # Get or assign the new container ID
            if new_ctid is None:
                new_ctid = self.proxmox_client.get_next_vmid()
            
            # Get VM info
            vm_name = conversion_info["vm_config"].get("name", f"vm-{vmid}")
            
            # Execute the actual conversion steps
            logger.info(f"Starting conversion of VM {vmid} to CT {new_ctid}")
            
            # 1. Get VM disk image
            temp_disk_path = os.path.join(conversion_info["temp_dir"], "disk.raw")
            snapshot = conversion_info["snapshot"]
            disk_key = conversion_info["main_disk"]["key"]
            
            # Use qemu-img to convert and extract the disk
            qm_disk_path = f"/var/lib/vz/images/{vmid}/vm-{vmid}-disk-{disk_key.split('')[1]}.qcow2"
            extract_cmd = f"qemu-img convert -f qcow2 {qm_disk_path} -O raw {temp_disk_path}"
            
            # Run the extraction command
            subprocess.run(extract_cmd, shell=True, check=True)
            
            # 2. Create a rootfs for the container
            rootfs_path = os.path.join(conversion_info["temp_dir"], "rootfs")
            os.makedirs(rootfs_path, exist_ok=True)
            
            # Mount the disk
            mount_cmd = f"mount -o loop {temp_disk_path} {rootfs_path}"
            subprocess.run(mount_cmd, shell=True, check=True)
            
            # 3. Prepare the container configuration
            ct_config = {
                "hostname": vm_name,
                "cores": conversion_info["vm_config"].get("cores", 1),
                "memory": int(conversion_info["vm_config"].get("memory", 512)),
                "swap": 0,
                "rootfs": f"{storage}:0",
                "net0": conversion_info["vm_config"].get("net0", "name=eth0,bridge=vmbr0,ip=dhcp"),
                "ostype": "debian",  # Default to debian; should be detected from the VM
                "unprivileged": 0    # Start with privileged for compatibility
            }
            
            # 4. Create the container
            logger.info(f"Creating container {new_ctid} from VM {vmid}")
            
            # Create the CT configuration
            pct_cmd = ["pct", "create", str(new_ctid)]
            for key, value in ct_config.items():
                pct_cmd.extend(["-" + key, str(value)])
            
            # Run the command to create the container config
            subprocess.run(pct_cmd, check=True)
            
            # 5. Copy files from rootfs to container
            logger.info(f"Copying files from VM to container {new_ctid}")
            # Unmount the disk first
            subprocess.run(f"umount {rootfs_path}", shell=True, check=True)
            
            # Get CT storage path
            ct_rootfs = f"/var/lib/vz/private/{new_ctid}"
            
            # Copy the files using rsync or tar
            copy_cmd = f"rsync -a {rootfs_path}/ {ct_rootfs}/"
            subprocess.run(copy_cmd, shell=True, check=True)
            
            # 6. Finalize the container
            logger.info(f"Finalizing container {new_ctid}")
            
            # Ensure container is properly configured for boot
            # (This may require adjustments depending on the OS)
            finalize_cmds = [
                f"chroot {ct_rootfs} update-grub",
                f"chroot {ct_rootfs} ln -sf /proc/mounts /etc/mtab",
                f"chroot {ct_rootfs} apt-get update -y",
            ]
            
            for cmd in finalize_cmds:
                try:
                    subprocess.run(cmd, shell=True, check=True)
                except subprocess.CalledProcessError:
                    logger.warning(f"Command failed but continuing: {cmd}")
            
            # 7. Clean up
            logger.info("Cleaning up conversion resources")
            
            # Delete the snapshot if requested
            if not keep_vm:
                self.proxmox_client.delete_vm_snapshot(node=node, vmid=vmid, name=snapshot)
            
            # Remove temporary directory
            shutil.rmtree(conversion_info["temp_dir"], ignore_errors=True)
            
            # Return success with the new container ID
            return True, f"Successfully converted VM {vmid} to container {new_ctid}", {
                "ctid": new_ctid,
                "name": vm_name,
                "original_vmid": vmid
            }
            
        except Exception as e:
            logger.error(f"Error converting VM {vmid} to container: {str(e)}")
            
            # Clean up resources on error
            if hasattr(self, "temp_dir") and self.temp_dir:
                # Ensure any mounts are cleaned up
                try:
                    rootfs_path = os.path.join(self.temp_dir, "rootfs")
                    subprocess.run(f"umount {rootfs_path}", shell=True)
                except:
                    pass
                    
                # Remove the temp directory
                shutil.rmtree(self.temp_dir, ignore_errors=True)
            
            return False, f"Error during conversion: {str(e)}", {}
    
    def cleanup_failed_conversion(self, node: str, vmid: int, snapshot_name: str) -> bool:
        """
        Clean up resources from a failed conversion.
        
        Args:
            node: Node name
            vmid: VM ID
            snapshot_name: Name of the snapshot to remove
            
        Returns:
            Success flag
        """
        try:
            # Delete the snapshot
            self.proxmox_client.delete_vm_snapshot(node=node, vmid=vmid, name=snapshot_name)
            
            # Clean up temporary directory if it exists
            if hasattr(self, "temp_dir") and self.temp_dir:
                shutil.rmtree(self.temp_dir, ignore_errors=True)
                
            return True
        except Exception as e:
            logger.error(f"Error cleaning up conversion resources: {str(e)}")
            return False
