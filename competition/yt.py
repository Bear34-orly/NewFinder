"""
Appels à l'API YouTube pour le module Concurrence.

Tous les appels passent par youtube_get (rotation automatique des clés).
Un compteur d'unités de quota estime le coût de chaque analyse :
  - channels.list / playlistItems.list / videos.list = 1 unité
  - search.list = 100 unités
"""

import re
from datetime import datetime, timedelta, timezone

from discovery.youtube_client import youtube_get

BASE = "https://www.googleapis.com/youtube/v3"

LONG_MIN_SECONDS = 181  # au-dessus de 3 minutes = format long (les Shorts vont jusqu'à 3 min)


class ChannelNotFound(Exception):
    pass


class Tracker:
    """Compte les unités de quota consommées pendant une analyse."""

    def __init__(self):
        self.units = 0

    def add(self, n: int):
        self.units += n


def parse_duration(iso: str) -> int:
    """'PT1H2M3S' -> secondes."""
    m = re.fullmatch(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso or "")
    if not m:
        return 0
    d, h, mi, s = (int(x) if x else 0 for x in m.groups())
    return d * 86400 + h * 3600 + mi * 60 + s


def _get(path: str, params: dict, tracker: Tracker, cost: int) -> dict:
    resp = youtube_get(f"{BASE}/{path}", params)
    tracker.add(cost)
    if resp.status_code != 200:
        raise RuntimeError(f"Erreur API YouTube ({resp.status_code}) sur {path}: {resp.text[:200]}")
    return resp.json()


def _channel_from_item(item: dict) -> dict:
    snippet = item.get("snippet", {})
    stats = item.get("statistics", {})
    uploads = item.get("contentDetails", {}).get("relatedPlaylists", {}).get("uploads")
    cid = item["id"]
    thumbs = snippet.get("thumbnails", {})
    thumb = (thumbs.get("medium") or thumbs.get("default") or {}).get("url")
    hidden = bool(stats.get("hiddenSubscriberCount"))
    return {
        "channel_id": cid,
        "title": snippet.get("title"),
        "handle": snippet.get("customUrl"),
        "url": f"https://www.youtube.com/channel/{cid}",
        "thumbnail": thumb,
        "published_at": snippet.get("publishedAt"),
        "country": snippet.get("country"),
        "subscribers": None if hidden else int(stats.get("subscriberCount", 0)),
        "total_views": int(stats.get("viewCount", 0)),
        "video_count": int(stats.get("videoCount", 0)),
        "uploads_playlist": uploads or ("UU" + cid[2:]),
    }


def parse_channel_input(text: str) -> dict:
    """
    Comprend un lien ou un nom de chaîne.
    Retourne {"id": ...} ou {"handle": ...} ou {"username": ...}.
    """
    text = (text or "").strip()
    if not text:
        raise ChannelNotFound("Lien de chaîne vide.")

    m = re.search(r"youtube\.com/channel/(UC[\w-]{20,})", text)
    if m:
        return {"id": m.group(1)}
    if re.fullmatch(r"UC[\w-]{20,}", text):
        return {"id": text}

    m = re.search(r"youtube\.com/@([^/?#\s]+)", text)
    if m:
        return {"handle": m.group(1)}
    if text.startswith("@"):
        return {"handle": text[1:]}

    m = re.search(r"youtube\.com/user/([^/?#\s]+)", text)
    if m:
        return {"username": m.group(1)}

    if re.fullmatch(r"[\w.\-]{3,40}", text):
        return {"handle": text}

    raise ChannelNotFound(
        "Je ne reconnais pas ce lien. Utilise le lien de la chaîne avec @nom "
        "(ex: https://www.youtube.com/@nom) ou le lien /channel/UC..."
    )


def resolve_channel(text: str, tracker: Tracker) -> dict:
    ref = parse_channel_input(text)
    params = {"part": "snippet,statistics,contentDetails", "maxResults": 1}
    if "id" in ref:
        params["id"] = ref["id"]
    elif "handle" in ref:
        params["forHandle"] = "@" + ref["handle"]
    else:
        params["forUsername"] = ref["username"]

    data = _get("channels", params, tracker, 1)
    items = data.get("items", [])
    if not items:
        raise ChannelNotFound("Chaîne introuvable. Vérifie le lien.")
    return _channel_from_item(items[0])


def get_channels(channel_ids: list, tracker: Tracker) -> dict:
    """Infos de plusieurs chaînes (50 par appel). Retourne {channel_id: info}."""
    result = {}
    ids = list(dict.fromkeys(channel_ids))
    for i in range(0, len(ids), 50):
        chunk = ids[i:i + 50]
        data = _get("channels", {
            "part": "snippet,statistics,contentDetails",
            "id": ",".join(chunk),
            "maxResults": 50,
        }, tracker, 1)
        for item in data.get("items", []):
            result[item["id"]] = _channel_from_item(item)
    return result


def get_recent_videos(uploads_playlist: str, tracker: Tracker, limit: int = 50) -> list:
    """Les dernières vidéos d'une chaîne, avec vues, durée et date (2 unités)."""
    data = _get("playlistItems", {
        "part": "contentDetails",
        "playlistId": uploads_playlist,
        "maxResults": min(limit, 50),
    }, tracker, 1)
    ids = [it["contentDetails"]["videoId"] for it in data.get("items", [])]
    if not ids:
        return []

    data = _get("videos", {
        "part": "snippet,contentDetails,statistics",
        "id": ",".join(ids),
        "maxResults": 50,
    }, tracker, 1)

    videos = []
    for it in data.get("items", []):
        stats = it.get("statistics", {})
        snippet = it.get("snippet", {})
        videos.append({
            "id": it["id"],
            "title": snippet.get("title", ""),
            "published_at": snippet.get("publishedAt"),
            "duration_s": parse_duration(it.get("contentDetails", {}).get("duration")),
            "views": int(stats.get("viewCount", 0)),
            "likes": int(stats.get("likeCount", 0)),
            "comments": int(stats.get("commentCount", 0)),
        })
    return videos


def search_videos(query: str, language: str, tracker: Tracker, days: int = 365) -> list:
    """Une recherche (100 unités). Retourne [{channel_id, video_id, title}]."""
    published_after = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    data = _get("search", {
        "part": "snippet",
        "q": query,
        "type": "video",
        "order": "viewCount",
        "publishedAfter": published_after,
        "maxResults": 50,
        "relevanceLanguage": language,
        "safeSearch": "moderate",
    }, tracker, 100)

    out = []
    for it in data.get("items", []):
        vid = it.get("id", {}).get("videoId")
        sn = it.get("snippet", {})
        if vid and sn.get("channelId"):
            out.append({"channel_id": sn["channelId"], "video_id": vid, "title": sn.get("title", "")})
    return out
