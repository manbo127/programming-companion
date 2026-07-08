"""
对话管理器 — 内存缓存 + JSON 文件持久化
双层存储：内存提供快速读写，JSON 提供跨会话持久化
"""
import json
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from config import Config


@dataclass
class Conversation:
    """单次对话"""
    session_id: str
    messages: list[dict] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self):
        now = datetime.now().isoformat()
        if not self.created_at:
            self.created_at = now
        if not self.updated_at:
            self.updated_at = now

    def add_message(self, role: str, content: str):
        """添加一条消息"""
        self.messages.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
        })
        self.updated_at = datetime.now().isoformat()

    def get_recent_messages(self, limit: int = 20) -> list[dict]:
        """
        获取最近 N 条消息，返回 LLM 可用格式。
        只返回 role 和 content 字段。
        """
        recent = self.messages[-limit:]
        return [{"role": m["role"], "content": m["content"]} for m in recent]

    def to_dict(self) -> dict:
        """序列化为字典"""
        return {
            "session_id": self.session_id,
            "messages": self.messages,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Conversation":
        """从字典反序列化"""
        conv = cls(
            session_id=data["session_id"],
            messages=data.get("messages", []),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
        )
        return conv


class ConversationManager:
    """对话管理器 — 管理多个会话的生命周期"""

    def __init__(self):
        self.data_dir = Config.DATA_DIR
        os.makedirs(self.data_dir, exist_ok=True)
        # 内存缓存: {session_id: Conversation}
        self._cache: dict[str, Conversation] = {}

    def get_or_create(self, session_id: Optional[str] = None) -> Conversation:
        """
        获取或创建对话。
        查找顺序: 内存缓存 → JSON 文件 → 新建
        """
        # 1. 内存缓存
        if session_id and session_id in self._cache:
            return self._cache[session_id]

        # 2. JSON 文件
        if session_id:
            conv = self._load_from_file(session_id)
            if conv:
                self._cache[session_id] = conv
                return conv

        # 3. 新建
        new_id = session_id or str(uuid.uuid4())
        conv = Conversation(session_id=new_id)
        self._cache[new_id] = conv
        return conv

    def save(self, conv: Conversation):
        """保存对话到内存和文件"""
        self._cache[conv.session_id] = conv
        self._save_to_file(conv)

    def delete(self, session_id: str):
        """删除对话"""
        self._cache.pop(session_id, None)
        filepath = self._filepath(session_id)
        if os.path.exists(filepath):
            os.remove(filepath)

    def list_sessions(self) -> list[dict]:
        """列出所有会话（从文件扫描）"""
        sessions = []
        try:
            for filename in os.listdir(self.data_dir):
                if filename.endswith(".json"):
                    session_id = filename[:-5]
                    filepath = os.path.join(self.data_dir, filename)
                    try:
                        with open(filepath, "r", encoding="utf-8") as f:
                            data = json.load(f)
                        sessions.append({
                            "session_id": session_id,
                            "created_at": data.get("created_at", ""),
                            "updated_at": data.get("updated_at", ""),
                            "message_count": len(data.get("messages", [])),
                        })
                    except (json.JSONDecodeError, IOError):
                        continue
        except FileNotFoundError:
            pass

        sessions.sort(key=lambda s: s["updated_at"], reverse=True)
        return sessions

    # ── 私有方法 ──────────────────────────────────────

    def _filepath(self, session_id: str) -> str:
        return os.path.join(self.data_dir, f"{session_id}.json")

    def _load_from_file(self, session_id: str) -> Optional[Conversation]:
        """从 JSON 文件加载对话"""
        filepath = self._filepath(session_id)
        if not os.path.exists(filepath):
            return None
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            return Conversation.from_dict(data)
        except (json.JSONDecodeError, IOError):
            return None

    def _save_to_file(self, conv: Conversation):
        """保存对话到 JSON 文件"""
        filepath = self._filepath(conv.session_id)
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(conv.to_dict(), f, ensure_ascii=False, indent=2)
        except IOError as e:
            print(f"[WARN] 对话保存失败: {e}")
