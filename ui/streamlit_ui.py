import streamlit as st
import os
import requests
import json
import uuid
import pandas as pd
from typing import List, Dict, Any, Optional
import sys
import time
import plotly.express as px
import plotly.graph_objects as go
import hashlib
import hmac
import base64

# Add app directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Get environment variables
API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:5000")
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434/v1")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2:latest")
DEFAULT_TEMP = 0.7
DEFAULT_TOP_P = 0.9
DEFAULT_MAX_TOKENS = 1000

# Authentication config - this should be moved to a secure config in production
AUTH_ENABLED = os.environ.get("AUTH_ENABLED", "false").lower() == "true"
AUTH_USERNAME = os.environ.get("AUTH_USERNAME", "admin")
# In production, use a properly hashed password and salt
AUTH_PASSWORD_HASH = os.environ.get("AUTH_PASSWORD_HASH", 
                                    hashlib.sha256("admin".encode()).hexdigest())

# Helper function for password verification
def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against its hash"""
    return hashlib.sha256(password.encode()).hexdigest() == password_hash

# Helper function for error handling
def handle_api_error(func):
    """Decorator for API call error handling"""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except requests.exceptions.ConnectionError:
            st.error("❌ Connection error: Unable to connect to the API server. Please check if the server is running.")
            return None
        except requests.exceptions.Timeout:
            st.error("❌ Request timed out. The server might be busy or unreachable.")
            return None
        except requests.exceptions.RequestException as e:
            st.error(f"❌ Request error: {str(e)}")
            return None
        except Exception as e:
            st.error(f"❌ Unexpected error: {str(e)}")
            return None
    return wrapper

# Initialize session state
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
    
if "messages" not in st.session_state:
    st.session_state.messages = []
    
if "current_tab" not in st.session_state:
    st.session_state.current_tab = "Chat"
    
if "proxmox_connected" not in st.session_state:
    st.session_state.proxmox_connected = False
    
if "theme" not in st.session_state:
    st.session_state.theme = "light"
    
if "show_settings" not in st.session_state:
    st.session_state.show_settings = False
    
if "auto_refresh" not in st.session_state:
    st.session_state.auto_refresh = False
    
if "refresh_interval" not in st.session_state:
    st.session_state.refresh_interval = 60
    
if "authenticated" not in st.session_state:
    st.session_state.authenticated = not AUTH_ENABLED

# API client for Proxmox AI
class ProxmoxAIClient:
    def __init__(self, base_url):
        self.base_url = base_url.rstrip('/')
        
    @handle_api_error
    def check_health(self):
        """Check if the API is healthy"""
        response = requests.get(f"{self.base_url}/health", timeout=5)
        return response.status_code == 200
            
    @handle_api_error
    def chat(self, message, session_id, context=None):
        """Send a chat message to the API"""
        payload = {
            "message": message,
            "session_id": session_id,
            "context": context
        }
        response = requests.post(f"{self.base_url}/chat", json=payload, timeout=10)
        return response.json()
            
    @handle_api_error
    def get_nodes(self):
        """Get all Proxmox nodes"""
        response = requests.get(f"{self.base_url}/nodes", timeout=5)
        return response.json().get("nodes", [])
            
    @handle_api_error
    def get_vms(self, node=None):
        """Get all VMs, optionally filtered by node"""
        url = f"{self.base_url}/vms"
        if node:
            url += f"?node={node}"
            
        response = requests.get(url, timeout=5)
        return response.json().get("vms", [])
            
    @handle_api_error
    def get_containers(self, node=None):
        """Get all containers, optionally filtered by node"""
        url = f"{self.base_url}/containers"
        if node:
            url += f"?node={node}"
            
        response = requests.get(url, timeout=5)
        return response.json().get("containers", [])
            
    @handle_api_error
    def get_storage(self, node=None):
        """Get storage information, optionally filtered by node"""
        url = f"{self.base_url}/storage"
        if node:
            url += f"?node={node}"
            
        response = requests.get(url, timeout=5)
        return response.json().get("storage", [])
    
    @handle_api_error
    def list_backups(self, node, storage=None):
        """List available backups on a node"""
        url = f"{self.base_url}/backups/{node}"
        if storage:
            url += f"?storage={storage}"
            
        response = requests.get(url, timeout=5)
        return response.json().get("backups", [])
    
    @handle_api_error
    def vm_action(self, action, node, vmid):
        """Perform an action on a VM (start, stop, shutdown)"""
        response = requests.post(f"{self.base_url}/vms/{node}/{vmid}/{action}", timeout=10)
        return response.json()
    
    @handle_api_error
    def container_action(self, action, node, vmid):
        """Perform an action on a container (start, stop, shutdown)"""
        response = requests.post(f"{self.base_url}/containers/{node}/{vmid}/{action}", timeout=10)
        return response.json()

    @handle_api_error
    def get_cluster_monitoring(self):
        """Get cluster-wide monitoring data"""
        response = requests.get(f"{self.base_url}/monitoring/cluster", timeout=5)
        return response.json()
            
    @handle_api_error
    def get_node_monitoring(self, node):
        """Get monitoring data for a specific node"""
        response = requests.get(f"{self.base_url}/monitoring/node/{node}", timeout=5)
        return response.json()
            
    @handle_api_error
    def get_vm_monitoring(self, node, vmid):
        """Get monitoring data for a specific VM"""
        response = requests.get(f"{self.base_url}/monitoring/vm/{node}/{vmid}", timeout=5)
        return response.json()
            
    @handle_api_error
    def get_container_monitoring(self, node, vmid):
        """Get monitoring data for a specific container"""
        response = requests.get(f"{self.base_url}/monitoring/container/{node}/{vmid}", timeout=5)
        return response.json()
            
    @handle_api_error
    def list_convertible_vms(self, node):
        """List VMs that can be converted to containers"""
        response = requests.get(f"{self.base_url}/vm-converter/list-convertible/{node}", timeout=5)
        return response.json().get("convertible_vms", [])
            
    @handle_api_error
    def convert_vm_to_container(self, node, vmid, target_node=None, options=None):
        """Convert a VM to a container"""
        payload = {
            "vmid": vmid,
            "target_node": target_node or node,
            "options": options or {}
        }
        response = requests.post(f"{self.base_url}/vm-converter/convert/{node}", json=payload, timeout=30)
        return response.json()
            
    @handle_api_error
    def create_backup(self, node, vmid, storage=None, backup_mode="snapshot", compress=True):
        """Create a backup of a VM or container"""
        payload = {
            "storage": storage,
            "backup_mode": backup_mode,
            "compress": compress
        }
        response = requests.post(f"{self.base_url}/backups/{node}/{vmid}/create", json=payload, timeout=30)
        return response.json()
            
    @handle_api_error
    def restore_backup(self, node, vmid, backup_id, target_node=None, target_storage=None):
        """Restore a backup to a VM or container"""
        payload = {
            "backup_id": backup_id,
            "target_node": target_node or node,
            "target_storage": target_storage
        }
        response = requests.post(f"{self.base_url}/backups/{node}/{vmid}/restore", json=payload, timeout=30)
        return response.json()
            
    @handle_api_error
    def get_tasks(self, node=None, limit=10):
        """Get recent tasks from Proxmox"""
        url = f"{self.base_url}/tasks"
        if node:
            url += f"?node={node}"
        if limit:
            url += f"{'&' if node else '?'}limit={limit}"
            
        response = requests.get(url, timeout=5)
        return response.json().get("tasks", [])

# Define a basic OpenAIClient for Ollama
class OpenAIClient:
    def __init__(self, base_url):
        self.base_url = base_url
        
    @handle_api_error
    def chat_completions_create(self, model, messages, temperature=0.7, top_p=0.9, max_tokens=1000):
        """Call Ollama API to generate chat completions"""
        url = f"{self.base_url}/chat/completions"
        
        # Format messages for Ollama
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "top_p": top_p
        }
        
        if max_tokens:
            payload["max_tokens"] = max_tokens
            
        response = requests.post(url, json=payload)
        return response.json()

# Initialize clients
if "proxmox_ai_client" not in st.session_state:
    st.session_state.proxmox_ai_client = ProxmoxAIClient(API_BASE_URL)
    
if "ollama_client" not in st.session_state:
    st.session_state.ollama_client = OpenAIClient(OLLAMA_BASE_URL)

# Page configuration
st.set_page_config(
    page_title="Proxmox AI Manager",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Login screen if authentication is enabled
if AUTH_ENABLED and not st.session_state.authenticated:
    st.markdown("""
    <style>
    .login-container {
        max-width: 400px;
        margin: 0 auto;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.title("🔒 Proxmox AI Login")
    
    with st.container():
        st.markdown('<div class="login-container">', unsafe_allow_html=True)
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        login_button = st.button("Login")
        
        if login_button:
            if username == AUTH_USERNAME and verify_password(password, AUTH_PASSWORD_HASH):
                st.session_state.authenticated = True
                st.experimental_rerun()
            else:
                st.error("❌ Invalid username or password")
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Stop the rest of the app from loading
    st.stop()

# Apply custom theme based on user preference
if st.session_state.theme == "dark":
    st.markdown("""
    <style>
    :root {
        --primary-color: #7289da;
        --background-color: #2c2f33;
        --secondary-background-color: #23272a;
        --text-color: #ffffff;
        --font: 'Source Sans Pro', sans-serif;
    }
    .stApp {
        background-color: var(--background-color);
        color: var(--text-color);
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 4px 4px 0px 0px;
        padding: 10px 16px;
        background-color: var(--secondary-background-color);
    }
    .stTabs [aria-selected="true"] {
        background-color: var(--primary-color);
        color: white;
    }
    </style>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
    <style>
    :root {
        --primary-color: #4CAF50;
        --font: 'Source Sans Pro', sans-serif;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 4px 4px 0px 0px;
        padding: 10px 16px;
    }
    .stTabs [aria-selected="true"] {
        background-color: var(--primary-color);
        color: white;
    }
    </style>
    """, unsafe_allow_html=True)

# Sidebar for settings and controls
with st.sidebar:
    st.title("🚀 Proxmox AI")
    
    # Status indicator
    if st.session_state.proxmox_connected:
        st.success("✅ Connected to Proxmox API")
    else:
        st.error("❌ Not connected to Proxmox API")
    
    st.divider()
    
    # Display connection form
    with st.expander("Connection Settings", expanded=not st.session_state.proxmox_connected):
        host = st.text_input("Proxmox Host", placeholder="proxmox.example.com")
        port = st.text_input("Proxmox Port", value="8006")
        token_id = st.text_input("Token ID", placeholder="root@pam!tokenname")
        token_secret = st.text_input("Token Secret", type="password")
        verify_ssl = st.checkbox("Verify SSL", value=False)
        
        if st.button("Connect to Proxmox"):
            try:
                # Here you would implement the actual connection logic
                # For now, we'll just set the connection state
                st.session_state.proxmox_connected = True
                st.session_state.proxmox_host = host
                st.session_state.proxmox_port = port
                st.experimental_rerun()
            except Exception as e:
                st.error(f"Failed to connect: {str(e)}")
    
    # UI Settings
    with st.expander("UI Settings", expanded=False):
        theme = st.selectbox("Theme", ["light", "dark"], 
                            index=0 if st.session_state.theme == "light" else 1)
        
        if theme != st.session_state.theme:
            st.session_state.theme = theme
            st.experimental_rerun()
        
        auto_refresh = st.checkbox("Auto Refresh Data", value=st.session_state.auto_refresh)
        
        if auto_refresh:
            refresh_interval = st.slider("Refresh Interval (seconds)", 
                                     min_value=10, max_value=300, 
                                     value=st.session_state.refresh_interval)
            st.session_state.refresh_interval = refresh_interval
        
        st.session_state.auto_refresh = auto_refresh
    
    # LLM Settings
    with st.expander("LLM Settings", expanded=False):
        st.selectbox("Model", [OLLAMA_MODEL, "llama3:latest", "mistral:latest"], index=0)
        st.slider("Temperature", min_value=0.0, max_value=1.0, value=DEFAULT_TEMP, step=0.1)
        st.slider("Top P", min_value=0.0, max_value=1.0, value=DEFAULT_TOP_P, step=0.1)
        st.slider("Max Tokens", min_value=100, max_value=4000, value=DEFAULT_MAX_TOKENS, step=100)
    
    # Add helpful information 
    st.divider()
    st.info("Proxmox AI combines natural language processing with Proxmox management capabilities.")
    
    # Developer panel
    with st.expander("Developer Tools", expanded=False):
        if st.button("Clear Session"):
            for key in list(st.session_state.keys()):
                if key not in ["theme", "show_settings"]:
                    del st.session_state[key]
            st.session_state.messages = []
            st.session_state.session_id = str(uuid.uuid4())
            st.experimental_rerun()
        
        st.checkbox("Enable Logging", value=False)
        
        if st.checkbox("Show Raw API Responses"):
            st.session_state.show_raw_responses = True
        else:
            st.session_state.show_raw_responses = False

# App title and description
st.title("Proxmox AI Assistant ")
st.markdown("""
Welcome to the Proxmox Server Whisperer! I can help you manage your Proxmox Virtual Environment (Proxmox VE) servers. 
You provide guidance on best practices, troubleshooting, and configuration for Proxmox VE installations.
Respond in a helpful and knowledgeable manner, focusing on Proxmox-related topics.

**Note:** This is running in standalone mode without direct Proxmox connection.
""")

# Sidebar for settings
st.sidebar.title("Settings")
model_mode = st.sidebar.selectbox(
    "Mode",
    ["Server Whisperer", "Solution Comparison", "Mystical Web Search", "Proxmox Guru"],
    index=0
)

temperature = st.sidebar.slider(
    "Temperature",
    min_value=0.0,
    max_value=1.0,
    value=DEFAULT_TEMP,
    step=0.1,
    help="Higher values make output more random, lower values more deterministic"
)

top_p = st.sidebar.slider(
    "Top P",
    min_value=0.0,
    max_value=1.0,
    value=DEFAULT_TOP_P,
    step=0.1,
    help="Controls diversity via nucleus sampling"
)

max_tokens = st.sidebar.slider(
    "Max Tokens",
    min_value=100,
    max_value=2000,
    value=DEFAULT_MAX_TOKENS,
    step=100,
    help="Maximum number of tokens to generate"
)

# Clear chat button
if st.sidebar.button("Clear Chat"):
    st.session_state.messages = []
    st.rerun()

# System status
st.sidebar.divider()
st.sidebar.subheader("System Status")

# Check Ollama status
try:
    response = requests.get(f"{OLLAMA_BASE_URL}/models", timeout=5)
    if response.status_code == 200:
        st.sidebar.success("")
        models = response.json().get("models", [])
        model_names = [model.get("name") for model in models] if models else []
        if model_names:
            st.sidebar.text(f"Available models: {', '.join(model_names)}")
        else:
            st.sidebar.text(f"Using model: {OLLAMA_MODEL}")
    else:
        st.sidebar.error("")
except Exception as e:
    st.sidebar.error(f" ({str(e)})")

# Display notice about Proxmox connection
st.sidebar.error(" Proxmox: Not connected (Running in standalone mode)")

# Display help information
st.sidebar.divider()
st.sidebar.info("""
**Standalone Mode**
Running without Proxmox connection.
The AI can still provide general knowledge about Proxmox.
""")

# Check API connection
api_connected = st.session_state.proxmox_ai_client.check_health()
if api_connected:
    st.session_state.proxmox_connected = True

# Main UI with tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "💬 Chat", 
    "🖥️ VMs & Containers", 
    "🔄 Converter", 
    "💾 Backups", 
    "📊 Monitoring"
])

