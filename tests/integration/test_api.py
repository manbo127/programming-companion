"""
集成测试 — 使用测试 client 和 FakeLLM。
"""
import json
import pytest
from companion import create_app
from companion.extensions import db


@pytest.fixture
def app():
    app = create_app(config_override={
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "WTF_CSRF_ENABLED": False,
        "SECRET_KEY": "test",
        "SERVER_NAME": "localhost",
    })
    with app.app_context():
        db.create_all()
    return app


@pytest.fixture
def client(app):
    return app.test_client()


def _bootstrap(client):
    return client.get("/api/v1/bootstrap")


def _create_conv(client):
    return client.post("/api/v1/conversations", json={})


class TestBootstrap:
    def test_creates_anonymous_client(self, client):
        r = _bootstrap(client)
        assert r.status_code == 200
        data = r.get_json()["data"]
        assert data["client_id"]
        assert "recent_conversations" in data

    def test_sets_cookie(self, client):
        r = _bootstrap(client)
        assert "companion_client_id" in r.headers.get("Set-Cookie", "")

    def test_client_cookie_is_signed(self, client):
        r = _bootstrap(client)
        client_id = r.get_json()["data"]["client_id"]
        cookie = client.get_cookie("companion_client_id")
        assert cookie is not None
        assert cookie.value != client_id

    def test_direct_api_also_sets_identity_cookie(self, client):
        r = client.post("/api/v1/conversations", json={})
        assert r.status_code == 201
        assert "companion_client_id" in r.headers.get("Set-Cookie", "")


class TestConversations:
    def test_create_and_list(self, client):
        _bootstrap(client)
        r = client.post("/api/v1/conversations", json={"title": "列表中的对话"})
        assert r.status_code == 201
        cid = r.get_json()["data"]["id"]
        r = client.get("/api/v1/conversations")
        assert len(r.get_json()["data"]) >= 1

    def test_404_unknown(self, client):
        _bootstrap(client)
        r = client.get("/api/v1/conversations/nonexistent-id")
        assert r.status_code == 404

    def test_delete_and_404(self, client):
        _bootstrap(client)
        r = _create_conv(client)
        cid = r.get_json()["data"]["id"]
        r = client.delete(f"/api/v1/conversations/{cid}")
        assert r.status_code == 200
        r = client.get(f"/api/v1/conversations/{cid}")
        assert r.status_code == 404

    def test_update_title_and_reject_blank_title(self, client):
        _bootstrap(client)
        cid = client.post("/api/v1/conversations", json={"title": "第一次命名"}).get_json()["data"]["id"]
        updated = client.patch(
            f"/api/v1/conversations/{cid}",
            json={"title": "  递归复习  "},
        )
        assert updated.status_code == 200
        assert updated.get_json()["data"]["title"] == "递归复习"
        assert client.patch(
            f"/api/v1/conversations/{cid}", json={"title": "   "}
        ).status_code == 422

    def test_empty_legacy_conversation_is_hidden_from_history(self, client):
        _bootstrap(client)
        _create_conv(client)
        listed = client.get("/api/v1/conversations").get_json()["data"]
        assert listed == []


