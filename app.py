"""
Flask 主应用 — 路由与核心编排逻辑
作为"指挥中心"协调各模块，自身不包含重业务逻辑
"""
import traceback
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS

from config import Config
from services.llm_client import get_llm_client
from services.classifier import MessageClassifier
from services.motivation import MotivationEngine
from services.conversation import ConversationManager
from prompts.templates import build_system_prompt, build_user_message


app = Flask(__name__)
app.config["SECRET_KEY"] = Config.SECRET_KEY
CORS(app)

# ── 初始化全局组件 ──────────────────────────────────────
llm_client = get_llm_client()
classifier = MessageClassifier()
motivation = MotivationEngine()
conv_manager = ConversationManager()


# ═══════════════════════════════════════════════════════════
# 路由 1: 主页 — 聊天界面
# ═══════════════════════════════════════════════════════════

@app.route("/")
def index():
    """返回聊天界面"""
    return render_template("index.html")


# ═══════════════════════════════════════════════════════════
# 路由 2: 核心 API — 发送消息获取回复
# ═══════════════════════════════════════════════════════════

@app.route("/api/chat", methods=["POST"])
def chat():
    """
    接收用户消息，返回学伴回复。

    请求体 JSON:
        - message: str      用户文本
        - code: str         代码（可选）
        - error: str        错误信息（可选）
        - session_id: str   会话 ID（可选，首次自动创建）

    响应 JSON:
        - reply: str        学伴回复
        - scene: str        识别的场景
        - motivation: str   激励话术（可选）
        - session_id: str   会话 ID
    """
    try:
        data = request.get_json(force=True)
        if not data:
            return jsonify({"error": "请求体不能为空"}), 400

        user_text = data.get("message", "").strip()
        user_code = data.get("code", "").strip()
        user_error = data.get("error", "").strip()
        session_id = data.get("session_id", "").strip()

        # 至少需要一些输入
        if not user_text and not user_code and not user_error:
            return jsonify({"error": "请输入一些内容"}), 400

        # ── 步骤 1: 消息分类 ─────────────────────────
        result = classifier.classify(
            text=user_text,
            code=user_code,
            error=user_error,
        )

        # ── 步骤 2: 获取/创建对话 ────────────────────
        conv = conv_manager.get_or_create(session_id)

        # ── 步骤 3: 组装用户消息 ────────────────────
        user_content = build_user_message(
            text=user_text,
            code=user_code,
            error=user_error,
            scene=result.scene,
        )
        conv.add_message("user", user_content)

        # ── 步骤 4: 情绪分析 ────────────────────────
        emotion_state = motivation.analyze(user_text)
        emotion_hint = motivation.build_emotion_hint(emotion_state)

        # ── 步骤 5: 构建 system prompt ──────────────
        system_prompt = build_system_prompt(
            scene=result.scene,
            emotion_hint=emotion_hint,
        )

        # ── 步骤 6: 调用 LLM ────────────────────────
        messages = [{"role": "system", "content": system_prompt}]
        # 添加历史消息（最近 N 条）
        history = conv.get_recent_messages(Config.MAX_HISTORY_MESSAGES)
        messages.extend(history)

        temperature = {
            "error": Config.ERROR_TEMPERATURE,
            "guidance": Config.GUIDANCE_TEMPERATURE,
            "knowledge": Config.KNOWLEDGE_TEMPERATURE,
            "general": Config.GENERAL_TEMPERATURE,
        }.get(result.scene, 0.7)

        max_tokens = {
            "error": Config.ERROR_MAX_TOKENS,
            "guidance": Config.GUIDANCE_MAX_TOKENS,
            "knowledge": Config.KNOWLEDGE_MAX_TOKENS,
            "general": Config.GENERAL_MAX_TOKENS,
        }.get(result.scene, 2048)

        reply = llm_client.chat(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        # ── 步骤 7: 激励话术叠加 ────────────────────
        motivation_text = ""
        praise = motivation.get_praise()
        encourage = motivation.get_encouragement()

        if praise:
            motivation_text = praise
        elif encourage:
            motivation_text = encourage
        elif emotion_state.is_frustrated:
            motivation_text = motivation.get_comfort()

        final_reply = reply
        if motivation_text:
            final_reply = reply + "\n\n---\n*" + motivation_text + "*"

        # ── 步骤 8: 保存 + 返回 ────────────────────
        conv.add_message("assistant", final_reply)
        conv_manager.save(conv)

        return jsonify({
            "reply": final_reply,
            "scene": result.scene,
            "motivation": motivation_text,
            "session_id": conv.session_id,
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({
            "error": f"服务暂时不可用: {str(e)}",
            "reply": f"抱歉，我现在遇到了一点问题。请稍后再试。\n\n（错误信息: {str(e)}）",
            "scene": "general",
            "motivation": "小码也需要休息一下，马上就好～",
            "session_id": "",
        }), 500


# ═══════════════════════════════════════════════════════════
# 路由 3: 会话管理 — 列出/删除会话
# ═══════════════════════════════════════════════════════════

@app.route("/api/sessions", methods=["GET"])
def list_sessions():
    """列出所有会话"""
    try:
        sessions = conv_manager.list_sessions()
        return jsonify({"sessions": sessions})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/sessions/<session_id>", methods=["GET"])
def get_session(session_id: str):
    """获取指定会话的消息历史"""
    try:
        conv = conv_manager.get_or_create(session_id)
        messages = conv.get_recent_messages(limit=1000)
        return jsonify({
            "session_id": conv.session_id,
            "messages": messages,
            "created_at": conv.created_at,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/sessions/<session_id>", methods=["DELETE"])
def delete_session(session_id: str):
    """删除指定会话"""
    try:
        conv_manager.delete(session_id)
        # 同时重置激励计数器
        motivation.reset()
        return jsonify({"status": "deleted", "session_id": session_id})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/sessions/new", methods=["POST"])
def new_session():
    """创建新会话并返回 session_id"""
    conv = conv_manager.get_or_create()  # 不传 id 自动生成
    motivation.reset()
    return jsonify({"session_id": conv.session_id})


# ═══════════════════════════════════════════════════════════
# 启动入口
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("  程序设计学习智能学伴 — 小码")
    print("  Programming Learning Companion")
    print("=" * 60)
    print(f"  访问地址: http://127.0.0.1:5000")
    print(f"  DeepSeek 模型: {Config.DEEPSEEK_MODEL}")
    print(f"  数据目录: {Config.DATA_DIR}")
    print("=" * 60)

    app.run(host="127.0.0.1", port=5000, debug=Config.DEBUG)
