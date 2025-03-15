import json
import urllib.request
import urllib.parse
import http.client
import ssl
import asyncio
import os
from typing import Dict, List, Any, Optional, Callable, AsyncIterator

# Proxmox AI components
from proxmox_client import ProxmoxClient
from proxmox_helpers.command_handler import ProxmoxCommandHandler
from proxmox_helpers.script_manager import ProxmoxScriptManager
from database.manager import DatabaseManager

# Get environment variables
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434/v1")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2:latest")
PROXMOX_DB_URL = os.environ.get("PROXMOX_DB_URL", "postgresql://postgres:postgres@localhost:5432/proxmox_ai")
PROXMOX_SCRIPTS_PATH = os.environ.get("PROXMOX_SCRIPTS_PATH", "./ProxmoxVE")

class OpenAIClient:
    def __init__(self, base_url: str):
        self.base_url = base_url
        parsed_url = urllib.parse.urlparse(base_url)
        self.host = parsed_url.netloc
        self.path_prefix = parsed_url.path
        if not self.path_prefix.endswith('/'):
            self.path_prefix += '/'

    def chat_completions_create(self, model: str, messages: List[Dict[str, str]], **kwargs):
        # Build request body
        body = {
            "model": model,
            "messages": messages
        }
        
        # Add any additional parameters like temperature, top_p, etc.
        body.update({k: v for k, v in kwargs.items() if v is not None})
        
        # Convert to JSON
        data = json.dumps(body).encode('utf-8')
        
        # Print debug information
        print(f"Request URL: http://{self.host}{self.path_prefix}chat/completions")
        print(f"Request payload: {json.dumps(body, indent=2)}")
        
        # Create request headers
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Content-Length": str(len(data))
        }
        
        # Create connection
        if self.base_url.startswith("https"):
            conn = http.client.HTTPSConnection(self.host)
        else:
            conn = http.client.HTTPConnection(self.host)
        
        try:
            # Send request
            endpoint = f"{self.path_prefix}chat/completions"
            if endpoint.startswith('/'):
                endpoint = endpoint[1:]
            conn.request("POST", f"/{endpoint}", body=data, headers=headers)
            
            # Get response
            response = conn.getresponse()
            
            # Print debug information
            print(f"Response status: {response.status}")
            
            # Parse response
            if response.status != 200:
                raise Exception(f"Error: {response.status} {response.reason}")
            
            response_data = json.loads(response.read().decode())
            print(f"Response data: {json.dumps(response_data, indent=2)[:200]}...")  # Print first 200 chars
            
            return ChatCompletionResponse(response_data)
        except Exception as e:
            print(f"Error during request: {e}")
            # Return a minimal response to avoid errors
            return ChatCompletionResponse({
                "choices": [
                    {
                        "message": {
                            "content": f"Error communicating with Ollama: {e}"
                        }
                    }
                ]
            })
        finally:
            conn.close()
    
    async def chat_completions_create_async(self, model: str, messages: List[Dict[str, str]], 
                                           temperature=0.7, top_p=0.9, max_tokens=None, 
                                           stream=False, callback=None, **kwargs):
        """Create a chat completion asynchronously with streaming support."""
        path = self.path_prefix + "chat/completions"
        
        # Build request body
        body = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "top_p": top_p,
            "stream": stream
        }
        
        if max_tokens:
            body["max_tokens"] = max_tokens
        
        # Add any additional parameters
        body.update({k: v for k, v in kwargs.items() if v is not None})
        
        # Convert to JSON
        data = json.dumps(body).encode('utf-8')
        
        # Print debug information
        print(f"Request URL: http://{self.host}{path}")
        print(f"Request payload: {json.dumps(body, indent=2)}")
        
        # Create request headers
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Content-Length": str(len(data))
        }
        
        # Use TLS/SSL if the URL is https
        if self.base_url.startswith("https"):
            context = ssl.create_default_context()
            conn = http.client.HTTPSConnection(self.host, context=context)
        else:
            conn = http.client.HTTPConnection(self.host)
        
        try:
            # Send request
            conn.request("POST", path, body=data, headers=headers)
            
            # Get response
            response = conn.getresponse()
            
            # Print debug information
            print(f"Response status: {response.status}")
            
            # Parse response based on streaming or not
            if response.status != 200:
                error_content = response.read().decode()
                raise Exception(f"Error {response.status}: {error_content}")
            
            if stream:
                full_response = ""
                
                # Process the streaming response
                while True:
                    chunk = response.readline()
                    if not chunk:
                        break
                    
                    chunk_str = chunk.decode('utf-8').strip()
                    if chunk_str == '':
                        continue
                        
                    if chunk_str.startswith('data:'):
                        chunk_str = chunk_str[5:].strip()
                        
                    if chunk_str == '[DONE]':
                        break
                        
                    try:
                        chunk_data = json.loads(chunk_str)
                        if 'choices' in chunk_data:
                            content = chunk_data['choices'][0].get('delta', {}).get('content', '')
                            if content:
                                if callback:
                                    callback(content)
                                full_response += content
                    except json.JSONDecodeError:
                        continue
                
                return full_response
            else:
                response_data = json.loads(response.read().decode())
                response_obj = ChatCompletionResponse(response_data)
                
                if callback:
                    callback(response_obj.choices[0].message.content)
                
                return response_obj
        finally:
            conn.close()


