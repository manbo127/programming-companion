"""
会话 API — CRUD
"""
import json
from flask import Blueprint, g, request
from companion.extensions import db
from companion.repositories.profile_repository import ProfileRepository
from companion.repositories.conversation_repository import ConversationRepository
from companion.services.motivation import MotivationEngine
from companion.api.errors import api_success, api_error
from companion.api.bootstrap import _get_or_create_client

bp = Blueprint("conversations", __name__, url_prefix="/api/v1")


@bp.route("/conversations", methods=["POST"])
def create_conversation():
    client = _get_or_create_client()
    data = request.get_json(silent=True) or {}
    title = str(data.get("title", "") or "")[:200] or None
    conv = ConversationRepository.create(client.id, title=title)
    db.session.commit()
    return api_success({
        "id": conv.id,
        "title": conv.title,
        "created_at": conv.created_at.isoformat(),
    }, status=201)


@bp.route("/conversations", methods=["GET"])
def list_conversations():
    client = _get_or_create_client()
    # 旧版本会在打开首页时提前创建空会话；不再把这些幽灵记录展示给用户。
    convs = [
        conv for conv in ConversationRepository.list_by_client(client.id)
        if conv.title or conv.messages
    ]
    return api_success([
        {
            "id": c.id,
            "title": c.title or "新的对话",
            "updated_at": c.updated_at.isoformat() if c.updated_at else None,
            "message_count": len(c.messages) if c.messages else 0,
        }
        for c in convs
    ])


@bp.route("/conversations/<conv_id>", methods=["GET"])
def get_conversation(conv_id: str):
    client = _get_or_create_client()
    conv = ConversationRepository.get_by_id(conv_id, client.id)
    if conv is None:
        return api_error("NOT_FOUND", "会话不存在", 404)
    return api_success({
        "id": conv.id,
        "title": conv.title,
        "summary": conv.summary,
        "positive_streak": conv.positive_streak,
        "frustration_streak": conv.frustration_streak,
        "created_at": conv.created_at.isoformat() if conv.created_at else None,
        "updated_at": conv.updated_at.isoformat() if conv.updated_at else None,
    })


@bp.route("/conversations/<conv_id>", methods=["PATCH"])
def update_conversation(conv_id: str):
    client = _get_or_create_client()
    conv = ConversationRepository.get_by_id(conv_id, client.id)
    if conv is None:
        return api_error("NOT_FOUND", "会话不存在", 404)
    data = request.get_json(silent=True) or {}
    if "title" in data:
        title = str(data["title"] or "").strip()[:200]
        if not title:
            return api_error("VALIDATION_ERROR", "对话名称不能为空", 422)
        conv = ConversationRepository.update(conv, title=title)
    db.session.commit()
    return api_success({"id": conv.id, "title": conv.title})


@bp.route("/conversations/<conv_id>", methods=["DELETE"])
def delete_conversation(conv_id: str):
    client = _get_or_create_client()
    conv = ConversationRepository.get_by_id(conv_id, client.id)
    if conv is None:
        return api_error("NOT_FOUND", "会话不存在", 404)
    ConversationRepository.delete(conv)
    MotivationEngine.reset_conversation(conv_id)
    db.session.commit()
    return api_success({"deleted": conv_id})


@bp.route("/conversations/<conv_id>/messages", methods=["GET"])
def list_messages(conv_id: str):
    client = _get_or_create_client()
    conv = ConversationRepository.get_by_id(conv_id, client.id)
    if conv is None:
        return api_error("NOT_FOUND", "会话不存在", 404)
    msgs = sorted(conv.messages, key=lambda m: m.sequence_no) if conv.messages else []
    return api_success([
        {
            "id": m.id,
            "sequence_no": m.sequence_no,
            "role": m.role,
            "content": m.content,
            "code": m.code,
            "error_text": m.error_text,
            "scene": m.scene,
            "detected_language": m.detected_language,
            "error_type": m.error_type,
            "emotion": m.emotion,
            "emotion_score": m.emotion_score,
            "motivation_text": m.motivation_text,
            "sources": json.loads(m.sources_json) if m.sources_json else [],
            "diagnosis": json.loads(m.diagnosis_json) if m.diagnosis_json else None,
            "status": m.status,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        }
        for m in msgs
    ])
