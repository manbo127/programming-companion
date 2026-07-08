import requests


class LLMClientError(Exception):
    pass


class DeepSeekClient:
    def __init__(self, api_key: str, base_url: str, model: str, timeout: int = 60):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.timeout = timeout

    def chat(self, messages: list[dict]) -> str:
        if not self.api_key:
            raise LLMClientError(
                "未配置 DEEPSEEK_API_KEY。请先在环境变量中设置 DeepSeek API Key。"
            )

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.7,
            "stream": False,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            response = requests.post(
                self.base_url,
                json=payload,
                headers=headers,
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise LLMClientError(f"调用 DeepSeek API 失败：{exc}") from exc

        if response.status_code >= 400:
            raise LLMClientError(
                f"DeepSeek API 返回错误：HTTP {response.status_code}，{response.text}"
            )

        data = response.json()
        try:
            return data["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMClientError(f"DeepSeek API 返回格式异常：{data}") from exc
