"""
健康检查端点
"""
from flask import Blueprint, current_app, jsonify, g
from companion.extensions import db
from sqlalchemy import text as sa_text
from sqlalchemy import inspect
from companion.observability import Observability

bp = Blueprint("health", __name__, url_prefix="/api/v1")


@bp.route("/health", methods=["GET"])
def health():
    """返回应用和数据库健康状态，不泄漏 API Key 或完整配置。"""
    db_ok = False
    db_msg = ""
    try:
        db.session.execute(sa_text("SELECT 1"))
        db.session.commit()
        db_ok = True
        db_msg = "ok"
    except Exception:
        # The public health endpoint must not expose database paths or driver
        # details. Full diagnostics remain available in the service log.
        db.session.rollback()
        current_app.logger.exception("Database health check failed")
        db_msg = "unavailable"

    return jsonify({
        "data": {
            "status": "ok" if db_ok else "degraded",
            "database": db_msg,
            "llm": {
                "provider": "deepseek" if current_app.config.get("DEEPSEEK_API_KEY") else "not_configured",
                "model": current_app.config.get("DEEPSEEK_MODEL", ""),
            },
        },
        "error": None,
        "request_id": getattr(g, "request_id", ""),
    }), (200 if db_ok else 503)


@bp.route("/ready", methods=["GET"])
def ready():
    """部署就绪检查：验证核心表和生产模型配置，不发起付费模型请求。"""
    required_tables = {"clients", "learner_profiles", "conversations", "messages", "learning_events"}
    try:
        existing = set(inspect(db.engine).get_table_names())
        missing = sorted(required_tables - existing)
        database_ready = not missing
    except Exception:
        current_app.logger.exception("Readiness database inspection failed")
        missing = ["unavailable"]
        database_ready = False
    llm_ready = bool(current_app.config.get("DEEPSEEK_API_KEY")) or current_app.config.get("TESTING", False)
    is_ready = database_ready and llm_ready
    return jsonify({
        "data": {
            "status": "ready" if is_ready else "not_ready",
            "database": "ok" if database_ready else "migration_required",
            "dialect": db.engine.dialect.name,
            "missing_tables": missing,
            "llm": "configured" if llm_ready else "not_configured",
        },
        "error": None,
        "request_id": getattr(g, "request_id", ""),
    }), (200 if is_ready else 503)


@bp.route("/metrics", methods=["GET"])
def metrics():
    """不包含用户文本、Cookie、密钥或数据库路径的轻量运行指标。"""
    return jsonify({
        "data": Observability.snapshot(),
        "error": None,
        "request_id": getattr(g, "request_id", ""),
    })
