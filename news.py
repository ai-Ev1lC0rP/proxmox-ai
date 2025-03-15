import json
import urllib.request
import urllib.parse
import http.client
import ssl
import sys
import os
import random
import re
import asyncio
from typing import Dict, List, Any, Optional, Callable, AsyncIterator
from datetime import datetime

# Import our news analyzer module
try:
    import news_analyzer
    NEWS_ANALYZER_AVAILABLE = True
except ImportError:
    print("Warning: news_analyzer module not available. Install NLTK for news source comparison functionality.")
    NEWS_ANALYZER_AVAILABLE = False

# Simple config loader that emulates dotenv functionality
def load_env_from_file():
    try:
        env_file = os.path.join(os.path.dirname(__file__), '.env')
        if os.path.exists(env_file):
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        key, value = line.split('=', 1)
                        os.environ[key.strip()] = value.strip().strip('"\'')
            print("Loaded environment variables from .env file")
    except Exception as e:
        print(f"Warning: Could not load .env file: {e}")

# Load environment variables from .env file
load_env_from_file()

current_date = datetime.now().strftime("%Y-%m-%d")

# Get API keys from environment variables
NEWS_API_KEY = os.environ.get("NEWS_API_KEY", "")
GUARDIAN_API_KEY = os.environ.get("GUARDIAN_API_KEY", "")
NYT_API_KEY = os.environ.get("NYT_API_KEY", "")
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434/v1")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2:latest")
MAX_NEWS_RESULTS = int(os.environ.get("MAX_NEWS_RESULTS", "5"))

# 1. Create News Fetcher Tool

def function_tool(func):
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    wrapper.is_tool = True
    wrapper.__name__ = func.__name__
    return wrapper

def extract_article_from_html(html, start_pattern, title_pattern, url_pattern, content_pattern):
    """Extract article information from HTML content using regex patterns"""
    articles = []
    
    # Find all articles
    article_sections = re.findall(start_pattern, html, re.DOTALL)
    
    for section in article_sections[:MAX_NEWS_RESULTS]:
        # Extract title
        title_match = re.search(title_pattern, section, re.DOTALL)
        title = title_match.group(1).strip() if title_match else "No title"
        
        # Extract URL
        url_match = re.search(url_pattern, section, re.DOTALL)
        url = url_match.group(1).strip() if url_match else "#"
        
        # Extract content
        content_match = re.search(content_pattern, section, re.DOTALL)
        content = content_match.group(1).strip() if content_match else "No content available"
        
        # Clean up the text (remove HTML tags)
        title = re.sub(r'<[^>]+>', '', title)
        content = re.sub(r'<[^>]+>', '', content)
        
        articles.append({
            'title': title,
            'url': url,
            'date': current_date,
            'source': 'News Source',
            'content': content
        })
    
    return articles

