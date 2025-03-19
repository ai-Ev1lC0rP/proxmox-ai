-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create proxmox_documents table with vector support
CREATE TABLE IF NOT EXISTS proxmox_documents (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    source VARCHAR(255),
    doc_type VARCHAR(50) NOT NULL,
    embedding vector(1536),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP
);

-- Create chat_history table
CREATE TABLE IF NOT EXISTS chat_history (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(50) NOT NULL,
    user_message TEXT,
    ai_response TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create index on session_id for faster lookups
CREATE INDEX IF NOT EXISTS idx_chat_history_session_id ON chat_history(session_id);

-- Create index on proxmox_documents for vector similarity search
CREATE INDEX IF NOT EXISTS idx_proxmox_documents_embedding ON proxmox_documents USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Create users table if needed for auth
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    email VARCHAR(100) UNIQUE,
    is_admin BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Add some initial metadata
INSERT INTO proxmox_documents (title, content, doc_type, source)
VALUES 
('Proxmox VE API Documentation', 'The Proxmox VE API is a RESTful API that allows you to manage your Proxmox VE environment programmatically.', 'documentation', 'https://pve.proxmox.com/pve-docs/api-viewer/'),
('Proxmox VM Creation', 'Virtual machines in Proxmox VE are managed through the qemu API endpoint. You can create, start, stop, and manage VMs using these endpoints.', 'guide', 'https://pve.proxmox.com/wiki/Qemu/KVM_Virtual_Machines');