class ChatCompletionResponse:
    def __init__(self, data: Dict[str, Any]):
        self.data = data
        # Handle missing choices
        if 'choices' not in data or not data.get('choices'):
            print(f"Warning: No choices in response. Response data: {json.dumps(data, indent=2)}")
            self.choices = [Choice({
                "message": {
                    "content": f"Error: No response from LLM. Response data: {json.dumps(data, indent=2)[:500]}"
                }
            })]
        else:
            self.choices = [Choice(choice) for choice in data.get("choices", [])]


class Choice:
    def __init__(self, data: Dict[str, Any]):
        self.data = data
        if 'message' not in data:
            print(f"Warning: No message in choice. Choice data: {json.dumps(data, indent=2)}")
            self.message = Message({"content": "Error: No message in response"})
        else:
            self.message = Message(data.get("message", {}))


class Message:
    def __init__(self, data: Dict[str, Any]):
        self.data = data
        self.content = data.get("content", "")


class OpenAIChatCompletionsModel:
    def __init__(self, model: str, openai_client: OpenAIClient, temperature=0.7, top_p=0.9, max_tokens=None):
        self.model = model
        self.openai_client = openai_client
        self.temperature = temperature
        self.top_p = top_p
        self.max_tokens = max_tokens
    
    def _format_messages(self, prompt=None, messages=None):
        """
        Format messages for the LLM. Either use provided messages or create a simple user message.
        """
        if messages:
            return messages
        elif prompt:
            return [{"role": "user", "content": prompt}]
        else:
            raise ValueError("Either prompt or messages must be provided")
    
    def generate(self, messages: List[Dict[str, str]], **kwargs):
        """
        Generate a completion for the given messages.
        """
        # Use provided parameters or default ones from model object
        temperature = kwargs.get('temperature', self.temperature)
        top_p = kwargs.get('top_p', self.top_p)
        max_tokens = kwargs.get('max_tokens', self.max_tokens)
        
        # Create chat completion
        response = self.openai_client.chat_completions_create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
            **{k: v for k, v in kwargs.items() if k not in ['temperature', 'top_p', 'max_tokens']}
        )
        
        return response.choices[0].message.content
    
    def complete(self, prompt: str, **kwargs):
        """
        Complete a single prompt and return the text.
        """
        messages = self._format_messages(prompt=prompt)
        return self.generate(messages, **kwargs)
    
    async def complete_async(self, prompt: str, streaming=True, callback=None, **kwargs):
        """
        Complete a single prompt asynchronously with streaming support.
        """
        messages = self._format_messages(prompt=prompt)
        
        # Use provided parameters or default ones from model object
        temperature = kwargs.get('temperature', self.temperature)
        top_p = kwargs.get('top_p', self.top_p)
        max_tokens = kwargs.get('max_tokens', self.max_tokens)
        
        # Create chat completion
        if streaming:
            return await self.openai_client.chat_completions_create_async(
                model=self.model,
                messages=messages,
                temperature=temperature,
                top_p=top_p,
                max_tokens=max_tokens,
                stream=True,
                callback=callback,
                **{k: v for k, v in kwargs.items() if k not in ['temperature', 'top_p', 'max_tokens']}
            )
        else:
            response = await self.openai_client.chat_completions_create_async(
                model=self.model,
                messages=messages,
                temperature=temperature,
                top_p=top_p,
                max_tokens=max_tokens,
                stream=False,
                **{k: v for k, v in kwargs.items() if k not in ['temperature', 'top_p', 'max_tokens']}
            )
            return response.choices[0].message.content


