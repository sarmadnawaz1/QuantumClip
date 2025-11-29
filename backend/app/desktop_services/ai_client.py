"""AI Client for interfacing with different AI providers.

This module provides a unified interface for OpenAI, Groq, and Google Gemini.
"""

import os
from typing import List, Dict, Optional

# Import AI clients
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

try:
    from groq import Groq
except ImportError:
    Groq = None

try:
    import google.generativeai as genai
except ImportError:
    genai = None


# Current provider (can be changed at runtime)
_current_provider = "groq"  # Default to groq
_current_model = None


def set_provider(provider: str):
    """Set the current AI provider."""
    global _current_provider
    _current_provider = provider.lower()


def set_model(model: str):
    """Set the current model."""
    global _current_model
    _current_model = model


def chat_completion(messages: List[Dict], model: Optional[str] = None, temperature: float = 0.7):
    """
    Send a chat completion request to the current AI provider.
    
    Args:
        messages: List of message dictionaries with 'role' and 'content'
        model: Optional model name override
        temperature: Temperature for generation
        
    Returns:
        Response object with choices[0].message.content
    """
    provider = _current_provider
    model_to_use = model or _current_model
    
    print(f"[AI CLIENT] Using provider: {provider}, model: {model_to_use}")
    
    if provider == "openai":
        return _openai_completion(messages, model_to_use, temperature)
    elif provider == "groq":
        return _groq_completion(messages, model_to_use, temperature)
    elif provider == "gemini":
        return _gemini_completion(messages, model_to_use, temperature)
    else:
        # Fallback to groq
        return _groq_completion(messages, model_to_use, temperature)


def _openai_completion(messages, model, temperature):
    """OpenAI completion."""
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        raise Exception("OPENAI_API_KEY not set")
    
    client = OpenAI(api_key=api_key)
    model = model or "gpt-3.5-turbo"
    
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature
    )
    
    return response


def _groq_completion(messages, model, temperature):
    """Groq completion."""
    api_key = os.getenv("GROQ_API_KEY", "")
    if not api_key:
        raise Exception("GROQ_API_KEY not set")
    
    client = Groq(api_key=api_key)
    model = model or "llama-3.1-8b-instant"
    
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature
    )
    
    return response


def _gemini_completion(messages, model, temperature):
    """Google Gemini completion."""
    api_key = os.getenv("GOOGLE_API_KEY", "")
    if not api_key:
        raise Exception("GOOGLE_API_KEY not set")
    
    genai.configure(api_key=api_key)
    model_name = model or "gemini-1.5-flash"
    model_obj = genai.GenerativeModel(model_name)
    
    # Convert messages to Gemini format (just the user content)
    prompt = "\n".join([m["content"] for m in messages if m["role"] == "user"])
    
    response = model_obj.generate_content(
        prompt,
        generation_config=genai.types.GenerationConfig(temperature=temperature)
    )
    
    # Create a response object similar to OpenAI format
    class GeminiResponse:
        def __init__(self, text):
            self.choices = [type('obj', (object,), {
                'message': type('obj', (object,), {'content': text})()
            })()]
    
    return GeminiResponse(response.text)

