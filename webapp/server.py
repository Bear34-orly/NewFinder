"""
Serveur qui lit la base PostgreSQL et sert une page web avec recherche,
filtre par marché, temps (nouveau/tout), statut (proven/watchlist) et
statistiques par marché. Contient aussi la page Concurrence (voir
webapp/competition_routes.py).

Le site est protégé par un mot de passe SI la variable SITE_PASSWORD existe ; sans elle, le site est OUVERT à tous.
Sans cette variable, le site refuse tout accès (il ne s'ouvre jamais par erreur).

Lancer avec: python -m webapp.server
Puis ouvrir: http://localhost:5000
"""

import hashlib
import hmac
import os
import secrets
import time
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from flask import (Flask, Response, jsonify, redirect, render_template,
                   render_template_string, request, session, url_for)

from config.face_settings import FACE_TAG_SAME_RATIO
from config.faceless_signals import DOUBTFUL_RATIO
from discovery.database import delete_channel, list_all_channels, load_growth
from webapp.competition_routes import bp as competition_bp

load_dotenv()

app = Flask(__name__)
app.register_blueprint(competition_bp)

ADMIN_KEY = os.environ.get("ADMIN_KEY")

# ---------- Accès privé (mot de passe unique) ----------
SITE_PASSWORD = os.environ.get("SITE_PASSWORD")

# Clé qui signe le cookie de connexion. Elle dépend du mot de passe : si tu le changes,
# toutes les connexions existantes sont coupées.
if SITE_PASSWORD:
    app.secret_key = hashlib.sha256(("niche-finder-session:" + SITE_PASSWORD).encode()).hexdigest()
else:
    app.secret_key = secrets.token_hex(32)

app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=bool(os.environ.get("RENDER")),  # Render est en https ; en local (http) on désactive
    PERMANENT_SESSION_LIFETIME=timedelta(days=30),
)

PUBLIC_ENDPOINTS = {"login", "logout", "health", "robots"}
MAX_LOGIN_FAILURES = 8          # essais ratés autorisés ...
LOGIN_WINDOW_SECONDS = 600      # ... pendant 10 minutes
_login_failures: list[float] = []

LOGIN_PAGE = """<!doctype html>
<html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>Connexion</title>
<style>
  body { margin:0; min-height:100vh; display:flex; align-items:center; justify-content:center;
         background:#111; color:#eee; font-family:system-ui,-apple-system,Segoe UI,sans-serif; }
  form { width:min(340px, 88vw); padding:28px; border:1px solid #2a2a2a; border-radius:14px; background:#181818; }
  h1 { font-size:18px; margin:0 0 16px; }
  input, button { width:100%; box-sizing:border-box; padding:11px 12px; border-radius:8px; font-size:15px; }
  input { border:1px solid #333; background:#111; color:#eee; margin-bottom:12px; }
  button { border:0; background:#22c55e; color:#04130a; font-weight:600; cursor:pointer; }
  .err { color:#f87171; font-size:14px; margin:0 0 12px; }
</style></head><body>
<form method="post" action="/login">
  <h1>Accès privé</h1>
  {% if error %}<p class="err">{{ error }}</p>{% endif %}
  <input type="password" name="password" placeholder="Mot de passe" autocomplete="current-password" autofocus required>
  <button type="submit">Entrer</button>
</form></body></html>"""

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


def _face_reasons(channel: dict) -> list[str]:
    """Raisons pour lesquelles une chaîne reçoit le tag 'Visage ?' (liste vide = pas de tag)."""
    reasons = []
    same = channel.get("same_face_ratio")
    text = channel.get("face_text_ratio")
    if same is not None and same >= FACE_TAG_SAME_RATIO:
        reasons.append(f"même visage sur {round(same * 100)} % des miniatures")
    if text is not None and text >= DOUBTFUL_RATIO:
        reasons.append(f"{round(text * 100)} % des titres ressemblent à une interview ou un format avec visage")
    return reasons


def _get_channels_cached() -> list[dict]:
    """Relit la base seulement si le cache a plus de CACHE_SECONDS secondes."""
    now = time.time()
    if _cache["data"] is None or now - _cache["time"] > CACHE_SECONDS:
        channels = list_all_channels()
        try:
            growth = load_growth(7)
        except Exception as e:           # l'historique ne doit jamais casser le site
            print(f"Croissance indisponible : {e}")
            growth = {}
        for c in channels:
            g = growth.get(c["channel_id"]) or {}
            c["subs_gain"] = g.get("subs_gain")
            c["gain_days"] = g.get("gain_days")
            c["subs_gain_week"] = g.get("subs_gain_week")
            c["growth_pct_week"] = g.get("growth_pct_week")
            c["views_gain_week"] = g.get("views_gain_week")
            c["is_new"] = _is_new(c)
            reasons = _face_reasons(c)
            c["face_flag"] = bool(reasons)
            c["face_hint"] = " ; ".join(reasons)
        _cache["data"] = channels
        _cache["time"] = now
    return _cache["data"]


