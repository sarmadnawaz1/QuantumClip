"""Settings and configuration endpoints."""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi.concurrency import run_in_threadpool

import os
import json
import time
import logging
import re

from app.core import get_db, get_current_user
from app.core.security import encrypt_api_key, decrypt_api_key
from app.models.api_key import UserAPIKey
from app.schemas.api_key import APIKeyCreate, APIKeyResponse

router = APIRouter()
logger = logging.getLogger(__name__)

CACHE_TTL_SECONDS = 60 * 60  # 1 hour cache for provider metadata
_TTS_CACHE: Dict[str, Dict[str, Any]] = {
    "edge": {"timestamp": 0, "voices": []},
    "elevenlabs": {"timestamp": 0, "voices": [], "models": [], "api_key": None},
    "fish": {"timestamp": 0, "voices": []},
}


async def _load_user_api_keys(db: AsyncSession, user_id: int) -> Dict[str, UserAPIKey]:
    """Load active user API keys and index them by service name."""
    result = await db.execute(
        select(UserAPIKey).where(
            UserAPIKey.user_id == user_id,
            UserAPIKey.is_active == True  # noqa: E712
        )
    )
    return {key.service_name.lower(): key for key in result.scalars().all()}


def _resolve_api_key(
    service_name: str,
    user_keys: Dict[str, UserAPIKey],
    env_key: Optional[str]
) -> Optional[str]:
    """Resolve API key from environment or stored user keys."""
    if env_key:
        return env_key

    key_record = user_keys.get(service_name.lower())
    if not key_record:
        return None

    try:
        return decrypt_api_key(key_record.encrypted_key)
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.warning("Failed to decrypt %s API key: %s", service_name, exc)
        return None


def _sanitize_filename(value: str) -> str:
    """Sanitize strings for safe filenames."""
    return re.sub(r"[^a-zA-Z0-9._-]+", "_", value)


async def _get_edge_voice_options() -> List[Dict[str, Any]]:
    """Fetch and cache Edge TTS voice metadata."""
    cache = _TTS_CACHE["edge"]
    now = time.time()
    if cache["voices"] and now - cache["timestamp"] < CACHE_TTL_SECONDS:
        return cache["voices"]

    try:
        import edge_tts  # type: ignore

        voices = await edge_tts.list_voices()
        unique: Dict[str, Dict[str, Any]] = {}
        for voice in voices:
            short_name = voice.get("ShortName")
            if not short_name or short_name in unique:
                continue
            locale = voice.get("Locale")
            language_code = (voice.get("Language") or (locale.split("-")[0] if locale else None) or "").lower() or None

            unique[short_name] = {
                "id": short_name,
                "label": voice.get("LocalName") or voice.get("DisplayName") or short_name,
                "description": voice.get("FriendlyName") or voice.get("ShortName"),
                "locale": locale,
                "language_code": language_code,
                "language": language_code,
                "gender": voice.get("Gender"),
                "styles": voice.get("StyleList") or [],
                "preview_url": None,
                "preview_available": True,
                "models": [],
            }

        # Sort voices: English first, then others alphabetically
        voices_list = list(unique.values())
        english_voices = []
        other_voices = []
        
        for voice in voices_list:
            locale = voice.get("locale") or ""
            language_code = voice.get("language_code") or ""
            # Check if it's English (en-US, en-GB, en-AU, etc.)
            if locale.lower().startswith("en-") or language_code == "en":
                english_voices.append(voice)
            else:
                other_voices.append(voice)
        
        # Sort English voices by locale, then label
        english_voices.sort(key=lambda v: (v.get("locale") or "", v.get("label") or v["id"]))
        # Sort other voices by locale, then label
        other_voices.sort(key=lambda v: (v.get("locale") or "", v.get("label") or v["id"]))
        
        # Combine: English first, then others
        cache["voices"] = english_voices + other_voices
        cache["timestamp"] = now
    except Exception as exc:  # pragma: no cover - depends on external service
        logger.warning("Failed to load Edge TTS voices: %s", exc)

    return cache["voices"]


LANGUAGE_NAME_TO_CODE = {
    "english": "en",
    "american english": "en",
    "british english": "en",
    "spanish": "es",
    "spanish (mexican)": "es",
    "mexican spanish": "es",
    "spanish (spain)": "es",
    "french": "fr",
    "french canadian": "fr",
    "german": "de",
    "italian": "it",
    "portuguese": "pt",
    "brazilian portuguese": "pt",
    "portuguese (brazil)": "pt",
    "hindi": "hi",
    "urdu": "ur",
    "arabic": "ar",
    "farsi": "fa",
    "persian": "fa",
    "turkish": "tr",
    "russian": "ru",
    "ukrainian": "uk",
    "polish": "pl",
    "dutch": "nl",
    "swedish": "sv",
    "finnish": "fi",
    "danish": "da",
    "norwegian": "no",
    "czech": "cs",
    "slovak": "sk",
    "romanian": "ro",
    "hungarian": "hu",
    "bulgarian": "bg",
    "greek": "el",
    "hebrew": "he",
    "thai": "th",
    "indonesian": "id",
    "malay": "ms",
    "vietnamese": "vi",
    "chinese": "zh",
    "mandarin": "zh",
    "japanese": "ja",
    "korean": "ko"
}


