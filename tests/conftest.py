"""
测试基础配置和 fixtures
"""
import pytest
from companion import create_app
from companion.extensions import db as _db
from companion.config import TestingConfig


@pytest.fixture(scope="session")
def app():
    """创建测试 Flask 应用（session 级别）。"""
    app = create_app(config_override={
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "WTF_CSRF_ENABLED": False,
        "SECRET_KEY": "test-secret-key",
        "SERVER_NAME": "localhost",
    })
    return app


@pytest.fixture(scope="session")
def _db_engine(app):
    """创建所有表（session 级别）。"""
    with app.app_context():
        _db.create_all()
        yield _db
        _db.drop_all()


@pytest.fixture
def db(_db_engine, app):
    """每个测试独立事务，测试结束后回滚。"""
    connection = _db_engine.engine.connect()
    transaction = connection.begin()
    _db_engine.session.configure(bind=connection)
    yield _db_engine
    _db_engine.session.remove()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(app, db):
    """测试客户端。"""
    return app.test_client()


@pytest.fixture
def runner(app):
    """CLI runner。"""
    return app.test_cli_runner()