# Tab 1: Chat Interface
with tab1:
    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Add custom system message for Proxmox AI
    SYSTEM_MESSAGE = """You are the Proxmox Server Whisperer, an AI assistant that helps users manage their Proxmox Virtual Environment (Proxmox VE) servers. 
    You provide guidance on best practices, troubleshooting, and configuration for Proxmox VE installations.
    Respond in a helpful and knowledgeable manner, focusing on Proxmox-related topics."""

    # User input
    if prompt := st.chat_input("Ask me about your Proxmox environment..."):
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Generate and display response
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            full_response = ""
            
            try:
                if api_connected:
                    # Use the API for chat if connected
                    with st.spinner("Thinking..."):
                        # Extract context from previous messages (excluding system messages)
                        context = [
                            {"role": msg["role"], "content": msg["content"]} 
                            for msg in st.session_state.messages 
                            if msg["role"] != "system"
                        ]
                        
                        # Make API call
                        result = st.session_state.proxmox_ai_client.chat(
                            message=prompt,
                            session_id=st.session_state.session_id,
                            context=context
                        )
                        
                        full_response = result.get("response", "Error generating response")
                else:
                    # Process the prompt locally using Ollama
                    if st.session_state.ollama_client:
                        # Prepare the messages with system message
                        history = [{"role": "system", "content": SYSTEM_MESSAGE}]
                        # Add the rest of the conversation history
                        for m in st.session_state.messages:
                            if m["role"] != "system":
                                history.append({"role": m["role"], "content": m["content"]})
                        
                        # Prepare parameters
                        params = {
                            "model": OLLAMA_MODEL,
                            "messages": history,
                            "temperature": temperature,
                            "top_p": top_p,
                            "max_tokens": max_tokens
                        }
                        
                        # Call the API
                        with st.spinner("Thinking..."):
                            response = st.session_state.ollama_client.chat_completions_create(**params)
                            
                            if response and "choices" in response:
                                full_response = response["choices"][0]["message"]["content"]
                            else:
                                full_response = "I'm having trouble generating a response. Please check if Ollama is running with the correct model."
                    else:
                        full_response = "I'm not properly connected to Ollama. Please check that Ollama is running and the URL is correct."
                    
                # Display the full response
                message_placeholder.markdown(full_response)
                
                # Add assistant response to chat history
                st.session_state.messages.append({"role": "assistant", "content": full_response})
                
            except Exception as e:
                error_message = f"Error generating response: {str(e)}"
                message_placeholder.error(error_message)
                st.session_state.messages.append({"role": "assistant", "content": error_message})

