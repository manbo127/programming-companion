"""跨对话学习画像记忆。

只从已经结构化的消息元数据生成摘要，不将原始用户文本提升到 system
prompt，从而降低持久化提示词注入和误记敏感信息的风险。
"""
from collections import Counter
from datetime import datetime, timezone
import re

from companion.extensions import db
from companion.models import Conversation, LearnerProfile, Message
from companion.repositories.profile_repository import ProfileRepository


class ProfileMemoryService:
    """生成、清除并控制匿名学习者的跨对话自动记忆。"""

    MAX_MESSAGES = 100
    MAX_ITEMS = 3
    SCENE_LABELS = {
        "error": "代码排错",
        "guidance": "解题引导",
        "knowledge": "知识讲解",
        "general": "自由交流",
    }
    LANGUAGE_LABELS = {
        "python": "Python",
        "java": "Java",
        "c": "C",
        "c语言": "C",
        "cpp": "C++",
        "c++": "C++",
        "javascript": "JavaScript",
        "typescript": "TypeScript",
        "go": "Go",
        "rust": "Rust",
        "sql": "SQL",
    }

    @classmethod
    def refresh(cls, client_id: str) -> LearnerProfile:
        """根据近期已完成消息重新生成安全、可解释的画像摘要。"""
        profile = ProfileRepository.get_or_create_profile(client_id)
        if not profile.memory_enabled:
            return profile

        query = (
            db.session.query(Message)
            .join(Conversation, Message.conversation_id == Conversation.id)
            .filter(
                Conversation.client_id == client_id,
                Message.role == "user",
                Message.status == "completed",
            )
        )
        if profile.memory_reset_at is not None:
            query = query.filter(Message.created_at >= profile.memory_reset_at)

        messages = (
            query.order_by(Message.created_at.desc(), Message.id.desc())
            .limit(cls.MAX_MESSAGES)
            .all()
        )

        scene_counts = Counter(m.scene for m in messages if m.scene in cls.SCENE_LABELS)
        language_counts = Counter(
            cls._language_label(m.detected_language)
            for m in messages
            if cls._language_label(m.detected_language)
        )
        error_counts = Counter(
            cls._safe_error_type(m.error_type)
            for m in messages
            if cls._safe_error_type(m.error_type)
        )

        parts = []
        if scene_counts:
            parts.append("近期主要活动：" + cls._format_counts(scene_counts, cls.SCENE_LABELS))
        if language_counts:
            parts.append("近期使用语言：" + cls._format_counts(language_counts))
        if error_counts:
            parts.append("近期遇到的错误：" + cls._format_counts(error_counts))

        profile.memory_summary = "；".join(parts) if parts else None
        profile.memory_updated_at = datetime.now(timezone.utc)
        db.session.flush()
        return profile

    @staticmethod
    def clear(profile: LearnerProfile) -> LearnerProfile:
        """清除自动摘要，并以当前时间作为新的记忆起点。"""
        now = datetime.now(timezone.utc)
        profile.memory_summary = None
        profile.memory_reset_at = now
        profile.memory_updated_at = now
        db.session.flush()
        return profile

    @classmethod
    def set_enabled(cls, profile: LearnerProfile, enabled: bool) -> LearnerProfile:
        """关闭时清除自动记忆；重新开启后仅学习新的互动。"""
        if profile.memory_enabled == enabled:
            return profile
        profile.memory_enabled = enabled
        if not enabled:
            cls.clear(profile)
        else:
            profile.memory_reset_at = datetime.now(timezone.utc)
            profile.memory_updated_at = profile.memory_reset_at
        db.session.flush()
        return profile

    @classmethod
    def _format_counts(cls, counts: Counter, labels: dict | None = None) -> str:
        items = []
        for value, count in counts.most_common(cls.MAX_ITEMS):
            label = labels.get(value, value) if labels else value
            items.append(f"{label}（{count} 次）")
        return "、".join(items)

    @classmethod
    def _language_label(cls, value: str | None) -> str:
        if not value or value == "unknown":
            return ""
        return cls.LANGUAGE_LABELS.get(value.strip().lower(), "")

    @staticmethod
    def _safe_error_type(value: str | None) -> str:
        if not value:
            return ""
        cleaned = re.sub(r"[^A-Za-z0-9_.+\-]", "", value)[:80]
        return cleaned
