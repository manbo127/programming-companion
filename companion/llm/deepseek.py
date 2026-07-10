"""
DeepSeek LLM 实现
"""
import time
from openai import OpenAI
from .base import LLMGateway, LLMResponse


class DeepSeekGateway(LLMGateway):
    """DeepSeek API 客户端（OpenAI 兼容接口）。"""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.deepseek.com/v1",
        model: str = "deepseek-chat",
        timeout: float = 35.0,
        max_retries: int = 2,
        total_timeout: float = 40.0,
    ):
        self.client = OpenAI(api_key=api_key, base_url=base_url, timeout=timeout, max_retries=0)
        self.model = model
        self._request_timeout = timeout
        self._max_retries = max(1, max_retries)
        self._total_timeout = max(timeout, total_timeout)
        self._retry_delay = 1.5

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
                resp = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stream=False,
                    timeout=min(self._request_timeout, remaining),
                )
                choice = resp.choices[0]
                return LLMResponse(
                    content=choice.message.content or "",
                    model=self.model,
                    input_tokens=resp.usage.prompt_tokens if resp.usage else 0,
                    output_tokens=resp.usage.completion_tokens if resp.usage else 0,
                    latency_ms=int((time.monotonic() - t0) * 1000),
                )
            except Exception as e:
                last_error = e
                delay = self._retry_delay * (attempt + 1)
                if attempt < self._max_retries - 1 and (time.monotonic() - t0 + delay) < self._total_timeout:
                    time.sleep(delay)

        raise RuntimeError(
            f"DeepSeek API call failed after {self._max_retries} retries: {last_error}"
        )
