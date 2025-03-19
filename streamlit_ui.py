import streamlit as st
import os
import requests
import json
from typing import List, Dict, Any, Optional
import sys

# Add app directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Get environment variables
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434/v1")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2:latest")
DEFAULT_TEMP = 0.7
DEFAULT_TOP_P = 0.9
DEFAULT_MAX_TOKENS = 1000

# Initialize session state for messages
if "messages" not in st.session_state:
    st.session_state.messages = []

# Define a basic OpenAIClient for Ollama
class OpenAIClient:
    def __init__(self, base_url):
        self.base_url = base_url
        
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
            
        try:
            response = requests.post(url, json=payload)
            return response.json()
        except Exception as e:
            st.error(f"Error calling Ollama API: {str(e)}")
            return None

# Initialize OpenAIClient
if "ollama_client" not in st.session_state:
    st.session_state.ollama_client = OpenAIClient(OLLAMA_BASE_URL)

# App title and description
st.title("Proxmox AI Assistant 🧙‍♂️")
st.markdown("""
Welcome to the Proxmox Server Whisperer! I can help you manage your Proxmox VE environment, 
troubleshoot issues, and provide guidance on best practices.

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
        st.sidebar.success("✅ Ollama: Connected")
        models = response.json().get("models", [])
        model_names = [model.get("name") for model in models] if models else []
        if model_names:
            st.sidebar.text(f"Available models: {', '.join(model_names)}")
        else:
            st.sidebar.text(f"Using model: {OLLAMA_MODEL}")
    else:
        st.sidebar.error("❌ Ollama: Error")
except Exception as e:
    st.sidebar.error(f"❌ Ollama: Not connected ({str(e)})")

# Display notice about Proxmox connection
st.sidebar.error("❌ Proxmox: Not connected (Running in standalone mode)")

# Display help information
st.sidebar.divider()
st.sidebar.info("""
**Standalone Mode**
Running without Proxmox connection.
The AI can still provide general knowledge about Proxmox.
""")

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
            # Process the prompt using Ollama
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

# Add some helpful information at the bottom
st.divider()
st.caption("Proxmox AI Assistant powered by Ollama LLM and Streamlit")
