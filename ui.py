import chainlit as cl
from news import run_news_workflow, perform_web_search, run_news_comparison_workflow
from app import setup_ollama
from typing import List, Dict, Any, Tuple
import os

# Default model parameters
MODEL_PARAMS = {
    "temperature": 0.7,
    "top_p": 0.9,
    "max_tokens": 1000,
}

# Add more news sources for integration
NEWS_SOURCES = {
    "google_news": "Google News",
    "bbc": "BBC News",
    "guardian": "The Guardian",
    "news_api": "News API",
    "nyt": "New York Times",
    "reuters": "Reuters",
    "associated_press": "Associated Press",
    "cnn": "CNN",
    "bloomberg": "Bloomberg",
}

# Active sources (default to all enabled)
ACTIVE_SOURCES = list(NEWS_SOURCES.keys())

# Maximum conversation history length (number of message pairs)
MAX_HISTORY_LENGTH = 10

def prepare_messages_for_llm(history: List[Dict[str, str]], user_query: str, system_prompt: str = None) -> List[Dict[str, str]]:
    """
    Format conversation history and current query for LLM input.
    
    Args:
        history: List of previous message pairs
        user_query: Current user message
        system_prompt: Optional system prompt to include
        
    Returns:
        Formatted messages for LLM input
    """
    messages = []
    
    # Add system prompt if provided
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    
    # Add conversation history
    for msg in history:
        messages.append(msg)
    
    # Add current user query
    messages.append({"role": "user", "content": user_query})
    
    return messages

@cl.on_message
async def main(message: cl.Message):
    """
    Main function to handle user messages and run the news workflow or research assistant.
    """
    # Get the topic from the user message
    topic = message.content
    
    # Get user settings from the session
    session = cl.user_session.get("settings", {})
    mode = session.get("mode", "news")
    streaming = session.get("streaming", True)
    temperature = session.get("temperature", MODEL_PARAMS["temperature"])
    top_p = session.get("top_p", MODEL_PARAMS["top_p"])
    max_tokens = session.get("max_tokens", MODEL_PARAMS["max_tokens"])
    sources = session.get("sources", ACTIVE_SOURCES)
    
    # Get conversation history
    history = cl.user_session.get("conversation_history", [])
    
    # Initialize the message for streaming
    msg = cl.Message(content="", author="Assistant")
    await msg.send()
    
    try:
        if mode == "news":
            # Create appropriate system prompt for news mode
            system_prompt = f"You are a Proxmox Server Whisperer focused on solving server issues about '{topic}'. Provide solutions with a fun and magical theme as if you're casting spells to fix server problems."
            
            # Send a thinking message
            if not streaming:
                await msg.update(content=f"Consulting the ancient scrolls about '{topic}'...")
            
            # Run the news workflow with the selected sources
            news_content = run_news_workflow(
                topic, 
                sources=sources,
                streaming=streaming,
                temperature=temperature,
                top_p=top_p,
                max_tokens=max_tokens,
                callback=msg.stream_token if streaming else None,
                conversation_history=history
            )
            
            # Update with final content if not streaming
            if not streaming:
                await msg.update(content=news_content)
                
            # Add to conversation history
            history.append({"role": "user", "content": topic})
            history.append({"role": "assistant", "content": news_content if not streaming else msg.content})
            
        elif mode == "comparison":
            # News comparison mode - compare sources and detect bias
            system_prompt = f"You are a Server Oracle analyzing different approaches to solve '{topic}'. Compare different magical solutions and identify the best spells to cast on your servers."
            
            if not streaming:
                await msg.update(content=f"Deciphering multiple magical tomes about '{topic}'...")
            
            # Run the news comparison workflow
            comparison_results = run_news_comparison_workflow(
                topic,
                sources=sources,
                streaming=streaming,
                temperature=temperature,
                top_p=top_p,
                max_tokens=max_tokens,
                callback=msg.stream_token if streaming else None,
                conversation_history=history
            )
            
            # Update with final content if not streaming
            if not streaming:
                await msg.update(content=comparison_results)
                
            # Add to conversation history
            history.append({"role": "user", "content": f"Compare approaches to: {topic}"})
            history.append({"role": "assistant", "content": comparison_results if not streaming else msg.content})
            
        elif mode == "search":
            # Search mode - focused web search
            system_prompt = f"You are a Proxmox Knowledge Seeker focused on finding ancient wisdom about '{topic}'. Use your magical search results to provide detailed server solutions."
            
            if not streaming:
                await msg.update(content=f"Searching the mystical web for '{topic}'...")
            
            # Perform web search
            search_results = perform_web_search(
                topic,
                streaming=streaming,
                temperature=temperature,
                top_p=top_p,
                max_tokens=max_tokens,
                callback=msg.stream_token if streaming else None,
                conversation_history=history
            )
            
            # Update with final content if not streaming
            if not streaming:
                await msg.update(content=search_results)
                
            # Add to conversation history
            history.append({"role": "user", "content": topic})
            history.append({"role": "assistant", "content": search_results if not streaming else msg.content})
            
        else:
            # Research mode - direct interaction with the LLM
            system_prompt = "You are a mystical Proxmox Guru. Provide magical, informative, and creative responses to server management questions, while acknowledging your mystical limitations."
            
            # Prepare messages for LLM with conversation history
            messages = prepare_messages_for_llm(history, topic, system_prompt)
            
            model = setup_ollama(
                temperature=temperature,
                top_p=top_p,
                max_tokens=max_tokens
            )
            
            if streaming:
                # Stream the response
                async def stream_callback(token):
                    await msg.stream_token(token)
                
                response = await model.complete_async(
                    prompt=topic, 
                    streaming=True, 
                    callback=stream_callback,
                    temperature=temperature,
                    top_p=top_p,
                    max_tokens=max_tokens,
                    messages=messages
                )
                
                # Add to conversation history after streaming is complete
                history.append({"role": "user", "content": topic})
                history.append({"role": "assistant", "content": msg.content})
            else:
                # Get the complete response
                response = model.complete(
                    prompt=topic,
                    temperature=temperature,
                    top_p=top_p,
                    max_tokens=max_tokens,
                    messages=messages
                )
                await msg.update(content=response)
                
                # Add to conversation history
                history.append({"role": "user", "content": topic})
                history.append({"role": "assistant", "content": response})
        
        # Trim history if it exceeds maximum length
        if len(history) > MAX_HISTORY_LENGTH * 2:  # *2 because each turn has user + assistant message
            history = history[-MAX_HISTORY_LENGTH * 2:]
            
        # Update conversation history in session
        cl.user_session.set("conversation_history", history)
            
    except Exception as e:
        # Handle any errors
        await msg.update(content=f"Error: {str(e)}")

