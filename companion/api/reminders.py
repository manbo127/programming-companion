"""
提醒 API
"""
from flask import Blueprint
from companion.extensions import db
from companion.repositories.reminder_repository import ReminderRepository
from companion.api.errors import api_success, api_error
from companion.api.bootstrap import _get_or_create_client
from companion.services.review_plan import ReviewPlanService

bp = Blueprint("reminders", __name__, url_prefix="/api/v1")


@bp.route("/reminders", methods=["GET"])
def list_reminders():
    client = _get_or_create_client()
    ReviewPlanService.materialize_due(client.id)
    db.session.commit()
    reminders = ReminderRepository.unread_for_client(client.id)
    return api_success([
        {
            "id": r.id,
            "type": r.reminder_type,
            "content": r.content,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in reminders
    ])


@bp.route("/reminders/<int:reminder_id>/read", methods=["POST"])
def mark_read(reminder_id: int):
    client = _get_or_create_client()
    reminder = ReminderRepository.get_by_id(reminder_id, client.id)
    if reminder is None:
        return api_error("NOT_FOUND", "提醒不存在", 404)
    ReminderRepository.mark_read(reminder)
    db.session.commit()
    return api_success({"status": "read"})


@bp.route("/reminders/<int:reminder_id>/dismiss", methods=["POST"])
def dismiss(reminder_id: int):
    client = _get_or_create_client()
    reminder = ReminderRepository.get_by_id(reminder_id, client.id)
    if reminder is None:
        return api_error("NOT_FOUND", "提醒不存在", 404)
    ReminderRepository.dismiss(reminder)
    db.session.commit()
    return api_success({"status": "dismissed"})
