from flask import Flask, jsonify, request
from flask_cors import CORS

from config import Config
from intent_classifier import classify_intent
from llm_client import DeepSeekClient, LLMClientError
from memory_manager import append_message, get_recent_messages
from prompt_builder import build_messages


app = Flask(__name__)
app.config.from_object(Config)
CORS(app)

llm_client = DeepSeekClient(
    api_key=app.config["DEEPSEEK_API_KEY"],
    base_url=app.config["DEEPSEEK_BASE_URL"],
    model=app.config["DEEPSEEK_MODEL"],
    timeout=app.config["LLM_TIMEOUT"],
)


@app.get("/")
def index():
    return jsonify(
        {
            "name": "Programming Learning Companion Backend",
            "status": "running",
            "main_api": "/api/chat",
        }
    )


@app.get("/api/health")
def health_check():
    return jsonify({"success": True, "message": "backend is running"})


@app.post("/api/chat")
def chat():
    data = request.get_json(silent=True) or {}

    message = (data.get("message") or "").strip()
    code = (data.get("code") or "").strip()
    error = (data.get("error") or "").strip()
    scene = (data.get("scene") or "").strip()

    if not message and not code and not error:
        return (
            jsonify(
                {
                    "success": False,
                    "message": "请至少输入 message、code 或 error 中的一项。",
                }
            ),
            400,
        )

    intent = scene or classify_intent(message=message, code=code, error=error)
    recent_history = get_recent_messages(limit=app.config["CONTEXT_MESSAGE_LIMIT"])
    llm_messages = build_messages(
        intent=intent,
        message=message,
        code=code,
        error=error,
        history=recent_history,
    )

    try:
        reply = llm_client.chat(llm_messages)
    except LLMClientError as exc:
        return (
            jsonify(
                {
                    "success": False,
                    "scene": intent,
                    "message": str(exc),
                }
            ),
            502,
        )

    append_message(
        role="user",
        content=message,
        scene=intent,
        code=code,
        error=error,
    )
    append_message(role="assistant", content=reply, scene=intent)

    return jsonify(
        {
            "success": True,
            "scene": intent,
            "reply": reply,
        }
    )


@app.get("/api/history")
def history():
    limit = request.args.get("limit", default=50, type=int)
    return jsonify({"success": True, "data": get_recent_messages(limit=limit)})


@app.post("/api/clear")
def clear_history():
    from memory_manager import clear_messages

    clear_messages()
    return jsonify({"success": True, "message": "聊天记录已清空"})


if __name__ == "__main__":
    app.run(
        host=app.config["HOST"],
        port=app.config["PORT"],
        debug=app.config["DEBUG"],
    )
