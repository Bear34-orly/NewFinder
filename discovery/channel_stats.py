"""
Étape 3 du pipeline : récupération des statistiques de chaîne
(abonnés, nb de vidéos, playlist uploads, avatar, bannière,
description) pour calculer le ratio vues/abonnés et exclure les
grosses chaînes déjà établies.
"""

import time

from discovery.youtube_client import youtube_get

YOUTUBE_CHANNELS_URL = "https://www.googleapis.com/youtube/v3/channels"

BATCH_SIZE = 50


def get_channel_stats(channel_ids: list[str], api_key: str) -> dict[str, dict]:
    stats = {}

    for i in range(0, len(channel_ids), BATCH_SIZE):
        batch = channel_ids[i:i + BATCH_SIZE]
        params = {
            "part": "snippet,statistics,contentDetails,brandingSettings",
            "id": ",".join(batch),
        }

        resp = youtube_get(YOUTUBE_CHANNELS_URL, params, timeout=15)

        if resp.status_code != 200:
            print(f"  [!] Erreur API channels ({resp.status_code}): {resp.text[:200]}")
            continue

        data = resp.json()
        for item in data.get("items", []):
            cid = item.get("id")
            snippet = item.get("snippet", {})
            statistics = item.get("statistics", {})
            content_details = item.get("contentDetails", {})
            branding = item.get("brandingSettings", {})
            uploads_playlist = content_details.get("relatedPlaylists", {}).get("uploads")

            subscriber_count = statistics.get("subscriberCount")
            subscriber_count = int(subscriber_count) if subscriber_count is not None else None

            thumbnails = snippet.get("thumbnails", {})
            avatar_url = (
                thumbnails.get("high", {}).get("url")
                or thumbnails.get("medium", {}).get("url")
                or thumbnails.get("default", {}).get("url")
            )

            banner_url = branding.get("image", {}).get("bannerExternalUrl")

            description = snippet.get("description", "") or ""
            short_description = description.strip().replace("\n", " ")[:200]
            if len(description) > 200:
                short_description += "..."

            stats[cid] = {
                "subscriber_count": subscriber_count,
                "video_count": int(statistics.get("videoCount", 0)),
                "channel_view_count": int(statistics.get("viewCount", 0)),
                "uploads_playlist_id": uploads_playlist,
                "channel_thumbnail_url": avatar_url,
                "channel_banner_url": banner_url,
                "channel_description": short_description,
            }

        time.sleep(0.1)

    return stats


def enrich_with_channel_data(
    videos: list[dict],
    api_key: str,
    max_subscribers: int = 100_000,
) -> list[dict]:
    channel_ids = list({v["channel_id"] for v in videos})
    stats = get_channel_stats(channel_ids, api_key)

    enriched = []
    for v in videos:
        c = stats.get(v["channel_id"])
        if not c:
            continue

        subs = c["subscriber_count"]

        if subs is not None and subs > max_subscribers:
            continue

        ratio = (v["view_count"] / subs) if subs else None

        enriched.append({
            **v,
            **c,
            "view_sub_ratio": round(ratio, 1) if ratio else None,
        })

    enriched.sort(key=lambda v: (v["view_sub_ratio"] is None, -(v["view_sub_ratio"] or 0)))
    return enriched