@cl.on_chat_start
async def start():
    """
    Function that runs when a new chat session starts.
    Sets up the UI with settings controls.
    """
    # Initialize default settings
    cl.user_session.set(
        "settings", 
        {
            "mode": "news",
            "streaming": True,
            "temperature": MODEL_PARAMS["temperature"],
            "top_p": MODEL_PARAMS["top_p"],
            "max_tokens": MODEL_PARAMS["max_tokens"],
            "sources": ACTIVE_SOURCES
        }
    )
    
    # Initialize conversation history
    cl.user_session.set("conversation_history", [])
    
    # Create settings panel with mode toggle
    settings = [
        cl.Select(
            id="mode",
            label="Mode",
            value="news",
            options=[
                cl.Option(value="news", label="Server Whisperer"),
                cl.Option(value="comparison", label="Solution Comparison"),
                cl.Option(value="search", label="Mystical Web Search"),
                cl.Option(value="research", label="Proxmox Guru")
            ],
            description="Select mode: Server Whisperer for direct assistance, Solution Comparison for comparing approaches, Mystical Web Search for gathering knowledge, or Proxmox Guru for deep magic"
        ),
        cl.Switch(
            id="streaming",
            label="Enable Streaming",
            initial=True,
            description="Stream the response as it's being generated"
        ),
        cl.Slider(
            id="temperature",
            label="Temperature",
            min=0.0,
            max=1.0,
            step=0.1,
            initial=MODEL_PARAMS["temperature"],
            description="Higher values make output more random, lower values more deterministic"
        ),
        cl.Slider(
            id="top_p",
            label="Top P",
            min=0.0,
            max=1.0,
            step=0.1,
            initial=MODEL_PARAMS["top_p"],
            description="Controls diversity via nucleus sampling"
        ),
        cl.Slider(
            id="max_tokens",
            label="Max Tokens",
            min=100,
            max=2000,
            step=100,
            initial=MODEL_PARAMS["max_tokens"],
            description="Maximum number of tokens to generate"
        ),
        cl.MultiSelect(
            id="sources",
            label="News Sources",
            options=[cl.Option(value=k, label=v) for k, v in NEWS_SOURCES.items()],
            initial=ACTIVE_SOURCES,
            description="Select which news sources to include"
        ),
        cl.Switch(
            id="context_retention",
            label="Remember Conversation Context",
            initial=True,
            description="Retain conversation history for more contextual responses"
        )
    ]
    
    # Add settings to the UI
    await cl.ChatSettings(settings).send()
    
    # Send a welcome message
    await cl.Message(
        content="Welcome to the Proxmox Server Whisperer! 🧙‍♂️ I can tame your wild servers and decode their mysterious behaviors. Select your magical mode in the settings panel and tell me about your server conundrum!",
        author="Assistant"
    ).send()
    
@cl.on_settings_update
async def on_settings_update(settings: Dict[str, Any]):
    """
    Handle settings updates from the user.
    """
    # Update the user session with new settings
    cl.user_session.set("settings", settings)
    
    # Clear conversation history if context retention is turned off
    if not settings.get("context_retention", True):
        cl.user_session.set("conversation_history", [])
    
    # Send a confirmation message about the updated settings
    mode_map = {
        "news": "Server Whisperer",
        "comparison": "Solution Comparison",
        "search": "Mystical Web Search",
        "research": "Proxmox Guru"
    }
    mode_text = mode_map.get(settings.get("mode"), "Unknown")
    streaming_text = "enabled" if settings.get("streaming", True) else "disabled"
    context_text = "enabled" if settings.get("context_retention", True) else "disabled"
    num_sources = len(settings.get("sources", []))
    
    # Only mention sources if in news mode
    source_text = f"Selected {num_sources} news sources." if settings.get("mode") == "news" else ""
    
    await cl.Message(
        content=f"Settings updated: Mode set to {mode_text}, streaming {streaming_text}, context retention {context_text}. "
                f"Using temperature={settings.get('temperature')}, top_p={settings.get('top_p')}, "
                f"max_tokens={settings.get('max_tokens')}. "
                f"{source_text}",
        author="Assistant"
    ).send()

@cl.on_stop
def on_stop():
    """
    Handle chat session stopping - can be used to clean up resources
    or save conversation history if needed.
    """
    pass

@cl.action_callback("clear_history")
async def clear_history():
    """
    Action callback to clear conversation history
    """
    # Clear conversation history
    cl.user_session.set("conversation_history", [])
    
    # Send confirmation message
    await cl.Message(
        content="Conversation history has been cleared. Starting fresh!",
        author="Assistant"
    ).send()