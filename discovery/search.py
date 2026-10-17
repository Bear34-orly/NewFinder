"""
Étape 1 du pipeline : recherche de vidéos candidates sur les 60 derniers
jours, pour un ou plusieurs marchés donnés en argument, avec déduplication.
Les clés API tournent automatiquement (voir youtube_client.py).

Usage:
    python -m discovery.search history
    python -m discovery.search history finance military
    python -m discovery.search all
    python -m discovery.search all --lang en        (par défaut : anglais)
    python -m discovery.search all --lang others    (espagnol, français, allemand, russe)
    python -m discovery.search history --lang fr    (une seule langue)
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


def search_videos(query: str, api_key: str, order: str = "viewCount", max_results: int = 25,
                  video_duration: str = "medium", language: str = "en") -> list[dict]:
    params = {
        "part": "snippet",
        "q": query,
        "type": "video",
        "order": order,
        "publishedAfter": _published_after(),
        "maxResults": min(max_results, 50),
        "relevanceLanguage": language,
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


def discover_market(market_queries: list[str], api_key: str, sleep_between_calls: float = 0.2,
                    language: str = "en") -> list[dict]:
    all_results = {}

    for i, query in enumerate(market_queries, 1):
        print(f"[{i}/{len(market_queries)}] Recherche: '{query}'")

        for duration in ("medium", "long"):
            videos = search_videos(query, api_key, order="viewCount", video_duration=duration, language=language)
            for v in videos:
                if v["video_id"] not in all_results:
                    all_results[v["video_id"]] = v
                else:
                    existing_source = all_results[v["video_id"]]["query_source"]
                    if query not in existing_source:
                        all_results[v["video_id"]]["query_source"] = f"{existing_source}, {query}"

            time.sleep(sleep_between_calls)

    return list(all_results.values())


def run_for_market(market: str, api_key: str, language: str = "en"):
    """Retourne (nombre de chaînes validées, quota_épuisé)."""
    from config.queries import build_queries
    from discovery.video_stats import enrich_and_filter, dedupe_by_channel
    from discovery.channel_stats import enrich_with_channel_data
    from discovery.language_filter import filter_and_prioritize_by_language
    from discovery.faceless_filter import pre_filter_faceless, score_channel_result
    from discovery.channel_activity import validate_channel_activity
    from discovery.database import save_validated_channels

    print(f"\n{'#' * 60}")
    print(f"# MARCHÉ : {market.upper()}  (langue de recherche : {language})")
    print(f"{'#' * 60}\n")

    seeds = build_queries(market, language)
    learned = {"queries": [], "active": [], "tests": [], "new": [], "radar": [], "info": None}
    try:
        from discovery.keyword_engine import plan_learned_queries
        learned = plan_learned_queries(market, language, seeds)
    except Exception as e:
        print(f"  (mots-clés appris ignorés : {type(e).__name__}: {e})")
    seed_keys = {s.lower() for s in seeds}
    queries = seeds + [q for q in learned["queries"] if q.lower() not in seed_keys]
    print(f"{len(seeds)} requêtes de départ + {len(queries) - len(seeds)} mot(s)-clé(s) appris pour '{market}'.")
    for label, items in (("ACTIF", learned["active"]), ("EN TEST", learned["tests"]),
                         ("RADAR", learned.get("radar", [])), ("NOUVEAU", learned["new"])):
        for kw in items:
            print(f"    + [{label}] {kw['query']}")
    if learned["info"] and not learned["info"]["enough_data"]:
        print("    (pas encore assez de titres pour apprendre de nouveaux mots-clés sur ce marché)")
    print()

    results = discover_market(queries, api_key, language=language)
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

    print("\nFiltre faceless (texte multilingue, avant analyse coûteuse d'activité)...")
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
            # Score de texte multilingue sur l'ensemble des titres de la chaîne.
            text_score = score_channel_result(result)
            if text_score["verdict"] == "face":
                print(f"    -> rejetée (texte non-faceless : {text_score['hits']}/{text_score['total']} titres, "
                      f"ex: {text_score['examples'][:1]})")
                continue
            if text_score["verdict"] == "doubtful":
                print(f"    -> douteuse ({text_score['hits']}/{text_score['total']} titres avec signal)")
            result["face_text_ratio"] = text_score["ratio"]
            result["face_text_verdict"] = text_score["verdict"]
            result["density_score"] = result["strong_video_count"] / result["total_videos_checked"]
            result["channel_url"] = f"https://www.youtube.com/channel/{result['channel_id']}"
            validated.append(result)

    validated.sort(key=lambda v: (v["channel_status"] != "PROVEN", -v["density_score"]))

    # Visages sur les miniatures (tag "Visage ?"). Ignoré sans bloquer si OpenCV n'est pas installé.
    print("\nAnalyse des visages sur les miniatures...")
    try:
        from discovery.face_detect import attach_face_scores
        attach_face_scores(validated)
    except ImportError as e:
        print(f"  (analyse des miniatures ignorée : {e})")

    proven_count = sum(1 for v in validated if v["channel_status"] == "PROVEN")
    watchlist_count = len(validated) - proven_count

    print(f"\n=== {len(validated)} CHAÎNES VALIDÉES pour '{market}' "
          f"({proven_count} proven, {watchlist_count} watchlist) ===\n")
    for v in validated:
        print(f"- [{v['channel_status']}] [{v['density_score']:.0%}] {v['channel_title']} | "
              f"{v['subscriber_count']:,} abonnés | {v['proven_video_count']} vidéos >=100K | "
              f"{v['strong_video_count']} vidéos fortes sur {v['total_videos_checked']} vidéos")
        print(f"    {v['channel_url']}")

    # Chaînes déjà en base avant cette passe (pour savoir lesquelles sont vraiment nouvelles).
    known_before = None
    if learned["queries"]:
        try:
            from discovery.database import existing_channel_ids
            known_before = existing_channel_ids([v["channel_id"] for v in validated])
        except Exception as e:
            print(f"  (mots-clés appris non jugés cette fois : {type(e).__name__}: {e})")

    save_validated_channels(validated, market=market)

    # Jugement des mots-clés appris (seulement si la passe est allée au bout).
    if learned["queries"] and known_before is not None:
        if quota_stopped:
            print("\nMots-clés appris : passe incomplète (quota épuisé), résultats non comptés.")
        else:
            try:
                from discovery.keyword_engine import record_pass_results
                summary = record_pass_results(market, language, learned, seeds,
                                              with_channels, validated, known_before)
                print("\nMots-clés appris, résultat de la passe :")
                for s in summary:
                    change = "" if s["old_status"] == s["new_status"] else f" -> {s['new_status'].upper()}"
                    print(f"  - {s['query']}: {s['found']} chaîne(s) trouvée(s), "
                          f"{s['fresh']} nouvelle(s) validée(s) (passe {s['times_run']}){change}")
            except Exception as e:
                print(f"  (jugement des mots-clés ignoré : {type(e).__name__}: {e})")

    return len(validated), quota_stopped


if __name__ == "__main__":
    from config.markets import MARKETS
    from config.queries import LANGUAGES, OTHER_LANGUAGES

    parser = argparse.ArgumentParser(description="Découverte de chaînes faceless émergentes par marché.")
    parser.add_argument(
        "markets",
        nargs="+",
        help="Un ou plusieurs marchés à traiter (ex: history finance military), ou 'all' pour tous les marchés définis.",
    )
    parser.add_argument(
        "--lang",
        default="en",
        help="Langue de recherche : en (défaut), es, fr, de, ru, ou 'others' (es+fr+de+ru).",
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

    lang_arg = args.lang.lower()
    if lang_arg == "others":
        languages_to_run = list(OTHER_LANGUAGES)
    elif lang_arg in LANGUAGES:
        languages_to_run = [lang_arg]
    else:
        raise SystemExit(f"Langue inconnue: {args.lang}. Choix : {LANGUAGES + ['others']}")

    print(f"{key_count()} clé(s) API chargée(s).")
    print(f"Marchés à traiter : {markets_to_run}")
    print(f"Langues de recherche : {languages_to_run}\n")

    summary = {}
    stop_all = False
    for language in languages_to_run:
        for market in markets_to_run:
            label = f"{market} [{language}]"
            try:
                count, quota_stopped = run_for_market(market, api_key, language)
            except QuotaExhaustedError:
                print(f"\n[!] Toutes les clés sont épuisées pendant la recherche de '{label}'. Arrêt.")
                summary[label] = "interrompu (quota)"
                stop_all = True
                break
            summary[label] = count
            if quota_stopped:
                print("\n[!] Quota épuisé sur toutes les clés : les marchés suivants ne sont pas lancés.")
                stop_all = True
                break
        if stop_all:
            break

    print(f"\n{'=' * 60}")
    print("RÉSUMÉ GLOBAL")
    print(f"{'=' * 60}\n")
    for market, count in summary.items():
        print(f"  {market}: {count} chaîne(s) validée(s)" if isinstance(count, int) else f"  {market}: {count}")