# Tab 2: VMs & Containers
with tab2:
    st.header("Virtual Machines & Containers")
    
    if not st.session_state.proxmox_connected:
        st.warning("Not connected to Proxmox API. This tab requires a connection to a Proxmox environment.")
    else:
        # Get nodes
        nodes = st.session_state.proxmox_ai_client.get_nodes()
        
        if not nodes:
            st.warning("No Proxmox nodes found. Check your connection settings.")
        else:
            # Node selection
            selected_node = st.selectbox("Select Node", [node["node"] for node in nodes])
            
            # Create tabs for VMs and Containers
            vm_tab, ct_tab = st.tabs(["Virtual Machines", "Containers"])
            
            # VMs tab
            with vm_tab:
                st.subheader("Virtual Machines")
                vms = st.session_state.proxmox_ai_client.get_vms(node=selected_node)
                
                if not vms:
                    st.info(f"No virtual machines found on node {selected_node}")
                else:
                    # Create a dataframe for better display
                    vm_data = []
                    for vm in vms:
                        vm_data.append({
                            "ID": vm.get("vmid"),
                            "Name": vm.get("name"),
                            "Status": vm.get("status"),
                            "CPU": f"{vm.get('cpu', 0)}",
                            "Memory": f"{vm.get('mem', 0) / 1024:.1f} GB",
                            "Disk": f"{vm.get('disk', 0) / (1024**3):.1f} GB"
                        })
                    
                    vm_df = pd.DataFrame(vm_data)
                    st.dataframe(vm_df, use_container_width=True)
                    
                    # Actions for VMs
                    st.subheader("VM Actions")
                    cols = st.columns(3)
                    
                    with cols[0]:
                        vm_id = st.selectbox("Select VM ID", [vm["ID"] for vm in vm_data])
                    
                    with cols[1]:
                        action = st.selectbox("Action", ["start", "stop", "shutdown"])
                    
                    with cols[2]:
                        if st.button("Execute VM Action"):
                            with st.spinner(f"Executing {action} on VM {vm_id}..."):
                                result = st.session_state.proxmox_ai_client.vm_action(action, selected_node, vm_id)
                                if result.get("status") == "success":
                                    st.success(f"Successfully {action}ed VM {vm_id}")
                                else:
                                    st.error(f"Failed to {action} VM {vm_id}: {result.get('message', 'Unknown error')}")
            
            # Containers tab
            with ct_tab:
                st.subheader("Containers")
                containers = st.session_state.proxmox_ai_client.get_containers(node=selected_node)
                
                if not containers:
                    st.info(f"No containers found on node {selected_node}")
                else:
                    # Create a dataframe for better display
                    ct_data = []
                    for ct in containers:
                        ct_data.append({
                            "ID": ct.get("vmid"),
                            "Name": ct.get("name"),
                            "Status": ct.get("status"),
                            "CPU": f"{ct.get('cpu', 0)}",
                            "Memory": f"{ct.get('mem', 0) / 1024:.1f} GB",
                            "Disk": f"{ct.get('disk', 0) / (1024**3):.1f} GB"
                        })
                    
                    ct_df = pd.DataFrame(ct_data)
                    st.dataframe(ct_df, use_container_width=True)
                    
                    # Actions for containers
                    st.subheader("Container Actions")
                    cols = st.columns(3)
                    
                    with cols[0]:
                        ct_id = st.selectbox("Select Container ID", [ct["ID"] for ct in ct_data])
                    
                    with cols[1]:
                        ct_action = st.selectbox("Container Action", ["start", "stop", "shutdown"])
                    
                    with cols[2]:
                        if st.button("Execute Container Action"):
                            with st.spinner(f"Executing {ct_action} on Container {ct_id}..."):
                                result = st.session_state.proxmox_ai_client.container_action(ct_action, selected_node, ct_id)
                                if result.get("status") == "success":
                                    st.success(f"Successfully {ct_action}ed Container {ct_id}")
                                else:
                                    st.error(f"Failed to {ct_action} Container {ct_id}: {result.get('message', 'Unknown error')}")

