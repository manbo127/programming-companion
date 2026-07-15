"""
用户画像 API
"""
from flask import Blueprint, request, current_app
from companion.extensions import db
from companion.repositories.profile_repository import ProfileRepository
from companion.services.profile_memory import ProfileMemoryService
from companion.api.errors import api_success, api_error
from companion.api.bootstrap import _get_or_create_client

bp = Blueprint("profile", __name__, url_prefix="/api/v1")

TEXT_FIELDS = {"nickname", "skill_level", "preferred_languages", "learning_goal", "feedback_style"}


def serialize_profile(profile):
    return {
        "nickname": profile.nickname,
        "skill_level": profile.skill_level,
        "preferred_languages": profile.preferred_languages,
        "learning_goal": profile.learning_goal,
        "feedback_style": profile.feedback_style or "balanced",
        "memory_summary": profile.memory_summary,
        "memory_enabled": bool(profile.memory_enabled),
        "memory_reset_at": profile.memory_reset_at.isoformat() if profile.memory_reset_at else None,
        "memory_updated_at": profile.memory_updated_at.isoformat() if profile.memory_updated_at else None,
    }


@bp.route("/profile", methods=["GET"])
def get_profile():
    client = _get_or_create_client()
    profile = ProfileRepository.get_or_create_profile(client.id)
    db.session.commit()
    return api_success(serialize_profile(profile))


@bp.route("/profile", methods=["PATCH"])
def update_profile():
    client = _get_or_create_client()
    data = request.get_json(silent=True) or {}
    updates = {k: str(v or "").strip()[:200] for k, v in data.items() if k in TEXT_FIELDS}
    has_memory_setting = "memory_enabled" in data
    if has_memory_setting and not isinstance(data["memory_enabled"], bool):
        return api_error("VALIDATION_ERROR", "memory_enabled 必须为布尔值", 422)
    if not updates:
        if not has_memory_setting:
            return api_error("VALIDATION_ERROR", "没有可更新的字段", 422)
    if "skill_level" in updates and updates["skill_level"] not in ("beginner", "intermediate"):
        return api_error("VALIDATION_ERROR", "skill_level 必须为 beginner 或 intermediate", 422)
    if "feedback_style" in updates and updates["feedback_style"] not in ("warm", "balanced", "concise"):
        return api_error("VALIDATION_ERROR", "feedback_style 必须为 warm、balanced 或 concise", 422)
    profile = ProfileRepository.get_or_create_profile(client.id)
    if updates:
        ProfileRepository.update_profile(profile, **updates)
    if has_memory_setting:
        ProfileMemoryService.set_enabled(profile, data["memory_enabled"])
    db.session.commit()
    return api_success(serialize_profile(profile))


@bp.route("/profile/memory", methods=["DELETE"])
def clear_profile_memory():
    """清除自动学习到的跨对话摘要，保留用户手动填写的画像。"""
    client = _get_or_create_client()
    profile = ProfileRepository.get_or_create_profile(client.id)
    ProfileMemoryService.clear(profile)
    db.session.commit()
    return api_success(serialize_profile(profile))


@bp.route("/profile/memory/refresh", methods=["POST"])
def refresh_profile_memory():
    """按需重新计算自动画像；正常聊天完成后也会自动执行。"""
    client = _get_or_create_client()
    profile = ProfileRepository.get_or_create_profile(client.id)
    if not profile.memory_enabled:
        return api_error("MEMORY_DISABLED", "跨对话记忆当前已关闭", 409)
    ProfileMemoryService.refresh(client.id)
    db.session.commit()
    return api_success(serialize_profile(profile))
