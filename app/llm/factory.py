from abc import ABC, abstractmethod
import openai
from anthropic import Anthropic
from typing import Dict, Any, List, Optional
from flask import current_app
import time
from app.models import LLMProvider, TokenUsage, RequestStatus
from app import db

class LLMResponse:
    def __init__(self, content: str, tokens_used: Dict[str, int] = None, 
                 model: str = None, cost: float = 0.0):
        self.content = content
        self.tokens_used = tokens_used or {}
        self.model = model
        self.cost = cost

class BaseLLMProvider(ABC):
    def __init__(self, api_key: str = None):
        self.api_key = api_key
    
    @abstractmethod
    def generate_response(self, messages: List[Dict[str, str]], 
                         model: str = None, **kwargs) -> LLMResponse:
        pass
    
    @abstractmethod
    def get_available_models(self) -> List[str]:
        pass
    
    @abstractmethod
    def calculate_cost(self, tokens: Dict[str, int], model: str) -> float:
        pass

class OpenAIProvider(BaseLLMProvider):
    def __init__(self, api_key: str = None):
        super().__init__(api_key)
        openai.api_key = api_key or current_app.config.get('OPENAI_API_KEY')
        self.client = openai.OpenAI(api_key=self.api_key)
    
    def generate_response(self, messages: List[Dict[str, str]], 
                         model: str = "gpt-4", **kwargs) -> LLMResponse:
        try:
            start_time = time.time()
            
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=kwargs.get('temperature', 0.7),
                max_tokens=kwargs.get('max_tokens', 4000),
                top_p=kwargs.get('top_p', 1.0),
                frequency_penalty=kwargs.get('frequency_penalty', 0),
                presence_penalty=kwargs.get('presence_penalty', 0)
            )
            
            end_time = time.time()
            response_time_ms = int((end_time - start_time) * 1000)
            
            tokens_used = {
                'prompt_tokens': response.usage.prompt_tokens,
                'completion_tokens': response.usage.completion_tokens,
                'total_tokens': response.usage.total_tokens
            }
            
            cost = self.calculate_cost(tokens_used, model)
            
            # Track usage if enabled
            if current_app.config.get('COST_TRACKING_ENABLED'):
                self._track_usage(tokens_used, model, cost, response_time_ms, **kwargs)
            
            return LLMResponse(
                content=response.choices[0].message.content,
                tokens_used=tokens_used,
                model=model,
                cost=cost
            )
            
        except Exception as e:
            current_app.logger.error(f"OpenAI API error: {str(e)}")
            raise
    
    def get_available_models(self) -> List[str]:
        return ["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo", "gpt-3.5-turbo-16k"]
    
    def calculate_cost(self, tokens: Dict[str, int], model: str) -> float:
        # Pricing as of 2024 (you should update these regularly)
        pricing = {
            "gpt-4": {"prompt": 0.03, "completion": 0.06},
            "gpt-4-turbo": {"prompt": 0.01, "completion": 0.03},
            "gpt-3.5-turbo": {"prompt": 0.0015, "completion": 0.002},
            "gpt-3.5-turbo-16k": {"prompt": 0.003, "completion": 0.004}
        }
        
        if model not in pricing:
            return 0.0
        
        prompt_cost = (tokens.get('prompt_tokens', 0) / 1000) * pricing[model]['prompt']
        completion_cost = (tokens.get('completion_tokens', 0) / 1000) * pricing[model]['completion']
        
        return prompt_cost + completion_cost
    
    def _track_usage(self, tokens: Dict[str, int], model: str, cost: float, 
                    response_time_ms: int, **kwargs):
        # Implementation for tracking usage in database
        pass

class AzureOpenAIProvider(BaseLLMProvider):
    def __init__(self, api_key: str = None, endpoint: str = None):
        super().__init__(api_key)
        self.endpoint = endpoint or current_app.config.get('AZURE_OPENAI_ENDPOINT')
        self.client = openai.AzureOpenAI(
            api_key=api_key or current_app.config.get('AZURE_OPENAI_API_KEY'),
            azure_endpoint=self.endpoint,
            api_version="2024-02-15-preview"
        )
    
    def generate_response(self, messages: List[Dict[str, str]], 
                         model: str = "gpt-4", **kwargs) -> LLMResponse:
        try:
            start_time = time.time()
            
            response = self.client.chat.completions.create(
                model=model,  # This should be your Azure deployment name
                messages=messages,
                temperature=kwargs.get('temperature', 0.7),
                max_tokens=kwargs.get('max_tokens', 4000),
                top_p=kwargs.get('top_p', 1.0),
                frequency_penalty=kwargs.get('frequency_penalty', 0),
                presence_penalty=kwargs.get('presence_penalty', 0)
            )
            
            end_time = time.time()
            response_time_ms = int((end_time - start_time) * 1000)
            
            tokens_used = {
                'prompt_tokens': response.usage.prompt_tokens,
                'completion_tokens': response.usage.completion_tokens,
                'total_tokens': response.usage.total_tokens
            }
            
            cost = self.calculate_cost(tokens_used, model)
            
            return LLMResponse(
                content=response.choices[0].message.content,
                tokens_used=tokens_used,
                model=model,
                cost=cost
            )
            
        except Exception as e:
            current_app.logger.error(f"Azure OpenAI API error: {str(e)}")
            raise
    
    def get_available_models(self) -> List[str]:
        return ["gpt-4", "gpt-4-turbo", "gpt-35-turbo", "gpt-35-turbo-16k"]
    
    def calculate_cost(self, tokens: Dict[str, int], model: str) -> float:
        # Azure OpenAI pricing (similar to OpenAI but may vary)
        pricing = {
            "gpt-4": {"prompt": 0.03, "completion": 0.06},
            "gpt-4-turbo": {"prompt": 0.01, "completion": 0.03},
            "gpt-35-turbo": {"prompt": 0.0015, "completion": 0.002},
            "gpt-35-turbo-16k": {"prompt": 0.003, "completion": 0.004}
        }
        
        if model not in pricing:
            return 0.0
        
        prompt_cost = (tokens.get('prompt_tokens', 0) / 1000) * pricing[model]['prompt']
        completion_cost = (tokens.get('completion_tokens', 0) / 1000) * pricing[model]['completion']
        
        return prompt_cost + completion_cost

