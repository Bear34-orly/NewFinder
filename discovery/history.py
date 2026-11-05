"""
Photo quotidienne de toutes les chaînes : abonnés, vues totales, nombre de vidéos.

Une ligne par chaîne et par jour dans la table channel_history. C'est ce qui permet de voir
qui MONTE vite (abonnés gagnés sur 7 jours), pas seulement qui est gros aujourd'hui.

Coût YouTube : 1 unité par groupe de 50 chaînes (2 000 chaînes = 40 unités).

Usage :
    python -m discovery.history            # photo du jour (crée l'historique de départ au 1er lancement)
    python -m discovery.history --status   # résumé de l'historique
"""

import argparse
import time

import requests

from discovery.database import (
    history_summary, list_channel_ids, save_history_snapshots, seed_history_from_channels,
)
from discovery.youtube_client import QuotaExhaustedError, has_keys, youtube_get

YOUTUBE_CHANNELS_URL = "https://www.googleapis.com/youtube/v3/channels"
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 5


def _get(params: dict):
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return youtube_get(YOUTUBE_CHANNELS_URL, params, timeout=20)
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY_SECONDS)
    return None


def fetch_counts(channel_ids: list[str]) -> list[dict]:
    """Abonnés, vues et nombre de vidéos de chaque chaîne (50 par appel). Abonnés masqués => None."""
    rows = []
    for i in range(0, len(channel_ids), 50):
        chunk = channel_ids[i:i + 50]
        resp = _get({"part": "statistics", "id": ",".join(chunk), "maxResults": 50})
        if resp is None or resp.status_code != 200:
            continue
        for item in resp.json().get("items", []):
            st = item.get("statistics", {})
            hidden = bool(st.get("hiddenSubscriberCount"))
            rows.append({
                "channel_id": item["id"],
                "subscriber_count": None if hidden else int(st.get("subscriberCount", 0)),
                "view_count": int(st["viewCount"]) if "viewCount" in st else None,
                "video_count": int(st["videoCount"]) if "videoCount" in st else None,
            })
    return rows


def snapshot() -> dict:
    ids = list_channel_ids()
    seeded = seed_history_from_channels()
    if seeded:
        print(f"Historique de départ : {seeded} chaînes (chiffres de leur dernière vérification).")
    if not ids:
        print("Aucune chaîne en base.")
        return {"channels": 0, "saved": 0}
    if not has_keys():
        print("Aucune clé YouTube : photo du jour impossible.")
        return {"channels": len(ids), "saved": 0}
    try:
        rows = fetch_counts(ids)
    except QuotaExhaustedError:
        print("Quota YouTube épuisé : photo du jour non faite.")
        return {"channels": len(ids), "saved": 0}
    saved = save_history_snapshots(rows)
    missing = len(ids) - len(rows)
    print(f"Photo du jour : {saved} chaînes enregistrées sur {len(ids)}"
          + (f" ({missing} introuvables côté YouTube)." if missing else "."))
    return {"channels": len(ids), "saved": saved}


def status():
    s = history_summary()
    print(f"Historique : {s['rows']} lignes, {s['channels']} chaînes, {s['days_recorded']} jour(s) "
          f"({s['first_day']} -> {s['last_day']}).")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--status", action="store_true")
    args = ap.parse_args()
    status() if args.status else snapshot()