@function_tool
def get_news_articles(topic, sources=None):
    print(f"Fetching real news articles about {topic}...")
    
    # Try multiple methods to get news
    all_articles = []
    
    # Try using several methods to fetch news
    methods_tried = 0
    
    # Filter news sites by sources if provided
    filtered_news_sites = []
    if sources:
        filtered_news_sites = [site for site in news_sites if site['source'].lower().replace(' ', '_') in sources]
    else:
        filtered_news_sites = news_sites
    
    # Method 1: Try direct HTML fetch from news sites
    for site in filtered_news_sites:
        try:
            # Get the URL for this topic
            url = site['url'](topic)
            
            headers = {'User-Agent': site['user_agent']}
            req = urllib.request.Request(url, headers=headers)
            
            with urllib.request.urlopen(req, timeout=10) as response:
                html = response.read().decode('utf-8')
                
                # Basic article extraction
                if site['source'] == 'Google News':
                    # Extract articles using regex patterns
                    articles = extract_article_from_html(
                        html, 
                        site['article_start'], 
                        site['title_pattern'], 
                        site['url_pattern'], 
                        site['content_pattern']
                    )
                    
                    # Fix Google News URLs
                    for article in articles:
                        article['source'] = site['source']
                        if not article['url'].startswith('http'):
                            article['url'] = article['url'].replace('./articles/', 'https://news.google.com/articles/')
                    
                    all_articles.extend(articles)
                else:
                    # Extract articles using regex patterns
                    articles = extract_article_from_html(
                        html, 
                        site['article_start'], 
                        site['title_pattern'], 
                        site['url_pattern'], 
                        site['content_pattern']
                    )
                    
                    # Set the source
                    for article in articles:
                        article['source'] = site['source']
                        if article['url'].startswith('/'):
                            base_url = url.split('/search')[0]
                            article['url'] = f"{base_url}{article['url']}"
                    
                    all_articles.extend(articles)
                
                methods_tried += 1
                
                # If we have enough articles, break
                if len(all_articles) >= MAX_NEWS_RESULTS:
                    break
                    
        except Exception as e:
            print(f"Could not fetch from {site['source']}: {e}")
    
    # Method 2: If we have a Guardian API key, try that
    if len(all_articles) < MAX_NEWS_RESULTS and GUARDIAN_API_KEY and ('guardian' in sources if sources else True):
        try:
            guardian_url = f"https://content.guardianapis.com/search?q={urllib.parse.quote(topic)}&show-fields=headline,body&api-key={GUARDIAN_API_KEY}"
            with urllib.request.urlopen(guardian_url) as response:
                data = json.loads(response.read().decode())
                results = data.get('response', {}).get('results', [])
                
                for result in results[:MAX_NEWS_RESULTS - len(all_articles)]:
                    all_articles.append({
                        'title': result.get('webTitle', ''),
                        'url': result.get('webUrl', ''),
                        'date': result.get('webPublicationDate', ''),
                        'source': 'The Guardian',
                        'content': result.get('fields', {}).get('body', 'No content available')
                    })
            
            methods_tried += 1
        except Exception as e:
            print(f"Could not fetch from The Guardian API: {e}")
    
    # Method 3: If we have a News API key, try that
    if len(all_articles) < MAX_NEWS_RESULTS and NEWS_API_KEY and ('news_api' in sources if sources else True):
        try:
            news_api_url = f"https://newsapi.org/v2/everything?q={urllib.parse.quote(topic)}&apiKey={NEWS_API_KEY}&pageSize={MAX_NEWS_RESULTS - len(all_articles)}"
            req = urllib.request.Request(news_api_url, headers={'User-Agent': 'Mozilla/5.0'})
            
            with urllib.request.urlopen(req) as response:
                data = json.loads(response.read().decode())
                articles = data.get('articles', [])
                
                for article in articles:
                    all_articles.append({
                        'title': article.get('title', ''),
                        'url': article.get('url', ''),
                        'date': article.get('publishedAt', current_date),
                        'source': article.get('source', {}).get('name', 'News API'),
                        'content': article.get('description', '') + '\n\n' + article.get('content', '')
                    })
            
            methods_tried += 1
        except Exception as e:
            print(f"Could not fetch from News API: {e}")
    
    # Method 4: If we have a NY Times API key, try that
    if len(all_articles) < MAX_NEWS_RESULTS and NYT_API_KEY and ('nyt' in sources if sources else True):
        try:
            nyt_url = f"https://api.nytimes.com/svc/search/v2/articlesearch.json?q={urllib.parse.quote(topic)}&api-key={NYT_API_KEY}"
            with urllib.request.urlopen(nyt_url) as response:
                data = json.loads(response.read().decode())
                docs = data.get('response', {}).get('docs', [])
                
                for doc in docs[:MAX_NEWS_RESULTS - len(all_articles)]:
                    # Format the content from the abstract and lead paragraph
                    content = doc.get('abstract', '') 
                    if doc.get('lead_paragraph'):
                        content += '\n\n' + doc.get('lead_paragraph', '')
                    
                    # Build the URL
                    url = doc.get('web_url', '')
                    
                    all_articles.append({
                        'title': doc.get('headline', {}).get('main', ''),
                        'url': url,
                        'date': doc.get('pub_date', current_date),
                        'source': 'New York Times',
                        'content': content
                    })
            
            methods_tried += 1
        except Exception as e:
            print(f"Could not fetch from NY Times API: {e}")

    # If we have articles, format and return them
    if all_articles:
        # Format the results
        news_results = "\n\n".join([
            f"Title: {article.get('title')}\n"
            f"URL: {article.get('url')}\n"
            f"Date: {article.get('date')}\n"
            f"Source: {article.get('source')}\n"
            f"Content: {article.get('content')}"
            for article in all_articles[:MAX_NEWS_RESULTS]
        ])
        return news_results
    
    # Last resort: Try an alternative approach - search engine results
    try:
        search_url = f"https://duckduckgo.com/html/?q={urllib.parse.quote(topic+'news')}"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        req = urllib.request.Request(search_url, headers=headers)
        
        with urllib.request.urlopen(req, timeout=10) as response:
            html = response.read().decode('utf-8')
            
            # Find all result items
            result_pattern = r'<div class="result__body">(.*?)</div>\s*</div>\s*</div>'
            title_pattern = r'<a class="result__a"[^>]*>(.*?)</a>'
            url_pattern = r'<a class="result__a"[^>]*href="([^"]*)"'
            snippet_pattern = r'<a class="result__snippet"[^>]*>(.*?)</a>'
            
            results = re.findall(result_pattern, html, re.DOTALL)
            search_articles = []
            
            for result in results[:MAX_NEWS_RESULTS]:
                title_match = re.search(title_pattern, result, re.DOTALL)
                url_match = re.search(url_pattern, result, re.DOTALL)
                snippet_match = re.search(snippet_pattern, result, re.DOTALL)
                
                title = title_match.group(1).strip() if title_match else "No title"
                url = url_match.group(1).strip() if url_match else "#"
                content = snippet_match.group(1).strip() if snippet_match else "No content available"
                
                # Clean up the text (remove HTML tags)
                title = re.sub(r'<[^>]+>', '', title)
                content = re.sub(r'<[^>]+>', '', content)
                
                search_articles.append({
                    'title': title,
                    'url': url,
                    'date': current_date,
                    'source': 'Search Result',
                    'content': content
                })
            
            if search_articles:
                news_results = "\n\n".join([
                    f"Title: {article.get('title')}\n"
                    f"URL: {article.get('url')}\n"
                    f"Date: {article.get('date')}\n"
                    f"Source: {article.get('source')}\n"
                    f"Content: {article.get('content')}"
                    for article in search_articles
                ])
                return news_results
    except Exception as e:
        print(f"Could not fetch search results: {e}")
    
    # If all else fails, return a message
    return "Could not retrieve real news articles about this topic. Please try a different topic or check your API keys in the .env file."


