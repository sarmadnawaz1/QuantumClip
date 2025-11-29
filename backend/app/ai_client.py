"""AI Client for interacting with various LLM providers - based on desktop app."""

import os
from typing import Optional, List, Dict, Any
from app.utils import load_config
from app.core.config import settings


class ChatCompletion:
    """Chat completion response wrapper."""
    def __init__(self, content: str):
        self.choices = [type('obj', (object,), {
            'message': type('obj', (object,), {
                'content': content
            })()
        })()]


def has_api_key(provider: str) -> bool:
    """
    Check if a provider has an API key configured.
    
    Args:
        provider: Provider name (groq, openai, gemini)
        
    Returns:
        True if API key is available, False otherwise
    """
    provider_lower = provider.lower()
    if provider_lower == 'groq':
        return bool(settings.groq_api_key or os.environ.get("GROQ_API_KEY"))
    elif provider_lower == 'openai':
        return bool(settings.openai_api_key or os.environ.get("OPENAI_API_KEY"))
    elif provider_lower == 'gemini':
        return bool(settings.google_api_key or os.environ.get("GOOGLE_API_KEY"))
    return False


def chat_completion_with_fallback(
    messages: List[Dict[str, str]],
    model: Optional[str] = None,
    temperature: float = 0.9,
    preferred_provider: Optional[str] = None
) -> ChatCompletion:
    """
    Generate chat completion trying multiple providers in order.
    Tries: preferred_provider → Groq → OpenAI → Gemini
    
    Args:
        messages: List of message dicts with 'role' and 'content'
        model: Optional model override
        temperature: Temperature for generation
        preferred_provider: Preferred provider to try first (groq, openai, gemini)
        
    Returns:
        ChatCompletion object with response
        
    Raises:
        Exception: If all providers fail
    """
    # Build list of providers to try in order
    providers_to_try = []
    
    # Add preferred provider first if specified and has API key
    if preferred_provider:
        preferred_provider = preferred_provider.lower()
        if has_api_key(preferred_provider):
            providers_to_try.append(preferred_provider)
    
    # Add other providers in order (skip if already added)
    for provider in ['groq', 'openai', 'gemini']:
        if provider not in providers_to_try and has_api_key(provider):
            providers_to_try.append(provider)
    
    if not providers_to_try:
        raise Exception("No AI provider configured. Please configure at least one of: Groq, OpenAI, or Gemini API keys.")
    
    # Try each provider until one succeeds
    last_error = None
    for provider in providers_to_try:
        try:
            print(f"🤖 [AI CLIENT] Trying {provider}...")
            return chat_completion(
                messages=messages,
                model=model,
                temperature=temperature,
                provider=provider
            )
        except Exception as e:
            last_error = e
            print(f"❌ [AI CLIENT] {provider} failed: {e}")
            continue
    
    # If all providers failed, raise the last error
    raise Exception(f"All AI providers failed. Last error ({providers_to_try[-1]}): {str(last_error)}")


def chat_completion(
    messages: List[Dict[str, str]],
    model: Optional[str] = None,
    temperature: float = 0.9,
    provider: Optional[str] = None
) -> ChatCompletion:
    """
    Generate chat completion using the specified AI provider.
    Checks for API key availability before attempting to use the provider.
    
    Args:
        messages: List of message dicts with 'role' and 'content'
        model: Optional model override
        temperature: Temperature for generation
        provider: Provider to use (groq, openai, gemini). If not specified, uses default from config.
        
    Returns:
        ChatCompletion object with response
        
    Raises:
        Exception: If the specified provider's API key is not configured
    """
    config = load_config()
    
    # Determine provider
    if not provider:
        provider = config.get('default_ai_provider', 'Groq').lower()
    else:
        provider = provider.lower()
    
    # Check if the selected provider has an API key
    if not has_api_key(provider):
        raise Exception(f"{provider.upper()} API key not configured. Please add the API key in Settings.")
    
    # Use the specified provider
    if provider == 'groq':
        return _groq_completion(messages, model, temperature)
    elif provider == 'openai':
        return _openai_completion(messages, model, temperature)
    elif provider == 'gemini':
        return _gemini_completion(messages, model, temperature)
    else:
        # Default to Groq if unknown provider
        print(f"⚠️ Unknown provider '{provider}', defaulting to Groq")
        return _groq_completion(messages, model, temperature)


def _groq_completion(messages: List[Dict], model: Optional[str], temperature: float) -> ChatCompletion:
    """Generate completion using Groq."""
    from groq import Groq
    from app.core.config import settings
    
    api_key = settings.groq_api_key or os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise Exception("Groq API key not configured. Please add GROQ_API_KEY to your environment or settings.")
    
    client = Groq(api_key=api_key)
    
    if not model:
        config = load_config()
        model = config.get('groq', {}).get('model', 'llama-3.1-8b-instant')
    
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature
    )
    
    return ChatCompletion(response.choices[0].message.content)


def _openai_completion(messages: List[Dict], model: Optional[str], temperature: float) -> ChatCompletion:
    """Generate completion using OpenAI."""
    from openai import OpenAI
    from app.core.config import settings
    
    api_key = settings.openai_api_key or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise Exception("OpenAI API key not configured. Please add OPENAI_API_KEY to your environment or settings.")
    
    client = OpenAI(api_key=api_key)
    
    if not model:
        config = load_config()
        model = config.get('openai', {}).get('model', 'gpt-3.5-turbo')
    
    response = client.chat.completions.create(
        model=model,
        messages=messages,
            temperature=temperature
        )
        
        return ChatCompletion(response.choices[0].message.content)
        
    except Exception as e:
        print(f"OpenAI error: {e}")
        raise


def _gemini_completion(messages: List[Dict], model: Optional[str], temperature: float) -> ChatCompletion:
    """Generate completion using Google Gemini."""
    try:
        import google.generativeai as genai
        from app.core.config import settings
        
        if not settings.google_api_key:
            raise Exception("Google API key not configured")
        
        genai.configure(api_key=settings.google_api_key)
        
        if not model:
            config = load_config()
            model = config.get('gemini', {}).get('model', 'gemini-1.5-flash')
        
        # Convert messages to Gemini format
        gemini_model = genai.GenerativeModel(model)
        
        # Combine messages into single prompt for Gemini
        prompt = "\n\n".join([f"{msg['role']}: {msg['content']}" for msg in messages])
        
        response = gemini_model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(temperature=temperature)
        )
        
        return ChatCompletion(response.text)
        
    except Exception as e:
        print(f"Gemini error: {e}")
        raise

