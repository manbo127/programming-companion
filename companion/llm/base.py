"""
LLM Gateway 基类 — 定义统一接口
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class LLMResponse:
    """统一的 LLM 响应结构。"""
    content: str
    model: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: int = 0
    request_id: str = ""
    finish_reason: str = ""
    attempts: int = 1


class LLMProviderError(RuntimeError):
    """可安全传递到 API 层的大模型供应商错误。"""

    def __init__(self, code: str, message: str, *, retryable: bool, status_code: int = 503):
        super().__init__(message)
        self.code = code
        self.retryable = retryable
        self.status_code = status_code


class LLMGateway(ABC):
    """大模型调用统一接口。所有 LLM 实现必须继承此类。"""

    @abstractmethod
    def chat(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> LLMResponse:
        """发送聊天请求，返回 LLMResponse。"""
        ...
