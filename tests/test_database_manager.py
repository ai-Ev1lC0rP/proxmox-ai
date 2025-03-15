"""
Tests for the Database Manager module

These tests verify that the database manager correctly handles 
connections, embedding creation, and command log storage.
"""
import os
import pytest
import numpy as np
from unittest.mock import patch, MagicMock
from typing import List, Dict, Any, Tuple

from database.manager import DatabaseManager
from database.schema import CommandLog, Node

# Test Constants
TEST_DB_URL = "postgresql://postgres:postgres@localhost:5432/test_proxmox_ai"
TEST_COMMAND = "list all VMs"
TEST_EMBEDDING = np.random.random(384).astype(np.float32)  # Typical embedding size

@pytest.fixture
def mock_session():
    """Create a mock SQLAlchemy session for testing"""
    session_mock = MagicMock()
    return session_mock

@pytest.fixture
def db_manager_with_mock_session(mock_session):
    """Create a DatabaseManager with a mock session"""
    with patch('database.manager.create_engine'), \
         patch('database.manager.sessionmaker', return_value=lambda: mock_session):
        db_manager = DatabaseManager(TEST_DB_URL)
        return db_manager

@pytest.fixture
def db_manager_with_mock_encoder():
    """Create a DatabaseManager with a mock sentence encoder"""
    mock_encoder = MagicMock()
    mock_encoder.encode.return_value = [TEST_EMBEDDING]
    
    with patch('database.manager.create_engine'), \
         patch('database.manager.sessionmaker'), \
         patch('database.manager.SentenceTransformer', return_value=mock_encoder):
        db_manager = DatabaseManager(TEST_DB_URL)
        return db_manager

class TestDatabaseManager:
    """Test suite for the DatabaseManager class"""
    
    def test_init(self):
        """Test initialization with different DB URLs"""
        # With explicit URL
        with patch('database.manager.create_engine') as mock_create_engine, \
             patch('database.manager.sessionmaker'):
            db_manager = DatabaseManager(TEST_DB_URL)
            mock_create_engine.assert_called_once_with(TEST_DB_URL)
        
        # With environment variable
        with patch('database.manager.create_engine') as mock_create_engine, \
             patch('database.manager.sessionmaker'), \
             patch.dict(os.environ, {"PROXMOX_DB_URL": "postgresql://test_env_url"}):
            db_manager = DatabaseManager()
            mock_create_engine.assert_called_once_with("postgresql://test_env_url")
    
    def test_create_embedding(self, db_manager_with_mock_encoder):
        """Test creation of text embeddings"""
        db_manager = db_manager_with_mock_encoder
        
        # Test with a single text
        embedding = db_manager.create_embedding(TEST_COMMAND)
        assert isinstance(embedding, np.ndarray)
        assert embedding.shape == TEST_EMBEDDING.shape
        
        # Test with batch of texts
        texts = ["command1", "command2", "command3"]
        with patch.object(db_manager, '_encoder') as mock_encoder:
            mock_encoder.encode.return_value = [TEST_EMBEDDING.copy() for _ in texts]
            embeddings = db_manager.create_embeddings(texts)
            
            assert len(embeddings) == len(texts)
            assert all(isinstance(emb, np.ndarray) for emb in embeddings)
            mock_encoder.encode.assert_called_once()
    
    def test_log_command(self, db_manager_with_mock_session):
        """Test logging commands to the database"""
        db_manager = db_manager_with_mock_session
        mock_session = db_manager._session
        
        # Mock the create_embedding method
        with patch.object(db_manager, 'create_embedding', return_value=TEST_EMBEDDING):
            # Test logging a command
            db_manager.log_command(TEST_COMMAND)
            
            # Verify the session was used correctly
            mock_session.add.assert_called_once()
            mock_session.commit.assert_called_once()
            
            # Verify the CommandLog object was created with the right data
            command_log = mock_session.add.call_args[0][0]
            assert isinstance(command_log, CommandLog)
            assert command_log.command == TEST_COMMAND
            assert np.array_equal(command_log.embedding, TEST_EMBEDDING)
    
    def test_find_similar_commands(self, db_manager_with_mock_session):
        """Test finding similar commands by embedding"""
        db_manager = db_manager_with_mock_session
        mock_session = db_manager._session
        
        # Mock query results
        mock_results = [
            (CommandLog(command="list VMs", embedding=TEST_EMBEDDING), 0.9),
            (CommandLog(command="show all VMs", embedding=TEST_EMBEDDING), 0.8),
        ]
        
        # Set up the mock session to return our test results
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.order_by.return_value.limit.return_value = mock_results
        
        # Mock the create_embedding method
        with patch.object(db_manager, 'create_embedding', return_value=TEST_EMBEDDING):
            # Test finding similar commands
            similar_commands = db_manager.find_similar_commands(TEST_COMMAND, limit=2)
            
            # Verify results
            assert len(similar_commands) == 2
            assert similar_commands[0][0] == "list VMs"
            assert similar_commands[0][1] == 0.9
            assert similar_commands[1][0] == "show all VMs"
            assert similar_commands[1][1] == 0.8
    
    def test_update_node(self, db_manager_with_mock_session):
        """Test updating or creating nodes in the database"""
        db_manager = db_manager_with_mock_session
        mock_session = db_manager._session
        
        # Create a node dict with test data
        node_data = {
            "id": "pve-01",
            "name": "proxmox-01",
            "status": "online",
            "ip": "192.168.1.10",
            "cpu": 8,
            "memory": 32768,
            "uptime": 1209600  # 14 days in seconds
        }
        
        # Set up mock to simulate node not found (for create case)
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value.first.return_value = None
        
        # Test creating a new node
        db_manager.update_node(node_data)
        
        # Verify a new Node object was added
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
        node_obj = mock_session.add.call_args[0][0]
        assert isinstance(node_obj, Node)
        assert node_obj.id == node_data["id"]
        assert node_obj.name == node_data["name"]
        assert node_obj.status == node_data["status"]
        
        # Reset mocks for update test
        mock_session.reset_mock()
        
        # Set up mock to simulate existing node found
        existing_node = Node(id=node_data["id"])
        mock_query.filter.return_value.first.return_value = existing_node
        
        # Test updating an existing node
        updated_data = node_data.copy()
        updated_data["status"] = "offline"
        db_manager.update_node(updated_data)
        
        # Verify the node was updated and not added
        mock_session.add.assert_not_called()
        mock_session.commit.assert_called_once()
        assert existing_node.status == "offline"
