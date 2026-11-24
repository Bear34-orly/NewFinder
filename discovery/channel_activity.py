"""
Étape 4 du pipeline : validation de l'activité d'une chaîne, en trois
vérifications successives, puis classement proven/watchlist selon la
performance absolue (pas seulement le ratio).
"""

import time
from datetime import datetime, timedelta, timezone

import requests

from discovery.youtube_client import youtube_get

YOUTUBE_PLAYLIST_ITEMS_URL = "https://www.googleapis.com/youtube/v3/playlistItems"
YOUTUBE_VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"

MAX_MONTHS_BACK = 6
RECENT_ACTIVITY_DAYS = 30
MIN_STRONG_VIDEOS = 3
MAX_TOTAL_VIDEOS_TO_CHECK = 500

PROVEN_VIEWS_THRESHOLD = 100_000
MIN_PROVEN_VIDEOS = 3

MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 2
REQUEST_TIMEOUT = 20


def _parse_date(iso_str: str) -> datetime:
    return datetime.strptime(iso_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def _safe_get(url: str, params: dict) -> requests.Response | None:
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return youtube_get(url, params, timeout=REQUEST_TIMEOUT)
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            print(f"    [!] Erreur réseau (tentative {attempt}/{MAX_RETRIES}): {type(e).__name__}")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY_SECONDS)
    return None


def check_channel_age_and_activity(uploads_playlist_id: str, api_key: str) -> dict:
    cutoff_age = datetime.now(timezone.utc) - timedelta(days=MAX_MONTHS_BACK * 30)
    cutoff_recent = datetime.now(timezone.utc) - timedelta(days=RECENT_ACTIVITY_DAYS)

    video_ids = []
    page_token = None
    is_first_video = True

    while True:
        params = {
            "part": "contentDetails",
            "playlistId": uploads_playlist_id,
            "maxResults": 50,
        }
        if page_token:
            params["pageToken"] = page_token

        resp = _safe_get(YOUTUBE_PLAYLIST_ITEMS_URL, params)
        if resp is None:
            return {"status": "NETWORK_ERROR", "video_ids": []}

        if resp.status_code != 200:
            print(f"  [!] Erreur playlistItems ({resp.status_code}): {resp.text[:150]}")
            return {"status": "ERROR", "video_ids": []}

        data = resp.json()
        items = data.get("items", [])

        for item in items:
            cd = item.get("contentDetails", {})
            video_id = cd.get("videoId")
            published_str = cd.get("videoPublishedAt")
            if not video_id or not published_str:
                continue

            published = _parse_date(published_str)

            if is_first_video:
                is_first_video = False
                if published < cutoff_recent:
                    return {"status": "REJECTED_INACTIVE", "video_ids": []}

            if published < cutoff_age:
                return {"status": "REJECTED_TOO_OLD", "video_ids": []}

            video_ids.append(video_id)

        page_token = data.get("nextPageToken")
        if not page_token:
            return {"status": "OK", "video_ids": video_ids}

        time.sleep(0.1)


def get_video_stats_batch(video_ids: list[str], api_key: str) -> list[dict]:
    if not video_ids:
        return []

    all_stats = []
    for i in range(0, len(video_ids), 50):
        batch = video_ids[i:i + 50]
        params = {"part": "statistics,snippet", "id": ",".join(batch)}

        resp = _safe_get(YOUTUBE_VIDEOS_URL, params)
        if resp is None or resp.status_code != 200:
            continue

        data = resp.json()
        for item in data.get("items", []):
            views = int(item.get("statistics", {}).get("viewCount", 0))
            snippet = item.get("snippet", {})
            title = snippet.get("title", "")
            all_stats.append({"video_id": item["id"], "view_count": views, "title": title,
                              "published_at": snippet.get("publishedAt")})
        time.sleep(0.1)

    return all_stats


