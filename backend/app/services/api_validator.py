"""API Key Validation Service - Tests if API keys actually work."""

import os
from typing import Tuple


def validate_groq_key(api_key: str) -> Tuple[bool, str]:
    """
    Validate Groq API key by making a test request.
    
    Returns:
        (is_valid, message)
    """
    try:
        from groq import Groq
        
        # Set the API key temporarily
        client = Groq(api_key=api_key)
        
        # Make a minimal test request
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": "Say 'OK'"}],
            max_tokens=5
        )
        
        if response and response.choices:
            return True, "✅ Groq API key is valid and working!"
        else:
            return False, "❌ Groq API returned unexpected response"
            
    except Exception as e:
        error_msg = str(e)
        if "401" in error_msg or "authentication" in error_msg.lower():
            return False, "❌ Invalid Groq API key - authentication failed"
        elif "rate limit" in error_msg.lower():
            return False, "⚠️ Rate limit exceeded - but key is valid"
        else:
            return False, f"❌ Groq API error: {error_msg[:100]}"


def validate_openai_key(api_key: str) -> Tuple[bool, str]:
    """
    Validate OpenAI API key by making a test request.
    
    Returns:
        (is_valid, message)
    """
    try:
        from openai import OpenAI
        
        client = OpenAI(api_key=api_key)
        
        # Make a minimal test request
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Say OK"}],
            max_tokens=5
        )
        
        if response and response.choices:
            return True, "✅ OpenAI API key is valid and working!"
        else:
            return False, "❌ OpenAI API returned unexpected response"
            
    except Exception as e:
        error_msg = str(e)
        if "401" in error_msg or "authentication" in error_msg.lower() or "invalid" in error_msg.lower():
            return False, "❌ Invalid OpenAI API key - authentication failed"
        elif "rate limit" in error_msg.lower():
            return False, "⚠️ Rate limit exceeded - but key is valid"
        elif "quota" in error_msg.lower():
            return False, "⚠️ Quota exceeded - but key is valid"
        else:
            return False, f"❌ OpenAI API error: {error_msg[:100]}"


def validate_google_key(api_key: str) -> Tuple[bool, str]:
    """
    Validate Google Gemini API key by making a test request.
    
    Returns:
        (is_valid, message)
    """
    try:
        import google.generativeai as genai
        
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Make a minimal test request
        response = model.generate_content("Say OK")
        
        if response and response.text:
            return True, "✅ Google Gemini API key is valid and working!"
        else:
            return False, "❌ Google API returned unexpected response"
            
    except Exception as e:
        error_msg = str(e)
        if "API key not valid" in error_msg or "401" in error_msg or "403" in error_msg:
            return False, "❌ Invalid Google API key - authentication failed"
        elif "quota" in error_msg.lower() or "rate limit" in error_msg.lower():
            return False, "⚠️ Quota/rate limit - but key is valid"
        else:
            return False, f"❌ Google API error: {error_msg[:100]}"


def validate_replicate_key(api_key: str) -> Tuple[bool, str]:
    """
    Validate Replicate API key.
    
    Returns:
        (is_valid, message)
    """
    import requests

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
    }

    try:
        response = requests.get("https://api.replicate.com/v1/account", headers=headers, timeout=10)
    except Exception as exc:
        return False, f"❌ Replicate network error: {exc}"

    if response.status_code == 200:
        data = response.json() if response.headers.get("Content-Type", "").startswith("application/json") else {}
        return True, f"✅ Replicate key valid — plan: {data.get('account', {}).get('type', 'unknown')}"

    if response.status_code == 401:
        return False, "❌ Invalid Replicate API key (authentication failed)"
    if response.status_code == 402:
        return False, "⚠️ Replicate account has insufficient credit. Add balance to continue."
    if response.status_code == 429:
        return False, "⚠️ Replicate rate limit hit. Try again later or upgrade your plan."

    try:
        detail = response.json().get("detail")
    except Exception:
        detail = response.text[:120]
    return False, f"❌ Replicate error ({response.status_code}): {detail}"


