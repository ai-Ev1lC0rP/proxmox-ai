"""
Tests for the Proxmox Script Manager module

These tests verify that the script manager correctly indexes and executes
ProxmoxVE helper scripts for VM and container creation.
"""
import os
import json
import pytest
from unittest.mock import patch, MagicMock, mock_open
from typing import List, Dict, Any

from proxmox_helpers.script_manager import ProxmoxScriptManager
from database.manager import DatabaseManager
from database.schema import ScriptTemplate

# Test constants
TEST_SCRIPTS_PATH = "/path/to/proxmox/scripts"
TEST_VM_SCRIPT = "ubuntu2204-vm.sh"
TEST_CT_SCRIPT = "debian.sh"

# Sample script content
VM_SCRIPT_CONTENT = """#!/bin/bash
# Script: Create Ubuntu 22.04 VM
# Description: Creates a new Ubuntu 22.04 VM with specified parameters
# Parameters:
#   - VM_ID: Unique identifier for the VM
#   - VM_NAME: Name of the VM
#   - CPU_CORES: Number of CPU cores (default: 2)
#   - MEMORY: Memory in MB (default: 4096)
#   - DISK_SIZE: Disk size in GB (default: 32)
#   - STORAGE: Storage location (default: local-lvm)

set -e

# Default values
CPU_CORES=2
MEMORY=4096
DISK_SIZE=32
STORAGE="local-lvm"

# Function to create VM
function create_vm() {
    echo "Creating VM ${VM_NAME} with ID ${VM_ID}"
    # Command to create VM would go here
}

# Main script
if [ -z "$VM_ID" ] || [ -z "$VM_NAME" ]; then
    echo "Error: VM_ID and VM_NAME must be provided"
    exit 1
fi

create_vm
"""

CT_SCRIPT_CONTENT = """#!/bin/bash
# Script: Create Debian Container
# Description: Creates a new Debian container with specified parameters
# Parameters:
#   - CT_ID: Container ID
#   - CT_NAME: Container name
#   - CPU_CORES: CPU cores (default: 1)
#   - MEMORY: Memory in MB (default: 2048)
#   - DISK_SIZE: Disk size in GB (default: 8)
#   - STORAGE: Storage location (default: local-lvm)
#   - IP_ADDRESS: IP address for the container

set -e

# Default values
CPU_CORES=1
MEMORY=2048
DISK_SIZE=8
STORAGE="local-lvm"

# Function to create container
function create_container() {
    echo "Creating container ${CT_NAME} with ID ${CT_ID}"
    # Command to create container would go here
}

# Main script
if [ -z "$CT_ID" ] || [ -z "$CT_NAME" ] || [ -z "$IP_ADDRESS" ]; then
    echo "Error: CT_ID, CT_NAME, and IP_ADDRESS must be provided"
    exit 1
fi

create_container
"""

# Sample template JSON
TEMPLATE_JSON_CONTENT = """{
    "name": "ubuntu-vm-template",
    "description": "Template for Ubuntu VM creation",
    "script": "ubuntu2204-vm.sh",
    "defaults": {
        "CPU_CORES": 2,
        "MEMORY": 4096,
        "DISK_SIZE": 32,
        "STORAGE": "local-lvm"
    },
    "required_params": ["VM_ID", "VM_NAME"]
}"""


