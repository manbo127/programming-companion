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
from companion.services.profile_memory import ProfileMemoryService
from companion.services.context_memory import ContextMemoryService
from companion.services.topic_extractor import TopicExtractor
from companion.services.review_plan import ReviewPlanService
from companion.knowledge import KnowledgeRetriever
from companion.services.problem_guidance import ProblemGuidanceService
from companion.models import Message
from companion.observability import Observability


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
                    sources = json.loads(assistant.sources_json) if assistant.sources_json else []
                    diagnosis = json.loads(assistant.diagnosis_json) if assistant.diagnosis_json else None
                    return {
                        "reply": assistant.content,
                        "scene": assistant.scene or "general",
                        "motivation": assistant.motivation_text or "",
                        "sources": sources,
                        "diagnosis": diagnosis,
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
        topic = TopicExtractor.extract(message_text, code, error_text)
        if topic is None:
            topic = LearningRepository.latest_topic_for_conversation(client_id, conversation_id)

        # 仅使用本地审核过的摘要检索，不在用户请求链路中访问外部网页。
        retrieval = KnowledgeRetriever.retrieve(
            "\n".join(part for part in (message_text, code, error_text, error_type) if part),
            language=detected_lang,
            topic=topic,
        )

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
        if profile and profile.memory_enabled:
            profile_dict = {
                "nickname": profile.nickname or "未知",
                "skill_level": profile.skill_level or "beginner",
                "preferred_languages": profile.preferred_languages or "未设置",
                "learning_goal": profile.learning_goal or "未设置",
                "feedback_style": profile.feedback_style or "balanced",
                "memory_summary": profile.memory_summary or "暂无",
            }
        prior_scene_turns = (
            db.session.query(Message)
            .filter(
                Message.conversation_id == conversation_id,
                Message.role == "user",
                Message.scene == scene,
                Message.sequence_no < seq,
            )
            .count()
        )
        diagnosis = ProblemGuidanceService.diagnose(error_info, detected_lang)
        guidance_plan = ProblemGuidanceService.plan(
            scene,
            prior_scene_turns,
            profile.skill_level if profile and profile.skill_level else "beginner",
        )
        guidance_context = ProblemGuidanceService.prompt_context(guidance_plan, diagnosis)

        system_prompt = build_system_prompt(
            scene=scene,
            emotion_hint=emotion_hint,
            profile=profile_dict,
            language=detected_lang,
            knowledge_context=retrieval.prompt_context(),
            guidance_context=guidance_context,
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
        max_tokens = current_app.config.get("MAX_CONTEXT_TOKENS", 6000)
        scan_messages = current_app.config.get("MAX_CONTEXT_SCAN_MESSAGES", 120)

        history_desc = (
            db.session.query(Message)
            .filter(
                Message.conversation_id == conversation_id,
                Message.sequence_no < seq,
            )
            .order_by(Message.sequence_no.desc())
            .limit(scan_messages)
            .all()
        )
        context_window = ContextMemoryService.build_window(
            system_prompt=system_prompt,
            current_user_content=user_content,
            history_desc=history_desc,
            conversation_summary=conv.summary,
            max_tokens=max_tokens,
            max_messages=max_msgs,
        )
        llm_messages = context_window.messages

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
            llm_model = llm_resp.model
            llm_request_id = llm_resp.request_id
            llm_attempts = llm_resp.attempts
            finish_reason = llm_resp.finish_reason
            Observability.record_llm(llm_resp)
        except Exception:
            # LLM 调用失败，保留用户消息并允许相同幂等 ID 重试。
            user_msg.status = "failed"
            db.session.commit()
            Observability.record_llm(failed=True)
            raise

        # 7. 保存 assistant 消息
        motivation_text = ""
        feedback_style = profile.feedback_style if profile and profile.feedback_style else "balanced"
        praise = motive.get_praise(feedback_style)
        encourage = motive.get_encouragement(feedback_style)
        if praise:
            motivation_text = praise
        elif encourage:
            motivation_text = encourage
        elif emotion_state.is_frustrated:
            motivation_text = motive.get_comfort(feedback_style)

        assistant_msg = Message(
            conversation_id=conversation_id,
            sequence_no=seq + 1,
            role="assistant",
            content=reply,
            scene=scene,
            detected_language=detected_lang,
            error_type=error_type,
            emotion=emotion_state.label,
            emotion_score=emotion_state.score,
            motivation_text=motivation_text,
            status="completed",
            prompt_version="2.0.0",
            latency_ms=latency_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            llm_model=llm_model,
            llm_request_id=llm_request_id,
            llm_attempts=llm_attempts,
            finish_reason=finish_reason,
            sources_json=json.dumps(retrieval.sources, ensure_ascii=False) if retrieval.sources else None,
            diagnosis_json=json.dumps(diagnosis.to_dict(), ensure_ascii=False) if diagnosis else None,
            created_at=datetime.now(timezone.utc),
        )
        db.session.add(assistant_msg)

        # 更新用户消息状态
        user_msg.scene = scene
        user_msg.detected_language = detected_lang
        user_msg.error_type = error_type
        user_msg.status = "completed"

        # 8. 每轮都记录一个结构化学习事件，使主题、语言和趋势能够持续分析。
        if scene == "error" and error_type:
            event_type = "error"
        elif emotion_state.is_frustrated:
            event_type = "frustration"
        elif emotion_state.is_positive:
            event_type = "positive_progress"
        else:
            event_type = f"{scene}_interaction"
        LearningRepository.record(
            client_id=client_id,
            event_type=event_type,
            conversation_id=conversation_id,
            message_id=user_msg.id,
            topic=topic,
            language=detected_lang,
            error_type=error_type or None,
            metadata_json=json.dumps({
                "scene": scene,
                "emotion": emotion_state.label,
                "emotion_score": emotion_state.score,
                "emotion_intensity": emotion_state.intensity,
            }, ensure_ascii=False),
        )
        ReviewPlanService.observe(
            client_id,
            topic,
            had_error=bool(error_type),
            positive=emotion_state.is_positive,
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

        ContextMemoryService.refresh_conversation_summary(
            conv,
            user_msg,
            max_entries=current_app.config.get("CONVERSATION_SUMMARY_ENTRIES", 8),
        )

        # 11. 用本轮已结构化的场景、语言和错误信号刷新跨对话画像。
        # 不保存原始用户文本，避免将不可信内容提升为长期 system prompt。
        ProfileMemoryService.refresh(client_id)

        db.session.commit()

        return {
            "reply": reply,
            "scene": scene,
            "motivation": motivation_text,
            "sources": retrieval.sources,
            "diagnosis": diagnosis.to_dict() if diagnosis else None,
            "message_id": assistant_msg.id,
            "latency_ms": latency_ms,
        }
