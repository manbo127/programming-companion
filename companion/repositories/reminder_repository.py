"""
提醒 Repository
"""
from datetime import datetime, timezone
from companion.extensions import db
from companion.models import Reminder


class ReminderRepository:
    """学习提醒存储。"""

    @staticmethod
    def create_if_new(client_id: str, dedupe_key: str, reminder_type: str, content: str) -> Reminder | None:
        existing = (
            db.session.query(Reminder)
            .filter_by(client_id=client_id, dedupe_key=dedupe_key)
            .first()
        )
        if existing:
            return None
        reminder = Reminder(
            client_id=client_id,
            dedupe_key=dedupe_key,
            reminder_type=reminder_type,
            content=content,
            created_at=datetime.now(timezone.utc),
        )
        db.session.add(reminder)
        db.session.flush()
        return reminder

    @staticmethod
    def unread_for_client(client_id: str) -> list[Reminder]:
        return (
            db.session.query(Reminder)
            .filter_by(client_id=client_id, status="unread")
            .order_by(Reminder.created_at.desc())
            .all()
        )

    @staticmethod
    def mark_read(reminder: Reminder):
        reminder.status = "read"
        reminder.read_at = datetime.now(timezone.utc)
        db.session.flush()

    @staticmethod
    def dismiss(reminder: Reminder):
        reminder.status = "dismissed"
        reminder.read_at = datetime.now(timezone.utc)
        db.session.flush()

    @staticmethod
    def get_by_id(reminder_id: int, client_id: str) -> Reminder | None:
        return (
            db.session.query(Reminder)
            .filter_by(id=reminder_id, client_id=client_id)
            .first()
        )
