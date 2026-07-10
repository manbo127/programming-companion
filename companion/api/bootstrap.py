"""
Bootstrap API — 初始化匿名学习者并返回概览数据
"""
from flask import Blueprint, g, request, current_app
from itsdangerous import BadSignature, URLSafeSerializer
from companion.extensions import db
from companion.repositories.profile_repository import ProfileRepository
from companion.repositories.conversation_repository import ConversationRepository
from companion.repositories.reminder_repository import ReminderRepository
from companion.api.errors import api_success
from companion.models import Client

bp = Blueprint("bootstrap", __name__, url_prefix="/api/v1")


def _get_or_create_client() -> Client:
    """从签名 Cookie 获取或创建匿名 client。"""
    cookie_name = current_app.config["CLIENT_COOKIE_NAME"]
    serializer = URLSafeSerializer(current_app.secret_key, salt="companion-client")
    signed_value = request.cookies.get(cookie_name, "")
    client_id = ""

    if signed_value:
        try:
            client_id = serializer.loads(signed_value)
        except BadSignature:
            current_app.logger.warning("Ignored an invalid client cookie")

    if not client_id:
        import uuid
        client_id = str(uuid.uuid4())
        g._new_client_cookie = serializer.dumps(client_id)

    client = ProfileRepository.get_or_create_client(client_id)
    db.session.flush()
    return client


@bp.route("/bootstrap", methods=["GET"])
def bootstrap():
    """返回当前学习者画像、最近会话、未读提醒。"""
    client = _get_or_create_client()
    profile = ProfileRepository.get_profile(client.id)
    conversations = ConversationRepository.list_by_client(client.id)[:5]
    reminders = ReminderRepository.unread_for_client(client.id)

    data = {
        "client_id": client.id,
        "profile": {
            "nickname": profile.nickname if profile else None,
            "skill_level": profile.skill_level if profile else "beginner",
            "preferred_languages": profile.preferred_languages if profile else None,
            "learning_goal": profile.learning_goal if profile else None,
        } if profile else {},
        "recent_conversations": [
            {
                "id": c.id,
                "title": c.title or "未命名对话",
                "updated_at": c.updated_at.isoformat() if c.updated_at else None,
                "message_count": len(c.messages) if c.messages else 0,
            }
            for c in conversations
        ],
        "unread_reminders": [
            {
                "id": r.id,
                "type": r.reminder_type,
                "content": r.content,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in reminders
        ],
    }

    resp = api_success(data)
    # 设置 client cookie（HttpOnly + SameSite）
    new_cookie = getattr(g, "_new_client_cookie", None)
    if new_cookie:
        resp.set_cookie(
            current_app.config["CLIENT_COOKIE_NAME"],
            new_cookie,
            max_age=current_app.config["CLIENT_COOKIE_MAX_AGE"],
            httponly=True,
            samesite="Lax",
            secure=current_app.config.get("CLIENT_COOKIE_SECURE", False),
        )
    return resp