# Add more news sources
news_sites = [
    {
        'url': lambda topic: f"https://news.google.com/search?q={urllib.parse.quote(topic)}&hl=en-US&gl=US&ceid=US:en",
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'article_start': r'<a class="DY5T1d"',
        'title_pattern': r'<a[^>]*>([^<]+)</a>',
        'url_pattern': r'href="([^"]+)"',
        'content_pattern': r'class="[^"]*">([^<]+)</div>',
        'source': 'Google News'
    },
    {
        'url': lambda topic: f"https://www.bbc.com/search?q={urllib.parse.quote(topic)}",
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'article_start': r'<div class="ssrcss-1mc1y2-PromoContent',
        'title_pattern': r'<span[^>]*>([^<]+)</span>',
        'url_pattern': r'href="([^"]+)"',
        'content_pattern': r'<p[^>]*>([^<]+)</p>',
        'source': 'BBC News'
    },
    {
        'url': lambda topic: f"https://www.reuters.com/search/news?blob={urllib.parse.quote(topic)}",
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'article_start': r'<div class="search-result-content',
        'title_pattern': r'<h3[^>]*>([^<]+)</h3>',
        'url_pattern': r'<a href="([^"]+)"',
        'content_pattern': r'<p[^>]*>([^<]+)</p>',
        'source': 'Reuters'
    },
    {
        'url': lambda topic: f"https://apnews.com/search?q={urllib.parse.quote(topic)}",
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'article_start': r'<div class="CardHeadline',
        'title_pattern': r'<h2[^>]*>([^<]+)</h2>',
        'url_pattern': r'<a href="([^"]+)"',
        'content_pattern': r'<p[^>]*>([^<]+)</p>',
        'source': 'Associated Press'
    },
    {
        'url': lambda topic: f"https://www.cnn.com/search?q={urllib.parse.quote(topic)}",
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'article_start': r'<div class="cnn-search__result',
        'title_pattern': r'<h3[^>]*>([^<]+)</h3>',
        'url_pattern': r'<a href="([^"]+)"',
        'content_pattern': r'<div class="cnn-search__result-body">([^<]+)</div>',
        'source': 'CNN'
    },
    {
        'url': lambda topic: f"https://www.bloomberg.com/search?query={urllib.parse.quote(topic)}",
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'article_start': r'<article class="',
        'title_pattern': r'<h1[^>]*>([^<]+)</h1>',
        'url_pattern': r'<a href="([^"]+)"',
        'content_pattern': r'<p[^>]*>([^<]+)</p>',
        'source': 'Bloomberg'
    }
]

