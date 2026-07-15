"""
FakeLLM — 测试用，不依赖网络和付费 API。
"""
from .base import LLMGateway, LLMResponse


class FakeLLM(LLMGateway):
    """用于测试的假 LLM，返回预设回复。"""

    def __init__(self, responses: list[str] | None = None, default: str = ""):
        self.responses = responses or []
        self.default = default or "这是一个测试回复。"
        self.call_count = 0
        self.last_messages: list[dict] = []

    def chat(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> LLMResponse:
        self.call_count += 1
        self.last_messages = messages
        if self.call_count <= len(self.responses):
            content = self.responses[self.call_count - 1]
        else:
            content = self.default
        return LLMResponse(content=content, model="fake", latency_ms=1)
