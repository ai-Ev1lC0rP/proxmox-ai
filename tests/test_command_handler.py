"""
Tests for the Proxmox Command Handler module

These tests verify that the command handler correctly processes
natural language commands and executes appropriate actions.
"""
import pytest
from unittest.mock import patch, MagicMock
from typing import List, Dict, Any

from proxmox_helpers.command_handler import ProxmoxCommandHandler
from proxmox_client import ProxmoxClient
from database.manager import DatabaseManager

# Test data
TEST_NODE_ID = "pve-01"
TEST_VM_ID = 100
TEST_CT_ID = 200
TEST_STORAGE_ID = "local"

class TestProxmoxCommandHandler:
    """Test suite for the ProxmoxCommandHandler class"""
    
    @pytest.fixture
    def mock_proxmox_client(self):
        """Create a mock ProxmoxClient for testing"""
        mock_client = MagicMock(spec=ProxmoxClient)
        
        # Mock get_nodes
        node_data = [
            {"id": "pve-01", "name": "proxmox-01", "status": "online"},
            {"id": "pve-02", "name": "proxmox-02", "status": "online"}
        ]
        mock_client.get_nodes.return_value = node_data
        
        # Mock get_vms
        vm_data = [
            {"vmid": 100, "name": "ubuntu-vm", "status": "running", "node": "pve-01"},
            {"vmid": 101, "name": "debian-vm", "status": "stopped", "node": "pve-01"},
            {"vmid": 102, "name": "centos-vm", "status": "running", "node": "pve-02"}
        ]
        mock_client.get_vms.return_value = vm_data
        
        # Mock get_containers
        ct_data = [
            {"vmid": 200, "name": "ubuntu-ct", "status": "running", "node": "pve-01"},
            {"vmid": 201, "name": "alpine-ct", "status": "stopped", "node": "pve-02"}
        ]
        mock_client.get_containers.return_value = ct_data
        
        # Mock get_storage
        storage_data = [
            {"storage": "local", "type": "dir", "node": "pve-01", "content": "images,rootdir"},
            {"storage": "cephfs", "type": "cephfs", "node": "pve-02", "content": "images"}
        ]
        mock_client.get_storage.return_value = storage_data
        
        # Mock start and stop methods
        for method in ['start_vm', 'stop_vm', 'start_container', 'stop_container']:
            getattr(mock_client, method).return_value = {"status": "success"}
            
        return mock_client
    
    @pytest.fixture
    def mock_db_manager(self):
        """Create a mock DatabaseManager for testing"""
        with patch('database.manager.DatabaseManager', autospec=True) as MockDBManager:
            db_manager = MockDBManager.return_value
            
            # Mock find_similar_commands
            similar_commands = [
                ("list all VMs", 0.9),
                ("show virtual machines", 0.8)
            ]
            db_manager.find_similar_commands.return_value = similar_commands
            
            # Mock log_command
            db_manager.log_command.return_value = None
            
            yield db_manager
    
    @pytest.fixture
    def command_handler(self, mock_proxmox_client, mock_db_manager):
        """Create a ProxmoxCommandHandler with mock dependencies"""
        return ProxmoxCommandHandler(mock_proxmox_client, mock_db_manager)
    
    def test_list_nodes(self, command_handler, mock_proxmox_client, mock_db_manager):
        """Test listing Proxmox nodes"""
        # Call the method
        result = command_handler.list_nodes()
        
        # Verify the client was called
        mock_proxmox_client.get_nodes.assert_called_once()
        
        # Verify database was updated
        assert mock_db_manager.update_node.call_count == 2  # Two nodes
        
        # Verify the result
        assert len(result) == 2
        assert result[0]["id"] == "pve-01"
        assert result[1]["id"] == "pve-02"
    
    def test_list_vms(self, command_handler, mock_proxmox_client):
        """Test listing virtual machines"""
        # Test with no filters
        result = command_handler.list_vms()
        mock_proxmox_client.get_vms.assert_called_with(node=None)
        assert len(result) == 3
        
        # Test with node filter
        mock_proxmox_client.reset_mock()
        result = command_handler.list_vms(node=TEST_NODE_ID)
        mock_proxmox_client.get_vms.assert_called_with(node=TEST_NODE_ID)
        
        # Test with status filter
        mock_proxmox_client.reset_mock()
        result = command_handler.list_vms(status="running")
        assert len(result) == 2
        assert all(vm["status"] == "running" for vm in result)
    
    def test_list_containers(self, command_handler, mock_proxmox_client):
        """Test listing containers"""
        # Test with no filters
        result = command_handler.list_containers()
        mock_proxmox_client.get_containers.assert_called_with(node=None)
        assert len(result) == 2
        
        # Test with node filter
        mock_proxmox_client.reset_mock()
        result = command_handler.list_containers(node=TEST_NODE_ID)
        mock_proxmox_client.get_containers.assert_called_with(node=TEST_NODE_ID)
        
        # Test with status filter
        mock_proxmox_client.reset_mock()
        result = command_handler.list_containers(status="running")
        assert len(result) == 1
        assert result[0]["status"] == "running"
    
    def test_list_storage(self, command_handler, mock_proxmox_client):
        """Test listing storage resources"""
        # Test with no filters
        result = command_handler.list_storage()
        mock_proxmox_client.get_storage.assert_called_with(node=None)
        assert len(result) == 2
        
        # Test with node filter
        mock_proxmox_client.reset_mock()
        result = command_handler.list_storage(node=TEST_NODE_ID)
        mock_proxmox_client.get_storage.assert_called_with(node=TEST_NODE_ID)
    
    def test_start_vm(self, command_handler, mock_proxmox_client):
        """Test starting a VM"""
        # Test with node specified
        result = command_handler.start_vm(TEST_VM_ID, TEST_NODE_ID)
        mock_proxmox_client.start_vm.assert_called_with(TEST_VM_ID, TEST_NODE_ID)
        assert result["status"] == "success"
        
        # Test with automatic node discovery
        mock_proxmox_client.reset_mock()
        result = command_handler.start_vm(TEST_VM_ID)
        # Should determine the node automatically from the VM list
        mock_proxmox_client.start_vm.assert_called_with(TEST_VM_ID, "pve-01")
        assert result["status"] == "success"
    
    def test_stop_vm(self, command_handler, mock_proxmox_client):
        """Test stopping a VM"""
        # Test with node specified
        result = command_handler.stop_vm(TEST_VM_ID, TEST_NODE_ID)
        mock_proxmox_client.stop_vm.assert_called_with(TEST_VM_ID, TEST_NODE_ID)
        assert result["status"] == "success"
        
        # Test with automatic node discovery
        mock_proxmox_client.reset_mock()
        result = command_handler.stop_vm(TEST_VM_ID)
        # Should determine the node automatically from the VM list
        mock_proxmox_client.stop_vm.assert_called_with(TEST_VM_ID, "pve-01")
        assert result["status"] == "success"
    
    def test_start_container(self, command_handler, mock_proxmox_client):
        """Test starting a container"""
        # Test with node specified
        result = command_handler.start_container(TEST_CT_ID, TEST_NODE_ID)
        mock_proxmox_client.start_container.assert_called_with(TEST_CT_ID, TEST_NODE_ID)
        assert result["status"] == "success"
        
        # Test with automatic node discovery
        mock_proxmox_client.reset_mock()
        result = command_handler.start_container(TEST_CT_ID)
        # Should determine the node automatically from the container list
        mock_proxmox_client.start_container.assert_called_with(TEST_CT_ID, "pve-01")
        assert result["status"] == "success"
    
    def test_stop_container(self, command_handler, mock_proxmox_client):
        """Test stopping a container"""
        # Test with node specified
        result = command_handler.stop_container(TEST_CT_ID, TEST_NODE_ID)
        mock_proxmox_client.stop_container.assert_called_with(TEST_CT_ID, TEST_NODE_ID)
        assert result["status"] == "success"
        
        # Test with automatic node discovery
        mock_proxmox_client.reset_mock()
        result = command_handler.stop_container(TEST_CT_ID)
        # Should determine the node automatically from the container list
        mock_proxmox_client.stop_container.assert_called_with(TEST_CT_ID, "pve-01")
        assert result["status"] == "success"
    
    def test_handle_command(self, command_handler, mock_db_manager):
        """Test processing natural language commands"""
        # Test list nodes command
        with patch.object(command_handler, 'list_nodes') as mock_list_nodes:
            mock_list_nodes.return_value = [{"id": "pve-01"}]
            result = command_handler.handle_command("list all nodes")
            mock_list_nodes.assert_called_once()
            assert result == [{"id": "pve-01"}]
        
        # Test list VMs command
        with patch.object(command_handler, 'list_vms') as mock_list_vms:
            mock_list_vms.return_value = [{"vmid": 100}]
            result = command_handler.handle_command("show all virtual machines")
            mock_list_vms.assert_called_once()
            assert result == [{"vmid": 100}]
        
        # Test list containers command
        with patch.object(command_handler, 'list_containers') as mock_list_containers:
            mock_list_containers.return_value = [{"vmid": 200}]
            result = command_handler.handle_command("display all containers")
            mock_list_containers.assert_called_once()
            assert result == [{"vmid": 200}]
        
        # Test unknown command
        with patch.object(mock_db_manager, 'find_similar_commands') as mock_find_similar:
            mock_find_similar.return_value = [("list nodes", 0.8)]
            result = command_handler.handle_command("unknown command")
            assert "sorry" in result["error"].lower()
            assert "similar commands" in result["error"].lower()
            assert "list nodes" in result["error"]