class TestMessages:
    def test_send_message(self, client):
        _bootstrap(client)
        r = _create_conv(client)
        cid = r.get_json()["data"]["id"]
        r = client.post(f"/api/v1/conversations/{cid}/messages",
                        json={"message": "什么是Python", "client_message_id": "id1"})
        assert r.status_code == 200
        data = r.get_json()["data"]
        assert data["reply"]
        assert data["scene"]

        conversation = client.get(f"/api/v1/conversations/{cid}").get_json()["data"]
        assert "什么是Python" in conversation["summary"]

    def test_idempotent_client_message_id(self, client):
        _bootstrap(client)
        r = _create_conv(client)
        cid = r.get_json()["data"]["id"]
        r1 = client.post(f"/api/v1/conversations/{cid}/messages",
                         json={"message": "Hello", "client_message_id": "dup1"})
        r2 = client.post(f"/api/v1/conversations/{cid}/messages",
                         json={"message": "Hello", "client_message_id": "dup1"})
        assert r1.get_json()["data"]["reply"] == r2.get_json()["data"]["reply"]

    def test_empty_input_rejected(self, client):
        _bootstrap(client)
        r = _create_conv(client)
        cid = r.get_json()["data"]["id"]
        r = client.post(f"/api/v1/conversations/{cid}/messages", json={})
        assert r.status_code == 422

    def test_invalid_scene_hint(self, client):
        _bootstrap(client)
        r = _create_conv(client)
        cid = r.get_json()["data"]["id"]
        r = client.post(f"/api/v1/conversations/{cid}/messages",
                        json={"message": "hi", "scene_hint": "invalid"})
        assert r.status_code == 422

    def test_language_hint_is_persisted(self, client):
        _bootstrap(client)
        r = _create_conv(client)
        cid = r.get_json()["data"]["id"]
        r = client.post(
            f"/api/v1/conversations/{cid}/messages",
            json={
                "message": "解释这个报错",
                "code": "public class Main {}",
                "error": "SyntaxError",
                "language_hint": "java",
                "client_message_id": "language-hint",
            },
        )
        assert r.status_code == 200
        messages = client.get(f"/api/v1/conversations/{cid}/messages").get_json()["data"]
        assert messages[-1]["detected_language"] == "java"

    def test_invalid_language_hint_is_rejected(self, client):
        _bootstrap(client)
        cid = _create_conv(client).get_json()["data"]["id"]
        response = client.post(
            f"/api/v1/conversations/{cid}/messages",
            json={"message": "看看代码", "code": "hello", "language_hint": "brainfuck"},
        )
        assert response.status_code == 422

    def test_motivation_is_not_duplicated_in_reply(self, client):
        _bootstrap(client)
        cid = _create_conv(client).get_json()["data"]["id"]
        r = client.post(
            f"/api/v1/conversations/{cid}/messages",
            json={"message": "好难，我看不懂", "client_message_id": "frustrated-once"},
        )
        data = r.get_json()["data"]
        assert data["motivation"]
        assert data["motivation"] not in data["reply"]

    def test_oversized_message_returns_413(self, client, app):
        _bootstrap(client)
        cid = _create_conv(client).get_json()["data"]["id"]
        r = client.post(
            f"/api/v1/conversations/{cid}/messages",
            json={"message": "x" * (app.config["MAX_MESSAGE_LENGTH"] + 1)},
        )
        assert r.status_code == 413

    def test_motivation_streak_survives_memory_reset(self, client):
        from companion.services.motivation import MotivationEngine

        _bootstrap(client)
        cid = _create_conv(client).get_json()["data"]["id"]
        client.post(
            f"/api/v1/conversations/{cid}/messages",
            json={"message": "好难，我不会", "client_message_id": "streak-1"},
        )
        MotivationEngine._instances.clear()
        client.post(
            f"/api/v1/conversations/{cid}/messages",
            json={"message": "还是错，我看不懂", "client_message_id": "streak-2"},
        )
        conversation = client.get(f"/api/v1/conversations/{cid}").get_json()["data"]
        assert conversation["frustration_streak"] == 2

    def test_current_user_message_is_sent_to_llm_once(self, client, app):
        from companion.llm.fake import FakeLLM
        from companion.services.chat_service import ChatService

        client_id = _bootstrap(client).get_json()["data"]["client_id"]
        cid = _create_conv(client).get_json()["data"]["id"]
        fake = FakeLLM()

        with app.app_context():
            ChatService(llm=fake).process_message(
                client_id=client_id,
                conversation_id=cid,
                message_text="这是一条唯一上下文消息",
                client_message_id="single-context-message",
            )

        occurrences = [
            message for message in fake.last_messages
            if message["role"] == "user" and "这是一条唯一上下文消息" in message["content"]
        ]
        assert len(occurrences) == 1

    def test_positive_streak_creates_actionable_reminder(self, client):
        _bootstrap(client)
        cid = client.post(
            "/api/v1/conversations", json={"title": "积极进展"}
        ).get_json()["data"]["id"]
        for index in range(3):
            response = client.post(
                f"/api/v1/conversations/{cid}/messages",
                json={"message": "我明白了，谢谢", "client_message_id": f"positive-{index}"},
            )
            assert response.status_code == 200
        reminders = client.get("/api/v1/reminders").get_json()["data"]
        assert any(item["type"] == "positive_streak" for item in reminders)


