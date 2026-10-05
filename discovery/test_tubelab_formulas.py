"""
Test empirique : on remplace nos formules de titre "devinées" par les
formules VÉRIFIÉES par TubeLab (avec ratio de performance et volume
réel), et on regarde ce que ça donne une fois passé dans YouTube Data
API + notre pipeline complet de validation.
"""

import os
import time
from datetime import datetime, timedelta, timezone

import requests
from dotenv import load_dotenv

load_dotenv()

YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
DISCOVERY_DAYS = 60

# Formules extraites des résultats TubeLab (pattern simplifié en texte
# de recherche exploitable), avec leur ratio de performance d'origine
# noté en commentaire pour référence.
TUBELAB_FORMULAS = {
    "history": [
        "finally solved the mystery",   # ratio 8.77x
        "your life as",                  # ratio 4.53x, 523 vidéos
        "lost city of",                  # ratio 7.05x
        "how did ancient humans survive without",  # ratio 5.46x
        "how did humans discover",       # ratio 4.96x
    ],
    "finance": [
        "stop wasting money on",         # ratio 8.23x
        "why looking poor is important", # ratio 7.49x
        "what can $ get in",             # ratio 6.61x
        "is about to change",            # ratio 5.28x
    ],
}

# Sujets de base, réutilisés depuis config/markets.py
BASE_TOPICS = {
    "history": ["ancient civilizations", "roman empire", "ancient egypt", "medieval history"],
    "finance": ["personal finance", "stock market", "passive income", "real estate investing"],
}


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

    MARKET = "history"  # change ici pour tester "finance"

    formulas = TUBELAB_FORMULAS[MARKET]
    topics = BASE_TOPICS[MARKET]

    # Requêtes: formule seule (large) + formule combinée à un sujet
    queries = list(formulas)
    for topic in topics[:2]:
        for formula in formulas[:2]:
            queries.append(f"{formula} {topic}")

    print(f"{len(queries)} requêtes générées à partir des formules TubeLab pour '{MARKET}'.\n")

    all_results = {}
    for i, query in enumerate(queries, 1):
        print(f"[{i}/{len(queries)}] Recherche: '{query}'")
        for duration in ("medium", "long"):
            videos = search_videos(query, api_key, video_duration=duration)
            for v in videos:
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

    print("\nValidation de l'activité...")
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