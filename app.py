"""
兼容启动入口 — 保持旧版 app.py 兼容，内部使用新的 create_app。
"""
from companion import create_app
from flask import request, jsonify

app = create_app()


# ── 旧版 /api/chat 兼容层 ──────────────────────────────
# 内部调用新的 ChatService，前端最终应切换到 /api/v1

@app.route("/api/chat", methods=["POST"])
def legacy_chat():
    from companion.api.bootstrap import _get_or_create_client
    from companion.services.chat_service import ChatService
    from companion.repositories.conversation_repository import ConversationRepository
    from companion.extensions import db
    from flask import current_app

    data = request.get_json(force=True)
    if not data:
        return jsonify({"error": "请求体不能为空"}), 400

    message_text = str(data.get("message", ""))
    code = str(data.get("code", ""))
    error_text = str(data.get("error", ""))
    session_id = str(data.get("session_id", ""))

    if not message_text and not code and not error_text:
        return jsonify({"error": "请输入一些内容"}), 400

    client = _get_or_create_client()

    # 兼容旧 session_id → 创建或使用已有会话
    conv = None
    if session_id:
        conv = ConversationRepository.get_by_id(session_id, client.id)
    if conv is None:
        conv = ConversationRepository.create(client.id)
        db.session.flush()

    try:
        chat_service = ChatService()
        result = chat_service.process_message(
            client_id=client.id,
            conversation_id=conv.id,
            message_text=message_text,
            code=code,
            error_text=error_text,
        )
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "error": "服务暂时不可用",
            "reply": "抱歉，我现在遇到了一点问题。请稍后再试。",
            "scene": "general",
            "motivation": "",
            "session_id": conv.id,
        }), 500

    # 保留旧响应格式
    return jsonify({
        "reply": result["reply"],
        "scene": result["scene"],
        "motivation": result["motivation"],
        "session_id": conv.id,
    })


@app.route("/api/sessions", methods=["GET"])
def legacy_list_sessions():
    from companion.api.bootstrap import _get_or_create_client
    from companion.repositories.conversation_repository import ConversationRepository
    client = _get_or_create_client()
    convs = ConversationRepository.list_by_client(client.id)
    return jsonify({
        "sessions": [
            {
                "session_id": c.id,
                "created_at": c.created_at.isoformat() if c.created_at else "",
                "updated_at": c.updated_at.isoformat() if c.updated_at else "",
                "message_count": len(c.messages) if c.messages else 0,
            }
            for c in convs
        ]
    })


@app.route("/api/sessions/new", methods=["POST"])
def legacy_new_session():
    from companion.api.bootstrap import _get_or_create_client
    from companion.repositories.conversation_repository import ConversationRepository
    from companion.services.motivation import MotivationEngine
    from companion.extensions import db
    client = _get_or_create_client()
    conv = ConversationRepository.create(client.id)
    db.session.commit()
    return jsonify({"session_id": conv.id})


@app.route("/api/sessions/<session_id>", methods=["DELETE"])
def legacy_delete_session(session_id: str):
    from companion.api.bootstrap import _get_or_create_client
    from companion.repositories.conversation_repository import ConversationRepository
    from companion.services.motivation import MotivationEngine
    from companion.extensions import db
    client = _get_or_create_client()
    conv = ConversationRepository.get_by_id(session_id, client.id)
    if conv is None:
        return jsonify({"error": "会话不存在"}), 404
    ConversationRepository.delete(conv)
    MotivationEngine.reset_conversation(session_id)
    db.session.commit()
    return jsonify({"status": "deleted", "session_id": session_id})


@app.route("/api/sessions/<session_id>", methods=["GET"])
def legacy_get_session(session_id: str):
    from companion.api.bootstrap import _get_or_create_client
    from companion.repositories.conversation_repository import ConversationRepository
    client = _get_or_create_client()
    conv = ConversationRepository.get_by_id(session_id, client.id)
    if conv is None:
        return jsonify({"error": "会话不存在"}), 404
    return jsonify({
        "session_id": conv.id,
        "messages": [
            {
                "role": m.role,
                "content": m.content,
                "timestamp": m.created_at.isoformat() if m.created_at else "",
            }
            for m in sorted(conv.messages, key=lambda x: x.sequence_no) if conv.messages
        ],
        "created_at": conv.created_at.isoformat() if conv.created_at else "",
        "updated_at": conv.updated_at.isoformat() if conv.updated_at else "",
    })


if __name__ == "__main__":
    print("=" * 60)
    print("  程序设计学习智能学伴 — 小码")
    print("  Programming Learning Companion")
    print("=" * 60)
    print(f"  访问地址: http://127.0.0.1:5000")
    from companion.config import BaseConfig
    print(f"  DeepSeek 模型: {BaseConfig.DEEPSEEK_MODEL}")
    print("=" * 60)
    app.run(host="127.0.0.1", port=5000, debug=app.config.get("DEBUG", False))
