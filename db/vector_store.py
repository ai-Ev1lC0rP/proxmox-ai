"""
Vector store implementation for semantic search in Proxmox AI.
Uses pgvector to store and query document embeddings.
"""

from typing import List, Dict, Any, Optional, Tuple
import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from pgvector.sqlalchemy import Vector, cosine_distance

from .models import ProxmoxDocument, get_db, ChatHistory, init_db


class VectorStore:
    """
    Vector store for semantic search of Proxmox documentation.
    Uses pgvector for efficient similarity search.
    """
    
    def __init__(self, embedding_dimension: int = 1536):
        """
        Initialize the vector store.
        
        Args:
            embedding_dimension: Dimension of the embedding vectors
        """
        self.embedding_dimension = embedding_dimension
        
    def add_document(self, 
                    title: str, 
                    content: str, 
                    embedding: List[float],
                    source: Optional[str] = None,
                    doc_type: str = "guide") -> int:
        """
        Add a document to the vector store.
        
        Args:
            title: Document title
            content: Document content
            embedding: Vector embedding of the document
            source: Source of the document (e.g., URL, file path)
            doc_type: Type of document (e.g., api, guide, script)
            
        Returns:
            ID of the new document
        """
        db = get_db()
        try:
            # Convert list to numpy array for pgvector
            embedding_array = np.array(embedding, dtype=np.float32)
            
            # Create new document with embedding
            doc = ProxmoxDocument(
                title=title,
                content=content,
                source=source,
                doc_type=doc_type,
                embedding=embedding_array
            )
            
            db.add(doc)
            db.commit()
            db.refresh(doc)
            
            return doc.id
        finally:
            db.close()
    
    def search_similar(self, 
                       query_embedding: List[float], 
                       limit: int = 5, 
                       doc_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Search for documents similar to the query embedding.
        
        Args:
            query_embedding: Vector embedding of the query
            limit: Maximum number of results to return
            doc_type: Optional filter by document type
            
        Returns:
            List of documents with similarity scores
        """
        db = get_db()
        try:
            # Convert query embedding to numpy array
            query_array = np.array(query_embedding, dtype=np.float32)
            
            # Build query
            query = db.query(
                ProxmoxDocument,
                func.cosine_distance(ProxmoxDocument.embedding, query_array).label('distance')
            ).order_by('distance')
            
            # Apply doc_type filter if specified
            if doc_type:
                query = query.filter(ProxmoxDocument.doc_type == doc_type)
            
            # Execute query with limit
            results = query.limit(limit).all()
            
            # Format results
            documents = []
            for doc, distance in results:
                doc_dict = doc.to_dict()
                # Convert distance to similarity score (1 - distance)
                doc_dict['similarity'] = 1 - distance
                documents.append(doc_dict)
            
            return documents
        finally:
            db.close()
    
    def update_document_embedding(self, doc_id: int, new_embedding: List[float]) -> bool:
        """
        Update the embedding for an existing document.
        
        Args:
            doc_id: ID of the document to update
            new_embedding: New vector embedding
            
        Returns:
            Success flag
        """
        db = get_db()
        try:
            # Convert to numpy array
            embedding_array = np.array(new_embedding, dtype=np.float32)
            
            # Get document
            doc = db.query(ProxmoxDocument).filter(ProxmoxDocument.id == doc_id).first()
            
            if not doc:
                return False
            
            # Update embedding
            doc.embedding = embedding_array
            db.commit()
            
            return True
        finally:
            db.close()
    
    def delete_document(self, doc_id: int) -> bool:
        """
        Delete a document from the vector store.
        
        Args:
            doc_id: ID of the document to delete
            
        Returns:
            Success flag
        """
        db = get_db()
        try:
            doc = db.query(ProxmoxDocument).filter(ProxmoxDocument.id == doc_id).first()
            
            if not doc:
                return False
            
            db.delete(doc)
            db.commit()
            
            return True
        finally:
            db.close()
    
    def get_document_by_id(self, doc_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a document by its ID.
        
        Args:
            doc_id: ID of the document
            
        Returns:
            Document dictionary or None if not found
        """
        db = get_db()
        try:
            doc = db.query(ProxmoxDocument).filter(ProxmoxDocument.id == doc_id).first()
            
            if not doc:
                return None
            
            return doc.to_dict()
        finally:
            db.close()
            
    def get_all_documents(self, doc_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get all documents, optionally filtered by type.
        
        Args:
            doc_type: Optional filter by document type
            
        Returns:
            List of document dictionaries
        """
        db = get_db()
        try:
            query = db.query(ProxmoxDocument)
            
            if doc_type:
                query = query.filter(ProxmoxDocument.doc_type == doc_type)
                
            docs = query.all()
            
            return [doc.to_dict() for doc in docs]
        finally:
            db.close()

    def semantic_search(self, query: str, limit: int = 5, doc_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Perform semantic search based on a text query.
        
        Args:
            query: Text query
            limit: Maximum number of results to return
            doc_type: Optional filter by document type
            
        Returns:
            List of documents with similarity scores
        """
        # Get query embedding from OllamaClient
        try:
            from core.ollama_client import OllamaClient
            import os
            
            # Initialize OllamaClient
            ollama = OllamaClient(
                base_url=os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434/v1"),
                model=os.environ.get("OLLAMA_MODEL", "llama3.2:latest")
            )
            
            # Generate embedding for query
            success, embedding_result = ollama.generate_embeddings(query)
            
            if not success or 'embedding' not in embedding_result:
                raise Exception("Failed to generate embeddings for query")
                
            query_embedding = embedding_result['embedding']
            
            # Search using embedding
            return self.search_similar(query_embedding, limit, doc_type)
            
        except Exception as e:
            import logging
            logging.error(f"Semantic search error: {e}")
            return []
    
    def save_chat_history(self, session_id: str, user_message: str, ai_response: str) -> bool:
        """
        Save chat history to database.
        
        Args:
            session_id: Unique session identifier
            user_message: User's message
            ai_response: AI's response
            
        Returns:
            Success flag
        """
        db = get_db()
        try:
            # Create new chat history entry
            chat = ChatHistory(
                session_id=session_id,
                user_message=user_message,
                ai_response=ai_response,
                timestamp=func.now()
            )
            
            db.add(chat)
            db.commit()
            
            return True
        except Exception as e:
            import logging
            logging.error(f"Error saving chat history: {e}")
            return False
        finally:
            db.close()
    
    def get_chat_history(self, session_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get chat history for a specific session.
        
        Args:
            session_id: Unique session identifier
            limit: Maximum number of messages to return
            
        Returns:
            List of chat history entries
        """
        db = get_db()
        try:
            # Get chat history for session, newest first
            chats = db.query(ChatHistory)\
                .filter(ChatHistory.session_id == session_id)\
                .order_by(desc(ChatHistory.timestamp))\
                .limit(limit)\
                .all()
            
            # Convert to dictionaries and reverse to get chronological order
            return [chat.to_dict() for chat in reversed(chats)]
        except Exception as e:
            import logging
            logging.error(f"Error getting chat history: {e}")
            return []
        finally:
            db.close()

    def init_db_url(self, db_url: str):
        """
        Initialize the database connection URL.
        
        Args:
            db_url: Database connection URL
        """
        init_db(db_url)
