"""
LLM Client - Abstraction layer for different LLM providers
Supports: OpenRouter (Gemini 2.5 Flash), Google Gemini, OpenAI, Anthropic
"""
from typing import Optional, Dict, Any
from .config import config


class LLMClient:
    """
    Unified interface for LLM providers.
    Default: Google Gemini (free tier available)
    """
    
    def __init__(
        self, 
        provider: Optional[str] = None,
        model: Optional[str] = None
    ):
        self.provider = provider or config.llm_provider
        self.model = model or config.llm_model
        self._client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize the appropriate LLM client"""
        
        if self.provider == "openrouter":
            try:
                import requests
                
                if not config.openrouter_api_key:
                    raise ValueError(
                        "OPENROUTER_API_KEY not set in .env file.\n"
                        "Get your API key at: https://openrouter.ai/keys"
                    )
                
                # Store API key and base URL for requests-based implementation
                # Strip whitespace from API key
                self._openrouter_api_key = (config.openrouter_api_key or "").strip()
                if not self._openrouter_api_key:
                    raise ValueError(
                        "OPENROUTER_API_KEY is empty. Please check your .env file.\n"
                        "Get your API key at: https://openrouter.ai/keys"
                    )
                
                # Verify API key format
                if not self._openrouter_api_key.startswith('sk-or-'):
                    print(f"⚠ Warning: OpenRouter API key should typically start with 'sk-or-'")
                    print(f"   Your key starts with: {self._openrouter_api_key[:10]}...")
                
                self._openrouter_base_url = "https://openrouter.ai/api/v1"
                self._client = None  # We'll use requests directly
                
                print(f"✓ Connected to OpenRouter ({self.model})")
                print(f"   API key format: {'✓ Valid' if self._openrouter_api_key.startswith('sk-or-') else '⚠ Check format'}")
                
            except ImportError:
                raise ImportError("requests package not installed. Run: pip install requests")
        
        elif self.provider == "gemini":
            try:
                import google.generativeai as genai
                
                if not config.gemini_api_key:
                    raise ValueError(
                        "GEMINI_API_KEY not set in .env file.\n"
                        "Get your free API key at: https://aistudio.google.com/app/apikey"
                    )
                
                genai.configure(api_key=config.gemini_api_key)
                self._client = genai.GenerativeModel(self.model or 'gemini-1.5-flash')
                print(f"✓ Connected to Gemini ({self.model or 'gemini-1.5-flash'})")
                
            except ImportError:
                raise ImportError(
                    "Google Generative AI package not installed.\n"
                    "Run: pip install google-generativeai"
                )
                
        elif self.provider == "openai":
            try:
                from openai import OpenAI
                
                if not config.openai_api_key:
                    raise ValueError("OPENAI_API_KEY not set in .env file.")
                
                self._client = OpenAI(api_key=config.openai_api_key)
                print(f"✓ Connected to OpenAI ({self.model})")
                
            except ImportError:
                raise ImportError("OpenAI package not installed. Run: pip install openai")
                
        elif self.provider == "anthropic":
            try:
                import anthropic
                
                if not config.anthropic_api_key:
                    raise ValueError("ANTHROPIC_API_KEY not set in .env file.")
                
                self._client = anthropic.Anthropic(api_key=config.anthropic_api_key)
                print(f"✓ Connected to Anthropic ({self.model})")
                
            except ImportError:
                raise ImportError("Anthropic package not installed. Run: pip install anthropic")
        else:
            raise ValueError(f"Unsupported LLM provider: {self.provider}")
    
    def complete(
        self, 
        prompt: str, 
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 2000
    ) -> str:
        """
        Generate a completion from the LLM.
        
        Args:
            prompt: The user prompt
            system_prompt: Optional system prompt
            temperature: Sampling temperature (lower = more deterministic)
            max_tokens: Maximum tokens in response
            
        Returns:
            The LLM's response text
        """
        if self.provider == "openrouter":
            return self._openrouter_complete(prompt, system_prompt, temperature, max_tokens)
        elif self.provider == "gemini":
            return self._gemini_complete(prompt, system_prompt, temperature, max_tokens)
        elif self.provider == "openai":
            return self._openai_complete(prompt, system_prompt, temperature, max_tokens)
        elif self.provider == "anthropic":
            return self._anthropic_complete(prompt, system_prompt, temperature, max_tokens)
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")
    
    def _gemini_complete(
        self, 
        prompt: str, 
        system_prompt: Optional[str],
        temperature: float,
        max_tokens: int
    ) -> str:
        """Google Gemini API completion"""
        # Combine system prompt with user prompt for Gemini
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"
        
        # Configure generation settings
        generation_config = {
            "temperature": temperature,
            "max_output_tokens": max_tokens,
        }
        
        response = self._client.generate_content(
            full_prompt,
            generation_config=generation_config
        )
        
        return response.text
    
    def _openrouter_complete(
        self, 
        prompt: str, 
        system_prompt: Optional[str],
        temperature: float,
        max_tokens: int
    ) -> str:
        """OpenRouter API completion using requests directly"""
        import requests
        import json
        
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": prompt})
        
        # Ensure API key is set
        api_key = getattr(self, '_openrouter_api_key', None) or config.openrouter_api_key
        if not api_key:
            raise ValueError("OpenRouter API key is not set")
        
        api_key = api_key.strip()
        
        # Debug: Check API key format (show first/last few chars only)
        if not api_key.startswith('sk-or-'):
            print(f"⚠ Warning: OpenRouter API key should typically start with 'sk-or-'. Your key starts with: {api_key[:6]}...")
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com",  # Optional, for tracking
        }
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        try:
            response = requests.post(
                f"{self._openrouter_base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=60
            )
            
            # Check response before raising
            if response.status_code == 401:
                error_detail = response.text
                try:
                    error_json = response.json()
                    error_detail = error_json.get('error', {}).get('message', error_detail)
                except:
                    pass
                
                raise ValueError(
                    f"OpenRouter API authentication failed (401 Unauthorized).\n"
                    f"Error details: {error_detail}\n"
                    f"API key format check: {'✓' if api_key.startswith('sk-or-') else '✗ Key should start with sk-or-'}\n"
                    f"API key length: {len(api_key)} characters\n"
                    f"Please verify:\n"
                    f"  1. Your OPENROUTER_API_KEY in .env is correct\n"
                    f"  2. The key hasn't expired or been revoked\n"
                    f"  3. Get a new key at: https://openrouter.ai/keys"
                )
            
            response.raise_for_status()
            result = response.json()
            return result["choices"][0]["message"]["content"]
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                # Already handled above, but catch any edge cases
                raise
            raise
    
    def _openai_complete(
        self, 
        prompt: str, 
        system_prompt: Optional[str],
        temperature: float,
        max_tokens: int
    ) -> str:
        """OpenAI API completion"""
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": prompt})
        
        response = self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        return response.choices[0].message.content
    
    def _anthropic_complete(
        self, 
        prompt: str, 
        system_prompt: Optional[str],
        temperature: float,
        max_tokens: int
    ) -> str:
        """Anthropic Claude API completion"""
        message = self._client.messages.create(
            model=self.model if 'claude' in self.model else "claude-3-opus-20240229",
            max_tokens=max_tokens,
            system=system_prompt or "You are a helpful assistant.",
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=temperature
        )
        
        return message.content[0].text
    
    def complete_with_json(
        self, 
        prompt: str, 
        system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate a completion and parse as JSON.
        """
        import json
        
        # Add JSON instruction to prompt
        json_prompt = f"""{prompt}

IMPORTANT: Return ONLY valid JSON, no other text or markdown formatting."""
        
        response = self.complete(json_prompt, system_prompt, temperature=0.1)
        
        # Clean response
        response = response.strip()
        if response.startswith('```'):
            lines = response.split('\n')
            response = '\n'.join(lines[1:-1] if lines[-1].startswith('```') else lines[1:])
        
        # Find JSON in response
        start = response.find('{')
        end = response.rfind('}') + 1
        if start != -1 and end > start:
            response = response[start:end]
        
        return json.loads(response)
