"""
companion — 程序设计学习智能学伴 "小码"
应用工厂模块
"""
import os
import uuid
import logging
from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix

from .config import get_config
from .extensions import init_extensions


def create_app(config_override: dict | None = None) -> Flask:
    """创建并配置 Flask 应用。

    环境变量驱动配置：通过 APP_ENV 选择配置类（development / testing / production）。
    """
    app = Flask(
        __name__,
        template_folder="../templates",
        static_folder="../static",
        instance_relative_config=True,
    )

    # 加载配置
    config_obj = get_config()
    app.config.from_object(config_obj)
    if config_override:
        app.config.update(config_override)

    # Only trust forwarding headers when the application is explicitly placed
    # behind a known reverse proxy (one Nginx hop in the supplied deployment).
    proxy_hops = int(app.config.get("TRUST_PROXY_HOPS", 0))
    if proxy_hops:
        app.wsgi_app = ProxyFix(
            app.wsgi_app,
            x_for=proxy_hops,
            x_proto=proxy_hops,
            x_host=proxy_hops,
        )

    # 确保 instance 目录存在
    os.makedirs(app.instance_path, exist_ok=True)

    # 注入 request_id
    app.config.setdefault("REQUEST_ID_HEADER", "X-Request-ID")

    @app.before_request
    def _assign_request_id():
        from flask import request, g
        rid = request.headers.get(app.config["REQUEST_ID_HEADER"]) or str(uuid.uuid4())
        g.request_id = rid

    @app.after_request
    def _persist_client_cookie(response):
        """确保直接访问任意 API 时也能保存新建的匿名学习者身份。"""
        from flask import g, request
        new_cookie = getattr(g, "_new_client_cookie", None)
        cookie_name = app.config["CLIENT_COOKIE_NAME"]
        already_set = any(cookie_name in value for value in response.headers.getlist("Set-Cookie"))
        if new_cookie and not already_set:
            response.set_cookie(
                cookie_name,
                new_cookie,
                max_age=app.config["CLIENT_COOKIE_MAX_AGE"],
                httponly=True,
                samesite="Lax",
                secure=app.config.get("CLIENT_COOKIE_SECURE", False),
            )

        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault(
            "Permissions-Policy",
            "camera=(), microphone=(), geolocation=()",
        )
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data:; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; base-uri 'self'; form-action 'self'",
        )
        if app.config.get("APP_ENV") == "production" and request.is_secure:
            response.headers.setdefault(
                "Strict-Transport-Security",
                "max-age=31536000; includeSubDomains",
            )
        return response

    # 导入模型，确保 SQLAlchemy 知道它们
    with app.app_context():
        import companion.models  # noqa: F401

    # 初始化扩展（db, migrate, csrf）
    init_extensions(app)

    # 注册 Blueprint
    _register_blueprints(app)

    # 错误处理
    _register_error_handlers(app)

    # 结构化日志
    _setup_logging(app)

    return app


def _register_blueprints(app: Flask):
    """注册 API Blueprint。"""
    from .api.health import bp as health_bp
    from .api.bootstrap import bp as bootstrap_bp
    from .api.conversations import bp as conversations_bp
    from .api.messages import bp as messages_bp
    from .api.profile import bp as profile_bp
    from .api.learning import bp as learning_bp
    from .api.reminders import bp as reminders_bp

    app.register_blueprint(health_bp)
    app.register_blueprint(bootstrap_bp)
    app.register_blueprint(conversations_bp)
    app.register_blueprint(messages_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(learning_bp)
    app.register_blueprint(reminders_bp)

    # 旧版兼容路由
    @app.route("/")
    def index():
        from flask import render_template
        return render_template("index.html")


def _register_error_handlers(app: Flask):
    """注册统一错误处理器。"""
    from flask import jsonify, request, g
    from flask_wtf.csrf import CSRFError

    def _error_response(code: str, message: str, status: int, details: dict | None = None):
        return jsonify({
            "data": None,
            "error": {
                "code": code,
                "message": message,
                "details": details or {},
            },
            "request_id": getattr(g, "request_id", ""),
        }), status

    @app.errorhandler(400)
    def bad_request(_e):
        return _error_response("BAD_REQUEST", "请求格式错误", 400)

    @app.errorhandler(CSRFError)
    def csrf_error(_e):
        return _error_response("CSRF_FAILED", "安全令牌无效，请刷新页面后重试", 400)

    @app.errorhandler(404)
    def not_found(_e):
        return _error_response("NOT_FOUND", "资源不存在", 404)

    @app.errorhandler(405)
    def method_not_allowed(_e):
        return _error_response("METHOD_NOT_ALLOWED", "不允许的请求方法", 405)

    @app.errorhandler(413)
    def too_large(_e):
        return _error_response("PAYLOAD_TOO_LARGE", "请求体过大", 413)

    @app.errorhandler(422)
    def unprocessable(_e):
        return _error_response("VALIDATION_ERROR", "请求数据校验失败", 422)

    @app.errorhandler(500)
    def server_error(_e):
        app.logger.exception("Internal server error")
        return _error_response("INTERNAL_ERROR", "服务器内部错误，请稍后重试", 500)


def _setup_logging(app: Flask):
    """结构化日志配置。"""
    level = getattr(logging, app.config.get("LOG_LEVEL", "INFO").upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