@function_tool
def analyze_news_bias(topic, sources=None):
    """
    Analyze and compare news from different sources to detect bias.
    
    Args:
        topic (str): The topic to analyze
        sources (List[str], optional): List of news sources to compare
        
    Returns:
        str: A formatted report comparing the sources and highlighting bias
    """
    if not NEWS_ANALYZER_AVAILABLE:
        return "News analyzer is not available. Please install NLTK and dependencies to use this feature."
    
    print(f"Analyzing news sources and detecting bias for topic: {topic}")
    
    # Fetch news articles
    news_articles = get_news_articles(topic, sources=sources)
    
    # Ensure we have enough articles from different sources
    sources_available = set(article.get('source', 'Unknown') for article in news_articles)
    if len(sources_available) < 2:
        return f"Comparison requires at least two different news sources. Only found: {', '.join(sources_available)}"
    
    # Perform the comparison analysis
    analysis_report = news_analyzer.analyze_and_compare_news(news_articles, topic)
    
    return analysis_report

def run_news_comparison_workflow(topic, sources=None, streaming=False, temperature=0.7, top_p=0.9, 
                      max_tokens=1000, callback=None, conversation_history=None):
    """
    Runs a news comparison workflow for a given topic, analyzing bias and differences between sources.
    
    Args:
        topic (str): The topic to fetch news about
        sources (List[str], optional): List of news sources to use
        streaming (bool, optional): Whether to stream the response
        temperature (float, optional): Temperature for the model
        top_p (float, optional): Top-p for the model
        max_tokens (int, optional): Maximum tokens to generate
        callback (function, optional): Callback function for streaming
        conversation_history (List[Dict], optional): Previous conversation history
        
    Returns:
        str: The news source comparison analysis
    """
    print(f"Comparing news sources for topic: {topic}")
    
    # Check if Ollama is running
    if not check_ollama_status():
        return "Error: Ollama is not running. Please start it with 'ollama serve'"
    
    # Get the news comparison analysis
    comparison_report = analyze_news_bias(topic, sources=sources)
    
    # If we just want the raw analysis, return it
    if not streaming and not callback:
        return comparison_report
    
    # If we're going to have the LLM enhance the report, set up the model
    client = OpenAIClient(base_url=OLLAMA_BASE_URL)
    model = OpenAIChatCompletionsModel(
        model=OLLAMA_MODEL,
        openai_client=client,
        temperature=temperature,
        top_p=top_p,
        max_tokens=max_tokens
    )
    
    # Create a prompt for the model
    prompt = f"""
I have analyzed news from different sources about "{topic}". Here is the raw comparison report:

{comparison_report}

Please review this report and provide a user-friendly summary that:
1. Highlights the key differences between news sources
2. Explains the potential biases detected in simple terms
3. Offers guidance on how to interpret these differences
4. Suggests how to get a balanced perspective on this topic

Make the summary engaging, educational, and easy to understand for someone without expertise in media analysis.
"""
    
    if streaming and callback:
        # Process asynchronously with streaming
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            # Create messages with system instruction, conversation history, and the current prompt
            messages = [
                {"role": "system", "content": "You are a media literacy expert who helps users understand bias and differences in news reporting."}
            ]
            
            # Add conversation history if provided
            if conversation_history:
                messages.extend(conversation_history)
            
            # Add current user query
            messages.append({"role": "user", "content": prompt})
            
            result = loop.run_until_complete(model.complete_async(
                prompt, 
                messages=messages,
                streaming=True,
                callback=callback,
                temperature=temperature,
                top_p=top_p,
                max_tokens=max_tokens
            ))
            return result
        finally:
            loop.close()
    else:
        # For non-streaming, use the standard agent approach
        expert_agent = Agent(
            name="MediaLiteracyExpert",
            instructions="You are a media literacy expert who helps users understand bias and differences in news reporting.",
            model=model
        )
        
        # Process and return the result with conversation history if provided
        result = Runner.run_sync(expert_agent, prompt, conversation_history=conversation_history)
        return result.final_output

