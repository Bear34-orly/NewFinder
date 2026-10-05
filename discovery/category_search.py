"""
Recherche par catégorie YouTube + vocabulaire de sujets du marché
(pas de formule de titre, mais plusieurs sujets au lieu d'un terme
générique unique), pour éviter les faux positifs sémantiques comme
"finance" -> "car financing".
"""

import os
import time
from datetime import datetime, timedelta, timezone

import requests
from dotenv import load_dotenv

load_dotenv()

YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"

DISCOVERY_DAYS = 60

# Test contrôlé : quelques sujets représentatifs du marché Finance,
# pas les 12, pour rester dans un budget de quota raisonnable.
TEST_TOPICS = [
    "personal finance",
    "stock market",
    "passive income",
    "financial independence",
]

# Catégories les plus pertinentes observées jusqu'ici pour Finance
TEST_CATEGORIES = {
    "27": "Education",
    "22": "People & Blogs",
    "24": "Entertainment",
    "25": "News & Politics",
}


def _published_after() -> str:
    cutoff = datetime.now(timezone.utc) - timedelta(days=DISCOVERY_DAYS)
    return cutoff.strftime("%Y-%m-%dT%H:%M:%SZ")


def search_by_category(topic: str, category_id: str, api_key: str,
                        max_results: int = 50, order: str = "viewCount",
                        video_duration: str = "medium") -> list[dict]:
    params = {
        "part": "snippet",
        "type": "video",
        "q": topic,
        "videoCategoryId": category_id,
        "order": order,
        "publishedAfter": _published_after(),
        "maxResults": min(max_results, 50),
        "key": api_key,
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
            "query_source": f"{topic}+category:{category_id}",
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

    MARKET = "finance"

    all_results = {}
    total_calls = 0

    for topic in TEST_TOPICS:
        for cat_id, cat_name in TEST_CATEGORIES.items():
            print(f"Recherche: q='{topic}' + catégorie {cat_name} ({cat_id})...")
            results = search_by_category(topic, cat_id, api_key)
            print(f"  {len(results)} vidéos trouvées.")
            total_calls += 1
            for v in results:
                if v["video_id"] in all_results:
                    all_results[v["video_id"]]["query_source"] += f", {v['query_source']}"
                else:
                    all_results[v["video_id"]] = v
            time.sleep(0.2)

    print(f"\n{total_calls} appels de recherche effectués (~{total_calls * 100} unités de quota).")

    results = list(all_results.values())
    print(f"=== {len(results)} vidéos uniques ===")

    print("\nRécupération des stats de vues + langue déclarée...")
    enriched = enrich_and_filter(results, api_key, min_views=20_000)
    print(f"=== {len(enriched)} vidéos avec >= 20K vues ===")

    deduped = dedupe_by_channel(enriched)
    print(f"=== {len(deduped)} chaînes uniques (meilleure vidéo par chaîne) ===")

    print("\nRécupération des stats de chaîne (abonnés, ratio)...")
    with_channels = enrich_with_channel_data(deduped, api_key, max_subscribers=100_000)
    print(f"=== {len(with_channels)} chaînes <= 100K abonnés (candidats émergents) ===")

    print("\nFiltrage par langue...")
    lang_filtered = filter_and_prioritize_by_language(with_channels)
    print(f"=== {len(lang_filtered)} chaînes après filtrage linguistique ===")

    print("\nFiltre faceless (mots-clés)...")
    faceless_candidates = pre_filter_faceless(lang_filtered)
    print(f"=== {len(faceless_candidates)} candidats retenus après filtre faceless ===")

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