"""
Routes de la page Concurrence. Chaque personne s'identifie avec un code
d'accès personnel (en-tête X-Access-Code). Créer un code : voir
competition/create_code.py ou la route admin ci-dessous.
"""

import os
import threading
from functools import wraps

from flask import Blueprint, g, jsonify, request

from competition import service, store
from competition.compare import build_report
from competition.yt import ChannelNotFound, Tracker, resolve_channel
from discovery.youtube_client import QuotaExhaustedError, has_keys

bp = Blueprint("competition", __name__, url_prefix="/api/competition")


def require_code(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        row = store.get_code(request.headers.get("X-Access-Code", "").strip())
        if not row:
            return jsonify({"error": "Code d'accès invalide."}), 401
        g.user = row
        return fn(*args, **kwargs)
    return wrapper


def _public(analysis: dict) -> dict:
    out = {
        "id": analysis["id"],
        "channel_id": analysis["channel_id"],
        "status": analysis["status"],
        "progress": analysis.get("progress"),
        "error": analysis.get("error"),
        "units_used": analysis.get("units_used"),
        "created_at": analysis.get("created_at"),
        "finished_at": analysis.get("finished_at"),
    }
    if analysis["status"] == "done" and analysis.get("data"):
        out["report"] = build_report(analysis["data"])
    return out


@bp.route("/me")
@require_code
def me():
    used = store.count_analyses_today(g.user["code"])
    return jsonify({"name": g.user["name"], "daily_limit": g.user["daily_limit"], "used_today": used})


@bp.route("/channels", methods=["GET"])
@require_code
def channels_list():
    return jsonify(store.list_channels(g.user["code"]))


@bp.route("/channels", methods=["POST"])
@require_code
def channels_add():
    if not has_keys():
        return jsonify({"error": "Aucune clé API YouTube configurée sur le serveur."}), 500
    body = request.get_json(silent=True) or {}
    market = (body.get("market") or "").strip().lower() or None
    try:
        info = resolve_channel(body.get("url", ""), Tracker())
    except ChannelNotFound as e:
        return jsonify({"error": str(e)}), 404
    except QuotaExhaustedError:
        return jsonify({"error": "Quota YouTube épuisé pour aujourd'hui."}), 503
    store.add_channel(g.user["code"], info, market)
    return jsonify(store.get_channel(g.user["code"], info["channel_id"]))


@bp.route("/channels/<channel_id>", methods=["DELETE"])
@require_code
def channels_delete(channel_id):
    if store.delete_channel(g.user["code"], channel_id):
        return jsonify({"status": "deleted"})
    return jsonify({"error": "Chaîne introuvable."}), 404


@bp.route("/analyses", methods=["GET"])
@require_code
def analyses_list():
    channel_id = request.args.get("channel_id", "")
    return jsonify(store.list_analyses(g.user["code"], channel_id))


@bp.route("/analyses", methods=["POST"])
@require_code
def analyses_start():
    if not has_keys():
        return jsonify({"error": "Aucune clé API YouTube configurée sur le serveur."}), 500
    owner = g.user["code"]
    body = request.get_json(silent=True) or {}
    channel = store.get_channel(owner, body.get("channel_id", ""))
    if not channel:
        return jsonify({"error": "Chaîne introuvable dans ta liste."}), 404

    store.mark_stale_running()
    if store.has_running(owner):
        return jsonify({"error": "Une analyse est déjà en cours. Attends qu'elle se termine."}), 409
    used = store.count_analyses_today(owner)
    if used >= (g.user["daily_limit"] or 0):
        return jsonify({"error": f"Limite atteinte : {used}/{g.user['daily_limit']} analyses sur 24 h."}), 429

    analysis_id = store.create_analysis(owner, channel["channel_id"])
    threading.Thread(
        target=service.run_analysis,
        args=(analysis_id, owner, channel["channel_id"], channel.get("market")),
        daemon=True,
    ).start()
    return jsonify({"id": analysis_id, "status": "running"}), 202


@bp.route("/analyses/<int:analysis_id>")
@require_code
def analyses_get(analysis_id):
    analysis = store.get_analysis(g.user["code"], analysis_id)
    if not analysis:
        return jsonify({"error": "Analyse introuvable."}), 404
    return jsonify(_public(analysis))


@bp.route("/analyses/<int:analysis_id>/competitors", methods=["POST"])
@require_code
def competitor_add(analysis_id):
    body = request.get_json(silent=True) or {}
    try:
        service.add_manual_competitor(g.user["code"], analysis_id, body.get("url", ""))
    except (ChannelNotFound, ValueError) as e:
        return jsonify({"error": str(e)}), 400
    except QuotaExhaustedError:
        return jsonify({"error": "Quota YouTube épuisé pour aujourd'hui."}), 503
    return jsonify(_public(store.get_analysis(g.user["code"], analysis_id)))


@bp.route("/analyses/<int:analysis_id>/competitors/<channel_id>", methods=["DELETE"])
@require_code
def competitor_remove(analysis_id, channel_id):
    if not service.remove_competitor(g.user["code"], analysis_id, channel_id):
        return jsonify({"error": "Concurrent introuvable."}), 404
    return jsonify(_public(store.get_analysis(g.user["code"], analysis_id)))


# ---------------------------------------------------------------- admin

def _check_admin():
    admin_key = os.environ.get("ADMIN_KEY")
    if not admin_key:
        return jsonify({"error": "ADMIN_KEY non configuré côté serveur"}), 500
    if request.headers.get("X-Admin-Key", "") != admin_key:
        return jsonify({"error": "Clé admin invalide"}), 403
    return None


@bp.route("/admin/codes", methods=["GET"])
def admin_codes_list():
    denied = _check_admin()
    return denied or jsonify(store.list_codes())


@bp.route("/admin/codes", methods=["POST"])
def admin_codes_create():
    denied = _check_admin()
    if denied:
        return denied
    body = request.get_json(silent=True) or {}
    name = (body.get("name") or "").strip()
    if not name:
        return jsonify({"error": "Nom manquant."}), 400
    limit = int(body.get("daily_limit") or 3)
    return jsonify({"name": name, "daily_limit": limit, "code": store.create_code(name, limit)})
