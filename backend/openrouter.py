"""OpenRouter API client for making LLM requests."""

import asyncio
import time
from typing import List, Dict, Any, Optional

import httpx

from .config import OPENROUTER_API_URL, require_api_key

# Status codes worth a second attempt; everything else fails immediately.
RETRYABLE_STATUS = {408, 409, 425, 429, 500, 502, 503, 504}
AUTH_STATUS = {401, 403}


class OpenRouterAuthError(RuntimeError):
    """Credentials rejected by OpenRouter - retrying cannot help."""


async def query_model(
    model: str,
    messages: List[Dict[str, str]],
    timeout: float = 120.0,
    max_retries: int = 2,
) -> Optional[Dict[str, Any]]:
    """
    Query a single model via OpenRouter API.

    Args:
        model: OpenRouter model identifier (e.g., "openai/gpt-4o")
        messages: List of message dicts with 'role' and 'content'
        timeout: Request timeout in seconds
        max_retries: Extra attempts on timeouts / 429 / 5xx (exponential backoff)

    Returns:
        Dict with 'content', 'reasoning_details', 'usage', 'duration', or None
        if the model failed. Raises OpenRouterAuthError on bad credentials,
        since that affects every model and must not degrade silently.
    """
    headers = {
        "Authorization": f"Bearer {require_api_key()}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/derhefter/llm-council",
        "X-Title": "LLM Council",
    }

    payload = {
        "model": model,
        "messages": messages,
    }

    started = time.monotonic()
    last_error: Optional[str] = None

    for attempt in range(max_retries + 1):
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    OPENROUTER_API_URL,
                    headers=headers,
                    json=payload,
                )

                if response.status_code in AUTH_STATUS:
                    raise OpenRouterAuthError(
                        f"OpenRouter rejected the API key ({response.status_code}). "
                        "Check OPENROUTER_API_KEY."
                    )

                if response.status_code in RETRYABLE_STATUS and attempt < max_retries:
                    last_error = f"HTTP {response.status_code}"
                    await asyncio.sleep(2 ** (attempt + 1))
                    continue

                response.raise_for_status()

                data = response.json()
                message = data['choices'][0]['message']

                return {
                    'content': message.get('content'),
                    'reasoning_details': message.get('reasoning_details'),
                    'usage': data.get('usage') or {},
                    'duration': round(time.monotonic() - started, 2),
                }

        except OpenRouterAuthError:
            raise
        except (httpx.TimeoutException, httpx.TransportError) as e:
            last_error = f"{type(e).__name__}: {e}"
            if attempt < max_retries:
                await asyncio.sleep(2 ** (attempt + 1))
                continue
        except Exception as e:  # noqa: BLE001 - one bad model must not kill the run
            last_error = f"{type(e).__name__}: {e}"
            break

    print(f"Error querying model {model}: {last_error}")
    return None


async def query_models_parallel(
    models: List[str],
    messages: List[Dict[str, str]],
) -> Dict[str, Optional[Dict[str, Any]]]:
    """
    Query multiple models in parallel with the same messages.

    Returns:
        Dict mapping model identifier to response dict (or None if failed)
    """
    tasks = [query_model(model, messages) for model in models]
    responses = await asyncio.gather(*tasks)
    return {model: response for model, response in zip(models, responses)}


async def query_models_individually(
    prompts: Dict[str, str],
) -> Dict[str, Optional[Dict[str, Any]]]:
    """
    Query multiple models in parallel, each with its own prompt.

    Args:
        prompts: model identifier -> user prompt

    Returns:
        Dict mapping model identifier to response dict (or None if failed)
    """
    models = list(prompts)
    tasks = [
        query_model(model, [{"role": "user", "content": prompts[model]}])
        for model in models
    ]
    responses = await asyncio.gather(*tasks)
    return {model: response for model, response in zip(models, responses)}
