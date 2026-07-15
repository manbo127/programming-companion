"""
DeepSeek LLM 实现
"""
import time
import random
from openai import OpenAI
from .base import LLMGateway, LLMProviderError, LLMResponse


class DeepSeekGateway(LLMGateway):
    """DeepSeek API 客户端（OpenAI 兼容接口）。"""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.deepseek.com",
        model: str = "deepseek-v4-flash",
        timeout: float = 35.0,
        max_retries: int = 2,
        total_timeout: float = 40.0,
        thinking: str = "disabled",
        reasoning_effort: str = "high",
        client=None,
        sleep_fn=time.sleep,
        jitter_fn=random.uniform,
    ):
        if not api_key:
            raise ValueError("DeepSeek API key is required")
        if not base_url.startswith("https://"):
            raise ValueError("DeepSeek base URL must use HTTPS")
        if thinking not in {"enabled", "disabled"}:
            raise ValueError("thinking must be enabled or disabled")
        self.client = client or OpenAI(api_key=api_key, base_url=base_url, timeout=timeout, max_retries=0)
        self.model = model
        self._request_timeout = timeout
        self._max_retries = max(1, max_retries)
        self._total_timeout = max(timeout, total_timeout)
        self._retry_delay = 1.5
        self._thinking = thinking
        self._reasoning_effort = reasoning_effort
        self._sleep = sleep_fn
        self._jitter = jitter_fn

    @staticmethod
    def _status_code(error: Exception) -> int | None:
        value = getattr(error, "status_code", None)
        return int(value) if isinstance(value, int) else None

    @classmethod
    def _is_retryable(cls, error: Exception) -> bool:
        status = cls._status_code(error)
        if status is not None:
            return status in {408, 409, 429} or status >= 500
        name = type(error).__name__.lower()
        return any(token in name for token in ("timeout", "connection", "ratelimit"))

    @classmethod
    def _provider_error(cls, error: Exception) -> LLMProviderError:
        status = cls._status_code(error)
        name = type(error).__name__.lower()
        if status in {401, 403} or "authentication" in name or "permission" in name:
            return LLMProviderError("LLM_AUTH_ERROR", "模型服务认证失败", retryable=False)
        if status == 429 or "ratelimit" in name:
            return LLMProviderError("LLM_RATE_LIMIT", "模型服务当前繁忙，请稍后重试", retryable=True)
        if "timeout" in name:
            return LLMProviderError("LLM_TIMEOUT", "模型响应超时，请稍后重试", retryable=True)
        if status is not None and 400 <= status < 500:
            return LLMProviderError("LLM_REQUEST_ERROR", "模型请求参数无效", retryable=False)
        return LLMProviderError("LLM_UNAVAILABLE", "模型服务暂时不可用", retryable=True)

    def chat(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> LLMResponse:
        last_error = None
        t0 = time.monotonic()

        for attempt in range(self._max_retries):
            elapsed = time.monotonic() - t0
            remaining = self._total_timeout - elapsed
            if remaining <= 0:
                break
            try:
                extra_body = {"thinking": {"type": self._thinking}}
                if self._thinking == "enabled":
                    extra_body["reasoning_effort"] = self._reasoning_effort
                resp = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stream=False,
                    timeout=min(self._request_timeout, remaining),
                    extra_body=extra_body,
                )
                choice = resp.choices[0]
                content = choice.message.content or ""
                if not content.strip():
                    raise RuntimeError("empty model response")
                return LLMResponse(
                    content=content,
                    model=self.model,
                    input_tokens=resp.usage.prompt_tokens if resp.usage else 0,
                    output_tokens=resp.usage.completion_tokens if resp.usage else 0,
                    latency_ms=int((time.monotonic() - t0) * 1000),
                    request_id=str(getattr(resp, "_request_id", "") or ""),
                    finish_reason=str(getattr(choice, "finish_reason", "") or ""),
                    attempts=attempt + 1,
                )
            except Exception as e:
                last_error = e
                if not self._is_retryable(e) and str(e) != "empty model response":
                    break
                delay = self._retry_delay * (2 ** attempt) + self._jitter(0, 0.25)
                if attempt < self._max_retries - 1 and (time.monotonic() - t0 + delay) < self._total_timeout:
                    self._sleep(delay)

        raise self._provider_error(last_error or RuntimeError("request deadline exceeded"))