# Tab 3: VM to Container Converter
with tab3:
    st.header("VM to Container Converter")
    
    if not st.session_state.proxmox_connected:
        st.warning("Not connected to Proxmox API. This tab requires a connection to a Proxmox environment.")
    else:
        # Get nodes
        nodes = st.session_state.proxmox_ai_client.get_nodes()
        
        if not nodes:
            st.warning("No Proxmox nodes found. Check your connection settings.")
        else:
            # Node selection
            selected_node = st.selectbox("Select Node for Conversion", [node["node"] for node in nodes], key="converter_node")
            
            # Get convertible VMs
            convertible_vms = st.session_state.proxmox_ai_client.list_convertible_vms(selected_node)
            
            if not convertible_vms:
                st.info(f"No convertible VMs found on node {selected_node}")
            else:
                st.subheader("Convertible VMs")
                
                # Create a dataframe for better display
                vm_data = []
                for vm in convertible_vms:
                    vm_data.append({
                        "ID": vm.get("vmid"),
                        "Name": vm.get("name"),
                        "OS Type": vm.get("os_type", "Unknown"),
                        "Disk Size": f"{vm.get('disk', 0) / (1024**3):.1f} GB"
                    })
                
                vm_df = pd.DataFrame(vm_data)
                st.dataframe(vm_df, use_container_width=True)
                
                # Conversion form
                st.subheader("Convert VM to Container")
                
                with st.form("vm_conversion_form"):
                    vm_id = st.selectbox("Select VM to Convert", [vm["ID"] for vm in vm_data])
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        new_id = st.number_input("New Container ID (optional)", min_value=100, max_value=999999, value=0, step=1)
                        if new_id == 0:
                            new_id = None
                        
                        storage = st.text_input("Storage for new Container", value="local")
                    
                    with col2:
                        keep_vm = st.checkbox("Keep original VM", value=True)
                    
                    submit = st.form_submit_button("Start Conversion")
                    
                    if submit:
                        st.info("This is a conversion simulation. In a real environment, this would start a background conversion task.")
                        st.success(f"""
                        Simulated conversion started with parameters:
                        - Node: {selected_node}
                        - VM ID: {vm_id}
                        - New Container ID: {new_id or 'Auto-assigned'}
                        - Storage: {storage}
                        - Keep original VM: {'Yes' if keep_vm else 'No'}
                        """)

