"""
Petit serveur local qui lit channels.db en direct et sert une page web
avec recherche + filtre par marché, temps (nouveau/tout) et statut
(proven/watchlist). Aucune donnée n'est envoyée hors de ta machine.

Lancer avec: python -m webapp.server
Puis ouvrir: http://localhost:5000
"""

import os
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

from discovery.database import list_all_channels, delete_channel

load_dotenv()

app = Flask(__name__)

ADMIN_KEY = os.environ.get("ADMIN_KEY")

NEW_CHANNEL_WINDOW_DAYS = 30


def _is_new(channel: dict) -> bool:
    discovered_at = channel.get("first_discovered_at")
    if not discovered_at:
        return False
    try:
        dt = datetime.fromisoformat(discovered_at)
    except ValueError:
        return False
    cutoff = datetime.now(timezone.utc) - timedelta(days=NEW_CHANNEL_WINDOW_DAYS)
    return dt >= cutoff


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/channels")
def api_channels():
    search = request.args.get("search", "").strip().lower()
    market = request.args.get("market", "").strip().lower()
    view = request.args.get("view", "new").strip().lower()      # "new" ou "all"
    status = request.args.get("status", "all").strip().lower()  # "proven", "watchlist", "all"

    channels = list_all_channels()

    for c in channels:
        c["is_new"] = _is_new(c)

    if view == "new":
        channels = [c for c in channels if c["is_new"]]

    if status in ("proven", "watchlist"):
        channels = [c for c in channels if (c.get("channel_status") or "").lower() == status]

    if market and market != "all":
        channels = [c for c in channels if (c.get("market") or "").lower() == market]

    if search:
        channels = [c for c in channels if search in (c.get("channel_title") or "").lower()]

    return jsonify(channels)


@app.route("/api/channels/<channel_id>", methods=["DELETE"])
def api_delete_channel(channel_id):
    if not ADMIN_KEY:
        return jsonify({"error": "ADMIN_KEY non configuré côté serveur"}), 500

    provided_key = request.headers.get("X-Admin-Key", "")
    if provided_key != ADMIN_KEY:
        return jsonify({"error": "Clé admin invalide"}), 403

    deleted = delete_channel(channel_id)
    if deleted:
        return jsonify({"status": "deleted", "channel_id": channel_id})
    else:
        return jsonify({"error": "Chaîne introuvable"}), 404


@app.route("/api/markets")
def api_markets():
    channels = list_all_channels()
    markets = sorted({c["market"] for c in channels if c.get("market")})
    return jsonify(markets)


if __name__ == "__main__":
    app.run(debug=True, port=5000)