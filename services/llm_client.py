"""
DeepSeek LLM API 封装层
使用 OpenAI 兼容接口，保持代码简洁
"""
import time
from typing import Optional, Generator
from openai import OpenAI

from config import Config


class LLMClient:
    """DeepSeek API 客户端封装"""

    def __init__(self):
        self.client = OpenAI(
            api_key=Config.DEEPSEEK_API_KEY,
            base_url=Config.DEEPSEEK_BASE_URL,
        )
        self.model = Config.DEEPSEEK_MODEL
        self.max_retries = 3
        self.retry_delay = 1.5  # 秒

    def chat(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 2048,
        stream: bool = False,
    ) -> str:
        """
        发送聊天请求，返回回复文本。

        参数:
            messages: [{"role": "system/user/assistant", "content": "..."}]
            temperature: 温度参数 (0.0~2.0)
            max_tokens: 最大输出 token 数
            stream: 是否流式输出（暂供扩展）

        返回:
            LLM 回复的文本内容
        """
        last_error = None

        for attempt in range(self.max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stream=False,
                )
                return response.choices[0].message.content

            except Exception as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (attempt + 1))

        raise RuntimeError(
            f"DeepSeek API 调用失败（已重试 {self.max_retries} 次）: {last_error}"
        )

    def chat_with_retry(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        """chat 的别名，语义更明确"""
        return self.chat(messages, temperature, max_tokens)


# 全局单例
_llm_client: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    """获取全局 LLM 客户端单例"""
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client