def classify_videos(video_stats: list[dict], subscriber_count: int | None,
                     min_views_absolute: int = 200_000,
                     min_ratio: float = 20.0) -> dict:
    strong = []
    proven = []

    for v in video_stats:
        views = v["view_count"]
        ratio = (views / subscriber_count) if subscriber_count else None

        if views >= min_views_absolute or (ratio is not None and ratio >= min_ratio):
            strong.append({**v, "ratio": ratio})

        if views >= PROVEN_VIEWS_THRESHOLD:
            proven.append({**v, "ratio": ratio})

    return {"strong": strong, "proven": proven}


def validate_channel_activity(channel: dict, api_key: str, strong_max_age_days: int | None = None,
                              strong_min_views: int = PROVEN_VIEWS_THRESHOLD) -> dict:
    """
    strong_max_age_days (radar seulement) : si renseigné, la chaîne est rejetée dès qu'elle a une
    vidéo d'au moins strong_min_views vues publiée il y a plus de strong_max_age_days jours.
    """
    uploads_playlist_id = channel.get("uploads_playlist_id")
    if not uploads_playlist_id:
        return {**channel, "activity_status": "NO_PLAYLIST"}

    total_videos = channel.get("video_count", 0)
    if total_videos > MAX_TOTAL_VIDEOS_TO_CHECK:
        return {**channel, "activity_status": "REJECTED_TOO_MANY_VIDEOS"}

    check = check_channel_age_and_activity(uploads_playlist_id, api_key)

    if check["status"] != "OK":
        return {**channel, "activity_status": check["status"]}

    video_stats = get_video_stats_batch(check["video_ids"], api_key)

    if strong_max_age_days is not None:
        limit = datetime.now(timezone.utc) - timedelta(days=strong_max_age_days)
        for v in video_stats:
            published = v.get("published_at")
            if published and v["view_count"] >= strong_min_views and _parse_date(published) < limit:
                return {**channel, "activity_status": "REJECTED_OLD_STRONG_VIDEO"}

    classified = classify_videos(video_stats, channel.get("subscriber_count"))

    strong_videos = classified["strong"]
    proven_videos = classified["proven"]

    if len(strong_videos) < MIN_STRONG_VIDEOS:
        return {**channel, "activity_status": "REJECTED_NOT_ENOUGH_STRONG_VIDEOS",
                "strong_video_count": len(strong_videos)}

    channel_status = "PROVEN" if len(proven_videos) >= MIN_PROVEN_VIDEOS else "WATCHLIST"

    recent_thumbnail_ids = check["video_ids"][:4]

    return {
        **channel,
        "activity_status": "VALID",
        "channel_status": channel_status,
        "strong_video_count": len(strong_videos),
        "proven_video_count": len(proven_videos),
        "strong_videos": strong_videos,
        "proven_videos": proven_videos,
        "total_videos_checked": len(check["video_ids"]),
        "recent_thumbnail_ids": recent_thumbnail_ids,
    }


# ---------------------------------------------------------------------------
# Nouveau site (radar seulement) : critères d'entrée d'une chaîne
# ---------------------------------------------------------------------------

MAX_PAGES_NEW_CHANNEL = 10     # 10 pages de 50 vidéos : au-delà, la chaîne a beaucoup trop de vidéos pour être jeune