def _normalize_language_code(raw_value: Optional[str]) -> Optional[str]:
    if not raw_value:
        return None
    value = raw_value.strip().lower()
    if not value:
        return None
    if len(value) == 2 and value.isalpha():
        return value
    if "-" in value or "_" in value:
        return value.split("-")[0].split("_")[0]
    return LANGUAGE_NAME_TO_CODE.get(value)


def _load_elevenlabs_metadata(
    api_key: str,
    fallback_models: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Fetch ElevenLabs voice and model metadata (synchronous)."""
    cache = _TTS_CACHE["elevenlabs"]
    now = time.time()
    if (
        cache["voices"]
        and cache.get("api_key") == api_key
        and now - cache["timestamp"] < CACHE_TTL_SECONDS
    ):
        return cache

    voices_data: List[Dict[str, Any]] = []
    models_data: List[Dict[str, Any]] = []

    try:
        from elevenlabs.client import ElevenLabs  # type: ignore

        client = ElevenLabs(api_key=api_key)

        # Fetch voices via paginated search (covers custom + default voices)
        seen_voice_ids: set[str] = set()
        next_page_token: Optional[str] = None
        while True:
            search_response = client.voices.search(
                page_size=100,
                next_page_token=next_page_token,
                sort="name",
                sort_direction="asc",
                include_total_count=False
            )
            for voice in getattr(search_response, "voices", []):
                voice_id = getattr(voice, "voice_id", None)
                if not voice_id or voice_id in seen_voice_ids:
                    continue
                seen_voice_ids.add(voice_id)

                labels = getattr(voice, "labels", {}) or {}
                samples = getattr(voice, "samples", []) or []
                sample_url = getattr(voice, "preview_url", None)
                if not sample_url:
                    for sample in samples or []:
                        sample_url = getattr(sample, "preview_url", None) or getattr(sample, "sample_url", None)
                        if sample_url:
                            break

                verified_languages = getattr(voice, "verified_languages", None) or []
                language_code = None
                for lang in verified_languages:
                    code = getattr(lang, "language_code", None)
                    if code:
                        language_code = code.lower()
                        break
                if not language_code:
                    language_code = _normalize_language_code(labels.get("language"))
                if not language_code:
                    language_code = _normalize_language_code(getattr(voice, "language", None))
                locale = labels.get("accent") or labels.get("region")

                voices_data.append({
                    "id": voice_id,
                    "label": getattr(voice, "name", None) or voice_id,
                    "description": getattr(voice, "description", None),
                    "language_code": language_code,
                    "language": language_code,
                    "accent": labels.get("accent"),
                    "gender": labels.get("gender"),
                    "category": getattr(voice, "category", None),
                    "preview_url": sample_url,
                    "preview_available": bool(sample_url),
                    "locale": locale,
                    "models": list(getattr(voice, "high_quality_base_model_ids", []) or []),
                })

            next_page_token = getattr(search_response, "next_page_token", None)
            if not next_page_token:
                break

        # Fallback to legacy endpoint if search returned nothing
        if not voices_data:
            voices_response = client.voices.get_all(show_legacy=True)
            for voice in getattr(voices_response, "voices", []):
                voice_id = getattr(voice, "voice_id", None)
                if not voice_id or voice_id in seen_voice_ids:
                    continue
                labels = getattr(voice, "labels", {}) or {}
                sample_url = getattr(voice, "preview_url", None)
                verified_languages = getattr(voice, "verified_languages", None) or []
                language_code = None
                for lang in verified_languages:
                    code = getattr(lang, "language_code", None)
                    if code:
                        language_code = code.lower()
                        break
                if not language_code:
                    language_code = _normalize_language_code(labels.get("language"))
                if not language_code:
                    language_code = _normalize_language_code(getattr(voice, "language", None))
                locale = labels.get("accent") or labels.get("region")

                voices_data.append({
                    "id": voice_id,
                    "label": getattr(voice, "name", None) or voice_id,
                    "description": getattr(voice, "description", None),
                    "language_code": language_code,
                    "language": language_code,
                    "accent": labels.get("accent"),
                    "gender": labels.get("gender"),
                    "category": getattr(voice, "category", None),
                    "preview_url": sample_url,
                    "preview_available": bool(sample_url),
                    "locale": locale,
                    "models": list(getattr(voice, "high_quality_base_model_ids", []) or []),
                })

        # Fetch models
        try:
            models_response = client.models.list()
            for model in models_response or []:
                if getattr(model, "can_do_text_to_speech", True):
                    models_data.append({
                        "id": getattr(model, "model_id", None),
                        "label": getattr(model, "name", None) or getattr(model, "model_id", None),
                        "description": getattr(model, "description", None),
                    })
        except Exception as exc:  # pragma: no cover - remote API variability
            logger.warning("Failed to load ElevenLabs models list: %s", exc)
            models_data = []

    except Exception as exc:  # pragma: no cover - remote API variability
        logger.warning("Failed to load ElevenLabs voices: %s", exc)

    if not models_data:
        models_data = fallback_models

    # Filter out entries without IDs
    voices_data = [voice for voice in voices_data if voice.get("id")]
    models_data = [model for model in models_data if model.get("id")]

    cache.update({
        "timestamp": now,
        "api_key": api_key,
        "voices": sorted(voices_data, key=lambda item: (item.get("label") or item["id"])),
        "models": models_data,
    })

    return cache


@router.get("/providers")
async def get_providers():
    """Get available AI providers and their status."""
    from app.core.config import settings
    
    return {
        "ai_providers": {
            "groq": {
                "name": "Groq",
                "available": bool(settings.groq_api_key),
                "models": ["llama-3.1-8b-instant", "mixtral-8x7b-32768"]
            },
            "openai": {
                "name": "OpenAI",
                "available": bool(settings.openai_api_key),
                "models": ["gpt-4", "gpt-3.5-turbo"]
            },
            "gemini": {
                "name": "Google Gemini",
                "available": bool(settings.google_api_key),
                "models": ["gemini-1.5-flash", "gemini-pro"]
            }
        },
        "image_services": {
            "pollination": {
                "name": "Pollination AI",
                "available": True,
                "free": True
            },
            "replicate": {
                "name": "Replicate",
                "available": bool(settings.replicate_api_key),
                "models": ["black-forest-labs/flux-schnell"]
            },
            "together": {
                "name": "Together AI",
                "available": bool(settings.together_api_key),
                "models": ["black-forest-labs/FLUX.1-schnell-Free"]
            },
            "fal": {
                "name": "FAL AI",
                "available": bool(settings.fal_key),
                "models": ["fal-ai/flux/schnell"]
            },
            "runware": {
                "name": "Runware.ai",
                "available": bool(settings.runware_api_key),
                "models": ["flux_dev", "flex_schenele", "juggernaut_lightning"]
            }
        },
        "tts_providers": {
            "edge": {
                "name": "Edge TTS",
                "available": True,
                "free": True
            },
            "elevenlabs": {
                "name": "ElevenLabs",
                "available": bool(settings.elevenlabs_api_key),
                "models": ["eleven_turbo_v2_5", "eleven_multilingual_v2"]
            },
            "fish": {
                "name": "Fish Audio",
                "available": bool(settings.fish_audio_api_key),
                "models": ["speech-1.6", "speech-1.5"]
            }
        }
    }


@router.get("/image-services/options")
async def get_image_service_options(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Detailed list of supported image generation services and models."""
    from app.core.config import settings
    config_data = {}
    config_file = "config.json"

    if os.path.exists(config_file):
        try:
            with open(config_file, 'r') as f:
                config_data = json.load(f)
        except Exception as exc:
            print(f"⚠️ Failed to load config.json for image services: {exc}")

    # Load user API keys
    result = await db.execute(
        select(UserAPIKey).where(
            UserAPIKey.user_id == current_user["id"],
            UserAPIKey.is_active == True
        )
    )
    user_keys = {key.service_name.lower(): key for key in result.scalars().all()}

    replicate_config = config_data.get("replicate_flux_api", {})
    fal_config = config_data.get("fal_flux_api", {})
    together_config = config_data.get("together_flux_api", {})
    runware_config = config_data.get("runware_flux_api", {})

    def build_runware_models():
        models = []
        for model_id, info in runware_config.get("models", {}).items():
            models.append({
                "id": model_id,
                "label": info.get("name", model_id.replace('_', ' ').title()),
                "description": info.get("description"),
                "default_steps": info.get("steps"),
                "quality": "pro" if info.get("steps", 0) >= 20 else "fast"
            })
        return models

    services = {
        "pollination": {
            "label": "Pollination (Free Flux)",
            "description": "Free community Flux model. Fast but basic quality.",
            "requires_api_key": False,
            "available": True,
            "configured": True,
            "recommended": False,
            "default_model": None,
            "models": []
        },
        "runware": {
            "label": "Runware.ai (Flux)",
            "description": "High-quality Flux models with up to 28 steps. Best overall quality.",
            "requires_api_key": True,
            "available": True,
            "configured": bool(settings.runware_api_key) or ('runware' in user_keys),
            "configured_via": 'user' if 'runware' in user_keys else ('environment' if settings.runware_api_key else None),
            "settings_url": "/settings/api-keys",
            "recommended": True,
            "default_model": runware_config.get("default_model") or ("flux_dev" if "flux_dev" in runware_config.get("models", {}) else None),
            "models": build_runware_models()
        },
        "replicate": {
            "label": "Replicate (Flux Schnell)",
            "description": "Paid API with reliable Flux Schnell outputs. Adjust steps for quality vs. speed.",
            "requires_api_key": True,
            "available": True,
            "configured": bool(settings.replicate_api_key) or ('replicate' in user_keys),
            "configured_via": 'user' if 'replicate' in user_keys else ('environment' if settings.replicate_api_key else None),
            "settings_url": "/settings/api-keys",
            "recommended": False,
            "default_model": replicate_config.get("model", "black-forest-labs/flux-schnell"),
            "models": [{
                "id": replicate_config.get("model", "black-forest-labs/flux-schnell"),
                "label": "Flux Schnell",
                "default_steps": replicate_config.get("num_inference_steps", 4),
                "quality": "balanced"
            }]
        },
        "together": {
            "label": "Together AI (Flux Free)",
            "description": "Free tier Flux. Good for experimentation with rate limits.",
            "requires_api_key": True,
            "available": True,
            "configured": bool(settings.together_api_key) or ('together' in user_keys),
            "configured_via": 'user' if 'together' in user_keys else ('environment' if settings.together_api_key else None),
            "settings_url": "/settings/api-keys",
            "recommended": False,
            "default_model": together_config.get("model", "black-forest-labs/FLUX.1-schnell-Free"),
            "models": [{
                "id": together_config.get("model", "black-forest-labs/FLUX.1-schnell-Free"),
                "label": "FLUX.1 Schnell Free",
                "default_steps": together_config.get("steps", 4),
                "quality": "fast"
            }]
        },
        "fal": {
            "label": "FAL AI (Flux)",
            "description": "Flux via FAL. Good quality when steps increased.",
            "requires_api_key": True,
            "available": True,
            "configured": bool(settings.fal_key) or ('fal' in user_keys),
            "configured_via": 'user' if 'fal' in user_keys else ('environment' if settings.fal_key else None),
            "settings_url": "/settings/api-keys",
            "recommended": False,
            "default_model": fal_config.get("model", "fal-ai/flux/schnell"),
            "models": [{
                "id": fal_config.get("model", "fal-ai/flux/schnell"),
                "label": "Flux Schnell",
                "default_steps": fal_config.get("num_inference_steps", 4),
                "quality": "balanced"
            }]
        }
    }

    # Ensure models lists are always present
    for key, entry in services.items():
        if "models" not in entry or entry["models"] is None:
            entry["models"] = []
        # For API-key services, mark availability based on configuration
        requires_key = entry.get("requires_api_key", False)
        if requires_key:
            entry["available"] = bool(entry.get("configured"))

    return services


@router.get("/tts-services/options")
async def get_tts_service_options(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Detailed list of supported TTS providers and voices/models."""
    from app.core.config import settings
    config_data = {}
    config_file = "config.json"

    if os.path.exists(config_file):
        try:
            with open(config_file, 'r') as f:
                config_data = json.load(f)
        except Exception as exc:
            print(f"⚠️ Failed to load config.json for TTS services: {exc}")

    tts_config = config_data.get("tts", {})
    elevenlabs_config = config_data.get("elevenlabs", {})
    fish_config = config_data.get("fish_audio", {})

    # Load user API keys and resolve environment overrides
    user_keys = await _load_user_api_keys(db, current_user["id"])

    # Edge TTS voices (no API key required)
    edge_voices = await _get_edge_voice_options()

    # ElevenLabs metadata (requires API key)
    elevenlabs_default_models = [
        {
            "id": item.get("id") or item.get("model_id") or item.get("name"),
            "label": item.get("name") or item.get("id"),
            "description": item.get("description"),
        }
        for item in (elevenlabs_config.get("available_models") or [])
        if (item.get("id") or item.get("model_id"))
    ]

    elevenlabs_api_key = _resolve_api_key("elevenlabs", user_keys, settings.elevenlabs_api_key)
    elevenlabs_configured_via = (
        "environment" if settings.elevenlabs_api_key else ("user" if "elevenlabs" in user_keys else None)
    )
    elevenlabs_meta: Dict[str, Any] = {"voices": [], "models": elevenlabs_default_models}
    if elevenlabs_api_key:
        elevenlabs_meta = await run_in_threadpool(
            _load_elevenlabs_metadata,
            elevenlabs_api_key,
            elevenlabs_default_models
        )

    # Fish Audio metadata (partial - falls back to config)
    fish_api_key = _resolve_api_key("fish_audio", user_keys, settings.fish_audio_api_key)
    fish_models = [
        {
            "id": item.get("id") or item.get("model_id") or item.get("name"),
            "label": item.get("name") or item.get("id"),
            "description": item.get("description"),
        }
        for item in (fish_config.get("available_models") or [])
        if (item.get("id") or item.get("model_id"))
    ]
    fish_voices_config = fish_config.get("available_voices") or fish_config.get("voices") or []
    fish_voice_options = []
    for entry in fish_voices_config:
        if isinstance(entry, dict):
            voice_id = entry.get("id") or entry.get("voice_id") or entry.get("name")
            if not voice_id:
                continue
            language_code = entry.get("language_code") or _normalize_language_code(entry.get("language"))
            if not language_code and entry.get("locale"):
                language_code = _normalize_language_code(entry.get("locale"))
            fish_voice_options.append({
                "id": voice_id,
                "label": entry.get("name") or voice_id,
                "description": entry.get("description"),
                "language_code": language_code,
                "language": language_code,
                "gender": entry.get("gender"),
                "models": entry.get("models") or [],
                "preview_url": entry.get("preview_url"),
                "preview_available": bool(entry.get("preview_url")),
                "locale": entry.get("locale"),
                "accent": entry.get("accent"),
            })
        elif isinstance(entry, str):
            fish_voice_options.append({
                "id": entry,
                "label": entry,
                "description": None,
                "language_code": None,
                "language": None,
                "gender": None,
                "models": [],
                "preview_url": None,
                "preview_available": bool(fish_api_key),
            })

    services = {
        "edge": {
            "label": "Edge TTS (free)",
            "description": "Built-in Microsoft Edge voices. No API key required.",
            "requires_api_key": False,
            "available": True,
            "configured": True,
            "configured_via": "built-in",
            "recommended": True,
            "default_model": None,
            "models": [],
            "supports_preview": True,
            "preview_endpoint": "/api/v1/settings/tts-services/preview",
            "voices": edge_voices,
        },
        "elevenlabs": {
            "label": "ElevenLabs",
            "description": "Premium voices with multiple languages. Requires ElevenLabs API key.",
            "requires_api_key": True,
            "available": bool(elevenlabs_api_key),
            "configured": bool(elevenlabs_api_key),
            "configured_via": elevenlabs_configured_via,
            "settings_url": "/settings/api-keys",
            "recommended": False,
            "default_model": elevenlabs_config.get("model", "eleven_turbo_v2_5"),
            "models": elevenlabs_meta.get("models") or elevenlabs_default_models,
            "supports_preview": True,
            "preview_endpoint": "/api/v1/settings/tts-services/preview",
            "voices": elevenlabs_meta.get("voices", []),
        },
        "fish": {
            "label": "Fish Audio",
            "description": "High-quality Fish Speech voices. Requires Fish Audio API key.",
            "requires_api_key": True,
            "available": bool(fish_api_key),
            "configured": bool(fish_api_key),
            "configured_via": (
                "environment" if settings.fish_audio_api_key else ("user" if "fish_audio" in user_keys else None)
            ),
            "settings_url": "/settings/api-keys",
            "recommended": False,
            "default_model": fish_config.get("default_voice", "speech-1.6"),
            "models": fish_models,
            "supports_preview": bool(fish_api_key),
            "preview_endpoint": "/api/v1/settings/tts-services/preview",
            "voices": fish_voice_options,
        },
    }

    # Edge voices list can be large; ensure we always return at least a fallback selection
    if not services["edge"]["voices"]:
        services["edge"]["voices"] = [
            {
                "id": "en-US-GuyNeural",
                "label": "English (US) - Guy",
                "description": "American English male voice",
                "locale": "en-US",
                "preview_url": None,
                "preview_available": True,
                "models": [],
            }
        ]

    return services


@router.get("/tts-services/preview")
async def get_tts_voice_preview(
    provider: str,
    voice_id: str,
    model_id: Optional[str] = None,
    sample_text: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Generate (or reuse cached) preview audio for a TTS voice."""
    from app.core.config import settings

    provider_normalized = provider.lower().strip()
    voice_id = voice_id.strip()
    if not provider_normalized or not voice_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="provider and voice_id are required")

    user_keys = await _load_user_api_keys(db, current_user["id"])
    sample_text = (sample_text or "Hello! My name is QuantumClip Voice. You can use me in your videos with QuantumClip.").strip()
    sample_text = sample_text[:250]

    upload_dir = os.path.join(settings.upload_dir, "tts_previews")
    os.makedirs(upload_dir, exist_ok=True)

    model_part = model_id or "default"
    filename = f"{_sanitize_filename(provider_normalized)}__{_sanitize_filename(voice_id)}__{_sanitize_filename(model_part)}.mp3"
    file_path = os.path.join(upload_dir, filename)

    def _file_stale(path: str) -> bool:
        if not os.path.exists(path):
            return True
        return time.time() - os.path.getmtime(path) > CACHE_TTL_SECONDS

    if _file_stale(file_path):
        # Generate a fresh preview
        try:
            if provider_normalized == "edge":
                import edge_tts  # type: ignore

                try:
                    communicate = edge_tts.Communicate(sample_text, voice_id)
                    await communicate.save(file_path)
                except Exception as edge_error:
                    # Edge TTS might fail for invalid voice IDs
                    error_msg = str(edge_error)
                    logger.warning("Edge TTS error for voice %s: %s", voice_id, error_msg)
                    if "not found" in error_msg.lower() or "invalid" in error_msg.lower():
                        raise HTTPException(
                            status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Voice '{voice_id}' not found in Edge TTS. The voice ID may be incorrect or the voice may not be available."
                        )
                    raise

            elif provider_normalized == "elevenlabs":
                api_key = _resolve_api_key("elevenlabs", user_keys, settings.elevenlabs_api_key)
                if not api_key:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ElevenLabs API key not configured")

                def _generate_elevenlabs():
                    from elevenlabs.client import ElevenLabs  # type: ignore
                    from elevenlabs import save  # type: ignore

                    client = ElevenLabs(api_key=api_key)
                    audio = client.generate(
                        text=sample_text,
                        voice=voice_id,
                        model=model_id or None
                    )
                    save(audio, file_path)

                await run_in_threadpool(_generate_elevenlabs)

            elif provider_normalized == "fish":
                api_key = _resolve_api_key("fish_audio", user_keys, settings.fish_audio_api_key)
                if not api_key:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Fish Audio API key not configured")

                def _generate_fish():
                    try:
                        from fish_audio_sdk import Session, TTSRequest  # type: ignore
                    except ModuleNotFoundError as exc:  # pragma: no cover - optional dependency
                        raise HTTPException(
                            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Fish Audio SDK is not installed on the server"
                        ) from exc

                    session = Session(api_key)
                    request = TTSRequest(
                        text=sample_text,
                        reference_id=voice_id,
                        model=model_id or "speech-1.6"
                    )
                    with open(file_path, "wb") as output:
                        for chunk in session.tts(request):
                            output.write(chunk)

                await run_in_threadpool(_generate_fish)

            else:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported TTS provider")

        except HTTPException:
            raise
        except Exception as exc:  # pragma: no cover - network/library issues
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except OSError:
                    pass
            logger.error("Failed to generate TTS preview for %s/%s: %s", provider_normalized, voice_id, exc)
            error_detail = str(exc)
            if "not found" in error_detail.lower() or "invalid" in error_detail.lower():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, 
                    detail=f"Voice '{voice_id}' not found or invalid for provider '{provider_normalized}'"
                )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                detail=f"Failed to generate preview audio: {error_detail}"
            )

    # Verify file exists before returning
    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Preview file was not generated successfully"
        )

    # Return the audio file directly
    from fastapi.responses import FileResponse
    return FileResponse(
        path=file_path,
        media_type="audio/mpeg",
        filename=filename,
        headers={
            "Cache-Control": "public, max-age=3600",
            "Content-Disposition": f'inline; filename="{filename}"'
        }
    )


