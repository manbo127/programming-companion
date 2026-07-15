"""
应用启动入口
"""
import os

from dotenv import load_dotenv

# Load local .env values before the application configuration is imported.
# Systemd-provided environment variables keep precedence in production.
load_dotenv()

from companion import create_app

app = create_app()


if __name__ == "__main__":
    app.run(
        host=os.getenv("FLASK_HOST", "127.0.0.1"),
        port=int(os.getenv("FLASK_PORT", "5000")),
        debug=app.config.get("DEBUG", False),
    )
