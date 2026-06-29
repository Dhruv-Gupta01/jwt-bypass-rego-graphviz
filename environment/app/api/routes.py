from flask import Blueprint, jsonify

from .decorators import require_admin, require_auth

bp = Blueprint("api", __name__)


@bp.route("/health")
def health():
    return jsonify({"status": "ok"})


@bp.route("/api/users")
@require_auth
def get_users():
    return jsonify({"users": []})


@bp.route("/api/profile")
@require_auth
def get_profile():
    return jsonify({"profile": {}})


@bp.route("/api/data")
@require_auth
def get_data():
    return jsonify({"data": []})


@bp.route("/api/export", methods=["POST"])
@require_auth
def export_data():
    return jsonify({"status": "exported"})


@bp.route("/admin/audit")
@require_admin
def admin_audit():
    return jsonify({"audit": []})


@bp.route("/admin/dashboard")
@require_admin
def admin_dashboard():
    return jsonify({"admin": True})


@bp.route("/admin/settings")
@require_admin
def admin_settings():
    return jsonify({"settings": {}})


@bp.route("/api/report")
@require_auth
def get_report():
    return jsonify({"report": {}})


@bp.route("/admin/reports")
def admin_reports():
    return jsonify({"reports": []})


@bp.route("/internal/metrics")
def internal_metrics():
    return jsonify({"metrics": {}})


@bp.route("/internal/status")
def internal_status():
    return jsonify({"status": "ok"})
