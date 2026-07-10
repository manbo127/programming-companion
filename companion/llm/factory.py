"""
LLM 工厂 — 根据配置创建对应实现。
"""
import os
from .base import LLMGateway
from .deepseek import DeepSeekGateway
from .fake import FakeLLM


def create_llm_gateway(config: dict | None = None) -> LLMGateway:
    """根据配置创建 LLM 实例。

    测试环境（TESTING=true 或 DEEPSEEK_API_KEY 为空时）返回 FakeLLM。
    """
    if config is None:
        config = {}

    testing = config.get("TESTING", False)
    api_key = config.get("DEEPSEEK_API_KEY", os.getenv("DEEPSEEK_API_KEY", ""))

    if testing or not api_key:
        return FakeLLM()

    return DeepSeekGateway(
        api_key=api_key,
        base_url=config.get("DEEPSEEK_BASE_URL", os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")),
        model=config.get("DEEPSEEK_MODEL", os.getenv("DEEPSEEK_MODEL", "deepseek-chat")),
        timeout=float(config.get("DEEPSEEK_TIMEOUT", os.getenv("DEEPSEEK_TIMEOUT", "35"))),
        max_retries=int(config.get("DEEPSEEK_MAX_RETRIES", os.getenv("DEEPSEEK_MAX_RETRIES", "2"))),
        total_timeout=float(config.get("DEEPSEEK_TOTAL_TIMEOUT", os.getenv("DEEPSEEK_TOTAL_TIMEOUT", "40"))),
    )
