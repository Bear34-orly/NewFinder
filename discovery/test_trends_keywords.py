"""
Test à côté de search.py : utilise les mots-clés extraits de l'analyse
Google Trends (History × Finance) pour lancer une recherche ciblée,
faire passer les résultats par tout le pipeline de validation habituel,
et stocker les chaînes trouvées immédiatement pour analyse ultérieure.
"""

import os
import time
from datetime import datetime, timedelta, timezone

import requests
from dotenv import load_dotenv

load_dotenv()

YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
DISCOVERY_DAYS = 60

# Mots-clés retenus depuis l'analyse Google Trends (bruit déjà écarté :
# BTS history, Epic Rap Battles, Caleb Hammer, etc.)
TRENDS_KEYWORDS = [
"european intellectual history since nietzsche",
"forgotten weapons",
"history by mae",
"lake of the ozarks history",
"drunk history dolly parton",
"history student",
"drunk history thomas jefferson",
"history of concrete",
"history of concrete john wilson",
"history of concrete trailer",
"tasting history",
"history for granite",
"logo history",
"history of",
"20th century fox history",
"20th century fox",
"20th century fox logo history",
"20th century fox logo",
"boring",
"boring history",
"history documentary",
"documentary",
]

MARKET = "history"  # marché de rattachement pour le stockage en base


def _published_after() -> str:
    cutoff = datetime.now(timezone.utc) - timedelta(days=DISCOVERY_DAYS)
    return cutoff.strftime("%Y-%m-%dT%H:%M:%SZ")


def search_videos(query: str, api_key: str, order: str = "viewCount", video_duration: str = "medium") -> list[dict]:
    params = {
        "part": "snippet",
        "q": query,
        "type": "video",
        "order": order,
        "publishedAfter": _published_after(),
        "maxResults": 50,
        "key": api_key,
        "relevanceLanguage": "en",
        "safeSearch": "moderate",
        "videoDuration": video_duration,
    }
    resp = requests.get(YOUTUBE_SEARCH_URL, params=params, timeout=15)
    if resp.status_code != 200:
        print(f"  [!] Erreur API ({resp.status_code}): {resp.text[:200]}")
        return []
    data = resp.json()
    results = []
    for item in data.get("items", []):
        vid = item.get("id", {}).get("videoId")
        if not vid:
            continue
        snippet = item.get("snippet", {})
        results.append({
            "video_id": vid,
            "title": snippet.get("title"),
            "channel_id": snippet.get("channelId"),
            "channel_title": snippet.get("channelTitle"),
            "published_at": snippet.get("publishedAt"),
            "query_source": query,
        })
    return results


if __name__ == "__main__":
    from discovery.video_stats import enrich_and_filter, dedupe_by_channel
    from discovery.channel_stats import enrich_with_channel_data
    from discovery.language_filter import filter_and_prioritize_by_language
    from discovery.faceless_filter import pre_filter_faceless
    from discovery.channel_activity import validate_channel_activity
    from discovery.database import save_validated_channels, list_all_channels

    api_key = os.environ.get("YOUTUBE_API_KEY")
    if not api_key:
        raise SystemExit("YOUTUBE_API_KEY manquant dans .env")

    all_results = {}
    for i, query in enumerate(TRENDS_KEYWORDS, 1):
        print(f"[{i}/{len(TRENDS_KEYWORDS)}] Recherche: '{query}'")
        for duration in ("medium", "long"):
            videos = search_videos(query, api_key, video_duration=duration)
            for v in videos:
                if v["video_id"] not in all_results:
                    all_results[v["video_id"]] = v
            time.sleep(0.2)

    results = list(all_results.values())
    print(f"\n=== {len(results)} vidéos uniques trouvées ===")

    print("\nRécupération des stats de vues + langue déclarée...")
    enriched = enrich_and_filter(results, api_key, min_views=20_000)
    print(f"=== {len(enriched)} vidéos avec >= 20K vues ===")

    deduped = dedupe_by_channel(enriched)
    print(f"=== {len(deduped)} chaînes uniques ===")

    print("\nRécupération des stats de chaîne...")
    with_channels = enrich_with_channel_data(deduped, api_key, max_subscribers=100_000)
    print(f"=== {len(with_channels)} chaînes <= 100K abonnés ===")

    print("\nFiltrage par langue...")
    lang_filtered = filter_and_prioritize_by_language(with_channels)
    print(f"=== {len(lang_filtered)} chaînes après filtrage linguistique ===")

    print("\nFiltre faceless...")
    faceless_candidates = pre_filter_faceless(lang_filtered)
    print(f"=== {len(faceless_candidates)} candidats après filtre faceless ===")

    print("\nValidation de l'activité (âge <6 mois + publie encore + vidéos fortes)...")
    validated = []
    for i, channel in enumerate(faceless_candidates, 1):
        print(f"  [{i}/{len(faceless_candidates)}] {channel['channel_title']}...", end=" ")
        result = validate_channel_activity(channel, api_key)
        print(result["activity_status"])
        if result["activity_status"] == "VALID":
            result["density_score"] = result["strong_video_count"] / result["total_videos_checked"]
            result["channel_url"] = f"https://www.youtube.com/channel/{result['channel_id']}"
            validated.append(result)

    validated.sort(key=lambda v: v["density_score"], reverse=True)

    existing_ids = {c["channel_id"] for c in list_all_channels()}
    new_channels = [v for v in validated if v["channel_id"] not in existing_ids]
    known_channels = [v for v in validated if v["channel_id"] in existing_ids]

    print(f"\n=== {len(new_channels)} NOUVELLES chaînes (jamais vues avant) ===\n")
    for v in new_channels:
        print(f"- [{v['density_score']:.0%}] {v['channel_title']} | {v['subscriber_count']:,} abonnés | "
              f"{v['strong_video_count']}/{v['total_videos_checked']} vidéos fortes")
        print(f"    {v['channel_url']}")
        print(f"    trouvée via: {v['query_source']}")

    print(f"\n=== {len(known_channels)} chaînes déjà connues ===\n")
    for v in known_channels:
        print(f"- {v['channel_title']}")

    if new_channels:
        save_validated_channels(new_channels, market=MARKET)
        print(f"\n{len(new_channels)} chaînes enregistrées dans la base.")