class TestCrossConversationProfileMemory:
    def test_structured_memory_is_generated_and_injected_into_new_conversation(self, client, app):
        from companion.llm.fake import FakeLLM
        from companion.services.chat_service import ChatService

        client_id = _bootstrap(client).get_json()["data"]["client_id"]
        first_conversation = _create_conv(client).get_json()["data"]["id"]
        response = client.post(
            f"/api/v1/conversations/{first_conversation}/messages",
            json={
                "message": "请解释这个错误",
                "code": "def pick(items):\n    return items[4]",
                "error": "IndexError: list index out of range",
                "client_message_id": "memory-source",
            },
        )
        assert response.status_code == 200

        profile = client.get("/api/v1/profile").get_json()["data"]
        assert profile["memory_enabled"] is True
        assert "Python" in profile["memory_summary"]
        assert "IndexError" in profile["memory_summary"]

        second_conversation = _create_conv(client).get_json()["data"]["id"]
        fake = FakeLLM()
        with app.app_context():
            ChatService(llm=fake).process_message(
                client_id=client_id,
                conversation_id=second_conversation,
                message_text="我们开始新的对话",
                client_message_id="memory-target",
            )

        system_prompt = fake.last_messages[0]["content"]
        assert "跨会话摘要" in system_prompt
        assert "Python" in system_prompt
        assert "IndexError" in system_prompt

    def test_clear_memory_excludes_older_messages_from_refresh(self, client):
        _bootstrap(client)
        conversation_id = _create_conv(client).get_json()["data"]["id"]
        client.post(
            f"/api/v1/conversations/{conversation_id}/messages",
            json={
                "message": "解释报错",
                "code": "print(values[9])",
                "error": "IndexError: list index out of range",
                "language_hint": "python",
                "client_message_id": "before-memory-reset",
            },
        )
        assert client.get("/api/v1/profile").get_json()["data"]["memory_summary"]

        cleared = client.delete("/api/v1/profile/memory")
        assert cleared.status_code == 200
        assert cleared.get_json()["data"]["memory_summary"] is None

        refreshed = client.post("/api/v1/profile/memory/refresh")
        assert refreshed.status_code == 200
        assert refreshed.get_json()["data"]["memory_summary"] is None

    def test_memory_can_be_disabled_without_losing_manual_profile(self, client, app):
        from companion.llm.fake import FakeLLM
        from companion.services.chat_service import ChatService

        client_id = _bootstrap(client).get_json()["data"]["client_id"]
        updated = client.patch(
            "/api/v1/profile",
            json={"nickname": "小林", "memory_enabled": False},
        )
        assert updated.status_code == 200
        assert updated.get_json()["data"]["nickname"] == "小林"
        assert updated.get_json()["data"]["memory_enabled"] is False

        conversation_id = _create_conv(client).get_json()["data"]["id"]
        fake = FakeLLM()
        with app.app_context():
            ChatService(llm=fake).process_message(
                client_id=client_id,
                conversation_id=conversation_id,
                message_text="你好",
                client_message_id="disabled-memory",
            )
        assert "昵称: 小林" not in fake.last_messages[0]["content"]

    def test_memory_enabled_requires_boolean(self, client):
        _bootstrap(client)
        response = client.patch("/api/v1/profile", json={"memory_enabled": "false"})
        assert response.status_code == 422


class TestLearningAnalytics:
    def test_topic_progress_and_distribution_are_derived_from_events(self, client):
        _bootstrap(client)
        conversation_id = _create_conv(client).get_json()["data"]["id"]
        first = client.post(
            f"/api/v1/conversations/{conversation_id}/messages",
            json={
                "message": "我的 Python 列表为什么越界",
                "code": "print(items[8])",
                "error": "IndexError: list index out of range",
                "language_hint": "python",
                "client_message_id": "analytics-error",
            },
        )
        second = client.post(
            f"/api/v1/conversations/{conversation_id}/messages",
            json={"message": "列表这个知识点我明白了，谢谢", "client_message_id": "analytics-positive"},
        )
        assert first.status_code == second.status_code == 200

        response = client.get("/api/v1/learning/overview?days=30")
        assert response.status_code == 200
        data = response.get_json()["data"]
        assert data["total_events"] == 2
        assert "数组与列表" in data["recent_topics"]
        topic = next(item for item in data["topic_progress"] if item["topic"] == "数组与列表")
        assert topic["attempts"] == 2
        assert topic["errors"] == 1
        assert topic["positive"] == 1
        assert data["languages_used"] == ["python"]
        assert data["scene_distribution"]

    def test_learning_window_is_clamped(self, client):
        _bootstrap(client)
        data = client.get("/api/v1/learning/overview?days=1").get_json()["data"]
        assert data["window_days"] == 7


