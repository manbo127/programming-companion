"""
Flask 扩展初始化 — db, migrate, csrf
"""
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect

db = SQLAlchemy()
migrate = Migrate()
csrf = CSRFProtect()


def init_extensions(app):
    """初始化所有 Flask 扩展。"""
    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)

    # SQLite PRAGMA
    with app.app_context():
        from sqlalchemy import event, text

        @event.listens_for(db.engine, "connect")
        def _set_sqlite_pragma(dbapi_connection, _connection_record):
            if app.config.get("SQLALCHEMY_DATABASE_URI", "").startswith("sqlite"):
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.execute("PRAGMA busy_timeout=5000")
                cursor.execute("PRAGMA synchronous=NORMAL")
                cursor.close()
