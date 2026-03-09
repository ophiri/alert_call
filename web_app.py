"""
Flask Web Application for managing phone numbers.
Provides a UI and REST API to add/remove/toggle phone numbers.
Protected by a token passed via query param or X-Auth-Token header.
"""
import functools
import hashlib
import logging
import re

from flask import Flask, jsonify, redirect, render_template, request, url_for

import config
from phone_store import phone_store, end_event_store

logger = logging.getLogger(__name__)

app = Flask(__name__)

# Generate a URL-safe token from the password
AUTH_TOKEN = hashlib.sha256(config.WEB_PASSWORD.encode()).hexdigest()[:16]


def _is_authenticated() -> bool:
    """Check if the request carries a valid auth token (header or query param)."""
    token = request.headers.get("X-Auth-Token") or request.args.get("token")
    return token == AUTH_TOKEN


def login_required(f):
    """Decorator to require token auth on routes."""
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        if not _is_authenticated():
            if request.is_json or request.path.startswith("/api/"):
                return jsonify({"success": False, "error": "לא מחובר"}), 401
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


def _validate_phone(number: str) -> str:
    """Validate and normalize an Israeli/international phone number."""
    # Strip whitespace and dashes
    cleaned = re.sub(r"[\s\-\(\)]+", "", number.strip())
    # Accept formats like +972..., 05...
    if cleaned.startswith("05") and len(cleaned) == 10:
        cleaned = "+972" + cleaned[1:]
    if not re.match(r"^\+\d{10,15}$", cleaned):
        raise ValueError("מספר טלפון לא תקין. יש להזין מספר בפורמט בינלאומי, למשל +972501234567")
    return cleaned


# =============================================================================
# Auth
# =============================================================================

@app.route("/login", methods=["GET", "POST"])
def login():
    """Login page - validates password and redirects with token."""
    if request.method == "POST":
        password = request.form.get("password", "")
        if password == config.WEB_PASSWORD:
            logger.info("User logged in from %s", request.remote_addr)
            return redirect(url_for("index", token=AUTH_TOKEN))
        return render_template("login.html", error="סיסמה שגויה")
    return render_template("login.html")


# =============================================================================
# Web Pages
# =============================================================================

@app.route("/")
@login_required
def index():
    """Main management page."""
    return render_template("index.html", token=AUTH_TOKEN)


# =============================================================================
# REST API
# =============================================================================

@app.route("/api/numbers", methods=["GET"])
@login_required
def api_get_numbers():
    """Get all phone numbers."""
    numbers = phone_store.get_all()
    return jsonify({"success": True, "numbers": numbers})


@app.route("/api/numbers", methods=["POST"])
@login_required
def api_add_number():
    """Add a new phone number."""
    data = request.get_json()
    if not data or "number" not in data:
        return jsonify({"success": False, "error": "חסר מספר טלפון"}), 400

    try:
        number = _validate_phone(data["number"])
        name = data.get("name", "").strip()
        entry = phone_store.add(number, name)
        return jsonify({"success": True, "entry": entry})
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400


@app.route("/api/numbers/<path:number>", methods=["DELETE"])
@login_required
def api_remove_number(number):
    """Remove a phone number."""
    removed = phone_store.remove(number)
    if removed:
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "המספר לא נמצא"}), 404


@app.route("/api/numbers/<path:number>/toggle", methods=["POST"])
@login_required
def api_toggle_number(number):
    """Toggle active/inactive state of a phone number."""
    try:
        new_state = phone_store.toggle(number)
        return jsonify({"success": True, "active": new_state})
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 404


@app.route("/api/status", methods=["GET"])
@login_required
def api_status():
    """Get service status."""
    active_count = len(phone_store.get_active_numbers())
    total_count = len(phone_store.get_all())
    end_active = len(end_event_store.get_active_numbers())
    end_total = len(end_event_store.get_all())
    return jsonify({
        "success": True,
        "active_numbers": active_count,
        "total_numbers": total_count,
        "end_event_active": end_active,
        "end_event_total": end_total,
    })


# =============================================================================
# End-Event Numbers API
# =============================================================================

@app.route("/api/end-numbers", methods=["GET"])
@login_required
def api_get_end_numbers():
    """Get all end-event phone numbers."""
    numbers = end_event_store.get_all()
    return jsonify({"success": True, "numbers": numbers})


@app.route("/api/end-numbers", methods=["POST"])
@login_required
def api_add_end_number():
    """Add a new end-event phone number."""
    data = request.get_json()
    if not data or "number" not in data:
        return jsonify({"success": False, "error": "חסר מספר טלפון"}), 400

    try:
        number = _validate_phone(data["number"])
        name = data.get("name", "").strip()
        entry = end_event_store.add(number, name)
        return jsonify({"success": True, "entry": entry})
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400


@app.route("/api/end-numbers/<path:number>", methods=["DELETE"])
@login_required
def api_remove_end_number(number):
    """Remove an end-event phone number."""
    removed = end_event_store.remove(number)
    if removed:
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "המספר לא נמצא"}), 404


@app.route("/api/end-numbers/<path:number>/toggle", methods=["POST"])
@login_required
def api_toggle_end_number(number):
    """Toggle active/inactive state of an end-event phone number."""
    try:
        new_state = end_event_store.toggle(number)
        return jsonify({"success": True, "active": new_state})
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 404
