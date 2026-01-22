"""
Web Search Client - Searches the web for verification evidence
Supports Tavily (free tier: 1,000 searches/month) with DuckDuckGo fallback
"""
import time
from typing import List, Dict, Any, Optional
from datetime import datetime
from .config import config


class WebSearchClient:
    """
    Web search client with multiple providers:
    - Tavily (primary): Free tier with 1,000 searches/month, no rate limits
    - DuckDuckGo (fallback): Free but has rate limits
    """
    
    # Class-level rate limiter for DuckDuckGo
    _last_ddg_search_time = 0
    _min_ddg_delay = 2.5  # Minimum seconds between DuckDuckGo searches
    
    def __init__(self, max_results: int = 5, provider: Optional[str] = None):
        self.max_results = max_results
        self.provider = provider or config.search_provider.lower()
        self._tavily_client = None
        self._ddg = None
        self._initialized = False
        self._use_tavily = False
        
        # Try to initialize Tavily first if API key is available
        if config.tavily_api_key:
            try:
                from tavily import TavilyClient
                self._tavily_client = TavilyClient(api_key=config.tavily_api_key)
                self._use_tavily = True
                if not self._initialized:
                    print("✓ Web search ready (Tavily - Free tier: 1,000 searches/month)")
                    self._initialized = True
            except ImportError:
                print("⚠ Tavily not installed, falling back to DuckDuckGo")
                print("   Install with: pip install tavily-python")
            except Exception as e:
                print(f"⚠ Tavily initialization failed: {e}, falling back to DuckDuckGo")
        
        # Fallback to DuckDuckGo if Tavily not available
        if not self._use_tavily:
            if not self._initialized:
                print("✓ Web search ready (DuckDuckGo - Free, but has rate limits)")
                self._initialized = True
    
    def _get_tavily_client(self):
        """Initialize Tavily client"""
        if self._tavily_client is None and config.tavily_api_key:
            try:
                from tavily import TavilyClient
                self._tavily_client = TavilyClient(api_key=config.tavily_api_key)
            except ImportError:
                raise ImportError(
                    "tavily-python package not installed.\n"
                    "Run: pip install tavily-python\n"
                    "Get free API key at: https://tavily.com"
                )
            except Exception as e:
                raise Exception(f"Tavily initialization failed: {e}")
        return self._tavily_client
    
    def _get_ddg_client(self):
        """Initialize DuckDuckGo client"""
        if self._ddg is None:
            try:
                from duckduckgo_search import DDGS
                self._ddg = DDGS()
            except ImportError:
                raise ImportError(
                    "duckduckgo-search package not installed.\n"
                    "Run: pip install duckduckgo-search"
                )
        return self._ddg
    
    def search(self, query: str, retry_count: int = 2) -> List[Dict[str, Any]]:
        """
        Search the web for a query.
        Uses Tavily if available, otherwise falls back to DuckDuckGo.
        
        Args:
            query: Search query string
            retry_count: Number of retries on failure
            
        Returns:
            List of search results with url, title, snippet, source
        """
        # Try Tavily first if available
        if self._use_tavily and config.tavily_api_key:
            try:
                return self._search_tavily(query)
            except Exception as e:
                print(f"   ⚠ Tavily search failed: {str(e)[:100]}, trying DuckDuckGo...")
                self._use_tavily = False  # Disable Tavily for this session
        
        # Fallback to DuckDuckGo
        return self._search_duckduckgo(query, retry_count)
    
    def _search_tavily(self, query: str) -> List[Dict[str, Any]]:
        """Search using Tavily API"""
        client = self._get_tavily_client()
        
        try:
            response = client.search(
                query=query,
                max_results=self.max_results,
                search_depth="basic"  # Use "basic" for free tier
            )
            
            processed_results = []
            for result in response.get('results', []):
                processed_results.append({
                    'url': result.get('url', ''),
                    'title': result.get('title', ''),
                    'snippet': result.get('content', ''),
                    'source': self._extract_source(result.get('url', '')),
                    'timestamp': datetime.now().isoformat()
                })
            
            return processed_results
            
        except Exception as e:
            error_str = str(e).lower()
            if 'quota' in error_str or 'limit' in error_str:
                print(f"   ⚠ Tavily quota exceeded, falling back to DuckDuckGo")
                self._use_tavily = False
            raise
    
    def _search_duckduckgo(self, query: str, retry_count: int = 3) -> List[Dict[str, Any]]:
        """Search using DuckDuckGo with rate limiting"""
        for attempt in range(retry_count + 1):
            try:
                # Rate limiting: ensure minimum delay since last search
                current_time = time.time()
                time_since_last = current_time - WebSearchClient._last_ddg_search_time
                if time_since_last < WebSearchClient._min_ddg_delay:
                    wait_needed = WebSearchClient._min_ddg_delay - time_since_last
                    time.sleep(wait_needed)
                
                # Additional delay for retries
                if attempt > 0:
                    time.sleep(3.0)  # Extra 3 seconds between retries
                
                ddg = self._get_ddg_client()
                results = list(ddg.text(query, max_results=self.max_results))
                
                processed_results = []
                for result in results:
                    processed_results.append({
                        'url': result.get('href', ''),
                        'title': result.get('title', ''),
                        'snippet': result.get('body', ''),
                        'source': self._extract_source(result.get('href', '')),
                        'timestamp': datetime.now().isoformat()
                    })
                
                # Update last search time
                WebSearchClient._last_ddg_search_time = time.time()
                
                # Small delay after successful search to be respectful
                time.sleep(0.5)
                return processed_results
                
            except Exception as e:
                error_str = str(e).lower()
                if ('ratelimit' in error_str or 'rate limit' in error_str or '429' in error_str) and attempt < retry_count:
                    wait_time = (attempt + 1) * 5  # Longer exponential backoff: 5s, 10s, 15s
                    print(f"   ⏳ Rate limited, waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                    self._ddg = None  # Reset client to get fresh connection
                elif 'timeout' in error_str or 'connection' in error_str:
                    wait_time = (attempt + 1) * 3
                    print(f"   ⏳ Connection issue, waiting {wait_time}s...")
                    time.sleep(wait_time)
                    self._ddg = None
                else:
                    if attempt == retry_count:
                        print(f"   ⚠ Search failed after {retry_count} retries: {str(e)[:100]}")
                    return []
        
        return []
    
    def _extract_source(self, url: str) -> str:
        """Extract source name from URL"""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            # Remove www. prefix
            if domain.startswith('www.'):
                domain = domain[4:]
            return domain
        except Exception:
            return url
    
    def search_news(self, query: str, days: int = 30) -> List[Dict[str, Any]]:
        """Search recent news articles (DuckDuckGo only for now)"""
        try:
            ddg = self._get_ddg_client()
            results = list(ddg.news(query, max_results=self.max_results))
            
            processed_results = []
            for result in results:
                processed_results.append({
                    'url': result.get('url', ''),
                    'title': result.get('title', ''),
                    'snippet': result.get('body', ''),
                    'source': result.get('source', ''),
                    'date': result.get('date', ''),
                    'timestamp': datetime.now().isoformat()
                })
            
            return processed_results
            
        except Exception as e:
            print(f"⚠ News search error: {e}")
            return []