# 2. Create AI Agents

class OpenAIClient:
    def __init__(self, base_url: str):
        self.base_url = base_url
        parsed_url = urllib.parse.urlparse(base_url)
        self.host = parsed_url.netloc
        self.path_prefix = parsed_url.path
        if not self.path_prefix.endswith('/'):
            self.path_prefix += '/'
    
    def chat_completions_create(self, model: str, messages: List[Dict[str, str]], **kwargs):
        """Create a chat completion."""
        path = self.path_prefix + "chat/completions"
        
        # Build request body
        body = {
            "model": model,
            "messages": messages
        }
        
        # Add any additional parameters like temperature, top_p, etc.
        body.update({k: v for k, v in kwargs.items() if v is not None})
        
        # Convert to JSON
        data = json.dumps(body).encode('utf-8')
        
        # Create request headers
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Content-Length": str(len(data))
        }
        
        # Create connection
        # Use TLS/SSL if the URL is https
        if self.base_url.startswith("https"):
            conn = http.client.HTTPSConnection(self.host)
        else:
            conn = http.client.HTTPConnection(self.host)
        
        try:
            # Send request
            conn.request("POST", path, body=data, headers=headers)
            
            # Get response
            response = conn.getresponse()
            
            # Parse response
            if response.status != 200:
                raise Exception(f"Error: {response.status} {response.reason}")
            
            response_data = json.loads(response.read().decode())
            return ChatCompletionResponse(response_data)
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
    
    def generate(self, messages: List[Dict[str, str]], **kwargs):
        """Generate a completion for the given messages."""
        # Combine default parameters with any overrides
        params = {
            "temperature": kwargs.get("temperature", self.temperature),
            "top_p": kwargs.get("top_p", self.top_p),
        }
        
        if self.max_tokens or "max_tokens" in kwargs:
            params["max_tokens"] = kwargs.get("max_tokens", self.max_tokens)
        
        return self.openai_client.chat_completions_create(
            model=self.model,
            messages=messages,
            **params
        )
    
    def complete(self, prompt: str, **kwargs):
        """Complete a single prompt and return the text."""
        messages = [{"role": "user", "content": prompt}]
        completion = self.generate(messages, **kwargs)
        return completion.choices[0].message.content
    
    async def complete_async(self, prompt: str, streaming=True, callback=None, **kwargs):
        """Complete a single prompt asynchronously with streaming support."""
        messages = [{"role": "user", "content": prompt}]
        
        # Combine default parameters with any overrides
        params = {
            "temperature": kwargs.get("temperature", self.temperature),
            "top_p": kwargs.get("top_p", self.top_p),
            "stream": streaming
        }
        
        if self.max_tokens or "max_tokens" in kwargs:
            params["max_tokens"] = kwargs.get("max_tokens", self.max_tokens)
        
        # If streaming and a callback is provided, stream the response
        result = await self.openai_client.chat_completions_create_async(
            model=self.model,
            messages=messages,
            callback=callback,
            **params
        )
        
        if streaming:
            # For streaming, result is already the full content string
            return result
        else:
            # For non-streaming, result is a ChatCompletionResponse object
            return result.choices[0].message.content

class Agent:
    def __init__(self, name: str, instructions: str, model: OpenAIChatCompletionsModel, tools=None):
        self.name = name
        self.instructions = instructions
        self.model = model
        self.tools = tools or []

    def run(self, query: str) -> str:
        messages = [
            {"role": "system", "content": self.instructions},
            {"role": "user", "content": query}
        ]
        return self.model.generate(messages)

