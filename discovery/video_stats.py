"""
Étape 2 du pipeline : récupération des statistiques de vues ET de la
langue déclarée (defaultAudioLanguage) pour les vidéos découvertes,
tri par performance, et déduplication par chaîne.
"""

import time

from discovery.youtube_client import youtube_get

YOUTUBE_VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"

BATCH_SIZE = 50


def get_video_stats(video_ids: list[str], api_key: str) -> dict[str, dict]:
    stats = {}

    for i in range(0, len(video_ids), BATCH_SIZE):
        batch = video_ids[i:i + BATCH_SIZE]
        params = {
            "part": "statistics,snippet",
            "id": ",".join(batch),
        }

        resp = youtube_get(YOUTUBE_VIDEOS_URL, params, timeout=15)

        if resp.status_code != 200:
            print(f"  [!] Erreur API stats ({resp.status_code}): {resp.text[:200]}")
            continue

        data = resp.json()
        for item in data.get("items", []):
            vid = item.get("id")
            statistics = item.get("statistics", {})
            snippet = item.get("snippet", {})

            declared_lang = snippet.get("defaultAudioLanguage") or snippet.get("defaultLanguage")

            stats[vid] = {
                "view_count": int(statistics.get("viewCount", 0)),
                "like_count": int(statistics.get("likeCount", 0)) if "likeCount" in statistics else None,
                "comment_count": int(statistics.get("commentCount", 0)) if "commentCount" in statistics else None,
                "declared_language": declared_lang,
            }

        time.sleep(0.1)

    return stats


def enrich_and_filter(videos: list[dict], api_key: str, min_views: int = 20_000) -> list[dict]:
    video_ids = [v["video_id"] for v in videos]
    stats = get_video_stats(video_ids, api_key)

    enriched = []
    for v in videos:
        s = stats.get(v["video_id"])
        if not s:
            continue
        v = {**v, **s}
        if v["view_count"] >= min_views:
            enriched.append(v)

    enriched.sort(key=lambda v: v["view_count"], reverse=True)
    return enriched


def dedupe_by_channel(videos: list[dict]) -> list[dict]:
    seen_channels = set()
    result = []
    for v in videos:
        if v["channel_id"] not in seen_channels:
            seen_channels.add(v["channel_id"])
            result.append(v)
    return result