import json
from datetime import datetime
from pathlib import Path

from config import Config


def _ensure_history_file() -> None:
    Config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not Config.HISTORY_FILE.exists():
        Config.HISTORY_FILE.write_text("[]", encoding="utf-8")


def _read_messages() -> list[dict]:
    _ensure_history_file()
    try:
        return json.loads(Config.HISTORY_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []


def _write_messages(messages: list[dict]) -> None:
    _ensure_history_file()
    Config.HISTORY_FILE.write_text(
        json.dumps(messages, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def append_message(
    role: str,
    content: str,
    scene: str,
    code: str = "",
    error: str = "",
) -> dict:
    messages = _read_messages()
    item = {
        "role": role,
        "content": content,
        "scene": scene,
        "code": code,
        "error": error,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    messages.append(item)
    _write_messages(messages)
    return item


def get_recent_messages(limit: int = 8) -> list[dict]:
    messages = _read_messages()
    return messages[-limit:]


def clear_messages() -> None:
    _write_messages([])
