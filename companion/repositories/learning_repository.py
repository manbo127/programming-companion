"""
学习事件 Repository
"""
from datetime import datetime, timezone
from companion.extensions import db
from companion.models import LearningEvent


class LearningRepository:
    """学习事件存储。"""

    @staticmethod
    def record(
        client_id: str,
        event_type: str,
        conversation_id: str | None = None,
        message_id: int | None = None,
        topic: str | None = None,
        language: str | None = None,
        error_type: str | None = None,
        metadata_json: str | None = None,
    ) -> LearningEvent:
        event = LearningEvent(
            client_id=client_id,
            conversation_id=conversation_id,
            message_id=message_id,
            event_type=event_type,
            topic=topic,
            language=language,
            error_type=error_type,
            metadata_json=metadata_json,
            created_at=datetime.now(timezone.utc),
        )
        db.session.add(event)
        db.session.flush()
        return event

    @staticmethod
    def recent_events(client_id: str, limit: int = 50) -> list[LearningEvent]:
        return (
            db.session.query(LearningEvent)
            .filter_by(client_id=client_id)
            .order_by(LearningEvent.created_at.desc())
            .limit(limit)
            .all()
        )

    @staticmethod
    def count_recent_by_error_type(client_id: str, error_type: str, since_hours: int = 24) -> int:
        since = datetime.now(timezone.utc).timestamp() - (since_hours * 3600)
        return (
            db.session.query(LearningEvent)
            .filter(
                LearningEvent.client_id == client_id,
                LearningEvent.error_type == error_type,
                LearningEvent.created_at >= datetime.fromtimestamp(since, tz=timezone.utc),
            )
            .count()
        )
