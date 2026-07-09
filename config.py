"""
配置中心 — 所有可调参数集中管理
"""
import os


class Config:
    """应用配置"""

    # ── DeepSeek API ──────────────────────────────────────
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "your-api-key-here")
    DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"
    DEEPSEEK_MODEL = "deepseek-chat"
    DEEPSEEK_TIMEOUT = float(os.getenv("DEEPSEEK_TIMEOUT", "35"))

    # ── 模型参数（按场景）──────────────────────────────────
    # 错误分析：低温度保证准确性
    ERROR_TEMPERATURE = 0.3
    ERROR_MAX_TOKENS = 2048

    # 解题引导：中等温度兼顾创造性与准确性
    GUIDANCE_TEMPERATURE = 0.6
    GUIDANCE_MAX_TOKENS = 2048

    # 知识点问答：中等偏低温度
    KNOWLEDGE_TEMPERATURE = 0.4
    KNOWLEDGE_MAX_TOKENS = 2048

    # 一般对话：较高温度使对话更自然
    GENERAL_TEMPERATURE = 0.7
    GENERAL_MAX_TOKENS = 2048

    # ── 对话管理 ──────────────────────────────────────────
    MAX_HISTORY_MESSAGES = 20  # 每次发送给 LLM 的最大历史消息数

    # ── 激励模块阈值 ──────────────────────────────────────
    PRAISE_THRESHOLD = 3       # 连续正确 ≥ 此值触发表扬
    ENCOURAGE_THRESHOLD = 2    # 连续错误 ≥ 此值触发强化鼓励

    # ── 数据存储 ──────────────────────────────────────────
    # Vercel serverless 只有 /tmp 可写，本地用项目目录
    if os.getenv("VERCEL"):
        DATA_DIR = "/tmp/conversations"
    else:
        DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "conversations")

    # ── Flask ─────────────────────────────────────────────
    SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "programming-companion-dev-key")
    DEBUG = os.getenv("FLASK_DEBUG", "true").lower() == "true"


# 确保数据目录存在
os.makedirs(Config.DATA_DIR, exist_ok=True)
