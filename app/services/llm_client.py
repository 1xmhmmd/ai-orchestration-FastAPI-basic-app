"""
Thin async wrapper around the OpenAI Chat Completions API.

Why wrap it instead of calling the SDK directly from agents:
- Single place to configure timeout, retries, and error translation so
  every agent gets the same resilience behaviour for free.
- Agents depend on this narrow interface, not on the OpenAI SDK — makes
  it trivial to swap providers (Anthropic, local vLLM, etc.) later
  without touching agent logic (dependency inversion).
- Centralizes token-usage logging, which matters for cost observability
  in any real AI product.
"""

import logging

from openai import APIError, APITimeoutError, AsyncOpenAI, RateLimitError
from openai.types.chat import ChatCompletion
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.config import Settings
from app.core.exceptions import UpstreamLLMError

logger = logging.getLogger(__name__)


class LLMResponse:
    def __init__(self, text: str, input_tokens: int | None, output_tokens: int | None):
        self.text = text
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens


class LLMClient:
    """Async client for chat-style LLM completions."""

    def __init__(self, settings: Settings):
        self._settings = settings
        self._client = AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            timeout=settings.LLM_REQUEST_TIMEOUT_SECONDS,
        )

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        retry=retry_if_exception_type((APITimeoutError, RateLimitError)),
    )
    async def _create_completion(self, *, system_prompt: str, user_prompt: str) -> ChatCompletion:
        return await self._client.chat.completions.create(
            model=self._settings.OPENAI_MODEL,
            max_tokens=self._settings.LLM_MAX_OUTPUT_TOKENS,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )

    async def complete(self, *, system_prompt: str, user_prompt: str) -> LLMResponse:
        try:
            completion = await self._create_completion(
                system_prompt=system_prompt, user_prompt=user_prompt
            )
        except (APITimeoutError, RateLimitError, APIError) as exc:
            logger.error("LLM call failed after retries: %s", exc)
            raise UpstreamLLMError(
                "The AI provider failed to respond. Please try again shortly."
            ) from exc

        choice = completion.choices[0]
        usage = completion.usage
        return LLMResponse(
            text=choice.message.content or "",
            input_tokens=getattr(usage, "prompt_tokens", None),
            output_tokens=getattr(usage, "completion_tokens", None),
        )
