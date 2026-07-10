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