class TestReviewPlans:
    def test_error_creates_spaced_review_and_due_plan_materializes_once(self, client, app):
        from datetime import datetime, timedelta, timezone
        from companion.models import ReviewPlan

        client_id = _bootstrap(client).get_json()["data"]["client_id"]
        conversation_id = _create_conv(client).get_json()["data"]["id"]
        response = client.post(
            f"/api/v1/conversations/{conversation_id}/messages",
            json={
                "message": "递归函数一直报错",
                "code": "def walk(n):\n    return walk(n - 1)",
                "error": "RecursionError: maximum recursion depth exceeded",
                "client_message_id": "review-plan-source",
            },
        )
        assert response.status_code == 200
        plans = client.get("/api/v1/review-plans").get_json()["data"]
        assert len(plans) == 1
        assert plans[0]["topic"] == "递归"

        with app.app_context():
            plan = db.session.query(ReviewPlan).filter_by(client_id=client_id).one()
            plan.next_review_at = datetime.now(timezone.utc) - timedelta(minutes=1)
            db.session.commit()

        first = client.get("/api/v1/reminders").get_json()["data"]
        second = client.get("/api/v1/reminders").get_json()["data"]
        scheduled = [item for item in first if item["type"] == "scheduled_review"]
        assert len(scheduled) == 1
        assert len([item for item in second if item["type"] == "scheduled_review"]) == 1

        completed = client.post(f"/api/v1/review-plans/{plans[0]['id']}/complete")
        assert completed.status_code == 200
        assert completed.get_json()["data"]["interval_index"] == 1

    def test_other_client_cannot_complete_review_plan(self, client, app):
        from companion.services.review_plan import ReviewPlanService

        first_client_id = _bootstrap(client).get_json()["data"]["client_id"]
        with app.app_context():
            plan = ReviewPlanService.observe(first_client_id, "递归", had_error=True, positive=False)
            db.session.commit()
            plan_id = plan.id

        other = app.test_client()
        other.get("/api/v1/bootstrap")
        assert other.post(f"/api/v1/review-plans/{plan_id}/complete").status_code == 404


class TestKnowledgeSources:
    def test_sources_are_returned_and_persisted_with_assistant_message(self, client):
        _bootstrap(client)
        conversation_id = _create_conv(client).get_json()["data"]["id"]
        response = client.post(
            f"/api/v1/conversations/{conversation_id}/messages",
            json={
                "message": "Python 的 IndexError 为什么会出现？",
                "code": "print(items[9])",
                "error": "IndexError: list index out of range",
                "language_hint": "python",
                "client_message_id": "knowledge-sources",
            },
        )
        assert response.status_code == 200
        sources = response.get_json()["data"]["sources"]
        assert sources
        assert all(item["url"].startswith("https://") for item in sources)

        messages = client.get(
            f"/api/v1/conversations/{conversation_id}/messages"
        ).get_json()["data"]
        assistant = next(item for item in messages if item["role"] == "assistant")
        assert assistant["sources"] == sources

    def test_duplicate_response_keeps_sources(self, client):
        _bootstrap(client)
        conversation_id = _create_conv(client).get_json()["data"]["id"]
        payload = {
            "message": "Rust moved value 怎么理解",
            "language_hint": "rust",
            "client_message_id": "same-source-message",
        }
        first = client.post(f"/api/v1/conversations/{conversation_id}/messages", json=payload)
        second = client.post(f"/api/v1/conversations/{conversation_id}/messages", json=payload)
        assert first.status_code == second.status_code == 200
        assert second.get_json()["data"]["sources"] == first.get_json()["data"]["sources"]


class TestStructuredDiagnosis:
    def test_error_diagnosis_is_returned_and_saved(self, client):
        _bootstrap(client)
        conversation_id = _create_conv(client).get_json()["data"]["id"]
        response = client.post(
            f"/api/v1/conversations/{conversation_id}/messages",
            json={
                "message": "这里为什么越界？",
                "code": "print(items[4])",
                "error": 'File "demo.py", line 3\nIndexError: list index out of range',
                "language_hint": "python",
                "client_message_id": "structured-diagnosis",
            },
        )
        assert response.status_code == 200
        diagnosis = response.get_json()["data"]["diagnosis"]
        assert diagnosis["category"] == "边界错误"
        assert diagnosis["location"] == "第 3 行"

        messages = client.get(
            f"/api/v1/conversations/{conversation_id}/messages"
        ).get_json()["data"]
        assistant = next(item for item in messages if item["role"] == "assistant")
        assert assistant["diagnosis"] == diagnosis

    def test_guidance_stage_is_injected_into_model_prompt(self, client, app):
        from companion.llm.fake import FakeLLM
        from companion.services.chat_service import ChatService

        client_id = _bootstrap(client).get_json()["data"]["client_id"]
        conversation_id = _create_conv(client).get_json()["data"]["id"]
        fake = FakeLLM()
        with app.app_context():
            ChatService(llm=fake).process_message(
                client_id=client_id,
                conversation_id=conversation_id,
                message_text="冒泡排序怎么做",
                scene_hint="guidance",
                client_message_id="guidance-stage-one",
            )
        assert "第 1 阶段（理解题意）" in fake.last_messages[0]["content"]


