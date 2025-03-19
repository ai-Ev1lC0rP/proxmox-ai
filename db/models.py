"""
Database models for the Proxmox AI project.
Uses SQLAlchemy with pgvector extension for vector storage.
"""

import os
import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy import Column, Integer, String, Text, DateTime, create_engine, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from pgvector.sqlalchemy import Vector

# Create base class for declarative models
Base = declarative_base()

# Get database URL from environment or use default
DB_URL = os.environ.get("PROXMOX_DB_URL", "postgresql://postgres:postgres@localhost:5432/proxmox_ai")

class ProxmoxDocument(Base):
    """
    Model for storing Proxmox documentation and knowledge base articles.
    Includes vector embeddings for semantic search.
    """
    __tablename__ = "proxmox_documents"
    
    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    source = Column(String(255), nullable=True)
    doc_type = Column(String(50), nullable=False)  # e.g., "api", "guide", "script"
    embedding = Column(Vector(1536), nullable=True)  # 1536 is dimension for most embeddings
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "source": self.source,
            "doc_type": self.doc_type,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class ChatHistory(Base):
    """
    Model for storing chat history between users and the AI.
    Useful for context tracking and conversation continuity.
    """
    __tablename__ = "chat_history"
    
    id = Column(Integer, primary_key=True)
    session_id = Column(String(50), nullable=False, index=True)
    user_message = Column(Text, nullable=True)
    ai_response = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        return {
            "id": self.id,
            "session_id": self.session_id,
            "user_message": self.user_message,
            "ai_response": self.ai_response,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


# Create database engine and session factory
engine = create_engine(DB_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db(db_url: Optional[str] = None):
    """
    Initialize the database by creating all tables
    
    Args:
        db_url: Optional database URL to override the default
    """
    global engine, SessionLocal
    
    # If a new URL is provided, recreate the engine and session factory
    if db_url:
        engine = create_engine(db_url)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    Base.metadata.create_all(bind=engine)

def get_db():
    """Get a database session"""
    db = SessionLocal()
    try:
        return db
    except:
        db.close()
        raise
    return db
