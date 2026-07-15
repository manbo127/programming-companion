"""
数据模型 — SQLAlchemy ORM
"""
import uuid
from datetime import datetime, timezone
from companion.extensions import db


def _utcnow():
    return datetime.now(timezone.utc)


def _new_uuid() -> str:
    return str(uuid.uuid4())


class Client(db.Model):
    """匿名学习者。"""
    __tablename__ = "clients"

    id = db.Column(db.String(36), primary_key=True, default=_new_uuid)
    created_at = db.Column(db.DateTime, nullable=False, default=_utcnow)
    last_seen_at = db.Column(db.DateTime, nullable=False, default=_utcnow)
    email = db.Column(db.String(254), nullable=True, unique=True, index=True)
    password_hash = db.Column(db.String(255), nullable=True)
    is_anonymous = db.Column(db.Boolean, nullable=False, default=True)
    failed_login_attempts = db.Column(db.Integer, nullable=False, default=0)
    locked_until = db.Column(db.DateTime, nullable=True)
    last_login_at = db.Column(db.DateTime, nullable=True)

    # 关系
    profile = db.relationship("LearnerProfile", back_populates="client", uselist=False,
                              cascade="all, delete-orphan")
    conversations = db.relationship("Conversation", back_populates="client",
                                    cascade="all, delete-orphan")
    learning_events = db.relationship("LearningEvent", back_populates="client",
                                      cascade="all, delete-orphan")
    reminders = db.relationship("Reminder", back_populates="client",
                                cascade="all, delete-orphan")
    review_plans = db.relationship("ReviewPlan", back_populates="client",
                                   cascade="all, delete-orphan")
    account_sessions = db.relationship("AccountSession", back_populates="client",
                                       cascade="all, delete-orphan")


class AccountSession(db.Model):
    """注册账号的可撤销设备会话。"""
    __tablename__ = "account_sessions"

    id = db.Column(db.String(36), primary_key=True, default=_new_uuid)
    client_id = db.Column(db.String(36), db.ForeignKey("clients.id", ondelete="CASCADE"),
                          nullable=False, index=True)
    token_hash = db.Column(db.String(64), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=_utcnow)
    last_seen_at = db.Column(db.DateTime, nullable=False, default=_utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    revoked_at = db.Column(db.DateTime, nullable=True)

    client = db.relationship("Client", back_populates="account_sessions")


class LearnerProfile(db.Model):
    """学习者画像，与 Client 一一对应。"""
    __tablename__ = "learner_profiles"

    client_id = db.Column(db.String(36), db.ForeignKey("clients.id", ondelete="CASCADE"),
                          primary_key=True)
    nickname = db.Column(db.String(50), nullable=True)
    skill_level = db.Column(db.String(20), nullable=True, default="beginner")
    preferred_languages = db.Column(db.Text, nullable=True)  # JSON array
    learning_goal = db.Column(db.Text, nullable=True)
    feedback_style = db.Column(db.String(20), nullable=False, default="balanced")
    memory_summary = db.Column(db.Text, nullable=True)
    memory_enabled = db.Column(db.Boolean, nullable=False, default=True)
    memory_reset_at = db.Column(db.DateTime, nullable=True)
    memory_updated_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=_utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=_utcnow, onupdate=_utcnow)

    client = db.relationship("Client", back_populates="profile")


class Conversation(db.Model):
    """对话会话。"""
    __tablename__ = "conversations"

    id = db.Column(db.String(36), primary_key=True, default=_new_uuid)
    client_id = db.Column(db.String(36), db.ForeignKey("clients.id", ondelete="CASCADE"),
                          nullable=False, index=True)
    title = db.Column(db.String(200), nullable=True)
    summary = db.Column(db.Text, nullable=True)
    positive_streak = db.Column(db.Integer, nullable=False, default=0)
    frustration_streak = db.Column(db.Integer, nullable=False, default=0)
    last_error_fingerprint = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=_utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=_utcnow, onupdate=_utcnow)

    client = db.relationship("Client", back_populates="conversations")
    messages = db.relationship("Message", back_populates="conversation",
                               cascade="all, delete-orphan",
                               order_by="Message.sequence_no")