def check_new_channel_videos(uploads_playlist_id: str, max_age_days: int, active_days: int) -> dict:
    """
    Lit les vidéos de la chaîne de la plus récente à la plus ancienne (1 unité de quota par 50 vidéos) :
      - la plus récente doit avoir moins de `active_days` jours (sinon REJECTED_INACTIVE) ;
      - dès qu'une vidéo a plus de `max_age_days` jours, la lecture s'arrête (REJECTED_TOO_OLD).
    Retourne {"status": "OK", "video_ids": [...]} si toutes les vidéos sont assez récentes.
    """
    now = datetime.now(timezone.utc)
    cutoff_age = now - timedelta(days=max_age_days)
    cutoff_active = now - timedelta(days=active_days)

    video_ids = []
    page_token = None
    is_first_video = True
    pages = 0

    while True:
        params = {"part": "contentDetails", "playlistId": uploads_playlist_id, "maxResults": 50}
        if page_token:
            params["pageToken"] = page_token

        resp = _safe_get(YOUTUBE_PLAYLIST_ITEMS_URL, params)
        if resp is None:
            return {"status": "NETWORK_ERROR", "video_ids": []}
        if resp.status_code != 200:
            print(f"  [!] Erreur playlistItems ({resp.status_code}): {resp.text[:150]}")
            return {"status": "ERROR", "video_ids": []}

        data = resp.json()
        for item in data.get("items", []):
            cd = item.get("contentDetails", {})
            video_id = cd.get("videoId")
            published_str = cd.get("videoPublishedAt")
            if not video_id or not published_str:
                continue
            published = _parse_date(published_str)

            if is_first_video:
                is_first_video = False
                if published < cutoff_active:
                    return {"status": "REJECTED_INACTIVE", "video_ids": []}

            if published < cutoff_age:
                return {"status": "REJECTED_TOO_OLD", "video_ids": []}

            video_ids.append(video_id)

        pages += 1
        page_token = data.get("nextPageToken")
        if not page_token:
            return {"status": "OK", "video_ids": video_ids}
        if pages >= MAX_PAGES_NEW_CHANNEL:
            return {"status": "REJECTED_TOO_MANY_VIDEOS", "video_ids": []}
        time.sleep(0.1)


def validate_new_channel(channel: dict, max_age_days: int, active_days: int, min_videos: int,
                         min_views: int, min_strong_videos: int) -> dict:
    """
    Critères d'entrée du nouveau site :
      1. au moins `min_strong_videos` vidéo(s) à `min_views` vues ou plus (pas de maximum) ;
      2. au moins `min_videos` vidéos publiées ;
      3. une vidéo publiée il y a moins de `active_days` jours ;
      4. aucune vidéo de plus de `max_age_days` jours.
    Aucune limite d'abonnés. Les contrôles les moins chers passent en premier.
    """
    uploads_playlist_id = channel.get("uploads_playlist_id")
    if not uploads_playlist_id:
        return {**channel, "activity_status": "NO_PLAYLIST"}

    check = check_new_channel_videos(uploads_playlist_id, max_age_days, active_days)
    if check["status"] != "OK":
        return {**channel, "activity_status": check["status"]}

    video_ids = check["video_ids"]
    if len(video_ids) < min_videos:
        return {**channel, "activity_status": "REJECTED_TOO_FEW_VIDEOS", "total_videos_checked": len(video_ids)}

    video_stats = get_video_stats_batch(video_ids, "")
    # Si une partie des lots a échoué (réseau), les chiffres seraient trop bas : on ne juge pas la chaîne.
    if len(video_stats) < 0.9 * len(video_ids):
        return {**channel, "activity_status": "NETWORK_ERROR"}

    classified = classify_videos(video_stats, channel.get("subscriber_count"))
    strong_videos = classified["strong"]
    proven_videos = [v for v in video_stats if v["view_count"] >= min_views]
    proven_videos = [{**v, "ratio": (v["view_count"] / channel["subscriber_count"]) if channel.get("subscriber_count") else None}
                     for v in proven_videos]

    if len(proven_videos) < min_strong_videos:
        return {**channel, "activity_status": "REJECTED_NO_STRONG_VIDEO", "total_videos_checked": len(video_ids)}

    channel_status = "PROVEN" if len(proven_videos) >= MIN_PROVEN_VIDEOS else "WATCHLIST"

    return {
        **channel,
        "activity_status": "VALID",
        "channel_status": channel_status,
        "strong_video_count": len(strong_videos),
        "proven_video_count": len(proven_videos),
        "strong_videos": strong_videos,
        "proven_videos": proven_videos,
        "total_videos_checked": len(video_ids),
        "recent_thumbnail_ids": video_ids[:4],
    }