class TestEmotionPersonalization:
    def test_feedback_style_is_validated_and_persisted(self, client):
        _bootstrap(client)
        updated = client.patch("/api/v1/profile", json={"feedback_style": "concise"})
        assert updated.status_code == 200
        assert updated.get_json()["data"]["feedback_style"] == "concise"
        assert client.patch("/api/v1/profile", json={"feedback_style": "loud"}).status_code == 422

    def test_emotion_label_and_score_are_saved(self, client):
        _bootstrap(client)
        conversation_id = _create_conv(client).get_json()["data"]["id"]
        response = client.post(
            f"/api/v1/conversations/{conversation_id}/messages",
            json={"message": "太难了，我还是看不懂", "client_message_id": "emotion-score"},
        )
        assert response.status_code == 200
        messages = client.get(
            f"/api/v1/conversations/{conversation_id}/messages"
        ).get_json()["data"]
        assistant = next(item for item in messages if item["role"] == "assistant")
        assert assistant["emotion"] == "frustrated"
        assert assistant["emotion_score"] < 0


class TestLLMHealthMetadata:
    def test_health_exposes_model_name_but_never_api_key(self, client):
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        payload = response.get_json()
        assert payload["data"]["llm"]["model"]
        assert "test-key" not in response.get_data(as_text=True)

    def test_readiness_checks_schema_and_llm_without_calling_model(self, client):
        response = client.get("/api/v1/ready")
        assert response.status_code == 200
        data = response.get_json()["data"]
        assert data["status"] == "ready"
        assert data["database"] == "ok"
        assert data["dialect"] == "sqlite"

    def test_metrics_contain_aggregates_not_sensitive_values(self, client):
        from companion.observability import Observability

        Observability.reset_for_testing()
        client.get("/api/v1/health")
        response = client.get("/api/v1/metrics")
        assert response.status_code == 200
        data = response.get_json()["data"]
        assert data["http"]["requests_total"] >= 1
        serialized = response.get_data(as_text=True)
        assert "test-key" not in serialized
        assert "companion.db" not in serialized


class TestDatabaseOperations:
    def test_sqlite_backup_cli_creates_integrity_checked_copy(self, tmp_path):
        from companion import create_app
        from companion.extensions import db as backup_db

        database_path = tmp_path / "source.db"
        backup_dir = tmp_path / "backups"
        app = create_app(config_override={
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{database_path.as_posix()}",
            "WTF_CSRF_ENABLED": False,
            "SECRET_KEY": "backup-test",
        })
        with app.app_context():
            backup_db.create_all()
        result = app.test_cli_runner().invoke(
            args=["backup-database", "--output-dir", str(backup_dir)]
        )
        assert result.exit_code == 0, result.output
        backups = list(backup_dir.glob("companion-*.db"))
        assert len(backups) == 1
        assert backups[0].stat().st_size > 0


