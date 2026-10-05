"""
Automatise la recherche de mots-clés en Breakout sur Google Trends,
en partant des `topics` déjà définis dans config/markets.py pour un
marché donné (jamais du nom du marché seul).

Pytrends est très vite limité en débit par Google (erreur 429) — ce
module espace fortement les appels et n'en fait qu'un seul par sujet
(related_queries) plutôt que deux, pour rester sous le radar.
"""

import time

from pytrends.request import TrendReq

# Mots qui trahissent presque toujours du bruit : jeux vidéo,
# téléréalité, musique, mobilier, fiction — enrichi au fil des marchés
# testés (ex: "roblox", "call of duty", "season" venus du test Military).
NOISE_WORDS = {
    "song", "songs", "music", "bed", "furniture", "vs", "tattoo",
    "parade", "costume", "toy", "toys", "coloring", "font", "logo font",
    "wallpaper", "wallpapers", "meme", "memes",
    "roblox", "call", "duty", "zombies", "easter", "egg", "season",
    "game", "games", "gameplay", "movie", "film", "netflix", "episode",
}

RETRY_DELAY_SECONDS = 30
MAX_RETRIES = 2
REQUEST_TIMEOUT = 30


def _looks_like_noise(query: str) -> bool:
    words = query.lower().split()
    return any(w in NOISE_WORDS for w in words)


def _safe_pytrends_call(func, *args, **kwargs):
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            print(f"    [!] Erreur pytrends (tentative {attempt}/{MAX_RETRIES}): {e}")
            if attempt < MAX_RETRIES:
                print(f"    ... attente {RETRY_DELAY_SECONDS}s avant nouvelle tentative")
                time.sleep(RETRY_DELAY_SECONDS)
    return None


def _shortened_version(topic: str) -> str | None:
    words = topic.split()
    if len(words) <= 2:
        return None
    return " ".join(words[:2])


def get_breakout_queries_for_topic(pytrends: TrendReq, topic: str, geo: str = "US",
                                    timeframe: str = "today 3-m") -> dict:
    def _build_and_fetch(query_term):
        pytrends.build_payload([query_term], cat=0, timeframe=timeframe, geo=geo, gprop="youtube")
        return pytrends.related_queries()

    used_topic = topic
    related = _safe_pytrends_call(_build_and_fetch, topic)
    data = related.get(topic, {}) if related else {}

    no_data = related is None or (data.get("rising") is None and data.get("top") is None)
    if no_data:
        short = _shortened_version(topic)
        if short:
            print(f"    (pas assez de données pour '{topic}', repli sur '{short}')")
            time.sleep(10)
            used_topic = short
            related = _safe_pytrends_call(_build_and_fetch, short)
            data = related.get(short, {}) if related else {}

    if related is None:
        return {"topic": topic, "used_topic": used_topic, "breakout_queries": [],
                "top_queries": [], "status": "ERROR"}

    rising = data.get("rising")
    top = data.get("top")

    breakout_queries = []
    if rising is not None:
        for _, row in rising.iterrows():
            query_text = row["query"]
            if _looks_like_noise(query_text):
                continue
            if str(row.get("value")) == "Breakout" or (
                isinstance(row.get("value"), (int, float)) and row["value"] > 100
            ):
                breakout_queries.append(query_text)

    top_queries = []
    if top is not None:
        for _, row in top.iterrows():
            query_text = row["query"]
            if not _looks_like_noise(query_text):
                top_queries.append(query_text)

    status = "OK" if (rising is not None or top is not None) else "NO_DATA"
    return {
        "topic": topic,
        "used_topic": used_topic,
        "breakout_queries": breakout_queries,
        "top_queries": top_queries,
        "status": status,
    }


def refresh_market_keywords(market: str, geo: str = "US", sleep_between_calls: float = 20.0) -> dict:
    from config.markets import MARKETS

    if market not in MARKETS:
        raise ValueError(f"Marché inconnu: {market}")

    topics = MARKETS[market]["topics"]
    pytrends = TrendReq(hl="en-US", tz=360, timeout=(REQUEST_TIMEOUT, REQUEST_TIMEOUT), retries=0)

    results = {}
    for i, topic in enumerate(topics, 1):
        print(f"[{i}/{len(topics)}] '{topic}'...")
        breakout_data = get_breakout_queries_for_topic(pytrends, topic, geo=geo)
        results[topic] = breakout_data
        if i < len(topics):
            print(f"    ... pause {sleep_between_calls}s avant le sujet suivant")
            time.sleep(sleep_between_calls)

    return results


if __name__ == "__main__":
    MARKET = "animals"

    print(f"Rafraîchissement des mots-clés pour '{MARKET}' (topics déjà définis dans markets.py)\n")
    results = refresh_market_keywords(MARKET)

    print(f"\n{'=' * 60}")
    print("RÉSUMÉ")
    print(f"{'=' * 60}\n")

    all_new_breakouts = []
    for topic, data in results.items():
        used_note = f" (via '{data['used_topic']}')" if data["used_topic"] != topic else ""
        print(f"{topic}{used_note} [{data['status']}]")
        if data["breakout_queries"]:
            for q in data["breakout_queries"]:
                print(f"    🚀 BREAKOUT: {q}")
                all_new_breakouts.append(q)
        if data["top_queries"]:
            print(f"    (top: {', '.join(data['top_queries'][:5])})")
        print()

    print(f"\nTotal de nouvelles requêtes Breakout détectées : {len(all_new_breakouts)}")
    if all_new_breakouts:
        print("Candidats à ajouter aux topics de ce marché :")
        for q in all_new_breakouts:
            print(f"  - {q}")