class Agent:
    def __init__(self, name: str, instructions: str, model: OpenAIChatCompletionsModel):
        self.name = name
        self.instructions = instructions
        self.model = model
    
    def run(self, query: str, **kwargs):
        """Run the agent."""
        messages = [
            {"role": "system", "content": self.instructions},
            {"role": "user", "content": query}
        ]
        return self.model.generate(messages, **kwargs)
    
    async def run_async(self, query: str, streaming=True, callback=None, **kwargs):
        """
        Run the agent asynchronously with streaming support.
        """
        messages = [
            {"role": "system", "content": self.instructions},
            {"role": "user", "content": query}
        ]
        
        if streaming:
            # In streaming mode, we'll run directly against the client
            return await self.model.openai_client.chat_completions_create_async(
                model=self.model.model,
                messages=messages,
                temperature=kwargs.get('temperature', self.model.temperature),
                top_p=kwargs.get('top_p', self.model.top_p),
                max_tokens=kwargs.get('max_tokens', self.model.max_tokens),
                stream=True,
                callback=callback,
                **{k: v for k, v in kwargs.items() if k not in ['temperature', 'top_p', 'max_tokens']}
            )
        else:
            # For non-streaming mode, we use the generate method
            response = await self.model.openai_client.chat_completions_create_async(
                model=self.model.model,
                messages=messages,
                temperature=kwargs.get('temperature', self.model.temperature),
                top_p=kwargs.get('top_p', self.model.top_p),
                max_tokens=kwargs.get('max_tokens', self.model.max_tokens),
                stream=False,
                **{k: v for k, v in kwargs.items() if k not in ['temperature', 'top_p', 'max_tokens']}
            )
            return response.choices[0].message.content


class Runner:
    @staticmethod
    def run_sync(agent: Agent, query: str, **kwargs):
        """Run the agent."""
        return Result(agent.run(query, **kwargs))
    
    @staticmethod
    async def run_async(agent: Agent, query: str, streaming=True, callback=None, **kwargs):
        """
        Run the agent asynchronously.
        """
        result = await agent.run_async(query, streaming=streaming, callback=callback, **kwargs)
        return Result(result)


class Result:
    def __init__(self, final_output: str):
        self.final_output = final_output