class Runner:
    @staticmethod
    def run_sync(agent: Agent, query: str, conversation_history=None) -> Any:
        try:
            if conversation_history:
                messages = [
                    {"role": "system", "content": agent.instructions}
                ]
                messages.extend(conversation_history)
                messages.append({"role": "user", "content": query})
                result = agent.model.generate(messages)
            else:
                result = agent.run(query)
            return Result(result)
        except Exception as e:
            print(f"Error running agent: {e}")
            return Result(f"Error: {e}")

class Result:
    def __init__(self, final_output: str):
        self.final_output = final_output

# Create the model and agent
def check_ollama_status():
    try:
        conn = http.client.HTTPConnection("localhost", 11434)
        conn.request("GET", "/api/version")
        response = conn.getresponse()
        response.read()  # Read and discard the response body
        if response.status == 200:
            print("Ollama is running")
            return True
        else:
            print(f"Ollama returned non-200 status: {response.status}")
            return False
    except Exception as e:
        print(f"Ollama check failed: {e}")
        return False

def list_ollama_models():
    try:
        conn = http.client.HTTPConnection("localhost", 11434)
        conn.request("GET", "/api/tags")
        response = conn.getresponse()
        if response.status == 200:
            data = json.loads(response.read().decode('utf-8'))
            print("Available models:")
            for model in data.get('models', []):
                print(f" - {model.get('name')}")
            return data.get('models', [])
        else:
            print(f"Failed to list models: {response.status}")
            return []
    except Exception as e:
        print(f"Error listing models: {e}")
        return []

# Define workflow function for future use
def run_news_workflow(topic, sources=None, streaming=False, temperature=0.7, top_p=0.9, 
                      max_tokens=1000, callback=None, conversation_history=None):
    """
    Runs the complete news workflow for a given topic.
    
    Args:
        topic (str): The topic to fetch news about
        sources (List[str], optional): List of news sources to use
        streaming (bool, optional): Whether to stream the response
        temperature (float, optional): Temperature for the model
        top_p (float, optional): Top-p for the model
        max_tokens (int, optional): Maximum tokens to generate
        callback (function, optional): Callback function for streaming
        conversation_history (List[Dict], optional): Previous conversation history
        
    Returns:
        str: The summarized and edited news content
    """
    print(f"Searching for news about: {topic}")
    
    # Check if Ollama is running
    if not check_ollama_status():
        return "Error: Ollama is not running. Please start it with 'ollama serve'"
    
    # List available models
    models = list_ollama_models()
    model_names = [m.get('name') for m in models]
    
    # Use model from environment variable or fallback to default
    model_name = OLLAMA_MODEL
    if model_names and model_name not in model_names:
        print(f"Warning: Model '{model_name}' not found. Available models: {model_names}")
        if model_names:
            model_name = model_names[0]
            print(f"Using model: {model_name}")
    
    # Create the model and client
    client = OpenAIClient(base_url=OLLAMA_BASE_URL)
    model = OpenAIChatCompletionsModel(
        model=model_name,
        openai_client=client,
        temperature=temperature,
        top_p=top_p,
        max_tokens=max_tokens
    )
    
    # Step 1: Fetch news articles
    news = get_news_articles(topic, sources=sources)
    
    if streaming and callback:
        # For streaming, process directly without using the Runner
        prompt = f"Summarize these news articles about {topic}:\n\n{news}"
        
        # Create instructions
        instructions = "You are an expert editor who can summarize news articles in a concise, informative way. Focus on facts and eliminate any speculation or bias."
        
        # Create messages with system instruction, conversation history, and the current prompt
        messages = [
            {"role": "system", "content": instructions}
        ]
        
        # Add conversation history if provided
        if conversation_history:
            messages.extend(conversation_history)
        
        # Add current user query
        messages.append({"role": "user", "content": prompt})
        
        # Process asynchronously with streaming
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(model.complete_async(
                prompt, 
                messages=messages,
                streaming=True,
                callback=callback,
                temperature=temperature,
                top_p=top_p,
                max_tokens=max_tokens
            ))
            return result
        finally:
            loop.close()
    else:
        # For non-streaming, use the standard agent approach
        editor_agent = Agent(
            name="Editor",
            instructions="You are an expert editor who can summarize news articles in a concise, informative way. Focus on facts and eliminate any speculation or bias.",
            model=model
        )
        
        # Process and return the result with conversation history if provided
        query = f"Summarize these news articles about {topic}:\n\n{news}"
        result = Runner.run_sync(editor_agent, query, conversation_history=conversation_history)
        return result.final_output

