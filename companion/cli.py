"""部署和数据库运维命令。"""
from datetime import datetime, timezone
from pathlib import Path
import sqlite3

import click
from flask import current_app

from companion.database import sqlite_path_from_url
from companion.extensions import db


def register_cli(app):
    @app.cli.command("database-info")
    def database_info():
        """输出不含凭证和路径的数据库能力信息。"""
        dialect = db.engine.dialect.name
        click.echo(f"dialect={dialect}")
        click.echo(f"sqlite_wal={'supported' if dialect == 'sqlite' else 'not_applicable'}")
        click.echo(f"multi_worker={'no' if dialect == 'sqlite' else 'yes'}")

    @app.cli.command("backup-database")
    @click.option("--output-dir", default="backups", type=click.Path(file_okay=False, path_type=Path))
    def backup_database(output_dir: Path):
        """使用 SQLite Online Backup API 创建一致性备份。"""
        url = current_app.config["SQLALCHEMY_DATABASE_URI"]
        source_path = sqlite_path_from_url(url)
        if source_path is None:
            raise click.ClickException("backup-database currently supports file-based SQLite only")
        if not source_path.exists():
            raise click.ClickException("database file does not exist")
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        target = output_dir / f"companion-{timestamp}.db"
        with sqlite3.connect(source_path) as source, sqlite3.connect(target) as destination:
            source.backup(destination)
            result = destination.execute("PRAGMA integrity_check").fetchone()
        if not result or result[0] != "ok":
            target.unlink(missing_ok=True)
            raise click.ClickException("backup integrity check failed")
        click.echo(str(target))
