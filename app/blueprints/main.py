import os
import hmac
from functools import wraps, lru_cache
from base64 import b64decode

import joblib
from flask import Blueprint, Response, flash, redirect, render_template, request, url_for, current_app

from src.utils.config import MODEL_DIR
from app.ai_assistant import ZONE_ALIASES, VENUE_ALIASES, get_ai_recommendations, get_stadium_status

from app.services import (
    delete_prediction,
    generate_csv,
    get_dashboard_stats,
    get_prediction_history,
    perform_prediction,
    sanitize_form_data,
)

main_bp = Blueprint("main", __name__)


def _check_auth_header(auth_header: str) -> bool:
    try:
        if not auth_header.lower().startswith("basic "):
            return False
        payload = b64decode(auth_header.split(" ", 1)[1]).decode("utf-8")
        username, password = payload.split(":", 1)
        expected_user = os.environ.get("ADMIN_USER")
        expected_pass = os.environ.get("ADMIN_PASS")
        if not expected_user or not expected_pass:
            return False
        return hmac.compare_digest(username, expected_user) and hmac.compare_digest(password, expected_pass)
    except Exception:
        return False


def require_basic_auth(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        # If admin not enabled, deny
        if not current_app.config.get("SHOW_ADMIN"):
            return Response("Not Found", status=404)
        auth = request.headers.get("Authorization", "")
        if _check_auth_header(auth):
            return func(*args, **kwargs)
        # Request auth
        resp = Response("Unauthorized", status=401)
        resp.headers["WWW-Authenticate"] = 'Basic realm="StadiumIQ Admin"'
        return resp
    return wrapper


@lru_cache(maxsize=1)
def _get_form_options() -> dict[str, list[str]]:
    try:
        preprocessor = joblib.load(MODEL_DIR / "preprocessor.pkl")
        encoder = preprocessor.named_transformers_["categorical"]
        # encoder.categories_ returns a list of arrays corresponding to the categories.
        # Categorical columns in build_preprocessor are ["Service Name", "Usage Unit", "Region/Zone"]
        service_names = encoder.categories_[0].tolist()
        usage_units = encoder.categories_[1].tolist()
        regions = encoder.categories_[2].tolist()
        return {
            "service_names": sorted(service_names),
            "usage_units": sorted(usage_units),
            "regions": sorted(regions),
        }
    except Exception as e:
        import logging
        logging.error(f"Failed to load form options from preprocessor: {e}")
        return {"service_names": [], "usage_units": [], "regions": []}


def _template_context(options: dict) -> dict:
    """Build the shared template context with stadium aliasing."""
    return {
        "service_names": options["service_names"],
        "usage_units": options["usage_units"],
        "regions": options["regions"],
        "zone_aliases": ZONE_ALIASES,
        "venue_aliases": VENUE_ALIASES,
    }


@main_bp.route("/")
def index():
    history = get_prediction_history(limit=5)
    options = _get_form_options()
    ctx = _template_context(options)
    return render_template(
        "index.html",
        history=history,
        prediction_result=None,
        cost_breakdown=None,
        ai_result=None,
        values={},
        errors=[],
        **ctx,
    )


@main_bp.route("/predict", methods=["POST"])
def predict():
    errors, values = sanitize_form_data(request.form)
    options = _get_form_options()
    ctx = _template_context(options)

    if errors:
        for error in errors:
            flash(error, "danger")
        history = get_prediction_history(limit=5)
        return render_template(
            "index.html",
            history=history,
            prediction_result=None,
            cost_breakdown=None,
            ai_result=None,
            values=values,
            errors=errors,
            **ctx,
        )

    try:
        predicted_cost, breakdown = perform_prediction(values)
        flash("Operational assessment complete.", "success")
        history = get_prediction_history(limit=5)

        # Generate AI recommendations in the same request (fast enough for sync)
        ai_result = get_ai_recommendations(values, predicted_cost)

        return render_template(
            "index.html",
            history=history,
            prediction_result=predicted_cost,
            cost_breakdown=breakdown,
            ai_result=ai_result,
            values=values,
            errors=[],
            **ctx,
        )
    except Exception as exc:
        flash(f"Assessment failed: {exc}", "danger")
        history = get_prediction_history(limit=5)
        return render_template(
            "index.html",
            history=history,
            prediction_result=None,
            cost_breakdown=None,
            ai_result=None,
            values=values,
            errors=[str(exc)],
            **ctx,
        )


@main_bp.route("/history")
def history():
    search = request.args.get("q", "", type=str)
    rows = get_prediction_history(search=search)
    return {"predictions": [dict(row) for row in rows]}


@main_bp.route("/api/form-options")
def api_form_options():
    """Return the valid dropdown options loaded from the trained preprocessor."""
    options = _get_form_options()
    return options


@main_bp.route("/api/ai-assist", methods=["POST"])
def api_ai_assist():
    """
    GenAI endpoint: accepts sanitised form values + predicted cost,
    returns AI-powered stadium operations recommendations from Gemini.
    """
    try:
        payload = request.get_json(force=True, silent=True) or {}
        values = payload.get("values", {})
        predicted_cost = float(payload.get("predicted_cost", 0.0))
        result = get_ai_recommendations(values, predicted_cost)
        return result, 200
    except Exception as exc:
        return {"error": str(exc), "recommendations": [], "source": "error"}, 500


@main_bp.route("/api/stadium-status")
def api_stadium_status():
    """Return simulated live stadium status metrics for the command dashboard."""
    return get_stadium_status(), 200


@main_bp.route("/admin")
@require_basic_auth
def admin():
    search = request.args.get("q", "", type=str)
    stats = get_dashboard_stats(search=search)
    history_rows = get_prediction_history(search=search)
    return render_template(
        "admin.html",
        stats=stats,
        history=history_rows,
        search=search,
        zone_aliases=ZONE_ALIASES,
        venue_aliases=VENUE_ALIASES,
    )


@main_bp.route("/admin/delete/<int:prediction_id>", methods=["POST"])
@require_basic_auth
def delete_prediction_route(prediction_id: int):
    delete_prediction(prediction_id)
    flash("Record removed successfully.", "success")
    return redirect(url_for("main.admin"))


@main_bp.route("/api/delete/<int:prediction_id>", methods=["DELETE"])
@require_basic_auth
def api_delete_prediction(prediction_id: int):
    try:
        delete_prediction(prediction_id)
        return {"status": "ok", "message": "deleted"}, 200
    except Exception as exc:
        return {"status": "error", "message": str(exc)}, 500


@main_bp.route("/download")
@require_basic_auth
def download():
    search = request.args.get("q", "", type=str)
    rows = get_prediction_history(search=search)
    content = generate_csv(rows)
    response = Response(content, mimetype="text/csv")
    response.headers["Content-Disposition"] = "attachment; filename=stadiumiq_operations.csv"
    return response


@main_bp.route("/api/stats")
@require_basic_auth
def api_stats():
    search = request.args.get("q", "", type=str)
    stats = get_dashboard_stats(search=search)
    return stats
