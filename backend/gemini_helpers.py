"""
Gemini Helpers — Shared utilities for calling Gemini with automatic model cascade.

Tries the best model first, falls back to next-best if it fails.
Model priority: gemini-3.1-pro-preview → gemini-3.1-flash-lite-preview → gemini-2.0-flash

Performance features:
  - call_gemini_fast(): Uses fastest model only (for chart suggestions)
  - LRU response cache keyed by data hash (skips API for repeated schemas)
  - temperature parameter for deterministic outputs
"""
import os
import json
import hashlib
import re
from functools import lru_cache
from typing import Optional, List

# Gemini SDK
try:
    from google import genai
    from google.genai import types as genai_types
    GEMINI_AVAILABLE = True
except ImportError:
    try:
        import google.generativeai as genai_legacy
        GEMINI_AVAILABLE = True
    except ImportError:
        GEMINI_AVAILABLE = False

# ─── Singleton Client ───────────────────────────────────────────────
_gemini_client = None

# Model cascade: best → fallback (ordered by capability)
MODEL_CASCADE = [
    "gemini-3.1-pro-preview",
    "gemini-3.1-flash-lite-preview",
    "gemini-2.0-flash",
]

# Fast model (for performance-sensitive calls like chart suggestions)
FAST_MODEL = "gemini-3.1-flash-lite-preview"

# ─── Response Cache ─────────────────────────────────────────────────
_response_cache = {}
_CACHE_MAX_SIZE = 64


def _cache_key(prompt: str) -> str:
    """Create a short hash key for caching."""
    return hashlib.md5(prompt.encode()).hexdigest()[:16]


def _get_cached(key: str) -> Optional[str]:
    return _response_cache.get(key)


def _set_cached(key: str, value: str):
    if len(_response_cache) >= _CACHE_MAX_SIZE:
        # Evict oldest entry (FIFO)
        oldest = next(iter(_response_cache))
        del _response_cache[oldest]
    _response_cache[key] = value


def get_gemini_client():
    """Get or create the singleton Gemini client."""
    global _gemini_client
    if _gemini_client is None and GEMINI_AVAILABLE:
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except ImportError:
            pass
        api_key = os.environ.get("GEMINI_API_KEY")
        if api_key:
            try:
                _gemini_client = genai.Client(api_key=api_key)
            except Exception:
                # Fallback for older SDK
                pass
    return _gemini_client


def _strip_markdown_fences(text: str) -> str:
    """Remove markdown code fences and language tags from response."""
    text = text.strip()
    # Handle ```json ... ``` or ``` ... ```
    if text.startswith("```"):
        # Remove opening fence + optional language tag
        text = re.sub(r'^```\w*\s*\n?', '', text)
        # Remove closing fence
        text = re.sub(r'\n?```\s*$', '', text)
    return text.strip()


def call_gemini(
    prompt: str,
    client=None,
    models: Optional[List[str]] = None,
    temperature: Optional[float] = None,
    use_cache: bool = False,
) -> str:
    """
    Call Gemini with automatic model cascade and return cleaned text.

    Args:
        prompt: The prompt text to send
        client: Optional Gemini client (uses singleton if not provided)
        models: Optional model list override (defaults to MODEL_CASCADE)
        temperature: Optional temperature (0.0 for deterministic, None for default)
        use_cache: If True, cache and reuse responses for identical prompts

    Returns:
        Cleaned response text (markdown fences stripped)

    Raises:
        RuntimeError if all models fail
    """
    client = client or get_gemini_client()
    if not client:
        raise RuntimeError("Gemini client not available. Check GEMINI_API_KEY.")

    # Check cache
    if use_cache:
        cache_key = _cache_key(prompt)
        cached = _get_cached(cache_key)
        if cached is not None:
            print("⚡ Cache hit — skipping Gemini API call")
            return cached

    models = models or MODEL_CASCADE
    last_error = None

    # Build generation config if temperature is specified
    gen_config = None
    if temperature is not None:
        try:
            gen_config = genai_types.GenerateContentConfig(temperature=temperature)
        except Exception:
            gen_config = None

    for model_name in models:
        try:
            kwargs = {
                "model": model_name,
                "contents": prompt,
            }
            if gen_config:
                kwargs["config"] = gen_config

            response = client.models.generate_content(**kwargs)
            text = _strip_markdown_fences(response.text)

            # Store in cache if enabled
            if use_cache:
                _set_cached(cache_key, text)

            return text
        except Exception as e:
            last_error = e
            print(f"⚠️ Gemini model '{model_name}' failed: {e}")
            continue

    raise RuntimeError(f"All Gemini models failed. Last error: {last_error}")


def call_gemini_fast(
    prompt: str,
    client=None,
    temperature: Optional[float] = None,
    use_cache: bool = True,
) -> str:
    """
    Call Gemini using ONLY the fastest model (gemini-2.0-flash).
    Ideal for performance-sensitive calls like chart suggestions.
    Caches by default.
    """
    return call_gemini(
        prompt,
        client=client,
        models=[FAST_MODEL],
        temperature=temperature,
        use_cache=use_cache,
    )


def call_gemini_json(
    prompt: str,
    client=None,
    models: Optional[List[str]] = None,
    temperature: Optional[float] = None,
    use_cache: bool = False,
) -> dict:
    """
    Call Gemini with model cascade and parse JSON response.

    Returns:
        Parsed JSON (dict or list)
    """
    text = call_gemini(
        prompt,
        client=client,
        models=models,
        temperature=temperature,
        use_cache=use_cache,
    )
    return json.loads(text)


def call_gemini_multimodal(
    contents,
    client=None,
    models: Optional[List[str]] = None,
    temperature: Optional[float] = None,
) -> str:
    """
    Call Gemini with multimodal content (images, PDFs) and model cascade.

    Args:
        contents: A list of genai Content objects or a single Content
        client: Optional Gemini client
        models: Optional model list override
        temperature: Optional temperature for deterministic output

    Returns:
        Cleaned response text
    """
    client = client or get_gemini_client()
    if not client:
        raise RuntimeError("Gemini client not available. Check GEMINI_API_KEY.")

    models = models or MODEL_CASCADE
    last_error = None

    gen_config = None
    if temperature is not None:
        try:
            gen_config = genai_types.GenerateContentConfig(temperature=temperature)
        except Exception:
            gen_config = None

    for model_name in models:
        try:
            kwargs = {
                "model": model_name,
                "contents": contents,
            }
            if gen_config:
                kwargs["config"] = gen_config

            response = client.models.generate_content(**kwargs)
            text = _strip_markdown_fences(response.text)
            return text
        except Exception as e:
            last_error = e
            print(f"⚠️ Gemini model '{model_name}' (multimodal) failed: {e}")
            continue

    raise RuntimeError(f"All Gemini models failed (multimodal). Last error: {last_error}")


def compute_data_hash(df_shape: tuple, columns: list) -> str:
    """
    Compute a deterministic hash for a dataset (for caching/seeding).
    Uses shape + column names to create a stable key.
    """
    key = f"{df_shape[0]}x{df_shape[1]}:" + ",".join(sorted(columns))
    return hashlib.md5(key.encode()).hexdigest()[:12]