class ProxmoxAI:
    """Main Proxmox AI class that integrates LLM with Proxmox API"""
    
    def __init__(self, model: OpenAIChatCompletionsModel = None):
        """
        Initialize the Proxmox AI assistant
        
        Args:
            model: OpenAI-compatible LLM model (defaults to Ollama if not provided)
        """
        # Initialize the model
        self.model = model or setup_ollama()
        
        # Initialize Proxmox components
        self._setup_proxmox_components()
        
        # Create the agent with specific Proxmox instructions
        self.agent = Agent(
            name="Proxmox AI Assistant",
            instructions=self._get_system_instructions(),
            model=self.model
        )
    
    def _setup_proxmox_components(self):
        """Set up Proxmox API client and related components"""
        # Initialize database manager
        self.db_manager = DatabaseManager(PROXMOX_DB_URL)
        
        # Initialize Proxmox client
        self.proxmox_client = self._setup_proxmox_client()
        
        # Initialize command handler
        self.command_handler = ProxmoxCommandHandler(
            self.proxmox_client, 
            self.db_manager
        )
        
        # Initialize script manager
        self.script_manager = ProxmoxScriptManager(
            PROXMOX_SCRIPTS_PATH,
            self.db_manager
        )
    
    def _setup_proxmox_client(self) -> Optional[ProxmoxClient]:
        """
        Set up the Proxmox client from environment variables
        
        Returns:
            ProxmoxClient: Configured Proxmox client or None if not configured
        """
        # Get Proxmox connection details from environment
        host = os.environ.get("PROXMOX_HOST")
        port = int(os.environ.get("PROXMOX_PORT", "8006"))
        user = os.environ.get("PROXMOX_USER")
        token_name = os.environ.get("PROXMOX_TOKEN_ID")
        token_value = os.environ.get("PROXMOX_SECRET")
        verify_ssl = os.environ.get("PROXMOX_VERIFY_SSL", "false").lower() == "true"
        
        # Check if required environment variables are set
        if not all([host, (user or token_name), token_value]):
            print("Warning: Proxmox connection details not fully provided. "
                  "Set PROXMOX_HOST, PROXMOX_TOKEN_ID, and PROXMOX_SECRET environment variables.")
            return None
        
        # Create and return the client
        return ProxmoxClient(
            host=host,
            port=port,
            user=user,
            token_name=token_name,
            token_value=token_value,
            verify_ssl=verify_ssl
        )
    
    def _get_system_instructions(self) -> str:
        """
        Generate system instructions for the Proxmox AI agent
        
        Returns:
            str: System instructions
        """
        return """
        You are Proxmox AI, an advanced assistant for Proxmox Virtual Environment (PVE) management.
        You can help with managing VMs, containers, storage, and other Proxmox resources.
        
        You can:
        1. List and manage Proxmox nodes, VMs, and containers
        2. Start, stop, and monitor VMs and containers
        3. Create new VMs and containers using templates
        4. Provide recommendations for Proxmox setup and configuration
        5. Interpret logs and system status information
        
        When users ask you about Proxmox management tasks, you will:
        1. Understand their request and determine what operation is needed
        2. Use the appropriate Proxmox API commands to fulfill the request
        3. Present the results in a clear, organized format
        4. Explain what you did and provide context for the results
        
        Respond in a helpful, clear manner. If you don't have enough information,
        ask clarifying questions to better understand what the user needs.
        """
    
    def process_command(self, command: str) -> Dict[str, Any]:
        """
        Process a command directly through the command handler
        
        Args:
            command: User command to process
            
        Returns:
            Dict: Command result
        """
        # Log the command
        self.db_manager.log_command(command)
        
        try:
            # Process the command
            result = self.command_handler.handle_command(command)
            return result
        except Exception as e:
            print(f"Error processing command: {e}")
            return {"error": str(e)}
    
    def process_query(self, query: str, **kwargs) -> str:
        """
        Process a natural language query through the LLM
        
        Args:
            query: User query
            **kwargs: Additional parameters for the LLM
            
        Returns:
            str: Generated response
        """
        # Log the query
        self.db_manager.log_command(query)
        
        # Run the agent with the query
        result = Runner.run_sync(self.agent, query, **kwargs)
        return result.final_output
    
    async def process_query_async(
        self, query: str, streaming=True, callback: Optional[Callable[[str], None]] = None, **kwargs
    ) -> str:
        """
        Process a natural language query asynchronously
        
        Args:
            query: User query
            streaming: Whether to stream the response
            callback: Callback function for streaming
            **kwargs: Additional parameters for the LLM
            
        Returns:
            str: Generated response
        """
        # Log the query
        self.db_manager.log_command(query)
        
        # Run the agent with the query asynchronously
        result = await Runner.run_async(
            self.agent, query, streaming=streaming, callback=callback, **kwargs
        )
        return result.final_output

    def execute_script(self, script_id: int, parameters: Dict[str, str]) -> Dict[str, Any]:
        """
        Execute a Proxmox script with parameters
        
        Args:
            script_id: ID of the script to execute
            parameters: Parameters to pass to the script
            
        Returns:
            Dict: Script execution result
        """
        # Get script template from database
        script_template = self.db_manager._session.query(
            self.db_manager._get_table("ScriptTemplate")
        ).filter_by(id=script_id).first()
        
        if not script_template:
            return {"error": f"Script template with ID {script_id} not found"}
        
        # Execute the script
        return self.script_manager.execute_script(script_template, parameters)