def _invalidate_cache():
    _cache["data"] = None


def _login_locked() -> int:
    """Retourne le nombre de secondes d'attente si trop d'essais ratés, sinon 0."""
    now = time.time()
    _login_failures[:] = [t for t in _login_failures if now - t < LOGIN_WINDOW_SECONDS]
    if len(_login_failures) >= MAX_LOGIN_FAILURES:
        return int(LOGIN_WINDOW_SECONDS - (now - _login_failures[0])) + 1
    return 0


@app.before_request
def require_login():
    """Tout est fermé sauf la page de connexion, /health et robots.txt."""
    if request.endpoint in PUBLIC_ENDPOINTS:
        return None
    if not SITE_PASSWORD:
        return None          # pas de mot de passe configuré : le site est OUVERT à tous (choix assumé)
    if session.get("auth") is True:
        return None
    if request.path.startswith("/api/"):
        return jsonify({"error": "Non connecté"}), 401
    return redirect(url_for("login"))


@app.after_request
def add_privacy_headers(response):
    response.headers["X-Robots-Tag"] = "noindex, nofollow, noarchive"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    if request.path.startswith("/api/") or request.endpoint in ("index", "login"):
        response.headers["Cache-Control"] = "no-store"
    return response


@app.route("/login", methods=["GET", "POST"])
def login():
    if not SITE_PASSWORD:
        return redirect(url_for("index"))      # site ouvert : pas de page de connexion
    if request.method == "POST":
        wait = _login_locked()
        if wait:
            minutes = max(1, wait // 60)
            return render_template_string(LOGIN_PAGE, error=f"Trop d'essais. Réessaie dans {minutes} min."), 429
        given = request.form.get("password", "")
        if hmac.compare_digest(given.encode("utf-8"), SITE_PASSWORD.encode("utf-8")):
            _login_failures.clear()
            session.clear()
            session["auth"] = True
            session.permanent = True
            return redirect(url_for("index"))
        _login_failures.append(time.time())
        time.sleep(1)  # ralentit les essais automatiques
        return render_template_string(LOGIN_PAGE, error="Mot de passe incorrect."), 401
    if session.get("auth") is True:
        return redirect(url_for("index"))
    return render_template_string(LOGIN_PAGE, error=None)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/health")
def health():
    """Réponse minimale pour que Render vérifie que le site tourne (aucune donnée)."""
    return Response("ok", mimetype="text/plain")


@app.route("/robots.txt")
def robots():
    return Response("User-agent: *\nDisallow: /\n", mimetype="text/plain")


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/channels")
def api_channels():
    search = request.args.get("search", "").strip().lower()
    market = request.args.get("market", "").strip().lower()
    language = request.args.get("language", "").strip().lower()
    view = request.args.get("view", "new").strip().lower()
    status = request.args.get("status", "all").strip().lower()

    channels = list(_get_channels_cached())

    if view == "new":
        channels = [c for c in channels if c["is_new"]]

    if status in ("proven", "watchlist"):
        channels = [c for c in channels if (c.get("channel_status") or "").lower() == status]

    if market and market != "all":
        channels = [c for c in channels if (c.get("market") or "").lower() == market]

    if language and language != "all":
        channels = [c for c in channels if (c.get("detected_language") or "").lower() == language]

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

    reason = request.args.get("reason", "unknown")
    deleted = delete_channel(channel_id, reason)
    _invalidate_cache()
    if deleted:
        return jsonify({"status": "deleted", "channel_id": channel_id})
    return jsonify({"error": "Chaîne introuvable"}), 404


@app.route("/api/markets")
def api_markets():
    channels = _get_channels_cached()
    markets = sorted({c["market"] for c in channels if c.get("market")})
    return jsonify(markets)


@app.route("/api/languages")
def api_languages():
    channels = _get_channels_cached()
    languages = sorted({(c.get("detected_language") or "").lower() for c in channels if c.get("detected_language")})
    return jsonify(languages)


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