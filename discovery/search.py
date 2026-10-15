"""
Étape 1 du pipeline : recherche de vidéos candidates sur les 60 derniers
jours, pour un ou plusieurs marchés donnés en argument, avec déduplication.
Les clés API tournent automatiquement (voir youtube_client.py).

Usage:
    python -m discovery.search history
    python -m discovery.search history finance military
    python -m discovery.search all
"""

import argparse
import time
from datetime import datetime, timedelta, timezone

import requests
from dotenv import load_dotenv

from discovery.youtube_client import QuotaExhaustedError, has_keys, key_count, youtube_get

load_dotenv()

YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"

DISCOVERY_DAYS = 60

MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 3
REQUEST_TIMEOUT = 20


def _rfc3339(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _published_after() -> str:
    cutoff = datetime.now(timezone.utc) - timedelta(days=DISCOVERY_DAYS)
    return _rfc3339(cutoff)


def _safe_get(url: str, params: dict):
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return youtube_get(url, params, timeout=REQUEST_TIMEOUT)
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            print(f"    [!] Erreur réseau (tentative {attempt}/{MAX_RETRIES}): {type(e).__name__}")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY_SECONDS)
    return None


def search_videos(query: str, api_key: str, order: str = "viewCount", max_results: int = 25, video_duration: str = "medium") -> list[dict]:
    params = {
        "part": "snippet",
        "q": query,
        "type": "video",
        "order": order,
        "publishedAfter": _published_after(),
        "maxResults": min(max_results, 50),
        "relevanceLanguage": "en",
        "safeSearch": "moderate",
        "videoDuration": video_duration,
    }

    resp = _safe_get(YOUTUBE_SEARCH_URL, params)

    if resp is None:
        print(f"  [!] Échec réseau persistant pour la requête '{query}', on continue sans ces résultats.")
        return []

    if resp.status_code != 200:
        print(f"  [!] Erreur API ({resp.status_code}) pour la requête '{query}': {resp.text[:200]}")
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


def discover_market(market_queries: list[str], api_key: str, sleep_between_calls: float = 0.2) -> list[dict]:
    all_results = {}

    for i, query in enumerate(market_queries, 1):
        print(f"[{i}/{len(market_queries)}] Recherche: '{query}'")

        for duration in ("medium", "long"):
            videos = search_videos(query, api_key, order="viewCount", video_duration=duration)
            for v in videos:
                if v["video_id"] not in all_results:
                    all_results[v["video_id"]] = v
                else:
                    existing_source = all_results[v["video_id"]]["query_source"]
                    if query not in existing_source:
                        all_results[v["video_id"]]["query_source"] = f"{existing_source}, {query}"

            time.sleep(sleep_between_calls)

    return list(all_results.values())


