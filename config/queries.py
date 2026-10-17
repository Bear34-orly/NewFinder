"""
Construit la liste des requêtes de recherche d'un marché dans une langue.

- Anglais : les sujets de config/markets.py + les 4 premiers sujets combinés
  avec 3 formules de titre. Les formules tournent chaque semaine, pour que
  toutes finissent par être utilisées. Les doublons sont retirés.
- Autres langues (es, fr, de, ru) : tous les sujets traduits du marché (config/translations.py et
  config/translations_more.py) + une partie de la réserve, et, comme en anglais, les 4 premiers sujets
  combinés avec 3 formules de titre traduites (désactivable : USE_FORMULAS_OTHER_LANGUAGES).
"""

from datetime import date

from config.markets import MARKETS
from config.translations import TRANSLATED_TOPICS
from config.extra_topics import EXTRA_PER_RUN, EXTRA_TOPICS, EXTRA_TRANSLATED
from config.translations_more import FORMULAS

LANGUAGES = ["en", "es", "fr", "de", "ru"]
OTHER_LANGUAGES = ["es", "fr", "de", "ru"]
FORMULAS_PER_RUN = 3
USE_FORMULAS_OTHER_LANGUAGES = True   # False : les autres langues n'utilisent plus les formules de titre (moins de requêtes)


def _dedupe(items: list[str]) -> list[str]:
    seen = set()
    out = []
    for q in items:
        key = q.strip().lower()
        if key and key not in seen:
            seen.add(key)
            out.append(q.strip())
    return out


def _rotated_formulas(formulas: list[str], week: int) -> list[str]:
    if not formulas:
        return []
    start = week % len(formulas)
    rotated = formulas[start:] + formulas[:start]
    return rotated[:FORMULAS_PER_RUN]


def _rotated_extras(items: list[str], week: int) -> list[str]:
    """Prend EXTRA_PER_RUN mots-clés de la réserve, en rotation chaque semaine."""
    if not items:
        return []
    start = (week * EXTRA_PER_RUN) % len(items)
    rotated = items[start:] + items[:start]
    return rotated[:EXTRA_PER_RUN]


def build_queries(market: str, language: str = "en", week: int | None = None) -> list[str]:
    if market not in MARKETS:
        raise ValueError(f"Marché inconnu: {market}")
    if language not in LANGUAGES:
        raise ValueError(f"Langue inconnue: {language}")

    if week is None:
        week = date.today().isocalendar()[1]

    if language == "en":
        cfg = MARKETS[market]
        queries = list(cfg["topics"]) + _rotated_extras(EXTRA_TOPICS.get(market, []), week)
        formulas = _rotated_formulas(cfg["title_formulas"], week)
        for topic in cfg["topics"][:4]:
            for formula in formulas:
                queries.append(f"{topic} {formula}")
        return _dedupe(queries)

    translated = TRANSLATED_TOPICS.get(market, {}).get(language, [])
    extras = _rotated_extras(EXTRA_TRANSLATED.get(market, {}).get(language, []), week)
    queries = list(translated) + extras
    if USE_FORMULAS_OTHER_LANGUAGES:
        formulas = _rotated_formulas(MARKETS[market]["title_formulas"], week)
        for topic in translated[:4]:
            for formula in formulas:
                translated_formula = FORMULAS.get(formula, {}).get(language)
                if translated_formula:
                    queries.append(f"{topic} {translated_formula}")
    return _dedupe(queries)
