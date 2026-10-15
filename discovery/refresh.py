"""
Rafraîchissement des chiffres des chaînes déjà enregistrées.

Pourquoi : les compteurs (vidéos, vidéos fortes, vidéos >= 100K, abonnés) sont
calculés UNE seule fois, le jour de la découverte. Ensuite la chaîne publie de
nouvelles vidéos et ses vues grimpent, mais la base ne le sait pas.

Ce script relit chaque chaîne sur YouTube et met à jour uniquement les chiffres.
Il enregistre aussi les titres des vidéos fortes (apprentissage des mots-clés).
Il ne supprime jamais rien : une chaîne devenue inactive est seulement signalée.

Usage :
    python -m discovery.refresh all
    python -m discovery.refresh history animals
    python -m discovery.refresh all --max 100      (les 100 plus anciennes d'abord)

Coût en quota : environ 3 à 4 unités par chaîne (aucune recherche à 100 unités).
"""

import argparse
import time
from datetime import datetime, timezone

import requests

from discovery.channel_activity import (
    MAX_RETRIES, MIN_PROVEN_VIDEOS, MIN_STRONG_VIDEOS, RECENT_ACTIVITY_DAYS,
    REQUEST_TIMEOUT, RETRY_DELAY_SECONDS, YOUTUBE_PLAYLIST_ITEMS_URL,
    YOUTUBE_VIDEOS_URL, classify_videos, get_video_stats_batch,
)
from discovery.database import list_channel_refs, save_video_titles, update_channel_stats
from discovery.youtube_client import QuotaExhaustedError, has_keys, key_count, youtube_get

YOUTUBE_CHANNELS_URL = "https://www.googleapis.com/youtube/v3/channels"
MAX_VIDEOS_PER_CHANNEL = 500  # même plafond que la découverte


def _get(url: str, params: dict):
    """GET avec quelques essais en cas de coupure réseau. Retourne None si échec."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return youtube_get(url, params, timeout=REQUEST_TIMEOUT)
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY_SECONDS)
    return None


def fetch_channel_infos(channel_ids: list) -> dict:
    """Abonnés, nombre de vidéos et playlist d'uploads (50 chaînes par appel)."""
    infos = {}
    for i in range(0, len(channel_ids), 50):
        chunk = channel_ids[i:i + 50]
        resp = _get(YOUTUBE_CHANNELS_URL, {
            "part": "statistics,contentDetails", "id": ",".join(chunk), "maxResults": 50,
        })
        if resp is None or resp.status_code != 200:
            continue
        for item in resp.json().get("items", []):
            stats = item.get("statistics", {})
            hidden = bool(stats.get("hiddenSubscriberCount"))
            infos[item["id"]] = {
                "subscriber_count": None if hidden else int(stats.get("subscriberCount", 0)),
                "video_count": int(stats.get("videoCount", 0)),
                "uploads": item.get("contentDetails", {}).get("relatedPlaylists", {}).get("uploads"),
            }
    return infos


def list_all_videos(uploads_playlist: str):
    """
    Toutes les vidéos de la chaîne (id + date), de la plus récente à la plus ancienne.
    Retourne None en cas d'erreur réseau/API.
    """
    videos = []
    page_token = None
    while True:
        params = {"part": "contentDetails", "playlistId": uploads_playlist, "maxResults": 50}
        if page_token:
            params["pageToken"] = page_token
        resp = _get(YOUTUBE_PLAYLIST_ITEMS_URL, params)
        if resp is None or resp.status_code != 200:
            return None
        data = resp.json()
        for item in data.get("items", []):
            cd = item.get("contentDetails", {})
            if cd.get("videoId"):
                videos.append({"id": cd["videoId"], "published_at": cd.get("videoPublishedAt")})
        page_token = data.get("nextPageToken")
        if not page_token or len(videos) >= MAX_VIDEOS_PER_CHANNEL:
            return videos[:MAX_VIDEOS_PER_CHANNEL]
        time.sleep(0.1)


