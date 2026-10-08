"""
Serveur qui lit la base PostgreSQL et sert une page web avec recherche,
filtre par marché, temps (nouveau/tout), statut (proven/watchlist) et
statistiques par marché. Contient aussi la page Concurrence (voir
webapp/competition_routes.py).

Lancer avec: python -m webapp.server
Puis ouvrir: http://localhost:5000
"""

import os
import time
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

from discovery.database import delete_channel, list_all_channels
from webapp.competition_routes import bp as competition_bp

load_dotenv()

app = Flask(__name__)
app.register_blueprint(competition_bp)

ADMIN_KEY = os.environ.get("ADMIN_KEY")

NEW_CHANNEL_WINDOW_DAYS = 30
CACHE_SECONDS = 20

_cache = {"data": None, "time": 0.0}


def _parse_date(value):
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _is_new(channel: dict) -> bool:
    dt = _parse_date(channel.get("first_discovered_at"))
    if not dt:
        return False
    cutoff = datetime.now(timezone.utc) - timedelta(days=NEW_CHANNEL_WINDOW_DAYS)
    return dt >= cutoff


def _get_channels_cached() -> list[dict]:
    """Relit la base seulement si le cache a plus de CACHE_SECONDS secondes."""
    now = time.time()
    if _cache["data"] is None or now - _cache["time"] > CACHE_SECONDS:
        channels = list_all_channels()
        for c in channels:
            c["is_new"] = _is_new(c)
        _cache["data"] = channels
        _cache["time"] = now
    return _cache["data"]


def _invalidate_cache():
    _cache["data"] = None


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/channels")
def api_channels():
    search = request.args.get("search", "").strip().lower()
    market = request.args.get("market", "").strip().lower()
    view = request.args.get("view", "new").strip().lower()
    status = request.args.get("status", "all").strip().lower()

    channels = list(_get_channels_cached())

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
    _invalidate_cache()
    if deleted:
        return jsonify({"status": "deleted", "channel_id": channel_id})
    return jsonify({"error": "Chaîne introuvable"}), 404


@app.route("/api/markets")
def api_markets():
    channels = _get_channels_cached()
    markets = sorted({c["market"] for c in channels if c.get("market")})
    return jsonify(markets)


@app.route("/api/stats")
def api_stats():
    """Statistiques globales et par marché, calculées sur les chaînes en base."""
    channels = _get_channels_cached()
    now = datetime.now(timezone.utc)
    cutoff_7 = now - timedelta(days=7)
    cutoff_30 = now - timedelta(days=30)

    def is_proven(c):
        return (c.get("channel_status") or "").upper() == "PROVEN"

    def added_since(c, cutoff):
        dt = _parse_date(c.get("first_discovered_at"))
        return bool(dt and dt >= cutoff)

    totals = {
        "channels": len(channels),
        "proven": sum(1 for c in channels if is_proven(c)),
        "watchlist": sum(1 for c in channels if not is_proven(c)),
        "added_7d": sum(1 for c in channels if added_since(c, cutoff_7)),
        "added_30d": sum(1 for c in channels if added_since(c, cutoff_30)),
    }

    by_market = {}
    for c in channels:
        by_market.setdefault((c.get("market") or "inconnu"), []).append(c)

    markets = []
    for name, items in by_market.items():
        subs = [c.get("subscriber_count") or 0 for c in items]
        dens = [c.get("density_score") or 0 for c in items]
        proven_n = sum(1 for c in items if is_proven(c))
        top = sorted(items, key=lambda c: (c.get("proven_video_count") or 0), reverse=True)[:3]
        markets.append({
            "market": name,
            "channels": len(items),
            "proven": proven_n,
            "watchlist": len(items) - proven_n,
            "avg_subscribers": round(sum(subs) / len(subs)) if subs else 0,
            "avg_density": round(sum(dens) / len(dens), 3) if dens else 0,
            "added_30d": sum(1 for c in items if added_since(c, cutoff_30)),
            "top_channels": [{
                "channel_id": c.get("channel_id"),
                "channel_title": c.get("channel_title"),
                "channel_url": c.get("channel_url"),
                "proven_video_count": c.get("proven_video_count") or 0,
                "subscriber_count": c.get("subscriber_count") or 0,
            } for c in top],
        })

    markets.sort(key=lambda m: (m["proven"], m["channels"]), reverse=True)
    return jsonify({"totals": totals, "markets": markets})


if __name__ == "__main__":
    app.run(debug=True, port=5000)