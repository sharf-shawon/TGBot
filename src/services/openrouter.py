"""OpenRouter API client for interacting with AI models."""

import asyncio
import json
from typing import AsyncIterator, Optional

import httpx


class OpenRouterClient:
    """Client for OpenRouter API."""

    BASE_URL = "https://openrouter.ai/api/v1"

    def __init__(self, api_key: str):
        """Initialize the OpenRouter client.

        Args:
            api_key: OpenRouter API key
        """
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "HTTP-Referer": "https://github.com/yourusername/tgbot",
            "X-Title": "Telegram Bot",
        }

    async def get_models(self) -> list[dict]:
        """Fetch all available models from OpenRouter.

        Returns:
            List of model dictionaries

        Raises:
            httpx.HTTPError: If API request fails
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/models",
                headers=self.headers,
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()
            return data.get("data", [])

    async def get_free_models(self) -> list[dict]:
        """Fetch only free models from OpenRouter.

        Returns:
            List of free model dictionaries

        Raises:
            httpx.HTTPError: If API request fails
        """
        models = await self.get_models()
        # Filter for free models:
        # 1. Models with pricing.prompt == "0" and pricing.completion == "0"
        # 2. Models with ":free" suffix in their ID (rate-limited free access)
        free_models = []
        for model in models:
            model_id = model.get("id", "")
            pricing = model.get("pricing", {})
            
            # Check for :free suffix (OpenRouter's free tier models)
            if ":free" in model_id:
                free_models.append(model)
                continue
            
            # Check for zero pricing (completely free models)
            try:
                prompt_price = float(pricing.get("prompt", "1"))
                completion_price = float(pricing.get("completion", "1"))
                
                if prompt_price == 0 and completion_price == 0:
                    free_models.append(model)
            except (ValueError, TypeError):
                # Skip models with invalid pricing data
                continue
        
        return free_models

    async def chat_completion(
        self,
        model: str,
        messages: list[dict],
        max_tokens: Optional[int] = 1000,
        temperature: float = 0.7,
        max_retries: int = 3,
    ) -> dict:
        """Send a chat completion request to OpenRouter with retry logic.

        Args:
            model: Model ID to use
            messages: List of message dictionaries with "role" and "content"
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            max_retries: Maximum number of retry attempts for rate limits

        Returns:
            Dictionary with 'content' and optional 'error' keys

        Raises:
            httpx.HTTPError: If API request fails after retries
        """
        last_error = None
        
        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        f"{self.BASE_URL}/chat/completions",
                        headers=self.headers,
                        json={
                            "model": model,
                            "messages": messages,
                            "max_tokens": max_tokens,
                            "temperature": temperature,
                        },
                        timeout=60.0,
                    )
                    
                    # Handle rate limiting with exponential backoff
                    if response.status_code == 429:
                        if attempt < max_retries - 1:
                            wait_time = (2 ** attempt) * 2  # 2, 4, 8 seconds
                            await asyncio.sleep(wait_time)
                            continue
                        else:
                            return {
                                "content": None,
                                "error": "rate_limit",
                                "message": (
                                    "⏳ Rate limit reached. The free tier has "
                                    "limited requests.\n\n"
                                    "Please wait a moment and try again, or "
                                    "consider upgrading your OpenRouter plan for "
                                    "higher limits."
                                ),
                            }
                    
                    # Handle other HTTP errors
                    if response.status_code == 401:
                        return {
                            "content": None,
                            "error": "auth",
                            "message": (
                                "🔑 Authentication failed. Your API key may "
                                "be invalid.\n\n"
                                "Use /delete_api_key to remove it and /start "
                                "to set a new one."
                            ),
                        }
                    
                    if response.status_code == 402:
                        return {
                            "content": None,
                            "error": "insufficient_credits",
                            "message": (
                                "💳 This model requires credits.\\n\\n"
                                "Note: Some 'free' models may have usage "
                                "limits or require credits during high "
                                "demand.\\n\\n"
                                "Options:\\n"
                                "1. Add credits at "
                                "https://openrouter.ai/credits\\n"
                                "2. Wait a moment and try again\\n"
                                "3. Use /change_model to try a different model"
                            ),
                        }
                    
                    # Raise for other HTTP errors
                    response.raise_for_status()
                    
                    data = response.json()
                    
                    # Extract the assistant's message
                    choices = data.get("choices", [])
                    if choices:
                        message = choices[0].get("message", {})
                        content = message.get("content", "No response generated.")
                        return {"content": content, "error": None}
                    
                    return {
                        "content": "No response generated.",
                        "error": "no_choices",
                    }
                    
            except httpx.TimeoutException:
                last_error = {
                    "content": None,
                    "error": "timeout",
                    "message": (
                        "⏱️ Request timed out. The model may be busy.\n\n"
                        "Please try again in a moment."
                    ),
                }
                if attempt < max_retries - 1:
                    await asyncio.sleep(2)
                    continue
                return last_error
                
            except httpx.ConnectError:
                last_error = {
                    "content": None,
                    "error": "connection",
                    "message": (
                        "🌐 Connection error. Please check your internet connection."
                    ),
                }
                if attempt < max_retries - 1:
                    await asyncio.sleep(2)
                    continue
                return last_error
                
            except httpx.HTTPError as e:
                last_error = {
                    "content": None,
                    "error": "http_error",
                    "message": f"❌ API Error: {str(e)}\n\nPlease try again later.",
                }
                break
        
        return last_error or {
            "content": None,
            "error": "unknown",
            "message": "An unknown error occurred.",
        }

    async def test_api_key(self) -> bool:
        """Test if the API key is valid.

        Returns:
            True if API key is valid, False otherwise
        """
        try:
            await self.get_models()
            return True
        except httpx.HTTPError:
            return False

    async def chat_completion_stream(
        self,
        model: str,
        messages: list[dict],
        max_tokens: Optional[int] = 1000,
        temperature: float = 0.7,
    ) -> AsyncIterator[dict]:
        """Send a streaming chat completion request to OpenRouter.

        Args:
            model: Model ID to use
            messages: List of message dictionaries with "role" and "content"
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature

        Yields:
            Dictionaries with 'content' (text chunk) or 'error' keys

        Raises:
            httpx.HTTPError: If API request fails
        """
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                async with client.stream(
                    "POST",
                    f"{self.BASE_URL}/chat/completions",
                    headers=self.headers,
                    json={
                        "model": model,
                        "messages": messages,
                        "max_tokens": max_tokens,
                        "temperature": temperature,
                        "stream": True,
                    },
                ) as response:
                    # Handle HTTP errors
                    if response.status_code == 429:
                        yield {
                            "content": None,
                            "error": "rate_limit",
                            "message": (
                                "⏳ Rate limit reached. The free tier has "
                                "limited requests.\n\n"
                                "Please wait a moment and try again, or "
                                "consider upgrading your OpenRouter plan for "
                                "higher limits."
                            ),
                        }
                        return

                    if response.status_code == 401:
                        yield {
                            "content": None,
                            "error": "auth",
                            "message": (
                                "🔑 Authentication failed. Your API key may "
                                "be invalid.\n\n"
                                "Use /delete_api_key to remove it and /start "
                                "to set a new one."
                            ),
                        }
                        return

                    if response.status_code == 402:
                        yield {
                            "content": None,
                            "error": "insufficient_credits",
                            "message": (
                                "💳 This model requires credits.\\n\\n"
                                "Note: Some 'free' models may have usage "
                                "limits or require credits during high "
                                "demand.\\n\\n"
                                "Options:\\n"
                                "1. Add credits at "
                                "https://openrouter.ai/credits\\n"
                                "2. Wait a moment and try again\\n"
                                "3. Use /change_model to try a different model"
                            ),
                        }
                        return

                    response.raise_for_status()

                    # Process SSE stream
                    async for line in response.aiter_lines():
                        line = line.strip()
                        if not line:
                            continue

                        # SSE format: "data: {json}"
                        if line.startswith("data: "):
                            data_str = line[6:]  # Remove "data: " prefix

                            # Check for stream end
                            if data_str == "[DONE]":
                                break

                            try:
                                data = json.loads(data_str)
                                choices = data.get("choices", [])
                                if choices:
                                    delta = choices[0].get("delta", {})
                                    content = delta.get("content", "")
                                    if content:
                                        yield {"content": content, "error": None}
                            except json.JSONDecodeError:
                                # Skip malformed JSON
                                continue

        except httpx.TimeoutException:
            yield {
                "content": None,
                "error": "timeout",
                "message": (
                    "⏱️ Request timed out. The model may be busy.\n\n"
                    "Please try again in a moment."
                ),
            }

        except httpx.ConnectError:
            yield {
                "content": None,
                "error": "connection",
                "message": (
                    "🌐 Connection error. Please check your internet connection."
                ),
            }

        except httpx.HTTPError as e:
            yield {
                "content": None,
                "error": "http_error",
                "message": f"❌ API Error: {str(e)}\n\nPlease try again later.",
            }

