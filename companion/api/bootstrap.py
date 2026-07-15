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
from companion.models import AccountSession, Client
from datetime import datetime, timezone
import hashlib
import hmac

bp = Blueprint("bootstrap", __name__, url_prefix="/api/v1")


def _switch_client_cookie(client_id: str, session_id: str | None = None, session_token: str | None = None):
    """让后续响应切换到指定身份；Cookie 内容始终经过签名。"""
    serializer = URLSafeSerializer(current_app.secret_key, salt="companion-client")
    payload = client_id
    if session_id and session_token:
        payload = {"v": 2, "c": client_id, "s": session_id, "t": session_token}
    g._new_client_cookie = serializer.dumps(payload)


def _as_aware(value):
    if value is not None and value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _get_or_create_client() -> Client:
    """从签名 Cookie 获取或创建匿名 client。"""
    cookie_name = current_app.config["CLIENT_COOKIE_NAME"]
    serializer = URLSafeSerializer(current_app.secret_key, salt="companion-client")
    signed_value = request.cookies.get(cookie_name, "")
    client = None

    if signed_value:
        try:
            payload = serializer.loads(signed_value)
            if isinstance(payload, str):
                candidate = db.session.get(Client, payload)
                # 旧格式仅允许匿名身份，注册账号必须持有可撤销服务端会话。
                if candidate and candidate.is_anonymous:
                    client = candidate
            elif isinstance(payload, dict) and payload.get("v") == 2:
                candidate = db.session.get(Client, str(payload.get("c", "")))
                session = db.session.get(AccountSession, str(payload.get("s", "")))
                token_hash = hashlib.sha256(str(payload.get("t", "")).encode()).hexdigest()
                now = datetime.now(timezone.utc)
                if (
                    candidate and not candidate.is_anonymous and session
                    and session.client_id == candidate.id and session.revoked_at is None
                    and _as_aware(session.expires_at) > now
                    and hmac.compare_digest(session.token_hash, token_hash)
                ):
                    session.last_seen_at = now
                    g._current_account_session = session
                    client = candidate
        except BadSignature:
            current_app.logger.warning("Ignored an invalid client cookie")

    if client is None:
        import uuid
        client = Client(id=str(uuid.uuid4()), is_anonymous=True)
        db.session.add(client)
        db.session.flush()
        _switch_client_cookie(client.id)

    client.last_seen_at = datetime.now(timezone.utc)
    db.session.flush()
    return client


@bp.route("/bootstrap", methods=["GET"])
def bootstrap():
    """返回当前学习者画像、最近会话、未读提醒。"""
    client = _get_or_create_client()
    profile = ProfileRepository.get_profile(client.id)
    conversations = [
        conv for conv in ConversationRepository.list_by_client(client.id)
        if conv.title or conv.messages
    ][:5]
    reminders = ReminderRepository.unread_for_client(client.id)

    data = {
        "client_id": client.id,
        "account": {
            "authenticated": not client.is_anonymous,
            "email": client.email if not client.is_anonymous else None,
        },
        "profile": {
            "nickname": profile.nickname if profile else None,
            "skill_level": profile.skill_level if profile else "beginner",
            "preferred_languages": profile.preferred_languages if profile else None,
            "learning_goal": profile.learning_goal if profile else None,
            "feedback_style": profile.feedback_style if profile else "balanced",
            "memory_summary": profile.memory_summary if profile else None,
            "memory_enabled": bool(profile.memory_enabled) if profile else True,
            "memory_reset_at": profile.memory_reset_at.isoformat() if profile and profile.memory_reset_at else None,
            "memory_updated_at": profile.memory_updated_at.isoformat() if profile and profile.memory_updated_at else None,
        } if profile else {},
        "recent_conversations": [
            {
                "id": c.id,
                "title": c.title or "新的对话",
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

    # Bootstrap 可能刚创建匿名学习者；必须持久化后再把签名身份发给浏览器。
    db.session.commit()

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