@router.get("/api-keys", response_model=List[APIKeyResponse])
async def list_user_api_keys(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List user's API keys (without exposing actual keys)."""
    result = await db.execute(
        select(UserAPIKey).where(UserAPIKey.user_id == current_user["id"])
    )
    api_keys = result.scalars().all()
    
    return api_keys


@router.post("/api-keys", response_model=APIKeyResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    api_key_data: APIKeyCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Store a new API key for a service.
    VALIDATES the key by making a test API call before saving!
    """
    from app.services.api_validator import validate_api_key
    
    # VALIDATE THE API KEY FIRST!
    print(f"🔍 Testing {api_key_data.service_name} API key before saving...")
    is_valid, validation_message = validate_api_key(
        api_key_data.service_name, 
        api_key_data.api_key
    )
    
    if not is_valid:
        # Key is invalid - don't save it!
        print(f"❌ Validation failed: {validation_message}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=validation_message
        )
    
    print(f"✅ API key validated successfully: {validation_message}")
    
    # Check if key already exists for this service
    result = await db.execute(
        select(UserAPIKey).where(
            UserAPIKey.user_id == current_user["id"],
            UserAPIKey.service_name == api_key_data.service_name
        )
    )
    existing_key = result.scalar_one_or_none()
    
    if existing_key:
        # Update existing key
        existing_key.encrypted_key = encrypt_api_key(api_key_data.api_key)
        existing_key.key_name = api_key_data.key_name
        existing_key.is_active = True
        await db.commit()
        await db.refresh(existing_key)
        return existing_key
    
    # Create new API key
    new_api_key = UserAPIKey(
        user_id=current_user["id"],
        service_name=api_key_data.service_name,
        encrypted_key=encrypt_api_key(api_key_data.api_key),
        key_name=api_key_data.key_name,
    )
    
    db.add(new_api_key)
    await db.commit()
    await db.refresh(new_api_key)
    
    return new_api_key


@router.delete("/api-keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_api_key(
    key_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete an API key."""
    result = await db.execute(select(UserAPIKey).where(UserAPIKey.id == key_id))
    api_key = result.scalar_one_or_none()
    
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )
    
    # Check ownership
    if api_key.user_id != current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this API key"
        )
    
    await db.delete(api_key)
    await db.commit()
    
    return None