class TestUserAccounts:
    def test_registration_converts_anonymous_identity_and_keeps_history(self, client):
        client_id = _bootstrap(client).get_json()["data"]["client_id"]
        conversation_id = client.post(
            "/api/v1/conversations", json={"title": "注册前的对话"}
        ).get_json()["data"]["id"]
        response = client.post(
            "/api/v1/auth/register",
            json={"email": "Learner@Example.com", "password": "safe-pass-123"},
        )
        assert response.status_code == 201
        assert response.get_json()["data"] == {
            "authenticated": True,
            "email": "learner@example.com",
        }
        bootstrap = client.get("/api/v1/bootstrap").get_json()["data"]
        assert bootstrap["client_id"] == client_id
        assert bootstrap["account"]["authenticated"] is True
        assert any(item["id"] == conversation_id for item in bootstrap["recent_conversations"])

    def test_login_switches_to_existing_account_and_isolates_data(self, app):
        owner = app.test_client()
        owner.get("/api/v1/bootstrap")
        owner.post(
            "/api/v1/auth/register",
            json={"email": "owner@example.com", "password": "safe-pass-123"},
        )
        owned_id = owner.post(
            "/api/v1/conversations", json={"title": "私有历史"}
        ).get_json()["data"]["id"]

        visitor = app.test_client()
        visitor.get("/api/v1/bootstrap")
        assert visitor.get(f"/api/v1/conversations/{owned_id}").status_code == 404
        logged_in = visitor.post(
            "/api/v1/auth/login",
            json={"email": "owner@example.com", "password": "safe-pass-123"},
        )
        assert logged_in.status_code == 200
        assert visitor.get(f"/api/v1/conversations/{owned_id}").status_code == 200

    def test_password_is_hashed_and_repeated_failures_lock_account(self, client, app):
        from companion.models import Client

        _bootstrap(client)
        client.post(
            "/api/v1/auth/register",
            json={"email": "lock@example.com", "password": "safe-pass-123"},
        )
        with app.app_context():
            account = db.session.query(Client).filter_by(email="lock@example.com").one()
            assert account.password_hash != "safe-pass-123"

        attacker = app.test_client()
        attacker.get("/api/v1/bootstrap")
        for _ in range(5):
            response = attacker.post(
                "/api/v1/auth/login",
                json={"email": "lock@example.com", "password": "wrong-pass"},
            )
            assert response.status_code == 401
        locked = attacker.post(
            "/api/v1/auth/login",
            json={"email": "lock@example.com", "password": "safe-pass-123"},
        )
        assert locked.status_code == 429
        assert locked.get_json()["error"]["code"] == "ACCOUNT_LOCKED"

    def test_logout_returns_to_fresh_anonymous_identity(self, client):
        original = _bootstrap(client).get_json()["data"]["client_id"]
        client.post(
            "/api/v1/auth/register",
            json={"email": "logout@example.com", "password": "safe-pass-123"},
        )
        assert client.post("/api/v1/auth/logout").status_code == 200
        after = client.get("/api/v1/bootstrap").get_json()["data"]
        assert after["client_id"] != original
        assert after["account"]["authenticated"] is False

    def test_logout_revokes_only_current_device_session(self, app):
        first = app.test_client()
        original_id = first.get("/api/v1/bootstrap").get_json()["data"]["client_id"]
        first.post(
            "/api/v1/auth/register",
            json={"email": "devices@example.com", "password": "safe-pass-123"},
        )
        first_session_cookie = first.get_cookie("companion_client_id").value

        second = app.test_client()
        second.get("/api/v1/bootstrap")
        assert second.post(
            "/api/v1/auth/login",
            json={"email": "devices@example.com", "password": "safe-pass-123"},
        ).status_code == 200

        assert first.post("/api/v1/auth/logout").status_code == 200
        assert second.get("/api/v1/auth/me").get_json()["data"]["authenticated"] is True

        # 即使恢复当前设备退出前的旧 Cookie，服务端 revoked_at 仍会使其失效。
        first.set_cookie("companion_client_id", first_session_cookie)
        after_replay = first.get("/api/v1/bootstrap").get_json()["data"]
        assert after_replay["client_id"] != original_id
        assert after_replay["account"]["authenticated"] is False


class TestOwnership:
    def test_cannot_access_other_conversation(self, client, app):
        # Create two separate clients
        c1 = app.test_client()
        c2 = app.test_client()
        c1.get("/api/v1/bootstrap")
        r = c1.post("/api/v1/conversations", json={})
        cid = r.get_json()["data"]["id"]
        # Client 2 tries to access
        c2.get("/api/v1/bootstrap")
        r = c2.get(f"/api/v1/conversations/{cid}")
        assert r.status_code == 404


class TestCascadeDelete:
    def test_delete_conv_cascades_messages(self, client):
        _bootstrap(client)
        r = _create_conv(client)
        cid = r.get_json()["data"]["id"]
        client.post(f"/api/v1/conversations/{cid}/messages",
                    json={"message": "msg1"})
        client.delete(f"/api/v1/conversations/{cid}")
        r = client.get(f"/api/v1/conversations/{cid}/messages")
        assert r.status_code == 404
