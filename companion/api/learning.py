"""
学习概览 API
"""
from flask import Blueprint, request
from companion.repositories.learning_repository import LearningRepository
from companion.repositories.reminder_repository import ReminderRepository
from companion.api.errors import api_success
from companion.api.bootstrap import _get_or_create_client

bp = Blueprint("learning", __name__, url_prefix="/api/v1")


@bp.route("/learning/overview", methods=["GET"])
def learning_overview():
    client = _get_or_create_client()
    events = LearningRepository.recent_events(client.id, limit=50)
    error_types = {}
    topics = set()
    languages = set()
    for e in events:
        if e.error_type:
            error_types[e.error_type] = error_types.get(e.error_type, 0) + 1
        if e.topic:
            topics.add(e.topic)
        if e.language and e.language != "unknown":
            languages.add(e.language)

    return api_success({
        "total_events": len(events),
        "top_error_types": sorted(error_types.items(), key=lambda x: x[1], reverse=True)[:5],
        "recent_topics": list(topics),
        "languages_used": list(languages),
    })


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