def days_since(iso_str):
    if not iso_str:
        return None
    try:
        dt = datetime.strptime(iso_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        return None
    return (datetime.now(timezone.utc) - dt).days


def compute_stats(info: dict, videos: list, old_subscribers) -> dict | None:
    """Recalcule les compteurs avec les mêmes règles que la découverte."""
    if not videos:
        return None
    subs = info["subscriber_count"] if info["subscriber_count"] is not None else old_subscribers
    video_stats = get_video_stats_batch([v["id"] for v in videos], api_key="")
    # Si une partie des lots a échoué (réseau), les chiffres seraient trop bas : on n'écrit rien.
    if len(video_stats) < 0.9 * len(videos):
        return None
    classified = classify_videos(video_stats, subs)
    strong, proven = classified["strong"], classified["proven"]
    total = len(videos)
    return {
        "subscriber_count": subs,
        "video_count": info["video_count"],
        "strong_video_count": len(strong),
        "proven_video_count": len(proven),
        "total_videos_checked": total,
        "density_score": len(strong) / total if total else 0,
        "channel_status": "PROVEN" if len(proven) >= MIN_PROVEN_VIDEOS else "WATCHLIST",
        "recent_thumbnail_ids": [v["id"] for v in videos[:4]],
        # titres des vidéos fortes ou >= 100K : matière de l'apprentissage des mots-clés
        "title_videos": strong + [v for v in proven if v not in strong],
    }


def refresh(market: str | None = None, max_channels: int | None = None) -> dict:
    refs = list_channel_refs(None if not market or market == "all" else market)
    if max_channels:
        refs = refs[:max_channels]
    print(f"{len(refs)} chaîne(s) à rafraîchir.\n")

    result = {"updated": 0, "failed": 0, "inactive": [], "weak": [], "quota_stopped": False}
    if not refs:
        return result

    try:
        infos = fetch_channel_infos([r["channel_id"] for r in refs])
    except QuotaExhaustedError:
        print("[!] Toutes les clés sont épuisées avant de commencer.")
        result["quota_stopped"] = True
        return result

    for i, ref in enumerate(refs, 1):
        name = ref["channel_title"] or ref["channel_id"]
        print(f"  [{i}/{len(refs)}] {name}...", end=" ", flush=True)
        info = infos.get(ref["channel_id"])
        if not info or not info.get("uploads"):
            print("introuvable ou sans vidéos (conservée telle quelle)")
            result["failed"] += 1
            continue
        try:
            videos = list_all_videos(info["uploads"])
            stats = compute_stats(info, videos, ref["subscriber_count"]) if videos else None
        except QuotaExhaustedError:
            print("\n  [!] Toutes les clés sont épuisées : arrêt. Ce qui est déjà mis à jour est sauvegardé.")
            result["quota_stopped"] = True
            break
        if not stats:
            print("échec réseau ou API (conservée telle quelle)")
            result["failed"] += 1
            continue

        update_channel_stats(ref["channel_id"], stats)
        save_video_titles(ref["channel_id"], ref.get("market"), ref.get("detected_language"),
                          stats.pop("title_videos", []))
        result["updated"] += 1
        print(f"{stats['proven_video_count']} >=100K | {stats['strong_video_count']} fortes | "
              f"{stats['total_videos_checked']} vidéos | {stats['channel_status']}")

        last = days_since(videos[0]["published_at"])
        if last is not None and last > RECENT_ACTIVITY_DAYS:
            result["inactive"].append((name, last))
        if stats["strong_video_count"] < MIN_STRONG_VIDEOS:
            result["weak"].append(name)

    print(f"\n=== {result['updated']} mise(s) à jour, {result['failed']} non modifiée(s) ===")
    if result["inactive"]:
        print(f"\nChaînes sans nouvelle vidéo depuis plus de {RECENT_ACTIVITY_DAYS} jours (non supprimées) :")
        for name, d in result["inactive"]:
            print(f"  - {name} : {d} jours")
    if result["weak"]:
        print(f"\nChaînes passées sous {MIN_STRONG_VIDEOS} vidéos fortes (non supprimées) :")
        for name in result["weak"]:
            print(f"  - {name}")
    return result


if __name__ == "__main__":
    from config.markets import MARKETS

    parser = argparse.ArgumentParser(description="Met à jour les compteurs des chaînes déjà enregistrées.")
    parser.add_argument("markets", nargs="*", default=["all"],
                        help="Un ou plusieurs marchés, ou 'all' (par défaut).")
    parser.add_argument("--max", type=int, default=None,
                        help="Nombre maximum de chaînes à traiter (les plus anciennement vérifiées d'abord).")
    args = parser.parse_args()

    if not has_keys():
        raise SystemExit("Aucune clé API trouvée : renseigne YOUTUBE_API_KEYS dans .env.")

    unknown = [m for m in args.markets if m != "all" and m not in MARKETS]
    if unknown:
        raise SystemExit(f"Marché(s) inconnu(s): {unknown}")

    print(f"{key_count()} clé(s) API chargée(s).")
    for m in args.markets:
        print(f"\n##### {m.upper()} #####")
        r = refresh(m, args.max)
        if r["quota_stopped"]:
            break