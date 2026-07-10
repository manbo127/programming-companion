"""
对话 Repository — 数据访问层
"""
import uuid
from datetime import datetime, timezone
from typing import Optional
from companion.extensions import db
from companion.models import Conversation, Message


class ConversationRepository:
    """对话会话存储操作。"""

    @staticmethod
    def create(client_id: str, title: str | None = None) -> Conversation:
        conv = Conversation(
            id=str(uuid.uuid4()),
            client_id=client_id,
            title=title,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.session.add(conv)
        db.session.flush()
        return conv

    @staticmethod
    def get_by_id(conv_id: str, client_id: str) -> Optional[Conversation]:
        return (
            db.session.query(Conversation)
            .filter_by(id=conv_id, client_id=client_id)
            .first()
        )

    @staticmethod
    def list_by_client(client_id: str) -> list[Conversation]:
        return (
            db.session.query(Conversation)
            .filter_by(client_id=client_id)
            .order_by(Conversation.updated_at.desc())
            .all()
        )

    @staticmethod
    def update(conv: Conversation, **kwargs) -> Conversation:
        for k, v in kwargs.items():
            if hasattr(conv, k):
                setattr(conv, k, v)
        conv.updated_at = datetime.now(timezone.utc)
        db.session.flush()
        return conv

    @staticmethod
    def delete(conv: Conversation):
        db.session.delete(conv)
        db.session.flush()

    @staticmethod
    def get_next_sequence(conv_id: str) -> int:
        last = (
            db.session.query(Message.sequence_no)
            .filter_by(conversation_id=conv_id)
            .order_by(Message.sequence_no.desc())
            .first()
        )
        return (last[0] + 1) if last else 1
