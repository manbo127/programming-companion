"""
健康检查端点
"""
from flask import Blueprint, current_app, jsonify, g
from companion.extensions import db
from sqlalchemy import text as sa_text

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
        },
        "error": None,
        "request_id": getattr(g, "request_id", ""),
    }), (200 if db_ok else 503)