# Check if Ollama is running
def check_ollama_status():
    """Check if Ollama is running at the specified URL."""
    print(f"Checking Ollama status at {OLLAMA_BASE_URL}...")
    
    try:
        url = f"{OLLAMA_BASE_URL}/models"
        parsed_url = urllib.parse.urlparse(url)
        
        # Create connection
        if url.startswith("https"):
            conn = http.client.HTTPSConnection(parsed_url.netloc)
        else:
            conn = http.client.HTTPConnection(parsed_url.netloc)
        
        # Send request
        path = parsed_url.path
        conn.request("GET", path)
        
        # Get response
        response = conn.getresponse()
        if response.status == 200:
            print("Ollama is running.")
            return True
        else:
            print(f"Ollama returned status {response.status}.")
            return False
    except Exception as e:
        print(f"Error checking Ollama status: {e}")
        return False


# Get available models
def list_ollama_models():
    """List all available models in Ollama."""
    print(f"Listing available models at {OLLAMA_BASE_URL}...")
    
    try:
        url = f"{OLLAMA_BASE_URL}/models"
        parsed_url = urllib.parse.urlparse(url)
        
        # Create connection
        if url.startswith("https"):
            conn = http.client.HTTPSConnection(parsed_url.netloc)
        else:
            conn = http.client.HTTPConnection(parsed_url.netloc)
        
        # Send request
        path = parsed_url.path
        conn.request("GET", path)
        
        # Get response
        response = conn.getresponse()
        if response.status == 200:
            data = json.loads(response.read().decode())
            models = [model["name"] for model in data.get("models", [])]
            print(f"Available models: {models}")
            return models
        else:
            print(f"Error: {response.status} {response.reason}")
            return []
    except Exception as e:
        print(f"Error listing Ollama models: {e}")
        return []


def setup_ollama(temperature=0.7, top_p=0.9, max_tokens=None):
    """
    Setup and return an Ollama model with the specified parameters.
    
    Args:
        temperature (float, optional): Temperature for sampling. Defaults to 0.7.
        top_p (float, optional): Top-p for nucleus sampling. Defaults to 0.9.
        max_tokens (int, optional): Maximum tokens to generate. Defaults to None.
        
    Returns:
        OpenAIChatCompletionsModel: Configured Ollama model
    """
    # Check if Ollama is running
    if not check_ollama_status():
        print("Warning: Ollama doesn't seem to be running. Make sure Ollama is running and accessible.")
    
    # List available models
    available_models = list_ollama_models()
    
    # Check if specified model is available
    if available_models and OLLAMA_MODEL not in available_models:
        print(f"Warning: Specified model '{OLLAMA_MODEL}' not found in available models: {available_models}")
        if available_models:
            print(f"Using first available model: {available_models[0]}")
            model_name = available_models[0]
        else:
            print(f"No models available. Will attempt to use '{OLLAMA_MODEL}' anyway.")
            model_name = OLLAMA_MODEL
    else:
        model_name = OLLAMA_MODEL
    
    # Create OpenAI client
    client = OpenAIClient(OLLAMA_BASE_URL)
    
    # Create model
    model = OpenAIChatCompletionsModel(
        model=model_name,
        openai_client=client,
        temperature=temperature,
        top_p=top_p,
        max_tokens=max_tokens
    )
    
    print(f"Ollama model '{model_name}' is ready.")
    return model


if __name__ == "__main__":
    # Simple example usage
    model = setup_ollama()
    
    # Create Proxmox AI assistant
    proxmox_ai = ProxmoxAI(model)
    
    # Process a query
    query = "Show me all Proxmox nodes"
    print(f"\nProcessing query: {query}")
    response = proxmox_ai.process_query(query)
    print(f"Response: {response}")