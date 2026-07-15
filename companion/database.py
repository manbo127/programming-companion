"""数据库配置和运维辅助。"""
from pathlib import Path


def normalize_database_url(url: str) -> str:
    """兼容部分平台仍提供的 postgres:// 前缀，并显式选择 psycopg 3。"""
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


def engine_options(url: str) -> dict:
    if url.startswith("sqlite"):
        return {
            "connect_args": {"check_same_thread": False, "timeout": 5},
            "pool_pre_ping": True,
        }
    return {
        "pool_pre_ping": True,
        "pool_recycle": 1800,
        "pool_size": 5,
        "max_overflow": 10,
    }


def sqlite_path_from_url(url: str) -> Path | None:
    if not url.startswith("sqlite") or ":memory:" in url:
        return None
    from sqlalchemy.engine import make_url

    database = make_url(url).database
    return Path(database).resolve() if database else None
