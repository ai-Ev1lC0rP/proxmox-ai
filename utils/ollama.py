"""
Ollama integration utilities for the Proxmox AI project.
Provides a client for communicating with the Ollama API.
"""

import os
import json
import requests
from typing import Dict, List, Any, Optional, Union, Tuple


class OllamaClient:
    """Client for interacting with the Ollama API using a similar interface to OpenAI."""
    
    def __init__(self, base_url: str = None, model: str = None):
        """
        Initialize the Ollama client.
        
        Args:
            base_url: Base URL for the Ollama API (default: from environment)
            model: Default model to use (default: from environment)
        """
        self.base_url = base_url or os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434/v1")
        self.model = model or os.environ.get("OLLAMA_MODEL", "llama3.2:latest")
        
        # Remove trailing slash if present
        if self.base_url.endswith("/"):
            self.base_url = self.base_url[:-1]
            
    def check_connection(self) -> Tuple[bool, str]:
        """
        Check if the Ollama API is available.
        
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            response = requests.get(f"{self.base_url.replace('/v1', '')}/api/tags", timeout=5)
            if response.status_code == 200:
                return True, "Connected"
            return False, f"Error: {response.status_code}"
        except Exception as e:
            return False, f"Connection error: {str(e)}"
    
    def list_models(self) -> List[Dict[str, Any]]:
        """
        List available models from Ollama.
        
        Returns:
            List of model information dictionaries
        """
        try:
            response = requests.get(f"{self.base_url}/models", timeout=10)
            response.raise_for_status()
            return response.json().get("models", [])
        except Exception as e:
            print(f"Error listing models: {e}")
            return []
    
    def chat_completions(
        self, 
        messages: List[Dict[str, str]], 
        model: str = None,
        temperature: float = 0.7,
        top_p: float = 0.9,
        max_tokens: int = None,
        stream: bool = False
    ) -> Dict[str, Any]:
        """
        Get chat completions from Ollama API.
        
        Args:
            messages: List of message dictionaries with role and content
            model: Model to use (overrides default)
            temperature: Sampling temperature (0-1)
            top_p: Nucleus sampling parameter (0-1)
            max_tokens: Maximum tokens to generate
            stream: Whether to stream the response
            
        Returns:
            Response dictionary with generated text
        """
        model_to_use = model or self.model
        
        payload = {
            "model": model_to_use,
            "messages": messages,
            "options": {
                "temperature": temperature,
                "top_p": top_p,
            }
        }
        
        if max_tokens:
            payload["options"]["num_predict"] = max_tokens
            
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                timeout=60,
                stream=stream
            )
            response.raise_for_status()
            
            if stream:
                return response  # Return the response object for streaming
            
            return response.json()
        except Exception as e:
            error_msg = f"Error getting chat completion: {str(e)}"
            print(error_msg)
            return {
                "error": error_msg,
                "choices": [{
                    "message": {
                        "content": f"Error: Failed to get response from Ollama. Please check your connection and try again. ({str(e)})"
                    }
                }]
            }
    
    def embeddings(self, text: str, model: str = None) -> Dict[str, Any]:
        """
        Get embeddings for text from Ollama API.
        
        Args:
            text: Text to embed
            model: Model to use (overrides default)
            
        Returns:
            Response dictionary with embeddings
        """
        model_to_use = model or self.model
        
        payload = {
            "model": model_to_use,
            "prompt": text
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/embeddings",
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            error_msg = f"Error getting embeddings: {str(e)}"
            print(error_msg)
            return {"error": error_msg, "embedding": []}
