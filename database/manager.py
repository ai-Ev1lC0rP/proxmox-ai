"""
Database manager for Proxmox AI with PostgreSQL and pgvector support

This module provides database connection management and
vector embedding operations for semantic search capabilities.
"""
from typing import List, Dict, Any, Optional, Tuple, Union
import os
import logging
import numpy as np
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.exc import SQLAlchemyError

# For vector embeddings
from sentence_transformers import SentenceTransformer

from database.schema import (
    Base, ProxmoxNode, VirtualMachine, Container, 
    Storage, CommandLog, ProxmoxTask, ScriptTemplate
)

logger = logging.getLogger(__name__)

class DatabaseManager:
    """
    Manages database connections and operations with support for vector embeddings
    """
    
    def __init__(self, db_url: str = None):
        """
        Initialize the database manager
        
        Args:
            db_url: PostgreSQL connection URL. If None, read from environment.
        """
        if db_url is None:
            # Default to environment variable or local development setup
            db_url = os.environ.get(
                'PROXMOX_DB_URL', 
                'postgresql://postgres:postgres@localhost:5432/proxmox_ai'
            )
        
        self.db_url = db_url
        self.engine = create_engine(db_url)
        self.session_factory = sessionmaker(bind=self.engine)
        self.Session = scoped_session(self.session_factory)
        
        # Load the embedding model for semantic search 
        # (using a small model for efficiency)
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
    
    def init_db(self) -> None:
        """Initialize the database schema"""
        try:
            # Create pgvector extension if it doesn't exist
            self.engine.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            
            # Create tables
            Base.metadata.create_all(self.engine)
            logger.info("Database schema created successfully")
        except SQLAlchemyError as e:
            logger.error(f"Error initializing database: {e}")
            raise
    
    def create_text_embedding(self, text: str) -> np.ndarray:
        """
        Create a vector embedding for text
        
        Args:
            text: The text to embed
            
        Returns:
            Vector embedding as a numpy array
        """
        # Get vector embedding from the model
        return self.embedding_model.encode(text)
    
    def vector_to_pg_array(self, vector: np.ndarray) -> str:
        """
        Convert a numpy vector to a PostgreSQL array string format
        
        Args:
            vector: The vector to convert
            
        Returns:
            String representation for PostgreSQL
        """
        return f"[{','.join(str(x) for x in vector)}]"
    
    def store_command_log(self, command: str, output: str = None, 
                         success: bool = True, error_message: str = None,
                         node_name: str = None, resource_id: int = None,
                         resource_type: str = None) -> CommandLog:
        """
        Store a command log with vector embedding for future retrieval
        
        Args:
            command: The command that was executed
            output: Command output (if available)
            success: Whether the command succeeded
            error_message: Error message (if any)
            node_name: Target Proxmox node name
            resource_id: Target resource ID (VM or container ID)
            resource_type: Type of resource ('vm', 'container', etc.)
            
        Returns:
            The created CommandLog object
        """
        try:
            # Create embedding for semantic search
            embedding = self.create_text_embedding(command)
            embedding_str = self.vector_to_pg_array(embedding)
            
            # Create CommandLog object
            command_log = CommandLog(
                command=command,
                output=output,
                success=success,
                error_message=error_message,
                node_name=node_name,
                resource_id=resource_id,
                resource_type=resource_type,
                embedding=embedding_str
            )
            
            # Store in database
            session = self.Session()
            session.add(command_log)
            session.commit()
            logger.info(f"Command log stored: {command[:30]}...")
            
            return command_log
        except Exception as e:
            logger.error(f"Error storing command log: {e}")
            session.rollback()
            raise
        finally:
            session.close()
    
    def search_similar_commands(self, query: str, limit: int = 5) -> List[CommandLog]:
        """
        Search for semantically similar commands using vector embeddings
        
        Args:
            query: The search query
            limit: Maximum number of results to return
            
        Returns:
            List of matching CommandLog objects
        """
        try:
            # Create embedding for the query
            query_embedding = self.create_text_embedding(query)
            query_embedding_str = self.vector_to_pg_array(query_embedding)
            
            # Use pgvector to find similar commands
            session = self.Session()
            # This requires the pgvector extension to be installed
            sql = text(f"""
                SELECT id, command, output, success, error_message, timestamp,
                       node_name, resource_id, resource_type,
                       embedding <-> '{query_embedding_str}'::vector as distance
                FROM command_logs
                ORDER BY distance ASC
                LIMIT :limit
            """)
            
            result = session.execute(sql, {"limit": limit})
            command_logs = []
            
            for row in result:
                cmd_log = CommandLog(
                    id=row.id,
                    command=row.command,
                    output=row.output,
                    success=row.success,
                    error_message=row.error_message,
                    timestamp=row.timestamp,
                    node_name=row.node_name,
                    resource_id=row.resource_id,
                    resource_type=row.resource_type,
                    embedding=row.embedding
                )
                command_logs.append(cmd_log)
            
            return command_logs
        except Exception as e:
            logger.error(f"Error searching similar commands: {e}")
            raise
        finally:
            session.close()
    
    def update_proxmox_data(self, data_type: str, data: List[Dict[str, Any]]) -> None:
        """
        Update Proxmox data in the database
        
        Args:
            data_type: Type of data ('nodes', 'vms', 'containers', 'storage')
            data: List of data objects to store
        """
        try:
            session = self.Session()
            
            if data_type == 'nodes':
                for node_data in data:
                    node = session.query(ProxmoxNode).filter_by(
                        node_id=node_data['node']
                    ).first()
                    
                    if node:
                        # Update existing node
                        node.name = node_data.get('name', node.name)
                        node.status = node_data.get('status', node.status)
                        node.uptime = node_data.get('uptime', node.uptime)
                        # Update other fields as needed
                    else:
                        # Create new node
                        node = ProxmoxNode(
                            node_id=node_data['node'],
                            name=node_data.get('name', node_data['node']),
                            status=node_data.get('status'),
                            uptime=node_data.get('uptime'),
                            # Set other fields as needed
                        )
                        session.add(node)
            
            elif data_type == 'vms':
                for vm_data in data:
                    vm = session.query(VirtualMachine).filter_by(
                        vmid=vm_data['vmid']
                    ).first()
                    
                    # Get parent node
                    node = session.query(ProxmoxNode).filter_by(
                        node_id=vm_data['node']
                    ).first()
                    
                    if node is None:
                        # Create a minimal node entry if it doesn't exist
                        node = ProxmoxNode(
                            node_id=vm_data['node'],
                            name=vm_data['node']
                        )
                        session.add(node)
                        session.flush()
                    
                    if vm:
                        # Update existing VM
                        vm.name = vm_data.get('name', vm.name)
                        vm.status = vm_data.get('status', vm.status)
                        vm.cpu = vm_data.get('cpus', vm.cpu)
                        vm.memory = vm_data.get('maxmem', vm.memory)
                        vm.disk = vm_data.get('maxdisk', vm.disk)
                        vm.template = vm_data.get('template', vm.template)
                        vm.node_id = node.id
                    else:
                        # Create new VM
                        vm = VirtualMachine(
                            vmid=vm_data['vmid'],
                            name=vm_data.get('name'),
                            status=vm_data.get('status'),
                            cpu=vm_data.get('cpus'),
                            memory=vm_data.get('maxmem'),
                            disk=vm_data.get('maxdisk'),
                            template=vm_data.get('template', 0),
                            node_id=node.id
                        )
                        session.add(vm)
            
            elif data_type == 'containers':
                for ct_data in data:
                    container = session.query(Container).filter_by(
                        vmid=ct_data['vmid']
                    ).first()
                    
                    # Get parent node
                    node = session.query(ProxmoxNode).filter_by(
                        node_id=ct_data['node']
                    ).first()
                    
                    if node is None:
                        # Create a minimal node entry if it doesn't exist
                        node = ProxmoxNode(
                            node_id=ct_data['node'],
                            name=ct_data['node']
                        )
                        session.add(node)
                        session.flush()
                    
                    if container:
                        # Update existing container
                        container.name = ct_data.get('name', container.name)
                        container.status = ct_data.get('status', container.status)
                        container.cpu = ct_data.get('cpus', container.cpu)
                        container.memory = ct_data.get('maxmem', container.memory)
                        container.disk = ct_data.get('maxdisk', container.disk)
                        container.node_id = node.id
                    else:
                        # Create new container
                        container = Container(
                            vmid=ct_data['vmid'],
                            name=ct_data.get('name'),
                            status=ct_data.get('status'),
                            cpu=ct_data.get('cpus'),
                            memory=ct_data.get('maxmem'),
                            disk=ct_data.get('maxdisk'),
                            node_id=node.id
                        )
                        session.add(container)
            
            elif data_type == 'storage':
                for storage_data in data:
                    storage = session.query(Storage).filter_by(
                        storage_id=storage_data['storage'],
                        node_name=storage_data['node']
                    ).first()
                    
                    if storage:
                        # Update existing storage
                        storage.type = storage_data.get('type', storage.type)
                        storage.content = storage_data.get('content', storage.content)
                        storage.total = storage_data.get('total', storage.total)
                        storage.used = storage_data.get('used', storage.used)
                        storage.available = storage_data.get('avail', storage.available)
                    else:
                        # Create new storage
                        storage = Storage(
                            storage_id=storage_data['storage'],
                            node_name=storage_data['node'],
                            type=storage_data.get('type'),
                            content=storage_data.get('content'),
                            total=storage_data.get('total'),
                            used=storage_data.get('used'),
                            available=storage_data.get('avail')
                        )
                        session.add(storage)
            
            session.commit()
            logger.info(f"Updated {data_type} data in database")
        except Exception as e:
            logger.error(f"Error updating {data_type} data: {e}")
            session.rollback()
            raise
        finally:
            session.close()
    
    def get_script_templates(self, script_type: str = None) -> List[ScriptTemplate]:
        """
        Get script templates from the database
        
        Args:
            script_type: Optional filter by script type ('vm', 'ct', etc.)
            
        Returns:
            List of ScriptTemplate objects
        """
        try:
            session = self.Session()
            query = session.query(ScriptTemplate)
            
            if script_type:
                query = query.filter_by(script_type=script_type)
            
            return query.all()
        except Exception as e:
            logger.error(f"Error getting script templates: {e}")
            raise
        finally:
            session.close()
    
    def search_script_templates(self, query: str, limit: int = 5) -> List[ScriptTemplate]:
        """
        Search for script templates using vector embeddings
        
        Args:
            query: The search query
            limit: Maximum number of results to return
            
        Returns:
            List of matching ScriptTemplate objects
        """
        try:
            # Create embedding for the query
            query_embedding = self.create_text_embedding(query)
            query_embedding_str = self.vector_to_pg_array(query_embedding)
            
            # Use pgvector to find similar script templates
            session = self.Session()
            sql = text(f"""
                SELECT id, name, script_type, description, template_path, 
                       parameters, syntax_example,
                       embedded_description <-> '{query_embedding_str}'::vector as distance
                FROM script_templates
                ORDER BY distance ASC
                LIMIT :limit
            """)
            
            result = session.execute(sql, {"limit": limit})
            templates = []
            
            for row in result:
                template = ScriptTemplate(
                    id=row.id,
                    name=row.name,
                    script_type=row.script_type,
                    description=row.description,
                    template_path=row.template_path,
                    parameters=row.parameters,
                    syntax_example=row.syntax_example,
                    embedded_description=row.embedded_description
                )
                templates.append(template)
            
            return templates
        except Exception as e:
            logger.error(f"Error searching script templates: {e}")
            raise
        finally:
            session.close()
