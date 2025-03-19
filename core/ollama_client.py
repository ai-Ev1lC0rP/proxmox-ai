"""
Ollama API client for Proxmox AI.
Provides embeddings and LLM integration with the Proxmox environment.
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional, Tuple, Union
import requests
from requests.exceptions import RequestException, Timeout

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("ollama_client")


class OllamaClient:
    """
    Client for interacting with the Ollama API to generate chat completions
    and create embeddings for semantic search.
    """
    
    def __init__(self, base_url: str = None, model: str = None, timeout: int = 30):
        """
        Initialize the Ollama client.
        
        Args:
            base_url: Base URL for the Ollama API (default: from env)
            model: Model to use for completions/embeddings (default: from env)
            timeout: Request timeout in seconds
        """
        self.base_url = base_url or os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434/v1")
        self.model = model or os.environ.get("OLLAMA_MODEL", "llama3.2:latest")
        self.timeout = timeout
        
        # Remove trailing slashes from base_url
        if self.base_url.endswith("/"):
            self.base_url = self.base_url[:-1]
        
        # Add /v1 if it's not already there
        if not self.base_url.endswith("/v1"):
            self.base_url = f"{self.base_url}/v1" if "/v1" not in self.base_url else self.base_url
        
        logger.info(f"Initialized Ollama client with base URL: {self.base_url}, model: {self.model}")
    
    def get_available_models(self) -> Tuple[bool, List[Dict[str, Any]]]:
        """
        Get a list of available models from Ollama.
        
        Returns:
            Tuple of (success: bool, models: list)
        """
        try:
            # Construct the models endpoint URL
            models_url = f"{self.base_url}/models"
            
            # Make the API request
            response = requests.get(models_url, timeout=self.timeout)
            response.raise_for_status()
            
            # Parse the response
            data = response.json()
            models = data.get("models", [])
            
            return True, models
            
        except (RequestException, Timeout) as e:
            logger.error(f"Error fetching available models: {str(e)}")
            return False, []
    
    def generate_completion(self, 
                           prompt: str, 
                           context: Optional[List[Dict[str, str]]] = None,
                           system_prompt: Optional[str] = None,
                           temperature: float = 0.7,
                           max_tokens: int = 1024) -> Tuple[bool, Dict[str, Any]]:
        """
        Generate a completion using the Ollama API.
        
        Args:
            prompt: User prompt to generate completion for
            context: Optional chat context (list of message dicts)
            system_prompt: Optional system prompt to guide the model
            temperature: Sampling temperature (0.0 to 1.0)
            max_tokens: Maximum tokens to generate
            
        Returns:
            Tuple of (success: bool, response: dict)
        """
        try:
            # Construct the chat completion endpoint URL
            chat_url = f"{self.base_url}/chat/completions"
            
            # Prepare messages
            messages = []
            
            # Add system prompt if provided
            if system_prompt:
                messages.append({
                    "role": "system",
                    "content": system_prompt
                })
            
            # Add previous context if provided
            if context and isinstance(context, list):
                messages.extend(context)
            
            # Add the current user prompt
            messages.append({
                "role": "user",
                "content": prompt
            })
            
            # Prepare the request payload
            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": False
            }
            
            # Make the API request
            response = requests.post(chat_url, json=payload, timeout=self.timeout)
            response.raise_for_status()
            
            # Parse the response
            data = response.json()
            
            return True, data
            
        except (RequestException, Timeout) as e:
            logger.error(f"Error generating completion: {str(e)}")
            return False, {"error": str(e)}
    
    def generate_embeddings(self, texts: Union[str, List[str]]) -> Tuple[bool, List[List[float]]]:
        """
        Generate embeddings for a text or list of texts.
        
        Args:
            texts: Single text string or list of text strings
            
        Returns:
            Tuple of (success: bool, embeddings: list)
        """
        try:
            # Construct the embeddings endpoint URL
            embeddings_url = f"{self.base_url}/embeddings"
            
            # Convert single text to list for consistent handling
            if isinstance(texts, str):
                texts = [texts]
            
            results = []
            
            # Process each text separately
            for text in texts:
                # Prepare the request payload
                payload = {
                    "model": self.model,
                    "prompt": text
                }
                
                # Make the API request
                response = requests.post(embeddings_url, json=payload, timeout=self.timeout)
                response.raise_for_status()
                
                # Parse the response
                data = response.json()
                embedding = data.get("embedding", [])
                
                results.append(embedding)
            
            return True, results
            
        except (RequestException, Timeout) as e:
            logger.error(f"Error generating embeddings: {str(e)}")
            return False, []
    
    def generate_proxmox_command(self, 
                               user_request: str, 
                               proxmox_context: Optional[Dict[str, Any]] = None,
                               examples: Optional[List[Dict[str, str]]] = None) -> Tuple[bool, Dict[str, Any]]:
        """
        Generate a Proxmox command based on a natural language request.
        
        Args:
            user_request: Natural language request
            proxmox_context: Context about the Proxmox environment
            examples: Few-shot examples of request to command mappings
            
        Returns:
            Tuple of (success: bool, result: dict)
        """
        try:
            # Create system prompt instructing model to generate Proxmox commands
            system_prompt = (
                "You are a Proxmox expert assistant that translates natural language requests into "
                "precise Proxmox commands or API calls. Respond with valid commands that could be run "
                "directly on a Proxmox system. Focus on accuracy and security. "
                "If multiple command options exist, provide the best approach with explanation."
            )
            
            # Add context to the prompt if provided
            prompt = user_request
            if proxmox_context:
                context_str = json.dumps(proxmox_context, indent=2)
                prompt = (
                    f"Based on the following Proxmox environment information:\n"
                    f"```\n{context_str}\n```\n"
                    f"Please respond to this request: {user_request}"
                )
            
            # Prepare messages
            messages = [{"role": "system", "content": system_prompt}]
            
            # Add few-shot examples if provided
            if examples:
                for example in examples:
                    if "request" in example and "command" in example:
                        messages.append({"role": "user", "content": example["request"]})
                        messages.append({"role": "assistant", "content": example["command"]})
            
            # Add the current user prompt
            messages.append({"role": "user", "content": prompt})
            
            # Make the completion request
            chat_url = f"{self.base_url}/chat/completions"
            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": 0.3,  # Lower temperature for more deterministic command generation
                "max_tokens": 1024,
                "stream": False
            }
            
            # Make the API request
            response = requests.post(chat_url, json=payload, timeout=self.timeout)
            response.raise_for_status()
            
            # Parse the response
            data = response.json()
            
            # Extract the command from the model response
            command_text = ""
            if "choices" in data and len(data["choices"]) > 0:
                command_text = data["choices"][0]["message"]["content"]
            
            return True, {
                "original_request": user_request,
                "generated_command": command_text,
                "full_response": data
            }
            
        except (RequestException, Timeout) as e:
            logger.error(f"Error generating Proxmox command: {str(e)}")
            return False, {"error": str(e)}
    
    def analyze_proxmox_logs(self, logs: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Analyze Proxmox log data to extract insights and potential issues.
        
        Args:
            logs: Raw log data from Proxmox
            
        Returns:
            Tuple of (success: bool, analysis: dict)
        """
        try:
            # Create system prompt for log analysis
            system_prompt = (
                "You are a Proxmox log analysis expert. Analyze the provided logs and extract the following information:\n"
                "1. Critical errors or warnings\n"
                "2. Performance issues or bottlenecks\n"
                "3. Security concerns\n"
                "4. Resource utilization problems\n"
                "5. Recommendations for fixing identified issues\n\n"
                "Provide your analysis in a structured format."
            )
            
            # Prepare the prompt
            prompt = f"Please analyze the following Proxmox logs:\n\n```\n{logs}\n```"
            
            # Make the completion request
            success, response = self.generate_completion(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.3,
                max_tokens=2048
            )
            
            if not success:
                return False, {"error": "Failed to generate log analysis"}
            
            # Extract analysis content
            analysis_text = ""
            if "choices" in response and len(response["choices"]) > 0:
                analysis_text = response["choices"][0]["message"]["content"]
            
            # Structure the response
            return True, {
                "analysis": analysis_text,
                "log_length": len(logs),
                "full_response": response
            }
            
        except Exception as e:
            logger.error(f"Error analyzing Proxmox logs: {str(e)}")
            return False, {"error": str(e)}
    
    def generate_documentation(self, 
                              topic: str, 
                              proxmox_api_context: Optional[Dict[str, Any]] = None) -> Tuple[bool, Dict[str, Any]]:
        """
        Generate documentation for a specific Proxmox topic.
        
        Args:
            topic: Proxmox topic to generate documentation for
            proxmox_api_context: Optional API context for reference
            
        Returns:
            Tuple of (success: bool, documentation: dict)
        """
        try:
            # Create system prompt for documentation generation
            system_prompt = (
                "You are a technical writer creating Proxmox documentation. "
                "Provide clear, accurate, and comprehensive documentation for Proxmox topics. "
                "Include practical examples, command syntax, and best practices. "
                "Use a clear structure with headings, code blocks, and examples."
            )
            
            # Prepare the prompt
            prompt = f"Please generate detailed documentation for the following Proxmox topic: {topic}"
            
            # Add API context if provided
            if proxmox_api_context:
                context_str = json.dumps(proxmox_api_context, indent=2)
                prompt += f"\n\nReference API context:\n```\n{context_str}\n```"
            
            # Make the completion request
            success, response = self.generate_completion(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.5,
                max_tokens=2048
            )
            
            if not success:
                return False, {"error": "Failed to generate documentation"}
            
            # Extract documentation content
            doc_text = ""
            if "choices" in response and len(response["choices"]) > 0:
                doc_text = response["choices"][0]["message"]["content"]
            
            # Structure the response
            return True, {
                "topic": topic,
                "documentation": doc_text,
                "full_response": response
            }
            
        except Exception as e:
            logger.error(f"Error generating documentation: {str(e)}")
            return False, {"error": str(e)}