# Tab 4: Backups
with tab4:
    st.header("Backups & Restore")
    
    if not st.session_state.proxmox_connected:
        st.warning("Not connected to Proxmox API. This tab requires a connection to a Proxmox environment.")
    else:
        # Create tabs for backup and restore
        backup_tab, restore_tab = st.tabs(["Create Backup", "Restore Backup"])
        
        # Backup tab
        with backup_tab:
            st.subheader("Create New Backup")
            
            # Get nodes
            nodes = st.session_state.proxmox_ai_client.get_nodes()
            
            if not nodes:
                st.warning("No Proxmox nodes found. Check your connection settings.")
            else:
                # Node selection
                selected_node = st.selectbox("Select Node", [node["node"] for node in nodes], key="backup_node")
                
                # Get VMs and containers
                vms = st.session_state.proxmox_ai_client.get_vms(node=selected_node)
                containers = st.session_state.proxmox_ai_client.get_containers(node=selected_node)
                
                # Combine them for selection
                vm_options = [(vm.get("vmid"), f"VM: {vm.get('name')} ({vm.get('vmid')})") for vm in vms]
                ct_options = [(ct.get("vmid"), f"CT: {ct.get('name')} ({ct.get('vmid')})") for ct in containers]
                options = vm_options + ct_options
                
                if not options:
                    st.info(f"No VMs or containers found on node {selected_node}")
                else:
                    with st.form("backup_form"):
                        vmid = st.selectbox("Select VM or Container", [opt[1] for opt in options])
                        vmid = int(options[[opt[1] for opt in options].index(vmid)][0])
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            storage = st.text_input("Storage for backup", value="local")
                            mode = st.selectbox("Backup mode", ["snapshot", "suspend", "stop"])
                        
                        with col2:
                            compress = st.checkbox("Compress backup", value=True)
                            mail = st.text_input("Email notification (optional)")
                            remove = st.number_input("Number of backups to keep (0 = keep all)", min_value=0, value=0)
                        
                        submit = st.form_submit_button("Create Backup")
                        
                        if submit:
                            st.info("This is a backup simulation. In a real environment, this would start a background backup task.")
                            st.success(f"""
                            Simulated backup started with parameters:
                            - Node: {selected_node}
                            - VM/CT ID: {vmid}
                            - Storage: {storage}
                            - Mode: {mode}
                            - Compress: {'Yes' if compress else 'No'}
                            - Email: {mail or 'None'}
                            - Keep: {"All backups" if remove == 0 else f"{remove} backups"}
                            """)
        
        # Restore tab
        with restore_tab:
            st.subheader("Restore from Backup")
            
            # Get nodes
            nodes = st.session_state.proxmox_ai_client.get_nodes()
            
            if not nodes:
                st.warning("No Proxmox nodes found. Check your connection settings.")
            else:
                # Node selection
                selected_node = st.selectbox("Select Node", [node["node"] for node in nodes], key="restore_node")
                
                # Get backups
                backups = st.session_state.proxmox_ai_client.list_backups(selected_node)
                
                if not backups:
                    st.info(f"No backups found on node {selected_node}")
                else:
                    with st.form("restore_form"):
                        backup_options = [f"{b.get('volid')} ({b.get('vmid')} - {b.get('ctime')})" for b in backups]
                        selected_backup = st.selectbox("Select Backup", backup_options)
                        backup_volid = backups[backup_options.index(selected_backup)].get('volid')
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            target_vmid = st.number_input("Target VM/CT ID (optional)", min_value=100, max_value=999999, value=0, step=1)
                            if target_vmid == 0:
                                target_vmid = None
                        
                        with col2:
                            target_storage = st.text_input("Target storage (optional)")
                            restore_type = st.selectbox("Restore type", ["fast", "full"])
                        
                        submit = st.form_submit_button("Restore Backup")
                        
                        if submit:
                            st.info("This is a restore simulation. In a real environment, this would start a background restore task.")
                            st.success(f"""
                            Simulated restore started with parameters:
                            - Node: {selected_node}
                            - Backup: {backup_volid}
                            - Target VM/CT ID: {target_vmid or 'Same as original'}
                            - Target Storage: {target_storage or 'Same as original'}
                            - Restore Type: {restore_type}
                            """)

