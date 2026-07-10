"""
聊天服务 — 核心编排逻辑
负责消息分类、情绪分析、Prompt 构建、LLM 调用、事件记录全流程。
"""
import json
import time
from datetime import datetime, timezone
from companion.extensions import db
from companion.llm.base import LLMGateway
from companion.llm.factory import create_llm_gateway
from companion.services.classifier import MessageClassifier
from companion.services.motivation import MotivationEngine
from companion.prompts.builder import build_system_prompt, build_user_message
from companion.utils.code_utils import detect_language, parse_error_info
from companion.repositories.conversation_repository import ConversationRepository
from companion.repositories.profile_repository import ProfileRepository
from companion.repositories.learning_repository import LearningRepository
from companion.repositories.reminder_repository import ReminderRepository
from companion.models import Message


class MessageInProgressError(RuntimeError):
    """相同幂等消息仍在处理中。"""


class ChatService:
    """聊天核心服务 — 无状态，通过依赖注入获取组件。"""

    def __init__(self, llm: LLMGateway | None = None):
        self.classifier = MessageClassifier()
        self._llm = llm

    @property
    def llm(self) -> LLMGateway:
        if self._llm is None:
            from flask import current_app
            self._llm = create_llm_gateway(current_app.config)
        return self._llm

    def process_message(
        self,
        client_id: str,
        conversation_id: str,
        message_text: str = "",
        code: str = "",
        error_text: str = "",
        client_message_id: str = "",
        scene_hint: str | None = None,
        language_hint: str = "",
    ) -> dict:
        """处理一条用户消息，返回 assistant 回复 + 元信息。

        处理顺序:
        1. 校验 + 所有权检查
        2. 幂等检查
        3. 保存用户消息
        4. 分类 + 语言检测 + 错误解析 + 情绪
        5. 构建 system prompt
        6. 调用 LLM（事务外）
        7. 保存 assistant 消息 + 事件 + 提醒
        8. 更新会话标题
        """
        t0 = time.monotonic()

        # 1. 校验 + 所有权
        conv = ConversationRepository.get_by_id(conversation_id, client_id)
        if conv is None:
            raise ValueError("Conversation not found")

        # 2. 幂等检查
        existing = None
        if client_message_id:
            existing = (
                db.session.query(Message)
                .filter_by(conversation_id=conversation_id, client_message_id=client_message_id, role="user")
                .first()
            )
            if existing:
                # 找到对应的 assistant 回复
                assistant = (
                    db.session.query(Message)
                    .filter_by(conversation_id=conversation_id, sequence_no=existing.sequence_no + 1, role="assistant")
                    .first()
                )
                if assistant:
                    return {
                        "reply": assistant.content,
                        "scene": assistant.scene or "general",
                        "motivation": assistant.motivation_text or "",
                        "message_id": assistant.id,
                        "status": "duplicate",
                    }
                if existing.status == "pending":
                    raise MessageInProgressError(client_message_id)

        # 3. 保存用户消息
        if existing is not None:
            user_msg = existing
            seq = existing.sequence_no
            user_msg.content = message_text
            user_msg.code = code if code else None
            user_msg.error_text = error_text if error_text else None
            user_msg.status = "pending"
        else:
            seq = ConversationRepository.get_next_sequence(conversation_id)
            user_msg = Message(
                conversation_id=conversation_id,
                sequence_no=seq,
                client_message_id=client_message_id or None,
                role="user",
                content=message_text,
                code=code if code else None,
                error_text=error_text if error_text else None,
                status="pending",
                created_at=datetime.now(timezone.utc),
            )
            db.session.add(user_msg)
        db.session.flush()

        # 4. 分类 + 检测
        valid_scenes = {"error", "guidance", "knowledge", "general"}
        if scene_hint in valid_scenes:
            scene = scene_hint
        else:
            result = self.classifier.classify(text=message_text, code=code, error=error_text)
            scene = result.scene

        detected_lang = detect_language(code, hint=language_hint) if code else "unknown"
        error_info = parse_error_info(error_text) if error_text else {}
        error_type = error_info.get("error_type", "")

        # 情绪分析（会话级）
        motive = MotivationEngine.for_conversation(
            conversation_id,
            consecutive_errors=conv.frustration_streak or 0,
            consecutive_success=conv.positive_streak or 0,
        )
        emotion_state = motive.analyze(message_text)
        emotion_hint = motive.build_emotion_hint(emotion_state)

        # 更新会话激励计数器
        conv.positive_streak = motive.consecutive_success
        conv.frustration_streak = motive.consecutive_errors
        if error_type:
            fingerprint = f"{error_type}"
            conv.last_error_fingerprint = fingerprint

        # 5. 构建 prompt
        profile = ProfileRepository.get_profile(client_id)
        profile_dict = {}
        if profile:
            profile_dict = {
                "nickname": profile.nickname or "未知",
                "skill_level": profile.skill_level or "beginner",
                "preferred_languages": profile.preferred_languages or "未设置",
                "learning_goal": profile.learning_goal or "未设置",
                "memory_summary": profile.memory_summary or "暂无",
            }

        system_prompt = build_system_prompt(
            scene=scene,
            emotion_hint=emotion_hint,
            profile=profile_dict,
        )

        user_content = build_user_message(
            text=message_text,
            code=code,
            error=error_text,
            scene=scene,
        )

        # 构建消息历史（最近 N 条）
        from flask import current_app
        max_msgs = current_app.config.get("MAX_CONTEXT_MESSAGES", 20)
        max_chars = current_app.config.get("MAX_CONTEXT_CHARS", 8000)

        history_desc = (
            db.session.query(Message)
            .filter(
                Message.conversation_id == conversation_id,
                Message.sequence_no < seq,
            )
            .order_by(Message.sequence_no.desc())
            .limit(max_msgs)
            .all()
        )

        llm_messages = [{"role": "system", "content": system_prompt}]
        total_chars = len(system_prompt)
        selected_history = []
        for h in history_desc:
            role = h.role
            text_content = h.content or ""
            if h.code:
                text_content += f"\n【代码】\n{h.code}"
            if h.error_text:
                text_content += f"\n【错误信息】\n{h.error_text}"
            if total_chars + len(text_content) > max_chars:
                break
            selected_history.append({"role": role, "content": text_content})
            total_chars += len(text_content)

        selected_history.reverse()
        llm_messages.extend(selected_history)
        llm_messages.append({"role": "user", "content": user_content})

        # 用户消息和会话状态先落库，模型等待期间不持有写事务。
        db.session.commit()

        # 6. 调用 LLM（事务外）
        temp_map = {
            "error": current_app.config.get("ERROR_TEMPERATURE", 0.3),
            "guidance": current_app.config.get("GUIDANCE_TEMPERATURE", 0.6),
            "knowledge": current_app.config.get("KNOWLEDGE_TEMPERATURE", 0.4),
            "general": current_app.config.get("GENERAL_TEMPERATURE", 0.7),
        }
        token_map = {
            "error": current_app.config.get("ERROR_MAX_TOKENS", 2048),
            "guidance": current_app.config.get("GUIDANCE_MAX_TOKENS", 2048),
            "knowledge": current_app.config.get("KNOWLEDGE_MAX_TOKENS", 2048),
            "general": current_app.config.get("GENERAL_MAX_TOKENS", 2048),
        }

        try:
            llm_resp = self.llm.chat(
                messages=llm_messages,
                temperature=temp_map.get(scene, 0.7),
                max_tokens=token_map.get(scene, 2048),
            )
            reply = llm_resp.content
            latency_ms = llm_resp.latency_ms
            input_tokens = llm_resp.input_tokens
            output_tokens = llm_resp.output_tokens
        except Exception:
            # LLM 调用失败，保留用户消息并允许相同幂等 ID 重试。
            user_msg.status = "failed"
            db.session.commit()
            raise

        # 7. 保存 assistant 消息
        motivation_text = ""
        praise = motive.get_praise()
        encourage = motive.get_encouragement()
        if praise:
            motivation_text = praise
        elif encourage:
            motivation_text = encourage
        elif emotion_state.is_frustrated:
            motivation_text = motive.get_comfort()

        assistant_msg = Message(
            conversation_id=conversation_id,
            sequence_no=seq + 1,
            role="assistant",
            content=reply,
            scene=scene,
            detected_language=detected_lang,
            error_type=error_type,
            emotion=emotion_hint,
            motivation_text=motivation_text,
            status="completed",
            prompt_version="2.0.0",
            latency_ms=latency_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            created_at=datetime.now(timezone.utc),
        )
        db.session.add(assistant_msg)

        # 更新用户消息状态
        user_msg.scene = scene
        user_msg.detected_language = detected_lang
        user_msg.error_type = error_type
        user_msg.status = "completed"

        # 8. 学习事件
        if scene == "error" and error_type:
            LearningRepository.record(
                client_id=client_id,
                event_type=error_type.replace("Error", "_error").lower() or "syntax_error",
                conversation_id=conversation_id,
                message_id=user_msg.id,
                language=detected_lang,
                error_type=error_type,
            )
        elif emotion_state.is_frustrated:
            LearningRepository.record(
                client_id=client_id,
                event_type="frustration",
                conversation_id=conversation_id,
                message_id=user_msg.id,
            )
        elif emotion_state.is_positive:
            LearningRepository.record(
                client_id=client_id,
                event_type="positive_progress",
                conversation_id=conversation_id,
                message_id=user_msg.id,
            )

        # 9. 检查提醒
        if error_type:
            recent_count = LearningRepository.count_recent_by_error_type(
                client_id, error_type, since_hours=24
            )
            if recent_count >= 3:
                ReminderRepository.create_if_new(
                    client_id=client_id,
                    dedupe_key=f"error_recurring:{error_type}",
                    reminder_type="error_recurring",
                    content=f"我注意到你最近遇到了多次 {error_type} 错误，要不要我帮你系统梳理一下相关的知识点？",
                )
        if emotion_state.consecutive_success >= 3:
            ReminderRepository.create_if_new(
                client_id=client_id,
                dedupe_key=f"positive_streak:{conversation_id}:3",
                reminder_type="positive_streak",
                content="你已经连续完成了三次积极推进。要不要趁热挑战一个稍难一点的知识点？",
            )

        # 10. 更新会话标题
        if not conv.title and message_text.strip():
            conv.title = message_text.strip()[:50]
        conv.updated_at = datetime.now(timezone.utc)

        db.session.commit()

        return {
            "reply": reply,
            "scene": scene,
            "motivation": motivation_text,
            "message_id": assistant_msg.id,
            "latency_ms": latency_ms,
        }