def validate_together_key(api_key: str) -> Tuple[bool, str]:
    """
    Validate Together AI API key.
    
    Returns:
        (is_valid, message)
    """
    try:
        from together import Together
        
        client = Together(api_key=api_key)
        
        # Try to list models
        models = client.models.list()
        
        if models:
            return True, "✅ Together AI API key is valid and working!"
        else:
            return False, "❌ Together AI returned unexpected response"
            
    except Exception as e:
        error_msg = str(e)
        if "401" in error_msg or "authentication" in error_msg.lower():
            return False, "❌ Invalid Together AI API key"
        else:
            return False, f"❌ Together AI error: {error_msg[:100]}"


def validate_fal_key(api_key: str) -> Tuple[bool, str]:
    """
    Validate FAL AI API key.
    
    Returns:
        (is_valid, message)
    """
    try:
        import fal_client
        
        # Set the API key
        os.environ['FAL_KEY'] = api_key
        
        # FAL doesn't have a simple validation endpoint
        # We just check the key format
        if api_key and len(api_key) > 10:
            return True, "✅ FAL AI API key format is valid!"
        else:
            return False, "❌ Invalid FAL AI API key format"
            
    except Exception as e:
        return False, f"❌ FAL AI error: {str(e)[:100]}"


def validate_runware_key(api_key: str) -> Tuple[bool, str]:
    """
    Validate Runware API key.
    
    Returns:
        (is_valid, message)
    """
    try:
        # Runware uses bearer token authentication
        # We can validate by checking the format
        if api_key and len(api_key) > 10:
            return True, "✅ Runware API key format is valid!"
        else:
            return False, "❌ Invalid Runware API key format"
            
    except Exception as e:
        return False, f"❌ Runware error: {str(e)[:100]}"


def validate_elevenlabs_key(api_key: str) -> Tuple[bool, str]:
    """
    Validate ElevenLabs API key.
    
    Returns:
        (is_valid, message)
    """
    try:
        from elevenlabs.client import ElevenLabs
        
        client = ElevenLabs(api_key=api_key)
        
        # Try to get user info or voices
        voices = client.voices.get_all()
        
        if voices:
            return True, f"✅ ElevenLabs API key is valid! ({len(voices.voices)} voices available)"
        else:
            return False, "❌ ElevenLabs returned unexpected response"
            
    except Exception as e:
        error_msg = str(e)
        if "401" in error_msg or "unauthorized" in error_msg.lower():
            return False, "❌ Invalid ElevenLabs API key"
        elif "quota" in error_msg.lower():
            return False, "⚠️ Quota exceeded - but key is valid"
        else:
            return False, f"❌ ElevenLabs error: {error_msg[:100]}"


def validate_fish_audio_key(api_key: str) -> Tuple[bool, str]:
    """
    Validate Fish Audio API key.
    
    Returns:
        (is_valid, message)
    """
    try:
        # Fish Audio SDK validation
        if api_key and len(api_key) > 10:
            return True, "✅ Fish Audio API key format is valid!"
        else:
            return False, "❌ Invalid Fish Audio API key format"
            
    except Exception as e:
        return False, f"❌ Fish Audio error: {str(e)[:100]}"


def validate_api_key(service_name: str, api_key: str) -> Tuple[bool, str]:
    """
    Validate an API key for any service.
    
    Args:
        service_name: Name of the service (groq, openai, google, etc.)
        api_key: The API key to validate
        
    Returns:
        (is_valid, message)
    """
    validators = {
        'groq': validate_groq_key,
        'openai': validate_openai_key,
        'google': validate_google_key,
        'replicate': validate_replicate_key,
        'together': validate_together_key,
        'fal': validate_fal_key,
        'runware': validate_runware_key,
        'elevenlabs': validate_elevenlabs_key,
        'fish_audio': validate_fish_audio_key,
    }
    
    validator = validators.get(service_name.lower())
    
    if not validator:
        return False, f"❌ Unknown service: {service_name}"
    
    print(f"🔍 Validating {service_name} API key...")
    is_valid, message = validator(api_key)
    print(f"{'✅' if is_valid else '❌'} {service_name}: {message}")
    
    return is_valid, message