@function_tool
def perform_web_search(topic, streaming=False, temperature=0.7, top_p=0.9, max_tokens=1000, callback=None, conversation_history=None):
    """
    Perform a web search for the given topic, and provide a summary of the findings.
    
    Args:
        topic (str): The topic to search for
        streaming (bool): Whether to stream the response
        temperature (float): Temperature parameter for the LLM
        top_p (float): Top-p parameter for the LLM
        max_tokens (int): Maximum tokens to generate
        callback (function): Callback function for streaming
        conversation_history (List[Dict], optional): Previous conversation history
        
    Returns:
        str: A summary of the search results
    """
    print(f"Performing web search for {topic}...")
    
    # Get search results using Web API
    search_results = []
    
    # Try multiple search services
    try:
        # 1. Try DuckDuckGo
        search_results.extend(search_duckduckgo(topic))
    except Exception as e:
        print(f"DuckDuckGo search failed: {e}")
    
    try:
        # 2. Try Google Search
        search_results.extend(search_google(topic))
    except Exception as e:
        print(f"Google search failed: {e}")
    
    # If all searches failed, return a message
    if not search_results:
        return f"I couldn't find any search results for '{topic}'. Please try a different query or check your internet connection."
    
    # Deduplicate results
    unique_results = []
    seen_urls = set()
    for result in search_results:
        if result.get('url') not in seen_urls:
            unique_results.append(result)
            seen_urls.add(result.get('url'))
    
    # Limit to the top search results
    top_results = unique_results[:MAX_NEWS_RESULTS]
    
    # Format the search results as a prompt for the LLM
    prompt = f"""
You are a helpful web search assistant. Below are search results for the query: "{topic}"

SEARCH RESULTS:
"""
    
    for i, result in enumerate(top_results, 1):
        title = result.get('title', 'No title')
        snippet = result.get('snippet', 'No description available')
        url = result.get('url', 'No URL available')
        prompt += f"{i}. {title}\n   {snippet}\n   Source: {url}\n\n"
    
    prompt += f"""
Based on these search results, provide a comprehensive and informative response to the query: "{topic}"

Your response should:
1. Summarize the key information from multiple sources
2. Highlight any consensus or disagreements among sources
3. Cite sources using [1], [2], etc. based on the numbering above
4. Be factual, accurate, and balanced
5. Be well-organized and easy to read

Your response:
"""
    
    # Initialize the Ollama model
    from app import setup_ollama
    model = setup_ollama(temperature=temperature, top_p=top_p, max_tokens=max_tokens)
    
    # Generate the response
    if streaming and callback:
        # Use async with streaming
        import asyncio
        
        async def generate_streaming():
            # Create a messages array with the system instruction, conversation history, and current query
            messages = [
                {"role": "system", "content": "You are a helpful web search assistant that provides comprehensive, accurate, and balanced information based on search results."}
            ]
            
            # Add conversation history if provided
            if conversation_history:
                messages.extend(conversation_history)
            
            # Add current user query
            messages.append({"role": "user", "content": prompt})
            
            result = await model.complete_async(
                prompt,
                messages=messages,
                streaming=True,
                callback=callback,
                temperature=temperature,
                top_p=top_p,
                max_tokens=max_tokens
            )
            return result
        
        # Run the async function and return the result
        return asyncio.run(generate_streaming())
    else:
        # Generate the response without streaming
        # Create messages with system instruction, conversation history, and the current prompt
        messages = [
            {"role": "system", "content": "You are a helpful web search assistant that provides comprehensive, accurate, and balanced information based on search results."}
        ]
        
        # Add conversation history if provided
        if conversation_history:
            messages.extend(conversation_history)
        
        # Add current user query
        messages.append({"role": "user", "content": prompt})
        
        return model.complete(
            prompt,
            messages=messages,
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens
        )