@router.get("/resolutions")
async def get_resolutions():
    """Get available video resolutions."""
    # Load from config
    config_file = "config.json"
    if os.path.exists(config_file):
        with open(config_file, 'r') as f:
            config = json.load(f)
            return config.get("video_resolutions", {})
    
    return {
        "720p": {"portrait": {"width": 720, "height": 1280}, "landscape": {"width": 1280, "height": 720}},
        "1080p": {"portrait": {"width": 1080, "height": 1920}, "landscape": {"width": 1920, "height": 1080}},
        "2K": {"portrait": {"width": 1440, "height": 2560}, "landscape": {"width": 2560, "height": 1440}},
        "4K": {"portrait": {"width": 2160, "height": 3840}, "landscape": {"width": 3840, "height": 2160}}
    }


@router.get("/fonts")
async def get_fonts():
    """Get available fonts."""
    font_dir = "font"
    if os.path.exists(font_dir):
        fonts = [f.replace(".ttf", "") for f in os.listdir(font_dir) if f.endswith(".ttf")]
        return {"fonts": fonts}
    
    return {"fonts": []}


@router.get("/music")
async def get_background_music():
    """Get available background music."""
    music_dir = "music"
    if os.path.exists(music_dir):
        music_files = sorted([f for f in os.listdir(music_dir) if f.endswith((".mp3", ".MP3", ".wav"))])
        return {"music": music_files}
    
    return {"music": []}


