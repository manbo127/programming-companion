"""
学习概览 API
"""
from flask import Blueprint, request
from companion.repositories.learning_repository import LearningRepository
from companion.repositories.reminder_repository import ReminderRepository
from companion.services.learning_analytics import LearningAnalyticsService
from companion.api.errors import api_success
from companion.api.bootstrap import _get_or_create_client

bp = Blueprint("learning", __name__, url_prefix="/api/v1")


@bp.route("/learning/overview", methods=["GET"])
def learning_overview():
    client = _get_or_create_client()
    try:
        days = min(max(int(request.args.get("days", 30)), 7), 90)
    except (TypeError, ValueError):
        days = 30
    return api_success(LearningAnalyticsService.overview(client.id, days=days))


@bp.route("/learning/events", methods=["GET"])
def learning_events():
    client = _get_or_create_client()
    try:
        limit = min(max(int(request.args.get("limit", 20)), 1), 100)
    except (TypeError, ValueError):
        limit = 20
    events = LearningRepository.recent_events(client.id, limit=limit)
    return api_success([
        {
            "id": e.id,
            "event_type": e.event_type,
            "topic": e.topic,
            "language": e.language,
            "error_type": e.error_type,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }
        for e in events
    ])