class AnthropicProvider(BaseLLMProvider):
    def __init__(self, api_key: str = None):
        super().__init__(api_key)
        self.client = Anthropic(api_key=api_key or current_app.config.get('ANTHROPIC_API_KEY'))
    
    def generate_response(self, messages: List[Dict[str, str]], 
                         model: str = "claude-3-sonnet-20240229", **kwargs) -> LLMResponse:
        try:
            start_time = time.time()
            
            # Convert OpenAI format messages to Anthropic format
            system_message = None
            converted_messages = []
            
            for msg in messages:
                if msg['role'] == 'system':
                    system_message = msg['content']
                else:
                    converted_messages.append({
                        'role': msg['role'],
                        'content': msg['content']
                    })
            
            response = self.client.messages.create(
                model=model,
                max_tokens=kwargs.get('max_tokens', 4000),
                temperature=kwargs.get('temperature', 0.7),
                system=system_message,
                messages=converted_messages
            )
            
            end_time = time.time()
            response_time_ms = int((end_time - start_time) * 1000)
            
            tokens_used = {
                'prompt_tokens': response.usage.input_tokens,
                'completion_tokens': response.usage.output_tokens,
                'total_tokens': response.usage.input_tokens + response.usage.output_tokens
            }
            
            cost = self.calculate_cost(tokens_used, model)
            
            return LLMResponse(
                content=response.content[0].text,
                tokens_used=tokens_used,
                model=model,
                cost=cost
            )
            
        except Exception as e:
            current_app.logger.error(f"Anthropic API error: {str(e)}")
            raise
    
    def get_available_models(self) -> List[str]:
        return [
            "claude-3-opus-20240229",
            "claude-3-sonnet-20240229", 
            "claude-3-haiku-20240307",
            "claude-2.1",
            "claude-2.0"
        ]
    
    def calculate_cost(self, tokens: Dict[str, int], model: str) -> float:
        # Anthropic pricing (as of 2024)
        pricing = {
            "claude-3-opus-20240229": {"prompt": 0.015, "completion": 0.075},
            "claude-3-sonnet-20240229": {"prompt": 0.003, "completion": 0.015},
            "claude-3-haiku-20240307": {"prompt": 0.00025, "completion": 0.00125},
            "claude-2.1": {"prompt": 0.008, "completion": 0.024},
            "claude-2.0": {"prompt": 0.008, "completion": 0.024}
        }
        
        if model not in pricing:
            return 0.0
        
        prompt_cost = (tokens.get('prompt_tokens', 0) / 1000) * pricing[model]['prompt']
        completion_cost = (tokens.get('completion_tokens', 0) / 1000) * pricing[model]['completion']
        
        return prompt_cost + completion_cost

class LLMFactory:
    _providers = {
        LLMProvider.OPENAI: OpenAIProvider,
        LLMProvider.AZURE_OPENAI: AzureOpenAIProvider,
        LLMProvider.ANTHROPIC: AnthropicProvider
    }
    
    @classmethod
    def create_provider(cls, provider_type: LLMProvider, **kwargs) -> BaseLLMProvider:
        if provider_type not in cls._providers:
            raise ValueError(f"Unsupported LLM provider: {provider_type}")
        
        provider_class = cls._providers[provider_type]
        return provider_class(**kwargs)
    
    @classmethod
    def get_default_provider(cls) -> BaseLLMProvider:
        default_provider = current_app.config.get('DEFAULT_LLM_PROVIDER', 'openai')
        provider_enum = LLMProvider(default_provider)
        return cls.create_provider(provider_enum)
    
    @classmethod
    def get_available_providers(cls) -> List[str]:
        return [provider.value for provider in LLMProvider]

# Singleton pattern for LLM manager
class LLMManager:
    _instance = None
    _current_provider = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LLMManager, cls).__new__(cls)
        return cls._instance
    
    def set_provider(self, provider_type: LLMProvider, **kwargs):
        self._current_provider = LLMFactory.create_provider(provider_type, **kwargs)
    
    def get_provider(self) -> BaseLLMProvider:
        if self._current_provider is None:
            self._current_provider = LLMFactory.get_default_provider()
        return self._current_provider
    
    def generate_response(self, messages: List[Dict[str, str]], **kwargs) -> LLMResponse:
        provider = self.get_provider()
        return provider.generate_response(messages, **kwargs) 