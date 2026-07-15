"""
JSON → SQLite 迁移脚本
将 data/conversations/*.json 导入 SQLite 数据库。

用法:
  python scripts/migrate_json_to_sqlite.py          # 实际迁移
  python scripts/migrate_json_to_sqlite.py --dry-run  # 预览模式
"""
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

# 确保项目根目录在路径中
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def migrate(json_dir: str, dry_run: bool = False):
    """将 JSON 对话文件迁移到 SQLite。"""
    from companion import create_app
    from companion.extensions import db
    from companion.models import Client, Conversation, Message

    app = create_app()
    app.app_context().push()

    json_path = Path(json_dir)
    if not json_path.exists():
        print(f"JSON 目录不存在: {json_dir}")
        return

    json_files = sorted(json_path.glob("*.json"))
    if not json_files:
        print("没有找到 JSON 文件。")
        return

    # 创建 legacy client
    legacy_client_id = str(uuid.uuid4())
    client = db.session.get(Client, legacy_client_id)
    if client is None:
        client = Client(id=legacy_client_id)
        db.session.add(client)
        db.session.flush()
        print(f"创建 legacy client: {legacy_client_id}")

    imported = 0
    skipped = 0
    errors = 0

    for jf in json_files:
        try:
            with open(jf, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"[WARN] 跳过损坏文件 {jf.name}: {e}")
            errors += 1
            continue

        session_id = data.get("session_id", jf.stem)

        # 幂等检查：如果存在同名会话则跳过
        existing = db.session.get(Conversation, session_id)
        if existing:
            print(f"[SKIP] 已存在: {session_id}")
            skipped += 1
            continue

        conv = Conversation(
            id=session_id,
            client_id=legacy_client_id,
            title=None,
            created_at=_parse_time(data.get("created_at")),
            updated_at=_parse_time(data.get("updated_at")),
        )
        db.session.add(conv)

        messages = data.get("messages", [])
        for i, m in enumerate(messages):
            msg = Message(
                conversation_id=session_id,
                sequence_no=i + 1,
                role=m.get("role", "user"),
                content=m.get("content", ""),
                status="completed",
                created_at=_parse_time(m.get("timestamp")),
            )
            db.session.add(msg)

        if dry_run:
            print(f"[DRY-RUN] 将导入: {session_id} ({len(messages)} 条消息)")
        else:
            imported += 1
            print(f"[IMPORT] {session_id}: {len(messages)} 条消息")

    if dry_run:
        print(f"\n预览完成: 将导入 {len(json_files) - errors - skipped} 个会话，跳过 {skipped} 个已存在，{errors} 个错误")
    else:
        db.session.commit()
        print(f"\n迁移完成: 导入 {imported} 个会话，跳过 {skipped} 个已存在，{errors} 个错误")


def _parse_time(ts: str | None):
    if not ts:
        return datetime.now(timezone.utc)
    try:
        return datetime.fromisoformat(ts)
    except (ValueError, TypeError):
        return datetime.now(timezone.utc)


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    json_dir = os.path.join(PROJECT_ROOT, "data", "conversations")
    migrate(json_dir, dry_run=dry_run)