def search_duckduckgo(query):
    """
    Search DuckDuckGo for the given query.
    
    Args:
        query (str): The query to search for
        
    Returns:
        list: List of search result objects
    """
    try:
        url = f"https://api.duckduckgo.com/?q={urllib.parse.quote(query)}&format=json"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))
            
            results = []
            
            # Process topics if available
            if 'RelatedTopics' in data:
                for topic in data['RelatedTopics']:
                    if 'Text' in topic and 'FirstURL' in topic:
                        results.append({
                            'title': topic.get('Text', '').split(' - ')[0],
                            'snippet': topic.get('Text', ''),
                            'url': topic.get('FirstURL', '')
                        })
            
            return results
    except Exception as e:
        print(f"Error searching DuckDuckGo: {e}")
        return []

def search_google(query):
    """
    Search Google for the given query.
    
    Args:
        query (str): The query to search for
        
    Returns:
        list: List of search result objects
    """
    try:
        # Use a similar approach to Google News but for general search
        url = f"https://www.google.com/search?q={urllib.parse.quote(query)}&hl=en-US&gl=US"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as response:
            html = response.read().decode('utf-8')
            
            # Extract search results using regex
            results = []
            
            # Find search result divs
            search_divs = re.findall(r'<div class="g">(.*?)</div>\s*</div>\s*</div>', html, re.DOTALL)
            
            for div in search_divs:
                # Extract title
                title_match = re.search(r'<h3[^>]*>(.*?)</h3>', div, re.DOTALL)
                title = title_match.group(1) if title_match else "No title"
                title = re.sub(r'<[^>]*>', '', title)  # Remove HTML tags
                
                # Extract URL
                url_match = re.search(r'<a href="([^"]*)"', div)
                url = url_match.group(1) if url_match else ""
                
                # Extract snippet
                snippet_match = re.search(r'<div class="VwiC3b [^"]*"[^>]*>(.*?)</div>', div, re.DOTALL)
                snippet = snippet_match.group(1) if snippet_match else "No description available"
                snippet = re.sub(r'<[^>]*>', '', snippet)  # Remove HTML tags
                
                if title and url:
                    results.append({
                        'title': title,
                        'snippet': snippet,
                        'url': url
                    })
            
            return results
    except Exception as e:
        print(f"Error searching Google: {e}")
        return []

if __name__ == "__main__":
    # Check Ollama status
    if not check_ollama_status():
        print("Warning: Ollama may not be running. Please start it with 'ollama serve'")
        sys.exit(1)
    
    # List available models
    models = list_ollama_models()
    model_names = [m.get('name') for m in models]
    
    # Use model from environment variable or fallback to default
    model_name = OLLAMA_MODEL
    if model_names and model_name not in model_names:
        print(f"Warning: Model '{model_name}' not found. Available models: {model_names}")
        if model_names:
            model_name = model_names[0]
            print(f"Using model: {model_name}")
    
    # Create the model and agent
    model = OpenAIChatCompletionsModel(
        model=model_name,
        openai_client=OpenAIClient(base_url=OLLAMA_BASE_URL)
    )
    
    # Create two agents - a news agent and an editor agent
    news_agent = Agent(
        name="News Assistant",
        instructions="You are a helpful assistant that can search for news articles.",
        model=model,
        tools=[get_news_articles]
    )
    
    editor_agent = Agent(
        name="Editor",
        instructions="You are an expert editor who can summarize news articles in a concise, informative way. Focus on facts and eliminate any speculation or bias.",
        model=model
    )
    
    # Get topic from command line or use default from environment
    default_topic = os.environ.get("DEFAULT_NEWS_TOPIC", "artificial intelligence")
    topic = sys.argv[1] if len(sys.argv) > 1 else default_topic
    
    # Run the workflow
    print(f"Searching for news about: {topic}")
    news = get_news_articles(topic)
    print("\nNews results:")
    print(news)
    
    # Run the agent to summarize the news
    print("\nGenerating summary...")
    result = Runner.run_sync(editor_agent, f"Summarize these news articles about {topic}:\n\n{news}")
    print("\nSummary:")
    print(result.final_output)