@router.get("/fonts")
async def get_fonts():
    """Get available fonts for subtitles."""
    font_dir = "font"
    if os.path.exists(font_dir):
        fonts = sorted([f for f in os.listdir(font_dir) if f.endswith(".ttf")])
        return {"fonts": fonts}
    
    return {"fonts": []}


@router.get("/sample-scripts")
async def get_sample_scripts():
    """Get sample script templates."""
    sample_dir = "sample_scripts"
    scripts = []
    
    if os.path.exists(sample_dir):
        for filename in os.listdir(sample_dir):
            if filename.endswith(".txt"):
                filepath = os.path.join(sample_dir, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                        scripts.append({
                            "name": filename.replace(".txt", "").replace("_", " ").title(),
                            "filename": filename,
                            "content": content
                        })
                except Exception as e:
                    print(f"Error reading sample script {filename}: {e}")
    
    return {"scripts": scripts}


@router.get("/overlays")
async def get_video_overlays():
    """Get available video overlays."""
    overlay_dir = "overlays"
    if os.path.exists(overlay_dir):
        overlays = [f for f in os.listdir(overlay_dir) if f.endswith((".mp4", ".mov"))]
        return {"overlays": overlays}
    
    return {"overlays": []}


@router.post("/api-keys/test")
async def test_api_key(
    service_name: str,
    api_key: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Test an API key without saving it.
    Makes a real API call to verify the key works.
    """
    from app.services.api_validator import validate_api_key
    
    print(f"🧪 Testing {service_name} API key for user {current_user['id']}...")
    
    is_valid, message = validate_api_key(service_name, api_key)
    
    return {
        "valid": is_valid,
        "message": message,
        "service": service_name
    }


@router.get("/tts-voices/favorites")
async def get_favorite_voices(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user's favorite TTS voices."""
    from app.models.user import User
    
    result = await db.execute(select(User).where(User.id == current_user["id"]))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    # Get favorites from user preferences (stored as JSON)
    favorites = getattr(user, 'favorite_voices', None)
    if favorites is None:
        # Try to get from a JSON field or return empty list
        return {"favorites": []}
    
    if isinstance(favorites, str):
        import json
        try:
            favorites = json.loads(favorites)
        except:
            favorites = []
    
    return {"favorites": favorites if isinstance(favorites, list) else []}


@router.post("/tts-voices/favorites")
async def add_favorite_voice(
    provider: str,
    voice_id: str,
    voice_label: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Add a TTS voice to user's favorites."""
    from app.models.user import User
    import json
    
    result = await db.execute(select(User).where(User.id == current_user["id"]))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    # Get current favorites
    favorites = getattr(user, 'favorite_voices', None)
    if favorites is None or favorites == "":
        favorites = []
    elif isinstance(favorites, str):
        try:
            favorites = json.loads(favorites)
        except:
            favorites = []
    
    if not isinstance(favorites, list):
        favorites = []
    
    # Check if already favorited
    favorite_key = f"{provider}:{voice_id}"
    if any(fav.get("key") == favorite_key for fav in favorites):
        return {"message": "Voice already in favorites", "favorites": favorites}
    
    # Add to favorites
    favorites.append({
        "key": favorite_key,
        "provider": provider,
        "voice_id": voice_id,
        "voice_label": voice_label or voice_id,
        "added_at": time.time()
    })
    
    # Save to user (assuming we add a favorite_voices JSON column)
    # For now, we'll use a simple approach - store in user's metadata
    # In production, you'd want a proper UserPreference model
    try:
        setattr(user, 'favorite_voices', json.dumps(favorites))
        await db.commit()
        await db.refresh(user)
    except Exception as e:
        logger.warning(f"Could not save favorites to user model: {e}")
        # Fallback: store in a separate preferences table or use a different approach
    
    return {"message": "Voice added to favorites", "favorites": favorites}


@router.delete("/tts-voices/favorites")
async def remove_favorite_voice(
    provider: str,
    voice_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Remove a TTS voice from user's favorites."""
    from app.models.user import User
    import json
    
    result = await db.execute(select(User).where(User.id == current_user["id"]))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    # Get current favorites
    favorites = getattr(user, 'favorite_voices', None)
    if favorites is None or favorites == "":
        return {"message": "No favorites found", "favorites": []}
    
    if isinstance(favorites, str):
        try:
            favorites = json.loads(favorites)
        except:
            favorites = []
    
    if not isinstance(favorites, list):
        favorites = []
    
    # Remove from favorites
    favorite_key = f"{provider}:{voice_id}"
    favorites = [fav for fav in favorites if fav.get("key") != favorite_key]
    
    # Save to user
    try:
        setattr(user, 'favorite_voices', json.dumps(favorites))
        await db.commit()
        await db.refresh(user)
    except Exception as e:
        logger.warning(f"Could not save favorites to user model: {e}")
    
    return {"message": "Voice removed from favorites", "favorites": favorites}


@router.post("/subtitle/preview")
async def preview_subtitle(
    text: str = Query(..., description="Subtitle text to preview"),
    font: Optional[str] = Query(None, description="Font name"),
    font_size: int = Query(60, ge=20, le=200, description="Font size"),
    position: str = Query("bottom", description="Position: top, center, or bottom"),
    text_color: str = Query("#FFFFFF", description="Text color in hex"),
    bg_opacity: int = Query(180, ge=0, le=255, description="Background opacity"),
    outline_width: int = Query(3, ge=0, le=10, description="Outline width"),
    width: int = Query(1080, description="Preview width"),
    height: int = Query(1920, description="Preview height"),
):
    """Generate a preview image for subtitle styling."""
    from app.services.video_service import create_subtitle_image
    from PIL import Image
    import numpy as np
    from fastapi.responses import Response
    import io
    
    try:
        # Parse text color
        text_color_hex = text_color.lstrip('#')
        text_color_rgb = tuple(int(text_color_hex[i:i+2], 16) for i in (0, 2, 4))
        
        # Get font path
        font_path = None
        if font and os.path.exists(f"font/{font}"):
            font_path = f"font/{font}"
        
        # Create subtitle image
        subtitle_array = create_subtitle_image(
            text=text,
            width=width,
            height=height,
            font_path=font_path,
            font_size=font_size,
            position=position,
            text_color=text_color_rgb,
            bg_color=(0, 0, 0),
            bg_opacity=bg_opacity,
            outline_width=outline_width,
            padding=20,
        )
        
        # Convert to PIL Image and then to bytes
        img = Image.fromarray(subtitle_array.astype(np.uint8))
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        
        return Response(content=img_bytes.read(), media_type="image/png")
        
    except Exception as e:
        logger.error(f"Error generating subtitle preview: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate subtitle preview: {str(e)}"
        )


@router.get("/transitions")
async def get_transitions():
    """Get list of available transitions with descriptions."""
    from app.services.video_service import SUPPORTED_TRANSITIONS, TRANSITION_ALIASES
    
    transitions = []
    for transition in sorted(SUPPORTED_TRANSITIONS):
        if transition == "none":
            continue
        
        # Get description
        descriptions = {
            "crossfade": "Smooth fade between scenes",
            "fade_black": "Fade to black between scenes",
            "fade_white": "Fade to white between scenes",
            "flash": "Quick white flash transition",
            "slide_left": "Slide left transition",
            "slide_right": "Slide right transition",
            "slide_up": "Slide up transition",
            "slide_down": "Slide down transition",
            "wipe_left": "Wipe left transition",
            "wipe_right": "Wipe right transition",
            "wipe_up": "Wipe up transition",
            "wipe_down": "Wipe down transition",
            "zoom_in": "Zoom in transition",
            "zoom_out": "Zoom out transition",
            "zoom_cross": "Cross zoom transition",
            "pixelate": "Pixelate transition",
            "random": "Random transition each time",
            "mix": "Mix all available transitions randomly",
        }
        
        transitions.append({
            "id": transition,
            "name": transition.replace("_", " ").title(),
            "description": descriptions.get(transition, "Custom transition"),
            "aliases": [k for k, v in TRANSITION_ALIASES.items() if v == transition]
        })
    
    return {"transitions": transitions}


@router.get("/transition/preview")
async def preview_transition(
    transition_type: str = Query(..., description="Transition type"),
    duration: float = Query(0.5, ge=0.1, le=2.0, description="Transition duration"),
    width: int = Query(1080, description="Preview width"),
    height: int = Query(1920, description="Preview height"),
):
    """Generate a preview video/GIF for a transition."""
    from app.services.video_service import normalize_transition_type, create_transition_clip
    from PIL import Image
    import numpy as np
    from fastapi.responses import Response
    import io
    import os
    
    try:
        # Normalize transition type
        normalized = normalize_transition_type(transition_type)
        if normalized == "none":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot preview 'none' transition"
            )
        
        # Create sample images for preview
        # Use gradient images or sample images if available
        sample_dir = "style_previews"
        sample_images = []
        if os.path.exists(sample_dir):
            sample_files = [f for f in os.listdir(sample_dir) if f.endswith('.png')]
            if len(sample_files) >= 2:
                sample_images = [
                    os.path.join(sample_dir, sample_files[0]),
                    os.path.join(sample_dir, sample_files[1])
                ]
        
        # If no sample images, create gradient images
        if not sample_images:
            # Create gradient images
            prev_img = Image.new('RGB', (width, height), color=(100, 150, 200))
            next_img = Image.new('RGB', (width, height), color=(200, 100, 150))
            
            prev_path = "temp_prev_preview.png"
            next_path = "temp_next_preview.png"
            prev_img.save(prev_path)
            next_img.save(next_path)
            sample_images = [prev_path, next_path]
        
        # Create transition preview
        prev_entry = {"image_path": sample_images[0]}
        next_entry = {"image_path": sample_images[1]}
        
        fps = 30
        transition_clip = create_transition_clip(
            prev_entry=prev_entry,
            next_entry=next_entry,
            transition_type=normalized,
            duration=duration,
            width=width,
            height=height,
            fps=fps
        )
        
        if not transition_clip:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to create transition preview for {normalized}"
            )
        
        # Export as GIF (simpler than video for preview)
        gif_path = f"temp_transition_preview_{normalized}.gif"
        transition_clip.write_gif(gif_path, fps=fps, logger=None)
        
        # Read and return
        with open(gif_path, 'rb') as f:
            gif_data = f.read()
        
        # Cleanup
        try:
            os.remove(gif_path)
            if sample_images[0].startswith("temp_"):
                os.remove(sample_images[0])
            if sample_images[1].startswith("temp_"):
                os.remove(sample_images[1])
        except:
            pass
        
        return Response(content=gif_data, media_type="image/gif")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating transition preview: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate transition preview: {str(e)}"
        )