# Tab 5: Monitoring
with tab5:
    st.header("Proxmox Monitoring")
    
    if not st.session_state.proxmox_connected:
        st.warning("Not connected to Proxmox API. This tab requires a connection to a Proxmox environment.")
    else:
        # Create tabs for different monitoring views
        cluster_tab, node_tab, vm_tab, ct_tab, tasks_tab = st.tabs([
            "Cluster Overview", 
            "Node Metrics", 
            "VM Performance", 
            "Container Performance",
            "Recent Tasks"
        ])
        
        # Cluster overview
        with cluster_tab:
            st.subheader("Cluster Status")
            
            # Get cluster monitoring data
            cluster_data = st.session_state.proxmox_ai_client.get_cluster_monitoring()
            
            if not cluster_data:
                st.warning("No cluster data available. Ensure your Proxmox API is accessible.")
            else:
                # Display cluster metrics
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    # CPU usage gauge
                    cpu_usage = cluster_data.get("cpu_usage", 0)
                    fig = go.Figure(go.Indicator(
                        mode="gauge+number",
                        value=cpu_usage,
                        title={"text": "CPU Usage (%)"},
                        gauge={
                            "axis": {"range": [0, 100]},
                            "bar": {"color": "darkblue"},
                            "steps": [
                                {"range": [0, 50], "color": "lightgreen"},
                                {"range": [50, 80], "color": "orange"},
                                {"range": [80, 100], "color": "red"}
                            ],
                            "threshold": {
                                "line": {"color": "red", "width": 4},
                                "thickness": 0.75,
                                "value": 90
                            }
                        }
                    ))
                    fig.update_layout(height=300, margin=dict(l=20, r=20, t=50, b=20))
                    st.plotly_chart(fig, use_container_width=True)
                
                with col2:
                    # Memory usage gauge
                    memory_usage = cluster_data.get("memory_usage", 0)
                    fig = go.Figure(go.Indicator(
                        mode="gauge+number",
                        value=memory_usage,
                        title={"text": "Memory Usage (%)"},
                        gauge={
                            "axis": {"range": [0, 100]},
                            "bar": {"color": "darkblue"},
                            "steps": [
                                {"range": [0, 50], "color": "lightgreen"},
                                {"range": [50, 80], "color": "orange"},
                                {"range": [80, 100], "color": "red"}
                            ],
                            "threshold": {
                                "line": {"color": "red", "width": 4},
                                "thickness": 0.75,
                                "value": 90
                            }
                        }
                    ))
                    fig.update_layout(height=300, margin=dict(l=20, r=20, t=50, b=20))
                    st.plotly_chart(fig, use_container_width=True)
                
                with col3:
                    # Storage usage gauge
                    storage_usage = cluster_data.get("storage_usage", 0)
                    fig = go.Figure(go.Indicator(
                        mode="gauge+number",
                        value=storage_usage,
                        title={"text": "Storage Usage (%)"},
                        gauge={
                            "axis": {"range": [0, 100]},
                            "bar": {"color": "darkblue"},
                            "steps": [
                                {"range": [0, 50], "color": "lightgreen"},
                                {"range": [50, 80], "color": "orange"},
                                {"range": [80, 100], "color": "red"}
                            ],
                            "threshold": {
                                "line": {"color": "red", "width": 4},
                                "thickness": 0.75,
                                "value": 90
                            }
                        }
                    ))
                    fig.update_layout(height=300, margin=dict(l=20, r=20, t=50, b=20))
                    st.plotly_chart(fig, use_container_width=True)
                
                # VM and Container Counts
                st.subheader("Resource Distribution")
                
                # Create distribution data
                resources = [
                    {"category": "VMs", "count": cluster_data.get("vm_count", 0)},
                    {"category": "Containers", "count": cluster_data.get("container_count", 0)},
                    {"category": "Nodes", "count": cluster_data.get("node_count", 0)}
                ]
                
                df = pd.DataFrame(resources)
                
                # Plot a bar chart
                fig = px.bar(
                    df, 
                    x="category", 
                    y="count", 
                    color="category",
                    labels={"count": "Count", "category": "Resource Type"},
                    title="Resource Distribution"
                )
                fig.update_layout(height=400, width=800)
                st.plotly_chart(fig, use_container_width=True)
                
                # Show cluster nodes table
                st.subheader("Cluster Nodes")
                if "nodes" in cluster_data:
                    nodes_df = pd.DataFrame(cluster_data["nodes"])
                    if not nodes_df.empty:
                        st.dataframe(nodes_df, use_container_width=True)
                    else:
                        st.info("No node data available.")
                else:
                    st.info("No node data available in cluster metrics.")
                
                # Auto-refresh if enabled
                if st.session_state.auto_refresh:
                    time.sleep(0.1)  # Small delay to prevent UI lag
                    st.experimental_rerun()
                    
        # Node metrics
        with node_tab:
            st.subheader("Node Performance Metrics")
            
            # Get nodes for selection
            nodes = st.session_state.proxmox_ai_client.get_nodes()
            
            if not nodes:
                st.warning("No nodes found. Check your connection to the Proxmox API.")
            else:
                # Node selector
                node_names = [node.get("node") for node in nodes]
                selected_node = st.selectbox(
                    "Select Node", 
                    options=node_names,
                    index=0
                )
                
                if selected_node:
                    # Get monitoring data for selected node
                    node_data = st.session_state.proxmox_ai_client.get_node_monitoring(selected_node)
                    
                    if not node_data:
                        st.warning(f"No monitoring data available for node {selected_node}.")
                    else:
                        # Display node metrics
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            # CPU Usage over time
                            if "cpu_history" in node_data and node_data["cpu_history"]:
                                cpu_df = pd.DataFrame(node_data["cpu_history"])
                                fig = px.line(
                                    cpu_df, 
                                    x="time", 
                                    y="usage",
                                    title=f"CPU Usage History - {selected_node}",
                                    labels={"usage": "CPU Usage (%)", "time": "Time"}
                                )
                                fig.update_layout(height=300)
                                st.plotly_chart(fig, use_container_width=True)
                            else:
                                st.info("No CPU history data available.")
                        
                        with col2:
                            # Memory Usage over time
                            if "memory_history" in node_data and node_data["memory_history"]:
                                mem_df = pd.DataFrame(node_data["memory_history"])
                                fig = px.line(
                                    mem_df, 
                                    x="time", 
                                    y="usage",
                                    title=f"Memory Usage History - {selected_node}",
                                    labels={"usage": "Memory Usage (%)", "time": "Time"}
                                )
                                fig.update_layout(height=300)
                                st.plotly_chart(fig, use_container_width=True)
                            else:
                                st.info("No memory history data available.")
                        
                        # Network I/O
                        if "network_io" in node_data and node_data["network_io"]:
                            st.subheader("Network I/O")
                            net_df = pd.DataFrame(node_data["network_io"])
                            
                            # Create a grouped bar chart for network I/O
                            fig = px.bar(
                                net_df,
                                x="interface",
                                y=["in", "out"],
                                title="Network Traffic by Interface",
                                barmode="group",
                                labels={
                                    "interface": "Network Interface",
                                    "value": "Traffic (MB/s)",
                                    "variable": "Direction"
                                }
                            )
                            fig.update_layout(height=400)
                            st.plotly_chart(fig, use_container_width=True)
                        else:
                            st.info("No network I/O data available.")
                        
                        # Disk I/O
                        if "disk_io" in node_data and node_data["disk_io"]:
                            st.subheader("Disk I/O")
                            disk_df = pd.DataFrame(node_data["disk_io"])
                            
                            # Create a grouped bar chart for disk I/O
                            fig = px.bar(
                                disk_df,
                                x="device",
                                y=["read", "write"],
                                title="Disk I/O by Device",
                                barmode="group",
                                labels={
                                    "device": "Disk Device",
                                    "value": "I/O (MB/s)",
                                    "variable": "Operation"
                                }
                            )
                            fig.update_layout(height=400)
                            st.plotly_chart(fig, use_container_width=True)
                        else:
                            st.info("No disk I/O data available.")
                        
                        # Auto-refresh if enabled
                        if st.session_state.auto_refresh:
                            time.sleep(0.1)  # Small delay to prevent UI lag
                            st.experimental_rerun()
        
        # VM performance
        with vm_tab:
            st.subheader("Virtual Machine Performance")
            
            # Get nodes
            nodes = st.session_state.proxmox_ai_client.get_nodes()
            
            if not nodes:
                st.warning("No nodes found. Check your connection to the Proxmox API.")
            else:
                # Node selection
                col1, col2 = st.columns(2)
                
                with col1:
                    selected_node = st.selectbox("Select Node", [node["node"] for node in nodes], key="vm_monitoring_node")
                
                # Get VMs for the selected node
                vms = st.session_state.proxmox_ai_client.get_vms(node=selected_node)
                
                if not vms:
                    st.info(f"No VMs found on node {selected_node}")
                else:
                    with col2:
                        vm_options = [f"{vm.get('name')} ({vm.get('vmid')})" for vm in vms]
                        selected_vm = st.selectbox("Select VM", vm_options)
                        vmid = vms[vm_options.index(selected_vm)].get('vmid')
                    
                    # Get VM performance metrics
                    vm_performance = st.session_state.proxmox_ai_client.get_vm_monitoring(selected_node, vmid)
                    
                    if not vm_performance:
                        st.info(f"No performance data available for VM {vmid}")
                    else:
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            st.metric("CPU Usage", f"{vm_performance.get('cpu', 0):.1f}%")
                            st.metric("Memory Used", f"{vm_performance.get('mem', 0) / 1024:.1f} MB")
                        
                        with col2:
                            st.metric("Disk Read", f"{vm_performance.get('disk_read', 0) / 1024:.1f} KB/s")
                            st.metric("Disk Write", f"{vm_performance.get('disk_write', 0) / 1024:.1f} KB/s")
                        
                        with col3:
                            st.metric("Net In", f"{vm_performance.get('netin', 0) / 1024:.1f} KB/s")
                            st.metric("Net Out", f"{vm_performance.get('netout', 0) / 1024:.1f} KB/s")
        
        # Container performance
        with ct_tab:
            st.subheader("Container Performance")
            
            # Get nodes
            nodes = st.session_state.proxmox_ai_client.get_nodes()
            
            if not nodes:
                st.warning("No nodes found. Check your connection to the Proxmox API.")
            else:
                # Node selection
                col1, col2 = st.columns(2)
                
                with col1:
                    selected_node = st.selectbox("Select Node", [node["node"] for node in nodes], key="ct_monitoring_node")
                
                # Get containers for the selected node
                containers = st.session_state.proxmox_ai_client.get_containers(node=selected_node)
                
                if not containers:
                    st.info(f"No containers found on node {selected_node}")
                else:
                    with col2:
                        ct_options = [f"{ct.get('name')} ({ct.get('vmid')})" for ct in containers]
                        selected_ct = st.selectbox("Select Container", ct_options)
                        ct_id = containers[ct_options.index(selected_ct)].get('vmid')
                    
                    # Get container performance metrics
                    ct_performance = st.session_state.proxmox_ai_client.get_container_monitoring(selected_node, ct_id)
                    
                    if not ct_performance:
                        st.info(f"No performance data available for container {ct_id}")
                    else:
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            st.metric("CPU Usage", f"{ct_performance.get('cpu', 0):.1f}%")
                            st.metric("Memory Used", f"{ct_performance.get('mem', 0) / 1024:.1f} MB")
                        
                        with col2:
                            st.metric("Disk Read", f"{ct_performance.get('disk_read', 0) / 1024:.1f} KB/s")
                            st.metric("Disk Write", f"{ct_performance.get('disk_write', 0) / 1024:.1f} KB/s")
                        
                        with col3:
                            st.metric("Net In", f"{ct_performance.get('netin', 0) / 1024:.1f} KB/s")
                            st.metric("Net Out", f"{ct_performance.get('netout', 0) / 1024:.1f} KB/s")
        
        # Recent tasks
        with tasks_tab:
            st.subheader("Recent Tasks")
            
            col1, col2 = st.columns(2)
            
            with col1:
                selected_node = st.selectbox("Filter by Node (optional)", ["All Nodes"] + [node["node"] for node in nodes], key="tasks_node")
                node_filter = None if selected_node == "All Nodes" else selected_node
            
            with col2:
                limit = st.slider("Number of tasks", min_value=5, max_value=50, value=10)
            
            if st.button("Refresh Tasks"):
                st.session_state.refresh_tasks = True
            
            # Display tasks
            st.dataframe(pd.DataFrame([
                {"ID": "UPID:pve:00001234:123AA:123:task:12345",
                 "Type": "task",
                 "User": "root@pam",
                 "Status": "running",
                 "Node": "pve",
                 "Started": "2023-03-17 12:34:56",
                 "Duration": "00:05:22"}
            ]), use_container_width=True)
            
            st.info("This is a simulation with sample data. In a connected environment, real task data would be displayed.")

# Add some helpful information at the bottom
st.divider()
st.caption("Proxmox AI Assistant powered by Ollama LLM and Streamlit")
