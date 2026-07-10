"""
用户画像 API
"""
from flask import Blueprint, request, current_app
from companion.extensions import db
from companion.repositories.profile_repository import ProfileRepository
from companion.api.errors import api_success, api_error
from companion.api.bootstrap import _get_or_create_client

bp = Blueprint("profile", __name__, url_prefix="/api/v1")

ALLOWED_FIELDS = {"nickname", "skill_level", "preferred_languages", "learning_goal"}


@bp.route("/profile", methods=["GET"])
def get_profile():
    client = _get_or_create_client()
    profile = ProfileRepository.get_or_create_profile(client.id)
    return api_success({
        "nickname": profile.nickname,
        "skill_level": profile.skill_level,
        "preferred_languages": profile.preferred_languages,
        "learning_goal": profile.learning_goal,
    })


@bp.route("/profile", methods=["PATCH"])
def update_profile():
    client = _get_or_create_client()
    data = request.get_json(silent=True) or {}
    updates = {k: str(v)[:200] for k, v in data.items() if k in ALLOWED_FIELDS}
    if not updates:
        return api_error("VALIDATION_ERROR", "没有可更新的字段", 422)
    if "skill_level" in updates and updates["skill_level"] not in ("beginner", "intermediate"):
        return api_error("VALIDATION_ERROR", "skill_level 必须为 beginner 或 intermediate", 422)
    profile = ProfileRepository.get_or_create_profile(client.id)
    ProfileRepository.update_profile(profile, **updates)
    db.session.commit()
    return api_success({
        "nickname": profile.nickname,
        "skill_level": profile.skill_level,
        "preferred_languages": profile.preferred_languages,
        "learning_goal": profile.learning_goal,
    })