def run_for_market(market: str, api_key: str):
    """Retourne (nombre de chaînes validées, quota_épuisé)."""
    from config.markets import build_queries
    from discovery.video_stats import enrich_and_filter, dedupe_by_channel
    from discovery.channel_stats import enrich_with_channel_data
    from discovery.language_filter import filter_and_prioritize_by_language
    from discovery.faceless_filter import pre_filter_faceless
    from discovery.channel_activity import validate_channel_activity
    from discovery.database import save_validated_channels

    print(f"\n{'#' * 60}")
    print(f"# MARCHÉ : {market.upper()}")
    print(f"{'#' * 60}\n")

    queries = build_queries(market)
    print(f"{len(queries)} requêtes générées pour '{market}'.\n")

    results = discover_market(queries, api_key)
    print(f"\n=== {len(results)} vidéos uniques trouvées (60 derniers jours) ===")

    # Chaînes supprimées par l'utilisateur : on ne les retraite jamais (économise du quota).
    from discovery.database import list_rejected_ids
    rejected = list_rejected_ids()
    if rejected:
        before = len(results)
        results = [r for r in results if r["channel_id"] not in rejected]
        print(f"=== {before - len(results)} vidéos ignorées (chaînes déjà refusées) ===")

    print("\nRécupération des stats de vues + langue déclarée...")
    enriched = enrich_and_filter(results, api_key, min_views=20_000)
    print(f"=== {len(enriched)} vidéos avec >= 20K vues ===")

    deduped = dedupe_by_channel(enriched)
    print(f"=== {len(deduped)} chaînes uniques (meilleure vidéo par chaîne) ===")

    print("\nRécupération des stats de chaîne (abonnés, ratio)...")
    with_channels = enrich_with_channel_data(deduped, api_key, max_subscribers=100_000)
    print(f"=== {len(with_channels)} chaînes <= 100K abonnés (candidats émergents) ===")

    print("\nFiltrage par langue (declared_language en priorité, en > es > fr > de/ru)...")
    lang_filtered = filter_and_prioritize_by_language(with_channels)
    print(f"=== {len(lang_filtered)} chaînes après filtrage linguistique ===")

    print("\nFiltre faceless (mots-clés, avant analyse coûteuse d'activité)...")
    faceless_candidates = pre_filter_faceless(lang_filtered)
    print(f"=== {len(faceless_candidates)} candidats retenus après filtre faceless ===")

    print("\nValidation de l'activité (âge <6 mois + publie encore + vidéos fortes)...")
    validated = []
    quota_stopped = False
    for i, channel in enumerate(faceless_candidates, 1):
        print(f"  [{i}/{len(faceless_candidates)}] {channel['channel_title']}...", end=" ")
        try:
            result = validate_channel_activity(channel, api_key)
        except QuotaExhaustedError:
            print("\n  [!] Toutes les clés sont épuisées : arrêt de la validation, sauvegarde de ce qui est déjà validé.")
            quota_stopped = True
            break
        status_display = result["activity_status"]
        if status_display == "VALID":
            status_display += f" ({result['channel_status']})"
        print(status_display)
        if result["activity_status"] == "VALID":
            result["density_score"] = result["strong_video_count"] / result["total_videos_checked"]
            result["channel_url"] = f"https://www.youtube.com/channel/{result['channel_id']}"
            validated.append(result)

    validated.sort(key=lambda v: (v["channel_status"] != "PROVEN", -v["density_score"]))

    proven_count = sum(1 for v in validated if v["channel_status"] == "PROVEN")
    watchlist_count = len(validated) - proven_count

    print(f"\n=== {len(validated)} CHAÎNES VALIDÉES pour '{market}' "
          f"({proven_count} proven, {watchlist_count} watchlist) ===\n")
    for v in validated:
        print(f"- [{v['channel_status']}] [{v['density_score']:.0%}] {v['channel_title']} | "
              f"{v['subscriber_count']:,} abonnés | {v['proven_video_count']} vidéos >=100K | "
              f"{v['strong_video_count']} vidéos fortes sur {v['total_videos_checked']} vidéos")
        print(f"    {v['channel_url']}")

    save_validated_channels(validated, market=market)

    return len(validated), quota_stopped


if __name__ == "__main__":
    from config.markets import MARKETS

    parser = argparse.ArgumentParser(description="Découverte de chaînes faceless émergentes par marché.")
    parser.add_argument(
        "markets",
        nargs="+",
        help="Un ou plusieurs marchés à traiter (ex: history finance military), ou 'all' pour tous les marchés définis.",
    )
    args = parser.parse_args()

    if not has_keys():
        raise SystemExit("Aucune clé API trouvée : renseigne YOUTUBE_API_KEYS (ou YOUTUBE_API_KEY) dans .env.")

    # Les clés sont gérées par youtube_client.py : ce paramètre n'est plus utilisé.
    api_key = ""

    if "all" in [m.lower() for m in args.markets]:
        markets_to_run = list(MARKETS.keys())
    else:
        markets_to_run = args.markets
        unknown = [m for m in markets_to_run if m not in MARKETS]
        if unknown:
            raise SystemExit(f"Marché(s) inconnu(s): {unknown}. Marchés disponibles: {list(MARKETS.keys())}")

    print(f"{key_count()} clé(s) API chargée(s).")
    print(f"Marchés à traiter : {markets_to_run}\n")

    summary = {}
    for market in markets_to_run:
        try:
            count, quota_stopped = run_for_market(market, api_key)
        except QuotaExhaustedError:
            print(f"\n[!] Toutes les clés sont épuisées pendant la recherche de '{market}'. Arrêt.")
            summary[market] = "interrompu (quota)"
            break
        summary[market] = count
        if quota_stopped:
            print("\n[!] Quota épuisé sur toutes les clés : les marchés suivants ne sont pas lancés.")
            break

    print(f"\n{'=' * 60}")
    print("RÉSUMÉ GLOBAL")
    print(f"{'=' * 60}\n")
    for market, count in summary.items():
        print(f"  {market}: {count} chaîne(s) validée(s)" if isinstance(count, int) else f"  {market}: {count}")