class TestProxmoxScriptManager:
    """Test suite for the ProxmoxScriptManager class"""
    
    @pytest.fixture
    def mock_db_manager(self):
        """Create a mock DatabaseManager"""
        with patch('database.manager.DatabaseManager', autospec=True) as MockDBManager:
            db_manager = MockDBManager.return_value
            yield db_manager
    
    @pytest.fixture
    def script_manager(self, mock_db_manager):
        """Create a ProxmoxScriptManager with a mock db_manager"""
        return ProxmoxScriptManager(TEST_SCRIPTS_PATH, mock_db_manager)
    
    def test_init(self, mock_db_manager):
        """Test initialization with different paths"""
        # With explicit path
        script_manager = ProxmoxScriptManager(TEST_SCRIPTS_PATH, mock_db_manager)
        assert script_manager._scripts_path == TEST_SCRIPTS_PATH
        assert script_manager._db_manager == mock_db_manager
        
        # With default path
        with patch.dict(os.environ, {"PROXMOX_SCRIPTS_PATH": "/env/path/scripts"}):
            script_manager = ProxmoxScriptManager(None, mock_db_manager)
            assert script_manager._scripts_path == "/env/path/scripts"
    
    def test_parse_script_metadata(self, script_manager):
        """Test parsing script metadata from script content"""
        # Test with VM script
        metadata = script_manager._parse_script_metadata(VM_SCRIPT_CONTENT)
        assert metadata["name"] == "Create Ubuntu 22.04 VM"
        assert "Creates a new Ubuntu 22.04 VM" in metadata["description"]
        assert len(metadata["parameters"]) == 6
        assert metadata["parameters"][0]["name"] == "VM_ID"
        assert metadata["parameters"][2]["name"] == "CPU_CORES"
        assert metadata["parameters"][2]["default"] == "2"
        
        # Test with container script
        metadata = script_manager._parse_script_metadata(CT_SCRIPT_CONTENT)
        assert metadata["name"] == "Create Debian Container"
        assert "Creates a new Debian container" in metadata["description"]
        assert len(metadata["parameters"]) == 7
        assert metadata["parameters"][0]["name"] == "CT_ID"
        assert metadata["parameters"][6]["name"] == "IP_ADDRESS"
        assert metadata["parameters"][6].get("default") is None  # No default
    
    def test_parse_template_json(self, script_manager):
        """Test parsing template JSON files"""
        # Mock open to return our test JSON content
        with patch("builtins.open", mock_open(read_data=TEMPLATE_JSON_CONTENT)):
            template_data = script_manager._parse_template_json("dummy/path/template.json")
            
            assert template_data["name"] == "ubuntu-vm-template"
            assert template_data["script"] == "ubuntu2204-vm.sh"
            assert template_data["defaults"]["CPU_CORES"] == 2
            assert "VM_ID" in template_data["required_params"]
    
    def test_index_script(self, script_manager, mock_db_manager):
        """Test indexing a single script"""
        # Set up mocks
        mock_session = MagicMock()
        mock_db_manager._session = mock_session
        mock_db_manager._get_session.return_value.__enter__.return_value = mock_session
        
        # Mock open to return our test script content
        with patch("builtins.open", mock_open(read_data=VM_SCRIPT_CONTENT)):
            # Test indexing VM script
            script_path = os.path.join(TEST_SCRIPTS_PATH, "vm", TEST_VM_SCRIPT)
            script_manager._index_script(script_path, "vm")
            
            # Verify script was added to database
            mock_session.add.assert_called_once()
            script_template = mock_session.add.call_args[0][0]
            
            assert isinstance(script_template, ScriptTemplate)
            assert script_template.name == "Create Ubuntu 22.04 VM"
            assert script_template.path == script_path
            assert script_template.type == "vm"
            assert "VM_ID" in script_template.parameters
    
    def test_index_all_scripts(self, script_manager):
        """Test indexing all scripts in the directory"""
        # Mock the file discovery process
        vm_scripts = [
            os.path.join(TEST_SCRIPTS_PATH, "vm", TEST_VM_SCRIPT)
        ]
        ct_scripts = [
            os.path.join(TEST_SCRIPTS_PATH, "ct", TEST_CT_SCRIPT)
        ]
        
        with patch("glob.glob") as mock_glob:
            # Set up mock to return our test scripts
            mock_glob.side_effect = lambda path: {
                os.path.join(TEST_SCRIPTS_PATH, "vm", "*.sh"): vm_scripts,
                os.path.join(TEST_SCRIPTS_PATH, "ct", "*.sh"): ct_scripts,
                os.path.join(TEST_SCRIPTS_PATH, "templates", "*.json"): []
            }[path]
            
            # Mock the _index_script method
            with patch.object(script_manager, "_index_script") as mock_index_script:
                # Call method under test
                script_manager.index_all_scripts()
                
                # Verify scripts were indexed
                assert mock_index_script.call_count == 2
                mock_index_script.assert_any_call(vm_scripts[0], "vm")
                mock_index_script.assert_any_call(ct_scripts[0], "ct")
    
    def test_get_script_templates(self, script_manager, mock_db_manager):
        """Test retrieving script templates from database"""
        # Set up mock database query result
        template1 = ScriptTemplate(
            id=1, 
            name="Create Ubuntu VM", 
            description="Creates Ubuntu VM", 
            type="vm",
            path="/path/to/ubuntu-vm.sh",
            parameters=json.dumps([
                {"name": "VM_ID", "description": "VM ID"},
                {"name": "VM_NAME", "description": "VM Name"}
            ])
        )
        template2 = ScriptTemplate(
            id=2, 
            name="Create Debian Container", 
            description="Creates Debian container", 
            type="ct",
            path="/path/to/debian-ct.sh",
            parameters=json.dumps([
                {"name": "CT_ID", "description": "Container ID"},
                {"name": "CT_NAME", "description": "Container Name"}
            ])
        )
        
        # Mock session query to return templates
        mock_query = MagicMock()
        mock_db_manager._session.query.return_value = mock_query
        mock_query.filter.return_value.all.return_value = [template1, template2]
        
        # Test with no type filter
        templates = script_manager.get_script_templates()
        assert len(templates) == 2
        assert templates[0]["name"] == "Create Ubuntu VM"
        assert templates[1]["name"] == "Create Debian Container"
        
        # Test with type filter
        mock_query.reset_mock()
        mock_query.filter.return_value.filter.return_value.all.return_value = [template1]
        templates = script_manager.get_script_templates(script_type="vm")
        assert len(templates) == 1
        assert templates[0]["name"] == "Create Ubuntu VM"
    
    def test_execute_script(self, script_manager):
        """Test executing a script with parameters"""
        # Set up mock ScriptTemplate
        template = ScriptTemplate(
            id=1, 
            name="Create Ubuntu VM", 
            description="Creates Ubuntu VM", 
            type="vm",
            path="/path/to/ubuntu-vm.sh",
            parameters=json.dumps([
                {"name": "VM_ID", "description": "VM ID"},
                {"name": "VM_NAME", "description": "VM Name"},
                {"name": "CPU_CORES", "description": "CPU Cores", "default": "2"}
            ])
        )
        
        # Mock subprocess.run
        with patch("subprocess.run") as mock_run:
            mock_process = MagicMock()
            mock_process.returncode = 0
            mock_process.stdout = "VM created successfully"
            mock_run.return_value = mock_process
            
            # Test executing script with parameters
            params = {
                "VM_ID": "100",
                "VM_NAME": "test-vm"
            }
            result = script_manager.execute_script(template, params)
            
            # Verify subprocess.run was called with correct env vars
            mock_run.assert_called_once()
            env = mock_run.call_args[1]["env"]
            assert env["VM_ID"] == "100"
            assert env["VM_NAME"] == "test-vm"
            assert env["CPU_CORES"] == "2"  # Default value
            
            # Verify result
            assert result["success"] is True
            assert result["output"] == "VM created successfully"
        
        # Test execution failure
        with patch("subprocess.run") as mock_run:
            mock_process = MagicMock()
            mock_process.returncode = 1
            mock_process.stderr = "Error: VM creation failed"
            mock_run.return_value = mock_process
            
            result = script_manager.execute_script(template, params)
            assert result["success"] is False
            assert "Error" in result["error"]
