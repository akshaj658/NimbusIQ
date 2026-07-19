import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask
from whitenoise import WhiteNoise

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.blueprints.main import main_bp
from app.database import initialize_database


def create_app() -> Flask:
    app = Flask(__name__, template_folder="templates", static_folder="static")
    from src.utils.logger import logger
    configured_secret = os.environ.get("SECRET_KEY")
    if not configured_secret:
        # generate a secure random secret for session signing in absence of env var
        import secrets
        configured_secret = secrets.token_urlsafe(32)
        logger.warning("SECRET_KEY not set in environment; generated a temporary secret. Set SECRET_KEY in production.")

    app.config.update(
        SECRET_KEY=configured_secret,
        DATABASE_PATH=os.environ.get("DATABASE_PATH", str(PROJECT_ROOT / "cloudcostai.db")),
        SHOW_ADMIN=os.environ.get("SHOW_ADMIN", "false").lower() in ("1", "true", "yes"),
        MAX_CONTENT_LENGTH=1_000_000,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        JSON_SORT_KEYS=False,
    )
    app.register_blueprint(main_bp)
    app.wsgi_app = WhiteNoise(app.wsgi_app, root=str(PROJECT_ROOT / "app" / "static"), prefix="/static")
    initialize_database()

    @app.after_request
    def set_security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer-when-downgrade")
        response.headers.setdefault("Permissions-Policy", "geolocation=()")
        # Minimal CSP allowing same-origin scripts and styles; tighten as needed
        response.headers.setdefault("Content-Security-Policy", "default-src 'self'; script-src 'self' https://cdn.jsdelivr.net https://unpkg.com; style-src 'self' https://cdn.jsdelivr.net https://fonts.googleapis.com; font-src https://fonts.gstatic.com; img-src 'self' data:;")
        return response
    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), debug=False)