class Message(db.Model):
    """对话消息。"""
    __tablename__ = "messages"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    conversation_id = db.Column(db.String(36),
                                db.ForeignKey("conversations.id", ondelete="CASCADE"),
                                nullable=False, index=True)
    sequence_no = db.Column(db.Integer, nullable=False)
    client_message_id = db.Column(db.String(64), nullable=True)
    role = db.Column(db.String(16), nullable=False)  # user / assistant
    content = db.Column(db.Text, nullable=False, default="")
    code = db.Column(db.Text, nullable=True)
    error_text = db.Column(db.Text, nullable=True)
    scene = db.Column(db.String(20), nullable=True)  # error/guidance/knowledge/general
    detected_language = db.Column(db.String(20), nullable=True)
    error_type = db.Column(db.String(100), nullable=True)
    emotion = db.Column(db.String(20), nullable=True)
    emotion_score = db.Column(db.Float, nullable=True)
    motivation_text = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), nullable=False, default="completed")
    prompt_version = db.Column(db.String(20), nullable=True)
    latency_ms = db.Column(db.Integer, nullable=True)
    input_tokens = db.Column(db.Integer, nullable=True)
    output_tokens = db.Column(db.Integer, nullable=True)
    llm_model = db.Column(db.String(100), nullable=True)
    llm_request_id = db.Column(db.String(100), nullable=True)
    llm_attempts = db.Column(db.Integer, nullable=True)
    finish_reason = db.Column(db.String(50), nullable=True)
    sources_json = db.Column(db.Text, nullable=True)
    diagnosis_json = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=_utcnow)

    conversation = db.relationship("Conversation", back_populates="messages")

    __table_args__ = (
        db.UniqueConstraint("conversation_id", "sequence_no", name="uq_msg_seq"),
        db.UniqueConstraint("conversation_id", "client_message_id", name="uq_msg_client_id"),
        db.Index("ix_msg_conv_seq", "conversation_id", "sequence_no"),
        db.Index("ix_msg_conv_created", "conversation_id", "created_at"),
    )


class LearningEvent(db.Model):
    """学习事件记录。"""
    __tablename__ = "learning_events"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    client_id = db.Column(db.String(36), db.ForeignKey("clients.id", ondelete="CASCADE"),
                          nullable=False, index=True)
    conversation_id = db.Column(db.String(36), nullable=True)
    message_id = db.Column(db.Integer, nullable=True)
    event_type = db.Column(db.String(50), nullable=False)
    topic = db.Column(db.String(200), nullable=True)
    language = db.Column(db.String(20), nullable=True)
    error_type = db.Column(db.String(100), nullable=True)
    metadata_json = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=_utcnow)

    client = db.relationship("Client", back_populates="learning_events")


class Reminder(db.Model):
    """学习提醒。"""
    __tablename__ = "reminders"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    client_id = db.Column(db.String(36), db.ForeignKey("clients.id", ondelete="CASCADE"),
                          nullable=False, index=True)
    dedupe_key = db.Column(db.String(200), nullable=False)
    reminder_type = db.Column(db.String(50), nullable=False)
    content = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="unread")
    created_at = db.Column(db.DateTime, nullable=False, default=_utcnow)
    read_at = db.Column(db.DateTime, nullable=True)

    client = db.relationship("Client", back_populates="reminders")

    __table_args__ = (
        db.UniqueConstraint("client_id", "dedupe_key", name="uq_reminder_dedupe"),
    )


class ReviewPlan(db.Model):
    """基于知识点的间隔复习计划。"""
    __tablename__ = "review_plans"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    client_id = db.Column(db.String(36), db.ForeignKey("clients.id", ondelete="CASCADE"),
                          nullable=False, index=True)
    topic = db.Column(db.String(200), nullable=False)
    reason = db.Column(db.String(50), nullable=False, default="practice")
    interval_index = db.Column(db.Integer, nullable=False, default=0)
    next_review_at = db.Column(db.DateTime, nullable=False)
    last_reviewed_at = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(20), nullable=False, default="active")
    created_at = db.Column(db.DateTime, nullable=False, default=_utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=_utcnow, onupdate=_utcnow)

    client = db.relationship("Client", back_populates="review_plans")

    __table_args__ = (
        db.UniqueConstraint("client_id", "topic", name="uq_review_plan_client_topic"),
    )
