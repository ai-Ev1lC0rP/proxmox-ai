"""
API routes for the Proxmox AI project.
Provides HTTP endpoints for interacting with Proxmox VE environments.
"""

from typing import Dict, List, Any, Optional, Union
from fastapi import FastAPI, HTTPException, Depends, Query, Body, Path
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.client import ProxmoxClient
from core.ai import ProxmoxAI
from utils.ollama import OllamaClient
from db.models import get_db
from db.vector_store import VectorStore

# Create FastAPI app
app = FastAPI(title="Proxmox AI API", 
              description="API for managing Proxmox VE environments with AI assistance",
              version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models for request/response validation
class ChatRequest(BaseModel):
    """Chat request model"""
    message: str
    history: Optional[List[Dict[str, str]]] = []
    session_id: Optional[str] = None
    

class ChatResponse(BaseModel):
    """Chat response model"""
    response: str
    session_id: str
    

class ProxmoxCredentials(BaseModel):
    """Proxmox credentials model"""
    host: str
    port: Optional[int] = 8006
    token_id: Optional[str] = None
    token_secret: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    verify_ssl: Optional[bool] = False


class VMConfig(BaseModel):
    """VM configuration model"""
    name: str
    cores: int
    memory: int  # in MB
    disk_size: int  # in GB
    iso: Optional[str] = None
    network_bridge: Optional[str] = "vmbr0"
    additional_config: Optional[Dict[str, Any]] = None


class ContainerConfig(BaseModel):
    """Container configuration model"""
    name: str
    cores: int
    memory: int  # in MB
    disk_size: int  # in GB
    template: str
    network_bridge: Optional[str] = "vmbr0"
    unprivileged: Optional[bool] = True
    additional_config: Optional[Dict[str, Any]] = None


# Get clients
def get_proxmox_client():
    """Get an initialized Proxmox client using environment variables"""
    host = os.environ.get("PROXMOX_HOST", "localhost")
    port = int(os.environ.get("PROXMOX_PORT", "8006"))
    token_id = os.environ.get("PROXMOX_TOKEN_ID")
    token_secret = os.environ.get("PROXMOX_SECRET")
    verify_ssl = os.environ.get("PROXMOX_VERIFY_SSL", "false").lower() == "true"
    
    if not (token_id and token_secret):
        # Fallback to username/password if tokens aren't provided
        username = os.environ.get("PROXMOX_USER")
        password = os.environ.get("PROXMOX_PASSWORD")
        
        if not (username and password):
            raise ValueError("Proxmox credentials not provided in environment variables")
            
        return ProxmoxClient(
            host=host,
            port=port,
            username=username,
            password=password,
            verify_ssl=verify_ssl
        )
    
    return ProxmoxClient(
        host=host,
        port=port,
        token_id=token_id,
        token_secret=token_secret,
        verify_ssl=verify_ssl
    )


def get_ollama_client():
    """Get an initialized Ollama client using environment variables"""
    base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434/v1")
    model = os.environ.get("OLLAMA_MODEL", "llama3.2:latest")
    return OllamaClient(base_url=base_url, model=model)


def get_proxmox_ai():
    """Get an initialized ProxmoxAI instance"""
    try:
        proxmox_client = get_proxmox_client()
        ollama_client = get_ollama_client()
        vector_store = VectorStore()
        
        return ProxmoxAI(
            proxmox_client=proxmox_client,
            ollama_client=ollama_client,
            vector_store=vector_store
        )
    except Exception as e:
        # If we can't connect to Proxmox, create AI without proxmox client
        print(f"Warning: Could not connect to Proxmox - {str(e)}")
        ollama_client = get_ollama_client()
        vector_store = VectorStore()
        
        return ProxmoxAI(
            proxmox_client=None,
            ollama_client=ollama_client,
            vector_store=vector_store
        )


# Routes
@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Welcome to Proxmox AI API"}


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    # Check Ollama connection
    ollama_client = get_ollama_client()
    ollama_status, ollama_message = ollama_client.check_connection()
    
    # Try to check Proxmox connection
    proxmox_status = False
    proxmox_message = "Not configured"
    
    try:
        proxmox_client = get_proxmox_client()
        nodes = proxmox_client.get_node_status()
        if nodes:
            proxmox_status = True
            proxmox_message = f"Connected ({len(nodes)} nodes)"
        else:
            proxmox_message = "No nodes found"
    except Exception as e:
        proxmox_message = f"Error: {str(e)}"
    
    # Check database connection
    db_status = False
    db_message = "Not checked"
    
    try:
        db = get_db()
        db.execute("SELECT 1")
        db_status = True
        db_message = "Connected"
    except Exception as e:
        db_message = f"Error: {str(e)}"
    
    return {
        "status": "ok" if ollama_status else "degraded",
        "services": {
            "ollama": {
                "status": "healthy" if ollama_status else "unhealthy",
                "message": ollama_message
            },
            "proxmox": {
                "status": "healthy" if proxmox_status else "unhealthy",
                "message": proxmox_message
            },
            "database": {
                "status": "healthy" if db_status else "unhealthy",
                "message": db_message
            }
        }
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Chat with the Proxmox AI assistant"""
    proxmox_ai = get_proxmox_ai()
    
    # Convert history format if needed
    formatted_history = []
    for msg in request.history:
        if isinstance(msg, dict) and "role" in msg and "content" in msg:
            formatted_history.append(msg)
        elif isinstance(msg, dict) and "user" in msg:
            formatted_history.append({"role": "user", "content": msg["user"]})
        elif isinstance(msg, dict) and "assistant" in msg:
            formatted_history.append({"role": "assistant", "content": msg["assistant"]})
    
    # Get response from AI
    response = proxmox_ai.chat(
        message=request.message,
        history=formatted_history,
        session_id=request.session_id
    )
    
    return {"response": response, "session_id": request.session_id or "new_session"}


@app.get("/nodes", response_model=List[Dict[str, Any]])
async def get_nodes():
    """Get all Proxmox nodes"""
    try:
        proxmox_client = get_proxmox_client()
        return proxmox_client.get_node_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting nodes: {str(e)}")


@app.get("/vms", response_model=List[Dict[str, Any]])
async def get_vms(node: Optional[str] = None):
    """Get all virtual machines"""
    try:
        proxmox_client = get_proxmox_client()
        return proxmox_client.get_vms(node=node)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting VMs: {str(e)}")


@app.get("/containers", response_model=List[Dict[str, Any]])
async def get_containers(node: Optional[str] = None):
    """Get all containers"""
    try:
        proxmox_client = get_proxmox_client()
        return proxmox_client.get_containers(node=node)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting containers: {str(e)}")


@app.post("/vms/{node}/{vmid}/start")
async def start_vm(node: str, vmid: int):
    """Start a virtual machine"""
    try:
        proxmox_client = get_proxmox_client()
        result = proxmox_client.start_vm(node=node, vmid=vmid)
        return {"success": True, "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error starting VM: {str(e)}")


@app.post("/vms/{node}/{vmid}/stop")
async def stop_vm(node: str, vmid: int):
    """Stop a virtual machine"""
    try:
        proxmox_client = get_proxmox_client()
        result = proxmox_client.stop_vm(node=node, vmid=vmid)
        return {"success": True, "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error stopping VM: {str(e)}")


@app.post("/containers/{node}/{vmid}/start")
async def start_container(node: str, vmid: int):
    """Start a container"""
    try:
        proxmox_client = get_proxmox_client()
        result = proxmox_client.start_container(node=node, vmid=vmid)
        return {"success": True, "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error starting container: {str(e)}")


@app.post("/containers/{node}/{vmid}/stop")
async def stop_container(node: str, vmid: int):
    """Stop a container"""
    try:
        proxmox_client = get_proxmox_client()
        result = proxmox_client.stop_container(node=node, vmid=vmid)
        return {"success": True, "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error stopping container: {str(e)}")


@app.post("/vms/create", response_model=Dict[str, Any])
async def create_vm(node: str, config: VMConfig):
    """Create a new virtual machine"""
    try:
        proxmox_client = get_proxmox_client()
        vmid = proxmox_client.get_next_vmid()
        
        result = proxmox_client.create_vm(
            node=node,
            vmid=vmid,
            name=config.name,
            cores=config.cores,
            memory=config.memory,
            disk_size=config.disk_size,
            iso=config.iso,
            network_bridge=config.network_bridge,
            additional_config=config.additional_config
        )
        
        return {
            "success": True,
            "vmid": vmid,
            "result": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating VM: {str(e)}")


@app.post("/containers/create", response_model=Dict[str, Any])
async def create_container(node: str, config: ContainerConfig):
    """Create a new container"""
    try:
        proxmox_client = get_proxmox_client()
        vmid = proxmox_client.get_next_vmid()
        
        result = proxmox_client.create_container(
            node=node,
            vmid=vmid,
            name=config.name,
            cores=config.cores,
            memory=config.memory,
            disk_size=config.disk_size,
            template=config.template,
            network_bridge=config.network_bridge,
            unprivileged=config.unprivileged,
            additional_config=config.additional_config
        )
        
        return {
            "success": True,
            "vmid": vmid,
            "result": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating container: {str(e)}")


@app.get("/backups", response_model=List[Dict[str, Any]])
async def get_backups(node: Optional[str] = None):
    """Get all backups"""
    try:
        proxmox_client = get_proxmox_client()
        return proxmox_client.get_backups(node=node)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting backups: {str(e)}")


@app.post("/backups/create")
async def create_backup(node: str, vmid: int, mode: str = "snapshot", compress: bool = True):
    """Create a new backup"""
    try:
        proxmox_client = get_proxmox_client()
        result = proxmox_client.create_backup(
            node=node,
            vmid=vmid,
            mode=mode,
            compress=compress
        )
        
        return {
            "success": True,
            "result": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating backup: {str(e)}")


@app.get("/storage", response_model=List[Dict[str, Any]])
async def get_storage(node: Optional[str] = None):
    """Get storage information"""
    try:
        proxmox_client = get_proxmox_client()
        return proxmox_client.get_storage(node=node)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting storage info: {str(e)}")


@app.get("/cluster/resources", response_model=Dict[str, Any])
async def get_cluster_resources():
    """Get cluster resources overview"""
    try:
        proxmox_client = get_proxmox_client()
        resources = {}
        
        # Get VMs, containers, and storage resources
        resources["vms"] = proxmox_client.get_vms()
        resources["containers"] = proxmox_client.get_containers()
        resources["storage"] = proxmox_client.get_storage()
        
        # Get node information
        resources["nodes"] = proxmox_client.get_node_status()
        
        # Compile resource usage statistics
        total_memory = 0
        used_memory = 0
        total_disk = 0
        used_disk = 0
        total_vcpu = 0
        
        # Calculate totals from nodes
        for node in resources["nodes"]:
            if "maxmem" in node:
                total_memory += node.get("maxmem", 0)
            if "mem" in node:
                used_memory += node.get("mem", 0)
            if "maxdisk" in node:
                total_disk += node.get("maxdisk", 0)
            if "disk" in node:
                used_disk += node.get("disk", 0)
            if "maxcpu" in node:
                total_vcpu += node.get("maxcpu", 0)
        
        # Count VMs and containers
        vm_count = len(resources["vms"])
        container_count = len(resources["containers"])
        
        # Add summary
        resources["summary"] = {
            "total_memory": total_memory,
            "used_memory": used_memory,
            "memory_usage_percent": (used_memory / total_memory * 100) if total_memory > 0 else 0,
            "total_disk": total_disk,
            "used_disk": used_disk,
            "disk_usage_percent": (used_disk / total_disk * 100) if total_disk > 0 else 0,
            "total_vcpu": total_vcpu,
            "vm_count": vm_count,
            "container_count": container_count,
            "total_instances": vm_count + container_count
        }
        
        return resources
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting cluster resources: {str(e)}")


@app.get("/ollama/models", response_model=List[Dict[str, Any]])
async def get_ollama_models():
    """Get available Ollama models"""
    try:
        ollama_client = get_ollama_client()
        return ollama_client.list_models()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting Ollama models: {str(e)}")


@app.get("/docs/search", response_model=List[Dict[str, Any]])
async def search_documentation(query: str, limit: int = 5):
    """
    Search documentation using semantic search.
    Requires the query to be converted to an embedding.
    """
    try:
        # Get the Ollama client for embeddings
        ollama_client = get_ollama_client()
        
        # Get embedding for the query
        embedding_response = ollama_client.embeddings(query)
        
        if "error" in embedding_response:
            raise HTTPException(status_code=500, detail=embedding_response["error"])
            
        embedding = embedding_response.get("embedding", [])
        
        if not embedding:
            raise HTTPException(status_code=500, detail="Failed to get embedding for query")
        
        # Search the vector store
        vector_store = VectorStore()
        results = vector_store.search_similar(embedding, limit=limit)
        
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching documentation: {str(e)}")

from fastapi import APIRouter, Depends, HTTPException, Query, Body, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Union
import os
import logging

from core.client import ProxmoxClient
from core.ollama_client import OllamaClient
from core.agents.vm_converter import VMConverterAgent
from core.agents.backup_agent import ProxmoxBackupAgent
from core.agents.monitoring_agent import ProxmoxMonitoringAgent
from db.vector_store import VectorStore

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("api_routes")

# Create API router
router = APIRouter()

# Dependency for ProxmoxClient
def get_proxmox_client():
    """Dependency to get configured ProxmoxClient"""
    try:
        client = ProxmoxClient(
            host=os.environ.get("PROXMOX_HOST", "localhost"),
            port=int(os.environ.get("PROXMOX_PORT", "8006")),
            token_id=os.environ.get("PROXMOX_TOKEN_ID"),
            token_secret=os.environ.get("PROXMOX_SECRET"),
            verify_ssl=os.environ.get("PROXMOX_VERIFY_SSL", "false").lower() == "true"
        )
        return client
    except Exception as e:
        logger.error(f"Failed to create ProxmoxClient: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to connect to Proxmox API: {str(e)}")

# Dependency for OllamaClient
def get_ollama_client():
    """Dependency to get configured OllamaClient"""
    try:
        client = OllamaClient(
            base_url=os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434/v1"),
            model=os.environ.get("OLLAMA_MODEL", "llama3.2:latest")
        )
        return client
    except Exception as e:
        logger.error(f"Failed to create OllamaClient: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to initialize Ollama client: {str(e)}")

# Dependency for VectorStore
def get_vector_store():
    """Dependency to get configured VectorStore"""
    try:
        vector_store = VectorStore(
            db_url=os.environ.get("PROXMOX_DB_URL", "postgresql://postgres:postgres@localhost:5432/proxmox_ai")
        )
        return vector_store
    except Exception as e:
        logger.error(f"Failed to create VectorStore: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to initialize Vector Store: {str(e)}")

# Define Pydantic models for request/response validation
class ChatRequest(BaseModel):
    """Model for chat requests"""
    message: str = Field(..., description="User message")
    session_id: str = Field(..., description="Session ID for conversation tracking")
    context: Optional[List[Dict[str, str]]] = Field(None, description="Previous conversation context")

class ChatResponse(BaseModel):
    """Model for chat responses"""
    response: str = Field(..., description="AI response")
    session_id: str = Field(..., description="Session ID for conversation tracking")
    context: List[Dict[str, str]] = Field(..., description="Updated conversation context")

class CommandRequest(BaseModel):
    """Model for natural language command requests"""
    command: str = Field(..., description="Natural language command to execute")
    node: Optional[str] = Field(None, description="Target node for the command")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context for command execution")

class VMConverterRequest(BaseModel):
    """Model for VM to container conversion requests"""
    node: str = Field(..., description="Node name")
    vmid: int = Field(..., description="VM ID to convert")
    new_ctid: Optional[int] = Field(None, description="Target container ID (if None, next available ID is used)")
    storage: str = Field("local", description="Storage for the new container")
    keep_vm: bool = Field(True, description="Whether to keep the original VM after conversion")

class BackupRequest(BaseModel):
    """Model for backup requests"""
    node: str = Field(..., description="Node name")
    vmid: int = Field(..., description="VM or container ID")
    storage: str = Field("local", description="Storage name")
    mode: str = Field("snapshot", description="Backup mode ('snapshot', 'suspend', or 'stop')")
    compress: bool = Field(True, description="Whether to compress the backup")
    mail: Optional[str] = Field(None, description="Email to send notification to")
    remove: int = Field(0, description="Number of backups to keep (0 = keep all)")

class RestoreRequest(BaseModel):
    """Model for restore requests"""
    node: str = Field(..., description="Node name")
    backup_id: str = Field(..., description="Backup volid to restore")
    target_vmid: Optional[int] = Field(None, description="Target VM/CT ID (default: original ID)")
    target_storage: Optional[str] = Field(None, description="Target storage (default: original storage)")
    restore_type: str = Field("fast", description="Restore type ('fast' or 'full')")

# Health check endpoint
@router.get("/health")
async def health_check():
    """Check if the API is healthy"""
    return {"status": "healthy", "message": "Proxmox AI API is running"}

# Chat endpoint
@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest, 
    ollama_client: OllamaClient = Depends(get_ollama_client),
    vector_store: VectorStore = Depends(get_vector_store)
):
    """Process a chat message and return AI response"""
    try:
        # Search for relevant documentation based on user message
        search_results = vector_store.semantic_search(request.message, limit=3)
        
        # Create system prompt with relevant documentation
        system_prompt = (
            "You are a helpful Proxmox assistant. Use the following Proxmox documentation "
            "to provide accurate and helpful responses. If you don't know the answer, say so.\n\n"
        )
        
        if search_results:
            system_prompt += "Relevant documentation:\n"
            for result in search_results:
                system_prompt += f"- {result['title']}: {result['content']}\n"
        
        # Initialize or continue conversation context
        context = request.context or []
        
        # Generate completion
        success, response = ollama_client.generate_completion(
            prompt=request.message,
            context=context,
            system_prompt=system_prompt
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to generate response")
        
        # Extract AI message
        ai_message = response.get("choices", [{}])[0].get("message", {}).get("content", "")
        
        # Update context with new messages
        updated_context = context + [
            {"role": "user", "content": request.message},
            {"role": "assistant", "content": ai_message}
        ]
        
        # Save chat history to database
        vector_store.save_chat_history(
            session_id=request.session_id,
            user_message=request.message,
            ai_response=ai_message
        )
        
        return {
            "response": ai_message,
            "session_id": request.session_id,
            "context": updated_context
        }
    
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")

# Natural language command endpoint
@router.post("/command")
async def execute_command(
    request: CommandRequest,
    proxmox_client: ProxmoxClient = Depends(get_proxmox_client),
    ollama_client: OllamaClient = Depends(get_ollama_client)
):
    """Execute a natural language command on Proxmox"""
    try:
        # Get environment context if not provided
        context = request.context or {}
        if not context and request.node:
            # Get node resources as context
            context["node_status"] = proxmox_client.proxmox.nodes(request.node).status.get()
            context["node_vms"] = proxmox_client.get_vms(node=request.node)
            context["node_containers"] = proxmox_client.get_containers(node=request.node)
        
        # Generate Proxmox command from natural language
        success, command_result = ollama_client.generate_proxmox_command(
            user_request=request.command,
            proxmox_context=context
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to interpret command")
        
        generated_command = command_result.get("generated_command", "")
        
        # For now, we return the generated command but don't execute it
        # This is for safety - execution would require parsing the command properly
        return {
            "command": request.command,
            "interpreted_as": generated_command,
            "executed": False,
            "message": "Command was interpreted but not executed for safety. Review and execute manually."
        }
    
    except Exception as e:
        logger.error(f"Error in command endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Command error: {str(e)}")

# Proxmox environment endpoints
@router.get("/nodes")
async def get_nodes(proxmox_client: ProxmoxClient = Depends(get_proxmox_client)):
    """Get all Proxmox nodes"""
    try:
        nodes = proxmox_client.get_node_status()
        return {"nodes": nodes}
    except Exception as e:
        logger.error(f"Error getting nodes: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get nodes: {str(e)}")

@router.get("/vms")
async def get_vms(
    node: Optional[str] = Query(None, description="Filter by node name"),
    proxmox_client: ProxmoxClient = Depends(get_proxmox_client)
):
    """Get all VMs, optionally filtered by node"""
    try:
        vms = proxmox_client.get_vms(node=node)
        return {"vms": vms}
    except Exception as e:
        logger.error(f"Error getting VMs: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get VMs: {str(e)}")

@router.get("/containers")
async def get_containers(
    node: Optional[str] = Query(None, description="Filter by node name"),
    proxmox_client: ProxmoxClient = Depends(get_proxmox_client)
):
    """Get all containers, optionally filtered by node"""
    try:
        containers = proxmox_client.get_containers(node=node)
        return {"containers": containers}
    except Exception as e:
        logger.error(f"Error getting containers: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get containers: {str(e)}")

@router.get("/storage")
async def get_storage(
    node: Optional[str] = Query(None, description="Filter by node name"),
    proxmox_client: ProxmoxClient = Depends(get_proxmox_client)
):
    """Get storage information, optionally filtered by node"""
    try:
        storage = proxmox_client.get_storage(node=node)
        return {"storage": storage}
    except Exception as e:
        logger.error(f"Error getting storage: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get storage: {str(e)}")

# VM operations
@router.post("/vms/{node}/{vmid}/start")
async def start_vm(
    node: str,
    vmid: int,
    proxmox_client: ProxmoxClient = Depends(get_proxmox_client)
):
    """Start a VM"""
    try:
        result = proxmox_client.start_vm(node=node, vmid=vmid)
        return {"status": "success", "task": result}
    except Exception as e:
        logger.error(f"Error starting VM {vmid} on node {node}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start VM: {str(e)}")

@router.post("/vms/{node}/{vmid}/stop")
async def stop_vm(
    node: str,
    vmid: int,
    proxmox_client: ProxmoxClient = Depends(get_proxmox_client)
):
    """Stop a VM"""
    try:
        result = proxmox_client.stop_vm(node=node, vmid=vmid)
        return {"status": "success", "task": result}
    except Exception as e:
        logger.error(f"Error stopping VM {vmid} on node {node}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to stop VM: {str(e)}")

@router.post("/vms/{node}/{vmid}/shutdown")
async def shutdown_vm(
    node: str,
    vmid: int,
    timeout: int = Query(60, description="Shutdown timeout in seconds"),
    proxmox_client: ProxmoxClient = Depends(get_proxmox_client)
):
    """Gracefully shutdown a VM"""
    try:
        result = proxmox_client.shutdown_vm(node=node, vmid=vmid, timeout=timeout)
        return {"status": "success", "task": result}
    except Exception as e:
        logger.error(f"Error shutting down VM {vmid} on node {node}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to shutdown VM: {str(e)}")

# Container operations
@router.post("/containers/{node}/{vmid}/start")
async def start_container(
    node: str,
    vmid: int,
    proxmox_client: ProxmoxClient = Depends(get_proxmox_client)
):
    """Start a container"""
    try:
        result = proxmox_client.start_container(node=node, vmid=vmid)
        return {"status": "success", "task": result}
    except Exception as e:
        logger.error(f"Error starting container {vmid} on node {node}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start container: {str(e)}")

@router.post("/containers/{node}/{vmid}/stop")
async def stop_container(
    node: str,
    vmid: int,
    proxmox_client: ProxmoxClient = Depends(get_proxmox_client)
):
    """Stop a container"""
    try:
        result = proxmox_client.stop_container(node=node, vmid=vmid)
        return {"status": "success", "task": result}
    except Exception as e:
        logger.error(f"Error stopping container {vmid} on node {node}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to stop container: {str(e)}")

@router.post("/containers/{node}/{vmid}/shutdown")
async def shutdown_container(
    node: str,
    vmid: int,
    timeout: int = Query(60, description="Shutdown timeout in seconds"),
    proxmox_client: ProxmoxClient = Depends(get_proxmox_client)
):
    """Gracefully shutdown a container"""
    try:
        result = proxmox_client.shutdown_container(node=node, vmid=vmid, timeout=timeout)
        return {"status": "success", "task": result}
    except Exception as e:
        logger.error(f"Error shutting down container {vmid} on node {node}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to shutdown container: {str(e)}")

# VM to container conversion endpoints
@router.get("/vm-converter/list-convertible/{node}")
async def list_convertible_vms(
    node: str,
    proxmox_client: ProxmoxClient = Depends(get_proxmox_client)
):
    """List VMs that can be converted to containers"""
    try:
        converter = VMConverterAgent(proxmox_client)
        convertible_vms = converter.list_convertible_vms(node=node)
        return {"convertible_vms": convertible_vms}
    except Exception as e:
        logger.error(f"Error listing convertible VMs on node {node}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list convertible VMs: {str(e)}")

@router.post("/vm-converter/convert", status_code=202)
async def convert_vm_to_ct(
    request: VMConverterRequest,
    background_tasks: BackgroundTasks,
    proxmox_client: ProxmoxClient = Depends(get_proxmox_client)
):
    """Convert a VM to a container (asynchronous operation)"""
    try:
        # Check prerequisites first
        converter = VMConverterAgent(proxmox_client)
        prereq_ok, prereq_msg = converter.check_prerequisites()
        
        if not prereq_ok:
            raise HTTPException(status_code=400, detail=prereq_msg)
        
        # Start conversion in background
        def do_conversion():
            converter.convert_vm_to_ct(
                node=request.node,
                vmid=request.vmid,
                new_ctid=request.new_ctid,
                storage=request.storage,
                keep_vm=request.keep_vm
            )
        
        background_tasks.add_task(do_conversion)
        
        return {
            "status": "conversion_started",
            "message": f"Started conversion of VM {request.vmid} to container",
            "node": request.node,
            "vmid": request.vmid
        }
    except Exception as e:
        logger.error(f"Error converting VM {request.vmid} to container: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to convert VM: {str(e)}")

# Backup and restore endpoints
@router.get("/backups/{node}")
async def list_backups(
    node: str,
    storage: Optional[str] = Query(None, description="Optional storage name to filter by"),
    proxmox_client: ProxmoxClient = Depends(get_proxmox_client)
):
    """List available backups on a node"""
    try:
        backup_agent = ProxmoxBackupAgent(proxmox_client)
        backups = backup_agent.list_backups(node=node, storage=storage)
        return {"backups": backups}
    except Exception as e:
        logger.error(f"Error listing backups on node {node}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list backups: {str(e)}")

@router.post("/backups/create", status_code=202)
async def create_backup(
    request: BackupRequest,
    background_tasks: BackgroundTasks,
    proxmox_client: ProxmoxClient = Depends(get_proxmox_client)
):
    """Create a backup of a VM or container (asynchronous operation)"""
    try:
        backup_agent = ProxmoxBackupAgent(proxmox_client)
        
        # Start backup in background
        def do_backup():
            backup_agent.create_backup(
                node=request.node,
                vmid=request.vmid,
                storage=request.storage,
                mode=request.mode,
                compress=request.compress,
                mail=request.mail,
                remove=request.remove
            )
        
        background_tasks.add_task(do_backup)
        
        return {
            "status": "backup_started",
            "message": f"Started backup of VM/CT {request.vmid}",
            "node": request.node,
            "vmid": request.vmid
        }
    except Exception as e:
        logger.error(f"Error creating backup for VM/CT {request.vmid}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create backup: {str(e)}")

@router.post("/backups/restore", status_code=202)
async def restore_backup(
    request: RestoreRequest,
    background_tasks: BackgroundTasks,
    proxmox_client: ProxmoxClient = Depends(get_proxmox_client)
):
    """Restore a backup to a VM or container (asynchronous operation)"""
    try:
        backup_agent = ProxmoxBackupAgent(proxmox_client)
        
        # Start restore in background
        def do_restore():
            backup_agent.restore_backup(
                node=request.node,
                backup_id=request.backup_id,
                target_vmid=request.target_vmid,
                target_storage=request.target_storage,
                restore_type=request.restore_type
            )
        
        background_tasks.add_task(do_restore)
        
        return {
            "status": "restore_started",
            "message": f"Started restore of backup {request.backup_id}",
            "node": request.node,
            "backup_id": request.backup_id
        }
    except Exception as e:
        logger.error(f"Error restoring backup {request.backup_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to restore backup: {str(e)}")

# Monitoring endpoints
@router.get("/monitoring/cluster")
async def get_cluster_monitoring(proxmox_client: ProxmoxClient = Depends(get_proxmox_client)):
    """Get cluster-wide monitoring data"""
    try:
        monitoring_agent = ProxmoxMonitoringAgent(proxmox_client)
        cluster_status = monitoring_agent.get_cluster_status()
        return cluster_status
    except Exception as e:
        logger.error(f"Error getting cluster monitoring data: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get cluster monitoring data: {str(e)}")

@router.get("/monitoring/node/{node}")
async def get_node_monitoring(
    node: str,
    proxmox_client: ProxmoxClient = Depends(get_proxmox_client)
):
    """Get detailed metrics for a specific node"""
    try:
        monitoring_agent = ProxmoxMonitoringAgent(proxmox_client)
        node_metrics = monitoring_agent.get_node_metrics(node=node)
        return node_metrics
    except Exception as e:
        logger.error(f"Error getting node metrics for {node}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get node metrics: {str(e)}")

@router.get("/monitoring/vm/{node}/{vmid}")
async def get_vm_monitoring(
    node: str,
    vmid: int,
    proxmox_client: ProxmoxClient = Depends(get_proxmox_client)
):
    """Get performance metrics for a specific VM"""
    try:
        monitoring_agent = ProxmoxMonitoringAgent(proxmox_client)
        vm_performance = monitoring_agent.get_vm_performance(node=node, vmid=vmid)
        return vm_performance
    except Exception as e:
        logger.error(f"Error getting VM performance for VM {vmid} on node {node}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get VM performance metrics: {str(e)}")

@router.get("/monitoring/container/{node}/{vmid}")
async def get_container_monitoring(
    node: str,
    vmid: int,
    proxmox_client: ProxmoxClient = Depends(get_proxmox_client)
):
    """Get performance metrics for a specific container"""
    try:
        monitoring_agent = ProxmoxMonitoringAgent(proxmox_client)
        container_performance = monitoring_agent.get_container_performance(node=node, vmid=vmid)
        return container_performance
    except Exception as e:
        logger.error(f"Error getting container performance for CT {vmid} on node {node}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get container performance metrics: {str(e)}")

@router.get("/monitoring/tasks")
async def get_tasks_monitoring(
    node: Optional[str] = Query(None, description="Filter by node name"),
    limit: int = Query(10, description="Maximum number of tasks to return"),
    proxmox_client: ProxmoxClient = Depends(get_proxmox_client)
):
    """Monitor recent tasks across the cluster or on a specific node"""
    try:
        monitoring_agent = ProxmoxMonitoringAgent(proxmox_client)
        tasks = monitoring_agent.monitor_tasks(node=node, limit=limit)
        return {"tasks": tasks}
    except Exception as e:
        logger.error(f"Error monitoring tasks: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to monitor tasks: {str(e)}")

app.include_router(router)
