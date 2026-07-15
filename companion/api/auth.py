"""可选账号体系：匿名可用，注册后保留当前学习数据。"""
import re
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from flask import Blueprint, current_app, g
from flask import request
from werkzeug.security import check_password_hash, generate_password_hash

from companion.api.bootstrap import _get_or_create_client, _switch_client_cookie
from companion.api.errors import api_error, api_success
from companion.extensions import db
from companion.models import AccountSession, Client
from companion.repositories.profile_repository import ProfileRepository


bp = Blueprint("auth", __name__, url_prefix="/api/v1/auth")
EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
MAX_FAILURES = 5
LOCK_MINUTES = 15


def _credentials():
    data = request.get_json(silent=True) or {}
    email = str(data.get("email", "") or "").strip().lower()[:254]
    password = str(data.get("password", "") or "")
    if not EMAIL_RE.fullmatch(email):
        return None, None, api_error("VALIDATION_ERROR", "请输入有效邮箱", 422)
    if not 8 <= len(password) <= 128:
        return None, None, api_error("VALIDATION_ERROR", "密码长度必须为 8–128 位", 422)
    return email, password, None


def _account(client: Client) -> dict:
    return {
        "authenticated": not client.is_anonymous,
        "email": client.email if not client.is_anonymous else None,
    }


def _new_account_session(client: Client):
    now = datetime.now(timezone.utc)
    raw_token = secrets.token_urlsafe(32)
    session = AccountSession(
        client_id=client.id,
        token_hash=hashlib.sha256(raw_token.encode()).hexdigest(),
        created_at=now,
        last_seen_at=now,
        expires_at=now + timedelta(seconds=current_app.config["ACCOUNT_SESSION_MAX_AGE"]),
    )
    db.session.add(session)
    db.session.flush()
    return session, raw_token


@bp.get("/me")
def me():
    return api_success(_account(_get_or_create_client()))


@bp.post("/register")
def register():
    client = _get_or_create_client()
    if not client.is_anonymous:
        return api_error("ALREADY_AUTHENTICATED", "当前已经登录", 409)
    email, password, error = _credentials()
    if error is not None:
        return error
    if db.session.query(Client.id).filter(Client.email == email).first():
        return api_error("EMAIL_EXISTS", "该邮箱已注册", 409)
    client.email = email
    client.password_hash = generate_password_hash(password)
    client.is_anonymous = False
    client.failed_login_attempts = 0
    client.last_login_at = datetime.now(timezone.utc)
    ProfileRepository.get_or_create_profile(client.id)
    session, raw_token = _new_account_session(client)
    db.session.commit()
    _switch_client_cookie(client.id, session.id, raw_token)
    return api_success(_account(client), status=201)


@bp.post("/login")
def login():
    _get_or_create_client()  # 确保请求拥有合法的签名身份，但不信任请求体中的用户 ID。
    email, password, error = _credentials()
    if error is not None:
        return error
    account = db.session.query(Client).filter(Client.email == email, Client.is_anonymous.is_(False)).first()
    now = datetime.now(timezone.utc)
    locked_until = account.locked_until if account else None
    if locked_until and locked_until.tzinfo is None:
        locked_until = locked_until.replace(tzinfo=timezone.utc)
    if account and locked_until and locked_until > now:
        return api_error("ACCOUNT_LOCKED", "登录失败次数过多，请稍后再试", 429)
    if not account or not account.password_hash or not check_password_hash(account.password_hash, password):
        if account:
            account.failed_login_attempts = (account.failed_login_attempts or 0) + 1
            if account.failed_login_attempts >= MAX_FAILURES:
                account.locked_until = now + timedelta(minutes=LOCK_MINUTES)
            db.session.commit()
        return api_error("INVALID_CREDENTIALS", "邮箱或密码不正确", 401)
    account.failed_login_attempts = 0
    account.locked_until = None
    account.last_login_at = now
    account.last_seen_at = now
    previous_session = getattr(g, "_current_account_session", None)
    if previous_session:
        previous_session.revoked_at = now
    session, raw_token = _new_account_session(account)
    db.session.commit()
    _switch_client_cookie(account.id, session.id, raw_token)
    return api_success(_account(account))


@bp.post("/logout")
def logout():
    import uuid

    _get_or_create_client()
    active_session = getattr(g, "_current_account_session", None)
    if active_session:
        active_session.revoked_at = datetime.now(timezone.utc)
    anonymous = Client(id=str(uuid.uuid4()), is_anonymous=True)
    db.session.add(anonymous)
    db.session.commit()
    _switch_client_cookie(anonymous.id)
    return api_success(_account(anonymous))
