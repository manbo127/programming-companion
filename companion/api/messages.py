"""
消息 API — POST 发送消息获取回复
"""
from flask import Blueprint, request, current_app
from companion.extensions import db
from companion.services.chat_service import ChatService, MessageInProgressError
from companion.repositories.conversation_repository import ConversationRepository
from companion.api.errors import api_success, api_error
from companion.api.bootstrap import _get_or_create_client
from companion.utils.code_utils import SUPPORTED_LANGUAGES
from companion.llm.base import LLMProviderError

bp = Blueprint("messages", __name__, url_prefix="/api/v1")

# 合法场景枚举
VALID_SCENES = {"error", "guidance", "knowledge", "general"}


@bp.route("/conversations/<conv_id>/messages", methods=["POST"])
def send_message(conv_id: str):
    """发送消息并获取学伴回复。"""
    client = _get_or_create_client()

    # 校验 JSON
    data = request.get_json(silent=True)
    if data is None:
        return api_error("BAD_REQUEST", "请求体必须是 JSON", 400)

    # 校验字段类型和长度
    message_text = str(data.get("message", "") or "")
    code = str(data.get("code", "") or "")
    error_text = str(data.get("error", "") or "")
    client_message_id = str(data.get("client_message_id", "") or "")[:64]
    scene_hint = str(data.get("scene_hint", "") or "")
    language_hint = str(data.get("language_hint", "") or "")[:20]
    if language_hint and language_hint not in SUPPORTED_LANGUAGES:
        return api_error(
            "VALIDATION_ERROR",
            f"language_hint 必须为 {', '.join(SUPPORTED_LANGUAGES)} 之一",
            422,
        )

    limits = {
        "message": (message_text, current_app.config["MAX_MESSAGE_LENGTH"]),
        "code": (code, current_app.config["MAX_CODE_LENGTH"]),
        "error": (error_text, current_app.config["MAX_ERROR_LENGTH"]),
    }
    oversized = [name for name, (value, limit) in limits.items() if len(value) > limit]
    if oversized:
        return api_error("PAYLOAD_TOO_LARGE", f"字段过长: {', '.join(oversized)}", 413)

    # 至少需要一些输入
    if not message_text and not code and not error_text:
        return api_error("VALIDATION_ERROR", "请输入一些内容", 422)

    # 校验 scene_hint
    if scene_hint and scene_hint not in VALID_SCENES:
        return api_error("VALIDATION_ERROR", f"scene_hint 必须为 {', '.join(sorted(VALID_SCENES))} 之一", 422)

    # 所有权检查
    conv = ConversationRepository.get_by_id(conv_id, client.id)
    if conv is None:
        return api_error("NOT_FOUND", "会话不存在", 404)

    try:
        chat_service = ChatService()
        result = chat_service.process_message(
            client_id=client.id,
            conversation_id=conv_id,
            message_text=message_text,
            code=code,
            error_text=error_text,
            client_message_id=client_message_id,
            scene_hint=scene_hint,
            language_hint=language_hint,
        )
        db.session.commit()
    except MessageInProgressError:
        db.session.rollback()
        return api_error("MESSAGE_IN_PROGRESS", "这条消息仍在处理中，请稍后再试", 409)
    except ValueError as e:
        return api_error("NOT_FOUND", str(e), 404)
    except LLMProviderError as e:
        current_app.logger.warning("LLM provider failure code=%s retryable=%s", e.code, e.retryable)
        db.session.rollback()
        return api_error(e.code, str(e), e.status_code)
    except Exception:
        current_app.logger.exception("Chat error")
        db.session.rollback()
        return api_error("LLM_ERROR", "学伴暂时无法回复，请稍后重试", 502)

    return api_success({
        "reply": result["reply"],
        "scene": result["scene"],
        "motivation": result["motivation"],
        "sources": result.get("sources", []),
        "diagnosis": result.get("diagnosis"),
        "message_id": result["message_id"],
        "latency_ms": result.get("latency_ms"),
    })
