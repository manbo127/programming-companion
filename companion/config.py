"""
配置中心 — 所有参数通过环境变量管理，不提交真实凭证。
"""
import os
from pathlib import Path
from companion.database import engine_options, normalize_database_url


def _env_bool(name: str, default: bool = False) -> bool:
    """Parse a conventional boolean environment variable."""
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class BaseConfig:
    """基础配置，公共默认值。"""
    # ── Flask ──────────────────────────────────────────
    APP_ENV = os.getenv("APP_ENV", "development").lower()
    SECRET_KEY = os.getenv("FLASK_SECRET_KEY")
    DEBUG = False
    TESTING = False
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", str(2 * 1024 * 1024)))
    TRUST_PROXY_HOPS = int(os.getenv("TRUST_PROXY_HOPS", "0"))
    PREFERRED_URL_SCHEME = "http"

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = _env_bool("SESSION_COOKIE_SECURE", False)

    # ── Database ───────────────────────────────────────
    _project_root = Path(__file__).resolve().parent.parent
    SQLALCHEMY_DATABASE_URI = normalize_database_url(os.getenv(
        "DATABASE_URL",
        f"sqlite:///{_project_root / 'instance' / 'companion.db'}",
    ))
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = engine_options(SQLALCHEMY_DATABASE_URI)

    # ── DeepSeek API ──────────────────────────────────
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
    DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash")
    DEEPSEEK_TIMEOUT = float(os.getenv("DEEPSEEK_TIMEOUT", "35"))
    DEEPSEEK_MAX_RETRIES = int(os.getenv("DEEPSEEK_MAX_RETRIES", "2"))
    DEEPSEEK_TOTAL_TIMEOUT = float(os.getenv("DEEPSEEK_TOTAL_TIMEOUT", "40"))
    DEEPSEEK_THINKING = os.getenv("DEEPSEEK_THINKING", "disabled")
    DEEPSEEK_REASONING_EFFORT = os.getenv("DEEPSEEK_REASONING_EFFORT", "high")

    # ── LLM 参数（按场景）───────────────────────────────
    ERROR_TEMPERATURE = 0.3
    ERROR_MAX_TOKENS = 2048
    GUIDANCE_TEMPERATURE = 0.6
    GUIDANCE_MAX_TOKENS = 2048
    KNOWLEDGE_TEMPERATURE = 0.4
    KNOWLEDGE_MAX_TOKENS = 2048
    GENERAL_TEMPERATURE = 0.7
    GENERAL_MAX_TOKENS = 2048

    # ── 上下文裁剪 ─────────────────────────────────────
    MAX_CONTEXT_MESSAGES = 20
    MAX_CONTEXT_CHARS = 8000
    MAX_CONTEXT_TOKENS = int(os.getenv("MAX_CONTEXT_TOKENS", "6000"))
    MAX_CONTEXT_SCAN_MESSAGES = int(os.getenv("MAX_CONTEXT_SCAN_MESSAGES", "120"))
    CONVERSATION_SUMMARY_ENTRIES = int(os.getenv("CONVERSATION_SUMMARY_ENTRIES", "8"))

    # ── 激励阈值 ──────────────────────────────────────
    PRAISE_THRESHOLD = 3
    ENCOURAGE_THRESHOLD = 2

    # ── 输入校验 ──────────────────────────────────────
    MAX_MESSAGE_LENGTH = 5000
    MAX_CODE_LENGTH = 10000
    MAX_ERROR_LENGTH = 5000

    # ── 日志 ──────────────────────────────────────────
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

    # ── 会话 Cookie ───────────────────────────────────
    CLIENT_COOKIE_NAME = "companion_client_id"
    CLIENT_COOKIE_MAX_AGE = 365 * 24 * 3600  # 1 year
    ACCOUNT_SESSION_MAX_AGE = int(os.getenv("ACCOUNT_SESSION_MAX_AGE", str(30 * 24 * 3600)))
    CLIENT_COOKIE_SECURE = _env_bool(
        "CLIENT_COOKIE_SECURE",
        os.getenv("APP_ENV", "development").lower() == "production",
    )

    # ── CSRF ──────────────────────────────────────────
    WTF_CSRF_ENABLED = True


class DevelopmentConfig(BaseConfig):
    DEBUG = True
    SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "dev-key-not-for-production")
    WTF_CSRF_ENABLED = False


class TestingConfig(BaseConfig):
    TESTING = True
    DEBUG = False
    SECRET_KEY = "test-secret-key"
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    DEEPSEEK_API_KEY = "test-key"


class ProductionConfig(BaseConfig):
    """生产环境：SECRET_KEY 必须由环境变量提供。"""
    DEBUG = False
    PREFERRED_URL_SCHEME = "https"
    SESSION_COOKIE_SECURE = _env_bool("SESSION_COOKIE_SECURE", True)

    def __init__(self):
        if not self.SECRET_KEY or self.SECRET_KEY.startswith("change-me"):
            raise RuntimeError("FLASK_SECRET_KEY must be set in production")
        if self.TRUST_PROXY_HOPS < 0:
            raise RuntimeError("TRUST_PROXY_HOPS must be zero or a positive integer")


_config_map = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}


def get_config():
    env = os.getenv("APP_ENV", "development").lower()
    cls = _config_map.get(env, DevelopmentConfig)
    if env == "production":
        return cls()
    return cls()
