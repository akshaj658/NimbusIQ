"""
app/app.py
==========
Flask application factory and configuration bootstrap for StadiumIQ.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, Response
from whitenoise import WhiteNoise

load_dotenv()

PROJECT_ROOT: Path = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.blueprints.main import main_bp
from app.database import initialize_database


def create_app() -> Flask:
    """Creates, configures, and boots the Flask application.

    Returns:
        The booted and configured Flask app.
    """
    app = Flask(__name__, template_folder="templates", static_folder="static")
    from src.utils.logger import logger
    
    configured_secret = os.environ.get("SECRET_KEY")
    if not configured_secret:
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
    def set_security_headers(response: Response) -> Response:
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer-when-downgrade")
        response.headers.setdefault("Permissions-Policy", "geolocation=()")
        # Minimal CSP allowing same-origin scripts and styles; tighten as needed
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; "
            "script-src 'self' https://cdn.jsdelivr.net https://unpkg.com; "
            "style-src 'self' https://cdn.jsdelivr.net https://fonts.googleapis.com; "
            "font-src https://fonts.gstatic.com; "
            "img-src 'self' data:;"
        )
        return response
        
    return app


app: Flask = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), debug=False)
