"""
Database schema definitions for Proxmox AI

This module defines the SQLAlchemy models and PostgreSQL schema 
with pgvector extension support for vector embeddings.
"""
from typing import List, Optional, Dict, Any
import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean, JSON, Float, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
import numpy as np

Base = declarative_base()

class ProxmoxNode(Base):
    """Model representing a Proxmox node in the cluster"""
    __tablename__ = 'proxmox_nodes'
    
    id = Column(Integer, primary_key=True)
    node_id = Column(String(255), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    status = Column(String(50))
    uptime = Column(Integer)
    ip_address = Column(String(50))
    cpu_model = Column(String(255))
    cpu_count = Column(Integer)
    cpu_usage = Column(Float)
    memory_total = Column(Integer)
    memory_used = Column(Integer)
    memory_free = Column(Integer)
    disk_total = Column(Integer)
    disk_used = Column(Integer)
    disk_free = Column(Integer)
    last_updated = Column(DateTime, default=datetime.datetime.utcnow)
    
    vms = relationship("VirtualMachine", back_populates="node")
    containers = relationship("Container", back_populates="node")
    
    def __repr__(self) -> str:
        return f"<ProxmoxNode(name='{self.name}', status='{self.status}')>"


class VirtualMachine(Base):
    """Model representing a virtual machine"""
    __tablename__ = 'virtual_machines'
    
    id = Column(Integer, primary_key=True)
    vmid = Column(Integer, nullable=False)
    name = Column(String(255))
    status = Column(String(50))
    cpu = Column(Integer)
    memory = Column(Integer)
    disk = Column(Integer)
    template = Column(Boolean, default=False)
    node_id = Column(Integer, ForeignKey('proxmox_nodes.id'))
    tags = Column(String(255))
    config = Column(JSON)
    last_updated = Column(DateTime, default=datetime.datetime.utcnow)
    
    node = relationship("ProxmoxNode", back_populates="vms")
    
    def __repr__(self) -> str:
        return f"<VirtualMachine(vmid={self.vmid}, name='{self.name}', status='{self.status}')>"


class Container(Base):
    """Model representing an LXC container"""
    __tablename__ = 'containers'
    
    id = Column(Integer, primary_key=True)
    vmid = Column(Integer, nullable=False)
    name = Column(String(255))
    status = Column(String(50))
    cpu = Column(Integer)
    memory = Column(Integer)
    disk = Column(Integer)
    template = Column(Boolean, default=False)
    node_id = Column(Integer, ForeignKey('proxmox_nodes.id'))
    tags = Column(String(255))
    config = Column(JSON)
    last_updated = Column(DateTime, default=datetime.datetime.utcnow)
    
    node = relationship("ProxmoxNode", back_populates="containers")
    
    def __repr__(self) -> str:
        return f"<Container(vmid={self.vmid}, name='{self.name}', status='{self.status}')>"


class Storage(Base):
    """Model representing a storage resource"""
    __tablename__ = 'storage'
    
    id = Column(Integer, primary_key=True)
    storage_id = Column(String(255), nullable=False)
    node_name = Column(String(255), nullable=False)
    type = Column(String(50))
    content = Column(String(255))
    total = Column(Integer)
    used = Column(Integer)
    available = Column(Integer)
    last_updated = Column(DateTime, default=datetime.datetime.utcnow)
    
    def __repr__(self) -> str:
        return f"<Storage(storage_id='{self.storage_id}', type='{self.type}')>"


class CommandLog(Base):
    """Model representing executed command logs with embeddings for semantic search"""
    __tablename__ = 'command_logs'
    
    id = Column(Integer, primary_key=True)
    command = Column(Text, nullable=False)
    output = Column(Text)
    success = Column(Boolean, default=True)
    error_message = Column(Text)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Related models if this is a command that targeted specific resources
    node_name = Column(String(255))
    resource_id = Column(Integer)
    resource_type = Column(String(50))  # 'vm', 'container', 'storage', etc.
    
    # For pgvector - will be an embedding of the command for semantic search
    # We'll use the pgvector extension to store and query these embeddings
    embedding = Column(String)  # This will be converted to a vector by pgvector
    
    def __repr__(self) -> str:
        return f"<CommandLog(command='{self.command[:30]}...', success={self.success})>"


class ProxmoxTask(Base):
    """Model representing Proxmox tasks"""
    __tablename__ = 'proxmox_tasks'
    
    id = Column(Integer, primary_key=True)
    task_id = Column(String(255), unique=True, nullable=False)
    type = Column(String(50))
    node = Column(String(255))
    status = Column(String(50))
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    duration = Column(Float)
    user = Column(String(255))
    description = Column(Text)
    
    def __repr__(self) -> str:
        return f"<ProxmoxTask(task_id='{self.task_id}', status='{self.status}')>"


class ScriptTemplate(Base):
    """Model representing script templates for VM/CT creation"""
    __tablename__ = 'script_templates'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    script_type = Column(String(50), nullable=False)  # 'vm', 'ct', 'util', etc.
    description = Column(Text)
    template_path = Column(String(255))
    parameters = Column(JSON)  # Parameters the script accepts
    syntax_example = Column(Text)  # Example command syntax
    embedded_description = Column(String)  # Vector embedding of the description for search
    
    def __repr__(self) -> str:
        return f"<ScriptTemplate(name='{self.name}', script_type='{self.script_type}')>"
