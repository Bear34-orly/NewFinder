"""
Proximité entre deux chaînes, calculée à partir de mesures (pas d'IA).

Score 0-100 = moyenne pondérée de :
  - taille (abonnés)                       poids 30
  - sujets (mots communs dans les titres)  poids 30
  - durée médiane des vidéos               poids 15
  - fréquence de publication               poids 10
  - même marché (si connu des deux côtés)  poids 15

Une composante inconnue est ignorée (le score est recalculé sur le reste).
Le "même format" n'est PAS mesurable automatiquement : c'est l'utilisateur
qui confirme ou retire chaque concurrent proposé.
"""

import math
from collections import Counter

from competition.metrics import tokens

WEIGHTS = {"size": 30, "topics": 30, "duration": 15, "frequency": 10, "market": 15}


def keyword_counter(profile: dict) -> Counter:
    c = Counter()
    for v in profile.get("videos", []):
        c.update(set(tokens(v["title"])))  # un mot compte une fois par titre
    return c


def top_keywords(profile: dict, n: int = 30) -> set:
    return {w for w, _ in keyword_counter(profile).most_common(n)}


def search_queries(profile: dict, max_queries: int = 2) -> list:
    """Construit les requêtes de recherche YouTube à partir des titres de la chaîne."""
    bigrams = Counter()
    unigrams = Counter()
    for v in profile.get("videos", []):
        toks = tokens(v["title"])
        unigrams.update(set(toks))
        bigrams.update({f"{a} {b}" for a, b in zip(toks, toks[1:])})

    queries = []
    top_bi = [b for b, n in bigrams.most_common(3) if n >= 2]
    if top_bi:
        queries.append(top_bi[0])
    top_uni = [w for w, _ in unigrams.most_common(6)]
    if len(top_uni) >= 3:
        queries.append(" ".join(top_uni[:3]))
    elif top_uni:
        queries.append(" ".join(top_uni))
    if len(queries) < max_queries and len(top_bi) > 1:
        queries.append(top_bi[1])

    seen, out = set(), []
    for q in queries:
        if q and q not in seen:
            seen.add(q)
            out.append(q)
    return out[:max_queries]


def _log_closeness(a, b, scale):
    """1 si a == b, décroît avec le rapport (échelle logarithmique)."""
    if not a or not b or a <= 0 or b <= 0:
        return None
    return max(0.0, 1.0 - abs(math.log(a / b)) / scale)


def similarity(mine: dict, other: dict, same_market=None) -> dict:
    parts = {}

    parts["size"] = _log_closeness(mine.get("subscribers"), other.get("subscribers"), math.log(30))

    a, b = top_keywords(mine), top_keywords(other)
    if a and b:
        jac = len(a & b) / len(a | b)
        parts["topics"] = min(1.0, jac / 0.25)
        common = sorted(a & b)
    else:
        parts["topics"] = None
        common = []
    common_count = len(common)

    parts["duration"] = _log_closeness(mine.get("median_duration_min"), other.get("median_duration_min"), math.log(4))
    parts["frequency"] = _log_closeness(mine.get("videos_per_month"), other.get("videos_per_month"), math.log(8))
    parts["market"] = None if same_market is None else (1.0 if same_market else 0.0)

    total_w = sum(WEIGHTS[k] for k, v in parts.items() if v is not None)
    score = (sum(WEIGHTS[k] * v for k, v in parts.items() if v is not None) / total_w * 100) if total_w else 0

    return {
        "score": round(score),
        "parts": {k: (None if v is None else round(v * 100)) for k, v in parts.items()},
        "common_keywords": common[:8],
        "common_count": common_count,
    }
